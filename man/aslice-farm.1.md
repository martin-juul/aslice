% ASLICE-FARM(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-farm — plan builds and run farm coordination or workers

# SYNOPSIS

`aslice farm plan`

`aslice farm coordinator`

`aslice farm agent` [`--once`] [`--vm-guest`] [`--reproduce-only`]

`aslice farm enroll --project` *url*

# DESCRIPTION

These are specified interfaces; this page does not establish completed implementation.

**plan** diffs the orchard, expands affected formulae across the declared build
and OS-test matrix, and orders dependency work. Changed inputs invalidate affected
transitive consumers even with compatible ABI. The orchard selector and output
destination grammar are not yet specified.

**coordinator** schedules eligible work, collects evidence, and applies gates.
Dispatch requires qualified CPU, OS, guest, and resource capabilities; missing
workers or required tests remain pending. Capacity shortages do not waive gates.
Agents exchange signed jobs and results rather than sharing the coordinator database.

**agent** pulls signed jobs, executes the sandboxed pipeline, and uploads results.
It runs on demand, not as an automatically launched client daemon. **--once** is
the single-run adapter used by self-hosted CI. **--vm-guest** executes matrix tests
inside the disposable guest. **--reproduce-only** limits participation to verification
jobs. Valid combinations of these mode flags are unspecified; the examples use
them separately.

**enroll --project** names the coordinator project URL, issues the agent key, and
pins the coordinator key. Community workers contribute reproduction evidence;
their output never becomes a served release directly. Enrollment is not proof of
worker qualification, and build workers receive no publication credentials.

Farm cancellation revokes the guest lease and preserves logs and receipts;
late results cannot satisfy revoked gates. No public cancellation subcommand or
family-wide dry-run/exit-code extension is specified. BUILD-INFRA owns scheduling,
enrollment, quarantine, and publication requirements.

# EXAMPLES

```sh
aslice farm plan
aslice farm coordinator
aslice farm enroll --project https://farm.aslice.sh
aslice farm agent --once
aslice farm agent --vm-guest
aslice farm agent --reproduce-only
```

# EXIT STATUS

The common statuses in [aslice(1)](aslice.1.md#exit-status) apply where
relevant: 0 success, 1 error or recovery required, 2 plan refused, 4 contention
without unresolved recovery, and 130 safely completed cancellation. No additional
family-specific numeric statuses are specified.

# SEE ALSO

[aslice(1)](aslice.1.md), [aslice-author(1)](aslice-author.1.md), [aslice-repo(1)](aslice-repo.1.md),
[BUILD-INFRA](../docs/BUILD-INFRA.md), [DATABASE](../docs/DATABASE.md#6-farm-coordinator)
