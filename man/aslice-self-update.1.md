% ASLICE-SELF-UPDATE(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-self-update — update the manager or remove the managed installation

# SYNOPSIS

`aslice self-update` [`--check`]

`aslice decommission` [`--dry-run`]

# DESCRIPTION

These are specified interfaces; this page does not establish completed implementation.

**self-update** treats the manager as package zero: a signed immutable artifact.
A known-good supervisor checks the proposed binary against a versioned state
snapshot, retains control through activation and health checks, and preserves the
old manager/state pair and bootstrap recovery entry point. Before commit a failure
reverses tentative activation; after commit restoration is a new transaction that
preserves history and trust floors. Database migration creates a versioned copy;
shims update transactionally. The old recovery capability is retained until success.

**--check** reports available updates without installing. Package holds and configured
release environments apply. Crossing a format major requires an explicit migration
plan and confirmation; it is not an unattended ordinary package upgrade.

**decommission** inventories managed external effects before deleting the prefix:
services, login-shell integration, graft effects, system patches, and managed
certificate imports need authorized restoration. It journals those changes while
the manager, trust records, and backups still exist. **--dry-run** performs the
inventory without changes. Conflicts or pending restoration retain recovery tools;
deleting the prefix by hand is not a substitute for decommission.

Decommission follows the protected-effect authorization and restoration rules in
STATE-AND-RECOVERY. Additional unattended confirmation syntax and command-specific
dry-run options for self-update are unspecified; `--check` is its read-only form.

# EXAMPLES

```sh
aslice self-update --check
aslice self-update
aslice decommission --dry-run
aslice decommission
```

# EXIT STATUS

The common statuses in [aslice(1)](aslice.1.md#exit-status) apply where
relevant: 0 success, 1 error or recovery required, 2 plan refused, 4 contention
without unresolved recovery, and 130 safely completed cancellation. No additional
family-specific numeric statuses are specified.

# SEE ALSO

[aslice(1)](aslice.1.md), [aslice-recover(1)](aslice-recover.1.md), [aslice-system-patch(1)](aslice-system-patch.1.md),
[STATE-AND-RECOVERY](../docs/STATE-AND-RECOVERY.md#self-update-and-decommission),
[HELPERS](../docs/HELPERS.md)
