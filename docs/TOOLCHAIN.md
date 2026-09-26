# aslice Toolchain — One Compiler Bundle, Every Build

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

- **Status:** Design draft, v0.7 — September 2026
- **Companion to:** [DESIGN.md](DESIGN.md), [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md), [BUILD-INFRA.md](BUILD-INFRA.md), [GENESIS.md](runbooks/GENESIS.md). This document is the authoritative specification for the toolchain; where it and another document disagree, the disagreement is a bug in one of them.
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md).

Navigation: [1. What the toolchain is](#what-the-toolchain-is) · [2. Why self-hosted](#why-self-hosted) · [3. Components](#components) · [4. The SDK strategy](#the-sdk-strategy) · [5. Linkage rules](#linkage-rules) · [6. Flavors and the `-march` floor](#flavors-and-the--march-floor) · [7. Identity: `toolchain_id`](#identity-toolchain_id) · [8. How a build consumes the toolchain](#how-a-build-consumes-the-toolchain) · [9. Installing it yourself](#installing-it-yourself) · [10. Genesis](#genesis) · [11. Bumps](#bumps) · [12. Boundaries](#boundaries)

<a id="what-the-toolchain-is"></a>

## 1. What the toolchain is

aslice brings its own toolchain. A user never installs Xcode or the Command Line Tools ([MANUAL §2.1](MANUAL.md#what-you-need)); every build — on the farm or on a laptop — runs with `aslice-toolchain` and nothing else.

The bundle: modern Clang, LLD where viable (ld64 from cctools-port otherwise), a modern libc++, CMake, Ninja, and pkgconf, plus thin compiler wrappers that carry the build contract into every invocation (§6). It is self-hosted: it builds itself (§10), it is the authoritative toolchain for every package including aslice itself, and it is consumed as a pinned slice like any other input — content-addressed, signed, mounted read-only into builds (§8).

It is also just a package. `aslice-toolchain` lives in the core orchard, and `aslice install aslice-toolchain` gives you the compiler bundle for your own work (§9).

<a id="why-self-hosted"></a>

## 2. Why self-hosted

The supported platform requires a self-hosted toolchain ([DESIGN §4.3](DESIGN.md#toolchain-floor--self-hosted-from-day-one)):

- **Hosted toolchains cannot reach the floor.** Xcode 15-era toolchains refuse deployment targets below ~10.13, and hosted Intel runners never ship anything older. The platform floor is 10.11, so the toolchain that targets it cannot be Apple's current one.
- **The C++ runtime is the real constraint.** Clang's target floor is far older than libc++'s: `-mmacosx-version-min=10.11` is still accepted, but 10.11's system libc++ predates half of C++17. The toolchain therefore ships a modern libc++ and statically links it into everything it produces (§5).
- **Builds must not see ambient machine state.** A build job pins every input — toolchain, dependencies, sources, formula ([BUILD-INFRA §2.1](BUILD-INFRA.md#jobs-are-closed-worlds)). A compiler borrowed from the host would be ambient state.
- **Reproducibility needs a fixed point.** Two builders bit-compare only if the compiler is byte-identical on both; a slice mounted at its canonical path is (§8).

The platform is frozen, which is what makes this affordable: the toolchain is built and archived once per bump (§11), not chased.

<a id="components"></a>

## 3. Components

| Component | Role | Notes |
|---|---|---|
| Clang | C/C++ compiler | Targets darwin15 through Monterey; accepts `-mmacosx-version-min=10.11` |
| libc++ | C++ runtime | Statically linked into every product (§5); the system libc++ is never used |
| LLD / ld64 | Linker | LLD where viable on this platform; ld64 from cctools-port otherwise. v2 moves LLD-first (§11) |
| CMake / Ninja / pkgconf | Build tooling | The harness's `ctx.cmake` / `ctx.make` / `ctx.meson` helpers wrap these with correct defaults ([PACKAGE-FORMAT §6.3](PACKAGE-FORMAT.md#buildstar--the-custom-api)) |
| Compiler wrappers | Contract enforcement | What `CC`/`CXX` point at in a build; inject the flavor floor, the deployment target, and prefix-mapping (§6) |

The table identifies the components and their roles. Exact versions and the per-OS workaround register live in the toolchain slice's manifest (§4), which is the authoritative inventory.

<a id="the-sdk-strategy"></a>

## 4. The SDK strategy

One SDK serves everything: the oldest archived Apple SDK, paired with the deployment-target mechanism. `-mmacosx-version-min` is mature — the deployment target establishes an intended floor, while availability guards and per-release execution tests establish whether the binary actually works ([DESIGN §4.1](DESIGN.md#the-os-axis-collapses--at-1011)). So a package builds once, against the oldest SDK, per flavor — not once per OS release.

The consequences are handled explicitly:

- **Workarounds are recorded, not remembered.** Where a component or a package needs a per-OS quirk — an availability guard, a missing-symbol shim — the workaround is written down in the toolchain's manifest ([DESIGN §4.3](DESIGN.md#toolchain-floor--self-hosted-from-day-one)), versioned with the toolchain.
- **Formulae declare their own floor.** A package that cannot cleanly target 10.11 declares `min_os` and moves on ([PACKAGE-FORMAT §3.2](PACKAGE-FORMAT.md#platform-bounds--minimum-os-maximum-os)); the toolchain does not contort itself to drag it down.
- **Claims require tests.** The farm targets every claimed release, 10.11 through 12, in batches of validated guests ([BUILD-INFRA §8](BUILD-INFRA.md#the-vm-test-matrix)). Required coverage remains pending until host/hypervisor/guest compatibility and actual OS/flavor tests pass; the matrix is not yet evidence of completed validation.
- **The SDKs are never-lose.** The archived Apple installers and SDKs are genesis inventory — two independent locations, one of them offline ([GENESIS §3](runbooks/GENESIS.md#the-never-lose-set)). Apple pulls old SDKs; we don't notice.

<a id="linkage-rules"></a>

## 5. Linkage rules

- **libc++ is static, everywhere.** Every C++ slice links the toolchain's modern libc++ statically. Slices carry no C++ runtime dependency, at the cost of each embedding libc++ — the right trade on a platform whose system runtime is frozen at a pre-C++17 vintage.
- **The manager links only libSystem dynamically.** The aslice manager uses C++20 with static libc++ and third-party libraries; libSystem remains the platform dependency. This restriction applies to the manager, not all packages: slices may bind packaged dynamic libraries and permitted system frameworks under [PACKAGE-FORMAT §5](PACKAGE-FORMAT.md#dependency-semantics) and [ORCHARD-POLICY §6](ORCHARD-POLICY.md#dependencies-and-system-software). Execution across 10.11–12 still requires the acceptance tests in [STATE-AND-RECOVERY §10](STATE-AND-RECOVERY.md#acceptance-and-implementation-order).
- **There is no libstdc++ path.** GCC's runtime is not shipped, not linked, not supported. One C++ runtime means one C++ ABI to reason about.

<a id="flavors-and-the--march-floor"></a>

## 6. Flavors and the `-march` floor

The flavor vocabulary is the x86-64 psABI microarchitecture levels ([DESIGN §4.2](DESIGN.md#the-µarch-axis-grows-three-flavors)): `v1` (the SSE2 baseline every 64-bit Intel Mac meets), `v2` (SSE4.2/POPCNT), `v3` (AVX2/BMI2/FMA). There is no v4 flavor — no Intel Mac ever shipped AVX-512.

The mechanics:

- **The floor comes from the toolchain, never the formula.** The build environment's `CC`/`CXX` are wrappers that inject the flavor's `-march=x86-64-vN` floor, export `MACOSX_DEPLOYMENT_TARGET`, and apply prefix-mapping. Formula authors never write `-march` themselves ([PACKAGE-FORMAT §3](PACKAGE-FORMAT.md#packagetoml--full-schema)); `ctx.flavor` and `ctx.min_os` exist so scripts can *branch* on them, not so they can set flags ([PACKAGE-FORMAT §6.3](PACKAGE-FORMAT.md#buildstar--the-custom-api)).
- **User flags layer on top, subject to the ABI contract.** A user's `-march=native` or `-O3` is appended at install time and recorded in the artifact manifest ([DESIGN §7.4](DESIGN.md#user-flags)). ABI-neutral choices may share a compatibility key, but byte-distinct results have distinct artifact identities. The harness rejects unsupported ABI-changing flags unless represented by a declared ABI variant; unknown effects require an isolated build and explicit dependency validation. Substitution also checks actual CPU/OS requirements ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)).
- **The manager is built v1.** It gains nothing from vector ISAs and must run on every supported machine ([DESIGN §4.2](DESIGN.md#the-µarch-axis-grows-three-flavors)).

The owned Mac Pro handles `v1`/`v2`; complete `v3` jobs run on the on-demand 2015 MacBook Pro. Emitting instructions is only one part of a build: configure probes, generated tools, dependencies, and tests may execute them. Assignment therefore requires detected CPU and OS capabilities, including those exposed inside guests. Mac Pro VMs cannot provide `v3` execution; jobs wait when no capable worker is available ([BUILD-INFRA §6.1](BUILD-INFRA.md#the-build-plan)).

<a id="identity-toolchain_id"></a>

## 7. Identity: `toolchain_id`

The toolchain is an ingredient of each source-build compatibility key ([DESIGN §7.2](DESIGN.md#build-identity)). The following pseudocode summarizes [STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#compatibility-and-artifact-identity); the result is the full 64 lowercase hexadecimal digits, never a truncated storage key:

```text
build_id = hex_lower(sha256(rfc8785({
    repository, name, version, epoch, revision, abi_variants,  # normalized version
    runtime_abi_epoch, flavor, min_os, toolchain_id, vendor_digest,
})))
```

The `toolchain_id` names the compiler and the floor — `clang-19-10.11` reads as Clang 19 targeting 10.11. Vendor packages set `flavor` and `toolchain_id` to null and bind the vendor artifact digest; source builds use null for the absent vendor digest. Other absent optional identity fields are explicit nulls, and ABI variant maps contain the complete resolved assignment ([STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#compatibility-and-artifact-identity)).

ABI-neutral optimization choices, debug information, timestamps, and build host are absent from the compatibility key. Exact flags, payload hashes, dependency bindings, and CPU requirements enter the artifact manifest. Two builds may share a compatibility key while having different artifact identities; substitution requires ABI evidence, dependent tests, and a compatible target machine ([STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#compatibility-and-artifact-identity) and [STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)). Short digests are display abbreviations only.

<a id="how-a-build-consumes-the-toolchain"></a>

## 8. How a build consumes the toolchain

The toolchain is a pinned slice, consumed like every other input:

- **Pinned in the job manifest** by `build_id`, digest, and URL; the hash of a job manifest is the exact description of a build ([BUILD-INFRA §2.1](BUILD-INFRA.md#jobs-are-closed-worlds)).
- **Mounted read-only at its canonical store path** inside the isolated buildroot, so `-ffile-prefix-map` output is byte-for-byte identical between farm and user builds ([BUILD-INFRA §3](BUILD-INFRA.md#the-pipeline-shared-at-both-scales)).
- **Scrubbed, pinned environment**, set by the harness and never the formula: `LC_ALL=C`, `TZ=UTC`, `SOURCE_DATE_EPOCH` pinned to the source timestamp, prefix-mapping ([PACKAGE-FORMAT §6.3](PACKAGE-FORMAT.md#buildstar--the-custom-api); [DESIGN §9.5](DESIGN.md#build-provenance)). Determinism is a property of the harness, not of the formula.
- **Compiler cache** — a ccache-compatible cache lives in `cache/` and survives across builds ([DESIGN §11](DESIGN.md#performance-model)). It is a performance tool, never an input to identity.
- **The same executor everywhere.** `aslice build` on a laptop uses the farm's sandboxed executor and pinned inputs ([BUILD-INFRA §1](BUILD-INFRA.md#the-founding-axiom)). Reproduction still requires compatible CPU, OS, and resources.

<a id="installing-it-yourself"></a>

## 9. Installing it yourself

`aslice-toolchain` is an ordinary package: `aslice install aslice-toolchain` links the bundle into your profile like anything else, and you can compile your own software with it. It never touches `/usr`, and it coexists with Xcode or the CLT if you have them — doctor treats their presence as informational only ([DESIGN §12.6](DESIGN.md#doctor-sanity-checking)).

The support boundary is the validated aslice build matrix; coverage is established by recorded runs as workers become available ([BUILD-INFRA §8](BUILD-INFRA.md#the-vm-test-matrix)). As a general-purpose compiler it is yours to use, and bug reports about aslice builds outrank feature requests about other people's build systems.

<a id="genesis"></a>

## 10. Genesis

The toolchain is born twice ([GENESIS §1](runbooks/GENESIS.md#the-from-nothing-sequence), step 2):

1. **stage0** — proposed on the owned 2013 Mac Pro running Monterey, with compatible Apple host Clang and Command Line Tools, against the oldest archived SDK. Apple lists Monterey as this model's [newest compatible OS](refs/MAC_PRO_2013_COMPATIBLE_OPERATING_SYSTEM.MD). Validate the chosen compiler sources, CLT, SDK, and build tools together before accepting this baseline; record their exact versions and results. A bootstrap failure requires revisiting the toolchain recipe, not assuming a newer host OS is available.
2. **stage1** — stage0 rebuilds the toolchain with itself. stage1 is the toolchain anyone ever uses; stage0 exists so that "who compiled the compiler?" has a documented answer.

Both stages are archived as slices *and* in the repository tree, in the never-lose set ([GENESIS §3](runbooks/GENESIS.md#the-never-lose-set)). Recovery after total loss uses the archived stage0, avoiding an Apple host rebuild. The manager rebuilt with stage1 is compared against the archived unsigned canonical reference; the served signed/notarized binary is verified separately ([STATE-AND-RECOVERY §10](STATE-AND-RECOVERY.md#acceptance-and-implementation-order)) ([GENESIS §4](runbooks/GENESIS.md#re-standup-after-total-loss)). GENESIS.md specifies the ceremony, inventory rows, and drill; this section identifies only the toolchain stages and their recovery roles.

<a id="bumps"></a>

## 11. Bumps

A bump changes `toolchain_id`, and `toolchain_id` is part of every build identity — so one bump means an orchard-wide rebuild and fresh slices for everything. The policy follows from that cost:

- **Need-driven.** A bump happens for a concrete cause: a security fix in the compiler or linker, or a language or library capability the orchard genuinely needs. There is no fixed schedule, and upstream's release cadence is not a reason by itself.
- **Batched.** Everything that needs a toolchain change lands in the same bump; the orchard rebuilds once, not monthly.
- **Announced.** A bump is an event with a changelog entry and a migration note, not a background update.
- **Archived forever.** Every previous toolchain slice stays in the repository tree, so historical build identities keep resolving: old locks and old snapshots remain installable (snapshot retention: all published snapshots and referenced hosted objects, with current archive authorization — [GENESIS §3](runbooks/GENESIS.md#the-never-lose-set)).

The known roadmap item is `aslice-toolchain` v2: LLD-first linking and ccache integration ([DESIGN §14](DESIGN.md#roadmap)).

<a id="boundaries"></a>

## 12. Boundaries

- **x86_64 only.** No i386 flavor, no 32-bit toolchain work, no multilib ([DESIGN §2.2](DESIGN.md#non-goals), N6). 32-bit *execution* on 10.11–10.14 is a vendor-payload concern, handled by extraction, not compilation ([PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software)).
- **Hosted Xcode and hosted CI are a bonus layer, never load-bearing.** Where hosted runners can reach (~10.13+ deployment targets) they add coverage; the self-hosted toolchain is authoritative ([DESIGN §14](DESIGN.md#roadmap) and [DESIGN §15](DESIGN.md#risks-and-open-questions); [GENESIS §2](runbooks/GENESIS.md#the-genesis-inventory)).
- **It targets this platform, period.** macOS 10.11–12 on Intel. It is not a cross-compiler and grows no other targets.

---

## History

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v0.6 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v0.5 | September 2026 | resolve compatibility-key and build-flag conflicts against STATE-AND-RECOVERY §1–§2: full hexadecimal keys, complete identity inputs, separate artifact identity, and conditional substitution. No runtime implementation is claimed. |
| v0.4 | September 2026 | prose rewrite of the self-hosting rationale, component inventory, and recovery explanation; no content changes. |
| v0.2 | September 2026 | owned-hardware bootstrap with proposed Monterey baseline subject to toolchain validation; capability requirements and pending VM coverage made explicit; companion versions refreshed. |
| v0.1 | September 2026 | initial document, consolidating the toolchain story previously scattered across DESIGN §4.3, GENESIS §1–§4, BUILD-INFRA §2, and PACKAGE-FORMAT §6.3; adds two owner decisions: the toolchain is an ordinary, installable package (§9), and bumps are need-driven, batched, and announced (§11). |
| Not recorded | September 2026 | corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending. |
| v0.7 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |

</details>
