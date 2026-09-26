-- aslice system-state, schema 2. Execute only in a new, owner-controlled file.
-- Connection policy and semantic validation: ../DATABASE.md.
PRAGMA application_id = 1095977987;
PRAGMA user_version = 2;
PRAGMA auto_vacuum = NONE;
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
PRAGMA trusted_schema = OFF;
BEGIN IMMEDIATE;
CREATE TABLE database_identity (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
  role TEXT NOT NULL CHECK(role = 'system-state'),
  instance_id TEXT NOT NULL CHECK(length(instance_id) = 32 AND length(CAST(instance_id AS BLOB)) = 32 AND instance_id NOT GLOB '*[^0-9a-f]*'),
  owner_id TEXT NOT NULL CHECK(length(owner_id) > 0),
  schema_version INTEGER NOT NULL CHECK(schema_version = 2)
) STRICT;

CREATE TABLE maintenance_tasks (
  task TEXT PRIMARY KEY CHECK(task IN ('cleanup','optimize','quick_check','checkpoint')),
  last_attempt INTEGER CHECK(last_attempt >= 0),
  last_success INTEGER CHECK(last_success >= 0),
  outcome TEXT NOT NULL CHECK(outcome IN ('due','running','ok','deferred','interrupted','error')),
  deferred_reason TEXT,
  CHECK(last_success IS NULL OR (last_attempt IS NOT NULL AND last_success <= last_attempt))
) STRICT;
INSERT INTO maintenance_tasks(task,outcome) VALUES
  ('cleanup','due'),('optimize','due'),('quick_check','due'),('checkpoint','due');

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

CREATE TABLE closures (
  closure_digest TEXT PRIMARY KEY REFERENCES objects(digest),
  authorization_digest TEXT NOT NULL REFERENCES objects(digest)
) STRICT;

CREATE TABLE closure_members (
  closure_digest TEXT NOT NULL REFERENCES closures, repository TEXT NOT NULL, environment TEXT NOT NULL,
  artifact_id TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(closure_digest,repository,environment,artifact_id),
  FOREIGN KEY(repository,environment) REFERENCES scopes
) STRICT;

CREATE TABLE prefixes (
  prefix_id TEXT PRIMARY KEY CHECK(length(prefix_id) = 32 AND length(CAST(prefix_id AS BLOB)) = 32 AND prefix_id NOT GLOB '*[^0-9a-f]*'),
  canonical_path TEXT NOT NULL UNIQUE CHECK(substr(canonical_path,1,1) = '/'),
  owner_uid INTEGER NOT NULL CHECK(owner_uid >= 0)
) STRICT;

CREATE TABLE prefix_references (
  prefix_id TEXT NOT NULL REFERENCES prefixes, closure_digest TEXT NOT NULL REFERENCES closures,
  purpose TEXT NOT NULL CHECK(purpose IN ('active','retained','transaction')),
  PRIMARY KEY(prefix_id,closure_digest,purpose)
) STRICT;

CREATE TABLE effects (
  effect_id TEXT PRIMARY KEY, prefix_id TEXT NOT NULL REFERENCES prefixes,
  closure_digest TEXT NOT NULL REFERENCES closures, target TEXT NOT NULL UNIQUE,
  before_digest TEXT NOT NULL REFERENCES objects(digest), after_digest TEXT NOT NULL REFERENCES objects(digest),
  backup_digest TEXT NOT NULL REFERENCES objects(digest),
  state TEXT NOT NULL CHECK(state IN ('prepared','applied','restored','needs-attention')),
  UNIQUE(effect_id,closure_digest)
) STRICT;

CREATE TABLE services (
  label TEXT PRIMARY KEY, effect_id TEXT NOT NULL, closure_digest TEXT NOT NULL,
  plist_digest TEXT NOT NULL REFERENCES objects(digest),
  FOREIGN KEY(effect_id,closure_digest) REFERENCES effects(effect_id,closure_digest)
) STRICT;

CREATE TABLE recovery_receipts (
  operation_id TEXT PRIMARY KEY, record_digest TEXT NOT NULL REFERENCES objects(digest),
  state TEXT NOT NULL CHECK(state IN ('prepared','applying','activated','committed','recovering','rolled-back','needs-attention'))
) STRICT;

CREATE INDEX effect_prefix ON effects(prefix_id);
CREATE INDEX reference_closure ON prefix_references(closure_digest);
CREATE VIEW managed_services AS SELECT s.label,s.closure_digest,e.prefix_id,e.target,e.state
 FROM services s JOIN effects e USING(effect_id,closure_digest);

COMMIT;
