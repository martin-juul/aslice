% ASLICE-APPLY(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-apply — execute a saved plan; replay a lock file

# SYNOPSIS

`aslice apply` [*plan.json* | *aslice.lock* | *https://…*] [`--dry-run`] [`--accept-system-changes`] [`--accept-grafts`] [`--json`]

# DESCRIPTION

**apply** executes a declarative document that already names exact state, detected by content: a saved **plan** (JSON, from `aslice plan`) is executed step for step; a **lock file** (`lock_version = 1`, PACKAGE-FORMAT §7) is replayed exactly — the recorded package set becomes a new generation. An `https://` argument is fetched, hash-printed, and shown before any consent is asked. With no argument there is no default document — apply prints its usage.

The third document kind belongs elsewhere: a whole-machine **setup file** (`schema = 1`, SETUP.md) is refused here with a pointer to `aslice machine apply` (aslice-machine(1)), which is also the spelling that has a default document (`./aslice-machine.toml`). The surface splits by document kind: exact state replays top-level, the machine wishlist converges under `aslice machine`.

# APPLY SEMANTICS

The document is shown and confirmed before execution. Before execution, exact artifact records, repository identities, machine requirements, and the expected base generation are revalidated. A stale plan is refused. Packages are staged before activation; external writes and profile changes follow the durable journal. Failure after live changes invokes recovery and may require conflict resolution or reboot. Package rollback does not restore application data (STATE-AND-RECOVERY §5, §8).

**--dry-run** prints the complete plan and changes nothing.

# CONSENT GATES

A plan or lock containing system packages or system patches is refused non-interactively — exit status 2 — unless **--accept-system-changes** is passed for that operation; interactively each gated step prompts, naming what will be written. There is deliberately no persistent always-accept setting — consent is per-decision, like the risk (DESIGN.md §12.7).

Graft-bearing packages gate the same way: non-interactively the apply is refused — exit status 2 — for any graft without a recorded approval, unless **--accept-grafts** is passed for that run; interactively the behavior manifest is shown and approval asked per package (aslice-graft(1)).

# EXIT STATUS

**0** applied, or nothing to do. **1** error (schema, resolution, execution). **2** refused at a consent or trust gate.

# FILES

**/opt/aslice/profiles/<name>/aslice.lock**
:   The per-profile lock, rewritten with every generation; exportable with `aslice lock export`.

# NOTES

Plans and the `plan`/`apply` split: DESIGN.md §12.1. The lock format: PACKAGE-FORMAT.md §7. Whole-machine setup: SETUP.md and aslice-machine(1).

# SEE ALSO

aslice(1), aslice-machine(1), aslice-install(1), aslice-use(1), aslice-service(1), aslice-repo(1), aslice-graft(1)
