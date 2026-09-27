"""Deterministically scheduled real processes over modeled inherited byte streams."""
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

DRIVER = str(Path(sys.argv.pop(1)).resolve())
MANAGER = str(Path(sys.argv.pop(1)).resolve())


class HelperChannelTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        context = Workspace(Path(temporary.name) / 'workspace')
        self.workspace = context.__enter__()
        self.addCleanup(context.__exit__)
        self.model = Model(self.workspace)
        self.server = Server(self.model)
        self.addCleanup(self.server.close)
        self.sequences = {}

    def pair(self, capacity=65536, cpp=False):
        descriptors = [self.server.issue(owner, ['channel', 'process']) for owner in ('manager', 'helper')]
        endpoints = self.server.inherit_channel('manager', 'helper', capacity)
        processes = []
        for descriptor, endpoint in zip(descriptors, endpoints):
            owner = descriptor['identity']
            path = self.workspace / 'sessions' / (owner + '.json')
            path.write_text(json.dumps(descriptor))
            arguments = ([DRIVER, str(path), endpoint] if cpp else
                         [sys.executable, str(ROOT / 'tests/simulator/process_peer.py'), str(path)])
            process = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
            for stream in (process.stdin, process.stdout, process.stderr):
                self.addCleanup(stream.close)
            self.server.attach_process(owner, process)
            greeting = json.loads(process.stdout.readline())
            if cpp:
                self.assertIsNone(greeting['failure'])
            else:
                self.assertEqual(greeting, {'version': 1, 'authenticated': True})
            self.sequences[owner] = 0
            processes.append(process)
        return (*processes, *endpoints)

    def exchange(self, process, action):
        process.stdin.write(json.dumps(action) + '\n')
        process.stdin.flush()
        line = process.stdout.readline()
        self.assertTrue(line, 'peer exited without responding')
        return json.loads(line)

    def request(self, owner, operation, **arguments):
        self.sequences[owner] += 1
        return self.exchange(self.server.processes[owner], {
            'version': 1, 'id': self.sequences[owner], 'capability': 'channel',
            'operation': operation, 'arguments': arguments, 'preconditions': {}})

    def stop(self, owner):
        process = self.server.processes[owner]
        process.kill()
        process.wait(timeout=5)
        watcher = self.server.watchers[list(self.server.processes).index(owner)]
        watcher.join(timeout=5)
        self.assertFalse(watcher.is_alive())

    def pump(self, sender, receiver, length):
        received = 0
        while received < length:
            sent = self.exchange(sender, {'command': 'send'})
            self.assertIsNone(sent['failure'])
            count = sent['result']['written']
            self.assertGreater(count, 0)
            self.assertLessEqual(count, 257)
            read = self.exchange(receiver, {'command': 'receive', 'limit': count})
            self.assertIsNone(read['failure'])
            self.assertEqual(len(read['result']['hex']) // 2, count)
            received += count
        self.assertEqual(received, length)

    def test_shared_cpp_inspection_with_short_transfers(self):
        manager, helper, _, _ = self.pair(capacity=257, cpp=True)
        fixture = ROOT / 'tests/fixtures/artifact-manifest.json'
        manifest = json.loads(fixture.read_text())
        queued = self.exchange(manager, {'command': 'request', 'manifest': manifest})
        self.pump(manager, helper, queued['remaining'])
        inspected = self.exchange(helper, {'command': 'inspect'})
        self.assertIn('remaining', inspected)
        self.assertIn('error', self.exchange(helper, {'command': 'inspect'}))
        self.pump(helper, manager, inspected['remaining'])
        outcome = self.exchange(manager, {'command': 'verify'})
        expected = json.loads(subprocess.check_output([MANAGER, 'artifact', 'inspect', str(fixture)], timeout=10))
        self.assertEqual(outcome, {'observations': [expected], 'effects': []})

    def test_full_empty_foreign_and_malformed_operations(self):
        _, _, left, right = self.pair(capacity=2)
        self.assertEqual(self.request('helper', 'receive', endpoint=right, length=1)['failure']['code'], 'would-block')
        self.assertEqual(self.request('manager', 'send', endpoint=left, hex='616263')['result'], {'written': 2})
        self.assertEqual(self.request('manager', 'send', endpoint=left, hex='64')['failure']['code'], 'would-block')
        self.assertEqual(self.request('manager', 'receive', endpoint=right, length=1)['failure']['code'], 'handle')
        for args in ({'length': True}, {'length': 16385}, {'length': 0}, {'length': 1, 'extra': 1}):
            self.assertEqual(self.request('helper', 'receive', endpoint=right, **args)['failure']['code'], 'arguments')
        for value in ('0', 'zz', 'AA', '00' * 16385):
            self.assertEqual(self.request('manager', 'send', endpoint=left, hex=value)['failure']['code'], 'arguments')
        self.assertEqual(self.request('helper', 'receive', endpoint=right, length=1)['result'], {'hex': '61', 'eof': False})
        self.assertEqual(self.request('helper', 'receive', endpoint=right, length=2)['result'], {'hex': '62', 'eof': False})

    def test_transport_loss_preserves_endpoint_and_exit_drains_before_eof(self):
        manager, _, left, right = self.pair()
        self.request('manager', 'send', endpoint=left, hex='6162')
        self.assertEqual(self.exchange(manager, 'disconnect'), {'disconnected': True})
        self.assertTrue(self.request('helper', 'observe', endpoint=right)['result']['peer_open'])
        self.assertIsNone(self.request('helper', 'send', endpoint=right, hex='63')['failure'])
        self.stop('manager')
        self.assertEqual(self.request('helper', 'receive', endpoint=right, length=9)['result'], {'hex': '6162', 'eof': False})
        self.assertEqual(self.request('helper', 'receive', endpoint=right, length=9)['result'], {'hex': '', 'eof': True})
        self.assertEqual(self.request('helper', 'send', endpoint=right, hex='64')['failure']['code'], 'broken-pipe')
        self.request('helper', 'close', endpoint=right)
        self.assertEqual(self.model.channels.endpoints, {})

    def test_lost_ack_and_after_effect_are_not_retransmitted_by_cpp(self):
        manager, helper, _, right = self.pair(cpp=True)
        manifest = json.loads((ROOT / 'tests/fixtures/artifact-manifest.json').read_text())
        queued = self.exchange(manager, {'command': 'request', 'manifest': manifest})
        with self.model.mutex:
            self.model.state['faults'] = [{'tick': self.model.state['tick'] + 1, 'kind': 'lost_ack'}]
        self.assertEqual(self.exchange(manager, {'command': 'send'})['error'], 'transport')
        self.assertIn('error', self.exchange(manager, {'command': 'send'}))
        self.assertEqual(len(self.model.channels.endpoints[right]['buffer']), queued['remaining'])
        read = self.exchange(helper, {'command': 'receive'})
        self.assertEqual(read['received'], queued['remaining'])
        self.assertIn('remaining', self.exchange(helper, {'command': 'inspect'}))
        with self.model.mutex:
            self.model.state['faults'] = [{'tick': self.model.state['tick'] + 1, 'kind': 'after'}]
        failed = self.exchange(helper, {'command': 'send'})
        self.assertEqual(failed['failure']['code'], 'injected')
        self.assertGreater(failed['effects'][0]['bytes'], 0)
        self.assertIn('error', self.exchange(helper, {'command': 'send'}))

    def test_power_loss_discards_channels_without_reusing_endpoints(self):
        manager, helper, left, right = self.pair()
        self.request('manager', 'send', endpoint=left, hex='61')
        with self.model.mutex:
            self.model.state['faults'] = [{'tick': self.model.state['tick'] + 1, 'kind': 'power_loss'}]
        self.sequences['helper'] += 1
        helper.stdin.write(json.dumps({'version': 1, 'id': self.sequences['helper'],
            'capability': 'channel', 'operation': 'observe',
            'arguments': {'endpoint': right}, 'preconditions': {}}) + '\n')
        helper.stdin.flush()
        for process in (manager, helper):
            process.wait(timeout=5)
        for watcher in self.server.watchers:
            watcher.join(timeout=5)
        self.assertEqual(self.model.channels.endpoints, {})
        for owner in ('new-manager', 'new-helper'):
            self.server.issue(owner, ['channel'])
        fresh = self.server.inherit_channel('new-manager', 'new-helper')
        self.assertTrue(set(fresh).isdisjoint({left, right}))

    def test_inheritance_cannot_be_added_after_launch_or_without_capability(self):
        self.server.issue('first', ['channel'])
        self.server.issue('second', ['process'])
        with self.assertRaises(ValueError):
            self.server.inherit_channel('first', 'second')
        self.pair()
        with self.assertRaises(ValueError):
            self.server.inherit_channel('manager', 'helper')

    def test_capacity_and_endpoint_allocation_are_bounded(self):
        for owner in ('first', 'second'):
            self.server.issue(owner, ['channel'])
        for capacity in (True, 0, -1, 65537):
            with self.assertRaises(ValueError):
                self.server.inherit_channel('first', 'second', capacity)
        self.assertEqual(self.model.channels.endpoints, {})
        for _ in range(128):
            self.server.inherit_channel('first', 'second', 1)
        with self.assertRaises(ValueError):
            self.server.inherit_channel('first', 'second', 1)
        self.model.process_exited('first')
        self.model.process_exited('second')
        self.assertEqual(self.model.channels.endpoints, {})
        self.assertEqual(self.server.inherit_channel('first', 'second', 1), ('257', '258'))

    def test_before_effect_failure_does_not_transfer_bytes(self):
        _, _, left, right = self.pair()
        with self.model.mutex:
            self.model.state['faults'] = [{'tick': self.model.state['tick'] + 1, 'kind': 'before'}]
        response = self.request('manager', 'send', endpoint=left, hex='6162')
        self.assertEqual(response['failure']['code'], 'injected')
        self.assertEqual(response['effects'], [])
        self.assertEqual(self.request('helper', 'receive', endpoint=right, length=2)['failure']['code'], 'would-block')


if __name__ == '__main__':
    unittest.main()
