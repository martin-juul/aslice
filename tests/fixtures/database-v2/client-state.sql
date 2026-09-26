-- aslice client-state, schema 2. Execute only in a new, owner-controlled file.
-- Connection policy and semantic validation: ../DATABASE.md.
PRAGMA application_id = 1095977985;
PRAGMA user_version = 2;
PRAGMA auto_vacuum = NONE;
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
PRAGMA trusted_schema = OFF;
BEGIN IMMEDIATE;
CREATE TABLE database_identity (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
  role TEXT NOT NULL CHECK(role = 'client-state'),
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

CREATE TABLE artifacts (
  repository TEXT NOT NULL, environment TEXT NOT NULL,
  artifact_id TEXT NOT NULL REFERENCES objects(digest),
  build_id TEXT NOT NULL CHECK(length(build_id) = 64 AND length(CAST(build_id AS BLOB)) = 64 AND build_id NOT GLOB '*[^0-9a-f]*'),
  name TEXT NOT NULL CHECK(length(name) > 0), version TEXT NOT NULL CHECK(length(version) > 0),
  origin TEXT NOT NULL CHECK(origin IN ('slice','local-build','vendor-direct')),
  package_record_digest TEXT NOT NULL REFERENCES objects(digest),
  blob_digest TEXT NOT NULL REFERENCES objects(digest),
  materialization_digest TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(repository, environment, artifact_id),
  UNIQUE(repository, environment, name, artifact_id),
  FOREIGN KEY(repository, environment) REFERENCES scopes
) STRICT;

CREATE TABLE bindings (
  repository TEXT NOT NULL, environment TEXT NOT NULL, artifact_id TEXT NOT NULL,
  dependency_repository TEXT NOT NULL, dependency_name TEXT NOT NULL,
  dependency_environment TEXT NOT NULL, dependency_artifact TEXT NOT NULL,
  PRIMARY KEY(repository, environment, artifact_id, dependency_repository, dependency_name),
  FOREIGN KEY(repository, environment, artifact_id) REFERENCES artifacts,
  FOREIGN KEY(dependency_repository, dependency_environment, dependency_name, dependency_artifact)
    REFERENCES artifacts(repository, environment, name, artifact_id)
) STRICT;

CREATE TABLE profiles (
  profile TEXT PRIMARY KEY CHECK(length(profile) > 0)
) STRICT;

CREATE TABLE profile_priorities (
  profile TEXT NOT NULL REFERENCES profiles, collision_key TEXT NOT NULL CHECK(length(collision_key) > 0),
  repository TEXT NOT NULL, environment TEXT NOT NULL, name TEXT NOT NULL CHECK(length(name) > 0),
  PRIMARY KEY(profile,collision_key), FOREIGN KEY(repository,environment) REFERENCES scopes
) STRICT;

CREATE TABLE generations (
  profile TEXT NOT NULL REFERENCES profiles, generation INTEGER NOT NULL CHECK(generation > 0),
  manifest_digest TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(profile, generation)
) STRICT;

CREATE TABLE active_generations (
  profile TEXT PRIMARY KEY REFERENCES profiles, generation INTEGER NOT NULL,
  FOREIGN KEY(profile, generation) REFERENCES generations
) STRICT;

CREATE TABLE members (
  profile TEXT NOT NULL, generation INTEGER NOT NULL,
  repository TEXT NOT NULL, environment TEXT NOT NULL, name TEXT NOT NULL, artifact_id TEXT NOT NULL,
  PRIMARY KEY(profile, generation, repository, name),
  FOREIGN KEY(profile, generation) REFERENCES generations,
  FOREIGN KEY(repository, environment, name, artifact_id) REFERENCES artifacts(repository, environment, name, artifact_id)
) STRICT;

CREATE TABLE requests (
  profile TEXT NOT NULL REFERENCES profiles, repository TEXT NOT NULL, environment TEXT NOT NULL,
  name TEXT NOT NULL CHECK(length(name) > 0), requested INTEGER NOT NULL CHECK(requested IN (0,1)),
  PRIMARY KEY(profile, repository, name),
  FOREIGN KEY(repository, environment) REFERENCES scopes
) STRICT;

CREATE TABLE holds (
  profile TEXT NOT NULL, repository TEXT NOT NULL, name TEXT NOT NULL,
  reason TEXT NOT NULL,
  PRIMARY KEY(profile, repository, name),
  FOREIGN KEY(profile, repository, name) REFERENCES requests
) STRICT;

CREATE TABLE runtime_defaults (
  profile TEXT NOT NULL REFERENCES profiles, runtime TEXT NOT NULL CHECK(length(runtime) > 0),
  stream TEXT NOT NULL CHECK(length(stream) > 0),
  PRIMARY KEY(profile, runtime)
) STRICT;

CREATE TABLE history (
  operation_id TEXT PRIMARY KEY CHECK(length(operation_id) = 32 AND length(CAST(operation_id AS BLOB)) = 32 AND operation_id NOT GLOB '*[^0-9a-f]*'),
  sequence INTEGER NOT NULL UNIQUE CHECK(sequence > 0),
  command TEXT NOT NULL, occurred_at INTEGER NOT NULL CHECK(occurred_at >= 0),
  outcome TEXT NOT NULL CHECK(outcome IN ('committed','rolled-back','needs-attention')),
  before_digest TEXT REFERENCES objects(digest), after_digest TEXT REFERENCES objects(digest),
  record_digest TEXT NOT NULL REFERENCES objects(digest)
) STRICT;

CREATE TABLE gc_roots (
  kind TEXT NOT NULL CHECK(kind IN ('transaction','protected','process','launch','execution','backup')),
  reference_id TEXT NOT NULL, repository TEXT NOT NULL, environment TEXT NOT NULL, artifact_id TEXT NOT NULL,
  expires_at INTEGER CHECK(expires_at >= 0),
  PRIMARY KEY(kind, reference_id, repository, environment, artifact_id),
  FOREIGN KEY(repository, environment, artifact_id) REFERENCES artifacts
) STRICT;

CREATE INDEX bindings_provider ON bindings(dependency_repository, dependency_environment, dependency_artifact);
CREATE INDEX members_artifact ON members(repository, environment, artifact_id);
CREATE INDEX gc_artifact ON gc_roots(repository, environment, artifact_id);
CREATE VIEW installed AS
 SELECT m.*, COALESCE(r.requested,0) AS on_request FROM members m
 JOIN active_generations a USING(profile,generation)
 LEFT JOIN requests r USING(profile,repository,name);
CREATE VIEW retained_artifacts AS
 WITH RECURSIVE roots(repository,environment,artifact_id) AS (
 SELECT repository,environment,artifact_id FROM members
 UNION SELECT repository,environment,artifact_id FROM gc_roots
 UNION SELECT b.dependency_repository,b.dependency_environment,b.dependency_artifact
 FROM bindings b JOIN roots r USING(repository,environment,artifact_id))
 SELECT * FROM roots;

COMMIT;
