% ASLICE-INSPECT(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-inspect — find packages and inspect their metadata

# SYNOPSIS

`aslice search` *query*

`aslice info` *package*

`aslice flavors` *package*

`aslice leaves` [`--user-built`]

`aslice why` *package*

`aslice provenance` *package*

`aslice audit`

# DESCRIPTION

These are specified interfaces; this page does not establish completed implementation.

**search** matches package names and descriptions. **info** reports versions,
variants, dependencies, size, provenance, local-build origin, and actionable notes.
For a package declared `link = false`, info explains its `link_reason`.
*query* is the search text; pattern syntax and empty-query behavior are unspecified.
*package* identifies the package being inspected. Core names are bare; other
repositories require their namespace, for example `audiolab:convolver`.

**flavors** shows the prebuilt matrix for the current machine. Availability does
not override CPU or OS constraints. **leaves** lists installed packages without
installed dependents; **--user-built** restricts it to locally compiled packages.
A leaf is not necessarily an explicitly requested package. **why** explains which
installed packages require the named package; use orchard dependents for recipe
impact analysis before a build.

**provenance** shows authenticated build evidence: builder, source hash, formula
commit, toolchain, environment, and reproducibility evidence. Vendor packages
instead record artifact URL/hash, signer and notarization state at packaging,
repackager version, and hosted versus vendor-fetched origin. Provenance is separate
from canonical artifact identity.

**audit** reports known vulnerabilities in the installed set. It does not perform
updates. Use upgrade's security modes for remediation and needs-restarting for
remaining runtime actions. A family-specific audit exit convention for findings
is not specified; do not infer needs-restarting's status 3 here.

# OPTIONS AND LIMITS

**--json** selects the common machine-readable output. Command-specific report
schemas and search ordering are not specified here. Inspection does not install,
remove, or repair packages; repository refresh still authenticates its inputs.

# EXAMPLES

```sh
aslice search ffmpeg
aslice info extended:ffmpeg
aslice flavors extended:ffmpeg
aslice leaves --user-built
aslice why x264
aslice provenance extended:ffmpeg
aslice audit
```

# EXIT STATUS

The common statuses in [aslice(1)](aslice.1.md#exit-status) apply where
relevant: 0 success, 1 error or recovery required, 2 plan refused, 4 contention
without unresolved recovery, and 130 safely completed cancellation. No additional
family-specific numeric statuses are specified.

# SEE ALSO

[aslice(1)](aslice.1.md), [aslice-upgrade(1)](aslice-upgrade.1.md), [aslice-needs-restarting(1)](aslice-needs-restarting.1.md),
[aslice-orchard(1)](aslice-orchard.1.md),
[MANUAL](../docs/MANUAL.md#everyday-commands), [DESIGN](../docs/DESIGN.md#build-provenance)
