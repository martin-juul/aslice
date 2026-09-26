% ASLICE-ORCHARD(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-orchard — maintain an orchard: lifecycle, health, the local merge gate

# SYNOPSIS

`aslice orchard add` *org/orchard*

`aslice orchard pin` *org/orchard* *commit*

`aslice orchard lint` [*path*] [`--json`]

`aslice orchard doctor` [*path*] [`--json`]

`aslice orchard freshness` [*path*] [`--json`]

`aslice orchard ci` [*pkg*…] [`--flavors` *v2,v3*] [`--all`]

`aslice orchard dependents` *pkg* [`--transitive`] [`--json`]

`aslice orchard deprecate` *pkg* `--reason` *reason* [`--replacement` *pkg*] `--date` *date* [`--disable-date` *date*]

`aslice orchard disable` *pkg*

`aslice orchard undeprecate` *pkg*

`aslice orchard tombstone` *pkg*

`aslice orchard rename` *old* *new*

`aslice orchard port` `--from-homebrew` *formula*

# DESCRIPTION

The orchard group is the maintainer's CLI: everything between authoring one formula (`aslice create`, `aslice lint`, `aslice test`, `aslice bump-pr`) and publishing the result (`aslice repo build`). **add** and **pin** are the consumer side — follow someone's orchard and pin it to a commit. Every other verb operates on a **local orchard checkout**: pass *path*, or run from inside the tree and the orchard is discovered by walking up to the directory whose children are formula directories.

**deprecate**, **disable**, **undeprecate**, **tombstone**, **rename** edit the formula's `[deprecation]` table — the lifecycle, declared ([PACKAGE-FORMAT §3.14](../docs/PACKAGE-FORMAT.md#deprecation--the-package-lifecycle-declared-v06), [ORCHARD-POLICY §8](../docs/ORCHARD-POLICY.md#deprecation-and-removal-lifecycle)). Each verb validates what the linter will check (dates in order; `replacement` required when `reason = "renamed"`, and resolving whenever supplied), lints the formula, and opens a PR; on a plain git remote without PR machinery, the branch and diff are printed instead. **tombstone** removes the formula from HEAD — the index keeps the name, final version, reason, and replacement forever — and refuses a name that still has enabled dependents. The security fast path, straight to disabled by owner approval during single-owner launch, is `deprecate --reason security --disable-date` with today's date; the approval is recorded in the PR.

**lint** checks every formula in the tree, not just one. **doctor** is the orchard-side counterpart of aslice-doctor(1): a curated battery with stable check IDs (`orchard.lint.*`, `orchard.livecheck.*`, `orchard.deprecation.*`), pass/warn/fail with the remedy named — lint clean tree-wide, core formulae carrying `tests.star` and a working `[livecheck]`, deprecation coherence, documented patches, named maintainers, resolvable `provides`/`conflicts`/`replaces`, no duplicate names. **freshness** runs every formula's livecheck and prints days-behind-upstream per package, worst first, with the orchard median — the number the farm dashboard publishes ([ORCHARD-POLICY §9](../docs/ORCHARD-POLICY.md#freshness-livecheck-and-autobump)). Formulae without `[livecheck]` are reported untracked, which is a finding in core.

**ci** runs the merge gate ([ORCHARD-POLICY §10](../docs/ORCHARD-POLICY.md#merge-gates-what-ci-must-prove)) on your machine before the farm does: lint, a sandboxed build per declared flavor at the formula's `min_os`, the `tests.star` smoke test, the ABI gate diffed against a published index snapshot, and — for graft-bearing binaries — rehearsal of each declared graft against its behavior manifest — the same harness the farm runs. With no arguments it scopes to the packages changed against the upstream branch; `--all` prices the full orchard and says so before starting. Passing locally merges nothing; the farm re-runs all six gates.

**dependents** prints reverse dependencies from the orchard graph (`[depends]`, `[extension]`, `[ride]`), marking dynamic, static, header, generated, bundled, and build-tool edges and their triggering paths. Changed recipe, source, toolchain, configuration, or selected dependency inputs invalidate affected transitive consumers even with compatible ABI; exact artifact bindings remain separate evidence. The farm's dependent-rebuild cascade runs the same query server-side, so what breaks on a bump is known before the PR, not after the merge.

**port** translates a simple Homebrew Ruby formula into a TOML+Starlark draft for human review. Only the simple majority translate mechanically; the rest need manual porting. Use `aslice machine import --from-brewfile` (aslice-machine(1)) to migrate a machine, and **port** to prepare a formula.

# LIMITS

**ci** cannot conjure the farm's VMs: rehearsal runs locally on the host OS, but the cross-OS tiers — smoke-runs on every release in `[min_os, 12]`, and graft rehearsal on every OS the artifact targets — are marked deferred-to-farm, never faked. **freshness** is only as good as each formula's `[livecheck]`; a rotted strategy is a bug against the named maintainer, and **doctor** says so. The mutating verbs change nothing until their PR merges — there is no maintainer override of the merge gate for them to bypass.

# EXIT STATUS

**lint**, **doctor**, **freshness**, **ci**: 0 all-pass, 1 warnings only, 2 any fail — the aslice-doctor(1) contract. The mutating verbs return 0 when the PR (or branch and diff) is ready.

# EXAMPLES

```sh
aslice orchard add myorg/orchard
aslice orchard pin myorg/orchard "$commit"
aslice orchard lint
aslice orchard doctor --json
aslice orchard freshness
aslice orchard ci extended:ffmpeg --flavors v2,v3
aslice orchard dependents x264 --transitive
aslice orchard deprecate extended:ffmpeg --reason upstream-eol --date 2027-03-01
aslice orchard disable extended:ffmpeg
aslice orchard undeprecate extended:ffmpeg
aslice orchard rename extended:ffmpeg extended:ffmpeg7
aslice orchard tombstone extended:ffmpeg
aslice orchard port --from-homebrew ffmpeg
```

# SEE ALSO

aslice(1), aslice-doctor(1), aslice-repo(1), aslice-machine(1), aslice-graft(1), [AUTHORING §12](../docs/AUTHORING.md#maintaining-the-orchard), [DESIGN §12.14](../docs/DESIGN.md#orchard-maintenance-the-maintainers-cli), [ORCHARD-POLICY §8](../docs/ORCHARD-POLICY.md#deprecation-and-removal-lifecycle) and [ORCHARD-POLICY §10](../docs/ORCHARD-POLICY.md#merge-gates-what-ci-must-prove)
