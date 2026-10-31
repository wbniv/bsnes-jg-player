#!/usr/bin/env python3
"""Verified release candidates and a resumable, single-writer R2 publisher."""
import argparse
import contextlib
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BUCKET = 'bsnes-jg-downloads'
PREFIX = 'bsnes-jg/releases/'
POINTER = 'bsnes-jg/current.json'
ALIAS = 'bsnes-jg-wasm/current.json'
CONTROL = 'bsnes-jg/_release/'
PUBLIC = 'https://downloads.biohack.net/'
LANDING = PUBLIC + 'bsnes-jg/'
CERT = '1bc3d0586ff02c6be1479785652484ba70efccdfee46ce451520d221802d9a5e'
IMMUTABLE = 'public, max-age=31536000, immutable'
MUTABLE = 'no-store'
VERSION = re.compile(r'0|[1-9][0-9]*')
PACKAGES = {'player': 'org.bsnesjg.tv.native', 'library': 'org.bsnesjg.tv.native.phase2'}
SSM = '/indri-studio/bsnes-jg/release/r2'
CACHE = ROOT / '.private/release/r2.json'

class ReleaseError(Exception):
    pass

class Conflict(ReleaseError):
    pass

def require(ok, message):
    if not ok:
        raise ReleaseError(message)

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def version(value):
    require(len(value.split('.')) == 3 and all(VERSION.fullmatch(p) for p in value.split('.')), 'Use a numeric major.minor.patch version')
    return value

def run(args, **kwargs):
    return subprocess.check_output([str(a) for a in args], text=True, **kwargs).strip()

def safe_name(name):
    require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name), 'Invalid artifact filename')
    return name

def record_check(record):
    version(record['versionName'])
    require(type(record['versionCode']) is int and 0 < record['versionCode'] <= 2100000000, 'Invalid Android version code')
    artifacts = record['artifacts']
    require(len(artifacts) == 2 and {a['type'] for a in artifacts} == set(PACKAGES), 'Exactly player and library APKs required')
    require(len({a['filename'] for a in artifacts}) == 2, 'Duplicate artifact names')
    for a in artifacts:
        safe_name(a['filename'])
        require(a['filename'].startswith('bsnes-jg_') and a['filename'].endswith('-v'+record['versionName']+'.apk') and a['packageId'] == PACKAGES[a['type']] and a['engine'] == 'native', 'Wrong artifact identity')
        require(re.fullmatch('[0-9a-f]{64}', a['sha256']) and type(a['bytes']) is int and a['bytes'] > 0, 'Invalid artifact digest/size')
        require(a['url'] == PUBLIC + PREFIX + record['versionName'] + '/' + a['filename'], 'Unexpected public artifact URL')

def pointer_check(pointer):
    require(set(pointer) >= {'current','previous'}, 'Malformed current/previous pointer')
    record_check(pointer['current'])
    if pointer['previous']:
        record_check(pointer['previous'])
        require(pointer['current']['versionName'] != pointer['previous']['versionName'], 'Current and previous must differ')

def sdk_tool(name):
    base = Path(os.environ.get('ANDROID_HOME', str(Path.home() / 'android-sdk-local'))) / 'build-tools'
    matches = sorted(base.glob('*/' + name), key=lambda p: tuple(int(x) for x in p.parent.name.split('.') if x.isdigit()))
    if not matches:
        matches = sorted((Path.home()/'android-sdk-local/build-tools').glob('*/'+name))
    require(bool(matches), 'Android build tool missing: ' + name)
    return matches[-1]

