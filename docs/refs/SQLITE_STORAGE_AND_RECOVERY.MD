# SQLite storage, compatibility, and recovery

## Source identity

- Original sources: official SQLite [WAL](https://sqlite.org/wal.html), [PRAGMAs](https://sqlite.org/pragma.html), [backup API](https://sqlite.org/backup.html), [corruption recovery](https://sqlite.org/recovery.html), [STRICT tables](https://sqlite.org/stricttables.html), [security guidance](https://sqlite.org/security.html), and [authorizer API](https://sqlite.org/c3ref/set_authorizer.html).
- Author/publisher: SQLite developers; no individual authorship is asserted for these manuals.
- Source version/date: live documentation snapshot retrieved 2026-09-26 UTC. WAL page states last updated 2026-08-25 19:42:39Z; other immutable page revision identifiers were not recovered. Feature/fix versions are identified below rather than inferred from the retrieval date.
- Retrieved: 2026-09-26 UTC through the web reader; all seven source pages successfully retrieved and relevant passages compared. No complete source-byte capture is claimed.
- Capture type: attributed technical account in original wording, with source locators; no verbatim quotations or source assets.
- Rights: SQLite documentation authors retain any applicable rights. This record paraphrases technical facts and links the originals; it does not claim permission to redistribute the complete website or apply the software's public-domain status automatically to page assets.
- Used by: [DATABASE connection and migration policy](../DATABASE.md#10-sqlite-connection-and-migration-policy) for the fixed bundled build, WAL, synchronization, schema compatibility, and query controls; [backup and restore](../DATABASE.md#11-backup-sets-and-restore) for consistent copies and the limits of salvage.

## Captured material

### WAL and its corruption fix

Source locators: WAL, sections 1, 2.1–2.3, 4, 6, and 11. This is a paraphrase.

WAL requires same-host shared memory and is unsuitable for network filesystems.
Transactions across attached WAL databases are individually atomic, not atomic as
a group. Readers retain an end mark while a writer appends; only one writer runs
at a time. Long readers can prevent checkpoint completion. The usual automatic
checkpoint threshold is 1,000 pages. The WAL file holds persistent committed state;
separating it from the main file can lose data or corrupt the database.

The page identifies the WAL-reset race as affecting releases through 3.51.2 and
fixed in 3.51.3, with backports 3.44.6 and 3.50.7. Multiple connections racing a
checkpoint and a write can cause later checkpoints to omit committed pages. Its
rarity is not a durability guarantee. This supports requiring a patched build,
not assuming that WAL mode alone protects every SQLite release.

### Synchronization and validation settings

Source locators: PRAGMA entries `synchronous`, `foreign_keys`, `fullfsync`,
`checkpoint_fullfsync`, `integrity_check`, and `foreign_key_check`. Paraphrase.

In WAL mode, FULL adds synchronization at transaction commit; NORMAL can lose a
recent committed transaction after power loss. Filesystem and hardware behavior
remain relevant. Foreign-key enforcement must be enabled per connection, outside
an active transaction. Integrity checking and foreign-key checking are separate
checks. `fullfsync` requests the macOS F_FULLFSYNC mechanism; its default is off.
`checkpoint_fullfsync` applies that mechanism at checkpoints where supported; when
fullfsync already applies to all synchronization, the checkpoint setting is
irrelevant. These switches do not establish that a particular disk honors flushes.

### Consistent backup

Source locators: Backup API, sections 1 and 3. Paraphrase.

The online backup API copies between database connections and can work
incrementally, limiting how long other users are blocked. A completed operation
provides a consistent snapshot. Callers must handle locking and API errors and
check completion. Copying a live main file outside the API has concurrency and
interruption hazards. The page also identifies VACUUM INTO as an alternative.
Neither method captures application journals, filesystem pointers, signing keys,
or external objects automatically; the project's coordinated manifest is an
application requirement beyond SQLite's backup contract.

### Corruption recovery limits

Source locators: Recovering Data From A Corrupt SQLite Database, sections 1.1 and 2.
Paraphrase.

Salvage may omit data, resurrect deleted values, change values or types, move
content to the wrong table, and violate constraints. Perfect restoration is
possible in some cases, but recovered output remains suspect. The CLI `.recover`
facility can extract material for further analysis. This is unsuitable as proof of
trusted signing reservations, grants, or committed operation history; those require
independent evidence and validation.

### Schema compatibility

Source locators: STRICT Tables, sections 2 and 4. Paraphrase.

STRICT tables require SQLite 3.37.0 or later. Each column has an allowed declared
type, and values must be losslessly convertible to that type unless ANY is used.
Integrity checks include strict type validation. The on-disk representation remains
compatible in layout, but older parsers generally reject the schema keyword.
The documented writable_schema workaround is not safe reader compatibility for
aslice; the project refuses unsupported readers rather than bypassing validation.

### Untrusted query controls

Source locator: Defense Against The Dark Arts, section 1.1. Paraphrase.

SQLite recommends defensive mode and lower resource limits when accepting
untrusted SQL. Limiting statement size, expression depth, attached databases, and
execution reduces attack surface and denial-of-service exposure. SQLite's input
validation and fuzzing are useful defenses, not proof that an application has a
correct authorization policy. The project's deadlines, output caps, and fixed
function allowlist are local policy choices requiring their own tests.

Source locator: Compile-Time Authorization Callbacks, `sqlite3_set_authorizer` API
description. Paraphrase.

The connection authorizer runs during statement preparation. SQLITE_DENY rejects
the statement; SQLITE_IGNORE may continue with altered behavior, such as replacing
a read column with NULL. Only one authorizer is installed per connection, and it
is disabled by default. The API explicitly supports restricting user SQL to reads.
Implementers must account for null callback arguments and preserve authorization
through statement recompilation. An application accepting SQL needs this explicit
policy rather than checking the first word of a statement.

## Applicability and limits

These are SQLite mechanisms, not macOS 10.11–12, HFS+/APFS, Pi, or aslice acceptance
results. The project uses schema version 1 and selects a fixed mainline baseline
of 3.51.3; a production artifact must additionally pin source bytes, source ID,
compiler options, VFS, and build provenance. No installed SQLite binary is supplied
by this record.

## Project interpretation

Separate owner databases, durable records outside SQLite, staging restores, and
copy migrations are project decisions. They combine SQLite's per-database
guarantees with the existing recovery state machine. SQLite does not authorize
privileged effects or authenticate backup manifests. The related
[TUF record](THE_UPDATE_FRAMEWORK_SPECIFICATION.MD) continues to govern metadata
trust; rebuilding a database cannot reset it.

## Omissions and evidence gaps

Full HTML, diagrams, sample C programs, the SQLite amalgamation, upstream test
suites, VFS implementation details, and linked third-party race reproductions are
not archived. The account covers the relied-upon design facts without claiming a
complete API reference. A pinned source/build artifact and actual filesystem,
power-loss, adversarial-query, and disaster-recovery transcripts remain launch
gates. Live pages cannot prove their content at an earlier date.

## Preservation

This is a new dated account, with no previous edition replaced and no source assets
transformed. Its exact bytes are covered by SHA256SUMS. Catalog and inventory
coverage identify it as a technical account, not a complete original. Future
changes must retain relied-upon fix/version evidence and record comparison dates.
