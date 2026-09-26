% ASLICE-APPLY(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-apply — execute a saved plan; replay a lock file

# SYNOPSIS

`aslice apply` [*plan.json* | *aslice.lock* | *https://…*] [`--dry-run`] [`--accept-system-changes`] [`--accept-grafts`] [`--json`]

# DESCRIPTION

**apply** detects the document kind from its content and executes the exact state it records. A saved **plan** (JSON, from `aslice plan`) is executed step for step. A **lock file** (`lock_version = 1`, [PACKAGE-FORMAT §7](../docs/PACKAGE-FORMAT.md#lock-files)) is replayed exactly — the recorded package set becomes a new generation. An `https://` argument is fetched, hash-printed, and shown before any consent is asked. With no argument there is no default document — apply prints its usage.

A whole-machine **setup file** (`schema = 1`, SETUP.md) is refused here with a pointer to `aslice machine apply` (aslice-machine(1)). That command resolves a machine wishlist and uses `./aslice-machine.toml` as its default document. Exact-state replay belongs to the top-level command; wishlist convergence belongs under `aslice machine`.

# APPLY SEMANTICS

Before execution, the document is shown and confirmed, and its exact artifact records, repository identities, machine requirements, and expected base generation are revalidated. A stale plan is refused. Packages are staged before activation; external writes and profile changes follow the durable journal. Failure after live changes invokes recovery and may require conflict resolution or reboot. Package rollback does not restore application data ([STATE-AND-RECOVERY §5](../docs/STATE-AND-RECOVERY.md#durable-transactions-and-recovery) and [STATE-AND-RECOVERY §8](../docs/STATE-AND-RECOVERY.md#plans-locks-archives-and-offline-use)).

**--dry-run** prints the complete plan and changes nothing.

# CONSENT GATES

A plan or lock containing system packages or system patches is refused non-interactively — exit status 2 — unless **--accept-system-changes** is passed for that operation; interactively each gated step prompts, naming what will be written. There is deliberately no persistent always-accept setting — consent is per-decision, like the risk ([DESIGN §12.7](../docs/DESIGN.md#system-software-kexts-and-sip-disabled-development-tools)).

Graft-bearing packages gate the same way: non-interactively the apply is refused — exit status 2 — for any graft without a recorded approval, unless **--accept-grafts** is passed for that run; interactively the behavior manifest is shown and approval asked per package (aslice-graft(1)).

# EXIT STATUS

**0** applied, or nothing to do. **1** error (schema, resolution, execution). **2** refused at a consent or trust gate.

# FILES

**/opt/aslice/profiles/<name>/aslice.lock**
:   The per-profile lock, rewritten with every generation; exportable with `aslice lock export`.

# NOTES

Plans and the `plan`/`apply` split: [DESIGN §12.1](../docs/DESIGN.md#commands). The lock format: [PACKAGE-FORMAT §7](../docs/PACKAGE-FORMAT.md#lock-files). Whole-machine setup: SETUP.md and aslice-machine(1).

# SEE ALSO

aslice(1), aslice-machine(1), aslice-install(1), aslice-use(1), aslice-service(1), aslice-repo(1), aslice-graft(1)
