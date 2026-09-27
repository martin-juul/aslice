"""Portable version and resolver behavior through the native executable."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == '__main__' else None


@unittest.skipIf(BINARY is None, 'run through CTest')
class PackageTests(unittest.TestCase):
    def call(self, *args, code=0):
        result = subprocess.run([str(BINARY), *args], capture_output=True,
                                text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, code, result.stderr)
        if code:
            self.assertEqual(result.stdout, '')
            return result.stderr
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_normalization(self):
        examples = {'v7.1': '7.1.0', '1.3': '1.3.0', '2.0.0-rc.2': '2.0.0-rc.2',
                    '1.1.1k': '1.1.1.11', '2024.09.1': '2024.9.1', '2!1.0': '2!1.0.0'}
        for raw, normalized in examples.items():
            self.assertEqual(self.call('version', 'normalize', raw)['version'], normalized)
        for raw in ('r4520', 'abc123', '1.2.3+build', '1.2.3-01', '1..2', '', '1.2.3.4k'):
            self.call('version', 'normalize', raw, code=2)

    def test_order(self):
        ordered = ['1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-alpha.beta', '1.0.0-beta',
                   '1.0.0-beta.2', '1.0.0-beta.11', '1.0.0-rc.1', '1.0.0', '1.0.0.1',
                   '2.0.0', '1!0.0.0']
        for a, b in zip(ordered, ordered[1:]):
            self.assertEqual(self.call('version', 'compare', a, b)['order'], -1)
            self.assertEqual(self.call('version', 'compare', b, a)['order'], 1)
        self.assertEqual(self.call('version', 'compare', '1.0.0', '1.0.0.0')['order'], 0)
        for bad in ('1.2', '01.2.3', '1.2.3-', '1.2.3+foo', '18446744073709551616.0.0'):
            self.call('version', 'compare', bad, '1.2.3', code=2)

    def test_ranges(self):
        examples = [('0.164.5', '^0.164', True), ('0.165.0', '^0.164', False),
                    ('0.0.4', '^0.0.3', False), ('3.0.14', '~3.0.8', True),
                    ('3.1.0', '~3.0.8', False), ('1.6.43', '>=1.6, <1.7', True),
                    ('1.7.0', '>=1.6, <1.7', False), ('3.2.1', '^2.0 || ^3.2', True),
                    ('3.1.1', '^2.0 || ^3.2', False), ('1.3.1', '=1.3.1', True),
                    ('1.3.2', '=1.3.1', False), ('1.3.1', '>1.3.1', False),
                    ('1.3.1', '<=1.3.1', True), ('2.0.0-rc.1', '*', False),
                    ('2.0.0-rc.2', '>=2.0.0-rc.1, <2.0.0', True),
                    ('2.1.0-rc.1', '>=2.0.0-rc.1', False), ('1!1.0.0', '>=1!0.9', True)]
        for value, constraint, expected in examples:
            with self.subTest(value=value, constraint=constraint):
                self.assertEqual(self.call('version', 'matches', value, constraint)['matches'], expected)
        for bad in ('', '|| *', '* ||', '>=1.0,', '!=1.0', '1.0', '=v1.0', '=01.0', '^18446744073709551615.0.0'):
            self.call('version', 'matches', '1.0.0', bad, code=2)

    def test_resolver_backtracking_and_prereleases(self):
        def pkg(name, version, deps=None):
            return dict(name=name, version=version, dependencies=deps or {}, files={}, min_os='10.11', flavor='v1')
        packages = [pkg('app', '1.0.0', {'dep': '^1.0'}),
                    pkg('app', '2.0.0', {'dep': '^2.0'}),
                    pkg('dep', '1.5.0'), pkg('dep', '3.0.0'), pkg('app', '3.0.0-rc.1')]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'catalog.json'
            path.write_text(json.dumps(dict(format='aslice-prototype-1', packages=packages)))
            result = self.call('dev', 'fixture', 'resolve', '--catalog', str(path), 'app')
            self.assertEqual([(p['name'], p['version']) for p in result['packages']],
                             [('core:app', '1.0.0'), ('core:dep', '1.5.0')])
            result = self.call('dev', 'fixture', 'resolve', '--catalog', str(path), '--prerelease', 'app')
            self.assertEqual(result['packages'][0]['version'], '3.0.0-rc.1')
            packages.append(pkg('consumer', '1.0.0', {'app': '=3.0.0-rc.1'}))
            path.write_text(json.dumps(dict(format='aslice-prototype-1', packages=packages)))
            self.call('dev', 'fixture', 'resolve', '--catalog', str(path), 'consumer')
            self.call('dev', 'fixture', 'resolve', '--catalog', str(path), 'missing', code=2)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_variant_requirements_revision_order_and_collision_backtracking(self):
        def pkg(name, version='1.0.0', **extra):
            return dict(name=name, version=version, dependencies={}, files={},
                        min_os='10.11', flavor='v1', **extra)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'catalog.json'

            def solve(packages, *roots, code=0):
                path.write_text(json.dumps(dict(format='aslice-prototype-1', packages=packages)))
                return self.call('dev', 'fixture', 'resolve', '--catalog', str(path), *roots, code=code)

            consumer = pkg('consumer')
            consumer['dependencies'] = {'dep': '^1.0 +metal'}
            providers = [pkg('dep', revision=9, variants={'metal': False}),
                         pkg('dep', revision=2, variants={'metal': True}),
                         pkg('dep', revision=1, variants={'metal': True})]
            for catalog in (providers, list(reversed(providers))):
                result = solve([consumer, *catalog], 'consumer')['packages']
                self.assertEqual(result[1]['revision'], 2)
                self.assertEqual(result[1]['variants'], {'metal': True})
            solve([consumer, providers[0]], 'consumer', code=2)
            solve([consumer, pkg('dep')], 'consumer', code=2)

            other = pkg('other')
            other['dependencies'] = {'dep': '+debug ^1.0'}
            combined = pkg('dep', variants={'metal': True, 'debug': True})
            solve([consumer, other, *providers], 'consumer', 'other', code=2)
            result = solve([consumer, other, *providers, combined], 'consumer', 'other')['packages']
            self.assertEqual(result[1]['variants'], combined['variants'])

            # Upstream version (including epoch) precedes recipe revision.
            ranked = [pkg('dep', '1.0.0', revision=99), pkg('dep', '2.0.0', revision=0)]
            self.assertEqual(solve(ranked, 'dep')['packages'][0]['version'], '2.0.0')
            ranked.append(pkg('dep', '1!0.1.0'))
            self.assertEqual(solve(ranked, 'dep')['packages'][0]['version'], '1!0.1.0')

            # A colliding preferred build must not hide an eligible alternative.
            app = pkg('app')
            app['dependencies'] = {'dep': '* +metal'}
            app['files'] = {'bin/shared': {'text': 'app', 'executable': False}}
            newest = pkg('dep', revision=2, variants={'metal': True})
            newest['files'] = {'bin/SHARED': {'text': 'dep', 'executable': False}}
            older = pkg('dep', revision=1, variants={'metal': True})
            self.assertEqual(solve([app, newest, older], 'app')['packages'][1]['revision'], 1)
            solve([app, newest], 'app', code=2)

    def test_variant_and_revision_input_refusals(self):
        base = dict(name='app', version='1.0.0', min_os='10.11', flavor='v1',
                    dependencies={}, files={})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'catalog.json'
            malformed = [dict(base, revision=value) for value in (-1, 1.5, True, '1', 2**64)]
            malformed += [dict(base, variants=value) for value in ([], {'metal': 1}, {'': True}, {'bad.name': True})]
            malformed += [dict(base, dependencies={'dep': value}) for value in
                          ('+', '+metal +metal', '+bad.name', '^1.0+metal', '?variant.metal', '')]
            for package in malformed:
                with self.subTest(package=package):
                    path.write_text(json.dumps(dict(format='aslice-prototype-1', packages=[package])))
                    self.call('dev', 'fixture', 'resolve', '--catalog', str(path), 'app', code=2)


if __name__ == '__main__':
    unittest.main()
