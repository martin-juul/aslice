"""Validate real manifest identities and inventories without repository authorization."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == '__main__' else None
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(BINARY is None, 'run through CTest')
class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.manifest = self.directory / 'manifest.json'
        self.payload = self.directory / 'payload'
        self.payload.mkdir()
        (self.payload / 'bin').mkdir()
        self.binary = self.payload / 'bin/example'
        self.binary.write_bytes(b'x')
        self.binary.chmod(0o755)
        self.data = json.loads((ROOT / 'tests/fixtures/artifact-manifest.json').read_text())
        self.data['files'][0]['sha256'] = hashlib.sha256(b'x').hexdigest()

    def call(self, payload=False, code=0, raw=None):
        self.manifest.write_text(raw if raw is not None else json.dumps(self.data), encoding='utf-8')
        arguments = [str(BINARY), 'artifact', 'verify' if payload else 'inspect', str(self.manifest)]
        if payload:
            arguments += ['--payload', str(self.payload)]
        result = subprocess.run(arguments, capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, code, result.stderr)
        if code:
            self.assertEqual(result.stdout, '')
            self.assertTrue(result.stderr)
            return
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_identity_and_payload(self):
        result = self.call(payload=True)
        canonical = json.dumps(self.data, separators=(',', ':'), sort_keys=True, ensure_ascii=False).encode()
        self.assertEqual(result['artifact_id'], 'sha256:' + hashlib.sha256(canonical).hexdigest())
        self.assertEqual(result['manifest_size'], len(canonical))
        self.assertEqual(result['payload_bytes'], 1)
        self.assertFalse(result['authenticated'])
        self.assertTrue(result['payload_verified'])
        self.assertEqual(result['posix_modes_verified'], os.name != 'nt')
        self.assertEqual(result['artifact_id'], self.call(raw=json.dumps(self.data, indent=4))['artifact_id'])

    def test_utf16_canonical_key_order(self):
        # UTF-8 ordering would put U+E000 before the supplementary character.
        self.data['user_flags'] = {'\ue000': 'last', '\U0001f600': 'first', 'a': '\n"\\'}
        def ordered(value):
            if isinstance(value, dict):
                return {key: ordered(value[key]) for key in sorted(value, key=lambda s: s.encode('utf-16-be'))}
            if isinstance(value, list):
                return [ordered(item) for item in value]
            return value
        canonical = json.dumps(ordered(self.data), ensure_ascii=False, separators=(',', ':')).encode()
        self.assertEqual(self.call()['artifact_id'], 'sha256:' + hashlib.sha256(canonical).hexdigest())

    def test_shape_and_semantic_refusals(self):
        baseline = deepcopy(self.data)
        mutations = [lambda d: d.update(extra=True), lambda d: d.pop('epoch'),
                     lambda d: d.update(epoch=-1), lambda d: d.update(epoch=9007199254740992),
                     lambda d: d.update(revision=1.5), lambda d: d.update(manifest_version=2),
                     lambda d: d.update(min_os='12', max_os='11'),
                     lambda d: d.update(cpu_features=['sse2', 'sse2']),
                     lambda d: d['files'][0].update(path='../escape'),
                     lambda d: d['files'][0].update(path='/absolute'),
                     lambda d: d['files'][0].update(path='bin//example'),
                     lambda d: d['files'][0].update(mode='4755'),
                     lambda d: d['files'][0].update(target='extra'),
                     lambda d: d['files'].append(deepcopy(d['files'][0])),
                     lambda d: d['files'].append(dict(path='Bin/other', kind='directory', mode='0755')),
                     lambda d: d['files'].append(dict(path='bin/example/child', kind='directory', mode='0755')),
                     lambda d: d['dependencies'].append(dict(repository='core', name='example', artifact_id='sha256:'+'a'*64)),
                     lambda d: d['abi'].update(extra=[])]
        for mutate in mutations:
            self.data = deepcopy(baseline)
            mutate(self.data)
            self.call(code=2)
        self.call(code=2, raw='{"manifest_version":1,"manifest_version":1}')
        self.call(code=2, raw='[' * 100 + '0' + ']' * 100)

    def test_corruption_and_unlisted_files(self):
        self.binary.write_bytes(b'y')
        self.call(payload=True, code=2)
        self.binary.write_bytes(b'xx')
        self.call(payload=True, code=2)
        self.binary.write_bytes(b'x')
        extra = self.payload / 'unlisted'
        extra.write_text('extra')
        self.call(payload=True, code=2)
        extra.unlink()
        if os.name != 'nt':
            self.binary.chmod(0o644)
            self.call(payload=True, code=2)
            self.binary.chmod(0o755)
        self.binary.unlink()
        self.call(payload=True, code=2)

    def test_relocation_bounds_binding_and_bytes(self):
        relocation = dict(path='bin/example', offset=0, width=1, expected_hex='78', replacement='self')
        self.data['relocations'] = [relocation]
        self.call(payload=True)
        relocation['expected_hex'] = '79'
        self.call(payload=True, code=2)
        relocation['expected_hex'] = '78'
        relocation['replacement'] = 'dependency:core:absent'
        self.call(code=2)
        relocation['replacement'] = 'self'
        relocation['offset'] = 1
        self.call(code=2)
        relocation['offset'] = 0
        self.data['relocations'].append(deepcopy(relocation))
        self.call(code=2)

    def test_symlink_inventory(self):
        link = dict(path='bin/alias', kind='symlink', mode='0777', target='example')
        self.data['files'].append(link)
        self.call()
        for target in ('../../escape', '/tmp/example', 'missing', 'alias'):
            link['target'] = target
            self.call(code=2)
        link['target'] = 'example'
        if os.name != 'nt':
            (self.payload / 'bin/alias').symlink_to('example')
            self.call(payload=True)
            (self.payload / 'bin/alias').unlink()
            (self.payload / 'bin/alias').symlink_to('missing')
            self.call(payload=True, code=2)


if __name__ == '__main__':
    unittest.main()
