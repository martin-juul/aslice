# aslice — A Package Manager for Intel macOS

**Name.** *aslice* — an apple slice: a nod to the Macintosh apple and to the shape of the project itself. Binary packages are **slices**; formula repositories are **orchards**; the manager picks slices off the orchard, prebuilt or baked to order. The vocabulary is deliberately distinct from Homebrew's beer terminology to avoid community confusion and trademark friction. The project name is styled lowercase everywhere, including sentence starts — like the command.

- **Status:** Design draft, v1.4 — September 2026
- **Change log:** v0.2 extends the platform floor from 10.15 (Catalina) to 10.11 (El Capitan) — see §4 for the consequences (three flavors, self-hosted toolchain in Phase 0, HFS+ support). v0.3 resolves open question #4: **aslice collects no telemetry or analytics of any kind, ever** — the project is infrastructure, not a product (§2.2 N7, §9.4, §15). v0.4 sharpens it: **download counts are rejected as a value signal too** — on a deprecated-OS platform, obscure ≠ low-value (§9.4). v0.5 adds the **repository system** (§9.6) and **vendor binary packages**: software that only ships as a `.pkg`/`.dmg`, hosted or vendor-fetched, installed without ever running installer scripts (§12.4; schema in PACKAGE-FORMAT v0.2 §3.11). v0.6 opens **32-bit vendor binaries**: i386 and universal pkg/dmg payloads install on the releases that still execute 32-bit code (10.11–10.14) — distributed, never built (§2.2 N6, §12.4; PACKAGE-FORMAT v0.3). v0.7 adds the **build-infrastructure design**: one harness — `aslice build` on a user's machine, `aslice farm` on the farm — running the identical sandboxed pipeline at both scales (§5.1, §9.3; full spec in [BUILD-INFRA.md](BUILD-INFRA.md)). v0.8 completes the repository story: a **shipped official source list**, **inherent trust levels** (official / verified / third-party / local — enforced capabilities, not labels), and **dual signature schemes** — Ed25519/minisign canonical, OpenPGP (GPG) built-in first-class for third-party ecosystems (§9.6, §10.2; full spec in [REPOSITORIES.md](REPOSITORIES.md)). v0.9 adds **cross-repository overlap resolution**: ambiguous bare package names prompt the user, the decision is remembered in the SQLite state database, revalidated on repo changes, and scriptable via `aslice repo prefer` (§9.6, §12.1; REPOSITORIES.md §10–§11). v1.0 adds the **logging design**: structured, local-only operation logs with a message-quality standard — every error is actionable, security events are unsuppressible, and nothing ever leaves the machine (§5.2, §8.1, §12.1, §12.5). v1.1 specifies **`aslice doctor`**: a read-only, scriptable sanity battery — machine, store, profiles, database, repositories, coexistence, environment — where every fail names its remedy and `--fix` is narrow and loud (§12.6). v1.2 opens a narrowly-scoped **system-software category**: kernel extensions and SIP-disabled development software become installable as declared `[system]` packages — warned at every decision point, elevated per-operation by a dedicated helper, gated by repository trust level — replacing the blanket rejection with an honest, reversible install path (§10.4, §10.7, §12.1, §12.7, §13.1). v1.3 adds **launchd-native service management**: packages describe services declaratively in the manifest (`[service]`, PACKAGE-FORMAT v0.4 §3.8), `aslice service` provides status/start/stop/restart over real launchd jobs, and upgrades orchestrate stop → atomic swap → restart so a running service is never updated out from under itself (§8.3, §10.4, §12.1, §12.8). Root-domain daemons go through `aslice-system` and the repository `system` capability; user agents stay unprivileged and ungated. v1.4 resolves open question #8: a failed post-upgrade service health check **asks the user whether to roll back** — an interactive prompt (default: stay and inspect) that swaps the generation back and restarts the previous service version on assent; non-interactive contexts never prompt and never auto-rollback, with `--rollback-on-service-failure` as the explicit unattended path (§12.1, §12.8)
- **Scope:** macOS 10.11 (El Capitan) through 12 (Monterey), Intel x86_64 only
- **Implementation:** C++20 core, single self-contained binary
- **Audience:** Maintainers, founding contributors, and early reviewers

---

## 1. Context and Opportunity

### 1.1 The gap that is opening

The Intel-Mac package-management ecosystem is losing its maintainer on a known schedule:

- **Homebrew 7.0.0 (September 2026)** moved Intel x86_64 to Tier 3 ("not supported"): no new bottles are built for Intel, CI coverage is gone, and macOS 10.15 support was removed outright. Existing bottles stay hosted but freeze in time.
- **September 2027:** Homebrew plans to remove the ability to run on Intel systems at all.
- **Autumn 2027:** GitHub Actions retires its Intel macOS runners (`macos-13` images), eliminating the last hosted CI capable of natively building x86_64 macOS binaries. This is one of the explicit reasons Homebrew cites for its exit.
- **Apple:** macOS 26 Tahoe is the final release for Intel Macs; macOS 27 Golden Gate is Apple-silicon-only. Intel Macs receive security updates only, on a countdown.

Meanwhile a large installed base remains: Homebrew's own analytics, discussed publicly in mid-2026, put Intel at roughly a quarter of active Homebrew Mac installations. Everything from El Capitan to Monterey is now outside Homebrew's support window — and precisely where these machines are stranded.

### 1.2 Who the users are

Three populations, all underserved:

