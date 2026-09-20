# aslice — System Design

> **Status:** v1.8 design draft — for review before implementation begins.
> **Scope:** macOS 10.11 (El Capitan) through 12 (Monterey), x86_64 only.
> **Companions:** PACKAGE-FORMAT.md (slice format spec), REPOSITORIES.md (multi-repo, mirrors, and vendor .pkg/.dmg support), HOMEBREW-REVIEW.md (the Homebrew audit this design answers), ORCHARD-POLICY.md (governance), BUILD-INFRA.md (build-farm architecture).

---

## 1. Mission

aslice is a binary-first package manager for Intel Macs that Apple has left behind. It delivers modern, security-patched open-source software to macOS 10.11–12 as content-addressed, cryptographically signed packages, with correct dependency resolution, atomic upgrades, instant rollback, and multi-repository support — and it does so without requiring the user to trust anything except an explicit, pinned set of keys.

The project exists because of a simple asymmetry: the software world moved on, but the hardware didn't break. A 2015 iMac is a fine machine. What it can't run is a modern TLS stack, a current ffmpeg, a supported Python. aslice's job is to close that gap — permanently, since the platform it targets is frozen and will never change again.

**What "modern software on old macOS" concretely means:** current OpenSSL/LibreSSL with TLS 1.3 on systems whose Secure Transport is frozen at 2015; ffmpeg 7.x with x264/x265/SVT-AV1; Python 3.13, Node LTS, Rust, Go (where the runtime supports the deployment target — otherwise the newest version that does, honestly labeled); curl with HTTP/2 and HTTP/3; git current; and the library stack (icu4c, libxml2, sqlite, harfbuzz) that makes those possible. Every one of these is buildable for darwin15 with a modern cross-capable Clang; nobody has productized it. That productization is aslice.

### 1.1 Design principles

1. **The platform is frozen; the software is not.** macOS 10.11–12 never changes. This is an enormous engineering advantage — ABI assumptions, test matrices, and workarounds are written once and stay true. Every design decision should exploit it.
2. **Binary-first, source-optional.** Users get prebuilt, signed slices. Building from source is a supported workflow, not a prerequisite.
3. **Nothing shared, nothing global.** Each package is a self-contained tree with its own dependencies. No files outside the managed prefix. The system installation is never touched. (See §12.11 for the single declared, consent-gated exception: the `[system-patch]` category — explicit, flagged, reversible, never silent.)
4. **Correctness over cleverness.** Content addressing, a SAT-style dependency solver, and atomic generation swaps. No "it usually works."
5. **Honesty over convenience.** Every trust decision is explicit and recorded. If something can't be verified, aslice says so, in so many words. No silent fallbacks, ever.
6. **Unix through and through.** Small mechanisms, text streams, exit codes, scriptability. Fancy features compose from simple ones or don't ship.
7. **The user owns the machine.** No telemetry, no analytics, no phone-home, no surprise network traffic. aslice is infrastructure, not a product (§9.4).

---

## 2. Relationship to Homebrew (and Others)

Homebrew is the elephant in every room this project will ever enter. The full audit is in HOMEBREW-REVIEW.md; this section summarizes the position.

### 2.1 What Homebrew gets right (and aslice keeps)

- The **tap model**: a package repository is just a git repo of formulae. Distributed, forkable, hostable anywhere. aslice generalizes this into first-class multi-repository support (REPOSITORIES.md).
- **Formula as data**: one declarative file per package, human-readable, diff-able, reviewable.
- **Bottles**: prebuilt binaries are the default experience; source builds are the fallback.
- **`brew doctor`**: a dedicated diagnostics command that checks the environment and says what's wrong in plain language. aslice's `doctor` (§12.2) adopts this wholesale, with structured check output.
- **Community governance in the open**: public CI, public discussions, documented contribution paths.

### 2.2 Where Homebrew's design fails this platform (and aslice diverges)

| Homebrew decision | Why it fails on 10.11–12 | aslice's answer |
|---|---|---|
| `/usr/local` shared prefix | Wild-west filesystem; packages collide; uninstall is guesswork | Isolated `/opt/aslice` prefix (§8.1); per-package store; content-addressed |
| Roll-forward brew update | Upgrades are one-way; a broken formula update breaks users | Generations + instant rollback (§8.4) |
| `uses_from_macos` dependencies | On 10.11, system OpenSSL is 0.9.8, system curl is a security incident | Strict hermeticity (§6.4): only allowlisted system frameworks, never system userland |
| Test-bot on recent macOS only | 10.11 regressions ship to users | Farm tests on every supported OS × flavor (§9.2, BUILD-INFRA.md) |
| Options/variations removed (2019) | Users on old hardware need variants (no-AVX, minimal deps) | First-class variants (§6.3) with prebuilt matrices |
| Ruby DSL, in-process eval | Formulae are arbitrary code in the manager's process | Starlark sandbox, no network, no FS outside build dir (§6.2) |
| Analytics on by default (opt-out) | Violates user trust; meaningless on tiny populations | No telemetry, ever (§9.4) |
| Livecheck is per-formula best-effort | Updates are whoever-remembers | Farm-side freshness pipeline with signed update PRs (§9.5) |
| Single maintainer-held signing story | Key custody is informal | Threshold keys, YubiKey custody, rotation runbook (§10.2) |
| No ABI tracking | Library updates break dependents silently | ABI manifests + rebuild cascades (§7.5) |
| Monorepo of formulae | Trust is all-or-nothing | Tiered trust: official / verified / third-party / local (REPOSITORIES.md §3) |
| Prefix is where-it-is (`/usr/local` or `/opt/homebrew`) | No choice for users without admin rights | `/opt/aslice` default with fully supported `~/.aslice` no-admin fallback (§8.1, §10.3) |

None of this is Homebrew-bashing: Homebrew is optimized for *current* macOS, where `uses_from_macos` is safe and roll-forward is usually fine. aslice is optimized for the opposite constraint set.

### 2.3 Other prior art, briefly

- **Nix/Guix:** content-addressed store, generations, rollback — aslice borrows all three, minus the daemon, the custom language, and the "everything is a derivation" learning curve. aslice packages are conventional tarballs, not a parallel universe.
- **pkgsrc/MacPorts:** still support old macOS, but source-first means hours-long builds on a Core 2 Duo. aslice is binary-first.
- **MacPorts specifically:** the closest living relative. aslice differentiates on: signed binary slices as the default, modern dependency solving, atomic transactions, mirror/mirror-of-mirror support, and a governance model designed for a volunteer project from day one.
- **conda/spack:** good multi-version and variant stories; wrong ecosystem and too heavy.

---

## 3. Architecture Overview

```
                    ┌─────────────────────────────────────┐
                    │           orchards (git)            │
                    │  formula sources: core, extended,   │
                    │  third-party (REPOSITORIES.md §2)   │
                    └──────────────┬──────────────────────┘
                                   │ publish
                                   ▼
                    ┌─────────────────────────────────────┐
                    │     repositories (index + slices)   │
                    │  static files, TUF metadata, any    │
                    │  HTTPS host or local dir            │
                    └──────────────┬──────────────────────┘
                                   │ fetch (TUF-verified)
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
┌───────────────┐        ┌─────────────────┐        ┌────────────────┐
│  aslice CLI   │───────▶│  state (SQLite) │        │  store         │
│  solver, txn, │        │  installed pkgs,│        │  /opt/aslice/  │
│  fetch, verify│        │  pins, repos,   │        │  store/<hash>- │
└──────┬────────┘        │  generations    │        │  <name>-<ver>  │
       │                 └─────────────────┘        └───────┬────────┘
       ▼                                                    │ link
┌───────────────┐                                           ▼
│  build sandbox│                                 ┌────────────────┐
│  (seatbelt)   │                                 │  profile links │
└───────────────┘                                 │  /opt/aslice/  │
                                                  │  bin, lib, ... │
                                                  └────────────────┘
```

The four planes:

1. **Source plane** — orchards: git repositories of formula files. Humans write and review these. The core orchard is `aslice/orchard`.
2. **Distribution plane** — repositories: static file trees (TUF metadata + content-addressed slice files) that any HTTPS server, S3 bucket, GitHub Releases page, or local directory can host. Repositories are *derived* from orchards by the build farm; they never contain anything the orchard didn't declare.
3. **Machine plane** — the store, the SQLite state DB, profiles, and generations. Fully described by the manifest of installed slices; reconstructable from it.
4. **Build plane** — the sandboxed build harness, run by the farm (for published slices) or locally (for `--build-from-source`). Same harness, same sandbox, same output format (BUILD-INFRA.md).

The planes interact through exactly two artifacts: **formulae** (source → distribution) and **slices** (distribution → machine). Both are specified, versioned, and signed.

---

## 4. The Frozen-Platform Advantage

Designing for 10.11–12 means the ground never moves:

