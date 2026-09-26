# aslice Toolchain — One Compiler Bundle, Every Build

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

- **Status:** Design draft, v0.5 — September 2026
- **Companion to:** [DESIGN.md](DESIGN.md) v1.22 (§4 platform floor, §7.2 build identity), [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) v0.16 (§6 build environment), [BUILD-INFRA.md](BUILD-INFRA.md) v0.16 (farm consumption), [GENESIS.md](GENESIS.md) v0.7 (the from-nothing runbook). This document is the authoritative specification for the toolchain; where it and another document disagree, the disagreement is a bug in one of them.
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md).

## 1. What the toolchain is

aslice brings its own toolchain. A user never installs Xcode or the Command Line Tools (MANUAL §2.1); every build — on the farm or on a laptop — runs with `aslice-toolchain` and nothing else.

The bundle: modern Clang, LLD where viable (ld64 from cctools-port otherwise), a modern libc++, CMake, Ninja, and pkgconf, plus thin compiler wrappers that carry the build contract into every invocation (§6). It is self-hosted: it builds itself (§10), it is the authoritative toolchain for every package including aslice itself, and it is consumed as a pinned slice like any other input — content-addressed, signed, mounted read-only into builds (§8).

It is also just a package. `aslice-toolchain` lives in the core orchard, and `aslice install aslice-toolchain` gives you the compiler bundle for your own work (§9).

## 2. Why self-hosted

The supported platform requires a self-hosted toolchain (DESIGN §4.3):

- **Hosted toolchains cannot reach the floor.** Xcode 15-era toolchains refuse deployment targets below ~10.13, and hosted Intel runners never ship anything older. The platform floor is 10.11, so the toolchain that targets it cannot be Apple's current one.
- **The C++ runtime is the real constraint.** Clang's target floor is far older than libc++'s: `-mmacosx-version-min=10.11` is still accepted, but 10.11's system libc++ predates half of C++17. The toolchain therefore ships a modern libc++ and statically links it into everything it produces (§5).
- **Builds must not see ambient machine state.** A build job pins every input — toolchain, dependencies, sources, formula (BUILD-INFRA §2.1). A compiler borrowed from the host would be ambient state.
- **Reproducibility needs a fixed point.** Two builders bit-compare only if the compiler is byte-identical on both; a slice mounted at its canonical path is (§8).

The platform is frozen, which is what makes this affordable: the toolchain is built and archived once per bump (§11), not chased.

## 3. Components

| Component | Role | Notes |
|---|---|---|
| Clang | C/C++ compiler | Targets darwin15 through Monterey; accepts `-mmacosx-version-min=10.11` |
| libc++ | C++ runtime | Statically linked into every product (§5); the system libc++ is never used |
| LLD / ld64 | Linker | LLD where viable on this platform; ld64 from cctools-port otherwise. v2 moves LLD-first (§11) |
| CMake / Ninja / pkgconf | Build tooling | The harness's `ctx.cmake` / `ctx.make` / `ctx.meson` helpers wrap these with correct defaults (PACKAGE-FORMAT §6.3) |
| Compiler wrappers | Contract enforcement | What `CC`/`CXX` point at in a build; inject the flavor floor, the deployment target, and prefix-mapping (§6) |

The table identifies the components and their roles. Exact versions and the per-OS workaround register live in the toolchain slice's manifest (§4), which is the authoritative inventory.

## 4. The SDK strategy

One SDK serves everything: the oldest archived Apple SDK, paired with the deployment-target mechanism. `-mmacosx-version-min` is mature — a binary built against the oldest target runs correctly on every later release, provided it avoids or weak-links newer APIs (DESIGN §4.1). So a package builds once, against the oldest SDK, per flavor — not once per OS release.

The consequences are handled explicitly:

- **Workarounds are recorded, not remembered.** Where a component or a package needs a per-OS quirk — an availability guard, a missing-symbol shim — the workaround is written down in the toolchain's manifest (DESIGN §4.3), versioned with the toolchain.
- **Formulae declare their own floor.** A package that cannot cleanly target 10.11 declares `min_os` and moves on (PACKAGE-FORMAT §3.2); the toolchain does not contort itself to drag it down.
- **Claims require tests.** The farm targets every claimed release, 10.11 through 12, in batches of validated guests (BUILD-INFRA §8). Required coverage remains pending until host/hypervisor/guest compatibility and actual OS/flavor tests pass; the matrix is not yet evidence of completed validation.
- **The SDKs are never-lose.** The archived Apple installers and SDKs are genesis inventory — two independent locations, one of them offline (GENESIS §3). Apple pulls old SDKs; we don't notice.

## 5. Linkage rules

