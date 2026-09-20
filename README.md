# aslice

A package manager for Intel Macs — macOS 10.11 (El Capitan) through 12 (Monterey), from Core 2 Duo through Coffee Lake.

A successor-in-spirit to Homebrew for the platform Homebrew is leaving behind:

- **Prebuilt binaries ("slices")** for the common flavors (x86-64 baseline, SSE4.2, and AVX2 — the v1/v2/v3 flavors), hosted on GitHub with mirror-friendly fallback
- **User-selectable build flags and variants** — compile your own without losing interoperability with the prebuilt world (ABI-aware substitution)
- **Vendor binary packages & repositories** — software that only ships as `.pkg`/`.dmg` installed without ever running installer scripts, **including 32-bit and universal binaries** on 10.11–10.14 (the last macOS releases that run them); anyone can publish a signed, static repository — ships with an official source list, inherent trust levels (official / verified / third-party / local), and both Ed25519 and OpenPGP (GPG) signature schemes
- **A stronger security model** — declarative formulae, sandboxed builds, TUF-signed metadata, code-free binary installs, no sudo in steady state
- **A stronger performance model** — single C++20 binary, sub-10ms startup, parallel solver and downloads, zstd payloads, atomic rollback-capable generations
- **No telemetry, ever** — aslice collects no metrics or analytics of any kind; it is infrastructure, not a product

## Vocabulary

- **slice** — a binary package (`*.slice`)
- **orchard** — a formula repository (what Homebrew calls a tap)
- **repository** — a signed, static distribution tree of recipes and slices, hostable by anyone (GitHub, a mirror, a thumb drive)
- **flavor** — microarchitecture target: `v1` (SSE2 baseline), `v2` (SSE4.2/POPCNT), or `v3` (AVX2)

## Status

Design phase.

## Documents

- [Design document](docs/DESIGN.md) — architecture, platform matrix, distribution, security model, roadmap
- [Package format specification](docs/PACKAGE-FORMAT.md) — `package.toml` schema, dependency semantics, versioning, lock files, build API
- [Homebrew comparison & gap review](docs/HOMEBREW-REVIEW.md) — feature-by-feature review against Homebrew 7.0, what's missing, and proposed spec amendments
- [Build infrastructure](docs/BUILD-INFRA.md) — the build farm and the `aslice build` / `aslice farm` harness: one pipeline that runs identically on the farm and on any user's Mac
- [Repositories](docs/REPOSITORIES.md) — the shipped official source list, inherent repository trust levels, and the dual Ed25519/OpenPGP signing model
- [Orchard policy](docs/ORCHARD-POLICY.md) — the maintainer rulebook: acceptance bars per tier, variant discipline, deprecation lifecycle, patch documentation, merge gates, release cadence

## Scope

- macOS 10.11 through 12 — Intel x86_64 only (aslice-built slices are 64-bit; 32-bit vendor payloads install on 10.11–10.14, the releases that still execute them)
- No Apple Silicon, no macOS 13+ targets, by explicit design