- **The ABI surface is fixed.** libSystem, libc++, CoreFoundation versions are known constants per OS release. A compatibility matrix is a document, not a research project.
- **The test matrix is finite.** 7 OS releases × 3 CPU flavors (§4.2) = 21 cells. A package either passes in all 21 or declares its floor. Homebrew's matrix is a treadmill; aslice's is a checklist.
- **Workarounds are permanent.** The patch that makes Python 3.13 build on 10.11 will be correct forever. It is written once, reviewed once, and never rots.
- **Security backports are the whole game.** Since the platform won't get fixes from Apple, aslice's value is tracking upstream security releases for ~300 core packages. This is a tractable, automatable workload (§9.5).

### 4.1 OS support matrix

| Release | Darwin | Notes for aslice |
|---|---|---|
| 10.11 El Capitan | 15 | The floor. SIP introduced (aslice respects it; §8.1). No `utimensat`, weak TLS, ancient libcurl. Maximum hermeticity required. |
| 10.12 Sierra | 16 | `utimensat` appears; APFS not yet default. |
| 10.13 High Sierra | 17 | APFS default on SSDs; aslice must handle both HFS+ and APFS semantics (§8.3). |
| 10.14 Mojave | 18 | Last 32-bit-supporting release. aslice x86_64-only, but 32-bit *installer payloads* (.pkg with i386 slices) are handled where the OS runs them (REPOSITORIES.md §6.3). |
| 10.15 Catalina | 19 | Notarization era begins; aslice slices are unsigned-native-code tarballs — Gatekeeper treatment documented (§10.3). |
| 11 Big Sur | 20 | dyld shared cache changes; Apple Silicon exists but is out of scope — aslice x86_64 slices run on Intel Macs only. |
| 12 Monterey | 21 | The ceiling. Last Intel-supported macOS. |

Every package declares `min_os` (and rarely `max_os`). The solver refuses plans that would install a package below its floor. The farm refuses to publish slices built on a newer SDK than `min_os` implies (§9.2).

### 4.2 CPU flavors

Intel Macs spanning 2007–2020 have meaningfully different instruction sets. aslice defines three build flavors:

| Flavor | Target | Covers | Rationale |
|---|---|---|---|
| `v1` | `x86-64` (SSE4.2) | Core 2 Duo Penryn (2008) and later | The true floor. Everything must have a v1 slice. |
| `v2` | `x86-64-v2` (SSE4.2, POPCNT, AVX) | Sandy Bridge (2011)+ | Meaningful speedup for codec/math workloads. |
| `v3` | `x86-64-v3` (AVX2, BMI2, FMA) | Haswell (2013)+ | The 2013–2020 installed base — most of the target users. |

The client detects its flavor at install (`sysctl -a` CPU features; the logic is 50 lines, not a library). The solver requests the highest flavor the machine supports; every package must provide `v1`, may provide `v2`/`v3`. Missing a preferred flavor is a graceful downgrade, never an error.

Prebuild economics: the farm builds all flavors for the ~300-package core orchard; `v1`-only for the extended orchard's long tail, with popular packages promoted to full matrices (§9.3). Flavor is a *build-axis*, not a variant — it never appears in dependency identities, so mixing v1 and v3 packages in one install is legal and common.

---

## 5. Core Components

aslice is a single static C++20 binary (plus a tiny privileged helper, §10.4). Dependency footprint for the binary itself: libcurl (vendored, with its own TLS), SQLite (vendored), zstd (vendored), a TUF client library (vendored), a Starlark interpreter (vendored), a SAT solver (vendored), libsodium/minisign (vendored). The aslice binary has **zero external dependencies** — it must run on a bare 10.11 install with nothing else present. This is non-negotiable: a package manager that needs packages to run is a bootstrap paradox.

### 5.1 Component inventory

| Component | Responsibility | Notes |
|---|---|---|
| CLI | Argument parsing, subcommands, output formatting | Machine-readable output mode (`--json`) for everything |
| Solver | Version resolution, variants, conflicts | CDCL SAT with domain-specific heuristics (§7) |
| Fetcher | HTTPS downloads, resume, mirror failover | Parallel, throttled, fully logged (§5.2) |
| Verifier | TUF metadata validation, slice signature/hash checks | Fail-closed; no overrides without explicit flags (§10) |
| Store manager | Content-addressed slice installation, GC | Dedup, integrity audit, `store verify` (§8.3) |
| Linker | Profile/generation symlink management | Atomic swaps (§8.4) |
| State DB | Installed set, pins, repos, keys, generations, audit log | SQLite, WAL mode, single-writer (§5.2) |
| Build harness | Sandboxed formula execution | Seatbelt sandbox, network-off, deterministic env (§6.5) |
| Repo client | Multi-repo sync, priority, namespacing | REPOSITORIES.md §4 |
| Self-updater | `self-update`, channels, bootstrap verification | §12.12 |
| Doctor | Environment diagnostics | §12.2 |
| Logger | Structured, leveled, to file and stderr | §5.4 |

### 5.2 The state database

One SQLite file at `/opt/aslice/var/db/aslice.sqlite` (per-user fallback `~/.aslice/var/db/…` for no-admin installs, §8.1). WAL mode, `PRAGMA foreign_keys = ON`, busy-timeout 5s, single writer enforced by an advisory lock file (`db.lock`, `flock`). Schema is versioned (`PRAGMA user_version`); migrations are forward-only, applied transactionally, and the DB is backed up (`aslice.db.backup-<gen>`) before any migration.

Tables (summary; full DDL in the implementation repo):

- `repositories` — name, url, priority, trust level, key fingerprints, enabled, last-sync
- `packages` — installed slice identity: name, version, revision, variant set, flavor, store path, content hash, repo origin, install timestamp; each record stamped `on_request` (user-requested vs pulled-in, §8.4) and **provenance** (farm slice vs local build, surfaced by `info`/`audit`/`doctor`)
- `dependencies` — resolved dependency edges as installed
- `files` — every file installed by every slice (path, hash, type) — powers `aslice owns`, conflict detection, and perfect uninstall
- `generations` — generation number, timestamp, manifest (set of package IDs), description of cause
- `pins` — name/version/variant pins with reasons
- `keys` — trusted signing keys per repo, with TOFU history
- `audit_log` — every mutating operation: what, when, which generation, success/failure
- `mirrors` — per-repo mirror lists, health stats, last-checked

The DB is the source of truth for "what is on this machine." The store is reconstructable from it plus the repositories; the profile is reconstructable from the DB alone.

### 5.3 Why C++20 (and what that demands)

aslice is C++20 because: (a) it must be a zero-dependency static binary; (b) it manipulates Mach-O binaries, SQLite, and syscalls directly; (c) performance matters on a 2008 Core 2 Duo — solver, hashing, and zstd decompression all benefit; (d) the toolchain problem is self-solving — aslice's own `aslice-toolchain` package (modern Clang targeting darwin15) is Phase 0 deliverable #1, and the project dogfoods it from the first commit.

Discipline this imposes:

- **No exceptions across module boundaries** (error codes/`std::expected`); exceptions allowed internally, banned in ABI surfaces.
- **No RTTI** in performance-critical paths; `fmt`-style formatting, not iostreams.
- **Standard library:** libc++ only, vendored at build time; no Boost.
- **Sanitizers in CI:** ASan/UBSan on every PR; fuzzing for the TUF client, the solver input layer, and all parsers (TOML, Starlark host functions, index formats).
- **Memory safety where it counts:** the signature-verification and archive-extraction paths are the highest-risk code; they are written in a restricted subset (no raw `new`, bounds-checked spans, `std::filesystem` with explicit error handling) and reviewed as security-critical. If a future Rust rewrite of these paths happens, the design accommodates it — they're isolated modules behind C interfaces.

### 5.4 Logging

Everything aslice does is logged. Two sinks:

- **stderr** — human output, leveled (`-q` … `-vvv`), progress bars on TTY, plain lines when piped.
- **Log file** — `/opt/aslice/var/log/aslice.log`, structured (one JSON object per line), rotated at 10 MB × 5, includes: timestamp, level, subsystem, operation ID, message, context fields. Every network operation logs URL, bytes, duration, hash-verified status. Every solver run logs input request and solution summary. Every filesystem mutation logs path and result.

The log is the first thing `doctor` asks about and the first thing bug reports attach (`aslice doctor --report` produces a sanitized bundle: log tail, `aslice info`, DB summary with no personally identifying fields, relevant system versions).

Log messages are written for the reader: not "fetch failed" but "failed to fetch slice ffmpeg-7.1-v3 from mirror 2 of 3 (cdn.example.org): HTTP 404 after 1.2s; trying next mirror". A user debugging alone at midnight should be able to read the log and understand what happened.

---

## 6. Formulae: How Software Is Described

The full format is specified in PACKAGE-FORMAT.md. This section covers what the design requires of it.

