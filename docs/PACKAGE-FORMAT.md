# aslice Package Format

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

**Status:** Format draft, v0.18 — September 2026
**Companion to:** [DESIGN.md](DESIGN.md) — this document is the authoritative specification for §6 (Package Format). Where they disagree, this document wins. The toolchain this format's builds run on is specified in [TOOLCHAIN.md](TOOLCHAIN.md).
**Scope:** the `package.toml` definition format, `build.star` build API, dependency and version semantics, transitive resolution, and lock files.
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md) — project terms, acronyms, and the Homebrew translation table.

---

## 1. Philosophy

The quickest way to describe this format is by contrast. npm's `package.json` has the same broad job — describe a package and its dependencies — so the differences, tabulated below, are the design of this format in miniature:

| npm convention | aslice decision | Why |
|---|---|---|
| `scripts.postinstall` — arbitrary code at install | **Does not exist as a formula mechanism.** Builds and binary installs execute zero package code by default; a vendor installer script runs only as a declared, approved, sandboxed graft (§3.11; DESIGN §12.15) | npm's install scripts are its largest supply-chain hole; we start without one |
| Semver, loosely enforced | Semver-derived, **strictly normalized and validated** (§4) | A solver is only as good as its version algebra |
| `package-lock.json` | `aslice.lock`, first-class and machine-aware (§7) | Locks record µarch flavor — a dimension npm doesn't have |
| `dependencies` / `devDependencies` | `runtime` / `build` / `test`, plus **conditional** dependencies (§5.3) | Native builds have three distinct dependency lifecycles |
| Anything goes in unknown fields | Schema-validated, unknown fields **rejected** | Silent typos in package metadata are a real supply-chain bug class |
| Prebuilt native addons via `node-gyp`/prebuild-install (untyped blobs) | **Vendor binaries are first-class, typed packages** with OS-support tags and pinned signers (§3.11) | Half the software worth having on this platform will never be buildable from source |

The governing principle is **data first**. A `package.toml` is pure TOML: it can be validated, indexed, and audited without executing anything. Where a build needs real logic, that logic lives in a separate Starlark file, and it runs only inside the build sandbox (DESIGN §10.5).

---

## 2. Files of a package

```
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

## 3. `package.toml` — full schema

Every formula begins with `spec = 1`, the format version. A reader rejects a `spec` value it does not know, and rejects unknown fields at any level; the format can therefore evolve without old tools silently misreading new files.

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

### 3.2 Platform bounds — minimum OS, maximum OS

```toml
[package]
min_os = "10.12"    # oldest macOS this formula builds/runs on; default "10.11"
max_os = "12"       # optional; omit unless upstream genuinely breaks on newer
```

- `min_os` does two jobs: it sets the package's deployment target, and it controls index visibility. A 10.11 machine never sees a package with `min_os = "10.12"`; the solver filters it out and says why ("requires macOS ≥ 10.12"), rather than letting the failure surface at run time.
- Legal values are exactly the supported window: `"10.11"`, `"10.12"`, `"10.13"`, `"10.14"`, `"10.15"`, `"11"`, `"12"`.
- Declare the real floor (DESIGN §4.1). A build that needs contortions to claim 10.11 does not support 10.11.
- For `type = "binary"` packages, each `[[binary]]` artifact carries bounds of its own (§3.11); the `[package]` values are the defaults an artifact inherits.

### 3.3 `flavors` — minimum instruction set

```toml
[package]
flavors = ["v2", "v3"]    # omit → all of ["v1", "v2", "v3"]
```

- A package that genuinely needs AVX2 — hand-written AVX2 kernels with no dispatch fallback, say — declares `flavors = ["v3"]`. The farm then skips its `v1`/`v2` slices, and v1/v2 machines get a clear solve-time message.
- The toolchain, not the formula, supplies the flavor's `-march=x86-64-vN` floor (§6.3); formula authors never write `-march` themselves. A user's `-march=native` request layers on top at install time (DESIGN §7.4). ABI-neutral choices may share a compatibility key; exact flags and CPU requirements enter the artifact manifest. ABI-changing flags require a declared ABI variant or are rejected, and unknown effects require an isolated build and explicit dependency validation (STATE-AND-RECOVERY §2).
- `min_os` and `flavors` are orthogonal axes, and both enter the build identity (DESIGN §7.2).
- `flavors` remains a source-build axis. Vendor artifacts instead require `cpu_features` and `requires_i386`, describing actual execution requirements. Nothing being compiled does not imply compatibility with every CPU (STATE-AND-RECOVERY §2).

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

- Each `abi = true` variant's `description` must name the interface it changes (policy: DESIGN §13.2). There is no cap — a package declares as many variants as its users need.
- A variant may carry platform bounds of its own: `min_os = "10.13"` or `flavors = ["v2", "v3"]` inside a `[variants.*]` table narrows where that variant is available.
- `[variants.*]` is rejected on `type = "binary"` packages; a vendor artifact has no build-time switches to describe.

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

### 3.7 Interop declarations — provides, conflicts, replaces

```toml
conflicts = ["ffmpeg4", "libav"]      # cannot be installed into the same profile
replaces  = ["ffmpeg4"]               # rename/supersede: upgrades replace the old package atomically
aliases   = ["ff"]                    # search/install aliases, no semantics

