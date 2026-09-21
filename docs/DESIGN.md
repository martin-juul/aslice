# aslice — A Package Manager for Intel macOS

**Name.** *aslice* — an apple slice: a nod to the Macintosh apple and to the shape of the project itself. Binary packages are **slices**; formula repositories are **orchards**; the manager picks slices off the orchard, prebuilt or baked to order. The vocabulary is kept distinct from Homebrew's beer terminology to avoid community confusion and trademark friction. The project name is styled lowercase everywhere, including sentence starts — like the command.

- **Status:** Design draft, v1.15 — September 2026
- **Change log:** v0.2 extends the platform floor from 10.15 (Catalina) to 10.11 (El Capitan) — see §4 for the consequences (three flavors, self-hosted toolchain in Phase 0, HFS+ support). v0.3 resolves open question #4: **aslice collects no telemetry or analytics of any kind, ever** — the project is infrastructure, not a product (§2.2 N7, §9.4, §15). v0.4 sharpens it: **download counts are rejected as a value signal too** — on a deprecated-OS platform, obscure ≠ low-value (§9.4). v0.5 adds the **repository system** (§9.6) and **vendor binary packages**: software that only ships as a `.pkg`/`.dmg`, hosted or vendor-fetched, installed without ever running installer scripts (§12.4; schema in PACKAGE-FORMAT v0.2 §3.11). v0.6 opens **32-bit vendor binaries**: i386 and universal pkg/dmg payloads install on the releases that still execute 32-bit code (10.11–10.14) — distributed, never built (§2.2 N6, §12.4; PACKAGE-FORMAT v0.3). v0.7 adds the **build-infrastructure design**: one harness — `aslice build` on a user's machine, `aslice farm` on the farm — running the identical sandboxed pipeline at both scales (§5.1, §9.3; full spec in [BUILD-INFRA.md](BUILD-INFRA.md)). v0.8 completes the repository story: a **shipped official source list**, **inherent trust levels** (official / verified / third-party / local — enforced capabilities, not labels), and **dual signature schemes** — Ed25519/minisign canonical, OpenPGP (GPG) built-in first-class for third-party ecosystems (§9.6, §10.2; full spec in [REPOSITORIES.md](REPOSITORIES.md)). v0.9 adds **cross-repository overlap resolution**: ambiguous bare package names prompt the user, the decision is remembered in the SQLite state database, revalidated on repo changes, and scriptable via `aslice repo prefer` (§9.6, §12.1; REPOSITORIES.md §10–§11). v1.0 adds the **logging design**: structured, local-only operation logs with a message-quality standard — every error is actionable, security events are unsuppressible, and nothing ever leaves the machine (§5.2, §8.1, §12.1, §12.5). v1.1 specifies **`aslice doctor`**: a read-only, scriptable sanity battery — machine, store, profiles, database, repositories, coexistence, environment — where every fail names its remedy and `--fix` is narrow and loud (§12.6). v1.2 opens a narrowly-scoped **system-software category**: kernel extensions and SIP-disabled development software become installable as declared `[system]` packages — warned at every decision point, elevated per-operation by a dedicated helper, gated by repository trust level — replacing the blanket rejection with an honest, reversible install path (§10.4, §10.7, §12.1, §12.7, §13.1). v1.3 adds **launchd-native service management**: packages describe services declaratively in the manifest (`[service]`, PACKAGE-FORMAT v0.4 §3.8), `aslice service` provides status/start/stop/restart over real launchd jobs, and upgrades orchestrate stop → atomic swap → restart so a running service is never updated out from under itself (§8.3, §10.4, §12.1, §12.8). Root-domain daemons go through `aslice-system` and the repository `system` capability; user agents stay unprivileged and ungated. v1.4 resolves open question #8: a failed post-upgrade service health check **asks the user whether to roll back** — an interactive prompt (default: stay and inspect) that swaps the generation back and restarts the previous service version on assent; non-interactive contexts never prompt and never auto-rollback, with `--rollback-on-service-failure` as the explicit unattended path (§12.1, §12.8). v1.5 adds **first-class multi-version runtime management** — the Volta lesson, taken seriously: version switching is the package manager's job, not a second tool's. A shim layer multiplexes versioned runtimes (php, nodejs, ruby, python, …) by session (`aslice use`), project (`aslice pin`), and default (`aslice default`) selections; interpreter-target tools like composer and yarn **ride** the selected runtime; and compiled extensions are slices bound to the runtime's ABI epoch, so an extension is always installed for exactly one runtime version — as are pip/gem/npm/pecl installs, through per-version userbases (§8.5, §12.9; schema in PACKAGE-FORMAT v0.5 §3.13). v1.6 adds **trust-store management** — `aslice ca-update`: the CA bundle becomes an ordinary signed, generation-managed slice (`ca-certificates`), its source configurable with the Mozilla root program (via curl's caextract) as the default; profile env wiring heals userland TLS (curl, git, python) completely; and an opt-in `aslice ca-update --keychain` imports the missing modern roots into the **System keychain** through `aslice-system` — machine-wide healing for Safari, Mail, and every SecureTransport app, recorded to the certificate and reversible to the certificate (§4.1, §12.6, §12.10). v1.7 extends trust-store management and amends a founding line: `aslice ca-update --crypto` upgrades the crypto-provider slices (modern ciphers/TLS for userland, with SecureTransport's limits printed, never hidden), `--apple-certs` imports Apple's own roots — which Mozilla's program does not carry — from a pinned `apple-roots` slice into the System keychain; and the absolute "never touch the system" stance becomes a declared exception: **`[system-patch]` packages** (§12.11) may replace Apple-provided files through a backup + profile-symlink + generation-rollback mechanism — consent at every decision point, official/local repositories only, refused paths blocked by construction (§2.2 N5, §10.4, §10.7, §12.10, §12.11, §13.1). v1.8 lands the review's remaining operational machinery — **self-update** (aslice is package zero: TUF-verified slice, generation swap, health-checked re-exec, automatic rollback — §5.2, §12.12), the **`on_request` install record** and **`aslice clean`** cache eviction (§8.4), the full day-two CLI surface (`outdated`, `reinstall`, package-hold `pin`/`unpin`, `livecheck`, `test`, `create`, `bump-pr`, `exec`, `shellenv`, `store verify` — §12.1), the **system-framework allowlist** (§13.1), and the **merge gates and project-hygiene documents** (§13.4) — and resolves the eight remaining open questions (§15): the prefix gains a per-user `~/.aslice` fallback (§8.1, §10.3), Starlark stays, local `abi = false` builds share store paths with DB-recorded provenance (§5.2), pointer-only formulae keep their current allowance, verified repositories keep enable-implies-binaries and the `system` capability, project-local dependency directories stay out of scope, and `verified` repositories may serve `[system-patch]` under an explicit per-repo grant (§12.11). v1.9 runs the **genesis audit** — a project-wide review of from-nothing bootstrap assumptions: the installer gains a loudly-printed plain-HTTP fallback for TLS-dead machines, fetching the same hash-pinned artifacts (§10.3); the repository tree's vendored-source role is made explicit — every source artifact the farm fetches lives in `blobs/sha256/`, and the client fetch order is upstream → formula `mirrors` → the repository's own blob area, all three under the same pinned sha256 (§9.6; machinery in BUILD-INFRA v0.6, the mirror story in REPOSITORIES v0.8, dead-upstream policy in ORCHARD-POLICY v0.8, review bookkeeping in HOMEBREW-REVIEW v0.11); the project-hygiene bullet records what actually shipped in Phase 0 — `SECURITY.md`, `CONTRIBUTING.md`, `docs/KEY-RUNBOOK.md`, and deliberately no `CODE_OF_CONDUCT.md` (§13.4); and the from-nothing sequence for the whole project is codified as `docs/GENESIS.md` (§14). v1.10 corrects the GitHub-hosted-CI facts: the `macos-13` Intel image was retired in December 2025, not autumn 2027 — the last hosted Intel label is `macos-15-intel`, available until August 2027 (§1, §9.2, §13 Phase A); adds the per-profile `aslice link`/`unlink` commands for `link = false` shadowing packages (§12.1; PACKAGE-FORMAT §3.8); and records the owner decision that unsigned vendor artifacts may ship in the extended orchard with `signer` omitted — announced loudly at every install — while the core stays signed-only (§12.2, §12.4; schema in PACKAGE-FORMAT §3.11, policy in ORCHARD-POLICY §12). v1.11 adds **declarative whole-machine setup** — `setup.toml`, the unified `aslice apply` verb (plan / lock / setup documents), `aslice export`, and `aslice import --from-brewfile` (§12.13; schema and semantics in [SETUP.md](SETUP.md)); N5's exception list grows to include consent-gated system-preference writes and `/etc/shells` enrollment (§2.2); supersedes the `aslice bundle` wishlist proposal of HOMEBREW-REVIEW §4.6. v1.12 is an editorial pass — prose revised for directness throughout; no design, schema, or factual changes. v1.13 is a second editorial pass — sentence-level revision for readability; no design, schema, or factual changes. v1.14 is a prose polish in the project's technical-writing voice — six sentences reworded for precision (§1.1, §4.1, §5.3, §7.5, §9.3, §11); no design, schema, or factual changes. v1.15 adds a NOMENCLATURE.md vocabulary reference to the header; no design, schema, or factual changes
- **Scope:** macOS 10.11 (El Capitan) through 12 (Monterey), Intel x86_64 only
- **Implementation:** C++20 core, single self-contained binary
- **Audience:** Maintainers, founding contributors, and early reviewers
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md) — project terms, acronyms, and the Homebrew translation table.

---

## 1. Context and Opportunity

### 1.1 The gap that is opening

The Intel-Mac package-management ecosystem is losing its maintainer on a known schedule:

- **Homebrew 7.0.0 (September 2026)** moved Intel x86_64 to Tier 3 ("not supported"): no new bottles are built for Intel, CI coverage is gone, and macOS 10.15 support was removed outright. Existing bottles stay hosted but freeze in time.
- **September 2027:** Homebrew plans to remove the ability to run on Intel systems at all.
- **GitHub Actions:** the `macos-13` Intel runner image was retired in December 2025; its replacement `macos-15-intel` is the last hosted Intel label, available until August 2027, after which hosted CI can no longer natively build x86_64 macOS binaries at all.
- **Apple:** macOS 26 Tahoe is the final release for Intel Macs; macOS 27 Golden Gate is Apple-silicon-only. Intel Macs receive security updates only, on a countdown.

A large installed base remains: Homebrew's own analytics, discussed publicly in mid-2026, put Intel at roughly a quarter of active Homebrew Mac installations. Everything from El Capitan to Monterey is now outside Homebrew's support window — and precisely where these machines are stranded.

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

Each clause is developed in its own section: the platform axes in §4, the variant model in §7, the security model in §10.

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
- **G10 — First-class multi-version runtimes.** php, nodejs, ruby, and python — and anything else users keep in several versions — install side by side and switch with Volta-grade ergonomics: session, project, and default selection via a shim layer, with extensions bound to exactly one runtime version (§12.9).

### 2.2 Non-goals

