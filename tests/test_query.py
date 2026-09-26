"""Adversarial integration tests against the compiled, pinned SQLite query engine."""
import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

BINARY = Path(sys.argv.pop(1)).resolve() if __name__ == "__main__" else None
ROOT = Path(__file__).resolve().parents[1]
INSTANCE = "a" * 32
OWNER = "test-owner:fixture"
ROLES = ("client-state", "client-cache", "system-state", "coordinator", "publisher", "release-signer")


@unittest.skipIf(BINARY is None, "run through CTest with the compiled query driver")
class QueryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "snapshot.sqlite"
        self.fixture()

    def fixture(self, role="client-state"):
        self.path.unlink(missing_ok=True)
        with closing(sqlite3.connect(self.path)) as db:
            db.executescript((ROOT / "docs/sqlite" / f"{role}.sql").read_text())
            db.execute("INSERT INTO database_identity VALUES(1,?,?,?,?)",
                       (role, INSTANCE, OWNER, 3 if role in ("client-cache", "coordinator") else 2))
            db.executescript("CREATE TABLE sample(value); INSERT INTO sample VALUES(1),(2);"
                             "CREATE VIEW safe_view AS SELECT value FROM sample;"
                             "CREATE VIEW unsafe_view AS SELECT random() AS value;")
            db.commit()
            # Owner-produced standalone snapshot, not raw bytes of a WAL database.
            db.execute("PRAGMA journal_mode=DELETE")

    def run_query(self, sql, *, role="client-state", instance=INSTANCE, owner=OWNER,
                  rows=10000, output=16*1024*1024, timeout=5000):
        before = hashlib.sha256(self.path.read_bytes()).digest()
        result = subprocess.run([str(BINARY), str(self.path), role, instance, owner, "--stdin-sql",
                                 str(rows), str(output), str(timeout)],
                                input=sql, capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).digest(), before)
        self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()), [self.path.name])
        return result

    def ok(self, sql, **kwargs):
        result = self.run_query(sql, **kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        data = json.loads(result.stdout)
        self.assertFalse(data["truncated"])
        return data

    def refused(self, sql, code=None, **kwargs):
        result = self.run_query(sql, **kwargs)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        if code:
            self.assertTrue(result.stderr.startswith(code + ":"), result.stderr)

    def test_pinned_sqlite(self):
        result = subprocess.run([str(BINARY), "--sqlite-version"], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.splitlines(), ["3.51.3",
            "2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618"])

    def test_all_role_schemas(self):
        for role in ROLES:
            with self.subTest(role=role):
                self.fixture(role)
                self.assertEqual(self.ok("SELECT role FROM database_identity", role=role)["rows"], [[role]])

    def test_values_and_duplicate_columns(self):
        data = self.ok("SELECT NULL AS x, 42 AS x, 9007199254740992 AS x, "
                       "-9223372036854775808 AS x, 1.25 AS x, x'00ff10' AS x, x'' AS x, "
                       "'a\"\\' AS x, CAST(x'610062' AS TEXT) AS x, 'ไทย😀' AS x")
        self.assertEqual(data["columns"], ["x"] * 10)
        self.assertEqual(data["rows"], [[None, 42, "9007199254740992", "-9223372036854775808",
                         1.25, {"bytes": "AP8Q"}, {"bytes": ""}, 'a"\\', 'a\0b', 'ไทย😀']])

    def test_select_cte_view_and_functions(self):
        self.assertEqual(self.ok("SELECT sum(value) AS total FROM safe_view;")["rows"], [[3]])
        self.assertEqual(self.ok("WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<4) SELECT x FROM n")["rows"], [[1], [2], [3], [4]])
        self.assertEqual(self.ok("SELECT UPPER('hello'), count(*) FROM sample")["rows"], [["HELLO", 2]])
        self.assertEqual(self.ok("SELECT value FROM sample WHERE 0")["rows"], [])

    def test_unsafe_queries(self):
        for sql in ["DELETE FROM sample", "UPDATE sample SET value=9", "INSERT INTO sample VALUES(3)",
                    "CREATE TABLE bad(x)", "DROP TABLE sample", "VACUUM", "REINDEX", "ANALYZE",
                    "ATTACH ':memory:' AS bad", "DETACH main", "BEGIN", "COMMIT", "ROLLBACK",
                    "SAVEPOINT bad", "PRAGMA user_version", "PRAGMA journal_mode=WAL",
                    "SELECT * FROM pragma_table_info('sample')", "SELECT load_extension('bad')",
                    "SELECT readfile('/etc/passwd')", "SELECT writefile('/tmp/bad','x')",
                    "SELECT random()", "SELECT value FROM unsafe_view", "SELECT 1; SELECT 2",
                    "SELECT 1; -- non-whitespace tail", "SELECT ?", "SELECT :value",
                    "EXPLAIN SELECT 1", "EXPLAIN QUERY PLAN SELECT 1", "", "-- comment only"]:
            with self.subTest(sql=sql):
                self.refused(sql)

    def test_identity_refusals(self):
        for kwargs in [dict(role="publisher"), dict(role="unknown"), dict(instance="b"*32),
                       dict(instance=""), dict(owner="other"), dict(owner="")]:
            with self.subTest(kwargs=kwargs):
                self.refused("SELECT 1", "identity_mismatch", **kwargs)
        for statement in ["PRAGMA application_id=0", "PRAGMA user_version=99",
                          "DELETE FROM database_identity",
                          "ALTER TABLE database_identity RENAME TO hidden; CREATE VIEW database_identity AS SELECT * FROM hidden"]:
            self.fixture()
            with closing(sqlite3.connect(self.path)) as db:
                db.executescript(statement)
            self.refused("SELECT 1", "identity_mismatch")

    def test_limits_discard_partial_rows(self):
        self.refused("SELECT value FROM sample", "query_limit", rows=1)
        self.refused("SELECT value FROM sample", "query_limit", output=45)
        self.refused("SELECT 1", "query_timeout", timeout=0)
        self.refused("WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n) SELECT sum(x) FROM n",
                     "query_timeout", timeout=10)
        self.refused("WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<10001) SELECT x FROM n",
                     "query_limit", rows=20000)
        self.refused("SELECT '" + "a" * 65536 + "'", "query_refused")
        self.refused("SELECT 1\0; SELECT 2", "query_refused")

    def test_invalid_values(self):
        self.refused("SELECT CAST(x'ff' AS TEXT)", "invalid_text")
        self.refused("SELECT 1e999", "invalid_number")

    def test_output_boundary_and_hard_ceiling(self):
        result = self.run_query("SELECT 1")
        size = len(result.stdout.rstrip("\n").encode())
        self.ok("SELECT 1", output=size)
        self.refused("SELECT 1", "query_limit", output=size-1)
        sql = ("WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<5000) "
               "SELECT '" + "a"*4096 + "' FROM n")
        self.refused(sql, "query_limit", output=32*1024*1024)

    def test_malformed_snapshot(self):
        for content in [b"", b"not a sqlite database", b"SQLite format 3\0" + b"\0"*100]:
            with self.subTest(size=len(content)):
                self.path.write_bytes(content)
                self.refused("SELECT 1")


if __name__ == "__main__":
    unittest.main()
