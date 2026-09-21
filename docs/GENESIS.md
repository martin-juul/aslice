# GENESIS — Standing Up aslice From Nothing

This document is the from-zero runbook. It records how the entire project — keys, toolchain, manager, orchard, repository, farm — is brought into existence, and how it is brought *back* into existence after a total loss. The motivation can be stated in one sentence: a project that can be born only once is a project that dies once. Every chicken-and-egg pair in the system has a documented path here, and when a new one is introduced it receives a row in §2 and a step in §1 **before the change lands** — the same discipline the key runbook observes.

One standing rule governs all of this, inherited from the toolchain genesis, the TUF ceremony, and the scanner genesis (BUILD-INFRA §7.5): **genesis events are documented exceptions with receipts, never silent gaps.**

---

## 1. The from-nothing sequence

The sequence below is executed in the order given. Steps 1–5 need one Intel Mac running the newest Intel macOS available, Apple's Command Line Tools, this repository, and the root custodians — and nothing else: no aslice, no orchard, no farm, no network services of ours.

| # | Step | Produces | Spec |
|---|---|---|---|
| 0 | **Preconditions** — an Intel Mac (the stage0 host), Apple CLT, the spec repo, ≥4 of 5 root custodians | a clean room | — |
| 1 | **Root key ceremony** — generate the 3-of-5 threshold root on YubiKeys, sign root metadata, publish fingerprints to three placements (repo, second transport, installer pin) | TUF root | KEY-RUNBOOK §2 |
| 2 | **Toolchain genesis** — build `aslice-toolchain` with the host Clang against the oldest archived SDK, then rebuild the toolchain *with itself*; archive both stages | stage0 + stage1 toolchain | DESIGN §4.3 |
| 3 | **Build aslice** with the stage1 toolchain; minisign-sign the binary, Apple-notarize it | the bootstrap binary | DESIGN §10.3 |
| 4 | **Harness bring-up** — `aslice build` local mode with the full sandboxed pipeline | the build harness | BUILD-INFRA §12 |
| 5 | **Orchard seed** — build the ~30 core packages (curl, git, openssl, python, zstd, cmake, ninja, …) on real hardware; every fetched source is vendored into the tree as it is downloaded | the seed slices + the source archive's first generation | DESIGN §14, BUILD-INFRA §3 |
| 6 | **First repository** — `aslice repo build / sign / publish` on the signing host; the transparency log's genesis entry references the ceremony hash from step 1 | snapshot #1 | DESIGN §9.6 |
| 7 | **Installer published** — bootstrap binary + signed checksums on both transports (Release asset + Pages) | the curlable first step | DESIGN §10.3 |
| 8 | **Farm stand-up** — agents enroll, VM matrix images built per the §8 procedure, quarantine gates live; `clamav` per its genesis protocol, then the backlog sweep | the system of record | BUILD-INFRA §5–§8, §7.5 |
| 9 | **Acceptance** — a wiped 10.11 VM runs the installer and installs from snapshot #1. The whole chain, end to end, or it didn't happen | a living project | §5 |

The order is load-bearing, and it deserves to be stated as a litany: keys before metadata, toolchain before manager, manager before orchard, orchard before repository, repository before installer — all of it before the first user.

## 2. The genesis inventory

The inventory below lists every "what makes the thing that makes the thing" pair in the system, together with its genesis path and the section that specifies it. New genesis dependencies receive a row here before they merge; the table is the checklist that keeps §1 honest.

| Artifact | Produced by | Genesis path | Spec |
|---|---|---|---|
| TUF root metadata | 3-of-5 custodian ceremony | air-gapped ceremony, three placements, transparency-log genesis | KEY-RUNBOOK §2 |
| `aslice` bootstrap binary | the stage1 toolchain | toolchain genesis (below); signed + notarized; reproducible rebuild is a Phase 3 cross-check starting with aslice itself | DESIGN §10.3, §4.3 |
| `aslice-toolchain` | Apple's host Clang (stage0), then itself (stage1) | newest Intel macOS + CLT + archived SDK; both stages archived; per-OS workarounds in the manifest | DESIGN §4.3, §14 |
| Archived SDKs | Apple's Xcode releases | cached on the farm, in the never-lose set (§3) | DESIGN §15 |
| TLS for aslice's own fetches | compiled-in TLS stack + CA bundle | `aslice-fetch` never touches the system store — the rotten-roots problem is designed out, not bootstrapped around | DESIGN §4.1 |
| The installer's own fetch | system curl — **on a machine whose TLS may be dead** | HTTPS first; on failure, plain HTTP for the *same hash-pinned artifacts*, with a prominent notice — the pins, signature, and TUF root are the trust, the transport never was | DESIGN §10.3 |
| `sources.toml` (official source list) | the bootstrap package | shipped data, a TUF target, core key fingerprint also compiled into the binary; replaceable wholesale by the paranoid | REPOSITORIES §2 |
| First index snapshot | signing host | `aslice repo build/sign/publish` after the orchard seed; coordinator state is reconstructible from git + result store | DESIGN §9.6, BUILD-INFRA §5 |
| `ca-certificates` slice | the orchard itself | fetched by the farm with its own working TLS, packed data-only, published like any slice — no chicken, no egg | DESIGN §12.10, ORCHARD-POLICY §9 |
| `clamav` scanner | the orchard — which it scans | genesis protocol: throwaway hand-built scanner for the first build, companion gates at full strength, transparency-log go-live, backlog sweep including its own origin slice | BUILD-INFRA §7.5 |
| Source tarballs | upstreams — which disappear | **every fetched source is vendored** into the tree's `blobs/sha256/`; fetch order is upstream → formula `mirrors` → the repository's own blob area, all three under the same pinned sha256 — the archive is a fallback, never a new trust path | DESIGN §9.6, BUILD-INFRA §3 |
| Upstream PGP keys | upstreams | fingerprint pinned in the formula at authoring time (TOFU with the pin recorded); key substitution fails closed | PACKAGE-FORMAT §3 |
| VM matrix golden images | Apple's 10.11–12 installers | per-release build procedure; installer apps archived with sha256 in the farm's installer manifest — Apple pulls old installers, we don't notice | BUILD-INFRA §8 |
| Coordinator / signing host | commodity hardware | coordinator: boring by design, state reconstructible; signing host: rebuilt from the ceremony archive, restore drill before it may sign | BUILD-INFRA §5, KEY-RUNBOOK §7 |
| GitHub (all of it) | a vendor | the repository tree is trivially mirrorable; mirrors are first-class config; hosted CI is a disposable bonus layer, never load-bearing | DESIGN §9.1, §9.2 |

