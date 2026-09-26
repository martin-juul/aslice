% ASLICE-DB(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-db — inspect, maintain, compact, back up, and restore an aslice database role

# SYNOPSIS

`aslice db list` [`--role` *role*] [`--json`]

`aslice db` [`--role` *role*] [`--prefix` *path* | `--instance` *id*] `schema` [`--live`]

`aslice db` [*selectors*] `query` *SQL* [`--json`]

`aslice db` [*selectors*] `check` [`--json`]

`aslice db` [*selectors*] `maintain` [`--dry-run`] [`--json`]

`aslice db` [*selectors*] `compact` [`--dry-run`] [`--json`]

`aslice db` [*selectors*] `backup` *destination* [`--json`]

`aslice db` [*selectors*] `restore` *set* [`--dry-run` | `--confirm` *preview-digest*] [`--json`]

`aslice recover` [`--role` *role*] [`--prefix` *path* | `--instance` *id*]

# DESCRIPTION

This is a specified interface; the commands are not implemented yet. Database
maintenance follows [DATABASE](../docs/DATABASE.md), which owns the schemas and
recovery procedures.

Select one of `client-state`, `client-cache`, `system-state`, `coordinator`,
`publisher`, or `release-signer`. The default is `client-state` in the selected
prefix. List shows all configured instances visible to the caller unless filtered.
`--prefix` selects a client instance; `--instance` selects a configured system or
service instance. Conflicting selectors are refused. Selecting a role grants no
additional permissions.

Schema shows the shipped DDL; `--live` inspects the selected database. Query runs
one bounded read-only SQL statement against a consistent inspection snapshot.
Check validates identity, schema, integrity, foreign keys, references, durable
record continuity, and domain invariants. These commands never repair state.

Maintain runs eligible cleanup in batches of at most 100 rows, bounded
optimization, lightweight checks, and checkpoint work. It reports deferred tasks;
age never authorizes deleting protected references or retained history. Compact
explicitly reclaims file space through a coordinated versioned copy: snapshot,
vacuum staging, validate equivalence/references, then journal activation. It retains
the original and recovery entry point. Both accept `--dry-run` without writes.
Compaction reports snapshot, workspace, retained-original, and free-space estimates
before work and refuses insufficient space. Interruption follows activation recovery.
Check also reports maintenance attempts, successes, outcomes, deferred reasons,
freelist pages, and estimated reclaimable bytes (not guaranteed savings).

Automatic maintenance uses a 100 ms interruptible work budget after successful
mutations and in existing service idle loops. It never waits for locks or requests
elevation solely for housekeeping. Synchronization is not a hard wall-clock bound.
Cleanup is due hourly, optimization daily, and a lightweight check weekly. PASSIVE
checkpoints that cannot finish remain deferred. No automatic vacuum or new client
daemon is introduced; `auto_vacuum=NONE` leaves deleted pages available for reuse.

Backup runs as the selected owner and writes a new backup set, including a
consistent SQLite snapshot and a manifest of records and evidence. Protected
participants remain separately protected. The result identifies missing
participants; an incomplete set is not a successful disaster-recovery backup.
Copy verified complete sets to independent storage at another location.

Restore validates into staging, previews changes, and invokes recovery before
activating a database/manager pair. It preserves the damaged originals and old
pair. `--dry-run` prints the preview digest. `--confirm` authorizes that exact
preview; changes to the base invalidate it. Interactive restore without the flag
asks for confirmation after showing the preview. Noninteractive restore refuses
without `--confirm`. There is no flag to bypass missing evidence, stale history,
trust checks, or external-edit conflicts.

Recover reconstructs projections from intact durable records and resolves
interrupted operations. It discovers protected participants and requires their
authorization. Rebuilding the cache never resets retained trust. Missing trust
requires explicit trust recovery, not a fresh TOFU decision.

# QUERY LIMITS AND REFUSALS

Query permits SELECT statements, including read-only CTEs, views, and approved
side-effect-free built-in functions. It refuses multiple statements, writes, DDL,
ATTACH/DETACH, PRAGMAs, transaction control, extension loading, and file/network
functions. Execution is limited to 5 seconds, 10,000 rows, and 16 MiB of output;
exceeding a limit returns failure and discards partial rows.

Busy interactive commands show owner information and offer wait or exit.
Unattended commands wait only with **--wait**; a configured timeout
alone does not authorize waiting. Lock waiting is separate from query execution. The common `--lock-timeout DURATION`
option overrides `db.lock_timeout = "30s"`; use a nonnegative integer with `ms`, `s`,
or `m`, including `0s` for no waiting. Count cumulative owner and SQL lock waits;
useful work does not consume the allowance. Progress starts after one second and
updates every five seconds with role, operation, elapsed wait, and owner (or unknown).
Cancellation requests safe resolution, with one separate 30-second recovery wait
allowance. Committed work reconciles forward; unresolved recovery retains journals,
backups, and roots and blocks conflicting mutations while unaffected working
packages and external repair tools remain usable. After waiting or recovery,
revalidate the plan and reconfirm material changes. See
[DATABASE §10.1](../docs/DATABASE.md#101-contention-and-safe-stopping).
Normal commands can bypass a busy cache using authenticated inputs in memory and
skip cache writes; explicit cache inspection/maintenance reports contention.
Inspection of a missing database never creates it.

Unsupported schemas, wrong role/instance identities, invalid ownership, incomplete
records, stale backups without a continuous suffix, missing before-images, and
conflicting external edits are refused with a concrete remedy. Restoring a signing
database cannot establish an uncertain version high-water mark. SQLite salvage
output is evidence, not an approved restore source.

# EXAMPLES

```sh
aslice db list --json
aslice db schema
aslice db query 'SELECT profile,repository,name,artifact_id FROM installed'
aslice db --role client-cache check --json
aslice db --role client-state backup /Volumes/Backup/aslice/prefix-set-001
aslice db restore /Volumes/Backup/aslice/prefix-set-001 --dry-run --json
# Use the complete digest emitted by the preview:
aslice db restore /Volumes/Backup/aslice/prefix-set-001 --confirm "$preview_digest"
aslice recover --role client-state
aslice db --role publisher --instance orchard-publisher check --json
```

# OUTPUT

Human output uses tables with diagnostics on stderr. `--json` emits one version-1
object with `command`, `role`, `instance_id`, `status`, `data`, and `errors`.
Statuses are `ok`, `refused`, `needs-attention`, and `error`. Errors include stable
`code`, `message`, and `remedy`, plus a path where relevant.

Timeout/cancellation diagnostics in `data` include `phase`, `committed`,
`recovery_required`, and `retry_safe`, as defined by DATABASE. A committed operation
with pending recovery is never reported as an unchanged or safely retryable mutation.

Query data uses positional rows and ordered column names, preserving duplicate
column names. Null remains null; BLOB values use base64 `bytes` objects; integers
outside JSON's safe range become decimal strings. `truncated` identifies exceeded
limits. Backup output includes manifest digest, boundary heads, byte counts,
completeness, and missing participants. Restore preview binds the set digest,
current heads, identities, ownership mapping, affected paths, and effects.

# EXIT STATUS

0 success; 1 failed check, I/O failure, or needs-attention; 2 usage, unsafe SQL, or
unsupported schema; 3 authorization or confirmation refusal; 4 busy or changed
base without unresolved recovery; 130 safely completed cancellation. Recovery-required
outcomes exit 1; busy optional maintenance preserves foreground success. A partial
backup or failed check never exits successfully.

# FILES

`<prefix>/db/state.sqlite`, `<prefix>/cache/db/cache.sqlite`
:   Client state and disposable cache; SQLite owns their WAL/SHM sidecars.

`/Library/Application Support/aslice/system/db/state.sqlite`
:   Helper-owned protected projection.

`<coordinator>/db/coordinator.sqlite`, `<publisher>/db/publisher.sqlite`, `<signer>/db/signer.sqlite`
:   Service-owned local databases; roots come from protected provisioning configuration.

`records/`, `trust/`, transaction journals, and referenced immutable objects
:   Separate reconstruction and authority material. Their required contents belong
    in a coordinated backup set; a database file alone is insufficient.

# SEE ALSO

aslice(1), aslice-doctor(1), aslice-gc(1), aslice-repo(1),
[DATABASE](../docs/DATABASE.md),
[STATE-AND-RECOVERY](../docs/STATE-AND-RECOVERY.md),
[KEY-RUNBOOK](../docs/runbooks/KEY-RUNBOOK.md)
