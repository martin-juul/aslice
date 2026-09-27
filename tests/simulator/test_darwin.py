"""Host image preparation tests, not Darwin execution or isolation evidence."""

import copy
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.simulator import darwin
from tools.simulator.corpus import macho_uuid, verify
from tools.simulator.corpus_fetch import download
from tools.simulator.model import atomic_json


def identity():
    return {
        "version": 1,
        "guest": "ubuntu-26.04-x86_64",
        "darling_commit": darwin.DARLING_COMMIT,
        "submodules": {"test-only": "1" * 40},
        "artifacts": {"test-only": "2" * 64},
        "build": {
            key: "test fixture, not runtime evidence"
            for key in ("compiler", "packages", "command", "source_tree")
        },
    }


class StoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.root = self.directory / "store"
        self.image = self.directory / "base.raw"
        self.image.write_bytes(b"test base")
        self.runtime = self.directory / "runtime.json"
        atomic_json(self.runtime, identity())
        self.commands = []

        def run(command, **kwargs):
            self.commands.append(command)
            if command[1] == "info":
                return subprocess.CompletedProcess(
                    command, 0, json.dumps({"format": "raw", "virtual-size": 4096})
                )
            Path(command[-2]).write_bytes(b"test disk")
            return subprocess.CompletedProcess(command, 0, "")

        self.addCleanup(patch.stopall)
        patch("tools.simulator.darwin.subprocess.run", side_effect=run).start()

    def create(self, store):
        return store.create("alpha", self.image, self.runtime)

    def test_create_snapshot_restore_clone_delete_restart(self):
        with darwin.Machines(self.root) as store:
            first = self.create(store)
            self.assertEqual(
                (first["cpus"], first["memory_mib"], first["disk_gib"]), (4, 8192, 64)
            )
            self.assertFalse(first["network"])
            self.assertFalse(first["runtime_validated"])
            self.assertEqual(first["host_mounts"], [])
            store.snapshot("alpha", "initial")
            active = store.directory("alpha") / first["disk"]
            active.write_bytes(b"changed disk")
            restored = store.snapshot("alpha", "initial", restore=True)
            self.assertEqual(active.read_bytes(), b"changed disk")
            self.assertEqual(
                (store.directory("alpha") / restored["disk"]).read_bytes(), b"test disk"
            )
            cloned = store.clone("alpha", "beta")
            self.assertEqual(cloned["base"], restored["base"])
            self.assertNotEqual(cloned["disk"], restored["disk"])
            deleted = store.delete("alpha")
            self.assertTrue(Path(deleted["retained_at"]).is_dir())
        with darwin.Machines(self.root) as store:
            self.assertEqual(
                [item["name"] for item in store.status()["machines"]], ["beta"]
            )

    def test_live_snapshot_and_clone_refused(self):
        with darwin.Machines(self.root) as store:
            data = self.create(store)
            data["state"] = "running"
            atomic_json(store.directory("alpha") / "machine.json", data)
            for action in (
                lambda: store.snapshot("alpha", "bad"),
                lambda: store.snapshot("alpha", "bad", restore=True),
                lambda: store.clone("alpha", "beta"),
                lambda: store.delete("alpha"),
            ):
                with self.assertRaisesRegex(ValueError, "stopped"):
                    action()

    def test_restore_hash_mismatch_keeps_active_disk(self):
        with darwin.Machines(self.root) as store:
            data = self.create(store)
            store.snapshot("alpha", "initial")
            (store.directory("alpha") / "snapshots/initial/disk.qcow2").write_bytes(
                b"tampered"
            )
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                store.snapshot("alpha", "initial", restore=True)
            self.assertEqual(store.read("alpha"), data)
            self.assertTrue((store.directory("alpha") / data["disk"]).exists())

    def test_runtime_mismatch_refuses_restore(self):
        with darwin.Machines(self.root) as store:
            self.create(store)
            store.snapshot("alpha", "initial")
            manifest = store.directory("alpha") / "snapshots/initial/snapshot.json"
            data = json.loads(manifest.read_text())
            data["runtime_sha256"] = "0" * 64
            atomic_json(manifest, data)
            with self.assertRaisesRegex(ValueError, "identities"):
                store.snapshot("alpha", "initial", restore=True)

    def test_base_mutation_refused(self):
        with darwin.Machines(self.root) as store:
            data = self.create(store)
            (self.root / "bases" / data["base"] / "image").write_bytes(b"changed base")
            with self.assertRaisesRegex(ValueError, "base image identity"):
                store.clone("alpha", "beta")

    def test_interrupted_copy_never_activates(self):
        with darwin.Machines(self.root) as store:
            self.create(store)
            with patch(
                "tools.simulator.darwin.shutil.copyfileobj",
                side_effect=OSError("disk full"),
            ):
                with self.assertRaisesRegex(OSError, "disk full"):
                    store.clone("alpha", "beta")
            self.assertFalse((store.directory("beta") / "machine.json").exists())
            self.assertTrue(any(store.directory("beta").glob("*.partial")))
            states = {
                item["name"]: item["state"] for item in store.status()["machines"]
            }
            self.assertEqual(states["beta"], "incomplete")
            self.assertEqual(states["alpha"], "stopped")

    def test_names_and_foreign_store_refused(self):
        for value in ("../escape", "CON", "con", "nul", "x/y", "x:y", "", "a" * 49):
            with self.assertRaises(ValueError):
                darwin.name(value)
        self.root.mkdir()
        (self.root / "foreign").write_text("keep")
        with self.assertRaises(ValueError):
            with darwin.Machines(self.root):
                pass

    def test_concurrent_process_and_crash_recovery(self):
        # Popen is intentionally real. The lease must work across processes.
        script = (
            "import os,sys; from tools.simulator.darwin import Machines; "
            "m=Machines(sys.argv[1]); m.__enter__(); "
            "op=m.operation('crash-test','alpha'); op.__enter__(); os._exit(19)"
        )
        with darwin.Machines(self.root):
            peer = subprocess.Popen(
                [sys.executable, "-c", script, str(self.root)],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _, stderr = peer.communicate(timeout=10)
            self.assertNotEqual(peer.returncode, 19, stderr)
            self.assertNotEqual(peer.returncode, 0)
        peer = subprocess.Popen(
            [sys.executable, "-c", script, str(self.root)], cwd=ROOT
        )
        self.assertEqual(peer.wait(timeout=10), 19)
        with darwin.Machines(self.root) as store:
            self.assertIn("interrupted", store.status()["operations"][0]["outcome"])

    def test_runtime_and_resource_validation_before_creation(self):
        with darwin.Machines(self.root) as store:
            with self.assertRaises(ValueError):
                store.create("alpha", self.image, self.runtime, cpus=0)
            data = identity()
            data["darling_commit"] = "master"
            atomic_json(self.runtime, data)
            with self.assertRaises(ValueError):
                self.create(store)
            self.assertEqual(store.status()["machines"], [])


class CorpusTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for filename in ("source.c", "LICENSE"):
            (self.root / filename).write_text("test identity fixture")
        for filename, kind in (("binary", 2), ("symbols", 10)):
            (self.root / filename).write_bytes(
                struct.pack("<8I", 0xFEEDFACF, 0x01000007, 3, kind, 1, 24, 0, 0)
                + struct.pack("<2I", 0x1B, 24)
                + b"x" * 16
            )

        def artifact(filename):
            return {"path": filename, "sha256": darwin.sha256(self.root / filename)}

        self.entry = {
            "role": "debugger",
            "binary": artifact("binary"),
            "symbols": artifact("symbols"),
            "source": artifact("source.c"),
            "license": artifact("LICENSE"),
            "build": {
                "host": "macOS",
                "compiler": "fixture",
                "sdk": "fixture",
                "command": "fixture",
            },
            "expected": "test fixture only",
        }

    def verify_entry(self, entry=None):
        manifest = self.root / "corpus.json"
        atomic_json(manifest, {"version": 1, "entries": [entry or self.entry]})
        return verify(manifest)

    def test_matching_symbols_does_not_grant_acceptance(self):
        result = self.verify_entry()
        self.assertFalse(result["complete"])
        self.assertFalse(result["entries"][0]["provenance_verified"])
        self.assertEqual(result["entries"][0]["execution"], "pending")
        self.assertEqual(result["missing_roles"], ["cli", "cocoa", "document"])

    def test_darling_build_is_only_infrastructure(self):
        self.entry["build"]["host"] = "Darling"
        self.assertFalse(self.verify_entry()["entries"][0]["compatibility_candidate"])

    def test_wrong_hash_symbols_and_traversal(self):
        for change in ("hash", "symbols", "traversal"):
            entry = copy.deepcopy(self.entry)
            if change == "hash":
                entry["binary"]["sha256"] = "0" * 64
            elif change == "symbols":
                path = self.root / "symbols"
                data = path.read_bytes()
                path.write_bytes(data[:-16] + b"y" * 16)
                entry["symbols"]["sha256"] = darwin.sha256(path)
            else:
                entry["source"]["path"] = "../source.c"
            with self.assertRaises(ValueError):
                self.verify_entry(entry)

    def test_malformed_macho_refused(self):
        binary = self.root / "binary"
        for data in (
            b"\x7fELF",
            struct.pack("<8I", 0xFEEDFACF, 0x01000007, 3, 2, 1, 8, 0, 0)
            + struct.pack("<2I", 0x1B, 0),
        ):
            binary.write_bytes(data)
            with self.assertRaises(ValueError):
                macho_uuid(binary)


class PreflightTests(unittest.TestCase):
    def test_base_backing_paths_are_not_followed(self):
        with patch("tools.simulator.darwin.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess(
                [],
                0,
                json.dumps(
                    {
                        "format": "qcow2",
                        "virtual-size": 4096,
                        "backing-filename": "/outside",
                    }
                ),
            )
            with self.assertRaisesRegex(ValueError, "standalone"):
                darwin.image_info(Path("base.qcow2"))
            self.assertNotIn("--backing-chain", run.call_args.args[0])

    def test_provisioning_download_refuses_wrong_hash_or_oversize(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "artifact"
            with patch(
                "tools.simulator.corpus_fetch.urllib.request.urlopen",
                return_value=io.BytesIO(b"wrong"),
            ):
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    download("https://example.invalid", "0" * 64, destination)
            self.assertFalse(destination.exists())
            self.assertTrue(destination.with_suffix(".partial").exists())
            destination = Path(temporary) / "large"
            with patch(
                "tools.simulator.corpus_fetch.urllib.request.urlopen",
                return_value=io.BytesIO(b"too large"),
            ), patch("tools.simulator.corpus_fetch.MAX_DOWNLOAD", 2):
                with self.assertRaisesRegex(ValueError, "exceeds"):
                    download("https://example.invalid", "0" * 64, destination)
            self.assertFalse(destination.exists())

    def test_missing_qemu_is_explicit_and_no_automatic_software_fallback(self):
        with patch("tools.simulator.darwin.shutil.which", return_value=None):
            result = darwin.preflight()
        self.assertFalse(result["infrastructure_ready"])
        self.assertFalse(result["complete"])
        self.assertFalse(result["software_emulation"])
        self.assertIn("missing executable: qemu-img", result["blockers"])


@unittest.skipUnless(
    shutil.which("qemu-img"), "QEMU image integration unavailable: qemu-img missing"
)
class QemuImageTests(unittest.TestCase):
    def test_actual_overlay_snapshot_clone_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root / "base.raw"
            with base.open("wb") as stream:
                stream.truncate(1024 * 1024)
            runtime = root / "runtime.json"
            atomic_json(runtime, identity())
            with darwin.Machines(root / "store") as store:
                data = store.create("alpha", base, runtime, disk_gib=1)
                active = store.directory("alpha") / data["disk"]
                info = json.loads(
                    subprocess.check_output(
                        ["qemu-img", "info", "--output=json", str(active)]
                    )
                )
                self.assertEqual(info["virtual-size"], 1024**3)
                self.assertEqual(info["format"], "qcow2")
                store.snapshot("alpha", "initial")
                store.clone("alpha", "beta")
                restored = store.snapshot("alpha", "initial", restore=True)
                subprocess.run(
                    [
                        "qemu-img",
                        "check",
                        str(store.directory("alpha") / restored["disk"]),
                    ],
                    check=True,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
