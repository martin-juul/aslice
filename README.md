# aslice

A package manager for Intel Macs running macOS 10.11 (El Capitan) through 12 (Monterey) — every 64-bit Intel Mac, from the 2007 Core 2 Duo machines to the final Intel models of 2020. It is a successor-in-spirit to Homebrew, for the platform Homebrew is leaving behind.

- **Prebuilt binaries ("slices")** for the three microarchitecture flavors: v1 (x86-64 baseline), v2 (SSE4.2/POPCNT), v3 (AVX2). Hosted on GitHub, with a mirror-friendly fallback.
- **User-selectable build flags and variants.** Compile your own without losing interoperability with the prebuilt packages; substitution is checked against the recorded ABI contract, not against provenance.
- **Vendor binary packages.** Software that only ships as a `.pkg` or `.dmg` installs payload-only: installer scripts never run. 32-bit and universal payloads are supported on 10.11–10.14, the last releases that execute them.
- **Third-party repositories.** Anyone can publish a signed, static repository of recipes and slices. aslice ships with an official source list, inherent trust levels (official / verified / third-party / local), and both Ed25519 and OpenPGP signature schemes.
- **A stronger security model.** Declarative formulae, sandboxed builds, TUF-signed metadata, no package code at binary install time, no sudo in steady state.
- **A stronger performance model.** Single C++20 binary, sub-10 ms startup, parallel solver and downloads, zstd payloads, atomic generations with rollback.
- **Declarative whole-machine setup.** One `setup.toml` holds packages, runtime streams, services, macOS `defaults` preferences, and the login shell. `aslice apply` takes a Mac fresh from system recovery to ready-to-work in one command; `aslice export` captures an existing machine back into the file, so setups can be shared in a common format.
- **No telemetry.** aslice collects no metrics or analytics of any kind. It is infrastructure, not a product.

## Vocabulary

- **slice** — a binary package (`*.slice`)
- **orchard** — a formula repository (what Homebrew calls a tap)
- **repository** — a signed, static distribution tree of recipes and slices, hostable by anyone (GitHub, a mirror, a thumb drive)
- **flavor** — microarchitecture target: `v1` (SSE2 baseline), `v2` (SSE4.2/POPCNT), or `v3` (AVX2)

## Status

Design phase.

## Documents

- [Design document](docs/DESIGN.md): architecture, platform matrix, distribution, security model, roadmap
- [Package format specification](docs/PACKAGE-FORMAT.md): `package.toml` schema, dependency semantics, versioning, lock files, build API
- [Homebrew comparison & gap review](docs/HOMEBREW-REVIEW.md): feature-by-feature review against Homebrew 7.0, what is missing, and the resulting spec amendments
- [Build infrastructure](docs/BUILD-INFRA.md): the build farm and the `aslice build` / `aslice farm` harness — one pipeline, identical on the farm and on a user's Mac
- [Repositories](docs/REPOSITORIES.md): the shipped official source list, repository trust levels, and the dual Ed25519/OpenPGP signing model
- [Orchard policy](docs/ORCHARD-POLICY.md): the maintainer rulebook — acceptance bars per tier, variant discipline, deprecation lifecycle, patch documentation, merge gates, release cadence
- [Declarative system setup](docs/SETUP.md): the `setup.toml` schema and `aslice apply` / `export` / `import --from-brewfile` — rebuild a Mac from one file, or capture one into it

## Scope

- macOS 10.11 through 12, Intel x86_64 only. aslice-built slices are 64-bit; 32-bit vendor payloads install on 10.11–10.14, the releases that still execute them.
- No Apple Silicon, no macOS 13+ targets.
