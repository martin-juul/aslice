# GENESIS — Standing Up aslice From Nothing

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

This document is the from-zero runbook. It records how the entire project — keys, toolchain, manager, orchard, repository, farm — is brought into existence, and how it is brought *back* into existence after a total loss. The motivation is one sentence: a project that can be born only once is a project that dies once. Every chicken-and-egg pair in the system has a documented path here, and when a new one is introduced it receives a row in §2 and a step in §1 **before the change lands** — the same discipline the key runbook observes.

One standing rule governs all of this, inherited from the toolchain genesis, the TUF ceremony, and the scanner genesis (BUILD-INFRA §7.5): **genesis events are documented exceptions with receipts, never silent gaps.**

*Project terms, acronyms, and the Homebrew translation table: [NOMENCLATURE.md](NOMENCLATURE.md).*

---

## 1. The from-nothing sequence

The sequence below is a runbook, not a record of completed bring-up. Use the owned 2013 Mac Pro for the initial `v1` bootstrap and `v1`/`v2` seed builds, with Monterey as the proposed baseline. Validate the host Clang, CLT, archived SDK, and toolchain source versions together first (TOOLCHAIN §10). Bring the owned 2015 MacBook Pro online for complete `v3` jobs and independent `v1`/`v2` rebuilds when required. No newer Intel macOS or additional machine purchase is assumed.

The initial inputs are Apple's compatible Command Line Tools, archived SDKs, this repository, upstream sources, one operator, and two existing Raspberry Pis. Prepare an offline root Pi and a separate dedicated networked release Pi for automatic signing, encrypted backups in another location, and separately stored recovery secrets. The Mac Pro's restricted publisher VM delivers authenticated candidates and atomically publishes verified signatures; it holds only the timestamp key among repository signing keys. Build guests receive no publication credentials (BUILD-INFRA §5, §7.2). Required tests and independent rebuilds remain gates even during bring-up, except for explicitly documented genesis exceptions.

| # | Step | Produces | Spec |
|---|---|---|---|
| 0 | **Preconditions** — owned Mac Pro with validated Monterey bootstrap tools, archived SDK, spec repo, one operator and two existing Pis; validate root and networked release signing tools, publisher isolation, and recovery materials | bootstrap and signing environments | TOOLCHAIN §10, BUILD-INFRA §5 |
| 1 | **Root setup** — generate the 1-of-1 root on the offline root Pi and distinct release keys on the dedicated networked release Pi, restore encrypted backups on a clean spare Pi, sign root metadata, publish fingerprints to three placements (repo, second transport, installer pin) | TUF root | KEY-RUNBOOK §2 |
| 2 | **Toolchain genesis** — build `aslice-toolchain` with the host Clang against the oldest archived SDK, then rebuild the toolchain *with itself*; archive both stages | stage0 + stage1 toolchain | TOOLCHAIN.md §10, DESIGN §4.3 |
| 3 | **Build aslice** with the stage1 toolchain; complete Apple signing/notarization, then minisign-sign the final binary on the release Pi | the bootstrap binary | DESIGN §10.3 |
| 4 | **Harness bring-up** — `aslice build` local mode with the full sandboxed pipeline | the build harness | BUILD-INFRA §12 |
| 5 | **Orchard seed** — build the ~30 core packages (curl, git, openssl, python, zstd, cmake, ninja, …) on real hardware; every fetched source is vendored into the tree as it is downloaded | the seed slices + the source archive's first generation | DESIGN §14, BUILD-INFRA §3 |
| 6 | **First repository** — prepare a bundle online, sign on the release Pi, verify and atomically publish with `aslice repo build / sign / publish` (KEY-RUNBOOK §2.1); preserve the step 1 setup-report hash for the transparency log's genesis entry | snapshot #1 | DESIGN §9.6 |
| 7 | **Installer published** — bootstrap binary + signed checksums on both transports (Release asset + Pages) | the curlable first step | DESIGN §10.3 |
| 8 | **Farm stand-up** — coordinator and publisher VM on Mac Pro, laptop agent on demand; measure resources and CPU/guest capabilities, validate OS matrix in batches per BUILD-INFRA §8, quarantine gates live; `clamav` per its genesis protocol, then the backlog sweep | validated capacity and coverage records; pending work for unavailable combinations | BUILD-INFRA §5–§8, §7.5 |
| 9 | **Acceptance** — complete KEY-RUNBOOK §7's signing, expiry, tamper-rejection, recovery, and test-repository migration drills; a wiped 10.11 VM installs from snapshot #1. Retain receipts before public launch | a living project | §5 |

The order is load-bearing, and it deserves to be stated as a litany: keys before metadata, toolchain before manager, manager before orchard, orchard before repository, repository before installer — all of it before the first user.

## 2. The genesis inventory

The inventory below lists every "what makes the thing that makes the thing" pair in the system, together with its genesis path and the section that specifies it. New genesis dependencies receive a row here before they merge; the table is the checklist that keeps §1 honest.