- **N1 — Apple Silicon.** Not now, not by accident. The architecture must not preclude it, but no engineering effort goes to it. Homebrew owns that space.
- **N2 — macOS 13+ on Intel.** Tahoe-era Intel machines (2019–2020) are welcome, but the build targets remain 10.11–12; Ventura+ Intel gets whatever falls out naturally.
- **N3 — GUI application *polish* at launch.** Vendor-binary packages (§12.4) cover `.pkg`/`.dmg`-only software — CLI tools and apps alike. What is deferred is app-specific chrome: Launchpad integration, updater handoff, a GUI manager. Core CLI packages still come first.
- **N4 — Linux/Windows.** The codebase should stay portable, but no effort is spent there.
- **N5 — Replacing the system.** aslice lives in its own prefix and never modifies the OS by default: `/System`, `/usr`, and Apple's binaries are read-only to it. The exceptions are few, declared, flagged, consent-gated, and reversible: the `[system-patch]` category (§12.11) — backup + symlink + rollback, trust-gated — because on a frozen platform some fixes are only possible in Apple's territory; and declarative setup's system-preference writes and `/etc/shells` enrollment (§12.13), which run through the same helper, record their pre-change values, and roll back with their generation. `/usr/local`'s ownership is never touched regardless.
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
| Prefix ownership of `/usr/local` chowned to the user | Security researchers have criticized this for a decade | Private prefix `/opt/aslice` — with a documented per-user `~/.aslice` fallback — created once by an installer, never world-writable, never sudo thereafter (§10.4) |
| Ruby runtime, git-cloned taps | Slow startup, slow `brew update` | Single C++ binary, content-addressed TUF-signed index with snapshot diffs (§11) |
| CI hostage to GitHub-hosted Intel runners | The current collapse | **Self-hosted build farm on real Intel hardware** from day one (§9.3) |
| Opt-out usage analytics | Consent assumed; users are a metrics pipeline | **No telemetry or analytics of any kind, ever** — aslice is infrastructure, not a product (§2.2 N7) |
| Casks may run `installer script:` and vendor pkg hooks | Arbitrary vendor code with user (or admin) privileges at install | **Vendor binaries install payload-only** (§12.4): pkg/dmg contents are extracted per a declarative map, signer-pinned, and embedded scripts never execute |
| Versioned runtimes are separate formulae (`php@8.1`, `python@3.12`); switching means `brew link --overwrite` or an external manager (nvm, pyenv, rbenv, Volta) shadowing brew | Two sources of truth for what `python3` resolves to; the package manager and the version manager fight over PATH | **Runtime version management is built in** (§12.9): one formula with release streams, shims resolving session/project/default, riding tools, and extensions ABI-bound to the runtime |

---

## 4. Platform Matrix and Microarchitecture Strategy

### 4.1 The OS axis collapses — at 10.11

Naively, 5 OS versions × 3 µarch flavors = 15 builds per package. In practice it is **3**:

macOS has a mature deployment-target mechanism. A binary compiled with `-mmacosx-version-min=10.11` runs correctly on every release from El Capitan through Monterey, provided it avoids (or weak-links against) newer APIs. So the default remains: **build once against the oldest target, per µarch flavor** — the floor is 10.11 now instead of 10.15.

The lower floor has real consequences; each is handled explicitly:

- **A wider `min_os` spread.** Many modern upstreams cannot cleanly target 10.11: C++17/20 library features, `clock_gettime` and friends (absent before 10.12), `thread_local` quirks, modern IPC. Formulae declare `min_os`; the index filters per OS. Expect a natural stratification — the core orchard mostly at a 10.11 floor, much of the extended orchard at 10.12–10.14 floors. A package that *could* build for 10.11 but isn't worth the patching declares its floor and moves on.
- **libc++ comes from the toolchain, not the system.** System libc++ on 10.11 predates half of C++17. All C++ packages statically link a modern libc++ from `aslice-toolchain` (§4.3), so the age of the system runtime stops mattering.
- **HFS+ is back in the window.** 10.11–10.12 predate APFS entirely, and HDDs stayed HFS+ into the Mojave era. Everything filesystem-dependent degrades gracefully: `clonefile` → hardlink → copy (§11), and generation switching relies on `rename(2)`, which is atomic on HFS+ as well.
- **Ancient TLS and expired root certificates** make the 10.11–10.13 system trust store nearly unusable for the modern web. `aslice-fetch` links its own TLS stack and CA bundle and verifies against pinned, countersigned hashes regardless — the security model never depended on the system store. But *userland* still does: the curl, git, and python a user runs trust the rotting system roots, and so do Safari and Mail. `aslice ca-update` (§12.10) heals both halves — a signed, generation-managed CA bundle for the profile, and an opt-in System-keychain import for the machine — with `--crypto` covering the cipher/TLS stack of userland and `--apple-certs` the Apple-private roots that Software Update and the App Store chain to.

### 4.2 The µarch axis grows: three flavors

Extending the floor to 10.11 pulls pre-SSE4 CPUs into the supported population, so the flavor space grows from two to three. aslice adopts the x86-64 psABI microarchitecture levels as its flavor vocabulary:

| Flavor | Level | Key ISA | Who needs it |
|---|---|---|---|
| `v1` | x86-64 baseline | SSE2 | Runs on every 64-bit Intel Mac; the *only* choice for Core 2 Duo machines (2007–2009, Merom/Penryn) found on 10.11–10.13 |
| `v2` | x86-64-v2 | SSE4.2, POPCNT | Nehalem/Westmere and later — Mac Pro 2009+, most 2010+ Macs, and everything Catalina-capable |
| `v3` | x86-64-v3 | AVX2, BMI2, FMA | Haswell+ (2014→); 10–40% faster on codecs, crypto, compression, math |

Notes:

- **There is no x86-64-v4 (AVX-512) flavor.** No Intel Mac ever shipped AVX-512; the flavor space stays at three, which keeps the binary matrix and the UX small.
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

Privilege separation is structural: the helpers are separate executables (spawned by the main binary, which re-executes itself with a subcommand) running under Seatbelt profiles (§10.5) with only the capabilities their phase requires. The fetch helper can't touch the store; the extractor has no network; the linker has no network and no compiler. Each helper is small (a few hundred lines) and independently auditable — this is where the C++ attack-surface discipline pays for itself. `aslice-extract` is also the component that expands vendor `.pkg` (xar) and `.dmg` payloads (§12.4) — archive and installer-payload handling are the same trust problem and get the same tiny, fuzzed code path. The same helpers are what the build farm executes: the farm harness is an orchestrator that spawns `aslice build` jobs, and every build — farm or laptop — runs through this identical sandboxed executor (full design: [BUILD-INFRA.md](BUILD-INFRA.md)).

### 5.2 Major components

| Component | Responsibility | Notes |
|---|---|---|
| **Index client** | Fetches and caches the package index | TUF metadata + zstd-compressed JSON snapshots; incremental updates via snapshot diffs, not git |
| **Solver** | Version + variant resolution | PubGrub-style CDCL algorithm over (name, version, variant) space; flavors as hard constraints (§7.5) |
| **Store** | Content- and identity-addressed package trees | `/opt/aslice/store/<name>-<version>-<buildid>/` (§8) |
| **Profiles / generations** | Atomic merged views | Symlink forests with rename-swap; rollback = flip a symlink (§8.3) |
| **Builder** | Fetch→unpack→patch→configure→build→install in sandbox | Deterministic environment; DESTDIR staging; ABI scan on output (§7.3) |
| **Verifier** | Signature, hash, ABI, and policy checks before linking | Nothing reaches the profile without passing (§10.2) |
| **Database** | Installed-set and metadata | Single SQLite file, WAL mode, prepared statements; the only mutable state besides the store. Holds the installed set — each record stamped `on_request` (user-requested vs pulled-in, §8.4) and **provenance** (farm slice vs local build, surfaced by `info`/`audit`/`doctor`) — per-repo key pins and trust levels, remembered overlap resolutions, solve cache, and operation history ([REPOSITORIES.md](REPOSITORIES.md) §11) — records decisions and state, never grants authority; verification never consults it for trust |
| **Reporter** | SBOM generation, `audit`, provenance display | SPDX SBOM per package; OSV feed integration (§10.6) |
| **Logger** | Structured operation and security-event logging | JSONL on disk under `log/`, human rendering on the terminal; local-only, forever (§12.5) |
| **Shim resolver** | Version selection for multi-version runtimes | Multicall `argv[0]` dispatch; session → project → default resolution; exec-only, no wrapper process (§12.9) |
| **Self-updater** | Updates aslice itself through the package machinery | aslice is package zero: TUF-verified slice, generation swap, health-checked re-exec, automatic rollback on failure (§12.12) |

### 5.3 Why C++ — and what it costs

The user-facing case for C++ is startup time, single-binary deployment across 10.11–12 with no runtime story, direct Mach-O/dyld/Seatbelt API access, and the profiler, sanitizer, and fuzzer tooling the performance work of §11 needs. The cost is memory safety, which is a security-goal liability. aslice treats it as an engineering constraint:

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

- **No Turing-complete host code at install time.** Starlark executes only during *builds*, inside the sandbox, with capabilities enumerated in `ctx`. There is no `post_install` hook that runs on the user's machine — post-install behavior (creating data dirs, registering launch agents) is expressed declaratively in `package.toml` and executed by aslice itself. (Homebrew 7.0 is migrating the same direction with `*_steps`; aslice starts there.)
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

Install of a `.slice` is: verify signature → verify payload hashes → extract into store path → ABI-check against the packages that will link to it → register in SQLite → link into profile. **No code from the package executes at any point.** A repackaged vendor binary produces the same `.slice` shape — its manifest's provenance section records the vendor artifact hash and signer instead of a build recipe.

---

## 7. The Variant and ABI Model — Interoperability by Design

Homebrew's experience is the cautionary tale: options in `homebrew-core` were removed in 2019 because every variant combinatorially broke bottle assumptions and support load. aslice's answer is to make the distinction Homebrew never formalized: **what changes the ABI versus what merely changes the bits.**

### 7.1 The three kinds of build-time choice

| Kind | Examples | Effect on identity | Effect on interop |
|---|---|---|---|
| **µarch flavor** | `v1` / `v2` / `v3` | Hard selection constraint | ABI-identical; a higher-flavor binary won't *run* on lesser hardware |
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

Note what this does *not* do: it does not hash the dependency closure (the Nix model). Nix's approach gives perfect hermeticity at the cost of making substitution impossible whenever any dependency differs — the interop failure this model must avoid. aslice instead gets interop from the ABI contract below.

### 7.3 The ABI contract (the Mach-O insight)

macOS already ships an interop mechanism that package managers underuse: **Mach-O install names with compatibility versions.** Every dylib records an install name and a `compatibility_version`/`current_version`; every client records what it linked against. dyld enforces it at load time. aslice formalizes what the linker already knows:

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
- **Breakage is caught at install time, not at runtime** three weeks later. If a rebuilt library no longer covers what its clients reference, the solver refuses the combination and names the symbol set that regressed.
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