- **libc++ is static, everywhere.** Every C++ slice links the toolchain's modern libc++ statically. Slices carry no C++ runtime dependency, at the cost of each embedding libc++ — the right trade on a platform whose system runtime is frozen at a pre-C++17 vintage.
- **libSystem is the only dynamic dependency.** Fully static linking is impossible on macOS — `libSystem` must be dynamic — but nothing else need be (DESIGN §4.3). The manager itself is built to the same rule: C++20, static libc++ and third-party libraries, one Mach-O binary that runs on 10.11–12 with zero runtime dependencies.
- **There is no libstdc++ path.** GCC's runtime is not shipped, not linked, not supported. One C++ runtime means one C++ ABI to reason about.

## 6. Flavors and the `-march` floor

The flavor vocabulary is the x86-64 psABI microarchitecture levels (DESIGN §4.2): `v1` (the SSE2 baseline every 64-bit Intel Mac meets), `v2` (SSE4.2/POPCNT), `v3` (AVX2/BMI2/FMA). There is no v4 flavor — no Intel Mac ever shipped AVX-512.

The mechanics:

- **The floor comes from the toolchain, never the formula.** The build environment's `CC`/`CXX` are wrappers that inject the flavor's `-march=x86-64-vN` floor, export `MACOSX_DEPLOYMENT_TARGET`, and apply prefix-mapping. Formula authors never write `-march` themselves (PACKAGE-FORMAT §3); `ctx.flavor` and `ctx.min_os` exist so scripts can *branch* on them, not so they can set flags (PACKAGE-FORMAT §6.3).
- **User flags layer on top, subject to the ABI contract.** A user's `-march=native` or `-O3` is appended at install time and recorded in the artifact manifest (DESIGN §7.4). ABI-neutral choices may share a compatibility key, but byte-distinct results have distinct artifact identities. The harness rejects unsupported ABI-changing flags unless represented by a declared ABI variant; unknown effects require an isolated build and explicit dependency validation. Substitution also checks actual CPU/OS requirements (STATE-AND-RECOVERY §2).
- **The manager is built v1.** It gains nothing from vector ISAs and must run on every supported machine (DESIGN §4.2).

The owned Mac Pro handles `v1`/`v2`; complete `v3` jobs run on the on-demand 2015 MacBook Pro. Emitting instructions is only one part of a build: configure probes, generated tools, dependencies, and tests may execute them. Assignment therefore requires detected CPU and OS capabilities, including those exposed inside guests. Mac Pro VMs cannot provide `v3` execution; jobs wait when no capable worker is available (BUILD-INFRA §6.1).

## 7. Identity: `toolchain_id`

The toolchain is an ingredient of each source-build compatibility key (DESIGN §7.2). The following pseudocode summarizes STATE-AND-RECOVERY §1; the result is the full 64 lowercase hexadecimal digits, never a truncated storage key:

```
build_id = hex_lower(sha256(rfc8785({
    repository, name, version, epoch, revision, abi_variants,  # normalized version
    runtime_abi_epoch, flavor, min_os, toolchain_id, vendor_digest,
})))
```

The `toolchain_id` names the compiler and the floor — `clang-19-10.11` reads as Clang 19 targeting 10.11. Vendor packages set `flavor` and `toolchain_id` to null and bind the vendor artifact digest; source builds use null for the absent vendor digest. Other absent optional identity fields are explicit nulls, and ABI variant maps contain the complete resolved assignment (STATE-AND-RECOVERY §1).

ABI-neutral optimization choices, debug information, timestamps, and build host are absent from the compatibility key. Exact flags, payload hashes, dependency bindings, and CPU requirements enter the artifact manifest. Two builds may share a compatibility key while having different artifact identities; substitution requires ABI evidence, dependent tests, and a compatible target machine (STATE-AND-RECOVERY §1–§2). Short digests are display abbreviations only.

## 8. How a build consumes the toolchain

The toolchain is a pinned slice, consumed like every other input:

- **Pinned in the job manifest** by `build_id`, digest, and URL; the hash of a job manifest is the exact description of a build (BUILD-INFRA §2.1).
- **Mounted read-only at its canonical store path** inside the isolated buildroot, so `-ffile-prefix-map` output is byte-for-byte identical between farm and user builds (BUILD-INFRA §3).
- **Scrubbed, pinned environment**, set by the harness and never the formula: `LC_ALL=C`, `TZ=UTC`, `SOURCE_DATE_EPOCH` pinned to the source timestamp, prefix-mapping (PACKAGE-FORMAT §6.3; DESIGN §9.5). Determinism is a property of the harness, not of the formula.
- **Compiler cache** — a ccache-compatible cache lives in `cache/` and survives across builds (DESIGN §11). It is a performance tool, never an input to identity.
- **The same executor everywhere.** `aslice build` on a laptop uses the farm's sandboxed executor and pinned inputs (BUILD-INFRA §1). Reproduction still requires compatible CPU, OS, and resources.

