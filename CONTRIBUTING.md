# Contributing to aslice

aslice keeps deprecated Intel Macs (macOS 10.11–12, x86_64) useful. Contributions land in three places, in rough order of what the project needs most:

1. **The orchards** — packages. New formulae, version bumps, patches that keep old software building on old OS releases, better `tests.star` smoke tests. This is the daily work and the easiest way in.
2. **The farm** — build time. Spare Intel Macs can enroll as community evidence builders (`aslice farm enroll` + `--reproduce-only`): your machine rebuilds published jobs and reports digest agreement. Identical code to the real farm, zero authority, genuinely useful (BUILD-INFRA §7.4).
3. **aslice itself** — the manager is C++20. Talk in an issue before writing large features; the design docs (`docs/DESIGN.md` and companions) are the spec, and PRs that contradict them need to win the argument first.

## Ground rules (read these before your first PR)

- **No telemetry, ever.** Do not submit code that phones home, counts users, measures engagement, or "anonymously" reports anything. This is a charter decision, not a preference; PRs adding metrics plumbing are closed on sight. (The farm measures *itself* — build times, queue depth, reproducibility coverage — and that is the only instrumentation that exists.)
- **Zero install-time code.** Packages never execute code at install — no `post_install`, no installer scripts, ever. Vendor `.pkg`/`.dmg` software is payload-only extraction. This is the security model; there is no "just this once."
- **No sudo in steady state.** If your change needs root outside the declared `aslice-system` paths (kexts, SIP-off dev tools, system-domain services, `[system-patch]`), the change is wrong.
- **The platform is the platform.** 10.11–12, x86_64. PRs for Apple Silicon, macOS 13+, or Linux are out of scope by charter, however good they are.

## Writing a formula

The format is specified in `docs/PACKAGE-FORMAT.md` (read §3 and §6 first), the rules in `docs/ORCHARD-POLICY.md`. What reviewers enforce, in short:

- **`min_os` accuracy.** Declare the oldest OS you are prepared to stand behind. CI builds at that floor and smoke-runs every release up to 12 on the VM matrix — optimism does not survive that gauntlet. Patch heroics land as *patches*, and the floor is lowered only when CI proves it (ORCHARD-POLICY §4).
- **Variant discipline.** `abi = true` variants are capped at six per package and each must justify itself in review: what exported interface does it change, and who is unserved without it? `abi = false` variants are free. Defaults serve ~95% of installs, securely — TLS on, deprecated protocols off, even when upstream defaults differ (§5).
- **Patches carry headers.** Every patch file documents its origin (upstream commit/PR/issue URL, or the distro it was borrowed from, credited), what it fixes, and its removal condition ("drop when upstream ≥ 7.2"). Undocumented patches are a lint error. Patches fix builds, portability, and security — never features; a feature patch is a fork wearing a trench coat (§7).
- **Documentation standards.** One-line `description` (no leading article, no marketing, ends with a period), SPDX `license`, reachable `homepage`, `keywords` that help search, and `notes` only when a user genuinely needs post-install guidance. `tests.star` must prove the installed artifact works — link against the library, run the tool on real input; `--version` is a last resort and says so in a comment (§14).
- **`[livecheck]` is required in core.** If upstream releases software, the formula says how to detect it (§9).
- **Dependencies resolve to aslice packages.** Leaning on `/usr/lib` dylibs or `/usr/bin` tools is rejected — on this platform the system libraries are the problem. The exceptions are macOS *frameworks* on the allowlist (Accelerate, SystemConfiguration, CoreAudio, …), enumerated in DESIGN §13.1.

### The local loop

```sh
aslice create <url>                     # scaffold a formula from a tarball
aslice lint ./my-formula                # schema + policy + --new-package rules
aslice build ./my-formula               # full sandboxed pipeline, the same one CI runs
aslice build ./my-formula --keep --shell  # drop into the sandbox at the failed phase
aslice test my-formula                  # tests.star against the installed result
```

The build your laptop runs is byte-for-byte the pipeline the farm runs (BUILD-INFRA §1). "Works on my machine" is eliminated by construction — if it passes your sandbox, it passes CI's.

### Porting from Homebrew

`tools/` contains the Ruby-formula importer (DESIGN §13.3). It handles the mechanical translation; you handle the judgment calls:

| Homebrew | aslice |
|---|---|
| `keg_only` | `link = false` + `link_reason` (PACKAGE-FORMAT §3.8) |
| `caveats` | `notes` — actionable only |
| `post_install` | **does not translate** — declare `[service]`, use `notes`, or rethink |
| `uses_from_macos` | rejected, except allowlisted frameworks |
| `deprecate!`/`disable!` | `[deprecation]` table (§3.14) |
| `livecheck` block | `[livecheck]` table (§3.15) — usually near-mechanical |
| `plist_options` / `service` | `[service]` table (generated plist) |

MacPorts and pkgsrc patches for 10.11-era portability are fair game — credit them in the patch header.

## The review process

Merge gates are mechanical (ORCHARD-POLICY §10): lint → sandboxed build on every declared flavor → smoke-run on every OS in `[min_os, 12]` → ABI gate for provider bumps, with dependent rebuilds published in the same atomic snapshot. Signing happens post-merge on the signing host; **maintainers never hold signing keys**, so a green PR is the whole job.

Review load is tiered: patch bumps need any maintainer; major bumps and new extended packages need any maintainer with gates green; new core packages, versioned lineages, `abi = true` variant additions, system-software and system-patch packages, and policy changes need two maintainers, one not the author (§17). Decisions run on lazy consensus — silence in a reasonable window is assent, and process lawyering is not a sport we play.

## Documentation style

The docs ship with the manager, and reviewers hold them to the same bar as formulae. Write the way the code is written: mechanics first, one fact per sentence, one idea per paragraph.

- **Say what the thing does, then why.** The reader came for the mechanism; motivation follows it.
- **Negation is for guarantees, not decoration.** "It doesn't X — it Ys" is a tic, not an explanation. Reserve "never"/"not" for places where the reader might genuinely expect the opposite (normative guarantees: "never executes", "not accepted").
- **Cut intensifiers.** "simply", "exactly", "obviously", "just" do no work; delete them and the sentence keeps its meaning. If it doesn't, the sentence was wrong.
- **Mechanisms, not adjectives.** Don't call a design clean or robust; state the invariant and let the reader form the adjective.
- **Headers describe.** "The state database's role", not "The state database's role, stated plainly".
- **Tables and code carry the precision; prose carries the reader.** A normative must/never/may in prose must also hold in the spec it summarizes.
- **Changelog entries are historical record.** Never edit them retroactively, even to fix the prose.

## Conduct

There is no code of conduct document, and there won't be one. People are expected to be decent to each other without a policy forcing it.

Discussion here is direct. This is not a corporate project, and nobody is going to wrap technical feedback in three layers of diplomacy: if you are acting like an idiot, expect to be told that you are acting like an idiot. That is not a conduct violation — it is how direct technical projects talk. Dish it out in good faith, take it in good faith, and keep it about the work.

Maintainer judgment on what's over the line is final. The line is short and obvious: keep it about the work.

## License

Contributions are licensed under the project's license. By opening a PR you agree your contribution may be distributed, rebuilt, and served by the farm under those terms.

---

*History: September 2026 — editorial pass: prose revised for directness; `min_os` honesty renamed `min_os` accuracy for consistency with AUTHORING.md; documentation style section added. No rule changes. September 2026 — prose rewrite throughout: reworded in the project's technical-writing voice; no rule changes.*