Version and variant resolution uses a PubGrub-style CDCL algorithm:

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
- **Per-user installs** (`~/.aslice` as prefix) are the documented no-admin fallback layout (open question #1, resolved v1.8): the installer offers it when `/opt/aslice` cannot be created, farm slices are relocated via the manifest metadata, and everything else — profiles, generations, rollback, logging — is identical. Multi-user shared installs work because profiles, not ownership, define the view.

### 8.2 Profiles as the interoperability surface

A profile is the merged symlink forest (bin/, lib/, share/, …) that users put on PATH: `/opt/aslice/profiles/default/bin`. Linking is nothing but symlink creation into a generation directory, so any combination of store paths — prebuilt, user-compiled, different flavors, old and new versions of different packages — coexists under one view. Collisions (two packages shipping `bin/foo`) are first-class: the profile records priority, and `aslice profile prefer` flips it without touching the store.

### 8.3 Generations: atomic switching and rollback

Every mutating operation builds a **new generation directory** and then swaps one symlink — atomic via `rename(2)` on both APFS and HFS+. This yields, almost for free:

- `aslice rollback [generation]` — instant return to any previous state.
- `aslice switch-generation 38` — bisect a broken upgrade in seconds.
- **Interrupted installs cannot corrupt the live profile.** A crash mid-install leaves the old generation live; the partial new generation is garbage-collected.
- **Services are quiesced around the swap.** An upgrade that touches a package with a running service stops the launchd job first, swaps, then starts it again — the binary is never replaced under a running process (§12.8).
- `aslice gc` removes store paths unreachable from any retained generation (with `--older-than 30d` style policies).

### 8.4 Garbage collection discipline

The store grows unboundedly without GC — the classic Nix complaint. Defaults: keep the last 5 generations, auto-GC on install when store exceeds a configurable watermark (default 20 GB), and never collect a store path referenced by a running process's profile generation. `aslice gc --dry-run` always shows what would go and why.

**Installed-on-request tracking.** Every DB install record carries `on_request = true|false` — whether the user named the package or the solver pulled it in. `aslice autoremove` collects nothing reachable from an `on_request` root, cross-checked against retained generations, and `aslice mark <pkg> --on-request/--as-dependency` repairs the record when the user disagrees with it. Package holds live here too: `aslice pin <pkg>` / `unpin` record the hold in the same table, `upgrade` skips held packages, and `outdated` says so rather than hiding them.

**Cache eviction.** The GC above owns the *store*; the *cache* — downloaded slices, source tarballs, index snapshots, ccache — is owned by `aslice clean`: LRU eviction of anything not referenced by an installed package or retained generation, watermark-driven (default: evict when the cache exceeds 10 GB, never touch anything younger than 30 days), with `--dry-run` symmetry to `gc`. Source tarballs are the sleeper category: `--build-from-source` users accumulate them silently.

### 8.5 Shims: the multiplexing layer

Profiles have one structural limitation: a name like `bin/php` can point at only one store path per generation. That is correct for libraries — the profile is the interop surface and ambiguity there is a bug — but wrong for **runtimes**, where several versions installed at once is the normal state of a working machine. aslice resolves it with a thin **shim layer** (§12.9): a directory of multicall shims that sits *before* the profile on PATH and multiplexes versioned tools according to session, project, and default selections. Shimmed names are not linked into generations at all; the profile instead links versioned aliases (`bin/php8.4`) for services and scripts that must name an exact runtime. The store, generations, and rollback semantics are untouched — a shim only ever chooses among already-installed store paths; it creates no state the generations don't own.

---

## 9. Distribution and the Build Farm

### 9.1 Hosting on GitHub — two layers, mirror-friendly

**Layer 1: Package blobs as OCI artifacts on GHCR.** Slices are pushed to `ghcr.io/aslice/<name>` as OCI artifacts (ORAS), giving content-addressed blob storage, dedup across versions via shared layers, resumable/ranged downloads, and free bandwidth within GitHub's generous registry limits. Every tag is additionally anchored to a signed manifest digest.

**Layer 2: The index as static, signed files.** The package index (TUF metadata + zstd JSON snapshots) is published both to a GitHub Release asset stream and to `raw`/Pages endpoints, and — critically — is *trivially mirrorable*: any static HTTP server can host a complete aslice repo. Mirror support is a first-class config (`mirrors = [...]`), not an afterthought, because the long-term health of a legacy-platform project cannot depend on one vendor's continued generosity.

**Fallback:** plain GitHub Releases assets (2 GB per asset ceiling — no package comes close) for environments where GHCR auth/rate limits are a problem. The client treats GHCR, Releases, and static mirrors as interchangeable transports for identical, identically-signed content. All three are *transports* for the canonical distribution unit — the **repository tree** (§9.6): a static, signed, mirrorable directory of TUF metadata, index snapshots, formula metadata, and blobs. GHCR is where blobs may live; a repository is what a client consumes.

### 9.2 The GitHub CI problem

GitHub-hosted Intel runners are a deprecating asset: `macos-11`/`macos-12`/`macos-13` images are already retired (the last of them in December 2025), and the replacement `macos-15-intel` label — the final hosted Intel runner — is available only until August 2027. **Any design whose correctness depends on hosted Intel CI is a dead design.** aslice therefore treats GitHub CI as a convenience layer and the self-hosted farm as the system of record.

### 9.3 The build farm

*The harness that runs on this hardware — identical to what runs on a user's machine — is specified in [BUILD-INFRA.md](BUILD-INFRA.md): job manifests, scheduling lanes, the quarantine/signing trust model, community evidence builders, and VM matrix orchestration. This section is the hardware summary.*

**Phase A (launch):** GitHub-hosted `macos-15-intel` runners, while they exist (until August 2027), cover what hosted Xcode can reach (~10.13+ deployment targets) using the self-hosted toolchain. They are a bonus layer; the system of record is the farm below, which exists precisely because hosted Xcode can no longer target 10.11/10.12 at all. AVX2 (`v3`) builds compile fine on any Intel runner (compiling AVX2 code doesn't require executing it); *tests* for v3 slices run on AVX2 hardware only, while `v1` and `v2` slices test everywhere.

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

GHCR, Releases, and static mirrors are *transports*. The canonical distribution unit — what a client consumes — is the **aslice repository**: a self-contained, signed, static tree:

```
repo.example.org/
 ├── tuf/            # root.json, snapshot.json, timestamp.json, targets.json
 ├── index/          # zstd JSON snapshots + diffs (the solver's world)
 ├── formulas/       # resolved package metadata (pure data; never executable)
 └── blobs/sha256/   # slices and vendored sources, content-addressed
```

- **Vendored sources live here too.** The farm deposits every source artifact it ever fetches into `blobs/sha256/` (BUILD-INFRA §3); a client's fetch order is upstream → formula `mirrors` → the repository's own blob area — all three verified by the same pinned sha256, so the archive is a fallback, never a new trust path. Upstreams disappear; an orchard that vendors its sources does not notice.
- **Anyone can host one.** Any static HTTP server, a GitHub Pages site, a GHCR org (blobs in OCI, index overlaid), or a `file://` directory on a lab NAS. A mirror is a full copy of the tree; clients fail over across a repository's declared mirrors.
- **Repositories carry recipes *and* binaries.** `formulas/` holds the resolved metadata the solver needs (recipes); `blobs/` holds the slices — each tagged in the index with its OS-support bounds (`min_os`/`max_os`), flavor, and arch. A repository may be *binary-only* — repackaged vendor software with no orchard behind it at all (§12.4) — which is how communities serve niche pkg/dmg-only ecosystems (audio plugins, lab instruments) without asking the project for orchard space.
- **Trust is per-repository, with inherent levels.** Every repository has one of four enforced trust levels — `official` (pre-pinned, threshold keys), `verified` (project-countersigned community repos, shipped disabled), `third-party` (user-added, TOFU), `local` (development trees, formulas only unless signed). Levels are capability sets enforced by the solver and verifier — what namespaces a repo may serve, whether its binaries may install, whether it may shadow core names — not labels. `aslice repo add <url>` pins the repository's root key fingerprint on first use (TOFU): the fingerprint is displayed with a strong recommendation to verify out-of-band, stored in the DB, and any later change blocks the repository and is reported. The project ships an **official source list** (`sources.toml`, itself a TUF target) with core + extended pre-pinned — the core fingerprint is also compiled into the bootstrap binary — and verified community repos listed for discovery. The project's canonical repository ships pre-pinned in the bootstrap. Full model: [REPOSITORIES.md](REPOSITORIES.md).
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
- **Key compromise response:** root key is 3-of-5 threshold across founding maintainers; revocation and rotation are covered by a practiced runbook.

### 10.3 Trust bootstrapping

The installer is a small, auditable shell script that fetches two things — the `aslice` bootstrap binary and the TUF root metadata — each pinned by hash in the script *and* cross-checkable against a signed checksums file on a second transport (Release asset + Pages). Everything after that first step is verified by TUF. The script never runs `sudo` except, optionally, to create `/opt/aslice` and chown it to the invoking user — once. When the invoker has no admin rights, the installer offers the **per-user fallback layout** instead: the same tree under `~/.aslice` (§8.1) — identical semantics, user-owned by construction, no sudo at any point. Two documented layouts, chosen once at install; arbitrary custom prefixes remain possible through the relocation metadata, but the two defaults are the tested, supported paths.

**When the transport itself is dead.** On a machine whose TLS stack cannot complete a handshake with anything modern — the day-zero condition of this platform — HTTPS fetches can fail before a single byte arrives. The installer's fallback is plain HTTP for the *same hash-pinned artifacts*: the bootstrap binary and the TUF root are fetched over HTTP, verified against the pins and the minisign signature as before, and the fallback is announced with a banner naming the degraded transport and the reason it is safe; it is never silent. The pins, the minisign signature, and the TUF root are the trust; the transport never was (§4.1). A machine too old for TLS gets its package manager anyway — it just gets told, in so many words, what protected it.

### 10.4 Privilege discipline

- **No sudo in steady state.** Not for install, not for upgrade, not for uninstall. The prefix is user-owned from creation.
- **Never touches `/usr/local`.** Coexistence with Homebrew/MacPorts is by construction, and the historic `/usr/local` ownership flaw is not inherited. Vendor-binary apps install under `/opt/aslice/apps/` — never `/Applications` — with a per-user `~/Applications` symlink as the opt-in convenience (§12.4).
- **No setuid binaries, no helper daemon at launch.** A future multi-user mode (shared lab machines) will use a launchd daemon that accepts only TUF-verified operation plans over a local socket with peer-credential checks — designed, but gated behind demand.
- **One scoped exception: `aslice-system`.** Declared system-software packages (kexts, SIP-disabled development tools — §12.7) require privileged steps no user-space manager can perform. Those steps are executed by a single tiny auditable helper that elevates **per operation, with explicit consent, for only the declared actions** — it is not a daemon, holds no ambient authority, and every invocation is an unsuppressible logged security event (§12.5). Its scope also covers **system-domain service operations** — bootstrapping and removing root LaunchDaemons for declared `domain = "system"` services (§12.8) — and **declared `[system-patch]` file replacements** (§12.11: backup, symlink swap, restore) — with the same per-operation consent and logging; user-domain agents never touch it. The steady-state rule stands: nothing else in aslice ever elevates.

### 10.5 Sandboxed builds

Every build phase runs under a Seatbelt (`sandbox-exec`) profile — Seatbelt predates the entire 10.11–12 window and is present on every supported release:

| Phase | Profile |
|---|---|
| fetch | Network to declared hosts only; write to cache dir only |
| unpack/patch/configure/build | **No network at all**; write only within the build dir; read-only toolchain and store |
| install (to staging) | No network; write to staging dir only |
| test | No network by default; opt-in `test_network = true` per formula, logged at warn |

Vendor-binary payload extraction (`xar` expansion, `hdiutil` attach, cpio unpack) runs under the unpack profile — no network, writes confined to staging; there is no phase in which a vendor artifact gets to run anything.

Seatbelt is deprecated by Apple on newer releases but frozen-in-place across our entire (frozen) target window; the profile abstraction (`SandboxPolicy` compiled to Seatbelt today) is designed so a future backend can replace it without touching formulae. A build that escapes its profile fails the build and files an automatic audit event.

### 10.6 Vulnerability and SBOM pipeline

- Every slice embeds an **SPDX SBOM** generated from the build manifest (sources, patches, dependency closure, toolchain). Vendor-binary slices ship a payload-only SBOM (file list, hashes, signer) — less deep than a source SBOM, still enough for `audit` to bind CVEs via CPE.
- `aslice audit` matches the installed set against OSV/GitHub Advisory feeds and reports CVEs with affected-version ranges — locally, offline-capable with a cached feed.
- Formulae declare upstream security-contact and EOL policy; packages past upstream EOL are surfaced in `audit` and require `--allow-eol` to install.

### 10.7 What this does not solve

- A malicious *core maintainer* with signing access can still ship bad slices; threshold keys, reproducible-build cross-checks (§9.5), and a public transparency log of index snapshots are the mitigations, and they reduce but do not eliminate insider risk.
- Sandboxing contains *builds*, not the runtime behavior of installed software. aslice is a package manager, not an endpoint product. The same distinction applies to vendor binaries: payload-only installation removes *installer-script* risk, not the risk of the vendor binary itself — signer pinning and hash pinning ensure you get the vendor's artifact unmodified, and that is all they ensure.
- **System packages (§12.7) step outside the sandbox story.** A kext runs in kernel space — a bug panics the machine — and SIP-disabled development tools weaken the protections of §10 for *all* software, not just themselves. aslice's guarantee for this category is narrower and says so: the bits are exactly the declared, verified ones; the privileged steps are exactly the declared ones, performed by aslice's own helper with explicit consent; the user was warned at every decision point. Nothing more is claimed, and the category is never servable by third-party repositories.
- **System patches (§12.11) step furthest outside the sandbox story.** A `[system-patch]` package replaces an Apple-provided file for *every* user and process on the machine; a bad one breaks the OS, not just itself. aslice's guarantee here is the narrowest in the design and is stated as such: the replacement is exactly the declared, signed, verified content; the original is backed up and restorable to the byte; refused paths (kernel, dyld, libSystem, `/System`, platform-binary dylibs) are refused by construction, not by policy; and consent was explicit at every decision point. Nothing more is claimed.
- C++ memory-safety risk in aslice itself is managed per §5.3; the parsers and extractors — the untrusted-input surfaces — get the fuzzing and the smallest footprints.

---

## 11. Performance Model

The performance goals, and the mechanism that achieves each:

| Goal | Mechanism |
|---|---|
| **CLI startup < 10 ms** | Single Mach-O binary, static libc++, no interpreter, no JIT, lazy dyld binding, no network on the hot path |
| **`install` of a cached slice < 300 ms** | Verify (Ed25519: microseconds) → zstd decompress → APFS `clonefile` into store (HFS+ systems fall back to hardlink/copy) → symlink generation swap. No relocation pass on default prefix. |
| **Index update < 200 ms typical** | Snapshot diffs against a cached snapshot hash — a few KB on a typical day, versus Homebrew's git-fetch taps |
| **Solve < 50 ms typical** | SQLite-backed package index with prepared statements; PubGrub with clause caching; memoized per snapshot |
| **Downloads saturate the pipe** | HTTP/2 multiplexing, 8-way parallel fetches, resumable ranges, zstd `--long` delta-friendly payloads |
| **Cold full install of a large tree (e.g., `ffmpeg` closure) < 10 s on SSD** | Parallel fetch + pipeline overlap (decompress stream N+1 while linking N) |
| **Builds: near-zero manager overhead** | The builder's job is to get out of the way: Ninja parallelism, `ccache`-compatible compiler cache in `cache/`, tmpfs-backed build dir when RAM allows |
| **Shim dispatch < 1 ms** | Multicall binary (no interpreter, no JIT), one prepared-statement DB lookup, `exec` instead of fork — the shim adds no measurable latency to `php -v` in a hot loop (§12.9) |

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
aslice ca-update [--check]             # refresh the CA trust bundle: signed slice, generation-managed (§12.10)
aslice ca-update --keychain            # also import missing roots into the System keychain — opt-in, recorded, reversible
aslice ca-update --crypto              # also upgrade the crypto-provider slices — modern ciphers/TLS for userland (§12.10)
aslice ca-update --apple-certs         # also import Apple's own roots (Software Update, App Store, iCloud, Developer ID) into the System keychain
aslice rollback / switch-generation / history
aslice service list / status <pkg>       # launchd truth: pid, state, last exit (§12.8)
aslice service start / stop / restart <pkg> / service run <pkg>   # run = foreground, for debugging
aslice install php@8.4                   # a runtime release stream; coexists with every other installed stream (§12.9)
aslice use php 8.4                       # select for the current shell (session) — via shell integration or eval
aslice pin php 8.4                       # select for this project tree — writes ./aslice.toml (commit it)
aslice default php 8.4                   # select the profile-wide fallback
aslice versions php / aslice which php   # installed streams; trace *why* this php resolved
aslice install php-redis                 # extension slice — binds to the selected php's ABI epoch (§12.9)
aslice install composer                  # a tool that *rides* the selected runtime (§12.9)
aslice init zsh                          # prints the shell integration for `aslice use` (bash/zsh/fish)
aslice gc [--dry-run] [--older-than 30d]
aslice orchard add myorg/orchard / orchard pin myorg/orchard <commit>
aslice repo add https://repo.example.org   # add a signed repository (§9.6)
aslice repo list / repo remove <name> / repo build / repo publish
aslice repo enable / repo disable <name>   # verified repos ship listed-but-disabled
aslice repo re-pin / keys / audit <name>   # trust-level machinery (REPOSITORIES.md §7)
aslice repo prefer / resolutions / forget  # overlap decisions, remembered in the state DB (REPOSITORIES.md §10)
aslice adopt --from-homebrew           # migration assistant (§13.3)
aslice apply setup.toml                  # declarative whole-machine setup: packages, runtime selections, services, defaults, login shell (§12.13); the same verb replays aslice.lock and executes plan.json
aslice export [--defaults com.apple.dock,…]   # capture this machine as a setup.toml — leaves + selections; preferences on demand (§12.13)
aslice import --from-brewfile Brewfile   # translate a Brewfile into a setup.toml, skip list printed (§12.13)
aslice config set flavor v2            # overrides
aslice doctor                          # environment sanity checks (§12.6)
aslice log [--follow] [--level debug]  # query the local operation log (§12.5)
aslice install foo --accept-system-changes   # explicit consent for [system] and [system-patch] packages, non-interactive (§12.7, §12.11)
aslice system-patch list / status        # which Apple-provided files are currently replaced, by which package (§12.11)
aslice self-update [--check]           # aslice updates itself — package zero, generation swap, health-checked (§12.12)
aslice outdated [--json]               # what would upgrade, and why; honors pins
aslice reinstall ffmpeg                # same version, fresh link — repairs a damaged profile entry
aslice link openssl@3 / aslice unlink openssl@3   # per-profile opt-in/out for `link = false` shadowing packages (PACKAGE-FORMAT §3.8); each flip is a new generation
aslice pin openssl / aslice unpin openssl   # hold a package: upgrade skips it, outdated says so (one argument — distinct from runtime `pin php 8.4`, §12.9)
aslice clean [--dry-run]               # cache eviction (§8.4); gc owns the store, clean owns the cache
aslice livecheck [pkg|--all]           # query upstream for newer releases (PACKAGE-FORMAT §3.15)
aslice test ffmpeg                     # run a package's tests.star against the installed slice, on demand
aslice create <url>                    # fetch, hash, sniff the build system, emit a package.toml draft
aslice bump-pr <pkg> <version>         # the human version bump: edit, lint, smoke-build one flavor, open the orchard PR
aslice exec ffmpeg -- ffprobe in.mov   # run a command in a temporary profile view, discarded on exit
aslice shellenv                        # print PATH/MANPATH/INFOPATH + trust-store exports for the current profile (pure echo, no writes)
aslice store verify [--quarantine <pkg>]   # re-hash store paths against manifests — the immutability tripwire (§8.1)
# every command: -v / -vv raise verbosity, --quiet suppresses all but errors,
# --log-format json|human selects rendering (§12.5)
```

### 12.2 Interaction principles

- **Binary is the default, source is a flag.** A user who never passes `--variant` or `--cflags` never sees a compiler.
- **Every decision is explainable.** `--explain` on any command shows the solver's derivation; `--dry-run` shows the exact plan: which slices, which local builds, which generation change.
- **Announce, don't bury.** EOL packages, unsigned orchards, deprecated variants, fallback-to-source events, and unsigned or non-notarized vendor binaries are always announced in the output. `doctor` reports what the machine can and cannot do rather than pretending uniformity.
- **Scriptable:** `--json` on everything; stable exit-code contract; machine-readable `plan`/`apply` split (`aslice plan install ffmpeg > plan.json && aslice apply plan.json`) — which is also what the future multi-user daemon consumes.

### 12.3 Orchards, repositories, and trust levels

Orchards are git repos of formula directories — the *authoring* format. Repositories (§9.6) are the *distribution* format. Trust is explicit at both layers:

- **Core/extended orchards:** signed by project keys; Starlark + TOML only.
- **Third-party orchards:** installed disabled by default; enabling one prints its trust implications (its formulae can cause local source builds — sandboxed — but *never* execute at binary-install time, because nothing ever does).
- **The canonical repository:** the project orchards compiled and signed by project keys; pre-pinned in the bootstrap.
- **Third-party repositories:** added explicitly, root key pinned on first use (TOFU, fingerprint displayed, changes blocking). A third-party repository can serve its own signed slices — including binary-only vendor repackagings — under its own keys. The one thing no repository can do is make aslice execute package code at install time; that door is closed structurally, not by trust policy.

### 12.4 Vendor binaries (pkg/dmg) and GUI apps

Some software for this platform will only ever ship as a `.pkg` installer or a `.dmg` — commercial audio tools, vendor CLIs, frozen releases of abandoned apps. aslice installs it **without ever running installer code**:

- **`.pkg`:** expanded with `xar`/`pkgutil --expand`; only the `Payload` is extracted, per the declarative path map in the formula. `preinstall`/`postinstall` scripts are never executed. Packages whose function genuinely *requires* script execution remain out of scope — the payload-only line holds. Drivers and kexts are **not** rejected, though: they install through the declarative system-software category (§12.7), where the privileged steps are performed by aslice's own helper from manifest declarations, never by vendor scripts.
- **`.dmg`:** attached read-only via `hdiutil -nobrowse -readonly`; declared items copied. No autolaunch, no quarantine propagation.
- **Apps** install under `/opt/aslice/apps/` (owned by the prefix, not `/Applications`), with an optional per-user `~/Applications` symlink; Finder and Launch Services pick them up from either location.
- **Provenance is pinned.** The formula records the expected signing identity (`Developer ID Application: Vendor (TEAMID)`) and notarization expectation; the verifier checks the signature *before* extraction and hard-fails on a silent signer change — a classic supply-chain attack against binary distribution. An unsigned vendor artifact carries no signer to pin: it is permitted only in the extended orchard, declared with `signer` omitted and announced at every install (PACKAGE-FORMAT §3.11, ORCHARD-POLICY §12); the core orchard stays signed-only.
- **Two distribution modes, license-driven.** `redistribute = true` → the farm repackages the payload into a normal `.slice`, hosted in the repository like any other (best UX: atomic, resumable, rollback-able). `redistribute = false` → the formula stays a pointer: the client fetches the vendor URL itself (hash- and signer-pinned), extracts locally in the sandbox, installs payload only. Same install semantics; only the transport differs. Non-redistributable software still gets generations, lock files, and `audit`.
- **OS support is tagged per artifact.** Each `[[binary]]` entry carries its own `min_os`/`max_os`/`arch`, so a vendor's "legacy" build for 10.11–10.13 and "current" build for 10.14+ coexist in one formula and the solver picks the artifact matching the machine — never a "this application cannot be opened" surprise after install. Vendor claims are checked at pack time against the bundle's `LSMinimumSystemVersion` and the pkg's Distribution requirements where present; mismatches are lint errors, because an accurate tag is the entire point.
- **32-bit payloads install where — and only where — the OS can run them.** 10.11 through 10.14 are the last macOS releases that execute 32-bit code, and a large share of pkg/dmg-only software on this platform (audio plugins, lab instruments, frozen pro tools) is i386 or universal. Vendor artifacts may therefore carry `arch = ["i386"]` or `["x86_64", "i386"]`; the pack-time verifier inspects every Mach-O slice in the payload with `lipo`-style logic and derives the true ceiling — an i386-containing artifact must declare `max_os = "10.14"` (or lower), and on 10.15+ it is a clean solve-time refusal, not an install that can't launch. Universal payloads are installed **whole**: no `lipo -thin` stripping, ever — thinning a fat binary invalidates the vendor's code signature, and signature integrity outranks disk savings. This changes nothing about what aslice *builds* (N6: farm slices stay x86_64-only); it is distribution, not compilation.

Vendor binaries participate in the store, generations, profiles, lock files, and `audit` like source-built packages. Their `build_id` excludes flavor and toolchain (§7.2), and their payload dylibs get the same ABI scan at pack time — dependents link against vendor libraries through the same contract as farm-built ones. The scan is per-architecture: universal payloads record separate `x86_64` and `i386` ABI entries, and the x86_64 entry is what aslice-built dependents (always 64-bit) consume.

### 12.5 Logging and diagnostics

A package manager that fails opaquely trains users to fear it. aslice logs **everything it does, to the local machine, and nowhere else** — the charter (N7) applies to logs as it does to metrics: nothing is ever transmitted, aggregated, or phoned home, not even opt-in.

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
- **Supportability.** `aslice log` filters by operation, package, level, or time range; `aslice doctor` ends with the paths of the relevant log files. When a user files an issue, `aslice log --last-op` produces the excerpt a maintainer needs — locally generated, user-attached, never auto-submitted.

**Silence discipline.** Steady-state success is quiet: a successful binary install prints its plan summary and result, and everything else lives in the log at info level. aslice never logs at warn for things that are fine (a lesson from tools whose warning noise trains users to ignore real ones).

### 12.6 Doctor: sanity checking

`aslice doctor` is the single entry point for "is my installation healthy?" — it runs a fixed battery of checks, reports each as pass/warn/fail with the actionable-message standard of §12.5, and never changes anything itself (repairs are explicit commands it *recommends*). It is read-only, offline-capable, and fast (< 1 s for the standard battery; deep checks are opt-in).

**Check groups:**

| Group | Checks | Verdicts |
|---|---|---|
| **Machine** | CPU flavor vs. configured flavor (a v3 config on v2 hardware is a fail, not a surprise SIGILL later); macOS release vs. supported window; APFS vs. HFS+ (capabilities that degrade, announced); free disk vs. GC watermark | pass / warn / fail |
| **Prefix and store** | Prefix ownership and permissions (user-owned, not world-writable); store path integrity — manifests re-hashed against on-disk content (`--deep` re-hashes every file, default checks a sample plus anything the DB flags); dangling store paths referenced by no generation | pass / fail |
| **Profiles and generations** | `default` symlink resolves; every profile symlink lands inside the store; the live generation matches the DB's installed set; collision priorities resolve to real paths | pass / fail |
| **Database** | SQLite integrity check; schema version vs. binary (a newer DB than the binary is a fail with downgrade instructions, never silent corruption); WAL recovery state | pass / fail |
| **Repositories** | Per repo: reachable (or cached-snapshot age if `--offline`), TUF metadata expiry countdown, pinned key still matches live root, trust-level consistency (a `verified` repo whose countersignature lapsed is a fail with the freeze explanation — REPOSITORIES §3), shadowed core names, current overlaps and their resolution state, index staleness beyond policy | pass / warn / fail |
| **Coexistence** | Homebrew/MacPorts presence, PATH ordering advice, anything in `/usr/local` shadowing aslice binaries (or vice versa) — advisory only, aslice never touches either | pass / warn |
| **Environment** | `ASLICE_*` variables that override config (listed, not hidden); shell init files referencing stale prefixes; Xcode CLT presence (informational — the self-hosted toolchain makes it optional for aslice itself) | info / warn |
| **Trust store** | `ca-certificates` bundle freshness against the index (a stale trust store is this platform's day-one failure); profile env wiring (`SSL_CERT_FILE`/`CURL_CA_BUNDLE`/`GIT_SSL_CAINFO`) points at the aslice bundle; System-keychain imported set matches the DB record — drift after OS updates or third-party cleanup reported, never silently repaired (§12.10) | pass / warn |
| **System patches** | Every declared `[system-patch]` target still symlinks into the live generation; backup files present and hash-matching the DB record; drift after macOS updates (a patch Apple restored, or a newer Apple file our symlink now shadows) reported with reapply/restore remedies, never silently re-patched (§12.11) | pass / warn / fail |

**Rules:**

- **Every fail and warn names the remedy.** Not "store integrity error" but "store path `x264-0.164-0+core.v3.77aa10b2` fails manifest hash (1 file) — quarantine with `aslice store verify --quarantine x264` and reinstall." The check table is code, not prose: each check has an ID (`doctor.store.hash`), so messages, `--json` output, and docs all reference the same stable identifier.
- **Exit codes are scriptable:** 0 all-pass, 1 warnings only, 2 any fail. `--json` emits the full battery result; CI and fleet tooling gate on it (`aslice doctor --json | jq '.checks[] | select(.verdict=="fail")'`).
- **Warnings are real action items.** Each warn carries a command; anything informational goes to the `info` tier, which `--brief` suppresses. A doctor that cries wolf gets ignored — the battery is curated so that a clean machine prints one line: `aslice: your installation is healthy (N checks, M repos, G generations)`.
- **It ends with pointers.** The summary footer lists the log directory and the last operation ID (§12.5), so a failing machine goes from `doctor` to root cause in two commands.
- **`--fix` exists but is narrow.** The only automatic repairs offered are ones with no possible data loss: pruning dangling cache entries, re-linking a broken generation symlink to its recorded target, refreshing stale index snapshots. Everything else prints the exact command for the user to run. `--fix` announces each action before taking it and logs all of them.

---

### 12.7 System software: kexts and SIP-disabled development tools

Some software this platform needs cannot live entirely inside the store: kernel extensions (audio-interface drivers, filesystems, hypervisors) and development tools that require SIP disabled (low-level debuggers, DTrace-based profilers, kernel instrumentation — a real population on 10.11–12 development machines). Earlier drafts rejected this category outright; v1.2 replaces the rejection with a declared path, because the software exists and users install it today by hand — with no provenance, no warnings, and no rollback. A package manager that refuses to see that protects no one.

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
- **Kext reality is respected.** On SIP-enabled 10.11+, loaded kexts must be signed — the formula declares whether its kexts are signed (signer-pinned per §12.4 when vendor-supplied) or whether it requires SIP off. aslice checks `csrutil status` rather than assuming: a `sip_off_required` package on a SIP-enabled machine stops *before download* with exact instructions (boot to Recovery, `csrutil disable`, re-run the command); a signed-kext package on a SIP-enabled machine installs with no SIP conversation at all. OS updates can re-enable SIP or invalidate kexts — `doctor` (§12.6) reports SIP state, declared-vs-loaded kexts, and that drift.

**Warnings at every decision point.** Declared system requirements surface at every decision point:

- **Solve and plan:** installing a system package prints a prominent block *before any download*: the kexts it installs, the SIP requirement, the `reason` text, and the consequences — kexts run in kernel space (a bug panics the machine), and SIP-disabled operation weakens every protection in §10 for all software on the machine.
- **Non-interactive refusal:** scripts, `--json` plans, and `aslice apply` **refuse** system packages unless `--accept-system-changes` is passed for that operation. There is deliberately no persistent "always accept system changes" setting — consent is per-decision, like the risk.
- **Elevation:** the consent prompt for `aslice-system` repeats the declaration; every elevation is logged as an unsuppressible security event (§12.5).
- **Doctor:** SIP state, kext drift after OS updates, and unsigned-kext installs are all `doctor` checks with remedy text and stable check IDs (`doctor.system.sip`, `doctor.system.kexts`).

**Trust gating.** Serving system packages requires the **`system` capability**, granted by trust level (REPOSITORIES.md §3): **official and verified repositories have it; third-party repositories never do; `local` repositories have it** (a developer's own `file://` tree on their own machine — the same authority as installing the kext by hand, now with warnings and rollback). Talking a user into installing a kernel extension is the social-engineering attack the trust levels exist to block, so no remote stranger's repository can offer one. Tier policy — extended by default, core only when the platform genuinely requires it — lives in ORCHARD-POLICY §13.

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

aslice *generates* the launchd plist from this declaration at enable time — the formula ships no plist file and no code. Two consequences fall out of the store model. `ProgramArguments` resolves through the **profile** (`/opt/aslice/profiles/default/bin/nginx`), never a store path, so the job survives upgrades and rollbacks untouched: the same plist launches whichever version the live generation points at. And the label is namespaced (`org.aslice.nginx`), so `aslice service` maps one-to-one onto real launchd jobs — no pidfiles, no guessing, no wrapper daemons.

**The command.** `aslice service` is a thin layer over `launchctl`'s modern interface (`bootstrap` / `bootout` / `kickstart` / `print`, present since 10.10, so the whole 10.11–12 window is covered):

- `aslice service list` / `status <pkg>` — reads `launchctl print gui/<uid>/org.aslice.<pkg>`: pid, state, last exit status, keepalive. Status is launchd's truth, not a pidfile.
- `aslice service start` / `stop` / `restart <pkg>` — `bootstrap` / `bootout` / `kickstart -k` against the generated plist.
- `aslice service run <pkg>` — foreground, unregistered, for debugging (the one `brew services` idea worth copying).
- Per-service environment overrides live in `$XDG_CONFIG_HOME/aslice/services/<pkg>.env` and are applied when aslice generates the plist — never by editing it afterwards (the store is immutable, §8.1, so overrides *must* live outside it, which is where they belong). This closes HOMEBREW-REVIEW §4.4's P1.

**Upgrades stop the service first.** The mutation pipeline of §8.3 becomes service-aware whenever a plan touches a package with a loaded job:

1. Resolve, fetch, and build the **entire new generation** while the old one — and the service — keeps running. Any failure here never touched the service.
2. `bootout` the affected jobs — and only the affected ones; an ffmpeg upgrade never bounces your postgres.
3. Swap the generation symlink (atomic, §8.3).
4. Reconcile plists — only if the declaration changed; the profile indirection means a plain version bump needs no plist edit.
5. `bootstrap` / `kickstart -k` the jobs and verify they came up (pid present, no immediate crash-exit). A job that won't start is an error carrying launchd's last exit status and the log path — and then aslice **asks the user about rolling back** (below).

**A failed health check asks; it never decides silently.** The failure is shown first — the job's launchd exit status and the log path — then, on an interactive terminal:

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

### 12.9 Multi-version runtimes: use, pin, default — and version-bound extensions

php, nodejs, ruby, and python are not packages in the ordinary sense: users keep several versions installed at once, switch between them constantly, and stack version managers (nvm, pyenv, rbenv, Volta) on top of their package manager to cope — two sources of truth for what `python3` means, fighting over the same PATH. Homebrew's answer (separate `php@8.1` / `php@8.2` formulae plus `brew link --overwrite` juggling) makes the manager itself the obstacle. aslice takes the Volta lesson seriously: **version management is the package manager's job**, and the store model of §8 makes it nearly free — multiple versions coexist by construction; what was missing is a *selection* layer.

**One formula, release streams.** A runtime is a single formula (`php`) whose orchard publishes several maintained streams (8.3, 8.4, 8.5) in the index simultaneously. `aslice install php@8.4` is an ordinary version-constrained install; the store happily holds 8.3.11, 8.4.13, and 8.5.0 side by side. What installing a stream does *not* do is change which `php` you get — selection is always explicit, never a side effect of installing. (Homebrew conflates the two via `link`; Volta's `volta install` conflates them too. aslice separates install from select because `aslice upgrade` must never move you to a new PHP minor under your feet.)

**The shim layer.** PATH gains one directory ahead of the profile: `/opt/aslice/shims` (the installer sets the order; `doctor.coexistence` verifies it). A shim is a hardlink to the aslice binary dispatched on `argv[0]` — zero per-tool code — created for every name a runtime formula declares in `shims = [...]` (php, phpize, pecl, php-fpm; node, npm, npx; ruby, gem, bundle; python3, pip3, …). Invoked as `php`, the shim resolves a stream (below), looks the store path up in the state DB, and `exec`s the real binary — no fork, no wrapper process, signals and `ps` intact, cold-path cost under a millisecond (§11). Shimmed names are *not* linked into generations; the profile links **versioned aliases** instead (`bin/php8.4`), which services and scripts use when they must name an exact runtime — §12.8's generated plists bind the alias of the stream selected at enable time, so `aslice default php 8.5` never silently changes what a running php-fpm executes, and moving a service between streams is an explicit disable/enable. Resolution, first match wins:

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

**`aslice default` — the fallback.** `aslice default php 8.4` records the profile-wide selection in the state DB; `aslice default php` shows it; bare `aslice default` lists all selections. The default is what cron jobs, services, and shells outside any project tree land on. Installing a second stream never changes it; uninstalling the selected stream refuses until another is selected (`--force` overrides, logged). `aslice versions php` shows the matrix: installed streams, the pinned/default/session selections, and which extensions are installed per stream.

**Extensions bind to exactly one runtime version.** This is where version managers historically give up — pecl compiles against whichever `phpize` ran first, pip installs into whichever site-packages happens to be writable, and the result only *looks* shared until an ABI breaks. aslice splits the problem by who does the installing:

- **aslice-managed extensions are slices, keyed to the runtime's ABI epoch.** Compiled extensions — `php-redis`, `php-imagick`, `ruby-pg` — are orchard packages declaring `[extension] runtime = "php"` (PACKAGE-FORMAT §3.13). The runtime formula declares its own **ABI epoch** (`"8.4"` for php, `"3.12"` for python, `"3.3"` for ruby, `"22"` for nodejs — the granularity at which the extension ABI breaks: minor for php/python/ruby, major for node), and the epoch enters the extension's build identity: `php-redis-6.1.0+php8.4.v3` and `…+php8.3.v3` are different store paths that coexist like flavors. Installing an extension binds to the *currently selected* stream (same resolution as the shims; `--runtime php@8.3` overrides): the solver requires that stream installed, the build compiles against that concrete runtime store path, and linking writes a small loader file into the profile's per-epoch scan directory (`etc/php/8.4/conf.d/20-redis.ini`) — so extension sets are generation-managed and `aslice rollback` restores runtime and extension set together. The farm prebuilds the extension × supported-epoch × flavor matrix, so binaries exist for every supported stream. A patch upgrade within a stream (8.4.12 → 8.4.13) keeps the epoch and extensions carry over untouched; installing a *new* stream (`aslice install php@8.5`) offers to provision the previous stream's extension set for it (interactively; `--with-extensions-from 8.4` for scripts) — a new epoch is a conscious port, never an accident.
- **Ecosystem-native installs bind through the shim, per version, outside the store.** `pip install`, `gem install`, `npm i -g`, `pecl install`, `composer global require` keep working — but the shim execs the tool with the per-version **userbase** environment of the *resolved* stream (`~/.aslice/runtimes/php/8.4/`, `…/python/3.12/`, …, mapped through `PYTHONUSERBASE`, `GEM_HOME`/`GEM_PATH`, `NPM_CONFIG_PREFIX`, PHP's user-ini/extension-dir conventions — declared by each runtime formula in PACKAGE-FORMAT §3.13, never hardcoded). The store stays immutable; each stream gets its own writable territory; a `pip install` under python 3.12 is invisible to 3.13 — the binding falls out of the directory layout. Userbase contents are user territory: aslice never audits, snapshots, or garbage-collects them, `doctor.runtimes` reports their presence and size, and uninstalling a stream warns about its orphaned userbase instead of deleting it.

**Tools ride the runtime.** The third category is interpreter-target tools with no native code against the runtime ABI: composer (a phar), yarn, prettier, poetry. These are ordinary slices that declare `[ride] runtime = "php"`: the slice installs once, its shim resolves the runtime through the normal session → project → default order at exec time, and the tool launches under that runtime — composer's PHP is always your selected PHP, switching automatically when you switch. This is Volta's best idea (a global yarn that follows your node) generalized to every ecosystem, with one deliberate difference: riding is a property of the tool's *formula*, never user configuration, because whether a tool can safely ride is a fact about its code, not a preference.

**Upgrades stay in their lane.** `aslice upgrade php` moves within the selected stream only — 8.4 patches, never 8.5; its output mentions newly available streams (`php 8.5 is available: aslice install php@8.5`) without touching them. That is the contract that makes `aslice upgrade` safe on a production Mac mini: the runtime your sites, services, and crontabs resolve to changes only when you say `use`, `pin`, or `default`. GC is conservative in the same direction: a stream that is selected as default, pinned by a project `aslice.toml` the DB knows about, or referenced by an enabled service is never collected.

**Doctor.** `doctor.runtimes` checks: the shim directory is present and *precedes* the profile on PATH (with the exact fix line); every declared shim resolves (no dangling selections — e.g. a default pointing at an uninstalled stream); every enabled service's versioned alias resolves to an installed stream; extension scan directories match the DB (a loader for an epoch whose runtime is gone); orphaned userbases reported, never removed. All read-only, same remedy-text standard as §12.6.

---

### 12.10 Trust store: modern CA certificates on a frozen platform

The most common day-one failure on 10.11–10.13 is TLS itself, not a missing library. The system trust store froze years ago: roots expired (the DST Root CA X3 expiry in 2021 broke Let's Encrypt chains for everything using the system store), modern roots never arrived (ISRG Root X1/X2 and their successors), and every release in the support window ages further. aslice's own fetches never cared (§4.1 — `aslice-fetch` carries its own TLS stack and bundle), but the user's tools do: the curl, git, wget, and python aslice installs will consult a trust store, and so will Safari, Mail, and every other SecureTransport app on the machine. `aslice ca-update` fixes both halves.

**The bundle is an ordinary signed slice.** `ca-certificates` is a data-only package in the core orchard, versioned by upstream release, kept fresh by the same livecheck/autobump machinery as every other package (REVIEW §4.2). Updating trust therefore rides the existing TUF + minisign + generation pipeline — verification before extraction, rollback like any other package, no new trust path, nothing fetched outside the signed index. Linking places the bundle at the profile's `etc/ssl/cert.pem`, and the shell integration exports it to userland: `SSL_CERT_FILE`, `CURL_CA_BUNDLE`, `GIT_SSL_CAINFO` (set by `aslice shellenv` / `aslice init`, visible in `doctor`'s environment group like every other override). aslice's own curl and git are built against aslice's OpenSSL, so command-line TLS heals *completely* — modern roots, modern ciphers, TLS 1.3 — independent of the OS.

**The source is configurable; the default is Mozilla.** The shipped bundle is the Mozilla root program's store as converted to PEM by the curl project (curl's caextract) — the same trust decisions Homebrew, Debian, and Fedora ship, chosen because Mozilla's root program is the most actively curated public trust list and curl's conversion is the most widely audited consumer of it. Alternatives are a config decision (`aslice config set ca.source <name>`), not a fork: an enterprise or community orchard can publish its own `ca-certificates` variant (a corporate inspection root added to the Mozilla base is the canonical case — it ships from that orchard, under that orchard's trust level, and the overlap-resolution machinery of REPOSITORIES §10 applies), and `aslice ca-update --from-file ./corp-bundle.pem` installs a local bundle whose sha256 is recorded in the DB (`--from-file` never fetches). Whatever the source, the bundle is validated before activation — parses completely, non-empty, no certificate already expired — and a bundle that fails validation is refused, never linked.

**The crypto stack is a flag.** `aslice ca-update --crypto` upgrades the crypto-provider slices — `openssl` and anything else the installed set declares as a TLS provider — to the newest version the index offers, through the ordinary upgrade machinery (generations, rollback, health checks). This is the other half of the day-one failure: modern roots are useless to a tool whose TLS stack predates TLS 1.2, and aslice's curl, git, wget, and python — built against aslice's OpenSSL — come out of a `--crypto` run with modern ciphers and TLS 1.3. The limitation is printed on every run: `--crypto` cannot touch the OS's own stack — SecureTransport and the system libcrypto are Apple's, and on 10.11–10.12 they stay frozen. The replaceable parts of the OS's TLS surface (the `/usr/bin/openssl` CLI and its kin) are a `[system-patch]` decision (§12.11): when such a package is installed, the flag re-converges it through the ordinary generation mechanics; when none is, `--crypto`'s output notes that one exists in the core orchard — offered, never installed by the flag itself.

**The System keychain is opt-in.** The private bundle heals aslice's own userland; it does nothing for Safari, Mail, Calendar, or any other app using SecureTransport — those trust the machine's System keychain, on every release in the window, for every user. `aslice ca-update --keychain` closes that gap, under rules strict enough for the privilege it uses:

- **Executed by `aslice-system`** (§10.4), the same declarative privileged helper that manages kexts — this is aslice operating on the machine, not package code running as root; the zero-install-code rule (§10.1) is untouched. The operation is additive and explicit: for each root in the bundle *not already present* in `/Library/Keychains/System.keychain` (fingerprint comparison), `security add-trusted-cert -d -r trustRoot` — admin authorization, every run, per-decision consent as in §12.7; there is no "always allow" setting. SIP is not involved: the System keychain lives in `/Library`, not `/System`.
- **Recorded to the certificate, reversible to the certificate.** Every import is written to the DB (fingerprint, label, bundle version, date); `aslice ca-update --keychain-remove` deletes exactly the recorded set and nothing else. aslice never removes, disables, or overrides an Apple-shipped or user-added root — expired roots already in the keychain are *reported* by `doctor`, never touched; distrust decisions belong to the bundle's source program for new installs and to the machine's owner for existing ones.
- **The limits are printed.** The import fixes *trust*, not *crypto*: SecureTransport on 10.11–10.12 still lacks TLS 1.3 and modern cipher suites, so sites that require them stay unreachable in Safari no matter what the keychain holds. `ca-update --keychain` says so in its output, and `doctor` reports the same — the user who still can't reach a TLS-1.3-only site gets the true explanation (use aslice's curl, or a browser with its own stack) instead of a debugging rabbit hole.

**Apple's own roots ride the same rails.** Mozilla's program does not carry Apple's roots — but Software Update, the App Store, iCloud, activation, Apple Pay, and Developer ID/Gatekeeper validation all chain to Apple's own PKI, and those roots and intermediates age on a frozen release like the public ones (a lapsed WWDR intermediate breaks Developer ID launches as surely as DST Root CA X3 broke the web). Apple publishes its current roots on its official PKI pages; the core orchard ships them as a second pinned, data-only slice — `apple-roots`, fetched from Apple's certificate-authority pages by the farm, hash-pinned, livecheck-watched, signed and indexed exactly like `ca-certificates`. `aslice ca-update --apple-certs` imports the missing Apple roots and replacement intermediates into the System keychain through the identical machinery as `--keychain` — same `aslice-system` execution, same per-run admin consent, same fingerprint-additive discipline, same recorded-to-the-certificate DB entries, removed by the same `--keychain-remove`. Apple-shipped certificates already on the machine are still never removed or overridden: a superseded Apple intermediate is *reported* by `doctor`, and its replacement imported alongside.

**Doctor and lifecycle.** `doctor.truststore.*` checks: bundle freshness against the index (staleness past policy is a warn with the one-line remedy), profile env wiring points at the aslice bundle, the crypto-provider slices and the `apple-roots` slice are current against the index, and the keychain's imported set — Mozilla-program and Apple roots alike — matches the DB record (OS updates and third-party "cleaner" tools both cause drift — reported, never silently repaired). A bundle upgrade is an ordinary generation transaction: rollback restores the previous bundle, and `--keychain` operations are idempotent against the DB record, so re-running after a rollback re-converges the keychain to the active bundle's additions.

---

### 12.11 System patches: flagged, reversible replacement of Apple-provided files

§12.10's crypto flag runs into a wall the founding charter built: some fixes *require* replacing what Apple shipped. The `/usr/bin/openssl` on 10.11 is a 0.9.8-era tool that cannot speak modern TLS no matter what the keychain holds, and the frozen platform is full of such fossils — dead CLIs, broken system tools, stale support files. Earlier drafts drew the line absolutely: aslice never touches `/usr`, `/System`, or Apple's binaries (§2.2 N5, §13.1). v1.7 keeps the default and removes the absolutism: **modifying the OS is allowed, but only through one declared, flagged, reversible mechanism** — and a package that wants it must say so in its manifest, under the strictest trust gate in the system.

**Declaration.** A package opts in with `[system-patch]`:

```toml
[system-patch]
targets          = ["/usr/bin/openssl", "/usr/bin/curl"]   # absolute paths this package replaces
sip_off_required = true          # /usr, /System, /bin, /sbin are SIP-protected on 10.11+
reason           = "Replaces the OS's frozen 0.9.8-era TLS CLIs with aslice's modern builds"   # mandatory; shown verbatim in every warning
```

`reason` is mandatory and displayed verbatim at every decision point, exactly as in §12.7 (schema: PACKAGE-FORMAT v0.6).

**The mechanism is backup, symlink, record — never overwrite.** All steps are executed by `aslice-system` (§10.4) with the same per-operation consent and unsuppressible logging as kexts and root daemons:

1. **Preflight.** The target must exist, must not already be aslice-managed (a second package patching the same path is a conflict, not a stack), and must not be on the **refused-by-construction list**: the kernel, `dyld`, `libSystem`, anything under `/System`, and *any dylib or framework in a platform binary's load path* — replacing those would either brick the machine or crash Apple's own binaries against library validation, so the linter rejects such targets and no flag overrides it. The category patches **tools, configs, and data** — never the shared library space. SIP is checked, not assumed: a SIP-protected target on a SIP-enabled machine stops before download with the exact Recovery instructions, per §12.7.
2. **Back up the original.** The original file is copied to a managed backup directory under the prefix and its sha256 recorded in the DB. The backup is the rollback: it is never overwritten by a later patch of the same path and never pruned while the patch is installed.
3. **Replace with a symlink — through the profile.** The target is atomically swapped (`rename(2)`) for a symlink into the profile (e.g. `/usr/bin/openssl` → `/opt/aslice/profiles/default/bin/openssl`) — never a raw store path. This is the same trick as §12.8's plists: a generation swap changes what the system path resolves to, so **rollback of a generation is rollback of the patch**, automatically, with zero extra machinery. Uninstalling or unlinking the patched package while the symlink is live is refused until the patch is restored; a store path referenced by an active patch is never garbage-collected.
4. **Record everything.** The DB stores: package, target path, original sha256 and size, backup location, symlink target, and the generation that installed it. `aslice system-patch list` / `status` shows the current patched set — which Apple files are replaced, by which package, since when.

**Restore is exact.** Restoring a patch (uninstall, `aslice system-patch restore <path>`, or a generation rollback that predates it) removes the symlink, copies the backup back, and verifies the restored file's sha256 against the DB record — the machine gets back the byte it had. A missing or corrupt backup is a `doctor` failure, never a silent skip.

**OS updates are drift, and drift is reported.** A macOS update may restore the Apple original over our symlink (the patch vanishes) or replace the underlying file with a *newer* Apple version (our symlink now shadows it). `doctor.systempatch.*` detects both: the vanished patch is reported with a one-line reapply remedy; the shadowed-newer-Apple-file is reported with both options — reapply (the new Apple file becomes the new backup) or restore and retire the patch. aslice never silently re-patches: Apple's file changing is the moment a human should decide.

**Consent and trust are the strictest in the system.** The pre-download block lists every target path, the `reason` text, the SIP requirement, and the consequence in plain terms: *this replaces an Apple-provided file; every user and every program on the machine will see the replacement until it is restored.* Non-interactive runs refuse without `--accept-system-changes` (the same flag as §12.7 — one consent vocabulary); the `aslice-system` elevation prompt repeats the target list; there is no "always allow." Serving `[system-patch]` packages requires the **`system-patch` capability**, granted by trust level (REPOSITORIES.md §3): **official and `local` repositories have it; third-party never.** A `verified` community repository may receive it only through an explicit per-repo grant — `aslice repo allow-system-patch <name>`, refused by default, recorded in the state DB, revocable with `aslice repo deny-system-patch <name>` — because the countersignature vets a repository to *distribute software*, and rewriting the OS warrants one deliberate decision from the machine's owner beyond that vetting (open question #10, resolved v1.8). The grant gates *serving*; the per-decision consent flow above is unchanged and applies whoever serves the package.

**Why this category exists.** This category exists because the alternative is users doing the same thing by hand — `curl | sudo sh`, a downloaded "TLS fixer," a copied dylib — with no provenance, no backup, and no way back (the §12.7 argument, applied to files). aslice's guarantee is narrower than for ordinary packages and says so (§10.7): the replacement bits are exactly the declared, verified ones; the original is preserved and restorable to the byte; refused paths are refused by construction; and the user was warned at every decision point.

### 12.12 Self-update: aslice is package zero

A package manager that cannot safely update itself either rots or trains users to re-run a curl-pipe script — the exact pattern this security model exists to kill. aslice updates itself through the same machinery as everything else, with one wrinkle handled explicitly.

- **aslice is a package.** The manager lives in its own store path (`/opt/aslice/store/aslice-x.y.z-…/`) with a formula in the core orchard, a manifest, an SBOM, and a minisign signature. `aslice self-update` is an ordinary transaction — resolve, fetch slice, verify, build generation, atomic swap — whose only special property is that the running binary is the thing being swapped.
- **The swap waits for the transaction to finish.** The profile symlink to `bin/aslice` flips with the generation as usual; the *running* process completes its bookkeeping, then re-execs the new binary to print the result. The old binary never vanishes mid-execution: the store path is immutable, and the previous generation remains invocable through ordinary rollback.
- **Health check with automatic rollback.** Post-swap, the new binary runs a smoke self-test (version report, DB open, index read). Failure rolls the generation back automatically and reports it — the one package whose bug could brick the installation gets the strongest rollback guarantee, not the weakest. A failed self-update leaves the previous, working aslice exactly where it was.
- **Channels and pins apply.** `self-update` honors the configured channel and refuses to cross a spec/format major version without printing the changelog and requiring confirmation. `aslice pin aslice` holds the manager itself — same hold machinery as any package.
- **Bootstrap trust is notarization plus signature** (§10.3): release binaries are minisign-signed with the project key *and* Apple-notarized, so first run on Gatekeeper releases has no "unidentified developer" friction; the install script verifies the minisign signature itself, keeping notarization as defense-in-depth and UX rather than the root of trust.

---

### 12.13 Declarative system setup: `setup.toml`, `apply`, `export`

A Mac back from system recovery is blank, and the path from *blank* to *ready to work* is an afternoon of remembering: which packages, which Dock settings, which shell, which services, which runtime streams. Nix has the system configuration; Homebrew has the Brewfile. aslice's answer is one declarative file — `setup.toml` — and one verb: after the installer, `aslice apply setup.toml` (or an `https://` URL) takes a blank machine to a working one, and because the file is plain TOML data it doubles as the shareable common language for "this is how my machine is set up". The inverse, `aslice export`, captures an existing machine back into the file. Full schema and semantics: [SETUP.md](SETUP.md); what follows is the architecture.

**The file is a wishlist with preferences, not a lock.** `packages = ["ffmpeg@7", "postgresql +ssl"]` carries the same constraints `install` accepts; `[runtimes.default]` carries §12.9's stream selections; `[services]` carries the enable set; `[defaults.user."<domain>"]` / `[defaults.system."<domain>"]` carry macOS preference keys; `[shell]` carries the login shell; `[aslice]` and `[[repos]]` carry configuration and extra repositories. Like a Brewfile it is the human layer above exact state — the difference from a lock is the `package.json`/`package-lock.json` difference (PACKAGE-FORMAT §7). Unlike a Brewfile it is **data, never code**: no evaluation, no hooks, nothing executable — applying a stranger's file has a bounded, inspectable blast radius, and the plan shows every write before any happens (§12.2's plan/apply split, now pointed at whole machines).

**One verb, three documents.** `apply` already replays locks and executes saved plans; setup is the same operation at a third fidelity — *make reality match this document* — so it is the same verb, with the document kind detected by content (JSON plan, `lock_version`, `schema`). A setup document is *planned* first: wishlist resolved against the current snapshot, preferences diffed, the full plan rendered and confirmed before execution. Ordering puts privileged work last (repositories → config → packages → selections → services → user defaults → system defaults + shell), so a plan refused at a consent gate still lands everything unprivileged and reports the remainder as skipped-refused.

**Convergence, with discipline.** Apply is idempotent — a second run is a no-op — and additive by default: it asserts, never removes what the file doesn't mention. `--prune` opts into retraction, bounded two ways: it touches only records the file itself applied, and it never removes repositories (trust decisions stay sticky, REPOSITORIES §10). Before every preference write, shell change, or `/etc/shells` enrollment, the pre-change value is recorded against the new generation — §12.11's backup discipline generalized — so `aslice rollback` restores preferences and login shell together with the profile, and `aslice history` attributes every applied change to its file hash and generation.

**Two new consent-gated writes.** System-domain preferences (`/Library/Preferences`) and enrolling a non-Apple login shell in `/etc/shells` are OS-territory writes, otherwise barred by N5 (§2.2). They join `[system-patch]`'s model exactly: declared in the file, executed by `aslice-system` (§10.4), interactively prompted with their targets named, refused non-interactively (exit 2) unless `--accept-system-changes` is passed — one flag, one contract across §12.7, §12.11, and here. Shell changes resolve through the profile path, never a raw store path, so generation rollback moves the login shell back automatically.

**Export captures what is knowable.** Packages, selections, services, shell, repositories, and non-default config are aslice's own state — exported completely, deterministically sorted for diffing. Preferences are not knowable: there is no baseline to diff a preferences folder against, and application domains can hold account tokens and machine-specific values, so `export` captures them only for domains named with `--defaults` / `--system-defaults`, emits deferred value types (dict, data, date) as comments, and stamps the output with a review-before-sharing warning. Locally-built packages and foreign (non-aslice) shells are commented out with notes rather than exported as if reproducible. `aslice import --from-brewfile` covers the migration path the review asked for (HOMEBREW-REVIEW §4.6): mechanical translation with a printed skip list for `cask`/`mas`/`vscode`.

**Limits.** Not a dotfiles manager (chezmoi/Stow/git own `~/`); not a system imager (FileVault, SIP, accounts, panes without domains are untouched); not fleet configuration management (no agent, no drift loop — `launchd` running `aslice apply` is the entire enforcement story); not exact reproduction (that is the lock's job). Keychain items are never read or written.

---

## 13. Policies, Governance, and Migration

### 13.1 Package acceptance policy

- Core orchard: maintained, security-patched, reproducible-build targets; no package enters without a working `tests.star` smoke test on at least one OS × one flavor.
- Upstream-EOL software: allowed in extended with `eol = true` metadata; excluded from core.
- Vendor binary packages: accepted into extended with accurate OS-support tags and a pinned signer when the artifact is signed — unsigned artifacts are extended-only, `signer` omitted, announced at every install (§12.2, §12.4); into core only if signed, redistributable (so the farm hosts the slice), and payload-only by construction. A vendor package whose scripts turn out to be required is removed, not accommodated.
- **Runtime dependencies resolve to aslice packages only** — the codified rejection of Homebrew's `uses_from_macos`. Never `/usr/lib` dylibs, never `/usr/bin` tools: on 10.11 the system libraries *are the problem*. The only exceptions are always-present system **frameworks** (`Accelerate`, `SystemConfiguration`, `CoreAudio`, `CoreFoundation`, …) enumerated in a lint allowlist — frameworks are the platform's ABI, not its bundled software. Allowlist additions are policy PRs against ORCHARD-POLICY §6 and the lint table together.
- **Patching system files is rejected by default — and flagged where it isn't.** aslice installs alongside macOS and never modifies `/System`, `/usr`, or Apple's binaries silently, incidentally, or as a side effect of anything else. Where fixing the frozen platform genuinely requires replacing an Apple-provided file, the declared `[system-patch]` category (§12.11) does it openly: original backed up, replacement via profile symlink, rollback to the byte, consent at every decision point, served by official and local repositories — and by verified ones only under an explicit per-repo `allow-system-patch` grant (§12.11) — with catastrophic and platform-binary-library paths refused by construction. The marketing feature survives, stated precisely: aslice never patches your system *behind your back*. Kernel extensions and SIP-disabled development software likewise remain the declared, warned, trust-gated category of §12.7.

### 13.2 Variant discipline

`abi = true` variants are capped per package (guideline: ≤ 6) and each must justify its existence in review. This keeps the solver space small, the prebuilt matrix tractable, and avoids repeating the option-sprawl that made Homebrew variants unmaintainable. `abi = false` (build-flavor) variants are unconstrained — they cost the project nothing because they never spawn binary flavors.

### 13.3 Coexistence and migration from Homebrew

- **Coexistence:** aslice lives in `/opt/aslice`, never touches `/usr/local`, and `doctor` detects a Homebrew installation and advises on PATH ordering rather than conflicting.
- **`aslice adopt --from-homebrew`:** reads Homebrew's Cellar and `brew leaves`, maps names to aslice formulae (with a maintained alias table for renames), produces an install plan that recreates the same leaf set — including mapping old `--with-*` Homebrew options to aslice variants where an alias exists. Cask leaves map to vendor-binary packages where one exists, flagged for review when the vendor artifact's OS tags don't cover the machine. It does not attempt binary reuse of Homebrew's Cellar (different prefix assumptions); it reuses the *intent*.
- **Formula importer (for orchard authors):** a tool that mechanically translates simple Homebrew Ruby formulae — `url`/`sha256`/`depends_on`/standard `configure && make` bodies — into TOML+Starlark drafts, with a human review step. Realistic coverage target: the simple ~60–70% of formulae; the rest are ports, not translations. A companion importer turns simple Casks (`url`/`sha256`/`app`/`pkg`) into `type = "binary"` drafts — Casks are *more* mechanical than formulae, so coverage should be higher; the reviewer fills in signer pinning and OS tags.

### 13.4 Governance

- Benevolent-core-team start: 3–5 founding maintainers holding threshold keys; decisions by lazy consensus, escalations by vote.
- Orchard PR review backed by CI that *builds the package in the sandbox on every declared flavor* — review is about correctness and policy, never "does it compile." The merge gate is five checks, with no maintainer override (ORCHARD-POLICY §10): lint (schema + policy), a matrix build on every declared flavor at the formula's `min_os` with smoke-runs across `[min_os, 12]`, the `tests.star` smoke test, an **ABI gate** on provider version/revision changes (a regression requires a proper version bump or scheduled dependent rebuilds, published in the same index snapshot), and post-merge-only signing.
- **Project hygiene documents shipped in Phase 0** (September 2026) — `SECURITY.md` (how to report a vulnerability in aslice itself; key-contact runbook), `CONTRIBUTING.md` (the formula style guide: when a variant is justified, `min_os` accuracy, patch documentation — and the project's conduct expectations), and `docs/KEY-RUNBOOK.md` (the written key-ceremony/rotation runbook referenced by §10.2). There is deliberately **no `CODE_OF_CONDUCT.md`** — an owner decision: this is not a corporate project, people are expected to be nice to each other without a document legislating it, and telling someone they're acting like an idiot when they are is acceptable; CONTRIBUTING.md's Conduct section carries the expectation in the open. Documents, not code — cheap before launch, expensive after the first incident.
- Public roadmap, public build-farm dashboard, public transparency log. A legacy-platform project survives on trust, and trust survives on visibility.
- Funding: GitHub Sponsors/OpenCollective for build-farm hardware and power; costs are low and fixed (§9.3) precisely because the platform is frozen.

---

## 14. Roadmap

**Phase 0 — Foundations (months 0–3)**
`aslice-toolchain` first: modern Clang/libc++ targeting darwin15, bootstrapped on the newest Intel macOS against the oldest archived SDK, then self-rebuilt. Then the C++ core skeleton: CLI, SQLite state, TUF client, zstd, Mach-O/otool wrappers — plus the build harness in local mode (`aslice build` with the full sandboxed phase pipeline, job/result schemas; BUILD-INFRA.md §12), because the core orchard seed is built *with* it. Bootstrap binary runs on every release 10.11–12 (VM-tested per release, including HFS+). Core orchard seeded with ~30 packages (curl, git, openssl, python, zstd, cmake, ninja) built on real hardware. **Self-update ships in the first usable binary** (§12.12) — retrofitting update mechanisms is how projects die — alongside the project hygiene documents (§13.4). The from-nothing sequence for the whole project — toolchain genesis, TUF root ceremony, orchard seed, farm standup — is executed and written down as `docs/GENESIS.md`, so the platform can be stood up from nothing again and again.

**Phase 1 — Usable (months 3–6)**
Solver with variants; store/profiles/generations; GHCR distribution; the build harness in both modes — `aslice build` locally and `aslice farm` coordinator/agents on real hardware, one pipeline (BUILD-INFRA.md); minisign slices; ~300-package core orchard, all flavors; `adopt --from-homebrew`; **the freshness pipeline** — `[livecheck]` in every core formula, scheduled orchard autobump opening bump PRs, and `aslice livecheck`/`bump-pr` for humans (PACKAGE-FORMAT §3.15; ORCHARD-POLICY §9); build farm Phase A + first self-hosted nodes. Repository client (`repo add/list`, TOFU key pinning) from the start — the canonical repository *is* the default transport, so the multi-repo machinery costs little extra. The `ca-certificates` slice and the private-bundle half of `aslice ca-update` (§12.10) ship here — every userland TLS fetch depends on them. So do the `apple-roots` slice and `ca-update --crypto` (§12.10): both are ordinary signed content and ordinary upgrades.

**Phase 2 — Differentiated (months 6–12)**
ABI scanner with DWARF diffing; SBOM + `audit`; SLSA provenance; `aslice-toolchain` v2 (LLD-first linking, ccache integration); extended orchard to ~2,000 packages; popular-variant prebuilds chosen from community requests (§9.4); reproducible builds for core; vendor-binary packages (`type = "binary"`, payload extraction, signer pinning) and the Cask importer; `aslice repo build/publish` for third-party repositories; **runtime version management** — the shim layer, `use`/`pin`/`default`, riding tools, and version-bound extension slices with the farm's runtime-epoch build axis (§12.9); the opt-in System-keychain import halves of `aslice ca-update` (`--keychain`, `--apple-certs`, §12.10) and the `[system-patch]` category (§12.11), once `aslice-system` is proven in service and kext duty; **declarative system setup** — `setup.toml`, the unified `apply`, `export`, and `import --from-brewfile` (§12.13) — after the primitives it composes (services, runtime selections, repositories) are proven.

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
| Vendor binaries are opaque — no source SBOM, no reproducibility, the binary itself is trusted | Medium | Signer + hash pinning (silent substitution hard-fails); payload-only SBOM with full file list; `audit` binds CVEs via CPE; core tier barred unless redistributable + payload-only (§13.1); users told what is and isn't verified (§10.7) |
| Vendor pulls or mutates a `redistribute = false` artifact | Medium | Hash pin fails rather than installing a different binary; the formula records last-known-good; community can negotiate redistribution or archive a licensed copy |
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
10. ~~Whether `verified` repositories should ever serve `[system-patch]` packages~~ — **resolved (v1.8): yes, under an explicit per-repo grant.** `aslice repo allow-system-patch <name>` — refused by default, recorded in the state DB, revocable — is the ceremony that *is* security at this severity: the countersignature vets a repository to distribute software, and rewriting the OS warrants one deliberate decision from the machine's owner beyond that vetting. Third-party repositories: never (§12.11; REPOSITORIES.md §3).

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
| Multi-version runtimes | Separate `php@x.y` formulae + `brew link` juggling; nvm/pyenv/rbenv/Volta shadow the manager | `port select` — one global symlink, no sessions or projects | `nix develop` per-project shells — powerful, heavyweight | **Built in: release streams, shims with session/project/default selection, riding tools, ABI-bound extensions (§12.9)** |
| Modern CA trust store | Nothing — system roots rot; the keg-only `ca-certificates` formula helps CLI tools only | `curl-ca-bundle` port — CLI-only, wired by hand | N/A (uses system trust) | **`aslice ca-update`: signed, generation-managed bundle + opt-in System-keychain import, recorded and reversible to the certificate — plus `--crypto` (modern TLS stack for userland) and `--apple-certs` (Apple's own roots, pinned slice) (§12.10)** |
| System file modification | Cask `installer script:` / pkg scripts — arbitrary code, often as root, no backup, no rollback | Manual installs, untracked | Not the model | **Declared `[system-patch]`: original backed up, profile-symlink replacement, generation-integrated rollback to the byte, consent- and trust-gated (§12.11)** |
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
