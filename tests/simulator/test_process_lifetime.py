"""Process exit, transport loss and power loss have different OS lifetimes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.simulator.harness import Workspace
from tools.simulator.model import Model
from tools.simulator.server import Server


class ProcessLifetimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.context = Workspace(Path(temporary.name) / 'workspace')
        self.workspace = self.context.__enter__()
        self.addCleanup(self.context.__exit__)
        self.model = Model(self.workspace)
        self.server = Server(self.model)
        self.addCleanup(self.server.close)
        self.sequence = {}

    def peer(self, identity, credentials=None):
        descriptor = self.server.issue(identity, ['filesystem', 'process'], credentials)
        path = self.workspace / 'sessions' / (identity + '.json')
        path.write_text(json.dumps(descriptor))
        process = subprocess.Popen([sys.executable, str(ROOT / 'tests/simulator/process_peer.py'), str(path)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for stream in (process.stdin, process.stdout, process.stderr):
            self.addCleanup(stream.close)
        self.server.attach_process(identity, process)
        self.assertEqual(json.loads(process.stdout.readline()), {'version': 1, 'authenticated': True})
        self.sequence[identity] = 0
        return process

    def request(self, process, identity, operation, capability='filesystem', **arguments):
        self.sequence[identity] += 1
        return self.exchange(process, {'version': 1, 'id': self.sequence[identity],
            'capability': capability, 'operation': operation, 'arguments': arguments, 'preconditions': {}})

    def exchange(self, process, value):
        process.stdin.write(json.dumps(value) + '\n')
        process.stdin.flush()
        return json.loads(process.stdout.readline())

    def reap(self, process):
        process.wait(timeout=5)
        # Synchronize observations with resource cleanup rather than timing sleeps.
        for identity, registered in self.server.processes.items():
            if registered is process:
                index = list(self.server.processes).index(identity)
                self.server.watchers[index].join(timeout=5)
                self.assertFalse(self.server.watchers[index].is_alive())

    def test_disconnect_retains_lock_and_handle_until_owner_exits(self):
        owner, contender = self.peer('owner'), self.peer('contender')
        opened = self.request(owner, 'owner', 'open_new', path='/work/file', mode=0o600)
        self.assertIsNone(opened['failure'])
        self.assertIsNone(self.request(owner, 'owner', 'lock', path='/work/file')['failure'])
        self.assertEqual(self.exchange(owner, 'disconnect'), {'disconnected': True})
        self.assertIsNone(owner.poll())
        blocked = self.request(contender, 'contender', 'lock', path='/work/file')
        self.assertEqual(blocked['failure']['code'], 'busy')
        self.assertTrue(any(handle['owner'] == 'owner' for handle in self.model.handles.values()))
        owner.kill()
        self.reap(owner)
        self.assertFalse(any(handle['owner'] == 'owner' for handle in self.model.handles.values()))
        self.assertIsNone(self.request(contender, 'contender', 'lock', path='/work/file')['failure'])

    def test_lost_ack_does_not_release_mutation_ownership(self):
        owner, contender = self.peer('owner'), self.peer('contender')
        self.request(owner, 'owner', 'create', path='/work/lock')
        with self.model.mutex:
            self.model.state['faults'] = [{'tick': self.model.state['tick'] + 1, 'kind': 'lost_ack'}]
        self.assertEqual(self.request(owner, 'owner', 'lock', path='/work/lock'), {'disconnected': True})
        self.assertIsNone(owner.poll())
        blocked = self.request(contender, 'contender', 'lock', path='/work/lock')
        self.assertEqual(blocked['failure']['code'], 'busy')
        self.assertIsNone(self.model.state['outcomes']['owner:2']['failure'])
        owner.kill()
        self.reap(owner)
        self.assertIsNone(self.request(contender, 'contender', 'lock', path='/work/lock')['failure'])

    def test_termination_preserves_other_live_processes_and_volatile_bytes(self):
        manager, helper, contender = self.peer('manager'), self.peer('helper'), self.peer('contender')
        self.request(helper, 'helper', 'create', path='/work/file')
        self.request(helper, 'helper', 'write', path='/work/file', hex='6162')
        self.request(helper, 'helper', 'lock', path='/work/file')
        with self.model.mutex:
            self.model.state['faults'] = [{'tick': self.model.state['tick'] + 1, 'kind': 'terminate'}]
        manager.stdin.write(json.dumps({'version': 1, 'id': 1, 'capability': 'process',
            'operation': 'checkpoint', 'arguments': {'name': 'stop'}, 'preconditions': {}}) + '\n')
        manager.stdin.flush()
        self.reap(manager)
        self.assertIsNone(helper.poll())
        self.assertEqual(self.request(helper, 'helper', 'read', path='/work/file')['result']['hex'], '6162')
        self.assertEqual(self.request(contender, 'contender', 'lock', path='/work/file')['failure']['code'], 'busy')
        self.assertEqual(self.server.terminated, {'manager': 'terminate'})

    def test_power_loss_stops_every_process_and_discards_unflushed_state(self):
        first, second = self.peer('first'), self.peer('second')
        self.request(second, 'second', 'open_new', path='/work/volatile', mode=0o600)
        self.request(second, 'second', 'lock', path='/work/volatile')
        with self.model.mutex:
            self.model.state['faults'] = [{'tick': self.model.state['tick'] + 1, 'kind': 'power_loss'}]
        first.stdin.write(json.dumps({'version': 1, 'id': 1, 'capability': 'process',
            'operation': 'checkpoint', 'arguments': {'name': 'power'}, 'preconditions': {}}) + '\n')
        first.stdin.flush()
        self.reap(first)
        self.reap(second)
        self.assertEqual(self.server.terminated, {'first': 'power_loss', 'second': 'power_loss'})
        self.assertEqual(self.model.locks, {})
        self.assertEqual(self.model.handles, {})
        self.assertNotIn('/work/volatile', self.model.state['paths'])
        self.assertEqual(self.server.credentials, {})
        self.assertEqual(self.model.process_credentials, {})
        for identity in ('first', 'second'):
            response, _ = self.model.execute(identity, ['machine'], {
                'version': 1, 'id': 999, 'capability': 'machine', 'operation': 'observe',
                'arguments': {}, 'preconditions': {}})
            self.assertEqual(response['failure']['code'], 'process')
            self.assertEqual(response['effects'], [])

    def test_process_identity_cannot_be_reissued_or_rebound(self):
        owner = self.peer('owner')
        with self.assertRaises(ValueError):
            self.server.issue('owner', ['filesystem'])
        with self.assertRaises(ValueError):
            self.server.attach_process('owner', owner)
        owner.kill()
        self.reap(owner)
        with self.assertRaises(ValueError):
            self.server.issue('owner', ['filesystem'])

    def test_issued_credentials_survive_disconnect_but_not_process_exit(self):
        owner = self.peer('owner', {'uid': 502, 'gid': 77, 'groups': [20]})
        observed = self.request(owner, 'owner', 'observe', capability='process')['result']
        self.assertEqual(observed, {'identity': 'owner', 'uid': 502, 'gid': 77, 'groups': [20]})
        self.exchange(owner, 'disconnect')
        self.assertEqual(self.model.process_credentials['owner'].uid, 502)
        owner.kill()
        self.reap(owner)
        self.assertNotIn('owner', self.model.process_credentials)
        response, _ = self.model.execute('owner', ['machine'], {
            'version': 1, 'id': 999, 'capability': 'machine', 'operation': 'observe',
            'arguments': {}, 'preconditions': {}})
        self.assertEqual(response['failure']['code'], 'process')
        self.assertEqual(response['effects'], [])
        with self.assertRaises(ValueError):
            self.server.issue('owner', ['process'], {'uid': 0, 'gid': 0, 'groups': []})


if __name__ == '__main__':
    unittest.main()
