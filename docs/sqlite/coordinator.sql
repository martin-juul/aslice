-- aslice coordinator, schema 1. Execute only in a new, owner-controlled file.
-- Connection policy and semantic validation: ../DATABASE.md.
PRAGMA application_id = 1095977988;
PRAGMA user_version = 1;
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
PRAGMA trusted_schema = OFF;
BEGIN IMMEDIATE;
CREATE TABLE database_identity (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
  role TEXT NOT NULL CHECK(role = 'coordinator'),
  instance_id TEXT NOT NULL CHECK(length(instance_id) = 32 AND length(CAST(instance_id AS BLOB)) = 32 AND instance_id NOT GLOB '*[^0-9a-f]*'),
  owner_id TEXT NOT NULL CHECK(length(owner_id) > 0),
  schema_version INTEGER NOT NULL CHECK(schema_version = 1)
) STRICT;

CREATE TABLE objects (
  digest TEXT PRIMARY KEY CHECK(length(digest) = 71 AND length(CAST(digest AS BLOB)) = 71 AND substr(digest,1,7) = 'sha256:' AND substr(digest,8) NOT GLOB '*[^0-9a-f]*'),
  byte_length INTEGER NOT NULL CHECK(byte_length >= 0),
  kind TEXT NOT NULL CHECK(length(kind) > 0)
) STRICT;

CREATE TABLE scopes (
  repository TEXT NOT NULL CHECK(length(repository) > 0 AND instr(repository,char(0)) = 0 AND repository NOT GLOB '*[^a-z0-9-]*' AND substr(repository,1,1) GLOB '[a-z0-9]'),
  environment TEXT NOT NULL CHECK(environment IN ('dev','staging','prod')),
  PRIMARY KEY(repository, environment)
) STRICT;

CREATE TABLE replay_head (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
  sequence INTEGER NOT NULL CHECK(sequence >= 0),
  record_digest TEXT REFERENCES objects(digest),
  CHECK((sequence = 0 AND record_digest IS NULL) OR (sequence > 0 AND record_digest IS NOT NULL))
) STRICT;

INSERT INTO replay_head VALUES(1, 0, NULL);

CREATE TABLE plans (
  plan_digest TEXT PRIMARY KEY REFERENCES objects(digest), repository TEXT NOT NULL, environment TEXT NOT NULL,
  orchard_commit TEXT NOT NULL, authorization_digest TEXT NOT NULL REFERENCES objects(digest),
  UNIQUE(repository,environment,plan_digest), FOREIGN KEY(repository,environment) REFERENCES scopes
) STRICT;

CREATE TABLE lanes (
  lane TEXT PRIMARY KEY CHECK(lane IN ('build','test','rebuild','vendor','graft'))
) STRICT;

CREATE TABLE workers (
  worker_id TEXT PRIMARY KEY, enrollment_digest TEXT NOT NULL REFERENCES objects(digest),
  enabled INTEGER NOT NULL CHECK(enabled IN (0,1))
) STRICT;

CREATE TABLE worker_capabilities (
  worker_id TEXT NOT NULL REFERENCES workers, capability TEXT NOT NULL, evidence_digest TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(worker_id,capability)
) STRICT;

CREATE TABLE jobs (
  job_digest TEXT PRIMARY KEY REFERENCES objects(digest), repository TEXT NOT NULL, environment TEXT NOT NULL,
  plan_digest TEXT NOT NULL, lane TEXT NOT NULL REFERENCES lanes,
  state TEXT NOT NULL CHECK(state IN ('queued','leased','complete','quarantined')),
  UNIQUE(plan_digest,job_digest),
  FOREIGN KEY(repository,environment,plan_digest) REFERENCES plans(repository,environment,plan_digest)
) STRICT;

CREATE TABLE job_requirements (
  job_digest TEXT NOT NULL REFERENCES jobs, capability TEXT NOT NULL,
  PRIMARY KEY(job_digest,capability)
) STRICT;

CREATE TABLE job_dependencies (
  plan_digest TEXT NOT NULL, job_digest TEXT NOT NULL, dependency_digest TEXT NOT NULL,
  PRIMARY KEY(job_digest,dependency_digest), CHECK(job_digest <> dependency_digest),
  FOREIGN KEY(plan_digest,job_digest) REFERENCES jobs(plan_digest,job_digest),
  FOREIGN KEY(plan_digest,dependency_digest) REFERENCES jobs(plan_digest,job_digest)
) STRICT;

CREATE TABLE attempts (
  job_digest TEXT NOT NULL REFERENCES jobs, attempt INTEGER NOT NULL CHECK(attempt > 0),
  worker_id TEXT NOT NULL REFERENCES workers, lease_token TEXT NOT NULL UNIQUE,
  expires_at INTEGER NOT NULL CHECK(expires_at >= 0),
  state TEXT NOT NULL CHECK(state IN ('active','expired','returned')),
  PRIMARY KEY(job_digest,attempt)
) STRICT;

CREATE TABLE results (
  job_digest TEXT PRIMARY KEY REFERENCES jobs, attempt INTEGER NOT NULL,
  result_digest TEXT NOT NULL REFERENCES objects(digest),
  FOREIGN KEY(job_digest,attempt) REFERENCES attempts
) STRICT;

CREATE TABLE quarantine (
  job_digest TEXT NOT NULL REFERENCES jobs, sequence INTEGER NOT NULL CHECK(sequence > 0),
  decision TEXT NOT NULL CHECK(decision IN ('hold','release')), record_digest TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(job_digest,sequence)
) STRICT;

CREATE TABLE gate_evidence (
  job_digest TEXT NOT NULL REFERENCES jobs, gate TEXT NOT NULL,
  verdict TEXT NOT NULL CHECK(verdict IN ('pending','pass','fail')),
  receipt_digest TEXT REFERENCES objects(digest),
  CHECK(verdict = 'pending' OR receipt_digest IS NOT NULL), PRIMARY KEY(job_digest,gate)
) STRICT;

CREATE UNIQUE INDEX one_active_attempt ON attempts(job_digest) WHERE state = 'active';
CREATE INDEX lease_expiry ON attempts(state,expires_at);
CREATE INDEX jobs_queue ON jobs(state,lane);
CREATE INDEX dependency_reverse ON job_dependencies(dependency_digest);
CREATE VIEW lease_status AS SELECT job_digest,attempt,worker_id,expires_at FROM attempts WHERE state = 'active';
CREATE VIEW pending_gates AS SELECT * FROM gate_evidence WHERE verdict <> 'pass';

COMMIT;