1. **Owners of 2012–2020 Intel Macs** used as daily drivers, home servers, audio rigs, and build machines. Many are maxed-out machines (Mac Pro 2013, iMac 5K, 16" MBP 2019) that remain genuinely capable.
2. **CI and legacy-maintenance shops** that must keep building and testing x86_64 macOS software through Tahoe's support window.
3. **Retro, audio, lab, and 32-bit-dependent environments** pinned to older releases. Catalina dropped 32-bit app support entirely; 10.11–10.14 are the last releases that run 32-bit software, classic audio drivers, and legacy pro tools — which is exactly why their users stay. Today these users are served only by MacPorts' best-effort legacy coverage. Vendor-binary packages (§12.4) meet them where they live: 32-bit and universal pkg/dmg payloads install cleanly on precisely these releases.

### 1.3 Why not MacPorts or Nix?

Both are suggested by Homebrew itself as migration paths. Both leave the opening intact:

| | MacPorts | Nix (via Determinate/nixpkgs) |
|---|---|---|
| Binary coverage for 10.11–12 Intel | Partial, shrinking; builds from source as the norm | x86_64-darwin support degrading; Hydra builds for old OS releases not a goal |
| Variant/flag model | Excellent (`+variants`) — but every variant is a local compile | Binary cache keyed on exact derivation; any flag change = full local rebuild |
| UX | Functional but austere | Steep learning curve |
| Philosophy | Build on the *target* OS version | Hermetic, prefix-independent |

The opening is a manager that combines **Homebrew's ergonomics**, **MacPorts' variant flexibility**, and **Nix's correctness ideas** (store paths, generations, atomic switching) — scoped tightly to a platform the incumbents are vacating, small enough to be excellent.

### 1.4 Design thesis

> **One OS axis collapses; one µarch axis matters. Variants are safe if you separate ABI from optimization. Security comes from making packages declarative and installs code-free.**

Each clause is developed in its own section below.

---

## 2. Goals and Non-Goals

### 2.1 Goals

- **G1 — Full coverage of macOS 10.11 through 12 on Intel**, treated as first-class citizens, not legacy tiers.
- **G2 — Three µarch flavors:** `v1` (SSE2 baseline — every 64-bit Intel Mac), `v2` (SSE4.2/POPCNT), and `v3` (AVX2 — Haswell and later). See §4.
- **G3 — Precompiled binaries for the common flavors**, hosted on GitHub infrastructure with a mirror-friendly fallback. Default install path is binary and near-instant.
- **G4 — User-selectable build flags and feature variants** with local compilation — *without* forfeiting interoperability with prebuilt packages (§7).
- **G5 — A materially better security model than Homebrew's** (§10): declarative package definitions, sandboxed builds, signed everything, code-free binary installs, no `/usr/local` chown, no sudo in steady state.
- **G6 — A materially better performance profile** (§11): sub-10 ms CLI startup, parallel solver and downloads, zstd payloads, APFS-aware linking.
- **G7 — Atomic, rollback-capable installations** via generations (§8).
- **G8 — Low maintainer burden.** The platform is frozen by Apple; the design exploits that stability instead of fighting it (§15).
- **G9 — Vendor-binary coverage.** Software that only exists as a `.pkg`/`.dmg` — vendor CLIs, commercial audio tools, frozen apps — installs through the same store, generations, and lock files as everything else, without ever executing installer scripts (§12.4).

### 2.2 Non-goals

- **N1 — Apple Silicon.** Not now, not by accident. The architecture must not preclude it, but no engineering effort goes to it. Homebrew owns that space.
- **N2 — macOS 13+ on Intel.** Tahoe-era Intel machines (2019–2020) are welcome, but the build targets remain 10.11–12; Ventura+ Intel gets whatever falls out naturally.
- **N3 — GUI application *polish* at launch.** Vendor-binary packages (§12.4) cover `.pkg`/`.dmg`-only software — CLI tools and apps alike. What is deferred is app-specific chrome: Launchpad integration, updater handoff, a GUI manager. Core CLI packages still come first.
- **N4 — Linux/Windows.** The codebase should stay portable, but no effort is spent there.
- **N5 — Replacing the system.** aslice never touches `/usr`, `/System`, or `/usr/local`'s ownership. It lives in its own prefix.
- **N6 — 32-bit *builds*.** Every Mac that can run 10.11 is 64-bit capable, so aslice *builds* x86_64-only slices: no i386 flavor, no 32-bit toolchain work, no multilib. **32-bit vendor payloads are a different matter** (v0.6): a pkg/dmg shipping i386 or universal binaries installs on the releases that can still execute them — 10.11 through 10.14, which is exactly why many of these machines are kept at all (§12.4). The line is compile vs. distribute: we never *build* 32-bit, we gladly *install* it where the OS allows.
- **N7 — Metrics.** No telemetry, analytics, install IDs, crash reporting, or usage instrumentation of any kind — not even opt-in. aslice is infrastructure, not a product. Prioritization signals come from maintainers and the community, never from users' machines (§9.4).

---

## 3. Positioning: "What Homebrew Could Not"

Homebrew's structural constraints — not its maintainers — produced its weaknesses. aslice's founding decisions target each one:

| Homebrew constraint | Consequence | aslice's founding decision |
|---|---|---|
| Formulae are arbitrary Ruby executed at install time | Taps and `post_install` are a code-execution supply chain; audit is impossible to automate fully | Formulae are **declarative TOML + hermetic Starlark build scripts** (§6); binary installs execute **zero** package code (§10.3) |
| Bottles exist only for default options; `homebrew-core` removed options entirely (v2.0, 2019) | Users needing flags lose binaries *and* break interop | **ABI-aware variant model** (§7): optimization flags never affect identity; feature flags affect it only when they change the exported interface |
| One linked version per package in the Cellar | Upgrades are destructive; rollback is archaeology | **Store paths + generations** (§8): any number of variants coexist; switching is atomic |
| Prefix ownership of `/usr/local` chowned to the user | Security researchers have criticized this for a decade | Private prefix `/opt/aslice`, created once by an installer, never world-writable, never sudo thereafter (§10.4) |
| Ruby runtime, git-cloned taps | Slow startup, slow `brew update` | Single C++ binary, content-addressed TUF-signed index with snapshot diffs (§11) |
| CI hostage to GitHub-hosted Intel runners | The current collapse | **Self-hosted build farm on real Intel hardware** from day one (§9.3) |
| Opt-out usage analytics | Consent assumed; users are a metrics pipeline | **No telemetry or analytics of any kind, ever** — aslice is infrastructure, not a product (§2.2 N7) |
| Casks may run `installer script:` and vendor pkg hooks | Arbitrary vendor code with user (or admin) privileges at install | **Vendor binaries install payload-only** (§12.4): pkg/dmg contents are extracted per a declarative map, signer-pinned, and embedded scripts never execute |

---

## 4. Platform Matrix and Microarchitecture Strategy

### 4.1 The OS axis collapses — at 10.11

Naively, 5 OS versions × 3 µarch flavors = 15 builds per package. In practice it is **3**:

macOS has a mature deployment-target mechanism. A binary compiled with `-mmacosx-version-min=10.11` runs correctly on every release from El Capitan through Monterey, provided it avoids (or weak-links against) newer APIs. So the default remains: **build once against the oldest target, per µarch flavor** — the floor is simply 10.11 now instead of 10.15.

The lower floor has real consequences, and they are handled explicitly:

- **A wider `min_os` spread.** Many modern upstreams cannot cleanly target 10.11: C++17/20 library features, `clock_gettime` and friends (absent before 10.12), `thread_local` quirks, modern IPC. Formulae declare `min_os` honestly; the index filters per OS. Expect a natural stratification — the core orchard mostly at a 10.11 floor, much of the extended orchard at 10.12–10.14 floors. A package that *could* build for 10.11 but isn't worth the patching declares its floor and moves on: loud honesty over heroics.
- **libc++ comes from the toolchain, not the system.** System libc++ on 10.11 predates half of C++17. All C++ packages statically link a modern libc++ from `aslice-toolchain` (§4.3), so the age of the system runtime stops mattering.
- **HFS+ is back in the window.** 10.11–10.12 predate APFS entirely, and HDDs stayed HFS+ into the Mojave era. Everything filesystem-dependent degrades gracefully: `clonefile` → hardlink → copy (§11), and generation switching relies on `rename(2)`, which is atomic on HFS+ as well.
- **Ancient TLS and expired root certificates** make the 10.11–10.13 system trust store nearly unusable for the modern web. `aslice-fetch` links its own TLS stack and CA bundle and verifies against pinned, countersigned hashes regardless — the security model never depended on the system store.

### 4.2 The µarch axis grows: three flavors

Extending the floor to 10.11 pulls pre-SSE4 CPUs into the supported population, so the flavor space grows from two to three. aslice adopts the x86-64 psABI microarchitecture levels as its flavor vocabulary:

| Flavor | Level | Key ISA | Who needs it |
|---|---|---|---|
| `v1` | x86-64 baseline | SSE2 | Runs on every 64-bit Intel Mac; the *only* choice for Core 2 Duo machines (2007–2009, Merom/Penryn) found on 10.11–10.13 |
| `v2` | x86-64-v2 | SSE4.2, POPCNT | Nehalem/Westmere and later — Mac Pro 2009+, most 2010+ Macs, and everything Catalina-capable |
| `v3` | x86-64-v3 | AVX2, BMI2, FMA | Haswell+ (2014→); 10–40% faster on codecs, crypto, compression, math |

Notes:

- **x86-64-v4 (AVX-512) is deliberately absent.** No Intel Mac ever shipped AVX-512. The flavor space is exactly three, keeping the binary matrix and the UX small.
- **Detection** is a sysctl ladder at install time: `hw.optional.avx2_0` → `v3`; else SSE4.2+POPCNT via `machdep.cpu.features` → `v2`; else `v1`. The manager itself is built `v1` (it gains nothing from vector ISAs) and selects flavors on the user's behalf; `aslice config set flavor v1` overrides downward.
- **The solver picks the highest flavor the hardware runs** and treats flavor as a hard constraint, not a preference — a `v3` slice on a Core 2 Duo is a solve-time conflict with a clear message, never a SIGILL at runtime.
- Flavor interaction with `min_os` is orthogonal: a Haswell iMac happily runs 10.11, so `v3` + `min_os 10.11` is a real, served combination.

### 4.3 Toolchain floor — self-hosted from day one

Extending to 10.11 changes the toolchain story from "convenience" to "load-bearing":

- **Modern hosted Xcode can't reach 10.11.** Xcode 15-era toolchains no longer accept deployment targets below ~10.13, and GitHub's hosted Intel runners never ship anything older. Therefore `aslice-toolchain` — modern Clang, LLD where viable (ld64 from cctools-port otherwise), modern libc++, CMake, Ninja, pkgconf — moves from Phase 2 to **Phase 0** and is the authoritative build toolchain for all packages.
- **Targeting darwin15 from a modern Clang works** (`-mmacosx-version-min=10.11` is still accepted; Clang's target floor is far older than libc++'s). The constraint is the C++ runtime, which is why the toolchain statically links its own libc++ into everything it produces.
- **The package manager core** is C++20 built with this self-hosted toolchain: static libc++ and third-party libraries, dynamically linking only `libSystem`. One Mach-O binary runs on 10.11–12 with zero runtime dependencies. (Fully static linking is impossible on macOS — `libSystem` must be dynamic — but nothing else need be.)
- **Bootstrap path:** build the toolchain on the newest available Intel macOS against the oldest archived SDK, with per-OS workarounds recorded in the toolchain's manifest; then rebuild the toolchain with itself. Build VMs run 10.11/10.12/10.13/10.14/10.15/11/12 guests on the farm (§9.3) so every claimed target is continuously tested, not assumed.

---

## 5. Core Architecture

### 5.1 Process layout

```
aslice (single binary, unprivileged)
 ├── aslice-fetch     ── sandboxed helper: network + disk cache only
 ├── aslice-extract   ── sandboxed helper: archive extraction only
 ├── aslice-build     ── sandboxed helper: runs Starlark build scripts
 └── aslice-link      ── the only component that writes the store/profile
```

Privilege separation is structural: the helpers are separate executables (spawned by the main binary, which re-executes itself with a subcommand) running under Seatbelt profiles (§10.5) with exactly the capabilities their phase requires. The fetch helper can't touch the store; the extractor has no network; the linker has no network and no compiler. Each helper is small (a few hundred lines) and independently auditable — this is where the C++ attack-surface discipline pays for itself. `aslice-extract` is also the component that expands vendor `.pkg` (xar) and `.dmg` payloads (§12.4) — archive and installer-payload handling are the same trust problem and get the same tiny, fuzzed code path. The same helpers are what the build farm executes: the farm harness is an orchestrator that spawns `aslice build` jobs, and every build — farm or laptop — runs through this identical sandboxed executor (full design: [BUILD-INFRA.md](BUILD-INFRA.md)).

### 5.2 Major components

| Component | Responsibility | Notes |
|---|---|---|
| **Index client** | Fetches and caches the package index | TUF metadata + zstd-compressed JSON snapshots; incremental updates via snapshot diffs, not git |
| **Solver** | Version + variant resolution | PubGrub-style CDCL algorithm over (name, version, variant) space; flavors as hard constraints (§7.5) |
| **Store** | Content- and identity-addressed package trees | `/opt/aslice/store/<name>-<version>-<buildid>/` (§8) |
| **Profiles / generations** | Atomic merged views | Symlink forests with rename-swap; rollback = flip a symlink (§8.3) |
| **Builder** | Fetch→unpack→patch→configure→build→install in sandbox | Deterministic environment; DESTDIR staging; ABI scan on output (§7.3) |
| **Verifier** | Signature, hash, ABI, and policy checks before linking | Nothing reaches the profile without passing (§10.2) |
| **Database** | Installed-set and metadata | Single SQLite file, WAL mode, prepared statements; the only mutable state besides the store. Holds the installed set, per-repo key pins and trust levels, remembered overlap resolutions, solve cache, and operation history ([REPOSITORIES.md](REPOSITORIES.md) §11) — records decisions and state, never grants authority; verification never consults it for trust |
| **Reporter** | SBOM generation, `audit`, provenance display | SPDX SBOM per package; OSV feed integration (§10.6) |
| **Logger** | Structured operation and security-event logging | JSONL on disk under `log/`, human rendering on the terminal; local-only, forever (§12.5) |

### 5.3 Why C++ — and what it costs

The user-facing case for C++ is startup time, single-binary deployment across 10.11–12 with no runtime story, direct Mach-O/dyld/Seatbelt API access, and world-class tooling for the performance goals. The honest cost is memory safety, which is a security-goal liability. aslice treats that as an engineering constraint, not an embarrassment:

- **Disciplined subset:** no owning raw pointers (RAII everywhere, `std::unique_ptr`/`shared_ptr` at boundaries), bounds-checked views (`std::span`, `string_view` with explicit lifetime rules), no C arrays, no `str*`/`mem*` libc string calls, exceptions banned across module boundaries.
- **Hardened build:** `-fstack-protector-strong -fstack-clash-protection -D_FORTIFY_SOURCE=2` (via libc++ equivalents), full RELRO-analog (`-Wl,-bind_at_load` where tolerable), PIE, CFI under LTO (`-fsanitize=cfi`) for release builds once lld/ld64 support is verified per-OS.
- **CI sanitizers:** every PR runs the test suite under ASan+UBSan on both flavors; parsers and the archive extractor are continuously fuzzed with libFuzzer — formula parsing, manifest parsing, tar/zip/**xar**/cpio extraction, and the index parser are all *untrusted-input surfaces* and are treated accordingly.
- **The trust-critical helpers are tiny.** fetch/extract/link together are the only code paths that touch hostile data with ambient authority, and each is kept small enough to review line-by-line.

---

## 6. Package Format

### 6.1 Formulae are data, with a hermetic build script

*The authoritative schema is [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md); this section is the guided tour.*

An aslice package is a directory in an orchard — a git repo of formula directories (what Homebrew calls a *tap*):

```
orchards/core/ffmpeg/
 ├── package.toml      # metadata, sources, dependencies, variants
 ├── build.star        # Starlark build script (sandboxed, no IO escape)
 ├── patches/          # optional, checksummed
 └── tests.star        # optional smoke tests
```

`package.toml`:

```toml
[package]
name        = "ffmpeg"
version     = "7.1"
revision    = 0
license     = "LGPL-2.1-or-later"
description = "Play, record, convert, and stream audio and video"
homepage    = "https://ffmpeg.org"

[source]
url    = "https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz"
sha256 = "40973d449e3c3a4a551b3e2e05f5a28f8ff74a2f2e0c2e6ec4f7f4b9c0f2a1c9"
# mirrors = ["https://mirror.example/..."]   # optional fallback mirrors

[variants.x265]          # feature variant
default = true
abi     = true           # changes exported interface → part of build identity (§7)
description = "HEVC encoding via x265"

[variants.debug]
default = false
abi     = false          # optimization/debug flags never affect identity
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

- **No Turing-complete host code at install time.** Starlark executes only during *builds*, inside the sandbox, with capabilities enumerated in `ctx`. There is no `post_install` hook that runs on the user's machine — post-install behavior (creating data dirs, registering launch agents) is expressed declaratively in `package.toml` and executed by aslice itself. (Homebrew 7.0 is migrating the same direction with `*_steps`; aslice simply starts there.)
- **Everything is pinned.** Source URLs carry hashes; patches are checksummed files; the index records the full closure.
- **Variants are declared, typed, and ABI-tagged** by the package author — the foundation of the interop model in §7.
- **Vendor binaries are the same format, minus the build.** `type = "binary"` packages describe a `.pkg`/`.dmg` artifact with per-OS tags, a pinned signer, and a declarative payload map — no `build.star`, no executed scripts (§12.4, PACKAGE-FORMAT §3.11).

### 6.2 Binary package format (`.slice`)

A binary package — a **slice** — is:

```
ffmpeg-7.1-0+core.v3.2f4a9c1e.slice
 ├── manifest.json     # identity, ABI contract, file list w/ hashes, SBOM, provenance
 ├── payload.tar.zst   # the tree, zstd-19 --long compressed
 └── signature         # minisign/cosign signature over the above (§10.2)
```

Install of a `.slice` is: verify signature → verify payload hashes → extract into store path → ABI-check against the packages that will link to it → register in SQLite → link into profile. **No code from the package executes at any point.** A repackaged vendor binary produces exactly the same `.slice` shape — its manifest's provenance section records the vendor artifact hash and signer instead of a build recipe.

---

## 7. The Variant and ABI Model — Interoperability by Design

This is the section that answers "package interoperability should still be available" and "what Homebrew could not." Homebrew's experience is the cautionary tale: options in `homebrew-core` were removed in 2019 because every variant combinatorially broke bottle assumptions and support load. aslice's answer is to make the distinction Homebrew never formalized: **what changes the ABI versus what merely changes the bits.**

### 7.1 The three kinds of build-time choice

| Kind | Examples | Effect on identity | Effect on interop |
|---|---|---|---|
| **µarch flavor** | `v1` / `v2` / `v3` | Hard selection constraint | ABI-identical; a higher-flavor binary just won't *run* on lesser hardware |
| **Optimization flags** | `-O2`/`-O3`, `-march=native`, LTO | **None** | ABI-identical by construction; freely substitutable |
| **Feature variants** | `+x265`, `+ssl` vs `+gnutls`, `+shared` | Only when `abi = true` | Changes exported interface → tracked in the ABI contract |

### 7.2 Build identity

```
build_id = base32(sha256(canonical_json({
    name, version, revision,
    abi_variants,          # only variants declared abi = true
    flavor,                # v1 | v2 | v3
    min_os,                # 10.11 | 10.12 | … | 12
    toolchain_id,          # e.g. "clang-19-10.11"
})))[:10]
```

Deliberately **absent** from the hash: `-O` level, `-march` beyond the flavor floor, debug info, build timestamps, build host. Two builds of the same formula with the same ABI variants are the *same identity* even if one was built by the build farm with `-O2` and one by the user with `-O3 -march=native`. They are interchangeable everywhere.

For `type = "binary"` vendor packages nothing is compiled, so `flavor` and `toolchain_id` drop out of the identity and the artifact's sha256 effectively *is* the input identity — one slice serves all flavors, tagged only with the vendor's OS-support bounds (§12.4).

Note what this does *not* do: it does not hash the dependency closure (the Nix model). Nix's approach gives perfect hermeticity at the cost of making substitution impossible whenever any dependency differs — exactly the interop failure the user wants to avoid. aslice instead gets interop from the ABI contract below.

### 7.3 The ABI contract (the Mach-O insight)

macOS already ships the world's most underrated interop mechanism: **Mach-O install names with compatibility versions.** Every dylib records an install name and a `compatibility_version`/`current_version`; every client records what it linked against. dyld enforces it at load time. aslice formalizes what the linker already knows:

At build time, `aslice-build` runs an **ABI scan** on the staged output and records in the manifest:

```json
"abi": {
  "provides": [
    { "install_name": "@rpath/libavcodec.61.dylib",
      "compatibility_version": "61.0.0",
      "symbols_sha256": "9be4…",       # nm-derived symbol-set fingerprint
      "arch": "x86_64" }
  ],
  "requires": [
    { "install_name": "@rpath/libx264.164.dylib",
      "min_compat": "164.0.0" }
  ]
}
```

Substitution rule: a package P satisfies dependency D iff P provides the required install name with `compatibility_version ≥ D.min_compat` **and** the symbol fingerprint covers D's referenced symbols. The scan uses `otool`/`nm` output plus DWARF-based ABI diffing (libabigail-style) for C++ packages, where symbol presence alone understates breakage.

Consequences:

- **Mix prebuilt and self-compiled freely.** Your `-O3 -march=native` ffmpeg and the build farm's `-O2` x264 interop because the contract, not the provenance, governs linking.
- **Breakage is caught at install time, not at runtime** three weeks later. If a rebuilt library no longer covers what its clients reference, the solver refuses the combination and tells you exactly which symbol set regressed.
- **`abi = true` variants partition the space correctly.** `ffmpeg+x265` and `ffmpeg-x265` are different build identities and can coexist in the store; dependents record which one they were linked against.
- **Vendor binaries participate too.** The ABI scan runs on a vendor package's payload at pack time, so a vendor dylib satisfies dependents through the same contract as a farm-built one (§12.4).

### 7.4 User flags

```
aslice install ffmpeg --variant +x265 --cflags="-O3 -march=native" --lto
```

- `--cflags`/`--ldflags`/`--lto`/`--debug` → local source build of **that package only**; dependencies still resolve to binaries when their contracts are satisfied. Flags are recorded in the manifest for provenance but **never** enter the build identity (§7.2) — the result remains a valid dependency for everything else on the machine.
- `--variant ±x` where `x` is `abi = true` → new build identity; source build unless a matching slice exists (community orchards may publish popular non-default variants).
- `--variant ±x` where `x` is `abi = false` → local build, same identity.
- A package tree of user-flag builds is tracked (`aslice leaves --user-built`) and survives upgrades — the solver reuses the recorded flag set when a new version appears.

### 7.5 The solver

Version+variant resolution uses a PubGrub-style CDCL algorithm:

- **Terms** are (package, version-range, variant-assignment, flavor).
- **Flavor is a hard constraint** injected from hardware detection — a v3 flavor on a v2 machine is a conflict at solve time with a clear message, never a SIGILL at runtime.
- **Binary-first preference:** among valid solutions, the solver maximizes use of available slices (objective: minimize local builds, then minimize download size, then maximize versions). `--prefer-source` flips the objective.
- **Deterministic and explainable:** every resolution emits a human-readable derivation tree (`aslice install --explain ffmpeg` shows why each version/variant was chosen). Solve results are cached in SQLite keyed by index snapshot hash; typical repeated solves are sub-millisecond.

The variant domain per package is small by policy (§13.2 limits `abi = true` variants to what maintainers will support), so the combinatorial explosion that killed Homebrew options stays boxed in.

---

## 8. Store, Profiles, and Generations

### 8.1 Layout

```
/opt/aslice/
 ├── store/
 │    ├── ffmpeg-7.1-0+core.v3.2f4a9c1e/
 │    ├── ffmpeg-7.1-0+core.v2.2f4a9c1e/        # flavors coexist
 │    ├── x264-0.164-0+core.v3.77aa10b2/
 │    └── …
 ├── apps/         # vendor-binary .app bundles (§12.4)
 ├── profiles/
 │    ├── default -> generations/42             # symlink; the live view
 │    └── generations/
 │         ├── 41/  { bin/, lib/, share/, … }   # symlink forests into store
 │         └── 42/
 ├── cache/        # slices, sources, index snapshots
 ├── log/          # structured operation logs (§12.5)
 ├── db/state.sqlite
 └── etc/aslice.toml
```

- **Store paths are immutable.** Nothing inside a store path is ever modified after registration; corruption is detectable by re-hashing against the manifest.
- **Install names use absolute store paths** for libraries whose manifest marks them non-relocatable, and `@rpath` with a managed rpath list for the rest. Because the default prefix is fixed (`/opt/aslice`), the overwhelmingly common case needs **zero path rewriting** — no bottle-relocation pass at install, which is both faster and removes a whole class of tampering surface. Custom prefixes are supported via manifest-recorded relocation metadata (the same approach Homebrew 7.0 adopted), applied by the link helper at install time.
- **Per-user installs** (`~/.aslice` as prefix) are fully supported with rewriting; multi-user shared installs work because profiles, not ownership, define the view.

### 8.2 Profiles as the interoperability surface

A profile is the merged symlink forest (bin/, lib/, share/, …) that users put on PATH: `/opt/aslice/profiles/default/bin`. Because linking is just symlink creation into a generation directory, any combination of store paths — prebuilt, user-compiled, different flavors, old and new versions of different packages — coexists under one view. Collisions (two packages shipping `bin/foo`) are first-class: the profile records priority, and `aslice profile prefer` flips it without touching the store.

### 8.3 Generations: atomic switching and rollback

Every mutating operation builds a **new generation directory** and then swaps one symlink — atomic via `rename(2)` on both APFS and HFS+. This yields, almost for free:

- `aslice rollback [generation]` — instant return to any previous state.
- `aslice switch-generation 38` — bisect a broken upgrade in seconds.
- **Interrupted installs cannot corrupt the live profile.** A crash mid-install leaves the old generation live; the partial new generation is garbage-collected.
- **Services are quiesced around the swap.** An upgrade that touches a package with a running service stops the launchd job first, swaps, then starts it again — the binary is never replaced under a running process (§12.8).
- `aslice gc` removes store paths unreachable from any retained generation (with `--older-than 30d` style policies).

### 8.4 Garbage collection discipline

The store grows unboundedly without GC — the classic Nix complaint. Defaults: keep the last 5 generations, auto-GC on install when store exceeds a configurable watermark (default 20 GB), and never collect a store path referenced by a running process's profile generation. `aslice gc --dry-run` always shows exactly what would go and why.

---

## 9. Distribution and the Build Farm

### 9.1 Hosting on GitHub — two layers, mirror-friendly

**Layer 1: Package blobs as OCI artifacts on GHCR.** Slices are pushed to `ghcr.io/aslice/<name>` as OCI artifacts (ORAS), giving content-addressed blob storage, dedup across versions via shared layers, resumable/ranged downloads, and free bandwidth within GitHub's generous registry limits. Every tag is additionally anchored to a signed manifest digest.

**Layer 2: The index as static, signed files.** The package index (TUF metadata + zstd JSON snapshots) is published both to a GitHub Release asset stream and to `raw`/Pages endpoints, and — critically — is *trivially mirrorable*: any static HTTP server can host a complete aslice repo. Mirror support is a first-class config (`mirrors = [...]`), not an afterthought, because the long-term health of a legacy-platform project cannot depend on one vendor's continued generosity.

**Fallback:** plain GitHub Releases assets (2 GB per asset ceiling — no package comes close) for environments where GHCR auth/rate limits are a problem. The client treats GHCR, Releases, and static mirrors as interchangeable transports for identical, identically-signed content. All three are *transports* for the canonical distribution unit — the **repository tree** (§9.6): a static, signed, mirrorable directory of TUF metadata, index snapshots, formula metadata, and blobs. GHCR is where blobs may live; a repository is what a client actually consumes.

### 9.2 The GitHub CI problem — stated plainly

GitHub-hosted Intel runners are a deprecating asset: `macos-11`/`macos-12` images are already retired, and the `macos-13` Intel image follows in autumn 2027. **Any design whose correctness depends on hosted Intel CI is a dead design.** aslice therefore treats GitHub CI as a convenience layer and the self-hosted farm as the system of record.

### 9.3 The build farm

*The harness that runs on this hardware — identical to what runs on a user's machine — is specified in [BUILD-INFRA.md](BUILD-INFRA.md): job manifests, scheduling lanes, the quarantine/signing trust model, community evidence builders, and VM matrix orchestration. This section is the hardware summary.*

**Phase A (launch):** GitHub-hosted `macos-13` Intel runners, while they exist, cover what hosted Xcode can reach (~10.13+ deployment targets) using the self-hosted toolchain. They are a bonus layer, not the system of record — hosted Xcode can no longer target 10.11/10.12 at all, which is precisely why the farm below exists. AVX2 (`v3`) builds compile fine on any Intel runner (compiling AVX2 code doesn't require executing it); *tests* for v3 slices run on AVX2 hardware only, while `v1` and `v2` slices test everywhere.

**Phase B (the durable answer): self-hosted runners on real hardware**, enrolled as GitHub Actions self-hosted runners (or Buildkite/Forgejo runners if GitHub's self-hosted macOS story degrades):

| Role | Hardware | Notes |
|---|---|---|
| `v1` tester | Oldest available Core 2 Duo (2007–2009 MacBook/iMac/mini) when obtainable; otherwise the 10.11 VM | v1 slices run everywhere, so this exists to *test*, not to build |
| `v2` builder + tester | Mac Pro 2013 or Mac mini 2012 (Ivy Bridge) | The no-AVX2 population on 10.14+ |
| `v3` builder + tester | Mac mini 2018 (Coffee Lake) — cheap, ECC-less but reliable, AVX2 | Workhorse; 2–4 units |
| OS coverage | VMware Fusion / Parallels VMs: 10.11, 10.12, 10.13, 10.14, 10.15, 11, 12 guests | Apple's license permits macOS VMs on Apple hardware; two Mac mini 2018s host the full seven-release matrix |
| Signing | Offline root key; online signing key on an air-gapped-adjacent Mac mini with YubiKey-backed key custody | §10.2 |

Estimated launch cost: under US$3,000 of used hardware plus power. This is the entire reason the project is feasible at hobbyist scale: **the platform is frozen.** No new macOS releases to chase, no new SDK churn, no Apple-silicon treadmill. The farm builds against a fixed target forever, and volunteer effort goes to packages, not platform firefighting. This inverts the dynamic that exhausted Homebrew's maintainers.

### 9.4 What gets prebuilt

- **Core orchard (~300 packages):** all three flavors where the formula's `min_os` allows (§4.1), default variants — the shell/git/curl/python/openssl/ffmpeg stratum.
- **Extended orchard (~2,000 packages):** all flavors compatible with each formula's `min_os` floor, default variants, built on a rolling cadence.
- **Popular non-default variants and prebuild priorities:** chosen by *value to a stranded platform*, never by volume. Download counts are explicitly rejected as a signal: on a deprecated-OS ecosystem, an obscure library fetched once a month may be irreplaceable — nobody else ships it for these machines — while a popular tool has alternatives everywhere. The prioritization inputs are all knowable without watching a single user:
  - **Dependency centrality** — how much of the orchard's build graph a package unblocks, computed from the graph itself.
  - **Build pain** — farm-measured compile time and patch/failure rate: the hours a prebuilt slice saves each of its users, however few they are.
  - **Irreplaceability** — upstream has dropped these OSes and Homebrew's bottles are frozen; if aslice doesn't ship it, it effectively doesn't exist for this platform.
  - **Direct community requests** — orchard issues and request threads, in the open.
- Everything else: source builds, with the ABI contract guaranteeing the result still interops with the prebuilt world.

### 9.5 Build provenance

Every slice ships a SLSA-style provenance attestation in its manifest: builder identity, source hash, formula git commit, toolchain ID, build environment digest, and (phase 3) reproducibility status. `aslice provenance ffmpeg` shows it. Reproducible-build verification — rebuilding on a second, independent builder and bit-comparing — starts with the core orchard and extends outward; slices that verify get a `reproducible: true` badge in the index.

For vendor-binary slices (§12.4) the provenance section instead records: the vendor artifact URL and sha256, the pinned signer identity and notarization state at pack time, the repackaging tool version, and whether the payload is hosted (redistributable) or vendor-fetched.

### 9.6 The repository system

GHCR, Releases, and static mirrors are *transports*. The canonical distribution unit — the thing a client actually consumes — is the **aslice repository**: a self-contained, signed, static tree:

```
repo.example.org/
 ├── tuf/            # root.json, snapshot.json, timestamp.json, targets.json
 ├── index/          # zstd JSON snapshots + diffs (the solver's world)
 ├── formulas/       # resolved package metadata (pure data; never executable)
 └── blobs/sha256/   # slices and vendored sources, content-addressed
```

- **Anyone can host one.** Any static HTTP server, a GitHub Pages site, a GHCR org (blobs in OCI, index overlaid), or a `file://` directory on a lab NAS. A mirror is simply a full copy of the tree; clients fail over across a repository's declared mirrors.
- **Repositories carry recipes *and* binaries.** `formulas/` holds the resolved metadata the solver needs (recipes); `blobs/` holds the slices — each tagged in the index with its OS-support bounds (`min_os`/`max_os`), flavor, and arch. A repository may be *binary-only* — repackaged vendor software with no orchard behind it at all (§12.4) — which is how communities serve niche pkg/dmg-only ecosystems (audio plugins, lab instruments) without asking the project for orchard space.
- **Trust is per-repository, with inherent levels.** Every repository has one of four enforced trust levels — `official` (pre-pinned, threshold keys), `verified` (project-countersigned community repos, shipped disabled), `third-party` (user-added, TOFU), `local` (development trees, formulas only unless signed). Levels are capability sets enforced by the solver and verifier — what namespaces a repo may serve, whether its binaries may install, whether it may shadow core names — not labels. `aslice repo add <url>` pins the repository's root key fingerprint on first use (TOFU): the fingerprint is displayed with a strong recommendation to verify out-of-band, stored in the DB, and any later change is a loud, blocking event. The project ships an **official source list** (`sources.toml`, itself a TUF target) with core + extended pre-pinned — the core fingerprint is also compiled into the bootstrap binary — and verified community repos listed for discovery. The project's canonical repository ships pre-pinned in the bootstrap. Full model: [REPOSITORIES.md](REPOSITORIES.md).
- **Namespaces and collisions.** Resolution order: core > extended > verified > third-party in add order. Explicit addressing is `repo:pkg` (`audiolab:convolver`); a third-party name shadowing a core name is reported by `doctor`, never silently preferred. When two *peer* repositories serve the same bare name, the user is **prompted on first encounter** and the decision is remembered in the state database — revalidated on repo removal/demotion, bypassed by explicit namespaces, inspectable via `aslice repo resolutions` (full model: [REPOSITORIES.md](REPOSITORIES.md) §10).
- **Authoring → publishing.** `aslice repo build` compiles an orchard (git formulae) — or a bare manifest directory — into a repository tree; `aslice repo sign` applies the keys; `aslice repo publish` pushes to the configured transport. The project's own pipeline is the same commands in CI, so the canonical repository holds no magic a community repository can't reproduce.

---

## 10. Security Model

The bar: be measurably better than Homebrew's model, on the same machine, without asking users to change how they work. Homebrew's model, fairly stated: formulae are executable Ruby fetched from git repos; taps are trusted wholesale; binary installs run `post_install` code; the installer chowns `/usr/local`; and signing/attestation arrived late and partially. aslice's model is built from the following load-bearing decisions.

### 10.1 Declarative packages, hermetic builds

- Formula *metadata* is TOML — pure data, validated against a schema, rejected on unknown fields.
- Formula *logic* is Starlark executed in the build sandbox with a capability-only API (`ctx.run`, `ctx.make`, `ctx.env`) — no filesystem access outside the build dir, no network, no subprocess outside the declared toolchain, deterministic by construction.
- **Binary installs execute no package code whatsoever.** There is no `post_install`. Data-directory creation, launch-agent registration, and shell-completion placement are declarative manifest entries applied by aslice's own code. This removes the single largest supply-chain surface in the Homebrew model: arbitrary maintainer Ruby running on every install. The same rule binds vendor binaries: `.pkg` `preinstall`/`postinstall` scripts and `.dmg` autolaunch mechanics never execute (§12.4) — payload extraction is all that happens.

### 10.2 Signatures and repository integrity (TUF)

- **Metadata:** the index is wrapped in [The Update Framework](https://theupdateframework.io/) — offline root key (threshold, YubiKey custody), short-lived online snapshot/timestamp keys, targets key on the signing host. This gives rollback, freeze, and mix-and-match attack protection — the failure modes that plain "signed packages" miss.
- **Packages:** every slice is signed — minisign-compatible Ed25519 for official infrastructure, with **OpenPGP (GPG) as a built-in first-class scheme** for third-party repositories and formula-declared upstream source verification (a self-contained verifier linked into aslice; no `gpg` binary, no keyserver dependence, modern algorithms only). The scheme is a property of the repository, the fingerprint is a property of the pin, and both are enforced before content is trusted ([REPOSITORIES.md](REPOSITORIES.md) §5). Signature verification happens **before extraction**, and the verified manifest is what the linker consumes.
- **Sources:** every source tarball hash is pinned in the formula *and* countersigned in the index; `fetch` verifies against both. Vendor artifacts are additionally **signer-pinned** (§12.4): a silent change of code-signing identity upstream is a hard failure, not a warning.
- **Key compromise response:** root key is 3-of-5 threshold across founding maintainers; revocation and rotation is a practiced runbook, not a hope.

### 10.3 Trust bootstrapping

The installer is a small, auditable shell script that fetches exactly two things — the `aslice` bootstrap binary and the TUF root metadata — each pinned by hash in the script *and* cross-checkable against a signed checksums file on a second transport (Release asset + Pages). Everything after that first step is verified by TUF. The script never runs `sudo` except, optionally, to create `/opt/aslice` and chown it to the invoking user — once.

### 10.4 Privilege discipline

- **No sudo in steady state.** Not for install, not for upgrade, not for uninstall. The prefix is user-owned from creation.
- **Never touches `/usr/local`.** Coexistence with Homebrew/MacPorts is by construction, and the historic `/usr/local` ownership flaw is simply not inherited. Vendor-binary apps install under `/opt/aslice/apps/` — never `/Applications` — with a per-user `~/Applications` symlink as the opt-in convenience (§12.4).
- **No setuid binaries, no helper daemon at launch.** A future multi-user mode (shared lab machines) will use a launchd daemon that accepts only TUF-verified operation plans over a local socket with peer-credential checks — designed, but gated behind demand.
- **One scoped exception: `aslice-system`.** Declared system-software packages (kexts, SIP-disabled development tools — §12.7) require privileged steps no user-space manager can perform. Those steps are executed by a single tiny auditable helper that elevates **per operation, with explicit consent, for exactly the declared actions** — it is not a daemon, holds no ambient authority, and every invocation is an unsuppressible logged security event (§12.5). Its scope also covers **system-domain service operations** — bootstrapping and removing root LaunchDaemons for declared `domain = "system"` services (§12.8) — with the same per-operation consent and logging; user-domain agents never touch it. The steady-state rule stands: nothing else in aslice ever elevates.

### 10.5 Sandboxed builds

Every build phase runs under a Seatbelt (`sandbox-exec`) profile — Seatbelt predates the entire 10.11–12 window and is present on every supported release:

| Phase | Profile |
|---|---|
| fetch | Network to declared hosts only; write to cache dir only |
| unpack/patch/configure/build | **No network at all**; write only within the build dir; read-only toolchain and store |
| install (to staging) | No network; write to staging dir only |
| test | No network by default; opt-in `test_network = true` per formula, loudly logged |

Vendor-binary payload extraction (`xar` expansion, `hdiutil` attach, cpio unpack) runs under the unpack profile — no network, writes confined to staging; there is no phase in which a vendor artifact gets to run anything.

Seatbelt is deprecated by Apple on newer releases but frozen-in-place across our entire (frozen) target window; the profile abstraction (`SandboxPolicy` compiled to Seatbelt today) is designed so a future backend can replace it without touching formulae. A build that escapes its profile fails the build and files an automatic audit event.

### 10.6 Vulnerability and SBOM pipeline

- Every slice embeds an **SPDX SBOM** generated from the build manifest (sources, patches, dependency closure, toolchain). Vendor-binary slices ship a payload-only SBOM (file list, hashes, signer) — less deep than a source SBOM, still enough for `audit` to bind CVEs via CPE.
- `aslice audit` matches the installed set against OSV/GitHub Advisory feeds and reports CVEs with affected-version ranges — locally, offline-capable with a cached feed.
- Formulae declare upstream security-contact and EOL policy; packages past upstream EOL are surfaced in `audit` and require `--allow-eol` to install.

### 10.7 What this does not solve (honesty section)

- A malicious *core maintainer* with signing access can still ship bad slices; threshold keys, reproducible-build cross-checks (§9.5), and a public transparency log of index snapshots are the mitigations, and they reduce but do not eliminate insider risk.
- Sandboxing contains *builds*, not the runtime behavior of installed software. aslice is a package manager, not an endpoint product. This bears repeating for vendor binaries: payload-only installation removes *installer-script* risk, not the risk of the vendor binary itself — signer pinning and hash pinning ensure you get exactly the vendor's artifact, and that is all they ensure.
- **System packages (§12.7) deliberately step outside the sandbox story.** A kext runs in kernel space — a bug panics the machine — and SIP-disabled development tools weaken the protections of §10 for *all* software, not just themselves. aslice's guarantee for this category is narrower and says so: the bits are exactly the declared, verified ones; the privileged steps are exactly the declared ones, performed by aslice's own helper with explicit consent; the user was warned at every decision point. Nothing more is claimed, and the category is never servable by third-party repositories.
- C++ memory-safety risk in aslice itself is managed per §5.3; the parsers and extractors — the untrusted-input surfaces — get the fuzzing and the smallest footprints.

---

## 11. Performance Model

Performance goals with concrete mechanisms:

| Goal | Mechanism |
|---|---|
| **CLI startup < 10 ms** | Single Mach-O binary, static libc++, no interpreter, no JIT, lazy dyld binding, no network on the hot path |
| **`install` of a cached slice < 300 ms** | Verify (Ed25519: microseconds) → zstd decompress → APFS `clonefile` into store (HFS+ systems fall back to hardlink/copy) → symlink generation swap. No relocation pass on default prefix. |
| **Index update < 200 ms typical** | Snapshot diffs against a cached snapshot hash — a few KB on a typical day, versus Homebrew's git-fetch taps |
| **Solve < 50 ms typical** | SQLite-backed package index with prepared statements; PubGrub with clause caching; memoized per snapshot |
| **Downloads saturate the pipe** | HTTP/2 multiplexing, 8-way parallel fetches, resumable ranges, zstd `--long` delta-friendly payloads |
| **Cold full install of a large tree (e.g., `ffmpeg` closure) < 10 s on SSD** | Parallel fetch + pipeline overlap (decompress stream N+1 while linking N) |
| **Builds: near-zero manager overhead** | The builder's job is to get out of the way: Ninja parallelism, `ccache`-compatible compiler cache in `cache/`, tmpfs-backed build dir when RAM allows |

The deeper performance win is architectural: **flavor targeting.** A v3 ffmpeg/x264/openssl on a Haswell+ machine is measurably faster than the lowest-common-denominator binaries legacy platforms ship — crypto, codecs, and compression see the largest gains. aslice is likely the only macOS package manager that serves AVX2 binaries as a first-class default rather than an accident.

---

## 12. CLI and User Experience

### 12.1 Commands

```
aslice install ffmpeg                  # binary-first; flavor auto-detected
aslice install ffmpeg --build-from-source
aslice install ffmpeg --variant +x265 --cflags="-O3 -march=native"
aslice install ffmpeg@v6               # version pinning
aslice install audiolab:convolver      # explicit repository namespace (§9.6)
aslice upgrade / aslice upgrade ffmpeg [--rollback-on-service-failure]   # the flag is the unattended path; interactively aslice asks (§12.8)
aslice uninstall x264 / aslice autoremove
aslice search / info / leaves / why <pkg>
aslice flavors ffmpeg                  # show the prebuilt matrix for this machine
aslice provenance ffmpeg               # builder, source hash, SLSA attestation
aslice audit                           # CVE report for the installed set
aslice rollback / switch-generation / history
aslice service list / status <pkg>       # launchd truth: pid, state, last exit (§12.8)
aslice service start / stop / restart <pkg> / service run <pkg>   # run = foreground, for debugging
aslice gc [--dry-run] [--older-than 30d]
aslice orchard add myorg/orchard / orchard pin myorg/orchard <commit>
aslice repo add https://repo.example.org   # add a signed repository (§9.6)
aslice repo list / repo remove <name> / repo build / repo publish
aslice repo enable / repo disable <name>   # verified repos ship listed-but-disabled
aslice repo re-pin / keys / audit <name>   # trust-level machinery (REPOSITORIES.md §7)
aslice repo prefer / resolutions / forget  # overlap decisions, remembered in the state DB (REPOSITORIES.md §10)
aslice adopt --from-homebrew           # migration assistant (§13.3)
aslice config set flavor v2            # overrides
aslice doctor                          # environment sanity, loudly honest (§12.6)
aslice log [--follow] [--level debug]  # query the local operation log (§12.5)
aslice install foo --accept-system-changes   # explicit consent for [system] packages, non-interactive (§12.7)
# every command: -v / -vv raise verbosity, --quiet suppresses all but errors,
# --log-format json|human selects rendering (§12.5)
```

### 12.2 Interaction principles

- **Binary is the default, source is a flag.** A user who never passes `--variant` or `--cflags` never sees a compiler.
- **Every decision is explainable.** `--explain` on any command shows the solver's derivation; `--dry-run` shows the exact plan: which slices, which local builds, which generation change.
- **Loud honesty.** EOL packages, unsigned orchards, deprecated variants, fallback-to-source events, and non-notarized vendor binaries are announced, not buried. `doctor` reports Tier-style truth about the machine rather than pretending uniformity.
- **Scriptable:** `--json` on everything; stable exit-code contract; machine-readable `plan`/`apply` split (`aslice plan install ffmpeg > plan.json && aslice apply plan.json`) — which is also what the future multi-user daemon consumes.

### 12.3 Orchards, repositories, and trust levels

Orchards are git repos of formula directories — the *authoring* format. Repositories (§9.6) are the *distribution* format. Trust is explicit at both layers:

- **Core/extended orchards:** signed by project keys; Starlark + TOML only.
- **Third-party orchards:** installed disabled by default; enabling one prints its trust implications (its formulae can cause local source builds — sandboxed — but *never* execute at binary-install time, because nothing ever does).
- **The canonical repository:** the project orchards compiled and signed by project keys; pre-pinned in the bootstrap.
- **Third-party repositories:** added explicitly, root key pinned on first use (TOFU, fingerprint displayed, changes blocking). A third-party repository can serve its own signed slices — including binary-only vendor repackagings — under its own keys. The one thing no repository can do is make aslice execute package code at install time; that door is closed structurally, not by trust policy.

### 12.4 Vendor binaries (pkg/dmg) and GUI apps

Some software for this platform will only ever ship as a `.pkg` installer or a `.dmg` — commercial audio tools, vendor CLIs, frozen releases of abandoned apps. aslice installs it **without ever running installer code**:

- **`.pkg`:** expanded with `xar`/`pkgutil --expand`; only the `Payload` is extracted, per the declarative path map in the formula. `preinstall`/`postinstall` scripts are never executed — full stop. Packages whose function genuinely *requires* script execution remain out of scope — the payload-only line holds. Drivers and kexts are **not** rejected, though: they install through the declarative system-software category (§12.7), where the privileged steps are performed by aslice's own helper from manifest declarations, never by vendor scripts.
- **`.dmg`:** attached read-only via `hdiutil -nobrowse -readonly`; declared items copied. No autolaunch, no quarantine propagation.
- **Apps** install under `/opt/aslice/apps/` (owned by the prefix, not `/Applications`), with an optional per-user `~/Applications` symlink; Finder and Launch Services pick them up from either location.
- **Provenance is pinned.** The formula records the expected signing identity (`Developer ID Application: Vendor (TEAMID)`) and notarization expectation; the verifier checks the signature *before* extraction and hard-fails on a silent signer change — a classic supply-chain attack against binary distribution.
- **Two distribution modes, license-driven.** `redistribute = true` → the farm repackages the payload into a normal `.slice`, hosted in the repository like any other (best UX: atomic, resumable, rollback-able). `redistribute = false` → the formula stays a pointer: the client fetches the vendor URL itself (hash- and signer-pinned), extracts locally in the sandbox, installs payload only. Same install semantics; only the transport differs. Non-redistributable software still gets generations, lock files, and `audit`.
- **OS support is tagged per artifact.** Each `[[binary]]` entry carries its own `min_os`/`max_os`/`arch`, so a vendor's "legacy" build for 10.11–10.13 and "current" build for 10.14+ coexist in one formula and the solver picks the artifact matching the machine — never a "this application cannot be opened" surprise after install. Vendor claims are checked at pack time against the bundle's `LSMinimumSystemVersion` and the pkg's Distribution requirements where present; mismatches are lint errors, because an honest tag is the entire point.
- **32-bit payloads install where — and only where — the OS can run them.** 10.11 through 10.14 are the last macOS releases that execute 32-bit code, and a large share of pkg/dmg-only software on this platform (audio plugins, lab instruments, frozen pro tools) is i386 or universal. Vendor artifacts may therefore carry `arch = ["i386"]` or `["x86_64", "i386"]`; the pack-time verifier inspects every Mach-O slice in the payload with `lipo`-style logic and derives the true ceiling — an i386-containing artifact must declare `max_os = "10.14"` (or lower), and on 10.15+ it is a clean solve-time refusal, not an install that can't launch. Universal payloads are installed **whole**: no `lipo -thin` stripping, ever — thinning a fat binary invalidates the vendor's code signature, and signature integrity outranks disk savings. This changes nothing about what aslice *builds* (N6: farm slices stay x86_64-only); it is distribution, not compilation.

Vendor binaries participate in the store, generations, profiles, lock files, and `audit` exactly like source-built packages. Their `build_id` excludes flavor and toolchain (§7.2), and their payload dylibs get the same ABI scan at pack time — dependents link against vendor libraries through the same contract as farm-built ones. The scan is per-architecture: universal payloads record separate `x86_64` and `i386` ABI entries, and the x86_64 entry is what aslice-built dependents (always 64-bit) consume.

### 12.5 Logging and diagnostics

A package manager that fails opaquely trains users to fear it. aslice logs **everything it does, to the local machine, and nowhere else** — the charter (N7) applies to logs exactly as to metrics: nothing is ever transmitted, aggregated, or phoned home, not even opt-in.

**Where logs live.** `/opt/aslice/log/` (or `~/.aslice/log/` for per-user prefixes), one JSONL file per day, rotated and size-capped (default: keep 14 days or 256 MB, whichever is less; both configurable). The build harness keeps its own per-build structured logs (`log.jsonl`, BUILD-INFRA §4) — this section governs the client.

**What gets logged.** Every operation is a structured event stream with a generated operation ID that ties terminal output, log records, and the `history` table (REPOSITORIES.md §11) together:

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
- **Supportability.** `aslice log` filters by operation, package, level, or time range; `aslice doctor` ends with the paths of the relevant log files. When a user files an issue, `aslice log --last-op` produces exactly the excerpt a maintainer needs — locally generated, user-attached, never auto-submitted.

**Silence discipline.** Steady-state success is quiet: a successful binary install prints its plan summary and result, and everything else lives in the log at info level. aslice never logs at warn for things that are fine (a lesson from tools whose warning noise trains users to ignore real ones).

### 12.6 Doctor: sanity checking

`aslice doctor` is the single entry point for "is my installation healthy?" — it runs a fixed battery of checks, reports each as pass/warn/fail with the actionable-message standard of §12.5, and never changes anything itself (repairs are explicit commands it *recommends*). It is read-only, offline-capable, and fast (< 1 s for the standard battery; deep checks are opt-in).

**Check groups:**

| Group | Checks | Verdicts |
|---|---|---|
| **Machine** | CPU flavor vs. configured flavor (a v3 config on v2 hardware is a fail, not a surprise SIGILL later); macOS release vs. supported window; APFS vs. HFS+ (capabilities that degrade, announced); free disk vs. GC watermark | pass / warn / fail |
| **Prefix and store** | Prefix ownership and permissions (user-owned, not world-writable); store path integrity — manifests re-hashed against on-disk content (`--deep` re-hashes every file, default checks a sample plus anything the DB flags); dangling store paths referenced by no generation | pass / fail |
| **Profiles and generations** | `default` symlink resolves; every profile symlink lands inside the store; the live generation matches the DB's installed set; collision priorities resolve to real paths | pass / fail |
| **Database** | SQLite integrity check; schema version vs. binary (a newer DB than the binary is a loud fail with downgrade instructions, never silent corruption); WAL recovery state | pass / fail |
| **Repositories** | Per repo: reachable (or cached-snapshot age if `--offline`), TUF metadata expiry countdown, pinned key still matches live root, trust-level consistency (a `verified` repo whose countersignature lapsed is a fail with the freeze explanation — REPOSITORIES §3), shadowed core names, current overlaps and their resolution state, index staleness beyond policy | pass / warn / fail |
| **Coexistence** | Homebrew/MacPorts presence, PATH ordering advice, anything in `/usr/local` shadowing aslice binaries (or vice versa) — advisory only, aslice never touches either | pass / warn |
| **Environment** | `ASLICE_*` variables that override config (listed, not hidden); shell init files referencing stale prefixes; Xcode CLT presence (informational — the self-hosted toolchain makes it optional for aslice itself) | info / warn |

**Rules:**

- **Every fail and warn names the remedy.** Not "store integrity error" but "store path `x264-0.164-0+core.v3.77aa10b2` fails manifest hash (1 file) — quarantine with `aslice store verify --quarantine x264` and reinstall." The check table is code, not prose: each check has an ID (`doctor.store.hash`), so messages, `--json` output, and docs all reference the same stable identifier.
- **Exit codes are scriptable:** 0 all-pass, 1 warnings only, 2 any fail. `--json` emits the full battery result; CI and fleet tooling gate on it (`aslice doctor --json | jq '.checks[] | select(.verdict=="fail")'`).
- **Warnings are honest, not noisy.** Each warn is a real action item with a command attached; anything informational goes to the `info` tier, which `--brief` suppresses. A doctor that cries wolf gets ignored — the battery is curated so that a clean machine prints one line: `aslice: your installation is healthy (N checks, M repos, G generations)`.
- **It ends with pointers, not a wall.** The summary footer lists the log directory and the last operation ID (§12.5), so a failing machine goes from `doctor` to root cause in two commands.
- **`--fix` exists but is narrow and loud.** The only automatic repairs offered are ones with no possible data loss: pruning dangling cache entries, re-linking a broken generation symlink to its recorded target, refreshing stale index snapshots. Everything else prints the exact command for the user to run. `--fix` announces each action before taking it and logs all of them.

---

### 12.7 System software: kexts and SIP-disabled development tools

Some software this platform needs cannot live entirely inside the store: kernel extensions (audio-interface drivers, filesystems, hypervisors) and development tools that require SIP disabled (low-level debuggers, DTrace-based profilers, kernel instrumentation — a real population on 10.11–12 development machines). Earlier drafts rejected this category outright; v1.2 replaces the rejection with an honest, declared path, because the software exists and users install it today by hand — with no provenance, no warnings, and no rollback. A package manager that refuses to see that protects no one.

**Declaration.** A package opts in via `package.toml`:

```toml
[system]
kexts            = ["Library/Extensions/FooAudio.kext"]  # payload-relative paths to install
sip_off_required = false     # true: the software cannot function while SIP is enabled
reason           = "Kernel driver for FooAudio USB interfaces"   # mandatory; this IS the warning text
```

Either `kexts` or `sip_off_required = true` (or both) marks a system package; `reason` is mandatory and shown verbatim in every warning. Development tools needing SIP off but installing no kext declare only `sip_off_required` and `reason`. The full schema lands in PACKAGE-FORMAT v0.4 alongside the REVIEW §8 amendments.

**Mechanism — declarative, elevated, still code-free.** The category preserves the founding rules:

- **Zero package code at install (§10.1) holds.** The privileged steps — placement into `/Library/Extensions`, ownership and permission repair, `kextcache` invalidation, load — are performed by **`aslice-system`** (§10.4) from the manifest's declarations. Vendor `postinstall` scripts still never execute; a vendor kext package whose scripts turn out to be required is still rejected (§12.4, ORCHARD-POLICY §13).
- **Store and rollback hold.** The kext payload lives in the store like any other file; `/Library/Extensions` entries are managed copies recorded in the DB. Uninstall unloads and removes them and refreshes the kernel cache; rolling back to a prior generation restores the prior kext set.
- **Kext reality is respected.** On SIP-enabled 10.11+, loaded kexts must be signed — the formula declares whether its kexts are signed (signer-pinned per §12.4 when vendor-supplied) or whether it requires SIP off. aslice checks `csrutil status` rather than assuming: a `sip_off_required` package on a SIP-enabled machine stops *before download* with exact instructions (boot to Recovery, `csrutil disable`, re-run the command); a signed-kext package on a SIP-enabled machine installs with no SIP conversation at all. OS updates can re-enable SIP or invalidate kexts — `doctor` (§12.6) reports SIP state, declared-vs-loaded kexts, and exactly that drift.

**The warnings are the feature.** Declared system requirements surface at every decision point:

- **Solve and plan:** installing a system package prints a prominent block *before any download*: the kexts it installs, the SIP requirement, the `reason` text, and the consequences — kexts run in kernel space (a bug panics the machine), and SIP-disabled operation weakens every protection in §10 for all software on the machine.
- **Non-interactive refusal:** scripts, `--json` plans, and `aslice apply` **refuse** system packages unless `--accept-system-changes` is passed for that operation. There is deliberately no persistent "always accept system changes" setting — consent is per-decision, like the risk.
- **Elevation:** the consent prompt for `aslice-system` repeats the declaration; every elevation is logged as an unsuppressible security event (§12.5).
- **Doctor:** SIP state, kext drift after OS updates, and unsigned-kext installs are all `doctor` checks with remedy text and stable check IDs (`doctor.system.sip`, `doctor.system.kexts`).

**Trust gating.** Serving system packages requires the **`system` capability**, granted by trust level (REPOSITORIES.md §3): **official and verified repositories have it; third-party repositories never do; `local` repositories have it** (a developer's own `file://` tree on their own machine — the same authority as installing the kext by hand, now with warnings and rollback). Talking a user into installing a kernel extension is precisely the social-engineering attack the trust levels exist to block, so no remote stranger's repository can offer one. Tier policy — extended by default, core only when the platform genuinely requires it — lives in ORCHARD-POLICY §13.

---

### 12.8 Services: launchd-native lifecycle and safe upgrades

Long-running services — nginx, PostgreSQL, Redis, dnsmasq, unbound — are where a package manager meets the running system, and they impose two requirements. The manifest must *describe* the service rather than ship scripts that manage it, and an upgrade must never replace the binary under a running process: stop the service, swap, start it again. Homebrew's answer is `brew services`, a wrapper that generates plists from a formula DSL and shells out to `launchctl` (via sudo for daemons). aslice's answer is declarative and launchd-native, and the stop–swap–restart sequence is part of the upgrade transaction itself, not a wiki page.

**Declaration.** A package describes its service in `package.toml` (schema: PACKAGE-FORMAT §3.8):

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

aslice *generates* the launchd plist from this declaration at enable time — the formula ships no plist file and, as ever, no code. Two consequences fall out of the store model. `ProgramArguments` resolves through the **profile** (`/opt/aslice/profiles/default/bin/nginx`), never a store path, so the job survives upgrades and rollbacks untouched: the same plist launches whichever version the live generation points at. And the label is namespaced (`org.aslice.nginx`), so `aslice service` maps one-to-one onto real launchd jobs — no pidfiles, no guessing, no wrapper daemons.

**The command.** `aslice service` is a thin, honest layer over `launchctl`'s modern interface (`bootstrap` / `bootout` / `kickstart` / `print`, present since 10.10, so the whole 10.11–12 window is covered):

- `aslice service list` / `status <pkg>` — reads `launchctl print gui/<uid>/org.aslice.<pkg>`: pid, state, last exit status, keepalive. Status is launchd's truth, not a pidfile.
- `aslice service start` / `stop` / `restart <pkg>` — `bootstrap` / `bootout` / `kickstart -k` against the generated plist.
- `aslice service run <pkg>` — foreground, unregistered, for debugging (the one `brew services` idea worth copying).
- Per-service environment overrides live in `$XDG_CONFIG_HOME/aslice/services/<pkg>.env` and are applied when aslice generates the plist — never by editing it afterwards (the store is immutable, §8.1, so overrides *must* live outside it, which is where they belong). This closes HOMEBREW-REVIEW §4.4's P1.

**Upgrades stop the service first.** The mutation pipeline of §8.3 becomes service-aware whenever a plan touches a package with a loaded job:

1. Resolve, fetch, and build the **entire new generation** while the old one — and the service — keeps running. Any failure here never touched the service.
2. `bootout` the affected jobs — and only the affected ones; an ffmpeg upgrade never bounces your postgres.
3. Swap the generation symlink (atomic, §8.3).
4. Reconcile plists — only if the declaration changed; the profile indirection means a plain version bump needs no plist edit.
5. `bootstrap` / `kickstart -k` the jobs and verify they came up (pid present, no immediate crash-exit). A job that won't start is a loud error carrying launchd's last exit status and the log path — and then aslice **asks the user about rolling back** (below).

**A failed health check asks, it never decides silently.** The failure is shown first — the job's launchd exit status and the log path — then, on an interactive terminal:

```
$ aslice upgrade nginx
…
error: service nginx failed to start after the upgrade (launchd exit status 78;
log: /opt/aslice/profiles/default/var/log/nginx/error.log)
The previous generation (nginx 1.26.2, generation 41) is intact and can be restored in seconds.
Roll back and restart the previous version? [y/N]
```

- **Yes** boots out the failed job, swaps the profile back to the previous generation (atomic rename, §8.3), and bootstraps the previous service version — the plist points through the profile, so it needs no edit — followed by the same health check on the restored version. The transaction is recorded in the operation log (§12.5) as rolled back, with the health-check failure attached, so `aslice log` can answer "what happened to nginx at 02:13" in one query.
- **No (the default)** leaves the new generation live and the service down: nothing is destroyed, the logs stay put for debugging, `doctor.services` flags the crashed job until it is resolved, and `aslice rollback` remains available — the prompt only accelerates a decision the user can make at any time. A declined rollback is remembered for the current operation only; the next failure asks again.
- **Non-interactive contexts** (no TTY, `--json`, scripts) never prompt and never auto-rollback: the upgrade exits with a machine-readable `service_start_failed` error naming the package, the exit status, and the log path, and rolling back is an explicit `aslice rollback`. Automation that wants the "yes" path unattended passes `--rollback-on-service-failure`. There is deliberately no flag that reports a downed service as success.

GC is already safe: a running job pins its store path through the profile generation it was started from, and §8.4 never collects store paths referenced by running processes.

**Root daemons are the privileged case.** `domain = "system"` jobs run as root (or a declared `user_name`) and are bootstrapped into the system domain by `aslice-system` (§10.4) — same per-operation consent, same unsuppressible logging as kexts. Because root execution is the privilege that matters, `domain = "system"` declarations are gated by the same **`system` capability** as `[system]` packages (REPOSITORIES.md §3): official and verified repositories may serve them, **third-party repositories never may**, local trees may on the user's own machine. User-domain agents are unprivileged and ungated — any repository may declare one, no sudo is ever involved, and the steady-state rule (§10.4) stands for nginx-on-8080 and every other development service.

**Doctor.** `doctor.services` checks: every enabled service's plist parses and its `ProgramArguments` resolve into the *live* generation; jobs loaded for packages no longer installed (and packages with declared services that were never enabled); crash-looping jobs (launchd's throttling state); and, for `domain = "system"` jobs, that what is running matches what the DB records `aslice-system` installed. All read-only; `--fix` offers only the no-data-loss repairs (§12.6).

---

## 13. Policies, Governance, and Migration

### 13.1 Package acceptance policy

- Core orchard: maintained, security-patched, reproducible-build targets; no package enters without a working `tests.star` smoke test on at least one OS × one flavor.
- Upstream-EOL software: allowed in extended with `eol = true` metadata; excluded from core.
- Vendor binary packages: accepted into extended only with a verifiable signature and honest OS-support tags; into core only if additionally redistributable (so the farm hosts the slice) and payload-only by construction. A vendor package whose scripts turn out to be required is removed, not accommodated.
- **Patching system files is rejected forever** — aslice installs alongside macOS; it never modifies `/System`, `/usr`, or Apple's binaries. This remains a hard line and a marketing feature. Kernel extensions and SIP-disabled development software are **not** rejected: they are the declared, warned, trust-gated system-software category of §12.7.

### 13.2 Variant discipline

`abi = true` variants are capped per package (guideline: ≤ 6) and each must justify its existence in review. This keeps the solver space small, the prebuilt matrix tractable, and avoids repeating the option-sprawl that made Homebrew variants unmaintainable. `abi = false` (build-flavor) variants are unconstrained — they cost the project nothing because they never spawn binary flavors.

### 13.3 Coexistence and migration from Homebrew

- **Coexistence:** aslice lives in `/opt/aslice`, never touches `/usr/local`, and `doctor` detects a Homebrew installation and advises on PATH ordering rather than conflicting.
- **`aslice adopt --from-homebrew`:** reads Homebrew's Cellar and `brew leaves`, maps names to aslice formulae (with a maintained alias table for renames), produces an install plan that recreates the same leaf set — including mapping old `--with-*` Homebrew options to aslice variants where an alias exists. Cask leaves map to vendor-binary packages where one exists, flagged for review when the vendor artifact's OS tags don't cover the machine. It does not attempt binary reuse of Homebrew's Cellar (different prefix assumptions); it reuses the *intent*.
- **Formula importer (for orchard authors):** a tool that mechanically translates simple Homebrew Ruby formulae — `url`/`sha256`/`depends_on`/standard `configure && make` bodies — into TOML+Starlark drafts, with a human review step. Realistic coverage target: the simple ~60–70% of formulae; the rest are ports, not translations. A companion importer turns simple Casks (`url`/`sha256`/`app`/`pkg`) into `type = "binary"` drafts — Casks are *more* mechanical than formulae, so coverage should be higher; the reviewer fills in signer pinning and OS tags.

### 13.4 Governance

- Benevolent-core-team start: 3–5 founding maintainers holding threshold keys; decisions by lazy consensus, escalations by vote.
- Orchard PR review backed by CI that *builds the package in the sandbox on both flavors* — review is about correctness and policy, never "does it compile."
- Public roadmap, public build-farm dashboard, public transparency log. A legacy-platform project survives on trust, and trust survives on visibility.
- Funding: GitHub Sponsors/OpenCollective for build-farm hardware and power; costs are low and fixed (§9.3) precisely because the platform is frozen.

---

## 14. Roadmap

**Phase 0 — Foundations (months 0–3)**
`aslice-toolchain` first: modern Clang/libc++ targeting darwin15, bootstrapped on the newest Intel macOS against the oldest archived SDK, then self-rebuilt. Then the C++ core skeleton: CLI, SQLite state, TUF client, zstd, Mach-O/otool wrappers — plus the build harness in local mode (`aslice build` with the full sandboxed phase pipeline, job/result schemas; BUILD-INFRA.md §12), because the core orchard seed is built *with* it. Bootstrap binary runs on every release 10.11–12 (VM-tested per release, including HFS+). Core orchard seeded with ~30 packages (curl, git, openssl, python, zstd, cmake, ninja) built on real hardware.

**Phase 1 — Usable (months 3–6)**
Solver with variants; store/profiles/generations; GHCR distribution; the build harness in both modes — `aslice build` locally and `aslice farm` coordinator/agents on real hardware, one pipeline (BUILD-INFRA.md); minisign slices; ~300-package core orchard, all flavors; `adopt --from-homebrew`; build farm Phase A + first self-hosted nodes. Repository client (`repo add/list`, TOFU key pinning) from the start — the canonical repository *is* the default transport, so the multi-repo machinery costs little extra.

**Phase 2 — Differentiated (months 6–12)**
ABI scanner with DWARF diffing; SBOM + `audit`; SLSA provenance; `aslice-toolchain` v2 (LLD-first linking, ccache integration); extended orchard to ~2,000 packages; popular-variant prebuilds chosen from community requests (§9.4); reproducible builds for core; vendor-binary packages (`type = "binary"`, payload extraction, signer pinning) and the Cask importer; `aslice repo build/publish` for third-party repositories.

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
| GPL/license compliance for hosted binaries | Low | Corresponding-source archive mirrored per license; SPDX SBOMs make compliance auditable; `redistribute = false` exists precisely for software we may not rehost |
| Community adoption never materializes | Existential | Scope stays hobbyist-sustainable by design; worst case, the core orchard remains a maintained artifact for the installed base |

**Open questions for early reviewers:**

1. Default prefix (`/opt/aslice` vs `~/.aslice`-first). The name itself is settled: **aslice**.
2. Starlark vs. a stricter pure-TOML-with-templates build DSL (Starlark chosen for expressiveness with hermeticity; the debate is real).
3. Whether `abi = false` user-flag builds should share store paths with farm builds (current: yes, identity is identical — but provenance diverges; review wanted).
4. ~~Telemetry~~ — **resolved (v0.3, sharpened v0.4): aslice collects no telemetry or analytics of any kind, ever.** No install IDs, no opt-in counters, no phone-home, no crash reporting — and no download-count-driven prioritization either, because volume mismeasures value on a platform where the rarest dependency may be the most irreplaceable (§9.4). The project is infrastructure, not a product, and its users — many on air-gapped audio rigs and lab machines — owe it no data. This is a charter-level commitment, not a tunable.
5. Whether the project's canonical repository should host *any* `redistribute = false` formulae in core, or whether pointer-only packages should be extended-tier by definition (current: allowed in both, barred from core unless redistributable — but that makes core depend on license goodwill; review wanted).
6. Whether `verified` repositories should install binaries immediately at enable time, or require an additional per-repo `--accept-binaries` step (current: enable implies binaries — the project countersignature is the vetting; the extra click was judged ceremony without security content; REPOSITORIES.md §9).
7. Whether the `system` capability (§12.7) should ride on the `verified` trust level or be a separate per-repo grant (`aslice repo allow-system <name>`). Current: verified repos get it — the countersignature is the vetting, and one more click was judged ceremony. But kexts are exactly where ceremony might be security; review wanted.
8. ~~Service health-check failure behavior~~ — **resolved (v1.4): ask the user.** A failed post-upgrade health check (§12.8, step 5) prompts interactively to roll the generation back and restart the previous version; the default is stay-and-inspect, non-interactive runs fail loudly without rolling back, and `--rollback-on-service-failure` is the explicit unattended path. Silent automatic rollback was rejected: it can mask a good new version behind a transient port conflict, and a package manager that destroys evidence of a failure is harder to trust than one that asks.

---

## Appendix A. Comparison Summary

| | Homebrew (Intel, 2026) | MacPorts | Nix | **aslice** |
|---|---|---|---|---|
| 10.11–12 Intel support | Tier 3 → removed 2027 (and never covered ≤10.14) | Partial, best-effort | Degrading | **First-class, the whole point** |
| Prebuilt binaries | Frozen legacy bottles | Sparse | x86_64-darwin cache shrinking | **v1 + v2 + v3 flavors, default path** |
| µarch targeting | No | No | No | **AVX2 flavor first-class** |
| User build flags | Removed from core | Yes (variants) | Yes (overlays) | **Yes — with ABI-aware interop** |
| Mix binary + custom builds | Breaks assumptions | Works, all-local | Full rebuild cascade | **Contract-checked substitution** |
| Install-time package code | Ruby `post_install` | Tcl phases | No | **None (declarative)** |
| pkg/dmg-only vendor software | Casks (installer scripts may run) | Rare | Not the model | **Payload-only, signer-pinned, OS-tagged artifacts — incl. 32-bit/universal on 10.11–10.14** |
| Kernel extensions / SIP-off dev tools | Cask pkg scripts (arbitrary vendor code, often as root) | Manual installs | Not the model | **Declared `[system]` category: warned, consent-gated, trust-gated, rollback-able (§12.7)** |
| Third-party binary distribution | Taps + bottles bolted on | No | Binary caches (trust via substituters) | **Repositories: signed, static, mirrorable, self-publishable** |
| Rollback | No | No | Yes | **Yes (generations)** |
| Service management | `brew services` (plist wrapper; daemons need sudo) | launchd by hand | NixOS modules (different OS) | **Declarative `[service]` + `aslice service`; stop–swap–restart upgrades with a prompted rollback on health-check failure (§12.8)** |
| Repo integrity | git + partial attestations | rsync + signatures | Signed cache | **TUF + signed slices + transparency log** |
| sudo in steady state | Some paths | `sudo port` | Daemon mode | **None** |
| Startup / solve speed | Ruby, seconds-scale | Moderate | Slow eval | **<10 ms / <50 ms** |

## Appendix B. References

- Homebrew 7.0.0 release notes (Intel → Tier 3, 10.15 removal, September 2026): https://brew.sh/2026/09/13/homebrew-7.0.0/
- Homebrew Support Tiers (Intel bottle cessation; removal in/after September 2027): https://docs.brew.sh/Support-Tiers
- Homebrew discussion: Intel CI disabled, "no bottle available" (September 2026): https://github.com/orgs/Homebrew/discussions/7044
- Homebrew Monterey deprecation discussion: https://github.com/orgs/Homebrew/discussions/5603
- Homebrew history/version table: https://en.wikipedia.org/wiki/Homebrew_(package_manager)
- macOS 27 Golden Gate drops Intel (Apple's platform trajectory): https://eshop.macsales.com/blog/98631-macos-27-golden-gate-drops-intel-support-heres-how-to-find-out-if-youre-affected/
- The Update Framework: https://theupdateframework.io/
- x86-64 psABI microarchitecture levels: https://gitlab.com/x86-psABIs/x86-64-ABI
