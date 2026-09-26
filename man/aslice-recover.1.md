% ASLICE-RECOVER(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-recover — inspect operations and recover interrupted managed state

# SYNOPSIS

`aslice operation status` [`--json`]

`aslice operation stop` [`--operation-id` *id*] [`--json`]

`aslice recover` [`--role` *role*] [`--prefix` *path* | `--instance` *id*]
[`--continue` | `--manual` | `--salvage` | `--activate`]
[`--dry-run`] [`--confirm-plan` *sha256:HEX*]
[`--accept-system-changes`] [`--accept-grafts`] [`--json`]

# DESCRIPTION

These are specified interfaces; this page does not establish completed implementation.

**operation status** reports the current owner, identity, phase, helpers,
verification, and recovery state. When no operation is current, its identity is
null. Status is read-only; success does not clear a mutation gate.

**operation stop** requests safe stopping as the initiating user or an
authenticated administrator. Before commit it attempts rollback; after commit it
stops checks safely and reports incomplete verification. Unattended use requires
**--operation-id**. Interactively, omission shows the current operation and binds
confirmation to that identity. A changed operation refuses the request; an unknown
ID is an input error. Stopping does not authorize recovery.

**recover** resolves interrupted operations and reconstructs projections from
intact durable records. It offers guided recover-and-continue and resumes saved
progress when evidence agrees. Lost trust requires explicit trust recovery, never
a fresh TOFU choice. Protected participants require their own authorization.
Selectors use [aslice-db(1)](aslice-db.1.md)'s role and instance rules; selecting a
role grants no authority. The default is client-state in the selected prefix.

# RECOVERY ACTIONS AND CONSENT

**--continue**
:   Authorize recovery and continuation of the retained request. An established
    interrupted operation is required; material changes require fresh confirmation.

**--manual**
:   Quiesce helpers and persist the mutation gate for external repair. Exit or reboot
    does not clear it; validate repairs before clearing the gate.

**--salvage**
:   Prepare a verified replacement beside the preserved original. Report missing
    bytes, verified replacements, omissions, and unresolved repairs for review.

**--activate**
:   Separately review and revalidate activation at the verified replacement path.
    Preparation alone never authorizes activation. The path-selection CLI beyond
    the recorded plan is not specified; do not infer a positional path argument.

**--dry-run**, **--json**
:   Preview without mutation; together return the full proposed plan in `data.plan`
    and its digest in `data.plan_digest`, with requirements and conflicts.

**--confirm-plan** *sha256:HEX*
:   Bind unattended action to the exact reviewed recovery plan. The action flag is
    also required. Recompute under mutation ownership and refuse changed digests
    before writes. Recovery actions are mutually exclusive; a generic yes cannot
    authorize them. Interactive execution reviews and confirms the proposed action.

**--accept-system-changes**, **--accept-grafts**
:   Supply required protected-effect consents for this execution. Authentication and
    repository capabilities still apply; a plan digest cannot replace them.

Conflicting mutations stay blocked while unaffected verified packages and external
repair tools remain usable. Outcomes distinguish repaired, usable with unresolved
repairs, and replacement prepared with activation blocked. Isolated replacement
execution is described in [aslice-profile(1)](aslice-profile.1.md). Recovery requests
are not package plans and cannot be passed to `aslice apply`.

# EXAMPLES

```sh
aslice operation status --json
aslice operation stop --operation-id "$operation_id"
aslice recover --continue
aslice recover --salvage --dry-run --json
# Use the complete digest from the reviewed preview:
aslice recover --salvage --confirm-plan "$plan_digest" --json
```

# EXIT STATUS

0 requested action completed, or status/preview successfully reported; 1 failure,
unresolved recovery/activation, pending reboot, or incomplete post-commit verification;
2 invalid input, stale confirmation, or missing consent/authority; 4 contention
without unresolved recovery and without mutation; 130 cancellation safely completed.
Unresolved cancellation returns 1. Successful salvage preparation may return 0
with `activation_allowed = false`; inspect the outcome before acting. Committed
work remains committed and must not be retried as a fresh mutation.

# SEE ALSO

[aslice(1)](aslice.1.md), [aslice-db(1)](aslice-db.1.md), [aslice-self-update(1)](aslice-self-update.1.md),
[STATE-AND-RECOVERY](../docs/STATE-AND-RECOVERY.md#1025-command-requests-and-outcomes)
