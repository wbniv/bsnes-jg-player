import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import release as r

class MemoryStore:
    def __init__(self): self.objects={};self.fail=None
    def get(self,key):
        if key not in self.objects:return None
        return self.objects[key],r.sha(self.objects[key])
    def put(self,key,data,cache=r.MUTABLE,absent=False,etag=None):
        if self.fail==('put',key): raise r.ReleaseError('injected failure')
        old=self.get(key)
        if absent and old or etag is not None and (not old or old[1]!=etag):raise r.Conflict('condition')
        self.objects[key]=data;return r.sha(data)
    def delete(self,key):
        if self.fail==('delete',key):raise r.ReleaseError('injected failure')
        self.objects.pop(key,None)
    def keys(self,prefix):return sorted(k for k in self.objects if k.startswith(prefix))

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.store=MemoryStore()
        self.old=self.candidate('0.1.8',9);self.current=self.candidate('0.1.9',10);self.new=self.candidate('0.1.10',11)
        self.pointer={'current':self.current,'previous':self.old}
        self.store.put(r.POINTER,r.encoded(self.pointer));self.store.put(r.ALIAS,r.encoded(self.pointer))
        for record in [self.old,self.current]:
            for a in record['artifacts']:self.store.put(r.PREFIX+record['versionName']+'/'+a['filename'],(self.root/a['filename']).read_bytes())
            self.store.put(r.PREFIX+record['versionName']+'/release.json',r.encoded(record))
    def candidate(self,version,code):
        artifacts=[]
        for kind in ['player','library']:
            name=f'bsnes-jg_{kind}-v{version}.apk';data=(version+kind).encode();(self.root/name).write_bytes(data)
            artifacts.append(dict(type=kind,packageId=r.PACKAGES[kind],engine='native',filename=name,bytes=len(data),sha256=r.sha(data),url=r.PUBLIC+r.PREFIX+version+'/'+name))
        return dict(versionName=version,versionCode=code,artifacts=artifacts)
    def verify(self,key,data,immutable=True):self.assertEqual(self.store.get(key)[0],data)
    def publish(self):return r.publish(self.store,self.new,self.root,self.verify)
    def test_third_release_prunes_only_old_and_resume_is_idempotent(self):
        self.store.put('other/keep',b'keep');self.publish();self.publish()
        p=json.loads(self.store.get(r.POINTER)[0]);self.assertEqual(p['previous'],self.current)
        self.assertEqual(p['current'],self.new);self.assertTrue(self.store.get('other/keep'))
        self.assertFalse(any('/0.1.8/' in key for key in self.store.keys(r.PREFIX)))
    def test_upload_failure_preserves_old_pointer_and_resume(self):
        key=r.PREFIX+'0.1.10/'+self.new['artifacts'][1]['filename'];self.store.fail=('put',key)
        with self.assertRaises(r.ReleaseError):self.publish()
        self.assertEqual(json.loads(self.store.get(r.POINTER)[0]),self.pointer)
        self.assertTrue(self.store.get(r.PREFIX+'0.1.8/release.json'))
        self.store.fail=None;self.publish()
    def test_public_hash_failure_never_promotes_or_prunes(self):
        def fail(*args):raise r.ReleaseError('hash mismatch')
        with self.assertRaises(r.ReleaseError):r.publish(self.store,self.new,self.root,fail)
        self.assertEqual(json.loads(self.store.get(r.POINTER)[0]),self.pointer)
        self.assertTrue(self.store.get(r.PREFIX+'0.1.8/release.json'))
    def test_alias_failure_resumes_without_shifting_previous_twice(self):
        self.store.fail=('put',r.ALIAS)
        with self.assertRaises(r.ReleaseError):self.publish()
        self.assertEqual(json.loads(self.store.get(r.POINTER)[0])['current'],self.new)
        self.store.fail=None;self.publish()
        self.assertEqual(json.loads(self.store.get(r.POINTER)[0])['previous'],self.current)
    def test_prune_failure_retains_current_previous_and_resumes(self):
        self.store.fail=('delete',r.PREFIX+'0.1.8/release.json')
        with self.assertRaises(r.ReleaseError):self.publish()
        for v in ['0.1.9','0.1.10']:self.assertTrue(self.store.get(r.PREFIX+v+'/release.json'))
        self.store.fail=None;self.publish()
    def test_concurrent_publisher_is_rejected_without_stealing_lock(self):
        self.store.put(r.CONTROL+'lock.json',b'other owner')
        with self.assertRaises(r.ReleaseError):self.publish()
        self.assertEqual(self.store.get(r.CONTROL+'lock.json')[0],b'other owner')
    def test_external_pointer_change_fails_cas(self):
        changed=copy.deepcopy(self.pointer);changed['previous']=None
        def verify(key,data,immutable=True):
            self.verify(key,data,immutable)
            self.store.put(r.POINTER,r.encoded(changed))
        with self.assertRaises(r.Conflict):r.publish(self.store,self.new,self.root,verify)
        self.assertEqual(json.loads(self.store.get(r.POINTER)[0]),changed)
    def test_unknown_prune_object_stops_before_any_deletion(self):
        self.store.put(r.PREFIX+'0.1.8/do-not-delete.txt',b'x')
        with self.assertRaises(r.ReleaseError):self.publish()
        self.assertTrue(self.store.get(r.PREFIX+'0.1.8/release.json'))
    def test_changed_candidate_cannot_reuse_journal(self):
        self.publish();self.new['extra']='changed'
        with self.assertRaises(r.ReleaseError):self.publish()
    def test_changed_local_bytes_rejected(self):
        (self.root/self.new['artifacts'][0]['filename']).write_bytes(b'tampered')
        with self.assertRaises(r.ReleaseError):self.publish()
        self.assertEqual(json.loads(self.store.get(r.POINTER)[0]),self.pointer)
    def test_highwater_survives_rollback(self):
        self.store.put(r.CONTROL+'high-water.json',r.encoded({'versionCode':15}))
        with self.assertRaises(r.ReleaseError):self.publish()
    def test_immutable_remote_bytes_not_overwritten(self):
        key=r.PREFIX+'0.1.10/'+self.new['artifacts'][0]['filename'];self.store.put(key,b'foreign')
        with self.assertRaises(r.ReleaseError):self.publish()
        self.assertEqual(self.store.get(key)[0],b'foreign')
    def test_interruption_after_journal_before_highwater_resumes(self):
        self.store.fail=('put',r.CONTROL+'high-water.json')
        with self.assertRaises(r.ReleaseError):self.publish()
        self.assertTrue(self.store.get(r.CONTROL+'journals/0.1.10.json'))
        self.store.fail=None;self.publish()
    def test_interruption_after_pointer_before_journal_resumes(self):
        original=self.store.put
        def put(key,data,*args,**kwargs):
            if key==r.CONTROL+'journals/0.1.10.json' and json.loads(data)['phase']=='published':
                raise r.ReleaseError('crash after pointer')
            return original(key,data,*args,**kwargs)
        self.store.put=put
        with self.assertRaises(r.ReleaseError):self.publish()
        self.store.put=original;self.publish()
        self.assertEqual(json.loads(self.store.get(r.POINTER)[0])['previous'],self.current)
    def test_path_traversal_and_duplicate_variants_rejected(self):
        self.new['artifacts'][0]['filename']='../../foreign.apk'
        with self.assertRaises(r.ReleaseError):self.publish()
        self.new=self.candidate('0.1.10',11);self.new['artifacts'][0]=self.new['artifacts'][1]
        with self.assertRaises(r.ReleaseError):self.publish()

class ApkTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.file=Path(self.tmp.name)/'test.apk'
        self.demo={'slug':'demo','sha256':r.sha(b'rom')};self.cert=r.CERT
        self.badging="package: name='org.bsnesjg.tv.native' versionCode='11' versionName='0.1.10'"
        self.make()
    def make(self,rom=b'rom',extra=False):
        with zipfile.ZipFile(self.file,'w') as z:
            z.writestr('assets/roms/demo.sfc',rom)
            if extra:z.writestr('assets/roms/unwanted.sfc',b'x')
            for abi in ['armeabi-v7a','arm64-v8a']:z.writestr('lib/'+abi+'/libcore.so',b'elf')
    def inspect(self):
        def output(args):return 'Signer #1 certificate SHA-256 digest: '+self.cert if 'apksigner' in str(args[0]) else self.badging
        with patch.object(r,'sdk_tool',side_effect=lambda name:Path(name)),patch.object(r,'run',side_effect=output):
            return r.inspect_apk(self.file,'player','0.1.10',11,self.demo,b'')
    def test_expected_certificate_and_payload_pass(self):self.assertEqual(self.inspect()['certificateSha256'],r.CERT)
    def test_wrong_or_debug_key_rejected(self):
        self.cert='0'*64
        with self.assertRaises(r.ReleaseError):self.inspect()
    def test_wrong_package_or_version_rejected(self):
        self.badging=self.badging.replace("versionCode='11'","versionCode='10'")
        with self.assertRaises(r.ReleaseError):self.inspect()
    def test_debuggable_rejected(self):
        self.badging+='\napplication-debuggable'
        with self.assertRaises(r.ReleaseError):self.inspect()
    def test_modified_or_extra_rom_rejected(self):
        self.make(b'bad')
        with self.assertRaises(r.ReleaseError):self.inspect()
        self.make(extra=True)
        with self.assertRaises(r.ReleaseError):self.inspect()

if __name__=='__main__':unittest.main()