### 6.1 Requirements

1. **Declarative first.** A formula is data: name, version, sources, dependencies, checksums, metadata. The common case contains zero logic.
2. **Sandboxed logic when needed.** Build steps, conditional dependencies, and platform workarounds need real programming constructs — provided by an embedded Starlark interpreter with no network access and no filesystem access outside the build directory.
3. **Explicit over implicit.** Every dependency is declared; undeclared linkage is a lint error caught by the ABI scanner (§7.5). Every downloaded artifact has a pinned hash. Every patch is an inline file or a hashed URL, with a comment explaining why it exists.
4. **Reviewable in a PR.** Plain text, stable formatting (an `aslice fmt` canonicalizer), meaningful diffs.

### 6.2 The two-layer formula

```toml
# ffmpeg.toml — data layer (always required)
[package]
name        = "ffmpeg"
version     = "7.1"
revision    = 0
license     = "LGPL-2.1-or-later"
description = "Complete audio/video processing toolkit"
homepage    = "https://ffmpeg.org"

[source]
url    = "https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz"
sha256 = "…"

[dependencies]
runtime = ["x264", "x265", "lame", "opus", "libvpx"]
build   = ["nasm", "pkg-config"]

[variants]
"no-gpl" = { description = "LGPL-only build", conflicts = ["x264", "x265"] }
"av1"    = { description = "Add SVT-AV1 encoder", adds_deps = ["svt-av1"] }

[platform]
min_os = "10.11"
```

```python
# ffmpeg.star — logic layer (optional; build steps and conditionals)
def configure(ctx):
    args = ["--prefix=" + ctx.prefix, "--enable-shared"]
    if ctx.os_version <= "10.12":
        args += ["--disable-videotoolbox"]  # broken headers pre-10.13
    if "av1" in ctx.variants:
        args += ["--enable-libsvtav1"]
    return args
```

The Starlark environment provides `ctx` (os_version, flavor, variants, prefix, dependency paths) and build helpers (`run`, `apply_patch`, `env`). It cannot: open sockets, read outside the build dir, spawn processes outside the sandbox, or persist state between phases. A formula that needs something the sandbox forbids is a bug report against the harness, not a reason to widen the sandbox.

### 6.3 Variants

Homebrew deleted options because combinatorial explosion broke CI. aslice keeps them under control instead:

- Variants are declared in the formula, typed (boolean/enum), documented, and **finite in practice**: orchard policy caps variants per package (guideline: ≤ 6, each justified in review).
- The farm prebuilds the default variant set for core packages; variant combinations beyond the default are built from source on the user's machine or requested via `aslice build-request` (§9.3).
- Variants are part of dependency identity only when they change the ABI (`abi = true` in the variant declaration). A "no-gpl" ffmpeg and a default ffmpeg cannot both satisfy a dependent that links ffmpeg — the solver treats them as conflicting providers. A "headless" variant that changes nothing downstream is invisible to dependents.

### 6.4 Hermeticity

Packages link only against: (a) other aslice packages; (b) macOS system **frameworks** (which are stable ABI surfaces — Accelerate, CoreAudio, etc.); (c) never `/usr/lib` dylibs, never `/usr/bin` tools. On 10.11 the system OpenSSL is 0.9.8zh and the system curl is a liability; depending on them is depending on the problem aslice exists to solve.

The build harness enforces this: the sandbox blocks read access to `/usr/lib` and `/usr/bin` except for an explicit allowlist (system frameworks, dyld, libSystem, compiler toolchain paths). Post-build, the ABI scanner verifies the Mach-O load commands of every produced binary against the declared dependency list. Violations fail the build. This is the single most important property of the system — it is what "modern software" means on a frozen platform.

### 6.5 The build sandbox

`aslice build` executes the formula in a seatbelt-sandboxed process:

- Filesystem: read-write access to a fresh build dir and the store paths of declared build dependencies; read-only allowlist (system frameworks, toolchain); everything else denied.
- Network: denied after the fetch phase. Fetches happen before the sandbox drops, into a content-addressed download cache, each artifact hash-verified before the build starts. A build that "phones home" is impossible by construction.
- Determinism: `SOURCE_DATE_EPOCH` set, fixed umask, LC_ALL=C, no timestamps in archives. Reproducible builds are a Phase 2 goal for the core orchard (§14); the sandbox is deterministic from day one so that goal stays reachable.
- Privilege: builds never run as root. Local builds run as the invoking user. Farm builds run as a dedicated `aslice-build` user (BUILD-INFRA.md §6).

The same harness runs on the farm and on the user's machine, from the same formula, producing the same slice format. A local `--build-from-source` install is not a second-class citizen: it is a valid slice, marked `built_locally` in the DB, installed into the store like any other.

---

## 7. The Solver

Dependency resolution is a SAT problem with optimization objectives. aslice embeds a CDCL solver (vendored, ~3k lines, fuzz-tested) rather than shelling out.

### 7.1 Problem encoding

- **Variables:** (package, version, revision, variant-set, flavor) tuples that could enter the solution.
- **Clauses:** dependency requirements (A ≥ 2.1), conflicts (variants, coinstallability), availability (what the enabled repos actually offer for this OS/flavor), pins, and the installed set's preferences.
- **Optimization (lexicographic):** (1) satisfy all hard constraints; (2) prefer already-installed versions (minimal change); (3) prefer highest versions; (4) prefer higher flavors matching the machine; (5) prefer default variants.

### 7.2 Properties the solver must guarantee

- **Soundness:** a printed solution always respects every constraint; the CLI shows the plan and asks before executing (unless `-y`).
- **Explanations:** when resolution fails, the output names the conflict chain: "ffmpeg 7.1 requires x264 ≥ 164, but repo 'core' provides x264 ≤ 163 for macOS 10.11 — x264 164 requires min_os 10.13." Unsatisfiable-core extraction, formatted for humans.
- **Determinism:** same inputs → same solution, always. Objective weights are fixed constants.
- **Performance:** ≤ 100 ms for the core orchard on a Core 2 Duo; ≤ 2 s worst case with extended orchard. The SAT encoding is incremental (reuse across a session).

### 7.3 Version semantics

Semantic-ish: `upstream.version-revision` where revision is aslice's (packaging changes with identical upstream). Ranges: `>=1.2 <2`, `~1.4` (compatible release). Epochs exist for upstreams that go backwards (`1:2.0 < 3.1`). Versions sort with the RPM algorithm, which handles the weird real-world cases (letters, tildes, more segments than expected) better than strict semver.

### 7.4 Virtual packages and providers

`tls-provider`, `awk`, `editor` — multiple packages can provide a capability. Providers declare it; dependents request the virtual. The solver picks a provider (preferring installed, then orchard-default hints) and records the choice in the DB so future resolutions are stable. Conflicts between providers of the same virtual are explicit in the formulae.

### 7.5 ABI tracking and rebuild cascades

Every slice ships an ABI manifest: exported symbols (Mach-O nlist + typed metadata: symbol name, demangled signature where applicable), the install names and compatibility versions of its dylibs. The farm diffs manifests between versions:

- **Compatible change** (added symbols only): dependents unaffected; publish freely.
- **Breaking change** (removed/changed symbols, compatibility version bump): the farm rebuilds all reverse dependencies in the same publish batch. The index metadata marks the batch as atomic — clients must upgrade the provider and its rebuilt dependents together. The solver encodes this as equality constraints across the batch.

This kills the classic "brew upgrade openssl broke everything" failure mode. The client never sees half of an ABI transition.

---

## 8. Installation Layout, Store, and Generations

### 8.1 The prefix

```
/opt/aslice/
├── store/                  # content-addressed slices
│   └── a1b2…-ffmpeg-7.1-v3/
│       ├── bin/  lib/  share/  …
│       └── .aslice/        # manifest, ABI info, SBOM, build log
├── profiles/
│   └── default -> generations/42
├── generations/
│   ├── 41/                 # symlink forest into store
│   └── 42/
├── bin -> profiles/default/bin
├── var/
│   ├── db/                 # state DB, backups
│   ├── log/
│   └── cache/              # download cache (safe to delete)
└── etc/                    # aslice.conf, repo configs, keyrings
```

Why `/opt/aslice`: `/usr/local` is Homebrew's and must not be collided with (coexistence, §13.3); `/opt` is conventional, SIP-clean, and admin-writable via one `sudo mkdir/chown` at install time. The prefix is fixed — not configurable — because hardcoded-prefix binaries (absolute install names in Mach-O) make prefix relocation genuinely hard, and "any prefix" support is how Homebrew ended up unable to bottle reliably. One prefix, known forever: `/opt/aslice`.

Per-user installs without admin: supported at `~/.aslice` with identical layout. The solver/store/generations don't care where the root is; only the install script and the shell-setup snippet differ. Mixed installs (some packages in /opt, some in ~) are **not** supported — one aslice root per user context, chosen at install time.

