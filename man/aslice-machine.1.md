% ASLICE-MACHINE(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-machine — declarative whole-machine setup: apply, export, import

# SYNOPSIS

`aslice machine apply` [*aslice-machine.toml* | *https://…*] [`--dry-run`] [`--prune`] [`--accept-system-changes`] [`--accept-grafts`] [`--json`]

`aslice machine export` [`--defaults` *domain*,…] [`--system-defaults` *domain*,…]

`aslice machine import` `--from-brewfile` *Brewfile*

# DESCRIPTION

**apply** converges the machine to a setup file (`schema = 1`, SETUP.md): the wishlist is resolved, preferences diffed, the plan shown, confirmed, and executed. With no argument, `./aslice-machine.toml` is read. An `https://` argument is fetched, hash-printed, and planned before any consent is asked.

A setup file declares: packages (the wishlist: names, `@version` constraints, `+variants`, `repo:` namespaces), profile-wide runtime selections, services to enable, the login shell, `defaults` preferences (user and system domains), aslice's own configuration, graft approval selections (the `[grafts]` allow-list, [SETUP §2.8](../docs/SETUP.md#grafts)), and additional repositories. The file is data, never code — there are no hooks and nothing is evaluated.

Saved plans and lock files name exact state and replay through top-level `aslice apply` (aslice-apply(1)). A plan passed to **machine apply**, or a setup file passed to top-level **apply**, is refused with a pointer to the command for that document kind.

**export** writes the current machine as a setup file on stdout: explicitly requested packages, including those with dependents, runtime selections, enabled services, a non-default login shell, configured repositories, graft selections (as `[grafts].allow`, without transferring approval), and non-default configuration. Preferences are captured only for domains named with **--defaults** / **--system-defaults** — there is no baseline to diff a whole preferences folder against, and application domains can contain account- or machine-specific values. Review before sharing.

**import --from-brewfile** translates a Homebrew Brewfile into a setup file on stdout: `brew` entries become packages, `tap` entries become comments, `cask`/`mas`/`vscode` entries are skipped with a printed list. Review and adjust the result; the translation does not guarantee fidelity.

# APPLY SEMANTICS

Establish any missing repository trust explicitly before planning. Compute the complete managed-state plan and collect required consent before mutation. One durable transaction covers configuration, packages, runtime selections, services, preferences, and shell changes; any failed step rolls back the entire apply. External conflicts or unavailable recovery state leave `needs-attention`, never successful partial completion ([SETUP §3.2](../docs/SETUP.md#the-plan-and-the-order-of-operations) and [SETUP §3.6](../docs/SETUP.md#failure-handling)). Apply remains convergent and additive by default.

**--prune** opts into retraction: anything recorded as file-managed but no longer declared is removed or restored to its recorded pre-apply value. Prune never touches hand-installed packages or hand-set keys, and never removes repositories — trust decisions are sticky ([SETUP §3.3](../docs/SETUP.md#idempotence-convergence-and---prune)).

Before every preference write, shell change, or `/etc/shells` enrollment, the pre-change value is recorded against the new generation: `aslice rollback` plans restoration of preferences and login shell with the profile, checking for intervening external edits before writing. Conflicts require attention; protected-volume changes may require Recovery and reboot. `aslice history` attributes every applied change to its file hash and generation.

# CONSENT GATES

System-domain preferences (`/Library/Preferences`) and `/etc/shells` enrollment write to OS territory. Interactively each gated step prompts, naming what will be written. Non-interactively they are refused — exit status 2 — unless **--accept-system-changes** is passed (the same flag and contract as system packages and system patches). **--dry-run** prints the complete plan, including gated steps, and changes nothing.

Graft-bearing packages require a matching local approval or a fresh decision. `[grafts].allow` names select an approval only when repository identity, version, script hashes, and effective manifest digest match; a fresh machine must approve again. Unsigned manifests never reuse approval. Non-interactive execution requires explicit consent when no matching approval exists. System effects additionally require their capability and system-change consent ([SETUP §2.8](../docs/SETUP.md#grafts); [STATE-AND-RECOVERY §4](../docs/STATE-AND-RECOVERY.md#graft-execution-boundary)).

# EXIT STATUS

**0** applied, or nothing to do. **1** error (schema, resolution, execution). **2** refused at a consent or trust gate.

# FILES

**./aslice-machine.toml**
:   The default document for `aslice machine apply` with no argument.

# NOTES

The full schema and semantics: SETUP.md. The user-facing walkthrough: [MANUAL §10](../docs/MANUAL.md#one-file-one-command-rebuilding-a-machine). The rationale: [DESIGN §12.13](../docs/DESIGN.md#declarative-system-setup-aslice-machinetoml-and-the-aslice-machine-commands).

# SEE ALSO

aslice(1), aslice-apply(1), aslice-install(1), aslice-use(1), aslice-service(1), aslice-system-patch(1), aslice-repo(1), aslice-graft(1)
