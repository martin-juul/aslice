# aslice Build Infrastructure — One Harness, Two Scales

- **Status:** Design draft, v0.6 — September 2026 (v0.2: companion references refreshed — DESIGN v1.7, PACKAGE-FORMAT v0.6, HOMEBREW-REVIEW v0.9; all internal cross-references re-verified against current section numbering, no content change. v0.3: companion references refreshed — DESIGN v1.8, PACKAGE-FORMAT v0.6, HOMEBREW-REVIEW v0.10; no content change. v0.4: the malware-signature gate — every staged slice is scanned against current definitions before signing-host promotion (new §7.5, §7.1 gate 5, §11 failure row, §12 Phase 1); the scanner is the orchard's own `clamav` core package (ORCHARD-POLICY v0.7 §2); client-side scanning stays the user's decision. v0.5: the gate's genesis protocol — the first `clamav` slice is scanned by a throwaway hand-built scanner with a `bootstrap` receipt, the other four quarantine gates carry full weight, go-live is a transparency-log event, and the packaged scanner sweeps the pre-gate backlog including its own origin slice (§7.5). v0.6: the genesis audit — every fetched source is vendored into the repository tree (§3, §9), VM golden-image genesis and the installer-app archive are specified (§8), and the from-nothing sequence lands as GENESIS.md (§12); companions DESIGN v1.9 / REVIEW v0.11)
- **Companion to:** [DESIGN.md](DESIGN.md) v1.9 (§4.3 toolchain, §5.1 process layout, §9 distribution, §10 security), [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) v0.6 (build phases §6), [HOMEBREW-REVIEW.md](HOMEBREW-REVIEW.md) v0.11 (§4.7 merge gates, §6 risks)
- **Scope:** the build harness (`aslice build`), farm orchestration (`aslice farm`), scheduling, worker trust, the VM test matrix, and the pipeline from build result to published repository.

---

## 1. The kicker, stated as a design axiom

**The farm is not a special system.** Every build the project ever runs executes through the exact same machinery a user gets when they type `aslice build`. There is no CI-only code path, no farm-secret tooling, no build that cannot be reproduced by a contributor on a 2012 Mac mini in a closet. This axiom buys:

- **Debuggability.** A failing farm build is reproducible locally with one command. "Works on my machine" is eliminated by construction, because it *is* the same machine, logically.
- **Resilience.** A farm outage degrades binary *freshness*, never user capability — users can always build from source, because the farm's pipeline is their pipeline. (This is the structural difference from Homebrew, where the bottle pipeline is infrastructure users never touch; when it stops, bottles stop.)
- **Trust.** Reproducibility cross-checks (§7) are just volunteers running the harness — no special access, no special build of the tooling.

The axiom's cost: the harness must be good enough for both an unattended fleet and a human at a keyboard. That shapes everything below.

## 2. The harness: one binary, four modes, one sandboxed core

```
aslice build <what>           # user mode: build one package (or a formula dir) locally
aslice farm plan              # coordinator: compute the build plan from an orchard
aslice farm coordinator       # coordinator: schedule → gate → collect
aslice farm agent [--once]    # worker mode: pull signed jobs, build, upload results
aslice farm agent --vm-guest  # guest mode: run tests inside a matrix VM (§8)
```

All four modes *orchestrate*; none of them executes package code directly. Execution is always delegated to the privilege-separated helpers of DESIGN §5.1 — `aslice-fetch`, `aslice-extract`, and above all **`aslice-build`**, the sandboxed per-phase executor that runs Starlark under Seatbelt. The harness spawns it phase by phase with the policy profile for that phase. Whether the caller is a user's shell or a farm agent, the bytes that run are identical.

### 2.1 Jobs are closed worlds

A **job** is the complete, self-contained description of one build:

```json
{
  "job_version": 1,
  "orchard":   { "repo": "aslice/orchard-core", "commit": "c3f7…" },
  "package":   { "name": "ffmpeg", "version": "7.1.0", "revision": 0,
                 "variants": { "x265": true }, "flavor": "v3", "min_os": "10.11" },
  "toolchain": { "build_id": "7c19…", "digest": "sha256:…", "url": "…" },
  "deps":      [ { "name": "x264", "build_id": "77aa10b2", "digest": "sha256:…", "url": "…" } ],
  "sources":   [ { "url": "…", "sha256": "40973d…" } ],
  "sandbox":   { "test_network": false },
  "resources": { "jobs": 8, "ram_gb": 8, "disk_gb": 20, "timeout_min": 90 },
  "repro_of":  null
}
```

No job references ambient machine state: the toolchain is a pinned slice, dependencies are pinned slices, sources are pinned hashes, the formula is a pinned git commit. A job manifest's hash **is** the expected result identity — two honest builders executing the same job must produce the same slice digest (modulo the formula's recorded reproducibility class, §7.3). This property is what makes farm verification and `aslice build --reproduce` the same code.

