# C++ platform rehearsal

The harness exercises the real C++ fixture lifecycle through a persistent
filesystem model, fault injection, evidence capture, and replay. It does **not**
implement the full aslice design.
The full suite returns failure because mandatory coverage is missing. The
inventory uses explicit reviewed requirement records in `tests/requirements`.
Unreviewed source ranges remain blocking; discovery gives no coverage credit.

Build with the repository's existing CMake configuration. The build produces
`aslice`, `aslice-rehearsal`, and, when testing is enabled, `rehearsal_driver`.
`aslice-rehearsal` links the same CLI library as `aslice`. The normal executable
does not link the simulator transport and cannot select it through an
environment variable. Rehearsal uses the shared command registry, including fixture resolution,
manifest inspection and payload verification, and slice packing and inspection.
Their filesystem operations use the selected C++ platform interface.

The CLI, store and generation code use an explicitly supplied `FileSystem`.
Native POSIX builds and rehearsal use the same C++ package selection, validation,
store import, activation, upgrade, rollback and removal code. Target paths have
POSIX syntax on every host; only the native adapter converts them to host paths.
Native Windows inspection maps drive paths to target paths inside the adapter;
UNC paths are refused. Native Windows prefix operations remain unavailable. Their rehearsal counterpart
does not require Windows symlink privileges.

Run from the repository root, using a new, empty workspace:

```sh
python -m tools.rehearsal run --suite fixture --workspace build/rehearsal --seed 17 --aslice build/native/aslice-rehearsal
python -m tools.rehearsal client --workspace build/rehearsal --aslice build/native/aslice-rehearsal -- dev fixture history --prefix /work/prefix
python -m tools.rehearsal replay --workspace build/replayed --trace build/rehearsal/evidence/process-1.json --aslice build/native/aslice-rehearsal
python -m tools.rehearsal coverage --json
python -m tools.rehearsal coverage --gate development --output build/requirement-coverage.json
```

On Windows, use the executable in `build/windows-clion` with its `.exe` suffix.
`client` preserves the executable's output and exit status. `coverage --json`
returns 1 while mandatory coverage is incomplete. `run --suite fixture` seeds
catalogs under simulated `/inputs`, then runs installation through removal and
checks a power-loss restart. Fixture/full runs require a fresh `/work/prefix`.
`run --suite full` runs the foundation and fixture checks, emits the coverage
inventory, and returns 1. It cannot report
completion by ignoring unavailable scenarios.
It accepts `--native-evidence PATH` for receipt ingestion, but currently grants no
physical qualification credit because authority verification is not implemented.
The development coverage gate checks inventory consistency while the default
release gate also reports all missing implementation, tests, and qualification.

`ctest --test-dir BUILD --output-on-failure` includes independent rehearsal
tests. They run the actual C++ driver against the service, checking content and
namespace durability independently, refusal before and after effects, lost
acknowledgements, persistent outcome lookup, power loss, normalization
collisions, permissions, protected paths, disk exhaustion, credentials, and
replay divergence. Lifecycle tests execute C++ commands on both hosts and check
external lock contention, activation interruption, actual child-process
termination, lost acknowledgements and durable recovery of an idempotent
activation. They inspect payload bytes and links without claiming to execute
installed Mach-O programs. The native Linux fixture tests still execute portable
shell payloads.

The `rehearsal-inspection` CTest verifies canonical manifest identities, payload
hashes, sizes, permissions, hard-link refusal, relocation bytes across read
boundaries, archive packing/inspection, malformed archives, and replay. It also
checks simulated catalog resolution and read failures. File verification hashes
streamed chunks and checks relocations in the same pass. Rehearsal checks POSIX
modes even when the harness host is Windows. Native Windows inspection reports
that POSIX modes were not verified.

The separate `solver-oracle` CTest enumerates every assignment for 100 small
catalogs, then checks the real C++ resolver's satisfiability result and selected
closure. It covers exact/wildcard constraints, missing dependencies, target
filtering and cycles. It does not qualify provider, revision or variant semantics.
The coverage report maps these bounded scenarios to their C++ components;
declared mappings are separate from execution evidence.

## State and protocol

Each workspace has `os`, `application`, `inputs`, `sessions`, and `evidence`
directories. Simulated application files live under `/work` in the OS model;
`application` is reserved for future database adapters. `/inputs` contains
harness-supplied immutable fixtures, independent of application state. The Python
model never issues application SQL. Workspaces
are exclusively leased using host file locks. Existing links, junctions and
hardlinks are refused. This is a controlled test workspace, not a sandbox for
arbitrary executables or hostile concurrent host processes.