def inspect_apk(path, kind, name, code, demo, catalog):
    report = run([sdk_tool('apksigner'), 'verify', '--verbose', '--print-certs', path])
    certs = re.findall(r'Signer #\d+ certificate SHA-256 digest: ([0-9a-fA-F]+)', report)
    require(certs == [CERT], 'APK must use the established release certificate')
    badging = run([sdk_tool('aapt'), 'dump', 'badging', path])
    package = re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", badging)
    require(package and package.groups() == (PACKAGES[kind], str(code), name), 'APK package/version mismatch')
    require('application-debuggable' not in badging, 'Debuggable APK is not a public release')
    with zipfile.ZipFile(path) as apk:
        names = apk.namelist()
        require(len(names) == len(set(names)), 'Duplicate APK entries')
        for abi in ['armeabi-v7a', 'arm64-v8a']:
            require(any(n.startswith('lib/' + abi + '/') and n.endswith('.so') for n in names), 'Missing native ABI ' + abi)
        if kind == 'player':
            roms = [n for n in names if n.startswith('assets/roms/') and n.endswith('.sfc')]
            require(roms == ['assets/roms/' + safe_name(demo['slug']) + '.sfc'], 'Player must contain only the selected demo')
            require(sha(apk.read(roms[0])) == demo['sha256'], 'Player demo hash mismatch')
        else:
            require(apk.read('assets/roms/library.json') == catalog, 'Library catalog changed during build')
            rows = json.loads(catalog)['roms']
            require(rows and len({r['slug'] for r in rows}) == len(rows), 'Empty/duplicate library inventory')
            expected = set()
            for row in rows:
                rom = 'assets/roms/' + safe_name(row['filename'])
                require(row['card'] == 'cards/' + safe_name(row['slug']) + '.png', 'Unsafe artwork path')
                card = 'assets/roms/' + row['card']
                expected.add(rom)
                require(sha(apk.read(rom)) == row['romSha256'] and len(apk.read(rom)) == row['size'], 'Library ROM mismatch')
                require(sha(apk.read(card)) == row['cardSha256'], 'Library artwork mismatch')
            require({n for n in names if n.startswith('assets/roms/') and n.endswith('.sfc')} == expected, 'Unexpected library ROM')
    data = path.read_bytes()
    return {'name': 'Native ' + kind, 'packageId': PACKAGES[kind], 'engine': 'native', 'type': kind,
            'filename': path.name, 'bytes': len(data), 'sha256': sha(data), 'certificateSha256': CERT,
            'url': PUBLIC + PREFIX + name + '/' + path.name}

class S3Store:
    """AWS CLI v2 transport. Credentials stay in environment, errors are redacted."""
    def __init__(self):
        require(CACHE.exists(), 'Run task secrets-pull first')
        require(CACHE.stat().st_mode & 0o077 == 0, 'Credential cache must be mode 0600')
        config = json.loads(CACHE.read_text())
        require(config['bucket'] == BUCKET and re.fullmatch('[0-9a-f]{32}', config['accountId']), 'Unexpected R2 configuration')
        self.endpoint = 'https://' + config['accountId'] + '.r2.cloudflarestorage.com'
        self.env = {k:v for k,v in os.environ.items() if not k.startswith('AWS_')}
        self.env.update(AWS_ACCESS_KEY_ID=config['accessKeyId'], AWS_SECRET_ACCESS_KEY=config['secretAccessKey'],
                        AWS_DEFAULT_REGION='auto', AWS_EC2_METADATA_DISABLED='true', AWS_PAGER='')

    def call(self, op, args, missing=False):
        result = subprocess.run(['aws','--endpoint-url',self.endpoint,'s3api',op,'--bucket',BUCKET,*args], env=self.env, capture_output=True, text=True)
        if result.returncode:
            if 'PreconditionFailed' in result.stderr or 'ConditionalRequestConflict' in result.stderr:
                raise Conflict('Conditional object write rejected')
            if missing and ('NoSuchKey' in result.stderr or '(404)' in result.stderr):
                return None
            raise ReleaseError('R2 operation failed: ' + op + ' (check credential scope/connectivity; credentials redacted)')
        return json.loads(result.stdout or '{}')

    def get(self, key):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)/'object'
            r = self.call('get-object',['--key',key,str(dest)], missing=True)
            return None if r is None else (dest.read_bytes(), r['ETag'])

    def put(self, key, data, cache=MUTABLE, absent=False, etag=None):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp)/'object'; src.write_bytes(data)
            args = ['--key',key,'--body',str(src),'--cache-control',cache,'--content-type',
                    'application/vnd.android.package-archive' if key.endswith('.apk') else 'application/json']
            if absent: args += ['--if-none-match','*']
            if etag: args += ['--if-match',etag]
            return self.call('put-object',args)['ETag']

    def delete(self, key):
        self.call('delete-object',['--key',key])

    def keys(self, prefix):
        # AWS CLI auto-paginates ListObjectsV2.
        return [x['Key'] for x in self.call('list-objects-v2',['--prefix',prefix]).get('Contents',[])]

def public_read(key):
    with urllib.request.urlopen(PUBLIC + key, timeout=90) as response:
        return response.read(), response.headers.get('Cache-Control','')

def verify_public(key, data, immutable=True):
    actual, cache = public_read(key)
    require(sha(actual) == sha(data) and len(actual) == len(data), 'Public download hash mismatch: ' + key)
    require(('immutable' in cache) if immutable else ('no-store' in cache or 'must-revalidate' in cache), 'Wrong public cache headers: ' + key)

