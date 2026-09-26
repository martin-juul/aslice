% ASLICE-INSTALL(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-install — install packages

# SYNOPSIS

`aslice install` [*options*] *package*…
`aslice reinstall` [*options*] *package*…

# DESCRIPTION

Installs packages, binary-first: resolves the request against the index, selects the newest version compatible with this OS release and the fastest flavor this CPU executes, downloads the slices, verifies signatures and hashes, checks library interfaces against the installed set, and links a new generation. No undeclared package code executes at any point — a package whose installer genuinely requires a script declares it as a graft, which runs only after its behavior manifest has been shown and approved (aslice-graft(1)). If any step fails, the live generation is untouched.

*package* may be a bare name (`ffmpeg`), a version constraint (`ffmpeg@v6`), a namespaced name (`audiolab:convolver`), or a runtime stream (`php@8.4` — installing a stream never changes the selected one; see aslice-use(1)).

**reinstall** performs a fresh link of the same version, repairing damaged profile entries.

# OPTIONS

**--build-from-source**
:   Compile locally instead of using a slice. Dependencies still resolve to binaries where possible.

**--variant** ±*name*
:   Enable or disable a declared feature variant. Interface-changing variants (`abi = true`) produce a distinct build identity; others trigger a local build with the same compatibility key and a distinct artifact identity. aslice reports whether a prebuilt slice exists for the combination before compiling.

**--cflags**="…", **--ldflags**="…", **--lto**, **--debug**
:   Optimization flags for a local build of the named package only. Recorded in the manifest for provenance; never part of the build identity, so the result interops with prebuilt packages.

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

```
aslice install ffmpeg
aslice install ffmpeg --variant +x265 --cflags="-O3 -march=native"
aslice install php@8.4 --with-extensions-from 8.3
aslice install foo --accept-system-changes
aslice install convolver --accept-grafts
```

# SEE ALSO

aslice(1), aslice-upgrade(1), aslice-uninstall(1), aslice-use(1), aslice-graft(1), MANUAL.md §3–§4
