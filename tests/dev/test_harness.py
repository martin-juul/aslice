"""Developer recipes must preserve state and expose failures to callers."""

import contextlib
import io
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.dev import cli
from tools.dev.audit import audit_build
from tools.dev.preview import make_server
from tools.dev.process import Runner, state_root
from tools.dev.package import package


class HarnessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_dry_run_never_creates_reports_or_starts_processes(self):
        runner = Runner(True, self.root)
        with patch('subprocess.Popen') as start, contextlib.redirect_stdout(io.StringIO()):
            runner.run(['missing-program', 'argument with spaces'])
        start.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_failure_retains_output_and_exit_status(self):
        runner = Runner(root=self.root)
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(subprocess.CalledProcessError) as error:
                runner.run([sys.executable, '-c', 'print("diagnostic"); raise SystemExit(7)'])
        self.assertEqual(error.exception.returncode, 7)
        self.assertIn('diagnostic', (runner.report / '01.log').read_text())

    def test_private_output_not_retained(self):
        runner = Runner(root=self.root)
        with contextlib.redirect_stdout(io.StringIO()):
            runner.run([sys.executable, '-c', 'print("private-url")'], retain=False)
        self.assertFalse(runner.report.exists())

    def test_cli_propagates_failure(self):
        with patch.object(cli.Runner, 'run', side_effect=subprocess.CalledProcessError(7, ['test'])), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['test', 'developer']), 7)

    def test_suite_filter_and_missing_build_error(self):
        runner = Runner(True, self.root)
        with patch.object(runner, 'run') as run:
            cli.tests(runner, self.root, 'modeled')
        arguments = run.call_args.args[0]
        self.assertEqual(arguments[-2:], ['-L', 'modeled'])
        self.assertIn('--no-tests=error', arguments)
        with self.assertRaisesRegex(ValueError, 'build first'):
            cli.tests(Runner(root=self.root), self.root, 'core')

    def test_machine_handle_and_root_forwarded_without_retention(self):
        args = cli.parser().parse_args(['simulator', 'machine', '--root', str(self.root), '--', 'stop', 'example'])
        runner = Runner(True, self.root)
        with patch.object(runner, 'run') as run:
            cli.simulator(runner, self.root, args)
        self.assertEqual(run.call_args.args[0][-4:], ['--root', self.root, 'stop', 'example'])
        self.assertFalse(run.call_args.kwargs['retain'])

    def test_container_recipe_uses_current_readonly_source_offline(self):
        args = cli.parser().parse_args(['docker', 'check', '--reuse-image', '--sanitizers', '--image', 'prepared'])
        runner = Runner(True, self.root)
        with patch.object(runner, 'run') as run:
            cli.docker_check(runner, args)
        arguments = run.call_args.args[0]
        self.assertIn('none', arguments)
        self.assertIn(f'type=bind,source={self.root.as_posix()},target=/src,readonly', arguments)
        self.assertEqual(arguments[-3:], ['prepared', '/src/tools/dev/docker-check.sh', 'ON'])

    def test_state_override_is_outside_build(self):
        with patch.dict(os.environ, {'ASLICE_SIMULATOR_HOME': str(self.root)}):
            self.assertEqual(state_root(), self.root)

    def test_audit_preserves_files_and_skips_dependencies(self):
        files = {'repro.cpp': b'int main() {}', 'machine.qcow2': b'keep', 'evidence.json': b'{}', 'node_modules/example.js': b'generated'}
        for name, data in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        result = audit_build(self.root)
        self.assertEqual([item['path'] for item in result['candidates']], ['repro.cpp'])
        self.assertEqual(result['protected'][0]['path'], 'machine.qcow2')
        self.assertEqual(result['skipped_directories'], ['node_modules'])
        self.assertTrue(all((self.root / name).read_bytes() == data for name, data in files.items()))

    def test_preview_static_routes_traversal_and_port_conflict(self):
        assets = self.root / 'assets'
        assets.mkdir()
        (assets / 'index.html').write_text('demo')
        (assets / 'app.js').write_text('script')
        (self.root / 'private.txt').write_text('private')
        with make_server(assets, 0) as server:
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}'
                with urlopen(url + '/') as response:
                    self.assertEqual(response.read(), b'demo')
                with urlopen(url + '/static/app.js') as response:
                    self.assertEqual(response.read(), b'script')
                with self.assertRaises(HTTPError) as error:
                    urlopen(url + '/%2e%2e/private.txt')
                self.assertEqual(error.exception.code, 404)
                error.exception.close()
                with self.assertRaises(OSError):
                    make_server(assets, server.server_port)
            finally:
                server.shutdown()
                thread.join(timeout=5)
            self.assertFalse(thread.is_alive())

    def test_package_is_self_contained_and_excludes_workspaces(self):
        for name in ('index.html', 'app.js', 'app.css'):
            path = self.root / 'build/simulator-web' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('asset')
        (self.root / 'LICENSE').write_text('license')
        private = self.root / 'tools/simulator/web/node_modules/private.txt'
        private.parent.mkdir(parents=True)
        private.write_text('must not ship')
        output = package(self.root, self.root / 'application.zip')
        with zipfile.ZipFile(output) as archive:
            names = archive.namelist()
            self.assertIn('aslice-simulator/Simulator.cmd', names)
            self.assertIn('aslice-simulator/build/simulator-web/app.js', names)
            self.assertFalse(any('node_modules' in name for name in names))
            self.assertIn(b'app.js', archive.read('aslice-simulator/SHA256SUMS'))
        with self.assertRaises(FileExistsError):
            package(self.root, output)

    @unittest.skipUnless(importlib.util.find_spec('aiohttp'), 'controller dependency unavailable')
    def test_application_start_reconnect_and_explicit_shutdown(self):
        from tools.simulator import controller
        from tools.simulator.application import shutdown
        root = self.root / 'persistent'
        try:
            controller.ensure(root)
            first = json.loads((root / '.controller/endpoint.json').read_text())
            controller.ensure(root)
            self.assertEqual(json.loads((root / '.controller/endpoint.json').read_text()), first)
            self.assertEqual(controller.request(root, 'ping')['version'], 1)
            self.assertEqual(shutdown(root)['machines'], 'preserved')
            self.assertFalse((root / '.controller/endpoint.json').exists())
        finally:
            if (root / '.controller/endpoint.json').exists():
                shutdown(root)
        # The lease releases just after endpoint removal.
        time.sleep(0.2)

    def test_application_failure_reaps_only_its_startup_child(self):
        from tools.simulator import controller
        with patch.object(controller, 'request', side_effect=OSError('unavailable')), \
             patch.object(controller.vm, 'detached') as detached, \
             patch.object(controller.time, 'monotonic', side_effect=[0, 16]):
            detached.return_value.poll.return_value = None
            with self.assertRaisesRegex(ValueError, 'failed to start'):
                controller.ensure(self.root / 'failed')
            detached.return_value.terminate.assert_called_once()
            detached.return_value.wait.assert_called_once_with(timeout=5)

    def test_shutdown_machine_failure_preserves_controller(self):
        from tools.simulator import controller
        from tools.simulator.application import shutdown
        endpoint = self.root / '.controller/endpoint.json'
        endpoint.parent.mkdir()
        endpoint.write_text('{}')
        with patch.object(controller, 'request', side_effect=[{'machines': [{'name': 'example', 'state': 'running'}]}, ValueError('busy')]) as request:
            with self.assertRaisesRegex(ValueError, 'busy'):
                shutdown(self.root, True)
        self.assertEqual([call.args[1] for call in request.call_args_list], ['status', 'stop'])


if __name__ == '__main__':
    unittest.main()
