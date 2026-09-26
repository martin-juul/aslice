% ASLICE(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice — a package manager for Intel macOS (10.11–12, x86_64)

# SYNOPSIS

`aslice` [*global-options*] *command* [*command-options*] [*args*]

# DESCRIPTION

These are specified interfaces; command implementation and installed help routing remain pending.

aslice installs and manages software on Intel Macs running macOS 10.11 through 12. Packages are **slices** — prebuilt, signed binaries — installed from signed, static **repositories** compiled from **orchards** (git repositories of formulae). Installs are binary-first, execute no undeclared package code — a vendor installer script runs only as a declared, approved graft (aslice-graft(1)) — and never require sudo in steady state. Package activation creates a new **generation**. `aslice rollback` restores retained managed state through the transaction journal; external conflicts and reboot requirements are reported, and application data needs its own backup procedure.

aslice collects no telemetry or analytics of any kind — there is no opt-out because there is no instrumentation.

# EVERYDAY COMMANDS

**install**, **uninstall**, **upgrade**, **outdated**, **reinstall**
:   Install, remove, and update packages. See aslice-install(1), aslice-upgrade(1), aslice-uninstall(1).

**graft**
:   Review and withdraw recorded installer-script approvals: `graft approvals`, `graft revoke`. Approving a graft happens at install; see aslice-graft(1).

**search**, **info**, **flavors**, **leaves**, **why**
:   Find and inspect packages. `flavors` shows the prebuilt matrix for this machine; `why` explains what requires a package; `leaves` lists packages with no installed dependents (`--user-built` for locally compiled ones).

**pin**, **unpin**
:   With one argument, hold a package against upgrades. With two (`pin php 8.4`), pin the current project to a runtime stream — see aslice-use(1).

**autoremove**, **mark**
:   Collect dependencies nothing needs; repair a package's requested/dependency record.

**history**, **rollback**, **switch-generation**
:   List generations and move between them. Rollback verifies retained artifacts and checks external-state conflicts; application databases are outside package rollback.

**gc**, **clean**, **store verify**
:   Reclaim the store, evict the cache, re-verify store integrity. See aslice-gc(1).

**service**
:   Manage launchd services declared by packages. See aslice-service(1).

**use**, **default**, **versions**, **which**
:   Runtime stream selection (php, python, ruby, nodejs). See aslice-use(1).

**ca-update**
:   Refresh the CA trust bundle; optionally heal the System keychain, the crypto stack, and Apple's roots. See aslice-ca-update(1).

**repo**
:   Add, enable, inspect, and publish package repositories. See aslice-repo(1).

**orchard**
:   Maintain a formula tree: lifecycle verbs (deprecate/disable/tombstone/rename), orchard-wide lint/doctor/freshness, the local merge gate (`ci`), reverse-dependency queries, the Homebrew-formula importer. See aslice-orchard(1).

**audit**, **provenance**
:   Report known vulnerabilities in the installed set; show a package's build provenance.

**db**
:   Inspect schemas and read-only queries, check records, maintain or compact databases, and perform owner-authorized backup/restore. See [aslice-db(1)](aslice-db.1.md).

**doctor**, **log**
:   Run the health battery; query the local operation log. See aslice-doctor(1).

**self-update**
:   Update aslice itself — signed, generation-managed, health-checked, with automatic rollback on failure. `--check` reports without installing.

**system-patch**
:   `list`, `status`, `restore`, `prepare`, `finalize` — inspect and reverse declared replacements of Apple-provided files. See aslice-system-patch(1).

**adopt**
:   `--from-homebrew` — produce an install plan recreating a Homebrew leaf set.

**apply**
:   Execute a saved plan; replay a lock file. See aslice-apply(1).

**machine**
:   Declarative whole-machine setup: `machine apply` converges the machine to an `aslice-machine.toml` (packages, runtime selections, services, preferences, graft pre-approvals, login shell), `machine export` captures this machine as the file, `machine import` translates a Brewfile. See aslice-machine(1).

**shellenv**, **init**
:   Print the environment exports for the current profile; print the shell integration (bash/zsh/fish) for `aslice use`.

**exec**, **test**, **livecheck**, **config**, **help**
:   Run a command in a temporary profile view; run a package's smoke tests; query upstream for newer releases; get/set configuration; print the man page for a command.

**recover**, **decommission**
:   Offer guided recover-and-continue, resuming saved progress when evidence agrees; unattended recovery requires explicit authorization. Conflicting mutations are blocked while unaffected verified packages and external repair tools remain accessible. Recovery can prepare a verified replacement beside the preserved original and report partial usability without claiming activation. Decommission inventories and removes managed external effects before deleting the prefix. `decommission --dry-run` inventories without changes; pending restoration preserves recovery tools ([STATE-AND-RECOVERY §6](../docs/STATE-AND-RECOVERY.md#self-update-and-decommission)).

# COMMAND FAMILIES

| Family page | Commands |
|---|---|
| [aslice-install(1)](aslice-install.1.md) | `install`, `reinstall` |
| [aslice-upgrade(1)](aslice-upgrade.1.md) | `upgrade`, `outdated` |
| [aslice-uninstall(1)](aslice-uninstall.1.md) | `uninstall`, `autoremove`, `mark`, `pin`, `unpin` |
| [aslice-apply(1)](aslice-apply.1.md) | `plan install`, `lock export`, `apply` |
| [aslice-adopt(1)](aslice-adopt.1.md) | `adopt --from-homebrew` |
| [aslice-graft(1)](aslice-graft.1.md) | `graft approvals`, `graft revoke` |
| [aslice-inspect(1)](aslice-inspect.1.md) | `search`, `info`, `flavors`, `leaves`, `why`, `provenance`, `audit` |
| [aslice-needs-restarting(1)](aslice-needs-restarting.1.md) | `needs-restarting` |
| [aslice-profile(1)](aslice-profile.1.md) | `history`, `rollback`, `switch-generation`, `link`, `unlink`, `profile prefer`, `exec`, `exec --replacement` |
| [aslice-use(1)](aslice-use.1.md) | `use`, `pin`, `default`, `versions`, `which` |
| [aslice-gc(1)](aslice-gc.1.md) | `gc`, `clean`, `store verify` |
| [aslice-doctor(1)](aslice-doctor.1.md) | `doctor`, `log` |
| [aslice-db(1)](aslice-db.1.md) | `db list`, `db schema`, `db query`, `db check`, `db maintain`, `db compact`, `db backup`, `db restore` |
| [aslice-recover(1)](aslice-recover.1.md) | `recover`, `operation status`, `operation stop` |
| [aslice-self-update(1)](aslice-self-update.1.md) | `self-update`, `decommission` |
| [aslice-repo(1)](aslice-repo.1.md) | `repo add`, `repo list`, `repo enable`, `repo disable`, `repo remove`, `repo re-pin`, `repo keys`, `repo audit`, `repo allow-system-patch`, `repo deny-system-patch`, `repo build`, `repo sign`, `repo publish` |
| [aslice-orchard(1)](aslice-orchard.1.md) | `orchard add`, `orchard pin`, `orchard lint`, `orchard doctor`, `orchard freshness`, `orchard ci`, `orchard dependents`, `orchard deprecate`, `orchard disable`, `orchard undeprecate`, `orchard tombstone`, `orchard rename`, `orchard port` |
| [aslice-author(1)](aslice-author.1.md) | `create`, `lint`, `build`, `test`, `livecheck`, `bump-pr` |
| [aslice-farm(1)](aslice-farm.1.md) | `farm plan`, `farm coordinator`, `farm agent`, `farm enroll` |
| [aslice-machine(1)](aslice-machine.1.md) | `machine apply`, `machine export`, `machine import` |
| [aslice-service(1)](aslice-service.1.md) | `service list`, `service status`, `service start`, `service stop`, `service restart`, `service run` |
| [aslice-ca-update(1)](aslice-ca-update.1.md) | `ca-update`, `ca-update --keychain`, `ca-update --keychain-remove`, `ca-update --crypto`, `ca-update --apple-certs`, `ca-update --from-file` |
| [aslice-system-patch(1)](aslice-system-patch.1.md) | `system-patch list`, `system-patch status`, `system-patch restore`, `system-patch prepare`, `system-patch finalize` |
| [aslice-shell(1)](aslice-shell.1.md) | `shellenv`, `init`, `config get`, `config set`, `help` |

# GLOBAL OPTIONS

**--wait**
:   Explicitly authorize cancellable waiting for a conflicting operation. Revalidate after waiting; a materially changed plan requires fresh confirmation.

**--lock-timeout** *duration*
:   Override `db.lock_timeout` (default `30s`) for authorized cumulative foreground owner/SQL lock waits. Busy interactive runs offer wait or exit; unattended waiting requires an explicit request. A configured timeout alone does not authorize waiting. Accept a nonnegative integer with `ms`, `s`, or `m`; `0s` tries without waiting. Progress and safe cancellation follow [DATABASE §10.1](../docs/DATABASE.md#101-contention-and-safe-stopping).

**-v**, **-vv**
:   Raise verbosity (debug, then trace). Affects what is printed, not what is logged.

**--quiet**
:   Suppress all output except errors. Security events are never suppressed.

**--json**
:   Machine-readable output. Stable schema; safe for scripts.

**--log-format** *human*|*json*
:   Select log rendering on the terminal.

**--dry-run**
:   Where supported: print the complete plan and change nothing.

**--explain**
:   Where supported: show the solver's derivation for every choice.

# ENVIRONMENT

**ASLICE_USE_<RUNTIME>**
:   Session runtime selection, set by `aslice use` (aslice-use(1)).

**SSL_CERT_FILE**, **CURL_CA_BUNDLE**, **GIT_SSL_CAINFO**
:   Point userland TLS at the aslice CA bundle; set by `aslice shellenv` / `aslice init`.

**XDG_CONFIG_HOME**
:   Location of per-service environment overrides (`aslice/services/`).

# FILES

**/opt/aslice** (or **~/.aslice**)
:   The prefix: `store/`, `profiles/generations/`, `shims/`, `apps/`, `cache/`, `log/`, `db/state.sqlite`, `cache/db/cache.sqlite`, `records/`, `etc/aslice.toml`.

# EXIT STATUS

**0** success; **1** general error or recovery required; **4** contention without unresolved recovery; **130** safely completed cancellation; **2** plan refused (trust, policy, or consent gate). aslice-doctor(1) and [aslice-db(1)](aslice-db.1.md) define their own exit codes.

# GUIDED OPERATION AND RECOVERY COMMANDS

These command contracts are specified, not implemented.

`aslice operation status` reports the current owner, operation identity, phase,
helpers, verification, and recovery state. `aslice operation stop` requests safe
stopping as the initiating user or an authenticated administrator. Before commit,
attempt rollback; after commit, stop checks safely and report incomplete verification.

`aslice recover --continue` explicitly authorizes recovery and continuation of the
retained request. `--manual` quiesces helpers and persists a mutation gate for
external repair. `--salvage` prepares a replacement beside the original for review;
`--activate` separately reviews and revalidates activation at its verified path.
Protected-effect consent still applies. Unattended actions require
`--confirm-plan sha256:HEX` matching the reviewed recovery plan; obtain it with
`--dry-run --json`. Unattended stopping requires `--operation-id ID`. These actions never implicitly authorize one another.

`aslice exec --replacement PATH -- PACKAGE COMMAND...` explicitly executes only a
validated isolated dependency closure from the replacement. It cannot silently
change normal shim selections or activate privileged integration.

Recovery outcomes distinguish repaired, usable with listed unresolved repairs, and
replacement prepared but activation blocked. The machine-readable fields and
confirmation and exit contracts are specified in
[STATE-AND-RECOVERY §10.2.5](../docs/STATE-AND-RECOVERY.md#1025-command-requests-and-outcomes).

Security maintenance: `aslice upgrade --security [--minimal]` reports all unresolved
advisories; `aslice needs-restarting [--json]` reports restart, rebuild, reboot, and
unknown inspection coverage. See [aslice-upgrade(1)](aslice-upgrade.1.md) and
[aslice-needs-restarting(1)](aslice-needs-restarting.1.md). Newly required source
builds need interactive consent or `--allow-source-builds` for unattended execution.

# SEE ALSO

The full user manual: `docs/MANUAL.md` in the aslice source tree. Package authoring: `docs/AUTHORING.md`. Design rationale: `docs/DESIGN.md`.

aslice-install(1), aslice-upgrade(1), aslice-uninstall(1), aslice-gc(1), aslice-service(1), aslice-use(1), aslice-repo(1), aslice-orchard(1), aslice-ca-update(1), aslice-doctor(1), aslice-system-patch(1), aslice-apply(1), aslice-machine(1), aslice-graft(1)
