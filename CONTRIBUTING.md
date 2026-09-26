# Contributing to aslice

aslice keeps deprecated Intel Macs (macOS 10.11–12, x86_64) useful. Contributions land in three places, in rough order of what the project needs most:

1. **The orchards** — packages. New formulae, version bumps, patches that keep old software building on old OS releases, better `tests.star` smoke tests. This is the daily work and the easiest way in.
2. **The farm** — build time. Spare Intel Macs can enroll as community evidence builders (`aslice farm enroll` + `--reproduce-only`): your machine rebuilds published jobs and reports digest agreement. Your machine runs the same code as the official farm, but its results carry no publication authority ([BUILD-INFRA §7.4](docs/BUILD-INFRA.md#community-builders--the-users-machine-enlisted-safely)).
3. **aslice itself** — the manager is C++20. Talk in an issue before writing large features; the design docs (`docs/DESIGN.md` and companions) are the spec, and PRs that contradict them need to win the argument first.

*Project terms, acronyms, and the Homebrew translation table: [docs/NOMENCLATURE.md](docs/NOMENCLATURE.md).*

## Ground rules (read these before your first PR)

- **No telemetry, ever.** Do not submit code that phones home, counts users, measures engagement, or "anonymously" reports anything. This is a charter decision, not a preference; PRs adding metrics plumbing are closed on sight. (The farm measures *itself* — build times, queue depth, reproducibility coverage — and that is the only instrumentation that exists.)
- **Zero undeclared install-time code.** Packages never execute code at install — no `post_install`, and no installer scripts unless declared as a graft: hash-pinned, approved by the user per package, sandboxed to a declared behavior manifest, farm-rehearsed for core and extended ([DESIGN §12.15](docs/DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)). Vendor `.pkg`/`.dmg` software is payload-only extraction by default. This is the security model; outside a declared graft there is no "just this once."
- **No sudo in steady state.** If your change needs root outside the declared `aslice-system` paths (kexts, SIP-off dev tools, system-domain services, `[system-patch]`), the change is wrong.
- **The platform is the platform.** 10.11–12, x86_64. PRs for Apple Silicon, macOS 13+, or Linux are out of scope by charter, however good they are.

## Writing a formula

Target changes at `develop` (dev). Staging uses `beta` and production uses `master`, all in the same repository and its mirrors. This applies to aslice and third-party orchards as well as core and extended. Build and freeze a candidate once, then promote its identical artifacts through staging to prod. Do not hardcode environment-specific configuration or edit payloads to change version suffixes. See [ORCHARD-POLICY §18.1](docs/ORCHARD-POLICY.md#181-environments-branching-and-promoted-builds) for branching and [ORCHARD-POLICY §18.2](docs/ORCHARD-POLICY.md#182-release-versioning-and-unchanged-content-enforcement) for `x.y.z-develop` → `x.y.z-beta` → `x.y.z`, required bumps, and promotion-failure reports.

Read [PACKAGE-FORMAT §3](docs/PACKAGE-FORMAT.md#packagetoml--full-schema) and [PACKAGE-FORMAT §6](docs/PACKAGE-FORMAT.md#build-instructions) for the format, then `docs/ORCHARD-POLICY.md` for the acceptance rules. Reviewers check the following:

- **`min_os` accuracy.** Declare the oldest OS you are prepared to stand behind. CI builds at that floor and smoke-runs every release up to 12 on the VM matrix — optimism does not survive that gauntlet. Patch heroics land as *patches*, and the floor is lowered only when CI proves it ([ORCHARD-POLICY §4](docs/ORCHARD-POLICY.md#os-and-flavor-declarations-the-honesty-rule)).
- **Variant discipline.** `abi = true` variants carry no cap: name the exported interface the variant changes, and review checks the tag against the ABI scan — not the worthiness of the need. ffmpeg-class packages legitimately carry many codec combinations, uncommon ones included; what a user enables is the user's call. `abi = false` variants are free. Defaults serve ~95% of installs, securely — TLS on, deprecated protocols off, even when upstream defaults differ ([ORCHARD-POLICY §5](docs/ORCHARD-POLICY.md#variant-discipline)).
- **Patches carry headers.** Every patch file documents its origin (upstream commit/PR/issue URL, or the distro it was borrowed from, credited), what it fixes, and its removal condition ("drop when upstream ≥ 7.2"). Undocumented patches are a lint error. Patches fix builds, portability, and security — never features; a feature patch is a fork wearing a trench coat ([ORCHARD-POLICY §7](docs/ORCHARD-POLICY.md#patches)).
- **Documentation standards.** One-line `description` (no leading article, no marketing, ends with a period), SPDX `license`, reachable `homepage`, `keywords` that help search, and `notes` only when a user genuinely needs post-install guidance. `tests.star` must prove the installed artifact works — link against the library, run the tool on real input; `--version` is a last resort and says so in a comment ([ORCHARD-POLICY §14](docs/ORCHARD-POLICY.md#package-documentation-standards)).
- **`[livecheck]` is required in core.** If upstream releases software, the formula says how to detect it ([ORCHARD-POLICY §9](docs/ORCHARD-POLICY.md#freshness-livecheck-and-autobump)).
- **Dependencies resolve to aslice packages.** Leaning on `/usr/lib` dylibs or `/usr/bin` tools is rejected — on this platform the system libraries are the problem. The exceptions are macOS *frameworks* on the allowlist (Accelerate, SystemConfiguration, CoreAudio, …), enumerated in [DESIGN §13.1](docs/DESIGN.md#package-acceptance-policy).

### The local loop

```sh
aslice create <url>                     # scaffold a formula from a tarball
aslice lint ./my-formula                # schema + policy + --new-package rules
aslice build ./my-formula               # full sandboxed pipeline, the same one CI runs
aslice build ./my-formula --keep --shell  # drop into the sandbox at the failed phase
aslice test my-formula                  # tests.star against the installed result
```

Local and farm builds use the same pipeline, but host capability and OS coverage still differ. `orchard ci` reports tests deferred to the farm; a local pass alone does not prove the complete matrix.

### Porting from Homebrew

`tools/` contains the Ruby-formula importer ([DESIGN §13.3](docs/DESIGN.md#coexistence-and-migration-from-homebrew)). It handles the mechanical translation; you handle the judgment calls:

| Homebrew | aslice |
|---|---|
| `keg_only` | `link = false` + `link_reason` ([PACKAGE-FORMAT §3.8](docs/PACKAGE-FORMAT.md#install--declarative-post-install-behavior)) |
| `caveats` | `notes` — actionable only |
| `post_install` | **does not translate** — declare `[service]`, use `notes`, or rethink; a vendor installer script the payload cannot replace is declared as a graft ([PACKAGE-FORMAT §3.11](docs/PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software)) |
| `uses_from_macos` | rejected, except allowlisted frameworks |
| `deprecate!`/`disable!` | `[deprecation]` table ([PACKAGE-FORMAT §3.14](docs/PACKAGE-FORMAT.md#deprecation--the-package-lifecycle-declared-v06)) |
| `livecheck` block | `[livecheck]` table ([PACKAGE-FORMAT §3.15](docs/PACKAGE-FORMAT.md#livecheck--upstream-freshness-declared-v06)) — usually near-mechanical |
| `plist_options` / `service` | `[service]` table (generated plist) |

MacPorts and pkgsrc patches for 10.11-era portability are fair game — credit them in the patch header.

## The review process

Merge gates are mechanical ([ORCHARD-POLICY §10](docs/ORCHARD-POLICY.md#merge-gates-what-ci-must-prove)): lint → sandboxed build on every declared flavor → smoke-run on every OS in `[min_os, 12]` → ABI gate for provider bumps → graft rehearsal for graft-bearing binaries, with dependent rebuilds published in the same atomic snapshot. Malware checks and required independent rebuilds remain publication gates; missing capacity leaves releases pending. During single-owner launch, the owner's merge is the final human release approval. The publisher automatically delivers an authenticated candidate to the dedicated networked release Pi, verifies returned signatures, and activates the complete release atomically ([KEY-RUNBOOK §2.1](docs/KEY-RUNBOOK.md#automatic-orchard-to-client-publication)). Clients discover it at metadata refresh; publication does not install it.

Owner approval applies to all changes during single-owner launch, including new core packages, versioned lineages, `abi = true` variants, system-software and system-patch packages, and policy changes. The owner may approve their own changes; second-reviewer and maintainer-vote requirements are superseded for this phase ([ORCHARD-POLICY §17](docs/ORCHARD-POLICY.md#governance-and-review-process)). Independent maintainers can help review; multi-party governance remains a future transition. Automated gates cannot be waived.

## Documentation style

The docs ship with the manager, and reviewers hold them to the same bar as formulae. Write the way the code is written: mechanics first, one fact per sentence, one idea per paragraph.

- **Say what the thing does, then why.** The reader came for the mechanism; motivation follows it.
- **Negation is for guarantees, not decoration.** "It doesn't X — it Ys" is a tic, not an explanation. Reserve "never"/"not" for places where the reader might genuinely expect the opposite (normative guarantees: "never executes", "not accepted").
- **Cut intensifiers.** "simply", "exactly", "obviously", "just" do no work; delete them and the sentence keeps its meaning. If it doesn't, the sentence was wrong.
- **Mechanisms, not adjectives.** Don't call a design clean or robust; state the invariant and let the reader form the adjective.
- **Headers describe.** "The state database's role", not "The state database's role, stated plainly".
- **Tables and code carry the precision; prose carries the reader.** A normative must/never/may in prose must also hold in the spec it summarizes.
- **History wording is immutable.** Never edit historical change descriptions retroactively, even to fix the prose. Preserve links, code, and historical section references; layout and ordering follow the convention below.

Documents with revision records end with one unnumbered `## History` section. Put a
Markdown table inside one closed `<details>` disclosure, with
`<summary>Document revision history</summary>` and no `open` attribute. Leave a blank
line before and after the table. Use `Version | Date | Changes` for versioned
documents and `Date | Changes` for unversioned documents; do not introduce versions
for an unversioned document.

Keep one row per historical entry. Remove exact duplicates, but retain distinct
accounts of the same revision as separate rows. Sort explicit document versions
numerically, newest first; place a recorded version range by its newest endpoint.
Put entries without a version after versioned entries. Where chronology cannot be
established, preserve source order. Keep the recorded date precision and use
`Not recorded` for missing metadata rather than inferring it from adjacent entries
or the current status date. Escape table pipes, including pipes in inline code.

Keep current status, version, date, and substantive qualifications at the top;
move revision notes from headers and scattered footers into History. Preserve
numbered sections and existing link targets. Increment an existing document
revision and record each documentation change; for an existing unversioned
history, add a dated entry. Software release versions are separate. Documents
without revision records need no History section. Archived sources, provenance
records, and narrative discussions of history are outside this convention.

## Conduct

There is no code of conduct document, and there won't be one. People are expected to be decent to each other without a policy forcing it.

Discussion here is direct. This is not a corporate project, and nobody is going to wrap technical feedback in three layers of diplomacy: if you are acting like an idiot, expect to be told that you are acting like an idiot. That is not a conduct violation — it is how direct technical projects talk. Dish it out in good faith, take it in good faith, and keep it about the work.

Maintainer judgment on what's over the line is final. The line is short and obvious: keep it about the work.

## License

Original contributions are licensed under [Apache-2.0](LICENSE), the project's license. Third-party material retains its applicable license and attribution. By submitting a contribution you agree to Apache-2.0's contribution terms.

---

## History

<details>
<summary>Document revision history</summary>

| Date | Changes |
|---|---|
| September 2026 | Consolidate revision notes into a collapsible history table and document the history convention; historical wording is unchanged. |
| September 2026 | grafts: the zero-install-time-code ground rule gains its declared exception (owner decision) — vendor installer scripts as declared, user-approved, farm-rehearsed grafts (DESIGN §12.15); the rule bullet updated, the merge-gate summary gains the rehearsal gate, and the porting table's `post_install` row gains the graft path. |
| September 2026 | editorial pass: prose revised for directness; `min_os` honesty renamed `min_os` accuracy for consistency with AUTHORING.md; documentation style section added. No rule changes. |
| September 2026 | prose rewrite throughout: reworded in the project's technical-writing voice; no rule changes. |
| September 2026 | NOMENCLATURE.md vocabulary pointer added; no rule changes. |
| September 2026 | variant discipline rule updated: the six-variant cap is retired (ORCHARD-POLICY v1.5); variants are governed by need and honest ABI tags. |
| September 2026 | prose rewrite of the contribution and review introductions; no rule changes. |
| September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |

</details>
