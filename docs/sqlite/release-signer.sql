-- aslice release-signer, schema 1. Execute only in a new, owner-controlled file.
-- Connection policy and semantic validation: ../DATABASE.md.
PRAGMA application_id = 1095977990;
PRAGMA user_version = 1;
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
PRAGMA trusted_schema = OFF;
BEGIN IMMEDIATE;
CREATE TABLE database_identity (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
  role TEXT NOT NULL CHECK(role = 'release-signer'),
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

CREATE TABLE candidates (
  repository TEXT NOT NULL, environment TEXT NOT NULL,
  candidate_digest TEXT NOT NULL REFERENCES objects(digest),
  inventory_digest TEXT NOT NULL REFERENCES objects(digest),
  base_digest TEXT REFERENCES objects(digest), authorization_digest TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(repository,environment,candidate_digest),
  UNIQUE(repository,environment,candidate_digest,inventory_digest),
  FOREIGN KEY(repository,environment) REFERENCES scopes
) STRICT;

CREATE TABLE reservations (
  repository TEXT NOT NULL, environment TEXT NOT NULL, metadata_role TEXT NOT NULL CHECK(metadata_role IN ('targets','snapshot')),
  version INTEGER NOT NULL CHECK(version > 0), candidate_digest TEXT NOT NULL,
  bytes_digest TEXT NOT NULL REFERENCES objects(digest),
  state TEXT NOT NULL CHECK(state IN ('reserved','signed','consumed')),
  PRIMARY KEY(repository,environment,metadata_role,version),
  UNIQUE(repository,environment,candidate_digest,metadata_role),
  UNIQUE(repository,environment,metadata_role,version,candidate_digest),
  FOREIGN KEY(repository,environment,candidate_digest) REFERENCES candidates
) STRICT;

CREATE TABLE signing_outcomes (
  repository TEXT NOT NULL, environment TEXT NOT NULL, candidate_digest TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK(outcome IN ('pending','signed','rejected','consumed')),
  record_digest TEXT NOT NULL REFERENCES objects(digest), PRIMARY KEY(repository,environment,candidate_digest),
  FOREIGN KEY(repository,environment,candidate_digest) REFERENCES candidates
) STRICT;

CREATE TABLE signed_metadata (
  repository TEXT NOT NULL, environment TEXT NOT NULL, metadata_role TEXT NOT NULL, version INTEGER NOT NULL,
  candidate_digest TEXT NOT NULL, signed_digest TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(repository,environment,metadata_role,version),
  FOREIGN KEY(repository,environment,metadata_role,version,candidate_digest)
    REFERENCES reservations(repository,environment,metadata_role,version,candidate_digest)
) STRICT;

CREATE TABLE slice_signatures (
  repository TEXT NOT NULL, environment TEXT NOT NULL, candidate_digest TEXT NOT NULL,
  blob_digest TEXT NOT NULL REFERENCES objects(digest), signature_digest TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(repository,environment,candidate_digest,blob_digest),
  FOREIGN KEY(repository,environment,candidate_digest) REFERENCES candidates
) STRICT;

CREATE TABLE publication_acknowledgements (
  repository TEXT NOT NULL, environment TEXT NOT NULL, candidate_digest TEXT NOT NULL,
  snapshot_digest TEXT NOT NULL REFERENCES objects(digest), receipt_digest TEXT NOT NULL REFERENCES objects(digest),
  PRIMARY KEY(repository,environment,candidate_digest),
  FOREIGN KEY(repository,environment,candidate_digest) REFERENCES candidates
) STRICT;

CREATE INDEX signing_pending ON signing_outcomes(outcome);
CREATE VIEW version_high_water AS SELECT repository,environment,metadata_role,MAX(version) AS version
 FROM reservations GROUP BY repository,environment,metadata_role;

COMMIT;
