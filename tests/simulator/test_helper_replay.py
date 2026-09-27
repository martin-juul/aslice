"""Runner evidence and replay must come from newly executed C++ helper peers."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.simulator.harness import Workspace, replay
from tools.simulator.helper_runner import inspection
from tools.simulator.model import Model

DRIVER = Path(sys.argv.pop(1)).resolve()
SIMULATOR = Path(sys.argv.pop(1)).resolve()


class HelperReplayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def record(self):
        manifest = json.loads((ROOT / 'tests/fixtures/artifact-manifest.json').read_text())
        with Workspace(self.root / 'original') as workspace:
            result, trace = inspection(workspace, DRIVER, manifest, seed=17)
        self.assertTrue(result['passed'], result)
        return trace

    def test_replay_runs_both_cpp_peers_and_retains_channel_setup(self):
        trace = self.record()
        recorded = json.loads(trace.read_text())
        self.assertEqual(recorded['schedule']['capacity'], 257)
        self.assertEqual(len(recorded['processes']), 2)
        self.assertGreater(len(recorded['requests']), 4)
        with Workspace(self.root / 'replay') as workspace:
            self.assertEqual(replay(workspace, SIMULATOR, trace, DRIVER), 0)
            result = json.loads((workspace / 'evidence/replay.json').read_text())
            self.assertTrue(result['matched'])
            self.assertTrue(all(len(result[field]) == 64 for field in (
                'recorded_executable_sha256', 'replay_executable_sha256')))
            self.assertEqual(list((workspace / 'sessions').iterdir()), [])
        # Stream normalization is separate from byte-exact OS transfer evidence.
        for process in recorded['processes'].values():
            raw = bytes.fromhex(process['stdout_hex']).replace(b'\r\n', b'\n')
            process['stdout_hex'] = raw.replace(b'\n', b'\r\n').hex()
        trace.write_text(json.dumps(recorded))
        with Workspace(self.root / 'normalized') as workspace:
            self.assertEqual(replay(workspace, SIMULATOR, trace, DRIVER), 0)

    def test_recorded_answer_does_not_replace_cpp_reexecution(self):
        trace = self.record()
        recorded = json.loads(trace.read_text())
        recorded['observations'][-1]['response']['observations'][0]['fabricated'] = True
        trace.write_text(json.dumps(recorded))
        with Workspace(self.root / 'replay') as workspace:
            self.assertEqual(replay(workspace, SIMULATOR, trace, DRIVER), 1)
            self.assertIn('observations', json.loads((workspace / 'evidence/replay.json').read_text())['differences'])

    def test_bad_schedule_refused_before_os_creation(self):
        trace = self.record()
        recorded = json.loads(trace.read_text())
        mutations = [dict(recorded['schedule'], capacity=True),
                     dict(recorded['schedule'], actors=['same', 'same']),
                     dict(recorded['schedule'], steps=[{'actor': 'foreign', 'action': {'command': 'send'}}])]
        for index, schedule in enumerate(mutations):
            malformed = copy.deepcopy(recorded)
            malformed['schedule'] = schedule
            trace.write_text(json.dumps(malformed))
            with Workspace(self.root / f'bad-{index}') as workspace:
                with self.assertRaises(ValueError):
                    replay(workspace, SIMULATOR, trace, DRIVER)
                self.assertFalse((workspace / 'os/state.json').exists())

    def test_failed_peer_is_reaped_and_recorded(self):
        # Simulator CLI does not implement the driver's channel invocation.
        with Workspace(self.root / 'failed') as workspace:
            result, trace = inspection(workspace, SIMULATOR, {})
            self.assertFalse(result['passed'])
            self.assertIsNotNone(result['error'])
            recorded = json.loads(trace.read_text())
            self.assertTrue(all(process['exit_status'] is not None for process in recorded['processes'].values()))
            self.assertEqual(list((workspace / 'sessions').iterdir()), [])

    def test_after_effect_failure_and_lost_ack_replay_without_resending(self):
        manifest = json.loads((ROOT / 'tests/fixtures/artifact-manifest.json').read_text())
        for kind in ('after', 'lost_ack'):
            with Workspace(self.root / kind) as workspace:
                model = Model(workspace)
                model.state['faults'] = [{'tick': 3, 'kind': kind}]
                model.save()
                result, trace = inspection(workspace, DRIVER, manifest)
                self.assertFalse(result['passed'])
                recorded = json.loads(trace.read_text())
                sends = [item for item in recorded['requests'] if item['request']['operation'] == 'send']
                self.assertEqual(len(sends), 1)
                self.assertGreater(sends[0]['response']['effects'][0]['bytes'], 0)
            with Workspace(self.root / (kind + '-replay')) as workspace:
                self.assertEqual(replay(workspace, SIMULATOR, trace, DRIVER), 0,
                                 (workspace / 'evidence/replay.json').read_text())

    def test_cli_helper_suite_and_explicit_driver_requirement(self):
        arguments = [sys.executable, '-m', 'tools.simulator', 'run', '--suite', 'helper',
                     '--aslice', str(SIMULATOR), '--workspace', str(self.root / 'suite')]
        refused = subprocess.run(arguments, cwd=ROOT, capture_output=True, timeout=10)
        self.assertEqual(refused.returncode, 2)
        self.assertFalse((self.root / 'suite').exists())
        result = subprocess.run([*arguments, '--helper-driver', str(DRIVER)], cwd=ROOT,
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['helper_inspection']['passed'])
        self.assertFalse(report['complete'])


if __name__ == '__main__':
    unittest.main()
