# aslice Nomenclature — The Words of the Project

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

- **Status:** Reference v0.17 — September 2026
- **Companions:** [DESIGN.md](DESIGN.md), [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md), [AUTHORING.md](AUTHORING.md), [BUILD-INFRA.md](BUILD-INFRA.md), [ORCHARD-POLICY.md](ORCHARD-POLICY.md), [REPOSITORIES.md](REPOSITORIES.md), [MANUAL.md](MANUAL.md), [SETUP.md](SETUP.md), [TOOLCHAIN.md](TOOLCHAIN.md)
- **Audience:** every reader. When a document uses a word you do not know, it is defined here — or should be.

A project that names everything owes its readers a place where the names are explained. This is that place. Terms are defined once, in one line where possible, with a pointer to the document that owns the term. Section links identify the owning contract; the current linked documents take precedence over historical companion-version pins.

<a id="conventions"></a>

## 1. Conventions

- **Bold** introduces the term being defined.
- *(DOC §x)* names the document that defines the term authoritatively; the definition here is a summary, and the pointer wins on any disagreement.
- *cf.* points at a related term you probably also want.
- *Not to be confused with* separates terms that collide in casual speech.

<a id="project-vocabulary"></a>

## 2. Project vocabulary

The words we made up, or made ours.

**slice** — the binary package: a payload and canonical metadata delivered in a zstd-compressed archive with a detached signature; vendor payloads may be universal. Also the ecosystem's name and the pun the project is built on. *([DESIGN §6.2](DESIGN.md#binary-package-format-slice) and [DESIGN §9](DESIGN.md#distribution-and-the-build-farm).)*

