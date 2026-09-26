"""Executable specification models, not aslice runtime or power-loss tests."""
from pathlib import Path
import hashlib
import json
import re
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / 'docs/sqlite'
ROLES = ('client-state', 'client-cache', 'system-state', 'coordinator', 'publisher', 'release-signer')


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
        insert(db, 'snapshots', 'core', 'prod', a, b, 100)
        insert(db, 'packages', 'core', 'prod', a, 'python', b, c, 'Interpreter')
        insert(db, 'solve_cache', b, c, 'model-1')
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
        insert(db, 'lanes', 'build')
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

    def create(self, role, fixture=True, suffix=''):
        db = sqlite3.connect(self.directory / (role + suffix + '.sqlite'))
        self.connections.append(db)
        db.executescript((SCHEMAS / (role + '.sql')).read_text(encoding='utf-8'))
        insert(db, 'database_identity', 1, role, 'a' * 32, 'owner-fixture', 1)
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
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)
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
        with staged:
            staged.execute('PRAGMA user_version=2')
        self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)
        self.assertEqual(backup.execute('PRAGMA user_version').fetchone()[0], 1)
        self.assertEqual(staged.execute('PRAGMA user_version').fetchone()[0], 2)


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
