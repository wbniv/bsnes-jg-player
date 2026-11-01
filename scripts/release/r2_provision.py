#!/usr/bin/env python3
"""Provision a publisher account token for the existing player R2 bucket."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid

from release import BUCKET, CACHE, SSM, Conflict, ReleaseError, S3Store, encoded, require

ACCOUNT_PARAMETER = '/indri-studio/cloudflare/account_id'
TOKEN_NAME = 'bsnes-jg-downloads-publisher'
PERMISSION = 'Workers R2 Storage Bucket Item Write'
PENDING = CACHE.with_name('r2-provision-pending.json')


def aws(*args, optional=False):
    result = subprocess.run(
        ['aws', '--profile', os.environ.get('BSNES_AWS_PROFILE', 'wf-terraform'),
         '--region', os.environ.get('BSNES_AWS_REGION', 'us-west-2'), *args],
        capture_output=True, text=True)
    if result.returncode:
        if optional and '(ParameterNotFound)' in result.stderr:
            return None
        raise ReleaseError('SSM request failed; response redacted. Check AWS access.')
    return json.loads(result.stdout or '{}')


def parameter(name, optional=False):
    result = aws('ssm', 'get-parameter', '--name', name, '--with-decryption', optional=optional)
    return None if result is None else result['Parameter']['Value']


def private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as out:
            name = out.name
            os.fchmod(out.fileno(), 0o600)
            out.write(encoded(value))
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def validate_config(config, account):
    require(config.get('bucket') == BUCKET and config.get('accountId') == account,
            'Stored credentials target a different bucket/account; refusing replacement')
    require(re.fullmatch('[0-9a-f]{32}', config.get('accessKeyId', '')) and
            re.fullmatch('[0-9a-f]{64}', config.get('secretAccessKey', '')),
            'Stored S3 credential fields have an unexpected format')


class Cloudflare:
    def __init__(self, account, token):
        self.base = '/accounts/' + account + '/tokens'
        self.token = token

    def request(self, method, path, payload=None):
        request = urllib.request.Request(
            'https://api.cloudflare.com/client/v4' + path,
            data=None if payload is None else encoded(payload), method=method,
            headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            raise ReleaseError(f'Cloudflare {method} {path} failed (HTTP {error.code}); '
                               'bootstrap identity cannot complete this request; response redacted') from None
        except (urllib.error.URLError, TimeoutError, ValueError):
            raise ReleaseError('Cloudflare request failed; response redacted. Retry checks for an existing token before creating another.') from None
        require(result.get('success') is True, 'Cloudflare rejected request; response redacted')
        return result

    def collection(self, path):
        page = 1
        while True:
            result = self.request('GET', path + f'?page={page}&per_page=50')
            yield from result['result']
            info = result.get('result_info', {})
            if page >= info.get('total_pages', 1):
                break
            page += 1

    def create(self, account):
        groups = [g for g in self.collection(self.base + '/permission_groups') if g['name'] == PERMISSION]
        require(len(groups) == 1, 'Bucket item write permission unavailable to this bootstrap identity')
        require(not any(t['name'] == TOKEN_NAME for t in self.collection(self.base)),
                'Publisher token already exists without recoverable local/SSM credentials. Recover it or review revocation; no duplicate created.')
        policy = {'effect': 'allow', 'resources': {
            f'com.cloudflare.edge.r2.bucket.{account}_default_{BUCKET}': '*'},
            'permission_groups': [{'id': groups[0]['id']}]}
        result = self.request('POST', self.base, {'name': TOKEN_NAME, 'policies': [policy]})['result']
        return {'accountId': account, 'bucket': BUCKET, 'accessKeyId': result['id'],
                'secretAccessKey': hashlib.sha256(result['value'].encode()).hexdigest()}


def expect_conflict(action):
    try:
        action()
    except Conflict:
        return
    raise ReleaseError('R2 accepted a write that should have failed its precondition')


def probe(config):
    store = S3Store(config)
    key = 'bsnes-jg/_validation/provision-' + uuid.uuid4().hex + '.json'
    original, replacement = encoded({'probe': 1}), encoded({'probe': 2})
    created = False
    try:
        etag = store.put(key, original, absent=True)
        created = True
        require(store.get(key) == (original, etag), 'Probe read/hash mismatch')
        require(key in store.keys(key), 'Probe object listing failed')
        expect_conflict(lambda: store.put(key, replacement, absent=True))
        expect_conflict(lambda: store.put(key, replacement, etag='"00000000000000000000000000000000"'))
        require(store.get(key) == (original, etag), 'Rejected write changed probe contents')
        store.put(key, replacement, etag=etag)
        require(store.get(key)[0] == replacement, 'Conditional replacement failed')
    finally:
        if created:
            store.delete(key)
    require(store.get(key) is None, 'Probe deletion failed')


def store_parameter(config):
    with tempfile.TemporaryDirectory() as tmp:
        request = Path(tmp) / 'request.json'
        private_json(request, {'Name': SSM, 'Type': 'SecureString',
                               'Value': json.dumps(config), 'Overwrite': False})
        try:
            aws('ssm', 'put-parameter', '--cli-input-json', 'file://' + str(request))
        except ReleaseError:
            # Handles a lost success response or another process storing the same pair.
            value = parameter(SSM, optional=True)
            require(value is not None and json.loads(value) == config,
                    'SSM save failed or another credential exists; pending credentials retained, nothing overwritten')


def provision():
    account = parameter(ACCOUNT_PARAMETER).strip()
    require(re.fullmatch('[0-9a-f]{32}', account), 'Invalid Cloudflare account ID')
    existing = parameter(SSM, optional=True)
    if existing is not None:
        config = json.loads(existing)
        validate_config(config, account)
        probe(config)
        private_json(CACHE, config)
        if PENDING.exists():
            require(PENDING.stat().st_mode & 0o077 == 0, 'Pending credentials must be private')
            require(json.loads(PENDING.read_text()) == config,
                    'SSM verified, but a different pending token needs review; retained both')
            PENDING.unlink()
        print('Existing SSM credentials verified; refreshed private cache. No token created.')
        return
    if PENDING.exists():
        require(PENDING.stat().st_mode & 0o077 == 0, 'Pending credentials must be private')
        config = json.loads(PENDING.read_text())
        print('Resuming pending credentials; no new token requested.')
    else:
        source = os.environ.get('BSNES_R2_BOOTSTRAP_PARAMETER', '').strip()
        require(source.startswith('/'),
                'No bootstrap identity selected. Pass BOOTSTRAP_PARAMETER=/path/to/authorized/token; '
                'it must permit account-token administration. No known working source is configured. '
                'Existing project API/S3 credentials are not automatically administrative credentials.')
        print(f'Provisioning {TOKEN_NAME} for {BUCKET}; bootstrap source: {source}')
        client = Cloudflare(account, parameter(source))
        config = client.create(account)
        # Persist the one-time secret before any S3/SSM calls. Never persist the admin token.
        private_json(PENDING, config)
    validate_config(config, account)
    print('Checking list/read/write/delete and conditional writes with one disposable object.')
    probe(config)
    store_parameter(config)
    private_json(CACHE, config)
    PENDING.unlink()
    print('R2 publisher credentials provisioned and verified; saved to ' + SSM)


def main():
    CACHE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(CACHE.parent, 0o700)
    lock = CACHE.with_name('r2-provision.lock')
    with open(lock, 'a') as handle:
        os.chmod(lock, 0o600)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ReleaseError('Another local provisioning task is running') from None
        provision()


if __name__ == '__main__':
    try:
        main()
    except (ReleaseError, OSError, ValueError, KeyError, TypeError) as error:
        # Never print arbitrary provider/config content from exceptions.
        message = str(error) if isinstance(error, ReleaseError) else 'Local/configuration operation failed (details redacted)'
        raise SystemExit('R2 provisioning stopped: ' + message)
