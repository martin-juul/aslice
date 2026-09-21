# aslice

aslice is a package manager for Intel Macs running macOS 10.11 (El Capitan) through 12 (Monterey) — every 64-bit Intel Mac, from the 2007 Core 2 Duo machines through the final Intel models of 2020.

These machines still work. What stopped working is the software supply around them: Apple no longer ships them security updates, and Homebrew, the package manager most of them run, has moved on to Apple Silicon. aslice picks up where Homebrew leaves off. It is a successor in spirit, rebuilt for a platform that will never change again — and that constraint, a burden on a moving platform, is what makes a cleaner design affordable here.

What you get:

- **Prebuilt binaries, called slices,** for three microarchitecture flavors: `v1` (the SSE2 baseline every 64-bit Intel Mac meets), `v2` (SSE4.2/POPCNT), and `v3` (AVX2). aslice detects your CPU once, at install time, and the resolver picks the best flavor your machine can run. Slices are hosted on GitHub, in a layout any mirror can copy.
- **Your own build flags, without leaving the binary world.** Variants that change a library's ABI are part of the package identity, so a self-compiled ffmpeg still substitutes correctly into a prebuilt dependency tree; variants that don't change the ABI cost nothing.
- **Vendor binaries, installed safely.** Software that ships only as a `.pkg` or `.dmg` is installed by extracting the payload; the vendor's installer scripts never run. This includes 32-bit and universal binaries on 10.11–10.14, the last macOS releases that execute them.
- **A security model sized to a platform that gets no more patches.** Formulae are declarative, builds run in a sandbox, the index is TUF-signed, installing a binary executes no package code, and nothing needs sudo in steady state.
- **Speed as a design constraint.** One C++20 binary, sub-10 ms startup, parallel solving and downloads, zstd payloads, and atomic generations you can roll back.
- **The whole machine in one file.** `setup.toml` holds packages, runtime versions, services, macOS `defaults` preferences, and the login shell. `aslice apply` takes a Mac from fresh-out-of-recovery to ready-to-work in one command; `aslice export` writes an existing machine back into the file, so setups can be shared and diffed.
- **No telemetry.** aslice collects nothing — no metrics, no analytics, no opt-out to go looking for. It is infrastructure, not a product.

## Vocabulary

Four words carry most of the design:

- **slice** — a binary package (`*.slice`).
- **orchard** — a formula repository; what Homebrew calls a tap.
- **repository** — a signed, static distribution tree of formulae and slices. Anyone can host one: on GitHub, on a mirror, on a thumb drive. Trust attaches to the repository rather than to individual packages, at four levels — official, verified, third-party, local — each with a defined set of capabilities. Signatures are Ed25519; OpenPGP is supported for publishers with an existing GPG workflow.
- **flavor** — a microarchitecture target: `v1`, `v2`, or `v3`, as above.

## Status

Design phase. The documents below are the specification as it stands; there is no release to install yet.

## Documents

In the order a newcomer should read them:

- [Design document](docs/DESIGN.md) — architecture, platform matrix, distribution, security model, roadmap
- [Package format specification](docs/PACKAGE-FORMAT.md) — the `package.toml` schema, dependency semantics, versioning, lock files, the build API
- [Homebrew comparison & gap review](docs/HOMEBREW-REVIEW.md) — a feature-by-feature review against Homebrew 7.0, what's missing, and the spec amendments it produced
- [Build infrastructure](docs/BUILD-INFRA.md) — the build farm and the `aslice build` / `aslice farm` harness: one pipeline, run identically by the farm and by any user's Mac
- [Repositories](docs/REPOSITORIES.md) — the shipped official source list, repository trust levels, and the dual Ed25519/OpenPGP signing model
- [Orchard policy](docs/ORCHARD-POLICY.md) — the maintainer rulebook: acceptance bars per tier, variant discipline, the deprecation lifecycle, patch documentation, merge gates, release cadence
- [Declarative system setup](docs/SETUP.md) — the `setup.toml` schema and `aslice apply` / `export` / `import --from-brewfile`: rebuild a Mac from one file, capture one back into it

## Scope

- macOS 10.11 through 12, Intel x86_64 only. aslice-built slices are 64-bit; 32-bit vendor payloads install on 10.11–10.14, the releases that still execute them.
- No Apple Silicon, no macOS 13+, no Linux. The narrow target is what buys the properties above: the resolver, the ABI model, and the build farm all assume a platform that no longer changes, and every hour that would have gone to chasing a moving target goes to the packages instead.

---

*History: September 2026 — rewritten for readability (second editorial pass); no content changes.*