| Artifact | Produced by | Genesis path | Spec |
|---|---|---|---|
| TUF root metadata | Owner-operated root Pi, 1-of-1 | offline generation, tested encrypted backup, three placements, archived setup report for log genesis | KEY-RUNBOOK §2 |
| `aslice` bootstrap binary | the stage1 toolchain | toolchain genesis (below); signed + notarized; reproducible rebuild is a Phase 3 cross-check starting with aslice itself | DESIGN §10.3, §4.3 |
| `aslice-toolchain` | Apple's host Clang (stage0), then itself (stage1) | proposed Monterey baseline on owned Mac Pro, validated CLT + archived SDK + toolchain recipe; both stages archived; per-OS workarounds in the manifest | TOOLCHAIN.md, DESIGN §4.3, §14 |
| Archived SDKs | Apple's Xcode releases | cached on the farm, in the never-lose set (§3) | DESIGN §15 |
| TLS for aslice's own fetches | compiled-in TLS stack + CA bundle | `aslice-fetch` never touches the system store — the rotten-roots problem is designed out, not bootstrapped around | DESIGN §4.1 |
| The installer's own fetch | system curl — **on a machine whose TLS may be dead** | HTTPS first; on failure, plain HTTP for the *same hash-pinned artifacts*, with a prominent notice — the pins, signature, and TUF root are the trust, the transport never was | DESIGN §10.3 |
| `sources.toml` (official source list) | the bootstrap package | shipped data, a TUF target, core key fingerprint also compiled into the binary; replaceable wholesale by the paranoid | REPOSITORIES §2 |
| First index snapshot | Release Pi + publisher | owner-approved orchard seed and all gates; automatic candidate delivery, signing, re-verification, and atomic publication (KEY-RUNBOOK §7 acceptance drill) | KEY-RUNBOOK §2.1, BUILD-INFRA §9 |
| `ca-certificates` slice | the orchard itself | fetched by the farm with its own working TLS, packed data-only, published like any slice — no chicken, no egg | DESIGN §12.10, ORCHARD-POLICY §9 |
| `clamav` scanner | the orchard — which it scans | genesis protocol: throwaway hand-built scanner for the first build, companion gates at full strength, transparency-log go-live, backlog sweep including its own origin slice | BUILD-INFRA §7.5 |
| Source tarballs | upstreams — which disappear | **every fetched source is vendored** into the tree's `blobs/sha256/`; fetch order is upstream → formula `mirrors` → the repository's own blob area, all three under the same pinned sha256 — the archive is a fallback, never a new trust path | DESIGN §9.6, BUILD-INFRA §3 |
| Upstream PGP keys | upstreams | fingerprint pinned in the formula at authoring time (TOFU with the pin recorded); key substitution fails closed | PACKAGE-FORMAT §3 |
| VM matrix golden images | Apple's 10.11–12 installers | per-release build procedure; installer apps archived with sha256 in the farm's installer manifest — Apple pulls old installers, we don't notice | BUILD-INFRA §8 |
| Coordinator / publisher | Owned Mac Pro / restricted publisher VM | coordinator state reconstructible; rebuild publisher and restore approved public state; replace lost/suspect timestamp key through a root update | BUILD-INFRA §5, KEY-RUNBOOK §3, §7 |
| Root and release signing | Existing offline root Pi and networked release Pi | archive verified OS/signing tools and signing state; encrypted key backups and separately stored secrets; restore drill before use | KEY-RUNBOOK §2, §7 |
| GitHub (all of it) | a vendor | the repository tree is trivially mirrorable; mirrors are first-class config; hosted CI is a disposable bonus layer, never load-bearing | DESIGN §9.1, §9.2 |

## 3. The never-lose set

Everything the project cannot regenerate must exist in **at least two independent locations**, one of them off GitHub and one of them offline. The loss of any single item is an inconvenience; the loss of the set is the disaster path (§4).

