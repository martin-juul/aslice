% ASLICE-SYSTEM-PATCH(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-system-patch — inspect and reverse declared replacements of Apple-provided files

# SYNOPSIS

`aslice system-patch list`
`aslice system-patch status` [*path*]
`aslice system-patch restore` *path*

# DESCRIPTION

Packages in the declared `[system-patch]` category (PACKAGE-FORMAT.md §3.16) replace specific Apple-provided files — frozen tools, configs, and data named by absolute path — where fixing the frozen platform genuinely requires it (DESIGN.md §12.11). The mechanism is backup–symlink–record: the original file is copied byte-exact into a managed backup directory under the prefix, the path is replaced by a symlink into the package's store entry, and the patch is recorded so it can be reversed to the byte.

The target list is refused by construction: the kernel, `dyld`, `libSystem`, anything under `/System`, and any dylib or framework in a platform binary's load path are lint-enforced refusals, not review judgment calls. Every patch carries a mandatory `reason`, shown verbatim at every decision point. Installation requires explicit consent — interactive confirmation, or `--accept-system-changes` non-interactively; there is no "always allow" — and a SIP preflight refuses targets that System Integrity Protection still protects rather than failing halfway through.

**list** shows every currently patched path and the package responsible. **status** reports one path (or all of them) in detail: original sha256, patch state, and whether an OS update has touched the file since the patch was installed. **restore** puts the byte-exact Apple original back, verified by sha256 against the backup before the symlink is removed.

# TRUST

Serving `[system-patch]` packages requires the repository `system-patch` capability (REPOSITORIES.md §3): official and local repositories have it by default; a verified repository receives it only through the user's explicit per-repo grant (`aslice repo allow-system-patch <name>`, refused by default, revocable with `aslice repo deny-system-patch <name>`); third-party repositories never.

# OS UPDATES

A macOS update can overwrite or remove a patched path, silently ending the patch. aslice never re-patches silently: **status** reports the drift, and `aslice doctor` diagnoses it with its usual remedy line — restore the Apple original with `aslice system-patch restore`, or reinstall the patch with fresh consent. Neither happens on its own.

# LIMITS

The backup holds bytes, not history: one original per patched path, never overwritten by a later patch of the same path. Rolling back the generation that installed the patch rolls back the patch with it — generations are the unit of undo. Uninstalling a patch package is refused while its symlinks are live; restore first.

# FILES

**The managed backup directory** (under the prefix)
:   Holds the byte-exact Apple originals, one per patched path. Never overwritten by a later patch of the same path; never pruned while the patch is installed; verified by sha256 at restore.

# SEE ALSO

aslice(1), aslice-doctor(1), aslice-repo(1), MANUAL.md §8.4, DESIGN.md §12.11, PACKAGE-FORMAT.md §3.16
