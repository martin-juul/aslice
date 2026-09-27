"""The actual C++ fixture lifecycle over simulated target I/O on either host."""
import copy
import json
import socket
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.simulator.fixtures import seed_catalogs, seed_input
from tools.simulator.harness import Workspace, launch, replay
from tools.simulator.model import Model
from tools.simulator.protocol import receive, send
from tools.simulator.server import Server

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == "__main__" else None


@unittest.skipUnless(BINARY, "run through CTest")
class FixtureLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="aslice-target-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.context = Workspace(self.parent / "workspace")
        self.workspace = self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)
        seed_catalogs(Model(self.workspace, seed=17))
        self.command("init")

    def command(self, verb, *arguments, version=1, code=0):
        command = ["dev", "fixture", verb, "--prefix", "/work/prefix"]
        if verb in ("install", "upgrade", "plan", "search", "info"):
            command += ["--catalog", f"/inputs/catalog-v{version}.json"]
        result, stdout, stderr, trace = launch(self.workspace, BINARY, command + list(arguments))
        self.assertEqual(result, code, stderr.decode(errors="replace"))
        self.trace = trace
        if code:
            self.assertTrue(stderr)
            return None
        self.assertEqual(stderr, b"")
        return json.loads(stdout)

    def state(self):
        return Model(self.workspace).state

    def files(self):
        state = self.state()
        return {path: copy.deepcopy(state["nodes"][inode]) for path, inode in state["paths"].items()}

    def fault(self, name, kind):
        model = Model(self.workspace)
        model.state["faults"] = [{"checkpoint": name, "kind": kind}]
        model.save()

    def test_install_upgrade_rollback_remove_and_power_loss(self):
        before = self.files()
        self.assertEqual(len(self.command("plan", "hello")["packages"]), 2)
        self.assertEqual(self.files(), before)
        first = self.command("install", "hello")["generation"]
        self.assertTrue(self.command("verify")["verified"])
        self.assertEqual(self.command("why", "greeting")["dependents"], ["core:hello"])
        installed = self.command("list")["packages"]
        self.assertEqual({item["name"] for item in installed}, {"core:hello", "core:greeting"})
        self.assertFalse(self.command("install", "hello")["changed"])
        before = self.files()
        self.command("upgrade", "--dry-run", version=2)
        self.assertEqual(self.files(), before)
        second = self.command("upgrade", version=2)["generation"]
        self.assertNotEqual(first, second)
        Model(self.workspace).power_loss()
        self.assertTrue(self.command("verify")["verified"])
        self.assertEqual(self.command("list")["generation"], second)
        self.command("rollback", first)
        self.assertTrue(all(item["version"] == "1.0.0" for item in self.command("list")["packages"]))
        self.command("uninstall", "greeting", code=2)
        self.command("uninstall", "hello")
        self.assertEqual(len(self.command("list")["packages"]), 1)
        self.command("autoremove")
        self.assertEqual(self.command("list")["packages"], [])
        self.command("rollback", second)
        self.assertTrue(all(item["version"] == "2.0.0" for item in self.command("list")["packages"]))
        self.assertGreaterEqual(len(self.command("history")["generations"]), 5)
        # Links and payload bytes exist in the OS model; no Mach-O execution is claimed.
        self.assertFalse((self.workspace / "work").exists())
        nodes = self.files()
        self.assertTrue(any(node["kind"] == "symlink" and node["target"].startswith("/work/prefix/store/") for node in nodes.values()))
        self.assertTrue(any(node.get("hex", "").startswith("23212f62696e2f7368") for node in nodes.values()))

    def test_activation_interruptions_keep_cpp_generation_decisions(self):
        original = self.command("list")["generation"]
        self.fault("before-switch", "before")
        self.command("install", "hello", code=1)
        self.assertEqual(self.command("list")["generation"], original)
        self.command("install", "hello")
        self.fault("after-switch", "after")
        self.command("upgrade", version=2, code=1)
        Model(self.workspace).power_loss()
        self.assertTrue(all(item["version"] == "2.0.0" for item in self.command("list")["packages"]))
        self.assertFalse(self.command("upgrade", version=2)["changed"])

    def test_real_process_termination_and_power_loss_have_distinct_evidence(self):
        original = self.command("list")["generation"]
        for kind in ("terminate", "power_loss"):
            self.fault("before-switch", kind)
            code, _, _, trace = launch(self.workspace, BINARY, ["dev", "fixture", "install", "hello",
                "--prefix", "/work/prefix", "--catalog", "/inputs/catalog-v1.json"])
            self.assertNotEqual(code, 0)
            evidence = json.loads(trace.read_text())
            self.assertTrue(evidence["terminated_by_harness"])
            self.assertEqual(evidence["termination_kind"], kind)
            self.assertEqual(self.command("list")["generation"], original)
        self.command("install", "hello")
        self.assertTrue(self.command("verify")["verified"])

    def test_malicious_catalog_and_external_edits_are_refused(self):
        before = self.files()
        self.command("install", "missing", code=2)
        self.assertEqual(self.files(), before)
        catalog = json.loads((ROOT / "tests/fixtures/prototype/catalog-v1.json").read_text())
        catalog["packages"][0]["files"] = {"../escape": {"text": "bad", "executable": False}}
        seed_input(Model(self.workspace), "/inputs/catalog-v1.json", json.dumps(catalog).encode())
        before = self.files()
        self.command("install", "hello", code=2)
        self.assertEqual(self.files(), before)
        seed_catalogs(Model(self.workspace))
        installed = self.command("install", "hello")["generation"]
        model = Model(self.workspace)
        path = next(path for path in model.state["paths"] if "/store/" in path and path.endswith("/bin/hello"))
        model.state["nodes"][model.state["paths"][path]]["hex"] = b"tampered".hex()
        model.save()
        self.command("verify", code=2)
        self.command("rollback", installed, code=2)

    def test_replay_reexecutes_install_and_its_filesystem_requests(self):
        self.command("install", "hello")
        with Workspace(self.parent / "replay") as fresh:
            self.assertEqual(replay(fresh, BINARY, self.trace), 0)
        evidence = json.loads(self.trace.read_text())
        operations = {item["request"]["operation"] for item in evidence["requests"]}
        self.assertTrue({"open_new", "write_handle", "rename", "flush_directory", "lock"} <= operations)

    def test_case_preservation_and_read_only_creation(self):
        catalog = json.loads((ROOT / "tests/fixtures/prototype/catalog-v1.json").read_text())
        catalog["packages"][1]["files"]["share/Hello.TXT"] = {"text": "Mixed case", "executable": False}
        seed_input(Model(self.workspace), "/inputs/catalog-v1.json", json.dumps(catalog).encode())
        self.command("install", "hello")
        self.assertTrue(self.command("verify")["verified"])
        Model(self.workspace).power_loss()
        self.assertTrue(self.command("verify")["verified"])
        state = self.state()
        path = next(path for path in state["paths"] if "/store/" in path and path.endswith("/share/hello.txt"))
        self.assertEqual(state["names"][path], "Hello.TXT")
        self.assertEqual(state["nodes"][state["paths"][path]]["mode"], 0o400)

    def test_cpp_retries_short_writes_without_truncating_payloads(self):
        model = Model(self.workspace)
        model.state["maximum_write"] = 17
        model.save()
        self.command("install", "hello")
        evidence = json.loads(self.trace.read_text())
        writes = [item for item in evidence["requests"] if item["request"]["operation"] == "write_handle"]
        self.assertTrue(any(item["response"]["result"]["written"] < len(item["request"]["arguments"]["hex"]) // 2 for item in writes))
        Model(self.workspace).power_loss()
        self.assertTrue(self.command("verify")["verified"])

    def test_cpp_contender_refuses_an_external_process_lock(self):
        model = Model(self.workspace)
        before = copy.deepcopy(model.state["paths"])
        server = Server(model)
        self.addCleanup(server.close)
        descriptor = server.issue("external-owner", ["filesystem"])
        owner = subprocess.Popen([sys.executable, '-c', 'import sys; sys.stdin.read()'], stdin=subprocess.PIPE)
        self.addCleanup(owner.stdin.close)
        server.attach_process("external-owner", owner)
        with socket.create_connection(server.server_address, timeout=5) as holder:
            send(holder, {"version": 1, "operation": "hello", "identity": "external-owner", "token": descriptor["token"]})
            self.assertTrue(receive(holder)["authenticated"])
            send(holder, {"version": 1, "id": 1, "capability": "filesystem", "operation": "lock",
                          "arguments": {"path": "/work/prefix/.lock"}, "preconditions": {}})
            self.assertIsNone(receive(holder)["failure"])
            session = self.workspace / "sessions/contender.json"
            session.write_text(json.dumps(server.issue("contender", ["machine", "filesystem", "process"])))
            contender = subprocess.Popen([str(BINARY), "--session", str(session), "dev", "fixture", "install", "hello",
                                      "--prefix", "/work/prefix", "--catalog", "/inputs/catalog-v1.json"],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            server.attach_process("contender", contender)
            _, stderr = contender.communicate(timeout=30)
            session.unlink()
            self.assertEqual(contender.returncode, 4, stderr)
            self.assertEqual(model.state["paths"], before)
        server.close()
        self.command("install", "hello")

    def test_lost_activation_acknowledgement_is_reconciled_by_cpp(self):
        self.command("install", "hello")
        model = Model(self.workspace)
        baseline = copy.deepcopy(model.state)
        self.command("upgrade", version=2)
        trace = json.loads(self.trace.read_text())
        activation = next(item for item in trace["requests"] if
                          item["request"]["operation"] == "rename" and
                          item["request"]["arguments"].get("destination") == "/work/prefix/profiles/default")
        baseline["faults"] = [{"tick": activation["response"]["receipt"]["tick"], "kind": "lost_ack"}]
        code, _, _, interrupted = launch(self.workspace, BINARY, trace["command"], baseline=baseline)
        self.assertEqual(code, 1)
        evidence = json.loads(interrupted.read_text())
        self.assertFalse(evidence["requests"][-1]["acknowledged"])
        self.assertFalse(self.command("upgrade", version=2)["changed"])
        Model(self.workspace).power_loss()
        self.assertTrue(all(item["version"] == "2.0.0" for item in self.command("list")["packages"]))
        self.assertTrue(self.command("verify")["verified"])


if __name__ == "__main__":
    unittest.main()
