% ASLICE-SERVICE(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-service — manage launchd services declared by packages

# SYNOPSIS

`aslice service list`

`aslice service status` *package*

`aslice service start`|`stop`|`restart` *package*

`aslice service run` *package*

# DESCRIPTION

Packages describe their services declaratively in the manifest; aslice generates the launchd job and manages it over launchctl's modern interface. Job labels are namespaced (a label distinguishing prefix, profile, and package (exact encoding: [HELPERS §6](../docs/HELPERS.md#details-still-to-be-established))), and user jobs resolve through their profile. Root jobs execute only a helper-verified root-owned dependency closure under `/Library/Application Support/aslice/system`; their executables, libraries, configuration, and launch definitions cannot come from a user-writable profile. Changed declarations regenerate the managed job.

**status** queries launchd for the pid, state, last exit status, and keepalive setting rather than reading a pidfile. **run** executes the service in the foreground, unregistered, for debugging.

User-domain services run as the invoking user, need no sudo, and any repository may declare them. `domain = "system"` root daemons are bootstrapped by the privileged `aslice-system` helper with per-operation consent and unsuppressible logging, and only official, verified, or local repositories ([REPOSITORIES §3](../docs/REPOSITORIES.md#trust-levels)) may serve them.

# UPGRADES

An upgrade that touches a running service builds the entire new generation first, stops only the affected jobs, swaps the generation atomically, restarts, and health-checks. If a service fails to start, an interactive run shows the launchd exit status and log path, then asks whether to roll back to the previous generation (default: stay and inspect). Non-interactive runs never prompt and never auto-rollback; they fail with a machine-readable `service_start_failed`. Automation passes **--rollback-on-service-failure** to `aslice upgrade` for the unattended "yes." There is no flag that reports a downed service as success. An upgrade that may migrate persistent data requires declared backward compatibility or an authorized, tested backup/restore procedure. A package rollback alone cannot undo a database migration.

# FILES

`$XDG_CONFIG_HOME/aslice/services/<pkg>.env`
:   User-service environment overrides, applied when aslice generates the launchd job. Root-service overrides are separately validated and copied to protected storage by the helper. Never edit generated plists; this file is where overrides belong.

# SEE ALSO

aslice(1), aslice-upgrade(1), aslice-doctor(1), [MANUAL §7](../docs/MANUAL.md#running-services)
