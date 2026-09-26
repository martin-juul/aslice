"""Executable specification models, not aslice runtime or power-loss tests."""
from pathlib import Path
import hashlib
import json
import re
import sqlite3
import tempfile
import unittest
import time

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / 'docs/sqlite'
V2_SCHEMAS = ROOT / 'tests/fixtures/database-v2'
VERSIONS = {'coordinator': 3, 'client-cache': 3}

ROLES = ('client-state', 'client-cache', 'system-state', 'coordinator', 'publisher', 'release-signer')
# Hashes of the reviewed version-1 DDL, ignoring comments/whitespace and the
# explicit auto_vacuum default. Prevent derived fixtures from silently drifting.
V1_SCHEMA_HASHES = dict(zip(ROLES, (
    'da810f286d155e6f01b8c3863c8cd2ea39138080228c54ae6306cfc5b4e61e8f',
    'cd5cf7076883b6346c20b4034028e122e60cd89df3bc62bb92ea5241f1bfaf69',
    'daec6740b1f3cc2c4f7a38f3d771408e0898bd7fb1a44abdff45577a2dbb25db',
    '7e311ac91d4a28860d8485525b3b43133a1b53d0bd4d63c152f06322c8845d88',
    '46cd1420b674a82ebb4fa7a9b019bde555b4a41d9e5911e5d35f7fa9371874ce',
    'dde160330b7f704ba5ed5088c844d5050fdec4d1661009c0d6b89d682a8f8068',
)))


def digest(value):
    return 'sha256:' + hashlib.sha256(value.encode()).hexdigest()


def obj(db, value):
    key = digest(value)
    db.execute('INSERT OR IGNORE INTO objects VALUES(?,?,?)', (key, len(value.encode()), 'fixture'))
    return key


def insert(db, table, *values):
    db.execute(f'INSERT INTO {table} VALUES({",".join("?" for _ in values)})', values)


def candidate(db, env='prod', name='candidate', inventory='inventory', repo='core'):
    key = obj(db, name)
    insert(db, 'candidates', repo, env, key, obj(db, inventory), None, obj(db, 'authorization'))
    return key


def populate(db, role):
    a, b, c = [obj(db, x) for x in ('a', 'b', 'c')]
    if role == 'client-state':
        for ident, name in ((a, 'python'), (b, 'openssl')):
            insert(db, 'artifacts', 'core', 'prod', ident, 'a' * 64, name, '1', 'slice', c, c, c)
        insert(db, 'bindings', 'core', 'prod', a, 'core', 'openssl', 'prod', b)
        insert(db, 'profiles', 'default')
        insert(db, 'profile_priorities', 'default', 'python', 'core', 'prod', 'python')
        insert(db, 'generations', 'default', 1, c)
        insert(db, 'active_generations', 'default', 1)
        insert(db, 'members', 'default', 1, 'core', 'prod', 'python', a)
        insert(db, 'requests', 'default', 'core', 'prod', 'python', 1)
        insert(db, 'holds', 'default', 'core', 'python', 'fixture')
        insert(db, 'runtime_defaults', 'default', 'python', '3.14')
        insert(db, 'gc_roots', 'process', 'lease', 'core', 'prod', b, 100)
        insert(db, 'history', 'b' * 32, 1, 'install', 0, 'committed', None, c, c)
    elif role == 'client-cache':
        insert(db, 'snapshots', 'core', 'prod', a, b, 100, 0, 0, 0)
        insert(db, 'current_snapshots', 'core', 'prod', a)
        insert(db, 'packages', 'core', 'prod', a, 'python', b, c, 'Interpreter')
        insert(db, 'solve_cache', b, c, 'model-1', 0, 0, 0)
        insert(db, 'solve_inputs', b, 'core', 'prod', a)
        insert(db, 'trust_projections', 'core', 'prod', c)
    elif role == 'system-state':
        insert(db, 'closures', a, c)
        insert(db, 'closure_members', a, 'core', 'prod', b)
        insert(db, 'prefixes', 'a' * 32, '/opt/aslice', 501)
        insert(db, 'prefix_references', 'a' * 32, a, 'active')
        insert(db, 'effects', 'service', 'a' * 32, a, '/Library/LaunchDaemons/test.plist', b, c, b, 'applied')
        insert(db, 'services', 'test', 'service', a, c)
        insert(db, 'recovery_receipts', 'a' * 32, c, 'committed')
    elif role == 'coordinator':
        insert(db, 'plans', a, 'core', 'prod', 'git-fixture', c)
        insert(db, 'job_kinds' if db.execute('PRAGMA user_version').fetchone()[0] == 3 else 'lanes', 'build')
        insert(db, 'workers', 'worker', c, 1)
        insert(db, 'worker_capabilities', 'worker', 'v1', c)
        insert(db, 'jobs', b, 'core', 'prod', a, 'build', 'leased')
        insert(db, 'jobs', c, 'core', 'prod', a, 'build', 'queued')
        insert(db, 'job_requirements', b, 'v1')
        insert(db, 'job_dependencies', a, c, b)
        insert(db, 'attempts', b, 1, 'worker', 'token', 100, 'active')
        insert(db, 'quarantine', b, 1, 'hold', c)
        insert(db, 'gate_evidence', b, 'test', 'pending', None)
    elif role == 'publisher':
        key = candidate(db)
        insert(db, 'publication_queue', 'core', 'prod', 1, key, 'release', 'ready')
        insert(db, 'fencing', 'core', 'prod', 1, 'publisher', 100, None)
        insert(db, 'timestamp_reservations', 'core', 'prod', 1, key, a, 'signed', b)
        insert(db, 'activations', 'core', 'prod', key, 1, 1, b, c)
        insert(db, 'acknowledgements', 'core', 'prod', key, c)
        dev = candidate(db, 'dev', 'dev-candidate')
        stage = candidate(db, 'staging', 'stage-candidate')
        insert(db, 'promotions', 'core', 'dev', 'staging', dev, stage, digest('inventory'), c)
    else:
        key = candidate(db)
        for metadata_role in ('targets', 'snapshot'):
            insert(db, 'reservations', 'core', 'prod', metadata_role, 1, key, a, 'signed')
            insert(db, 'signed_metadata', 'core', 'prod', metadata_role, 1, key, b)
        insert(db, 'signing_outcomes', 'core', 'prod', key, 'signed', c)
        insert(db, 'slice_signatures', 'core', 'prod', key, a, b)
        insert(db, 'publication_acknowledgements', 'core', 'prod', key, b, c)
    db.commit()


