# aslice Authoring Guide

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

**How to write, test, and ship aslice packages.**

- **Status:** v0.15 — September 2026
- **Audience:** package authors — people writing formulae for the core or extended orchards, packaging vendor binaries, or running their own orchard. Read [MANUAL.md](MANUAL.md) chapters 1–4 first; this guide assumes the vocabulary (slice, orchard, flavor, generation) and the user's view of the system.
- **Companions:** [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) is the authoritative schema — when this guide and the schema disagree, the schema is right. [ORCHARD-POLICY.md](ORCHARD-POLICY.md) is the policy this guide summarizes. [BUILD-INFRA.md](BUILD-INFRA.md) is the farm your PR builds on. [MANUAL.md](MANUAL.md) is what your users read.
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md) — project terms, acronyms, and the Homebrew translation table.

---

Navigation: [1. Overview](#overview) · [2. Your first package](#your-first-package) · [3. package.toml, section by section](#packagetoml-section-by-section) · [4. build.star: the build script](#buildstar-the-build-script) · [5. Variants and the ABI contract](#variants-and-the-abi-contract) · [6. Tests](#tests) · [7. Keeping it fresh](#keeping-it-fresh) · [8. Vendor binaries](#vendor-binaries) · [9. Special categories](#special-categories) · [10. The merge gate and review](#the-merge-gate-and-review) · [11. Publishing your own orchard and repository](#publishing-your-own-orchard-and-repository) · [12. Maintaining the orchard](#maintaining-the-orchard) · [Appendix. The author's checklist](#appendix-the-authors-checklist)

<a id="overview"></a>

## 1. Overview

An aslice package is a directory in an orchard, and an orchard is a git repository of package directories. Each directory holds four files, two of them optional:

```text
orchards/core/ffmpeg/
 ├── package.toml      # metadata, sources, dependencies, variants — pure data
 ├── build.star        # the build script — Starlark, sandboxed
 ├── patches/          # optional, every file checksummed
 └── tests.star        # optional smoke tests — required for core
```

Two rules carry the entire security model. Everything else in this guide is a consequence:

1. **`package.toml` is data, and binary installs run no code at all.** When a user installs your package from a slice, nothing of yours executes. No install hooks, no scripts — the sole exception is the declared graft of §8, and even that runs hash-pinned, user-approved, and sandboxed to its declared behavior. Your `build.star` runs only when the package is *built* — on the farm, or on a user's machine that asked for a source build — and even then it runs inside a sandbox with no network and no filesystem access outside the build directory.
2. **Everything is pinned.** Source URLs carry sha256 hashes; patches are checksummed; the index countersigns the closure. If you can't hash it, you can't ship it.

When you open a PR against an orchard, the farm lints your formula, builds it in the sandbox on every flavor it declares, runs your smoke tests across the supported OS range, and checks that your change doesn't break the published interface of anything that depends on it. Only then does a human look at it. Review is about correctness and policy — never "does it compile," because CI already answered that. After merge, the signing machine signs the new slices, and the index publishes them in the next snapshot.

The whole journey is **your PR → lint → matrix build → smoke tests → ABI gate → human review → merge → sign → publish**. This guide covers the parts you control.

---

<a id="your-first-package"></a>

## 2. Your first package

<a id="scaffolding"></a>

### 2.1 Scaffolding

```sh
aslice create https://example.org/releases/foo-1.2.tar.gz
```

`create` downloads the archive, hashes it, sniffs out the build system (autotools, CMake, Meson), and emits a formula directory with a draft `package.toml` and `build.star`. Treat the draft as a starting point, not a finished package: review every field it guessed. Then fill in the things only you know — the description, the license, `min_os`, and the livecheck block (§7).

<a id="building-it-locally"></a>

### 2.2 Building it locally

```sh
aslice build foo                  # builds in the same sandbox the farm uses
aslice test foo                   # runs tests.star against what you built
aslice install ./foo              # install your local build into your profile
```

`aslice build` uses the same pinned `aslice-toolchain`, phases, sandbox profiles, and environment scrubbing as the farm. The sandbox rejects undeclared host toolchains, including local Xcode CLT dependencies, on either machine. Reproducing a job still requires compatible CPU features, OS support, and resources. A successful local build establishes its tested configuration; required farm builds, cross-OS smoke tests, graft rehearsals, and independent rebuilds remain gates ([BUILD-INFRA §6.1](BUILD-INFRA.md#the-build-plan) and [BUILD-INFRA §7](BUILD-INFRA.md#trust-owner-merge-authorizes-processing-agents-produce-evidence) and [BUILD-INFRA §8](BUILD-INFRA.md#the-vm-test-matrix)).

<a id="the-iteration-loop"></a>

### 2.3 The iteration loop

The loop is edit, `aslice build`, `aslice test`, repeat. When the package does what the description says, run the linter the way CI runs it:

```sh
aslice lint foo                   # the same schema + policy checks as the merge gate
```

Then open the PR. The following chapters explain how to prepare the metadata, build script, and tests for review.

---

<a id="packagetoml-section-by-section"></a>

## 3. package.toml, section by section

The annotated formula below introduces the fields used in an ordinary package. PACKAGE-FORMAT.md is the schema reference for every field.

Recipe excerpts below require a verified source digest and all required policy fields before publication.

```toml
spec = 1

[package]
name        = "ffmpeg"
version     = "7.1.0"
revision    = 0             # bump when the formula changes but upstream doesn't
license     = "LGPL-2.1-or-later"    # SPDX identifier — the linter checks
description = "Play, record, convert, and stream audio and video"
homepage    = "https://ffmpeg.org"
min_os      = "10.13"       # the oldest release this formula actually supports
```

**Declare the floor you tested.** Many modern codebases can't cleanly target 10.11 — C++17 library features, `clock_gettime`, `thread_local` quirks. A package that claims 10.11 and fails there is far worse than one that honestly says 10.13. CI smoke-runs your package on every release from your declared `min_os` through 12, so an optimistic floor is not a secret; it is a failing build.

```toml
[[source]]
url    = "https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz"
sha256 = "<verified-source-sha256>"
mirrors = ["https://mirror.example.org/ffmpeg-7.1.tar.xz"]   # optional
```

The hash is the contract. A client fetches from the canonical URL, then your `mirrors`, then the repository's own blob archive, where the farm deposits every source it ever fetched; all three are verified against the same pinned sha256. Two consequences follow. First, upstream reorganizing its download site breaks nothing for anyone, because the archive still serves the source. Second, a hash mismatch is a hard failure everywhere — which is what you want, since the hash is the only thing standing between your users and a re-rolled tarball.

```toml
[variants.x265]
default = true
abi     = true
description = "HEVC encoding via x265"

[variants.debug]
default = false
abi     = false
description = "Build with debug symbols"

[depends]
runtime = ["x264", "x265?variant.x265", "lame", "opus", "srt"]
build   = ["nasm", "pkgconf"]
```

Variants are the package's options. The `abi = true` line means "enabling or disabling this changes the interface my consumers link against" — it is the most consequential line in the file, and §5 is about getting it right. Dependencies are aslice packages, never system libraries: on this platform the OS's bundled libraries *are the problem being solved*, so a formula that links `/usr/lib/libssl.dylib` is a lint error, not a shortcut. The only exceptions are the always-present system *frameworks* (`Accelerate`, `CoreAudio`, …), which are the platform's ABI; adding to that allowlist is a policy PR, not a formula decision.

```toml
[livecheck]
url    = "https://ffmpeg.org/download.html"
regex  = "ffmpeg-([0-9.]+)\\.tar\\.xz"
```

Livecheck is how the orchard notices new upstream releases without watching anyone's machine (§7). Core-tier formulae are expected to carry one.

---

<a id="buildstar-the-build-script"></a>

## 4. build.star: the build script

`build.star` is Starlark — Python-shaped, deterministic, no `eval`, no recursion — and it executes inside the build sandbox. You write phase functions, the harness calls them in order, and the `ctx` object is your entire world.

```python
def configure(ctx):
    args = [
        "--prefix=" + ctx.prefix,
        "--enable-gpl",
        "--enable-libx264",
    ]
    if ctx.variant("x265"):
        args.append("--enable-libx265")
    ctx.env.append("CFLAGS", ctx.user_cflags)   # accepted flags: recorded; ABI and CPU checks still apply
    ctx.run("./configure", *args)

def build(ctx):
    ctx.make(jobs = ctx.jobs)

def install(ctx):
    ctx.make("install", destdir = ctx.staging)
```

<a id="what-the-sandbox-means-in-practice"></a>

### 4.1 What the sandbox means in practice

- **No network.** Not "restricted network" — none. If your build downloads a dependency, vendor it as an additional `[[source]]` entry with its own hash, or package it separately and depend on it. Builds that phone home fail, and that is a feature: it is why aslice can promise users that building from source doesn't widen their trust surface.
- **Writes stay in the build directory.** The toolchain and the store are read-only to you. Install into `ctx.staging` (DESTDIR-style), never into the prefix; the harness assembles the store path from your staging tree.
- **The environment is deterministic.** Locale, timezone, `PATH`, and compiler flags are set by the harness. If your build embeds timestamps or host paths, it may build unreproducibly — which starts to matter when the farm's second builder tries to bit-match your slice.
- **The phases are fetch → unpack → patch → configure → build → install → test**, each with its own sandbox profile. Patches live in `patches/`, are checksummed, and are applied by the harness. Your script never shells out to `patch`.

<a id="the-ctx-object-by-group"></a>

### 4.2 The ctx object, by group

- **Paths:** `ctx.prefix` (the build-time relocation placeholder; the test context uses the materialized installation path), `ctx.staging` (install target), `ctx.build_dir`, `ctx.jobs`.
- **Configuration:** `ctx.variant("name")` for variant state, `ctx.user_cflags` / `ctx.user_ldflags` for the user's optimization flags. Always append them where the build system expects them; they are recorded in the artifact manifest. ABI-neutral flags may share a compatibility key; ABI-changing flags need a declared ABI variant, and unknown effects need explicit dependency validation (§5.2).
- **Execution:** `ctx.run(...)`, `ctx.make(...)`, `ctx.env` — the full capability set. There is no general subprocess escape. If you need a tool, it is a build dependency.
- **Platform facts:** the target OS floor and flavor. Gate workaround code on these, not on probing the build host. The farm builds every declared combination, and host-probing is how formulas lie.

<a id="common-build-systems"></a>

### 4.3 Common build systems

Autotools and CMake cover most of the orchard, and `create` scaffolds both. The short forms:

```python
# CMake
def configure(ctx):
    ctx.run("cmake", "-S", ".", "-B", "build",
            "-DCMAKE_INSTALL_PREFIX=" + ctx.prefix,
            "-DCMAKE_BUILD_TYPE=Release")

# A library that must not build its own copy of a dependency
def configure(ctx):
    ctx.env.set("PKG_CONFIG_PATH", ctx.deps["openssl"] + "/lib/pkgconfig")
```

The pattern to internalize: **dependencies come from aslice, and you say so explicitly.** Vendored copies, downloads at build time, and "the system probably has it" are the three ways formulae rot. The sandbox rejects all three — lean into it.

---

<a id="variants-and-the-abi-contract"></a>

## 5. Variants and the ABI contract

<a id="the-one-decision-that-matters"></a>

### 5.1 The one decision that matters

Every variant you declare answers one question: *does flipping this change what my consumers link against?*

- Enabling `x265` in ffmpeg adds an encoder that applications link to — the exported interface changes. `abi = true`.
- Debug symbols change the bits, not the interface. `abi = false`.
- ABI-neutral optimization choices (`-O3`, `-march=native`) need no feature variant and may share a compatibility key. Exact flags and CPU requirements enter the artifact manifest, so changed outputs have distinct artifact identities. Unsupported ABI-changing flags are rejected unless covered by a declared ABI variant; unknown effects require an isolated build and explicit dependency validation ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)).

Mark a variant `abi = true` and it becomes part of the package's build identity: `ffmpeg+x265` and `ffmpeg-x265` are different builds, they coexist in the store, and dependents record which one they linked against. Mark it `false` and flipping it triggers a local build sharing the compatibility key but receiving its own artifact identity. Exact dependency bindings and ABI checks still apply.

<a id="what-the-abi-scan-does-with-this"></a>

### 5.2 What the ABI scan does with this

When your package builds, the harness scans the staged output and records the interface in the manifest: every dylib's install name, current and compatibility versions, exported and required symbol lists, evidence classification, and exact dependency artifact bindings. For farm-built and user-built packages alike, substitution requires adequate ABI evidence, dependent tests, and compatible CPU/OS requirements. Incomplete evidence retains the exact provider artifact or requires rebuilding and testing dependents ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)). Your job is to keep the *declaration* accurate. Two situations come up:

- **If a version bump changes the exported interface** (soname bump, dropped symbols), the ABI gate in CI compares your build against the published one and fails the PR unless the version reflects it — an explicit version bump, or scheduled rebuilds of the dependents in the same snapshot. "It'll probably be fine" is precisely what the gate exists to prevent.
- **If you're unsure whether a variant changes the interface,** build both ways and compare the `aslice build --emit-abi` output. Declare what the evidence establishes; an incomplete scan is not proof of compatibility.

<a id="discipline"></a>

### 5.3 Discipline

`abi = true` variants carry no cap; each must name the interface it changes, and the ABI scan — not a reviewer's taste — is the check. This is the lesson of Homebrew's option sprawl, learned in advance and aimed the right way: the failure was unmaintained defaults and guesswork, not user choice. ffmpeg is the standing example — codec combinations are many, some uncommon, some buildable from source only, and all of them legitimate when a user needs one. Non-default variants build locally on the user's machine; the farm prebuilds defaults plus demonstrated-demand variants, so an unusual combination costs the project nothing. Build-flavor variants (`abi = false`) are unconstrained, because they spawn no binaries — but each still needs a reason to exist.

---

<a id="tests"></a>

## 6. Tests

`tests.star` runs after install, in the build sandbox, against the staged result:

```python
def test(ctx):
    ctx.run(ctx.prefix + "/bin/ffmpeg", "-version")
    ctx.run(ctx.prefix + "/bin/ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-f", "null", "-")
```

A good smoke test proves the package *works*, not merely that it exists: encode a second of video, serve a request, round-trip a document. Running the binary with `-version` catches broken linkage and missing dylibs, the most common real failure; a test that exercises the package's actual function catches the next five most common. Core tier requires a working smoke test on at least one OS × one flavor, and CI runs yours across the whole supported range from your `min_os` through 12.

Users can run your tests too, any time: `aslice test ffmpeg` executes them against the installed slice. Write them to be safe on a user's machine — read-only outside a temp directory, no network by default. If a test genuinely needs the network, declare `test_network = true` in the formula, and accept the scrutiny in review.

---

<a id="keeping-it-fresh"></a>

## 7. Keeping it fresh

<a id="livecheck-and-autobump"></a>

### 7.1 Livecheck and autobump

The `[livecheck]` block tells the orchard's scheduled job where to look for newer releases. When one appears, the orchard opens a bump PR automatically — formula edited, hash recomputed, CI running — and a maintainer reviews it like any other change. A human does the same thing by hand with `aslice bump-pr foo 7.2`: edit, lint, smoke-build one flavor, open the PR. And users can check any package themselves with `aslice livecheck foo`. Maintainers get the orchard-wide view with `aslice orchard freshness` — every package's days-behind-upstream, worst first (§12).

Write livecheck blocks against pages the upstream actually maintains — the download listing, the release feed — and prefer a regex that cannot silently match a prerelease. A livecheck that takes "7.2rc1" for newer than "7.1" ships a release candidate to users who didn't ask for one.

<a id="when-upstream-dies"></a>

### 7.2 When upstream dies

Upstreams on this platform die in a specific way. Usually it is not the project that dies, but its hospitality: the download page reorganizes, old tarballs vanish, the domain expires. When your formula's canonical URL dies, three things happen, in this order:

1. **Nothing already built breaks.** Every source the farm fetched is archived, hash-pinned, in the repository's own blob store, and clients fetch from there when the URL 404s. Your package keeps working while you fix the formula.
2. **Note the death in the formula.** A comment naming the date and the mirror situation, so the next maintainer knows the context without archaeology.
3. **Point the formula at a living mirror** if one exists; otherwise let it ride the archive and adjust livecheck. If the upstream is truly gone, move the package toward the archive track per [ORCHARD-POLICY §8](ORCHARD-POLICY.md#deprecation-and-removal-lifecycle).

The archiving is policy, not luck ([DESIGN §9.6](DESIGN.md#the-repository-system)). Dead-upstream software is half the reason this orchard exists.

---

<a id="vendor-binaries"></a>

## 8. Vendor binaries

Some software will only ever ship as a `.pkg` or `.dmg` — commercial audio tools, vendor CLIs, frozen releases of abandoned apps. You package it as `type = "binary"`, and aslice installs it without ever executing the vendor's installer scripts — unless you declare those scripts as grafts (below).

```toml
[package]
name = "convolver"
type = "binary"
# ...

[[binary]]
url         = "https://vendor.example/convolver-3.1.pkg"
sha256      = "…"
min_os      = "10.11"
max_os      = "12"
arch        = ["x86_64", "i386"]
redistribute = true
signer      = "Developer ID Application: Example Audio (TEAMID)"
notarized   = true

[[binary.payload]]
from = "Payload/Convolver.app"
to   = "apps/Convolver.app"

[[binary.payload]]
from = "Payload/bin/cvcli"
to   = "bin/cvcli"
```

(Payload maps are an array of tables — `from`/`to` pairs — per [PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software). As always: when this guide and the schema disagree, the schema is right.)

The rules, and the reasons for them:

- **Only the payload installs by default; scripts the software needs become grafts.** `preinstall`/`postinstall` scripts are never executed unless you declare them as grafts (`[[binary.graft]]`, [PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software); the model in [DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)). If the software genuinely requires its scripts — audio DSP drivers, pro-video plugins, kext installers — you don't route around the rule, you declare the script: extract it from the artifact, pin its sha256, and write the behavior manifest (`writes`, `kexts`, `daemons`, `network`, `elevated`) from evidence. Evidence means: read the script line by line, then rehearse it — `aslice orchard ci` runs each graft under its manifest-derived profile and diffs observed behavior against your declaration, locally on your OS and, at the merge gate, in the farm's per-OS VMs — and correct the manifest until the observed behavior matches your declaration exactly. An under-declared manifest fails the rehearsal gate; a script you cannot describe does not ship. Kexts and drivers are *not* excluded by any of this: a payload-shipped kext goes through the declared `[system]` category (§9), where aslice's own helper performs the privileged steps from your declarations, and a script-installed kext names its bundle ID in the graft's `kexts` field.
- **The signer is pinned.** If the vendor silently re-signs with a different identity, installs hard-fail. That is a classic supply-chain attack against binary distribution, and the pin is the whole defense. Don't leave it out because "the vendor is trustworthy" — the pin exists for the day they aren't, or the day their signing infrastructure isn't. The single exception is genuinely unsigned vendor software: permitted in the extended orchard only, with `signer` omitted and an announcement at every install ([PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software), [ORCHARD-POLICY §12](ORCHARD-POLICY.md#vendor-binary-packages-pkgdmg)).
- **OS tags are verified, or the formula doesn't merge.** Each `[[binary]]` entry declares its real `min_os`/`max_os`; the pack-time verifier checks your claims against the bundle's own metadata, and lint fails on mismatches. A vendor's "legacy 10.11 build" and "current 10.14+ build" can coexist as two entries in one formula.
- **The 32-bit ceiling follows required execution.** Required i386-only executables, helpers, or plugins restrict a payload to 10.11 through 10.14 and require `max_os = "10.14"` or lower. An unused i386 member in a fat executable with a usable x86_64 member does not impose that ceiling. The verifier checks entry points and dependency paths; ambiguous plugin requirements need evidence or rejection ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)). Universal payloads install whole. Never thin them with `lipo`: thinning invalidates the vendor's code signature, and the signature outranks the disk savings.
- **`redistribute` decides who fetches.** With `true`, the farm repackages into a normal slice and hosts it — the best user experience. With `false`, the formula is a pointer, and each client fetches the vendor URL itself, hash- and signer-pinned. Core tier requires `true`: core never depends on a vendor's server being up.

---

Graft admission also requires the staging, network-refusal, capability, and crash-recovery checks in [STATE-AND-RECOVERY §4](STATE-AND-RECOVERY.md#graft-execution-boundary). Matching a rehearsal trace alone does not prove containment.

<a id="special-categories"></a>

## 9. Special categories

Four declaration blocks cover the packages that don't fit the ordinary mold. Each exists because the alternative was users doing the same thing by hand, with no provenance and no rollback — and each is gated accordingly.

**`[service]`** — the package runs a daemon. Declare argv, domain, keepalive, working directory, log paths; aslice generates and manages the launchd job. `domain = "user"` services are ungated. `domain = "system"` root daemons are gated to official, verified, and local repositories — root execution is the privilege that matters.

**`[system]`** — kernel extensions and SIP-disabled development tools. Declare the kexts, whether SIP must be off, and a mandatory `reason` string, which is shown verbatim in every warning to every installer. Official, verified, and local repositories may serve these; third-party never. Write the `reason` as if the user will read it aloud before deciding. They will.

**`[system-patch]`** — the package replaces an Apple-provided file. Declare target paths, security prerequisites, and a reason. The helper retains byte-exact originals and metadata in protected root-owned storage. Executable replacements and their dependencies come from a verified root-owned closure; supported symlinks target that closure, never the user-writable profile ([STATE-AND-RECOVERY §3](STATE-AND-RECOVERY.md#privileged-ownership-and-capability-checks)). Writable paths use journaled operations; protected volumes use the OS-specific Recovery or boot-snapshot backend, and restoration may require Recovery and reboot (SYSTEM-VOLUMES). Official and local repositories may serve these packages; verified repositories need an explicit per-repo grant. The refused target list includes the kernel, dyld, libSystem, `/System`, platform-binary dylibs, and early-boot consumers. No flag overrides it.

**`[extension]` / `[ride]`** — runtime-bound packages. A compiled extension (`php-redis`) declares `[extension] runtime = "php"` and binds to the runtime's ABI epoch; the farm builds it for every supported stream. A tool that runs *on* a runtime without compiling against it (composer, yarn) declares `[ride] runtime = "php"` and follows the user's stream selection. Which one applies is a fact about the code: if it links the runtime's libraries, it is an extension; if it merely needs the interpreter, it rides. Get this wrong and the tool breaks on stream switches — the review will ask.

---

<a id="the-merge-gate-and-review"></a>

## 10. The merge gate and review

Every orchard PR passes six checks, with no maintainer override:

1. **Lint** — schema validity plus policy (SPDX license, `min_os` accuracy, dependency rules, variant ABI tags).
2. **Matrix build** — your package built in the sandbox on every declared flavor, at your declared `min_os`.
3. **Smoke runs** — your `tests.star` across every release from `min_os` through 12.
4. **ABI gate** — on version/revision changes to anything others depend on: interface regressions require an explicit version bump or scheduled dependent rebuilds in the same snapshot.
5. **Graft rehearsal** — for a binary package declaring grafts (§8): the farm rehearses each graft in a per-OS VM on every OS the artifact targets, diffs the observed writes, kext loads, daemon installs, and network access against your declared behavior manifest, and fails the PR on any deviation or under-declaration. A package without grafts skips this gate entirely.
6. **Post-merge-only signing** — slices are signed after merge, never before, so a PR can never smuggle a signed artifact around review.

Run the gates before opening the PR: `aslice orchard ci <pkg>` executes the same harness the farm runs — lint, per-flavor sandboxed builds at `min_os`, the smoke test, the ABI diff, graft rehearsal on your OS — minus the cross-OS VM tier, which it marks deferred rather than fakes (§12).

What reviewers look for, beyond the gates: whether the description is accurate; whether the variant ABI tags name the real interface changes; whether the patches are documented — every file in `patches/` gets a header comment saying what it does, why it is needed, and whether it went upstream; whether `min_os` is what you actually tested; and whether the formula does anything *clever*. Cleverness in a declarative system is usually a policy violation wearing a trench coat.

A word on tone. The project has no code-of-conduct document, deliberately; the expectation is simpler and older — be decent to each other. Review here is direct. A formula with a problem will be told it has a problem, and you are expected to hear that as information about the formula, not about you. Dish it out the same way. [CONTRIBUTING.md](../CONTRIBUTING.md) carries the expectation in the open, along with commit style, sign-off, and the PR template.

---

<a id="publishing-your-own-orchard-and-repository"></a>

## 11. Publishing your own orchard and repository

Everything the project uses, you can run yourself:

```sh
aslice repo build ./my-orchard        # orchard (git formulae) → repository tree
aslice repo sign ./repo               # apply your keys
aslice repo publish ./repo            # push to your transport — static hosting is enough
```

A repository is a static, signed tree. Any web server, GitHub Pages, or a `file://` directory on a lab NAS can host one. You produce it with the same `repo build` pipeline the project runs in CI. Users add it with `aslice repo add <url>`, which pins your signing key's fingerprint on first use.

Your repository arrives as **third-party**: your formulae can trigger sandboxed local builds, your signed binaries can install after the user enables them, and the privileged categories (root daemons, kexts, `[system-patch]`) are closed to you by construction. **Verified** status — the project's countersignature — lifts a repository to shipping listed-but-disabled with the privileged categories available. Note that it is granted to maintainers, not to repositories: sustained, reviewable track record first. The full capability matrix is [REPOSITORIES §3](REPOSITORIES.md#trust-levels); the countersigning scheme is §5.

If you mirror the official repository instead of authoring your own, mirror the whole tree, sources included. The blob archive is the difference between a mirror that is a copy of outputs and one that is a survival copy of the orchard's inputs.

---

<a id="maintaining-the-orchard"></a>

## 12. Maintaining the orchard

One formula at a time is chapters 2–11. The whole orchard — keeping every formula lint-clean, fresh, and coherently versioned — has its own command group: `aslice orchard`. The commands work on a local checkout: pass `[path]`, or run them from inside the tree and the orchard is discovered for you. Anything that changes a formula ends as a PR — edited, validated, and linted by the command, the same contract as `aslice bump-pr`.

**Lifecycle.** Deprecations and removals are edits to the formula's `[deprecation]` table (§7.2 walks the policy), and the group edits them for you:

```sh
aslice orchard deprecate ffmpeg --reason upstream-eol --replacement ffmpeg7 \
    --date 2027-03-01 --disable-date 2027-09-01
aslice orchard disable ffmpeg        # installs refuse from today; existing installs untouched
aslice orchard rename ffmpeg ffmpeg7 # deprecate-as-renamed, scaffold the successor
aslice orchard tombstone ffmpeg      # the formula leaves HEAD; the index tombstone is forever
aslice orchard undeprecate ffmpeg    # rescind
```

Dates are validated in order, a `renamed` deprecation refuses to ship without a resolving `replacement`, and a tombstone refuses a name that still has dependents. The security fast path — straight to disabled, by owner approval during single-owner launch — is `deprecate --reason security --disable-date <today>`: the approval is recorded in the PR, and the command keeps the mechanics honest.

**Health.** `aslice orchard doctor` is the orchard-side counterpart of the machine doctor: lint clean across the tree, every core formula carrying `tests.star` and a working `[livecheck]`, deprecation chains coherent, patches documented, maintainers named — each finding with a stable check ID and the remedy spelled out, `--json` for scripts. `aslice orchard lint` is the tree-wide version of the per-formula lint you already run. `aslice orchard freshness` runs every livecheck and ranks packages by days-behind-upstream, worst first — the number the farm dashboard publishes ([ORCHARD-POLICY §9](ORCHARD-POLICY.md#freshness-livecheck-and-autobump)), so you see the dashboard's input, not its summary.

**The gate, before the farm.** `aslice orchard ci ffmpeg` runs the locally executable checks from chapter 10: lint, a sandboxed build per declared flavor at `min_os` where the host is capable, the smoke test, the ABI diff against the published index, and graft rehearsal on your OS. It reports required coverage that the host cannot execute as deferred to the farm. A successful local run neither merges the PR nor waives farm gates, including cross-OS tests and required independent rebuilds. Signing remains post-merge. Run it bare on a PR branch to scope to the changed formulae; `--all` is the whole orchard and warns you what that costs.

**Blast radius.** Before bumping a library, ask what breaks:

```sh
aslice orchard dependents x264 --transitive
```

Reverse dependencies, marked by whether they link the package's ABI (rebuild candidates) or merely exec the tool. The farm's dependent-rebuild cascade runs this same query server-side; running it yourself turns gate 4's "scheduled dependent rebuilds" from a surprise into a plan.

And when the package you want already exists in Homebrew: `aslice orchard port --from-homebrew <formula>` translates the simple Ruby formulae mechanically — named *port* because the rest genuinely are ports. You review the draft, fill in what only a human knows, and chapter 2 takes it from there.

---

## Appendix. The author's checklist

Before opening the PR:

- [ ] `aslice lint` clean — the same checks CI runs
- [ ] `aslice build` on every flavor you declare, at your declared `min_os`
- [ ] `aslice test` passes — and the test exercises the package's function, not just its presence
- [ ] `min_os` is the floor you actually tested, not the floor you hope for
- [ ] Every `abi = true` variant names the interface it changes
- [ ] Every patch has a header: what, why, upstream status
- [ ] `[livecheck]` present and tested (`aslice livecheck`)
- [ ] Dependencies are aslice packages — no `/usr/lib`, no vendored copies, no build-time downloads
- [ ] Vendor binaries: signer pinned (or `signer` omitted — extended only, per [ORCHARD-POLICY §12](ORCHARD-POLICY.md#vendor-binary-packages-pkgdmg)), OS tags verified, `redistribute` decided deliberately — hosted slice (`true`) or pointer formula (`false`)
- [ ] Grafts, if any: every script declared with its sha256 and a complete behavior manifest (`writes`/`kexts`/`daemons`/`network`, empty meaning none), rehearsed locally until observed behavior matches the manifest (§8)
- [ ] The description would make sense to someone who has never heard of the software

Or the first three and the ABI check at once: `aslice orchard ci <pkg>` — chapter 10's gates, run on your machine before the farm runs them (§12).

## History

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v0.14 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v0.13 | September 2026 | resolve build-flag, protected-execution, i386-ceiling, and local/farm coverage conflicts using STATE-AND-RECOVERY, SYSTEM-VOLUMES, and BUILD-INFRA. Replace unconditional compatibility and farm-success claims with their evidence and capability gates. |
| v0.12 | September 2026 | prose rewrite of the iteration guidance, formula introduction, and repository publishing explanation; no content changes. |
| v0.10 | Not recorded | prose review pass — a meta-announcement folded (§2.2) and a throat-clearing lead-in removed (§11); gems kept deliberately ('If you can't hash it, you can't ship it', 'not the project that dies, but its hospitality', 'a policy violation wearing a trench coat'); no guidance changes |
| v0.9 | Not recorded | grafts — §8 gains the declared-graft authoring path: extract the script, pin its hash, write the behavior manifest from evidence, rehearse locally until observed behavior matches the declaration (schema PACKAGE-FORMAT v0.15 §3.11; model DESIGN v1.19 §12.15; acceptance ORCHARD-POLICY v1.7 §12); §1's no-code principle gains the graft nuance, the appendix checklist gains the graft line, and §10's merge gate becomes six checks with graft rehearsal as gate 5 (matching ORCHARD-POLICY v1.7 §10), §12's local-gate description following; no other guidance changes. |
| v0.8 | Not recorded | §5.3 drops the variant cap — guidance now matches ORCHARD-POLICY v1.5: variants are governed by need and honest ABI tags, ffmpeg-class combinations are legitimate, and non-default variants build locally at no project cost; §10's lint list and reviewer guidance and the appendix checklist replace cap-and-justification language with the ABI-tag check; §8 and the checklist drop the license framing around `redistribute` — the flag selects hosting mode (ORCHARD-POLICY v1.5 §12). |
| v0.7 | Not recorded | adds chapter 12, **Maintaining the orchard** — the `aslice orchard` command group (lifecycle verbs over `[deprecation]`, orchard `lint`/`doctor`/`freshness`, the local merge gate `orchard ci`, the reverse-dependency query `orchard dependents`, and the named Homebrew importer `orchard port --from-homebrew`); pointers added from §7.1, §10, and the appendix checklist; mechanism in DESIGN v1.16 §12.14; no guidance changes elsewhere. |
| v0.6 | Not recorded | NOMENCLATURE.md vocabulary reference added to the header; no guidance changes. |
| v0.5 | Not recorded | review pass — the source-archive reference retargeted to DESIGN §9.6 and the countersigning reference to REPOSITORIES.md §5; no guidance changes. |
| v0.4 | Not recorded | prose rewrite throughout — chapters reworded in the project's technical-writing voice; no guidance changes. |
| v0.3 | Not recorded | editorial pass — prose revised for directness; no guidance changes. |
| v0.2 | Not recorded | review corrections — §8's payload map uses the real `[[binary.payload]]` array-of-tables shape, the invented `ctx.dep_lib_dirs` helper becomes the documented `ctx.deps` path, the service/root-daemon gate includes local repositories (§9), and the unsigned-vendor extended-only exception is recorded (§8, appendix). |
| Not recorded | September 2026 | corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending. |
| v0.15 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |

</details>
