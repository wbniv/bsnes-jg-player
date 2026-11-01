import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import r2_provision as p
from test_release import MemoryStore


class ProvisionTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(p.os.environ, {'BSNES_R2_BOOTSTRAP_PARAMETER': '/test/bootstrap'})
        environment.start()
        self.addCleanup(environment.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.account = 'a' * 32
        self.config = dict(accountId=self.account, bucket=p.BUCKET,
                           accessKeyId='b' * 32, secretAccessKey='c' * 64)
        for name, path in [('CACHE', self.root / 'cache.json'), ('PENDING', self.root / 'pending.json')]:
            context = patch.object(p, name, path)
            context.start()
            self.addCleanup(context.stop)

    def parameter(self, name, optional=False):
        return self.account if name == p.ACCOUNT_PARAMETER else None if name == p.SSM else 'admin-value'

    def test_api_token_has_only_bucket_policy_and_hashed_secret(self):
        client = p.Cloudflare(self.account, 'admin-value')
        def request(method, path, payload=None):
            if 'permission_groups' in path:
                return dict(result=[dict(name=p.PERMISSION, id='group')])
            if method == 'GET':
                return dict(result=[])
            self.assertEqual(payload, {'name': p.TOKEN_NAME, 'policies': [{
                'effect': 'allow', 'resources': {
                    f'com.cloudflare.edge.r2.bucket.{self.account}_default_{p.BUCKET}': '*'},
                'permission_groups': [{'id': 'group'}]}]})
            return dict(result={'id': 'b' * 32, 'value': 'one-time-token'})
        with patch.object(client, 'request', side_effect=request):
            result = client.create(self.account)
        self.assertEqual(result['secretAccessKey'], hashlib.sha256(b'one-time-token').hexdigest())
        self.assertNotIn('admin-value', json.dumps(result))

    def test_existing_token_on_later_page_prevents_duplicate(self):
        client = p.Cloudflare(self.account, 'admin-value')
        with patch.object(client, 'request', side_effect=[
            dict(result=[dict(name=p.PERMISSION, id='group')]),
            dict(result=[], result_info={'total_pages': 2}),
            dict(result=[dict(name=p.TOKEN_NAME)], result_info={'total_pages': 2})
        ]) as request:
            with self.assertRaises(p.ReleaseError):
                client.create(self.account)
        self.assertTrue(all(c.args[0] == 'GET' for c in request.call_args_list))

    def test_failed_probe_preserves_pending_and_does_not_save_ssm(self):
        with patch.object(p, 'parameter', side_effect=self.parameter), \
             patch.object(p.Cloudflare, 'create', return_value=self.config), \
             patch.object(p, 'probe', side_effect=p.ReleaseError('denied')), \
             patch.object(p, 'store_parameter') as save:
            with self.assertRaises(p.ReleaseError):
                p.provision()
        save.assert_not_called()
        self.assertEqual(json.loads(p.PENDING.read_text()), self.config)
        self.assertEqual(p.PENDING.stat().st_mode & 0o777, 0o600)
        self.assertFalse(p.CACHE.exists())

    def test_resume_uses_pending_without_minting(self):
        p.private_json(p.PENDING, self.config)
        with patch.object(p, 'parameter', side_effect=self.parameter), \
             patch.object(p.Cloudflare, 'create') as create, \
             patch.object(p, 'probe'), patch.object(p, 'store_parameter') as save:
            p.provision()
        create.assert_not_called()
        save.assert_called_once_with(self.config)
        self.assertFalse(p.PENDING.exists())
        self.assertEqual(json.loads(p.CACHE.read_text()), self.config)

    def test_existing_ssm_is_validated_without_bootstrap_or_overwrite(self):
        def existing(name, optional=False):
            self.assertIn(name, [p.ACCOUNT_PARAMETER, p.SSM])
            return self.account if name == p.ACCOUNT_PARAMETER else json.dumps(self.config)
        with patch.object(p, 'parameter', side_effect=existing), \
             patch.object(p, 'probe') as probe, patch.object(p, 'store_parameter') as save:
            p.provision()
        probe.assert_called_once_with(self.config)
        save.assert_not_called()

    def test_wrong_bucket_is_rejected_before_probe(self):
        config = dict(self.config, bucket='indri-apt')
        with patch.object(p, 'parameter', side_effect=[self.account, json.dumps(config)]), \
             patch.object(p, 'probe') as probe:
            with self.assertRaises(p.ReleaseError):
                p.provision()
        probe.assert_not_called()

    def test_missing_bootstrap_never_selects_another_project(self):
        with patch.dict(p.os.environ, {'BSNES_R2_BOOTSTRAP_PARAMETER': ''}), \
             patch.object(p, 'parameter', side_effect=self.parameter) as parameter, \
             patch.object(p.Cloudflare, 'create') as create:
            with self.assertRaisesRegex(p.ReleaseError, 'No bootstrap identity selected'):
                p.provision()
        create.assert_not_called()
        self.assertEqual([call.args[0] for call in parameter.call_args_list], [p.ACCOUNT_PARAMETER, p.SSM])

    def test_bootstrap_403_never_creates_or_stores_credentials(self):
        with patch.object(p, 'parameter', side_effect=self.parameter), \
             patch.object(p.Cloudflare, 'request', side_effect=p.ReleaseError('HTTP 403')) as request, \
             patch.object(p, 'store_parameter') as save:
            with self.assertRaises(p.ReleaseError):
                p.provision()
        self.assertEqual(request.call_args.args[0], 'GET')
        save.assert_not_called()
        self.assertFalse(p.PENDING.exists())
        self.assertFalse(p.CACHE.exists())

    def test_probe_exercises_conditions_and_cleans_up(self):
        store = MemoryStore()
        with patch.object(p, 'S3Store', return_value=store):
            p.probe(self.config)
        self.assertEqual(store.objects, {})

    def test_failed_initial_put_does_not_delete_an_object(self):
        store = MemoryStore()
        with patch.object(store, 'put', side_effect=p.ReleaseError('denied')), \
             patch.object(store, 'delete') as delete, patch.object(p, 'S3Store', return_value=store):
            with self.assertRaises(p.ReleaseError):
                p.probe(self.config)
        delete.assert_not_called()

    def test_failed_ssm_save_retains_pending(self):
        p.private_json(p.PENDING, self.config)
        with patch.object(p, 'parameter', side_effect=self.parameter), \
             patch.object(p, 'probe'), patch.object(p, 'store_parameter', side_effect=p.ReleaseError('SSM denied')):
            with self.assertRaises(p.ReleaseError):
                p.provision()
        self.assertTrue(p.PENDING.exists())
        self.assertFalse(p.CACHE.exists())

    def test_ssm_request_never_overwrites_or_puts_secret_in_arguments(self):
        def aws(*args, **kwargs):
            self.assertEqual(args[:3], ('ssm', 'put-parameter', '--cli-input-json'))
            path = Path(args[3].removeprefix('file://'))
            payload = json.loads(path.read_text())
            self.assertFalse(payload['Overwrite'])
            self.assertEqual(payload['Type'], 'SecureString')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(self.config['secretAccessKey'], str(args))
            return {}
        with patch.object(p, 'aws', side_effect=aws):
            p.store_parameter(self.config)
