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

A setup file declares: packages (the wishlist: names, `@version` constraints, `+variants`, `repo:` namespaces), profile-wide runtime selections, services to enable, the login shell, `defaults` preferences (user and system domains), aslice's own configuration, graft pre-approvals (the `[grafts]` allow-list, SETUP.md §2.8), and additional repositories. The file is data, never code — there are no hooks and nothing is evaluated.

Saved plans and lock files are not this command: they name exact state and replay through top-level `aslice apply` (aslice-apply(1)). The surface splits by document kind — a plan passed to **machine apply**, or a setup file passed to top-level **apply**, is refused with a pointer to the right spelling.

**export** writes the current machine as a setup file on stdout: leaf packages, runtime selections, enabled services, a non-default login shell, configured repositories, recorded graft approvals (as `[grafts].allow`), and non-default configuration. Preferences are captured only for domains named with **--defaults** / **--system-defaults** — there is no baseline to diff a whole preferences folder against, and application domains can contain account- or machine-specific values. Review before sharing.

**import --from-brewfile** translates a Homebrew Brewfile into a setup file on stdout: `brew` entries become packages, `tap` entries become comments, `cask`/`mas`/`vscode` entries are skipped with a printed list. A starting point for hand-tuning, not a fidelity guarantee.

# APPLY SEMANTICS

The plan is computed in full and confirmed before execution: validate, repositories (TOFU-pinned, never elevated), configuration, packages (one generation for the whole set), runtime selections, services, user preferences, then system preferences and shell. Apply is convergent — a second run of the same file is a no-op — and additive by default: items absent from the file are left alone.

**--prune** opts into retraction: anything recorded as file-managed but no longer declared is removed or restored to its recorded pre-apply value. Prune never touches hand-installed packages or hand-set keys, and never removes repositories — trust decisions are sticky (REPOSITORIES.md §10).

Before every preference write, shell change, or `/etc/shells` enrollment, the pre-change value is recorded against the new generation: `aslice rollback` plans restoration of preferences and login shell with the profile, checking for intervening external edits before writing. Conflicts require attention; protected-volume changes may require Recovery and reboot. `aslice history` attributes every applied change to its file hash and generation.

# CONSENT GATES

System-domain preferences (`/Library/Preferences`) and `/etc/shells` enrollment write to OS territory. Interactively each gated step prompts, naming what will be written. Non-interactively they are refused — exit status 2 — unless **--accept-system-changes** is passed (the same flag and contract as system packages and system patches). **--dry-run** prints the complete plan, including gated steps, and changes nothing.

Graft-bearing packages are a second gate, of a different kind: an approved graft runs its declared installer script under a sandbox derived from its behavior manifest (aslice-graft(1)). Interactively the manifest is shown and approval asked per package; non-interactively the apply is refused — exit status 2 — for any graft not named in the file's `[grafts]` allow-list (signed manifests only) unless **--accept-grafts** is passed. The allow-list suppresses the prompt, never the display.

# EXIT STATUS

**0** applied, or nothing to do. **1** error (schema, resolution, execution). **2** refused at a consent or trust gate.

# FILES

**./aslice-machine.toml**
:   The default document for `aslice machine apply` with no argument.

# NOTES

The full schema and semantics: SETUP.md. The user-facing walkthrough: MANUAL.md §10. The rationale: DESIGN.md §12.13.

# SEE ALSO

aslice(1), aslice-apply(1), aslice-install(1), aslice-use(1), aslice-service(1), aslice-system-patch(1), aslice-repo(1), aslice-graft(1)
