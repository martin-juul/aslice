"""Require POSIX mutations to refuse symlinked parents without changing files."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == '__main__' else None


@unittest.skipUnless(BINARY, 'run through CTest on POSIX')
class DirectoryTests(unittest.TestCase):
    def test_directory_descriptor_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            result = subprocess.run([str(BINARY), str(root)], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(list(root.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
