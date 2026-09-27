"""Exercise the compiled CLI and execute every embedded schema in SQLite."""
from pathlib import Path
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == "__main__" else None
ROOT = Path(__file__).resolve().parents[1]
ROLES = ("client-state", "client-cache", "system-state", "coordinator",
         "publisher", "release-signer")


@unittest.skipIf(BINARY is None, "run through CTest with the compiled binary")
class CliTests(unittest.TestCase):
    def invoke(self, *args):
        # No checkout-relative reads and no prefix creation are needed.
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([str(BINARY), *args], cwd=directory,
                                    capture_output=True, text=True)
            self.assertEqual(list(Path(directory).iterdir()), [])
            return result

    def test_help_and_version(self):
        for args in ((), ("--help",), ("help",), ("--version",)):
            result = self.invoke(*args)
            self.assertEqual(result.returncode, 0)
            self.assertIn("aslice", result.stdout)
            self.assertEqual(result.stderr, "")

    @unittest.skipUnless(os.name == "nt", "Windows runtime linkage check")
    def test_runs_without_toolchain_on_path(self):
        environment = os.environ.copy()
        environment["PATH"] = str(Path(os.environ["SYSTEMROOT"]) / "System32")
        result = subprocess.run([str(BINARY), "--version"], env=environment,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("aslice", result.stdout)

    def test_schemas_match_specification_and_execute(self):
        for role in ROLES:
            with self.subTest(role=role):
                result = self.invoke("db", "schema", "--role", role)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(result.stdout,
                                 (ROOT / "docs/sqlite" / f"{role}.sql").read_text())
                with sqlite3.connect(":memory:") as database:
                    database.executescript(result.stdout)
                    self.assertEqual(database.execute("PRAGMA integrity_check").fetchone(),
                                     ("ok",))
                    self.assertEqual(database.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_default_and_trailing_role(self):
        default = self.invoke("db", "schema")
        explicit = self.invoke("db", "schema", "--role", "client-state")
        self.assertEqual(default.returncode, 0)
        self.assertEqual(explicit.returncode, 0)
        self.assertEqual(default.stdout, explicit.stdout)
        self.assertEqual(default.stdout,
                         self.invoke("db", "--role", "client-state", "schema").stdout)

    def test_refusals_have_no_partial_output(self):
        cases = [("prototype",), ("install", "curl"), ("--version", "extra"),
                 ("db", "schema", "--live"),
                 ("db", "schema", "--json"), ("db", "schema", "schema"),
                 ("db", "schema", "--role"), ("db", "schema", "--role", ""),
                 ("db", "schema", "--role", "unknown"),
                 ("db", "--role", "client-state", "schema", "--role", "publisher"),
                 ("db", "schema", "--prefix", "/tmp/aslice")]
        for args in cases:
            with self.subTest(args=args):
                result = self.invoke(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("--help", result.stderr)


if __name__ == "__main__":
    unittest.main()