### 8.2 The store

Slices are unpacked to `store/<content-hash>-<name>-<version>-<flavor>/`. Content addressing gives: dedup (identical slice → identical path, installed once), integrity (path = expectation), and safe concurrency (a slice being written is never a slice being read — extraction happens to a temp name, verified, then atomically renamed into place).

Hardlinking files out of the store (the Nix trick) is not used: APFS clonefiles are used for large identical files within a slice where beneficial, but links *between* store paths are forbidden — store paths are immutable and independent, so deletion and corruption analysis stay trivial.

### 8.3 Filesystem realities

- **HFS+ vs APFS:** 10.11–10.12 installs are HFS+; 10.13+ usually APFS. HFS+ lacks copy-on-write and has case-insensitive-by-default semantics; aslice normalizes: store paths are lowercase-safe, and the installer warns (not errors) on case-sensitive volumes — a handful of upstream tarballs contain same-name-different-case files and will fail to extract; those formulae declare `needs_case_insensitive = true` (the common case).
- **Quarantine:** files aslice downloads get `com.apple.quarantine` only if the download tool adds it; aslice's fetcher strips it post-verification (the slice is signed and verified — quarantine prompts are noise). Documented in §10.3.
- **`noatime`/performance:** store operations avoid unnecessary metadata writes; the GC uses `st_birthtime` where available.
- **Path length:** max store path ~120 chars, well under limits.
- **Symlink policy:** symlinks inside store paths are preserved as-is (relative within the slice, or absolute to the slice root — rewritten at pack time). Profile forests (§8.4) are symlinks *into* the store; nothing in the store points out.

### 8.4 Generations and rollback

A **profile** is what the user actually has on PATH: `/opt/aslice/bin -> profiles/default/bin`, and the profile is a forest of symlinks into the store. A **generation** is an immutable, numbered profile forest. Every mutating transaction (install, remove, upgrade) builds a *new* generation directory, then atomically swings the profile symlink (`rename(2)` — atomic on both HFS+ and APFS). The old generation is untouched.

```bash
aslice install ffmpeg          # builds generation 43, swings link
aslice rollback                # back to generation 42: one symlink rename
aslice switch-generation 38    # any retained generation
aslice generations             # list with timestamps and causes
```

Generations are garbage-collected by policy: keep last 20, plus any younger than 30 days, plus pinned ones (`aslice generation pin 42`). GC deletes the generation forest and any newly-unreferenced store paths.

Rollback correctness: because slices are immutable and independent, a generation forest is always coherent — there is no "half-upgraded" state, because the symlink swing is the only observable transition, and it is atomic. A crash mid-transaction leaves the old generation active; the half-built new generation is cleaned up on next run (staged in `generations/.staging-<opid>`; `doctor` and startup both sweep).