1. **The git repositories** — orchards and spec — with a full non-GitHub mirror (any static host or `file://` NAS; the repo tree's own mirror mechanism covers distribution content).
2. **The recovery archive** — public fingerprints, device inventory, signed setup/rotation reports, every versioned root, approved release metadata and signing state, signer OS/tool media and hashes, and transparency-log history when available (KEY-RUNBOOK §2).
3. **Encrypted offline backups of root and release keys** — a copy at a separate physical location, with recovery secrets stored separately and recoverable after primary-site loss. Never put private keys or secrets in public mirrors. Test restoration before launch and annually (KEY-RUNBOOK §7).
4. **The stage0 and stage1 toolchain slices** — the from-nothing compiler chain, archived as slices *and* in the repository tree.
5. **The archived SDKs** used by toolchain genesis.
6. **The Apple installer apps for 10.11–12** plus the VM-image manifest (hashes, build notes per release).
7. **The vendored-source blob area** — the complete content-addressed source archive; it *is* a repository tree, so its mirrors are automatic.
8. **Every published installer + checksums file** — the historical first steps, kept so any historical snapshot remains installable (snapshot retention: all published snapshots and referenced hosted objects, with current archive authorization).

## 4. Re-standup after total loss

GitHub gone, farm flooded, domain lapsed: this is the scenario in which §1 must run from the archive alone.

1. Recover the never-lose set and separately stored secrets. Restore root and release keys onto clean Pis, keeping root recovery offline and enabling the release signer’s restricted network only after verification, compare public fingerprints with independently retained trusted records, and verify archived signatures and latest signing state. If root authority is suspect or unavailable, stop this in-band recovery path and use KEY-RUNBOOK §6.
2. Rebuild the publisher, generate a new timestamp key if the old one is unavailable or suspect, and authorize it through an offline root update before publication. Re-run §1 steps 2–7, **skipping nothing**. The stage0 toolchain comes from the archive — no Apple host rebuild is needed, which is precisely why stage0 is archived. aslice is rebuilt from source with stage1 and compared against the archived unsigned canonical reference; the served signed/notarized binary is verified separately (STATE-AND-RECOVERY §10). The orchard is *re-linked* from the archived tree rather than rebuilt, for the slices and sources are all in `blobs/sha256/`.
3. Re-publish the tree on new infrastructure — any static host, a `file://` directory, a GHCR org; the tree does not care (DESIGN §9.6). Preserve the trusted root chain and publish sequential root updates for changed keys or renewal; clients authenticate each transition under both old and new root thresholds. New mirrors are added to `sources.toml` as a TUF update.
4. Renew targets and snapshot automatically from the last approved content and refresh timestamps daily as needed; no expired metadata is silently accepted. Verify recovery with existing and fresh clients, including the restored signing state and replacement publisher, per KEY-RUNBOOK §7.
5. If the root key and usable backups are gone, or root authority is compromised, use KEY-RUNBOOK §6: explicitly rebootstrap with independently authenticated new pins. The archive makes it a bad week, not a death.

## 5. The drill

Once a year, on a clean machine, using **only** the never-lose set, rehearse §1 through step 9 using isolated test authority for new-key genesis, and separately test production-key restoration without publishing a replacement genesis: a wiped 10.11 VM installing from a re-standup repository. The drill is minuted like a key ceremony, and its verdict is binary — either the project stood up from nothing, or the gap it found receives a row in §2 and a fix before anything else ships. A genesis that has never been executed is assumed not to work; the keys live by the same rule (KEY-RUNBOOK §7).

---

*History: v0.1 (September 2026) — initial runbook, from the genesis audit that followed the §7.5 scanner-genesis discussion: collected the documented genesis paths (toolchain, root ceremony, scanner, bootstrap TLS), filled the gaps it found (installer TLS-dead fallback in DESIGN v1.9 §10.3; vendored-source archive in DESIGN v1.9 §9.6 / BUILD-INFRA v0.6 §3 / REPOSITORIES v0.8 §2; VM-image genesis and the installer-app archive in BUILD-INFRA v0.6 §8), and wrote the never-lose set and the annual re-standup drill down as obligations rather than intentions. v0.2 (September 2026) — editorial pass: prose revised for directness; no procedural changes. v0.3 (September 2026) — prose rewrite throughout: the runbook reworded in the project's technical-writing voice; no procedural changes. v0.4 (September 2026) — NOMENCLATURE.md vocabulary pointer added; no procedural changes. v0.5 (September 2026) — prose review pass: the opening's motivation sentence dropped its hedge ('can be stated in' → 'is'); gems kept deliberately ('a bad week, not a death', 'the checklist that keeps §1 honest', 'documented exceptions with receipts, never silent gaps'); no procedural changes. v0.6 (September 2026) — TOOLCHAIN.md references added to §1 step 2 and the §2 toolchain row; no procedural changes.*

*History: v0.7 (September 2026) — align bootstrap, signing VM preparation, and farm bring-up with the two owned Macs; proposed Monterey baseline and measured guest coverage replace assumed capacity. Procedures remain unvalidated until executed.*

*Superseded design record: v0.8 (September 2026) — single-operator offline Pi signing replaces the founding-custodian prerequisite; encrypted backups, signer-tool archives, manual batches, and recovery drills define launch and re-standup. Hardware and signing procedures remain unvalidated until executed.*

*History: v0.9 (September 2026) — owner merge becomes the final human release approval, with automatic signing on a dedicated networked Pi and serialized atomic publication. Automatic targets/snapshot renewal replaces manual renewal; the root remains offline. The manual-release design above is superseded. Services and acceptance drills remain implementation work (KEY-RUNBOOK §2.1, §7); schemas and client signature formats are unchanged.*

*History: September 2026 — corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending.*
