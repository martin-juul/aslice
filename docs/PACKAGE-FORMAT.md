# aslice Package Format

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

- **Status:** Format draft, v0.21 — September 2026
- **Companion to:** [DESIGN.md](DESIGN.md) — this document owns author input and the recipe API summarized in [DESIGN §6](DESIGN.md#package-format). [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md) owns identity, trust, and recovery; examples and schemas must agree. The toolchain this format's builds run on is specified in [TOOLCHAIN.md](TOOLCHAIN.md).
- **Scope:** the `package.toml` definition format, `build.star` build API, dependency and version semantics, transitive resolution, and lock files.
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md) — project terms, acronyms, and the Homebrew translation table.

---

Navigation: [1. Philosophy](#philosophy) · [2. Files of a package](#files-of-a-package) · [3. `package.toml` — full schema](#packagetoml--full-schema) · [4. Versioning](#versioning) · [5. Dependency semantics](#dependency-semantics) · [6. Build instructions](#build-instructions) · [7. Lock files](#lock-files) · [8. Validation and tooling](#validation-and-tooling) · [9. Worked examples](#worked-examples) · [Appendix. Field index](#appendix-field-index)

<a id="philosophy"></a>

## 1. Philosophy

The quickest way to describe this format is by contrast. npm's `package.json` has the same broad job — describe a package and its dependencies — so the differences, tabulated below, are the design of this format in miniature:

| npm convention | aslice decision | Why |
|---|---|---|
| `scripts.postinstall` — arbitrary code at install | **Does not exist as a formula mechanism.** Builds and binary installs execute zero package code by default; a vendor installer script runs only as a declared, approved, sandboxed graft (§3.11; [DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)) | npm's install scripts are its largest supply-chain hole; we start without one |
| Semver, loosely enforced | Semver-derived, **strictly normalized and validated** (§4) | A solver is only as good as its version algebra |
| `package-lock.json` | `aslice.lock`, first-class and machine-aware (§7) | Locks record µarch flavor — a dimension npm doesn't have |
| `dependencies` / `devDependencies` | `runtime` / `build` / `test`, plus **conditional** dependencies (§5.3) | Native builds have three distinct dependency lifecycles |
| Anything goes in unknown fields | Schema-validated, unknown fields **rejected** | Silent typos in package metadata are a real supply-chain bug class |
| Prebuilt native addons via `node-gyp`/prebuild-install (untyped blobs) | **Vendor binaries are first-class, typed packages** with OS-support tags and pinned signers (§3.11) | Half the software worth having on this platform will never be buildable from source |

The governing principle is **data first**. A `package.toml` is pure TOML: it can be validated, indexed, and audited without executing anything. Where a build needs real logic, that logic lives in a separate Starlark file, and it runs only inside the build sandbox ([DESIGN §10.5](DESIGN.md#sandboxed-builds)).

---

<a id="files-of-a-package"></a>

## 2. Files of a package

```text
orchards/core/ffmpeg/
 ├── package.toml      # this specification (required)
 ├── build.star        # build logic (required iff [build].system = "custom")
 ├── tests.star        # smoke tests (required for core orchard)
 ├── patches/          # patch files, each checksummed in package.toml
 └── files/            # auxiliary files: default configs, data files
```

Two rules govern the layout. The directory name **must** equal `package.name`, and one directory holds one package lineage: every version of `ffmpeg` lives in the same formula, and the orchard's git history is the version history.

A `type = "binary"` package (§3.11) consists of `package.toml` **alone**. Nothing is compiled, so there is no `build.star`; nothing is modified, so there are no patches.

---

<a id="packagetoml--full-schema"></a>

## 3. `package.toml` — full schema

Every formula begins with `spec = 1`, the format version. A reader rejects a `spec` value it does not know, and rejects unknown fields at any level; the format can therefore evolve without old tools silently misreading new files.

<a id="package--identity"></a>

### 3.1 `[package]` — identity

```toml
spec = 1

[package]
name         = "ffmpeg"
version      = "7.1.0"          # normalized; see §4
revision     = 0                # orchard-side packaging revision (same upstream, new recipe)
epoch        = 0                # last-resort ordering override; see §4.4
license      = "LGPL-2.1-or-later"   # SPDX expression, validated against the SPDX list
description  = "Play, record, convert, and stream audio and video"
homepage     = "https://ffmpeg.org"
documentation = "https://ffmpeg.org/documentation.html"   # optional
maintainers  = ["alice <alice@example.com>"]              # at least one for core/extended
keywords     = ["video", "codec", "transcode"]            # powers `aslice search`
tier         = "core"           # core | extended
```

| Field | Required | Rules |
|---|---|---|
| `name` | yes | `[a-z0-9][a-z0-9-]*`, ≤ 64 chars, unique per orchard |
| `version` | yes | Normalized aslice version (§4); stored normalized, not verbatim-upstream |
| `revision` | yes | Integer ≥ 0; resets to 0 on any `version` change; bumped for packaging-only changes |
| `epoch` | no | Integer ≥ 0, default 0; §4.4 |
| `license` | yes | SPDX expression; `LicenseRef-` for unlisted licenses (vendor freeware: `LicenseRef-Proprietary`) |
| `type` | no | `"build"` (default) or `"binary"` — vendor pkg/dmg packages, §3.11 |
| `min_os` / `max_os` | no | §3.2 |
| `flavors` | no | §3.3 |

Note what `[package]` does not contain: lifecycle state. End-of-life flags belong to `[audit]` (§3.9), and the deprecation lifecycle — active → deprecated → disabled → tombstoned — is declared in `[deprecation]` (§3.14). The identity table says what a package is, not where it stands in its life.

<a id="platform-bounds--minimum-os-maximum-os"></a>

### 3.2 Platform bounds — minimum OS, maximum OS

```toml
[package]
min_os = "10.12"    # oldest macOS this formula builds/runs on; default "10.11"
max_os = "12"       # optional; omit unless upstream genuinely breaks on newer
```

- `min_os` does two jobs: it sets the package's deployment target, and it controls index visibility. A 10.11 machine never sees a package with `min_os = "10.12"`; the solver filters it out and says why ("requires macOS ≥ 10.12"), rather than letting the failure surface at run time.
- Legal values are exactly the supported window: `"10.11"`, `"10.12"`, `"10.13"`, `"10.14"`, `"10.15"`, `"11"`, `"12"`.
- Declare the real floor ([DESIGN §4.1](DESIGN.md#the-os-axis-collapses--at-1011)). A build that needs contortions to claim 10.11 does not support 10.11.
- For `type = "binary"` packages, each `[[binary]]` artifact carries bounds of its own (§3.11); the `[package]` values are the defaults an artifact inherits.

<a id="flavors--minimum-instruction-set"></a>

### 3.3 `flavors` — minimum instruction set

```toml
[package]
flavors = ["v2", "v3"]    # omit → all of ["v1", "v2", "v3"]
```

- A package that genuinely needs AVX2 — hand-written AVX2 kernels with no dispatch fallback, say — declares `flavors = ["v3"]`. The farm then skips its `v1`/`v2` slices, and v1/v2 machines get a clear solve-time message.
- The toolchain, not the formula, supplies the flavor's `-march=x86-64-vN` floor (§6.3); formula authors never write `-march` themselves. A user's `-march=native` request layers on top at install time ([DESIGN §7.4](DESIGN.md#user-flags)). ABI-neutral choices may share a compatibility key; exact flags and CPU requirements enter the artifact manifest. ABI-changing flags require a declared ABI variant or are rejected, and unknown effects require an isolated build and explicit dependency validation ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)).
- `min_os` and `flavors` are orthogonal axes, and both enter the build identity ([DESIGN §7.2](DESIGN.md#build-identity)).
- `flavors` remains a source-build axis. Vendor artifacts instead require `cpu_features` and `requires_i386`, describing actual execution requirements. Nothing being compiled does not imply compatibility with every CPU ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)).

<a id="source--where-the-bits-come-from"></a>

### 3.4 `[[source]]` — where the bits come from

```toml
[[source]]
url     = "https://ffmpeg.org/releases/ffmpeg-7.1.0.tar.xz"
sha256  = "40973d44…"           # required, always
mirrors = ["https://mirror.example/ffmpeg-7.1.0.tar.xz"]

[[source]]                        # multiple sources allowed; unpacked in order
git    = "https://github.com/example/plugin.git"
commit = "d34db33f…"            # full commit hash, required for git sources; tags alone are not pins
into   = "contrib/plugin"       # optional target subdirectory
```

Rules:

- **Every source is content-pinned**: archives by sha256, git by full commit hash. A mutable ref such as `branch = "main"` is rejected by `aslice lint`.
- **PGP verification** may be added on top: `[source.pgp] key_url = "…", fingerprint = "…"`. Because the fingerprint itself is pinned in the formula, substituting a different key fails closed.
- Git submodules are forbidden. What a submodule would have provided is expressed as an additional `[[source]]` entry, which is pinned and mirrored like any other source.
- Patches live in `patches/` and are listed with their hashes:

```toml
[[patch]]
file   = "patches/0001-fix-darwin15-clock.patch"
sha256 = "a1b2c3…"
```

<a id="variants--feature-switches-with-abi-tags"></a>

### 3.5 `[variants.*]` — feature switches with ABI tags

```toml
[variants.x265]
default     = true
abi         = true        # changes the exported interface → enters build identity (DESIGN §7.2)
description = "HEVC encoding via x265"

[variants.debug]
default     = false
abi         = false       # ABI-neutral; may share a compatibility key
description = "Build with debug symbols"

[variants.lto]
default     = false
abi         = false
conflicts   = ["debug"]               # optional: mutually exclusive variants
requires    = []                      # optional: variant prerequisites
```

- Each `abi = true` variant's `description` must name the interface it changes (policy: [DESIGN §13.2](DESIGN.md#variant-discipline)). There is no cap — a package declares as many variants as its users need.
- A variant may carry platform bounds of its own: `min_os = "10.13"` or `flavors = ["v2", "v3"]` inside a `[variants.*]` table narrows where that variant is available.
- `[variants.*]` is rejected on `type = "binary"` packages; a vendor artifact has no build-time switches to describe.

<a id="depends--dependencies"></a>

### 3.6 `[depends]` — dependencies

```toml
[depends]
runtime = [
  "x264 ^0.164",                   # version constraint (§5.2)
  "x265 ^3.5 ?variant.x265",       # conditional: only when our x265 variant is on (§5.3)
  "openssl ^3.0 || ^3.2",
  "sdl2 +metal ^2.28",             # require the provider built with its metal variant
  "macfuse ?os>=10.14",            # OS-conditional dependency
]
build   = ["nasm ^2.16", "pkgconf"]
test    = ["ffprobe-selftest"]
```

The full dependency semantics are in §5. On `type = "binary"` packages, `build` and `test` dependencies are rejected — there is no build — while `runtime` remains valid: a vendor tool can legitimately need aslice's openssl.

<a id="interop-declarations--provides-conflicts-replaces"></a>

### 3.7 Interop declarations — provides, conflicts, replaces

```toml
conflicts = ["ffmpeg4", "libav"]      # cannot be installed into the same profile
replaces  = ["ffmpeg4"]               # rename/supersede: upgrades replace the old package atomically
aliases   = ["ff"]                    # search/install aliases, no semantics

[provides]
blas = "3.11"          # virtual package provided, with version; satisfies `depends: ["blas ^3"]`
```

- `provides` is the interop mechanism for interchangeable implementations: `openblas`, `blis`, and the Accelerate shim all provide `blas`. A dependent names the virtual package; the solver picks a provider, and the default is configurable per profile (`aslice profile prefer blas openblas`).
- `conflicts` expresses *identity* conflicts only. File collisions need no declaration: aslice detects them from the manifests and resolves them by profile-level priority ([DESIGN §8.2](DESIGN.md#profiles-as-the-interoperability-surface)).

<a id="install--declarative-post-install-behavior"></a>

### 3.8 `[install]` — declarative post-install behavior

Every behavior in this section is carried out by aslice itself; a package never runs code to make it happen (declared vendor grafts, §3.11, are the sole exception):

```toml
[install]
links_priority = 50                     # collision priority in profiles; default 50
link           = true                   # false: install into the store without linking into profiles
# aslice link / aslice unlink flip a link = false package
# in/out of a profile; each flip is a new generation (DESIGN §12.1)
link_reason    = "shadows-macos"        # required iff link = false; the explanation `info` shows
notes          = ["config lives in etc/postgresql"]   # actionable post-install guidance (caveats)

[[install.data_dir]]
path = "var/lib/postgresql"             # created at install, survives uninstall unless --purge
mode = "0750"

[service]                               # launchd, described — aslice generates the plist (v0.4)
run         = ["bin/postgres", "-D", "var/lib/postgresql"]  # argv, profile-relative; never a shell string
domain      = "user"                    # user (default) | system — root daemon, trust-gated (DESIGN §12.8)
keep_alive  = true                      # bool, or a table of launchd KeepAlive conditions
run_at_load = true
working_dir = "var"                     # prefix-relative
environment = { LANG = "en_US.UTF-8" }  # static env; per-user overrides in $XDG_CONFIG_HOME/aslice/services/<pkg>.env
log_dir     = "var/log/postgresql"      # StandardOutPath / StandardErrorPath
user_name   = "_postgres"               # optional; system domain only

[install.completions]
bash = "share/bash-completion/ffmpeg"
zsh  = "share/zsh/site-functions/_ffmpeg"
```

The plist itself never ships in the formula. aslice generates it from `[service]`, with a label distinguishing prefix, profile, and package; the exact encoding is specified with the helper protocol ([HELPERS §6](HELPERS.md#details-still-to-be-established)). User agents execute through their user-owned profile. Root-domain services execute only from a complete verified closure in protected helper-owned storage, including libraries, interpreters, configuration, and launch plists ([STATE-AND-RECOVERY §3](STATE-AND-RECOVERY.md#privileged-ownership-and-capability-checks)). They never execute through a user-writable profile or load user-owned environment overrides. `aslice-system` authorizes each protected activation or rollback, and the repository must hold the `system` capability ([REPOSITORIES §3](REPOSITORIES.md#trust-levels)). Changed declarations regenerate plists as part of the transaction. A package declares at most one `[service]`; software with several daemons is packaged as several packages. [DESIGN §12.8](DESIGN.md#services-launchd-native-lifecycle-and-safe-upgrades) specifies the service lifecycle.

`link = false` installs the package into the store without exposing it through a profile. In core it is the default for versioned lineages (`openssl3` style) and for anything whose `bin/` names collide with `/usr/bin` or `/bin` (policy: [ORCHARD-POLICY §6](ORCHARD-POLICY.md#dependencies-and-system-software)); `aslice link <pkg>` opts a package into a profile explicitly. Dependents never need the link: dependency resolution works on store paths (`ctx.deps`), so being depended upon while unlinked is a normal state. When `link = false`, lint requires `link_reason`, and `info` and the installer display it — the user is told why the package did not appear in the profile. Finally, `notes` is the caveats field: human-readable, actionable post-install lines ("config lives in …", "run `aslice service start postgresql` to …"), printed at install and shown by `info`. A line that isn't actionable isn't a note ([ORCHARD-POLICY §14](ORCHARD-POLICY.md#package-documentation-standards)).

<a id="audit--vulnerability-matching-and-lifecycle"></a>

### 3.9 `[audit]` — vulnerability matching and lifecycle

```toml
[audit]
cpe      = "cpe:2.3:a:ffmpeg:ffmpeg"   # binds the package to CVE feeds
eol      = false
eol_date = "2027-03-01"                # optional upstream EOL announcement
```

`aslice audit` joins the installed set against OSV and GitHub Advisory data, matching on CPE and name aliases. A package with `eol = true` installs only with `--allow-eol` and is excluded from the core orchard ([DESIGN §13.1](DESIGN.md#package-acceptance-policy)). For vendor binaries a `cpe` should be present whenever one exists: the payload is opaque to source-level analysis, so feed matching is the entire safety net.

<a id="build--the-declarative-build-shortcut"></a>

### 3.10 `[build]` — the declarative build shortcut

```toml
[build]
system = "cmake"                        # autotools | cmake | meson | cargo | go | make | custom
args   = ["-DENABLE_GPL=ON", "-DENABLE_LIBX265=ON"]
```

When `system` names a known build system, **no `build.star` is needed**: aslice runs the canonical phase sequence for that system — configure with the system-typical flags, parallel build, DESTDIR install, ABI scan. `system = "custom"` is the escape hatch and requires `build.star` (§6). The result is that an autotools hello-world formula is exactly three tables: `[package]`, `[[source]]`, and `[build] system = "autotools"`. `[build]` is forbidden on `type = "binary"` packages, which have no build.

<a id="binary--vendor-binaries-pkgdmg-only-software"></a>

### 3.11 `[[binary]]` — vendor binaries (pkg/dmg-only software)

A nontrivial share of the software worth having on this platform will never exist as buildable source: vendor CLIs, commercial audio tools, frozen releases of abandoned applications. Such software enters the ecosystem as a **vendor binary package** — a formula consisting of `package.toml` alone, describing one or more vendor artifacts, each tagged with the OS releases it supports.

The following recipe illustrates the complete table layout. URLs, signer identities, and abbreviated hashes are placeholders, not publishable inputs. Each artifact has its own payload map and verified execution requirements.

```toml
spec = 1

[package]
name    = "vendorcli"
type    = "binary"
version = "3.2.1"
revision = 0
license = "LicenseRef-Proprietary"
description = "Vendor's signal-routing CLI"
homepage = "https://vendor.example/vendorcli"
maintainers = ["alice <alice@example.com>"]
tier = "extended"

[[binary]]                              # one entry per vendor artifact; solver picks by tags
url       = "https://vendor.example/vendorcli-3.2.1-legacy.pkg"
sha256    = "aa11…"
format    = "pkg"                       # pkg | dmg
min_os    = "10.11"                     # artifact-level bounds; override [package] defaults
max_os    = "10.13"                     # vendor's legacy build genuinely stops at 10.13
cpu_features = ["sse2"]                 # illustrative; verify actual vendor requirements
requires_i386 = false                   # usable x86_64 path, no required i386-only helper
arch      = ["x86_64", "i386"]          # universal; the ceiling follows required i386-only execution
signer    = "Developer ID Application: Vendor Inc. (ABCD1234)"   # pinned; change = hard fail
notarized = false                       # pre-notarization-era artifact; expected and announced
redistribute = false                    # clients fetch the vendor URL themselves

[[binary.payload]]
from = "usr/local/bin/vendorcli"
to   = "bin/vendorcli"

[[binary.payload]]
from = "VendorCLI Helper.app"
to   = "apps/VendorCLI Helper.app"

[[binary]]                              # the vendor's current build, for newer machines
url       = "https://vendor.example/vendorcli-3.2.1.pkg"
sha256    = "bb22…"
format    = "pkg"
min_os    = "10.14"
cpu_features = ["sse2"]
requires_i386 = false
arch      = ["x86_64"]
signer    = "Developer ID Application: Vendor Inc. (ABCD1234)"
notarized = true
redistribute = false

[[binary.payload]]                      # declarative extraction map — scripts never run unless declared as grafts (below)
from = "usr/local/bin/vendorcli"        # path inside the pkg Payload
to   = "bin/vendorcli"

[[binary.payload]]                      # a .app payload installs under <prefix>/apps/
from = "VendorCLI Helper.app"
to   = "apps/VendorCLI Helper.app"

[install]
notes = ["vendorcli looks for its license file in ~/Library/Application Support/VendorCLI"]

[depends]
runtime = ["openssl ^3.0"]              # vendor binaries may depend on aslice packages
```

Rules:

- **`type = "binary"` forbids `[build]`, `build.star`, `[[patch]]`, `[[source]]`, `[variants]`, and `build`/`test` dependencies.** Nothing is compiled and nothing is patched, so the pipeline compresses to `fetch → verify (hash + signer) → extract payload → abi-scan → pack → sign` (§6.1).
- **Installer scripts never run by default; declared grafts are the exception.** A `.pkg` script or `.dmg` autolaunch runs only when declared, hash-pinned, and approved as a graft. It executes in an isolated staging view; the helper commits a validated delta through its journal. Scripts needing live privileged execution, unrestricted privileged IPC, network access, remote effects, or firmware effects are refused in v1 ([STATE-AND-RECOVERY §4](STATE-AND-RECOVERY.md#graft-execution-boundary)). Kexts and daemons are registered declaratively by the helper under the ordinary capability gates. An undeclared script never runs.
- **Signer pinning is mandatory** for signed artifacts, and `notarized` records the notarization expectation (checked on 10.14+, where notarization exists). The verifier hard-fails if the signer changes: silent signer substitution upstream is how binary distribution channels get compromised. An unsigned vendor artifact is allowed in extended with `signer` omitted, and the omission is announced at install ([DESIGN §12.2](DESIGN.md#interaction-principles)).
- **`redistribute` is required; there is no default.** `true` means the farm repackages the payload as a hosted slice — atomic, resumable, rollback-able. `false` means every client fetches the vendor URL itself, hash- and signer-pinned, and the index carries the formula but no blob. A mutated or pulled vendor artifact fails at the hash check rather than silently installing something else.
- **`arch` defaults to `["x86_64"]`.** aslice's own builds are x86_64-only, always ([DESIGN §2.2](DESIGN.md#non-goals) N6). A vendor payload may additionally declare `"i386"`, alone or universal as `["x86_64", "i386"]`: 32-bit code still executes on 10.11–10.14, and much of the pkg/dmg-only software worth having — audio plugins, lab instruments, frozen pro tools — ships that way.
- **The 32-bit ceiling follows required execution.** Required i386-only executables/helpers/plugins impose `max_os <= "10.14"`. A fat executable with a usable x86_64 member does not require i386 merely because an alternative member exists. Lint checks the declared entry points and dependency paths and requires evidence for ambiguous plugins ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)).
- **Universal payloads install whole.** Thinning a fat binary with `lipo -thin` would invalidate the vendor's code signature, and signer integrity outranks disk savings; the extraction is forbidden, and the store receives the artifact exactly as signed.
- **Pre-notarization-era artifacts are expected, not merely tolerated.** Software old enough to contain 32-bit code usually predates notarization (10.14+) and sometimes predates Developer ID signing altogether. `notarized = false` — or, in the extended tier, an omitted `signer` — is the normal case for these packages; it is announced at install, never blocked.
- **Execution requirements still apply.** Vendor compatibility keys set compiler/flavor fields to null and bind the vendor digest. Every artifact records CPU features and whether execution requires i386. ABI scanning retains exact dependency bindings when evidence is incomplete ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)).
- **OS tags are verified, not trusted.** At pack/repack time, each artifact's declared `min_os`/`max_os` is checked against the bundle's `LSMinimumSystemVersion`, the Mach-O minimum-version load commands, and — where present — the pkg Distribution's `allowed-os-versions`. Disagreement is a lint error.
- **Version normalization still applies** (§4): a vendor spelling like `3.2 Update 1` normalizes by the usual rules, and the verbatim string is preserved in `upstream_version`.

**Declared grafts — `[[binary.graft]]`.** When vendor software genuinely requires its installer scripts, the formula declares each script as a graft under the model of [DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible):

```toml
[[binary.graft]]
path     = "Scripts/postinstall"    # path inside the artifact (pkg Scripts/, or dmg-resident)
sha256   = "cc33…"                  # pinned; a mutated script is a hard fail, not a surprise
when     = "post"                   # pre | post — relative to payload extraction
writes   = ["/Library/Audio/Plug-Ins/HAL/VendorDSP.driver"]  # every path it may write
kexts    = ["com.vendor.dspdriver"] # helper-managed kext declarations; omit if none
daemons  = ["com.vendor.dspd"]      # helper-managed daemon declarations; omit if none
network  = false                    # v1 requires false; true is reserved and refused
elevated = true                     # helper authorization for protected delta commit; no live root script
```

- **The script is hash-pinned** (`path`, `sha256`): the farm verifies the hash at rehearsal and the client verifies it again before execution, so an upstream-mutated script fails rather than runs unreviewed.
- **The behavior manifest is exhaustive.** An omitted effect means none, not unknown. The staging sandbox must enforce the declared boundary, and boundary violations abort the transaction. Network inputs are fetched and pinned before execution; `network = true` is reserved and refused in v1. Rehearsal alone does not establish containment ([STATE-AND-RECOVERY §4](STATE-AND-RECOVERY.md#graft-execution-boundary)).
- **Approval binds repository identity, package version, script digests, and the complete effective behavior-manifest digest.** Changed bindings require a new decision. Machine-file names can select an existing matching approval but cannot create one ([SETUP §2.8](SETUP.md#grafts)). Unsigned manifests require a fresh decision every time.
- **`elevated = true` requires an authorized helper commit of the protected delta.** It does not authorize live root execution of the vendor script. Capability checks and required system-change consent apply to the effects regardless of how they are declared ([STATE-AND-RECOVERY §3](STATE-AND-RECOVERY.md#privileged-ownership-and-capability-checks)).
- **The farm rehearses each supported OS and signs the manifest** for core and extended. Rehearsal covers execution and attempted boundary violations; enforcement and crash recovery must also pass before admission. Journal recovery can require attention when external state has changed; arbitrary vendor effects are not promised reversible ([STATE-AND-RECOVERY §4](STATE-AND-RECOVERY.md#graft-execution-boundary) and [STATE-AND-RECOVERY §5](STATE-AND-RECOVERY.md#durable-transactions-and-recovery)).

<a id="system--kernel-extensions-and-sip-disabled-tools-v04"></a>

### 3.12 `[system]` — kernel extensions and SIP-disabled tools (v0.4)

```toml
[system]
kexts            = ["Library/Extensions/FooAudio.kext"]  # payload-relative paths to install
sip_off_required = false     # true: the software cannot function while SIP is enabled
reason           = "Kernel driver for FooAudio USB interfaces"   # mandatory; this IS the warning text
```

A package becomes a system package by declaring either a non-empty `kexts` or `sip_off_required = true` (or both). `reason` is mandatory whenever `[system]` is present, and aslice shows it verbatim in the install warning — so write it as warning text, not as a description. Kext paths are payload-relative and must live under `Library/Extensions/`; the linter rejects anything else. The mechanism — `aslice-system` elevation, the warning flow, `csrutil` checks, trust gating, rollback — is specified in [DESIGN §12.7](DESIGN.md#system-software-kexts-and-sip-disabled-development-tools), and the acceptance policy in [ORCHARD-POLICY §13](ORCHARD-POLICY.md#system-software-packages-kexts-sip-disabled-tools-and-system-patches). `[system]` composes with `type = "binary"` (vendor kexts, §3.11) and with `[service]` (a driver that also runs a daemon, §3.8).

<a id="runtime-extension-ride--multi-version-runtimes-v05"></a>

### 3.13 `[runtime]`, `[extension]`, `[ride]` — multi-version runtimes (v0.5)

Users routinely keep several versions of php, nodejs, ruby, and python installed at once. A **runtime formula** tells aslice how to multiplex among them (mechanism: [DESIGN §12.9](DESIGN.md#multi-version-runtimes-use-pin-default--and-version-bound-extensions)):

```toml
[runtime]
abi_epoch          = "8.4"      # the extension-ABI epoch of THIS version (see below)
shims              = ["php", "php-cgi", "php-fpm", "phpize", "php-config", "pecl"]
extension_scan_dir = "etc/php/{epoch}/conf.d"   # where aslice writes extension loaders

[[runtime.env]]                 # injected by the shim when exec'ing this runtime's tools
var   = "PHPRC"
value = "{userbase}/etc"

[[runtime.env]]
var   = "PHP_INI_SCAN_DIR"
value = "{userbase}/etc/conf.d:{profile}/{extension_scan_dir}"
```

- `shims` lists the tools that multiplex through the shim layer. aslice installs a shim under each listed name, and the profile itself links only the **versioned aliases** (`bin/php8.4`, derived from the stream). The bare name belongs to the shim layer; lint rejects any other package that tries to link it.
- `abi_epoch` records how often the runtime's *extension* ABI breaks: at minor granularity for php, python, and ruby (`"8.4"`, `"3.12"`, `"3.3"`), at major granularity for nodejs (`"22"`). The value is a fact about upstream's ABI policy, restated on each version; the linter cross-checks it against `version`, and a patch release never changes it. Extension builds key on it (below), and the shim uses it to name the per-version userbase.
- `extension_scan_dir` (optional) names the profile-relative directory where aslice writes loader files for `[extension]` packages bound to this runtime; `{epoch}` in the path expands to `abi_epoch`. Declare it for runtimes whose extensions are activated by config file (php); omit it where the runtime has no such convention.
- `[[runtime.env]]` declares the environment the shim injects at exec time. This is what binds ecosystem-native installs (pip, gem, npm, pecl, composer global) to the resolved version's writable **userbase**. The available template variables are `{userbase}` (`~/.aslice/runtimes/<name>/<epoch>`), `{profile}` (the live profile), `{store}` (the resolved runtime's store path), `{epoch}`, and `{extension_scan_dir}`. Beyond these, values are literal — no shell expansion, ever. Only `[runtime]` formulae may declare env injection; the feature exists to redirect ecosystem package managers into per-version territory and is not a general environment mechanism.

An **extension formula** is a compiled module for a runtime; it declares its binding:

```toml
[package]
name    = "php-redis"
version = "6.1.0"
# …

[extension]
runtime = "php"                         # the runtime formula this builds against
loader  = "20-redis.ini"                # written into the runtime's extension_scan_dir
module  = "lib/php/extensions/redis.so" # payload path the generated loader references
```

- To the solver, `[extension]` is a dependency on the runtime **at a specific ABI epoch** — whichever stream install-time resolution selects ([DESIGN §12.9](DESIGN.md#multi-version-runtimes-use-pin-default--and-version-bound-extensions)'s session → project → default chain, or an explicit `--runtime php@8.3`). The epoch enters the extension's build identity: [DESIGN §7.2](DESIGN.md#build-identity) gains a `runtime_epoch` term for these packages, so `php-redis` built for php 8.3 and for php 8.4 are distinct store paths that coexist the way flavors do, and the farm prebuilds the extension × supported-epoch × flavor matrix.
- The build itself is unremarkable: it compiles against the concrete runtime store path, reached as `ctx.deps["php"]`, with headers, `phpize`, and `php-config` all present, under the same sandbox as any other build. Nothing in §6 changes.
- At link time aslice writes `loader` into the epoch-keyed scan dir, pointing at `module` inside the extension's own store path. Extension sets are therefore generation-managed, and a rollback restores runtime and extension set together ([DESIGN §12.9](DESIGN.md#multi-version-runtimes-use-pin-default--and-version-bound-extensions)). `loader` and `module` are required exactly when the bound runtime declares `extension_scan_dir`.
- `depends.runtime` must not repeat the bound runtime: `[extension]` already expresses that dependency, and a duplicate carrying a conflicting constraint is a lint error.

A **riding tool** targets the interpreter without linking against it natively — composer, yarn, prettier, and poetry are the canonical cases. It declares:

```toml
[ride]
runtime = "php"                         # launched under the currently selected runtime
entry   = "lib/composer/composer.phar"  # payload path handed to the runtime
```

At exec time the tool's shim resolves in two steps: first the runtime stream (session → project → default), then `exec <runtime>/bin/php <tool-store>/<entry>`. Whether a tool may ride is a fact about its code, not a packaging preference: if the payload's ABI scan shows linkage against runtime libraries, lint rejects `[ride]` — such a tool is an `[extension]`-style binding or a self-contained package. A rider carries no runtime version constraint of its own; following the user's selection is what riding means.

<a id="deprecation--the-package-lifecycle-declared-v06"></a>

### 3.14 `[deprecation]` — the package lifecycle, declared (v0.6)

`[deprecation]` replaces the retired `[package] deprecated` boolean. A boolean can say that a package is deprecated; it cannot say since when, why, or what to use instead. Deprecation here is a lifecycle with dates and reasons (policy: [ORCHARD-POLICY §8](ORCHARD-POLICY.md#deprecation-and-removal-lifecycle)):

```toml
[deprecation]
date         = "2027-03-01"    # when deprecation starts
reason       = "upstream-eol"  # upstream-eol | security | renamed | unmaintainable | takedown | other
replacement  = "ffmpeg7"       # optional pointer; mandatory when reason = "renamed"
disable_date = "2027-09-01"    # optional: new installs refuse after this without --force-disabled
```

The transitions work as follows. **Active → deprecated:** installs and `info`/`audit` warn with `reason` and `replacement`; existing installs are unaffected, and the package still receives slices. **Deprecated → disabled:** at `disable_date`, new installs refuse without `--force-disabled`; existing installs keep working and remain in locks. **Disabled → tombstoned:** the formula leaves orchard HEAD, but the index keeps a permanent tombstone — name, final version, reason, replacement — so that historical snapshots and old locks resolve forever. Two further rules are policy rather than schema: an upstream-EOL package in extended may carry `reason = "upstream-eol"` indefinitely as normal life, not failure ([ORCHARD-POLICY §8](ORCHARD-POLICY.md#deprecation-and-removal-lifecycle)); and the security fast path, straight to disabled by owner approval during single-owner launch, is a policy decision the schema merely permits. `reason = "takedown"` records a verified rights-holder complaint ([ORCHARD-POLICY §8](ORCHARD-POLICY.md#deprecation-and-removal-lifecycle)); hosted slices stop being served, and the tombstone preserves the record.

<a id="livecheck--upstream-freshness-declared-v06"></a>

### 3.15 `[livecheck]` — upstream freshness, declared (v0.6)

`[livecheck]` tells the orchard's automation how to find new upstream releases (freshness policy: [ORCHARD-POLICY §9](ORCHARD-POLICY.md#freshness-livecheck-and-autobump)):

```toml
[livecheck]
strategy        = "git-tags"       # git-tags | homepage-regex | directory-index | crates | npm | pypi | sparkle
url             = "https://github.com/FFmpeg/FFmpeg/tags"   # strategy-specific
regex           = "^n([\\d.]+)$"   # optional pattern → version capture
skip_prerelease = true             # default true
throttle_days   = 3                # don't bump more often than this; default 3
cooldown_days   = 2                # wait after upstream release — supply-chain poisoning window; default 2, minimum 2
```

`[livecheck]` is required for core packages and encouraged in extended; a core package whose livecheck strategy rots is a bug against its named maintainer ([ORCHARD-POLICY §9](ORCHARD-POLICY.md#freshness-livecheck-and-autobump)). `aslice livecheck [pkg|--all]` runs the query by hand, machine-readable. The scheduled orchard sweep opens autobump PRs — new `version`, bot-fetched `sha256`, `revision` reset to 0, changelog link — and they merge only through the same gates as any other PR; the human path is `aslice bump-pr <pkg> <version>`. The cooldown may be raised for historically risky ecosystems (npm, PyPI, RubyGems, crates); it may never drop below 2.

<a id="system-patch--flagged-replacement-of-apple-provided-files-v06"></a>

### 3.16 `[system-patch]` — flagged replacement of Apple-provided files (v0.6)

This is the strictest declaration in the format. A system-patch package replaces an Apple-provided file through the protected helper. Originals and metadata remain in root-owned storage; executable replacements and their dependencies come from a verified root-owned closure. Supported symlinks target that closure, never the user-writable profile ([STATE-AND-RECOVERY §3](STATE-AND-RECOVERY.md#privileged-ownership-and-capability-checks)). The OS-specific backend governs application and restoration, including Recovery and reboot where needed (SYSTEM-VOLUMES). The mechanism and consent flow are specified in [DESIGN §12.11](DESIGN.md#system-patches-flagged-reversible-replacement-of-apple-provided-files), the acceptance policy in [ORCHARD-POLICY §13](ORCHARD-POLICY.md#system-software-packages-kexts-sip-disabled-tools-and-system-patches).

```toml
[system-patch]
targets          = ["/usr/bin/openssl"]   # absolute paths this package replaces
sip_off_required = false     # true: the replacement cannot be performed while SIP is enabled
reason           = "10.11's openssl is a 0.9.8-era tool that cannot speak modern TLS"  # mandatory; IS the warning text
```

- `targets` names tools, configs, and data files by absolute path — never the shared library space. Some targets are refused by construction: the kernel, `dyld`, `libSystem`, anything under `/System`, and any dylib or framework in a platform binary's load path. The list is lint-enforced and not negotiable in review ([ORCHARD-POLICY §13](ORCHARD-POLICY.md#system-software-packages-kexts-sip-disabled-tools-and-system-patches)).
- `reason` is mandatory whenever `[system-patch]` is present, and is shown verbatim at every decision point. As with `[system]` (§3.12), write it as warning text.
- Serving a system-patch package requires the repository **`system-patch` capability** ([REPOSITORIES §3](REPOSITORIES.md#trust-levels)). Official and local repositories hold it by default; a verified repository receives it only through the user's explicit per-repo grant (`aslice repo allow-system-patch <name>`), which is refused by default and revocable; third-party repositories can never hold it. Non-interactive installation requires `--accept-system-changes`; there is no "always allow" ([DESIGN §12.11](DESIGN.md#system-patches-flagged-reversible-replacement-of-apple-provided-files)).

---

<a id="versioning"></a>

## 4. Versioning

<a id="the-version-type"></a>

### 4.1 The version type

An aslice version is **SemVer 2.0 with one extension**: an optional fourth numeric component, added for upstreams that letter their patches. Formally:

```text
version  := epoch? core ("." patch4)? ("-" prerelease)?
epoch    := <uint> "!"          (rarely needed; §4.4)
core     := <uint> "." <uint> "." <uint>
patch4   := <uint>              (only for upstreams with letter/scheme patches)
```

Ordering compares epoch first, then the numeric core components, then patch4, then prerelease, under the usual SemVer rules. Build metadata (`+…`) is **not** used: identity is the build_id's job ([DESIGN §7.2](DESIGN.md#build-identity)), not the version's.

<a id="normalization-upstream--aslice"></a>

### 4.2 Normalization (upstream → aslice)

The orchard records `version` in normalized form only; where upstream spelled it differently, that spelling is kept in `source.upstream_version`:

| Upstream tag | Normalized | Rule |
|---|---|---|
| `v7.1` | `7.1.0` | Strip leading `v`; pad to three components |
| `1.3` | `1.3.0` | Pad |
| `2.0.0-rc.2` | `2.0.0-rc.2` | Prerelease passes through (SemVer spelling required) |
| `1.1.1k` | `1.1.1.11` | Letter patch → patch4 (`a`=1 … `z`=26) |
| `2024.09.1` | `2024.9.1` | CalVer with numeric components passes through |
| `r4520` / `git describe` hashes | **rejected** | Use epoch + a synthetic version, chosen by the maintainer |

A prerelease sorts before its release (`7.1.0-rc.1 < 7.1.0`) and is **excluded from default resolution** — you get one only by asking for it, with `aslice install ffmpeg --prerelease` or an explicit constraint.

<a id="constraint-syntax"></a>

### 4.3 Constraint syntax

| Syntax | Meaning | Example matches |
|---|---|---|
| `"x264"` | any version | — |
| `"x264 ^0.164"` | compatible: `>=0.164.0 <0.165.0` (caret; for `0.x`, minor is pinned per SemVer convention) | `0.164.5` |
| `"openssl ~3.0.8"` | patch-level: `>=3.0.8 <3.1.0` | `3.0.14` |
| `"zlib =1.3.1"` | exactly this version | `1.3.1` |
| `"libpng >=1.6, <1.7"` | range intersection | `1.6.43` |
| `"openssl ^3.0 \|\| ^3.2"` | union | `3.0.15`, `3.2.1` |
| `"python *"` | any (explicit wildcard; same as bare name) | — |

Constraints compose freely with conditionals and provider-variant requirements, in any order: `"x265 ^3.5 +asm ?variant.x265"`.

<a id="revision-and-epoch"></a>

### 4.4 Revision and epoch

- **`revision`** bumps when the recipe changes while upstream does not: a patch added, a dependency range fixed, a rebuild against a new ABI. `7.1.0-1` sorts after `7.1.0-0`. Revisions are orchard bookkeeping and form no part of upstream identity.
- **`epoch`** exists for two bad days: the day an upstream changes its versioning scheme, and the day a maintainer ships a mistaken higher version that must be rolled back. `epoch = 1` outranks every `epoch = 0` version regardless of the remaining components. It is a break-glass mechanism, and its use is announced at install time.

---

<a id="dependency-semantics"></a>

## 5. Dependency semantics

<a id="the-three-kinds"></a>

### 5.1 The three kinds

| Kind | Needed when | Propagates transitively? |
|---|---|---|
| `build` | compiling this package | **No** — build tools never leak into a consumer's closure |
| `runtime` | linking against or executing this package | **Yes** — the runtime closure is recursive |
| `test` | `tests.star` only | No |

A consumer records exact dependency artifact bindings ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)). The loader check compares provider `current_version` with the client's compatibility requirement; the provider's `compatibility_version` is recorded separately. Exported and required symbol lists provide coverage evidence; an equality fingerprint cannot establish set inclusion or semantic compatibility. Existing consumers retain their bound artifacts after a profile switch. Rebinding requires a rebuild or verified relocation producing a new artifact, with dependency tests rerun. Unknown evidence retains the exact binding or requires rebuilding and testing dependents; the plan reports that work before execution.

<a id="transitive-resolution"></a>

### 5.2 Transitive resolution

Resolution is PubGrub over the full graph ([DESIGN §7.5](DESIGN.md#the-solver)). Four rules adapt it to aslice:

1. **Single version per profile, by default.** A profile links exactly one build of a given name; the store may hold many, but the profile points at one. Libraries that need side-by-side majors are packaged under separate names — `openssl3` and, if ever needed, `openssl4` — which is an orchard naming convention, not a solver exception. The designed exception is multi-version **runtimes** (`[runtime]`, §3.13): the store holds every installed stream, the profile links each stream's versioned aliases (`bin/php8.4`), and the bare name (`php`) multiplexes through the shim layer in place of a profile link ([DESIGN §12.9](DESIGN.md#multi-version-runtimes-use-pin-default--and-version-bound-extensions)).
2. **Version unification.** When `a` needs `dep ^1.2` and `b` needs `dep ^1.4`, the profile gets one `dep` satisfying both (`^1.4`) — or the solve fails, rendering the conflict as a derivation tree (`--explain`).
3. **Build dependencies float.** Two packages in the same profile may have been built against different `nasm` versions; only runtime identity is unified.
4. **Cycles** in runtime edges are rejected at lint time. Build-time cycles — rare, but bootstrap compilers need them — require an explicit `bootstrap = true` edge annotation together with a pinned seed slice.

<a id="conditional-dependencies"></a>

### 5.3 Conditional dependencies

| Conditional | Meaning |
|---|---|
| `"x265 ?variant.x265"` | only when *this package's* `x265` variant is enabled |
| `"macfuse ?os>=10.14"` | only on matching OS releases |
| `"intel-mkl ?flavor>=v2"` | only when the target flavor is at least v2 (flavors are ordered `v1 < v2 < v3`) |

Conditionals are evaluated at solve time, against the machine's OS and flavor and the chosen variant assignment. The dependency graph the solver works on is therefore the graph that will actually be built.

<a id="provider-variant-requirements"></a>

### 5.4 Provider-variant requirements

`"sdl2 +metal ^2.28"` demands a provider whose build identity includes `+metal` (an `abi = true` variant). Since identity covers ABI variants, the match happens at the hash level: the solver either finds a slice with exactly that identity or plans a source build of the provider with that variant. There is no "close enough."

---

<a id="build-instructions"></a>

## 6. Build instructions

<a id="phase-model"></a>

### 6.1 Phase model

Declarative and custom builds alike run the same phase sequence, under the sandbox profiles of [DESIGN §10.5](DESIGN.md#sandboxed-builds):

```text
fetch → verify → unpack → patch → configure → build → install(staging) → abi-scan → test → pack(.slice) → sign
```

Only `fetch` has network access. `abi-scan` is run by aslice itself and cannot be skipped by a formula: the ABI contract is not optional metadata.

The `pack` phase emits the container defined in [SLICE-FORMAT](SLICE-FORMAT.md), with a [slice descriptor](../schematics/json/slice.schema.json) and [artifact manifest](../schematics/json/artifact-manifest.schema.json). Package signing produces a detached signature over the frozen archive bytes. Any Apple signing that changes payload bytes precedes manifest generation and packing.

For `type = "binary"` packages (§3.11) the pipeline compresses to `fetch → verify (hash + signer) → extract payload → abi-scan → pack → sign`: nothing is compiled, and embedded installer scripts are never executed — declared grafts (§3.11) are extracted and hash-verified, not run by this pipeline; they execute only at farm rehearsal and at client install, each time under their own manifest-derived profile ([DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)). Payload extraction runs under the same no-network unpack sandbox profile as source archives ([DESIGN §10.5](DESIGN.md#sandboxed-builds)).

<a id="declarative-builds"></a>

### 6.2 Declarative builds

`[build].system` covers the common cases with the defaults idiomatic to each system: `configure` with a prefix for autotools, out-of-tree `-DCMAKE_INSTALL_PREFIX` for cmake, `meson setup --prefix`, `cargo build --release` with `--locked` enforced (vendored or lockfile-pinned dependencies only, §6.5), and so on. Where the defaults need adjustment, per-phase overrides are available without going full `custom`:

```toml
[build]
system = "cmake"
args   = ["-DENABLE_GPL=ON"]
skip_tests = false
```

<a id="buildstar--the-custom-api"></a>

### 6.3 `build.star` — the custom API

The language is Starlark: deterministic, no network, filesystem confined to the build directory ([DESIGN §6.1](DESIGN.md#formulae-are-data-with-a-hermetic-build-script)). The script's entire capability surface is the `ctx` object:

| Member | Type | Meaning |
|---|---|---|
| `ctx.prefix` | string | Reserved relocation placeholder used during the build; materialization assigns the final artifact-addressed path ([STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#compatibility-and-artifact-identity)) |
| `ctx.staging` | string | DESTDIR staging directory |
| `ctx.jobs` | int | Parallelism granted by the scheduler |
| `ctx.flavor` | string | `"v1"` / `"v2"` / `"v3"` — the `-march=x86-64-vN` floor is already in `CC`/`CXX` wrappers |
| `ctx.min_os` | string | Deployment target; already exported as `MACOSX_DEPLOYMENT_TARGET` |
| `ctx.variant(name)` | fn → bool | Variant assignment for this build |
| `ctx.deps` | dict | name → store path of each resolved build+runtime dependency |
| `ctx.env` | map | Controlled environment; `ctx.env.set(k, v)` / `ctx.env.append(k, v)`; reads of host env are denied |
| `ctx.run(argv…)` | fn | Exec, argv-array only — **no shell**, no string interpolation attacks |
| `ctx.make(*args)`, `ctx.cmake(*args)`, `ctx.meson(*args)` | fn | Tool helpers with correct defaults |
| `ctx.user_cflags` / `ctx.user_ldflags` | string | User flags from install time ([DESIGN §7.4](DESIGN.md#user-flags)); appended and recorded in the artifact manifest; ABI-changing flags need a declared ABI variant, unknown effects need dependency validation |
| `ctx.patch(file)` | fn | Apply a checksummed patch from `patches/` |
| `ctx.replace(file, pattern, replacement)` | fn | In-place text substitution for trivial fixups without a patch file; count-checked — zero replacements is a build error, never a silent no-op |

The builder, not the formula, fixes the environment: `LC_ALL=C`, `TZ=UTC`, `SOURCE_DATE_EPOCH` pinned to the source timestamp, and prefix-mapping flags for reproducibility ([DESIGN §9.5](DESIGN.md#build-provenance)). If a formula needs something this API does not offer, the correct response is a bug report against aslice — not a sandbox escape.

<a id="what-the-sandbox-guarantees"></a>

### 6.4 What the sandbox guarantees

The security-relevant invariants this format relies on, collected in one place: no network after `fetch`; no writes outside the build directory; no reads of the host environment; no code execution at slice-install time, including vendor installer scripts, which never run on any path unless declared as grafts with an exhaustive behavior manifest (§3.11; [DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)); and `tests.star` runs network-free unless the formula declares `test_network = true`, which is logged at warn.

<a id="language-ecosystem-sub-managers"></a>

### 6.5 Language-ecosystem sub-managers

Ecosystems whose tools fetch their own dependencies — crates, Go modules, gems — are admitted **only** in lockfile-pinned, vendored form: `cargo build --locked --offline` against a `[[source]]`-supplied vendor tarball, `go build` with a pinned `go.sum` and vendored modules, and so on. Because the build sandbox denies network access, an ecosystem dependency that is not pinned in the formula fails closed.

---

<a id="lock-files"></a>

## 7. Lock files

<a id="who-locks-what"></a>

### 7.1 Who locks what

- **The orchard doesn't lock.** It doesn't need to: the signed index snapshot *is* the global lock, since every package in it names exact versions, build identities, and source hashes.
- **The machine locks.** Every profile carries a lock recording its exact resolved state, at `/opt/aslice/profiles/<name>/aslice.lock`. The lock is rewritten atomically with every generation, so `aslice rollback` restores the symlinks and the lock describing them together.
- **Projects and fleets export locks.** `aslice lock export > aslice.lock` captures a profile for reproduction elsewhere, and `aslice apply aslice.lock` replays it. The machine-wide sibling is the declarative setup file: `aslice machine apply aslice-machine.toml` plans and converges a whole machine (SETUP.md; [DESIGN §12.13](DESIGN.md#declarative-system-setup-aslice-machinetoml-and-the-aslice-machine-commands)).

<a id="format"></a>

### 7.2 Format

The machine-readable contract is [lock.tosd](../schematics/toml/lock.tosd), with a complete validation fixture in [lock.toml](../tests/fixtures/lock.toml). A lock records `lock_version`, profile, generated-by version, machine OS/flavor, per-repository identity/environment/index bindings, explicit provider/alias/replacement selections, and exact package records.

Each package records its repository, name/version/revision, compatibility `build_id`, immutable `artifact_id`, archive `blob_digest`, authenticated `recipe_digest`, origin, resolved variants, flags, CPU/OS requirements, and exact runtime artifact dependencies. Vendor-direct records additionally bind the vendor URL, digest, and signer when signed. Local artifacts must accompany an exported lock for exact replay elsewhere. `digest` is not overloaded between a manifest and a vendor installer. [STATE-AND-RECOVERY §8](STATE-AND-RECOVERY.md#8-plans-locks-archives-and-offline-use) defines replay and trust checks.

### Security dependency and selection records

Recipe dependencies describe intended build/runtime/embedded inputs; artifact manifests retain the actual exact bindings. Build evidence records both graphs, component identities, triggering inputs, and rebuild paths under [BUILD-INFRA](BUILD-INFRA.md#the-build-plan). Static libraries, headers, generators, and bundled sources must not disappear merely because the Mach-O scanner finds no dynamic link. An ABI-compatible change still invalidates affected transitive consumers.

Lock version 2 requires a top-level `selections` array. Each entry has `kind` (`provider`, `alias`, `replacement`), `requested`, `selected`, and `repository_identity`: exact requested and selected qualified names plus the selected repository's retained identity. Empty selections use `selections = []`; nonempty entries use `[[selections]]`. Requests and plans retain the same entries. Cross-namespace selections require an explicit user decision and current authorization; aliases and replacement declarations cannot grant authority. Unsupported version-1 locks and plans are rejected for execution and must be regenerated from authenticated records and explicit selections. Conversion never invents consent. See [REPOSITORIES](REPOSITORIES.md#overlapping-packages-across-repositories).

Plan version 2 separates operation policy, source `build_work`, advisory findings, and namespace selections from exact artifact actions. A build-work record binds recipe/input digests, package, reason, and dependency path. Before compilation the plan may contain build work without an `after` artifact; it must not invent an output hash. Verified outputs produce a realization plan with exact artifact records and the same approved inputs; changed inputs or expanded work require a new plan and consent. Exact replay still requires the recorded output bytes. Saved plans never grant source-build consent.

<a id="portability-semantics--exact-by-default-intent-preserving-across-flavors"></a>

### 7.3 Portability semantics — exact by default, intent-preserving across flavors

Exact lock replay requires **identical artifact IDs and verified payloads**, authorized by the recorded snapshot or current archive evidence. An incompatible machine or unavailable exact artifact blocks replay. An explicit portability request creates a new plan: retain requested versions and variants, resolve eligible artifacts for the target, and show every changed binding before consent. This is a new resolution, not successful exact replay.

For `type = "binary"` packages, explicitly requested cross-OS portability may select a different `[[binary]]` artifact to match the target machine's OS (§3.11): the version stays pinned, the artifact adapts, and the report says so. If no artifact matches at all — an i386-only package whose lock is replayed on 10.15+, say — re-resolution fails with the reason spelled out; there is nothing to adapt to, and `--frozen` changes nothing.

`--frozen` refuses re-resolution of any kind: a mismatch is an error, never an adaptation. This is the mode CI should use.

---

<a id="validation-and-tooling"></a>

## 8. Validation and tooling

- **`aslice lint <formula>`** runs full schema validation plus the policy checks: name rules, license validity, unpinned sources, submodule use, cycle detection, `min_os` plausibility against the toolchain — and, for `type = "binary"`, payload-map completeness against the actual artifact, signer and notarization verification, OS-tag consistency with bundle metadata — and, for every `[[binary.graft]]`, script-hash verification against the artifact plus behavior-manifest completeness (`writes`/`kexts`/`daemons`/`network` all explicitly declared, empty meaning none). Orchard CI runs lint plus a sandboxed build (or payload extraction) on every PR ([DESIGN §13.4](DESIGN.md#governance)).
- **`spec` evolution is additive-only** within a `spec` major: readers reject a higher `spec` value rather than guess at it. Breaking changes bump `spec` and ship with a mechanical migrator.
- **Unknown fields are errors**, misplaced ones included: `min_os` inside `[source]` fails lint rather than being silently ignored, and `[build]` on a `type = "binary"` package fails the same way.

---

<a id="worked-examples"></a>

## 9. Worked examples

<a id="minimal--zlib-no-buildstar-at-all"></a>

### 9.1 Minimal — zlib (no build.star at all)

```toml
spec = 1

[package]
name        = "zlib"
version     = "1.3.1"
revision    = 0
license     = "Zlib"
description = "Compression library"
homepage    = "https://zlib.net"
maintainers = ["maintainer <m@example.com>"]
tier        = "core"

[[source]]
url    = "https://zlib.net/zlib-1.3.1.tar.gz"
sha256 = "9a93b2b7…"

[build]
system = "cmake"
```

<a id="version-normalization--openssl-style-letter-patches"></a>

### 9.2 Version normalization — openssl-style letter patches

```toml
[package]
name    = "openssl1"
version = "1.1.1.23"            # upstream 1.1.1w (w = 23)
revision = 0
# …
[[source]]
url              = "https://www.openssl.org/source/old/1.1.1/openssl-1.1.1w.tar.gz"
sha256           = "cf309895…"
upstream_version = "1.1.1w"
```

<a id="virtual-provider--blas"></a>

### 9.3 Virtual provider — BLAS

```toml
[package]
name = "openblas"
version = "0.3.27"
# …
[provides]
blas = "3.11"
```

A dependent writes `runtime = ["blas ^3"]`; the profile's provider choice — `openblas` by default — is recorded in the lock as the concrete package.

<a id="full-featured--ffmpeg"></a>

### 9.4 Full-featured — ffmpeg

The full formula is the one developed through §2 and §3, `orchards/core/ffmpeg/`: conditional dependencies, provider-variant requirements, an audit CPE, a declarative service-free install. It is the reference formula that the linter's test suite round-trips.

<a id="vendor-binary--a-pkg-only-tool-with-a-legacy-artifact"></a>

### 9.5 Vendor binary — a pkg-only tool with a legacy artifact

The full form is in §3.11; the shape to remember is **two `[[binary]]` artifacts** — the vendor's 10.11–10.13 legacy build and its 10.14+ current build — sharing one signer pin, `redistribute = false` so clients fetch from the vendor directly, and a `[[binary.payload]]` map that constitutes the entire install. A machine on 10.12 receives the legacy artifact, a machine on 12 the current one, and the solver never shows either machine the other's slice. No installer script runs on either.

---

## Appendix. Field index

| Section | Fields |
|---|---|
| top-level | `spec` |
| `[package]` | `name` `version` `revision` `epoch` `license` `description` `homepage` `documentation` `maintainers` `keywords` `tier` `type` `min_os` `max_os` `flavors` |
| `[[source]]` | `url` `git` `commit` `sha256` `mirrors` `into` `upstream_version` + `[source.pgp]` (`key_url`, `fingerprint`) |
| `[[patch]]` | `file` `sha256` |
| `[variants.*]` | `default` `abi` `description` `conflicts` `requires` `min_os` `flavors` |
| `[depends]` | `runtime` `build` `test` — entries: `name [constraint] [+variant] [?condition]` |
| interop | `provides` (map), `conflicts`, `replaces`, `aliases` |
| `[install]` | `links_priority`, `link`, `link_reason`, `notes`, `[[install.data_dir]]`, `[install.completions]` |
| `[service]` | `run` `domain` `keep_alive` `run_at_load` `working_dir` `environment` `log_dir` `user_name` |
| `[audit]` | `cpe`, `eol`, `eol_date` |
| `[build]` | `system`, `args`, `skip_tests` |
| `[[binary]]` (type=binary) | `url` `sha256` `format` `min_os` `max_os` `arch` (`x86_64` default; `i386` / universal allowed, required i386-only execution ⇒ `max_os ≤ 10.14`, derived) `signer` `notarized` `redistribute` + `[[binary.payload]]` (`from`, `to`) |
| `[[binary.graft]]` | `path` `sha256` `when` (`pre` \| `post`) + behavior manifest: `writes` `kexts` `daemons` `network` `elevated` |
| `[system]` | `kexts` `sip_off_required` `reason` |
| `[runtime]` | `abi_epoch` `shims` `extension_scan_dir` + `[[runtime.env]]` (`var`, `value`) |
| `[extension]` | `runtime` `loader` `module` |
| `[ride]` | `runtime` `entry` |
| `[deprecation]` | `date` `reason` `replacement` `disable_date` |
| `[livecheck]` | `strategy` `url` `regex` `skip_prerelease` `throttle_days` `cooldown_days` |
| `[system-patch]` | `targets` `sip_off_required` `reason` |
| lock file | `lock_version`, `generated_by`, `[[repositories]]` (namespace, identity, environment, index_digest), `[machine]`, `[[package]]` (incl. `origin` = `slice` \| `local-build` \| `vendor-direct`) |

## History

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v0.18 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v0.17 | September 2026 | resolve stale summaries and example comments for build flags, vendor-key null fields, required i386 execution, and protected system-patch closures. These corrections follow STATE-AND-RECOVERY and SYSTEM-VOLUMES; schema structure is unchanged. |
| v0.16 | Not recorded | adds the TOOLCHAIN.md companion reference; no schema changes |
| v0.15 | Not recorded | adds **grafts** — declared vendor installer scripts for binary packages: `[[binary.graft]]` pins each script by hash and carries an exhaustive behavior manifest (`writes`, `kexts`, `daemons`, `network`, `elevated`) that doubles as its execution sandbox policy (§3.11; model and approval flow in DESIGN v1.19 §12.15, user-side declaration in SETUP §2.8). The payload-only default is unchanged: undeclared scripts still never run on any path. |
| v0.14 | Not recorded | follows the declarative-setup rename in §7.1's cross-reference: the machine file is now `aslice-machine.toml`, applied with `aslice machine apply` (SETUP.md v0.9; DESIGN v1.18 §12.13); lock replay stays top-level `aslice apply aslice.lock` — no schema or semantic changes. |
| v0.13 | Not recorded | drops the variant cap from §3.5 and the lint list (policy moved to need-plus-honest-tags, DESIGN §13.2), softens the §3.11 example's redistribution comment to mechanics only, and adds `takedown` to the §3.14 lifecycle reasons. |
| v0.12 | Not recorded | adds a NOMENCLATURE.md vocabulary reference to the header; no schema or semantic changes. |
| v0.11 | Not recorded | review pass — stray trailing whitespace removed from the §4.1 grammar block; no schema or semantic changes. |
| v0.10 | Not recorded | rewrites the prose throughout — every explanatory passage reworded for clarity, pace, and voice; no schema, semantic, or factual changes. |
| v0.9 | Not recorded | is an editorial pass — prose revised for directness; no schema or semantic changes. |
| v0.8 | Not recorded | §7.1 notes that `aslice apply` is now the unified convergence verb — saved plans, lock files, and declarative `setup.toml` documents (SETUP.md; DESIGN v1.11 §12.13). |
| v0.7 | Not recorded | review corrections — §3.16's serving rule now matches REPOSITORIES §3 as amended (official/local by default; verified only via the explicit per-repo `allow-system-patch` grant; third-party never), and §3.8 documents `aslice link`/`aslice unlink` for `link = false` packages (DESIGN v1.10 §12.1). |
| v0.6 | Not recorded | lands the lifecycle and freshness declarations specified for package authors and defined by ORCHARD-POLICY v0.4 §1: **`[deprecation]`** replaces the retired `[package] deprecated` boolean (§3.14), **`[livecheck]`** declares upstream freshness tracking (§3.15), **`[install]`** gains `link`/`link_reason` (explicit profile linking) and the `notes` caveats field (§3.8), the `build.star` ctx API gains **`ctx.replace`** (§6.3), and **`[system-patch]`** declares flagged replacement of Apple-provided files (§3.16; mechanism in DESIGN §12.11). |
| v0.5 | Not recorded | adds the **multi-version runtime declarations**: `[runtime]` marks a runtime formula (shim set, ABI epoch, per-version userbase environment injection, extension scan dir), `[extension]` binds a compiled extension slice to a runtime's ABI epoch, and `[ride]` marks an interpreter-target tool that launches under the currently selected runtime (§3.13; mechanism in DESIGN §12.9). |
| v0.4 | Not recorded | adds the **`[system]` declaration** for kernel extensions and SIP-disabled development tools (§3.12; mechanism and warnings in DESIGN §12.7) and replaces the checksummed-plist `[[install.service]]` with the **generated-plist `[service]` table** — the manifest describes the service, aslice writes the launchd plist (§3.8; lifecycle and stop–swap–restart upgrades in DESIGN §12.8). |
| v0.3 | Not recorded | opens **32-bit and universal vendor payloads**: `arch` may include `"i386"`, with the 10.14 execution ceiling derived from the artifact itself and enforced at lint and solve time (§3.11). |
| v0.2 | Not recorded | adds **vendor binary packages** — `type = "binary"`, `[[binary]]` artifacts with per-OS support tags, declarative payload maps, and mandatory signer pinning (§3.11); lock-file `origin` gains `"vendor-direct"` (§7.2). |
| Not recorded | September 2026 | corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending. |
| v0.19 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |
| v0.20 | September 2026 | Remove retired comparison references and competitive framing; retain aslice requirements and link their owning specifications. Align affected contract summaries where applicable. |
| v0.21 | September 2026 | Specify dependency-driven security remediation, explicit update and origin decisions, and the applicable farm, maintenance, and evidence contracts. Supersedes ABI-only rebuild and cost-first selection policies where previously stated; runtime and measured acceptance remain pending. |

</details>
