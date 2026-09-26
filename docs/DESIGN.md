# aslice — A Package Manager for Intel macOS

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

**Name.** *aslice* — an apple slice: a nod to the Macintosh apple and to the shape of the project itself. Binary packages are **slices**; formula repositories are **orchards**; the manager picks slices off the orchard, prebuilt or baked to order. The vocabulary is kept distinct from Homebrew's beer terminology to avoid community confusion and trademark friction. The project name is styled lowercase everywhere, including sentence starts — like the command.

- **Status:** Design draft, v1.33 — September 2026
- **Scope:** macOS 10.11 (El Capitan) through 12 (Monterey), Intel x86_64 only
- **Implementation:** C++20 core, single self-contained binary
- **Audience:** Maintainers, founding contributors, and early reviewers
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md) — project terms, acronyms, and the Homebrew translation table.

---

Navigation: [1. Context and Opportunity](#context-and-opportunity) · [2. Goals and Non-Goals](#goals-and-non-goals) · [3. Design decisions](#design-decisions) · [4. Platform Matrix and Microarchitecture Strategy](#platform-matrix-and-microarchitecture-strategy) · [5. Core Architecture](#core-architecture) · [6. Package Format](#package-format) · [7. The Variant and ABI Model — Interoperability by Design](#the-variant-and-abi-model--interoperability-by-design) · [8. Store, Profiles, and Generations](#store-profiles-and-generations) · [9. Distribution and the Build Farm](#distribution-and-the-build-farm) · [10. Security Model](#security-model) · [11. Performance Model](#performance-model) · [12. CLI and User Experience](#cli-and-user-experience) · [13. Policies, Governance, and Migration](#policies-governance-and-migration) · [14. Roadmap](#roadmap) · [15. Risks and Open Questions](#risks-and-open-questions) · [Appendix A. Specification status](#appendix-a-specification-status) · [Appendix B. References](#appendix-b-references)

<a id="context-and-opportunity"></a>

## 1. Context and Opportunity

<a id="the-gap-that-is-opening"></a>

### 1.1 The gap that is opening

The Intel-Mac package-management ecosystem is losing its maintainer on a known schedule:

- **Homebrew 7.0.0 (September 2026)** moved Intel x86_64 to Tier 3 ("not supported"): no new bottles are built for Intel, CI coverage is gone, and macOS 10.15 support was removed outright. Existing bottles stay hosted but freeze in time.
- **September 2027:** Homebrew plans to remove the ability to run on Intel systems at all.
- **GitHub Actions:** the `macos-13` Intel runner image was retired in December 2025; its replacement `macos-15-intel` is the last hosted Intel label, scheduled for retirement in fall 2027 according to the [GitHub announcement](refs/GITHUB_INTEL_RUNNER_RETIREMENT.MD). Owned runners remain a separate option.
- **Apple:** macOS 26 Tahoe is the final release for Intel Macs; macOS 27 Golden Gate is Apple-silicon-only. Intel Macs receive security updates only, on a countdown.

A large installed base remains: Homebrew's own analytics, discussed publicly in mid-2026, put Intel at roughly a quarter of active Homebrew Mac installations. Everything from El Capitan to Monterey is now outside Homebrew's support window — and precisely where these machines are stranded.

<a id="who-the-users-are"></a>

### 1.2 Who the users are

Three populations, all underserved:

1. **Owners of 2012–2020 Intel Macs** used as daily drivers, home servers, audio rigs, and build machines. Many are maxed-out machines (Mac Pro 2013, iMac 5K, 16" MBP 2019) that remain genuinely capable.
2. **CI and legacy-maintenance shops** that must keep building and testing x86_64 macOS software through Tahoe's support window.
3. **Retro, audio, lab, and 32-bit-dependent environments** pinned to older releases. Catalina dropped 32-bit app support entirely; 10.11–10.14 are the last releases that run 32-bit software, classic audio drivers, and legacy pro tools — which is exactly why their users stay. Vendor-binary packages (§12.4) meet them where they live: 32-bit and universal pkg/dmg payloads install cleanly on precisely these releases.

<a id="project-scope"></a>

### 1.3 Project scope

The project specifies package maintenance for Intel macOS 10.11–12: binary
distribution, local build choices, explicit artifact bindings, and recoverable managed
state. Support is established per platform configuration by implementation tests and
recovery drills. Coexistence and migration are described in §13.3.

<a id="design-thesis"></a>

### 1.4 Design thesis

> **Target a fixed OS range, record actual CPU requirements, distinguish compatibility from artifact identity, and validate every execution and recovery boundary.**

Each clause is developed in its own section: the platform axes in §4, the variant model in §7, the security model in §10.

---

<a id="goals-and-non-goals"></a>

## 2. Goals and Non-Goals

<a id="goals"></a>

### 2.1 Goals

- **G1 — Full coverage of macOS 10.11 through 12 on Intel**, treated as first-class citizens, not legacy tiers.
- **G2 — Three µarch flavors:** `v1` (SSE2 baseline — every 64-bit Intel Mac), `v2` (SSE4.2/POPCNT), and `v3` (AVX2 — Haswell and later). See §4.
- **G3 — Precompiled binaries for the common flavors**, hosted on GitHub infrastructure with a mirror-friendly fallback. Default install path is binary and near-instant.
- **G4 — User-selectable build flags and feature variants** with local compilation — *without* forfeiting interoperability with prebuilt packages (§7).
- **G5 — Explicit trust and execution boundaries** (§10): declarative package definitions, sandboxed builds, authenticated artifacts, payload-only binary installation by default, and separately authorized protected operations.
- **G6 — Measured performance targets** (§11): sub-10 ms CLI startup, efficient solving and parallel downloads, zstd payloads, APFS-aware linking. These targets remain unmeasured.
- **G7 — Atomic, rollback-capable installations** via generations (§8).
- **G8 — Low maintainer burden.** The platform is frozen by Apple; the design exploits that stability instead of fighting it (§15).
- **G9 — Vendor-binary coverage.** Software that only exists as a `.pkg`/`.dmg` — vendor CLIs, commercial audio tools, frozen apps — installs through the same store, generations, and lock files as everything else: payload-only by default, and through declared, approved, monitored grafts when its installer scripts are genuinely required (§12.4, §12.15).
- **G10 — First-class multi-version runtimes.** php, nodejs, ruby, and python — and anything else users keep in several versions — install side by side and switch with Volta-grade ergonomics: session, project, and default selection via a shim layer, with extensions bound to exactly one runtime version (§12.9).

<a id="non-goals"></a>

### 2.2 Non-goals

- **N1 — Apple Silicon.** Not now, not by accident. The architecture must not preclude it, but no engineering effort goes to it.
- **N2 — macOS 13+ on Intel.** Tahoe-era Intel machines (2019–2020) are welcome, but the build targets remain 10.11–12; Ventura+ Intel gets whatever falls out naturally.
- **N3 — GUI application *polish* at launch.** Vendor-binary packages (§12.4) cover `.pkg`/`.dmg`-only software — CLI tools and apps alike. What is deferred is app-specific chrome: Launchpad integration, updater handoff, a GUI manager. Core CLI packages still come first.
- **N4 — Linux/Windows.** The codebase should stay portable, but no effort is spent there.
- **N5 — Replacing the system.** aslice lives in its own prefix and never modifies the OS by default: `/System`, `/usr`, and Apple's binaries are read-only to it. The exceptions are few, declared, flagged, consent-gated, and reversible: the `[system-patch]` category (§12.11) — protected originals and execution closures with journaled restoration, trust-gated — because on a frozen platform some fixes are only possible in Apple's territory; declarative setup's system-preference writes and `/etc/shells` enrollment (§12.13), which run through the same helper, record their pre-change values, and roll back with their generation; and approved grafts' declared writes (§12.15), which run sandboxed against their behavior manifest and are captured for generation rollback. `/usr/local`'s ownership is never touched regardless.
- **N6 — 32-bit *builds*.** Every Mac that can run 10.11 is 64-bit capable, so aslice *builds* x86_64-only slices: no i386 flavor, no 32-bit toolchain work, no multilib. **32-bit vendor payloads are a different matter** (v0.6): a pkg/dmg shipping i386 or universal binaries installs on the releases that can still execute them — 10.11 through 10.14, which is exactly why many of these machines are kept at all (§12.4). The line is compile vs. distribute: we never *build* 32-bit, we gladly *install* it where the OS allows.
- **N7 — Metrics.** No telemetry, analytics, install IDs, crash reporting, or usage instrumentation of any kind — not even opt-in. aslice is infrastructure, not a product. Prioritization signals come from maintainers and the community, never from users' machines (§9.4).

---

<a id="design-decisions"></a>

## 3. Design decisions

aslice targets a fixed range of Intel macOS releases. Its specifications make the following choices; implementation and platform acceptance remain required.

| Concern | Mechanism |
|---|---|
| Package execution | Declarative TOML and sandboxed Starlark builds; binary installation is payload-only unless an explicitly approved graft is declared (§6; §12.15) |
| Build choices | Compatibility keys select candidates; exact artifact identities bind bytes, flags, dependencies, and execution requirements (§7) |
| Installed state | Immutable artifacts and generations, with journaled recovery for pointers and external effects (§8) |
| Ownership | A private user-owned prefix; privileged execution uses independently verified protected closures and an authorized helper (§10.4) |
| Distribution | A C++ client, authenticated indexes, and a self-hosted Intel build farm (§9; §11) |
| Privacy | No telemetry or analytics of any kind, ever (§2.2 N7) |
| Vendor software | Declared payload extraction, signer verification, and restricted graft execution where required (§12.4; §12.15) |
| Runtimes | Session/project/default selection with exact artifact bindings and validated extension compatibility (§12.9) |

---

<a id="platform-matrix-and-microarchitecture-strategy"></a>

## 4. Platform Matrix and Microarchitecture Strategy

<a id="the-os-axis-collapses--at-1011"></a>

### 4.1 The OS axis collapses — at 10.11

Seven OS releases and three flavors give 21 potential OS/flavor combinations. Deployment targeting can reduce build count, but each supported combination still needs runtime validation:

macOS has a mature deployment-target mechanism. The deployment target permits a binary to load on older releases; it does not prove runtime correctness. Newer APIs need availability handling, and each supported release needs tests. So the default remains: **build once against the oldest target, per µarch flavor** — the floor is 10.11 now instead of 10.15.

The lower floor has real consequences; each is handled explicitly:

- **A wider `min_os` spread.** Many modern upstreams cannot cleanly target 10.11: C++17/20 library features, `clock_gettime` and friends (absent before 10.12), `thread_local` quirks, modern IPC. Formulae declare `min_os`; the index filters per OS. Expect a natural stratification — the core orchard mostly at a 10.11 floor, much of the extended orchard at 10.12–10.14 floors. A package that *could* build for 10.11 but isn't worth the patching declares its floor and moves on.
- **libc++ comes from the toolchain, not the system.** System libc++ on 10.11 predates half of C++17. All C++ packages statically link a modern libc++ from `aslice-toolchain` (§4.3), so the age of the system runtime stops mattering.
- **HFS+ is back in the window.** 10.11–10.12 predate APFS entirely, and HDDs stayed HFS+ into the Mojave era. Everything filesystem-dependent degrades gracefully: `clonefile` → hardlink → copy (§11), and generation switching relies on `rename(2)`, which is atomic on HFS+ as well.
- **Ancient TLS and expired root certificates** make the 10.11–10.13 system trust store nearly unusable for the modern web. `aslice-fetch` links its own TLS stack and CA bundle and verifies against pinned, countersigned hashes regardless — the security model never depended on the system store. But *userland* still does: the curl, git, and python a user runs trust the rotting system roots, and so do Safari and Mail. `aslice ca-update` (§12.10) heals both halves — a signed, generation-managed CA bundle for the profile, and an opt-in System-keychain import for the machine — with `--crypto` covering the cipher/TLS stack of userland and `--apple-certs` the Apple-private roots that Software Update and the App Store chain to.

<a id="the-µarch-axis-grows-three-flavors"></a>

### 4.2 The µarch axis grows: three flavors

Extending the floor to 10.11 pulls pre-SSE4 CPUs into the supported population, so the flavor space grows from two to three. aslice adopts the x86-64 psABI microarchitecture levels as its flavor vocabulary:

| Flavor | Level | Key ISA | Who needs it |
|---|---|---|---|
| `v1` | x86-64 baseline | SSE2 | Runs on every 64-bit Intel Mac; the *only* choice for Core 2 Duo machines (2007–2009, Merom/Penryn) found on 10.11–10.13 |
| `v2` | x86-64-v2 | SSE4.2, POPCNT | Nehalem/Westmere and later — Mac Pro 2009+, most 2010+ Macs, and everything Catalina-capable |
| `v3` | x86-64-v3 | AVX2, BMI2, FMA | Haswell+ (2014→); 10–40% faster on codecs, crypto, compression, math |

Notes:

- **There is no x86-64-v4 (AVX-512) flavor.** No Intel Mac ever shipped AVX-512; the flavor space stays at three, which keeps the binary matrix and the UX small.
- **Detection** checks every cumulative feature in the [archived psABI level table](refs/X86_64_MICROARCHITECTURE_LEVELS.MD), including the OS-enabled register state required for AVX. An AVX2 or SSE4.2 flag alone is insufficient. The manager itself is built `v1` (it gains nothing from vector ISAs) and selects flavors on the user's behalf; `aslice config set flavor v1` overrides downward.
- **The solver picks the highest flavor the hardware runs** and treats flavor as a hard constraint, not a preference — a `v3` slice on a Core 2 Duo is a solve-time conflict with a clear message, never a SIGILL at runtime.
- Flavor interaction with `min_os` is orthogonal: a Haswell iMac happily runs 10.11, so `v3` + `min_os 10.11` is a real, served combination.

<a id="toolchain-floor--self-hosted-from-day-one"></a>

### 4.3 Toolchain floor — self-hosted from day one

*The authoritative toolchain document is [TOOLCHAIN.md](TOOLCHAIN.md); this section is the rationale in brief.*

Extending to 10.11 changes the toolchain story from "convenience" to "load-bearing":

- **Modern hosted Xcode can't reach 10.11.** Xcode 15-era toolchains no longer accept deployment targets below ~10.13, and GitHub's hosted Intel runners never ship anything older. Therefore `aslice-toolchain` — modern Clang, LLD where viable (ld64 from cctools-port otherwise), modern libc++, CMake, Ninja, pkgconf — moves from Phase 2 to **Phase 0** and is the authoritative build toolchain for all packages.
- **Targeting darwin15 from a modern Clang works** (`-mmacosx-version-min=10.11` is still accepted; Clang's target floor is far older than libc++'s). The constraint is the C++ runtime, which is why the toolchain statically links its own libc++ into everything it produces.
- **The package manager core** is C++20 built with this self-hosted toolchain: static libc++ and third-party libraries, dynamically linking only `libSystem`. One Mach-O binary runs on 10.11–12 with zero runtime dependencies. (Fully static linking is impossible on macOS — `libSystem` must be dynamic — but nothing else need be.)
- **Bootstrap path:** use the owned 2013 Mac Pro with Monterey as the proposed baseline, subject to validation of host Clang, CLT, archived SDK, and selected toolchain sources; then rebuild the toolchain with itself. Record exact versions and per-OS workarounds in the manifest ([TOOLCHAIN §10](TOOLCHAIN.md#genesis)). The target test matrix is 10.11/10.12/10.13/10.14/10.15/11/12, run in batches on capable guests (§9.3). Bring-up must establish compatibility; unavailable required coverage remains pending.

---

<a id="core-architecture"></a>

## 5. Core Architecture

<a id="process-layout"></a>

### 5.1 Process layout

```sh
aslice (single binary, unprivileged)
 ├── aslice-fetch     ── sandboxed helper: network + disk cache only
 ├── aslice-extract   ── sandboxed helper: archive extraction only
 ├── aslice-build     ── sandboxed helper: runs Starlark build scripts
 └── aslice-link      ── the only component that writes the store/profile
```

Privilege separation is structural: the helpers are separate executables (spawned by the main binary, which re-executes itself with a subcommand) running under Seatbelt profiles (§10.5) with only the capabilities their phase requires. The fetch helper can't touch the store; the extractor has no network; the linker has no network and no compiler. Each helper is small (a few hundred lines) and independently auditable — this is where the C++ attack-surface discipline pays for itself. `aslice-extract` is also the component that expands vendor `.pkg` (xar) and `.dmg` payloads (§12.4) — archive and installer-payload handling are the same trust problem and get the same tiny, fuzzed code path. The same helpers are what the build farm executes: the farm harness is an orchestrator that spawns `aslice build` jobs, and every build — farm or laptop — runs through this identical sandboxed executor (full design: [BUILD-INFRA.md](BUILD-INFRA.md)).

<a id="major-components"></a>

### 5.2 Major components

| Component | Responsibility | Notes |
|---|---|---|
| **Index client** | Fetches and caches the package index | TUF metadata + zstd-compressed JSON snapshots; incremental updates via snapshot diffs, not git |
| **Solver** | Version + variant resolution | PubGrub-style CDCL algorithm over (name, version, variant) space; flavors as hard constraints (§7.5) |
| **Store** | Content- and identity-addressed package trees | `/opt/aslice/store/<artifact-hex>/` (§8) |
| **Profiles / generations** | Atomic merged views | Symlink forests with rename-swap; pointer switching plus journaled recovery (§8.3) |
| **Builder** | Fetch→unpack→patch→configure→build→install in sandbox | Deterministic environment; DESTDIR staging; ABI scan on output (§7.3) |
| **Verifier** | Signature, hash, ABI, and policy checks before linking | Nothing reaches the profile without passing (§10.2) |
| **Database** | Separate owner projections and disposable cache | [DATABASE](DATABASE.md) specifies six SQLite roles and executable schemas; client state records installed state and durable decisions; `trust/` separately owns security authority and the operation journal coordinates external effects ([STATE-AND-RECOVERY §5](STATE-AND-RECOVERY.md#durable-transactions-and-recovery) and [STATE-AND-RECOVERY §7](STATE-AND-RECOVERY.md#persistent-trust-and-initial-bootstrap)) |
| **Reporter** | SBOM generation, `audit`, provenance display | SPDX SBOM per package; OSV feed integration (§10.6) |
| **Logger** | Structured operation and security-event logging | JSONL on disk under `log/`, human rendering on the terminal; local-only, forever (§12.5) |
| **Shim resolver** | Version selection for multi-version runtimes | Multicall `argv[0]` dispatch; session → project → default resolution; exec-only, no wrapper process (§12.9) |
| **Self-updater** | Updates aslice itself through the package machinery | aslice is package zero: TUF-verified slice, generation swap, supervised activation with retained recovery entry point, automatic rollback on failure (§12.12) |

<a id="why-c--and-what-it-costs"></a>

### 5.3 Why C++ — and what it costs

The user-facing case for C++ is startup time, single-binary deployment across 10.11–12 with no runtime story, direct Mach-O/dyld/Seatbelt API access, and the profiler, sanitizer, and fuzzer tooling the performance work of §11 needs. The cost is memory safety, which is a security-goal liability. aslice treats it as an engineering constraint:

- **Disciplined subset:** no owning raw pointers (RAII everywhere, `std::unique_ptr`/`shared_ptr` at boundaries), bounds-checked views (`std::span`, `string_view` with explicit lifetime rules), no C arrays, no `str*`/`mem*` libc string calls, exceptions banned across module boundaries.
- **Hardened build:** `-fstack-protector-strong -fstack-clash-protection -D_FORTIFY_SOURCE=2` (via libc++ equivalents), full RELRO-analog (`-Wl,-bind_at_load` where tolerable), PIE, CFI under LTO (`-fsanitize=cfi`) for release builds once lld/ld64 support is verified per-OS.
- **CI sanitizers:** every PR runs the test suite under ASan+UBSan on both flavors; parsers and the archive extractor are continuously fuzzed with libFuzzer — formula parsing, manifest parsing, tar/zip/**xar**/cpio extraction, and the index parser are all *untrusted-input surfaces* and are treated accordingly.
- **The trust-critical helpers are tiny.** fetch/extract/link together are the only code paths that touch hostile data with ambient authority, and each is kept small enough to review line-by-line.

---

<a id="package-format"></a>

## 6. Package Format

<a id="formulae-are-data-with-a-hermetic-build-script"></a>

### 6.1 Formulae are data, with a hermetic build script

*The authoritative schema is [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md); this section is the guided tour.*

An aslice package is a directory in an orchard — a git repo of formula directories (what Homebrew calls a *tap*):

```text
orchards/core/ffmpeg/
 ├── package.toml      # metadata, sources, dependencies, variants
 ├── build.star        # Starlark build script (sandboxed, no IO escape)
 ├── patches/          # optional, checksummed
 └── tests.star        # optional smoke tests
```

`package.toml`:

This excerpt illustrates recipe structure; abbreviated hashes and omitted policy fields must be completed and validated before publication.

```toml
spec = 1

[package]
name        = "ffmpeg"
version     = "7.1.0"
revision    = 0
license     = "LGPL-2.1-or-later"
description = "Play, record, convert, and stream audio and video"
homepage    = "https://ffmpeg.org"

[[source]]
url    = "https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz"
sha256 = "<verified-source-sha256>"
# mirrors = ["https://mirror.example/..."]   # optional fallback mirrors

[variants.x265]          # feature variant
default = true
abi     = true           # changes exported interface → part of build identity (§7)
description = "HEVC encoding via x265"

[variants.debug]
default = false
abi     = false          # ABI-neutral choice; artifact identity still records output
description = "Build with debug symbols"

[depends]
runtime = ["x264", "x265?variant.x265", "lame", "opus", "srt"]
build   = ["nasm", "pkgconf"]
```

`build.star` (Starlark: deterministic, no network, no filesystem access outside the build dir, no `eval`):

```python
def configure(ctx):
    args = [
        "--prefix=" + ctx.prefix,
        "--enable-gpl",
        "--enable-libx264",
    ]
    if ctx.variant("x265"):
        args.append("--enable-libx265")
    ctx.env.append("CFLAGS", ctx.user_cflags)   # user flags honored, recorded, non-ABI (§7.4)
    ctx.run("./configure", *args)

def build(ctx):
    ctx.make(jobs = ctx.jobs)

def install(ctx):
    ctx.make("install", destdir = ctx.staging)
```

Key properties:

- **No Turing-complete host code at install time.** Starlark executes only during *builds*, inside the sandbox, with capabilities enumerated in `ctx`. There is no `post_install` hook that runs on the user's machine — post-install behavior (creating data dirs, registering launch agents) is expressed declaratively in `package.toml` and executed by aslice itself.
- **Everything is pinned.** Source URLs carry hashes; patches are checksummed files; the index records the full closure.
- **Variants are declared, typed, and ABI-tagged** by the package author — the foundation of the interop model in §7.
- **Vendor binaries are the same format, minus the build.** `type = "binary"` packages describe a `.pkg`/`.dmg` artifact with per-OS tags, a pinned signer, and a declarative payload map — no `build.star`, and vendor scripts only as declared, approved grafts (§12.4, §12.15; [PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software)).

<a id="binary-package-format-slice"></a>

### 6.2 Binary package format (`.slice`)

A binary package — a **slice** — is one Zstandard frame containing a POSIX pax tar archive:

```text
ffmpeg-7.1-0+core.v3.2f4a9c1e.slice
 ├── slice.json        # container version, manifest digest/length, payload totals
 ├── manifest.json     # identity, ABI contract, file hashes, dependency bindings
 └── payload/          # normalized file tree
```

The [slice format specification](SLICE-FORMAT.md) defines byte layout, normalization, limits, and extraction checks. Its [container schematic](../schematics/json/slice.schema.json) and [artifact manifest schematic](../schematics/json/artifact-manifest.schema.json) define the JSON structures. Package signatures, SBOMs, and provenance are separate authenticated objects bound to the archive or artifact digest.

Installation authenticates metadata, the complete archive digest, and its detached signature before bounded extraction into staging. It checks the manifest and payload hashes, applies declared relocations, verifies ABI requirements, and activates the artifact through the transaction journal. Approved grafts run in an isolated staged view (§12.15). A repackaged vendor binary uses the same container; its authenticated provenance records the vendor digest and signer, while its recipe binds the repackaging procedure.

---

<a id="the-variant-and-abi-model--interoperability-by-design"></a>

## 7. The Variant and ABI Model — Interoperability by Design

Compatibility and artifact identity answer different questions. The compatibility key describes the declared ABI and platform contract; the artifact identity binds the resulting bytes and exact dependencies. Substitution requires evidence beyond key equality.

<a id="the-three-kinds-of-build-time-choice"></a>

### 7.1 The three kinds of build-time choice

| Kind | Examples | Effect on identity | Effect on interop |
|---|---|---|---|
| **µarch flavor** | `v1` / `v2` / `v3` | Hard selection constraint | ABI-identical; a higher-flavor binary won't *run* on lesser hardware |
| **Optimization flags** | `-O2`/`-O3`, `-march=native`, LTO | Same compatibility key only when ABI-neutral; distinct artifact identity | Actual CPU requirements and ABI evidence are checked |
| **Feature variants** | `+x265`, `+ssl` vs `+gnutls`, `+shared` | Compatibility key changes when `abi = true`; artifact identity binds every output | Changes exported interface → tracked in the ABI contract |

<a id="build-identity"></a>

### 7.2 Build identity

`build_id` is the full lowercase hexadecimal SHA-256 compatibility key defined in [STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#1-compatibility-and-artifact-identity). It includes repository identity, package version/epoch/revision, ABI variants, runtime ABI epoch, flavor, minimum OS, and toolchain identity. Vendor identities bind the vendor digest and set compiler/flavor fields to null.

Optimization choices may share a compatibility key, but byte-distinct outputs have distinct `artifact_id` values and immutable store addresses. Exact flags, dependency bindings, recipe digest, and actual CPU requirements are recorded in the artifact manifest. Equality of compatibility keys selects candidates; the ABI and CPU checks still decide whether substitution is allowed. Locks and generations select exact artifacts, never merely a compatibility key.

<a id="the-abi-contract-the-mach-o-insight"></a>

### 7.3 The ABI contract (the Mach-O insight)

The ABI scanner records each dylib's install name, current and compatibility versions, exported symbols, client symbol requirements, architecture, and evidence quality. The loader-version comparison is provider `current_version >= client required compatibility version`; a symbol hash establishes equality, not subset coverage. [STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#2-abi-and-execution-requirements) defines the comparison and its limits.

Exact dependency artifact bindings are the safe default. Automatic substitution requires adequate evidence plus dependent tests; stripped C++ interfaces and undeclared dynamically loaded plugins cannot be declared compatible from symbol names alone. Unknown evidence means retain the original provider or rebuild and test the dependent. Rebinding an absolute install name is an explicit rebuild or verified relocation producing a new artifact, not a profile switch.

This model permits tested combinations of local and prebuilt artifacts without claiming that all ABI or behavioral breakage can be detected before execution.

<a id="user-flags"></a>

### 7.4 User flags

```sh
aslice install ffmpeg --variant +x265 --cflags="-O3 -march=native" --lto
```

- `--cflags`/`--ldflags`/`--lto`/`--debug` → local source build of **that package only**; dependencies still resolve to binaries when their contracts are satisfied. Exact flags are recorded in the artifact manifest. ABI-neutral choices may share a compatibility key (§7.2); distinct outputs retain distinct artifact identities. Unsupported ABI-changing flags require a declared ABI variant or are rejected. Unknown effects require an isolated build and explicit dependency validation. Substitution still checks CPU/OS requirements, ABI evidence, and dependent tests ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)).
- `--variant ±x` where `x` is `abi = true` → new build identity; source build unless a matching slice exists (community orchards may publish popular non-default variants).
- `--variant ±x` where `x` is `abi = false` → local build, same compatibility key, distinct artifact identity when output changes.
- A package tree of user-flag builds is tracked (`aslice leaves --user-built`) and survives upgrades — the solver reuses the recorded flag set when a new version appears.

<a id="the-solver"></a>

### 7.5 The solver

Version and variant resolution uses a PubGrub-style CDCL algorithm:

- **Terms** are (package, version-range, variant-assignment, flavor).
- **Flavor is a hard constraint** injected from hardware detection — a v3 flavor on a v2 machine is a conflict at solve time with a clear message, never a SIGILL at runtime.
- **Operation policy precedes cost.** Authority, platform/ABI compatibility, holds, runtime streams, and explicit requests constrain every solve. Install selects the newest eligible version satisfying the request; upgrade selects the newest eligible update. A cached older binary cannot displace a newer eligible source-only update. Security update selects the newest eligible fixed version; `--security --minimal` selects the lowest eligible fixed versions whose complete dependency solution satisfies the requested advisories. Necessary dependency changes remain included and explained. Exact replay selects only the recorded artifacts and fails if they cannot be obtained or reproduced exactly. Only after these rules are satisfied do local-build count and download size break ties. `--prefer-source` changes that cost preference, not authority or update policy.
- **Compilation requires consent.** Plans disclose each source build, its input identities, dependency path, resource estimates (or unknown estimates), and why no eligible binary is selected. Interactive execution asks before compilation; unattended execution requires `--allow-source-builds`. A saved plan describes work but conveys no consent. Refusal never silently selects an older version.
- **Solver comparison remains pending.** PubGrub remains the specified solver. A libsolv prototype must run identical candidate sets and compare correctness under namespaces, exact bindings, variants, streams, holds, and security/minimal policies; conflict explanations; peak memory; and representative cold/warm solve latency distributions. No algorithm change or performance advantage is established by this specification.
- **Deterministic and explainable:** every resolution emits a human-readable derivation tree (`aslice install --explain ffmpeg` shows why each version/variant was chosen). Solve results are cached in the disposable SQLite cache keyed by complete input digest ([DATABASE](DATABASE.md#4-disposable-client-cache)); typical repeated solves are sub-millisecond.

The prebuilt variant domain per package is small by policy (§13.2: the farm builds defaults plus demonstrated-demand variants, and everything else compiles locally), which bounds farm work while preserving local build choices.

---

<a id="store-profiles-and-generations"></a>

## 8. Store, Profiles, and Generations

<a id="layout"></a>

### 8.1 Layout

```text
/opt/aslice/
 ├── store/
 │    ├── <artifact-hex-a>/                    # ffmpeg v3
 │    ├── <artifact-hex-b>/                    # ffmpeg v2; flavors coexist
 │    ├── <artifact-hex-c>/                    # x264 v3
 │    └── …
 ├── apps/         # vendor-binary .app bundles (§12.4)
 ├── profiles/
 │    ├── default -> generations/42             # symlink; the live view
 │    └── generations/
 │         ├── 41/  { bin/, lib/, share/, … }   # symlink forests into store
 │         └── 42/
 ├── cache/        # slices, sources, index snapshots
 ├── log/          # structured operation logs (§12.5)
 ├── trust/        # authoritative trust records; not reconstructed from SQLite
 ├── records/      # durable choices and compact operation history
 ├── cache/db/cache.sqlite # disposable verified projections and solves
 ├── db/state.sqlite # client state; other owners have separate databases
 └── etc/aslice.toml
```

- **Store paths are immutable.** Each artifact occupies `store/<artifact-hex>/`; distinct local and farm outputs never overwrite one another. Canonical hashes, relocation, and installed-byte receipts follow [STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#compatibility-and-artifact-identity).
- **Install names bind exact dependency artifacts.** Absolute paths and managed rpaths are recorded and traced by GC. Relocation verifies canonical bytes and creates an installed-byte receipt; incompatible prefixes or vendor signatures that relocation would invalidate cause refusal ([STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#compatibility-and-artifact-identity) and [STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)).
- **Per-user installs** (`~/.aslice` as prefix) are the documented no-admin fallback layout (open question #1, resolved v1.8): the installer offers it when `/opt/aslice` cannot be created, farm slices are relocated via the manifest metadata, and everything else — profiles, generations, rollback, logging — is identical. A writable store is scoped to its owner. Sharing across users requires an administrator-owned read-only store and a separate authorized writer; profiles alone do not establish a security boundary.

<a id="profiles-as-the-interoperability-surface"></a>

### 8.2 Profiles as the interoperability surface

A profile is the merged symlink forest (bin/, lib/, share/, …) that users put on PATH: `/opt/aslice/profiles/default/bin`. Linking is nothing but symlink creation into a generation directory, so any combination of store paths — prebuilt, user-compiled, different flavors, old and new versions of different packages — coexists under one view. Collisions (two packages shipping `bin/foo`) are first-class: the profile records priority, and `aslice profile prefer` flips it without touching the store.

<a id="generations-atomic-switching-and-rollback"></a>

### 8.3 Generations: atomic switching and rollback

Package views switch through an atomic symlink rename. Whole-machine changes additionally use the durable journal and recovery state machine in [STATE-AND-RECOVERY §5](STATE-AND-RECOVERY.md#5-durable-transactions-and-recovery): serialize mutations, persist before-images, apply external changes, activate pointers, reconcile SQLite, then commit before bounded service health checks. Effective mutation ownership continues through those checks and survives parent death while helpers still write. A rename alone is not an atomic transaction across these systems.

`aslice rollback [generation]` and `switch-generation` execute journaled transitions to retained managed state. External edits stop inverse writes with a conflict; application databases and user data are outside package rollback. Changed service declarations restore their plists too. Protected-volume changes follow [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md) and may require Recovery and a reboot. Recovery and active transactions retain all required artifacts against GC.

<a id="garbage-collection-discipline"></a>

### 8.4 Garbage collection discipline

Keep the last 5 generations by default. `gc.store_watermark` is the store limit (default 20 GB); `gc.warning_margin_percent` is the warning margin below it (default 10, range 0–100). Warn when usage reaches `limit × (1 - margin / 100)`. At or above the limit, ask `Run garbage collection? [y/N]`; No is the default. Never run GC automatically from the size check. Non-interactive checks print the warning and the `aslice gc` remedy without collecting. Explicit `aslice gc` remains available; `aslice gc --dry-run` shows what would be collected and why. Collection retains every root required by [STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements) and §5; a threshold does not make reachable artifacts collectible.

**Installed-on-request tracking.** Every DB install record carries `on_request = true|false` — whether the user named the package or the solver pulled it in. `aslice autoremove` collects nothing reachable from an `on_request` root, cross-checked against retained generations, and `aslice mark <pkg> --on-request/--as-dependency` repairs the record when the user disagrees with it. Package holds live here too: `aslice pin <pkg>` / `unpin` record the hold in the same table, `upgrade` skips held packages, and `outdated` says so rather than hiding them.

**Cache eviction.** The GC above owns the *store*; the *cache* — downloaded slices, source tarballs, index snapshots, ccache — is owned by `aslice clean`: LRU eviction of anything not referenced by an installed package or retained generation, watermark-driven (default: evict when the cache exceeds 10 GB, never touch anything younger than 30 days), with `--dry-run` symmetry to `gc`. Source tarballs are the sleeper category: `--build-from-source` users accumulate them silently.

<a id="shims-the-multiplexing-layer"></a>

### 8.5 Shims: the multiplexing layer

Profiles have one structural limitation: a name like `bin/php` can point at only one store path per generation. That is correct for libraries — the profile is the interop surface and ambiguity there is a bug — but wrong for **runtimes**, where several versions installed at once is the normal state of a working machine. aslice resolves it with a thin **shim layer** (§12.9): a directory of multicall shims that sits *before* the profile on PATH and multiplexes versioned tools according to session, project, and default selections. Shimmed names are not linked into generations at all; the profile instead links versioned aliases (`bin/php8.4`) for services and scripts that must name an exact runtime. The store, generations, and rollback semantics are untouched — a shim only ever chooses among already-installed store paths; it creates no state the generations don't own.

---

<a id="distribution-and-the-build-farm"></a>

## 9. Distribution and the Build Farm

<a id="hosting-on-github--two-layers-mirror-friendly"></a>

### 9.1 Hosting on GitHub — two layers, mirror-friendly

**Layer 1: Package blobs as OCI artifacts on GHCR.** Slices are pushed to `ghcr.io/aslice/<name>` as OCI artifacts (ORAS), giving content-addressed blob storage, deduplication of byte-identical blobs (a monolithic changed archive does not automatically share content across versions), resumable/ranged downloads, and free bandwidth within GitHub's generous registry limits. Every tag is additionally anchored to a signed manifest digest.

**Layer 2: The index as static, signed files.** The package index (TUF metadata + zstd JSON snapshots) is published both to a GitHub Release asset stream and to `raw`/Pages endpoints, and — critically — is *trivially mirrorable*: any static HTTP server can host a complete aslice repo. Mirror support is a first-class config (`mirrors = [...]`), not an afterthought, because the long-term health of a legacy-platform project cannot depend on one vendor's continued generosity.

**Fallback:** plain GitHub Releases assets (2 GB per asset ceiling — no package comes close) for environments where GHCR auth/rate limits are a problem. The client treats GHCR, Releases, and static mirrors as interchangeable transports for identical, identically-signed content. All three are *transports* for the canonical distribution unit — the **repository tree** (§9.6): a static, signed, mirrorable directory of TUF metadata, index snapshots, formula metadata, and blobs. GHCR is where blobs may live; a repository is what a client consumes.

<a id="the-github-ci-problem"></a>

### 9.2 The GitHub CI problem

GitHub-hosted Intel runners are a deprecating asset: `macos-11`/`macos-12`/`macos-13` images are already retired (the last of them in December 2025), and the replacement `macos-15-intel` label — the final hosted Intel runner — is available only until August 2027. **Any design whose correctness depends on hosted Intel CI is a dead design.** aslice therefore treats GitHub CI as a convenience layer and the self-hosted farm as the system of record.

<a id="the-build-farm"></a>

### 9.3 The build farm

*The harness that runs on this hardware — identical to what runs on a user's machine — is specified in [BUILD-INFRA.md](BUILD-INFRA.md): job manifests, scheduling lanes, the quarantine/signing trust model, community evidence builders, and VM matrix orchestration. This section is the hardware summary.*

**Phase A (launch):** hosted CI supplies optional coverage where its detected CPU and OS capabilities permit. The owned farm below is the system of record. Generating `v3` machine code does not establish that a complete package build succeeds on a weaker CPU: configure probes, generated tools, dependencies, and tests may execute that code during the build. In the owned farm, complete `v3` jobs belong exclusively to the laptop; VMs on the Mac Pro cannot add `v3` execution support.

**Phase B: the two owned Macs**, using the standalone farm harness with an optional self-hosted CI adapter:

| Role | Hardware | Notes |
|---|---|---|
| Primary `v1`/`v2` builder and tester | 2013 Mac Pro (trashcan) | Also coordinator, compatible OS-test VMs, and restricted publisher VM |
| On-demand `v3` builder and tester | 2015 MacBook Pro | Additional `v1`/`v2` builds and independent rebuild checks; compatible `v3` test guests |

No new hardware purchase is required. CPU configuration, RAM, storage, and concurrency remain unspecified until measured. Core 2 Duo testing is optional future coverage outside current inventory. The seven-release OS matrix runs in batches; host/hypervisor/guest compatibility and guest-visible CPU features must be validated before claiming coverage ([BUILD-INFRA §8](BUILD-INFRA.md#the-vm-test-matrix)).

When the laptop is absent, `v3` work queues while eligible `v1`/`v2` work continues. Missing tests and required independent rebuilds remain pending; all merge, signing, and atomic publication gates remain intact. The two Macs can independently cross-check `v1`/`v2`, but supply only one physical `v3` builder ([BUILD-INFRA §7.3](BUILD-INFRA.md#reproducibility-classes)).

The signing host is a dedicated networked release Pi; a separate offline Pi holds the root (§10.2). The Mac Pro's restricted publisher VM automatically delivers authenticated candidates and atomically publishes verified signatures; it holds only the timestamp key among repository signing keys. Build guests have no publication credentials. Shared-host compromise can corrupt evidence and publication and expose the timestamp key, but does not directly expose offline keys. Losing the Mac Pro stops preparation and publication until recovery ([BUILD-INFRA §11](BUILD-INFRA.md#failure-modes-planned)).

<a id="what-gets-prebuilt"></a>

### 9.4 What gets prebuilt

- **Core orchard (~300 packages):** all three flavors where the formula's `min_os` allows (§4.1), default variants — the shell/git/curl/python/openssl/ffmpeg stratum.
- **Extended orchard (~2,000 packages):** all flavors compatible with each formula's `min_os` floor, default variants, built on a rolling cadence.
- **Popular non-default variants and prebuild priorities:** chosen by *value to a stranded platform*, never by volume. Download counts are explicitly rejected as a signal: on a deprecated-OS ecosystem, an obscure library fetched once a month may be irreplaceable — nobody else ships it for these machines — while a popular tool has alternatives everywhere. The prioritization inputs are all knowable without watching a single user:
  - **Dependency centrality** — how much of the orchard's build graph a package unblocks, computed from the graph itself.
  - **Build pain** — farm-measured compile time and patch/failure rate: the hours a prebuilt slice saves each of its users, however few they are.
  - **Irreplaceability** — a maintained package fills a documented gap in software availability for the target platform.
  - **Direct community requests** — orchard issues and request threads, in the open.
- Everything else: source builds, with the ABI contract guaranteeing the result still interops with the prebuilt world.

<a id="build-provenance"></a>

### 9.5 Build provenance

Every slice has a separate authenticated SLSA-style provenance attestation binding its artifact and archive digests: builder identity, source hash, formula commit, toolchain, build environment, and reproducibility evidence. Variable provenance is not part of the canonical identity manifest ([STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#compatibility-and-artifact-identity); [SLICE-FORMAT §2](SLICE-FORMAT.md#content-identity-and-signatures)). `aslice provenance ffmpeg` shows it. Independent rebuild comparisons use the unsigned/normalized evidence contract in [STATE-AND-RECOVERY §10](STATE-AND-RECOVERY.md#acceptance-and-implementation-order); served byte-changing signatures precede final artifact identity. Verified reproducibility evidence supports the `reproducible: true` index badge.

For vendor-binary slices (§12.4) the provenance section instead records: the vendor artifact URL and sha256, the pinned signer identity and notarization state at pack time, the repackaging tool version, and whether the payload is hosted or vendor-fetched.

<a id="the-repository-system"></a>

### 9.6 The repository system

GHCR, Releases, and static mirrors are *transports*. The canonical distribution unit — what a client consumes — is the **aslice repository**: a self-contained, signed, static tree:

```text
repo.example.org/
 ├── tuf/            # root.json, snapshot.json, timestamp.json, targets.json
 ├── index/          # zstd JSON snapshots + diffs (the solver's world)
 ├── formulas/       # resolved package metadata (pure data; never executable)
 └── blobs/sha256/   # slices and vendored sources, content-addressed
```

- **Vendored sources live here too.** The farm deposits every source artifact it ever fetches into `blobs/sha256/` ([BUILD-INFRA §3](BUILD-INFRA.md#the-pipeline-shared-at-both-scales)); a client's fetch order is upstream → formula `mirrors` → the repository's own blob area — all three verified by the same pinned sha256, so the archive is a fallback, never a new trust path. Upstreams disappear; an orchard that vendors its sources does not notice.
- **Anyone can host one.** Any static HTTP server, a GitHub Pages site, a GHCR org (blobs in OCI, index overlaid), or a `file://` directory on a lab NAS. A mirror is a full copy of the tree; clients fail over across a repository's declared mirrors.
- **Repositories carry recipes *and* binaries.** `formulas/` holds the resolved metadata the solver needs (recipes); `blobs/` holds the slices — each tagged in the index with its OS-support bounds (`min_os`/`max_os`), flavor, and arch. A repository may be *binary-only* — repackaged vendor software with no orchard behind it at all (§12.4) — which is how communities serve niche pkg/dmg-only ecosystems (audio plugins, lab instruments) without asking the project for orchard space.
- **Trust is per-repository, with inherent levels.** Every repository has one of four enforced trust levels — `official` (pre-pinned TUF root, initially 1-of-1), `verified` (project-countersigned community repos, shipped disabled), `third-party` (user-added, TOFU), `local` (development trees, formulas only unless signed). Levels are capability sets enforced by the solver and verifier — what namespaces a repo may serve, whether its binaries may install, which privileged effects it may serve — not labels. `aslice repo add <url>` pins the repository's root key fingerprint on first use (TOFU): the fingerprint is displayed with a strong recommendation to verify out-of-band, retained in authoritative trust state; authenticated sequential root rotation proceeds normally, while an unauthenticated replacement blocks updates. The project ships an **official source list** (`sources.toml`, itself a TUF target) with core + extended pre-pinned — the core fingerprint is also compiled into the bootstrap binary — and verified community repos listed for discovery. The project's canonical repository ships pre-pinned in the bootstrap. Full model: [REPOSITORIES.md](REPOSITORIES.md).
- **Namespaces are exact.** Only core has bare names. Every other repository, including extended, requires its registered prefix (`extended:package`, `audiolab:convolver`). There is no overlap prompt, cross-repository fallback, or preference table ([REPOSITORIES §10](REPOSITORIES.md#overlapping-packages-across-repositories)).
- **Authoring → publishing.** `aslice repo build` compiles an orchard (git formulae) — or a bare manifest directory — into a repository tree; `aslice repo sign` applies the keys; `aslice repo publish` pushes to the configured transport. After owner-approved merge and all required gates, the official pipeline automatically delivers an authenticated candidate to the dedicated networked release Pi, verifies returned signatures, and atomically publishes the complete set ([KEY-RUNBOOK §2.1](runbooks/KEY-RUNBOOK.md#automatic-orchard-to-client-publication)). Publication is serialized, retries are idempotent, and stale candidates reconcile before signing again. Clients discover slices during normal metadata refresh for search, install, or upgrade; publication does not force installation. These remain the same authoring commands and client signature formats; the services remain implementation work.

---

Index retrieval, bounded diffs, staged activation, mirror failures, and transaction-scoped repository availability follow [REPOSITORIES](REPOSITORIES.md#authenticated-index-refresh). Cross-namespace virtual providers, aliases, and replacements require retained explicit selection; repository names never transfer authority.

<a id="security-model"></a>

## 10. Security Model

The security design separates recipe execution, artifact authentication, ordinary prefix ownership, and privileged effects. Each boundary has explicit authorization and acceptance requirements.

<a id="declarative-packages-hermetic-builds"></a>

### 10.1 Declarative packages, hermetic builds

- Formula *metadata* is TOML — pure data, validated against a schema, rejected on unknown fields.
- Formula *logic* is Starlark executed in the build sandbox with a capability-only API (`ctx.run`, `ctx.make`, `ctx.env`) — no filesystem access outside the build dir, no network, no subprocess outside the declared toolchain, deterministic by construction.
- **Binary installs are payload-only by default.** There is no undeclared `post_install`. Data-directory creation, launch-agent registration, and shell-completion placement are declarative manifest entries applied by aslice's own code. The same rule binds vendor binaries by default: `.pkg` `preinstall`/`postinstall` scripts and `.dmg` autolaunch mechanics execute only when the formula declares them as grafts — approved by the user, sandboxed to a behavior manifest, and captured for rollback (§12.15); otherwise payload extraction is all that happens (§12.4).

<a id="signatures-and-repository-integrity-tuf"></a>

### 10.2 Signatures and repository integrity (TUF)

- **Metadata:** the index is wrapped in [The Update Framework](refs/THE_UPDATE_FRAMEWORK_SPECIFICATION.MD) — a 1-of-1 root on an offline Pi, distinct targets, snapshot, and slice-signing keys on a dedicated networked release Pi, and the timestamp key on the publisher. Keys are Ed25519; private keys at rest and their offline backups are encrypted. Root metadata lasts one year, targets/snapshot 90 days, and timestamps 48 hours with daily refresh. Renew targets/snapshot automatically below 30 days using the last approved content, without changing keys; alert 30 days before root expiry for deliberate offline renewal. Timestamp refresh cannot extend snapshot or targets expiry ([KEY-RUNBOOK §1.1](runbooks/KEY-RUNBOOK.md#metadata-validity-and-renewal)). This gives rollback, freeze, and mix-and-match attack protection — the failure modes that plain "signed packages" miss.
- **Packages:** every slice is signed — minisign-compatible Ed25519 for official infrastructure, with **OpenPGP (GPG) as a built-in first-class scheme** for third-party repositories and formula-declared upstream source verification (a self-contained verifier linked into aslice; no `gpg` binary, no keyserver dependence, modern algorithms only). The scheme is a property of the repository, the fingerprint is a property of the pin, and both are enforced before content is trusted ([REPOSITORIES §5](REPOSITORIES.md#signing-keys-two-schemes-one-verification-pipeline)). Signature verification happens **before extraction**, and the verified manifest is what the linker consumes.
- **Sources:** every source tarball hash is pinned in the formula *and* countersigned in the index; `fetch` verifies against both. Vendor artifacts are additionally **signer-pinned** (§12.4): a silent change of code-signing identity upstream is a hard failure, not a warning.
- **Key compromise response:** initial users trust the project owner. Offline custody reduces exposure but supplies no independent-party oversight. Backup restoration, rotation, and explicit rebootstrap after root compromise or unrecoverable loss are specified in KEY-RUNBOOK and must be drilled before launch. Multi-party custody can follow through a sequential TUF root update satisfying both old and new thresholds; preserve all intermediate roots.

<a id="trust-bootstrapping"></a>

### 10.3 Trust bootstrapping

Authenticated HTTPS delivers the online installer and its pinned bootstrap inputs. The verified bootstrap binary performs signature verification; an unverified downloaded verifier is never executed. A second transport supplies redundancy, not independent authority.

For TLS-dead machines, transfer a bootstrap kit from a supported machine and verify its SHA-256 using the stock `shasum` against an independently authenticated digest before execution. HTTP is permitted only for subsequent artifacts whose authentic pins are already available. Without an authentic kit or installer, bootstrap stops. [STATE-AND-RECOVERY §7](STATE-AND-RECOVERY.md#7-persistent-trust-and-initial-bootstrap) defines both paths and their acceptance checks.

The installer may use sudo once to create the user-owned `/opt/aslice` prefix, or use `~/.aslice` without elevation. Privileged features subsequently use a separately protected root and explicit authorization (§10.4).

<a id="privilege-discipline"></a>

### 10.4 Privilege discipline

- **No sudo in steady state.** Not for install, not for upgrade, not for uninstall. The prefix is user-owned from creation.
- **Never touches `/usr/local`.** Other package managers retain ownership of their prefixes. Vendor-binary apps install under `/opt/aslice/apps/` — never `/Applications` — with a per-user `~/Applications` symlink as the opt-in convenience (§12.4).
- **No setuid binaries, no helper daemon at launch.** A future multi-user mode (shared lab machines) will use a launchd daemon that accepts only TUF-verified operation plans over a local socket with peer-credential checks — designed, but gated behind demand.
- **One scoped exception: `aslice-system`.** Per-operation elevation imports and activates independently verified root-owned closures under `/Library/Application Support/aslice/system`; root execution, dependencies, configuration, trust, journals, and backups never resolve through the user-owned prefix. All mechanisms pass the same effect-derived capability gates ([STATE-AND-RECOVERY §3](STATE-AND-RECOVERY.md#privileged-ownership-and-capability-checks)).

<a id="sandboxed-builds"></a>

### 10.5 Sandboxed builds

Every build phase runs under a Seatbelt (`sandbox-exec`) profile — Seatbelt predates the entire 10.11–12 window and is present on every supported release:

| Phase | Profile |
|---|---|
| fetch | Network to declared hosts only; write to cache dir only |
| unpack/patch/configure/build | **No network at all**; write only within the build dir; read-only toolchain and store |
| install (to staging) | No network; write to staging dir only |
| test | No network by default; opt-in `test_network = true` per formula, logged at warn |

Farm package-controlled execution uses disposable VMs in addition to these in-guest profiles, including official recipes, PRs, autobumps, and third-party orchards. Credentials remain outside the guest; [BUILD-INFRA](BUILD-INFRA.md#jobs-are-closed-worlds) defines the isolation and cache boundary. Local source builds retain the same input verification and sandbox requirements; farm isolation is not established by a passing schema.

Vendor-binary payload extraction (`xar` expansion, `hdiutil` attach, cpio unpack) runs under the unpack profile — no network, writes confined to staging. The one phase in which a vendor artifact gets to run anything is the approved graft, which executes under its own manifest-derived profile (§12.15).

Seatbelt is deprecated by Apple on newer releases but frozen-in-place across our entire (frozen) target window; the profile abstraction (`SandboxPolicy` compiled to Seatbelt today) is designed so a future backend can replace it without touching formulae. A build that escapes its profile fails the build and files an automatic audit event.

<a id="vulnerability-and-sbom-pipeline"></a>

### 10.6 Vulnerability and SBOM pipeline

- Every slice has a separate authenticated **SPDX SBOM**, bound to its artifact and archive digests, generated from the build manifest (sources, patches, dependency closure, toolchain). Vendor-binary slices have a payload-only SBOM (file list, hashes, signer) — less deep than a source SBOM, still enough for `audit` to bind CVEs via CPE.
- `aslice audit` evaluates the active exact dependency closures and embedded components against TUF-authorized orchard advisories. Upstream OSV/GitHub feeds supply assessment evidence, not repository authority or proof that an orchard backport is missing. Retained vulnerable generations are reported separately from active ones. Missing component inventories, absent advisories, expired metadata, and incomplete coverage produce `unknown`, never an inference of safety.
- Advisory records bind repository identity/environment, advisory and CVE identifiers, affected/fixed package revisions and artifact identities, OS/flavor applicability, evidence, and remediation. Freshness requires both current TUF authorization and an unexpired assessment. Vulnerability status (`vulnerable`, `fixed`, `not-affected`, `unknown`) is separate from remediation (`fix-available`, `held`, `unavailable`). A backport can mark an older revision fixed with evidence; upstream version ordering alone cannot. Cross-orchard consumers retain their own authority and remain visibly affected when no authorized rebuild exists.
- `aslice upgrade --security` selects fixes for applicable advisories; `--minimal` is valid only with `--security` and chooses the lowest eligible fixed solution. Every held, unavailable, unknown, or otherwise blocked advisory remains in the result with its reason and dependency path. Exit 3 (`incomplete-remediation`) means unresolved findings remain even if some fixes committed. Exit 2 is consent/trust refusal, 1 is execution/invocation error, and 0 requires complete requested remediation and verification. No changes does not imply security success.
- `aslice needs-restarting [--json]` inspects visible processes and exact mapped artifacts after updates. It reports `restart` for obsolete mapped closures, `consumer-rebuild` for static/embedded vulnerable inputs that restart cannot fix, `reboot` for an evidenced boot-bound effect, and `unknown` for inaccessible processes, races, or unsupported inspection. It never terminates processes. Findings include process/service identity when visible, artifact and advisory bindings, reason, and coverage. Exit 0 means complete inspection with no actions, 3 actions or incomplete coverage, and 1 inspection/invocation failure. These commands and macOS inspection remain to be implemented.

The closed [advisory schema](../schematics/json/advisory.schema.json) defines each field. [DNF security/minimal selection](https://dnf.readthedocs.io/en/stable/command_ref.html), [DNF restart reporting](https://dnf-plugins-core.readthedocs.io/en/latest/needs_restarting.html), and [Zypper security patches](https://doc.opensuse.org/documentation/tumbleweed/zypper/) are upstream precedents; aslice's exact bindings and macOS coverage rules above remain its own contract.
- Formulae declare upstream security-contact and EOL policy; packages past upstream EOL are surfaced in `audit` and require `--allow-eol` to install.

Security remediation invalidates affected transitive consumers on recipe, source, toolchain, build-configuration, or selected dependency changes. ABI compatibility remains a gate and does not waive remediation. The recipe graph and exact artifact bindings are separate evidence; [BUILD-INFRA](BUILD-INFRA.md#the-build-plan) specifies closure construction and atomic publication.

<a id="what-this-does-not-solve"></a>

### 10.7 What this does not solve

- The initial project owner controls root and release signing and can ship bad slices. Separate owner-controlled devices do not provide independent oversight. Online signer compromise can authorize malicious releases; the offline root permits authority replacement but cannot undo installations or make compromised content trustworthy. Reproducible-build cross-checks (§9.5) and a public transparency log of index snapshots support review and detection, but do not prevent authorized malicious signing. Independent root custodians are a future governance step, not a launch claim.
- Sandboxing contains *builds*, not the runtime behavior of installed software. aslice is a package manager, not an endpoint product. The same distinction applies to vendor binaries: payload-only installation removes *installer-script* risk, not the risk of the vendor binary itself — signer pinning and hash pinning ensure you get the vendor's artifact unmodified, and that is all they ensure.
- **System packages (§12.7) step outside the sandbox story.** A kext runs in kernel space — a bug panics the machine — and SIP-disabled development tools weaken the protections of §10 for *all* software, not just themselves. aslice's guarantee for this category is narrower and says so: the bits are exactly the declared, verified ones; the privileged steps are exactly the declared ones, performed by aslice's own helper with explicit consent; the user was warned at every decision point. Nothing more is claimed, and the category is never servable by third-party repositories.
- **System patches (§12.11) step furthest outside the sandbox story.** A `[system-patch]` package replaces an Apple-provided file for *every* user and process on the machine; a bad one breaks the OS, not just itself. aslice's guarantee here is the narrowest in the design and is stated as such: the replacement is exactly the declared, signed, verified content; the original is backed up and restorable to the byte; refused paths (kernel, dyld, libSystem, `/System`, platform-binary dylibs) are refused by construction, not by policy; and consent was explicit at every decision point. Nothing more is claimed.
- **Grafts (§12.15) execute vendor code by definition — that is what they are.** The behavior manifest, the derived sandbox, the farm rehearsal, and the rollback capture bound *what the script may do while it runs*; they say nothing about what the installed software does afterward, and an unsigned manifest says nothing at all beyond the maintainer's word. An approved graft is a deliberate grant of trust, and the approval prompt says so instead of pretending a signature vets the vendor's intentions.
- C++ memory-safety risk in aslice itself is managed per §5.3; the parsers and extractors — the untrusted-input surfaces — get the fuzzing and the smallest footprints.

---

<a id="performance-model"></a>

## 11. Performance Model

These are unmeasured performance targets and proposed mechanisms, not established results:

| Goal | Mechanism |
|---|---|
| **CLI startup < 10 ms** | Single Mach-O binary, static libc++, no interpreter, no JIT, lazy dyld binding, no network on the hot path |
| **`install` of a cached slice < 300 ms** | Verify (Ed25519: microseconds) → zstd decompress → APFS `clonefile` into store (HFS+ systems fall back to hardlink/copy) → symlink generation swap. No relocation pass on default prefix. |
| **Index update < 200 ms typical** | Snapshot diffs against a cached snapshot hash — a few KB on a typical day |
| **Solve < 50 ms typical** | SQLite-backed package index with prepared statements; PubGrub with clause caching; memoized per snapshot |
| **Downloads saturate the pipe** | HTTP/2 multiplexing, bounded parallel fetches and decompression, resumable ranges, Zstandard payloads |
| **Cold full install of a large tree (e.g., `ffmpeg` closure) < 10 s on SSD** | Parallel fetch + pipeline overlap (decompress stream N+1 while linking N) |
| **Builds: near-zero manager overhead** | The builder's job is to get out of the way: Ninja parallelism, `ccache`-compatible compiler cache in `cache/`, tmpfs-backed build dir when RAM allows |
| **Shim dispatch < 1 ms** | Multicall binary (no interpreter, no JIT), committed execution catalog and validated admission, `exec` instead of fork. This is a target requiring measurement with closure validation and recovery gates enabled (§12.9) |

Flavor targeting may improve some workloads, but no advantage is claimed until measured with identical inputs and compatible hardware. OCI storage shares identical blobs only; binary deltas, metadata sharding, and reusable prepared build environments are later experiments. Reusing an environment must still verify all inputs and create disposable execution instances.

Benchmark startup, immutable full/diff index refresh, solving, cached and cold installation, shim dispatch with admission checks, VM preparation, and security rebuild closures. Publish versioned workload manifests with exact inputs: small single-package and large dependency closures; satisfiable/conflicting variant solves; static/header/bundled security changes; cold and warm caches. Record hardware and guest identities, OS, CPU features, RAM, storage/filesystem, network conditions, package counts and compressed/uncompressed sizes, cache state, concurrency, repetitions, failures, peak memory, and median/p95/p99 latency. Include APFS and HFS+ runs and verification costs. Store raw farm measurements and harness versions; collect no user telemetry. Qualification and benchmark execution remain pending.

Transfer and decompression workers share explicit connection, memory, expanded-byte, disk-watermark, and CPU budgets. Start with at most eight transfers and two decompressors, reducing concurrency to fit measured memory/disk budgets; refuse a job whose single-object bound cannot fit. Enforce bounds before allocation and during streaming, cancel safely on overflow, and report the limiting resource. Values are initial limits to validate, not throughput claims.


---

<a id="cli-and-user-experience"></a>

## 12. CLI and User Experience

<a id="commands"></a>

### 12.1 Commands

Space-separated mixed-orchard packages form one transaction; pre-commit failure
rolls back the managed-state batch. Package-specific options identify their target
(for example `--variant ffmpeg:+x265`); reject ambiguous batch options and display
effective settings per package. Stateful `--for` scoping is superseded.

Busy interactive commands offer wait or exit with owner information; unattended
waiting requires explicit authorization. After waiting or recovery, revalidate and
obtain confirmation for material changes. The initiating user or an authenticated
administrator can request stopping: attempt rollback before commit; after commit,
stop checks safely and report incomplete verification. See
[STATE-AND-RECOVERY §5](STATE-AND-RECOVERY.md#durable-transactions-and-recovery).

The index covers specified public commands, including maintainer and farm
operations. Historical spellings and internal helper executables are excluded.
These interfaces remain specifications, not a claim of completed implementation.
Each family page defines its arguments, options, examples, limits, and applicable
exit statuses; details not yet specified are identified there.

`OPTIONS` refers to the owning page. Database and recovery `SELECTORS` mean
`--role ROLE` and either `--prefix PATH` or `--instance ID`; selection grants no
authority. Global verbosity, JSON/log rendering, and authorized lock waiting are
documented in [aslice(1)](../man/aslice.1.md#global-options). A dry-run is supported
only where its command contract says so.

**Package management**

| Syntax | Purpose and manual |
|---|---|
| `aslice install PACKAGE… [OPTIONS]` | Install the newest eligible packages; disclose source builds. [aslice-install(1)](../man/aslice-install.1.md). |
| `aslice reinstall PACKAGE… [OPTIONS]` | Relink the same version to repair profile entries. [aslice-install(1)](../man/aslice-install.1.md). |
| `aslice upgrade [PACKAGE…] [--security [--minimal]] [--allow-source-builds]` | Update all or selected packages; security modes retain unresolved findings. [aslice-upgrade(1)](../man/aslice-upgrade.1.md). |
| `aslice outdated [--json]` | Show proposed updates and package holds. [aslice-upgrade(1)](../man/aslice-upgrade.1.md). |
| `aslice uninstall PACKAGE…` | Remove packages from future generations. [aslice-uninstall(1)](../man/aslice-uninstall.1.md). |
| `aslice autoremove [--dry-run]` | Remove dependencies no longer needed by requested packages. [aslice-uninstall(1)](../man/aslice-uninstall.1.md). |
| `aslice mark PACKAGE --on-request\|--as-dependency` | Repair the requested/dependency record. [aslice-uninstall(1)](../man/aslice-uninstall.1.md). |
| `aslice pin PACKAGE` | Hold a package against upgrades (one argument). [aslice-uninstall(1)](../man/aslice-uninstall.1.md). |
| `aslice unpin PACKAGE` | Release an upgrade hold. [aslice-uninstall(1)](../man/aslice-uninstall.1.md). |
| `aslice plan install PACKAGE… [OPTIONS]` | Resolve a request to a saved plan without executing. [aslice-apply(1)](../man/aslice-apply.1.md). |
| `aslice lock export` | Write the current exact resolution to stdout. [aslice-apply(1)](../man/aslice-apply.1.md). |
| `aslice apply DOCUMENT [--dry-run] [OPTIONS]` | Execute a plan or replay a lock; DOCUMENT may be an HTTPS URL. [aslice-apply(1)](../man/aslice-apply.1.md). |
| `aslice adopt --from-homebrew` | Produce a migration plan from the installed Homebrew leaf set. [aslice-adopt(1)](../man/aslice-adopt.1.md). |
| `aslice graft approvals [--json]` | Review recorded script approvals. [aslice-graft(1)](../man/aslice-graft.1.md). |
| `aslice graft revoke PACKAGE…` | Withdraw approvals; a later install asks again. [aslice-graft(1)](../man/aslice-graft.1.md). |

**Inspection**

| Syntax | Purpose and manual |
|---|---|
| `aslice search QUERY` | Match package names and descriptions. [aslice-inspect(1)](../man/aslice-inspect.1.md). |
| `aslice info PACKAGE` | Show versions, variants, dependencies, notes, and provenance. [aslice-inspect(1)](../man/aslice-inspect.1.md). |
| `aslice flavors PACKAGE` | Show the prebuilt matrix for this machine. [aslice-inspect(1)](../man/aslice-inspect.1.md). |
| `aslice leaves [--user-built]` | List packages without installed dependents. [aslice-inspect(1)](../man/aslice-inspect.1.md). |
| `aslice why PACKAGE` | Explain installed dependents. [aslice-inspect(1)](../man/aslice-inspect.1.md). |
| `aslice provenance PACKAGE` | Show authenticated build or repackaging evidence. [aslice-inspect(1)](../man/aslice-inspect.1.md). |
| `aslice audit` | Report known vulnerabilities in the installed set. [aslice-inspect(1)](../man/aslice-inspect.1.md). |
| `aslice needs-restarting [--json]` | Report restart, rebuild, reboot, and unknown inspection coverage. [aslice-needs-restarting(1)](../man/aslice-needs-restarting.1.md). |

**Profiles and runtime selection**

| Syntax | Purpose and manual |
|---|---|
| `aslice history` | List retained generations and attributed changes. [aslice-profile(1)](../man/aslice-profile.1.md). |
| `aslice rollback [GENERATION]` | Journal restoration of retained managed state. [aslice-profile(1)](../man/aslice-profile.1.md). |
| `aslice switch-generation GENERATION` | Select a retained generation explicitly. [aslice-profile(1)](../man/aslice-profile.1.md). |
| `aslice link PACKAGE` | Expose an installed package in the profile. [aslice-profile(1)](../man/aslice-profile.1.md). |
| `aslice unlink PACKAGE` | Retract profile exposure without removing dependency bindings. [aslice-profile(1)](../man/aslice-profile.1.md). |
| `aslice profile prefer NAME PROVIDER` | Select a colliding name or virtual provider. [aslice-profile(1)](../man/aslice-profile.1.md). |
| `aslice exec PACKAGE -- COMMAND [ARGUMENT…]` | Run in a temporary profile view. [aslice-profile(1)](../man/aslice-profile.1.md). |
| `aslice exec --replacement PATH -- PACKAGE COMMAND [ARGUMENT…]` | Explicitly run a verified isolated replacement closure. [aslice-profile(1)](../man/aslice-profile.1.md). |
| `aslice use RUNTIME STREAM [--install]` | Select a stream for the current shell through emitted shell code. [aslice-use(1)](../man/aslice-use.1.md). |
| `aslice use RUNTIME --clear` | Clear the session selection. [aslice-use(1)](../man/aslice-use.1.md). |
| `aslice pin RUNTIME STREAM [--install]` | Write a project runtime pin (two arguments). [aslice-use(1)](../man/aslice-use.1.md). |
| `aslice default [RUNTIME [STREAM]]` | Set or inspect profile-wide fallback selections. [aslice-use(1)](../man/aslice-use.1.md). |
| `aslice versions RUNTIME` | Show installed streams, selections, and extensions. [aslice-use(1)](../man/aslice-use.1.md). |
| `aslice which RUNTIME` | Trace runtime resolution to the store path. [aslice-use(1)](../man/aslice-use.1.md). |

**Maintenance and recovery**

| Syntax | Purpose and manual |
|---|---|
| `aslice gc [--dry-run] [--older-than 30d]` | Collect unreachable store artifacts. [aslice-gc(1)](../man/aslice-gc.1.md). |
| `aslice clean [--dry-run]` | Evict eligible cache entries. [aslice-gc(1)](../man/aslice-gc.1.md). |
| `aslice store verify [--quarantine PACKAGE]` | Rehash artifacts and optionally quarantine a mismatch. [aslice-gc(1)](../man/aslice-gc.1.md). |
| `aslice doctor [--fix] [--json] [--brief] [--deep] [--offline]` | Inspect health; fix only the documented no-data-loss cases. [aslice-doctor(1)](../man/aslice-doctor.1.md). |
| `aslice log [--last-op] [--follow] [--level LEVEL]` | Query local operation logs. [aslice-doctor(1)](../man/aslice-doctor.1.md). |
| `aslice db list [--role ROLE] [--json]` | List configured visible database instances. [aslice-db(1)](../man/aslice-db.1.md). |
| `aslice db [SELECTORS] schema [--live]` | Show shipped DDL or inspect the live schema. [aslice-db(1)](../man/aslice-db.1.md). |
| `aslice db [SELECTORS] query SQL [--json]` | Run one bounded read-only query. [aslice-db(1)](../man/aslice-db.1.md). |
| `aslice db [SELECTORS] check [--json]` | Validate identity, integrity, references, and records. [aslice-db(1)](../man/aslice-db.1.md). |
| `aslice db [SELECTORS] maintain [--dry-run] [--json]` | Run bounded maintenance and report deferrals. [aslice-db(1)](../man/aslice-db.1.md). |
| `aslice db [SELECTORS] compact [--dry-run] [--json]` | Reclaim file space through a validated versioned copy. [aslice-db(1)](../man/aslice-db.1.md). |
| `aslice db [SELECTORS] backup DESTINATION [--json]` | Write an owner-authorized coordinated backup set. [aslice-db(1)](../man/aslice-db.1.md). |
| `aslice db [SELECTORS] restore SET [--dry-run\|--confirm DIGEST] [--json]` | Preview and explicitly authorize restoration. [aslice-db(1)](../man/aslice-db.1.md). |
| `aslice recover [SELECTORS] [--continue\|--manual\|--salvage\|--activate] [OPTIONS]` | Guide recovery; unattended actions bind to a reviewed plan digest. [aslice-recover(1)](../man/aslice-recover.1.md). |
| `aslice operation status [--json]` | Inspect owner, phase, helpers, and recovery state. [aslice-recover(1)](../man/aslice-recover.1.md). |
| `aslice operation stop [--operation-id ID] [--json]` | Request authorized safe stopping; ID is required unattended. [aslice-recover(1)](../man/aslice-recover.1.md). |
| `aslice self-update [--check]` | Update the manager with retained recovery capability. [aslice-self-update(1)](../man/aslice-self-update.1.md). |
| `aslice decommission [--dry-run]` | Restore managed external effects before removing the prefix. [aslice-self-update(1)](../man/aslice-self-update.1.md). |

**Repositories and authoring**

| Syntax | Purpose and manual |
|---|---|
| `aslice repo add URL [--trust local]` | Add a signed repository and establish trust. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice repo list [--sources-diff] [--json]` | List repositories. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice repo enable NAME` | Enable a listed source. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice repo disable NAME` | Disable a source. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice repo remove NAME` | Remove a configured source. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice repo re-pin NAME` | Replace key authority after independent verification. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice repo keys NAME` | Inspect keys. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice repo audit NAME` | Inspect trust, countersignature, and staleness. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice repo allow-system-patch NAME` | Grant a verified repository patch permission. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice repo deny-system-patch NAME` | Revoke its patch permission. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice repo build PATH` | Compile an orchard or manifest directory into a repository. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice repo sign PATH [--sign-with ed25519\|openpgp]` | Apply repository signing keys. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice repo publish PATH` | Publish through the configured transport. [aslice-repo(1)](../man/aslice-repo.1.md). |
| `aslice orchard add ORG/ORCHARD` | Follow a formula orchard. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice orchard pin ORG/ORCHARD COMMIT` | Pin an orchard to a commit. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice orchard lint [PATH] [--json]` | Validate every formula. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice orchard doctor [PATH] [--json]` | Report orchard health. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice orchard freshness [PATH] [--json]` | Report upstream freshness. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice orchard ci [PKG…] [--flavors v2,v3] [--all]` | Run local merge gates; unavailable farm tiers remain deferred. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice orchard dependents PKG [--transitive] [--json]` | Inspect reverse dependencies and rebuild impact. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice orchard deprecate PKG --reason REASON [--replacement PKG] --date DATE [--disable-date DATE]` | Declare lifecycle dates and reason. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice orchard disable PKG` | Bring the disable date forward to today. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice orchard undeprecate PKG` | Remove deprecation metadata. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice orchard tombstone PKG` | Remove the formula while retaining its index tombstone. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice orchard rename OLD NEW` | Deprecate as renamed and scaffold a successor. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice orchard port --from-homebrew FORMULA` | Translate a Homebrew formula into a reviewed draft. [aslice-orchard(1)](../man/aslice-orchard.1.md). |
| `aslice create URL` | Draft a formula from a source URL. [aslice-author(1)](../man/aslice-author.1.md). |
| `aslice lint FORMULA` | Validate one formula against schema and policy. [aslice-author(1)](../man/aslice-author.1.md). |
| `aslice build PACKAGE-OR-DIRECTORY [BUILD-OPTIONS]` | Compile locally with the farm harness; reproduction has its own form. [aslice-author(1)](../man/aslice-author.1.md). |
| `aslice build --reproduce PACKAGE VERSION FLAVOR BUILD-REFERENCE` | Compile locally with the farm harness; reproduction has its own form. [aslice-author(1)](../man/aslice-author.1.md). |
| `aslice test PACKAGE` | Run the installed slice smoke tests. [aslice-author(1)](../man/aslice-author.1.md). |
| `aslice livecheck [PACKAGE \| --all]` | Query upstream versions. [aslice-author(1)](../man/aslice-author.1.md). |
| `aslice bump-pr PACKAGE VERSION` | Edit, lint, smoke-build, and open a version-bump PR. [aslice-author(1)](../man/aslice-author.1.md). |
| `aslice farm plan` | Compute the affected build and test DAG. [aslice-farm(1)](../man/aslice-farm.1.md). |
| `aslice farm coordinator` | Schedule work, gate, and collect evidence. [aslice-farm(1)](../man/aslice-farm.1.md). |
| `aslice farm agent [--once] [--vm-guest] [--reproduce-only]` | Run a worker or guest test agent. [aslice-farm(1)](../man/aslice-farm.1.md). |
| `aslice farm enroll --project URL` | Enroll an evidence worker and pin the coordinator. [aslice-farm(1)](../man/aslice-farm.1.md). |

**Machine setup**

| Syntax | Purpose and manual |
|---|---|
| `aslice machine apply [aslice-machine.toml \| https://…] [--dry-run] [--prune] [--accept-system-changes] [--accept-grafts] [--json]` | Converge a machine wishlist; default ./aslice-machine.toml. [aslice-machine(1)](../man/aslice-machine.1.md). |
| `aslice machine export [--defaults DOMAIN,…] [--system-defaults DOMAIN,…]` | Capture managed state; preference domains are opt-in. [aslice-machine(1)](../man/aslice-machine.1.md). |
| `aslice machine import --from-brewfile Brewfile` | Translate a Brewfile with a skip list. [aslice-machine(1)](../man/aslice-machine.1.md). |
| `aslice service list` | List managed launchd services. [aslice-service(1)](../man/aslice-service.1.md). |
| `aslice service status PACKAGE` | Report launchd state and last exit. [aslice-service(1)](../man/aslice-service.1.md). |
| `aslice service start PACKAGE` | Start the declared service. [aslice-service(1)](../man/aslice-service.1.md). |
| `aslice service stop PACKAGE` | Stop the declared service. [aslice-service(1)](../man/aslice-service.1.md). |
| `aslice service restart PACKAGE` | Restart the declared service. [aslice-service(1)](../man/aslice-service.1.md). |
| `aslice service run PACKAGE` | Run in the foreground without registration. [aslice-service(1)](../man/aslice-service.1.md). |
| `aslice ca-update [--check]` | Refresh private trust or explicitly selected trust/crypto layers. [aslice-ca-update(1)](../man/aslice-ca-update.1.md). |
| `aslice ca-update --keychain` | Refresh private trust or explicitly selected trust/crypto layers. [aslice-ca-update(1)](../man/aslice-ca-update.1.md). |
| `aslice ca-update --keychain-remove` | Refresh private trust or explicitly selected trust/crypto layers. [aslice-ca-update(1)](../man/aslice-ca-update.1.md). |
| `aslice ca-update --crypto` | Refresh private trust or explicitly selected trust/crypto layers. [aslice-ca-update(1)](../man/aslice-ca-update.1.md). |
| `aslice ca-update --apple-certs` | Refresh private trust or explicitly selected trust/crypto layers. [aslice-ca-update(1)](../man/aslice-ca-update.1.md). |
| `aslice ca-update --from-file bundle.pem` | Refresh private trust or explicitly selected trust/crypto layers. [aslice-ca-update(1)](../man/aslice-ca-update.1.md). |
| `aslice system-patch list` | List managed replacements of Apple files. [aslice-system-patch(1)](../man/aslice-system-patch.1.md). |
| `aslice system-patch status [PATH]` | Inspect baseline, hashes, drift, and pending reboot. [aslice-system-patch(1)](../man/aslice-system-patch.1.md). |
| `aslice system-patch restore PATH [--accept-system-changes]` | Restore through the compatible OS backend. [aslice-system-patch(1)](../man/aslice-system-patch.1.md). |
| `aslice system-patch prepare [--accept-system-changes]` | Persist protected recovery material before Recovery. [aslice-system-patch(1)](../man/aslice-system-patch.1.md). |
| `aslice system-patch finalize [--accept-system-changes]` | Verify the booted result before committing. [aslice-system-patch(1)](../man/aslice-system-patch.1.md). |

**Shell and configuration**

| Syntax | Purpose and manual |
|---|---|
| `aslice shellenv` | Print profile paths and trust-store environment exports; no writes. [aslice-shell(1)](../man/aslice-shell.1.md). |
| `aslice init SHELL` | Print integration for bash, zsh, or fish. [aslice-shell(1)](../man/aslice-shell.1.md). |
| `aslice config get KEY` | Read configuration; detailed get behavior remains unspecified. [aslice-shell(1)](../man/aslice-shell.1.md). |
| `aslice config set KEY VALUE` | Set a configuration key. [aslice-shell(1)](../man/aslice-shell.1.md). |
| `aslice help COMMAND` | Print the owning man-page text. [aslice-shell(1)](../man/aslice-shell.1.md). |

Representative choices retain their distinct meanings:

```sh
aslice install ffmpeg                  # newest eligible version; flavor auto-detected
aslice install ffmpeg --build-from-source
aslice install ffmpeg --variant +x265 --cflags="-O3 -march=native"
aslice install ffmpeg@v6               # version constraint
aslice install audiolab:convolver      # explicit repository namespace
aslice install php@8.4                 # coexisting runtime stream; does not select it
aslice install php-redis               # extension bound to the selected runtime
aslice install composer                # tool that rides the selected runtime
aslice pin openssl                     # one argument: package upgrade hold
aslice pin php 8.4                     # two arguments: project runtime selection
aslice upgrade ffmpeg --rollback-on-service-failure
aslice upgrade --security
aslice upgrade --security --minimal --allow-source-builds
aslice install foo --accept-system-changes
aslice install protools-hd --accept-grafts
aslice plan install ffmpeg > plan.json
aslice lock export > aslice.lock
aslice profile prefer blas openblas
aslice config set flavor v2
aslice init zsh
```

<a id="interaction-principles"></a>

### 12.2 Interaction principles

- **Binary is the default, source is a flag.** A user who never passes `--variant` or `--cflags` never sees a compiler.
- **Every decision is explainable.** `--explain` on any command shows the solver's derivation; `--dry-run` shows the exact plan: which slices, which local builds, which generation change.
- **Announce, don't bury.** EOL packages, unsigned orchards, deprecated variants, fallback-to-source events, and unsigned or non-notarized vendor binaries are always announced in the output. `doctor` reports what the machine can and cannot do rather than pretending uniformity.
- **Scriptable:** `--json` on everything; stable exit-code contract; machine-readable `plan`/`apply` split (`aslice plan install ffmpeg > plan.json && aslice apply plan.json`) — which is also what the future multi-user daemon consumes.

<a id="orchards-repositories-and-trust-levels"></a>

### 12.3 Orchards, repositories, and trust levels

Orchards are git repos of formula directories — the *authoring* format. Repositories (§9.6) are the *distribution* format. Trust is explicit at both layers:

- **Core/extended orchards:** signed by project keys; Starlark + TOML only.
- **Third-party orchards:** installed disabled by default; enabling one prints its trust implications (its formulae can cause local source builds — sandboxed — but never execute at binary-install time: the only install-time code anywhere is the approved graft (§12.15), and a third-party orchard's grafts carry unsigned manifests, the big fat warning, and per-decision consent).
- **The canonical repository:** the project orchards compiled and signed by project keys; pre-pinned in the bootstrap.
- **Third-party repositories:** added explicitly, root key pinned on first use (TOFU, fingerprint displayed, changes blocking). A third-party repository can serve its own signed slices — including binary-only vendor repackagings — under its own keys. No repository can make aslice execute package code at install time *silently*: grafts run only with user approval, a declared behavior manifest, and monitoring (§12.15) — the door is guarded by consent and capture, not by trust policy.

<a id="vendor-binaries-pkgdmg-and-gui-apps"></a>

### 12.4 Vendor binaries (pkg/dmg) and GUI apps

Some software for this platform will only ever ship as a `.pkg` installer or a `.dmg` — commercial audio tools, vendor CLIs, frozen releases of abandoned apps. aslice installs it **without running installer code by default** — and with it only as a declared graft (§12.15):

- **`.pkg`:** expanded with `xar`/`pkgutil --expand`; only the `Payload` is extracted, per the declarative path map in the formula. `preinstall`/`postinstall` scripts never execute *by default*. Packages whose function genuinely *requires* script execution are no longer refused either: the scripts install as declared grafts — approved per package, monitored against a behavior manifest, captured for rollback (§12.15). The payload-only line remains the default every other package meets. Drivers and kexts are **not** rejected, though: they install through the declarative system-software category (§12.7), where the privileged steps are performed by aslice's own helper from manifest declarations — and when a driver package genuinely needs its vendor scripts, those run as grafts instead (§12.15).
- **`.dmg`:** attached read-only via `hdiutil -nobrowse -readonly`; declared items copied. No autolaunch, no quarantine propagation.
- **Apps** install under `/opt/aslice/apps/` (owned by the prefix, not `/Applications`), with an optional per-user `~/Applications` symlink; Finder and Launch Services pick them up from either location.
- **Provenance is pinned.** The formula records the expected signing identity (`Developer ID Application: Vendor (TEAMID)`) and notarization expectation; the verifier checks the signature *before* extraction and hard-fails on a silent signer change — a classic supply-chain attack against binary distribution. An unsigned vendor artifact carries no signer to pin: it is permitted only in the extended orchard, declared with `signer` omitted and announced at every install ([PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software), [ORCHARD-POLICY §12](ORCHARD-POLICY.md#vendor-binary-packages-pkgdmg)); the core orchard stays signed-only.
- **Two distribution modes.** `redistribute = true` → the farm repackages the payload into a normal `.slice`, hosted in the repository like any other (best UX: atomic, resumable, rollback-able). `redistribute = false` → the formula stays a pointer: the client fetches the vendor URL itself (hash- and signer-pinned), extracts locally in the sandbox, installs payload only. Same install semantics; only the transport differs. Pointer-mode software still gets generations, lock files, and `audit`.
- **OS support is tagged per artifact.** Each `[[binary]]` entry carries its own `min_os`/`max_os`/`arch`, so a vendor's "legacy" build for 10.11–10.13 and "current" build for 10.14+ coexist in one formula and the solver picks the artifact matching the machine — never a "this application cannot be opened" surprise after install. Vendor claims are checked at pack time against the bundle's `LSMinimumSystemVersion` and the pkg's Distribution requirements where present; mismatches are lint errors, because an accurate tag is the entire point.
- **32-bit payloads install where — and only where — the OS can run them.** 10.11 through 10.14 are the last macOS releases that execute 32-bit code, and a large share of pkg/dmg-only software on this platform (audio plugins, lab instruments, frozen pro tools) is i386 or universal. Vendor artifacts may therefore carry `arch = ["i386"]` or `["x86_64", "i386"]`; the pack-time verifier inspects every Mach-O slice in the payload with `lipo`-style logic and derives the true ceiling — required i386-only executables, helpers, or plugins impose `max_os = "10.14"` (or lower) and are refused at solve time on 10.15+. An unused i386 member alongside a usable x86_64 member does not impose the ceiling. Ambiguous plugin requirements need evidence or rejection ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)). Universal payloads are installed **whole**: no `lipo -thin` stripping, ever — thinning a fat binary invalidates the vendor's code signature, and signature integrity outranks disk savings. This changes nothing about what aslice *builds* (N6: farm slices stay x86_64-only); it is distribution, not compilation.

Vendor binaries participate in the store, generations, profiles, lock files, and `audit` like source-built packages. Their `build_id` excludes flavor and toolchain (§7.2), and their payload dylibs get the same ABI scan at pack time — dependents link against vendor libraries through the same contract as farm-built ones. The scan is per-architecture: universal payloads record separate `x86_64` and `i386` ABI entries, and the x86_64 entry is what aslice-built dependents (always 64-bit) consume.

<a id="logging-and-diagnostics"></a>

### 12.5 Logging and diagnostics

A package manager that fails opaquely trains users to fear it. aslice logs **everything it does, to the local machine, and nowhere else** — the charter (N7) applies to logs as it does to metrics: nothing is ever transmitted, aggregated, or phoned home, not even opt-in.

**Where logs live.** `/opt/aslice/log/` (or `~/.aslice/log/` for per-user prefixes), one JSONL file per day, rotated and size-capped (default: keep 14 days or 256 MB, whichever is less; both configurable). The build harness keeps its own per-build structured logs (`log.jsonl`, [BUILD-INFRA §4](BUILD-INFRA.md#user-mode-aslice-build)) — this section governs the client.

**What gets logged.** Every operation is a structured event stream with a generated operation ID that ties terminal output, log records, and the `history` table ([REPOSITORIES §11](REPOSITORIES.md#the-state-databases-role)) together:

| Category | Examples | Level |
|---|---|---|
| Mutations | install/upgrade/uninstall plans, generation swaps, rollbacks, GC runs | info |
| Security events | signature/hash/ABI verification results, key-pin changes, trust-level demotions, sandbox escapes, frozen repos | warn or error — **unsuppressible** (`--quiet` cannot hide them) |
| Decisions | overlap resolutions and revalidations (§9.6), fallback-to-source events, flavor downgrades, EOL acceptances | info |
| Diagnostics | network retries, mirror failovers, slow solves, disk-space pressure | debug at `-v`, trace at `-vv` |

**The message-quality standard.** Log messages are UI, and they are held to the same bar as the CLI itself:

- **Actionable errors, always.** Every error message names *what* failed, *why* as far as aslice can determine, and *what the user can do next*. `"verification failed"` is a bug; `"slice ffmpeg-7.1-0+core.v3: minisign signature invalid (key ed25519:RWQ0…, repo core) — refusing to install; run `aslice doctor` or re-fetch with --refresh-index"` is the standard.
- **Structured fields, human rendering.** Events are JSONL on disk (`ts`, `level`, `op`, `pkg`, `msg`, plus context fields); the terminal renders them as concise human lines. `--log-format json` pipes the raw stream for scripting; `-v`/`-vv` raise verbosity without changing what is *recorded*.
- **One message, one fact, one place.** Errors propagate with context attached at each layer (fetch → verify → link), so the final message reads as a causal chain, not a stack trace. No message is ever printed twice by two layers.
- **Progress is a log level, not a spinner-only UX.** Long operations (downloads, builds) emit periodic structured progress events, so a CI log or a `aslice log --follow` tells the same story the terminal spinner does.
- **Supportability.** `aslice log` filters by operation, package, level, or time range; `aslice doctor` ends with the paths of the relevant log files. When a user files an issue, `aslice log --last-op` produces the excerpt a maintainer needs — locally generated, user-attached, never auto-submitted.

**Silence discipline.** Steady-state success is quiet: a successful binary install prints its plan summary and result, and everything else lives in the log at info level. aslice never logs at warn for things that are fine (a lesson from tools whose warning noise trains users to ignore real ones).

<a id="doctor-sanity-checking"></a>

### 12.6 Doctor: sanity checking

`aslice doctor` is the single entry point for "is my installation healthy?" — it runs a fixed battery of checks, reports each as pass/warn/fail with the actionable-message standard of §12.5, and never changes anything itself (repairs are explicit commands it *recommends*). It is read-only, offline-capable, and fast (< 1 s for the standard battery; deep checks are opt-in).

**Check groups:**

| Group | Checks | Verdicts |
|---|---|---|
| **Machine** | CPU flavor vs. configured flavor (a v3 config on v2 hardware is a fail, not a surprise SIGILL later); macOS release vs. supported window; APFS vs. HFS+ (capabilities that degrade, announced); free disk vs. GC watermark | pass / warn / fail |
| **Prefix and store** | Prefix ownership and permissions (user-owned, not world-writable); store path integrity — manifests re-hashed against on-disk content (`--deep` re-hashes every file, default checks a sample plus anything the DB flags); dangling store paths referenced by no generation | pass / fail |
| **Profiles and generations** | `default` symlink resolves; every profile symlink lands inside the store; the live generation matches the DB's installed set; collision priorities resolve to real paths | pass / fail |
| **Database** | SQLite integrity check; schema version vs. binary (a newer DB than the binary is a fail with downgrade instructions, never silent corruption); WAL recovery state | pass / fail |
| **Repositories** | Per repo: reachable (or cached-snapshot age if `--offline`), TUF metadata expiry countdown, pinned key still matches live root, trust-level consistency (a `verified` repo whose countersignature lapsed is a fail with the freeze explanation — [REPOSITORIES §3](REPOSITORIES.md#trust-levels)), namespace uniqueness and qualified non-core names, index staleness beyond policy | pass / warn / fail |
| **Coexistence** | Homebrew/MacPorts presence, PATH ordering advice, anything in `/usr/local` shadowing aslice binaries (or vice versa) — advisory only, aslice never touches either | pass / warn |
| **Environment** | `ASLICE_*` variables that override config (listed, not hidden); shell init files referencing stale prefixes; Xcode CLT presence (informational — the self-hosted toolchain makes it optional for aslice itself) | info / warn |
| **Trust store** | `ca-certificates` bundle freshness against the index (a stale trust store is this platform's day-one failure); profile env wiring (`SSL_CERT_FILE`/`CURL_CA_BUNDLE`/`GIT_SSL_CAINFO`) points at the aslice bundle; System-keychain imported set matches the DB record — drift after OS updates or third-party cleanup reported, never silently repaired (§12.10) | pass / warn |
| **System patches** | Every declared `[system-patch]` target still symlinks into the live generation; backup files present and hash-matching the DB record; drift after macOS updates (a patch Apple restored, or a newer Apple file our symlink now shadows) reported with reapply/restore remedies, never silently re-patched (§12.11) | pass / warn / fail |
| **Grafts** | Every recorded graft footprint still matches the state DB: declared writes present (or recorded as user-removed), and nothing inside a graft's declared paths that the DB did not record — drift means something outside aslice touched the graft's territory, and the report names the paths (§12.15) | pass / warn |

**Rules:**

- **Every fail and warn names the remedy.** Not "store integrity error" but "store path `x264-0.164-0+core.v3.77aa10b2` fails manifest hash (1 file) — quarantine with `aslice store verify --quarantine x264` and reinstall." The check table is code, not prose: each check has an ID (`doctor.store.hash`), so messages, `--json` output, and docs all reference the same stable identifier.
- **Exit codes are scriptable:** 0 all-pass, 1 warnings only, 2 any fail. `--json` emits the full battery result; CI and fleet tooling gate on it (`aslice doctor --json | jq '.checks[] | select(.verdict=="fail")'`).
- **Warnings are real action items.** Each warn carries a command; anything informational goes to the `info` tier, which `--brief` suppresses. A doctor that cries wolf gets ignored — the battery is curated so that a clean machine prints one line: `aslice: your installation is healthy (N checks, M repos, G generations)`.
- **It ends with pointers.** The summary footer lists the log directory and the last operation ID (§12.5), so a failing machine goes from `doctor` to root cause in two commands.
- **`--fix` exists but is narrow.** The only automatic repairs offered are ones with no possible data loss: pruning dangling cache entries, re-linking a broken generation symlink to its recorded target, refreshing stale index snapshots. Everything else prints the exact command for the user to run. `--fix` announces each action before taking it and logs all of them.

---

<a id="system-software-kexts-and-sip-disabled-development-tools"></a>

### 12.7 System software: kexts and SIP-disabled development tools

Some software this platform needs cannot live entirely inside the store: kernel extensions (audio-interface drivers, filesystems, hypervisors) and development tools that require SIP disabled (low-level debuggers, DTrace-based profilers, kernel instrumentation — a real population on 10.11–12 development machines). Earlier drafts rejected this category outright; v1.2 replaces the rejection with a declared path, because the software exists and users install it today by hand — with no provenance, no warnings, and no rollback. A package manager that refuses to see that protects no one.

**Declaration.** A package opts in via `package.toml`:

```toml
[system]
kexts            = ["Library/Extensions/FooAudio.kext"]  # payload-relative paths to install
sip_off_required = false     # true: the software cannot function while SIP is enabled
reason           = "Kernel driver for FooAudio USB interfaces"   # mandatory; this IS the warning text
```

Either `kexts` or `sip_off_required = true` (or both) marks a system package; `reason` is mandatory and shown verbatim in every warning. Development tools needing SIP off but installing no kext declare only `sip_off_required` and `reason`. The declaration is specified in PACKAGE-FORMAT under the system table.

**Mechanism — declarative, elevated, still code-free.** The category preserves the founding rules:

- **Zero package code at install (§10.1) holds.** The privileged steps — placement into `/Library/Extensions`, ownership and permission repair, `kextcache` invalidation, load — are performed by **`aslice-system`** (§10.4) from the manifest's declarations. Vendor `postinstall` scripts run only as declared grafts (§12.15) — approved per package, sandboxed to a behavior manifest that names the kext, captured for rollback.
- **Store and rollback hold.** The kext payload lives in the store like any other file; `/Library/Extensions` entries are managed copies recorded in the DB. Uninstall unloads and removes them and refreshes the kernel cache; rolling back to a prior generation restores the prior kext set.
- **Kext reality is respected.** On SIP-enabled 10.11+, loaded kexts must be signed — the formula declares whether its kexts are signed (signer-pinned per §12.4 when vendor-supplied) or whether it requires SIP off. aslice checks `csrutil status` rather than assuming: a `sip_off_required` package on a SIP-enabled machine stops *before download* with exact instructions (boot to Recovery, `csrutil disable`, re-run the command); a signed-kext package on a SIP-enabled machine installs with no SIP conversation at all. OS updates can re-enable SIP or invalidate kexts — `doctor` (§12.6) reports SIP state, declared-vs-loaded kexts, and that drift.

**Warnings at every decision point.** Declared system requirements surface at every decision point:

- **Solve and plan:** installing a system package prints a prominent block *before any download*: the kexts it installs, the SIP requirement, the `reason` text, and the consequences — kexts run in kernel space (a bug panics the machine), and SIP-disabled operation weakens every protection in §10 for all software on the machine.
- **Non-interactive refusal:** scripts, `--json` plans, and the `apply` commands **refuse** system packages unless `--accept-system-changes` is passed for that operation. There is deliberately no persistent "always accept system changes" setting — consent is per-decision, like the risk.
- **Elevation:** the consent prompt for `aslice-system` repeats the declaration; every elevation is logged as an unsuppressible security event (§12.5).
- **Doctor:** SIP state, kext drift after OS updates, and unsigned-kext installs are all `doctor` checks with remedy text and stable check IDs (`doctor.system.sip`, `doctor.system.kexts`).

**Trust gating.** Serving system packages requires the **`system` capability**, granted by trust level ([REPOSITORIES §3](REPOSITORIES.md#trust-levels)): **official and verified repositories have it; third-party repositories never do; `local` repositories have it** (a developer's own `file://` tree on their own machine — the same authority as installing the kext by hand, now with warnings and rollback). Talking a user into installing a kernel extension is the social-engineering attack the trust levels exist to block, so no remote stranger's repository can offer one. Tier policy — extended by default, core only when the platform genuinely requires it — lives in [ORCHARD-POLICY §13](ORCHARD-POLICY.md#system-software-packages-kexts-sip-disabled-tools-and-system-patches).

---

<a id="services-launchd-native-lifecycle-and-safe-upgrades"></a>

### 12.8 Services: launchd-native lifecycle and safe upgrades

Long-running services — nginx, PostgreSQL, Redis, dnsmasq, unbound — are where a package manager meets the running system, and they impose two requirements. The manifest must *describe* the service rather than ship scripts that manage it, and an upgrade must never replace the binary under a running process: stop the service, swap, start it again. aslice generates launchd declarations and includes stop–swap–restart in its journaled upgrade transaction.

**Declaration.** A package describes its service in `package.toml` (schema: [PACKAGE-FORMAT §3.8](PACKAGE-FORMAT.md#install--declarative-post-install-behavior)):

```toml
[service]
run         = ["bin/nginx", "-g", "daemon off;"]  # argv, profile-relative; never a shell string
domain      = "user"        # "user" (default: gui/<uid> agent) | "system" (root LaunchDaemon — gated)
keep_alive  = true          # launchd KeepAlive — bool or a table of conditions
run_at_load = true
working_dir = "var"                   # prefix-relative
environment = { LANG = "en_US.UTF-8" }
log_dir     = "var/log/nginx"         # StandardOutPath / StandardErrorPath
```

aslice generates launchd plists. User jobs may resolve through the ordinary profile. Root jobs resolve only through the protected root-owned closure and pointer; their plist and execution-affecting configuration are root-controlled ([STATE-AND-RECOVERY §3](STATE-AND-RECOVERY.md#privileged-ownership-and-capability-checks)). Labels include prefix/profile identity as well as package name so concurrent profiles cannot control each other's jobs.

**The command.** `aslice service` is a thin layer over `launchctl`'s modern interface (`bootstrap` / `bootout` / `kickstart` / `print`, present since 10.10, so the whole 10.11–12 window is covered):

- `aslice service list` / `status <pkg>` — reads `launchctl print gui/<uid>/<prefix/profile/package label>`: pid, state, last exit status, keepalive. Status is launchd's truth, not a pidfile.
- `aslice service start` / `stop` / `restart <pkg>` — `bootstrap` / `bootout` / `kickstart -k` against the generated plist.
- `aslice service run <pkg>` — foreground, unregistered, for debugging (the one `brew services` idea worth copying).
- User-service environment overrides live in `$XDG_CONFIG_HOME/aslice/services/<pkg>.env`. Root-service overrides require a helper transaction and are copied into protected configuration after validation; root never loads the user-owned override file.

**Upgrades stop the service first.** The mutation pipeline of §8.3 becomes service-aware whenever a plan touches a package with a loaded job:

1. Resolve, fetch, and build the **entire new generation** while the old one — and the service — keeps running. Any failure here never touched the service.
2. `bootout` the affected jobs — and only the affected ones; an ffmpeg upgrade never bounces your postgres.
3. Swap the generation symlink (atomic, §8.3).
4. Reconcile plists — only if the declaration changed; the profile indirection means a plain version bump needs no plist edit.
5. Reconcile and commit the installation, then `bootstrap` / `kickstart -k` the jobs and run service-specific readiness checks, defaulting to 60 seconds per service with positive finite overrides. A PID alone proves only liveness. Retain mutation ownership through the checks. A job that won't start is an error carrying launchd's last exit status and the log path — and then aslice **asks the user about rolling back** (below).

**A failed health check asks; it never decides silently.** The failure is shown first — the job's launchd exit status and the log path — then, on an interactive terminal:

```console
$ aslice upgrade nginx
…
error: installation committed; service nginx failed to start after the upgrade (launchd exit status 78;
log: /opt/aslice/profiles/default/var/log/nginx/error.log)
The previous generation (nginx 1.26.2, generation 41) is retained.
Rollback requires verified service-data compatibility or an authorized restoration procedure.
Roll back and restart the previous version? [y/N]
```

- **Yes** starts a rollback transaction restoring the prior closure, profile, and service declaration, then tests readiness. Automatic rollback is refused if persistent data may have migrated without a validated restoration procedure ([STATE-AND-RECOVERY §5](STATE-AND-RECOVERY.md#durable-transactions-and-recovery)).
- **No (the default)** leaves the new generation live and the service down: nothing is destroyed, the logs stay put for debugging, `doctor.services` flags the crashed job until it is resolved, and `aslice rollback` remains available — the prompt only accelerates a decision the user can make at any time. A declined rollback is remembered for the current operation only; the next failure asks again.
- **Non-interactive contexts** (no TTY, `--json`, scripts) never prompt and never auto-rollback: the upgrade exits with a machine-readable `service_start_failed` error naming the package, the exit status, and the log path, and rolling back is an explicit `aslice rollback`. Automation that wants the "yes" path unattended passes `--rollback-on-service-failure`. There is deliberately no flag that reports a downed service as success.

GC is already safe: a running job pins its store path through the profile generation it was started from, and §8.4 never collects store paths referenced by running processes.

**Root daemons are the privileged case.** `domain = "system"` jobs run as root (or a declared `user_name`) and are bootstrapped into the system domain by `aslice-system` (§10.4) — same per-operation consent, same unsuppressible logging as kexts. Because root execution is the privilege that matters, `domain = "system"` declarations are gated by the same **`system` capability** as `[system]` packages ([REPOSITORIES §3](REPOSITORIES.md#trust-levels)): official and verified repositories may serve them, **third-party repositories never may**, local trees may on the user's own machine. User-domain agents are unprivileged and ungated — any repository may declare one, no sudo is ever involved, and the steady-state rule (§10.4) stands for nginx-on-8080 and every other development service.

**Doctor.** `doctor.services` checks: every enabled service's plist parses and its `ProgramArguments` resolve into the *live* generation; jobs loaded for packages no longer installed (and packages with declared services that were never enabled); crash-looping jobs (launchd's throttling state); and, for `domain = "system"` jobs, that what is running matches what the DB records `aslice-system` installed. All read-only; `--fix` offers only the no-data-loss repairs (§12.6).

---

<a id="multi-version-runtimes-use-pin-default--and-version-bound-extensions"></a>

### 12.9 Multi-version runtimes: use, pin, default — and version-bound extensions

Users may keep several php, nodejs, ruby, and python versions installed. The immutable store retains exact artifacts; a separate selection layer chooses the runtime for a session, project, or profile default. Services and compiled extensions retain explicit artifact bindings.

**One formula, release streams.** A runtime is a single formula (`php`) whose orchard publishes several maintained streams (8.3, 8.4, 8.5) in the index simultaneously. `aslice install php@8.4` is an ordinary version-constrained install; the store happily holds 8.3.11, 8.4.13, and 8.5.0 side by side. What installing a stream does *not* do is change which `php` you get — selection is always explicit, never a side effect of installing. An upgrade remains within the selected stream; installing a new stream does not select it.

Recovery does not deny all shim dispatch. A separately retained committed execution
catalog supplies defaults, installed streams, and exact closures independently of
SQLite. Durable affected-selection gates precede live writes. Established unaffected
selections and verified closures remain usable; unavailable required state fails promptly
without choosing another runtime. Session/project/default precedence below stays
unchanged. Explicit isolated replacement execution is separate from shim selection
([STATE-AND-RECOVERY §5.2](STATE-AND-RECOVERY.md#52-working-package-access-and-shims)).

**The shim layer.** PATH gains one directory ahead of the profile: `/opt/aslice/shims` (the installer sets the order; `doctor.coexistence` verifies it).

A shim is a hardlink to the aslice binary dispatched on `argv[0]` — zero per-tool code — created for every name a runtime formula declares in `shims = [...]` (php, phpize, pecl, php-fpm; node, npm, npx; ruby, gem, bundle; python3, pip3, …). Invoked as `php`, the shim resolves a stream (below), validates its exact closure through the committed execution catalog and affected-selection gate, and `exec`s the real binary — no fork, no wrapper process, signals and `ps` intact. The sub-millisecond dispatch target requires measurement with these checks enabled (§11). Shimmed names are *not* linked into generations; the profile links **versioned aliases** instead (`bin/php8.4`), which services and scripts use when they must name an exact runtime — §12.8's generated plists bind the alias of the stream selected at enable time, so `aslice default php 8.5` never silently changes what a running php-fpm executes, and moving a service between streams is an explicit disable/enable. Resolution, first match wins:

1. **Session** — `ASLICE_USE_PHP=8.4` in the environment, set by `aslice use`.
2. **Project** — the nearest `aslice.toml` walking up from the working directory, written by `aslice pin`.
3. **Default** — the profile-wide selection recorded by `aslice default` in the state DB.
4. **Sole installed stream** — if exactly one is installed, it wins; zero, or several with no selection, is an error naming the installed streams and the three ways to choose.

**`aslice use` — the current shell.** The command respects Unix semantics: a child process cannot rewrite its parent's environment, so `aslice use php 8.4` emits shell code — `export ASLICE_USE_PHP=8.4` on stdout, the human message on stderr. With the optional shell integration (`eval "$(aslice init zsh)"`, a few auditable lines for bash/zsh/fish), an `aslice` shell function evals that automatically; without it, `eval "$(aslice use php 8.4)"` does the same by hand, ssh-agent-style. The session pin is an ordinary environment variable: it propagates to subshells, dies with the shell, overrides project and default, and shows up in `env` and in `doctor`'s environment group like every other `ASLICE_*` override. `aslice use php --clear` unsets it. Implicit per-shell state without shell cooperation (PID-keyed databases, process-ancestry tricks) was rejected: tmux and daemon-spawned shells defeat ancestry, and a selection mechanism you cannot see with `env` is one you cannot debug. If the requested stream isn't installed, an interactive run offers to install it; non-interactive runs fail with the suggestion unless given `--install`.

**`aslice pin` — the project.** `aslice pin php 8.4` writes (or updates) `aslice.toml` in the project root:

```toml
# aslice.toml — commit me alongside composer.json / package.json / Gemfile
[runtimes]
php    = "8.4"
nodejs = "22"
```

Every shell, subshell, CI step, and editor-integrated terminal *inside that tree* now resolves to the pinned stream — Volta's `package.json` behavior, made ecosystem-neutral (one file pins php *and* node in the same repo; no per-ecosystem pin formats). Pins record streams (`8.4`), never exact patches: patch movement within a stream is `aslice upgrade`'s job and must not require editing a committed file. A pin naming a stream that isn't installed behaves like `use` in that situation: interactive offer, non-interactive error, `--install` to override. `aslice which php` traces the full resolution — session? project? default? — down to the store path, so "which php am I actually running, and why" is one command, the same explainability standard as `--explain` for the solver.

**`aslice default` — the fallback.** `aslice default php 8.4` journals the profile-wide selection and updates the state DB and committed execution catalog; `aslice default php` shows it; bare `aslice default` lists all selections. The default is what cron jobs, services, and shells outside any project tree land on. Installing a second stream never changes it; uninstalling the selected stream refuses until another is selected (`--force` overrides, logged). `aslice versions php` shows the matrix: installed streams, the pinned/default/session selections, and which extensions are installed per stream.

**Extensions bind to exactly one runtime version.** This is where version managers historically give up — pecl compiles against whichever `phpize` ran first, pip installs into whichever site-packages happens to be writable, and the result only *looks* shared until an ABI breaks. aslice splits the problem by who does the installing:

- **aslice-managed extensions are slices, keyed to the runtime's ABI epoch.** Compiled extensions — `php-redis`, `php-imagick`, `ruby-pg` — are orchard packages declaring `[extension] runtime = "php"` ([PACKAGE-FORMAT §3.13](PACKAGE-FORMAT.md#runtime-extension-ride--multi-version-runtimes-v05)). The runtime formula declares its own **ABI epoch** (`"8.4"` for php, `"3.12"` for python, `"3.3"` for ruby, `"22"` for nodejs — the granularity at which the extension ABI breaks: minor for php/python/ruby, major for node), and the epoch enters the extension's build identity: extensions for php 8.4 and php 8.3 have distinct artifact-addressed store paths. Installing an extension binds to the *currently selected* stream (same resolution as the shims; `--runtime php@8.3` overrides): the solver requires that stream installed, the build compiles against that concrete runtime store path, and linking writes a small loader file into the profile's per-epoch scan directory (`etc/php/8.4/conf.d/20-redis.ini`) — so extension sets are generation-managed and `aslice rollback` restores runtime and extension set together. The farm prebuilds the extension × supported-epoch × flavor matrix, so binaries exist for every supported stream. A patch upgrade within a stream (8.4.12 → 8.4.13) keeps the epoch, but existing extensions retain their exact runtime bindings until an explicit rebuild or verified relocation and dependency tests establish new artifacts; installing a *new* stream (`aslice install php@8.5`) offers to provision the previous stream's extension set for it (interactively; `--with-extensions-from 8.4` for scripts) — a new epoch is a conscious port, never an accident.
- **Ecosystem-native installs bind through the shim, per version, outside the store.** `pip install`, `gem install`, `npm i -g`, `pecl install`, `composer global require` keep working — but the shim execs the tool with the per-version **userbase** environment of the *resolved* stream (`~/.aslice/runtimes/php/8.4/`, `…/python/3.12/`, …, mapped through `PYTHONUSERBASE`, `GEM_HOME`/`GEM_PATH`, `NPM_CONFIG_PREFIX`, PHP's user-ini/extension-dir conventions — declared by each runtime formula in [PACKAGE-FORMAT §3.13](PACKAGE-FORMAT.md#runtime-extension-ride--multi-version-runtimes-v05), never hardcoded). The store stays immutable; each stream gets its own writable territory; a `pip install` under python 3.12 is invisible to 3.13 — the binding falls out of the directory layout. Userbase contents are user territory: aslice never audits, snapshots, or garbage-collects them, `doctor.runtimes` reports their presence and size, and uninstalling a stream warns about its orphaned userbase instead of deleting it.

**Tools ride the runtime.** The third category is interpreter-target tools with no native code against the runtime ABI: composer (a phar), yarn, prettier, poetry. These are ordinary slices that declare `[ride] runtime = "php"`: the slice installs once, its shim resolves the runtime through the normal session → project → default order at exec time, and the tool launches under that runtime — composer's PHP is always your selected PHP, switching automatically when you switch. This is Volta's best idea (a global yarn that follows your node) generalized to every ecosystem, with one deliberate difference: riding is a property of the tool's *formula*, never user configuration, because whether a tool can safely ride is a fact about its code, not a preference.

**Upgrades stay in their lane.** `aslice upgrade php` moves within the selected stream only — 8.4 patches, never 8.5; its output mentions newly available streams (`php 8.5 is available: aslice install php@8.5`) without touching them. That is the contract that makes `aslice upgrade` safe on a production Mac mini: the runtime your sites, services, and crontabs resolve to changes only when you say `use`, `pin`, or `default`. GC is conservative in the same direction: a stream that is selected as default, pinned by a project `aslice.toml` the DB knows about, or referenced by an enabled service is never collected.

**Doctor.** `doctor.runtimes` checks: the shim directory is present and *precedes* the profile on PATH (with the exact fix line); every declared shim resolves (no dangling selections — e.g. a default pointing at an uninstalled stream); every enabled service's versioned alias resolves to an installed stream; extension scan directories match the DB (a loader for an epoch whose runtime is gone); orphaned userbases reported, never removed. All read-only, same remedy-text standard as §12.6.

---

<a id="trust-store-modern-ca-certificates-on-a-frozen-platform"></a>

### 12.10 Trust store: modern CA certificates on a frozen platform

`ca-certificates` supplies a signed private PEM bundle for aslice userland. Shell integration points compatible clients at it. Updating certificates does not upgrade TLS implementations; `--crypto` separately updates aslice crypto-provider packages and never replaces SecureTransport.

`ca-update --keychain` uses a signed policy inventory and the protected helper, preserving supported purpose/domain constraints and refusing entries whose restrictions cannot be represented. PEM extraction alone does not reproduce Mozilla's browser trust policy. Roots and intermediates have distinct import operations; intermediates never become trust anchors merely because they were imported. `--apple-certs` uses the same constrained lifecycle for Apple's PKI, with service-specific validation and no promise to revive obsolete protocols.

Protected receipts distinguish existing Apple/user entries from aslice-owned additions. Updates preview and authorize retirement of aslice-owned roots; `--keychain-remove` reverses only unchanged owned effects. Known distrust is never silently undone by generation rollback. [STATE-AND-RECOVERY §9](STATE-AND-RECOVERY.md#9-certificate-trust-lifecycle) owns this lifecycle. `doctor.truststore.*` reports age, configuration, known retirement, and conflicts.

<a id="system-patches-flagged-reversible-replacement-of-apple-provided-files"></a>

### 12.11 System patches: flagged, reversible replacement of Apple-provided files

`[system-patch]` declares exact Apple-provided tool/configuration/data paths, a mandatory reason, and security prerequisites. The kernel, dyld, libSystem, `/System`, platform-binary libraries, and early-boot consumers remain refused. The capability is available to official/local repositories and explicitly granted verified repositories; never to third-party repositories. Grafts cannot bypass it.

The helper keeps exact originals and recovery metadata in protected root-owned storage and installs verified replacements from protected closures. Writable paths use journaled file operations. Catalina System-volume changes use a Recovery-assisted offline backend; Big Sur/Monterey changes stage a complete patch set and select a boot snapshot. SIP, authenticated root, FileVault, and startup-security conditions are checked separately.

[SYSTEM-VOLUMES](SYSTEM-VOLUMES.md) specifies prepare, Recovery application, pending-reboot state, finalization, rollback, and OS-update handling for 10.11–12. A volume rollback can require Recovery and reboot; it is not an instant profile swap. Originals are versioned by OS baseline and are never restored over an intervening OS update. A missing backup or incompatible baseline stops the operation with a recovery remedy.

`system-patch list`, `status`, and `restore` remain the inspection/restoration commands; `prepare` and `finalize` manage protected-volume transitions. Every mutation requires explicit system-change consent. The client refuses an OS/hardware/security configuration before mutation until its adapter has passed the required patch/boot/restore drill.

<a id="self-update-aslice-is-package-zero"></a>

### 12.12 Self-update: aslice is package zero

aslice is package zero, installed as an immutable artifact. A known-good supervisor launches the proposed replacement as a child, checks it against a versioned state snapshot, and retains responsibility through activation and post-activation health checks. These manager-integrity checks precede the durable commit; ordinary service readiness checks follow it. Before commit a failure reverses tentative activation; after commit restoration is a new transaction preserving history and trust floors. It never re-execs away its own recovery capability before success.

Database migration creates a new versioned copy; old manager/state pairs remain usable. A retained bootstrap recovery entry point handles power loss or supervisor failure. Shims are updated transactionally too. `aslice recover` runs recovery before permitting further mutations. [STATE-AND-RECOVERY §6](STATE-AND-RECOVERY.md#6-self-update-and-decommission) defines crash cases and decommission.

`self-update --check` is read-only. Package holds and configured release environments apply; crossing a format major requires an explicit migration plan and confirmation. Signing/notarization precede freezing the served artifact inventory, and the authentic bootstrap verifies detached signatures.

<a id="declarative-system-setup-aslice-machinetoml-and-the-aslice-machine-commands"></a>

### 12.13 Declarative system setup: `aslice-machine.toml` and the `aslice machine` commands

A Mac back from system recovery is blank, and the path from *blank* to *ready to work* is an afternoon of remembering: which packages, which Dock settings, which shell, which services, which runtime streams. aslice specifies one declarative file — `aslice-machine.toml` — and one command group: after the installer, `aslice machine apply` (the file defaults to `./aslice-machine.toml`; an `https://` URL works too) takes a blank machine to a working one, and because the file is plain TOML data it doubles as the shareable common language for "this is how my machine is set up". The inverse, `aslice machine export`, captures an existing machine back into the file. Full schema and semantics: [SETUP.md](SETUP.md); what follows is the architecture.

**The file is a wishlist with preferences, not a lock.** `packages = ["ffmpeg@7", "postgresql +ssl"]` carries the same constraints `install` accepts; `[runtimes.default]` carries §12.9's stream selections; `[services]` carries the enable set; `[defaults.user."<domain>"]` / `[defaults.system."<domain>"]` carry macOS preference keys; `[shell]` carries the login shell; `[aslice]` and `[[repos]]` carry configuration and extra repositories. Like a Brewfile it is the human layer above exact state — the difference from a lock is the `package.json`/`package-lock.json` difference ([PACKAGE-FORMAT §7](PACKAGE-FORMAT.md#lock-files)). Unlike a Brewfile it is **data, never code**: no evaluation, no hooks, nothing executable — applying a stranger's file has a bounded, inspectable blast radius, and the plan shows every write before any happens (§12.2's plan/apply split, now pointed at whole machines).

**One operation, three documents, two spellings.** Converging a machine, replaying a lock, and executing a saved plan are the same operation at three fidelities — *make reality match this document*. The document kind is still detected by content (JSON plan, `lock_version`, `schema`), but the spelling is split: plans and lock files keep the top-level verb (`aslice apply plan.json`, `aslice apply aslice.lock`), while the machine file lives under the `aslice machine` group — `aslice machine apply`, defaulting to `./aslice-machine.toml`. The split is deliberate: `aslice-machine.toml` is a reserved, self-describing name other tools can recognize, and a machine file passed to top-level `apply` (or a plan passed to `machine apply`) is refused with a pointer to the right spelling. A machine document is *planned* first: wishlist resolved against the current snapshot, preferences diffed, the full plan rendered and confirmed before execution. Ordering puts privileged work last (repositories → config → packages → selections → services → user defaults → system defaults + shell), so a plan refused at a consent gate still lands everything unprivileged and reports the remainder as skipped-refused.

**Convergence, with discipline.** Apply is idempotent — a second run is a no-op — and additive by default: it asserts, never removes what the file doesn't mention. `--prune` opts into retraction, bounded two ways: it touches only records the file itself applied, and it never removes repositories (trust decisions stay sticky, [REPOSITORIES §10](REPOSITORIES.md#overlapping-packages-across-repositories)). Before every preference write, shell change, or `/etc/shells` enrollment, the pre-change value is recorded against the new generation — §12.11's backup discipline generalized — so `aslice rollback` restores preferences and login shell together with the profile, and `aslice history` attributes every applied change to its file hash and generation.

**Two new consent-gated writes.** System-domain preferences (`/Library/Preferences`) and enrolling a non-Apple login shell in `/etc/shells` are OS-territory writes, otherwise barred by N5 (§2.2). They join `[system-patch]`'s model exactly: declared in the file, executed by `aslice-system` (§10.4), interactively prompted with their targets named, refused non-interactively (exit 2) unless `--accept-system-changes` is passed — one flag, one contract across §12.7, §12.11, and here. Shell changes resolve through the profile path, never a raw store path, so generation rollback moves the login shell back automatically.

**Export captures what is knowable.** Packages, selections, services, shell, repositories, and non-default config are aslice's own state — exported completely, deterministically sorted for diffing. Preferences are not knowable: there is no baseline to diff a preferences folder against, and application domains can hold account tokens and machine-specific values, so `export` captures them only for domains named with `--defaults` / `--system-defaults`, emits deferred value types (dict, data, date) as comments, and stamps the output with a review-before-sharing warning. Locally-built packages and foreign (non-aslice) shells are commented out with notes rather than exported as if reproducible. `aslice machine import --from-brewfile` provides migration ([SETUP §5](SETUP.md#aslice-machine-import---from-brewfile)): mechanical translation with a printed skip list for `cask`/`mas`/`vscode`.

**Limits.** Not a dotfiles manager (chezmoi/Stow/git own `~/`); not a system imager (FileVault, SIP, accounts, panes without domains are untouched); not fleet configuration management (no agent, no drift loop — `launchd` running `aslice machine apply` is the entire enforcement story); not exact reproduction (that is the lock's job). Keychain items are never read or written.

<a id="orchard-maintenance-the-maintainers-cli"></a>

### 12.14 Orchard maintenance: the maintainer's CLI

The per-formula verbs (`create`, `lint`, `test`, `bump-pr` — §12.1) and the publishing pipeline (`aslice repo build`/`sign`/`publish` — §9.6) bracket the maintainer's day; everything in between — keeping a whole orchard healthy — is the `aslice orchard` group. Every verb operates on a **local orchard checkout**: the optional `[path]` argument defaults to the current directory, discovered by walking up to the directory whose children are formula directories. The mutating verbs follow the `bump-pr` contract end to end: edit the formula, validate, lint, and open the PR — on a plain git remote without PR machinery, print the branch and the diff instead.

**Lifecycle verbs — the `[deprecation]` table, edited by command.** Schema in [PACKAGE-FORMAT §3.14](PACKAGE-FORMAT.md#deprecation--the-package-lifecycle-declared-v06), policy in [ORCHARD-POLICY §8](ORCHARD-POLICY.md#deprecation-and-removal-lifecycle):

```sh
aslice orchard deprecate ffmpeg --reason upstream-eol --replacement ffmpeg7 \
    --date 2027-03-01 --disable-date 2027-09-01
aslice orchard disable ffmpeg        # pull disable_date forward to today
aslice orchard undeprecate ffmpeg    # rescind — remove [deprecation]; the reason goes in the PR body
aslice orchard tombstone ffmpeg      # remove the formula; the index tombstone is permanent (§3.14)
aslice orchard rename ffmpeg ffmpeg7 # deprecate-as-renamed + scaffold the successor formula
```

Each verb rewrites `[deprecation]` (or removes the formula) and validates what the linter will check anyway: dates in order, `replacement` present if and only if `reason = "renamed"`, the replacement resolving in the orchard. `tombstone` refuses a name that still has enabled dependents, and [ORCHARD-POLICY §8](ORCHARD-POLICY.md#deprecation-and-removal-lifecycle)'s security fast path is `deprecate --reason security --disable-date <today>` — a vote and a merge, not a special command.

**Orchard-wide health.** `aslice doctor` checks one machine (§12.6); `aslice orchard doctor` checks one orchard:

- `aslice orchard lint [path]` — every formula in the tree against schema and policy; the gate a maintainer runs before pushing anything.
- `aslice orchard doctor [path] [--json]` — the health battery, run with §12.6's discipline: stable check IDs (`orchard.lint.*`, `orchard.livecheck.*`, `orchard.deprecation.*`), pass/warn/fail with the remedy named, exit codes 0/1/2 for scripts. The battery: lint clean across the tree; every core package carries `tests.star` and a working `[livecheck]`; deprecation coherence (replacements resolve, no disable date silently past, no name shadowing a tombstone); patch documentation per [ORCHARD-POLICY §7](ORCHARD-POLICY.md#patches); a named maintainer on every core package; `provides`/`conflicts`/`replaces` all resolve; no duplicate package names.
- `aslice orchard freshness [path] [--json]` — runs every formula's livecheck and prints days-behind-upstream per package, worst first, with the orchard median — the number [ORCHARD-POLICY §9](ORCHARD-POLICY.md#freshness-livecheck-and-autobump) publishes on the farm dashboard. Packages without `[livecheck]` are reported as untracked, which is a finding in core.

**The merge gate, locally.** `aslice orchard ci [pkg…] [--flavors v2,v3] [--all]` runs the six-gate check of §13.4 / [ORCHARD-POLICY §10](ORCHARD-POLICY.md#merge-gates-what-ci-must-prove) on the maintainer's machine, before the farm has to: lint, a sandboxed build per declared flavor at the formula's `min_os` through the BUILD-INFRA harness (one harness, two scales — the laptop run and the farm run are the same pipeline), the `tests.star` smoke test, and the ABI gate diffed against a published index snapshot. The cross-OS smoke-run tier is honestly marked deferred-to-farm — a laptop cannot conjure the 10.11 VM — and so is the graft rehearsal gate (§12.15), which wants the same VMs: locally, a graft's manifest is lint-checked for completeness and the script hash-verified, and the observed-behavior diff runs on the maintainer's own OS release only. With no arguments, `ci` scopes to the packages changed against the upstream branch; `--all` prices the full orchard and says so before starting. The gate passing locally merges nothing — it makes the PR boring.

**Impact queries.** `aslice orchard dependents x264 [--transitive] [--json]` walks the orchard's dependency graph — built from the `[depends]`, `[extension]`, and `[ride]` declarations — and prints reverse dependencies, marking build/runtime, static, header, generated, and bundled edges separately from exact artifact bindings. All affected transitive consumers rebuild on changed inputs, even with compatible ABI. This is the query the farm's dependent-rebuild cascade (§13.4) runs server-side, and the query `orchard ci` runs to scope its ABI gate; giving it to the maintainer means "what breaks if I bump this" is answered before the PR, not after the merge.

**The formula importer** of §13.3 ships in this group as `aslice orchard port --from-homebrew <formula>` — named *port*, because §13.3 is honest that only the simple majority of Ruby formulae translate mechanically; the rest are ports, and the command says so. (`aslice machine import --from-brewfile`, §12.13, remains the user-side verb: migrating a machine, not authoring a formula.)

---

<a id="vendor-install-scripts-grafts--declared-approved-monitored-reversible"></a>

### 12.15 Vendor install scripts: grafts — declared, approved, monitored, reversible

A graft is a vendor installer script declared by path, hash, phase, and effective behavior manifest. Approval binds repository identity, version, script hashes, and manifest digest; expanded permissions invalidate it. Unsigned manifests require a fresh decision and cannot be allow-listed.

Supported scripts run only in an isolated staging view. A validated delta is committed through the helper journal; live root execution and unrestricted privileged IPC are not graft capabilities. Kexts and daemons are registered declaratively by the helper under the same repository gates as other mechanisms. Network-dependent inputs must be fetched and pinned before execution; irreversible remote or firmware effects are unsupported.

[STATE-AND-RECOVERY §4](STATE-AND-RECOVERY.md#4-graft-execution-boundary) defines refusal conditions and rehearsal requirements. Each claimed OS must prove enforcement and crash recovery before graft admission. A behavior manifest or successful rehearsal alone does not establish containment or complete rollback.

<a id="policies-governance-and-migration"></a>

## 13. Policies, Governance, and Migration

<a id="package-acceptance-policy"></a>

### 13.1 Package acceptance policy

- Core orchard: maintained, security-patched, reproducible-build targets; no package enters without a working `tests.star` smoke test on at least one OS × one flavor.
- Upstream-EOL software: allowed in extended with `eol = true` metadata; excluded from core.
- Vendor binary packages: accepted into extended with accurate OS-support tags and a pinned signer when the artifact is signed — unsigned artifacts are extended-only, `signer` omitted, announced at every install (§12.2, §12.4); into core only if signed, hosted by the farm (`redistribute = true`), and payload-only by construction — or, when graft-bearing, rehearsed on the farm with a signed behavior manifest (§12.15). A vendor package whose scripts turn out to be required is no longer refused by default: the scripts are declared as grafts with a behavior manifest, farm-rehearsed and signed for core and extended (§12.15) — and a package whose graft behavior cannot be honestly manifested is removed, not accommodated.
- **Runtime dependencies resolve to aslice packages only**. Never `/usr/lib` dylibs, never `/usr/bin` tools: on 10.11 the system libraries *are the problem*. The only exceptions are always-present system **frameworks** (`Accelerate`, `SystemConfiguration`, `CoreAudio`, `CoreFoundation`, …) enumerated in a lint allowlist — frameworks are the platform's ABI, not its bundled software. Allowlist additions are policy PRs against [ORCHARD-POLICY §6](ORCHARD-POLICY.md#dependencies-and-system-software) and the lint table together.
- **Patching system files is rejected by default — and flagged where it isn't.** aslice installs alongside macOS and never modifies `/System`, `/usr`, or Apple's binaries silently, incidentally, or as a side effect of anything else. Where fixing the frozen platform genuinely requires replacing an Apple-provided file, the declared `[system-patch]` category (§12.11) does it openly: original bytes and metadata retained in protected storage, verified replacement from a root-owned closure, journaled restoration with Recovery/reboot where the backend requires it, consent at every decision point, served by official and local repositories — and by verified ones only under an explicit per-repo `allow-system-patch` grant (§12.11) — with catastrophic and platform-binary-library paths refused by construction. The marketing feature survives, stated precisely: aslice never patches your system *behind your back*. Kernel extensions and SIP-disabled development software likewise remain the declared, warned, trust-gated category of §12.7.

<a id="variant-discipline"></a>

### 13.2 Variant discipline

`abi = true` variants are governed by need, not quota. Each must name the exported interface it changes — the ABI scan supplies evidence, so the tag is checked, not the worthiness of the request — but there is no numeric cap: a package like ffmpeg legitimately carries many codec combinations, uncommon ones included, and which ones a user needs is the user's call, not the project's. Variants whose licenses permit compilation but not redistribution work like any other non-default variant: the client builds them locally from source and the farm never prebuilds them (§9.4), so the machinery is identical and nothing is forbidden. The discipline that survives the retired cap is where cost lands, not what users may want: the solver space stays tractable because the prebuilt matrix covers defaults plus demonstrated-demand variants (§9.4), and non-default variants build on demand. `abi = false` (build-flavor) variants are unconstrained — they cost the project nothing because they never spawn binary flavors.

<a id="coexistence-and-migration-from-homebrew"></a>

### 13.3 Coexistence and migration from Homebrew

- **Coexistence:** aslice lives in `/opt/aslice`, never touches `/usr/local`, and `doctor` detects a Homebrew installation and advises on PATH ordering rather than conflicting.
- **`aslice adopt --from-homebrew`:** reads Homebrew's Cellar and `brew leaves`, maps names to aslice formulae (with a maintained alias table for renames), produces an install plan that recreates the same leaf set — including mapping old `--with-*` Homebrew options to aslice variants where an alias exists. Cask leaves map to vendor-binary packages where one exists, flagged for review when the vendor artifact's OS tags don't cover the machine. It does not attempt binary reuse of Homebrew's Cellar (different prefix assumptions); it reuses the *intent*.
- **Formula importer (for orchard authors):** `aslice orchard port --from-homebrew <formula>` (§12.14) mechanically translates simple Homebrew Ruby formulae — `url`/`sha256`/`depends_on`/standard `configure && make` bodies — into TOML+Starlark drafts, with a human review step. Realistic coverage target: the simple ~60–70% of formulae; the rest are ports, not translations. A companion importer turns simple Casks (`url`/`sha256`/`app`/`pkg`) into `type = "binary"` drafts — Casks are *more* mechanical than formulae, so coverage should be higher; the reviewer fills in signer pinning and OS tags — and, for Casks carrying `installer script:` or pkg hooks, either deletes the scripts (payload-only rewrite, preferred) or declares them as grafts with a behavior manifest (§12.15).

<a id="governance"></a>

### 13.4 Governance

- Single-owner start: the project owner’s merge is the final human release approval, including new core slices; automated gates, signing, and atomic publication follow without intervention. Root operations remain offline. Add independent maintainers and agree multi-party custody when participation warrants it; neither a founding quorum nor hardware-token purchases block launch ([KEY-RUNBOOK §5](runbooks/KEY-RUNBOOK.md#future-independent-custody-and-hardware)).
- Orchard PR review backed by CI that *builds the package in the sandbox on every declared flavor* — review is about correctness and policy, never "does it compile." The merge gate is six checks, with no maintainer override ([ORCHARD-POLICY §10](ORCHARD-POLICY.md#merge-gates-what-ci-must-prove)): lint (schema + policy), a matrix build on every declared flavor at the formula's `min_os` with smoke-runs across `[min_os, 12]`, the `tests.star` smoke test, an **ABI gate** on provider version/revision changes (a regression requires a proper version bump or scheduled dependent rebuilds, published in the same index snapshot), a **rehearsal gate** for graft-bearing packages — the farm runs the install in a per-OS VM and diffs observed behavior against the declared behavior manifest, and a mismatch never ships (§12.15) — and post-merge-only signing.
- **Project hygiene documents shipped in Phase 0** (September 2026) — `SECURITY.md` (how to report a vulnerability in aslice itself; key-contact runbook), `CONTRIBUTING.md` (the formula style guide: when a variant is justified, `min_os` accuracy, patch documentation — and the project's conduct expectations), and `docs/runbooks/KEY-RUNBOOK.md` (the written key-ceremony/rotation runbook referenced by §10.2). There is deliberately **no `CODE_OF_CONDUCT.md`** — an owner decision: this is not a corporate project, people are expected to be nice to each other without a document legislating it, and telling someone they're acting like an idiot when they are is acceptable; CONTRIBUTING.md's Conduct section carries the expectation in the open. Documents, not code — cheap before launch, expensive after the first incident.
- Public roadmap, public build-farm dashboard, public transparency log. A legacy-platform project survives on trust, and trust survives on visibility.
- Funding: GitHub Sponsors/OpenCollective for power and future hardware upkeep; the launch topology uses the two owned Macs and requires no new hardware purchase (§9.3).

---

<a id="roadmap"></a>

## 14. Roadmap

**Phase 0 — Foundations (months 0–3, sequencing target rather than a delivery commitment)**
`aslice-toolchain` first: modern Clang/libc++ targeting darwin15, bootstrapped on the owned Mac Pro with Monterey as the proposed baseline, subject to toolchain validation, against the oldest archived SDK, then self-rebuilt. Then the minimal immutable store, generations, durable journal, retained recovery entry point, self-update supervisor, and persistent trust store ([STATE-AND-RECOVERY §10](STATE-AND-RECOVERY.md#acceptance-and-implementation-order)). Then the C++ core skeleton: CLI, SQLite state, TUF client, zstd, Mach-O/otool wrappers — plus the build harness in local mode (`aslice build` with the full sandboxed phase pipeline, job/result schemas; [BUILD-INFRA §12](BUILD-INFRA.md#roadmap-mapping)), because the core orchard seed is built *with* it. Bootstrap binary runs on every release 10.11–12 (VM-tested per release, including HFS+). Core orchard seeded with ~30 packages (curl, git, openssl, python, zstd, cmake, ninja) built on real hardware. **Self-update ships in the first usable binary** (§12.12) — retrofitting update mechanisms is how projects die — alongside the project hygiene documents (§13.4). The from-nothing sequence for the whole project — toolchain genesis, TUF root ceremony, orchard seed, farm standup — is executed and written down as `docs/runbooks/GENESIS.md`, so the platform can be stood up from nothing again and again.

**Phase 1 — Usable (months 3–6)**
Full solver with variants; extend the Phase 0 store/profiles/generations; GHCR distribution; the build harness in both modes — `aslice build` locally and `aslice farm` coordinator/agents on real hardware, one pipeline (BUILD-INFRA.md); minisign slices; ~300-package core orchard, all flavors; `adopt --from-homebrew`; **the freshness pipeline** — `[livecheck]` in every core formula, scheduled orchard autobump opening bump PRs, and `aslice livecheck`/`bump-pr` for humans ([PACKAGE-FORMAT §3.15](PACKAGE-FORMAT.md#livecheck--upstream-freshness-declared-v06); [ORCHARD-POLICY §9](ORCHARD-POLICY.md#freshness-livecheck-and-autobump)); build farm Phase A + first self-hosted nodes. Repository client (`repo add/list`, TOFU key pinning) from the start — the canonical repository *is* the default transport, so the multi-repo machinery costs little extra. The `ca-certificates` slice and the private-bundle half of `aslice ca-update` (§12.10) ship here — every userland TLS fetch depends on them. So do the `apple-roots` slice and `ca-update --crypto` (§12.10): both are ordinary signed content and ordinary upgrades.

**Phase 2 — Differentiated (months 6–12)**
ABI scanner with DWARF diffing; SBOM + `audit`; SLSA provenance; `aslice-toolchain` v2 (LLD-first linking, ccache integration); extended orchard to ~2,000 packages; popular-variant prebuilds chosen from community requests (§9.4); reproducible builds for core; vendor-binary packages (`type = "binary"`, payload extraction, signer pinning), the Cask importer, and **grafts** — declared vendor install scripts with behavior manifests, the farm's rehearsal VMs, and the pnpm-style approval flow (§12.15), built on the proven `aslice-system` helper; `aslice repo build/publish` for third-party repositories; **runtime version management** — the shim layer, `use`/`pin`/`default`, riding tools, and version-bound extension slices with the farm's runtime-epoch build axis (§12.9); the opt-in System-keychain import halves of `aslice ca-update` (`--keychain`, `--apple-certs`, §12.10) and the `[system-patch]` category (§12.11), once `aslice-system` is proven in service and kext duty; **declarative system setup** — `aslice-machine.toml` and the `aslice machine` group (`apply` / `export` / `import --from-brewfile`, §12.13) — after the primitives it composes (services, runtime selections, repositories) are proven.

**Phase 3 — Durable (year 2)**
Two-builder reproducibility cross-checks; transparency log; community mirror program; `~/Applications` polish and GUI-app niceties; multi-user daemon if demand materializes; governance formalization.

---

<a id="risks-and-open-questions"></a>

## 15. Risks and Open Questions

Guided recovery inventories evidence automatically, resumes saved progress, and
groups actual conflicts with recommendations. A known-good executable and recovery
records outside the prefix support rebuilding beside the preserved original.
Recovered selections do not authorize bytes: verify replacement artifacts and their
closures independently. Reviewed salvage can leave isolated unaffected packages
usable while normal activation or privileged integration remains blocked.

[STATE-AND-RECOVERY §10.2](STATE-AND-RECOVERY.md#102-recovery-engineering-contracts)
defines the recovery engineering contracts; its
[UX scorecard and acceptance scenarios](STATE-AND-RECOVERY.md#101-guided-workflow-acceptance)
are provisional targets and pending runtime work. Outcomes distinguish repaired,
usable with listed unresolved repairs, and replacement prepared but activation blocked.

| Risk | Severity | Mitigation |
|---|---|---|
| GitHub degrades self-hosted macOS runner support or GHCR terms change | High | Mirror-first index design (§9.1); Buildkite/Forgejo runner portability; static-mirror escape hatch means GHCR is replaceable |
| Apple removes Seatbelt in a future macOS | Low for scope | Target window is 10.11–12 — frozen releases where Seatbelt is present; the policy abstraction isolates the backend regardless |
| Modern Xcode can't target 10.11/10.12 (hosted floor ~10.13) | Medium | Self-hosted toolchain is Phase 0 and authoritative (§4.3); hosted CI is a bonus layer; archived SDKs cached on the farm; SDK use on builders stays within Apple's license on Apple hardware |
| Maintainer capacity | High | Frozen platform = fixed workload; automation-first orchard CI; small core orchard with quality bar; explicit scope refusal (no Apple Silicon, no new macOS) |
| Signing-key compromise | Medium | Offline root Pi, isolated networked release signer, encrypted backups, pre-launch recovery drills, explicit root-compromise rebootstrap, transparency log for detection |
| 10.11-era testing hardware scarcity | Medium | Validate 10.11–12 guests in batches on capable owned Macs; missing required coverage blocks publication; Core 2 Duo testing is optional future coverage outside current inventory |
| ABI scanner false negatives (missed breakage) | Medium | Belt and suspenders: compat-version check + symbol fingerprint + reverse-dependency smoke tests in CI; when in doubt, rebuild dependents (we own the build farm) |
| C++ vulnerability in aslice itself | Medium | §5.3 program: subset, hardening, sanitizers, fuzzing, tiny trust-critical helpers |
| Vendor binaries are opaque — no source SBOM, no reproducibility, the binary itself is trusted | Medium | Signer + hash pinning (silent substitution hard-fails); payload-only SBOM with full file list; `audit` binds CVEs via CPE; core tier barred unless farm-hosted + payload-only (§13.1); users told what is and isn't verified (§10.7) |
| Vendor pulls or mutates a `redistribute = false` artifact | Medium | Hash pin fails rather than installing a different binary; the formula records last-known-good; community can negotiate hosting or archive a copy |
| A graft's behavior manifest understates the script, or an approved vendor script turns malicious | Medium | The manifest-derived Seatbelt profile denies undeclared writes and network by construction; farm rehearsal diffs observed behavior and a mismatch never ships; every captured write rolls back with its generation; unsigned manifests get the big fat warning and per-decision consent, never persisted (§12.15) |
| A `[system-patch]` replacement breaks software that expected the Apple original | High | Strictest gate in the system (official/local, verified only with an explicit per-repo grant, per-decision consent); lint-time refused-path list blocks catastrophic and platform-binary-library targets; exact backup + byte-verified restore; the §10.7 honesty rules cap what is claimed (§12.11) |
| A macOS update restores or upgrades an Apple file a `[system-patch]` has replaced | Medium | `doctor.systempatch` drift detection with explicit reapply/restore remedies, never silent re-patching; patches use protected closures and platform-specific journaled restoration; reboot verification may remain pending (§12.11) |
| GPL/license compliance for hosted binaries | Low | Corresponding-source archive mirrored per license; SPDX SBOMs make compliance auditable; `redistribute = false` covers software the project does not rehost |
| Community adoption never materializes | Existential | Scope stays hobbyist-sustainable by design; worst case, the core orchard remains a maintained artifact for the installed base |

**Open questions for early reviewers:**

1. ~~Default prefix~~ — **resolved (v1.8): `/opt/aslice` by default, `~/.aslice` as the no-admin fallback.** The installer prefers the shared prefix; when it cannot create it, it offers a fully supported per-user install under `~/.aslice` with identical semantics (§8.1, §10.3) — two documented layouts, not an arbitrary-prefix free-for-all. The name itself is settled: **aslice**.
2. ~~Starlark vs. a stricter pure-TOML-with-templates build DSL~~ — **resolved (v1.8): Starlark stays.** Real legacy codebases need real conditionals and loops; the hermetic subset (no network, no filesystem outside the sandbox) carries the safety story, and escape hatches in a template language would be worse than a real one.
3. ~~Whether local flag builds share store paths~~ — **resolved by the state-and-recovery contract:** compatibility keys may match; byte-distinct artifacts have distinct immutable addresses. Provenance does not replace artifact identity ([STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#compatibility-and-artifact-identity)).
4. ~~Telemetry~~ — **resolved (v0.3, sharpened v0.4): aslice collects no telemetry or analytics of any kind, ever.** No install IDs, no opt-in counters, no phone-home, no crash reporting — and no download-count-driven prioritization either, because volume mismeasures value on a platform where the rarest dependency may be the most irreplaceable (§9.4). The project is infrastructure, not a product, and its users — many on air-gapped audio rigs and lab machines — owe it no data. This is a charter-level commitment, not a tunable.
5. ~~Whether the project's canonical repository should host *any* `redistribute = false` formulae in core~~ — **resolved (v1.8): the current allowance stands.** The canonical orchard hosts pointer-only formulae; core tier continues to require `redistribute = true` (§13.1, [ORCHARD-POLICY §12](ORCHARD-POLICY.md#vendor-binary-packages-pkgdmg)) — core never depends on a vendor's server being up.
6. ~~Whether `verified` repositories should install binaries immediately at enable time~~ — **resolved (v1.8): enable implies binaries.** The countersignature ceremony — key pinning, the trust prompt — is the consent; a second click is ceremony without security content ([REPOSITORIES §9](REPOSITORIES.md#amendments-carried-into-the-other-documents)).
7. ~~Whether the `system` capability (§12.7) should ride on the `verified` trust level or be a separate per-repo grant~~ — **resolved (v1.8): it rides on `verified`.** The countersignature vets the maintainers, and the §12.7 flow — per-decision warnings, no "always allow" — is where the ceremony lives. (Contrast #10, one severity level higher, where the answer went the other way.)
8. ~~Service health-check failure behavior~~ — **resolved (v1.4): ask the user.** A failed post-upgrade health check (§12.8, step 5) prompts interactively to roll the generation back and restart the previous version; the default is stay-and-inspect, non-interactive runs fail loudly without rolling back, and `--rollback-on-service-failure` is the explicit unattended path. Silent automatic rollback was rejected: it can mask a good new version behind a transient port conflict, and a package manager that destroys evidence of a failure is harder to trust than one that asks.
9. ~~Project-local dependency directories~~ — **resolved (v1.8): out of scope, permanently.** `.venv`, `vendor/`, `node_modules` remain the ecosystem tools' job; the shim layer binds runtimes and their extensions and stops there. Reimplementing pip/poetry/composer is a non-goal — and the thin convenience layer is how the creep would start.
10. ~~Whether `verified` repositories should ever serve `[system-patch]` packages~~ — **resolved (v1.8): yes, under an explicit per-repo grant.** `aslice repo allow-system-patch <name>` — refused by default, recorded in the state DB, revocable — is the ceremony that *is* security at this severity: the countersignature vets a repository to distribute software, and rewriting the OS warrants one deliberate decision from the machine's owner beyond that vetting. Third-party repositories: never (§12.11; [REPOSITORIES §3](REPOSITORIES.md#trust-levels)).

---

## Appendix A. Specification status

Artifact identity, protected execution, exact replay, and transaction recovery are specified in [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md). Protected-volume activation and restoration are specified in [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). These contracts and their structural fixtures do not establish runtime correctness. Each feature remains gated on its named implementation, security, and platform acceptance tests.

---

## Appendix B. References

- Homebrew 7.0.0 release notes (Intel → Tier 3, 10.15 removal, September 2026): [Homebrew 7 Release And Intel Support](refs/HOMEBREW_7_RELEASE_AND_INTEL_SUPPORT.MD)
- Homebrew Support Tiers (Intel bottle cessation; removal in/after September 2027): [Homebrew Support Tiers](refs/HOMEBREW_SUPPORT_TIERS.MD)
- Homebrew discussion: Intel CI disabled, "no bottle available" (September 2026): [Homebrew Intel Ci Discussion 7044](refs/HOMEBREW_INTEL_CI_DISCUSSION_7044.MD)
- Homebrew Monterey deprecation discussion: [Homebrew Monterey Discussion 5603](refs/HOMEBREW_MONTEREY_DISCUSSION_5603.MD)
- Homebrew history/version table: [Archived source](refs/HOMEBREW_HISTORICAL_OVERVIEW.MD)
- macOS 27 Golden Gate drops Intel (Apple's platform trajectory): [Archived source](refs/OWC_INTEL_MAC_TRANSITION_REPORT.MD)
- The Update Framework: https://theupdateframework.io/
- x86-64 psABI microarchitecture levels: [Archived source](refs/X86_64_MICROARCHITECTURE_LEVELS.MD)

## History

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v1.33 | September 2026 | Replace the example command list in §12.1 with a purpose-grouped public command index linked to owning man pages; complete family coverage and distinguish unspecified interfaces from implemented behavior. No command contracts changed. |
| v1.32 | September 2026 | Specify dependency-driven security remediation, explicit update and origin decisions, and the applicable farm, maintenance, and evidence contracts. Supersedes ABI-only rebuild and cost-first selection policies where previously stated; runtime and measured acceptance remain pending. |
| v1.31 | September 2026 | Describe aslice mechanisms without competitive rankings; align artifact bindings, protected restoration, and self-update commit boundaries, and retarget specification citations. |
| v1.30 | September 2026 | Align guided recovery, mixed-orchard transactions, explicit waiting, post-commit service checks, trusted rebuilding, and unaffected runtime access; link pending engineering decisions and acceptance targets. |
| v1.29 | September 2026 | Integrate six-role SQLite storage, complete solve-cache keys, durable records, and database maintenance commands from DATABASE; runtime implementation remains pending. |
| v1.28 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |
| v1.27 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v1.26 | September 2026 | align user-flag and universal-vendor summaries with STATE-AND-RECOVERY §1–§2: conditional ABI/CPU substitution, distinct artifact identity, and the i386 ceiling based on required execution. |
| v1.24 | September 2026 | owner merge becomes the final human release approval, with automatic signing on a dedicated networked Pi and serialized atomic publication. Automatic targets/snapshot renewal replaces manual renewal; the root remains offline. The manual-release design above is superseded. Services and acceptance drills remain implementation work (KEY-RUNBOOK §2.1, §7); schemas and client signature formats are unchanged. |
| v1.23 | September 2026 | **Superseded design record:** initial signing uses a single owner, separate offline root and release Pis, encrypted backups, and manual release batches. The Mac Pro VM prepares and publishes; multi-party custody and hardware tokens are deferred. KEY-RUNBOOK defines renewal, rotation, recovery, and pre-launch drills; prior custody requirements are superseded. |
| v1.22 | Not recorded | describes the two owned Macs, capability-based scheduling, pending coverage and rebuild gates, the shared-host signing VM boundary, and the proposed Monterey bootstrap baseline (§4.3, §9.3, §14, §15); no CLI or schema change. |
| v1.21 | Not recorded | adds [TOOLCHAIN.md](TOOLCHAIN.md) as the authoritative toolchain document; §4.3 keeps the rationale and points at it — no design change. |
| v1.20 | Not recorded | fills §12.1's gaps, found by the full-corpus review: `aslice plan` and `aslice lock export` (the plan/apply split, §12.2, §12.13, PACKAGE-FORMAT §7), `aslice mark` (§8.4), `aslice profile prefer` (§8.2), `aslice db query` (REPOSITORIES §11), and `aslice help` (MANUAL §14, man/) join the canonical command list; no design change — every verb was already specified where cited). |
| v1.19 | Not recorded | opens **vendor install scripts** — the payload-only rule gains its declared exception: a vendor script is a **graft**, declared in the formula with a **behavior manifest**, approved pnpm-style (interactive prompt recorded in the state DB, allow-list declarable in `aslice-machine.toml`, `--accept-grafts` for unattended runs), sandboxed to its manifest while it runs, captured for generation rollback, and **rehearsed, verified, and signed by the farm** for core and extended — unsigned manifests carry the big fat warning and per-decision consent (§2.1 G9, §2.2 N5, §3, §10.1, §10.4, §10.5, §10.7, §12.1, §12.3, §12.4, §12.7, §13.1, §13.4, §14, §15, new §12.15; schema in PACKAGE-FORMAT v0.15 §3.11; policy in ORCHARD-POLICY §12; trust levels in REPOSITORIES §3; owner decision, September 2026. |
| v1.18 | Not recorded | renames the declarative-setup file and splits its command surface by document kind: `setup.toml` becomes `aslice-machine.toml` — a reserved, self-describing name that other tools can recognize — and its verbs move under the `aslice machine` group (`aslice machine apply` / `export` / `import --from-brewfile`), while top-level `aslice apply` keeps saved plans and lock files only, refusing a machine file with a pointer to the right spelling (§12.13; schema in SETUP.md v0.9; owner decision, September 2026). |
| v1.17 | Not recorded | retires the `abi = true` variant cap: variants are governed by need and honest ABI tags rather than quota — ffmpeg-class packages carry as many codec combinations as users require, including compile-only licenses served as non-default local builds (§13.2, §7.5); the vendor-binary distribution modes lose their license-gate framing, keeping the mechanics and dropping the policing (§9.5, §12.4, §13.1, §15). |
| v1.16 | Not recorded | adds the **orchard-maintenance command group** — `aslice orchard` gains the lifecycle verbs (deprecate / disable / undeprecate / tombstone / rename — the `[deprecation]` table edited by command, validated, linted, and shipped as a PR), orchard-wide health (`lint`, `doctor`, `freshness` — the last computing the days-behind-upstream number ORCHARD-POLICY §9 publishes), the local merge gate (`orchard ci` — §13.4's five gates on the maintainer's machine through the same BUILD-INFRA harness the farm runs), and reverse-dependency impact queries (`orchard dependents` — the ABI blast radius before the PR, not after the merge); §12.1, new §12.14. The §13.3 Homebrew-formula importer is named: `aslice orchard port --from-homebrew`. |
| v1.15 | Not recorded | adds a NOMENCLATURE.md vocabulary reference to the header; no design, schema, or factual changes. |
| v1.14 | Not recorded | is a prose polish in the project's technical-writing voice — six sentences reworded for precision (§1.1, §4.1, §5.3, §7.5, §9.3, §11); no design, schema, or factual changes. |
| v1.13 | Not recorded | is a second editorial pass — sentence-level revision for readability; no design, schema, or factual changes. |
| v1.12 | Not recorded | is an editorial pass — prose revised for directness throughout; no design, schema, or factual changes. |
| v1.11 | Not recorded | adds **declarative whole-machine setup** — `setup.toml`, the unified `aslice apply` verb (plan / lock / setup documents), `aslice export`, and `aslice import --from-brewfile` (§12.13; schema and semantics in [SETUP.md](SETUP.md)); N5's exception list grows to include consent-gated system-preference writes and `/etc/shells` enrollment (§2.2); supersedes the `aslice bundle` wishlist proposal. |
| v1.10 | Not recorded | corrects the GitHub-hosted-CI facts: the `macos-13` Intel image was retired in December 2025, not autumn 2027 — the last hosted Intel label is `macos-15-intel`, available until August 2027 (§1, §9.2, §13 Phase A); adds the per-profile `aslice link`/`unlink` commands for `link = false` shadowing packages (§12.1; PACKAGE-FORMAT §3.8); and records the owner decision that unsigned vendor artifacts may ship in the extended orchard with `signer` omitted — announced loudly at every install — while the core stays signed-only (§12.2, §12.4; schema in PACKAGE-FORMAT §3.11, policy in ORCHARD-POLICY §12). |
| v1.9 | Not recorded | runs the **genesis audit** — a project-wide review of from-nothing bootstrap assumptions: the installer gains a loudly-printed plain-HTTP fallback for TLS-dead machines, fetching the same hash-pinned artifacts (§10.3); the repository tree's vendored-source role is made explicit — every source artifact the farm fetches lives in `blobs/sha256/`, and the client fetch order is upstream → formula `mirrors` → the repository's own blob area, all three under the same pinned sha256 (§9.6; machinery in BUILD-INFRA v0.6, the mirror story in REPOSITORIES v0.8, dead-upstream policy in ORCHARD-POLICY v0.8); the project-hygiene bullet records what actually shipped in Phase 0 — `SECURITY.md`, `CONTRIBUTING.md`, `docs/KEY-RUNBOOK.md`, and deliberately no `CODE_OF_CONDUCT.md` (§13.4); and the from-nothing sequence for the whole project is codified as `docs/GENESIS.md` (§14). |
| v1.8 | Not recorded | lands the review's remaining operational machinery — **self-update** (aslice is package zero: TUF-verified slice, generation swap, supervised activation with retained recovery entry point, automatic rollback — §5.2, §12.12), the **`on_request` install record** and **`aslice clean`** cache eviction (§8.4), the full day-two CLI surface (`outdated`, `reinstall`, package-hold `pin`/`unpin`, `livecheck`, `test`, `create`, `bump-pr`, `exec`, `shellenv`, `store verify` — §12.1), the **system-framework allowlist** (§13.1), and the **merge gates and project-hygiene documents** (§13.4) — and resolves the eight remaining open questions (§15): the prefix gains a per-user `~/.aslice` fallback (§8.1, §10.3), Starlark stays, local `abi = false` builds share store paths with DB-recorded provenance (§5.2), pointer-only formulae keep their current allowance, verified repositories keep enable-implies-binaries and the `system` capability, project-local dependency directories stay out of scope, and `verified` repositories may serve `[system-patch]` under an explicit per-repo grant (§12.11). |
| v1.7 | Not recorded | extends trust-store management and amends a founding line: `aslice ca-update --crypto` upgrades the crypto-provider slices (modern ciphers/TLS for userland, with SecureTransport's limits printed, never hidden), `--apple-certs` imports Apple's own roots — which Mozilla's program does not carry — from a pinned `apple-roots` slice into the System keychain; and the absolute "never touch the system" stance becomes a declared exception: **`[system-patch]` packages** (§12.11) may replace Apple-provided files through a backup + profile-symlink + generation-rollback mechanism — consent at every decision point, official/local repositories only, refused paths blocked by construction (§2.2 N5, §10.4, §10.7, §12.10, §12.11, §13.1). |
| v1.6 | Not recorded | adds **trust-store management** — `aslice ca-update`: the CA bundle becomes an ordinary signed, generation-managed slice (`ca-certificates`), its source configurable with the Mozilla root program (via curl's caextract) as the default; profile env wiring heals userland TLS (curl, git, python) completely; and an opt-in `aslice ca-update --keychain` imports the missing modern roots into the **System keychain** through `aslice-system` — machine-wide healing for Safari, Mail, and every SecureTransport app, recorded to the certificate and reversible to the certificate (§4.1, §12.6, §12.10). |
| v1.5 | Not recorded | adds **first-class multi-version runtime management** — the Volta lesson, taken seriously: version switching is the package manager's job, not a second tool's. A shim layer multiplexes versioned runtimes (php, nodejs, ruby, python, …) by session (`aslice use`), project (`aslice pin`), and default (`aslice default`) selections; interpreter-target tools like composer and yarn **ride** the selected runtime; and compiled extensions are slices bound to the runtime's ABI epoch, so an extension is always installed for exactly one runtime version — as are pip/gem/npm/pecl installs, through per-version userbases (§8.5, §12.9; schema in PACKAGE-FORMAT v0.5 §3.13). |
| v1.4 | Not recorded | resolves open question #8: a failed post-upgrade service health check **asks the user whether to roll back** — an interactive prompt (default: stay and inspect) that swaps the generation back and restarts the previous service version on assent; non-interactive contexts never prompt and never auto-rollback, with `--rollback-on-service-failure` as the explicit unattended path (§12.1, §12.8). |
| v1.3 | Not recorded | adds **launchd-native service management**: packages describe services declaratively in the manifest (`[service]`, PACKAGE-FORMAT v0.4 §3.8), `aslice service` provides status/start/stop/restart over real launchd jobs, and upgrades orchestrate stop → atomic swap → restart so a running service is never updated out from under itself (§8.3, §10.4, §12.1, §12.8). Root-domain daemons go through `aslice-system` and the repository `system` capability; user agents stay unprivileged and ungated. |
| v1.2 | Not recorded | opens a narrowly-scoped **system-software category**: kernel extensions and SIP-disabled development software become installable as declared `[system]` packages — warned at every decision point, elevated per-operation by a dedicated helper, gated by repository trust level — replacing the blanket rejection with an honest, reversible install path (§10.4, §10.7, §12.1, §12.7, §13.1). |
| v1.1 | Not recorded | specifies **`aslice doctor`**: a read-only, scriptable sanity battery — machine, store, profiles, database, repositories, coexistence, environment — where every fail names its remedy and `--fix` is narrow and loud (§12.6). |
| v1.0 | Not recorded | adds the **logging design**: structured, local-only operation logs with a message-quality standard — every error is actionable, security events are unsuppressible, and nothing ever leaves the machine (§5.2, §8.1, §12.1, §12.5). |
| v0.9 | Not recorded | adds **cross-repository overlap resolution**: ambiguous bare package names prompt the user, the decision is remembered in the SQLite state database, revalidated on repo changes, and scriptable via `aslice repo prefer` (§9.6, §12.1; REPOSITORIES.md §10–§11). |
| v0.8 | Not recorded | completes the repository story: a **shipped official source list**, **inherent trust levels** (official / verified / third-party / local — enforced capabilities, not labels), and **dual signature schemes** — Ed25519/minisign canonical, OpenPGP (GPG) built-in first-class for third-party ecosystems (§9.6, §10.2; full spec in [REPOSITORIES.md](REPOSITORIES.md)). |
| v0.7 | Not recorded | adds the **build-infrastructure design**: one harness — `aslice build` on a user's machine, `aslice farm` on the farm — running the identical sandboxed pipeline at both scales (§5.1, §9.3; full spec in [BUILD-INFRA.md](BUILD-INFRA.md)). |
| v0.6 | Not recorded | opens **32-bit vendor binaries**: i386 and universal pkg/dmg payloads install on the releases that still execute 32-bit code (10.11–10.14) — distributed, never built (§2.2 N6, §12.4; PACKAGE-FORMAT v0.3). |
| v0.5 | Not recorded | adds the **repository system** (§9.6) and **vendor binary packages**: software that only ships as a `.pkg`/`.dmg`, hosted or vendor-fetched, installed without ever running installer scripts (§12.4; schema in PACKAGE-FORMAT v0.2 §3.11). |
| v0.4 | Not recorded | sharpens it: **download counts are rejected as a value signal too** — on a deprecated-OS platform, obscure ≠ low-value (§9.4). |
| v0.3 | Not recorded | resolves open question #4: **aslice collects no telemetry or analytics of any kind, ever** — the project is infrastructure, not a product (§2.2 N7, §9.4, §15). |
| v0.2 | Not recorded | extends the platform floor from 10.15 (Catalina) to 10.11 (El Capitan) — see §4 for the consequences (three flavors, self-hosted toolchain in Phase 0, HFS+ support). |
| Not recorded | September 2026 | corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending. |

</details>
