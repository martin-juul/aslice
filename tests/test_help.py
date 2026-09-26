"""Exercise every command exposed by the registry through rendered help."""
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile
import unittest

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == '__main__' else None


@unittest.skipIf(BINARY is None, 'run through CTest')
class HelpTests(unittest.TestCase):
    def invoke(self, *arguments):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([str(BINARY), *arguments], cwd=directory,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(list(Path(directory).iterdir()), [])
            return result

    def commands(self):
        paths = []
        for group in ('db', 'version', 'artifact', 'slice', 'dev fixture'):
            result = self.invoke(*group.split())
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            for line in result.stdout.splitlines():
                match = re.match(r'^  (\w+)  ', line)
                if match:
                    paths.append((*group.split(), match[1]))
        self.assertEqual(len(paths), 23)
        return paths

    def test_root_and_nested_help(self):
        root = self.invoke()
        self.assertEqual(root.returncode, 0)
        for args in (('help',), ('--help',)):
            self.assertEqual(self.invoke(*args).stdout, root.stdout)
        for path in self.commands():
            direct = self.invoke(*path, '--help')
            nested = self.invoke('help', *path)
            self.assertEqual(direct.returncode, 0, direct.stderr)
            self.assertEqual(direct.stderr, '')
            self.assertEqual(direct.stdout, nested.stdout)
            self.assertIn('Example:', direct.stdout)
            self.assertIn('Platform:', direct.stdout)
            self.assertIn('Usage: aslice ' + ' '.join(path), direct.stdout)
            if '--prefix' in direct.stdout:
                self.assertEqual(self.invoke(*path, '--prefix', 'untouched', '--help').stdout,
                                 direct.stdout)

    def test_options_are_recognized_and_unknown_options_refused(self):
        for path in self.commands():
            page = self.invoke(*path, '--help').stdout
            for option, value in re.findall(r'^  (--[a-z-]+)(?: ([A-Z]+))?  ', page, re.M):
                if option == '--help':
                    continue
                result = self.invoke(*path, option, *(['missing-parent/fixture'] if value else []))
                self.assertNotIn('unknown option', result.stderr, (path, option))
                self.assertNotIn('duplicate option', result.stderr, (path, option))
                if value:
                    missing = self.invoke(*path, option)
                    self.assertEqual(missing.returncode, 2)
                    self.assertIn('requires', missing.stderr)
            unknown = self.invoke(*path, '--not-an-option')
            self.assertEqual(unknown.returncode, 2)
            self.assertEqual(unknown.stdout, '')
            self.assertIn('unknown option', unknown.stderr)
            self.assertIn(' '.join(path) + ' --help', unknown.stderr)
            self.assertEqual(self.invoke(*path, '--not-an-option', '--help').returncode, 2)

    def test_required_arguments_and_platform(self):
        for path in (('version', 'compare'), ('artifact', 'inspect'), ('slice', 'pack')):
            result = self.invoke(*path)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, '')
            self.assertIn('--help', result.stderr)
        fixture = self.invoke('dev', 'fixture')
        self.assertEqual('[unavailable on Windows]' in fixture.stdout, os.name == 'nt')
        old = self.invoke('prototype', '--help')
        self.assertEqual(old.returncode, 2)
        self.assertEqual(old.stdout, '')


if __name__ == '__main__':
    unittest.main()
