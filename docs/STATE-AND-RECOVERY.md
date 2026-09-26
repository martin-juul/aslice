# State, artifacts, and recovery

- **Status:** Specification v0.9 — September 2026. These contracts are specified, not implemented or validated on macOS.
- **Authority:** This document owns artifact identity, privileged ownership, transaction recovery, replay, and retained trust. DESIGN explains the architecture; PACKAGE-FORMAT describes author input. Examples and schemas must agree with these contracts.

Navigation: [1. Compatibility and artifact identity](#compatibility-and-artifact-identity) · [2. ABI and execution requirements](#abi-and-execution-requirements) · [3. Privileged ownership and capability checks](#privileged-ownership-and-capability-checks) · [4. Graft execution boundary](#graft-execution-boundary) · [5. Durable transactions and recovery](#durable-transactions-and-recovery) · [6. Self-update and decommission](#self-update-and-decommission) · [7. Persistent trust and initial bootstrap](#persistent-trust-and-initial-bootstrap) · [8. Plans, locks, archives, and offline use](#plans-locks-archives-and-offline-use) · [9. Certificate trust lifecycle](#certificate-trust-lifecycle) · [10. Acceptance and implementation order](#acceptance-and-implementation-order)

<a id="compatibility-and-artifact-identity"></a>

## 1. Compatibility and artifact identity

`build_id` is a compatibility key, encoded as the full 64 lowercase hexadecimal digits of SHA-256 over RFC 8785 canonical JSON containing repository identity, package name, normalized version, epoch, revision, ABI variants, runtime ABI epoch (null when absent), flavor, minimum OS, and toolchain identity. Vendor records replace flavor/toolchain with null and include the vendor artifact digest. Missing optional identity fields have explicit null values; ABI variant maps contain the complete resolved assignment. This key selects candidates; equality alone never authorizes substitution.

`artifact_id` is `sha256:` followed by the digest of the canonical artifact manifest. The manifest records the canonical payload's file hashes, modes, symlink targets, dependency artifact bindings, recipe digest, build flags, CPU requirements, and ABI evidence. It contains neither its own identity nor signatures, wall-clock timestamps, builder names, or other variable provenance. Distinct payloads or bindings have distinct identities even when their compatibility keys match. `blob_digest` hashes the delivered archive bytes; detached signatures cover that digest. Provenance and evidence receipts bind both identities and are separate objects.

Store addresses are `<prefix>/store/<artifact-hex>/`. Short digests are display abbreviations only. The same artifact may be reused; a different artifact never overwrites that address. Generations and locks identify exact artifacts, including locally built ones. Local artifacts need exporting with a lock for reproduction on another machine; a lock alone cannot recreate unpublished bytes. Namespace and repository identity are retained even if two repositories publish the same package name.

Canonical manifests use [RFC 8785](refs/RFC_8785_JSON_CANONICALIZATION_SCHEME.MD) JSON, reject duplicate keys and non-finite numbers, and restrict integers to the interoperable safe range. Arrays representing sets are sorted lexicographically and duplicate-free. File entries sort by path; dependencies sort by repository and name. Recipe bundles contain `package.toml`, `build.star`, `tests.star`, patches, and pinned source references. The signed index supplies their digest and byte length. A resolver fetches and authenticates these recipes before solving; the dependency graph is derived from them, never from an unauthenticated Git branch. Source archives are independently hash-verified.

Canonical payloads use reserved relocation placeholders for their own store prefix; they cannot embed a hash of bytes that themselves contain that hash. Relocation records identify a file, byte offset, reserved width, expected original bytes, and replacement source (self or a bound dependency). The materializer verifies the canonical bytes, applies only those records, and writes a receipt containing the prefix, artifact identity, materializer version, and final file hashes. A second materialization at the same prefix must match. Unrelocatable artifacts are rejected at incompatible prefixes. Vendor-signed code is not rewritten; accept it only where its existing signatures and paths remain valid. Code signing that changes bytes happens before the final artifact identity is frozen.

Archive extraction rejects absolute paths, `..`, duplicate entries, case/Unicode-normalization collisions on the destination filesystem, device nodes, setuid/setgid bits, and hardlinks or symlinks escaping the staged artifact. Extraction uses bounded sizes and descriptor-relative traversal without following untrusted symlinks. Signature and archive digest verification precede extraction. The manifest's file inventory must match the extracted tree exactly.

Materialization also verifies any required executable signatures after relocation.
A relocation record does not authorize invalidating a signature or re-signing installed
bytes. If valid signing and the requested paths cannot coexist, refuse that artifact
at that prefix; a separately built and signed artifact needs its own authenticated
identity and plan. A materialization receipt cannot substitute for signature authority.

<a id="abi-and-execution-requirements"></a>

## 2. ABI and execution requirements

The loader-version check compares a provider's `current_version` with the compatibility requirement recorded by the client. The provider's own `compatibility_version` is also recorded but is not substituted for `current_version` in that comparison. See [Apple's dynamic-library guidance](refs/APPLE_DYNAMIC_LIBRARY_DESIGN_GUIDELINES.MD).

An exported-symbol hash detects equality, not set inclusion. ABI records therefore carry exported and required symbol lists, versions, architecture, and an evidence classification. C++ layout/calling-convention evidence must come from a validated scanner; stripped or incomplete evidence is `unknown`. Plugins loaded dynamically require explicit dependency declarations and integration tests. Symbol coverage alone never proves semantic compatibility. Unknown evidence retains the exact dependency artifact or requires rebuilding and testing dependents. No scanner result promises detection of every ABI break.

Each consumer records exact runtime artifact bindings. Absolute install names continue to bind those artifacts after a profile switch. Rebinding is an explicit rebuild or verified relocation producing a new artifact and rerunning the dependency tests; a profile symlink is not a substitute for relinking. GC traces these bindings transitively as well as generations, active transactions, privileged closures, and registered running-process leases. If process liveness cannot be established, GC retains the candidate. Persistent launch registrations and temporary execution views are roots too.

Every executable artifact, including vendor binaries, records `cpu_features` and `requires_i386`. The CPU detector checks every required feature and the OS support needed to execute it. Flavor is a prebuild selection axis, not sufficient execution evidence for `-march=native`. Native builds record the selected CPU's full compiler target feature set conservatively. Unknown vendor ISA requirements require maintainer evidence and tests or rejection; x86_64 does not imply a v1 baseline. A fat executable with an executable x86_64 member does not require i386 merely because an alternative member exists. Required i386-only helpers or plugins impose the 10.14 ceiling; unreachable alternatives do not.

Arbitrary compiler flags are not automatically ABI-neutral. The harness rejects unsupported ABI-changing flags unless represented in the declared ABI variant contract. Unknown flag effects require an isolated build and explicit dependency validation, not transparent substitution.

<a id="privileged-ownership-and-capability-checks"></a>

## 3. Privileged ownership and capability checks

The ordinary prefix remains user-owned. Root execution uses a separate protected root at `/Library/Application Support/aslice/system`, owned by root with no unprivileged-writable ancestor or execution/configuration directory. Root services run from immutable verified closures there, including libraries, interpreters, plugins, launch configuration, and executable search paths. Their active pointer and generated plists are root-controlled. Root service environment changes require an authorized helper transaction; user-owned `.env` files are never loaded by root. Writable service data and logs are separate root-controlled locations, with narrower service-user ownership where explicitly required.

The helper imports a complete closure from untrusted staging only after independently checking authenticated manifests, repository capabilities, digests, and the authorized plan. It copies into newly created root-owned directories, verifies the copied bytes, and atomically activates the protected pointer. It does not execute code through the ordinary profile. It ignores user loader/search-path overrides and rejects user-writable configuration that can load code. Root rollback changes the protected pointer through the helper and needs the same authorization as activation. System-patch links, where supported, target this protected closure too; originals and their recovery journal are root-owned.

The helper executable itself is installed in the protected root from a verified release during explicit elevation. Each invocation is authorized through the OS elevation mechanism, has a fixed operation vocabulary, and validates paths and inputs independently of the invoking user's SQLite database. No persistent daemon or setuid binary is required. The protected trust records are updated only through authenticated transitions or explicit administrator rebootstrap.

Capabilities follow effects. Installing or loading a kext or registering a root daemon requires `system`, whether expressed by `[system]`, `[service]`, or a graft. Replacing an Apple-provided path requires `system-patch` and its target restrictions. Other writes outside the prefix are individually declared and authorized; refusal lists apply to all mechanisms. Third-party repositories cannot acquire these capabilities through grafts, a machine file, or an unsigned warning. Required `--accept-system-changes` and `--accept-grafts` gates accumulate; one never substitutes for the other.

<a id="graft-execution-boundary"></a>

## 4. Graft execution boundary

A supported graft executes against an isolated staging view with the declared path mapping. It never receives unrestricted root access to the live filesystem. All resulting filesystem changes are validated, previewed, and committed by the helper's transaction machinery. Kext and daemon registration are declarative helper operations, not direct `kextload`, `launchctl`, Mach-service, Apple-event, or privileged-broker calls from the script. Sandbox policy denies those routes and must be tested on each supported OS before admission. Observing a process tree is evidence, not an enforcement mechanism.

Scripts requiring live privileged RPC, firmware changes, uncontrolled background processes, or irreversible remote effects are unsupported and refused before execution. Network-dependent input must be fetched as a pinned source before staging; `network = true` remains reserved and is refused in v1. A vendor script that cannot run with these restrictions is not packageable as a v1 graft. The package manager does not claim to undo arbitrary vendor code.

Approval binds repository identity, package version, script digests, and the complete effective behavior-manifest digest. Broader permissions invalidate approval even if the script bytes are unchanged. Machine-file names select only existing local approvals matching repository identity, version, script digests, and the complete effective manifest digest. A fresh machine must approve again; exported names transfer no authority. Matching approvals remain subject to the same capability and consent checks; unsigned manifests never receive persistent approval. Rehearsal covers each supported OS and validates both successful execution and attempted boundary violations. It cannot replace enforcement.

<a id="durable-transactions-and-recovery"></a>

## 5. Durable transactions and recovery

[DATABASE](DATABASE.md) owns the six SQLite projections, durable choice/history records, backup sets, and database reconstruction. Compact records are retained indefinitely, including changes that create no package generation; verbose logs and resolved backups keep their existing retention policies.

Lock waits and cancellation follow [DATABASE §10.1](DATABASE.md#101-contention-and-safe-stopping). Busy interactive commands show owner information and offer wait or exit; waiting is cancellable. Unattended commands wait only when explicitly requested. An authorized wait uses one configurable 30-second foreground allowance across owner and SQL locks, with one separate 30-second recovery allowance. Revalidate state, trust, and the proposed operation after waiting or recovery; a materially changed plan requires fresh confirmation. Unresolved recovery retains evidence and blocks conflicting mutations and GC, while working packages and external system-repair tools remain accessible.

One operation holds effective prefix mutation ownership from preparation through post-commit health checks; it rechecks the planned base generation after acquiring ownership. Privileged operations additionally take the system-root lock, always after the prefix lock. GC follows the same order. Cross-prefix privileged operations serialize at the system lock. OS locks may release on process death, but surviving helpers retain effective ownership until they stop writing. Parent death, a reused PID, or cancellation never licenses a second writer. Recovery must establish helper quiescence before inverse writes or manual repair.

Each transaction records its identifier, base and proposed generation digests, exact artifact set, authorization, ordered operations, before/after fingerprints, backups, and progress. Privileged journals and backups live in the protected root. Before-images preserve file kind, bytes, mode, owner, ACLs, xattrs, and symlink targets where supported; unsupported metadata is a preflight refusal. Files, journal records, and affected directory entries are flushed before the next durable phase. HFS+ and APFS power-loss behavior must be validated, including the selected `fsync`/`F_FULLFSYNC` strategy; rename atomicity alone is not durability.

The state machine is `prepared → applying → activated → committed`, with `recovering`, `rolled-back`, and `needs-attention` outcomes. Protected-volume application can persist `pending-reboot` before activation; this is a resumable pre-commit state, not a commit. Preparation authenticates and stages everything, takes durable backups, validates expected state, and persists the complete intent before live changes. Applying quiesces services and performs journaled external operations. Activation switches the profile and protected pointers, then records the new generation in SQLite. Commit follows reconciliation and precedes service health checks. Checks default to 60 seconds per service; overrides must be positive and finite. Failure or timeout returns nonzero and explicitly reports that installation committed, naming failed or unverified services. A later eligible rollback is a new transaction. Artifact validation, manager compatibility checks, and required protected-volume finalization remain pre-commit gates. There is no atomic primitive spanning SQLite, both pointers, and external state; the journal supplies recovery.

On restart, conflicting mutations and GC stop until recovery resolves their requirements; replacement preparation follows §5.1. A verified `pending-reboot` record is the sole resumable protected-volume exception: explicit `system-patch finalize` revalidates the prepared intent, boot identity, patch tree, and authority before activation and commit; failure keeps restoration pending in Recovery. It never resumes ordinary writes merely because the process restarted. For other operations, if no durable commit exists, recovery examines the actual pointers and operation fingerprints and restores the before-state, idempotently, in reverse order. A committed transaction reconciles its after-state. Before either forward or inverse writes, compare the current object with the recorded expected fingerprint. Concurrent external edits, missing backups, or inaccessible privileged state produce `needs-attention` with exact paths and remedies; they are never overwritten silently. Disk-full failures retain the journal and backups. Generations and affected artifacts remain GC roots until resolution.

Space-separated package requests, including mixed-orchard requests, form one managed-state transaction. Every non-core package retains its qualified namespace. A pre-commit failure rolls back the entire managed-state batch, including machine apply. Package-specific options identify their target, for example `--variant ffmpeg:+x265`; reject ambiguous batch options and unknown targets. Stateful `--for` scoping is superseded. Show effective variants, flags, runtime bindings, and build choices per package before authorization. Trust establishment is a separate explicit prerequisite and is never reset by package rollback ([SETUP §3.2](SETUP.md#the-plan-and-the-order-of-operations)).

The initiating user or an authenticated administrator may request stopping an operation. Before commit, stop helpers safely and attempt fingerprint-checked rollback. After commit, stop checks safely and report committed installation with incomplete verification; cancellation does not erase the commit. Unresolved rollback retains the mutation gate and recovery evidence. Stopping authority does not grant permission for new privileged effects.

### 5.1 Guided recovery and trusted prefix rebuilding

After a crash, interactive commands offer **recover and continue** in one interaction. Unattended recovery and continuation require explicit authorization; ordinary install consent alone is insufficient. Once authorized, resume interrupted recovery automatically when durable evidence and actual state agree. Previous interruption alone is not a reason to ask again. Revalidate the original request before continuing and ask again only for actual conflicts, new authority, or material plan changes.

Recovery inventories affected files, services, registrations, permissions, and transaction progress automatically. It reconciles unambiguous state from verified evidence and groups unresolved choices by repository, package, or service. Each group shows the conflict, recommended action, consequences, and expandable path-level evidence. Offer restoration of recorded state, retention of validated current state, or manual repair where applicable; explain why an unavailable choice is unsafe. Preserve displaced content and durably record accepted deviations. Resume saved progress across exits and reboots, rechecking fingerprints before using an earlier choice.

Manual repair first waits for all helpers to stop writing and establishes a persistent gate against conflicting aslice mutations and GC. External repair tools remain usable. Re-entry inventories the repaired state, validates it against the chosen resolution, and records any accepted deviation before clearing the gate. Neither an exit nor a reboot clears it implicitly.

A known-good recovery executable and independent recovery records must exist outside the active prefix, using a private user directory under `~/Library/Application Support/aslice/` and a separate root-owned directory under `/Library/Application Support/aslice/` for privileged evidence. Neither location may resolve inside the active prefix. Retain trust evidence, transaction receipts, choice/history records, manifests, and required backups; provide a verified export for recovery after disk loss. An outside-prefix copy on the same disk is not protection against disk failure, and user-owned copies are not protection against compromise of that account. These records recover evidence, not missing artifact bytes. The ordered durable protocol is specified in [DATABASE §9.3](DATABASE.md#93-independent-records-and-durable-copy-updates); §10.2 defines the recovery engineering contracts.

Use per-prefix directories keyed by stable prefix identity under each Application
Support root. Directories and the retained owner-executable recovery binary use
0700; record files use 0600, with equivalent ACL restrictions. Privileged storage
and executable ancestors must not be unprivileged-writable. Keep compact history
indefinitely and retain backups and displaced content while unresolved or referenced.
Exports include a verified inventory and all required recovery files, identifying
missing components explicitly; preserve protected ownership boundaries on import.
The storage layout and durable update mechanics are fixed in §10.2.

Rebuilding separates recovered package selections from authority to execute bytes. Independently verify each rebuild artifact and its dependency closure under the retained or explicitly re-established repository trust. If evidence is insufficient, guide repository-level trust re-establishment with an actionable independent verification method. Irretrievably lost history requires an independently authenticated recovery bundle establishing current trust and safe version floors; affected rebuild artifacts remain blocked without it. Disclose lost security history and its consequences. A fingerprint acknowledgement alone is insufficient; do not silently accept replacement keys, recreate TOFU, or reset anti-rollback state. An unresolved authority gap blocks the affected artifacts, not recovery inspection or unrelated verified packages.

The guided trust step identifies the affected repository and missing evidence,
directs the user to obtain its recovery bundle on an independently trusted machine,
and explains how to authenticate the bundle through an established independent
channel, following §7's bootstrap verification discipline. Show the authenticated
repository/environment, authority, version-floor evidence, and lost-history report
before authorizing re-establishment. The bundle must justify safe floors against
all surviving checkpoints and receipts; a current root key or fresh metadata alone
does not reconstruct forgotten rollback history. If its authority or floors cannot
be established, explain the missing evidence and keep that repository blocked.
Bundle issuance, format, and verification follow §10.2.2; successful issuance and
recovery drills remain release gates.

Prepare a replacement beside the original, preserving the original prefix and recovery evidence. Present missing artifacts, independently verified replacements, and proposed omissions together in one reviewed salvage plan. Names recovered from a damaged database express intent only. Any substitution or omission changes the plan and must be reviewed; it is not exact replay. Record decisions and unresolved external effects durably.

Permit isolated execution of verified, unaffected dependency closures from the replacement while unrelated repairs remain pending. Validate exact dependencies, CPU/OS requirements, absolute paths, loader/plugin paths, and external configuration; unresolved dependencies or access to damaged state disqualify that closure. Do not activate the replacement's normal profile or affected privileged integration until their requirements are satisfied. Isolated execution retains its own GC roots and must not overwrite or implicitly redirect the original prefix. Activation requires a reviewed, revalidated plan covering relocation and external integrations, with the original retained.

Recovery ends with an accurate outcome: **repaired**, **usable with listed unresolved repairs**, or **replacement prepared but activation blocked**. List usable closures, remaining conflicts, blocked activation requirements, saved progress, and the next action. Partial usability is not a claim of completed repair.

Recovery copies retain append-only history and independently recorded progress.
Accept disagreement automatically only when authenticated evidence proves a valid
continuation; preserve both copies and block the affected repair otherwise. A newer
timestamp or a majority of matching copies is not proof. The durable protocol must
detect incomplete multi-copy updates and may not declare a transition safely retained
before its required evidence is durable.

Activation keeps the replacement at its verified path and changes only reviewed
entry points and registrations. Preserve the original prefix. A package requiring
the old absolute path blocks its activation until rebuilt or safely relocated and
revalidated under §1. Isolated execution requires a complete validated closure whose
paths and configuration avoid the damaged prefix; refuse a closure that cannot meet
that condition. No rename of the original is an implicit part of activation.

### 5.2 Working-package access and shims

Recovery gates mutations; it does not impose blanket runtime denial. Existing working packages remain accessible when their selected artifacts and complete dependencies are established as unaffected. Shims keep the session → project → default resolution order. If the required selection or closure cannot be established, fail promptly with the specific reason and recovery remedy. Do not choose another stream, repository, generation, or replacement merely because the selected state is unavailable. Isolated replacement execution is an explicit choice under §5.1, not shim fallback. The committed execution catalog below supplies the validated read path during projection damage.

A separately retained, immutable execution catalog records the committed profile
identity, generation and decision head, runtime defaults, installed streams, exact
artifact bindings, materialization receipts, runtime/extension configuration, and
complete dependency closures. It lives in the independent recovery set and is
bound by digest to its durable commit decision. Keep the previous catalog until no
recovery or execution root needs it. Its decision-head field is the prepared history head; the terminal decision binds the catalog digest without a circular reference. The catalog is a read projection of verified
committed evidence; its presence or checksum alone grants no trust. Protected
execution continues to require the helper's independently verified protected copy.

Before live changes, publish and flush an operation gate identifying every affected
selection, closure, and shared configuration resource. Dependency consumers belong
to the affected set. If the set cannot be bounded from verified evidence, block
dispatch only for the scope whose safety cannot be established and explain why.
Unrelated catalog entries remain eligible. The gate survives parent death and
reboot; only validated reconciliation of the recorded decision can clear it.

A shim reads the committed catalog and gate epoch, resolves session → project →
default exactly as usual, and validates the chosen entry's commit evidence,
materialized bytes, dependencies, CPU/OS requirements, and configuration. It takes
a short execution-admission lease, rechecks that the catalog and gate epoch have
not changed, and registers its closure as a retained execution root before exec.
Writers serialize gate publication against those admission leases; no new affected
execution may slip between validation and gate publication. Long-running programs
retain their artifact roots under §2; a short admission lease is not a lifetime
mutation lock. Unknown or changed evidence fails the selected invocation promptly.
Do not use an old default or another stream because the selected entry is blocked.

Build the next catalog from the verified after-state, bind it in the commit decision,
and publish its pointer only after commit. An interrupted publication reconciles
against that decision, never against modification times. Clear a gate only when
the selected catalog and affected actual state agree. Changes to defaults and other
choice-only state follow the same discipline. SQLite damage alone therefore need
not block execution; damage to the required catalog, gate, or closure evidence does.
The ordered copy protocol is specified in
[DATABASE §9.3](DATABASE.md#93-independent-records-and-durable-copy-updates).

### 5.3 Command surface

The following spellings are approved specification, not implemented commands.

| Command or option | Contract |
|---|---|
| `--wait` | Explicitly authorize cancellable lock waiting; `--lock-timeout DURATION` sets the cumulative allowance, default 30 seconds. Configuration alone does not authorize unattended waiting |
| `aslice operation status` | Report owner, operation identity, durable phase, helper activity, waiting, verification, and recovery state without mutation |
| `aslice operation stop` | Request safe stopping of the current operation; authorize the initiating user or an authenticated administrator and bind the request to the displayed operation identity |
| `aslice recover --continue` | Explicitly authorize recovery and continuation of the retained interrupted request; refuse if that request cannot be established. Interactive recover-and-continue offers the same action. Reconfirm material changes; unattended drift refuses |
| `aslice recover --manual` | Quiesce helpers, persist the mutation gate, and present grouped manual-repair guidance; re-entry validates actual state |
| `aslice recover --salvage` | Prepare and review a replacement plan beside the original; it does not authorize normal activation |
| `aslice recover --activate` | Review and revalidate activation of the prepared replacement at its verified path and required integrations; preserve the original |
| `aslice exec --replacement PATH -- PACKAGE COMMAND...` | Explicitly run the named package's validated isolated closure from that replacement; require the verified plan and unaffected complete closure, not merely a caller-supplied directory |
| `--health-timeout DURATION` | Override the 60-second per-service timeout with a positive finite integer duration in `ms`, `s`, or `m`; reject zero, overflow, and unbounded values |
| `--variant PACKAGE:+NAME`, `--variant PACKAGE:-NAME` | Target a declared feature variant; qualified non-core package names remain intact |
| `--cflags 'PACKAGE:FLAGS'`, `--ldflags 'PACKAGE:FLAGS'` | Target compiler/linker flags; quote whitespace. Single-package unqualified forms remain valid |

Resolve option targets against the exact requested package identifiers, separating
the target from its value after the complete identifier (for example
`audiolab:convolver:+feature`). Reject conflicting duplicate assignments and any
ambiguous target. Other package-specific options must likewise identify their
target in batches; §10.2.5 defines the complete targeting grammar.
Recovery flags select distinct actions; do not infer activation from salvage or
grant privileged consent from `--continue`. Existing protected-effect and graft
authorization remains required. Unattended salvage/activation must bind explicit
authorization to the reviewed plan; its exact confirmation transport remains pending.

Grouped conflicts recommend recorded-state restoration by default when supported
by verified evidence. Keeping current state is offered only after validation; a
recommendation cannot bypass a fingerprint conflict or erase displaced content.
Bind saved choices to their evidence and re-open only groups invalidated by changed
state. Manual repair remains available when neither automatic option is valid.

Recovery JSON uses stable outcome values `repaired`, `usable_with_unresolved_repairs`,
and `replacement_prepared_activation_blocked`, plus `committed`,
`verification_complete`, `activation_allowed`, and `unresolved_repairs`. The first
three flags are booleans; `unresolved_repairs` lists grouped reasons, affected
packages/services/paths, and next actions. Retain DATABASE's `recovery_required`
and `retry_safe` diagnostics. Never infer complete verification or activation
eligibility from partial usability. Object schemas and exit mappings for the
new command family are defined in §10.2.5.

Rollback records a new transaction in the journal, preserving the history of earlier transactions. When rollback spans several generations, it computes the target managed state and checks for conflicts. Service plists and protected closures are restored together with the package generation; changed declarations require regenerated plists. Preferences and login-shell settings use recorded before-values, and intervening external edits are reported as conflicts.

Package rollback does not restore application databases, userbases, or remote systems. Before a service upgrade that can migrate persistent data, require a declared backward-compatibility contract or a tested backup/restore procedure and explicit authorization; otherwise refuse automated upgrade of the running service. A pid check is only process liveness. Service-specific readiness and data compatibility determine whether automatic rollback is permitted. Unattended service failure returns failure and retains evidence unless the caller explicitly selected a valid rollback procedure.

<a id="self-update-and-decommission"></a>

## 6. Self-update and decommission

A known-good supervisor remains alive while the new manager runs as a child against a prepared state snapshot. It validates execution, version, database compatibility, index reading, and a bounded health timeout before activation. Post-activation failure is recovered by that supervisor or, after power loss, by a protected bootstrap recovery entry point retained outside the switched generation. The supervisor runs pre-activation compatibility checks and post-activation manager smoke checks before the durable commit, with a positive finite 60-second default timeout for each check. These are manager-integrity gates, distinct from ordinary post-commit service readiness. Failure before commit reverses tentative activation; after commit, restoration is a new authorized transaction preserving trust floors and compatible history replay. The recovery entry point is updated separately only after the replacement has passed recovery drills. Old managers remain usable with their compatible state snapshots; switching back after newer writes requires compatible replay so it cannot erase choices or high-water state ([DATABASE](DATABASE.md#10-sqlite-connection-and-migration-policy)). Destructive in-place database migrations are forbidden; use a versioned copy and journal its activation.

Self-update updates shim targets transactionally as well as the manager. Hardlinks to the old multicall binary are not silently left behind. Crash injection covers failure to execute, crash before health reporting, timeout, disk exhaustion, migration failure, pointer changes, and supervisor loss. `aslice recover` invokes the retained recovery entry point and refuses ordinary package mutations until recovery is resolved.

`aslice decommission --dry-run` inventories external effects while the manager, trust records, and backups still exist. `aslice decommission` then authorizes and journals: restoring the user's prior login shell and owned `/etc/shells` entry; stopping and unregistering managed services; reversing supported grafts and system patches; removing managed kexts where safe; removing only aslice-owned certificate trust entries; and removing owned integration links. A required reboot or conflicting external edit leaves cleanup pending and preserves the recovery tools. User data and ecosystem userbases are retained and listed. Hand-written shell initialization lines receive explicit removal instructions.

Only after cleanup succeeds may the prefix be deleted. Root-owned closures, receipts, and backups are removed by the helper only when no other prefix or active operation references them. Decommission prints remaining user data and any required manual actions; it never claims deletion of the prefix alone removes all effects.

<a id="persistent-trust-and-initial-bootstrap"></a>

## 7. Persistent trust and initial bootstrap

`trust/` is authoritative security state, separate from the reconstructed client-state database and disposable solve/index cache in SQLite. It retains repository identities, initial anchors, authenticated root chains, TUF high-water versions, grants, countersignatures, revocations, and previously verified cache receipts, scoped by repository and environment. SQLite may cache these records but cannot grant authority. Missing or corrupt trust state fails closed for new trust decisions and requires explicit recovery. Never silently recreate a TOFU decision. Ordinary user-owned trust protects against network substitution, not an attacker who already controls that user; privileged verification uses the protected copy from §3.

The compiled root pin authenticates the initial anchor, not an eternally fixed current key. Sequential root updates must satisfy the old and new thresholds and remain retained. Discovery files may advertise a successor but cannot bypass that chain. User-requested third-party re-pinning and root-compromise rebootstrap are distinct operations with explicit independent verification. Root loss does not authorize an automatic reset of metadata versions.

Each repository uses Ed25519 TUF metadata for freshness and target authorization. OpenPGP is an optional package/source signature scheme, verified in addition to TUF; it does not replace TUF roots or metadata. Discovery records distinguish the TUF anchor from the package-signing fingerprint. Unsigned local source recipes are a separate, explicitly local trust path and cannot become remotely trusted by export.

On a TLS-dead machine, obtain the bootstrap kit on a supported machine over authenticated HTTPS and transfer it offline. The kit contains the installer, bootstrap binary, initial root, verification instructions, and exact SHA-256 pins. Verify its published digest through an independently authenticated channel, then use the stock `/usr/bin/shasum -a 256` before executing the installer or binary. Validate that utility's presence on every supported clean OS image. The verified bootstrap binary performs signature verification; the shell script does not bootstrap trust by downloading an unverified verifier. If no independently authenticated kit or digest is available, stop and explain the missing trust anchor.

The online route obtains the installer over authenticated HTTPS. HTTP may carry later artifacts only after the authentic installer or kit has established their exact hashes. Release assets and Pages are redundant transports, not independent authorities if both share compromised control. A verification failure never falls back to an unauthenticated script or a new hash from the same failing channel.

<a id="plans-locks-archives-and-offline-use"></a>

## 8. Plans, locks, archives, and offline use

An executable package plan names its profile, base generation digest, repository identities/environments and exact index digests, and exact old/new package records for each action. Empty actions represent a no-op. Every new record carries artifact and blob digests, recipe digest, compatibility key, CPU/OS requirements, origin, and local build flags. Remove actions bind the old artifact. Apply rechecks the base generation, machine compatibility, current repository capabilities and known revocations, authenticated artifact metadata, and every consent. Textual announcements or a plan's claimed consent list grant no authority. Drift refuses the plan and requests replanning; it does not silently resolve newer packages.

Locks carry the complete package set, per-repository index bindings, exact artifacts and runtime dependency bindings. Local artifact export includes its recipe and inputs, but exact replay requires the recorded artifact bytes; rebuilding merely the same compatibility key is not exact replay. Vendor-direct records bind the original vendor digest and signer separately from the normalized extracted artifact. On a different machine, explicit re-resolution reports each changed artifact; `--frozen` refuses it. Only core packages may use bare names; every other repository, including extended, requires its registered namespace. Names never fall back across repositories ([REPOSITORIES §10](REPOSITORIES.md#overlapping-packages-across-repositories)). A machine wishlist creates a new plan; serialized machine-wide operation plans are deferred until their operation schema exists and cannot masquerade as package plans.

Ordinary repository refresh obeys TUF expiry and rollback checks. Offline mode may reuse only already-cached bytes with a retained local receipt proving prior verification while the metadata was valid. It rehashes those bytes, respects known revocations, prints verification time and metadata age, and makes no freshness claim. It cannot import new metadata, discover trust, or accept an uncached target under expired metadata. Lost receipts require revalidation against current trusted metadata or explicit trust recovery.

Historical index snapshots, recipes, manifests, and hosted artifact blobs referenced by published releases are retained, rather than keeping only monthly snapshots. A currently TUF-authorized archive catalog binds their original digests and lengths; selecting history downloads those immutable targets under current authorization without lowering TUF high-water state. Expired historical metadata is evidence, not current authority. Revoked artifacts stay in the audit record but are unavailable for ordinary installation. Vendor-direct availability cannot be guaranteed; a missing vendor artifact is an explicit failure. An old lock requests exact content, not permission to bypass revocation.

<a id="certificate-trust-lifecycle"></a>

## 9. Certificate trust lifecycle

The private CA bundle and System-keychain import have different contracts. A PEM extraction does not preserve every browser root-program restriction; [curl documents omitted constraints](refs/CURL_MOZILLA_CA_EXTRACTION.MD). Do not describe it as reproducing Firefox's trust policy. A bundle updates certificates, not TLS protocol implementations.

System import requires a signed certificate-policy inventory recording fingerprint, certificate role, permitted purposes, relevant constraints, and retirement state. The importer preserves supported constraints and refuses an entry whose required restrictions cannot be represented on that OS. It does not blanket-import the PEM bundle with unrestricted `trustRoot`. Roots and intermediates use distinct operations; importing an intermediate does not promote it to a trust anchor. Apple certificate updates require chain/purpose validation and tests for the named service; importing certificates does not guarantee that an obsolete service protocol works.

The protected receipt records exactly which certificates and trust settings aslice created and their before/after values. Bundle updates preview removal or distrust of aslice-owned retired roots with per-run authorization. Existing Apple and user entries are not taken over. Rollback cannot silently restore a root now known to be distrusted. A conflicting user change stops reconciliation for that entry and reports it. `--keychain-remove` removes only unchanged aslice-owned additions or restores recorded prior settings; it does not delete a certificate merely because its fingerprint once appeared in a bundle.

<a id="acceptance-and-implementation-order"></a>

## 10. Acceptance and implementation order

Status vocabulary is **specified**, **implemented**, **tested** (named matrix and evidence), and **operational** (deployed with recovery drills). A described feature is not delivered software. The following are release gates; no document edit counts as their execution:

1. Phase 0 includes the minimal immutable store, generation journal, recovery entry point, trust persistence, artifact format, and self-update supervisor. Full variant solving follows in Phase 1. Bootstrap a pinned Clang/libc++ configuration and execute representative C++20 code on every claimed OS; static libc++ alone does not prove backdeployment or safe C++ objects crossing shared-library boundaries.
2. Test artifact substitution and relocation with distinct bytes under one compatibility key, exact replay, stale plans, concurrent operations, GC leases, malformed archives, and namespace collisions. Validate C++ ABI evidence on Mach-O before enabling automatic substitution.
3. Attempt unprivileged replacement of every root execution/configuration dependency. Verify the protected closure remains unchanged and unauthorized helper operations fail. Exercise graft capability bypasses and privileged IPC denial on every supported OS.
4. Inject failures before and after every durable transaction step on HFS+ and APFS; test external-edit conflicts and service data migrations. Exercise decommission with a managed login shell, root service, graft, patch, and certificates.
5. Exercise TLS-dead and offline bootstrap from clean images, root rotation, trust-state loss, historical installation under current metadata, expired-metadata refusal, and offline receipt reuse. Existing KEY-RUNBOOK drills remain mandatory.
6. Compare independent builds before nondeterministic Apple signing/notarization and variable provenance. Record the unsigned canonical payload digest and exact normalization recipe in signed evidence; then sign/package once and freeze the served artifact inventory. Recovery compares the unsigned rebuild with that archived unsigned reference and separately verifies the archived served signatures. Never demand equality between a fresh unsigned executable and an archived notarized binary.

The two owned Macs do not establish complete guest coverage or independent v3 rebuild capacity. Keep missing gates pending. Privileged features cannot ship until their enforcement and recovery gates pass, even if ordinary user-space packages ship earlier.

### 10.1 Guided workflow acceptance

These scores are provisional design targets, not usability-test results.

| Workflow | Target | Required experience |
|---|---|---|
| Concurrent shells | 8/10 | Visible wait or exit choice, owner information, cancellable waiting, no repeated retry commands |
| Recovery after one crash | 9/10 | One recover-and-continue interaction when the plan remains valid |
| Interrupted recovery and conflicts | 8/10 | Resume saved progress; ask only actionable questions |
| Customized batch | 8/10 | Every package-specific option identifies its package; display effective settings |
| Damaged-prefix rebuild | 8/10 | Automatic evidence recovery, grouped choices, and preserved working access |

Pending runtime acceptance scenarios:

| Scenario | Required observation |
|---|---|
| Concurrent shells and surviving helpers | A second mutation cannot start from preparation through checks, including after parent death while a helper still writes; unattended contention does not wait without authorization |
| Waiting and cancellation | Waiting is cancellable, changed plans are revalidated and reconfirmed; only the initiator or authenticated administrator can stop another operation; pre-commit rollback and post-commit incomplete verification are distinct |
| Mixed-orchard batch and health failure | A pre-commit failure reverses the whole managed-state batch; ambiguous options refuse; post-commit service failure or the default 60-second timeout returns nonzero and reports committed installation |
| Repeated interruptions | Crash recovery resumes after exits and reboots without repeated acknowledgements when evidence agrees; changed fingerprints invalidate only affected choices |
| Grouped conflicts | Many file conflicts form repository/package/service groups with recommendations and expandable details; accepted deviations and displaced content survive interruption |
| Manual repair | Helpers stop before external repair; the mutation gate survives exit/reboot; repair tools and unaffected packages remain usable; validation precedes clearing the gate |
| Lost trust and conflicting copies | Corrupt, missing, stale, or disagreeing recovery records never silently reset trust or version floors; preserve both copies, disclose lost history, and guide independent verification |
| Working packages and shims | Unrelated recovery does not deny a validated selected closure; missing selection fails without stream, repository, or generation fallback |
| Execution catalog and gate races | Corrupt SQLite while retaining catalog evidence; unaffected selections still dispatch. Interrupt catalog publication and race exec against gate publication; no tentative selection or affected closure escapes admission checks, and execution roots survive |
| Recovery-copy protocol | Interrupt each intent, receipt, decision, mirror, head, and participant-acknowledgement flush. Repair verified lagging copies; retain a durable commit after mirror failure; refuse conflicting decisions or unknown commit evidence; never repeat privileged effects solely because an acknowledgement was lost |
| Isolated replacement execution | An unaffected verified closure runs while unrelated repairs remain pending; bad absolute paths, dependencies, plugins, or external configuration block that closure; no implicit activation or privileged registration |
| Reviewed activation | A single salvage plan lists missing bytes, verified replacements, and omissions; revalidated activation preserves the original and reports unresolved integration accurately |
| Disk exhaustion and evidence corruption | Retain journals, before-images, and useful diagnostics without claiming completion; free-space repair remains possible |
| Power loss | Inject loss at every durable transition, including recovery progress, copy updates, commit, and activation, on HFS+ and APFS; actual state and independently retained evidence govern resumption |

Record unexplained fingerprints, repeated acknowledgements, hundreds of per-file
prompts, or restrictions preventing manual repair as design issues requiring
revision. Run existing documentation, citation, contract, and database-model checks,
but never report them as proof of runtime recovery or hardware durability.

### 10.2 Recovery engineering contracts

The following contracts close the storage, authority, isolation, activation, and
command decisions. They are specifications with structural fixtures, not evidence
of runtime enforcement. [DATABASE §9.3](DATABASE.md#93-independent-records-and-durable-copy-updates)
owns cross-copy ordering; the contracts here supply its object formats and use.

#### 10.2.1 Storage, formats, and durability

The initialization record allocates a random 128-bit `instance_id`, encoded as 32
lowercase hexadecimal digits. It is independent of the prefix pathname and is not
reused for a replacement prefix. User recovery storage is
`~/Library/Application Support/aslice/prefixes/<instance_id>/`; protected participant
storage is `/Library/Application Support/aslice/recovery/<instance_id>/`. The helper
binds both identities in its protected prefix registration. Paths are opened through
verified directory descriptors; symlinked or wrongly owned recovery ancestors are
refused. Existing independent storage is migrated by verified copy under mutation
ownership, retaining the old copy until the new registration and inventory are durable.

Each set contains `records/`, `objects/sha256/`, `catalogs/`, `gates/`, `exports/`,
`head.json`, `initialization.json`, and `recovery/aslice`. Object filenames are full
digest hex; catalog and gate files are content-addressed objects with atomic selected
pointers. `head.json` contains `format`, `instance_id`, `sequence`, and `digest`.
The initialization record contains `format`, `instance_id`, `owner_uid`,
`prefix_path`, `recovery_path`, and `protected_instance_id` (null when unenrolled).
Both formats are version 1. The retained recovery executable and its complete runtime
closure are installed from authenticated artifacts and referenced by initialization
evidence; a copied executable with dependencies inside the prefix is insufficient.

[Recovery records](../schematics/json/recovery-record.schema.json) retain DATABASE's
canonical envelope and typed changes. [Participant receipts](../schematics/json/recovery-receipt.schema.json)
bind the owner, operation, authorized intent, step, before/after state, and evidence.
[Execution catalogs](../schematics/json/execution-catalog.schema.json) bind exact
selections and closures. [Gates](../schematics/json/recovery-gate.schema.json) name
affected selections, artifacts, and configuration resources at a monotonic epoch.
[Export inventories](../schematics/json/recovery-export.schema.json) identify every
required file by component owner, relative path, size, and digest, and list missing
components explicitly. Unknown versions, change kinds, or extra structural fields
fail before replay. A schema-valid object still requires canonical-byte, digest,
chain, ownership, and authorization checks. Schema descriptions and definitions
specify field representations; these are normative companions to this section.

Receipt `step` is a monotonic per-operation ordinal, allocated in the intent before
execution. Repeated requests with the same owner/operation/step and intent digest
return the retained receipt after actual-state reconciliation; different intent is
a conflict. No lost acknowledgement permits a second execution of the effect.
Terminal `committed` and `rolled-back` decisions for the same operation conflict;
neither timestamp nor copy count resolves them. `needs-attention` is progress, not
a terminal decision, and may be followed by a verified resolution.

Flush each temporary file's contents and metadata with `fsync`, then request
`F_FULLFSYNC` through the tested filesystem adapter before no-replacement publication.
Flush affected parent directories after create, rename, link, or unlink; only then
advance and flush the selected head or pointer. The adapter must establish stable
ordering for both file and directory changes on the claimed HFS+/APFS configuration.
Unsupported calls, failed flushes, and unvalidated storage behavior refuse new live
writes. A failure after an existing live write retains recovery evidence and the gate;
a failure after the decision flush preserves the commit. Never fall back silently
to rename-only durability. Adapter fixtures and power-loss tests remain required.

Export under the coordinated backup boundary in DATABASE, copying immutable objects
first and finalizing the inventory last. Import into private staging, reject traversal,
links, duplicate/colliding names, and inventory mismatch, then authenticate its known
head and all trust references. Protected files are imported only by the helper after
independent checks; user copies cannot restore protected authority. A partial export
is usable for inspection and verified salvage, not complete state activation.

#### 10.2.2 Recovery checkpoints for lost security history

A [recovery checkpoint](../schematics/json/recovery-checkpoint.schema.json) is a
canonical version-1 signed object issued by the repository's offline root authority.
Its signed body identifies repository and environment, an increasing checkpoint
sequence, issuance and expiry times, the root chain, role version floors and exact
metadata digests, revocation inventory, signing-history evidence, and a lost-history
statement. Signatures cover the canonical `signed` body using the active TUF root
role's Ed25519 keys and threshold. This is an aslice recovery object, not a new TUF
role or a replacement for normal TUF verification. Expiry is seven days after issuance;
clock uncertainty requires independently establishing time before use.

Before issuance, stop signing/publication for the affected environment and reconcile
the offline archive, signer reservations (including unpublished signatures), publisher
receipts, and retained checkpoints. Publish a fresh, consistent metadata set above
every consumed role version, including delegated targets roles. Its versions become
the checkpoint's floors. Timestamp refreshes are included in that reconciliation.
The root operator verifies the inventory on a trusted machine and signs offline;
archive the signed bundle and its digest separately before resuming publication.
If complete signing/version evidence cannot be established, do not issue a checkpoint
claiming safe continuity. Follow explicit authority rebootstrap instead.

Obtain the bundle on an independently trusted machine. Authenticate it against an
uncompromised retained root chain or obtain its exact SHA-256 and root fingerprint
directly from the known repository owner through a previously established independent
channel. Downloading two copies from owner-controlled hosting is not independent
verification. A new contact assertion or an old compromised root signature is
insufficient. Transfer offline and verify every object, signature threshold, expiry,
repository/environment, and floor before displaying the recovery plan.

For every surviving checkpoint or receipt, the offered floor must be at least its
version; equal versions require equal digests. A newer surviving floor requires a
new reconciled bundle, not client-side modification of the signed checkpoint. Retain
all known revocations unless authenticated policy explicitly resolves their status.
Re-establishment imports only verified authority and monotonic floors through a
journaled, administrator-authorized helper operation when protected trust is involved.
It does not recreate local approvals, lost choices, or proof that previously installed
bytes were safe. Report those losses. A root-compromise recovery requires the separate
[rebootstrap procedure](runbooks/KEY-RUNBOOK.md#disaster-recovery-trust-rebootstrap).

#### 10.2.3 Execution admission and replacement activation

Catalog entries reference the authenticated package records, artifact manifests,
materialization receipts, exact transitive dependency set, runtime selections, and
configuration evidence. Defaults map runtime names to installed stream identifiers;
entries use the exact package identifier plus stream, with null for a non-runtime.
All artifact sets and resource sets are sorted and duplicate-free. The catalog binds
the prepared history head; the terminal commit binds the catalog digest. The catalog
does not contain its own committing decision digest, avoiding a circular hash.

Before dispatch, validate the selected committed evidence and current materialized
bytes. Resolve Mach-O load commands, interpreter/shebang paths, declared dynamic
plugins, executable search paths, and configuration capable of loading code against
the complete closure. For isolated replacement execution, reject required references
into the damaged prefix, unresolved dynamic paths, and unverified external configuration.
Normal execution keeps the existing per-stream userbase policy; a replacement closure
depending on mutable ecosystem code is ineligible unless that code and its dependency
paths can be inventoried and validated for this execution. This is admission validation,
not a claim to sandbox arbitrary installed applications after exec.

Use one owner-controlled admission lock to serialize gate publication with lease
registration. Readers validate, acquire it, recheck the selected catalog digest and
gate epoch, and durably register the execution root before releasing it and calling
exec. Writers acquire it, advance and flush the gate, then release it before applying
effects. Leases record PID plus process-start identity; PID reuse or uncertain liveness
does not release roots. Existing processes retain artifacts; writers quiesce affected
managed services and refuse conflicting mutable configuration changes while an affected
live lease cannot safely be quiesced. Gates are persistent evidence, not OS-lock state.

Activation plans inventory each entry point and registration with before/after
fingerprints, target replacement path, exact artifacts, required relocation receipts,
and protected participants. Switching PATH integration, shims, launch registrations,
and shell records uses the same ordered helper/client transaction. Never rename the
original prefix or redirect an old absolute store path to different bytes. A changed
artifact or omission changes the plan digest and requires review. Before commit,
interruption reverses journaled effects; after commit it completes publication of the
new catalog and integrations. Missing decision evidence keeps activation blocked.

#### 10.2.4 Grouped conflict decisions

Group conflicts by repository identity and package identifier, subdividing by service
when service state differs; prefix-wide objects form a separate group. Sort groups
by those identifiers and paths within each group. Show counts, reasons, recommended
recorded-state restoration, available alternatives, and expandable evidence. All paths
remain available in JSON even when the terminal display collapses a large group.

Restoration requires verified before-images and current expected fingerprints. Keeping
current state requires authenticated artifact identity, valid capabilities, compatible
CPU/OS/dependencies, expected ownership, and validated effect/configuration state.
Unverifiable current bytes cannot be accepted as executable artifacts by acknowledgement.
Offer manual repair when neither choice passes. Preserve displaced bytes before writes.
Save the choice with the group digest, plan digest, current fingerprints, and referenced
evidence. Reuse it only if those bindings still match; invalidate only changed groups.
No blanket confirmation overrides these checks.

#### 10.2.5 Command requests and outcomes

[Operation requests](../schematics/json/operation-request.schema.json) describe the
approved recovery actions, status, and stop requests; they do not grant authority.
`aslice operation stop --operation-id ID` is mandatory unattended. Interactively,
omitting the ID displays the current operation and binds the confirmed request to
that ID. A changed operation refuses the request. An absent operation returns status
with null identity; stopping an unknown operation is an input error.

`--confirm-plan sha256:HEX` binds unattended recovery continuation, manual repair,
salvage, or activation to the exact reviewed plan. The corresponding action flag is
also required; a generic yes flag does not imply recovery authority. Without the
confirmation digest, a read-only `--dry-run --json` returns the proposed plan digest,
requirements, and conflicts. Recompute under mutation ownership and refuse changed
digests before writes. Recovery actions are mutually exclusive. Required system/graft
consents and authentication still accumulate. Package plans remain package-only;
recovery request objects cannot be passed to package `apply` as serialized machine plans.

The version-1 [recovery plan](../schematics/json/recovery-plan.schema.json) binds the
action, prefix identity, interrupted operation if any, base history head and generation,
replacement path, evidence, exact artifacts, omissions, required consents, ordered
effects, and saved conflict choices. Effect references bind complete canonical object
state including filesystem metadata, not just file contents; null means absent.
Its digest is SHA-256 of canonical plan bytes, excluding no fields. It contains no
own digest, wall-clock time, or newly allocated operation ID. Dry-run returns the full
plan in `data.plan` and its digest in `data.plan_digest`; absent plans use null.
Human preview resolves evidence references into the concrete affected paths and
before/after changes. A new mutation ID is allocated only after revalidation and
authorization. `continue` requires a non-null established interrupted operation.

All package-specific batch options use `PACKAGE:VALUE`: `--variant`, `--cflags`,
`--ldflags`, `--flavor`, `--runtime`, `--with-extensions-from`, `--build-from-source`,
`--lto`, `--debug`, and `--link`. Boolean options use `true` or `false` in targeted form. Match the complete
requested identifier followed by `:` (including namespace and requested version);
require exactly one match, then parse the entire remainder as that option's value.
Do not split at the first colon or apply stateful scoping. Identical repeated
assignments coalesce; different assignments to the same option/variant target refuse.
Single-package existing forms remain valid. `--allow-eol`, system/graft consent,
waiting, health timeout, dry-run, and output options apply to the whole operation;
their effective scope is shown in the plan. Flavor values are `v1`, `v2`, or `v3`;
runtime values retain `name@stream`, extension-source values retain the stream, and
compiler/linker values retain their quoted bytes. Empty flag strings explicitly clear
that override; other empty values refuse. Targeted options for unrequested packages
refuse; adding a future package-specific option requires defining its targeted form.

[Operation outcomes](../schematics/json/operation-outcome.schema.json) use the existing
JSON envelope: `format`, `command`, `role`, `instance_id`, `status`, `data`, and
`errors`. Status is `ok`, `refused`, `needs-attention`, or `error`; each error has
`code`, `message`, `remedy`, and optional `path`. The schema defines all status/recovery
data fields, including nulls for unavailable identities. `verification_complete` describes completed successful checks, not merely
finished attempts. `activation_allowed` requires every activation gate to pass.
`repaired` has no unresolved repairs; partial usability never implies completed repair.
`recovery_required` concerns unresolved transaction/evidence state: an ordinary failed
service check after commit can have this flag false and verification false.

| Exit | Meaning |
|---|---|
| 0 | Requested action completed, or a read-only status/dry-run was successfully reported; inspect reported outcomes before acting |
| 1 | Action failed, recovery/activation remains unresolved, reboot is pending, or committed installation has failed/incomplete verification |
| 2 | Invalid input, ambiguous targeting, stale confirmation, or missing consent/authority |
| 4 | Contention without unresolved recovery; no mutation started |
| 130 | Authorized cancellation reached a safe stopping point; committed work remains committed |

An unresolved cancellation exits 1. A successful salvage preparation exits 0 only
when all preparation requirements passed; its `activation_allowed` can remain false.
Status returning 0 never clears a gate. Errors carry stable codes and next actions;
post-commit health failure uses `service_start_failed`, while pending reboot uses
`pending_reboot`. Never retry committed work as a fresh mutation.

This revision supersedes commit-after-service-health-checks, automatic unattended
waiting, stateful `--for` batch scoping, and blanket shim denial solely because an
unrelated recovery is pending. Existing single-package option forms remain valid
when unambiguous; additional package-targeted spellings follow §5.3.
The shim audit found the broad denial in [DATABASE §9.1](DATABASE.md#91-commit-boundaries)
and its deletion summary in [DATABASE §1.2](DATABASE.md#12-identity-and-reconstruction);
those now defer to §5.2 here. DESIGN's session/project/default precedence
is retained. Structural fixtures and decision models exercise the specified contracts;
runtime enforcement and platform acceptance remain unimplemented.

### Security workflow contract versions

Plans and locks use version 2; operation-request and operation-outcome envelopes
use format 2. Recovery journals, recovery plans, and nested operation state remain
format 1. The new request fields are `allow_source_builds`, `selections`, and nullable
`update_policy`; consent defaults to false only for a newly created request, never
by converting an old saved record. `install`, `upgrade`, `apply`, and `needs-restarting` join
the request action vocabulary. Read-only restart inspection has no mutation plan.

Outcomes add `security_findings`, `restart_findings`, `inspection_coverage`, and
`exit_code`. Findings bind advisory/repository/artifact/component, vulnerability and
remediation statuses, reason, dependency path, and nullable retained generation.
Restart findings bind action, nullable process/service/artifact, advisory IDs, and
reason. Coverage is `not-requested`, `complete`, `partial`, or `unknown`. An
`incomplete-remediation` outcome uses exit 3 and retains every unresolved finding,
including after committed updates. Inspection with actions or incomplete coverage
also uses exit 3; `ok` uses 0, `refused` uses 2, and execution errors use 1.

Reject unsupported versions before effects. Regenerate plans and locks from
authenticated exact records and explicit selections; require fresh source-build
consent at execution. No migration may infer repository choices or consent from
old records. [DATABASE](DATABASE.md#104-security-and-scheduler-projection-version-3)
defines the separately versioned cache/coordinator reconstruction. Schemas and
decision models do not prove runtime remediation, isolation, or publication durability.

## History

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v0.9 | September 2026 | Add security and farm contract versions, authority-preserving reconstruction, and structural/model acceptance boundaries. |
| v0.8 | September 2026 | Close recovery storage, signed checkpoint, admission, activation, grouped conflict, batch grammar, and command outcome contracts; specify protected-volume pending-reboot and manager-integrity commit boundaries with structural schemas and model cases. Runtime/platform acceptance remains pending. |
| v0.7 | September 2026 | Specify guided recovery, trusted prefix rebuilding, committed execution catalogs, mixed-orchard transactions, explicit waiting, helper ownership, and post-commit service checks; record owner-approved storage, trust, isolation, activation, and command decisions, superseded rules, UX targets, and pending implementation acceptance. |
| v0.6 | September 2026 | Cross-link cumulative lock waits, phase-aware stopping, and bounded recovery without weakening commit or fingerprint rules. |
| v0.5 | September 2026 | Integrate separate SQLite roles, indefinite compact choice/history records, coordinated backups, and copy-migration compatibility; preserve the existing external-effect and trust recovery contracts. |
| v0.4 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |
| v0.3 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v0.2 | September 2026 | prose rewrite of the rollback transaction explanation; no content changes. |

</details>
