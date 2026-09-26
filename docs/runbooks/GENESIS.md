# GENESIS — Standing Up aslice From Nothing

**Document version:** v0.14 — September 2026

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](../STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](../SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

This document is the from-zero runbook. It records how the entire project — keys, toolchain, manager, orchard, repository, farm — is brought into existence, and how it is brought *back* into existence after a total loss. The motivation is one sentence: a project that can be born only once is a project that dies once. Every chicken-and-egg pair in the system has a documented path here, and when a new one is introduced it receives a row in §2 and a step in §1 **before the change lands** — the same discipline the key runbook observes.

One standing rule governs all of this, inherited from the toolchain genesis, the TUF ceremony, and the scanner genesis ([BUILD-INFRA §7.5](../BUILD-INFRA.md#the-malware-signature-gate)): **genesis events are documented exceptions with receipts, never silent gaps.**

*Project terms, acronyms, and the Homebrew translation table: [NOMENCLATURE.md](../NOMENCLATURE.md).*

---

<a id="the-from-nothing-sequence"></a>

## 1. The from-nothing sequence

The sequence below is a runbook, not a record of completed bring-up. Use the owned 2013 Mac Pro for the initial `v1` bootstrap and `v1`/`v2` seed builds, with Monterey as the proposed baseline. Validate the host Clang, CLT, archived SDK, and toolchain source versions together first ([TOOLCHAIN §10](../TOOLCHAIN.md#genesis)). Bring the owned 2015 MacBook Pro online for complete `v3` jobs and independent `v1`/`v2` rebuilds when required. No newer Intel macOS or additional machine purchase is assumed.

The initial inputs are Apple's compatible Command Line Tools, archived SDKs, this repository, upstream sources, one operator, and two existing Raspberry Pis. Prepare an offline root Pi and a separate dedicated networked release Pi for automatic signing, encrypted backups in another location, and separately stored recovery secrets. The Mac Pro's restricted publisher VM delivers authenticated candidates and atomically publishes verified signatures; it holds only the timestamp key among repository signing keys. Build guests receive no publication credentials ([BUILD-INFRA §5](../BUILD-INFRA.md#farm-topology) and [BUILD-INFRA §7.2](../BUILD-INFRA.md#agents-are-expendable)). Required tests and independent rebuilds remain gates even during bring-up, except for explicitly documented genesis exceptions.

| # | Step | Produces | Spec |
|---|---|---|---|
| 0 | **Preconditions** — owned Mac Pro with validated Monterey bootstrap tools, archived SDK, spec repo, one operator and two existing Pis; validate root and networked release signing tools, publisher isolation, and recovery materials | bootstrap and signing environments | [TOOLCHAIN §10](../TOOLCHAIN.md#genesis), [BUILD-INFRA §5](../BUILD-INFRA.md#farm-topology) |
| 1 | **Root setup** — generate the 1-of-1 root on the offline root Pi and distinct release keys on the dedicated networked release Pi, restore encrypted backups on a clean spare Pi, sign root metadata, publish fingerprints to three placements (repo, second transport, installer pin) | TUF root | [KEY-RUNBOOK §2](KEY-RUNBOOK.md#initial-root-setup) |
| 2 | **Toolchain genesis** — build `aslice-toolchain` with the host Clang against the oldest archived SDK, then rebuild the toolchain *with itself*; archive both stages | stage0 + stage1 toolchain | [TOOLCHAIN §10](../TOOLCHAIN.md#genesis), [DESIGN §4.3](../DESIGN.md#toolchain-floor--self-hosted-from-day-one) |
| 3 | **Build aslice** with the stage1 toolchain; complete Apple signing/notarization, then minisign-sign the final binary on the release Pi | the bootstrap binary | [DESIGN §10.3](../DESIGN.md#trust-bootstrapping) |
| 4 | **Harness bring-up** — `aslice build` local mode with the full sandboxed pipeline | the build harness | [BUILD-INFRA §12](../BUILD-INFRA.md#roadmap-mapping) |
| 5 | **Orchard seed** — build the ~30 core packages (curl, git, openssl, python, zstd, cmake, ninja, …) on real hardware; every fetched source is vendored into the tree as it is downloaded | the seed slices + the source archive's first generation | [DESIGN §14](../DESIGN.md#roadmap), [BUILD-INFRA §3](../BUILD-INFRA.md#the-pipeline-shared-at-both-scales) |
| 6 | **First repository** — prepare a bundle online, sign on the release Pi, verify and atomically publish with `aslice repo build / sign / publish` ([KEY-RUNBOOK §2.1](KEY-RUNBOOK.md#automatic-orchard-to-client-publication)); preserve the step 1 setup-report hash for the transparency log's genesis entry | snapshot #1 | [DESIGN §9.6](../DESIGN.md#the-repository-system) |
| 7 | **Installer published** — bootstrap binary + signed checksums on both transports (Release asset + Pages) | the curlable first step | [DESIGN §10.3](../DESIGN.md#trust-bootstrapping) |
| 8 | **Farm stand-up** — coordinator and publisher VM on Mac Pro, laptop agent on demand; measure resources and CPU/guest capabilities, validate OS matrix in batches per [BUILD-INFRA §8](../BUILD-INFRA.md#the-vm-test-matrix), quarantine gates live; `clamav` per its genesis protocol, then the backlog sweep | validated capacity and coverage records; pending work for unavailable combinations | [BUILD-INFRA §5](../BUILD-INFRA.md#farm-topology) and [BUILD-INFRA §8](../BUILD-INFRA.md#the-vm-test-matrix) and [BUILD-INFRA §7.5](../BUILD-INFRA.md#the-malware-signature-gate) |
| 9 | **Acceptance** — complete [KEY-RUNBOOK §7](KEY-RUNBOOK.md#drills-and-acceptance)'s signing, expiry, tamper-rejection, recovery, and test-repository migration drills; a wiped 10.11 VM installs from snapshot #1. Retain receipts before public launch | a living project | §5 |

Each stage supplies the next: keys before metadata, toolchain before manager, manager before orchard, orchard before repository, repository before installer — all of it before the first user.

<a id="the-genesis-inventory"></a>

## 2. The genesis inventory

The inventory below lists every "what makes the thing that makes the thing" pair in the system, together with its genesis path and the section that specifies it. New genesis dependencies receive a row here before they merge; the table is the checklist that keeps §1 honest.

| Artifact | Produced by | Genesis path | Spec |
|---|---|---|---|
| TUF root metadata | Owner-operated root Pi, 1-of-1 | offline generation, tested encrypted backup, three placements, archived setup report for log genesis | [KEY-RUNBOOK §2](KEY-RUNBOOK.md#initial-root-setup) |
| `aslice` bootstrap binary | the stage1 toolchain | toolchain genesis (below); signed + notarized; reproducible rebuild is a Phase 3 cross-check starting with aslice itself | [DESIGN §10.3](../DESIGN.md#trust-bootstrapping) and [DESIGN §4.3](../DESIGN.md#toolchain-floor--self-hosted-from-day-one) |
| `aslice-toolchain` | Apple's host Clang (stage0), then itself (stage1) | proposed Monterey baseline on owned Mac Pro, validated CLT + archived SDK + toolchain recipe; both stages archived; per-OS workarounds in the manifest | TOOLCHAIN.md, [DESIGN §4.3](../DESIGN.md#toolchain-floor--self-hosted-from-day-one) and [DESIGN §14](../DESIGN.md#roadmap) |
| Archived SDKs | Apple's Xcode releases | cached on the farm, in the never-lose set (§3) | [DESIGN §15](../DESIGN.md#risks-and-open-questions) |
| TLS for aslice's own fetches | compiled-in TLS stack + CA bundle | `aslice-fetch` never touches the system store — the rotten-roots problem is designed out, not bootstrapped around | [DESIGN §4.1](../DESIGN.md#the-os-axis-collapses--at-1011) |
| The installer's own fetch | system curl — **on a machine whose TLS may be dead** | Authenticate the installer over HTTPS. On a TLS-dead machine, obtain an independently authenticated kit on a supported machine, transfer it offline, and verify before execution. HTTP may carry only later artifacts with already-authenticated exact pins; without an authentic kit or digest, stop ([STATE-AND-RECOVERY §7](../STATE-AND-RECOVERY.md#persistent-trust-and-initial-bootstrap)) | [DESIGN §10.3](../DESIGN.md#trust-bootstrapping) |
| `sources.toml` (official source list) | the bootstrap package | shipped data, a TUF target, core key fingerprint also compiled into the binary; replaceable wholesale by the paranoid | [REPOSITORIES §2](../REPOSITORIES.md#the-shipped-source-list) |
| First index snapshot | Release Pi + publisher | owner-approved orchard seed and all gates; automatic candidate delivery, signing, re-verification, and atomic publication ([KEY-RUNBOOK §7](KEY-RUNBOOK.md#drills-and-acceptance) acceptance drill) | [KEY-RUNBOOK §2.1](KEY-RUNBOOK.md#automatic-orchard-to-client-publication), [BUILD-INFRA §9](../BUILD-INFRA.md#from-result-to-repository) |
| `ca-certificates` slice | the orchard itself | fetched by the farm with its own working TLS, packed data-only, published like any slice — no chicken, no egg | [DESIGN §12.10](../DESIGN.md#trust-store-modern-ca-certificates-on-a-frozen-platform), [ORCHARD-POLICY §9](../ORCHARD-POLICY.md#freshness-livecheck-and-autobump) |
| `clamav` scanner | the orchard — which it scans | genesis protocol: throwaway hand-built scanner for the first build, companion gates at full strength, transparency-log go-live, backlog sweep including its own origin slice | [BUILD-INFRA §7.5](../BUILD-INFRA.md#the-malware-signature-gate) |
| Source tarballs | upstreams — which disappear | **every fetched source is vendored** into the tree's `blobs/sha256/`; fetch order is upstream → formula `mirrors` → the repository's own blob area, all three under the same pinned sha256 — the archive is a fallback, never a new trust path | [DESIGN §9.6](../DESIGN.md#the-repository-system), [BUILD-INFRA §3](../BUILD-INFRA.md#the-pipeline-shared-at-both-scales) |
| Upstream PGP keys | upstreams | fingerprint pinned in the formula at authoring time (TOFU with the pin recorded); key substitution fails closed | [PACKAGE-FORMAT §3](../PACKAGE-FORMAT.md#packagetoml--full-schema) |
| VM matrix golden images | Apple's 10.11–12 installers | per-release build procedure; installer apps archived with sha256 in the farm's installer manifest — Apple pulls old installers, we don't notice | [BUILD-INFRA §8](../BUILD-INFRA.md#the-vm-test-matrix) |
| Coordinator / publisher | Owned Mac Pro / restricted publisher VM | coordinator state reconstructible; rebuild publisher and restore approved public state; replace lost/suspect timestamp key through a root update | [BUILD-INFRA §5](../BUILD-INFRA.md#farm-topology), [KEY-RUNBOOK §3](KEY-RUNBOOK.md#routine-key-rotation) and [KEY-RUNBOOK §7](KEY-RUNBOOK.md#drills-and-acceptance) |
| Root and release signing | Existing offline root Pi and networked release Pi | archive verified OS/signing tools and signing state; encrypted key backups and separately stored secrets; restore drill before use | [KEY-RUNBOOK §2](KEY-RUNBOOK.md#initial-root-setup) and [KEY-RUNBOOK §7](KEY-RUNBOOK.md#drills-and-acceptance) |
| GitHub (all of it) | a vendor | the repository tree is trivially mirrorable; mirrors are first-class config; hosted CI is a disposable bonus layer, never load-bearing | [DESIGN §9.1](../DESIGN.md#hosting-on-github--two-layers-mirror-friendly) and [DESIGN §9.2](../DESIGN.md#the-github-ci-problem) |

<a id="the-never-lose-set"></a>

## 3. The never-lose set

Include the coordinated database recovery sets from
[DATABASE](../DATABASE.md#11-backup-sets-and-restore): durable records, checkpoint
provenance, exact signed objects, reservations, quarantine and gate evidence, and
publication receipts. A SQLite snapshot on the lost disk is not an independent
backup. The ordered [database recovery procedure](../DATABASE.md#112-ordered-restore-procedure)
must establish current heads before the services in §4 resume.

Everything the project cannot regenerate must exist in **at least two independent locations**, one of them off GitHub and one of them offline. The loss of any single item is an inconvenience; the loss of the set is the disaster path (§4).

1. **The git repositories** — orchards and spec — with a full non-GitHub mirror (any static host or `file://` NAS; the repo tree's own mirror mechanism covers distribution content).
2. **The recovery archive** — public fingerprints, device inventory, signed setup/rotation reports, every versioned root, approved release metadata and signing state, signer OS/tool media and hashes, and transparency-log history when available ([KEY-RUNBOOK §2](KEY-RUNBOOK.md#initial-root-setup)).
3. **Encrypted offline backups of root and release keys** — a copy at a separate physical location, with recovery secrets stored separately and recoverable after primary-site loss. Never put private keys or secrets in public mirrors. Test restoration before launch and annually ([KEY-RUNBOOK §7](KEY-RUNBOOK.md#drills-and-acceptance)).
4. **The stage0 and stage1 toolchain slices** — the from-nothing compiler chain, archived as slices *and* in the repository tree.
5. **The archived SDKs** used by toolchain genesis.
6. **The Apple installer apps for 10.11–12** plus the VM-image manifest (hashes, build notes per release).
7. **The vendored-source blob area** — the complete content-addressed source archive; it *is* a repository tree, so its mirrors are automatic.
8. **Every published installer + checksums file** — the historical first steps, kept so any historical snapshot remains installable (snapshot retention: all published snapshots and referenced hosted objects, with current archive authorization).

<a id="re-standup-after-total-loss"></a>

## 4. Re-standup after total loss

GitHub gone, farm flooded, domain lapsed: this is the scenario in which §1 must run from the archive alone.

1. Recover the never-lose set and separately stored secrets. Restore root and release keys onto clean Pis. Compare public fingerprints with independently retained trusted records, and verify archived signatures and the latest signing state. Keep root recovery offline; enable the release signer's restricted network only after verification. If root authority is suspect or unavailable, stop this in-band recovery path and use [KEY-RUNBOOK §6](KEY-RUNBOOK.md#disaster-recovery-trust-rebootstrap).
2. Rebuild the publisher, generate a new timestamp key if the old one is unavailable or suspect, and authorize it through an offline root update before publication. Re-run §1 steps 2–7, **skipping nothing**. The stage0 toolchain comes from the archive — no Apple host rebuild is needed, which is precisely why stage0 is archived. aslice is rebuilt from source with stage1 and compared against the archived unsigned canonical reference; the served signed/notarized binary is verified separately ([STATE-AND-RECOVERY §10](../STATE-AND-RECOVERY.md#acceptance-and-implementation-order)). The orchard is *re-linked* from the archived tree rather than rebuilt, for the slices and sources are all in `blobs/sha256/`.
3. Re-publish the tree on new infrastructure — any static host, a `file://` directory, a GHCR org; the tree does not care ([DESIGN §9.6](../DESIGN.md#the-repository-system)). Preserve the trusted root chain and publish sequential root updates for changed keys or renewal; clients authenticate each transition under both old and new root thresholds. New mirrors are added to `sources.toml` as a TUF update.
4. Renew targets and snapshot automatically from the last approved content and refresh timestamps daily as needed; no expired metadata is silently accepted. Verify recovery with existing and fresh clients, including the restored signing state and replacement publisher, per [KEY-RUNBOOK §7](KEY-RUNBOOK.md#drills-and-acceptance).
5. If the root key and usable backups are gone, or root authority is compromised, use [KEY-RUNBOOK §6](KEY-RUNBOOK.md#disaster-recovery-trust-rebootstrap): explicitly rebootstrap with independently authenticated new pins. The archive makes it a bad week, not a death.

<a id="the-drill"></a>

## 5. The drill

Once a year, on a clean machine, using **only** the never-lose set, rehearse §1 through step 9 using isolated test authority for new-key genesis, and separately test production-key restoration without publishing a replacement genesis: a wiped 10.11 VM installing from a re-standup repository. The drill is minuted like a key ceremony, and its verdict is binary — either the project stood up from nothing, or the gap it found receives a row in §2 and a fix before anything else ships. A genesis that has never been executed is assumed not to work; the keys live by the same rule ([KEY-RUNBOOK §7](KEY-RUNBOOK.md#drills-and-acceptance)).

---

## History

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v0.14 | September 2026 | Extend the never-lose set with coordinated database records, evidence, and independent backup boundaries; link staged restore and continuity checks. |
| v0.11 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v0.10 | September 2026 | prose rewrite of bootstrap ordering and recovery verification; no content changes. |
| v0.9 | September 2026 | owner merge becomes the final human release approval, with automatic signing on a dedicated networked Pi and serialized atomic publication. Automatic targets/snapshot renewal replaces manual renewal; the root remains offline. The manual-release design above is superseded. Services and acceptance drills remain implementation work (KEY-RUNBOOK §2.1, §7); schemas and client signature formats are unchanged. |
| v0.8 | September 2026 | **Superseded design record:** single-operator offline Pi signing replaces the founding-custodian prerequisite; encrypted backups, signer-tool archives, manual batches, and recovery drills define launch and re-standup. Hardware and signing procedures remain unvalidated until executed. |
| v0.7 | September 2026 | align bootstrap, signing VM preparation, and farm bring-up with the two owned Macs; proposed Monterey baseline and measured guest coverage replace assumed capacity. Procedures remain unvalidated until executed. |
| v0.6 | September 2026 | TOOLCHAIN.md references added to §1 step 2 and the §2 toolchain row; no procedural changes. |
| v0.5 | September 2026 | prose review pass: the opening's motivation sentence dropped its hedge ('can be stated in' → 'is'); gems kept deliberately ('a bad week, not a death', 'the checklist that keeps §1 honest', 'documented exceptions with receipts, never silent gaps'); no procedural changes. |
| v0.4 | September 2026 | NOMENCLATURE.md vocabulary pointer added; no procedural changes. |
| v0.3 | September 2026 | prose rewrite throughout: the runbook reworded in the project's technical-writing voice; no procedural changes. |
| v0.2 | September 2026 | editorial pass: prose revised for directness; no procedural changes. |
| v0.1 | September 2026 | initial runbook, from the genesis audit that followed the §7.5 scanner-genesis discussion: collected the documented genesis paths (toolchain, root ceremony, scanner, bootstrap TLS), filled the gaps it found (installer TLS-dead fallback in DESIGN v1.9 §10.3; vendored-source archive in DESIGN v1.9 §9.6 / BUILD-INFRA v0.6 §3 / REPOSITORIES v0.8 §2; VM-image genesis and the installer-app archive in BUILD-INFRA v0.6 §8), and wrote the never-lose set and the annual re-standup drill down as obligations rather than intentions. |
| Not recorded | September 2026 | corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending. |
| v0.12 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |
| v0.13 | September 2026 | Relocate to `docs/runbooks/` and rebase relative links; no procedural changes. |

</details>
