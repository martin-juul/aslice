# State, artifacts, and recovery

- **Status:** Specification v0.6 — September 2026. These contracts are specified, not implemented or validated on macOS.
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

Lock waits and cancellation follow [DATABASE §10.1](DATABASE.md#101-contention-and-safe-stopping): one configurable 30-second foreground allowance spans owner and SQL locks, with one separate 30-second recovery allowance. A timeout before effects resolves prepared intent; after effects it enters fingerprint-checked recovery. A durable commit is preserved even if projection reconciliation remains pending. Unresolved recovery retains evidence and blocks mutations; cancellation requests a safe stopping point.

One process holds the prefix mutation lock before changing state; it rechecks the planned base generation after acquiring it. Privileged operations additionally take the system-root lock, always after the prefix lock. GC follows the same order. Cross-prefix privileged operations serialize at the system lock. Locks are OS-managed and released on process death; durable journals survive that release.

Each transaction records its identifier, base and proposed generation digests, exact artifact set, authorization, ordered operations, before/after fingerprints, backups, and progress. Privileged journals and backups live in the protected root. Before-images preserve file kind, bytes, mode, owner, ACLs, xattrs, and symlink targets where supported; unsupported metadata is a preflight refusal. Files, journal records, and affected directory entries are flushed before the next durable phase. HFS+ and APFS power-loss behavior must be validated, including the selected `fsync`/`F_FULLFSYNC` strategy; rename atomicity alone is not durability.

The state machine is `prepared → applying → activated → committed`, with `recovering`, `rolled-back`, and `needs-attention` outcomes. Preparation authenticates and stages everything, takes durable backups, validates expected state, and persists the complete intent before live changes. Applying quiesces services and performs journaled external operations. Activation switches the profile and protected pointers, then records the new generation in SQLite. Commit follows reconciliation and health checks. There is no atomic primitive spanning SQLite, both pointers, and external state; the journal supplies recovery.

On restart, mutations and GC stop until recovery completes. If no durable commit exists, recovery examines the actual pointers and operation fingerprints and restores the before-state, idempotently, in reverse order. A committed transaction reconciles its after-state. Before either forward or inverse writes, compare the current object with the recorded expected fingerprint. Concurrent external edits, missing backups, or inaccessible privileged state produce `needs-attention` with exact paths and remedies; they are never overwritten silently. Disk-full failures retain the journal and backups. Generations and affected artifacts remain GC roots until resolution.

Machine apply is one managed-state transaction: a failed step rolls back the entire apply. Trust establishment is a separate explicit prerequisite and is never reset by package rollback ([SETUP §3.2](SETUP.md#the-plan-and-the-order-of-operations)).

Rollback records a new transaction in the journal, preserving the history of earlier transactions. When rollback spans several generations, it computes the target managed state and checks for conflicts. Service plists and protected closures are restored together with the package generation; changed declarations require regenerated plists. Preferences and login-shell settings use recorded before-values, and intervening external edits are reported as conflicts.

Package rollback does not restore application databases, userbases, or remote systems. Before a service upgrade that can migrate persistent data, require a declared backward-compatibility contract or a tested backup/restore procedure and explicit authorization; otherwise refuse automated upgrade of the running service. A pid check is only process liveness. Service-specific readiness and data compatibility determine whether automatic rollback is permitted. Unattended service failure returns failure and retains evidence unless the caller explicitly selected a valid rollback procedure.

<a id="self-update-and-decommission"></a>

## 6. Self-update and decommission

A known-good supervisor remains alive while the new manager runs as a child against a prepared state snapshot. It validates execution, version, database compatibility, index reading, and a bounded health timeout before activation. Post-activation failure is recovered by that supervisor or, after power loss, by a protected bootstrap recovery entry point retained outside the switched generation. The recovery entry point is updated separately only after the replacement has passed recovery drills. Old managers remain usable with their compatible state snapshots; switching back after newer writes requires compatible replay so it cannot erase choices or high-water state ([DATABASE](DATABASE.md#10-sqlite-connection-and-migration-policy)). Destructive in-place database migrations are forbidden; use a versioned copy and journal its activation.

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

## History

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v0.6 | September 2026 | Cross-link cumulative lock waits, phase-aware stopping, and bounded recovery without weakening commit or fingerprint rules. |
| v0.5 | September 2026 | Integrate separate SQLite roles, indefinite compact choice/history records, coordinated backups, and copy-migration compatibility; preserve the existing external-effect and trust recovery contracts. |
| v0.3 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v0.2 | September 2026 | prose rewrite of the rollback transaction explanation; no content changes. |
| v0.4 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |

</details>
