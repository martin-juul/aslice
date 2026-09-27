# aslice

aslice is a package manager for Intel Macs running macOS 10.11 (El Capitan) through 12 (Monterey) — every 64-bit Intel Mac, from the 2007 Core 2 Duo machines through the final Intel models of 2020.

These machines still work. What stopped working is the software supply around them: Apple no longer ships them security updates, and Homebrew, the package manager most of them run, has moved on to Apple Silicon. aslice specifies a software supply for that fixed platform, with maintained packages, reproducible inputs, and explicit recovery contracts.

What you get:

- **Prebuilt binaries, called slices,** for three microarchitecture flavors: `v1` (the SSE2 baseline every 64-bit Intel Mac meets), `v2` (SSE4.2/POPCNT), and `v3` (AVX2). aslice detects your CPU once, at install time, and the resolver picks the best flavor your machine can run. Slices are hosted on GitHub, in a layout any mirror can copy.
- **Your own build flags, without leaving the binary world.** Variants that change a library's ABI are part of the package identity, so a self-compiled ffmpeg still substitutes correctly into a prebuilt dependency tree; variants that don't change the ABI cost nothing.
- **Vendor binaries, installed safely.** Software that ships only as a `.pkg` or `.dmg` is installed by extracting the payload, and installer scripts never run silently — where one is genuinely required (audio DSP drivers, pro-video plugins), it ships as a declared *graft*: hash-pinned, approved by you per package after its declared behavior is shown, sandboxed to that declaration, and rehearsed by the build farm in the official orchards. This includes 32-bit and universal binaries on 10.11–10.14, the last macOS releases that execute them.
- **A security model sized to a platform that gets no more patches.** Formulae are declarative, farm builds run in disposable VMs with sandboxed phases, the index is TUF-signed, installing a binary executes no undeclared package code, and nothing needs sudo in steady state.
- **Speed as a design constraint.** One C++20 binary, an unmeasured sub-10 ms startup target, efficient solving and parallel downloads, zstd payloads, and atomic generations you can roll back. [Benchmark workloads](docs/DESIGN.md#performance-model) define how these targets will be measured.
- **The whole machine in one file.** `aslice-machine.toml` records packages, runtime versions, services, macOS `defaults` preferences, and the login shell. `aslice machine apply` uses that file to take a Mac from fresh out of recovery to ready for work in one command. `aslice machine export` captures an existing setup in the same format for sharing and comparison.
- **No telemetry.** aslice collects nothing — no metrics, no analytics, no opt-out to go looking for. It is infrastructure, not a product.

## Vocabulary

Four words carry most of the design:

- **slice** — a binary package (`*.slice`).
- **orchard** — a formula repository; what Homebrew calls a tap.
- **repository** — a signed, static distribution tree of formulae and slices. Anyone can host one: on GitHub, on a mirror, on a thumb drive. Trust attaches to the repository rather than to individual packages, at four levels — official, verified, third-party, local — each with a defined set of capabilities. Signatures are Ed25519; OpenPGP is supported for publishers with an existing GPG workflow.
- **flavor** — a microarchitecture target: `v1`, `v2`, or `v3`, as above.

Every other term the documents use is defined in [NOMENCLATURE.md](docs/NOMENCLATURE.md).

## Status

Early prototype. The C++20 CLI implements help, version reporting, and offline
`aslice db schema` for all six database roles. `aslice dev fixture` exercises a local
fixture package lifecycle: resolve, install, execute, upgrade, roll back, and
remove. Portable commands also normalize and compare versions, resolve dependency
ranges, validate artifact manifests and payloads, and pack or inspect bounded
unsigned `.slice` containers. These commands run in native Windows CLion builds
as well as Docker. Production package installation and live database commands remain
unimplemented. The documents below remain the
specification; there is no release to install yet. The project lives at
[aslice.sh](https://aslice.sh) — the documentation will be served at
[aslice.sh/docs](https://aslice.sh/docs), and the installer will come from
[get.aslice.sh](https://get.aslice.sh/install.sh) once a release exists.

Build and try the prototype with Docker Desktop using Linux containers:

```sh
docker build -t aslice-prototype .
docker run --rm aslice-prototype --help
docker run --rm aslice-prototype db schema --role client-state
docker run --rm --network none --entrypoint sh aslice-prototype /src/tools/demo-prototype.sh
docker run --rm --entrypoint ctest aslice-prototype --test-dir /build --output-on-failure
```

The image uses LLVM 22 and libc++, checks formatting and analysis, and runs tests, including loading each
emitted schema into SQLite. Linux is a development host for this portable code;
these tests do not establish macOS compatibility. See the
[prototype build guide](docs/runbooks/PROTOTYPE.md) for local builds and limits.

## License

Original project material is licensed under [Apache-2.0](LICENSE). Third-party material retains its own license and attribution.

## Documents

- [Complete documentation index](docs/README.md) — reading paths and the full catalog.
- [Developer guide](docs/DEVELOPING.md) — the development CLI, simulator application, tests, packaging, and build-state preservation.
- [User manual](docs/MANUAL.md) — installing and using aslice.
- [Authoring guide](docs/AUTHORING.md) — writing, testing, and shipping packages.
- [Architecture and design](docs/DESIGN.md) — platform, architecture, security model, and roadmap.
- [Contributing guidelines](CONTRIBUTING.md) — proposing changes and running checks.
- [Project structure](STRUCTURE.md) — repository organization and planned C++ layout.

## Scope

- macOS 10.11 through 12, Intel x86_64 only. aslice-built slices are 64-bit; 32-bit vendor payloads install on 10.11–10.14, the releases that still execute them.
- No Apple Silicon, no macOS 13+, no Linux. The narrow target is what buys the properties above: the resolver, the ABI model, and the build farm all assume a platform that no longer changes, and every hour that would have gone to chasing a moving target goes to the packages instead.

---

Security updates and restart reporting are specified in
[aslice-upgrade(1)](man/aslice-upgrade.1.md) and
[aslice-needs-restarting(1)](man/aslice-needs-restarting.1.md). A newer eligible
source-only update requires disclosed compilation and execution consent. Runtime
remediation, farm qualification, and benchmarks remain pending.

## History

<details>
<summary>Document revision history</summary>

| Date | Changes |
|---|---|
| 2026-09-27 | Establish typed C++ boundaries, command registry help, and mandatory formatting, analysis, and sanitizer checks; retain fixture wire identities. |
| September 2026 | Split source by subsystem; add portable version constraints, manifest/payload verification, and unsigned slice packing and inspection. |
| September 2026 | Add the disposable package lifecycle experiment and native CLion/MinGW development dependencies. |
| September 2026 | Add the first C++ CLI prototype and Docker build instructions; macOS runtime acceptance remains pending. |
| September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| September 2026 | prose review pass: the second paragraph's tail straightened (one sentence instead of two; the *how* stays in Scope); gems kept deliberately ('These machines still work', 'infrastructure, not a product', 'on a thumb drive'); no content changes. |
| September 2026 | grafts: vendor installer scripts are admitted as declared, user-approved, farm-rehearsed grafts rather than never running (owner decision); the vendor-binary and security bullets updated. |
| September 2026 | rewritten for readability (second editorial pass); no content changes. |
| September 2026 | NOMENCLATURE.md added to the document list; vocabulary pointer added. |
| September 2026 | project domain (aslice.sh) linked in Status. |
| September 2026 | the declarative-setup file renamed `aslice-machine.toml`, its commands grouped under `aslice machine` (apply / export / import --from-brewfile); top-level `aslice apply` keeps plans and lock files (owner decision). |
| September 2026 | TOOLCHAIN.md added to the document list. |
| September 2026 | prose rewrite of the introduction and machine-setup overview; no content changes. |
| September 2026 | Add the helpers and background services reference to the documentation index; no runtime changes. |
| September 2026 | Link the repository structure guidelines and planned C++ layout. |
| September 2026 | Simplify README navigation and add docs/README.md with reading paths, a complete document catalog, and supporting resources. |
| September 2026 | Specify security-update and restart-reporting interfaces; mark performance targets unmeasured and farm execution disposable. |

</details>