Connections use IPv4 loopback and a single-use 256-bit bearer token bound to a
harness-issued process identity and capability set. The session descriptor is
removed after execution. The token authenticates the issued identity; it does
not attest the host PID. Messages use a four-byte, big-endian length followed by
UTF-8 JSON, with a 1 MiB frame limit, duplicate-key rejection, and bounded JSON
depth. Protocol version 1 requests contain `id`, `capability`, `operation`,
`arguments`, and `preconditions`. Unimplemented preconditions are refused.
Responses separately record `result`, `effects`, `receipt`, and `failure`.
The C++ caller retains effects even when an operation fails.

The initial model provides file creation, positional writes, reads, directory
creation/listing, symlinks without traversal, rename, mode changes, removal, exclusive locks,
file/directory flushes, machine observations, a logical clock, and outcome
lookup. It records ownership, modes, empty ACL/xattr fields, and one volume
identity. Open-file handles bind the process, access mode, and inode. Read handles retain
the opened inode after rename or unlink; write handles remain writable after
creating a read-only file. A read handle cannot authorize writes or flushes.
Setting `maximum_read` to a positive byte count models short reads. The C++
consumer continues until EOF and enforces its total byte limit. Native POSIX reads open each ancestor with `openat` and `O_NOFOLLOW`, then
check file type, size, link count, and mode on the opened descriptor. Native
Windows reads hold a handle that denies concurrent writes and deletes and rejects
reparse-point files; ancestor checks are still pathname checks on Windows.
POSIX creation, enumeration, rename, unlink, synchronization, and lock acquisition
also use opened parent directories. These operations refuse symlinked ancestors;
they do not yet establish the complete owner, ACL, volume, and protected-path
contracts or macOS durability qualification. Directory listings preserve spelling while matching names
through NFD/casefold. ACL/xattr semantics, complete permission checks, and native
APFS/HFS+ name behavior remain unimplemented. NFD plus Python casefold is an
explicit approximation. It must not qualify actual macOS filename behavior.

The harness can configure faults in `Model.state["faults"]` before launching a
process. Each entry selects a logical `tick` or a named `checkpoint`, and a
`kind`: `before`, `after`, `lost_ack`, `terminate`, or `power_loss`. The fixture
declares `before-switch` and `after-switch` activation checkpoints. Each fault
fires once. This schedule is included in the initial-state
evidence and replayed. Power loss discards unflushed data and namespace changes;
process exit alone preserves them. `terminate` kills the actual harness-launched
child process; `power_loss` also kills all children registered with that service
and disconnects its clients. Restarted commands reconcile observed target state
in C++. The fixture can finish a lost-acknowledgement activation when a repeated
mutation verifies the active generation and flushes its profile directory.
Interrupted store imports can still leave staging entries that require a fresh
disposable prefix; production journal recovery is not implemented.
No write is retried automatically. Duplicate operation IDs are refused, and
the `outcome` capability queries a recorded result. These simulator audit
records are not application recovery records.
Setting `Model.state["maximum_write"]` to a positive byte count exercises short
writes. The C++ adapter must loop over the actual returned counts; the model
stores only bytes actually written.

## Evidence and remaining work

Evidence includes the source revision and dirty flag, an owned-source digest,
executable digest, host, simulated target, mode, seed, arguments, output bytes,
exit status, initial/final OS state, and every authenticated platform request
and response. Tokens are excluded. Replay runs C++ again from the recorded
initial state and compares requests, effects, state and output. Text stream
comparison normalizes CRLF to LF; original bytes remain in evidence. Process
termination is compared by recorded cause, since kill exit codes differ between
Windows and POSIX. Evidence files are never overwritten by later runs of the
same process identity.

The source digest covers owned C++ and rehearsal code, tests and fixtures, embedded SQL schemas,
CMake configuration, and the dependency manifest. It does not cover the entire
toolchain or downloaded dependency closure. Revision and dirty status are null in source exports
without Git metadata; such evidence cannot establish source revision provenance.
The foundation check is a single portable CLI assertion;
it does not establish lifecycle coverage. Generated reports live under the
selected workspace's `evidence` directory.

Next work is to finish requirement review and owning-specification mappings,
introduce the remaining native/target platform adapters, including complete
filesystem metadata/authority enforcement and bounded platform clocks.
The simulator SQLite VFS, production package transactions and recovery,
services, builds, signing, publication, Homebrew corpus, disaster operations,
and OS matrix all remain mandatory gaps. `coverage.py` lists these explicitly.
Physical durability, native macOS API compatibility, containment, and worker
qualification require separate real-Mac evidence.
