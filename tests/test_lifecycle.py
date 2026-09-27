"""Compiled CLI lifecycle tests using executable POSIX fixture packages."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == "__main__" else None
FIXTURES = Path(__file__).resolve().parent / "fixtures/prototype"


@unittest.skipIf(BINARY is None or os.name == "nt", "run through CTest on a POSIX host")
class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="aslice-lifecycle-"))
        self.addCleanup(self.cleanup)
        self.prefix = self.directory / "prefix"
        self.catalog = self.directory / "catalog.json"
        self.data = json.loads((FIXTURES / "catalog-v1.json").read_text())
        self.save()
        self.command("init")

    def cleanup(self):
        for base, directories, files in os.walk(self.directory, followlinks=False):
            os.chmod(base, 0o700)
            for name in files:
                path = Path(base) / name
                if not path.is_symlink():
                    os.chmod(path, 0o600)
        shutil.rmtree(self.directory)

    def save(self):
        self.catalog.write_text(json.dumps(self.data))

    def command(self, *args, code=0, failpoint=None):
        environment = os.environ.copy()
        environment.pop("ASLICE_PROTOTYPE_FAILPOINT", None)
        if failpoint:
            environment["ASLICE_PROTOTYPE_FAILPOINT"] = failpoint
        result = subprocess.run([str(BINARY), "dev", "fixture", args[0], "--prefix", str(self.prefix),
                                 "--catalog", str(self.catalog), *args[1:]],
                                capture_output=True, text=True, env=environment, timeout=10)
        self.assertEqual(result.returncode, code, result.stderr)
        if code:
            self.assertEqual(result.stdout, "")
            self.assertTrue(result.stderr)
            return result.stderr
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def program(self, generation=None):
        directory = self.prefix / "profiles" / (f"generations/{generation}" if generation else "default")
        return subprocess.check_output([str(directory / "bin/hello")], text=True)

    def fingerprint(self):
        entries = []
        for path in sorted(self.prefix.rglob("*")):
            if path.is_symlink():
                value = ("link", os.readlink(path))
            elif path.is_file():
                value = ("file", path.read_bytes(), path.stat().st_mode)
            else:
                value = ("dir", path.stat().st_mode)
            entries.append((str(path.relative_to(self.prefix)), value))
        return entries

    def test_install_execute_upgrade_rollback_remove(self):
        self.assertEqual(len(self.command("search", "hello")["packages"]), 1)
        self.assertEqual(self.command("info", "hello")["packages"][0]["version"], "1.0.0")
        before = self.fingerprint()
        self.assertEqual(len(self.command("plan", "hello")["packages"]), 2)
        self.assertEqual(self.fingerprint(), before)
        first = self.command("install", "hello")["generation"]
        self.assertEqual(self.program(), "hello 1.0.0: dependency 1.0.0\n")
        self.assertTrue(self.command("verify")["verified"])
        self.assertEqual(self.command("why", "greeting")["dependents"], ["core:hello"])
        self.assertEqual(self.command("leaves")["packages"], ["core:hello"])
        self.data = json.loads((FIXTURES / "catalog-v2.json").read_text())
        self.save()
        before = self.fingerprint()
        self.command("upgrade", "--dry-run")
        self.assertEqual(self.fingerprint(), before)
        upgraded = self.command("upgrade")["generation"]
        self.assertNotEqual(first, upgraded)
        self.assertEqual(self.program(), "hello 2.0.0: dependency 2.0.0\n")
        self.assertEqual(self.program(first), "hello 1.0.0: dependency 1.0.0\n")
        self.command("rollback", first)
        self.assertEqual(self.program(), "hello 1.0.0: dependency 1.0.0\n")
        self.command("uninstall", "greeting", code=2)
        self.command("uninstall", "hello")
        self.assertEqual(len(self.command("list")["packages"]), 1)
        self.command("autoremove")
        self.assertEqual(self.command("list")["packages"], [])
        self.assertFalse((self.prefix / "profiles/default/bin/hello").exists())
        self.command("rollback", upgraded)
        self.assertEqual(self.program(), "hello 2.0.0: dependency 2.0.0\n")
        self.assertGreaterEqual(len(self.command("history")["generations"]), 5)

    def test_idempotence_and_explicit_dependency(self):
        installed = self.command("install", "hello")
        repeat = self.command("install", "hello")
        self.assertFalse(repeat["changed"])
        self.assertEqual(installed["generation"], repeat["generation"])
        self.command("install", "greeting")
        self.command("uninstall", "hello")
        self.assertFalse(self.command("autoremove")["changed"])
        self.assertTrue(self.command("list")["packages"][0]["requested"])

    def test_solver_backtracks_and_filters_platform(self):
        bad = copy.deepcopy(self.data["packages"][1])
        bad["version"] = "2.0.0"
        bad["dependencies"]["core:greeting"] = "=9.0.0"
        self.data["packages"].append(bad)
        for version, change in [("3.0.0", {"flavor": "v3"}), ("4.0.0", {"min_os": "12"})]:
            candidate = copy.deepcopy(self.data["packages"][1])
            candidate.update(version=version, **change)
            self.data["packages"].append(candidate)
        self.save()
        self.command("install", "hello")
        self.assertEqual(self.program(), "hello 1.0.0: dependency 1.0.0\n")

    def test_conflict_missing_and_cycles_leave_prefix_unchanged(self):
        before = self.fingerprint()
        self.command("install", "missing", code=2)
        self.assertEqual(self.fingerprint(), before)
        self.data["packages"][0]["dependencies"] = {"core:hello": "*"}
        self.save()
        self.assertIn("cycle", self.command("install", "hello", code=2))
        self.assertEqual(self.fingerprint(), before)

    def test_paths_and_collisions_refuse_before_import(self):
        before = self.fingerprint()
        for path in ["../outside", "/outside", "bin/../outside", "bin//hello", "bin/hello/"]:
            self.data["packages"][0]["files"] = {path: {"text": "bad", "executable": False}}
            self.save()
            self.command("install", "hello", code=2)
            self.assertEqual(self.fingerprint(), before)
        for path in ["bin/hello", "bin/HELLO", "bin/hello/child"]:
            self.data["packages"][0]["files"] = {path: {"text": "bad", "executable": False}}
            self.save()
            self.assertIn("collision", self.command("install", "hello", code=2))
            self.assertEqual(self.fingerprint(), before)

    def test_tampering_refuses_verification_and_rollback(self):
        installed = self.command("install", "hello")
        executable = (self.prefix / "profiles/default/bin/hello").resolve()
        executable.chmod(0o700)
        executable.write_text("tampered")
        self.command("verify", code=2)
        self.command("rollback", installed["generation"], code=2)

    def test_activation_failure_boundaries(self):
        old = self.command("list")["generation"]
        self.command("install", "hello", code=1, failpoint="before-switch")
        self.assertEqual(self.command("list")["generation"], old)
        self.command("install", "hello")
        self.assertEqual(self.program(), "hello 1.0.0: dependency 1.0.0\n")
        self.data = json.loads((FIXTURES / "catalog-v2.json").read_text())
        self.save()
        self.command("upgrade", code=1, failpoint="after-switch")
        self.assertEqual(self.program(), "hello 2.0.0: dependency 2.0.0\n")
        self.assertFalse(self.command("upgrade")["changed"])

    def test_busy_prefix_and_no_adoption(self):
        import fcntl
        self.command("init", code=2)
        with (self.prefix / ".lock").open("r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.command("install", "hello", code=4)
        self.assertEqual(self.command("list")["packages"], [])


if __name__ == "__main__":
    unittest.main()