### 2.2 Results are the job's mirror

```json
{
  "job_sha256": "…",
  "agent":      { "id": "mini-2018-2", "key_fp": "…", "os": "12.7", "flavor": "v3" },
  "slice":      { "digest": "sha256:…", "size": 18112331 },
  "abi_report": "abi/ffmpeg-7.1.0-v3.json",
  "log":        "logs/ffmpeg-7.1.0-v3.jsonl.gz",
  "timings":    { "fetch_s": 4.1, "build_s": 412.7, "test_s": 38.0 },
  "provenance": { "builder": "aslice 0.9.1", "started": "…", "finished": "…" }
}
```

Timings feed the farm dashboard and the "build pain" prebuild signal (DESIGN §9.4) — measured on the farm, never on users' machines.

## 3. The pipeline, shared at both scales

PACKAGE-FORMAT §6.1 defines the phases; here is the infrastructure detail:

| Phase | Environment | Notes |
|---|---|---|
| fetch | network: declared hosts only; writes: job cache | resumable, hash-verified, mirror-aware; **the farm vendors every artifact it fetches** into the tree's `blobs/sha256/` (§9) — the archive of last resort for dead upstreams |
| verify | no network | source hashes + PGP where declared |
| unpack / patch | no network; build dir only | the fuzzed extractor helper (xar/cpio/tar) |
| configure / build | no network; toolchain + dep slices mounted **read-only into an isolated buildroot** | builds never see the user's live store or profile |
| install | DESTDIR staging only | |
| abi-scan | aslice's own code, always, unskippable | per-arch entries for universal vendor payloads |
| test | no network by default | `tests.star`; per-formula OS/flavor skip policy |
| pack | writes `.slice` + provenance + ABI report | |
| sign | **farm only, on the signing host** (§7) | local builds stay unsigned, `origin = local-build` |

Determinism is the harness's job, not the formula's: `LC_ALL=C`, `TZ=UTC`, pinned `SOURCE_DATE_EPOCH`, prefix-mapping, scrubbed environment (DESIGN §9.5). The toolchain slice mounts at its canonical store path so `-ffile-prefix-map` output matches farm and user builds byte-for-byte.

For `type = "binary"` formulae the same command runs the compressed pipeline (fetch → verify hash+signer → extract payload → abi-scan → pack). This is how the farm produces `redistribute = true` slices — and how a user can dry-run a vendor repack locally to audit exactly what a vendor slice would contain before installing it.

## 4. User mode: `aslice build`

```
aslice build ffmpeg                                # resolve like install, but always compile
aslice build ./orchards/core/ffmpeg                # build a formula directory (maintainer loop)
aslice build ffmpeg --variant +x265 --cflags="-O3 -march=native"
aslice build --reproduce ffmpeg 7.1.0 v3 2f4a9c1e  # rebuild a published slice, compare digests
aslice build ffmpeg --offline                      # air-gapped; pre-fetched sources only
aslice build ffmpeg --keep --shell                 # keep build dir; sandboxed shell at the failed phase
```

- **Results are first-class installs.** The output enters the store with `origin = local-build`, recorded flags, and the identity rules of DESIGN §7.2 — it interops with the prebuilt world through the ABI contract like any slice. `aslice install --build-from-source` and `--variant`/`--cflags` builds are literally this command with an install step after it.
- **Resource manners.** Default `jobs = cores − 1` (override `ASLICE_BUILD_JOBS`), RAM/disk watermarks refuse builds that would thrash the machine, tmpfs build dir when RAM allows, ccache keyed by (toolchain, flags, flavor) under `cache/ccache`. A laptop stays usable while it compiles.
- **Failure UX.** Structured per-phase logs (`cache/build/<id>/log.jsonl` plus a rendered tail), `--resume-from <phase>`, and `--shell` — dropping into the exact sandboxed environment at the failed phase. Maintainer iteration never requires re-fetching or re-unpacking.
- **Cleanup.** Successful build dirs are deleted; failures are kept 7 days (configurable) and swept by `aslice clean`.
- **No daemons.** Builds are on-demand processes. `farm agent` runs only when the user starts it; nothing auto-launches, nothing phones home, nothing idles in the background.

