% ASLICE-INSTALL(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-install — install packages

# SYNOPSIS

`aslice install` [*options*] *package*…

`aslice reinstall` [*options*] *package*…

# DESCRIPTION

Installs the newest eligible packages, then prefers binaries for that selection: resolves the request against the index, selects the newest version compatible with this OS release and the fastest flavor this CPU executes, downloads the slices, verifies signatures and hashes, checks library interfaces against the installed set, and links a new generation. No undeclared package code executes at any point — a package whose installer genuinely requires a script declares it as a graft, which runs only after its behavior manifest has been shown and approved (aslice-graft(1)). Preparation failures leave the live generation unchanged. Failures after live changes enter journal recovery; external conflicts may require attention, and protected-volume changes may require Recovery and reboot. Package rollback does not restore application data ([STATE-AND-RECOVERY §5](../docs/STATE-AND-RECOVERY.md#durable-transactions-and-recovery); [SYSTEM-VOLUMES §4](../docs/SYSTEM-VOLUMES.md#activation-rollback-and-os-updates)).

*package* may be a bare name (`ffmpeg`), a version constraint (`ffmpeg@v6`), a namespaced name (`audiolab:convolver`), or a runtime stream (`php@8.4` — installing a stream never changes the selected one; see aslice-use(1)).

Space-separated packages, including mixed-orchard requests, form one transaction.
Pre-commit failure rolls back the complete managed-state batch. Display effective
settings per package before authorization; package-specific batch options identify
their target rather than using stateful **--for** scoping. Busy interactive commands
offer wait or exit, and unattended waiting requires an explicit request.

Commit precedes service health checks. Checks default to 60 seconds per service,
with positive finite overrides. Failure returns nonzero and reports committed
installation. The initiator or an authenticated administrator may request stopping:
before commit attempt rollback; after commit stop checks safely and report incomplete
verification. Effective mutation ownership lasts through checks and surviving helper writes.

**reinstall** performs a fresh link of the same version, repairing damaged profile entries.

# OPTIONS

**--build-from-source**
:   Compile locally instead of using a slice. Dependencies still resolve to binaries where possible.

**--variant** *package*:±*name*
:   Enable or disable a declared feature variant for the identified package. An unqualified variant remains valid for a single package; ambiguous batch options and unknown targets are refused. Interface-changing variants (`abi = true`) produce a distinct build identity; others trigger a local build with the same compatibility key and a distinct artifact identity. aslice reports whether a prebuilt slice exists for the combination before compiling.

**--cflags**="…", **--ldflags**="…", **--lto**, **--debug**
:   Compiler and linker flags for a local build of the named package only. Exact flags enter the artifact manifest. ABI-neutral choices may share a compatibility key; different outputs retain distinct artifact identities. Substitution still requires compatible CPU/OS requirements, ABI evidence, and dependent tests. Unsupported ABI-changing flags are rejected unless represented by a declared ABI variant; unknown effects require an isolated build and explicit dependency validation ([STATE-AND-RECOVERY §1](../docs/STATE-AND-RECOVERY.md#compatibility-and-artifact-identity) and [STATE-AND-RECOVERY §2](../docs/STATE-AND-RECOVERY.md#abi-and-execution-requirements)).

**--cflags** *package*:"…", **--ldflags** *package*:"…"
:   Package-targeted batch forms, for example `--cflags 'ffmpeg:-O3'`. Targets must identify an exact requested package, including its namespace for non-core packages. Reject ambiguous targets and conflicting duplicate assignments. Source-build, LTO, debug, and link options take `PACKAGE:true` or `PACKAGE:false` in batches; flavor, runtime, and extension-source options take `PACKAGE:VALUE`. Match the complete requested identifier, including a requested version, before parsing the value. Unqualified forms remain valid for one package. See [STATE-AND-RECOVERY §10.2.5](../docs/STATE-AND-RECOVERY.md#1025-command-requests-and-outcomes).

**--health-timeout** *duration*
:   Per-service health timeout after commit, default `60s`. Accept a positive finite integer with `ms`, `s`, or `m`; reject zero and overflow. Failure or timeout reports committed installation and returns nonzero.

**--runtime** *name@stream*
:   For runtime extensions: bind to the given stream instead of the currently selected one.

**--with-extensions-from** *stream*
:   When installing a new runtime stream: provision the extension set of an existing stream for it.

**--accept-system-changes**
:   Required consent for declared `[system]` and `[system-patch]` packages in non-interactive use. There is no persistent "always accept."

**--accept-grafts**
:   Consent, for this run only, to grafts not already covered by a recorded approval or the `[grafts]` allow-list. The behavior manifest is printed either way; without consent, non-interactive use refuses with exit status 2. See aslice-graft(1).

**--allow-eol**
:   Permit installing a package past its upstream's end-of-life. The install is announced and logged either way.

**--install**
:   With `use`/`pin`: install the requested stream if absent (see aslice-use(1)).

**--dry-run**, **--explain**, **--json**
:   Print the plan without changing anything; show the solver's derivation; machine-readable output.

# EXAMPLES

```sh
aslice install ffmpeg
aslice install ffmpeg --variant ffmpeg:+x265 --cflags="-O3 -march=native"
aslice install ffmpeg audiolab:convolver --variant ffmpeg:+x265 --cflags 'ffmpeg:-O3'
aslice install php@8.4 --with-extensions-from 8.3
aslice install foo --accept-system-changes
aslice install convolver --accept-grafts
```

# SOURCE-BUILD CONSENT

The plan discloses source compilation and its dependency reasons. Interactive
execution asks before compiling; unattended execution requires
**--allow-source-builds** for newly required builds. Saved plans and locks convey
no consent. Refusal returns 2 and never silently selects an older cached binary.
Version-1 plans/locks are rejected; regenerate version 2 from authenticated records
and explicit provider/replacement selections. Exact replay retains exact artifacts.

# EXIT STATUS

The common statuses in [aslice(1)](aslice.1.md#exit-status) apply where
relevant: 0 success, 1 error or recovery required, 2 plan refused, 4 contention
without unresolved recovery, and 130 safely completed cancellation. No additional
family-specific numeric statuses are specified.

# SEE ALSO

aslice(1), aslice-upgrade(1), aslice-uninstall(1), aslice-use(1), aslice-graft(1), [MANUAL §3](../docs/MANUAL.md#everyday-commands) and [MANUAL §4](../docs/MANUAL.md#how-installs-actually-work)