def immutable_put(store, key, data):
    existing = store.get(key)
    if existing:
        require(existing[0] == data, 'Immutable release object differs: ' + key)
    else:
        store.put(key, data, IMMUTABLE, absent=True)

def load_candidate(path):
    path = Path(path).resolve()
    record = json.loads((path/'release.json').read_text()); record_check(record)
    require(record.get('certificateSha256') == CERT, 'Candidate certificate identity missing')
    require(record.get('publicDownloadUrl') == LANDING, 'Candidate public QR configuration missing')
    demo = json.loads((path/'demo-rom.json').read_text()); catalog = (path/'library.json').read_bytes()
    require(sha(catalog) == record['libraryInventorySha256'], 'Candidate catalog changed')
    for a in record['artifacts']:
        file = path/a['filename']
        require(not file.is_symlink() and file.is_file(), 'Candidate must use regular local files')
        actual = inspect_apk(file,a['type'],record['versionName'],record['versionCode'],demo,catalog)
        require(actual == a, 'Candidate artifact inspection changed')
    web = record['web']; safe_name(web['filename'])
    require(sha((path/web['filename']).read_bytes()) == web['sha256'], 'Browser package changed')
    return record

@contextlib.contextmanager
def release_lock(store, candidate_id):
    token = uuid.uuid4().hex
    body = encoded({'token':token,'candidate':candidate_id,'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    try:
        store.put(CONTROL+'lock.json',body,absent=True)
    except Conflict:
        raise ReleaseError('Another release owns the remote lock. Inspect it; never auto-expire a live publisher.')
    try:
        yield
    finally:
        current = store.get(CONTROL+'lock.json')
        if current and current[0] == body:
            store.delete(CONTROL+'lock.json')

def publish(store, record, folder, verify=verify_public):
    """Caller inspects candidate first. Every remote mutation holds the remote lock."""
    record_check(record)
    folder = Path(folder)
    identity = sha(encoded(record))
    with release_lock(store, identity):
        raw = store.get(POINTER); require(raw is not None, 'Initial bootstrap needs a reviewed current manifest')
        pointer = json.loads(raw[0]); pointer_check(pointer)
        journal_key = CONTROL+'journals/'+record['versionName']+'.json'
        journal_raw = store.get(journal_key)
        if journal_raw:
            journal = json.loads(journal_raw[0]); require(journal['candidate'] == identity, 'Version belongs to another candidate')
        else:
            require(record['versionName'] not in [r['versionName'] for r in pointer.values() if isinstance(r,dict) and 'versionName' in r], 'Version already published')
            high_raw = store.get(CONTROL+'high-water.json')
            high = max([r['versionCode'] for r in [pointer['current'],pointer['previous']] if r] + [json.loads(high_raw[0])['versionCode'] if high_raw else 0])
            require(record['versionCode'] > high, 'Android versionCode must exceed publication high-water mark')
            journal = {'candidate':identity,'base':pointer,'phase':'prepared','versionCode':record['versionCode']}
            # Journal first: a crash after reserving the high-water mark remains resumable.
            store.put(journal_key,encoded(journal),absent=True)
        current_is_candidate = pointer['current'] == record
        require(current_is_candidate or pointer == journal['base'], 'Current pointer changed since this candidate began')
        high_raw = store.get(CONTROL+'high-water.json')
        high = json.loads(high_raw[0])['versionCode'] if high_raw else 0
        require(high <= record['versionCode'] or current_is_candidate, 'A later candidate has reserved a higher versionCode')
        store.put(CONTROL+'high-water.json',encoded({'versionCode':max(high,record['versionCode'])}))
        base = PREFIX+record['versionName']+'/'
        for a in record['artifacts']:
            data = (folder/a['filename']).read_bytes()
            require(sha(data) == a['sha256'] and len(data) == a['bytes'], 'Candidate bytes changed')
            immutable_put(store,base+a['filename'],data)
            verify(base+a['filename'],data)
        immutable_put(store,base+'release.json',encoded(record))
        verify(base+'release.json',encoded(record))
        new_pointer = {'current':record,'previous':journal['base']['current']}
        # Compare and swap protects against changes made outside this publisher.
        if not current_is_candidate:
            store.put(POINTER,encoded(new_pointer),etag=raw[1])
        journal['phase'] = 'published'; store.put(journal_key,encoded(journal))
        store.put(ALIAS,encoded(new_pointer))
        verify(POINTER,encoded(new_pointer),False); verify(ALIAS,encoded(new_pointer),False)
        keep = {r['versionName'] for r in new_pointer.values() if r}
        # Build and validate the complete deletion set before deleting any object.
        deletes = []
        for key in store.keys(PREFIX):
            parts = key[len(PREFIX):].split('/')
            require(len(parts) == 2, 'Unexpected nested object; refusing to prune: '+key)
            v, filename = parts; version(v); safe_name(filename)
            require(filename == 'release.json' or filename.startswith('bsnes-jg_') and filename.endswith('-v'+v+'.apk'), 'Unrecognized release object; refusing to prune: '+key)
            if v not in keep: deletes.append(key)
        require(store.get(POINTER)[0] == encoded(new_pointer), 'Pointer changed before prune')
        for key in deletes: store.delete(key)
        require({k[len(PREFIX):].split('/')[0] for k in store.keys(PREFIX)} == keep, 'Retention verification failed')
        journal.update(phase='complete',deleted=deletes)
        store.put(journal_key,encoded(journal))
        return {'candidate':identity,'status':'complete','current':record['versionName'],
                'previous':new_pointer['previous']['versionName'],'deleted':deletes}

def prepare(args):
    name = version(args.version); code = args.version_code
    require(0 < code <= 2100000000, 'Invalid Android versionCode')
    baseline = json.loads((ROOT/'docs/releases/current.json').read_text()); pointer_check(baseline)
    require(code > max(r['versionCode'] for r in baseline.values() if isinstance(r,dict) and 'versionCode' in r), 'Version code must exceed local release history')
    require(not run(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT), 'Commit tracked changes before preparing a release')
    revision = run(['git','rev-parse','HEAD'],cwd=ROOT)
    tracked = run(['git','ls-files','-z'],cwd=ROOT).split('\0')
    inputs = {p:sha((ROOT/p).read_bytes()) for p in tracked if p and not p.startswith('dist/') and (ROOT/p).is_file()}
    target = ROOT/'.private/release/candidates'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    require(not target.exists(), 'Candidate directory already exists; inspect/resume it instead')
    # Android retains its validated fixture; browser packaging uses an isolated tree.
    env = dict(os.environ, EMSDK_VERSION='6.0.4', ORG_GRADLE_PROJECT_releaseVersionName=name,
               ORG_GRADLE_PROJECT_releaseVersionCode=str(code), ORG_GRADLE_PROJECT_publicDownloadUrl=LANDING)
    for command in [['./android/tools/release-signing-secrets.sh','build'],['./build.sh']]:
        subprocess.run(command,cwd=ROOT,env=env,check=True)
    require(run(['git','rev-parse','HEAD'],cwd=ROOT) == revision, 'Source revision changed while building')
    require(all((ROOT/p).is_file() and sha((ROOT/p).read_bytes()) == digest for p,digest in inputs.items()), 'Tracked source inputs changed during build')
    catalog = ROOT/'android/app/build/generated/publishedLibrary/library.json'
    demo = json.loads((ROOT/'demo-rom.json').read_text())
    with tempfile.TemporaryDirectory(dir=ROOT/'.private/release') as tmp:
        folder=Path(tmp); shutil.copyfile(catalog,folder/'library.json'); shutil.copyfile(ROOT/'demo-rom.json',folder/'demo-rom.json')
        artifacts=[]
        for kind,flavor,slug in [('library','native','llvm-65816-torture-test-suite-on-snes'),('player','nativeplayer',demo['apkSlug'])]:
            file=folder/('bsnes-jg_'+safe_name(slug)+'-v'+name+'.apk')
            shutil.copyfile(ROOT/f'android/app/build/outputs/apk/{flavor}/release/app-{flavor}-release.apk',file)
            artifacts.append(inspect_apk(file,kind,name,code,demo,catalog.read_bytes()))
        webname='bsnes-jg-player-web-'+name+'.tgz'
        with tempfile.TemporaryDirectory(dir=ROOT/'.private/release') as package_tmp:
            package=Path(package_tmp)
            for name_ in ['package.json','LICENSE','NOTICE','README.md','demo-rom.json']:
                shutil.copyfile(ROOT/name_,package/name_)
            for name_ in ['astro','embed','bin']:
                shutil.copytree(ROOT/name_,package/name_)
            (package/'scripts').mkdir()
            shutil.copyfile(ROOT/'scripts/stage-dist.sh',package/'scripts/stage-dist.sh')
            (package/'web').symlink_to(ROOT/'web',target_is_directory=True)
            subprocess.run(['bash',str(package/'scripts/stage-dist.sh')],check=True,env=env)
            subprocess.run(['python3',str(ROOT/'scripts/release/fidelity.py'),str(package/'dist')],check=True)
            smoke=package/'smoke'
            subprocess.run(['node',str(package/'bin/sync.mjs'),'sync',str(smoke),'--demo'],check=True)
            subprocess.run(['node',str(package/'bin/sync.mjs'),'sync','--check',str(smoke)],check=True)
            pack=json.loads(run(['npm','pack','--json','--pack-destination',folder],cwd=package))[0]
        (folder/pack['filename']).rename(folder/webname)
        record={'versionName':name,'versionCode':code,'publishedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'sourceRepository':'https://github.com/wbniv/bsnes-jg-player','sourceRevision':revision,'sourceWorktreeDirty':False,
                'sourceInputsSha256':sha(encoded(inputs)),'certificateSha256':CERT,'publicDownloadUrl':LANDING,'demoRom':demo,'romCount':len(json.loads(catalog.read_text())['roms']),
                'libraryInventorySha256':sha(catalog.read_bytes()),'artifacts':artifacts,
                'web':{'filename':webname,'sha256':sha((folder/webname).read_bytes()),'packageVersion':json.loads((ROOT/'package.json').read_text())['version']},
                'tools':{'node':run(['node','--version']),'java':run(['java','-version'],stderr=subprocess.STDOUT)}}
        (folder/'release.json').write_bytes(encoded(record)); load_candidate(folder)
        shutil.copytree(folder,target)
    print('Verified candidate:',target)
    print('Next: task web:release:preview CANDIDATE='+str(target))

def audit(store):
    raw=store.get(POINTER); require(raw is not None,'Missing release pointer')
    pointer=json.loads(raw[0]); pointer_check(pointer)
    verify_public(POINTER,raw[0],False)
    require(store.get(ALIAS)[0] == raw[0], 'Legacy alias differs')
    for r in [pointer['current'],pointer['previous']]:
        if r:
            for a in r['artifacts']:
                data,cache=public_read(PREFIX+r['versionName']+'/'+a['filename'])
                require(sha(data)==a['sha256'] and len(data)==a['bytes'] and 'immutable' in cache,'Public artifact audit failed')
    expected={r['versionName'] for r in [pointer['current'],pointer['previous']] if r}
    require({k[len(PREFIX):].split('/')[0] for k in store.keys(PREFIX)}==expected,'Unexpected retained release versions')
    print('Public artifact hashes, retention and manifest audit PASS')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare'); p.add_argument('--version',required=True);p.add_argument('--version-code',type=int,required=True)
    for command in ['preview','publish','resume']:
        p=sub.add_parser(command);p.add_argument('--candidate',type=Path,required=True)
    sub.add_parser('check')
    p=sub.add_parser('unlock'); p.add_argument('--token',required=True)
    args=parser.parse_args()
    if args.command=='prepare': return prepare(args)
    store=S3Store()
    if args.command=='check': return audit(store)
    if args.command=='unlock':
        old=store.get(CONTROL+'lock.json');require(old and json.loads(old[0])['token']==args.token,'Lock token does not match')
        require(input('Confirm the owning publisher has stopped; type RELEASE LOCK: ')=='RELEASE LOCK','Cancelled')
        store.delete(CONTROL+'lock.json');return
    record=load_candidate(args.candidate)
    current=json.loads(store.get(POINTER)[0]);pointer_check(current)
    preview={'bucket':BUCKET,'candidate':record['versionName'],'current':current['current']['versionName'],
             'previous':current['previous']['versionName'] if current['previous'] else None,
             'pruneAfterPublication':[k for k in store.keys(PREFIX) if k[len(PREFIX):].split('/')[0] not in {record['versionName'], (current['previous']['versionName'] if current['current']==record and current['previous'] else current['current']['versionName'])}]}
    print(json.dumps(preview,indent=2))
    if args.command=='preview':return
    require(input('Publish these verified bytes and prune older releases? Type PUBLISH: ')=='PUBLISH','Cancelled')
    try:
        result=publish(store,record,args.candidate)
    except ReleaseError:
        observed=store.get(POINTER)
        if observed and json.loads(observed[0]).get('current') == record:
            print('Release is published but verification/alias/cleanup is incomplete. Resume the same candidate.',file=sys.stderr)
        raise
    (args.candidate/'publication-receipt.json').write_bytes(encoded(result));print(json.dumps(result,indent=2))

if __name__=='__main__':
    try: main()
    except (ReleaseError,subprocess.CalledProcessError,OSError,ValueError,KeyError) as error:
        print('Release stopped: '+str(error),file=sys.stderr);sys.exit(1)
