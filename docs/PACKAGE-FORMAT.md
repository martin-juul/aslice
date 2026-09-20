# aslice Package Format

**Status:** Format draft, v0.6 — September 2026
**Change log:** v0.2 adds **vendor binary packages** — `type = "binary"`, `[[binary]]` artifacts with per-OS support tags, declarative payload maps, and mandatory signer pinning (§3.11); lock-file `origin` gains `"vendor-direct"` (§7.2). v0.3 opens **32-bit and universal vendor payloads**: `arch` may include `"i386"`, with the 10.14 execution ceiling derived from the artifact itself and enforced at lint and solve time (§3.11). v0.4 adds the **`[system]` declaration** for kernel extensions and SIP-disabled development tools (§3.12; mechanism and warnings in DESIGN §12.7) and replaces the checksummed-plist `[[install.service]]` with the **generated-plist `[service]` table** — the manifest describes the service, aslice writes the launchd plist (§3.8; lifecycle and stop–swap–restart upgrades in DESIGN §12.8). v0.5 adds the **multi-version runtime declarations**: `[runtime]` marks a runtime formula (shim set, ABI epoch, per-version userbase environment injection, extension scan dir), `[extension]` binds a compiled extension slice to a runtime's ABI epoch, and `[ride]` marks an interpreter-target tool that launches under the currently selected runtime (§3.13; mechanism in DESIGN §12.9). v0.6 lands the lifecycle and freshness declarations proposed in HOMEBREW-REVIEW §8 and made normative policy by ORCHARD-POLICY v0.4 §1: **`[deprecation]`** replaces the retired `[package] deprecated` boolean (§3.14), **`[livecheck]`** declares upstream freshness tracking (§3.15), **`[install]`** gains `link`/`link_reason` (the principled keg-only) and the `notes` caveats field (§3.8), the `build.star` ctx API gains **`ctx.replace`** (§6.3), and **`[system-patch]`** declares flagged replacement of Apple-provided files (§3.16; mechanism in DESIGN §12.11)
**Companion to:** [DESIGN.md](DESIGN.md) — this document is the authoritative specification for §6 (Package Format). Where they disagree, this document wins.
**Scope:** the `package.toml` definition format, `build.star` build API, dependency and version semantics, transitive resolution, and lock files.

---

## 1. Philosophy

If you know npm's `package.json`, you know the shape of this format — and you should also know where we deliberately part ways with it:

| npm convention | aslice decision | Why |
|---|---|---|
| `scripts.postinstall` — arbitrary code at install | **Does not exist.** Binary installs execute zero package code (DESIGN §10.1) | npm's install scripts are its largest supply-chain hole; we start without one |
| Semver, loosely enforced | Semver-derived, **strictly normalized and validated** (§4) | A solver is only as good as its version algebra |
| `package-lock.json` | `aslice.lock`, first-class and machine-aware (§7) | Locks record µarch flavor — a dimension npm doesn't have |
| `dependencies` / `devDependencies` | `runtime` / `build` / `test`, plus **conditional** dependencies (§5.3) | Native builds have three distinct dependency lifecycles |
| Anything goes in unknown fields | Schema-validated, unknown fields **rejected** | Silent typos in package metadata are a real supply-chain bug class |
| Prebuilt native addons via `node-gyp`/prebuild-install (untyped blobs) | **Vendor binaries are first-class, typed packages** with OS-support tags and pinned signers (§3.11) | Half the software worth having on this platform will never be buildable from source |

The format is **data first**: `package.toml` is pure TOML, validatable without executing anything. Build *logic*, where needed, lives in a separate hermetic Starlark file that runs only inside the build sandbox (DESIGN §10.5).

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

Directory name **must** equal `package.name`. One directory = one package lineage (all versions of `ffmpeg` live in one formula; the orchard git history is the version history).

A `type = "binary"` package (§3.11) is `package.toml` **alone** — no `build.star`, no patches; there is nothing to build and nothing to patch.

---

## 3. `package.toml` — full schema

Every formula carries `spec = 1` — the format version. Readers reject unknown `spec` values and unknown fields, so the format can evolve without silent misreads.

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

Lifecycle state is deliberately *not* a `[package]` field: EOL flags live in `[audit]` (§3.9), and the deprecation lifecycle — active → deprecated → disabled → tombstoned — is declared in `[deprecation]` (§3.14).

### 3.2 Platform bounds — minimum OS, maximum OS

```toml
[package]
min_os = "10.12"    # oldest macOS this formula builds/runs on; default "10.11"
max_os = "12"       # optional; omit unless upstream genuinely breaks on newer
```