## 5. Farm topology

The hardware of DESIGN §9.3, given roles:

| Machine | Role |
|---|---|
| 2–4 × Mac mini 2018 (Coffee Lake) | `v3` builders; VM hosts for the 10.11–12 guest matrix; one doubles as coordinator |
| Mac Pro 2013 / Mac mini 2012 (Ivy Bridge) | `v2` builder + tester |
| Core 2 Duo (when obtainable) | `v1` smoke tester — tests only, never builds |
| Signing host (mini, network-restricted) | verification gate + slice signing; YubiKey-custodied keys (DESIGN §10.2) |
| Any user's Mac | optional evidence builder (§7.4) — reproduction jobs only |

The **coordinator is deliberately boring**: one process, a SQLite queue, an orchard checkout. It can live on a mini or a $5 VPS; its entire state is reconstructible from orchard git history plus the result store. The GitHub Actions self-hosted runner integration is a thin adapter — a runner job that literally executes `aslice farm agent --once` — so the system of record never depends on Actions semantics (DESIGN §9.2: hosted CI is a bonus layer, never load-bearing).

## 6. Scheduling: plan, lanes, leases

### 6.1 The build plan

`aslice farm plan` diffs the orchard (git), expands affected formulae into jobs across their declared matrix — flavors where `min_os` allows, smoke tests per OS release in `[min_os, 12]` — and topologically orders the DAG.

Provider changes trigger the **ABI gate** (REVIEW §4.7): scan-diff the old and new provider slice; on regression, dependent revision-bump jobs are generated *into the same plan*, so the index snapshot that eventually lands contains the provider and its rebuilt dependents **together**. The broken-window failure Homebrew users know — "everything's broken until the rebuilds land" — is structurally absent: the snapshot is atomic.

### 6.2 Lanes

Three queues, drained in order but preemptible upward:

1. **Freshness** — autobump PR gates (the livecheck machinery from REVIEW §4.2 builds here).
2. **Trunk** — merged changes heading for the next published snapshot.
3. **Backfill** — the long tail: extended-orchard packages, missing flavors, old versions needing slices. Prioritized by the §9.4 value signals (dependency centrality, farm-measured build pain, irreplaceability, community requests) — never by download counts.

### 6.3 Leases, not locks

Agents pull a job with a lease and heartbeat; an expired lease requeues the job untouched. Results are keyed by job-manifest hash, so a duplicated execution is discarded, not catastrophic. Everything is idempotent: the farm can be rebooted by pulling the plug and turning it back on.

### 6.4 PR gates

Orchard PRs run the plan subset for the touched formula: lint → build every declared flavor → smoke-test every OS on the VM matrix → ABI gate if a provider. Merge is blocked until green; signing and snapshot publication are post-merge, on the signing host (§9).

## 7. Trust: agents produce evidence, the signing host produces artifacts

### 7.1 Quarantine

Agent results land in an **untrusted staging area**. Nothing from staging is ever served. Promotion to the repository happens only on the signing host, after:

1. lint/policy re-check of the formula at the job's orchard commit;
2. the slice digest matches the job's expected identity where the reproducibility class demands it (§7.3);
3. the smoke test passed on the claimed OS × flavor;
4. the ABI report is sane (no unexplained fingerprint regressions);
5. the slice passes the malware-signature gate (§7.5) — scanned against current definitions, verdict recorded in its provenance.

Only then: sign, and feed `aslice repo build` (DESIGN §9.6).

### 7.2 Agents are expendable

An agent holds: the coordinator's public key (job manifests are signed; unsigned or unknown jobs are refused), a per-agent Ed25519 identity for *result* signing (evidence, not authority), a dedicated `_aslicefarm` user, Seatbelt phase profiles — and **no credentials** for the repository, the signing host, or anything else. A fully rooted agent can delay the queue and produce garbage that dies in quarantine. It cannot ship a bad slice.

For builds of third-party-orchard PRs — hostile-adjacent input by definition — agents additionally run the whole job inside a fresh VM snapshot that is reverted afterwards (§8). Seatbelt alone contains *builds*; PR review should not double as an exploit-bounty program for the farm.