class DatabaseSchemas(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aslice-db-model-')
        self.directory = Path(self.temp.name)
        self.connections = []

    def tearDown(self):
        for db in self.connections:
            db.close()
        self.temp.cleanup()

    def create(self, role, fixture=True, suffix='', version=None):
        db = sqlite3.connect(self.directory / (role + suffix + '.sqlite'))
        self.connections.append(db)
        ddl_root = V2_SCHEMAS if version == 2 else SCHEMAS
        db.executescript((ddl_root / (role + '.sql')).read_text(encoding='utf-8'))
        insert(db, 'database_identity', 1, role, 'a' * 32, 'owner-fixture', db.execute('PRAGMA user_version').fetchone()[0])
        for repo in ('core', 'other'):
            for env in ('dev', 'staging', 'prod'):
                insert(db, 'scopes', repo, env)
        if fixture:
            populate(db, role)
        db.commit()
        return db

    def reject(self, db, sql, parameters=()):
        db.execute('SAVEPOINT rejection')
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(sql, parameters)
        finally:
            db.execute('ROLLBACK TO rejection')
            db.execute('RELEASE rejection')

    def test_every_schema_fixture_view_and_documented_query(self):
        queries = re.findall(r'```sql\n(.*?)```', (ROOT / 'docs/DATABASE.md').read_text(encoding='utf-8'), re.S)
        self.assertEqual(len(queries), 6)
        for index, role in enumerate(ROLES):
            with self.subTest(role=role):
                db = self.create(role)
                self.assertEqual(db.execute('PRAGMA application_id').fetchone()[0], 1095977985 + index)
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], VERSIONS.get(role, 2))
                self.assertEqual(db.execute('PRAGMA auto_vacuum').fetchone(), (0,))
                self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
                self.assertEqual(db.execute('PRAGMA synchronous').fetchone()[0], 1 if role == 'client-cache' else 2)
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchall(), [('ok',)])
                for (view,) in db.execute("SELECT name FROM sqlite_schema WHERE type='view'"):
                    self.assertTrue(db.execute(f'SELECT * FROM {view}').fetchall(), view)
                self.assertTrue(db.execute(queries[index], {'now': 101}).fetchall())

    def test_invalid_common_identities_and_lengths(self):
        for role in ROLES:
            db = self.create(role)
            for value in ('sha256:abc', 'a' * 71, 'sha256:' + 'A' * 64, 'sha256:' + 'g' * 64,
                          digest('valid') + '\x00trailer', 'sha256:' + 'a' * 63 + '\x00'):
                self.reject(db, 'INSERT INTO objects VALUES(?,0,?)', (value, 'invalid'))
            self.reject(db, 'INSERT INTO objects VALUES(?,-1,?)', (digest('negative'), 'invalid'))
            self.reject(db, 'INSERT INTO scopes VALUES(?,?)', ('bad/name', 'prod'))
            self.reject(db, 'INSERT INTO scopes VALUES(?,?)', ('core\x00other', 'prod'))
            self.reject(db, 'INSERT INTO scopes VALUES(?,?)', ('core', 'production'))
            self.reject(db, "UPDATE database_identity SET role='wrong'")
            self.reject(db, "UPDATE database_identity SET instance_id='bad'")
            self.reject(db, 'UPDATE replay_head SET sequence=1')

    def test_client_bindings_and_generation_scope(self):
        db = self.create('client-state')
        a, b = digest('a'), digest('b')
        self.reject(db, 'INSERT INTO bindings SELECT * FROM bindings')
        self.reject(db, 'UPDATE bindings SET dependency_artifact=?', (digest('absent'),))
        self.reject(db, "UPDATE bindings SET dependency_environment='dev'")
        self.reject(db, "UPDATE members SET repository='other'")
        self.reject(db, 'UPDATE active_generations SET generation=2')
        self.reject(db, "UPDATE artifacts SET build_id='bad'")
        self.reject(db, 'INSERT INTO profile_priorities SELECT * FROM profile_priorities')
        self.assertEqual({row[2] for row in db.execute('SELECT * FROM retained_artifacts')}, {a, b})
        db.execute('DELETE FROM gc_roots')
        self.assertEqual({row[2] for row in db.execute('SELECT * FROM retained_artifacts')}, {a, b})

    def test_cache_and_system_foreign_keys(self):
        db = self.create('client-cache')
        self.reject(db, "UPDATE packages SET environment='dev'")
        self.reject(db, "UPDATE solve_inputs SET repository='other'")
        db = self.create('system-state')
        self.reject(db, "UPDATE prefix_references SET prefix_id=?", ('b' * 32,))
        self.reject(db, 'UPDATE services SET closure_digest=?', (digest('b'),))

    def test_coordinator_dependencies_and_gates(self):
        db = self.create('coordinator')
        self.reject(db, "UPDATE jobs SET environment='dev'")
        self.reject(db, 'UPDATE job_dependencies SET dependency_digest=?', (digest('absent'),))
        self.reject(db, 'UPDATE job_dependencies SET dependency_digest=job_digest')
        self.reject(db, "UPDATE gate_evidence SET verdict='pass'")
        self.reject(db, "INSERT INTO attempts SELECT job_digest,2,worker_id,'second',200,'active' FROM attempts")

    def test_reservations_and_promotion_scope(self):
        db = self.create('publisher')
        self.reject(db, 'INSERT INTO timestamp_reservations SELECT * FROM timestamp_reservations')
        self.reject(db, "UPDATE publication_queue SET environment='dev'")
        self.reject(db, "UPDATE promotions SET repository='other'")
        self.reject(db, "UPDATE promotions SET source_environment='prod'")
        different = candidate(db, 'staging', 'different', 'changed-content')
        self.reject(db, 'UPDATE promotions SET destination_candidate=?', (different,))
        another = candidate(db, name='another')
        self.reject(db, 'UPDATE activations SET candidate_digest=?', (another,))
        db = self.create('release-signer')
        self.reject(db, 'INSERT INTO reservations SELECT * FROM reservations')
        self.reject(db, "UPDATE signed_metadata SET repository='other'")
        self.reject(db, "UPDATE signed_metadata SET environment='dev'")
        self.reject(db, 'UPDATE reservations SET version=0')
        self.assertEqual(db.execute('SELECT version FROM version_high_water').fetchall(), [(1,), (1,)])

    def test_expired_lease_and_duplicate_results(self):
        db = self.create('coordinator')
        job = digest('b')
        # Recovery expires all inherited leases, regardless of restored expiry.
        with db:
            db.execute("UPDATE attempts SET state='expired' WHERE state='active'")
            db.execute("UPDATE jobs SET state='queued' WHERE state='leased'")
            insert(db, 'attempts', job, 2, 'worker', 'replacement', 200, 'active')
        def admit(attempt, value):
            existing = db.execute('SELECT result_digest FROM results WHERE job_digest=?', (job,)).fetchone()
            if existing:
                if existing[0] != value:
                    insert(db, 'quarantine', job, 2, 'hold', value)
                    db.execute("UPDATE jobs SET state='quarantined' WHERE job_digest=?", (job,))
                    raise ValueError('conflicting result')
                return 'duplicate'
            state = db.execute('SELECT state,expires_at FROM attempts WHERE job_digest=? AND attempt=?', (job, attempt)).fetchone()
            if state != ('active', 200):
                raise ValueError('expired lease')
            insert(db, 'results', job, attempt, value)
            db.execute("UPDATE attempts SET state='returned' WHERE job_digest=? AND attempt=?", (job, attempt))
            return 'accepted'
        with self.assertRaisesRegex(ValueError, 'expired'):
            admit(1, digest('a'))
        self.assertEqual(admit(2, digest('a')), 'accepted')
        self.assertEqual(admit(2, digest('a')), 'duplicate')
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            admit(2, digest('c'))
        self.assertEqual(db.execute('SELECT COUNT(*) FROM results').fetchone()[0], 1)
        self.assertEqual(db.execute("SELECT decision FROM quarantine ORDER BY sequence DESC LIMIT 1").fetchone()[0], 'hold')

    def test_replay_choices_history_idempotency_and_conflicts(self):
        db = self.create('client-state', fixture=False)
        records = choice_records()
        replay(db, records)
        expected = choices(db)
        replay(db, records)
        self.assertEqual(choices(db), expected)
        rebuilt = self.create('client-state', fixture=False, suffix='-rebuilt')
        replay(rebuilt, records)
        self.assertEqual(choices(rebuilt), expected)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM generations').fetchone()[0], 0)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM history').fetchone()[0], 3)
        missing = self.create('client-state', fixture=False, suffix='-gap')
        with self.assertRaisesRegex(ValueError, 'gap'):
            replay(missing, records[1:])
        altered = dict(records[1], command='unpin')
        with self.assertRaisesRegex(ValueError, 'conflict'):
            replay(db, [altered])
        broken = [dict(records[0], previous=digest('bad'))]
        with self.assertRaisesRegex(ValueError, 'predecessor'):
            replay(missing, broken)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            replay(missing, [dict(records[0], phase='prepared')])
        with self.assertRaisesRegex(ValueError, 'identity'):
            replay(missing, [dict(records[0], instance_id='b' * 32)])
        with self.assertRaisesRegex(ValueError, 'after-state'):
            replay(missing, [dict(records[0], after=digest('tampered'))])

    def test_signer_rebuild_retains_unpublished_consumed_reservations(self):
        original = self.create('release-signer', fixture=False)
        rebuilt = self.create('release-signer', fixture=False, suffix='-rebuilt')
        # Durable allocation evidence consumes a number before a signature exists.
        retained = [('first', 4, 'consumed'), ('second', 5, 'reserved')]
        for db in (original, rebuilt):
            for name, version, state in retained:
                key = candidate(db, name=name)
                insert(db, 'reservations', 'core', 'prod', 'snapshot', version, key, obj(db, name + '-bytes'), state)
            db.commit()
        self.assertEqual(original.execute('SELECT * FROM version_high_water').fetchall(),
                         rebuilt.execute('SELECT * FROM version_high_water').fetchall())
        self.assertEqual(rebuilt.execute('SELECT version FROM version_high_water').fetchone()[0], 5)
        self.assertEqual(rebuilt.execute('SELECT COUNT(*) FROM signed_metadata').fetchone()[0], 0)
        self.reject(rebuilt, 'INSERT INTO reservations SELECT * FROM reservations WHERE version=4')

    def test_backup_manifest_damage_and_missing_evidence(self):
        db = self.create('client-state')
        snapshot = self.directory / 'snapshot.sqlite'
        destination = sqlite3.connect(snapshot)
        db.backup(destination)
        destination.close()
        evidence = self.directory / 'retained-record.json'
        evidence.write_bytes(b'{"fixture":"retained"}')
        manifest = {p.name: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size)
                    for p in (snapshot, evidence)}
        def verify():
            for name, expected in manifest.items():
                p = self.directory / name
                if not p.is_file():
                    raise ValueError('missing evidence')
                if (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size) != expected:
                    raise ValueError('damaged evidence')
        verify()
        evidence.write_bytes(b'{"fixture":"modified"}')
        with self.assertRaisesRegex(ValueError, 'damaged'):
            verify()
        evidence.rename(self.directory / 'preserved-damaged-record.json')
        with self.assertRaisesRegex(ValueError, 'missing'):
            verify()
        self.assertEqual(db.execute('PRAGMA integrity_check').fetchone(), ('ok',))

    def test_backup_restore_stale_refusal_and_copy_migration(self):
        db = self.create('client-state', fixture=False)
        records = choice_records()
        replay(db, records[:1])
        backup = sqlite3.connect(self.directory / 'backup.sqlite')
        self.connections.append(backup)
        db.backup(backup)
        old_contents = choices(backup)
        replay(db, records[1:])
        latest = db.execute('SELECT sequence,record_digest FROM replay_head').fetchone()
        with self.assertRaisesRegex(ValueError, 'stale'):
            validate_restore(backup, latest)
        staged = sqlite3.connect(self.directory / 'staged.sqlite')
        self.connections.append(staged)
        backup.backup(staged)
        staged.execute('PRAGMA foreign_keys=ON')
        replay(staged, records)
        validate_restore(staged, latest)
        self.assertEqual(choices(staged), choices(db))
        self.assertEqual(choices(backup), old_contents)
        # A failed staging migration cannot affect either original.
        with self.assertRaises(sqlite3.DatabaseError):
            with staged:
                staged.execute('CREATE TABLE migration_probe(value TEXT) STRICT')
                staged.execute('INSERT INTO nonexistent VALUES(1)')
        self.assertEqual(choices(db), choices(staged))
        self.assertEqual(choices(backup), old_contents)
        self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 2)
        self.assertEqual(backup.execute('PRAGMA user_version').fetchone()[0], 2)
        self.assertEqual(staged.execute('PRAGMA user_version').fetchone()[0], 2)


