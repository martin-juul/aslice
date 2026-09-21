% ASLICE-APPLY(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-apply — converge a machine to a declarative document; aslice-export, aslice-import — capture and translate setups

# SYNOPSIS

`aslice apply` [*setup.toml* | *aslice.lock* | *plan.json* | *https://…*] [`--dry-run`] [`--prune`] [`--accept-system-changes`] [`--json`]

`aslice export` [`--defaults` *domain*,…] [`--system-defaults` *domain*,…]

`aslice import` `--from-brewfile` *Brewfile*

# DESCRIPTION

**apply** converges the machine to a declarative document. One verb serves three fidelities, detected by content: a saved **plan** (JSON, from `aslice plan`) is executed; a **lock file** (`lock_version = 1`, PACKAGE-FORMAT §7) is replayed exactly; a **setup file** (`schema = 1`, SETUP.md) is planned — wishlist resolved, preferences diffed — shown, confirmed, and executed. With no argument, `./setup.toml` is read. An `https://` argument is fetched, hash-printed, and planned before any consent is asked.

A setup file declares: packages (the wishlist: names, `@version` constraints, `+variants`, `repo:` namespaces), profile-wide runtime selections, services to enable, the login shell, `defaults` preferences (user and system domains), aslice's own configuration, and additional repositories. The file is data, never code — there are no hooks and nothing is evaluated.

**export** writes the current machine as a setup file on stdout: leaf packages, runtime selections, enabled services, a non-default login shell, configured repositories, and non-default configuration. Preferences are captured only for domains named with **--defaults** / **--system-defaults** — there is no baseline to diff a whole preferences folder against, and application domains can contain account- or machine-specific values. Review before sharing.

**import --from-brewfile** translates a Homebrew Brewfile into a setup file on stdout: `brew` entries become packages, `tap` entries become comments, `cask`/`mas`/`vscode` entries are skipped with a printed list. A starting point for hand-tuning, not a fidelity guarantee.

# APPLY SEMANTICS

The plan is computed in full and confirmed before execution: validate, repositories (TOFU-pinned, never elevated), configuration, packages (one generation for the whole set), runtime selections, services, user preferences, then system preferences and shell. Apply is convergent — a second run of the same file is a no-op — and additive by default: items absent from the file are left alone.

**--prune** opts into retraction: anything recorded as file-managed but no longer declared is removed or restored to its recorded pre-apply value. Prune never touches hand-installed packages or hand-set keys, and never removes repositories — trust decisions are sticky (REPOSITORIES.md §10).

Before every preference write, shell change, or `/etc/shells` enrollment, the pre-change value is recorded against the new generation: `aslice rollback` restores preferences and login shell together with the profile. `aslice history` attributes every applied change to its file hash and generation.

# CONSENT GATES

System-domain preferences (`/Library/Preferences`) and `/etc/shells` enrollment write to OS territory. Interactively each gated step prompts, naming exactly what will be written. Non-interactively they are refused — exit status 2 — unless **--accept-system-changes** is passed (the same flag and contract as system packages and system patches). **--dry-run** prints the complete plan, including gated steps, and changes nothing.

# EXIT STATUS

**0** applied, or nothing to do. **1** error (schema, resolution, execution). **2** refused at a consent or trust gate.

# FILES

**./setup.toml**
:   The default document for `aslice apply` with no argument.

**/opt/aslice/profiles/<name>/aslice.lock**
:   The per-profile lock, rewritten with every generation; exportable with `aslice lock export`.

# NOTES

The full schema and semantics: SETUP.md. The user-facing walkthrough: MANUAL.md §10. The rationale: DESIGN.md §12.13.

# SEE ALSO

aslice(1), aslice-install(1), aslice-use(1), aslice-service(1), aslice-system-patch(1), aslice-repo(1)