## 3. The never-lose set

Everything the project cannot regenerate must exist in **at least two independent locations**, one of them off GitHub and one of them offline. The loss of any single item is an inconvenience; the loss of the set is the disaster path (§4).

1. **The git repositories** — orchards and spec — with a full non-GitHub mirror (any static host or `file://` NAS; the repo tree's own mirror mechanism covers distribution content).
2. **The ceremony archive** — root fingerprints, YubiKey serials, signed ceremony reports, transparency-log history (KEY-RUNBOOK §2).
3. **The root YubiKeys themselves** — 5 custodians, geographically distributed (KEY-RUNBOOK §1).
4. **The stage0 and stage1 toolchain slices** — the from-nothing compiler chain, archived as slices *and* in the repository tree.
5. **The archived SDKs** used by toolchain genesis.
6. **The Apple installer apps for 10.11–12** plus the VM-image manifest (hashes, build notes per release).
7. **The vendored-source blob area** — the complete content-addressed source archive; it *is* a repository tree, so its mirrors are automatic.
8. **Every published installer + checksums file** — the historical first steps, kept so any historical snapshot remains installable (snapshot retention: one year whole, monthly forever).

## 4. Re-standup after total loss

GitHub gone, farm flooded, domain lapsed: this is the scenario in which §1 must run from the archive alone.

1. Recover the never-lose set from its second location. Verify the ceremony archive against a root YubiKey before trusting anything else it contains: the root is the anchor, and everything else is verified *from* it.
2. Re-run §1 steps 2–7, **skipping nothing**. The stage0 toolchain comes from the archive — no Apple host rebuild is needed, which is precisely why stage0 is archived. aslice is rebuilt from source with stage1 and digest-compared against the archived binary. The orchard is *re-linked* from the archived tree rather than rebuilt, for the slices and sources are all in `blobs/sha256/`.
3. Re-publish the tree on new infrastructure — any static host, a `file://` directory, a GHCR org; the tree does not care (DESIGN §9.6). The root metadata is unchanged, and clients chain-trust it. New mirrors are added to `sources.toml` as a TUF update.
4. The only thing the archive cannot restore is the *online* key material on the signing host; it is restored from the ceremony archive per KEY-RUNBOOK §7's drill — never improvised.
5. If the root itself is gone — fewer than 3 shares — the path is KEY-RUNBOOK §6: re-bootstrap with a new root, executed in the open. The archive makes it a bad week, not a death.

## 5. The drill

Once a year, on a clean machine, using **only** the never-lose set, run §1 end-to-end through step 9: a wiped 10.11 VM installing from a re-standup repository. The drill is minuted like a key ceremony, and its verdict is binary — either the project stood up from nothing, or the gap it found receives a row in §2 and a fix before anything else ships. A genesis that has never been executed is assumed not to work; the keys live by the same rule (KEY-RUNBOOK §7).

---

*History: v0.1 (September 2026) — initial runbook, from the genesis audit that followed the §7.5 scanner-genesis discussion: collected the documented genesis paths (toolchain, root ceremony, scanner, bootstrap TLS), filled the gaps it found (installer TLS-dead fallback in DESIGN v1.9 §10.3; vendored-source archive in DESIGN v1.9 §9.6 / BUILD-INFRA v0.6 §3 / REPOSITORIES v0.8 §2; VM-image genesis and the installer-app archive in BUILD-INFRA v0.6 §8), and wrote the never-lose set and the annual re-standup drill down as obligations rather than intentions. v0.2 (September 2026) — editorial pass: prose revised for directness; no procedural changes. v0.3 (September 2026) — prose rewrite throughout: the runbook reworded in the project's technical-writing voice; no procedural changes.*
