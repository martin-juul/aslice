% ASLICE-UNINSTALL(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-uninstall, aslice-autoremove, aslice-mark, aslice-pin — remove and hold packages

# SYNOPSIS

`aslice uninstall` *package*…
`aslice autoremove` [**--dry-run**]
`aslice mark` *package* **--on-request**|**--as-dependency**
`aslice pin` *package*
`aslice unpin` *package*

# DESCRIPTION

**uninstall** removes packages from future generations. Old generations still reference them, so rollback keeps working until `aslice gc` reclaims the store paths.

**autoremove** removes packages that arrived as dependencies and are no longer reachable from anything you explicitly requested. aslice records per package whether you asked for it by name (`on_request`); autoremove is conservative and cross-checked against retained generations.

**mark** repairs that record when aslice guessed wrong.

**pin** (one argument) holds a package: `upgrade` skips it, `outdated` reports it as held. **unpin** releases the hold. A pin is a database note, not a file freeze — reinstall and rollback work normally.

Note the overloaded spelling: `pin openssl` (one argument) is the hold described here; `pin php 8.4` (a runtime plus a stream) pins the current project directory to a runtime stream — see aslice-use(1).

# SEE ALSO

aslice(1), aslice-gc(1), aslice-use(1), MANUAL.md §3.3–§3.4