class WaitBudget:
    """Operation-controller model; fake clock tests count only lock waiting."""
    def __init__(self, milliseconds=30000, clock=None, sleep=None):
        self.limit = milliseconds
        self.waited = 0
        self.clock = clock or (lambda: time.monotonic() * 1000)
        self.sleep = sleep or (lambda ms: time.sleep(ms / 1000))
        self.progress = []
        self.next_notice = 1000

    def acquire(self, attempt, cancelled=lambda: False):
        delay = 10
        while True:
            if cancelled():
                raise InterruptedError('safe stopping requested')
            try:
                if attempt():
                    return
            except sqlite3.OperationalError as error:
                # Extended codes must be classified before masking BUSY.
                if error.sqlite_errorcode == sqlite3.SQLITE_BUSY_SNAPSHOT:
                    raise ValueError('stale snapshot: revalidate or recover') from error
                if error.sqlite_errorcode & 255 != sqlite3.SQLITE_BUSY:
                    raise
            if self.waited >= self.limit:
                raise TimeoutError('db_busy')
            start = self.clock()
            self.sleep(min(delay, self.limit - self.waited))
            self.waited += self.clock() - start
            while self.waited >= self.next_notice:
                self.progress.append(self.next_notice)
                self.next_notice += 5000
            delay = min(delay * 2, 250)
            if self.waited >= self.limit:
                if cancelled():
                    raise InterruptedError('safe stopping requested')
                raise TimeoutError('db_busy')


