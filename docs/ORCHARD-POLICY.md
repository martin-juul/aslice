# aslice Orchard Policy — The Maintainer Rulebook

- **Status:** Policy v0.1 — September 2026
- **Companion to:** [DESIGN.md](DESIGN.md) v1.1, [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) v0.3, [BUILD-INFRA.md](BUILD-INFRA.md) v0.1, [REPOSITORIES.md](REPOSITORIES.md) v0.3, [HOMEBREW-REVIEW.md](HOMEBREW-REVIEW.md) v0.3
- **Audience:** orchard maintainers, reviewers, and contributors
- **Commissioned by:** HOMEBREW-REVIEW.md §8 — one file where Homebrew scattered dozens of docs pages and tribal knowledge

---

## 1. Purpose and precedence

This file is the single rulebook for what may live in aslice's orchards, how packages are born, maintained, deprecated, and buried, and what bars a pull request must clear to merge. Homebrew accumulated these rules across dozens of documentation pages, review folklore, and maintainer memory; aslice writes them down while the project is young enough to fit them in one file.

**Precedence.** The specifications define *mechanism* — what fields exist, what the solver does, what CI can check. This file defines *policy* — what maintainers accept, require, and refuse. Where the two appear to conflict, the conflict is a bug: file an issue against whichever document is wrong. Schema fields referenced here that are not yet in PACKAGE-FORMAT.md v0.3 (`[deprecation]`, `[livecheck]`, `link`/`link_reason`, `notes`, `ctx.replace`) are the pending amendments listed in HOMEBREW-REVIEW.md §8; they are normative policy from this version onward and land in PACKAGE-FORMAT v0.4.

**Charter — not amendable by this document.** Three founding decisions outrank any policy edit (DESIGN §2.2 N7, §9.4, §1):

1. aslice collects no telemetry or analytics of any kind, ever — the project is infrastructure, not a product.
2. Download statistics are rejected as a value signal: obscure libraries downloaded once a month may have immense value precisely because we supply deprecated operating systems.
3. Scope is macOS 10.11–12 on Intel. No Apple Silicon, no newer macOS, no Linux — no matter how convenient a given PR would find it.

**The one-sentence test for every rule below:** does this make aslice more worthy of the trust of people running machines nobody else serves? If a rule stops answering yes, amend it (§18) rather than quietly ignoring it.

---

## 2. Orchard tiers and the acceptance bar

