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

Packages describe their services declaratively in the manifest; aslice generates the launchd job and manages it over launchctl's modern interface. Job labels are namespaced (`org.aslice.<pkg>`), and `ProgramArguments` resolve through the profile, so upgrades and rollbacks never require editing the job.

**status** reports launchd's truth — pid, state, last exit status, keepalive — not a pidfile. **run** executes the service in the foreground, unregistered, for debugging.

User-domain services run as the invoking user, need no sudo, and any repository may declare them. `domain = "system"` root daemons are bootstrapped by the privileged `aslice-system` helper with per-operation consent and unsuppressible logging, and only official, verified, or local repositories (REPOSITORIES.md §3) may serve them.

# UPGRADES

An upgrade that touches a running service builds the entire new generation first, stops only the affected jobs, swaps the generation atomically, restarts, and health-checks. If a service fails to start, an interactive run shows the launchd exit status and log path, then asks whether to roll back to the previous generation (default: stay and inspect). Non-interactive runs never prompt and never auto-rollback; they fail with a machine-readable `service_start_failed`. Automation passes **--rollback-on-service-failure** to `aslice upgrade` for the unattended "yes." There is no flag that reports a downed service as success.

# FILES

**$XDG_CONFIG_HOME/aslice/services/**<pkg>**.env**
:   Per-service environment overrides, applied when aslice generates the launchd job. Never edit generated plists; this file is where overrides belong.

# SEE ALSO

aslice(1), aslice-upgrade(1), aslice-doctor(1), MANUAL.md §7