class FakeClock:
    def __init__(self):
        self.now = 0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, ms):
        self.sleeps.append(ms)
        self.now += ms


def stop_operation(phase, cancelled=False, recovery_finished=True):
    """Durable phase model, deliberately independent of SQL rollback state."""
    committed = phase in ('committed', 'complete')
    action = {'unprepared': 'release', 'prepared': 'abort', 'effects': 'reverse',
              'committed': 'reconcile', 'complete': 'defer'}[phase]
    pending = phase not in ('unprepared', 'complete') and not recovery_finished
    return dict(phase=phase, committed=committed, recovery_required=pending,
                retry_safe=not pending and not committed, action=action,
                exit=0 if phase == 'complete' else 1 if pending else 130 if cancelled else 4,
                retained=pending, mutations_blocked=pending)


INTERVALS = dict(cleanup=3600, optimize=86400, quick_check=604800, checkpoint=0)


def maintenance(db, now, run, busy=False, budget=100, clock=None):
    """One automatic turn; run returns (outcome, reason), clock is monotonic ms."""
    clock = clock or (lambda: time.monotonic() * 1000)
    start = clock()
    if busy:
        return [('owner', 'deferred', 'busy')]  # no write solely for bookkeeping
    rows = db.execute('SELECT task,last_attempt,last_success,outcome FROM maintenance_tasks '
                      'ORDER BY last_attempt IS NOT NULL,last_attempt,task').fetchall()
    outcomes = []
    for task, attempt, success, outcome in rows:
        if clock() - start >= budget:
            break
        if success is not None and now >= success and now - success < INTERVALS[task] and outcome == 'ok':
            continue
        result, reason = run(task)
        with db:
            db.execute('UPDATE maintenance_tasks SET last_attempt=?,last_success=?,outcome=?,deferred_reason=? '
                       'WHERE task=?', (now, now if result == 'ok' else
                                        success if success is None or success <= now else None,
                                        result, reason, task))
        outcomes.append((task, result, reason))
    return outcomes


def eligible(role, kind, age, *, current=False, active=False, referenced=False, authorized=False):
    if current or active or referenced:
        return False
    if kind == 'object':
        return True  # caller has checked SQL AND retained external references
    if role == 'client-cache':
        return kind in ('solve', 'snapshot') and age >= 30 * 86400
    if role in ('client-state', 'system-state'):
        return kind == 'obsolete-projection' and authorized
    return False


def cache_source(*, busy, explicit, authenticated, fresh, policy_valid):
    if busy and explicit:
        raise TimeoutError('db_busy')
    if not (authenticated and fresh and policy_valid):
        raise ValueError('verified inputs unavailable')
    return ('memory', False) if busy else ('cache', True)


def logical_rows(db, columns=None):
    """Compare declared values, excluding operational bookkeeping and hidden rowids."""
    result = {}
    for (table,) in db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        if table == 'maintenance_tasks':
            continue
        names = [r[1] for r in db.execute(f'PRAGMA table_info({table})')]
        names = [n for n in names if n not in ('inserted_at', 'accessed_at', 'cleanup_pending', 'schema_version')]
        if columns is not None:
            if table not in columns:
                continue
            names = columns[table]
        result[table] = (names, sorted(db.execute(f'SELECT {",".join(names)} FROM {table}').fetchall(), key=repr))
    return result


