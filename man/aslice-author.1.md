% ASLICE-AUTHOR(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-author — create, validate, build, and update formulae

# SYNOPSIS

`aslice create` *url*

`aslice lint` *formula*

`aslice build` *package-or-directory* [*build-options*]

`aslice build --reproduce` *package* *version* *flavor* *build-reference*

`aslice test` *package*

`aslice livecheck` [*package* | `--all`]

`aslice bump-pr` *package* *version*

# DESCRIPTION

These are specified interfaces; this page does not establish completed implementation.

**create** fetches the source URL, hashes it, detects the build system, and emits a
`package.toml` draft. Review the draft before publishing. The destination and
overwrite rules are not yet specified.

**lint** validates a formula against schema and policy: names, licenses, pinned
sources, submodules, cycles, and plausible OS requirements. Vendor formulae also
require complete payload maps, signer/notarization checks, and consistent OS tags.
Grafts require matching script hashes and explicit declarations of writes, kexts,
daemons, and network use. Lint is not proof of runtime containment or OS support.

**build** resolves a package like install but compiles locally, or builds the
supplied formula directory. It uses the same pinned toolchain, sandbox, phase
pipeline, and environment scrubbing as the farm. The result enters the store as
`origin = local-build` with recorded flags and exact identity. A successful local
build establishes only its tested configuration; farm and cross-OS gates remain.
The reproduce form rebuilds a published slice and compares evidence. Its positional
build-reference grammar is not fully specified; BUILD-INFRA shows an abbreviated
reference example. Signed/notarized bytes require the normalized evidence comparison
defined in STATE-AND-RECOVERY, not equality with a fresh unsigned executable.

**test** runs the package's `tests.star` against the installed slice. **livecheck**
queries the declared upstream strategy for newer releases; **--all** selects all
packages. The no-argument scope is not specified. This is a freshness check, not
an upgrade. **bump-pr** edits the version, lints, smoke-builds one flavor, and opens
an orchard PR. With a plain git remote lacking PR machinery, it prints the branch
and diff. It does not merge or bypass release gates.

# BUILD OPTIONS

**--variant** *±name*, **--cflags**=*flags*
:   Select a declared variant or local compiler flags. Artifact identity records
    the actual inputs; ABI compatibility does not make different bytes identical.

**--offline**
:   Use prefetched sources; it does not waive source authentication.

**--keep**, **--shell**, **--resume-from** *phase*
:   Retain the build directory, enter the sandbox at the failed phase, or resume
    at a named phase. Valid resume inputs must be verified; arbitrary compiler
    checkpoint/resume is not promised.

**--emit-abi**
:   Emit ABI evidence for comparing builds and declaring interface-changing variants.
    Incomplete evidence is not proof of compatibility.

`ASLICE_BUILD_JOBS` overrides the default `cores − 1` job count. RAM and disk
watermarks refuse builds that would thrash the machine. Successful build directories
are deleted unless retained; failures are kept for 7 days by default and swept by
clean. Logs live in `cache/build/<id>/log.jsonl` with a rendered tail.
No family-wide dry-run contract or additional per-command numeric exits are specified.

# EXAMPLES

```sh
aslice create https://example.org/foo-1.0.tar.gz
aslice lint foo
aslice build ./orchards/core/ffmpeg
aslice build ffmpeg --variant +x265 --cflags="-O3 -march=native"
aslice build ffmpeg --offline
aslice build ffmpeg --keep --shell
aslice build ffmpeg --emit-abi
aslice test ffmpeg
aslice livecheck ffmpeg
aslice bump-pr ffmpeg 7.1.0
```

# EXIT STATUS

The common statuses in [aslice(1)](aslice.1.md#exit-status) apply where
relevant: 0 success, 1 error or recovery required, 2 plan refused, 4 contention
without unresolved recovery, and 130 safely completed cancellation. No additional
family-specific numeric statuses are specified.

# SEE ALSO

[aslice(1)](aslice.1.md), [aslice-orchard(1)](aslice-orchard.1.md), [aslice-repo(1)](aslice-repo.1.md),
[AUTHORING](../docs/AUTHORING.md), [BUILD-INFRA](../docs/BUILD-INFRA.md#user-mode-aslice-build),
[PACKAGE-FORMAT](../docs/PACKAGE-FORMAT.md#validation-and-tooling),
[STATE-AND-RECOVERY](../docs/STATE-AND-RECOVERY.md#acceptance-and-implementation-order)