- `min_os` sets the package's deployment target **and** its index visibility: a 10.11 machine simply never sees packages with `min_os = "10.12"` — filtered at solve time with an explicit "requires macOS ≥ 10.12" message, never a runtime surprise.
- The value is one of `"10.11"`, `"10.12"`, `"10.13"`, `"10.14"`, `"10.15"`, `"11"`, `"12"` — the supported window, verbatim.
- Honesty rule (DESIGN §4.1): declare the real floor. Do not contort a build to claim 10.11.
- For `type = "binary"` packages, `[[binary]]` entries carry their own bounds per artifact (§3.11); the `[package]` values are the defaults they inherit.

### 3.3 `flavors` — minimum instruction set

```toml
[package]
flavors = ["v2", "v3"]    # omit → all of ["v1", "v2", "v3"]
```

- A package that genuinely requires AVX2 (e.g., hand-written AVX2 kernels without a dispatch fallback) declares `flavors = ["v3"]` and the farm skips its `v1`/`v2` slices; v1/v2 machines get a clear solve-time message.
- The toolchain injects the flavor's `-march=x86-64-vN` floor automatically (§6.3); formula authors never write `-march` themselves. User `-march=native` requests layer on top at install time (DESIGN §7.4) without touching identity.
- `min_os` and `flavors` are orthogonal and both part of the build identity (DESIGN §7.2).
- Meaningless for `type = "binary"` (nothing is compiled — the vendor chose the ISAs); the field is rejected there. Vendor binaries serve all flavors by construction.

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

- **Every source is content-pinned.** Archives: sha256. Git: full commit hash. Mutable refs (`branch = "main"`) are rejected by `aslice lint`.
- **PGP verification** is optional and additional: `[source.pgp] key_url = "…", fingerprint = "…"` — the fingerprint is pinned in the formula, so key substitution still fails closed.
- Git submodules are forbidden; express them as additional `[[source]]` entries so they are pinned and mirrored.
- Patches live in `patches/` and are listed with their hashes:

```toml
[[patch]]
file   = "patches/0001-fix-darwin15-clock.patch"
sha256 = "a1b2c3…"
```

### 3.5 `[variants.*]` — feature switches with ABI honesty

```toml
[variants.x265]
default     = true
abi         = true        # changes the exported interface → enters build identity (DESIGN §7.2)
description = "HEVC encoding via x265"

[variants.debug]
default     = false
abi         = false       # build-flavor only; never enters identity
description = "Build with debug symbols"

[variants.lto]
default     = false
abi         = false
conflicts   = ["debug"]               # optional: mutually exclusive variants
requires    = []                      # optional: variant prerequisites
```

- `abi = true` variants are capped at 6 per package by policy (DESIGN §13.2) and each must name, in `description`, the interface it changes.
- Variants may carry their own platform bounds: `min_os = "10.13"`, `flavors = ["v2", "v3"]` inside a `[variants.*]` table narrow that variant's availability.
- Rejected on `type = "binary"` packages — a vendor artifact has no build-time switches.

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