def stage_compaction(source, path, free_bytes, interrupt=None, references=lambda db: None):
    size = source.execute('PRAGMA page_count').fetchone()[0] * source.execute('PRAGMA page_size').fetchone()[0]
    # Original stays allocated; new free space covers snapshot + 2x workspace.
    required = 3 * size + 65536  # fixture sidecar/journal margin
    if free_bytes < required:
        raise ValueError('insufficient space')
    expected = logical_rows(source)
    staged = sqlite3.connect(path)
    try:
        source.backup(staged)
        if interrupt == 'snapshot':
            raise InterruptedError('before activation')
        staged.execute('VACUUM')
        if logical_rows(staged) != expected:
            raise ValueError('logical mismatch')
        validate_restore(staged, source.execute('SELECT sequence,record_digest FROM replay_head').fetchone())
        references(staged)
    finally:
        staged.close()
    # Activation model retains both names and a durable intent; no runtime switch.
    return dict(old='original', new=str(path), active='original' if interrupt == 'prepared' else str(path),
                journal='prepared' if interrupt else 'committed', retained_original=True)


def recover_activation(intent, observed):
    if observed not in (intent['old'], intent['new']):
        raise ValueError('needs-attention: unexpected pointer')
    return dict(intent, active=observed, journal='rolled-back' if observed == intent['old'] else 'committed')


def version_one_schema(role):
    """Version-1 fixture DDL: omit precisely the version-2 additive structures."""
    sql = (V2_SCHEMAS / (role + '.sql')).read_text(encoding='utf-8')
    sql = re.sub(r',\n  cleanup_pending INTEGER NOT NULL DEFAULT 0 CHECK\(cleanup_pending IN \(0,1\)\)', '', sql)
    sql = re.sub(r'CREATE VIEW search_packages AS.*?;', 'CREATE VIEW search_packages AS SELECT repository,environment,name,artifact_id,summary FROM packages;', sql, flags=re.S)
    sql = re.sub(r'CREATE TABLE maintenance_tasks \(.*?CREATE TABLE objects', 'CREATE TABLE objects', sql, flags=re.S)
    sql = re.sub(r'CREATE TABLE current_snapshots \(.*?\) STRICT;\n\n', '', sql, flags=re.S)
    sql = re.sub(r'^CREATE INDEX (snapshot_cleanup|solve_cleanup|snapshot_solve_references).*\n', '', sql, flags=re.M)
    sql = re.sub(r',\n  inserted_at INTEGER NOT NULL CHECK\(inserted_at >= 0\),\n  accessed_at INTEGER NOT NULL CHECK\(accessed_at >= inserted_at\)', '', sql)
    return sql.replace('user_version = 2', 'user_version = 1').replace('schema_version = 2', 'schema_version = 1')


