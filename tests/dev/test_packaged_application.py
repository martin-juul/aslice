"""Launch an extracted application without importing code from the checkout."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.dev.package import package


@unittest.skipUnless(importlib.util.find_spec('aiohttp') and (ROOT / 'build/simulator-web/app.js').is_file(),
                     'compiled assets and controller dependency required')
class PackagedApplicationTests(unittest.TestCase):
    def test_extract_launch_reconnect_status_and_shutdown(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            output = package(ROOT, directory / 'application.zip')
            with zipfile.ZipFile(output) as archive:
                archive.extractall(directory / 'extracted')
            app = directory / 'extracted/aslice-simulator'
            for line in (app / 'SHA256SUMS').read_text().splitlines():
                digest, name = line.split('  ', 1)
                self.assertEqual(hashlib.sha256((app / name).read_bytes()).hexdigest(), digest)
            state = directory / 'machines'
            environment = {**os.environ, 'ASLICE_SIMULATOR_HOME': str(state)}
            environment.pop('PYTHONPATH', None)

            def run(*args):
                result = subprocess.run([sys.executable, str(app / 'simulator.py'), *args], cwd=directory,
                                        env=environment, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout

            try:
                run('open', '--no-browser')
                endpoint = json.loads((state / '.controller/endpoint.json').read_text())
                run('open', '--no-browser')
                self.assertEqual(json.loads((state / '.controller/endpoint.json').read_text()), endpoint)
                self.assertEqual(json.loads(run('status'))['machines'], [])
                with urlopen(f'http://127.0.0.1:{endpoint["port"]}/', timeout=5) as response:
                    self.assertIn(b'console-panel', response.read())
                run('shutdown')
                self.assertFalse((state / '.controller/endpoint.json').exists())
            finally:
                if (state / '.controller/endpoint.json').exists():
                    run('shutdown')
                time.sleep(0.3)


if __name__ == '__main__':
    unittest.main()
