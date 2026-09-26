# aslice Helpers and Background Services

- **Status:** Specification v0.4 — September 2026. This reference describes the client design; it does not establish completed implementation or validation on macOS.
- **Authority:** [DESIGN](DESIGN.md) defines the process roles. [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md) owns privileged storage, authorization, transactions, and recovery; [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md) owns protected-volume operations.

<a id="what-runs-and-for-how-long"></a>

## 1. What runs, and for how long

The aslice client starts helpers for individual operations. Fetching, extraction,
building, and linking run in separate processes with the capabilities their phases
need. Privileged work goes through a separately protected helper, authorized for
each operation. The current design requires no persistent aslice daemon and no
setuid binary.

A package can also provide a service, such as PostgreSQL. Once registered, that
service runs under launchd and can remain running after the aslice command exits.
It is package software, not an aslice helper. A runtime shim has a third lifecycle:
it selects an installed runtime and replaces itself with that program.

The names below identify documented process roles, not a public helper command
interface. [DESIGN §5.1](DESIGN.md#51-process-layout) describes the main binary
re-executing itself with a subcommand to create the ordinary helpers. This
reference does not assign separate installed executables or invocation syntax to
those roles. The protected installation requirement for `aslice-system` is
explicit and is described in §3.

<a id="component-inventory"></a>

## 2. Component inventory

The four ordinary helpers are spawned by the unprivileged client or its build
harness for the relevant phase; their lifetime is the operation or phase, not a
background service registration. Their restrictions come from
[DESIGN §10.5](DESIGN.md#105-sandboxed-builds) and the
[build pipeline](BUILD-INFRA.md#3-the-pipeline-shared-at-both-scales).

| Role | Purpose and caller | Privileges and filesystem access | Network access |
|---|---|---|---|
| `aslice-fetch` | The client or build harness requests slices, metadata, or source inputs. | Unprivileged; writes only to the cache, with no store access. | Declared hosts only. |
| `aslice-extract` | The client or harness requests archive extraction, including vendor `.pkg` and `.dmg` payloads. | Unprivileged; writes confined to the phase's build or staging directory. Extraction does not run vendor installer scripts. | None. |
| `aslice-build` | The build harness runs Starlark build phases in this helper, spawning it with each phase's policy. | Unprivileged; build phases write within the build directory and read the pinned toolchain and dependencies through an isolated buildroot. The install phase writes to staging only. | None for build and staging; tests have no network by default, with a logged per-formula `test_network = true` exception. |
| `aslice-link` | The client delegates ordinary store/profile writes to this role when registering artifacts and preparing or switching generations. | Unprivileged; the designated writer of the ordinary user-owned store/profile. No compiler access. Protected root closures belong to `aslice-system`. | None. |
| `aslice-system` | The client requests a declared privileged operation; protected-volume work also uses the recovery kit's helper. Each invocation is authorized, with no resident helper daemon required. | Elevated; imports verified closures and maintains protected configuration, trust, journals, and backups. External writes are limited to authorized operations (§3). | The contracts do not specify a general network profile for this helper. Independent verification is required even when staging came from the client. |
| Runtime shim | A shell or another caller invokes a runtime/tool name. The shim resolves the selection and `exec`s the installed program, leaving no wrapper process. | No elevation step; reads the committed execution catalog, validates the selected closure and gate epoch, registers an execution lease, and supplies the declared per-stream userbase environment. | No network sandbox contract is specified for shim dispatch or the program it launches. |

Extraction follows authentication of the archive and checks the staged inventory
against the manifest. Path traversal, escaping links, special files, collisions,
and unbounded expansion are refused under the
[slice verification contract](SLICE-FORMAT.md#3-verification-and-extraction).
The build helper's phase policy does not grant access to the user's live profile;
the harness supplies the pinned dependency view.

The shim is the multicall mechanism described in
[DESIGN §12.9](DESIGN.md#129-multi-version-runtimes-use-pin-default--and-version-bound-extensions): a
hardlink to the aslice binary dispatches by the invoked name. Selection checks the
session, nearest project configuration, and profile default, in that order, then
uses the sole installed stream if there is exactly one. Otherwise it reports the
missing or ambiguous selection. The shim chooses among installed artifacts; it
does not install a runtime during dispatch. Services bind an exact runtime stream
through a versioned alias rather than following subsequent default changes.

The build sandbox is not a sandbox for installed applications. Once a shim has
executed a runtime or ecosystem tool, that program has its ordinary runtime
behavior. Ecosystem installs use per-stream userbases outside the immutable store;
aslice does not audit, snapshot, or garbage-collect those contents. See the
[runtime guide](MANUAL.md#6-managing-runtimes-php-python-ruby-node).

<a id="the-privileged-helper"></a>

## 3. The privileged helper

<a id="installation-and-authorization"></a>

### 3.1 Installation and authorization

`aslice-system` itself is installed from a verified release during explicit
elevation into `/Library/Application Support/aslice/system`. That protected root
is root-owned, with no unprivileged-writable ancestor or execution/configuration
directory. The ordinary aslice prefix remains user-owned.

Each invocation is authorized through the OS elevation mechanism and accepts a
fixed operation vocabulary. The helper validates paths and inputs independently
of the invoking user's SQLite database. Repository capabilities follow the effect:
a root daemon or kext needs `system`; replacing an Apple-provided path needs
`system-patch` and must satisfy its target restrictions. A graft or machine file
cannot bypass these checks. Required `--accept-system-changes` and
`--accept-grafts` gates accumulate; neither replaces the other or grants repository
capabilities. Elevations are logged as unsuppressible security events.

<a id="protected-code-and-dependencies"></a>

### 3.2 Protected code and dependencies

The helper treats incoming staging as untrusted. Before importing a complete
execution closure, it independently checks authenticated manifests, repository
capabilities, digests, and the authorized plan. It copies into newly created
root-owned directories, verifies the copied bytes, and atomically activates the
protected pointer.

The closure includes libraries, interpreters, plugins, launch configuration, and
executable search paths. Root execution never resolves through the ordinary
profile. The helper ignores user loader/search-path overrides and rejects
user-writable configuration that can load code. Root service overrides require an
authorized helper transaction; root does not load user-owned service environment
files. Writable service data and logs have separate root-controlled locations,
with narrower service-user ownership where explicitly required.

Protected trust records, journals, backups, plists, and the active pointer remain
outside the user's authority. Trust updates require authenticated transitions or
explicit administrator rebootstrap. Root rollback changes the protected pointer
through the helper under the same authorization as activation. These requirements
come from [STATE-AND-RECOVERY §3](STATE-AND-RECOVERY.md#3-privileged-ownership-and-capability-checks).

<a id="operations-covered-by-the-design"></a>

### 3.3 Operations covered by the design

The helper's supported operation classes are specified, but remain subject to the
enforcement and recovery acceptance gates:

- **Root services:** register and manage system-domain launchd jobs from protected
  closures, including authorized configuration changes and rollback. See the
  [service procedure](MANUAL.md#7-running-services).
- **System packages:** perform declared kext placement, ownership/permission
  repair, cache invalidation, and loading, subject to the package's security
  preconditions. See [DESIGN §12.7](DESIGN.md#127-system-software-kexts-and-sip-disabled-development-tools).
- **Certificate trust:** apply the signed certificate-policy inventory, record
  owned changes, and remove or restore only the entries/settings the ownership and
  conflict checks permit. See [STATE-AND-RECOVERY §9](STATE-AND-RECOVERY.md#9-certificate-trust-lifecycle).
- **System preferences and shell enrollment:** perform declared system-domain
  preference writes and `/etc/shells` enrollment with recorded before-values. See
  [the machine-setup procedure](MANUAL.md#103-applying-it).
- **System patches:** replace permitted targets with protected originals and
  dependency closures; use Recovery and boot-snapshot procedures where required.
  See [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). The user changes security settings in
  Recovery; aslice does not toggle them automatically.
- **Grafts:** commit the validated delta from an approved isolated staging run.
  The script receives no unrestricted live-root access; kext and daemon
  registration remain declarative helper operations. Network inputs are fetched
  and pinned before staging. See [STATE-AND-RECOVERY §4](STATE-AND-RECOVERY.md#4-graft-execution-boundary).

<a id="recovery-and-removal"></a>

### 3.4 Recovery and removal

Privileged operations hold the system-root lock after the prefix lock and record
durable before/after state in protected journals. A process exiting does not erase
that state. Surviving helpers retain effective mutation ownership until they stop
writing; recovery and manual repair wait for that quiescence. Unfinished recovery
blocks conflicting mutations and GC while unaffected packages and external repair
tools remain usable. Conflicting external edits produce `needs-attention` rather
than being overwritten. Package rollback
does not restore application databases. See
[STATE-AND-RECOVERY §5](STATE-AND-RECOVERY.md#5-durable-transactions-and-recovery).

Removal starts with `aslice decommission --dry-run` while the manager, trust
records, and backups still exist. `aslice decommission` authorizes and journals
service unregistration, supported graft/patch reversal, safe kext removal, owned
certificate cleanup, and restoration of the prior login shell and owned shell
enrollment. It also removes owned integration links and lists retained user data
and manual shell-integration cleanup.

Only successful cleanup permits prefix deletion. The helper removes root-owned
closures, receipts, and backups only when no other prefix or active operation
references them. Pending reboot, snapshot references, or conflicts preserve the
required recovery material. See [the removal procedure](MANUAL.md#25-removing-aslice)
and [STATE-AND-RECOVERY §6](STATE-AND-RECOVERY.md#6-self-update-and-decommission).

<a id="following-an-operation"></a>

## 4. Following an operation

An ordinary binary install resolves authenticated package metadata, fetches and
verifies the archives, extracts into bounded staging, verifies and materializes
the artifacts, then registers them and prepares a generation. `aslice-fetch`,
`aslice-extract`, and `aslice-link` provide the separated process roles along that
path. No source build helper is needed for a prebuilt payload. The transaction
records durable intent before live changes and commits after reconciliation, then
runs bounded service health checks while retaining mutation ownership.
[MANUAL §4.1](MANUAL.md#41-what-a-slice-is) gives the installation sequence.
Approved grafts add the isolated execution step described above.

A source build adds the harness and `aslice-build`: fetch pinned inputs, unpack,
patch, configure, build, install into staging, scan, test, and pack. Installing the
result then uses the ordinary artifact/generation path. The same executor design
serves local and farm builds; farm coordinators, agents, and signing infrastructure
are outside this client inventory. See [BUILD-INFRA](BUILD-INFRA.md).

A runtime invocation enters through the shim, resolves an installed stream, sets
its declared userbase environment, and executes the program. That path neither
starts a persistent aslice process nor activates a privileged closure.

A privileged install or change adds per-operation authorization and independent
helper verification before protected activation or external writes. If a running
service is affected, preparation finishes first; the transaction then stops the
affected jobs, switches the relevant generation/closure, reconciles launch
definitions, restarts, and checks readiness. Data migrations require a declared
backward-compatibility contract or an authorized, tested restore procedure.
Protected-volume changes can remain pending through Recovery and reboot;
[finalization](SYSTEM-VOLUMES.md#4-activation-rollback-and-os-updates) verifies the
booted result before commit.

<a id="services-that-can-remain-running"></a>

## 5. Services that can remain running

Package-provided **user agents** run as the user in launchd's user domain. Any
repository may declare one, without sudo. Their executable paths may resolve
through the ordinary profile. Package-provided **root daemons** use the system
domain and the protected closure, running as root or a declared service user.
They require the `system` capability: official and verified repositories may
provide them, local trees may on the user's own machine, and third-party
repositories may not.

launchd owns these jobs' continuing lifecycle. `aslice service status` reads its
state; `aslice service run` is the foreground, unregistered debugging case. A
helper returning does not stop a registered service. Managed registrations and
running-process leases retain the artifacts they need. Commands and upgrade
failure handling are documented in [aslice-service(1)](../man/aslice-service.1.md)
and [MANUAL §7](MANUAL.md#7-running-services).

The **future multi-user aslice daemon** is a different proposal for shared
machines. [DESIGN §10.4](DESIGN.md#104-privilege-discipline) describes a launchd daemon
accepting TUF-verified operation plans over a local socket with peer-credential
checks. It is gated behind demand and is not required by the current client
design. It does not describe today's privileged helper lifecycle.

<a id="details-still-to-be-established"></a>

## 6. Details still to be established

The role names do not settle internal invocation syntax, IPC formats, executable
filenames within protected storage, or the complete filesystem allow-lists for
each helper. The privileged helper's general network policy and the shim's
dispatch sandbox policy are not specified. Service labels must distinguish
prefix/profile identity, but this reference assigns no concrete label format or
generated-plist path.

Seatbelt enforcement, privileged-input validation, transaction durability, and
Recovery adapters require evidence on the supported OS/filesystem/security
matrix. [STATE-AND-RECOVERY §10](STATE-AND-RECOVERY.md#10-acceptance-and-implementation-order)
and [SYSTEM-VOLUMES §5](SYSTEM-VOLUMES.md#5-acceptance-matrix) define those gates.
Documenting a role does not mark any of them passed.
