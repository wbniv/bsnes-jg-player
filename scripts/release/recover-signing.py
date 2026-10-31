#!/usr/bin/env python3
"""Verify SSM signing recovery without overwriting the working signing cache."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from release import CERT, require
from secrets import aws

with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);os.chmod(root,0o700)
    payload=json.loads(aws('ssm','get-parameter','--name','/indri-studio/bsnes-jg/android/release/signing-payload','--with-decryption')['Parameter']['Value'])
    store=root/'release.p12';password=root/'password'
    store.write_bytes(base64.b64decode(payload['keystoreBase64'],validate=True));store.chmod(0o600)
    password.write_text(payload['storePassword']);password.chmod(0o600)
    cert=subprocess.run(['keytool','-exportcert','-keystore',str(store),'-storepass:file',str(password),'-alias',payload['keyAlias']],capture_output=True)
    require(cert.returncode==0,'Recovered signing payload could not export its certificate (details redacted)')
    require(hashlib.sha256(cert.stdout).hexdigest()==CERT,'Recovered signing identity differs from retained releases')
    print('SSM signing recovery PASS; certificate SHA-256 '+CERT+'; temporary key removed on exit')
