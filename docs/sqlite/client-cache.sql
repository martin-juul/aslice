-- aslice client-cache, schema 1. Execute only in a new, owner-controlled file.
-- Connection policy and semantic validation: ../DATABASE.md.
PRAGMA application_id = 1095977986;
PRAGMA user_version = 1;
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA trusted_schema = OFF;
BEGIN IMMEDIATE;
CREATE TABLE database_identity (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
  role TEXT NOT NULL CHECK(role = 'client-cache'),
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

CREATE TABLE snapshots (
  repository TEXT NOT NULL, environment TEXT NOT NULL,
  snapshot_digest TEXT NOT NULL REFERENCES objects(digest), verified_receipt TEXT NOT NULL REFERENCES objects(digest),
  expires_at INTEGER NOT NULL CHECK(expires_at >= 0),
  PRIMARY KEY(repository, environment, snapshot_digest),
  FOREIGN KEY(repository, environment) REFERENCES scopes
) STRICT;

CREATE TABLE packages (
  repository TEXT NOT NULL, environment TEXT NOT NULL, snapshot_digest TEXT NOT NULL,
  name TEXT NOT NULL CHECK(length(name) > 0), artifact_id TEXT NOT NULL REFERENCES objects(digest),
  recipe_digest TEXT NOT NULL REFERENCES objects(digest), summary TEXT NOT NULL,
  PRIMARY KEY(repository, environment, snapshot_digest, name, artifact_id),
  FOREIGN KEY(repository, environment, snapshot_digest) REFERENCES snapshots
) STRICT;

CREATE TABLE solve_cache (
  input_digest TEXT PRIMARY KEY REFERENCES objects(digest),
  result_digest TEXT NOT NULL REFERENCES objects(digest), solver_version TEXT NOT NULL
) STRICT;

CREATE TABLE solve_inputs (
  input_digest TEXT NOT NULL REFERENCES solve_cache,
  repository TEXT NOT NULL, environment TEXT NOT NULL, snapshot_digest TEXT NOT NULL,
  PRIMARY KEY(input_digest, repository, environment),
  FOREIGN KEY(repository, environment, snapshot_digest) REFERENCES snapshots
) STRICT;

CREATE TABLE trust_projections (
  repository TEXT NOT NULL, environment TEXT NOT NULL,
  record_digest TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(repository, environment), FOREIGN KEY(repository, environment) REFERENCES scopes
) STRICT;

CREATE INDEX package_search ON packages(name,repository,environment);
CREATE VIEW search_packages AS SELECT repository,environment,name,artifact_id,summary FROM packages;

COMMIT;
