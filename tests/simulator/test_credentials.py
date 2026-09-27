"""C++ callers exercise harness-issued identities and bounded mode semantics."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.simulator.credentials import Credentials
from tools.simulator.harness import Workspace, launch, replay
from tools.simulator.model import Model

DRIVER = Path(sys.argv.pop(1)).resolve()
CLIENT = Path(sys.argv.pop(1)).resolve()


def action(operation, path='/work/file', **arguments):
    return {'capability': 'filesystem', 'operation': operation,
            'arguments': {'path': path, **arguments}}


class CredentialTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)
        context = Workspace(self.parent / 'workspace')
        self.workspace = context.__enter__()
        self.addCleanup(context.__exit__)
        model = Model(self.workspace)
        model.state['nodes']['2']['mode'] = 0o777
        model.state['nodes']['2']['gid'] = 77
        model.filesystem('setup', 'create', {'path': '/work/file', 'mode': 0o600})
        model.filesystem('setup', 'write', {'path': '/work/file', 'hex': '6162'})
        model.save()

    def script(self, commands, credentials=None, **kwargs):
        code, stdout, stderr, self.trace = launch(self.workspace, DRIVER, [], driver=True,
            script=commands, credentials=credentials, **kwargs)
        self.assertEqual((code, stderr), (0, b''))
        return [json.loads(line) for line in stdout.splitlines()]

    def mode(self, mode, **extra):
        model = Model(self.workspace)
        node = model.state['nodes'][model.state['paths']['/work/file']]
        node.update(mode=mode, **extra)
        model.save()

    def test_owner_group_and_other_classes_do_not_fall_through(self):
        self.mode(0o004)
        for uid, gid, groups, permitted in ((501, 99, [], False), (502, 77, [], False),
                                           (502, 99, [77], False), (503, 99, [], True)):
            with self.subTest(uid=uid, gid=gid, groups=groups):
                result = self.script([action('read')], {'uid': uid, 'gid': gid, 'groups': groups})[0]
                self.assertEqual(result['failure'] is None, permitted)
                if permitted:
                    self.assertEqual(result['result']['hex'], '6162')
                else:
                    self.assertEqual(result['failure']['code'], 'permission')
        self.mode(0o040)
        result = self.script([action('read')], {'uid': 502, 'gid': 99, 'groups': [77]})[0]
        self.assertEqual(result['result']['hex'], '6162')

    def test_owner_group_umask_durability_and_replay(self):
        principal = {'uid': 502, 'gid': 99, 'groups': [77, 10]}
        results = self.script([
            {'capability': 'process', 'operation': 'observe'},
            {'capability': 'process', 'operation': 'umask', 'arguments': {'mask': 0o027}},
            action('create', '/work/new', mode=0o666, uid=0, gid=0),
            action('stat', '/work/new'), action('flush_file', '/work/new'),
            action('flush_directory', '/work')], principal)
        self.assertEqual(results[0]['result']['groups'], [10, 77])
        self.assertEqual({key: results[3]['result'][key] for key in ('uid', 'gid', 'mode')},
                         {'uid': 502, 'gid': 77, 'mode': 0o640})
        trace = self.trace
        self.assertEqual(json.loads(trace.read_text())['credentials'],
                         {'uid': 502, 'gid': 99, 'groups': [10, 77]})
        with Workspace(self.parent / 'replay') as workspace:
            self.assertEqual(replay(workspace, DRIVER, trace), 0)
        model = Model(self.workspace)
        model.power_loss()
        result = self.script([action('stat', '/work/new')], principal)[0]['result']
        self.assertEqual((result['uid'], result['gid'], result['mode']), (502, 77, 0o640))

    def test_open_descriptor_survives_chmod_but_new_open_is_denied(self):
        results = self.script([action('open_read'), action('chmod', mode=0),
                               action('read_handle', handle='1', offset=0, length=2),
                               action('open_read')])
        self.assertEqual(results[2]['result']['hex'], '6162')
        self.assertEqual(results[3]['failure']['code'], 'permission')

    def test_directory_search_and_shared_namespace_permissions(self):
        principal = {'uid': 502, 'gid': 77, 'groups': []}
        # A writable parent permits removal without granting ownership of its files.
        result = self.script([action('chmod', mode=0o777), action('unlink')], principal)
        self.assertEqual(result[0]['failure']['code'], 'permission')
        self.assertIsNone(result[1]['failure'])
        model = Model(self.workspace)
        model.state['nodes']['2']['mode'] = 0o006
        model.save()
        result = self.script([action('create', '/work/new')], principal)[0]
        self.assertEqual(result['failure']['code'], 'permission')

    def test_root_dac_does_not_grant_capability_or_protected_path_authority(self):
        principal = {'uid': 0, 'gid': 0, 'groups': []}
        self.mode(0)
        result = self.script([action('read'), action('create', '/protected')], principal)
        self.assertEqual(result[0]['result']['hex'], '6162')
        self.assertEqual(result[1]['failure']['code'], 'protected')
        result = self.script([action('read')], principal, capabilities=['process'])[0]
        self.assertEqual(result['failure']['code'], 'capability')

    def test_unsupported_acl_and_special_mode_refuse_access(self):
        for attributes in ({'acl': [{'allow': 'everyone'}]}, {'mode': 0o1600}, {'flags': 1}):
            self.mode(attributes.get('mode', 0o600), acl=attributes.get('acl', []),
                      flags=attributes.get('flags', 0))
            result = self.script([action('read')])[0]
            self.assertEqual(result['failure']['code'], 'unsupported-metadata')

    def test_cpp_private_prefix_refuses_foreign_owner_and_acl(self):
        model = Model(self.workspace)
        model.filesystem('setup', 'mkdir', {'path': '/work/prefix', 'mode': 0o700})
        model.save()
        code, _, _, _ = launch(self.workspace, CLIENT,
            ['dev', 'fixture', 'init', '--prefix', '/work/prefix'],
            credentials={'uid': 502, 'gid': 77, 'groups': []})
        self.assertNotEqual(code, 0)
        model = Model(self.workspace)
        model.state['nodes'][model.state['paths']['/work/prefix']]['acl'] = [{'allow': 'everyone'}]
        model.save()
        code, _, _, _ = launch(self.workspace, CLIENT,
            ['dev', 'fixture', 'init', '--prefix', '/work/prefix'])
        self.assertNotEqual(code, 0)
        self.assertFalse(any(path.startswith('/work/prefix/') for path in Model(self.workspace).state['paths']))

    def test_invalid_credentials_refused_before_workspace_state(self):
        for index, value in enumerate(({'uid': True, 'gid': 20, 'groups': []},
                                      {'uid': 501, 'gid': -1, 'groups': []},
                                      {'uid': 501, 'gid': 20, 'groups': [1, 1]},
                                      {'uid': 501, 'gid': 20, 'groups': list(range(33))},
                                      {'uid': 501, 'gid': 20},
                                      {'uid': 501, 'gid': 20, 'groups': [False]})):
            with self.subTest(value=value), Workspace(self.parent / f'invalid-{index}') as workspace:
                with self.assertRaises(ValueError):
                    launch(workspace, DRIVER, [], driver=True, script=[], credentials=value)
                self.assertFalse((workspace / 'os/state.json').exists())
        source = {'uid': 502, 'gid': 77, 'groups': [20]}
        principal = Credentials.parse(source)
        source['groups'].append(99)
        self.assertEqual(principal.groups, (20,))


if __name__ == '__main__':
    unittest.main()
