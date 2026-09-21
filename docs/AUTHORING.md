# aslice Authoring Guide

**How to write, test, and ship aslice packages.**

- **Status:** v0.3 — September 2026 (v0.2: review corrections — §8's payload map uses the real `[[binary.payload]]` array-of-tables shape, the invented `ctx.dep_lib_dirs` helper becomes the documented `ctx.deps` path, the service/root-daemon gate includes local repositories (§9), and the unsigned-vendor extended-only exception is recorded (§8, appendix). v0.3: editorial pass — prose revised for directness; no guidance changes)
- **Audience:** package authors — people writing formulae for the core or extended orchards, packaging vendor binaries, or running their own orchard. Read [MANUAL.md](MANUAL.md) chapters 1–4 first; this guide assumes the vocabulary (slice, orchard, flavor, generation) and the user's view of the system.
- **Companions:** [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) is the authoritative schema — when this guide and the schema disagree, the schema is right. [ORCHARD-POLICY.md](ORCHARD-POLICY.md) is the policy this guide summarizes. [BUILD-INFRA.md](BUILD-INFRA.md) is the farm your PR builds on. [MANUAL.md](MANUAL.md) is what your users read.

---

## 1. Overview

An aslice package is a directory in an orchard — a git repository of package directories. Four files, two of them optional:

```
orchards/core/ffmpeg/
 ├── package.toml      # metadata, sources, dependencies, variants — pure data
 ├── build.star        # the build script — Starlark, sandboxed
 ├── patches/          # optional, every file checksummed
 └── tests.star        # optional smoke tests — required for core
```

Two rules carry the whole security model, and everything in this guide follows from them:

1. **`package.toml` is data, and binary installs run no code at all.** When a user installs your package from a slice, nothing of yours executes — no install hooks, no scripts, ever. Your `build.star` runs only when the package is *built* — on the farm, or on a user's machine when they ask for a source build — and it runs inside a sandbox with no network and no filesystem access outside the build directory.
2. **Everything is pinned.** Source URLs carry sha256 hashes; patches are checksummed; the index countersigns the closure. If you can't hash it, you can't ship it.

When you open a PR against an orchard, the farm lints your formula, builds it in the sandbox on every flavor it declares, runs your smoke tests across the supported OS range, and checks that your change doesn't break the published interface of anything that depends on it. Only then does a human review it — review is about correctness and policy, never "does it compile," because CI already answered that. After merge, the signing machine signs the new slices, and the index publishes them in the next snapshot.

The journey is: **your PR → lint → matrix build → smoke tests → ABI gate → human review → merge → sign → publish.** This guide walks the parts you control.

---

## 2. Your first package

### 2.1 Scaffolding

```
aslice create https://example.org/releases/foo-1.2.tar.gz
```

`create` downloads the archive, hashes it, sniffs the build system (autotools, CMake, Meson), and emits a formula directory with a draft `package.toml` and `build.star`. The draft is a starting point, not a finished package — review every field it guessed. Then fill in the things only you know: the description, the license, `min_os`, and the livecheck block (§7).

### 2.2 Building it locally

```
aslice build foo                  # builds in the same sandbox the farm uses
aslice test foo                   # runs tests.star against what you built
aslice install ./foo              # install your local build into your profile
```

`aslice build` on your machine is the *identical* pipeline the farm runs — same phases, same sandbox profiles, same environment scrubbing. If it builds for you, it builds on the farm; "works on my machine" is a property of the harness, not a hope. One caveat worth naming: the farm builds against the pinned `aslice-toolchain`, and a formula that quietly depends on your local Xcode CLT will fail there. The sandbox blocks undeclared toolchains, so you'll find out immediately, with an error naming what it tried to use.

### 2.3 The iteration loop

Edit, `aslice build`, `aslice test`, repeat. When the package does what the description says, run the linter the way CI runs it:

```
aslice lint foo                   # the same schema + policy checks as the merge gate
```

Then open the PR. The rest of this guide is how to make each of those steps boring.

---

## 3. package.toml, section by section

A complete-but-reasonable formula, annotated. The schema reference for every field is PACKAGE-FORMAT.md; this is the guided tour.

```toml
[package]
name        = "ffmpeg"
version     = "7.1"
revision    = 0             # bump when the formula changes but upstream doesn't
license     = "LGPL-2.1-or-later"    # SPDX identifier — the linter checks
description = "Play, record, convert, and stream audio and video"
homepage    = "https://ffmpeg.org"
min_os      = "10.13"       # the oldest release this formula actually supports
```

**Declare the floor you tested.** Many modern codebases can't cleanly target 10.11 — C++17 library features, `clock_gettime`, `thread_local` quirks. A package that claims 10.11 and fails there is far worse than one that says 10.13. CI smoke-runs your package on every release from your declared `min_os` through 12, so an optimistic floor is a failing build, not a secret.

```toml
[source]
url    = "https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz"
sha256 = "40973d449e3c3a4a551b3e2e05f5a28f8ff74a2f2e0c2e6ec4f7f4b9c0f2a1c9"
mirrors = ["https://mirror.example.org/ffmpeg-7.1.tar.xz"]   # optional
```

The hash is the contract. A client fetches from the canonical URL, then your `mirrors`, then the repository's own blob archive — the farm deposits every source it ever fetched there — and all three are verified against the same pinned sha256. Two consequences. First, upstream reorganizing its download site doesn't break your package for anyone: the archive still serves the source. Second, a hash mismatch is a hard failure everywhere, which is what you want — it's the only thing standing between your users and a re-rolled tarball.

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

Variants are the package's options; `abi = true` means "enabling or disabling this changes the interface my consumers link against," and it's the most consequential line in the file — §5 is about getting it right. Dependencies are aslice packages, never system libraries: on this platform the OS's bundled libraries *are the problem being solved*, so a formula that links `/usr/lib/libssl.dylib` is a lint error, not a shortcut. The enumerated exceptions are always-present system *frameworks* (`Accelerate`, `CoreAudio`, …) — the platform's ABI — and adding to that allowlist is a policy PR, not a formula decision.

```toml
[livecheck]
url    = "https://ffmpeg.org/download.html"
regex  = "ffmpeg-([0-9.]+)\\.tar\\.xz"
```

Livecheck is how the orchard notices new upstream releases without watching anyone's machine — §7. Core-tier formulae are expected to have one.

---

## 4. build.star: the build script

`build.star` is Starlark — Python-shaped, deterministic, no `eval`, no recursion — executing inside the build sandbox. You write phase functions; the harness calls them in order; the `ctx` object is your entire world.

```python
def configure(ctx):
    args = [
        "--prefix=" + ctx.prefix,
        "--enable-gpl",
        "--enable-libx264",
    ]
    if ctx.variant("x265"):
        args.append("--enable-libx265")
    ctx.env.append("CFLAGS", ctx.user_cflags)   # user flags: honored, recorded, never identity
    ctx.run("./configure", *args)

def build(ctx):
    ctx.make(jobs = ctx.jobs)

def install(ctx):
    ctx.make("install", destdir = ctx.staging)
```

### 4.1 What the sandbox means in practice

- **No network.** Not "restricted network" — none. If your build downloads a dependency, vendor it as an additional `[source]` entry with its own hash, or package it separately and depend on it. Builds that phone home fail; this is a feature, and it's why aslice can promise users that building from source doesn't widen their trust surface.
- **Writes stay in the build directory.** The toolchain and the store are read-only to you. Install into `ctx.staging` (DESTDIR-style), never into the prefix — the harness assembles the store path from your staging tree.
- **The environment is deterministic.** Locale, timezone, `PATH`, and compiler flags are set by the harness. If your build embeds timestamps or host paths, it may build unreproducibly — which matters when the farm's second builder tries to bit-match your slice.
- **The phases are fetch → unpack → patch → configure → build → install → test**, each with its own sandbox profile. Patches live in `patches/`, are checksummed, and are applied by the harness — your script never shells out to `patch`.

### 4.2 The ctx object, by group

- **Paths:** `ctx.prefix` (where the package will live), `ctx.staging` (install target), `ctx.build_dir`, `ctx.jobs`.
- **Configuration:** `ctx.variant("name")` for variant state, `ctx.user_cflags` / `ctx.user_ldflags` for the user's optimization flags — always append them where the build system expects them; they're recorded in the manifest for provenance but never change the package's identity (§5.2).
- **Execution:** `ctx.run(...)`, `ctx.make(...)`, `ctx.env` — the full capability set. There is no general subprocess escape; if you need a tool, it's a build dependency.
- **Platform facts:** the target OS floor and flavor. Gate workaround code on these, not on probing the build host — the farm builds every declared combination, and host-probing is how formulas lie.

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

The pattern to internalize: **dependencies come from aslice, and you say so explicitly.** Vendored copies, downloads at build time, and "the system probably has it" are the three ways formulae rot; the sandbox rejects all three, so lean into it.

---

## 5. Variants and the ABI contract

### 5.1 The one decision that matters

Every variant you declare answers one question: *does flipping this change what my consumers link against?*

- Enabling `x265` in ffmpeg adds an encoder that applications link to — the exported interface changes. `abi = true`.
- Debug symbols change the bits, not the interface. `abi = false`.
- Optimization flags users pass (`-O3`, `-march=native`) are never even variants — they're recorded provenance, and never affect identity at all.

Mark a variant `abi = true` and it becomes part of the package's build identity: `ffmpeg+x265` and `ffmpeg-x265` are different builds that coexist in the store, and dependents record which they linked against. Mark it `false` and flipping it just triggers a local build of the same identity.

### 5.2 What the ABI scan does with this

When your package builds, the harness scans the staged output and records the interface in the manifest: every dylib's install name and compatibility version, a symbol-set fingerprint, and what the package requires from others. The solver substitutes packages — farm-built, user-built, any variant — purely on whether a provider's recorded interface covers a consumer's recorded requirements. Your job is only to keep the *declaration* accurate:

- **If a version bump changes the exported interface** (soname bump, dropped symbols), the ABI gate in CI compares your build against the published one and fails the PR unless the version reflects it — an explicit version bump, or scheduled rebuilds of the dependents in the same snapshot. "It'll probably be fine" is what the gate exists to prevent.
- **If you're unsure whether a variant changes the interface,** build both ways and compare `aslice build --emit-abi` output. The scan is ground truth; declare what you measured.

### 5.3 Discipline

`abi = true` variants are capped per package (guideline: six) and each must justify itself in review. This is the lesson of Homebrew's option sprawl, learned in advance: every interface-changing variant multiplies the build matrix and the support surface. A variant that two users might want belongs in their local `--cflags`, not in the orchard. Build-flavor variants (`abi = false`) are uncapped because they spawn no binaries — but each still needs a reason to exist.

---

## 6. Tests

`tests.star` runs after install, in the build sandbox, against the staged result:

```python
def test(ctx):
    ctx.run(ctx.prefix + "/bin/ffmpeg", "-version")
    ctx.run(ctx.prefix + "/bin/ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-f", "null", "-")
```

A good smoke test proves the package *works*, not merely that it exists: encode a second of video, serve a request, round-trip a document. Running the binary with `-version` catches broken linkage and missing dylibs — the most common real failure — but a test that exercises the package's actual function catches the next five most common. Core tier requires a working smoke test on at least one OS × one flavor; CI runs yours across the whole supported range from your `min_os` through 12.

Users can run your tests too, any time: `aslice test ffmpeg` executes them against the installed slice. Write them to be safe to run on a user's machine — read-only outside a temp directory, no network by default. If a test genuinely needs the network, declare `test_network = true` in the formula and accept the scrutiny in review.

---

## 7. Keeping it fresh

### 7.1 Livecheck and autobump

The `[livecheck]` block tells the orchard's scheduled job where to look for newer releases. When one appears, the orchard opens a bump PR automatically — formula edited, hash recomputed, CI running — and a maintainer reviews it like any other change. Humans do the same thing by hand with `aslice bump-pr foo 7.2`: edit, lint, smoke-build one flavor, open the PR. Users can check any package with `aslice livecheck foo`.

Write livecheck blocks against pages the upstream actually maintains — the download listing, the release feed — and prefer a regex that can't silently match a prerelease. A livecheck that matched "7.2rc1" as newer than "7.1" ships a release candidate to users who didn't ask for one.

### 7.2 When upstream dies

Upstreams on this platform die in a specific way: not the project, but its hospitality — the download page reorganizes, old tarballs vanish, the domain expires. When your formula's canonical URL dies:

1. **Nothing already built breaks.** Every source the farm fetched is archived in the repository's own blob store, hash-pinned; clients fetch it from there when the URL 404s. Your package keeps working while you fix the formula.
2. **Note the death in the formula.** A comment naming the date and the mirror situation, so the next maintainer knows the context without archaeology.
3. **Point the formula at a living mirror** if one exists, or let it ride the archive and adjust livecheck — or, if the upstream is truly gone, move the package toward the archive track per ORCHARD-POLICY §8.

This archiving is policy, not luck (ORCHARD-POLICY §9): dead-upstream software is half the reason this orchard exists.

---

## 8. Vendor binaries

Some software will only ever ship as a `.pkg` or `.dmg` — commercial audio tools, vendor CLIs, frozen releases of abandoned apps. Package it as `type = "binary"` and aslice installs it without ever executing the vendor's installer scripts.

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

(Payload maps are an array of tables — `from`/`to` pairs — per PACKAGE-FORMAT §3.11. When this guide and the schema disagree, the schema is right.)

The rules, and the reasons for them:

- **Only the payload installs.** `preinstall`/`postinstall` scripts are never executed. If the software genuinely requires its scripts, it doesn't belong in aslice; package what can be installed payload-only. Kexts and drivers are *not* excluded by this rule — they go through the declared `[system]` category (§9), where aslice's own helper performs the privileged steps from your declarations.
- **The signer is pinned.** If the vendor silently re-signs with a different identity, installs hard-fail. That's a classic supply-chain attack against binary distribution, and the pin is the whole defense — don't leave it out because "the vendor is trustworthy." The pin exists for the day they aren't, or their signing infrastructure is. The single exception is genuinely unsigned vendor software: permitted in the extended orchard only, with `signer` omitted and an announcement at every install (PACKAGE-FORMAT §3.11, ORCHARD-POLICY §12).
- **OS tags are verified or the formula doesn't merge.** Each `[[binary]]` entry declares its real `min_os`/`max_os`; the pack-time verifier checks your claims against the bundle's own metadata, and lint fails on mismatches. A vendor's "legacy 10.11 build" and "current 10.14+ build" coexist as two entries in one formula.
- **32-bit and universal payloads are welcome where the OS runs them** — 10.11 through 10.14. The verifier inspects every Mach-O slice in the payload; an i386-containing artifact must declare `max_os = "10.14"`. Universal payloads install whole — never thin them with `lipo`, because thinning invalidates the vendor's code signature, and the signature outranks the disk savings.
- **`redistribute` decides who fetches.** `true` — the farm repackages into a normal slice and hosts it (best user experience; requires the license to allow redistribution). `false` — the formula is a pointer, and each client fetches the vendor URL itself, hash- and signer-pinned. Core tier requires `true`: core never depends on a vendor's server being up.

---

## 9. Special categories

Four declaration blocks for packages that don't fit the ordinary mold. Each exists because the alternative was users doing the same thing by hand with no provenance and no rollback; each is gated accordingly.

**`[service]`** — the package runs a daemon. Declare argv, domain, keepalive, working directory, log paths; aslice generates and manages the launchd job. `domain = "user"` services are ungated; `domain = "system"` root daemons are gated to official, verified, and local repositories, because root execution is the privilege that matters.

**`[system]`** — kernel extensions and SIP-disabled development tools. Declare the kexts, whether SIP must be off, and a mandatory `reason` string that is shown verbatim in every warning to every installer. Official, verified, and local repositories may serve these; third-party never. Write the `reason` like the user will read it aloud before deciding — they will.

**`[system-patch]`** — the package replaces an Apple-provided file. Declare the target paths, the SIP requirement, the reason; aslice backs up the original to the byte, symlinks through the profile, and restores on demand. The strictest gate in the system: official and local only, verified only under an explicit per-repo grant, and a refused-by-construction target list (kernel, dyld, libSystem, `/System`, platform-binary dylibs) that no flag overrides. Expect the longest review of your formula's life. The package that replaces 10.11's 0.9.8-era `/usr/bin/openssl` earned its category; "I wanted to patch this plist" did not.

**`[extension]` / `[ride]`** — runtime-bound packages. A compiled extension (`php-redis`) declares `[extension] runtime = "php"` and binds to the runtime's ABI epoch — the farm builds it for every supported stream. A tool that runs *on* a runtime without compiling against it (composer, yarn) declares `[ride] runtime = "php"` and follows the user's stream selection. Whether a tool can safely ride is a fact about its code: if it links the runtime's libraries, it's an extension; if it merely needs the interpreter, it rides. Get this wrong and the tool breaks on stream switches — the review will ask.

---

## 10. The merge gate and review

Every orchard PR passes five checks, with no maintainer override:

1. **Lint** — schema validity plus policy (SPDX license, `min_os` accuracy, dependency rules, variant caps).
2. **Matrix build** — your package built in the sandbox on every declared flavor, at your declared `min_os`.
3. **Smoke runs** — your `tests.star` across every release from `min_os` through 12.
4. **ABI gate** — on version/revision changes to anything others depend on: interface regressions require an explicit version bump or scheduled dependent rebuilds in the same snapshot.
5. **Post-merge-only signing** — slices are signed after merge, never before, so a PR can never smuggle a signed artifact around review.

What reviewers look for, beyond the gates: is the description accurate; are the variants justified; are patches documented — every file in `patches/` gets a header comment saying what it does, why it's needed, and whether it went upstream; is `min_os` what you tested; does the formula do anything *clever* — cleverness in a declarative system is usually a policy violation wearing a trench coat.

On tone: the project has no code-of-conduct document, deliberately. The expectation is simpler and older — be decent to each other. Review is direct here: a formula with a problem will be told it has a problem, and you're expected to hear that as information about the formula, not about you. Dish it out the same way. [CONTRIBUTING.md](../CONTRIBUTING.md) carries the expectation in the open; it also covers commit style, sign-off, and the PR template.

---

## 11. Publishing your own orchard and repository

Everything the project uses, you can run:

```
aslice repo build ./my-orchard        # orchard (git formulae) → repository tree
aslice repo sign ./repo               # apply your keys
aslice repo publish ./repo            # push to your transport — static hosting is enough
```

A repository is a static, signed tree — any web server, GitHub Pages, a `file://` directory on a lab NAS can host one, and the same `repo build` pipeline the project runs in CI produces it, so your tree holds no magic the official one doesn't. Users add it with `aslice repo add <url>`, which pins your signing key's fingerprint on first use.

Understand what your repository *is* to its users: it arrives as **third-party** — your formulae can trigger sandboxed local builds, your signed binaries can install after the user enables them, and the privileged categories (root daemons, kexts, `[system-patch]`) are closed to you by construction. **Verified** status — the project's countersignature — lifts your repository to shipping listed-but-disabled with the privileged categories available, and it's granted to maintainers, not to repositories: sustained, reviewable track record first. The full capability matrix is REPOSITORIES.md §3; the countersigning process is §7.

If you mirror the official repository instead of authoring your own, mirror the whole tree — sources included. The blob archive is the difference between a mirror that's a copy of outputs and one that's a survival copy of the orchard's inputs.

---

## Appendix. The author's checklist

Before opening the PR:

- [ ] `aslice lint` clean — the same checks CI runs
- [ ] `aslice build` on every flavor you declare, at your declared `min_os`
- [ ] `aslice test` passes — and the test exercises the package's function, not just its presence
- [ ] `min_os` is the floor you actually tested, not the floor you hope for
- [ ] Every `abi = true` variant is justified in the PR description
- [ ] Every patch has a header: what, why, upstream status
- [ ] `[livecheck]` present and tested (`aslice livecheck`)
- [ ] Dependencies are aslice packages — no `/usr/lib`, no vendored copies, no build-time downloads
- [ ] Vendor binaries: signer pinned (or `signer` omitted — extended only, per ORCHARD-POLICY §12), OS tags verified, `redistribute` set by license, not convenience
- [ ] The description would make sense to someone who has never heard of the software
