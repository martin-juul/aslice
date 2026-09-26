% ASLICE-UPGRADE(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-upgrade, aslice-outdated — update installed packages

# SYNOPSIS

`aslice upgrade` [*package*…]

`aslice outdated` [**--json**]

# DESCRIPTION

**outdated** lists what would change and why, honoring pins. **upgrade** performs it: resolves, fetches, and builds the complete new generation before touching the live one, so a failed download leaves the live generation unchanged. Power loss during activation or external writes requires journal recovery; conflicts are reported for attention ([STATE-AND-RECOVERY §5](../docs/STATE-AND-RECOVERY.md#durable-transactions-and-recovery)).

Rules upgrade never breaks on its own:

- Pinned packages (`aslice pin`) are skipped and reported as pinned.
- Runtime streams stay in their lane: `upgrade php` moves within the selected stream (8.4 patches), never across (8.5). New streams are a separate `install php@8.5`.
- Major aslice self-upgrades print the changelog and ask first.

Packages with running services are stopped, swapped, and restarted as part of the transaction; if a service fails its post-upgrade health check, an interactive run offers to roll back (aslice-service(1)).

# OPTIONS

**--rollback-on-service-failure**
:   Explicit unattended rollback on service readiness failure, permitted only when the persistent-data compatibility contract or authorized tested backup/restore procedure makes rollback valid. Without this flag, an unattended failure returns failure and retains evidence; it does not silently roll back. Interactive failures offer only eligible recovery choices ([STATE-AND-RECOVERY §5](../docs/STATE-AND-RECOVERY.md#durable-transactions-and-recovery)).

**--dry-run**, **--json**
:   Print the plan without changing anything; machine-readable output.

# SEE ALSO

aslice(1), aslice-install(1), aslice-service(1), [MANUAL §3.2](../docs/MANUAL.md#upgrading) and [MANUAL §7.2](../docs/MANUAL.md#upgrades-and-the-rollback-prompt)