[provides]
blas = "3.11"          # virtual package provided, with version; satisfies `depends: ["blas ^3"]`
```

- `provides` is the interop mechanism for interchangeable implementations: `openblas`, `blis`, and the Accelerate shim all provide `blas`. A dependent names the virtual package; the solver picks a provider, and the default is configurable per profile (`aslice profile prefer blas openblas`).
- `conflicts` expresses *identity* conflicts only. File collisions need no declaration: aslice detects them from the manifests and resolves them by profile-level priority (DESIGN §8.2).

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

The plist itself never ships in the formula. aslice **generates** it from `[service]` at enable time, writes it with the label `org.aslice.<name>`, and points `ProgramArguments[0]` through the profile (`/opt/aslice/profiles/default/bin/…`) rather than at a store path — so an upgrade or rollback that swaps store paths leaves the plist untouched. `domain = "system"` jobs run as root; they are installed and removed by `aslice-system`, each operation individually consented to (DESIGN §10.4), and only repositories holding the `system` capability may serve them (REPOSITORIES §3). User agents are unprivileged and ungated. A package declares at most one `[service]`; software with several daemons is packaged as several packages. The full lifecycle — `aslice service list/status/start/stop/restart/run`, and the stop–swap–restart upgrade transaction — is specified in DESIGN §12.8.

`link = false` is the principled form of Homebrew's keg-only (REVIEW §4.5): the package installs into the store, and nothing links into any profile. In core it is the default for versioned lineages (`openssl3` style) and for anything whose `bin/` names collide with `/usr/bin` or `/bin` (policy: ORCHARD-POLICY §6); `aslice link <pkg>` opts a package into a profile explicitly. Dependents never need the link: dependency resolution works on store paths (`ctx.deps`), so being depended upon while unlinked is a normal state. When `link = false`, lint requires `link_reason`, and `info` and the installer display it — the user is told why the package did not appear in the profile. Finally, `notes` is the caveats field: human-readable, actionable post-install lines ("config lives in …", "run `aslice service start postgresql` to …"), printed at install and shown by `info`. A line that isn't actionable isn't a note (ORCHARD-POLICY §14).

### 3.9 `[audit]` — vulnerability matching and lifecycle

```toml
[audit]
cpe      = "cpe:2.3:a:ffmpeg:ffmpeg"   # binds the package to CVE feeds
eol      = false
eol_date = "2027-03-01"                # optional upstream EOL announcement
```

`aslice audit` joins the installed set against OSV and GitHub Advisory data, matching on CPE and name aliases. A package with `eol = true` installs only with `--allow-eol` and is excluded from the core orchard (DESIGN §13.1). For vendor binaries a `cpe` should be present whenever one exists: the payload is opaque to source-level analysis, so feed matching is the entire safety net.

### 3.10 `[build]` — the declarative build shortcut

```toml
[build]
system = "cmake"                        # autotools | cmake | meson | cargo | go | make | custom
args   = ["-DENABLE_GPL=ON", "-DENABLE_LIBX265=ON"]
```

When `system` names a known build system, **no `build.star` is needed**: aslice runs the canonical phase sequence for that system — configure with the system-typical flags, parallel build, DESTDIR install, ABI scan. `system = "custom"` is the escape hatch and requires `build.star` (§6). The result is that an autotools hello-world formula is exactly three tables: `[package]`, `[[source]]`, and `[build] system = "autotools"`. `[build]` is forbidden on `type = "binary"` packages, which have no build.

### 3.11 `[[binary]]` — vendor binaries (pkg/dmg-only software)

A nontrivial share of the software worth having on this platform will never exist as buildable source: vendor CLIs, commercial audio tools, frozen releases of abandoned applications. Such software enters the ecosystem as a **vendor binary package** — a formula consisting of `package.toml` alone, describing one or more vendor artifacts, each tagged with the OS releases it supports.

```toml
spec = 1

[package]
name    = "vendorcli"
type    = "binary"
version = "3.2.1"
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
arch      = ["x86_64", "i386"]          # universal; the ceiling follows required i386-only execution
signer    = "Developer ID Application: Vendor Inc. (ABCD1234)"   # pinned; change = hard fail
notarized = false                       # pre-notarization-era artifact; expected and announced
redistribute = false                    # clients fetch the vendor URL themselves

