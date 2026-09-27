"""Independent archive and manifest checks through the real C++ platform client."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.rehearsal.fixtures import seed_catalogs, seed_input
from tools.rehearsal.harness import Workspace, launch, replay
from tools.rehearsal.model import Model, Refusal

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == "__main__" else None


@unittest.skipUnless(BINARY, "run through CTest")
class InspectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)
        context = Workspace(self.parent / "workspace")
        self.workspace = context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)
        self.data = json.loads((ROOT / "tests/fixtures/artifact-manifest.json").read_text())
        # Exercise a relocation crossing the platform's 64 KiB read boundary.
        self.payload = b"x" * 65535 + b"ABCD" + b"z" * 100
        self.data["files"][0].update(size=len(self.payload), sha256=hashlib.sha256(self.payload).hexdigest())
        self.data["relocations"] = [dict(path="bin/example", offset=65535, width=4,
                                         expected_hex=b"ABCD".hex(), replacement="self")]
        model = Model(self.workspace)
        for path in ("/work/payload", "/work/payload/bin"):
            model.filesystem("setup", "mkdir", dict(path=path, mode=0o755))
        model.filesystem("setup", "create", dict(path="/work/payload/bin/example", mode=0o755))
        model.filesystem("setup", "write", dict(path="/work/payload/bin/example", hex=self.payload.hex()))
        model.save()
        self.manifest()

    def manifest(self):
        seed_input(Model(self.workspace), "/inputs/manifest.json", json.dumps(self.data).encode())

    def call(self, *args, code=0):
        status, stdout, stderr, self.trace = launch(self.workspace, BINARY, list(args))
        self.assertEqual(status, code, stderr.decode(errors="replace"))
        if code:
            self.assertEqual(stdout, b"")
            self.assertTrue(stderr)
            return None
        self.assertEqual(stderr, b"")
        return json.loads(stdout)

    def verify(self, code=0):
        return self.call("artifact", "verify", "/inputs/manifest.json", "--payload", "/work/payload", code=code)

    def test_pack_inspect_and_replay(self):
        verified = self.verify()
        self.assertTrue(verified["posix_modes_verified"])
        canonical = json.dumps(self.data, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(verified["artifact_id"], "sha256:" + hashlib.sha256(canonical).hexdigest())
        packed = self.call("slice", "pack", "/inputs/manifest.json", "/work/payload", "/work/example.slice")
        inspected = self.call("slice", "inspect", "/work/example.slice")
        self.assertEqual(packed["blob_digest"], inspected["blob_digest"])
        self.assertEqual(inspected["artifact_id"], verified["artifact_id"])
        self.assertTrue(inspected["container_verified"])
        self.assertFalse(inspected["authenticated"])
        with Workspace(self.parent / "replay") as workspace:
            self.assertEqual(replay(workspace, BINARY, self.trace), 0)
        self.call("slice", "pack", "/inputs/manifest.json", "/work/payload", "/work/example.slice", code=2)

    def test_modes_and_hardlinks_refused(self):
        model = Model(self.workspace)
        inode = model.state["paths"]["/work/payload/bin/example"]
        model.state["nodes"][inode]["mode"] = 0o644
        model.save()
        self.verify(code=2)
        model.state["nodes"][inode]["mode"] = 0o755
        model.state["paths"]["/work/alias"] = inode
        model.save()
        self.verify(code=2)

    def test_relocation_hash_size_and_unlisted_refusals(self):
        original = copy.deepcopy(self.data)
        for change in (dict(size=len(self.payload)+1), dict(size=len(self.payload)-1), dict(sha256="0"*64)):
            self.data = copy.deepcopy(original)
            self.data["files"][0].update(change)
            self.manifest()
            self.verify(code=2)
        self.data = copy.deepcopy(original)
        self.data["relocations"][0]["expected_hex"] = b"ABCE".hex()
        self.manifest()
        self.verify(code=2)
        self.data = original
        self.manifest()
        model = Model(self.workspace)
        model.filesystem("setup", "create", dict(path="/work/payload/extra"))
        model.save()
        self.verify(code=2)

    def test_input_failure_and_malformed_archive(self):
        seed_input(Model(self.workspace), "/inputs/bad.slice", b"not an archive")
        self.call("slice", "inspect", "/inputs/bad.slice", code=2)
        model = Model(self.workspace)
        model.state["faults"] = [{"tick": model.state["tick"] + 2, "kind": "before"}]
        model.save()
        self.call("artifact", "inspect", "/inputs/manifest.json", code=1)

    def test_resolver_uses_simulated_catalog(self):
        seed_catalogs(Model(self.workspace))
        selected = self.call("dev", "fixture", "resolve", "--catalog", "/inputs/catalog-v1.json", "hello")
        self.assertEqual({p["name"] for p in selected["packages"]}, {"core:hello", "core:greeting"})
        trace = json.loads(self.trace.read_text())
        self.assertTrue(any(r["request"]["operation"] == "read_handle" for r in trace["requests"]))
        self.call("artifact", "inspect", str(ROOT / "tests/fixtures/artifact-manifest.json"), code=2)

    def test_short_reads_continue_until_eof(self):
        model = Model(self.workspace)
        model.state["maximum_read"] = 10000
        model.save()
        self.assertTrue(self.verify()["payload_verified"])

    def test_read_handles_bind_inode_identity_and_access(self):
        model = Model(self.workspace)
        path = "/work/payload/bin/example"
        opened, _ = model.filesystem("reader", "open_read", dict(path=path))
        handle = opened["handle"]
        model.filesystem("setup", "rename", dict(path=path, destination="/work/moved"))
        model.filesystem("setup", "create", dict(path=path))
        read, _ = model.filesystem("reader", "read_handle", dict(handle=handle, offset=65535, length=4))
        self.assertEqual(read, {"hex": b"ABCD".hex()})
        for identity, operation in (("other", "read_handle"), ("reader", "write_handle"),
                                    ("reader", "flush_handle")):
            with self.assertRaises(Refusal):
                model.filesystem(identity, operation, dict(handle=handle, hex="00"))
        model.filesystem("setup", "unlink", dict(path="/work/moved"))
        read, _ = model.filesystem("reader", "read_handle", dict(handle=handle, length=1))
        self.assertEqual(read, {"hex": "78"})
        model.disconnect("reader")
        with self.assertRaises(Refusal):
            model.filesystem("reader", "read_handle", dict(handle=handle))


if __name__ == "__main__":
    unittest.main()