## 9. Installing it yourself

`aslice-toolchain` is an ordinary package: `aslice install aslice-toolchain` links the bundle into your profile like anything else, and you can compile your own software with it. It never touches `/usr`, and it coexists with Xcode or the CLT if you have them — doctor treats their presence as informational only (DESIGN §12.6).

The support boundary is the validated aslice build matrix; coverage is established by recorded runs as workers become available (BUILD-INFRA §8). As a general-purpose compiler it is yours to use, and bug reports about aslice builds outrank feature requests about other people's build systems.

## 10. Genesis

The toolchain is born twice (GENESIS §1, step 2):

1. **stage0** — proposed on the owned 2013 Mac Pro running Monterey, with compatible Apple host Clang and Command Line Tools, against the oldest archived SDK. Apple lists Monterey as this model's [newest compatible OS](refs/MAC_PRO_2013_COMPATIBLE_OPERATING_SYSTEM.MD). Validate the chosen compiler sources, CLT, SDK, and build tools together before accepting this baseline; record their exact versions and results. A bootstrap failure requires revisiting the toolchain recipe, not assuming a newer host OS is available.
2. **stage1** — stage0 rebuilds the toolchain with itself. stage1 is the toolchain anyone ever uses; stage0 exists so that "who compiled the compiler?" has a documented answer.

Both stages are archived as slices *and* in the repository tree, in the never-lose set (GENESIS §3). Recovery after total loss uses the archived stage0, avoiding an Apple host rebuild. The manager rebuilt with stage1 is compared against the archived unsigned canonical reference; the served signed/notarized binary is verified separately (STATE-AND-RECOVERY §10) (GENESIS §4). GENESIS.md specifies the ceremony, inventory rows, and drill; this section identifies only the toolchain stages and their recovery roles.

## 11. Bumps

A bump changes `toolchain_id`, and `toolchain_id` is part of every build identity — so one bump means an orchard-wide rebuild and fresh slices for everything. The policy follows from that cost:

- **Need-driven.** A bump happens for a concrete cause: a security fix in the compiler or linker, or a language or library capability the orchard genuinely needs. There is no fixed schedule, and upstream's release cadence is not a reason by itself.
- **Batched.** Everything that needs a toolchain change lands in the same bump; the orchard rebuilds once, not monthly.
- **Announced.** A bump is an event with a changelog entry and a migration note, not a background update.
- **Archived forever.** Every previous toolchain slice stays in the repository tree, so historical build identities keep resolving: old locks and old snapshots remain installable (snapshot retention: all published snapshots and referenced hosted objects, with current archive authorization — GENESIS §3).

The known roadmap item is `aslice-toolchain` v2: LLD-first linking and ccache integration (DESIGN §14).

## 12. Boundaries

- **x86_64 only.** No i386 flavor, no 32-bit toolchain work, no multilib (DESIGN §2.2, N6). 32-bit *execution* on 10.11–10.14 is a vendor-payload concern, handled by extraction, not compilation (PACKAGE-FORMAT §3.11).
- **Hosted Xcode and hosted CI are a bonus layer, never load-bearing.** Where hosted runners can reach (~10.13+ deployment targets) they add coverage; the self-hosted toolchain is authoritative (DESIGN §14, §15; GENESIS §2).
- **It targets this platform, period.** macOS 10.11–12 on Intel. It is not a cross-compiler and grows no other targets.

---

*History: v0.1 (September 2026) — initial document, consolidating the toolchain story previously scattered across DESIGN §4.3, GENESIS §1–§4, BUILD-INFRA §2, and PACKAGE-FORMAT §6.3; adds two owner decisions: the toolchain is an ordinary, installable package (§9), and bumps are need-driven, batched, and announced (§11).*

*History: v0.2 (September 2026) — owned-hardware bootstrap with proposed Monterey baseline subject to toolchain validation; capability requirements and pending VM coverage made explicit; companion versions refreshed.*

*History: September 2026 — corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending.*

*History: v0.4 (September 2026) — prose rewrite of the self-hosting rationale, component inventory, and recovery explanation; no content changes.*

*History: v0.5 (September 2026) — resolve compatibility-key and build-flag conflicts against STATE-AND-RECOVERY §1–§2: full hexadecimal keys, complete identity inputs, separate artifact identity, and conditional substitution. No runtime implementation is claimed.*