[[binary]]                              # the vendor's current build, for newer machines
url       = "https://vendor.example/vendorcli-3.2.1.pkg"
sha256    = "bb22…"
format    = "pkg"
min_os    = "10.14"
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
- **Installer scripts never run by default; declared grafts are the exception.** A `.pkg`'s `preinstall`/`postinstall` scripts and a `.dmg`'s autolaunch are ignored unless the formula declares them as grafts (below, and DESIGN §12.15): hash-pinned, described by an exhaustive behavior manifest, approved by the user before running, executed under a manifest-derived sandbox, and captured so rollback and uninstall reverse their footprint. Software that genuinely needs its scripts — audio DSP drivers, pro-video plugins, kext installers — is packageable this way; an undeclared script still never runs on any path, and a package whose undeclared scripts are load-bearing remains rejected at review (DESIGN §13.1).
- **Signer pinning is mandatory** for signed artifacts, and `notarized` records the notarization expectation (checked on 10.14+, where notarization exists). The verifier hard-fails if the signer changes: silent signer substitution upstream is how binary distribution channels get compromised. An unsigned vendor artifact is allowed in extended with `signer` omitted, and the omission is announced at install (DESIGN §12.2).
- **`redistribute` is required; there is no default.** `true` means the farm repackages the payload as a hosted slice — atomic, resumable, rollback-able. `false` means every client fetches the vendor URL itself, hash- and signer-pinned, and the index carries the formula but no blob. A mutated or pulled vendor artifact fails at the hash check rather than silently installing something else.
- **`arch` defaults to `["x86_64"]`.** aslice's own builds are x86_64-only, always (DESIGN §2.2 N6). A vendor payload may additionally declare `"i386"`, alone or universal as `["x86_64", "i386"]`: 32-bit code still executes on 10.11–10.14, and much of the pkg/dmg-only software worth having — audio plugins, lab instruments, frozen pro tools — ships that way.
- **The 32-bit ceiling follows required execution.** Required i386-only executables/helpers/plugins impose `max_os <= "10.14"`. A fat executable with a usable x86_64 member does not require i386 merely because an alternative member exists. Lint checks the declared entry points and dependency paths and requires evidence for ambiguous plugins (STATE-AND-RECOVERY §2).
- **Universal payloads install whole.** Thinning a fat binary with `lipo -thin` would invalidate the vendor's code signature, and signer integrity outranks disk savings; the extraction is forbidden, and the store receives the artifact exactly as signed.
- **Pre-notarization-era artifacts are expected, not merely tolerated.** Software old enough to contain 32-bit code usually predates notarization (10.14+) and sometimes predates Developer ID signing altogether. `notarized = false` — or, in the extended tier, an omitted `signer` — is the normal case for these packages; it is announced at install, never blocked.
- **Execution requirements still apply.** Vendor compatibility keys set compiler/flavor fields to null and bind the vendor digest. Every artifact records CPU features and whether execution requires i386. ABI scanning retains exact dependency bindings when evidence is incomplete (STATE-AND-RECOVERY §2).
- **OS tags are verified, not trusted.** At pack/repack time, each artifact's declared `min_os`/`max_os` is checked against the bundle's `LSMinimumSystemVersion`, the Mach-O minimum-version load commands, and — where present — the pkg Distribution's `allowed-os-versions`. Disagreement is a lint error.
- **Version normalization still applies** (§4): a vendor spelling like `3.2 Update 1` normalizes by the usual rules, and the verbatim string is preserved in `upstream_version`.

**Declared grafts — `[[binary.graft]]`.** When vendor software genuinely requires its installer scripts, the formula declares each script as a graft under the model of DESIGN §12.15:

```toml
[[binary.graft]]
path     = "Scripts/postinstall"    # path inside the artifact (pkg Scripts/, or dmg-resident)
sha256   = "cc33…"                  # pinned; a mutated script is a hard fail, not a surprise
when     = "post"                   # pre | post — relative to payload extraction
writes   = ["/Library/Audio/Plug-Ins/HAL/VendorDSP.driver"]  # every path it may write
kexts    = ["com.vendor.dspdriver"] # kext bundle IDs it may install or load; omit if none
daemons  = ["com.vendor.dspd"]      # launchd jobs it may install; omit if none
network  = false                    # default; true only for scripts that genuinely need it
elevated = true                     # run via aslice-system as root (DESIGN §10.4)
```

