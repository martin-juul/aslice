"""Exercise the shared C++ wait controller against simulated OS locks and time."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.simulator.harness import Workspace
from tools.simulator.model import Model
from tools.simulator.server import Server

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == '__main__' and len(sys.argv) > 1 else None


@unittest.skipUnless(BINARY, 'run through CTest')
class LockWaitTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        context = Workspace(Path(temporary.name) / 'workspace')
        self.workspace = context.__enter__()
        self.addCleanup(context.__exit__)
        self.model = Model(self.workspace)
        self.server = Server(self.model)
        self.addCleanup(self.server.close)
        self.server.issue('holder', [])
        self.holder = subprocess.Popen([sys.executable, '-c', 'import sys; sys.stdin.read()'], stdin=subprocess.PIPE)
        self.addCleanup(self.holder.stdin.close)
        self.server.attach_process('holder', self.holder)
        self.model.filesystem('holder', 'create', {'path': '/work/.lock', 'mode': 0o600})
        self.model.filesystem('holder', 'lock', {'path': '/work/.lock'})

    def run_script(self, timeout='65ms', authorized=True, actions=None):
        script = self.workspace / 'inputs/script.json'
        script.write_text(json.dumps({'timeout': timeout, 'authorized': authorized,
            'actions': actions or [{'operation': 'lock', 'root': '/work'}]}))
        session = self.workspace / 'sessions/waiter.json'
        session.write_text(json.dumps(self.server.issue('waiter', ['clock', 'filesystem'])))
        waiter = subprocess.Popen([str(BINARY), '--session', str(session), '--script', str(script)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.server.attach_process('waiter', waiter)
        stdout, stderr = waiter.communicate(timeout=20)
        self.assertEqual((waiter.returncode, stderr), (0, b''))
        return [json.loads(line) for line in stdout.splitlines()]

    def waits(self):
        return [item['request']['arguments']['milliseconds'] for item in self.server.transcript
                if item['request']['capability'] == 'clock' and item['request']['operation'] == 'wait']

    def test_timeout_clips_backoff_and_exhaustion_does_not_reset(self):
        output = self.run_script(actions=[{'operation': 'lock', 'root': '/work'}] * 2)
        self.assertEqual(output, [{'outcome': 'busy', 'elapsed_ms': 65, 'remaining_ms': 0}] * 2)
        self.assertEqual(self.waits(), [10, 20, 35])
        self.assertEqual(self.model.state['monotonic_ms'], 65)
        self.assertEqual(set(self.model.locks.values()), {'holder'})

    def test_configured_timeout_without_permission_never_waits(self):
        output = self.run_script(timeout='30s', authorized=False)
        self.assertEqual(output, [{'outcome': 'busy', 'elapsed_ms': 0, 'remaining_ms': 30000}])
        self.assertEqual(self.waits(), [])

    def test_zero_timeout_attempts_once(self):
        self.assertEqual(self.run_script(timeout='0s')[0]['outcome'], 'busy')
        self.assertEqual(len(self.server.transcript), 1)
        self.assertEqual(self.waits(), [])

    def test_acquisition_after_owner_exit_stops_retrying(self):
        execute = self.model.execute
        def release(identity, capabilities, request):
            with self.model.mutex:
                result = execute(identity, capabilities, request)
                if self.model.state.get('monotonic_ms', 0) >= 30 and self.holder.poll() is None:
                    self.holder.kill()
                    self.holder.wait(timeout=5)
                    self.model.process_exited('holder')
                return result
        with patch.object(self.model, 'execute', side_effect=release):
            self.assertEqual(self.run_script(), [{'outcome': 'ok', 'elapsed_ms': 30, 'remaining_ms': 35}])
        self.assertEqual(self.waits(), [10, 20])

    def test_non_contention_failure_does_not_wait(self):
        output = self.run_script(actions=[{'operation': 'lock', 'root': '/work/missing'}])
        self.assertEqual(output[0]['outcome'], 'not-found')
        self.assertEqual(self.waits(), [])

    def test_cancellation_prevents_initial_attempt(self):
        output = self.run_script(actions=[{'operation': 'cancel'}, {'operation': 'lock', 'root': '/work'}])
        self.assertEqual([item['outcome'] for item in output], ['ok', 'cancelled'])
        self.assertEqual(self.server.transcript, [])

    def test_unknown_wait_outcome_is_not_retried(self):
        self.model.state['faults'] = [{'tick': 3, 'kind': 'lost_ack'}]
        output = self.run_script()
        self.assertEqual(output[0]['outcome'], 'transport')
        self.assertEqual(self.waits(), [10])
        self.assertEqual(self.model.state['monotonic_ms'], 10)
        self.assertEqual(len(self.server.transcript), 3)


if __name__ == '__main__':
    unittest.main()