**On-request tracking and `clean`.** Every DB record carries an `on_request` flag: packages the user explicitly asked for (`aslice install ffmpeg`) versus packages pulled in as dependencies. This powers `aslice leaves` (the user's actual wishlist), smarter `remove` warnings ("x264 is required by ffmpeg"), and **stale-dependency GC**: when the last dependent of a pulled-in package is removed, that package becomes a GC candidate surfaced by `aslice clean`/`doctor` rather than silently accumulating. `aslice clean` also evicts the download cache — the cache is a courtesy for re-installs, never a requirement, and on 2011-era disks every gigabyte counts. Superseded slice downloads are evicted aggressively; the cache never grows without bound.

**Rollback hygiene is deliberately narrow:** generations track *packages*, nothing else. aslice does not snapshot user data, config files in `~/`, or the system. The one exception is declared, per-file, and consent-gated: `[system-patch]` backups (§12.11). Scope discipline is what keeps rollback instant.

### 8.5 Concurrency

One mutating transaction at a time (the DB lock file covers the store + profile + DB as a unit). Read-only commands (`list`, `info`, `search`, `owns`) never block. Downloads may proceed concurrently with an active transaction but their *results* are staged until the lock is free. Multiple users on one machine: the prefix is admin-group-writable; the lock is machine-global; audit log records the user.

---

## 9. The Build Farm and Release Pipeline

(Architecture detail: BUILD-INFRA.md. Design requirements here.)

### 9.1 Requirements

1. Build every core-orchard package for **21 cells** (7 OS × 3 flavors) — though in practice the matrix is build-on-oldest + test-on-all: slices are built against the oldest SDK the formula supports, then smoke-tested on every OS release.
2. Build on real Intel hardware, not cross-emulation. The farm is small (frozen platform = fixed workload): a handful of Mac minis. VM-based workers (ESXi/Proxmox on Intel) are acceptable and documented.
3. Every slice is signed (minisign, §10.1) and accompanied by: build log, SBOM (SPDX), ABI manifest, and the exact orchard commit it was built from.
4. Publishing is a TUF snapshot: new slices + updated index + timestamp/snapshot/targets metadata, signed by the farm's online keys under thresholds (§10.2). A publish is atomic — clients never see partial states.
5. Provenance: every published slice links to its build log and orchard commit. Phase 2: SLSA-style provenance attestations; reproducibility cross-checks (two independent builders must agree on hashes for core packages).

### 9.2 Test obligations

A core package update is published only if: it builds on the oldest declared OS; its test suite (formula-declared `tests.star` — smoke tests at minimum) passes on every supported OS × the built flavor; the ABI gate (§7.5) passes or the rebuild cascade is included. The extended orchard is best-effort: built on oldest OS, smoke-tested on one, labeled as such in the index metadata (honesty: the index states the test coverage each slice received).

### 9.3 Economics

The core orchard (~300 packages: the dependency stratum plus the top applications) gets the full 21-cell treatment. The extended orchard (~2,000 packages, Phase 2) is v1-flavor, oldest-OS-build, single-OS-smoke-test by default. Popular extended packages get promoted based on… community requests and maintainer judgment. **Not** download counts: aslice collects no telemetry (§9.4), and on a legacy platform the most valuable package may be the one three people a year need — the obscure codec library that makes a 2010 audio workstation useful again. Promotion decisions happen in the open, in orchard issues.

### 9.4 No telemetry, ever

aslice has no analytics, no install IDs, no "anonymous usage statistics," no update-check phone-home beyond the TUF metadata fetch the user explicitly triggers (`aslice update`). The farm knows what it publishes, not who fetches it — repository hosting should prefer providers/CDNs that don't log or that let the project see only aggregate bandwidth. The principled stance: this project serves a niche community including people with privacy reasons to run old systems; their package manager must not be a sensor. If "we can't improve without data" ever gets argued, the answer is: maintainers read issues, and the frozen platform means the problem space is small enough to hold in your head.

### 9.5 Freshness pipeline

Because the platform is frozen, keeping software current is the project's core recurring work:

- Each core formula declares `livecheck` (URL + regex or JSON endpoint) for upstream releases.
- A farm-side scheduled job runs livechecks daily, opens orchard PRs for updates (with the version bump, refreshed hashes, and a changelog link), and labels security-relevant ones (CVE feeds matched against package CPEs).
- Maintainers merge; the farm builds; the ABI gate runs; publish happens.
- Target cadence: security updates for the TLS/network stratum within 72 hours of upstream release.

This is deliberately the same machinery a third-party repo can run — REPOSITORIES.md §8 documents the publish pipeline as a reusable tool (`aslice repo build`, `aslice repo publish`).

---

## 10. Security and Trust

The threat model and full key management are in §10.2; repository-level trust tiers in REPOSITORIES.md §3. Design commitments:

### 10.1 Verification chain

Every artifact the client consumes is verified before use:

1. **TUF metadata** (root → targets → snapshot → timestamp) signed by repository keys, threshold-quorumed, with consistent-snapshot guarantees — protects against rollback, freeze, mix-and-match, and mirror compromise.
2. **Slice signatures** — each slice is a `.slice` file (tar.zst + detached minisign signature + manifest); the signature key must be in the repo's TUF targets metadata (delegated) or the package is rejected. Defense in depth: even if TUF metadata were replayed, slices still verify against pinned keys.
3. **Hash pinning everywhere** — formula sources, patches, vendored artifacts: all SHA-256, all checked before sandbox entry.

Failures are loud, specific, and non-overridable without explicit per-command flags (`--insecure-no-verify` exists for development, prints a scarlet warning, requires typing, and is refused when the repo's trust tier is `official` — you cannot weaken the official repo's guarantees from the CLI).

### 10.2 Key management

- **Root keys (TUF):** 3-of-5 threshold, offline, on YubiKeys held by founding maintainers in at least two countries. Used ~quarterly (snapshot signing is delegated to online keys).
- **Online signing keys:** farm-held, minisign for slices + TUF delegation; rotating annually; compromise procedure = revoke via root quorum, re-sign affected snapshots, publish security advisory through the repo itself (clients surface it on next update).
- **The rotation runbook is a written document** (`docs/key-ceremony.md` in the org), rehearsed once before launch. Key ceremonies are logged in a transparency log (append-only, published in the repo) — a legacy-platform project survives on trust, and trust survives on visibility.
- **Client key pinning:** the official repo's root key hash ships compiled into the aslice binary *and* is displayed at install time for out-of-band verification. Third-party repos are TOFU with explicit fingerprint confirmation (REPOSITORIES.md §3).

### 10.3 Gatekeeper, notarization, and the bootstrap problem

The aslice installer itself: a signed, notarized .pkg for the initial install (one-time Apple developer cert cost — worth it: first impressions on 10.15+ without notarization are scary dialogs). The aslice binary is notarized. **Slices are not notarized** — they're tarballs of Unix software, and per-slice notarization is impossible at this scale; instead: quarantine attributes are stripped after verification (§8.3), and Gatekeeper's first-run assessment applies to executables launched via Finder, not CLI tools. The tradeoff is documented honestly: aslice's trust chain is TUF+minisign+provenance, not Apple's notary service. Users who want Apple-only trust should not install third-party package managers at all — and that's a legitimate choice aslice respects by never hiding what it is.

Bootstrap: the install script (`curl … | sh` is *not* the method) is: download .pkg from the canonical URL → pkg installs /opt/aslice skeleton + binary + pinned root key → `aslice doctor` runs → first `aslice update` syncs TUF metadata. The chicken-and-egg (aslice needs TLS; 10.11's TLS is broken) is solved by the vendored libcurl+TLS inside the aslice binary (§5) — the binary brings its own modern TLS from byte zero. CA certificates: an aslice `ca-certificates` package (Mozilla bundle) is installed as part of the bootstrap transaction, and aslice's vendored curl uses it in preference to the system keychain (§12.10).

### 10.4 Privilege separation

aslice runs unprivileged. Operations needing elevation (initial /opt/aslice creation; kext installs; service management into /Library/LaunchDaemons) go through a tiny, separate, audited helper: `aslice-system` (§12.7), installed setuid-root **only if** the user opts into those features, communicating over a narrow IPC with a fixed command set (no shell strings, ever). Default installs never need it after day one. The helper is small enough to print and read in one sitting — that is a design requirement, not an aspiration.

---

## 11. User Experience Details

### 11.1 Output philosophy

- Quiet by default, verbose on request, structured with `--json`.
- Progress: spinners/bars on TTY; when piped, one line per milestone (script-friendly).
- Plans are shown before mutations: what will be installed/upgraded/removed, sizes, and why (requested/dependency/upgrade of X). `-y` skips the prompt; `--dry-run` shows the plan and stops.
- Errors name the thing, the cause, and the suggested next step. "Error E2017" alone is a bug.

### 11.2 `aslice doctor`

Checks, in order: prefix writable; DB healthy (integrity check); store integrity (sampled or full with `--full`); profile symlink coherence; PATH setup correct; shell integration present; repos reachable and metadata fresh; clock sane (TUF expiry depends on it); SIP status (informational); Homebrew coexistence notes; CA bundle freshness; disk space headroom. Each check: OK / FIX (auto-fixable, `doctor --fix`) / ACTION (manual steps, printed). Exit code reflects worst finding — scriptable.

### 11.3 Shell integration

`aslice shellenv` prints the PATH/MANPATH/INFOPATH exports (detecting zsh/bash); the installer offers to add one line to the user's profile. Completions ship for zsh and bash. No shell hooks, no prompt modification, no shims directory injected ahead of system paths — aslice appends, never prepends, unless the user asks.

### 11.4 Scripts and automation

Everything scriptable: `--json` output, stable exit codes (0 ok; 1 generic; 2 usage; 3 network; 4 verification; 5 solver-unsat; 6 partial-failure), `--no-input` mode that refuses all prompts (for CI), `ASLICE_PREFIX`/`ASLICE_NO_COLOR`/`ASLICE_CACHE_DIR` env overrides. The CLI is a library consumer: `libaslice` (C++ API, C ABI wrapper) exists for a future GUI or other tooling, but the CLI ships first and the library is extracted from it, not vice versa.

---

## 12. CLI and User Experience

### 12.1 Commands

```
aslice install ffmpeg              # resolve, show plan, fetch, verify, link — new generation
aslice remove ffmpeg               # with reverse-dependency check and explanation
aslice upgrade [ffmpeg | --all]    # solver-driven; ABI batches move together (§7.5)
aslice update                      # sync repo metadata (TUF); shows what's outdated
aslice outdated                    # packages with newer versions available
aslice reinstall ffmpeg            # rebuild/relink a package in place (new generation)
aslice pin ffmpeg / unpin ffmpeg   # hold at version; solver respects pins
aslice list / leaves / deps ffmpeg # installed set; on-request leaves; dependency tree
aslice info ffmpeg                 # metadata, installed files, reverse deps, provenance
aslice search term                 # across enabled repos, with trust labels
aslice owns /opt/aslice/bin/ffplay # which slice owns a file (DB `files` table)
aslice doctor [--fix] [--full]     # diagnostics (§12.2); --report emits a sanitized bundle
aslice generations / rollback      # generation list, instant rollback (§8.4)
aslice clean                       # evict download cache + stale-dep GC (§8.4)
aslice store verify [--full]       # hash-audit the store against manifests
aslice build ./formula.toml        # local sandboxed source build (§6.5)
aslice livecheck [ffmpeg]          # run upstream-release checks (§9.5)
aslice test ./formula.toml         # run a formula's tests.star against a local build
aslice create <name> [--from-url]  # scaffold a new formula (data layer + .star stub)
aslice bump-pr ./formula.toml      # livecheck + hash refresh + open orchard PR (§9.5)
aslice edit ffmpeg                 # open the installed formula in $EDITOR (read-only view)
aslice log [-f]                    # tail the structured log (§5.4)
aslice repo add/list/remove/…      # repository management (REPOSITORIES.md §4)
aslice key list/trust/revoke       # client-side key management (§10.2)
aslice ca-update [--crypto|--keychain|--apple-certs]  # CA/roots management (§12.10)
aslice services [start|stop|restart]  # user LaunchAgent management (§12.8)
aslice self-update                 # update aslice itself (§12.12)
aslice exec ffmpeg -- ffplay …     # run a store binary with its slice env
aslice shellenv                    # print shell exports (§11.3)
aslice use python 3.13             # runtime version switching (§12.9)
aslice default python 3.13         # persist a runtime default (§12.9)

# every command: --json, --no-input, -q/-v/-vv, stable exit codes (§11.4)
```

### 12.2 Doctor

(See §11.2.) Design note: `doctor` is a first-class command because legacy-platform users debug alone. Its `--report` bundle is the standard bug-report attachment.

### 12.3 The install transaction

1. Lock (§8.5) → 2. Resolve (§7) → 3. Plan display → 4. Fetch slices (parallel, mirror failover, resume) → 5. Verify (TUF + minisign + hashes, §10.1) → 6. Stage extractions to temp paths → 7. Hash-audit extracted trees → 8. Atomic renames into store → 9. Build new generation forest → 10. Swing profile symlink → 11. DB commit → 12. Unlock. Any failure before step 10: old state untouched. Failure at 10–11: transaction retried once, then rolled back with the staging area swept. The audit log records every step.

### 12.4 Mirrors and offline

Repositories declare mirror lists in their TUF root metadata (REPOSITORIES.md §5). The fetcher races the first byte across up to two mirrors, sticks to the winner per session, and records health stats in the DB. `--offline` mode: resolve against cached metadata only, install only already-cached slices, fail with a precise list of what's missing otherwise. `aslice mirror add` lets a lab with 30 old Macs run one caching mirror on a LAN — the mirror is just a static file server; TUF verification is end-to-end, so mirrors are untrusted by design.

### 12.5 Vendor binary packages (.pkg / .dmg)

Specified in REPOSITORIES.md §6. Design commitments: vendor installers are first-class package sources (`type = "binary"`), installed by payload extraction (never by running vendor preinstall scripts blindly), verified by pinned hash + Apple Developer ID signature chain where present, and recorded in the DB like any slice. Where a vendor .pkg refuses payload-only installation (scripts that matter), the formula declares it and aslice runs the installer with `installer -pkg` under the user's sudo, logging the choice loudly. 32-bit payloads are supported on the OS releases that run them (10.11–10.14) — the index tags slices with architecture lists, and the solver matches the OS's capability, not just the CPU.

### 12.6 Coexistence with Homebrew

aslice never touches `/usr/local`. `doctor` detects Homebrew and advises on PATH order. `aslice adopt --from-homebrew` (§13.3) migrates intent. Running both forever is a supported configuration.

### 12.7 Kernel extensions and SIP-sensitive software

Some development tools on legacy macOS require kexts (VirtualBox, osxfuse successors) or SIP disabled (DTrace workflows, certain debuggers). aslice supports these as declared, warned categories:

- A formula declares `kext = true` or `needs_sip_disabled = true`; the plan display shows a **bold warning**, requires explicit `--accept-system-software` plus interactive confirmation, and logs the decision to the audit trail.
- Kext installation goes through `aslice-system` (§10.4), uses `kextload`/`kmutil` as the OS requires, and registers the kext in the DB so `aslice remove` unloads and deletes it, and `doctor` verifies load state.
- SIP: aslice never touches SIP settings. If a package needs SIP off, the CLI prints the exact steps (recovery mode, `csrutil`), the risks, and the reversal command — and the package stays refused until the machine state satisfies it. On rollback or removal, aslice **asks the user** whether to restore the prior system state (re-enable SIP reminders, unload kexts) — never silently.

### 12.8 Services (launchd)

Packages with daemons declare `[service]` in the formula: plist template, RunAtLoad/KeepAlive semantics, user-vs-system scope. aslice generates the plist into `~/Library/LaunchAgents` (user scope, default) or `/Library/LaunchDaemons` (system scope, via aslice-system, requires the service to declare why). `aslice services` lists/manages them. Services ride along with generations: upgrading a service package restarts the service only after the generation swing succeeds, and rollback restarts the old version. Health check post-restart: the formula may declare a probe (port, PID file, command); failure offers automatic rollback.

### 12.9 Runtime version management

(Python 3.11 vs 3.13, Node 18 vs 22, etc.) aslice's answer: **multiple versions are coinstallable slices** (`python@3.11`, `python@3.13` are distinct package names with a shared `python` virtual). `aslice use python 3.13` manipulates a `~/.aslice/runtimes` shim layer that precedes the profile on PATH for interactive shells (opt-in via shellenv); `aslice default python 3.13` writes the persistent choice. Project-level pinning: `.aslice.toml` in a project dir, activated by `aslice use --project` or direnv-style shell hook (strictly opt-in). Riding tools (pip, npm, gem) install into per-runtime-version site directories *inside the runtime's store path versioning* so switching runtimes never strands packages: `aslice` tracks them as extension slices of the runtime, rebuilt on runtime upgrades when ABI demands it. Full mechanism: §12.9 in the design doc history; the invariant is *the solver owns runtimes, shims own the prompt*.

### 12.10 CA certificates and crypto stores

Legacy macOS's trust stores are frozen mid-decay — expiring roots, missing modern CAs (ISRG Root X1 was the famous breakage), SHA-1-era intermediates. aslice addresses this at three layers, all explicit:

1. **Userland (default):** the `ca-certificates` slice (Mozilla's bundle, tracked as an ordinary auto-updated package) provides CA roots for aslice itself and for aslice-installed software — OpenSSL/LibreSSL/curl/gnutls from aslice are configured to use it. This fixes the 95% case (command-line tools, libraries) with zero system modification.
2. **System keychain (opt-in):** `aslice ca-update --keychain` imports/updates roots in the **System keychain** (`/Library/Keychains/System.keychain`, all users) via `aslice-system` using the Security framework. Machine-level operation, always prompted, logged, reversible (added certs are tagged with an aslice marker in their metadata where possible and enumerated before/after; removal command provided). Affects Safari, Mail, and all Secure Transport consumers.
3. **Crypto/roots refresh (flags):** `aslice ca-update --crypto` upgrades the crypto stratum (openssl, libressl, gnutls, ca-certificates) to current in one solver transaction. `aslice ca-update --apple-certs` refreshes Apple's own roots (from Apple's published PKI pages) into the System keychain — needed because Apple roots from 2015-era images sometimes predate intermediate rotations.

Trust sources are configurable (`aslice.conf`: Mozilla bundle default; alternatives documented), because some users' threat models prefer narrower bundles.

### 12.11 Patching the system, honestly: `[system-patch]`

The charter carve-out, engineered: aslice's founding promise was "never touch the system," and reality (§12.10 layer 2/3, plus files like ancient `/usr/lib/libcurl.4.dylib` that no framework fixes) makes a narrow, declared exception genuinely useful. It exists under the strictest gate in the system:

- A formula is marked `[system-patch]`: it targets specific absolute system paths (enumerated in the formula — no wildcards), each with the OS releases it applies to.
- **Backup first, always:** before any replacement, the original file is copied byte-exact (with permissions, ACLs, xattrs) into the store under the patch slice's path. Nothing is overwritten without a verified backup.
- **Replacement by symlink:** the system path is replaced with a symlink into the aslice store (per the charter: "it should be symlinks"), so the patched state is visible (`ls -l` tells the truth), and rollback is: restore backup bytes, remove symlink. A generation rollback automatically re-converges patched paths to the generation's manifest.
- **Rollback is offered, not assumed:** on remove/rollback of a system-patch slice, aslice asks the user whether to restore the original file — and defaults to restore, with `--keep-patch` as the explicit override. A macOS update that overwrites the patch is detected by `doctor` (hash mismatch vs manifest), which offers reapply-or-restore.
- **Double warning, double consent:** install requires `--accept-system-software` *and* an interactive per-file listing of what will be replaced, with the backup location printed. The audit log records every patched path forever.
- **Trust:** served by **official and local** repositories by default; a **verified** repository may serve `[system-patch]` packages only with an explicit per-repo grant — `aslice repo allow-system-patch <name>` (refused by default, recorded in the state DB, revocable via `aslice repo deny-system-patch <name>`); **third-party never** (REPOSITORIES.md §3, ORCHARD-POLICY §13). The grant gates *serving*; the per-decision consent flow above is unchanged and applies whoever serves the package.

**Honesty.** This category exists because the alternative is users doing the same thing by hand — `curl | sudo sh`, a downloaded "TLS fixer," a copied dylib — with no provenance, no backup, and no way back (the §12.7 argument, applied to files). aslice's guarantee is narrower than for ordinary packages and says so (§10.7): the replacement bits are exactly the declared, verified ones; the original is preserved and restorable to the byte; refused paths are refused by construction; and the user was warned at every decision point.

### 12.12 Self-update: aslice is package zero

A package manager that cannot safely update itself either rots or trains users to re-run a curl-pipe script — the exact pattern this security model exists to kill. aslice updates itself through the same machinery as everything else, with one wrinkle handled explicitly.

- **aslice is a package.** The manager lives in its own store path (`/opt/aslice/store/aslice-x.y.z-…/`) with a formula in the core orchard, a manifest, an SBOM, and a minisign signature. `aslice self-update` is an ordinary transaction — resolve, fetch slice, verify, build generation, atomic swap — whose only special property is that the running binary is the thing being swapped.
- **The swap waits for the transaction to finish.** The profile symlink to `bin/aslice` flips with the generation as usual; the *running* process completes its bookkeeping, then re-execs the new binary to print the result. The old binary never vanishes mid-execution: the store path is immutable, and the previous generation remains invocable through ordinary rollback.
- **Health check with automatic rollback.** Post-swap, the new binary runs a smoke self-test (version report, DB open, index read). Failure rolls the generation back automatically and reports loudly — the one package whose bug could brick the installation gets the strongest rollback guarantee, not the weakest. A failed self-update leaves the previous, working aslice exactly where it was.
- **Channels and pins apply.** `self-update` honors the configured channel and refuses to cross a spec/format major version without printing the changelog and requiring confirmation. `aslice pin aslice` holds the manager itself — same hold machinery as any package.
- **Bootstrap trust is notarization plus signature** (§10.3): release binaries are minisign-signed with the project key *and* Apple-notarized, so first run on Gatekeeper releases has no "unidentified developer" friction; the install script verifies the minisign signature itself, keeping notarization as defense-in-depth and UX rather than the root of trust.

---

## 13. Policies, Governance, and Migration

### 13.1 Package acceptance policy

- Core orchard: maintained, security-patched, reproducible-build targets; no package enters without a working `tests.star` smoke test on at least one OS × one flavor.
- Upstream-EOL software: allowed in extended with `eol = true` metadata; excluded from core.
- Vendor binary packages: accepted into extended only with a verifiable signature and honest OS-support tags; into core only if additionally redistributable (so the farm hosts the slice) and payload-only by construction. A vendor package whose scripts turn out to be required is removed, not accommodated.
- **Runtime dependencies resolve to aslice packages only** — the codified rejection of Homebrew's `uses_from_macos`. Never `/usr/lib` dylibs, never `/usr/bin` tools: on 10.11 the system libraries *are the problem*. The only exceptions are always-present system **frameworks** (`Accelerate`, `SystemConfiguration`, `CoreAudio`, `CoreFoundation`, …) enumerated in a lint allowlist — frameworks are the platform's ABI, not its bundled software. Allowlist additions are policy PRs against ORCHARD-POLICY §6 and the lint table together.
- **Patching system files is rejected by default — and flagged where it isn't.** aslice installs alongside macOS and never modifies `/System`, `/usr`, or Apple's binaries silently, incidentally, or as a side effect of anything else. Where fixing the frozen platform genuinely requires replacing an Apple-provided file, the declared `[system-patch]` category (§12.11) does it openly: original backed up, replacement via profile symlink, rollback to the byte, consent at every decision point, served by official and local repositories — and by verified ones only under an explicit per-repo `allow-system-patch` grant (§12.11) — with catastrophic and platform-binary-library paths refused by construction. The marketing feature survives, stated honestly: aslice never patches your system *behind your back*. Kernel extensions and SIP-disabled development software likewise remain the declared, warned, trust-gated category of §12.7.

### 13.2 Variant discipline

`abi = true` variants are capped per package (guideline: ≤ 6) and each must justify its existence in review. This keeps the solver space small, the prebuilt matrix tractable, and avoids repeating the option-sprawl that made Homebrew variants unmaintainable. `abi = false` (build-flavor) variants are unconstrained — they cost the project nothing because they never spawn binary flavors.

### 13.3 Coexistence and migration from Homebrew

- **Coexistence:** aslice lives in `/opt/aslice`, never touches `/usr/local`, and `doctor` detects a Homebrew installation and advises on PATH ordering rather than conflicting.
- **`aslice adopt --from-homebrew`:** reads Homebrew's Cellar and `brew leaves`, maps names to aslice formulae (with a maintained alias table for renames), produces an install plan that recreates the same leaf set — including mapping old `--with-*` Homebrew options to aslice variants where an alias exists. Cask leaves map to vendor-binary packages where one exists, flagged for review when the vendor artifact's OS tags don't cover the machine. It does not attempt binary reuse of Homebrew's Cellar (different prefix assumptions); it reuses the *intent*.
- **Formula importer (for orchard authors):** a tool that mechanically translates simple Homebrew Ruby formulae — `url`/`sha256`/`depends_on`/standard `configure && make` bodies — into TOML+Starlark drafts, with a human review step. Realistic coverage target: the simple ~60–70% of formulae; the rest are ports, not translations. A companion importer turns simple Casks (`url`/`sha256`/`app`/`pkg`) into `type = "binary"` drafts — Casks are *more* mechanical than formulae, so coverage should be higher; the reviewer fills in signer pinning and OS tags.

### 13.4 Governance

- Benevolent-core-team start: 3–5 founding maintainers holding threshold keys; decisions by lazy consensus, escalations by vote.
- Orchard PR review backed by CI that *builds the package in the sandbox on every declared flavor* — review is about correctness and policy, never "does it compile." The merge gate is five checks, with no maintainer override (ORCHARD-POLICY §10): lint (schema + policy), a matrix build on every declared flavor at the formula's `min_os` with smoke-runs across `[min_os, 12]`, the `tests.star` smoke test, an **ABI gate** on provider version/revision changes (a regression requires an honest version bump or scheduled dependent rebuilds, published in the same index snapshot), and post-merge-only signing.
- **Project hygiene documents ship in Phase 0** — `SECURITY.md` (how to report a vulnerability in aslice itself; key-contact runbook), `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md` (the formula style guide: when a variant is justified, `min_os` honesty, patch documentation), and the written key-ceremony/rotation runbook referenced by §10.2. Documents, not code — cheap before launch, expensive after the first incident.
- Public roadmap, public build-farm dashboard, public transparency log. A legacy-platform project survives on trust, and trust survives on visibility.
- Funding: GitHub Sponsors/OpenCollective for build-farm hardware and power; costs are low and fixed (§9.3) precisely because the platform is frozen.

---

## 14. Roadmap

**Phase 0 — Foundations (months 0–3)**
`aslice-toolchain` first: modern Clang/libc++ targeting darwin15, bootstrapped on the newest Intel macOS against the oldest archived SDK, then self-rebuilt. Then the C++ core skeleton: CLI, SQLite state, TUF client, zstd, Mach-O/otool wrappers — plus the build harness in local mode (`aslice build` with the full sandboxed phase pipeline, job/result schemas; BUILD-INFRA.md §12), because the core orchard seed is built *with* it. Bootstrap binary runs on every release 10.11–12 (VM-tested per release, including HFS+). Core orchard seeded with ~30 packages (curl, git, openssl, python, zstd, cmake, ninja) built on real hardware. **Self-update ships in the first usable binary** (§12.12) — retrofitting update mechanisms is how projects die — alongside the project hygiene documents (§13.4).

**Phase 1 — Usable (months 3–6)**
Solver with variants; store/profiles/generations; GHCR distribution; the build harness in both modes — `aslice build` locally and `aslice farm` coordinator/agents on real hardware, one pipeline (BUILD-INFRA.md); minisign slices; ~300-package core orchard, all flavors; `adopt --from-homebrew`; **the freshness pipeline** — `[livecheck]` in every core formula, scheduled orchard autobump opening bump PRs, and `aslice livecheck`/`bump-pr` for humans (PACKAGE-FORMAT §3.15; ORCHARD-POLICY §9); build farm Phase A + first self-hosted nodes. Repository client (`repo add/list`, TOFU key pinning) from the start — the canonical repository *is* the default transport, so the multi-repo machinery costs little extra. The `ca-certificates` slice and the private-bundle half of `aslice ca-update` (§12.10) ship here — every userland TLS fetch depends on them. So do the `apple-roots` slice and `ca-update --crypto` (§12.10): both are ordinary signed content and ordinary upgrades.

**Phase 2 — Differentiated (months 6–12)**
ABI scanner with DWARF diffing; SBOM + `audit`; SLSA provenance; `aslice-toolchain` v2 (LLD-first linking, ccache integration); extended orchard to ~2,000 packages; popular-variant prebuilds chosen from community requests (§9.4); reproducible builds for core; vendor-binary packages (`type = "binary"`, payload extraction, signer pinning) and the Cask importer; `aslice repo build/publish` for third-party repositories; **runtime version management** — the shim layer, `use`/`pin`/`default`, riding tools, and version-bound extension slices with the farm's runtime-epoch build axis (§12.9); the opt-in System-keychain import halves of `aslice ca-update` (`--keychain`, `--apple-certs`, §12.10) and the `[system-patch]` category (§12.11), once `aslice-system` is proven in service and kext duty.

**Phase 3 — Durable (year 2)**
Two-builder reproducibility cross-checks; transparency log; community mirror program; `~/Applications` polish and GUI-app niceties; multi-user daemon if demand materializes; governance formalization.

---

## 15. Risks and Open Questions

| Risk | Severity | Mitigation |
|---|---|---|
| GitHub degrades self-hosted macOS runner support or GHCR terms change | High | Mirror-first index design (§9.1); Buildkite/Forgejo runner portability; static-mirror escape hatch means GHCR is replaceable |
| Apple removes Seatbelt in a future macOS | Low for scope | Target window is 10.11–12 — frozen releases where Seatbelt is present; the policy abstraction isolates the backend regardless |
| Modern Xcode can't target 10.11/10.12 (hosted floor ~10.13) | Medium | Self-hosted toolchain is Phase 0 and authoritative (§4.3); hosted CI is a bonus layer; archived SDKs cached on the farm; SDK use on builders stays within Apple's license on Apple hardware |
| Volunteer burnout (the Homebrew lesson) | High | Frozen platform = fixed workload; automation-first orchard CI; small core orchard with quality bar; explicit scope refusal (no Apple Silicon, no new macOS) |
| Signing-key compromise | Medium | Threshold offline root, YubiKey custody, practiced rotation runbook, transparency log for detection |
| 10.11-era testing hardware scarcity | Medium | VMs cover the full 10.11–12 matrix on the farm; v1 correctness additionally smoke-tested on a real Core 2 Duo when one is obtainable; the frozen platform means test images never churn |
| ABI scanner false negatives (missed breakage) | Medium | Belt and suspenders: compat-version check + symbol fingerprint + reverse-dependency smoke tests in CI; when in doubt, rebuild dependents (we own the build farm) |
| C++ vulnerability in aslice itself | Medium | §5.3 program: subset, hardening, sanitizers, fuzzing, tiny trust-critical helpers |
| Vendor binaries are opaque — no source SBOM, no reproducibility, the binary itself is trusted | Medium | Signer + hash pinning (silent substitution hard-fails); payload-only SBOM with full file list; `audit` binds CVEs via CPE; core tier barred unless redistributable + payload-only (§13.1); users told plainly what is and isn't verified (§10.7) |
| Vendor pulls or mutates a `redistribute = false` artifact | Medium | Hash pin fails loudly rather than installing a different binary; the formula records last-known-good; community can negotiate redistribution or archive a licensed copy |
| A `[system-patch]` replacement breaks software that expected the Apple original | High | Strictest gate in the system (official/local, verified only with an explicit per-repo grant, per-decision consent); lint-time refused-path list blocks catastrophic and platform-binary-library targets; exact backup + byte-verified restore; the §10.7 honesty rules cap what is claimed (§12.11) |
| A macOS update restores or upgrades an Apple file a `[system-patch]` has replaced | Medium | `doctor.systempatch` drift detection with explicit reapply/restore remedies, never silent re-patching; patches resolve through the profile so generation rollbacks re-converge (§12.11) |
| GPL/license compliance for hosted binaries | Low | Corresponding-source archive mirrored per license; SPDX SBOMs make compliance auditable; `redistribute = false` exists precisely for software we may not rehost |
| Community adoption never materializes | Existential | Scope stays hobbyist-sustainable by design; worst case, the core orchard remains a maintained artifact for the installed base |

**Open questions for early reviewers:**

1. ~~Default prefix~~ — **resolved (v1.8): `/opt/aslice` by default, `~/.aslice` as the no-admin fallback.** The installer prefers the shared prefix; when it cannot create it, it offers a fully supported per-user install under `~/.aslice` with identical semantics (§8.1, §10.3) — two documented layouts, not an arbitrary-prefix free-for-all. The name itself is settled: **aslice**.
2. ~~Starlark vs. a stricter pure-TOML-with-templates build DSL~~ — **resolved (v1.8): Starlark stays.** Real legacy codebases need real conditionals and loops; the hermetic subset (no network, no filesystem outside the sandbox) carries the safety story, and escape hatches in a template language would be worse than a real one.
3. ~~Whether `abi = false` user-flag builds should share store paths with farm builds~~ — **resolved (v1.8): shared, with provenance in the DB.** Identical identity gets one store address; the state DB records whether each installed path came from a farm slice or a local build, and `info`/`audit`/`doctor` surface it (§5.2).
4. ~~Telemetry~~ — **resolved (v0.3, sharpened v0.4): aslice collects no telemetry or analytics of any kind, ever.** No install IDs, no opt-in counters, no phone-home, no crash reporting — and no download-count-driven prioritization either, because volume mismeasures value on a platform where the rarest dependency may be the most irreplaceable (§9.4). The project is infrastructure, not a product, and its users — many on air-gapped audio rigs and lab machines — owe it no data. This is a charter-level commitment, not a tunable.
5. ~~Whether the project's canonical repository should host *any* `redistribute = false` formulae in core~~ — **resolved (v1.8): the current allowance stands.** The canonical orchard hosts pointer-only formulae; core tier continues to require `redistribute = true` (§13.1, ORCHARD-POLICY §12) — core never depends on a vendor's server being up.
6. ~~Whether `verified` repositories should install binaries immediately at enable time~~ — **resolved (v1.8): enable implies binaries.** The countersignature ceremony — key pinning, the trust prompt — is the consent; a second click is ceremony without security content (REPOSITORIES.md §9).
7. ~~Whether the `system` capability (§12.7) should ride on the `verified` trust level or be a separate per-repo grant~~ — **resolved (v1.8): it rides on `verified`.** The countersignature vets the maintainers, and the §12.7 flow — per-decision warnings, no "always allow" — is where the ceremony lives. (Contrast #10, one severity level higher, where the answer went the other way.)
8. ~~Service health-check failure behavior~~ — **resolved (v1.4): ask the user.** A failed post-upgrade health check (§12.8, step 5) prompts interactively to roll the generation back and restart the previous version; the default is stay-and-inspect, non-interactive runs fail loudly without rolling back, and `--rollback-on-service-failure` is the explicit unattended path. Silent automatic rollback was rejected: it can mask a good new version behind a transient port conflict, and a package manager that destroys evidence of a failure is harder to trust than one that asks.
9. ~~Project-local dependency directories~~ — **resolved (v1.8): out of scope, permanently.** `.venv`, `vendor/`, `node_modules` remain the ecosystem tools' job; the shim layer binds runtimes and their extensions and stops there. Reimplementing pip/poetry/composer is a non-goal — and the thin convenience layer is how the creep would start.
10. ~~Whether `verified` repositories should ever serve `[system-patch]` packages~~ — **resolved (v1.8): yes, under an explicit per-repo grant.** `aslice repo allow-system-patch <name>` — refused by default, recorded in the state DB, revocable — is the ceremony that *is* security at this severity: the countersignature vets the repo's maintainers, and the grant names the machine owner's additional trust in writing. The DESIGN §12.11 consent flow is unchanged and applies whoever serves the package; third-party repositories remain barred entirely (REPOSITORIES.md §3, ORCHARD-POLICY §13).

---

## 16. References

- TUF (The Update Framework) specification — theupdateframework.io
- minisign — jedisct1/minisign
- Starlark language spec — bazel.build/rules/language
- Nix/OS store and generation model — nixos.org
- x86-64 microarchitecture levels — glibc hwcaps, RFC x86-64-psABI
- Homebrew architecture and history — docs.brew.sh, HOMEBREW-REVIEW.md
- Apple: Seatbelt sandbox profiles (sandbox-exec), System Integrity Protection, PackageKit payload format, Security framework keychain APIs, launchd.plist(5)
- REPOSITORIES.md — multi-repository architecture, mirrors, vendor .pkg/.dmg support
- PACKAGE-FORMAT.md — the slice format specification
- ORCHARD-POLICY.md — governance and acceptance policy
- BUILD-INFRA.md — build farm architecture

---

## Change log

- **v1.8** — Lands the HOMEBREW-REVIEW v0.9/v0.10 items that were specified but missing: §5.2 self-updater component + DB provenance fields (`on_request`, farm-vs-local); §8.4 on-request tracking, stale-dependency GC, and `aslice clean` cache eviction; §12.1 twelve-day-two commands (`self-update`, `outdated`, `reinstall`, pin/unpin, `clean`, `livecheck`, `test`, `create`, `bump-pr`, `exec`, `shellenv`, `store verify`); new §12.12 "Self-update: aslice is package zero" (generation swap, re-exec, health check with automatic rollback, channels/pins, notarization+minisign bootstrap); §12.11 trust paragraph rewritten for the verified-with-grant system-patch path; §13.1 framework allowlist bullet (codifies the `uses_from_macos` rejection) and system-patch grant wording; §13.4 five-check merge gate and Phase 0 hygiene documents (SECURITY.md, CoC, CONTRIBUTING, key runbook); §14 Phase 0 self-update + Phase 1 freshness pipeline. **All 8 remaining open questions resolved (§15):** #1 `/opt/aslice` with `~/.aslice` no-admin fallback (§8.1, §10.3, §2 table); #2 Starlark stays; #3 `abi=false` local builds share store paths with DB-recorded provenance (§5.2); #5 canonical orchard keeps pointer-only formulae, core still requires `redistribute = true`; #6 enable implies binaries for verified repos; #7 `system` capability rides on `verified`; #9 project-local dep directories permanently out of scope; #10 verified repos may serve `[system-patch]` under explicit per-repo grant (`aslice repo allow-system-patch`, §12.11; REPOSITORIES v0.7 §3; ORCHARD-POLICY v0.6 §13). §15 risk row gate wording corrected to match #10.
- **v1.7** — `[system-patch]` category (§12.11): declared, per-file system replacement with byte-exact backup, symlink replacement, offered rollback, drift detection; §13.1 rewritten from an absolute "never touch system files" to rejected-by-default with the flagged exception; risk rows added (§15); open question #10 added. CA/crypto amendment (§12.10): `ca-update` grows `--crypto` and `--apple-certs`; System-keychain import confirmed as the keychain layer; trust sources configurable with Mozilla default.
- **v1.6** — Kext/SIP-sensitive software support (§12.7) with declared categories, double consent, aslice-system mediation, and ask-the-user rollback; services/launchd (§12.8) with generation-aware restarts and health checks (open question #8 added, resolved v1.4 of POLICY — wait, #8 resolved in v1.8? No: #8 resolved in v1.4 per §15); runtime version management (§12.9).
- **v1.5** — Runtime version management design (§12.9): coinstallable runtimes, shim layer, version-bound extension slices.
- **v1.4** — Service health-check failure behavior resolved (#8): ask the user, default stay-and-inspect, `--rollback-on-service-failure` for unattended.
- **v1.3** — CA certificate strategy (§12.10): three layers (userland bundle, opt-in System-keychain import, crypto refresh); trust-source configurability.
- **v1.2** — Coexistence and migration from Homebrew (§13.3); vendor binary packages (§12.5, cross-ref REPOSITORIES.md §6); 32-bit installer payload support on capable OS releases.
- **v1.1** — CPU flavors (§4.2); hermeticity enforcement (§6.4); ABI tracking and rebuild cascades (§7.5); freshness pipeline (§9.5).
- **v1.0** — Initial design: mission, principles, architecture, frozen-platform advantage, core components, formulae, solver, store/generations, farm requirements, security/trust, UX.
