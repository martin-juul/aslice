% ASLICE-UPGRADE(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-upgrade, aslice-outdated — update installed packages

# SYNOPSIS

`aslice upgrade` [*package*…]
`aslice outdated` [**--json**]

# DESCRIPTION

**outdated** lists what would change and why, honoring pins. **upgrade** performs it: resolves, fetches, and builds the complete new generation before touching the live one, so a failed download leaves the live generation unchanged. Power loss during activation or external writes requires journal recovery; conflicts are reported for attention (STATE-AND-RECOVERY §5).

Rules upgrade never breaks on its own:

- Pinned packages (`aslice pin`) are skipped and reported as pinned.
- Runtime streams stay in their lane: `upgrade php` moves within the selected stream (8.4 patches), never across (8.5). New streams are a separate `install php@8.5`.
- Major aslice self-upgrades print the changelog and ask first.

Packages with running services are stopped, swapped, and restarted as part of the transaction; if a service fails its post-upgrade health check, an interactive run offers to roll back (aslice-service(1)).

# OPTIONS

**--rollback-on-service-failure**
:   Unattended path: roll the generation back automatically if an upgraded service fails to start. Interactive runs never need this — they are asked. Non-interactive runs without it are refused, leaving rollback to an explicit `aslice rollback`.

**--dry-run**, **--json**
:   Print the plan without changing anything; machine-readable output.

# SEE ALSO

aslice(1), aslice-install(1), aslice-service(1), MANUAL.md §3.2, §7.2