Full dependency semantics in §5. `build` and `test` dependencies are rejected on `type = "binary"` packages; `runtime` is valid (a vendor tool can legitimately need aslice's openssl).

### 3.7 Interop declarations — provides, conflicts, replaces

```toml
[provides]
blas = "3.11"          # virtual package provided, with version; satisfies `depends: ["blas ^3"]`

conflicts = ["ffmpeg4", "libav"]      # cannot be installed into the same profile
replaces  = ["ffmpeg4"]               # rename/supersede: upgrades replace the old package atomically
aliases   = ["ff"]                    # search/install aliases, no semantics
```

- `provides` is how interchangeable implementations interop: `openblas`, `blis`, and Accelerate-shim all `provide blas`; dependents name the virtual, the solver picks a provider (default: configurable per profile, `aslice profile prefer blas openblas`).
- `conflicts` is for *identity* conflicts. **File collisions are detected automatically** from manifests and never need declaration; profile-level priority resolves them (DESIGN §8.2).

### 3.8 `[install]` — declarative post-install behavior

Everything here is applied by aslice itself — not by package code:

```toml
[install]
links_priority = 50                     # collision priority in profiles; default 50
link           = true                   # false: install into the store without linking into profiles
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

aslice **generates** the launchd plist from `[service]` at enable time — the formula ships no plist file and no code. `ProgramArguments[0]` resolves through the profile (`/opt/aslice/profiles/default/bin/…`), never a store path, so upgrades and rollbacks need no plist edit; the label is `org.aslice.<name>`. `domain = "system"` jobs run as root, are installed and removed by `aslice-system` with per-operation consent (DESIGN §10.4), and may only be served by repositories holding the `system` capability (REPOSITORIES §3) — user agents are unprivileged and ungated. A package declares at most one `[service]`; software with multiple daemons is split into multiple packages. The full lifecycle — `aslice service list/status/start/stop/restart/run`, and the stop–swap–restart upgrade transaction — is DESIGN §12.8.

`link = false` is the principled keg-only (REVIEW §4.5): the package installs into the store but nothing links into profiles — versioned lineages (`openssl@3` style) and anything shipping `bin/` names colliding with `/usr/bin` or `/bin` default to it in core (policy: ORCHARD-POLICY §6). `aslice link <pkg>` opts in per profile, and dependents never need the link at all: dependency resolution is store-path-based (`ctx.deps`), so "unlinked but depended upon" is a normal state, not a hack. `link_reason` is lint-enforced when `link = false` and tells the user *why* — it is displayed by `info` and at install time. `notes` is the caveats field: an array of human-readable, genuinely actionable post-install lines ("config lives in …", "run `aslice service start postgresql` to …"), printed at install and shown by `info`. If it isn't actionable, it isn't a note (ORCHARD-POLICY §14).

### 3.9 `[audit]` — vulnerability matching and lifecycle

```toml
[audit]
cpe      = "cpe:2.3:a:ffmpeg:ffmpeg"   # binds the package to CVE feeds
eol      = false
eol_date = "2027-03-01"                # optional upstream EOL announcement
```

`aslice audit` joins installed packages against OSV/GitHub Advisory data via CPE and name aliases. Packages with `eol = true` require `--allow-eol` to install and are excluded from the core orchard (DESIGN §13.1). Vendor binaries should carry a `cpe` whenever one exists — they are opaque to source-level analysis, so feed matching is the whole safety net.

### 3.10 `[build]` — the declarative build shortcut

```toml
[build]
system = "cmake"                        # autotools | cmake | meson | cargo | go | make | custom
args   = ["-DENABLE_GPL=ON", "-DENABLE_LIBX265=ON"]
```

If `system` is one of the known build systems, **no `build.star` is needed** — aslice runs the canonical phase sequence (configure with the system-typical flags, parallel build, DESTDIR install, then the ABI scan). `system = "custom"` requires `build.star` (§6). An autotools hello-world formula is literally `[package]` + `[[source]]` + `[build] system = "autotools"`. Forbidden on `type = "binary"` — there is no build.

### 3.11 `[[binary]]` — vendor binaries (pkg/dmg-only software)

Some software will never exist as buildable source for this platform — vendor CLIs, commercial audio tools, frozen releases of abandoned apps. It enters the ecosystem as a **vendor binary package**: a `package.toml`-only formula describing one or more vendor artifacts, each tagged with the OS releases it supports.

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
arch      = ["x86_64", "i386"]          # universal; i386 present ⇒ max_os ≤ "10.14" (derived)
signer    = "Developer ID Application: Vendor Inc. (ABCD1234)"   # pinned; change = hard fail
notarized = false                       # pre-notarization-era artifact; expected and announced
redistribute = false                    # license forbids rehosting: clients fetch vendor URL

[[binary]]                              # the vendor's current build, for newer machines
url       = "https://vendor.example/vendorcli-3.2.1.pkg"
sha256    = "bb22…"
format    = "pkg"
min_os    = "10.14"
arch      = ["x86_64"]
signer    = "Developer ID Application: Vendor Inc. (ABCD1234)"
notarized = true
redistribute = false

[[binary.payload]]                      # declarative extraction map — scripts never run
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

- **`type = "binary"` forbids `[build]`, `build.star`, `[[patch]]`, `[[source]]`, `[variants]`, and `build`/`test` dependencies.** Nothing is compiled, nothing is patched. The pipeline compresses to `fetch → verify (hash + signer) → extract payload → abi-scan → pack → sign` (§6.1).
- **Installer scripts never execute.** `.pkg` `preinstall`/`postinstall` scripts and `.dmg` autolaunch are ignored — the payload map is the entire install. A package whose function requires its scripts is rejected at review (DESIGN §13.1), not accommodated.
- **Signer pinning is mandatory** for signed artifacts; `notarized` records the expectation (checked on 10.14+ where notarization exists). The verifier hard-fails on signer change: silent signer substitution upstream is how binary distribution gets owned. Unsigned vendor artifacts are allowed in extended with `signer` omitted, and are announced loudly at install (DESIGN §12.2).
- **`redistribute` is required.** `true` → the farm repackages the payload as a hosted slice (best UX: atomic, resumable, rollback-able). `false` → every client fetches the vendor URL itself, hash- and signer-pinned; the index carries the formula but no blob. A mutated or pulled vendor artifact fails loudly at the hash check, never silently installs something else.
- **`arch` defaults to `["x86_64"]`** — aslice-built packages are x86_64-only, always (DESIGN §2.2 N6). Vendor payloads may additionally declare `"i386"` alone or universal `["x86_64", "i386"]`, because 32-bit code still executes on 10.11–10.14 and much of the pkg/dmg-only software worth having (audio plugins, lab instruments, frozen pro tools) ships that way.
- **The 32-bit ceiling is derived, not declared.** macOS 10.15 removed 32-bit execution entirely. At pack/lint time the verifier inspects every Mach-O slice in the payload (lipo-style fat-header parsing); an artifact containing i386 code **must** declare `max_os = "10.14"` or lower, and the declared value is checked against what the binaries actually contain. Disagreement is a lint error; on 10.15+ machines the solver refuses with a clear "requires 32-bit support, removed in macOS 10.15" message.
- **Universal payloads install whole.** `lipo -thin` extraction is forbidden: thinning a fat binary invalidates the vendor's code signature, and signer integrity outranks disk savings. The store receives the artifact exactly as signed.
- **Pre-notarization-era artifacts are expected.** Software old enough to be 32-bit usually predates notarization (10.14+) and sometimes Developer ID signing entirely. `notarized = false` (or an omitted `signer`, extended tier only) is normal for these packages and is announced loudly at install, not blocked.
- **Flavor doesn't apply.** `build_id` excludes `flavor` and `toolchain_id`; one slice serves every flavor. The ABI scan still runs on the payload at pack time — dependents link against vendor dylibs through the same ABI contract as farm-built libraries (DESIGN §7.3).
- **OS tags are verified, not trusted.** At pack/repack time the declared `min_os`/`max_os` are checked against the bundle's `LSMinimumSystemVersion`, Mach-O minimum-version load commands, and the pkg Distribution's `allowed-os-versions` where present; disagreement is a lint error.
- **Version normalization still applies** (§4) — vendor spellings like `3.2 Update 1` normalize per the rules, with the verbatim string preserved in `upstream_version`.

### 3.12 `[system]` — kernel extensions and SIP-disabled tools (v0.4)

```toml
[system]
kexts            = ["Library/Extensions/FooAudio.kext"]  # payload-relative paths to install
sip_off_required = false     # true: the software cannot function while SIP is enabled
reason           = "Kernel driver for FooAudio USB interfaces"   # mandatory; this IS the warning text
```

Either a non-empty `kexts` or `sip_off_required = true` (or both) marks a system package; `reason` is mandatory whenever `[system]` is present and is shown verbatim in the install warning — write it like warning text. Kext paths are payload-relative and must live under `Library/Extensions/`; the linter rejects anything else. The mechanism — `aslice-system` elevation, the warning flow, `csrutil` checks, trust gating, rollback — is DESIGN §12.7; acceptance policy is ORCHARD-POLICY §13. `[system]` composes with `type = "binary"` (vendor kexts, §3.11) and with `[service]` (a driver that also runs a daemon, §3.8).

### 3.13 `[runtime]`, `[extension]`, `[ride]` — multi-version runtimes (v0.5)

A **runtime formula** — php, nodejs, ruby, python, and anything else users keep several versions of — declares how aslice multiplexes it (mechanism: DESIGN §12.9):

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

- `shims` names the tools that multiplex through the shim layer: aslice installs a shim for each name, and the profile links only the **versioned aliases** (`bin/php8.4`, derived from the stream) — the bare name belongs to the shim layer, and lint rejects any other package attempting to link it.
- `abi_epoch` is the granularity at which the runtime's *extension* ABI breaks: minor for php/python/ruby (`"8.4"`, `"3.12"`, `"3.3"`), major for nodejs (`"22"`). It is a fact about upstream's ABI policy, restated per version; the linter cross-checks it against `version`, and a patch release never changes it. Extension builds key on it (below), and the shim uses it to name the per-version userbase.
- `extension_scan_dir` (optional) is the profile-relative directory where aslice writes loader files for `[extension]` packages bound to this runtime; `{epoch}` expands to `abi_epoch`. Required for runtimes whose extensions are activated by config file (php); omitted where the runtime has no such convention.
- `[[runtime.env]]` declares environment injected by the shim at exec time — the mechanism that binds ecosystem-native installs (pip, gem, npm, pecl, composer global) to the resolved version's writable **userbase**. Template variables: `{userbase}` (`~/.aslice/runtimes/<name>/<epoch>`), `{profile}` (the live profile), `{store}` (the resolved runtime's store path), `{epoch}`, `{extension_scan_dir}`. Values are otherwise literal — no shell expansion, ever. Only `[runtime]` formulae may declare env injection: it exists to redirect ecosystem package managers into per-version territory, not as a general environment mechanism.

An **extension formula** — a compiled module for a runtime — declares its binding:

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

- The solver reads `[extension]` as a dependency on the runtime **at a specific ABI epoch**: the stream selected at install time (DESIGN §12.9's session → project → default resolution, or `--runtime php@8.3`). The epoch enters the extension's build identity (DESIGN §7.2 gains a `runtime_epoch` term for these packages), so `php-redis` for php 8.3 and 8.4 are distinct store paths that coexist exactly like flavors — and the farm prebuilds the extension × supported-epoch × flavor matrix.
- The build compiles against the concrete runtime store path (`ctx.deps["php"]` — headers, `phpize`, `php-config` all present), sandboxed as ever; nothing about §6 changes.
- aslice generates `loader` into the epoch-keyed scan dir at link time, pointing at `module` inside the extension's own store path — so extension sets are generation-managed: rollback restores runtime and extension set together (DESIGN §12.9). `loader`/`module` are required iff the bound runtime declares `extension_scan_dir`.
- `depends.runtime` must not repeat the bound runtime — `[extension]` already expresses it, and a duplicate carrying a conflicting constraint is a lint error.

A **riding tool** — an interpreter-target tool with no native linkage against the runtime (composer, yarn, prettier, poetry) — declares:

```toml
[ride]
runtime = "php"                         # launched under the currently selected runtime
entry   = "lib/composer/composer.phar"  # payload path handed to the runtime
```

The tool's shim performs two-step resolution at exec time: the runtime stream via session → project → default, then `exec <runtime>/bin/php <tool-store>/<entry>`. Whether a tool may ride is a fact about its code, not a preference: lint rejects `[ride]` when the payload's ABI scan shows linkage against runtime libraries (such a tool is an `[extension]`-style binding or a self-contained package). Riders carry no runtime version constraint of their own — following the user's selection is the point.

### 3.14 `[deprecation]` — the package lifecycle, declared (v0.6)

Replaces the retired `[package] deprecated` boolean: deprecation is a lifecycle with dates and reasons, not a flag (policy: ORCHARD-POLICY §8; origin: REVIEW §4.3).

```toml
[deprecation]
date         = "2027-03-01"    # when deprecation starts
reason       = "upstream-eol"  # upstream-eol | security | renamed | unmaintainable | other
replacement  = "ffmpeg7"       # optional pointer; mandatory when reason = "renamed"
disable_date = "2027-09-01"    # optional: new installs refuse after this without --force-disabled
```

Semantics: **active → deprecated** — installs and `info`/`audit` warn with `reason` and `replacement`; existing installs are unaffected and the package still receives slices. **Deprecated → disabled** — at `disable_date`, new installs refuse without `--force-disabled`; existing installs keep working and remain in locks. **Disabled → tombstoned** — the formula leaves orchard HEAD, but the index keeps a permanent tombstone (name, final version, reason, replacement) so historical snapshots and old locks resolve forever. Upstream-EOL packages in extended carry `reason = "upstream-eol"` indefinitely as normal life, not failure (ORCHARD-POLICY §8). The security fast path — straight to disabled by maintainer vote — is policy, not schema.

### 3.15 `[livecheck]` — upstream freshness, declared (v0.6)

How the orchard's automation finds new upstream releases (origin: REVIEW §4.2; freshness policy: ORCHARD-POLICY §9):

```toml
[livecheck]
strategy        = "git-tags"       # git-tags | homepage-regex | directory-index | crates | npm | pypi | sparkle
url             = "https://github.com/FFmpeg/FFmpeg/tags"   # strategy-specific
regex           = "^n([\\d.]+)$"   # optional pattern → version capture
skip_prerelease = true             # default true
throttle_days   = 3                # don't bump more often than this; default 3
cooldown_days   = 2                # wait after upstream release — supply-chain poisoning window; default 2, minimum 2
```

Required for core packages, encouraged in extended; a core package whose livecheck strategy rots is a bug against its named maintainer (ORCHARD-POLICY §9). `aslice livecheck [pkg|--all]` queries, machine-readable. The scheduled orchard sweep opens autobump PRs — new `version`, bot-fetched `sha256`, `revision` reset to 0, changelog link — which merge only through the same gates as any PR; `aslice bump-pr <pkg> <version>` is the human path. The cooldown may be raised for historically risky ecosystems (npm, PyPI, RubyGems, crates), never lowered below 2.

### 3.16 `[system-patch]` — flagged replacement of Apple-provided files (v0.6)

The strictest declaration in the format. A system-patch package replaces an Apple-provided file — the original backed up, the replacement a profile symlink, restore byte-exact (mechanism and consent flow: DESIGN §12.11; acceptance policy: ORCHARD-POLICY §13).

```toml
[system-patch]
targets          = ["/usr/bin/openssl"]   # absolute paths this package replaces
sip_off_required = false     # true: the replacement cannot be performed while SIP is enabled
reason           = "10.11's openssl is a 0.9.8-era tool that cannot speak modern TLS"  # mandatory; IS the warning text
```

- `targets` names tools, configs, and data by absolute path — never the shared library space. The refused-by-construction list — the kernel, `dyld`, `libSystem`, anything under `/System`, and any dylib or framework in a platform binary's load path — is lint-enforced and not negotiable in review (ORCHARD-POLICY §13).
- `reason` is mandatory whenever `[system-patch]` is present and is shown verbatim at every decision point — write it like warning text, exactly as with `[system]` (§3.12).
- Serving requires the repository **`system-patch` capability** (REPOSITORIES §3): official and local repositories only — verified and third-party never. Non-interactive installation requires `--accept-system-changes`; there is no "always allow" (DESIGN §12.11).

---

## 4. Versioning

### 4.1 The version type

aslice versions are **SemVer 2.0 plus one extension**: an optional fourth numeric component for lettered-patch upstreams. Formally:

```
version  := epoch? core ("." patch4)? ("-" prerelease)? 
epoch    := <uint> "!"          (rarely needed; §4.4)
core     := <uint> "." <uint> "." <uint>
patch4   := <uint>              (only for upstreams with letter/scheme patches)
```

Ordering: epoch first, then numeric core components, then patch4, then prerelease (SemVer rules). Build metadata (`+…`) is **not** used — identity is the build_id's job (DESIGN §7.2), not the version's.

### 4.2 Normalization (upstream → aslice)

The orchard records `version` in normalized form; the upstream spelling lives in `source.upstream_version` when they differ:

| Upstream tag | Normalized | Rule |
|---|---|---|
| `v7.1` | `7.1.0` | Strip leading `v`; pad to three components |
| `1.3` | `1.3.0` | Pad |
| `2.0.0-rc.2` | `2.0.0-rc.2` | Prerelease passes through (SemVer spelling required) |
| `1.1.1k` | `1.1.1.11` | Letter patch → patch4 (`a`=1 … `z`=26) |
| `2024.09.1` | `2024.9.1` | CalVer with numeric components passes through |
| `r4520` / `git describe` hashes | **rejected** | Use epoch + a synthetic version, chosen by the maintainer |

Prereleases sort before their release (`7.1.0-rc.1 < 7.1.0`) and are **excluded from default resolution**: you get one only if you ask (`aslice install ffmpeg --prerelease` or an explicit constraint).

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

Constraints compose with conditionals and provider-variant requirements in any order: `"x265 ^3.5 +asm ?variant.x265"`.

### 4.4 Revision and epoch

- **`revision`** bumps when the recipe changes but upstream doesn't (patch added, dependency range fixed, rebuild against a new ABI). `7.1.0-1` sorts after `7.1.0-0`. Revisions are orchard-visible and *not* part of upstream identity.
- **`epoch`** exists for the day an upstream changes its versioning scheme or a maintainer ships a mistaken higher version that must be rolled back: `epoch = 1` outranks every `epoch = 0` version regardless of the rest. It is a controlled break-glass mechanism, logged loudly at install time.

---

## 5. Dependency semantics

### 5.1 The three kinds

| Kind | Needed when | Propagates transitively? |
|---|---|---|
| `build` | compiling this package | **No** — build tools never leak into a consumer's closure |
| `runtime` | linking against or executing this package | **Yes** — the runtime closure is recursive |
| `test` | `tests.star` only | No |

A library consumer records *which provider build it linked against* via the ABI contract (DESIGN §7.3). Upgrading a provider whose `compatibility_version` and symbol fingerprint still cover its clients requires **no** dependent rebuilds; a provider that regresses forces the solver to either hold it back or plan dependent rebuilds — stated explicitly in the plan, never discovered later.

### 5.2 Transitive resolution

Resolution is PubGrub over the full graph (DESIGN §7.5), with these aslice-specific rules:

1. **Single-version-per-profile by default.** A profile links one build of a given name (the store can hold many; the *profile* points at one). Libraries needing side-by-side majors are separate package names: `openssl@3` and (if ever needed) `openssl@4` — an orchard naming convention, not a solver exception. Multi-version **runtimes** are the designed exception (`[runtime]`, §3.13): the store holds every installed stream, the profile links each stream's versioned aliases (`bin/php8.4`), and the bare name (`php`) multiplexes through the shim layer instead of a profile link (DESIGN §12.9).
2. **Version unification.** If `a` needs `dep ^1.2` and `b` needs `dep ^1.4`, the profile gets one `dep` satisfying both (`^1.4`), or the solve fails with the conflict rendered as a derivation tree (`--explain`).
3. **Build deps float.** Two packages may build against different `nasm` versions without conflict; only runtime identity is unified in a profile.
4. **Cycles** are rejected at lint time for runtime edges; build-time cycles (rare, e.g., bootstrap compilers) require an explicit `bootstrap = true` edge annotation with a pinned seed slice.

### 5.3 Conditional dependencies

| Conditional | Meaning |
|---|---|
| `"x265 ?variant.x265"` | only when *this package's* `x265` variant is enabled |
| `"macfuse ?os>=10.14"` | only on matching OS releases |
| `"intel-mkl ?flavor>=v2"` | only when the target flavor is at least v2 (flavors are ordered `v1 < v2 < v3`) |

Conditionals are evaluated at solve time against the machine's OS and flavor and the chosen variant assignment — so the dependency graph the solver sees is exactly the graph that will be built.

### 5.4 Provider-variant requirements

`"sdl2 +metal ^2.28"` requires a provider whose build identity includes `+metal` (an `abi = true` variant). Because identity covers ABI variants, this is a hash-level match — the solver either finds a slice with that identity or plans a source build of the provider with that variant. There is no "close enough."

---

## 6. Build instructions

### 6.1 Phase model

Every build, declarative or custom, runs the same phase sequence under the sandbox profiles of DESIGN §10.5:

```
fetch → verify → unpack → patch → configure → build → install(staging) → abi-scan → test → pack(.slice) → sign
```

`fetch` is the only phase with network access. `abi-scan` is always run by aslice itself and cannot be skipped by a formula — the ABI contract is not optional metadata.

For `type = "binary"` packages (§3.11) the pipeline compresses to `fetch → verify (hash + signer) → extract payload → abi-scan → pack → sign` — nothing is compiled, and embedded installer scripts are never executed. Extraction runs under the same no-network unpack sandbox profile as source archives (DESIGN §10.5).

### 6.2 Declarative builds

`[build].system` covers the common cases with the system-idiomatic defaults: `configure`-with-prefix for autotools, out-of-tree `-DCMAKE_INSTALL_PREFIX` for cmake, `meson setup --prefix`, `cargo build --release` with `--locked` enforced (vendored or lockfile-pinned dependencies only — see §6.5), and so on. Per-phase overrides without going full `custom`:

```toml
[build]
system = "cmake"
args   = ["-DENABLE_GPL=ON"]
skip_tests = false
```

### 6.3 `build.star` — the custom API

Starlark, deterministic, no network, filesystem confined to the build dir (DESIGN §6.1). The `ctx` object is the entire capability surface:

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
| `ctx.user_cflags` / `ctx.user_ldflags` | string | User flags from install time (DESIGN §7.4); appended, recorded, never identity-affecting |
| `ctx.patch(file)` | fn | Apply a checksummed patch from `patches/` |
| `ctx.replace(file, pattern, replacement)` | fn | In-place text substitution for trivial fixups without a patch file (Homebrew's `inreplace`, its most-used helper); count-checked — zero replacements is a build error, never a silent no-op |

Environment determinism is set by the builder, not the formula: `LC_ALL=C`, `TZ=UTC`, `SOURCE_DATE_EPOCH` pinned to the source timestamp, prefix-mapping flags for reproducibility (DESIGN §9.5). A formula that needs something outside this API is a bug report against aslice, not a sandbox escape.

### 6.4 What the sandbox guarantees

Restating the security-relevant invariants that this format relies on: no network after `fetch`; no writes outside the build dir; no reads of the host environment; no code execution at slice-install time — including vendor installer scripts, which are never run on any path (§3.11); `tests.star` runs network-free unless the formula declares `test_network = true` (loudly logged).

### 6.5 Language-ecosystem sub-managers

Crates, modules, and gems that fetch their own dependencies are allowed **only** in lockfile-pinned, vendored form: `cargo build --locked --offline` against a `[[source]]`-supplied vendor tarball, `go build` with a pinned `go.sum` and vendored modules, etc. Network access during build is denied, so any ecosystem dependency that isn't pinned in the formula fails closed and loudly.

---

## 7. Lock files

### 7.1 Who locks what

- **The orchard doesn't lock.** The signed index snapshot *is* the global lock: every package in it names exact versions, build identities, and source hashes.
- **The machine locks.** Every profile has a lock recording the exact resolved state. It lives at `/opt/aslice/profiles/<name>/aslice.lock` and is rewritten atomically with every generation (so `aslice rollback` restores both the symlinks *and* the lock that describes them).
- **Projects and fleets export locks.** `aslice lock export > aslice.lock` captures a profile for reproduction elsewhere; `aslice apply aslice.lock` replays it.

### 7.2 Format

```toml
lock_version = 1
generated_by = "aslice 0.3.0"
index_snapshot = "sha256:8f3a…"        # the TUF snapshot this lock resolved against

[machine]
os     = "12.7"
flavor = "v3"

[[package]]
name     = "ffmpeg"
version  = "7.1.0"
revision = 0
build_id = "2f4a9c1e"
flavor   = "v3"
min_os   = "10.11"
origin   = "slice"                     # slice | local-build | vendor-direct
variants = { x265 = true, debug = false }
digest   = "sha256:9be4…"              # slice manifest digest (what was verified)

[[package]]
name     = "x264"
version  = "0.164.0"
revision = 1
build_id = "77aa10b2"
flavor   = "v3"
min_os   = "10.11"
origin   = "slice"
variants = {}
digest   = "sha256:c001…"
```

`origin` values: `slice` (prebuilt, hosted), `local-build` (compiled on this machine with recorded flags), `vendor-direct` (a `redistribute = false` vendor package whose artifact was fetched from the vendor URL; the lock records the artifact hash and pinned signer so a replay verifies against exactly what was installed).

### 7.3 Portability semantics — exact by default, intent-preserving across flavors

A lock applied on a machine matching `machine.os`/`machine.flavor` reproduces **bit-identical build_ids** (verified against the same index snapshot or a newer one that still contains them). Applied on a *different* flavor or older OS, aslice re-resolves with the same versions and variants, swapping only build identities to the available flavor — and reports exactly what changed. Locks are thus exact where they can be and honest where they can't.

For `type = "binary"` packages, cross-OS portability means re-selecting the right `[[binary]]` artifact for the target machine's OS (§3.11) — the version stays pinned, the artifact adapts, and the report says so. When no artifact matches at all (e.g., an i386-only package whose lock is replayed on 10.15+), re-resolution fails with the reason spelled out — there is nothing to adapt to, and `--frozen` changes nothing.

`--frozen` mode refuses any re-resolution: mismatch is an error, not an adaptation. That's the CI mode.

---

## 8. Validation and tooling

- **`aslice lint <formula>`** — full schema validation plus policy checks (name rules, license validity, unpinned sources, submodule use, cycle detection, variant caps, `min_os` plausibility against the toolchain; for `type = "binary"`: payload-map completeness against the actual artifact, signer/notarization verification, OS-tag consistency with bundle metadata). Orchard CI runs lint + a sandboxed build (or payload extraction) on every PR (DESIGN §13.4).
- **`spec` evolution** — new format versions are additive-only within a `spec` major; readers reject higher `spec` values rather than guessing. Breaking changes bump `spec` and ship with a mechanical migrator.
- **Unknown fields are errors** — including misplaced ones (`min_os` inside `[source]` fails lint, not silently ignored; `[build]` on a `type = "binary"` package likewise).

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

A dependent says `runtime = ["blas ^3"]`; the profile's provider choice (`openblas` by default) is recorded in the lock as the concrete package.

### 9.4 Full-featured — ffmpeg

See `orchards/core/ffmpeg/` in §2/§3: conditional deps, provider-variant requirements, variant caps, audit CPE, declarative service-free install. It is the reference formula the linter's test suite round-trips.

### 9.5 Vendor binary — a pkg-only tool with a legacy artifact

The full form is in §3.11. The shape to remember: **two `[[binary]]` artifacts** (the vendor's 10.11–10.13 legacy build and its 10.14+ current build), one shared signer pin, `redistribute = false` so clients fetch the vendor URL directly, and a `[[binary.payload]]` map that is the entire install. A machine on 10.12 gets the legacy artifact; a machine on 12 gets the current one; the solver never shows either machine the other's slice — and no installer script runs on either.

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
| `[[binary]]` (type=binary) | `url` `sha256` `format` `min_os` `max_os` `arch` (`x86_64` default; `i386` / universal allowed, i386 ⇒ `max_os ≤ 10.14`, derived) `signer` `notarized` `redistribute` + `[[binary.payload]]` (`from`, `to`) |
| `[system]` | `kexts` `sip_off_required` `reason` |
| `[runtime]` | `abi_epoch` `shims` `extension_scan_dir` + `[[runtime.env]]` (`var`, `value`) |
| `[extension]` | `runtime` `loader` `module` |
| `[ride]` | `runtime` `entry` |
| `[deprecation]` | `date` `reason` `replacement` `disable_date` |
| `[livecheck]` | `strategy` `url` `regex` `skip_prerelease` `throttle_days` `cooldown_days` |
| `[system-patch]` | `targets` `sip_off_required` `reason` |
| lock file | `lock_version`, `generated_by`, `index_snapshot`, `[machine]`, `[[package]]` (incl. `origin` = `slice` \| `local-build` \| `vendor-direct`) |
