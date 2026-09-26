-- aslice publisher, schema 2. Execute only in a new, owner-controlled file.
-- Connection policy and semantic validation: ../DATABASE.md.
PRAGMA application_id = 1095977989;
PRAGMA user_version = 2;
PRAGMA auto_vacuum = NONE;
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
PRAGMA trusted_schema = OFF;
BEGIN IMMEDIATE;
CREATE TABLE database_identity (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
  role TEXT NOT NULL CHECK(role = 'publisher'),
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

CREATE TABLE candidates (
  repository TEXT NOT NULL, environment TEXT NOT NULL,
  candidate_digest TEXT NOT NULL REFERENCES objects(digest),
  inventory_digest TEXT NOT NULL REFERENCES objects(digest),
  base_digest TEXT REFERENCES objects(digest), authorization_digest TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(repository,environment,candidate_digest),
  UNIQUE(repository,environment,candidate_digest,inventory_digest),
  FOREIGN KEY(repository,environment) REFERENCES scopes
) STRICT;

CREATE TABLE promotions (
  repository TEXT NOT NULL, source_environment TEXT NOT NULL, destination_environment TEXT NOT NULL,
  source_candidate TEXT NOT NULL, destination_candidate TEXT NOT NULL, inventory_digest TEXT NOT NULL,
  receipt_digest TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(repository,destination_environment,destination_candidate),
  CHECK((source_environment = 'dev' AND destination_environment = 'staging') OR
        (source_environment = 'staging' AND destination_environment = 'prod')),
  FOREIGN KEY(repository,source_environment,source_candidate,inventory_digest)
    REFERENCES candidates(repository,environment,candidate_digest,inventory_digest),
  FOREIGN KEY(repository,destination_environment,destination_candidate,inventory_digest)
    REFERENCES candidates(repository,environment,candidate_digest,inventory_digest)
) STRICT;

CREATE TABLE publication_queue (
  repository TEXT NOT NULL, environment TEXT NOT NULL, queue_sequence INTEGER NOT NULL CHECK(queue_sequence > 0),
  candidate_digest TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('release','renewal','timestamp')),
  state TEXT NOT NULL CHECK(state IN ('pending','ready','activated','stale','failed')),
  PRIMARY KEY(repository,environment,queue_sequence), UNIQUE(repository,environment,candidate_digest),
  FOREIGN KEY(repository,environment,candidate_digest) REFERENCES candidates
) STRICT;

CREATE TABLE fencing (
  repository TEXT NOT NULL, environment TEXT NOT NULL, epoch INTEGER NOT NULL CHECK(epoch > 0),
  holder TEXT NOT NULL, expires_at INTEGER NOT NULL CHECK(expires_at >= 0),
  active_snapshot TEXT REFERENCES objects(digest),
  PRIMARY KEY(repository,environment), FOREIGN KEY(repository,environment) REFERENCES scopes
) STRICT;

CREATE TABLE timestamp_reservations (
  repository TEXT NOT NULL, environment TEXT NOT NULL, version INTEGER NOT NULL CHECK(version > 0),
  candidate_digest TEXT NOT NULL, bytes_digest TEXT NOT NULL REFERENCES objects(digest),
  state TEXT NOT NULL CHECK(state IN ('reserved','signed','consumed')),
  signed_digest TEXT REFERENCES objects(digest), CHECK(state <> 'signed' OR signed_digest IS NOT NULL),
  PRIMARY KEY(repository,environment,version),
  UNIQUE(repository,environment,version,candidate_digest),
  FOREIGN KEY(repository,environment,candidate_digest) REFERENCES candidates
) STRICT;

CREATE TABLE activations (
  repository TEXT NOT NULL, environment TEXT NOT NULL, candidate_digest TEXT NOT NULL,
  epoch INTEGER NOT NULL CHECK(epoch > 0), timestamp_version INTEGER NOT NULL,
  snapshot_digest TEXT NOT NULL REFERENCES objects(digest), receipt_digest TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(repository,environment,candidate_digest),
  FOREIGN KEY(repository,environment,candidate_digest) REFERENCES candidates,
  FOREIGN KEY(repository,environment,timestamp_version,candidate_digest)
    REFERENCES timestamp_reservations(repository,environment,version,candidate_digest)
) STRICT;

CREATE TABLE acknowledgements (
  repository TEXT NOT NULL, environment TEXT NOT NULL, candidate_digest TEXT NOT NULL,
  receipt_digest TEXT NOT NULL REFERENCES objects(digest), PRIMARY KEY(repository,environment,candidate_digest),
  FOREIGN KEY(repository,environment,candidate_digest) REFERENCES activations
) STRICT;

CREATE INDEX publication_ready ON publication_queue(state,repository,environment,queue_sequence);
CREATE VIEW publication_status AS SELECT q.*,a.snapshot_digest,k.receipt_digest AS acknowledgement
 FROM publication_queue q LEFT JOIN activations a USING(repository,environment,candidate_digest)
 LEFT JOIN acknowledgements k USING(repository,environment,candidate_digest);

COMMIT;