- **The script is hash-pinned** (`path`, `sha256`): the farm verifies the hash at rehearsal and the client verifies it again before execution, so an upstream-mutated script fails rather than runs unreviewed.
- **The behavior manifest is exhaustive.** `writes`, `kexts`, `daemons`, and `network` together are the sandbox policy: the graft executes under a manifest-derived profile that permits exactly the declared behavior, and any deviation aborts the install and rolls the generation back (DESIGN §12.15). An omitted or empty field means none, not unknown.
- **Approval is per package and version, recorded** in the state DB or declared in the machine file's `[grafts] allow` list (SETUP §2.8); non-interactive installs refuse unless `--accept-grafts` is passed, and there is no always-allow switch (DESIGN §12.15).
- **`elevated = true` routes execution through `aslice-system`** (DESIGN §10.4) — the only path on which package-associated code runs as root. A non-elevated graft runs as the installing user.
- **The farm rehearses and signs the manifest** for core and extended, and the index carries the signed manifest so clients can show the user exactly what a graft will do — and show the unsigned-manifest warning when no signature exists (REPOSITORIES §3) — before approval.

### 3.12 `[system]` — kernel extensions and SIP-disabled tools (v0.4)

```toml
[system]
kexts            = ["Library/Extensions/FooAudio.kext"]  # payload-relative paths to install
sip_off_required = false     # true: the software cannot function while SIP is enabled
reason           = "Kernel driver for FooAudio USB interfaces"   # mandatory; this IS the warning text
```

A package becomes a system package by declaring either a non-empty `kexts` or `sip_off_required = true` (or both). `reason` is mandatory whenever `[system]` is present, and aslice shows it verbatim in the install warning — so write it as warning text, not as a description. Kext paths are payload-relative and must live under `Library/Extensions/`; the linter rejects anything else. The mechanism — `aslice-system` elevation, the warning flow, `csrutil` checks, trust gating, rollback — is specified in DESIGN §12.7, and the acceptance policy in ORCHARD-POLICY §13. `[system]` composes with `type = "binary"` (vendor kexts, §3.11) and with `[service]` (a driver that also runs a daemon, §3.8).

### 3.13 `[runtime]`, `[extension]`, `[ride]` — multi-version runtimes (v0.5)

Users routinely keep several versions of php, nodejs, ruby, and python installed at once. A **runtime formula** tells aslice how to multiplex among them (mechanism: DESIGN §12.9):

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