### 7.3 Reproducibility classes

Not every package is bit-reproducible yet, and honesty beats aspiration. Each formula's provenance carries a class:

| Class | Meaning | Signing-host enforcement |
|---|---|---|
| `bitwise` | slice digest must match across independent builds | hard gate: mismatch = quarantine + investigation event |
| `normalized` | matches after stripping known-nondeterministic sections (e.g. Mach-O Code Directory hashes, embedded UUIDs) | gate on the normalized comparison |
| `unreproducible` | known divergence, source recorded in the formula | tracked as debt; class upgrades happen only by orchard PR with evidence |

### 7.4 Community builders — the user's machine, enlisted safely

Because the harness runs anywhere, anyone can enroll a spare Mac:

```
aslice farm enroll --project https://farm.aslice.org   # issues agent key, pins coordinator key
aslice farm agent --reproduce-only                     # verification jobs only, forever
```

Community agents receive `repro_of` jobs: rebuild a published job manifest and compare digests. Their results are **pure evidence** — agreement raises a slice's reproducibility confidence (feeding the `reproducible: true` badge of DESIGN §9.5); disagreement files an automatic investigation event. Community agents are never asked for, and never given, the ability to produce a served artifact.

The project gets a distributed rebuild network on exactly the machines the software targets; the volunteer gets dashboard credit and a warm Mac mini. This is "the farm must be runnable on a user's machine" answered at the trust level: **identical code, zero authority.**

### 7.5 The malware-signature gate

Every staged slice is scanned against current ClamAV definitions before the signing host may promote it. The gate exists for the two moments the trust model is thinnest: the autobump bot's **first fetch** of a brand-new upstream tarball (the hash is computed from that very fetch — nothing has pinned it yet), and the **vendor-payload lane**, where bundled adware and PUPs are the documented pathology of the `.pkg`/`.dmg` ecosystem (ORCHARD-POLICY §12). A scan verdict — scanner version, definitions date, result — is recorded in the slice's provenance, so every published artifact carries its receipt and scan coverage is a dashboard number.

- **The scanner is the orchard's own `clamav` core package** — the farm dogfoods the orchard (ORCHARD-POLICY §2: farm tooling is core by definition), running the same slice any user can install. Definitions refresh daily via freshclam on the farm network; a scanner whose definitions are stale beyond 48 hours pauses promotion rather than scanning with dead signatures — freshness of the gate is itself gated.
- **A detection quarantines the slice permanently**, files an investigation event, and pages the named maintainer. Nothing is auto-deleted and nothing is auto-"cleaned" — the verdict is a human decision, and for vendor payloads the only options are rejection or a maintainer-documented exclusion in the formula (a modified payload would break byte-integrity against the pinned signer).
- **Genesis is a documented exception, not a silent gap** — the same pattern as the toolchain genesis and the TUF root ceremony, applied to the chicken-and-egg of a scanner that is itself a package:
  1. The first `clamav` build is scanned by a **throwaway scanner**: a maintainer hand-builds ClamAV from the same hash-pinned, upstream-GPG-verified source inside a quarantined VM, scans the staged slice, and the verdict is recorded with `scanner = "bootstrap-handbuilt"` in its provenance. The orchard package never scans itself into existence.
  2. The other four §7.1 gates carry full weight for that first build — pinned and signature-verified sources, the sandboxed pipeline, two-maintainer infrastructure-package review (ORCHARD-POLICY §2), and a hard `bitwise` reproducibility requirement with an independent evidence rebuild (§7.4) before promotion. The scanner gate is one layer of five; genesis is when the other four stand up straight.
  3. The gate's go-live — the first snapshot in which the packaged scanner runs the quarantine worker — is recorded in the transparency log. Slices published before it are marked `pre-gate` on the dashboard: annotated, never rewritten.
  4. **Backlog sweep.** The packaged scanner then re-scans every pre-gate slice with current definitions, *including its own origin slice*; scan coverage climbs publicly to 100%. The origin slice's `bootstrap` receipt stays as-is — history with a receipt beats history revised.
- **Honest scope.** Signature scanning catches *known* malware. It does nothing against a novel supply-chain backdoor — that threat belongs to provenance, reproducibility classes, and review, and this gate changes nothing there. What it replaces on this platform is XProtect, which Apple no longer updates for 10.11–12: the farm maintains the definitions the built-in layer stopped receiving.
- **Client-side: nothing.** No scan-on-install machinery, no daemon, no definitions slice pushed at users. Anyone who wants on-demand scanning installs the same `clamav` package the farm runs and drives it themselves — the charter's no-telemetry, no-background-anything rules apply to security features exactly as to everything else.

