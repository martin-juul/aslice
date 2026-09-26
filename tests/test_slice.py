"""Real compressed container acceptance, with adversarial tar/zstd fixtures."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == '__main__' else None
CODEC = Path(sys.argv.pop(1)).resolve() if __name__ == '__main__' else None
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(BINARY is None, 'run through CTest')
class SliceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.payload = self.directory / 'payload'
        (self.payload / 'bin').mkdir(parents=True)
        binary = self.payload / 'bin/example'
        binary.write_bytes(b'x')
        binary.chmod(0o755)
        self.manifest = self.directory / 'manifest.json'
        data = json.loads((ROOT / 'tests/fixtures/artifact-manifest.json').read_text())
        data['files'][0]['sha256'] = hashlib.sha256(b'x').hexdigest()
        self.manifest.write_text(json.dumps(data))
        self.archive = self.directory / 'test.slice'
        self.packed = self.call('slice', 'pack', self.manifest, self.payload, self.archive)
        self.blob = self.archive.read_bytes()
        self.tar = self.codec('decompress', self.blob)

    def codec(self, operation, data):
        return subprocess.run([str(CODEC), operation], input=data, capture_output=True, check=True, timeout=30).stdout

    def call(self, *args, code=0):
        result = subprocess.run([str(BINARY), *map(str, args)], capture_output=True,
                                text=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, code, result.stderr)
        if code:
            self.assertEqual(result.stdout, '')
            self.assertTrue(result.stderr)
            return
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def reject(self, tar=None, blob=None):
        self.archive.write_bytes(blob if blob is not None else self.codec('compress', tar))
        self.call('slice', 'inspect', self.archive, code=2)

    @staticmethod
    def headers(tar):
        offsets = []
        pos = 0
        while tar[pos:pos + 512] != bytes(512):
            offsets.append(pos)
            size = int(tar[pos + 124:pos + 136].rstrip(b'\0 '), 8)
            pos += 512 + (size + 511) // 512 * 512
        return offsets

    def changed_header(self, offset, start, value):
        tar = bytearray(self.tar)
        tar[offset + start:offset + start + len(value)] = value
        tar[offset + 148:offset + 156] = b' ' * 8
        checksum = sum(tar[offset:offset + 512])
        tar[offset + 148:offset + 156] = f'{checksum:06o}\0 '.encode()
        return bytes(tar)

    def test_round_trip_reproducibility_and_no_overwrite(self):
        inspected = self.call('slice', 'inspect', self.archive)
        for key in ('artifact_id', 'blob_digest', 'blob_size'):
            self.assertEqual(inspected[key], self.packed[key])
        self.assertTrue(inspected['container_verified'])
        self.assertFalse(inspected['authenticated'])
        again = self.directory / 'again.slice'
        self.call('slice', 'pack', self.manifest, self.payload, again)
        self.assertEqual(self.blob, again.read_bytes())
        self.call('slice', 'pack', self.manifest, self.payload, self.archive, code=2)
        self.assertEqual(self.blob, self.archive.read_bytes())

    def test_frame_refusals(self):
        for blob in (self.blob + self.blob, self.blob + b'\0', self.blob[:-1], b'not zstd', bytes(16)):
            self.reject(blob=blob)
        self.reject(blob=self.codec('compress', bytes(64 * 1024 * 1024 + 1)))

    def test_tar_header_refusals(self):
        payload = self.headers(self.tar)[-1]
        for start, value in ((0, b'../escape\0'), (156, b'1'), (156, b'x'), (156, b'g'),
                             (108, b'0000001\0'), (136, b'00000000001\0'),
                             (100, b'0004755\0'), (265, b'root\0'), (345, b'prefix\0')):
            self.reject(tar=self.changed_header(payload, start, value))
        tar = bytearray(self.tar)
        tar[payload] ^= 1
        self.reject(tar=bytes(tar))

    def test_payload_metadata_and_archive_ending(self):
        offsets = self.headers(self.tar)
        payload = offsets[-1]
        tar = bytearray(self.tar)
        tar[payload + 512] = ord('y')
        self.reject(tar=bytes(tar))
        tar = bytearray(self.tar)
        tar[512] = ord(' ')  # descriptor cannot omit/open with a different encoding
        self.reject(tar=bytes(tar))
        tar = bytearray(self.tar)
        tar[offsets[1] + 512] = ord(' ')
        self.reject(tar=bytes(tar))
        self.reject(tar=self.tar[:-512])
        self.reject(tar=self.tar + b'x')
        self.reject(tar=self.tar[:payload] + self.tar[-1024:])
        self.reject(tar=self.tar[:-1024] + self.tar[payload:payload + 1024] + bytes(1024))
        # Nonzero padding after the regular file is not payload data.
        tar = bytearray(self.tar)
        tar[payload + 513] = 1
        self.reject(tar=bytes(tar))


if __name__ == '__main__':
    unittest.main()