def copy_domain_rows(source, destination, now=0, version=2):
    """Model copy migration. Deferred FK checks validate the complete copy at commit."""
    tables = [r[0] for r in source.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    with destination:
        destination.execute('PRAGMA defer_foreign_keys=ON')
        destination.execute('DELETE FROM replay_head')
        for table in tables:
            if table == 'maintenance_tasks':
                continue
            if not destination.execute('SELECT 1 FROM sqlite_schema WHERE name=?', (table,)).fetchone():
                continue
            old = [r[1] for r in source.execute(f'PRAGMA table_info({table})')]
            new = [r[1] for r in destination.execute(f'PRAGMA table_info({table})')]
            for row in source.execute(f'SELECT * FROM {table}'):
                values = dict(zip(old, row))
                values.update(inserted_at=now, accessed_at=now, cleanup_pending=0, schema_version=version)
                insert(destination, table, *(values[n] for n in new))


class DatabaseMaintenance(unittest.TestCase):
    setUp = DatabaseSchemas.setUp
    tearDown = DatabaseSchemas.tearDown
    create = DatabaseSchemas.create
    reject = DatabaseSchemas.reject

    def test_version_one_to_two_copy_migration_all_roles(self):
        for role in ROLES:
            with self.subTest(role=role):
                fixture = self.create(role, version=2)
                old = sqlite3.connect(self.directory / (role + '-v1.sqlite'))
                self.connections.append(old)
                ddl = version_one_schema(role)
                normalized = re.sub(r'^--.*$', '', ddl, flags=re.M).replace('PRAGMA auto_vacuum = NONE;', '')
                normalized = re.sub(r'\s+', ' ', normalized).strip().encode()
                self.assertEqual(hashlib.sha256(normalized).hexdigest(), V1_SCHEMA_HASHES[role])
                old.executescript(ddl)
                copy_domain_rows(fixture, old, version=1)
                expected = logical_rows(old)
                staged = sqlite3.connect(self.directory / (role + '-v2.sqlite'))
                self.connections.append(staged)
                staged.executescript((V2_SCHEMAS / (role + '.sql')).read_text(encoding='utf-8'))
                copy_domain_rows(old, staged, now=1000)
                if role == 'client-cache':
                    # Fixture stands for independently authenticated current inputs.
                    with staged:
                        insert(staged, 'current_snapshots', 'core', 'prod', digest('a'))
                    self.assertEqual(staged.execute('SELECT inserted_at,accessed_at FROM snapshots').fetchall(), [(1000,1000)])
                    self.assertEqual(staged.execute('SELECT inserted_at,accessed_at FROM solve_cache').fetchall(), [(1000,1000)])
                columns = {t: names for t, (names, rows) in expected.items()}
                self.assertEqual(logical_rows(staged, columns), expected)
                validate_restore(staged, old.execute('SELECT sequence,record_digest FROM replay_head').fetchone())
                self.assertEqual(staged.execute('PRAGMA application_id').fetchone(), old.execute('PRAGMA application_id').fetchone())
                self.assertEqual(staged.execute('PRAGMA user_version').fetchone(), (2,))
                self.assertEqual(staged.execute('SELECT schema_version FROM database_identity').fetchone(), (2,))
                self.assertEqual(staged.execute("SELECT count(*) FROM maintenance_tasks WHERE outcome='due' AND last_attempt IS NULL AND last_success IS NULL").fetchone(), (4,))
                self.assertEqual(old.execute('PRAGMA user_version').fetchone(), (1,))
                self.assertEqual(old.execute('SELECT schema_version FROM database_identity').fetchone(), (1,))
                with self.assertRaises(sqlite3.IntegrityError):
                    with staged:
                        staged.execute('UPDATE database_identity SET schema_version=1')
                self.assertEqual(logical_rows(old), expected)

    def test_wait_cumulative_budget_progress_cancellation_and_no_wait(self):
        fake = FakeClock()
        wait = WaitBudget(clock=fake.clock, sleep=fake.sleep)
        wait.acquire(lambda: fake.now >= 210)
        first = wait.waited
        fake.now += 90000  # useful work must not spend the allowance
        with self.assertRaises(TimeoutError):
            wait.acquire(lambda: False)
        self.assertEqual(wait.waited, 30000)
        self.assertGreater(first, 0)
        self.assertEqual(wait.progress, [1000, 6000, 11000, 16000, 21000, 26000])
        self.assertLessEqual(max(fake.sleeps), 250)
        none = WaitBudget(0, fake.clock, fake.sleep)
        none.acquire(lambda: True)
        with self.assertRaises(TimeoutError):
            none.acquire(lambda: False)
        self.assertEqual(none.waited, 0)
        cancel = WaitBudget(clock=fake.clock, sleep=fake.sleep)
        until = fake.now + 30
        with self.assertRaises(InterruptedError):
            cancel.acquire(lambda: False, lambda: fake.now >= until)
        self.assertEqual(cancel.waited, 30)
        # Recovery is fresh but finite, not the exhausted foreground controller.
        recovery = WaitBudget(clock=fake.clock, sleep=fake.sleep)
        with self.assertRaises(TimeoutError):
            recovery.acquire(lambda: False)
        self.assertEqual(recovery.waited, 30000)

    def test_real_writer_contention_release_timeout_and_stale_snapshot(self):
        writer = self.create('client-state')
        reader = sqlite3.connect(self.directory / 'client-state.sqlite', timeout=0)
        self.connections.append(reader)
        writer.execute('BEGIN IMMEDIATE')
        def attempt():
            reader.execute('BEGIN IMMEDIATE')
            return True
        with self.assertRaises(TimeoutError):
            WaitBudget(0).acquire(attempt)
        fake = FakeClock()
        def release(ms):
            fake.sleep(ms)
            if fake.now >= 30:
                writer.rollback()
        WaitBudget(100, fake.clock, release).acquire(attempt)
        reader.rollback()
        writer.execute('BEGIN IMMEDIATE')
        with self.assertRaises(TimeoutError):
            WaitBudget(30, fake.clock, fake.sleep).acquire(attempt)
        writer.rollback()
        reader.execute('BEGIN')
        reader.execute('SELECT * FROM profiles').fetchall()
        with writer:
            writer.execute("INSERT INTO profiles VALUES('new')")
        wait = WaitBudget(30000, fake.clock, fake.sleep)
        with self.assertRaisesRegex(ValueError, 'stale snapshot'):
            wait.acquire(lambda: reader.execute("INSERT INTO profiles VALUES('stale')"))
        self.assertEqual(wait.waited, 0)
        reader.rollback()
        wait.acquire(attempt)
        reader.rollback()

    def test_internal_locked_is_not_retried(self):
        db = self.create('client-state')
        db.execute('CREATE TABLE lock_probe(value INTEGER)')
        db.executemany('INSERT INTO lock_probe VALUES(?)', [(1,), (2,), (3,)])
        db.commit()
        cursor = db.execute('SELECT * FROM lock_probe')
        cursor.fetchone()
        wait = WaitBudget()
        with self.assertRaises(sqlite3.OperationalError) as caught:
            wait.acquire(lambda: db.execute('DROP TABLE lock_probe'))
        self.assertEqual(caught.exception.sqlite_errorcode, sqlite3.SQLITE_LOCKED)
        self.assertEqual(wait.waited, 0)
        cursor.close()

    def test_all_durable_phase_outcomes(self):
        for cancelled in (False, True):
            for resolved in (False, True):
                for phase, action in [('unprepared','release'), ('prepared','abort'),
                                      ('effects','reverse'), ('committed','reconcile'), ('complete','defer')]:
                    with self.subTest(phase=phase, cancelled=cancelled, resolved=resolved):
                        result = stop_operation(phase, cancelled, resolved)
                        self.assertEqual(result['action'], action)
                        pending = not resolved and phase in ('prepared','effects','committed')
                        self.assertEqual(result['recovery_required'], pending)
                        self.assertEqual(result['mutations_blocked'], pending)
                        self.assertEqual(result['retained'], pending)
                        self.assertEqual(result['committed'], phase in ('committed','complete'))
                        self.assertEqual(result['exit'], 0 if phase == 'complete' else 1 if pending else 130 if cancelled else 4)
                        if pending or result['committed']:
                            self.assertFalse(result['retry_safe'])

    def test_cache_bypass_verification_and_explicit_contention(self):
        self.assertEqual(cache_source(busy=True, explicit=False, authenticated=True, fresh=True, policy_valid=True), ('memory', False))
        with self.assertRaises(TimeoutError):
            cache_source(busy=True, explicit=True, authenticated=True, fresh=True, policy_valid=True)
        for failed in ('authenticated','fresh','policy_valid'):
            args = dict(busy=True, explicit=False, authenticated=True, fresh=True, policy_valid=True)
            args[failed] = False
            with self.assertRaises(ValueError):
                cache_source(**args)

    def test_schedule_fairness_due_times_busy_and_foreground_success(self):
        db = self.create('client-state')
        initial = db.execute('SELECT * FROM maintenance_tasks').fetchall()
        logical = logical_rows(db)
        self.assertEqual(maintenance(db, 100, lambda _: self.fail(), busy=True), [('owner','deferred','busy')])
        self.assertEqual(db.execute('SELECT * FROM maintenance_tasks').fetchall(), initial)
        fake = FakeClock()
        seen = []
        def backlog(task):
            fake.sleep(100)
            seen.append(task)
            return 'deferred', 'backlog'
        for now in range(100,104):
            maintenance(db, now, backlog, clock=fake.clock)
        self.assertEqual(len(set(seen)), 4)
        maintenance(db, 1000, lambda _: ('ok', None))
        self.assertEqual([x[0] for x in maintenance(db, 4599, lambda _: ('ok', None))], ['checkpoint'])
        self.assertIn('cleanup', [x[0] for x in maintenance(db, 4600, lambda _: ('ok', None))])
        self.assertIn('optimize', [x[0] for x in maintenance(db, 87400, lambda _: ('ok', None))])
        self.assertIn('quick_check', [x[0] for x in maintenance(db, 605800, lambda _: ('ok', None))])
        self.assertEqual(len(maintenance(db, 1, lambda _: ('ok', None))), 4)  # clock moved back
        maintenance(db, 1000000, lambda _: ('interrupted', 'budget'))
        self.assertEqual(db.execute("SELECT count(*) FROM maintenance_tasks WHERE outcome='interrupted' AND last_success=1").fetchone(), (4,))
        self.assertEqual(logical_rows(db), logical)
        self.assertEqual(stop_operation('complete', recovery_finished=False)['exit'], 0)

    def test_cleanup_retention_matrix_and_age_boundary(self):
        for role in ROLES:
            for kind in ('history','reservation','candidate','attempt','quarantine','evidence','process','trust'):
                self.assertFalse(eligible(role, kind, 10**12, authorized=True), (role,kind))
            self.assertFalse(eligible(role, 'object', 10**12, referenced=True))
            self.assertTrue(eligible(role, 'object', 0))
        for kind in ('solve','snapshot'):
            self.assertFalse(eligible('client-cache', kind, 2591999))
            self.assertTrue(eligible('client-cache', kind, 2592000))
            for protection in ('current','active','referenced'):
                self.assertFalse(eligible('client-cache', kind, 10**12, **{protection:True}))
        for role in ('client-state','system-state'):
            self.assertFalse(eligible(role, 'obsolete-projection', 10**12))
            self.assertTrue(eligible(role, 'obsolete-projection', 0, authorized=True))

    def test_cache_constraints_and_interrupted_bounded_cleanup(self):
        db = self.create('client-cache')
        self.reject(db, 'DELETE FROM snapshots')
        self.reject(db, 'UPDATE solve_cache SET accessed_at=-1')
        self.reject(db, 'UPDATE snapshots SET inserted_at=1')
        for i in range(205):
            insert(db, 'solve_cache', obj(db, f'input-{i}'), digest('c'), 'fixture', 0, 0, 0)
        db.commit()
        # Parent solves with children are excluded from this fixture batch;
        # production cleanup spends the same bound on child removals too.
        delete = ('DELETE FROM solve_cache WHERE input_digest IN '
                  '(SELECT input_digest FROM solve_cache WHERE accessed_at<=? '
                  'AND NOT EXISTS(SELECT 1 FROM solve_inputs i WHERE i.input_digest=solve_cache.input_digest) '
                  'ORDER BY accessed_at,input_digest LIMIT 100)')
        with db:
            self.assertEqual(db.execute(delete, (-1,)).rowcount, 0)
            self.assertEqual(db.execute(delete, (0,)).rowcount, 100)
        before = db.execute('SELECT count(*) FROM solve_cache').fetchone()
        with self.assertRaises(InterruptedError):
            with db:
                self.assertEqual(db.execute(delete, (0,)).rowcount, 100)
                raise InterruptedError()
        self.assertEqual(db.execute('SELECT count(*) FROM solve_cache').fetchone(), before)

        self.assertEqual(db.execute('SELECT count(*) FROM current_snapshots').fetchone(), (1,))
        db.set_progress_handler(lambda: 1, 1)
        with self.assertRaises(sqlite3.OperationalError):
            db.execute(delete, (0,))
        db.set_progress_handler(None, 0)
        db.rollback()
        self.assertEqual(db.execute('SELECT count(*) FROM solve_cache').fetchone(), before)

    def test_partial_snapshot_cleanup_stays_hidden_after_reopen(self):
        db = self.create('client-cache')
        with db:
            db.execute('DELETE FROM current_snapshots')
            db.execute('DELETE FROM solve_inputs')
            db.execute('UPDATE snapshots SET cleanup_pending=1')
        self.assertEqual(db.execute('SELECT count(*) FROM packages').fetchone(), (1,))
        self.assertEqual(db.execute('SELECT * FROM search_packages').fetchall(), [])
        reopened = sqlite3.connect(self.directory / 'client-cache.sqlite')
        self.connections.append(reopened)
        self.assertEqual(reopened.execute('SELECT * FROM search_packages').fetchall(), [])
        with self.assertRaises(InterruptedError):
            with db:
                db.execute('DELETE FROM packages')
                raise InterruptedError('batch interrupted')
        self.assertEqual(db.execute('SELECT cleanup_pending FROM snapshots').fetchone(), (1,))
        self.assertEqual(db.execute('SELECT count(*) FROM packages').fetchone(), (1,))

    def test_optimization_and_passive_checkpoint_with_active_reader(self):
        db = self.create('client-cache')
        db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        reader = sqlite3.connect(self.directory / 'client-cache.sqlite', timeout=0)
        self.connections.append(reader)
        reader.execute('BEGIN')
        reader.execute('SELECT * FROM snapshots').fetchall()
        with db:
            db.execute('UPDATE snapshots SET accessed_at=1')
        db.execute('PRAGMA analysis_limit=100')
        db.execute('PRAGMA optimize').fetchall()
        busy, total, copied = db.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone()
        self.assertLess(copied, total)  # PASSIVE can return busy=0 but remain incomplete
        self.assertEqual(reader.execute('SELECT accessed_at FROM snapshots').fetchone(), (0,))
        reader.rollback()
        busy, total, copied = db.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone()
        self.assertEqual(copied, total)
        self.assertEqual(db.execute('PRAGMA quick_check').fetchall(), [('ok',)])

    def test_compaction_equivalence_space_refusal_and_interrupted_activation(self):
        db = self.create('client-state')
        expected = logical_rows(db)
        db.execute('CREATE TABLE temporary_load(data BLOB)')
        db.executemany('INSERT INTO temporary_load VALUES(?)', [(b'x'*4096,)]*100)
        db.execute('DROP TABLE temporary_load')
        db.commit()
        self.assertEqual(db.execute('PRAGMA auto_vacuum').fetchone(), (0,))
        self.assertGreater(db.execute('PRAGMA freelist_count').fetchone()[0], 0)
        with self.assertRaisesRegex(ValueError, 'insufficient'):
            stage_compaction(db, self.directory/'no-space.sqlite', 0)
        self.assertFalse((self.directory/'no-space.sqlite').exists())
        with self.assertRaises(InterruptedError):
            stage_compaction(db, self.directory/'partial.sqlite', 10**9, 'snapshot')
        pending = stage_compaction(db, self.directory/'prepared.sqlite', 10**9, 'prepared')
        self.assertEqual((pending['active'], pending['journal']), ('original','prepared'))
        self.assertEqual(recover_activation(pending, pending['active'])['journal'], 'rolled-back')
        activated = stage_compaction(db, self.directory/'activated.sqlite', 10**9, 'activated')
        recovered = recover_activation(activated, activated['active'])
        self.assertEqual(recovered['journal'], 'committed')
        self.assertTrue(recovered['retained_original'])
        with self.assertRaisesRegex(ValueError, 'unexpected pointer'):
            recover_activation(activated, 'unrelated.sqlite')
        def missing_reference(staged):
            self.assertTrue(staged.execute('SELECT digest FROM objects').fetchall())
            raise ValueError('missing external reference')
        with self.assertRaisesRegex(ValueError, 'missing external'):
            stage_compaction(db, self.directory/'missing.sqlite', 10**9, references=missing_reference)
        result = stage_compaction(db, self.directory/'compact.sqlite', 10**9)
        self.assertTrue(result['retained_original'])
        self.assertEqual(result['journal'], 'committed')
        self.assertEqual(logical_rows(db), expected)
        compact = sqlite3.connect(result['new'])
        self.connections.append(compact)
        self.assertEqual(logical_rows(compact), expected)
        self.assertLess(compact.execute('PRAGMA page_count').fetchone()[0], db.execute('PRAGMA page_count').fetchone()[0])


def encoded(record):
    # Fixture subset of JCS: ASCII keys/values, integers, no floats or Unicode ordering.
    return json.dumps(record, sort_keys=True, separators=(',', ':'))


def choice_records():
    previous = None
    records = []
    for seq, (command, changes) in enumerate((
        ('mark', {'requested': 1, 'held': False, 'stream': None, 'provider': None}),
        ('pin', {'requested': 1, 'held': True, 'stream': '3.14', 'provider': 'python'}),
        ('unpin', {'requested': 0, 'held': False, 'stream': '3.14', 'provider': 'python'}),
    ), 1):
        record = dict(format=1, role='client-state', instance_id='a' * 32,
                      sequence=seq, previous=previous, operation_id=f'{seq:032x}',
                      phase='committed', command=command, occurred_at=seq,
                      scope=None, before=None if not records else records[-1]['after'],
                      after=digest(encoded(changes)), changes=[{'kind': 'fixture-choices-v1',
                          'before': None if not records else records[-1]['changes'][0]['after'],
                          'after': changes}], evidence=[])
        records.append(record)
        previous = digest(encoded(record))
    return records


def replay(db, records):
    """Terminal choice-only subset; not a filesystem journal/recovery implementation."""
    for record in records:
        key = digest(encoded(record))
        sequence, previous = db.execute('SELECT sequence,record_digest FROM replay_head').fetchone()
        if record['sequence'] <= sequence:
            saved = db.execute('SELECT record_digest FROM history WHERE sequence=?', (record['sequence'],)).fetchone()
            if saved != (key,):
                raise ValueError('conflict')
            continue
        if record['sequence'] != sequence + 1:
            raise ValueError('gap')
        if record['previous'] != previous:
            raise ValueError('predecessor')
        if record['phase'] != 'committed':
            raise ValueError('incomplete')
        if (record['role'], record['instance_id'], record['format']) != ('client-state', 'a' * 32, 1):
            raise ValueError('identity')
        before = db.execute('SELECT after_digest FROM history ORDER BY sequence DESC LIMIT 1').fetchone()
        if record['before'] != (before[0] if before else None):
            raise ValueError('before-state')
        changes = record['changes'][0]['after']
        if record['after'] != digest(encoded(changes)):
            raise ValueError('after-state')
        with db:
            obj(db, encoded(record))
            obj(db, encoded(changes))
            db.execute('INSERT INTO profiles VALUES(?) ON CONFLICT(profile) DO NOTHING', ('default',))
            db.execute('DELETE FROM profile_priorities')
            if changes['provider']:
                insert(db, 'profile_priorities', 'default', 'python', 'core', 'prod', changes['provider'])
            db.execute('INSERT INTO requests VALUES(?,?,?,?,?) ON CONFLICT(profile,repository,name) DO UPDATE SET requested=excluded.requested',
                       ('default', 'core', 'prod', 'python', changes['requested']))
            db.execute('DELETE FROM holds')
            if changes['held']:
                insert(db, 'holds', 'default', 'core', 'python', 'choice')
            db.execute('DELETE FROM runtime_defaults')
            if changes['stream']:
                insert(db, 'runtime_defaults', 'default', 'python', changes['stream'])
            insert(db, 'history', record['operation_id'], record['sequence'], record['command'],
                   record['occurred_at'], 'committed', record['before'], record['after'], key)
            db.execute('UPDATE replay_head SET sequence=?,record_digest=?', (record['sequence'], key))


def choices(db):
    return {table: db.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()
            for table in ('profiles', 'profile_priorities', 'requests', 'holds', 'runtime_defaults', 'history', 'replay_head')}


def validate_restore(db, latest):
    if db.execute('SELECT sequence,record_digest FROM replay_head').fetchone() != latest:
        raise ValueError('stale backup')
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or db.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('integrity')


if __name__ == '__main__':
    print('Schema/model tests using SQLite', sqlite3.sqlite_version, '(not production qualification)')
    unittest.main()