## 8. The VM test matrix

Builds happen on the newest build host against the oldest SDK (DESIGN §4.3); **tests run on the real OS.** The minis host the seven-guest matrix (10.11 → 12) under VMware Fusion or Parallels:

- Golden image per release, snapshotted clean. A test run is: revert → boot → mount a read-only shared folder containing the staged slice → `aslice farm agent --vm-guest` executes `tests.star` → structured results out → revert. No guest has network beyond the coordinator wire; no state survives between runs.
- **Image genesis is documented and archived.** Per release: the Apple installer app → `createinstallmedia` (or the virtualization app's new-VM flow) → minimal install → golden snapshot. The installer apps are archived with their sha256 in the farm's installer manifest — Apple can and does pull old installers, and the matrix must be re-creatable from nothing but the archive. Installers, images, and manifest are in the never-lose set (GENESIS.md §3).
- The platform being frozen means images are built once and cached forever — the matrix's marginal cost is electricity, not maintenance. (This is precisely the property GitHub's runner retirement destroys for Homebrew and preserves for aslice.)
- `v1` tests additionally run on real Core 2 Duo hardware when one is attached — VMs emulate the OS, not silicon errata.

## 9. From result to repository

```
agent → staging (untrusted)
      → signing host: verify → sign
      → aslice repo build / sign / publish     (DESIGN §9.6)
      → transparency-log append                (snapshot hash, public)
      → dashboard update
```

The index snapshot is published atomically with its dependent rebuilds (§6.1). Retention per REVIEW §6: snapshots ≤ 1 year kept whole, monthly forever — which is what makes historical installs (REVIEW §4.14) true.

The same publish deposits **every source artifact the build fetched** into the tree's `blobs/sha256/` area — the vendored-source archive (DESIGN §9.6). Upstreams delete, reshuffle, and re-roll tarballs constantly; an orchard that vendors its sources never notices, and a from-nothing re-standup never starves (GENESIS.md §2).

## 10. Farm-side metrics (the only kind there are)

No user telemetry exists anywhere in this system (DESIGN §2.2 N7). What the farm publishes is about the **farm**: median days behind upstream (freshness health), build pain per package (feeds §9.4), reproducibility coverage percentage, queue depth per lane, per-OS × flavor test pass rates, fleet status. All computed from the farm's own operation and published on the static dashboard — the transparency surface of DESIGN §13.4.

## 11. Failure modes, planned

| Failure | Behavior |
|---|---|
| Agent dies mid-job | Lease expires, job requeues, partial staging ignored |
| Coordinator dies | Queue is SQLite + git; restore on any machine, agents reconnect |
| Signing host down | Repository freezes at the last good snapshot — clients unaffected, freshness pauses |
| Poisoned/faulty result | Quarantined forever; digest mismatch or class violation files an investigation event |
| Scanner detection (§7.5) | Slice quarantined permanently pending maintainer review; investigation event filed; promotion pauses if definitions are stale |
| VM host down | Its guests' tests queue; builds continue (tests are the gate, not the build) |
| Disk pressure | Watermarks pause agents; scheduled farm-side `clean` sweeps staging and caches |
| GitHub Actions changes | The adapter is disposable; the standalone coordinator is the system of record |

## 12. Roadmap mapping

- **Phase 0:** harness skeleton — `aslice build` local mode with the full sandboxed pipeline; toolchain-as-slice; job/result schemas; `farm plan`. The from-nothing sequence (GENESIS.md §1) is executed end-to-end and written down as it runs — the project must be able to stand up from nothing, repeatedly, before it has users.
- **Phase 1:** coordinator + agents + leases; Actions adapter; VM matrix bring-up; PR gates for the core orchard; staging → quarantine → signing-host pipeline including the §7.5 malware-signature gate, bootstrapped per its genesis protocol, with the `clamav` core package the gate runs on.
- **Phase 2:** ABI-gate dependent-rebuild cascades; vendor-repackaging lane; backfill lane with §9.4 priorities; public dashboard.
- **Phase 3:** two-builder cross-checks for core; community evidence builders (`enroll`, `--reproduce-only`); transparency log; reproducibility class upgrades as a standing program.