- To the solver, `[extension]` is a dependency on the runtime **at a specific ABI epoch** — whichever stream install-time resolution selects (DESIGN §12.9's session → project → default chain, or an explicit `--runtime php@8.3`). The epoch enters the extension's build identity: DESIGN §7.2 gains a `runtime_epoch` term for these packages, so `php-redis` built for php 8.3 and for php 8.4 are distinct store paths that coexist the way flavors do, and the farm prebuilds the extension × supported-epoch × flavor matrix.
- The build itself is unremarkable: it compiles against the concrete runtime store path, reached as `ctx.deps["php"]`, with headers, `phpize`, and `php-config` all present, under the same sandbox as any other build. Nothing in §6 changes.
- At link time aslice writes `loader` into the epoch-keyed scan dir, pointing at `module` inside the extension's own store path. Extension sets are therefore generation-managed, and a rollback restores runtime and extension set together (DESIGN §12.9). `loader` and `module` are required exactly when the bound runtime declares `extension_scan_dir`.
- `depends.runtime` must not repeat the bound runtime: `[extension]` already expresses that dependency, and a duplicate carrying a conflicting constraint is a lint error.

A **riding tool** targets the interpreter without linking against it natively — composer, yarn, prettier, and poetry are the canonical cases. It declares:

```toml
[ride]
runtime = "php"                         # launched under the currently selected runtime
entry   = "lib/composer/composer.phar"  # payload path handed to the runtime
```

At exec time the tool's shim resolves in two steps: first the runtime stream (session → project → default), then `exec <runtime>/bin/php <tool-store>/<entry>`. Whether a tool may ride is a fact about its code, not a packaging preference: if the payload's ABI scan shows linkage against runtime libraries, lint rejects `[ride]` — such a tool is an `[extension]`-style binding or a self-contained package. A rider carries no runtime version constraint of its own; following the user's selection is what riding means.

### 3.14 `[deprecation]` — the package lifecycle, declared (v0.6)

`[deprecation]` replaces the retired `[package] deprecated` boolean. A boolean can say that a package is deprecated; it cannot say since when, why, or what to use instead. Deprecation here is a lifecycle with dates and reasons (policy: ORCHARD-POLICY §8; origin: REVIEW §4.3):

```toml
[deprecation]
date         = "2027-03-01"    # when deprecation starts
reason       = "upstream-eol"  # upstream-eol | security | renamed | unmaintainable | takedown | other
replacement  = "ffmpeg7"       # optional pointer; mandatory when reason = "renamed"
disable_date = "2027-09-01"    # optional: new installs refuse after this without --force-disabled
```

The transitions work as follows. **Active → deprecated:** installs and `info`/`audit` warn with `reason` and `replacement`; existing installs are unaffected, and the package still receives slices. **Deprecated → disabled:** at `disable_date`, new installs refuse without `--force-disabled`; existing installs keep working and remain in locks. **Disabled → tombstoned:** the formula leaves orchard HEAD, but the index keeps a permanent tombstone — name, final version, reason, replacement — so that historical snapshots and old locks resolve forever. Two further rules are policy rather than schema: an upstream-EOL package in extended may carry `reason = "upstream-eol"` indefinitely as normal life, not failure (ORCHARD-POLICY §8); and the security fast path, straight to disabled by owner approval during single-owner launch, is a policy decision the schema merely permits. `reason = "takedown"` records a verified rights-holder complaint (ORCHARD-POLICY §8); hosted slices stop being served, and the tombstone preserves the record.

### 3.15 `[livecheck]` — upstream freshness, declared (v0.6)

`[livecheck]` tells the orchard's automation how to find new upstream releases (origin: REVIEW §4.2; freshness policy: ORCHARD-POLICY §9):

```toml
[livecheck]
strategy        = "git-tags"       # git-tags | homepage-regex | directory-index | crates | npm | pypi | sparkle
url             = "https://github.com/FFmpeg/FFmpeg/tags"   # strategy-specific
regex           = "^n([\\d.]+)$"   # optional pattern → version capture
skip_prerelease = true             # default true
throttle_days   = 3                # don't bump more often than this; default 3
cooldown_days   = 2                # wait after upstream release — supply-chain poisoning window; default 2, minimum 2
```

`[livecheck]` is required for core packages and encouraged in extended; a core package whose livecheck strategy rots is a bug against its named maintainer (ORCHARD-POLICY §9). `aslice livecheck [pkg|--all]` runs the query by hand, machine-readable. The scheduled orchard sweep opens autobump PRs — new `version`, bot-fetched `sha256`, `revision` reset to 0, changelog link — and they merge only through the same gates as any other PR; the human path is `aslice bump-pr <pkg> <version>`. The cooldown may be raised for historically risky ecosystems (npm, PyPI, RubyGems, crates); it may never drop below 2.

### 3.16 `[system-patch]` — flagged replacement of Apple-provided files (v0.6)

This is the strictest declaration in the format. A system-patch package replaces an Apple-provided file through the protected helper. Originals and metadata remain in root-owned storage; executable replacements and their dependencies come from a verified root-owned closure. Supported symlinks target that closure, never the user-writable profile (STATE-AND-RECOVERY §3). The OS-specific backend governs application and restoration, including Recovery and reboot where needed (SYSTEM-VOLUMES). The mechanism and consent flow are specified in DESIGN §12.11, the acceptance policy in ORCHARD-POLICY §13.

```toml
[system-patch]
targets          = ["/usr/bin/openssl"]   # absolute paths this package replaces
sip_off_required = false     # true: the replacement cannot be performed while SIP is enabled
reason           = "10.11's openssl is a 0.9.8-era tool that cannot speak modern TLS"  # mandatory; IS the warning text
```

- `targets` names tools, configs, and data files by absolute path — never the shared library space. Some targets are refused by construction: the kernel, `dyld`, `libSystem`, anything under `/System`, and any dylib or framework in a platform binary's load path. The list is lint-enforced and not negotiable in review (ORCHARD-POLICY §13).
- `reason` is mandatory whenever `[system-patch]` is present, and is shown verbatim at every decision point. As with `[system]` (§3.12), write it as warning text.
- Serving a system-patch package requires the repository **`system-patch` capability** (REPOSITORIES §3). Official and local repositories hold it by default; a verified repository receives it only through the user's explicit per-repo grant (`aslice repo allow-system-patch <name>`), which is refused by default and revocable; third-party repositories can never hold it. Non-interactive installation requires `--accept-system-changes`; there is no "always allow" (DESIGN §12.11).

---

## 4. Versioning

### 4.1 The version type

An aslice version is **SemVer 2.0 with one extension**: an optional fourth numeric component, added for upstreams that letter their patches. Formally:

```
version  := epoch? core ("." patch4)? ("-" prerelease)?
epoch    := <uint> "!"          (rarely needed; §4.4)
core     := <uint> "." <uint> "." <uint>
patch4   := <uint>              (only for upstreams with letter/scheme patches)
```

Ordering compares epoch first, then the numeric core components, then patch4, then prerelease, under the usual SemVer rules. Build metadata (`+…`) is **not** used: identity is the build_id's job (DESIGN §7.2), not the version's.

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

### 4.4 Revision and epoch

- **`revision`** bumps when the recipe changes while upstream does not: a patch added, a dependency range fixed, a rebuild against a new ABI. `7.1.0-1` sorts after `7.1.0-0`. Revisions are orchard bookkeeping and form no part of upstream identity.
- **`epoch`** exists for two bad days: the day an upstream changes its versioning scheme, and the day a maintainer ships a mistaken higher version that must be rolled back. `epoch = 1` outranks every `epoch = 0` version regardless of the remaining components. It is a break-glass mechanism, and its use is announced at install time.

---

## 5. Dependency semantics

### 5.1 The three kinds

| Kind | Needed when | Propagates transitively? |
|---|---|---|
| `build` | compiling this package | **No** — build tools never leak into a consumer's closure |
| `runtime` | linking against or executing this package | **Yes** — the runtime closure is recursive |
| `test` | `tests.star` only | No |

A library's consumer records *which provider build it linked against* through the ABI contract (DESIGN §7.3). When an upgraded provider's `compatibility_version` and symbol fingerprint still cover its clients, no dependent rebuilds are needed. When a provider regresses, the solver must either hold the provider back or plan rebuilds of its dependents — and the plan says so explicitly, up front.

### 5.2 Transitive resolution

Resolution is PubGrub over the full graph (DESIGN §7.5). Four rules adapt it to aslice:

1. **Single version per profile, by default.** A profile links exactly one build of a given name; the store may hold many, but the profile points at one. Libraries that need side-by-side majors are packaged under separate names — `openssl3` and, if ever needed, `openssl@4` — which is an orchard naming convention, not a solver exception. The designed exception is multi-version **runtimes** (`[runtime]`, §3.13): the store holds every installed stream, the profile links each stream's versioned aliases (`bin/php8.4`), and the bare name (`php`) multiplexes through the shim layer in place of a profile link (DESIGN §12.9).
2. **Version unification.** When `a` needs `dep ^1.2` and `b` needs `dep ^1.4`, the profile gets one `dep` satisfying both (`^1.4`) — or the solve fails, rendering the conflict as a derivation tree (`--explain`).
3. **Build dependencies float.** Two packages in the same profile may have been built against different `nasm` versions; only runtime identity is unified.
4. **Cycles** in runtime edges are rejected at lint time. Build-time cycles — rare, but bootstrap compilers need them — require an explicit `bootstrap = true` edge annotation together with a pinned seed slice.

### 5.3 Conditional dependencies

| Conditional | Meaning |
|---|---|
| `"x265 ?variant.x265"` | only when *this package's* `x265` variant is enabled |
| `"macfuse ?os>=10.14"` | only on matching OS releases |
| `"intel-mkl ?flavor>=v2"` | only when the target flavor is at least v2 (flavors are ordered `v1 < v2 < v3`) |

Conditionals are evaluated at solve time, against the machine's OS and flavor and the chosen variant assignment. The dependency graph the solver works on is therefore the graph that will actually be built.

### 5.4 Provider-variant requirements

`"sdl2 +metal ^2.28"` demands a provider whose build identity includes `+metal` (an `abi = true` variant). Since identity covers ABI variants, the match happens at the hash level: the solver either finds a slice with exactly that identity or plans a source build of the provider with that variant. There is no "close enough."

---

## 6. Build instructions

### 6.1 Phase model

Declarative and custom builds alike run the same phase sequence, under the sandbox profiles of DESIGN §10.5:

```
fetch → verify → unpack → patch → configure → build → install(staging) → abi-scan → test → pack(.slice) → sign
```

Only `fetch` has network access. `abi-scan` is run by aslice itself and cannot be skipped by a formula: the ABI contract is not optional metadata.

The `pack` phase emits the container defined in [SLICE-FORMAT](SLICE-FORMAT.md), with a [slice descriptor](../schematics/json/slice.schema.json) and [artifact manifest](../schematics/json/artifact-manifest.schema.json). Package signing produces a detached signature over the frozen archive bytes. Any Apple signing that changes payload bytes precedes manifest generation and packing.

For `type = "binary"` packages (§3.11) the pipeline compresses to `fetch → verify (hash + signer) → extract payload → abi-scan → pack → sign`: nothing is compiled, and embedded installer scripts are never executed — declared grafts (§3.11) are extracted and hash-verified, not run by this pipeline; they execute only at farm rehearsal and at client install, each time under their own manifest-derived profile (DESIGN §12.15). Payload extraction runs under the same no-network unpack sandbox profile as source archives (DESIGN §10.5).

### 6.2 Declarative builds

`[build].system` covers the common cases with the defaults idiomatic to each system: `configure` with a prefix for autotools, out-of-tree `-DCMAKE_INSTALL_PREFIX` for cmake, `meson setup --prefix`, `cargo build --release` with `--locked` enforced (vendored or lockfile-pinned dependencies only, §6.5), and so on. Where the defaults need adjustment, per-phase overrides are available without going full `custom`:

```toml
[build]
system = "cmake"
args   = ["-DENABLE_GPL=ON"]
skip_tests = false
```

### 6.3 `build.star` — the custom API

The language is Starlark: deterministic, no network, filesystem confined to the build directory (DESIGN §6.1). The script's entire capability surface is the `ctx` object:

| Member | Type | Meaning |
|---|---|---|
| `ctx.prefix` | string | Final store path this build will occupy |
| `ctx.staging` | string | DESTDIR staging directory |
| `ctx.jobs` | int | Parallelism granted by the scheduler |
| `ctx.flavor` | string | `"v1"` / `"v2"` / `"v3"` — the `-march=x86-64-vN` floor is already in `CC`/`CXX` wrappers |
| `ctx.min_os` | string | Deployment target; already exported as `MACOSX_DEPLOYMENT_TARGET` |
| `ctx.variant(name)` | fn → bool | Variant assignment for this build |
| `ctx.deps` | dict | name → store path of each resolved build+runtime dependency |
| `ctx.env` | map | Controlled environment; `ctx.env.set(k, v)` / `ctx.env.append(k, v)`; reads of host env are denied |
| `ctx.run(argv…)` | fn | Exec, argv-array only — **no shell**, no string interpolation attacks |
| `ctx.make(*args)`, `ctx.cmake(*args)`, `ctx.meson(*args)` | fn | Tool helpers with correct defaults |
| `ctx.user_cflags` / `ctx.user_ldflags` | string | User flags from install time (DESIGN §7.4); appended and recorded in the artifact manifest; ABI-changing flags need a declared ABI variant, unknown effects need dependency validation |
| `ctx.patch(file)` | fn | Apply a checksummed patch from `patches/` |
| `ctx.replace(file, pattern, replacement)` | fn | In-place text substitution for trivial fixups without a patch file (Homebrew's `inreplace`, its most-used helper); count-checked — zero replacements is a build error, never a silent no-op |

The builder, not the formula, fixes the environment: `LC_ALL=C`, `TZ=UTC`, `SOURCE_DATE_EPOCH` pinned to the source timestamp, and prefix-mapping flags for reproducibility (DESIGN §9.5). If a formula needs something this API does not offer, the correct response is a bug report against aslice — not a sandbox escape.

### 6.4 What the sandbox guarantees

The security-relevant invariants this format relies on, collected in one place: no network after `fetch`; no writes outside the build directory; no reads of the host environment; no code execution at slice-install time, including vendor installer scripts, which never run on any path unless declared as grafts with an exhaustive behavior manifest (§3.11; DESIGN §12.15); and `tests.star` runs network-free unless the formula declares `test_network = true`, which is logged at warn.

### 6.5 Language-ecosystem sub-managers

Ecosystems whose tools fetch their own dependencies — crates, Go modules, gems — are admitted **only** in lockfile-pinned, vendored form: `cargo build --locked --offline` against a `[[source]]`-supplied vendor tarball, `go build` with a pinned `go.sum` and vendored modules, and so on. Because the build sandbox denies network access, an ecosystem dependency that is not pinned in the formula fails closed.

---

## 7. Lock files

### 7.1 Who locks what

- **The orchard doesn't lock.** It doesn't need to: the signed index snapshot *is* the global lock, since every package in it names exact versions, build identities, and source hashes.
- **The machine locks.** Every profile carries a lock recording its exact resolved state, at `/opt/aslice/profiles/<name>/aslice.lock`. The lock is rewritten atomically with every generation, so `aslice rollback` restores the symlinks and the lock describing them together.
- **Projects and fleets export locks.** `aslice lock export > aslice.lock` captures a profile for reproduction elsewhere, and `aslice apply aslice.lock` replays it. The machine-wide sibling is the declarative setup file: `aslice machine apply aslice-machine.toml` plans and converges a whole machine (SETUP.md; DESIGN §12.13).

### 7.2 Format

The machine-readable contract is [lock.tosd](../schematics/toml/lock.tosd), with a complete validation fixture in [lock.toml](../tests/fixtures/lock.toml). A lock records `lock_version`, profile, generated-by version, machine OS/flavor, per-repository identity/environment/index bindings, and exact package records.

Each package records its repository, name/version/revision, compatibility `build_id`, immutable `artifact_id`, archive `blob_digest`, authenticated `recipe_digest`, origin, resolved variants, flags, CPU/OS requirements, and exact runtime artifact dependencies. Vendor-direct records additionally bind the vendor URL, digest, and signer when signed. Local artifacts must accompany an exported lock for exact replay elsewhere. `digest` is not overloaded between a manifest and a vendor installer. [STATE-AND-RECOVERY §8](STATE-AND-RECOVERY.md#8-plans-locks-archives-and-offline-use) defines replay and trust checks.

### 7.3 Portability semantics — exact by default, intent-preserving across flavors

Applied on a machine matching `machine.os` and `machine.flavor`, a lock reproduces **identical artifact IDs and verified payloads**, verified against the same index snapshot or a newer one that still contains them. Applied on a different flavor or an older OS, aslice re-resolves: versions and variants are kept, build identities are swapped to what the flavor offers, and the report lists what changed. Locks are exact where they can be, and explicit about re-resolution where they cannot.

For `type = "binary"` packages, cross-OS portability means selecting a different `[[binary]]` artifact to match the target machine's OS (§3.11): the version stays pinned, the artifact adapts, and the report says so. If no artifact matches at all — an i386-only package whose lock is replayed on 10.15+, say — re-resolution fails with the reason spelled out; there is nothing to adapt to, and `--frozen` changes nothing.

`--frozen` refuses re-resolution of any kind: a mismatch is an error, never an adaptation. This is the mode CI should use.

---

## 8. Validation and tooling

- **`aslice lint <formula>`** runs full schema validation plus the policy checks: name rules, license validity, unpinned sources, submodule use, cycle detection, `min_os` plausibility against the toolchain — and, for `type = "binary"`, payload-map completeness against the actual artifact, signer and notarization verification, OS-tag consistency with bundle metadata — and, for every `[[binary.graft]]`, script-hash verification against the artifact plus behavior-manifest completeness (`writes`/`kexts`/`daemons`/`network` all explicitly declared, empty meaning none). Orchard CI runs lint plus a sandboxed build (or payload extraction) on every PR (DESIGN §13.4).
- **`spec` evolution is additive-only** within a `spec` major: readers reject a higher `spec` value rather than guess at it. Breaking changes bump `spec` and ship with a mechanical migrator.
- **Unknown fields are errors**, misplaced ones included: `min_os` inside `[source]` fails lint rather than being silently ignored, and `[build]` on a `type = "binary"` package fails the same way.

---

## 9. Worked examples

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

### 9.4 Full-featured — ffmpeg

The full formula is the one developed through §2 and §3, `orchards/core/ffmpeg/`: conditional dependencies, provider-variant requirements, an audit CPE, a declarative service-free install. It is the reference formula that the linter's test suite round-trips.

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
| lock file | `lock_version`, `generated_by`, `index_snapshot`, `[machine]`, `[[package]]` (incl. `origin` = `slice` \| `local-build` \| `vendor-direct`) |

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
| v0.6 | Not recorded | lands the lifecycle and freshness declarations proposed in HOMEBREW-REVIEW §8 and made normative policy by ORCHARD-POLICY v0.4 §1: **`[deprecation]`** replaces the retired `[package] deprecated` boolean (§3.14), **`[livecheck]`** declares upstream freshness tracking (§3.15), **`[install]`** gains `link`/`link_reason` (the principled keg-only) and the `notes` caveats field (§3.8), the `build.star` ctx API gains **`ctx.replace`** (§6.3), and **`[system-patch]`** declares flagged replacement of Apple-provided files (§3.16; mechanism in DESIGN §12.11). |
| v0.5 | Not recorded | adds the **multi-version runtime declarations**: `[runtime]` marks a runtime formula (shim set, ABI epoch, per-version userbase environment injection, extension scan dir), `[extension]` binds a compiled extension slice to a runtime's ABI epoch, and `[ride]` marks an interpreter-target tool that launches under the currently selected runtime (§3.13; mechanism in DESIGN §12.9). |
| v0.4 | Not recorded | adds the **`[system]` declaration** for kernel extensions and SIP-disabled development tools (§3.12; mechanism and warnings in DESIGN §12.7) and replaces the checksummed-plist `[[install.service]]` with the **generated-plist `[service]` table** — the manifest describes the service, aslice writes the launchd plist (§3.8; lifecycle and stop–swap–restart upgrades in DESIGN §12.8). |
| v0.3 | Not recorded | opens **32-bit and universal vendor payloads**: `arch` may include `"i386"`, with the 10.14 execution ceiling derived from the artifact itself and enforced at lint and solve time (§3.11). |
| v0.2 | Not recorded | adds **vendor binary packages** — `type = "binary"`, `[[binary]]` artifacts with per-OS support tags, declarative payload maps, and mandatory signer pinning (§3.11); lock-file `origin` gains `"vendor-direct"` (§7.2). |
| Not recorded | September 2026 | corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending. |

</details>