**orchard** — a Git repository of formula directories; compiled into a signed distribution repository. *(README; [REPOSITORIES §1](REPOSITORIES.md#axioms).)*

**formula** — the build description: a TOML file naming source, dependencies, phases, and invariants. Lives in a repository; produces slices. *([DESIGN §6.1](DESIGN.md#formulae-are-data-with-a-hermetic-build-script); [PACKAGE-FORMAT §3](PACKAGE-FORMAT.md#packagetoml--full-schema).)*

**repository** — a signed static distribution tree of indexes, authenticated recipes, manifests, and blobs. `repo.toml` configures its namespace and author metadata. *([REPOSITORIES §1](REPOSITORIES.md#axioms); [STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#compatibility-and-artifact-identity).)*

**official / core / extended** — the official orchard is the project-run repository (and the top trust level, [REPOSITORIES §3](REPOSITORIES.md#trust-levels)); **core** (~300 packages) and **extended** (~2,000) are its two tiers, with different acceptance bars and prebuild guarantees. *([ORCHARD-POLICY §2](ORCHARD-POLICY.md#orchard-tiers-and-the-acceptance-bar); [DESIGN §9.4](DESIGN.md#what-gets-prebuilt).)*

**flavor** — the µarch build of a slice: v1 (SSE2 baseline, every 64-bit Intel Mac), v2 (SSE4.2/POPCNT), v3 (AVX2). A formula declares which flavors it ships; the installer picks the best one your CPU understands, detected by sysctl at install time. *([DESIGN §4.2](DESIGN.md#the-µarch-axis-grows-three-flavors); [PACKAGE-FORMAT §3.3](PACKAGE-FORMAT.md#flavors--minimum-instruction-set); [MANUAL §4.2](MANUAL.md#flavors-matching-builds-to-your-cpu).)* *Not to be confused with* variant.

**store** — `<prefix>/store/<artifact-hex>/`, immutable artifact materializations verified against canonical manifests and installed-byte receipts. *([STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#compatibility-and-artifact-identity).)*

**generation** — an exact package view; its pointer switches atomically, while associated external effects require a journaled recovery transaction. *([STATE-AND-RECOVERY §5](STATE-AND-RECOVERY.md#durable-transactions-and-recovery).)*

**profile** — `<prefix>/profiles/<name>`, the merged symlink forest (bin/, lib/, share/, …) that points at the current generation: `/opt/aslice/profiles/default/bin` is what your shell's PATH actually sees. *([DESIGN §8.1](DESIGN.md#layout) and [DESIGN §8.2](DESIGN.md#profiles-as-the-interoperability-surface).)*

**shim** — the multicall executable that sits ahead of the profile on PATH and dispatches a bare tool name (`php`) to the selected runtime stream; exec-only, with no package knowledge and no state of its own. *([DESIGN §8.5](DESIGN.md#shims-the-multiplexing-layer) and [DESIGN §12.9](DESIGN.md#multi-version-runtimes-use-pin-default--and-version-bound-extensions).)* *Not to be confused with* aslice-system.

**aslice-system** — the privileged helper: the small sudo-authorized executable that performs the privileged half of an operation — kext placement, system patches, elevated grafts — and nothing more. *([DESIGN §10.4](DESIGN.md#privilege-discipline) and [DESIGN §12.7](DESIGN.md#system-software-kexts-and-sip-disabled-development-tools).)*

**stream** — one version line of a multi-version runtime: php 8.4 is a stream. Streams are selected per session, per project, or per profile default, and extensions bind to one. *([DESIGN §12.9](DESIGN.md#multi-version-runtimes-use-pin-default--and-version-bound-extensions); [MANUAL §6.1](MANUAL.md#streams-and-installing-them); [SETUP §2.3](SETUP.md#runtimes).)*

**leaf** — a package with no installed reverse dependencies; this does not determine whether it was explicitly requested. `on_request` roots govern autoremove. *([DESIGN §8.4](DESIGN.md#garbage-collection-discipline).)*

**tombstone** — the permanent record a removed formula leaves in a repository index: name, final version, reason, replacement — so historical snapshots and old locks resolve forever; the `aslice orchard tombstone` verb writes one. *([PACKAGE-FORMAT §3.14](PACKAGE-FORMAT.md#deprecation--the-package-lifecycle-declared-v06); [ORCHARD-POLICY §8](ORCHARD-POLICY.md#deprecation-and-removal-lifecycle); [DESIGN §12.14](DESIGN.md#orchard-maintenance-the-maintainers-cli).)* *(An earlier edition of this entry used the word for a negated declaration in the setup file — "this shall not be present." That feature does not exist: `aslice machine apply` asserts what the file declares and never removes what it does not mention, except under the bounded `--prune` mode. [SETUP §3](SETUP.md#aslice-machine-apply); [DESIGN §12.13](DESIGN.md#declarative-system-setup-aslice-machinetoml-and-the-aslice-machine-commands).)*

**wishlist** — the user-authored package constraints in a machine file, resolved into exact artifacts. *([SETUP §2](SETUP.md#the-file).)*

**lock** — `aslice.lock`, the recorded resolution of a profile: exact versions and hashes, replayable with `aslice apply`. *([PACKAGE-FORMAT §7](PACKAGE-FORMAT.md#lock-files).)*

**index snapshot** — a repository's frozen index at a commit, shipped as zstd JSON snapshots plus diffs. Apply resolves against snapshots, not against moving Git heads. *([DESIGN §9.6](DESIGN.md#the-repository-system); [SETUP §3.2](SETUP.md#the-plan-and-the-order-of-operations).)*

**plan** — the output of resolution: the exact set of fetch, build, link, and remove steps an apply will perform, shown before anything happens. *([DESIGN §12.1](DESIGN.md#commands) and [DESIGN §12.2](DESIGN.md#interaction-principles); [SETUP §3.2](SETUP.md#the-plan-and-the-order-of-operations).)*

**farm** — the CI build fleet as a whole. *([BUILD-INFRA §1](BUILD-INFRA.md#the-founding-axiom) and [BUILD-INFRA §5](BUILD-INFRA.md#farm-topology).)*

**coordinator** — the farm's scheduler: hands out jobs, collects results, keeps the ledger. *([BUILD-INFRA §5](BUILD-INFRA.md#farm-topology) and [BUILD-INFRA §6](BUILD-INFRA.md#scheduling-plan-lanes-leases).)*

**agent** — a build host: a real Mac of a known µarch that executes jobs under Seatbelt. *([BUILD-INFRA §5](BUILD-INFRA.md#farm-topology) and [BUILD-INFRA §7.2](BUILD-INFRA.md#agents-are-expendable).)*

**signing host** — the dedicated networked release Pi: automatically verifies publisher-authenticated candidates, owner-merge authorization, gates, and retained signing state, then signs slices, targets, and snapshots with distinct keys; never runs package builds or supplied scripts. A separate offline Pi holds root authority. *([BUILD-INFRA §5](BUILD-INFRA.md#farm-topology) and [BUILD-INFRA §7](BUILD-INFRA.md#trust-owner-merge-authorizes-processing-agents-produce-evidence); [KEY-RUNBOOK §1](runbooks/KEY-RUNBOOK.md#key-inventory-and-machines).)*

**publisher** — the restricted VM on the owned Mac Pro that checks gates, automatically delivers authenticated candidates, verifies returned signatures, and serializes atomic publication of complete releases. Holds the timestamp key and publication credentials, but no root or release private keys. *([BUILD-INFRA §5](BUILD-INFRA.md#farm-topology) and [BUILD-INFRA §9](BUILD-INFRA.md#from-result-to-repository).)*

**job / result** — the JSONL work unit handed to an agent and the signed outcome handed back. *([BUILD-INFRA §2](BUILD-INFRA.md#the-harness-one-binary-four-modes-one-sandboxed-core).)*

**evidence builder** — the independent second builder whose output is compared bitwise against the first: the reproducibility oracle. *([BUILD-INFRA §7.4](BUILD-INFRA.md#community-builders--the-users-machine-enlisted-safely).)*

**quarantine** — the untrusted staging area every agent result lands in; nothing is ever served from it, and publication requires the six gates, automatic release signing, and publisher verification. *([BUILD-INFRA §7.1](BUILD-INFRA.md#quarantine).)*

**genesis** — the from-nothing bootstrap: building the toolchain that builds the toolchain, from a golden image upward. *([GENESIS §1](runbooks/GENESIS.md#the-from-nothing-sequence) and [GENESIS §2](runbooks/GENESIS.md#the-genesis-inventory); [DESIGN §14](DESIGN.md#roadmap).)*

**vendored sources** — the blob archive of upstream tarballs the project keeps so that dead URLs cannot kill old builds. *([DESIGN §9.6](DESIGN.md#the-repository-system); [GENESIS §3](runbooks/GENESIS.md#the-never-lose-set).)*

**dashboard** — the farm's public web dashboard at aslice.sh/dashboard: build status, freshness, quarantine — farm-side metrics only; there is no user telemetry to show. *([DESIGN §13.4](DESIGN.md#governance); [BUILD-INFRA §10](BUILD-INFRA.md#farm-side-metrics-the-only-kind-there-are); [ORCHARD-POLICY §9](ORCHARD-POLICY.md#freshness-livecheck-and-autobump).)*

**transparency log** — the append-only, signed record of everything published; the public answer to "who released this, when." *([DESIGN §13.4](DESIGN.md#governance); [BUILD-INFRA §7.5](BUILD-INFRA.md#the-malware-signature-gate).)*

**build_id** — the compatibility key computed from declared build inputs; not a digest of output bytes. **artifact_id** identifies the canonical manifest and payload; **blob_digest** identifies the delivered archive. *([STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#compatibility-and-artifact-identity).)*

**ABI epoch** — a declared break in binary compatibility for a package (`abi = true` variants rebuild the reverse-dependency cone). *([DESIGN §7.3](DESIGN.md#the-abi-contract-the-mach-o-insight); [AUTHORING §5](AUTHORING.md#variants-and-the-abi-contract).)*

**provenance** — the recorded lineage of a slice: source hash, formula commit, builder, evidence. Checked at the pre-gate. *([DESIGN §9.5](DESIGN.md#build-provenance); [BUILD-INFRA §7](BUILD-INFRA.md#trust-owner-merge-authorizes-processing-agents-produce-evidence).)*

**origin=local-build** — the attribution label on a slice built on your machine rather than fetched; never confused with a farm build. *([BUILD-INFRA §3](BUILD-INFRA.md#the-pipeline-shared-at-both-scales) and [BUILD-INFRA §4](BUILD-INFRA.md#user-mode-aslice-build).)*

**state DB** — the client SQLite projection recording what is installed, why, and from where; durable choice/history records reconstruct it. Cache, protected system state, coordinator, publisher, and release signer use separate databases ([DATABASE](DATABASE.md)). *([DESIGN §8.1](DESIGN.md#layout); [REPOSITORIES §11](REPOSITORIES.md#the-state-databases-role).)*

**pin** — a *version pin* (`aslice pin`) holds an installed package at its exact release, and the lock records it ([MANUAL §3.3](MANUAL.md#holding-a-package-pin-and-unpin); [PACKAGE-FORMAT §7](PACKAGE-FORMAT.md#lock-files)). *Not to be confused with* hash-pinning: every source artifact's sha256 is declared in the formula and countersigned in the index ([AUTHORING §1](AUTHORING.md#overview); [DESIGN §10.2](DESIGN.md#signatures-and-repository-integrity-tuf)).

**ride** — a ride-along utility: a small package that installs alongside another and is governed by the parent's lifecycle. *([DESIGN §12.9](DESIGN.md#multi-version-runtimes-use-pin-default--and-version-bound-extensions); [PACKAGE-FORMAT §3.13](PACKAGE-FORMAT.md#runtime-extension-ride--multi-version-runtimes-v05).)*

**extension** — a package bound to one runtime stream: php-redis, ruby-pg. Declared with `[extension]`, loaded through the runtime's scan dir, rebuilt when the stream's extension-ABI epoch bumps. *([PACKAGE-FORMAT §3.13](PACKAGE-FORMAT.md#runtime-extension-ride--multi-version-runtimes-v05); [DESIGN §12.9](DESIGN.md#multi-version-runtimes-use-pin-default--and-version-bound-extensions); [MANUAL §6.3](MANUAL.md#extensions-and-ecosystem-tools).)*

**service** — a package-managed launchd unit, declared by the formula and driven by `aslice service`. *([MANUAL §7](MANUAL.md#running-services); [DESIGN §12.8](DESIGN.md#services-launchd-native-lifecycle-and-safe-upgrades).)*

**system package / system patch** — effect-derived privileged capabilities; root services and kexts require `system`, Apple-file replacement requires `system-patch`. `/System` and boot-critical targets remain refused. *([STATE-AND-RECOVERY §3](STATE-AND-RECOVERY.md#privileged-ownership-and-capability-checks); SYSTEM-VOLUMES.)*

**aslice-machine.toml / machine apply / machine export / machine import / adopt** — the declarative core: the file that says what you want, the command that makes it so, the command that writes the file from reality, the command that translates a Brewfile into the file, the command that claims an existing Homebrew install as a plan. *([SETUP §2](SETUP.md#the-file) and [SETUP §5](SETUP.md#aslice-machine-import---from-brewfile); [DESIGN §12.13](DESIGN.md#declarative-system-setup-aslice-machinetoml-and-the-aslice-machine-commands); [MANUAL §10](MANUAL.md#one-file-one-command-rebuilding-a-machine) and [MANUAL §11](MANUAL.md#aslice-and-homebrew).)*

**graft** — a vendor installer script, declared in the formula (`[[binary.graft]]`), hash-pinned, approved by the user per package, sandboxed to its declared behavior, and recorded for rollback; the sole exception to "no package code at install". *([DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible); [PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software); [MANUAL §4.5](MANUAL.md#grafts-when-installing-takes-a-script).)* *cf.* behavior manifest, rehearsal.

<a id="trust-and-security"></a>

## 3. Trust and security

**TUF** — The Update Framework: the roles-and-thresholds design our repository metadata signing follows. *([DESIGN §10.2](DESIGN.md#signatures-and-repository-integrity-tuf); [REPOSITORIES §5](REPOSITORIES.md#signing-keys-two-schemes-one-verification-pipeline).)*

**TOFU** — trust on first use: the first fetch of a repository key is the moment of trust; afterwards, changes must be explained. *([REPOSITORIES §4](REPOSITORIES.md#adding-a-third-party-repository).)*

**countersignature** — a second, project-held signature: over a community repository's key it earns the `verified` trust level, and the index countersigns every source hash. *([REPOSITORIES §3](REPOSITORIES.md#trust-levels); [DESIGN §10.2](DESIGN.md#signatures-and-repository-integrity-tuf).)*

**trust level** — a repository's standing: official, verified, third-party, or local. Capabilities follow the level. *([REPOSITORIES §3](REPOSITORIES.md#trust-levels); [DESIGN §12.3](DESIGN.md#orchards-repositories-and-trust-levels).)*

**capability** — a named permission a formula may request (system-package, system-patch); granted per repository, per level, never silently. *([DESIGN §12.7](DESIGN.md#system-software-kexts-and-sip-disabled-development-tools) and [DESIGN §12.11](DESIGN.md#system-patches-flagged-reversible-replacement-of-apple-provided-files); [REPOSITORIES §3](REPOSITORIES.md#trust-levels).)*

**per-repo grant** — the recorded user decision that this repository may exercise that capability on this machine. *([REPOSITORIES §3](REPOSITORIES.md#trust-levels) and [REPOSITORIES §7](REPOSITORIES.md#aslice-repo-command-surface-completed).)*

**signer pinning** — remembering which keys may sign a repository's metadata, or which Developer ID may sign a vendor artifact, and refusing surprises. *([REPOSITORIES §5](REPOSITORIES.md#signing-keys-two-schemes-one-verification-pipeline); [ORCHARD-POLICY §12](ORCHARD-POLICY.md#vendor-binary-packages-pkgdmg).)*

**notarization** — Apple's server-side ticket stapling for Developer-ID software; aslice's own bootstrap trust is notarization plus signature, and a vendor artifact's notarization status is pinned in provenance. *([DESIGN §12.12](DESIGN.md#self-update-aslice-is-package-zero) and [DESIGN §9.5](DESIGN.md#build-provenance).)*

**Gatekeeper** — macOS's first-launch policy layer; on 10.11–12 it still decides what may open. *([DESIGN §12.12](DESIGN.md#self-update-aslice-is-package-zero).)*

**XProtect** — Apple's built-in signature-based malware list; present on all supported systems. *([BUILD-INFRA §7.5](BUILD-INFRA.md#the-malware-signature-gate).)*

**key ceremony** — recorded generation or transition of root authority. Initial setup is owner-operated; witnesses and independent custodians are not launch requirements. *([KEY-RUNBOOK §2](runbooks/KEY-RUNBOOK.md#initial-root-setup).)*

**threshold root** — TUF root metadata requiring signatures from k distinct keys out of n authorized root keys, not a split private key. Initial custody is 1-of-1; independent multi-party custody can follow through authenticated rotation. *([DESIGN §10.2](DESIGN.md#signatures-and-repository-integrity-tuf); [KEY-RUNBOOK §1](runbooks/KEY-RUNBOOK.md#key-inventory-and-machines).)*

**minisign** — the small Ed25519 signature tool used for human-legible signatures. *([KEY-RUNBOOK §1](runbooks/KEY-RUNBOOK.md#key-inventory-and-machines); [DESIGN §10.2](DESIGN.md#signatures-and-repository-integrity-tuf).)*

**Ed25519** — the elliptic-curve signature scheme used throughout; small keys, fast verification. *([DESIGN §10.2](DESIGN.md#signatures-and-repository-integrity-tuf); [KEY-RUNBOOK §1](runbooks/KEY-RUNBOOK.md#key-inventory-and-machines).)*

**OpenPGP / WKD** — the older signature ecosystem and its Web Key Directory discovery; used where upstreams already speak it. *([REPOSITORIES §5](REPOSITORIES.md#signing-keys-two-schemes-one-verification-pipeline).)*

**revocation / blocking event / re-pin / repo frozen** — the failure vocabulary: a key is revoked, a blocking event halts publishes, users re-pin to successor keys, a compromised repository is frozen. *([KEY-RUNBOOK §4](runbooks/KEY-RUNBOOK.md#compromise-response); [REPOSITORIES §4](REPOSITORIES.md#adding-a-third-party-repository) and [REPOSITORIES §8](REPOSITORIES.md#failure-and-edge-cases).)*

<a id="building-and-packaging"></a>

## 4. Building and packaging

**aslice-toolchain / stage0 / stage1** — the self-hosted compiler bundle (Clang, LLD or ld64, a modern libc++, CMake, Ninja, pkgconf) every build uses; stage0 is built by Apple's host Clang against the oldest archived SDK, stage1 rebuilds the toolchain with itself, and both stages are archived forever. *(TOOLCHAIN.md; [DESIGN §4.3](DESIGN.md#toolchain-floor--self-hosted-from-day-one); [GENESIS §1](runbooks/GENESIS.md#the-from-nothing-sequence) and [GENESIS §3](runbooks/GENESIS.md#the-never-lose-set).)*

**variant** — a formula's declared feature switch: `+ssl`, `+x265`. Marked `abi = true`, a variant joins the build identity and its flip rebuilds the reverse-dependency cone; `abi = false` stays link-compatible. *([AUTHORING §5](AUTHORING.md#variants-and-the-abi-contract); [PACKAGE-FORMAT §3.5](PACKAGE-FORMAT.md#variants--feature-switches-with-abi-tags); [DESIGN §7.1](DESIGN.md#the-three-kinds-of-build-time-choice).)* *Not to be confused with* flavor.

**livecheck** — the formula stanza that knows how to ask upstream "is there a newer release?" *([PACKAGE-FORMAT §3.15](PACKAGE-FORMAT.md#livecheck--upstream-freshness-declared-v06); [AUTHORING §7.1](AUTHORING.md#livecheck-and-autobump).)*

**autobump / bump-pr** — the machinery that turns a livecheck hit into a version-bump pull request. *([ORCHARD-POLICY §9](ORCHARD-POLICY.md#freshness-livecheck-and-autobump); [BUILD-INFRA §6.2](BUILD-INFRA.md#lanes); [AUTHORING §7.1](AUTHORING.md#livecheck-and-autobump).)*

**cooldown / throttle** — the rate limits that keep autobump polite: minimum time between bumps of one formula, maximum bumps per sweep. *([ORCHARD-POLICY §9](ORCHARD-POLICY.md#freshness-livecheck-and-autobump).)*

**revision vs version** — version is upstream's number; revision is ours, bumped when the formula changes but the source does not. *([PACKAGE-FORMAT §4.4](PACKAGE-FORMAT.md#revision-and-epoch).)*

**min_os / max_os** — the macOS range a slice claims to support; enforced at install. *([PACKAGE-FORMAT §3.2](PACKAGE-FORMAT.md#platform-bounds--minimum-os-maximum-os).)*

**payload-only** — a slice with no build phase and no grafts: repackaged upstream bits. The default even for vendor binaries. *([ORCHARD-POLICY §12](ORCHARD-POLICY.md#vendor-binary-packages-pkgdmg); [PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software).)*

**vendor binary / redistribute** — upstream's own build, repackaged and hosted by the farm (`redistribute = true`) or fetched from the vendor at install (`redistribute = false`); the cask-shaped case. An installer script the software genuinely needs is declared as a graft, never run silently. *([ORCHARD-POLICY §12](ORCHARD-POLICY.md#vendor-binary-packages-pkgdmg); [DESIGN §12.4](DESIGN.md#vendor-binaries-pkgdmg-and-gui-apps) and [DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible).)*

**universal payload / 32-bit** — a slice carrying both i386 and x86_64 slices of a library, for the shrinking set that still needs i386. *([DESIGN §2.2](DESIGN.md#non-goals) and [DESIGN §12.4](DESIGN.md#vendor-binaries-pkgdmg-and-gui-apps); [PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software).)*

**ABI gate / symbol fingerprint** — the automated check that a rebuilt library still exports what it exported; the fingerprint is the sorted symbol list it compares. *([BUILD-INFRA §6.1](BUILD-INFRA.md#the-build-plan) and [BUILD-INFRA §7.1](BUILD-INFRA.md#quarantine); [AUTHORING §5.2](AUTHORING.md#what-the-abi-scan-does-with-this).)*

**install name / compatibility version** — the Mach-O dylib identity and its declared ABI number; both must survive a rebuild. *([DESIGN §7.3](DESIGN.md#the-abi-contract-the-mach-o-insight).)*

**reproducibility classes** — bitwise (identical output), normalized (identical after known fix-ups), unreproducible (declared, tracked, not hidden). *([BUILD-INFRA §7.3](BUILD-INFRA.md#reproducibility-classes).)*

**ctx / phases** — the build context object passed through the formula's ordered phases (fetch, patch, configure, build, check, install). *([AUTHORING §4](AUTHORING.md#buildstar-the-build-script); [PACKAGE-FORMAT §6.1](PACKAGE-FORMAT.md#phase-model).)*

**Seatbelt profile** — the sandbox policy a build runs under; the filesystem and network it may touch. *([DESIGN §10.5](DESIGN.md#sandboxed-builds); [BUILD-INFRA §2](BUILD-INFRA.md#the-harness-one-binary-four-modes-one-sandboxed-core).)*

**behavior manifest** — the complete declared effect set for a graft. Approval binds its digest; an enforced isolated staging boundary and a helper-validated commit constrain execution. Network access is refused in v1; rehearsal is evidence, not containment. *([STATE-AND-RECOVERY §4](STATE-AND-RECOVERY.md#graft-execution-boundary); [PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software).)*

**rehearsal** — the farm running a graft-bearing install in a per-OS VM under instrumentation and diffing the observed behavior against the declared behavior manifest; only an exact match gets the manifest signed. Also runnable locally via `aslice orchard ci`. *([ORCHARD-POLICY §10](ORCHARD-POLICY.md#merge-gates-what-ci-must-prove); [DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible); [BUILD-INFRA §6.4](BUILD-INFRA.md#pr-gates).)*

**buildroot / DESTDIR staging** — the throwaway tree a build installs into before the payload is harvested. *([AUTHORING §4](AUTHORING.md#buildstar-the-build-script).)*

**ccache / SOURCE_DATE_EPOCH / prefix-mapping** — the reproducibility toolkit: compiler cache, clamped timestamps, rewritten embedded paths. *([ORCHARD-POLICY §15](ORCHARD-POLICY.md#reproducibility-and-the-build-environment); [BUILD-INFRA §3](BUILD-INFRA.md#the-pipeline-shared-at-both-scales); [DESIGN §11](DESIGN.md#performance-model).)*

**smoke test** — the post-install "does it run at all" check a formula declares. *([AUTHORING §6](AUTHORING.md#tests).)*

**matrix / lanes** — the farm's build grid (µarch × macOS) and its queues: freshness, trunk, backfill. *([BUILD-INFRA §8](BUILD-INFRA.md#the-vm-test-matrix) and [BUILD-INFRA §6.2](BUILD-INFRA.md#lanes).)*

**lease / pre-gate / backlog sweep** — the coordinator's work mechanics: a job's exclusive claim, the checks before publish, the periodic mop-up of stale work. *([BUILD-INFRA §6.3](BUILD-INFRA.md#leases-not-locks) and [BUILD-INFRA §7.5](BUILD-INFRA.md#the-malware-signature-gate).)*

<a id="macos-platform-terms"></a>

## 5. macOS platform terms

**SIP** — System Integrity Protection: the kernel policy that makes `/System` and friends read-only even to root. Present but older on our systems; the system-patch capability exists because of it. *([DESIGN §12.7](DESIGN.md#system-software-kexts-and-sip-disabled-development-tools) and [DESIGN §12.11](DESIGN.md#system-patches-flagged-reversible-replacement-of-apple-provided-files).)*

**kext** — a kernel extension; signing rules tighten across our range. *([DESIGN §12.7](DESIGN.md#system-software-kexts-and-sip-disabled-development-tools); [PACKAGE-FORMAT §3.12](PACKAGE-FORMAT.md#system--kernel-extensions-and-sip-disabled-tools-v04).)*

**launchd / plist / user vs root domain** — Apple's service manager, its XML/JSON property lists, and the per-user versus system-wide contexts a service may live in. *([MANUAL §7](MANUAL.md#running-services); [DESIGN §12.8](DESIGN.md#services-launchd-native-lifecycle-and-safe-upgrades).)*

**defaults domain** — a preferences namespace addressed by `defaults(1)`. *([SETUP §2.6](SETUP.md#defaults).)*

**/etc/shells / chsh** — the list of valid login shells and the tool that changes yours; both matter when aslice ships a shell. *([SETUP §2.5](SETUP.md#shell).)*

**System keychain / SecureTransport** — the OS credential store and Apple's TLS stack. aslice's own TLS clients use their private bundle and packaged crypto stack; System-keychain updates are a separate opt-in operation. *([DESIGN §12.10](DESIGN.md#trust-store-modern-ca-certificates-on-a-frozen-platform); [MANUAL §8](MANUAL.md#keeping-tls-alive-on-an-old-os).)*

**dyld / dyld shared cache** — the dynamic linker and its prelinked cache of system libraries. *([DESIGN §7.3](DESIGN.md#the-abi-contract-the-mach-o-insight) and [DESIGN §11](DESIGN.md#performance-model).)*

**Mach-O / dylib / framework** — the executable format, the shared-library form, and the bundled-library directory form. *([DESIGN §7.3](DESIGN.md#the-abi-contract-the-mach-o-insight).)*

**universal binary** — one file containing several architectures' code, `lipo`-ed together. *([PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software); [DESIGN §12.4](DESIGN.md#vendor-binaries-pkgdmg-and-gui-apps).)*

**i386 / x86_64** — 32-bit and 64-bit Intel; 10.11–12 is the last range where both matter. *([DESIGN §1.2](DESIGN.md#who-the-users-are) and [DESIGN §2.2](DESIGN.md#non-goals).)*

**SSE4.2 / POPCNT / AVX2 / µarch** — instruction-set levels and microarchitecture: the farm builds per-µarch so a Core 2 Duo and a Coffee Lake each get code that fits. *([DESIGN §4.2](DESIGN.md#the-µarch-axis-grows-three-flavors).)*

**Core 2 Duo / Nehalem / Ivy Bridge / Haswell / Coffee Lake** — the Intel generations our µarch lanes are named for. *([DESIGN §4.2](DESIGN.md#the-µarch-axis-grows-three-flavors); [BUILD-INFRA §5](BUILD-INFRA.md#farm-topology).)*

**APFS / HFS+ / rename(2)** — the two filesystems in range and the atomic-swap syscall generations rely on. *([DESIGN §4.1](DESIGN.md#the-os-axis-collapses--at-1011) and [DESIGN §8.3](DESIGN.md#generations-atomic-switching-and-rollback).)*

**golden image / createinstallmedia / Recovery** — the pristine OS install the farm starts from, Apple's installer-to-USB tool, and the recovery partition. *([GENESIS §2](runbooks/GENESIS.md#the-genesis-inventory); [BUILD-INFRA §8](BUILD-INFRA.md#the-vm-test-matrix).)*

**Developer ID / pkg / dmg / LSMinimumSystemVersion** — Apple's signing program, its installer package and disk-image containers, and the Info.plist floor for what an app will launch on. *([DESIGN §12.4](DESIGN.md#vendor-binaries-pkgdmg-and-gui-apps); [PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software); [ORCHARD-POLICY §12](ORCHARD-POLICY.md#vendor-binary-packages-pkgdmg).)*

<a id="acronyms"></a>

## 6. Acronyms

| Term | Expansion | Meaning |
|---|---|---|
| ABI | application binary interface | application binary interface |
| CA | certificate authority | certificate authority |
| CI | continuous integration | continuous integration |
| CLI | command-line interface | command-line interface |
| CPE | Common Platform Enumeration | platform identifiers |
| CVE | Common Vulnerabilities and Exposures | vulnerability identifiers |
| DAG | directed acyclic graph | directed acyclic graph; the shape of dependency relations |
| EBNF | extended Backus–Naur form | extended Backus–Naur form; PACKAGE-FORMAT grammar notation |
| EOL | end of life | end of life |
| HTTP/2 | Hypertext Transfer Protocol, version 2 | the fetch transport |
| ISO-8601 | ISO 8601 date and time standard (a standard identifier) | the date format used for timestamps |
| JSONL | JavaScript Object Notation Lines | JSON lines, one record per line |
| LRU | least recently used | least recently used |
| OSV | Open Source Vulnerabilities | the Open Source Vulnerabilities database |
| PUP | potentially unwanted program | potentially unwanted program |
| SBOM | software bill of materials | software bill of materials |
| SLSA | Supply-chain Levels for Software Artifacts | supply-chain integrity framework |
| SPDX | System Package Data Exchange (formerly Software Package Data Exchange) | the license-identifier standard |
| SQLite | SQLite (a product name; SQL means Structured Query Language) | the embedded database |
| TLS | Transport Layer Security | transport layer security |
| TOML | Tom's Obvious, Minimal Language | the config format formulas and setup files use |
| TTY | teletype | terminal |
| UTC | Coordinated Universal Time | the timezone used for timestamps |
| VM | virtual machine | virtual machine |
| WAL | write-ahead log | write-ahead log mode |
| XDG | Cross-Desktop Group | the freedesktop directory specification, borrowed for paths |

<a id="the-homebrew-translation-table"></a>

## 7. The Homebrew translation table

For readers arriving from the other orchard. The left word is theirs; the right is ours.

| Homebrew | aslice |
|---|---|
| keg | a store path containing one exact materialized artifact |
| Cellar | the store |
| bottle | a slice (binary package) |
| pour | install a slice from binary |
| tap | an orchard (Git recipe tree); its published signed distribution tree is a repository |
| cask | a vendor-binary package — payload-only by default, graft-bearing when the installer script is genuinely required |
| keg-only | `link = false` in the formula |
| cask `pkg` installer scripts | grafts — declared `[[binary.graft]]` with a behavior manifest, approved per package, sandboxed |
| `post_install` | nothing for arbitrary code — rejected; do it in a service or an extension. A vendor installer script the payload cannot replace ships as a graft |
| `deprecate!` / `disable!` | the `[deprecation]` table, edited by `aslice orchard deprecate` / `disable` |
| `uses_from_macos` | explicit packaged dependencies, subject to the documented platform-interface allowlist |
| `brew services` | `aslice service` |
| Brewfile | `aslice-machine.toml` |
| `brew bundle` | `aslice machine apply` |
| `brew cleanup` | `aslice clean` / `aslice gc` |
| `HOMEBREW_*` env vars | `ASLICE_*` |
| formulae.brew.sh | the static web index |
| test-bot | the farm and its merge gates |

<a id="the--citation-conventions"></a>

## 8. The §-citation conventions

Active cross-document citations are relative Markdown links whose labels name the document and section. Bare section numbers refer only to the current document. There are no implicit cross-document exceptions.

Cited sections have explicit semantic anchors independent of numbering and heading wording. Keep existing headings and generated destinations; link separate destinations separately rather than pointing a range at its first section. Historical citations, literal examples, captured originals, and Pandoc command references retain their original syntax. Archive wrappers still follow the active citation rule.

Long documents with at least ten second-level sections include compact section navigation. Use tables for compact mappings, paragraphs or subsections for extended explanations, and language labels on code fences. Preserve Pandoc title blocks and definition lists. The offline checker and its exception boundaries are documented in [CONTRIBUTING](../CONTRIBUTING.md#documentation-checks).

---

## History

Historical labels and ordering below are preserved as recorded, including repeated version labels. They do not override the current specification.

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v0.17 | September 2026 | Add full expansions to the acronym table while preserving existing meanings. |
| v0.16 | September 2026 | Remove retired comparison references and competitive framing; retain aslice requirements and link their owning specifications. Align affected contract summaries where applicable. |
| v0.15 | September 2026 | Clarify state DB as one of six SQLite roles with separate durable records and disposable cache. |
| v0.14 | September 2026 | Point documentation checker guidance to CONTRIBUTING after removing standalone workflow reports. |
| v0.13 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |
| v0.12 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v0.10 | September 2026 | signing host, publisher, and quarantine follow automatic publication with a dedicated networked release Pi; the root remains offline. The manual-release design is superseded (KEY-RUNBOOK §2.1). |
| v0.9 | September 2026 | **Superseded design record:** initial signing used a single owner and two offline Pis with manual release batches. |
| v0.8 | Not recorded | signing host defined as the restricted VM on the owned Mac Pro, with shared-host isolation limits; companion versions refreshed |
| v0.7 | Not recorded | the **aslice-toolchain** entry added (§4); TOOLCHAIN.md v0.1 joins the companions; companion versions refreshed — DESIGN v1.21, PACKAGE-FORMAT v0.16, AUTHORING v0.10, BUILD-INFRA v0.15, ORCHARD-POLICY v1.10, REPOSITORIES v1.7, MANUAL v0.12, SETUP v0.11 |
| v0.6 | Not recorded | the full-corpus citation re-anchor — every pointer re-verified against the current section maps after a project-wide review, and the many that had drifted with renumbering corrected; factual fixes — the store is `/opt/aslice/store`, profiles live at `<prefix>/profiles/<name>`; **shim** is redefined as the exec-only runtime multiplexer (DESIGN §8.5) and the privileged helper breaks out as **aslice-system**; **stream** is redefined as the runtime stream (DESIGN §12.9) — the stable/rolling/edge cadence sense exists nowhere in the corpus; **flavor** is corrected to the µarch flavors v1/v2/v3 (DESIGN §4.2), never a payload schema epoch; **dashboard** loses its unattested curses sense; **quarantine** and **countersignature** corrected to the real pipeline (BUILD-INFRA §7.1, REPOSITORIES §3); **index snapshot**, **pin**, **extension**, and the official/core/extended tiers rewritten to the attested meanings; the **pointer formula** entry dropped — no such mechanism exists; §8's renumbering rule corrected to match reality; companion versions refreshed — BUILD-INFRA v0.13 |
| v0.6 | September 2026 | the full-corpus citation re-anchor: every §-pointer re-verified against the current section maps after the project-wide review, and the drifted ones corrected; factual fixes — store `/opt/aslice/store`, profiles `<prefix>/profiles/<name>`; **shim** redefined as the runtime multiplexer and **aslice-system** broken out; **stream** redefined as the runtime stream; **flavor** corrected to the µarch flavors; **dashboard** loses its unattested curses sense; **quarantine**, **countersignature**, **index snapshot**, **pin**, **extension**, and the official/core/extended tiers rewritten to attested meanings; the **pointer formula** entry dropped; §8's renumbering rule corrected; companions refreshed to BUILD-INFRA v0.13 |
| v0.5 | Not recorded | grafts — new entries **graft** (§2), **behavior manifest** and **rehearsal** (§4); the **payload-only** and **vendor binary** entries gain the graft nuance; the translation table's `post_install` and cask rows are nuanced and the cask `pkg`-script row added (§7); companion versions refreshed — DESIGN v1.19, PACKAGE-FORMAT v0.15, AUTHORING v0.9, ORCHARD-POLICY v1.7, REPOSITORIES v1.6, MANUAL v0.11, SETUP v0.10. |
| v0.5 | September 2026 | grafts: new entries **graft**, **behavior manifest**, **rehearsal**; **payload-only** and **vendor binary** entries nuanced; translation table rows for `post_install` and cask nuanced, cask `pkg`-script row added; companions refreshed to DESIGN v1.19, PACKAGE-FORMAT v0.15, AUTHORING v0.9, BUILD-INFRA v0.12, ORCHARD-POLICY v1.7, REPOSITORIES v1.6, MANUAL v0.11, SETUP v0.10 |
| v0.4 | Not recorded | the declarative-setup entries follow the rename — the machine file is `aslice-machine.toml` and its verbs are the `aslice machine` group (owner decision, September 2026); the tombstone entry's negated-declaration sense is corrected — the machine file has no such declaration, apply asserts and retraction is the bounded `--prune` mode; the lock and pin entries name the real lock file (`aslice.lock`, PACKAGE-FORMAT §7); companion versions refreshed — DESIGN v1.18, PACKAGE-FORMAT v0.14, MANUAL v0.10, SETUP v0.9 |
| v0.4 | September 2026 | the declarative-setup entries follow the rename: `aslice-machine.toml` and the `aslice machine` group; the tombstone entry's negated-declaration sense is corrected to the actual `--prune` semantics (SETUP §3, DESIGN §12.13); the lock and pin entries name the real lock file, `aslice.lock` (PACKAGE-FORMAT §7); companions refreshed to DESIGN v1.18, PACKAGE-FORMAT v0.14, AUTHORING v0.8, BUILD-INFRA v0.12, ORCHARD-POLICY v1.6, REPOSITORIES v1.5, MANUAL v0.10, SETUP v0.9 |
| v0.3 | Not recorded | the **vendor binary / redistribute** entry now describes the two modes (hosted vs vendor-fetched) and points at ORCHARD-POLICY §12 where the vendor-binary policy lives; the **dashboard** entry gains its second sense — the farm's public web dashboard at aslice.sh/dashboard, part of the owner's domain layout (September 2026); companion versions refreshed — DESIGN v1.17, AUTHORING v0.8, BUILD-INFRA v0.12, ORCHARD-POLICY v1.6, REPOSITORIES v1.5, MANUAL v0.9, SETUP v0.8 |
| v0.3 | September 2026 | the vendor-binary entry describes both modes and cites ORCHARD-POLICY §12; the dashboard entry gains its web sense (aslice.sh/dashboard); companions refreshed to DESIGN v1.17, PACKAGE-FORMAT v0.13, AUTHORING v0.8, BUILD-INFRA v0.12, ORCHARD-POLICY v1.6, REPOSITORIES v1.5, MANUAL v0.9, SETUP v0.8 |
| v0.2 | Not recorded | the **tombstone** entry gains its second sense — the permanent index record of a removed formula (PACKAGE-FORMAT §3.14, ORCHARD-POLICY §8), alongside the setup.toml negated declaration — prompted by the `aslice orchard tombstone` verb (DESIGN v1.16 §12.14); companion versions refreshed — DESIGN v1.16, AUTHORING v0.7, BUILD-INFRA v0.11, ORCHARD-POLICY v1.4, REPOSITORIES v1.4, SETUP v0.7 |
| v0.2 | September 2026 | the tombstone entry gains its index sense; the translation table gains the `deprecate!`/`disable!` row; companions refreshed to DESIGN v1.16, PACKAGE-FORMAT v0.12, AUTHORING v0.7, BUILD-INFRA v0.11, ORCHARD-POLICY v1.4, REPOSITORIES v1.4, MANUAL v0.8, SETUP v0.7 |
| v0.1 | September 2026 | initial nomenclature, covering the corpus as of DESIGN v1.15, PACKAGE-FORMAT v0.12, BUILD-INFRA v0.10, ORCHARD-POLICY v1.3, REPOSITORIES v1.3, SETUP v0.6, AUTHORING v0.6, MANUAL v0.8. |
| Not recorded | September 2026 | corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending. |

</details>
