% ASLICE-UPGRADE(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-upgrade, aslice-outdated — update installed packages

# SYNOPSIS

`aslice upgrade` [*package*…] [**--security** [**--minimal**]] [**--allow-source-builds**]

`aslice outdated` [**--json**]

# DESCRIPTION

**outdated** lists what would change and why, honoring pins. **upgrade** performs it: resolves, fetches, and builds the complete new generation before touching the live one, so a failed download leaves the live generation unchanged. Power loss during activation or external writes requires journal recovery; conflicts are reported for attention ([STATE-AND-RECOVERY §5](../docs/STATE-AND-RECOVERY.md#durable-transactions-and-recovery)).

Rules upgrade never breaks on its own:

- Pinned packages (`aslice pin`) are skipped and reported as pinned.
- Runtime streams stay in their lane: `upgrade php` moves within the selected stream (8.4 patches), never across (8.5). New streams are a separate `install php@8.5`.
- Major aslice self-upgrades print the changelog and ask first.

Packages with running services are stopped, swapped, and restarted as part of the transaction; if a service fails its post-upgrade health check, an interactive run offers to roll back (aslice-service(1)).

Normal upgrades choose the newest eligible version after authority, compatibility,
holds, stream boundaries, and explicit requests. An older cached binary does not
displace a newer source-only update. The plan discloses each build and dependency
reason. Interactive execution asks for source-build consent; unattended execution
requires **--allow-source-builds**. Saved plans do not transfer consent.

**--security** selects the newest eligible fixes for applicable authenticated
advisories. **--security --minimal** chooses the lowest eligible fixed versions
satisfying advisory and dependency constraints. Necessary dependency changes are
included and explained. **--minimal** alone is an invocation error. Holds and
platform gaps remain visible; no unresolved advisory is silently omitted.

# EXIT STATUS

**0** complete requested update and verification. **1** execution/invocation error.
**2** consent or trust refusal. **3** incomplete security remediation, including
held fixes, unavailable platform fixes, stale or unknown coverage, and cross-orchard
gaps. A partial committed update may still return 3; JSON reports both facts.

# OPTIONS

**--security**, **--minimal**
:   Restrict the update objective to advisory fixes; minimal selects the lowest eligible fixed solution and requires security mode.

**--allow-source-builds**
:   Authorize the disclosed source work for this execution. Required unattended; unrelated consent gates still apply.

**--health-timeout** *duration*
:   Set the per-service post-commit health timeout, default `60s`; require a positive finite integer with `ms`, `s`, or `m` and reject overflow.

**--rollback-on-service-failure**
:   Explicit unattended rollback on service readiness failure, permitted only when the persistent-data compatibility contract or authorized tested backup/restore procedure makes rollback valid. Without this flag, an unattended failure returns failure and retains evidence; it does not silently roll back. Interactive failures offer only eligible recovery choices ([STATE-AND-RECOVERY §5](../docs/STATE-AND-RECOVERY.md#durable-transactions-and-recovery)).

**--dry-run**, **--json**
:   Print the plan without changing anything; machine-readable output.

# COMMIT AND VERIFICATION

Installation commits before service health checks. Hold effective prefix mutation
ownership through checks, defaulting to 60 seconds per service with positive finite
overrides. A failed or timed-out check returns nonzero and explicitly reports
committed installation. Any eligible rollback is a new transaction. A stop request
after commit stops checks safely and reports incomplete verification.

# SEE ALSO

aslice(1), aslice-install(1), aslice-service(1), [MANUAL §3.2](../docs/MANUAL.md#upgrading) and [MANUAL §7.2](../docs/MANUAL.md#upgrades-and-the-rollback-prompt)
