% ASLICE-PROFILE(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-profile — inspect generations and select profile contents

# SYNOPSIS

`aslice history`

`aslice rollback` [*generation*]

`aslice switch-generation` *generation*

`aslice link` *package*

`aslice unlink` *package*

`aslice profile prefer` *name* *provider*

`aslice exec` *package* `--` *command* [*argument*…]

`aslice exec --replacement` *path* `--` *package* *command* [*argument*…]

# DESCRIPTION

These are specified interfaces; this page does not establish completed implementation.

**history** lists retained generations and attributes machine-file changes to
their file hash and generation. **rollback** restores the previous generation,
or the named retained generation. **switch-generation** selects a retained
generation explicitly. *generation* is the identity shown by history; its lexical
grammar is not specified.

Both transitions verify retained artifacts and journal managed-state restoration,
including the profile lock and changed service declarations. External edits stop
inverse writes with a conflict. Application data and databases need their own
compatible backup/restore procedure; protected-volume restoration can require
Recovery and reboot. Artifacts needed by active recovery remain GC roots.

**link** exposes an installed package in the current profile; **unlink** retracts
that exposure. Each creates a generation. This is the explicit opt-in for packages
declaring `link = false`; dependencies still use their store paths either way.
**profile prefer** selects the provider for a colliding name or virtual package,
for example `blas` and `openblas`, without modifying immutable store bytes.
It does not permit an implicit cross-repository provider substitution.

**exec** runs a command in a temporary profile view discarded on exit. The first
form names the package before `--`, followed by the executable and its arguments.
It does not establish a persistent runtime selection.

# REPLACEMENT EXECUTION

**--replacement** names the verified replacement path prepared by recovery. This
form places the package after `--`. It admits only a validated isolated dependency
closure. Bad absolute paths, dependencies, plugins, or external configuration block
that closure. It neither changes normal shim selections nor activates privileged
integration. Missing selection state never permits fallback to another stream or
generation. See [aslice-recover(1)](aslice-recover.1.md).

Additional profile selectors, dry-run spellings for these transitions, and exec's
child-status propagation are not specified; this page does not define them.

# EXAMPLES

```sh
aslice history
aslice rollback
aslice switch-generation 41
aslice link openssl3
aslice unlink openssl3
aslice profile prefer blas openblas
aslice exec ffmpeg -- ffprobe in.mov
aslice exec --replacement "$replacement_path" -- ffmpeg ffprobe in.mov
```

# EXIT STATUS

The common statuses in [aslice(1)](aslice.1.md#exit-status) apply where
relevant: 0 success, 1 error or recovery required, 2 plan refused, 4 contention
without unresolved recovery, and 130 safely completed cancellation. No additional
family-specific numeric statuses are specified.

# SEE ALSO

[aslice(1)](aslice.1.md), [aslice-use(1)](aslice-use.1.md), [aslice-gc(1)](aslice-gc.1.md),
[MANUAL](../docs/MANUAL.md#rollback-and-generations),
[STATE-AND-RECOVERY](../docs/STATE-AND-RECOVERY.md#52-working-package-access-and-shims)