Two project orchards, two bars. (Third-party orchards set their own policy under their own trust level — REPOSITORIES.md §3; this file binds the project's orchards only.)

| | **core** (~300 packages) | **extended** (~2,000 packages) |
|---|---|---|
| Purpose | The platform stratum: shells, toolchains, VCS, TLS, runtimes, editors, the libraries everything links against | Everything else worth having: applications, niche libraries, legacy tools |
| Upstream status | Actively maintained, or maintained-by-aslice with a named maintainer who owns it | May be upstream-EOL — must carry `[deprecation] reason = "upstream-eol"` (§8) |
| Tests | Working `tests.star` smoke test, passing in CI on at least one OS × flavor — **no test, no merge** | Strongly encouraged; required for libraries with dependents in core |
| `[livecheck]` | **Required** (§9) | Encouraged |
| Reproducibility | Working toward `reproducible: true` (§14); nondeterminism is a tracked defect | Best-effort |
| Vendor binaries | Only if `redistribute = true` **and** payload-only by construction (§12) | Allowed with verifiable signature and honest OS/arch tags |
| Security posture | CVE flags are blocking work items for the named maintainer (§15) | CVE flags surface in `audit`; fixed best-effort |

**Hard rejections — both tiers, no exceptions, no override flags:**

- **Anything requiring SIP to be disabled, kexts, or patches to system files** (DESIGN §13.1). This is a marketing feature, not a limitation: aslice never asks users to weaken their OS.
- **Anything whose installation requires executing vendor or maintainer scripts.** Binary installs execute zero package code, for every package, forever (DESIGN §10.1). A `.pkg`/`.dmg` whose function requires its `preinstall`/`postinstall` scripts is out of scope; an accepted package *discovered* to require them is removed, not accommodated (§12).
- **Runtime dependencies on `/usr/lib` dylibs or `/usr/bin` tools** — the codified rejection of Homebrew's `uses_from_macos` (§6).
- **HEAD / unpinned builds in core.** Reproducibility and the lock model both depend on pins. Extended strongly discourages them; third-party orchards answer to their own trust level.
- **Software that is itself hostile** — known malware, scareware, or packages whose primary function is deception. Obscurity is never a reason for exclusion (charter); hostility always is.
- **License-less or license-violating content.** Every package carries an SPDX `license`; core binaries must be redistributable by the project (§12 for vendor terms).

**The acceptance review for a new core package** answers, in the PR body: who maintains it (a name, not "the community"), what its `[livecheck]` strategy is, why it belongs in core rather than extended, and what its test proves.

---

## 3. Naming, versioning, and revisions

- **Names** are lowercase ASCII letters, digits, and hyphens, starting with a letter, and match the upstream project's own name unless that name collides or is misleading. Aliases for historical renames live in the orchard's alias table so `adopt --from-homebrew` and old locks keep resolving.
- **Versioned packages** (`openssl@3`) exist when two majors are simultaneously maintained and depended upon. Versioned packages default to `link = false` (§6). Creating one is a review decision: each additional versioned lineage is a maintenance obligation, not a convenience.
- **`version`** is exactly the upstream version string, no `v` prefix, no suffixes. **`revision`** is an integer starting at 0, reset on every version bump, and bumped when the recipe changes the produced bits without an upstream version change: a new patch, a dependency change, a default-variant or build-flag default change.
- **A revision bump that changes what a library exports is an ABI event** and passes through the ABI gate (§10) like any version bump. When in doubt, treat it as one.
- **`min_os` / `max_os`** are claims CI verifies (§4); `arch` tags on vendor artifacts follow §12.

---

## 4. OS and flavor declarations: the honesty rule

aslice's entire platform story rests on tags users can trust. The rules:

- **`min_os` is the oldest release CI actually builds and smoke-runs on** — the merge gate builds at the formula's `min_os` and tests across `[min_os, 12]` on the farm VMs (§10). Claiming a floor you don't test is impossible by construction; claiming one you don't *build* at is a lint error.
- **Loud honesty over heroics** (DESIGN §4.1): a package that *could* be patched down to 10.11 but isn't worth the effort declares its real floor (10.12, 10.14, whatever it is) and moves on. Users plan around honest tags; they file angry issues around optimistic ones. Patch heroics to lower a floor are welcome — as patches (§7), with the floor lowered only when CI proves it.
- **Flavors** default to all three (v1/v2/v3). A formula may opt out of a flavor only when genuinely impossible — source that *requires* AVX intrinsics, upstream that dropped 32-bit-era CPU support — and the opt-out names the reason in review. "The tests are slow on v1" is not a reason; skipping tests is a flavor-CI flag, not a flavor removal.
- **`max_os`** exists for real upper bounds: vendor artifacts containing 32-bit code (`max_os = "10.14"`, §12), APIs removed before Monterey. It is never used to dodge a build failure — a package that fails on 12 gets fixed or declares why, in the open.

---

## 5. Variant discipline

Variants are aslice's answer to Homebrew's options disaster, and the discipline is what keeps them from becoming one (DESIGN §13.2):

- **`abi = true` variants are capped at six per package**, and each earns its place in review: what exported interface does it change, and who cannot be served without it? "Some users might like it" is not a justification — that's an `abi = false` variant or a third-party orchard.
- **`abi = false` variants are unconstrained** — they never spawn binary flavors, so they cost the project nothing.
- **Defaults serve the overwhelming majority, securely.** The default variant set is what the farm prebuilds; it should be what 95% of installs want, with secure options on (TLS on, deprecated protocols off) even when upstream defaults differ.
- **Naming:** short, lowercase, positive (`x265`, not `no-x264`). Negative variants exist only when the *default* is on and disabling is the exceptional need.
- **Conflicts fail fast.** Mutually exclusive variants error at configure time with a message naming both — never a broken build discovered at link time.
- **Popular non-default variants** may receive prebuilt slices when community requests show demand (§11) — the prebuild matrix grows by demonstrated need, not speculation.

---

## 6. Dependencies and system software

- **Runtime dependencies resolve to aslice packages only.** Never `/usr/lib` dylibs, never `/usr/bin` tools, never "whatever the system ships." This is the codified rejection of Homebrew's `uses_from_macos` (HOMEBREW-REVIEW.md §5), and the rationale is foundational: on 10.11 the system libraries *are the problem* — OpenSSL 0.9.8-era TLS is why the machines are stranded. Lint enforces it.
- **The only exceptions are system *frameworks*** — `Accelerate`, `SystemConfiguration`, `CoreAudio`, `CoreFoundation`, and the other always-present dyld-shared-cache frameworks enumerated in the lint allowlist. Frameworks are the platform's ABI, not its bundled software; the Accelerate-shim BLAS provider depends on this distinction. Additions to the allowlist are policy PRs against this file and the lint table together.
- **`link = false` — the principled keg-only** (HOMEBREW-REVIEW.md §4.5). A package installs into the store without linking into profiles when it would shadow macOS-provided tools or when a versioned lineage demands it. Policy: in core, versioned packages (`openssl@3` style) and anything shipping `bin/` names colliding with `/usr/bin` or `/bin` default to `link = false`; `link_reason` is mandatory and lint-enforced. Dependents never need the profile link — dependency resolution is store-path-based, so "unlinked but depended upon" is a normal state, not a hack. Users opt in per profile with `aslice link <pkg>`.

---

## 7. Patches

Patches are how a legacy platform stays alive, and also how orchards rot. The rules keep them honest:

- **Every patch carries a header comment:** origin (upstream commit/PR/issue URL, or the distro it was borrowed from), what it fixes, and the condition under which it can be removed ("drop when upstream ≥ 7.2", "drop if min_os rises to 10.13"). Undocumented patches are a lint error.
- **Preference order:** upstream backport → another maintainer's battle-tested patch (Debian, MacPorts, pkgsrc — credited) → local authorship. Local patches should be written to be upstreamable, and upstreaming them is part of the work.
- **Patches fix builds, portability, and security — never features.** A patch that adds functionality is a fork; if upstream won't take it and the platform needs it, the conversation is "should this be a different package," not "apply it quietly."
- **Patch count is a health signal.** A formula accumulating double-digit patches triggers a review conversation: is this package maintainable here, should its `min_os` rise, is it time for `[deprecation]`? The goal is not zero patches — it is *accounted-for* patches.

---

## 8. Deprecation and removal lifecycle

Packages have a life, and the orchard says where each one is (HOMEBREW-REVIEW.md §4.3):

```toml
[deprecation]
date         = "2027-03-01"    # when deprecation starts
reason       = "upstream-eol"  # upstream-eol | security | renamed | unmaintainable | other
replacement  = "ffmpeg7"       # optional pointer
disable_date = "2027-09-01"    # optional: new installs refuse after this
```

- **active → deprecated:** installs and `info`/`audit` warn with the reason and replacement; existing installs unaffected; the package still receives slices.
- **deprecated → disabled** (at `disable_date`): new installs refuse without `--force-disabled`; existing installs keep working, remain in locks, and keep their generations.
- **disabled → tombstoned:** the formula leaves orchard HEAD, but the index keeps a **permanent tombstone** — name, final version, reason, replacement — so historical snapshots and old locks resolve forever. Tombstoning is the thing aslice's snapshot model does *better* than git-tap archaeology; never delete the record.
- **Renames** are deprecations with `reason = "renamed"` and a mandatory `replacement`, plus an alias-table entry.
- **Security fast path:** a package with an unfixable, actively dangerous vulnerability may skip straight to disabled by maintainer vote, with the reason recorded. User safety outranks process.
- **EOL-in-extended is normal life**, not a failure: upstream-EOL packages live in extended with `reason = "upstream-eol"` indefinitely, as long as they still build and someone answers for them (DESIGN §13.1). Nobody else ships for these machines — hosting the honorable dead is part of the mission.

---

## 9. Freshness: livecheck and autobump

The platform is frozen; upstreams are not. Freshness automation is *the* ongoing workload, and policy treats it as such (HOMEBREW-REVIEW.md §4.2):

- **Every core package carries `[livecheck]`**; extended packages should. A core package whose livecheck strategy rots (upstream moved forges, changed tag scheme) is a bug against the named maintainer.
- **Defaults:** `skip_prerelease = true`, `throttle_days = 3`, `cooldown_days = 2`. The cooldown is the supply-chain poisoning window — time for a malicious upstream release to get caught before aslice ships it. For the historically risky ecosystems (npm, PyPI, RubyGems, crates), cooldown may be raised, never lowered below 2.
- **Autobump** opens PRs mechanically: new `version`, bot-fetched `sha256`, `revision` reset, changelog link. Patch bumps get lightweight review; **major bumps always get human review**, because sonames, `min_os` floors, and variant surfaces move on majors.
- **`aslice bump-pr <pkg> <version>`** is the human path and held to the same gate.
- **The metric is public:** median days-behind-upstream for core is on the farm dashboard. It is a workload gauge for maintainers — computed from orchard state, never from user machines (charter §1).

---

## 10. Merge gates: what CI must prove

Every orchard PR clears the same five gates (HOMEBREW-REVIEW.md §4.7); there is no maintainer override, because the gates are what make review about policy instead of compilation:

1. **Lint** — schema, this policy (`link_reason`, patch headers, license, description rules), plus the `--new-package` ruleset for additions.
2. **Matrix build** — sandboxed build on **every declared flavor** at the formula's `min_os`, then smoke-run on **each OS release in `[min_os, 12]`** on the farm VMs. Tests may be flagged flavor/OS-irrelevant (pure data packages), with the flag visible in the PR.
3. **Smoke test** — `tests.star` passes on at least one OS × flavor for core; the test must exercise the installed artifact, not just `--version` where more is possible.
4. **ABI gate** — for any PR changing a library's version or revision: CI diffs the ABI scan between old and new slice. A `compatibility_version` or symbol-fingerprint regression must be resolved by either an honest version/soname bump, or marking and scheduling **dependent rebuilds**, which the farm executes on merge and publishes *in the same index snapshot* — clients never see the "everything's broken until rebuilds land" window.
5. **Post-merge signing** — slice signing and the index snapshot update happen only after merge, on the signing host. No PR, however trusted, touches keys.

Review *humans* decide: policy fit, variant justification, patch quality, tier placement. Review *machines* decide: builds, tests, ABI. Neither does the other's job.

---

## 11. Prebuild policy: what gets slices

- **Core:** every flavor compatible with the formula's `min_os`, default variants, rebuilt promptly on merge.
- **Extended:** every compatible flavor, default variants, on a rolling cadence as farm capacity allows.
- **Popular non-default variants:** prebuilt when community requests demonstrate demand; each addition is a farm-capacity decision recorded in the PR.
- **Vendor binaries:** hosted slices only when `redistribute = true`; otherwise the formula is a pointer and the client fetches the vendor artifact itself (§12).
- **Prioritization when capacity forces choices** — the four signals of DESIGN §9.4, in order: **dependency centrality** (what the build graph unblocks), **build pain** (farm-measured hours and failure rate a slice saves), **irreplaceability** (nobody else ships this for these machines), **direct community requests** (orchard issues, in the open). Download counts are explicitly *not* a signal — on a deprecated-OS platform the rarest library may be the most valuable one (charter §1).

---

## 12. Vendor binary packages (pkg/dmg)

The policy for software that only exists as an installer (DESIGN §12.4, §13.1):

- **Payload-only, forever.** `preinstall`/`postinstall` scripts never execute; `.dmg` autolaunch mechanics never run. If a package's function genuinely requires its scripts, it is out of scope — and an accepted package discovered to require them is **removed, not accommodated**.
- **Signer pinning is mandatory.** The formula records the expected signing identity (`Developer ID Application: Vendor (TEAMID)`) and notarization expectation; a silent signer change upstream is a hard failure. Non-notarized-but-signed software may ship flagged loudly; unsigned software does not enter the project orchards.
- **Honest tags, verified.** `min_os`/`max_os`/`arch` are checked at pack time against the bundle's `LSMinimumSystemVersion` and the pkg Distribution requirements where present; a mismatch is a lint error.
- **32-bit and universal payloads** are first-class on the releases that execute them (10.11–10.14): any i386 content forces `max_os = "10.14"` or lower; universal payloads install **whole** — `lipo`-thinning invalidates the vendor signature, and signature integrity outranks disk savings.
- **Licensing is documented.** `redistribute = true` requires a license basis (permission, license terms, or clearly redistributable freeware) noted in the formula; `redistribute = false` yields a pointer formula. A vendor pulling or mutating an artifact produces a loud hash failure by design — never a silent install of different bits.
- **Core tier:** vendor binaries enter core only if redistributable **and** payload-only — core must never depend on a vendor's server being up.

---

## 13. Package documentation standards

- **`description`:** one line, no leading article, no repeating the package name, no marketing ("blazing fast"), ends with a period. It is what `search` shows; write it for someone who has never heard of the software.
- **`license`** is SPDX, `homepage` must be reachable at review time, `keywords` power search.
- **`notes`** (the caveats field): post-install guidance a user genuinely needs — "config lives in …", "run `aslice services start postgresql` to …" — printed at install and shown in `info`. If it isn't actionable, it isn't a note.
- **`tests.star`:** the smoke test proves the installed artifact works — link a binary against the library, run the tool on real input. `--version` alone is a last resort, and its use says so in a comment.

---

## 14. Reproducibility and the build environment

- Builds run in the normalized environment (fixed `LC_ALL`, `TZ`, `SOURCE_DATE_EPOCH`, prefix-mapping; BUILD-INFRA.md) on farm and laptop alike.
- **Core works toward `reproducible: true`** — bit-identical rebuilds on a second, independent builder (Phase 3 cross-checks). Nondeterminism discovered in a core package is a tracked defect with an owner, not a shrug.
- **Never hide nondeterminism** by freezing outputs or skipping the check; the badge means something because losing it is visible.

---

## 15. Security response

- **CVE flow:** the OSV/advisory feed flags an installed-version overlap → `audit` surfaces it to users immediately (the SBOM is already in the slice) → the named maintainer patches, backports (§7), or bumps. Security PRs jump the review queue but never skip the merge gates.
- **Embargoed fixes** land via private orchard branch and publish with a coordinated snapshot at embargo lift; the freeze is a TUF-metadata event, not a secret.
- **Unfixable and dangerous** → the §8 security fast path.
- **Maintainers never hold signing keys.** Signing lives on the signing host, post-merge, per REPOSITORIES.md; a compromised maintainer account can open PRs, not ship slices.

---

## 16. Governance and review process

- **Decisions by lazy consensus** (DESIGN §13.4): silence after a reasonable window is assent; escalations go to maintainer vote.
- **Review load is tiered:** patch bumps → any maintainer; major bumps, new extended packages → any maintainer with gates green; **new core packages, versioned lineages, `abi = true` variant additions, policy changes** → two maintainers, one of whom is not the author.
- **Every package in core has a named maintainer.** Orphaned core packages get 90 days flagged on the dashboard, then move to extended or deprecation — the tier promise (§2) is only real if someone keeps it.
- **Maintainers are expected to** keep their livechecks green, answer CVE flags, and work the review queue. Stepping back is honorable; disappearing is a signal to reassign.

---

## 17. Release cadence

- **The index publishes continuously:** every merge produces a new signed snapshot (TUF timestamp on the online key); there is no release day for packages.
- **Channels** (when Phase 3 lands): `edge` tracks the latest snapshot; `stable` tracks a snapshot soaked N days with a published soak report. `aslice config set channel stable` is the entire user interface.
- **Snapshot retention:** all snapshots for one year, monthly snapshots forever (HOMEBREW-REVIEW.md §6). Historical installs (`--index-snapshot`) are a feature; retention is what makes the promise real.
- **Dependent rebuilds ride the triggering snapshot** (§10 gate 4) — no separate "rebuild wave" days.
- **aslice itself** releases through the same machinery as package zero (self-update, HOMEBREW-REVIEW.md §4.1); client releases are the only thing resembling a "release," and they are generation-swapped like everything else.

---

## 18. Amending this policy

- Amendments are PRs against this file, decided like any policy change (§16). Every amendment states its rationale in the PR and, when merged, in this section's running history — the file is the project's institutional memory.
- **Charter items (§1) are not amendable here.** No telemetry, no download-count metrics, the 10.11–12 Intel scope: those are founding commitments, and a package manager that revisits its founding commitments by committee stops being trusted by the people it was founded for.
- **When a rule is consistently broken in practice,** amend the rule or enforce it — but never let the file and the orchard drift apart. A policy document nobody follows is worse than none: it teaches contributors that written words are decorative here.

---

*History: v0.1 (September 2026) — initial rulebook, commissioned by HOMEBREW-REVIEW.md §8: consolidates the acceptance bar (DESIGN §13.1), variant discipline (§13.2), the deprecation lifecycle, patch documentation, merge gates, and release cadence proposed across the review into one maintainer-facing document.*
