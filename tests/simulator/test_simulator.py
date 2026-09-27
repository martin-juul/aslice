"""Independent assertions over real C++ requests and inspectable OS state."""
import json
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.simulator.harness import Workspace, launch, replay
from tools.simulator.model import Model, Refusal, canonical
from tools.simulator.protocol import MAX_FRAME, receive, send
from tools.simulator.server import Server

BINARIES = [Path(arg).resolve() for arg in sys.argv[1:4]] if __name__ == "__main__" else []
if BINARIES:
    del sys.argv[1:4]


def action(operation, path="/work/file", **arguments):
    return {"capability": "filesystem", "operation": operation,
            "arguments": {"path": path, **arguments}}


@unittest.skipUnless(BINARIES, "run through CTest")
class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="aslice-simulator-")
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.context = Workspace(self.parent / "workspace")
        self.workspace = self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)

    def script(self, actions, **kwargs):
        result = launch(self.workspace, BINARIES[1], [], driver=True, script=actions, **kwargs)
        code, stdout, stderr, trace = result
        self.assertEqual(stderr, b"")
        return code, [json.loads(line) for line in stdout.splitlines()], json.loads(trace.read_text()), trace

    def test_cpp_cli_and_normal_binary_separation(self):
        command = ["version", "normalize", "v7.1"]
        code, stdout, stderr, trace = launch(self.workspace, BINARIES[0], command)
        native = subprocess.run([str(BINARIES[2]), *command], capture_output=True, check=True)
        self.assertEqual((code, stdout, stderr), (0, native.stdout, native.stderr))
        evidence = json.loads(trace.read_text())
        self.assertEqual(evidence["requests"][0]["request"]["capability"], "machine")
        self.assertEqual(evidence["qualification"], "simulated")
        self.assertEqual(len(evidence["executable_sha256"]), 64)
        code, _, _, _ = launch(self.workspace, BINARIES[0], ["dev", "fixture", "init"])
        self.assertEqual(code, 2)
        native = subprocess.run([str(BINARIES[2]), "--session", "not-a-session", "--version"], capture_output=True)
        self.assertNotEqual(native.returncode, 0)

    def test_cpp_writes_and_durable_data_survive_restart(self):
        code, output, _, _ = self.script([action("create"), action("write", hex="68656c6c6f"),
            action("flush_file"), action("flush_directory", "/work"), action("read")])
        self.assertEqual(code, 0)
        self.assertEqual(output[-1]["result"], {"hex": "68656c6c6f"})
        model = Model(self.workspace)
        model.power_loss()
        _, output, _, _ = self.script([action("read")])
        self.assertEqual(output[-1]["result"], {"hex": "68656c6c6f"})

    def test_file_flush_does_not_flush_name(self):
        self.script([action("create"), action("write", hex="61"), action("flush_file")])
        Model(self.workspace).power_loss()
        _, output, _, _ = self.script([action("stat")])
        self.assertEqual(output[0]["error"], "not-found")

    def test_directory_flush_does_not_flush_data(self):
        self.script([action("create"), action("write", hex="61"), action("flush_directory", "/work")])
        Model(self.workspace).power_loss()
        _, output, _, _ = self.script([action("read")])
        self.assertEqual(output[0]["result"], {"hex": ""})

    def test_before_and_after_faults_distinguish_effects(self):
        model = Model(self.workspace)
        model.state["faults"] = [{"tick": 1, "kind": "before"}, {"tick": 2, "kind": "after"}]
        model.save()
        _, output, evidence, _ = self.script([action("create"), action("create"), action("stat")])
        self.assertEqual([item.get("error") for item in output], ["injected", "injected", None])
        self.assertEqual(evidence["requests"][0]["response"]["effects"], [])
        self.assertEqual(evidence["requests"][1]["response"]["effects"][0]["operation"], "create")
        self.assertEqual(output[1]["effects"][0]["operation"], "create")

    def test_lost_ack_has_persistent_outcome_without_retry(self):
        model = Model(self.workspace)
        model.state["faults"] = [{"tick": 1, "kind": "lost_ack"}]
        model.save()
        code, output, evidence, first_trace = self.script([action("create")], identity="writer")
        self.assertEqual(code, 3)
        self.assertEqual(output[0]["error"], "transport")
        self.assertFalse(evidence["requests"][0]["acknowledged"])
        _, output, _, next_trace = self.script([
            {"capability": "outcome", "operation": "lookup", "arguments": {"id": 1}}, action("create")],
            identity="writer")
        self.assertEqual(output[0]["result"]["effects"][0]["operation"], "create")
        self.assertEqual(output[1]["error"], "exists")
        self.assertNotEqual(first_trace, next_trace)
        self.assertEqual(json.loads(first_trace.read_text()), evidence)

    def test_power_loss_disconnects_and_discards_unflushed_writes(self):
        model = Model(self.workspace)
        model.state["faults"] = [{"tick": 2, "kind": "power_loss"}]
        model.save()
        code, _, evidence, _ = self.script([action("create"), action("write", hex="61")])
        self.assertNotEqual(code, 0)
        self.assertNotIn("/work/file", evidence["final_state"]["paths"])
        self.assertTrue(evidence["terminated_by_harness"])
        self.assertEqual(evidence["termination_kind"], "power_loss")

    def test_permissions_collisions_and_capability_refusals(self):
        _, output, _, _ = self.script([action("create", "/System/evil"),
            action("create", "/work/Caf\u00e9"), action("create", "/work/CAFE\u0301"),
            action("create", "/work/private", mode=0), action("write", "/work/private", hex="61"),
            {"capability": "apple", "operation": "execute", "arguments": {}}])
        self.assertEqual([item.get("error") for item in output],
                         ["protected", None, "exists", None, "permission", "capability"])

    def test_symlink_parent_is_never_host_traversed(self):
        _, output, _, _ = self.script([action("symlink", "/work/link", target=str(self.parent)),
                                      action("create", "/work/link/escape")])
        self.assertEqual(output[1]["error"], "permission")
        self.assertFalse((self.parent / "escape").exists())

    def test_directory_flush_preserves_symlink_target(self):
        self.script([action("symlink", "/work/link", target="relative-target"),
                     action("flush_directory", "/work")])
        Model(self.workspace).power_loss()
        _, output, _, _ = self.script([action("stat", "/work/link")])
        self.assertEqual(output[0]["result"]["target"], "relative-target")

    def test_disk_full_keeps_existing_bytes(self):
        model = Model(self.workspace)
        model.state["quota"] = 2
        model.save()
        _, output, _, _ = self.script([action("create"), action("write", hex="6162"),
                                      action("write", hex="616263"), action("read")])
        self.assertEqual(output[2]["error"], "no-space")
        self.assertEqual(output[3]["result"]["hex"], "6162")

    def test_replay_executes_cpp_and_detects_tampering(self):
        _, _, _, trace = self.script([action("create"), action("write", hex="61"), action("read")])
        with Workspace(self.parent / "replay") as fresh:
            self.assertEqual(replay(fresh, BINARIES[1], trace), 0)
        edited = json.loads(trace.read_text())
        edited["requests"][0]["response"]["result"]["inode"] = "wrong"
        altered = self.workspace / "inputs/altered.json"
        altered.write_text(json.dumps(edited))
        with Workspace(self.parent / "replay-bad") as fresh:
            self.assertEqual(replay(fresh, BINARIES[1], altered), 1)

    def test_full_suite_reports_missing_coverage(self):
        process = subprocess.run([sys.executable, "-m", "tools.simulator", "run", "--suite", "full",
                                  "--workspace", str(self.parent / "full"), "--seed", "17",
                                  "--aslice", str(BINARIES[0])], cwd=ROOT, capture_output=True)
        self.assertEqual(process.returncode, 1, process.stderr)
        report = json.loads(process.stdout)
        self.assertTrue(report["foundation_passed"])
        self.assertFalse(report["complete"])
        self.assertTrue(report["mandatory_gaps"])

    def test_protocol_authentication_and_oversize(self):
        server = Server(Model(self.workspace))
        self.addCleanup(server.close)
        descriptor = server.issue("p1", ["machine"])
        owner = subprocess.Popen([sys.executable, '-c', 'import sys; sys.stdin.read()'], stdin=subprocess.PIPE)
        self.addCleanup(owner.stdin.close)
        server.attach_process("p1", owner)
        for token in ("wrong", descriptor["token"]):
            with socket.create_connection(server.server_address, timeout=2) as connection:
                send(connection, {"version": 1, "operation": "hello", "identity": "p1", "token": token})
                if token == "wrong":
                    with self.assertRaises(EOFError):
                        receive(connection)
                else:
                    self.assertTrue(receive(connection)["authenticated"])
                    connection.sendall(struct.pack("!I", MAX_FRAME + 1))
                    with self.assertRaises(EOFError):
                        receive(connection)
        with socket.create_connection(server.server_address, timeout=2) as connection:
            send(connection, {"version": 1, "operation": "hello", "identity": "p1", "token": descriptor["token"]})
            with self.assertRaises(EOFError):
                receive(connection)

    def test_concurrent_lock_ownership_and_process_exit(self):
        model = Model(self.workspace)
        model.filesystem("a", "create", {"path": "/work/lock"})
        model.filesystem("a", "lock", {"path": "/work/lock"})
        with self.assertRaises(Refusal) as refused:
            model.filesystem("b", "lock", {"path": "/work/lock"})
        self.assertEqual(refused.exception.code, "busy")
        model.process_exited("a")
        model.filesystem("b", "lock", {"path": "/work/lock"})

    def test_path_and_workspace_refusals(self):
        for path in ("../escape", "/work/../escape", "C:/file", "/work//file", "/work/file/", "/work/./file"):
            with self.assertRaises(Refusal):
                canonical(path)
        with self.assertRaises(OSError):
            with Workspace(self.workspace):
                self.fail("concurrent workspace mutation was admitted")
        with self.assertRaises(ValueError):
            launch(self.workspace, BINARIES[0], ["--version"], identity="../../escape")

    def test_cpp_rejects_host_and_noncanonical_target_paths(self):
        for path in ("C:/host", "/work/../outside"):
            code, stdout, _, trace = launch(self.workspace, BINARIES[1], [], driver=True,
                                            script=[action("create", path)])
            self.assertEqual(code, 2)
            self.assertEqual(stdout, b"")
            self.assertEqual(json.loads(trace.read_text())["requests"], [])


if __name__ == "__main__":
    unittest.main()
