% ASLICE-ADOPT(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-adopt — plan migration of installed Homebrew packages

# SYNOPSIS

`aslice adopt --from-homebrew`

# DESCRIPTION

These are specified interfaces; this page does not establish completed implementation.

**--from-homebrew** reads Homebrew's Cellar and `brew leaves`, maps names through
the maintained alias table, and produces an install plan recreating that leaf set.
Old `--with-*` options map to variants where aliases exist. Cask leaves map to
vendor-binary packages where available; incompatible OS tags are flagged for review.

Review the proposed plan before installing. The command reuses package intent,
not Homebrew binaries or their prefix assumptions, and does not remove Homebrew.
It never takes ownership of `/usr/local`. Unmapped entries require review; the
exact report schema and output-file option are unspecified.

For a Brewfile rather than the installed leaf set, use machine import. Formula
authors use orchard port; neither is an alternate spelling of adopt.

# EXAMPLES

```sh
aslice adopt --from-homebrew
```

# EXIT STATUS

The common statuses in [aslice(1)](aslice.1.md#exit-status) apply where
relevant: 0 success, 1 error or recovery required, 2 plan refused, 4 contention
without unresolved recovery, and 130 safely completed cancellation. No additional
family-specific numeric statuses are specified.

# SEE ALSO

[aslice(1)](aslice.1.md), [aslice-apply(1)](aslice-apply.1.md), [aslice-machine(1)](aslice-machine.1.md),
[aslice-orchard(1)](aslice-orchard.1.md),
[DESIGN](../docs/DESIGN.md#coexistence-and-migration-from-homebrew)
