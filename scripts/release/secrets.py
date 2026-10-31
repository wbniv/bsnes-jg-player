#!/usr/bin/env python3
"""Keep R2 credentials in SSM and a private, generated local JSON cache."""
import argparse
import getpass
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
from release import CACHE, SSM, BUCKET, S3Store, require, encoded, ReleaseError


def aws(*args):
    cmd=['aws','--profile',os.environ.get('BSNES_AWS_PROFILE','wf-terraform'),'--region',os.environ.get('BSNES_AWS_REGION','us-west-2'),*args]
    p=subprocess.run(cmd,capture_output=True,text=True)
    require(p.returncode==0,'SSM operation failed; check AWS access (output redacted)')
    return json.loads(p.stdout)


def cache(config):
    CACHE.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(CACHE.parent,0o700)
    with tempfile.NamedTemporaryFile(dir=CACHE.parent,delete=False) as f:
        os.fchmod(f.fileno(),0o600); f.write(encoded(config)); name=f.name
    os.replace(name,CACHE)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['pull','bootstrap','setup','probe']);args=p.parse_args()
    if args.command=='bootstrap':
        # Refuse accidental replacement: rotation requires an explicit separate operation.
        account=aws('ssm','get-parameter','--name','/indri-studio/cloudflare/account_id')['Parameter']['Value'].strip()
        config={'accountId':account,'bucket':BUCKET,'accessKeyId':getpass.getpass('Bucket-scoped R2 access key ID: '),
                'secretAccessKey':getpass.getpass('Bucket-scoped R2 secret access key: ')}
        require(len(account)==32 and all(c in '0123456789abcdef' for c in account),'Invalid account ID')
        require(all(config.values()),'Missing credential field')
        require(input('Store new bucket-scoped credentials in '+SSM+'? Type STORE: ')=='STORE','Cancelled')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'request.json'
            path.write_bytes(encoded({'Name':SSM,'Type':'SecureString','Value':json.dumps(config),'Overwrite':False}));path.chmod(0o600)
            aws('ssm','put-parameter','--cli-input-json','file://'+str(path))
        cache(config)
    elif args.command=='pull':
        value=aws('ssm','get-parameter','--name',SSM,'--with-decryption')['Parameter']['Value']
        config=json.loads(value);require(config.get('bucket')==BUCKET,'Unexpected bucket in SSM');cache(config)
        print('Refreshed private R2 cache; values not printed')
    elif args.command=='setup':
        # Existing infrastructure is deliberately not recreated by the publisher.
        store=S3Store();store.call('head-bucket',[])
        print('Existing project bucket accessible. Domain/permission changes require account administration; no resources changed.')
    else:
        store=S3Store();key='bsnes-jg/_validation/'+uuid.uuid4().hex+'.json';data=encoded({'probe':True})
        try:
            store.put(key,data,absent=True);require(store.get(key)[0]==data,'Probe read mismatch')
        finally:
            store.delete(key)
        require(store.get(key) is None,'Probe deletion failed')
        print('Project-bucket object read/write/delete probe PASS (scope must also be reviewed in provider policy)')

if __name__=='__main__':
    try: main()
    except (ReleaseError,KeyError,ValueError,OSError) as e:
        raise SystemExit('Credential operation stopped: '+str(e))
