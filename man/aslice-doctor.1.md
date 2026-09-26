% ASLICE-DOCTOR(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-doctor — the installation health battery

# SYNOPSIS

`aslice doctor` [**--fix**] [**--json**] [**--brief**] [**--deep**] [**--offline**]

# DESCRIPTION

Runs a fixed battery of read-only checks and reports each as pass, warn, or fail. Every warn and fail names its remedy — the exact command, not a category. Check groups: machine (CPU flavor vs. config, OS release, filesystem, disk), prefix and store (ownership, manifest hashes), profiles and generations, database, repositories (reachability, key pins, trust consistency, staleness), coexistence (Homebrew/MacPorts, PATH), environment (overrides shown, not hidden), trust store (bundle freshness, keychain drift), services, runtime selections, and system patches (drift after OS updates).

A clean machine prints one line: `aslice: your installation is healthy (N checks, M repos, G generations)`. The footer lists the log directory and the last operation ID.

# OPTIONS

**--fix**
:   Perform only the repairs that cannot lose data — pruning dangling cache entries, re-linking a broken generation symlink to its recorded target, refreshing stale index snapshots — announcing each before acting. Everything else prints the command for you to run.

**--json**
:   Emit the full battery result. Every check has a stable ID (e.g. `doctor.store.hash`) for scripting.

**--brief**
:   Suppress informational findings; warnings and failures remain.

**--deep**
:   Re-hash every file in the store, beyond the sampled and flagged files checked by default.

**--offline**
:   Skip network access; report cached-index age instead of repository reachability.

# EXIT STATUS

**0** all checks pass; **1** warnings only; **2** any failure.

# SEE ALSO

aslice(1), aslice-ca-update(1), MANUAL.md §11
