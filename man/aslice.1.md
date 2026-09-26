% ASLICE(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice — a package manager for Intel macOS (10.11–12, x86_64)

# SYNOPSIS

`aslice` [*global-options*] *command* [*command-options*] [*args*]

# DESCRIPTION

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

**doctor**, **log**
:   Run the health battery; query the local operation log. See aslice-doctor(1).

**self-update**
:   Update aslice itself — signed, generation-managed, health-checked, with automatic rollback on failure. `--check` reports without installing.

**system-patch**
:   `list`, `status`, `restore` — inspect and reverse declared replacements of Apple-provided files. See aslice-system-patch(1).

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

# GLOBAL OPTIONS

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
:   The prefix: `store/`, `profiles/generations/`, `shims/`, `apps/`, `cache/`, `log/`, `db/state.sqlite`, `etc/aslice.toml`.

# EXIT STATUS

**0** success; **1** general error; **2** plan refused (trust, policy, or consent gate). aslice-doctor(1) defines its own battery exit codes.

**recover**, **decommission**
:   Resume durable recovery, or inventory and remove managed external effects before deleting the prefix. `decommission --dry-run` inventories without changes; pending restoration preserves recovery tools ([STATE-AND-RECOVERY §6](../docs/STATE-AND-RECOVERY.md#self-update-and-decommission)).

# SEE ALSO

The full user manual: `docs/MANUAL.md` in the aslice source tree. Package authoring: `docs/AUTHORING.md`. Design rationale: `docs/DESIGN.md`.

aslice-install(1), aslice-upgrade(1), aslice-uninstall(1), aslice-gc(1), aslice-service(1), aslice-use(1), aslice-repo(1), aslice-orchard(1), aslice-ca-update(1), aslice-doctor(1), aslice-system-patch(1), aslice-apply(1), aslice-machine(1), aslice-graft(1)
