"""Race the name after the actual C++ adapter opens its input descriptor."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == '__main__' else None


@unittest.skipUnless(BINARY, 'run through CTest')
class ReadTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.file = self.root / 'input'
        self.file.write_text('original', encoding='ascii')
        self.file.chmod(0o640)

    def test_opened_descriptor_keeps_original_file(self):
        process = subprocess.Popen([str(BINARY), str(self.file), '100'], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def stop():
            if process.poll() is None:
                process.kill()
            process.communicate()
        self.addCleanup(stop)
        metadata = json.loads(process.stdout.readline())
        self.assertEqual(metadata['links'], 1)
        if os.name == 'nt':
            with self.assertRaises(OSError):
                self.file.write_text('attacker')
            with self.assertRaises(OSError):
                self.file.rename(self.root / 'old')
        else:
            self.assertEqual(metadata['mode'], 0o640)
            self.file.rename(self.root / 'old')
            self.file.write_text('attacker')
        stdout, stderr = process.communicate('\n', timeout=10)
        self.assertEqual((process.returncode, stderr), (0, ''))
        self.assertEqual(json.loads(stdout), {'bytes': 'original'})

    def test_opened_metadata_and_size_limit(self):
        os.link(self.file, self.root / 'alias')
        result = subprocess.run([str(BINARY), str(self.file), '100'], input='\n',
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.splitlines()[0])['links'], 2)
        result = subprocess.run([str(BINARY), str(self.file), '3'], input=b'\n',
                                capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'')

    @unittest.skipIf(os.name == 'nt', 'POSIX links and FIFOs')
    def test_no_symlink_parent_leaf_or_fifo(self):
        (self.root / 'parent').symlink_to(self.root, target_is_directory=True)
        (self.root / 'link').symlink_to(self.file)
        os.mkfifo(self.root / 'fifo')
        for path in (self.root / 'parent/input', self.root / 'link', self.root / 'fifo'):
            result = subprocess.run([str(BINARY), str(path), '100'], input='\n',
                                    capture_output=True, text=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
