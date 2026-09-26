# aslice Orchard Policy — The Maintainer Rulebook

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

- **Status:** Policy v1.16 — September 2026
- **Companion to:** [DESIGN.md](DESIGN.md), [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md), [BUILD-INFRA.md](BUILD-INFRA.md), [REPOSITORIES.md](REPOSITORIES.md), [HOMEBREW-REVIEW.md](HOMEBREW-REVIEW.md), [TOOLCHAIN.md](TOOLCHAIN.md)
- **Audience:** orchard maintainers, reviewers, and contributors
- **Commissioned by:** [HOMEBREW-REVIEW §8](HOMEBREW-REVIEW.md#spec-amendment-checklist) — one file where Homebrew scattered dozens of docs pages and tribal knowledge
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md) — project terms, acronyms, and the Homebrew translation table.

---

Navigation: [1. Purpose and precedence](#purpose-and-precedence) · [2. Orchard tiers and the acceptance bar](#orchard-tiers-and-the-acceptance-bar) · [3. Naming, versioning, and revisions](#naming-versioning-and-revisions) · [4. OS and flavor declarations: the honesty rule](#os-and-flavor-declarations-the-honesty-rule) · [5. Variant discipline](#variant-discipline) · [6. Dependencies and system software](#dependencies-and-system-software) · [7. Patches](#patches) · [8. Deprecation and removal lifecycle](#deprecation-and-removal-lifecycle) · [9. Freshness: livecheck and autobump](#freshness-livecheck-and-autobump) · [10. Merge gates: what CI must prove](#merge-gates-what-ci-must-prove) · [11. Prebuild policy: what gets slices](#prebuild-policy-what-gets-slices) · [12. Vendor binary packages (pkg/dmg)](#vendor-binary-packages-pkgdmg) · [13. System software packages (kexts, SIP-disabled tools, and system patches)](#system-software-packages-kexts-sip-disabled-tools-and-system-patches) · [14. Package documentation standards](#package-documentation-standards) · [15. Reproducibility and the build environment](#reproducibility-and-the-build-environment) · [16. Security response](#security-response) · [17. Governance and review process](#governance-and-review-process) · [18. Release cadence](#release-cadence) · [19. Amending this policy](#amending-this-policy)

<a id="purpose-and-precedence"></a>

## 1. Purpose and precedence

This file is the single rulebook: what may live in aslice's orchards, how packages are born, maintained, deprecated, and buried, and what bars a pull request must clear to merge. Homebrew accumulated its equivalent rules across dozens of documentation pages, review folklore, and maintainer memory. aslice writes them down now, while the project is still young enough for one file to hold them.

**Precedence.** The specifications define *mechanism*: what fields exist, what the solver does, what CI can check. This file defines *policy*: what maintainers accept, require, and refuse. If the two appear to conflict, the conflict is a bug — file an issue against whichever document is wrong. Every schema field referenced here is landed: `[deprecation]` [PACKAGE-FORMAT §3.14](PACKAGE-FORMAT.md#deprecation--the-package-lifecycle-declared-v06), `[livecheck]` [PACKAGE-FORMAT §3.15](PACKAGE-FORMAT.md#livecheck--upstream-freshness-declared-v06), `link`/`link_reason` and `notes` [PACKAGE-FORMAT §3.8](PACKAGE-FORMAT.md#install--declarative-post-install-behavior), `ctx.replace` [PACKAGE-FORMAT §6.3](PACKAGE-FORMAT.md#buildstar--the-custom-api), `[system-patch]` [PACKAGE-FORMAT §3.16](PACKAGE-FORMAT.md#system-patch--flagged-replacement-of-apple-provided-files-v06) — all in PACKAGE-FORMAT v0.6, alongside `[system]` (v0.4 [PACKAGE-FORMAT §3.12](PACKAGE-FORMAT.md#system--kernel-extensions-and-sip-disabled-tools-v04), with the `[service]` table of [PACKAGE-FORMAT §3.8](PACKAGE-FORMAT.md#install--declarative-post-install-behavior)) and `[runtime]`/`[extension]`/`[ride]` (v0.5 [PACKAGE-FORMAT §3.13](PACKAGE-FORMAT.md#runtime-extension-ride--multi-version-runtimes-v05)).

**Charter — not amendable by this document.** Three founding decisions outrank any policy edit ([DESIGN §2.2](DESIGN.md#non-goals) N7, [DESIGN §9.4](DESIGN.md#what-gets-prebuilt), §1):

1. aslice collects no telemetry or analytics of any kind, ever — the project is infrastructure, not a product.
2. Download statistics are rejected as a value signal: obscure libraries downloaded once a month may have immense value because we supply deprecated operating systems.
3. Scope is macOS 10.11–12 on Intel. No Apple Silicon, no newer macOS, no Linux — no matter how convenient a given PR would find it.

**The one-sentence test for every rule below:** does this make aslice more worthy of the trust of people running machines nobody else serves? When a rule stops answering yes, amend it (§19); do not quietly ignore it.

---

<a id="orchard-tiers-and-the-acceptance-bar"></a>

## 2. Orchard tiers and the acceptance bar

Two project orchards, two acceptance bars. Third-party orchards set their own package acceptance policy under their own trust level ([REPOSITORIES §3](REPOSITORIES.md#trust-levels)). The environment, branching, and release-version contract in §18.1–§18.2 applies to aslice itself and **all orchards, including third-party orchards**; the remaining maintainer rules bind the project's orchards only.

| | **core** (~300 packages) | **extended** (~2,000 packages) |
|---|---|---|
| Purpose | The platform stratum: shells, toolchains, VCS, TLS, runtimes, editors, the libraries everything links against | Everything else worth having: applications, niche libraries, legacy tools |
| Upstream status | Actively maintained, or maintained-by-aslice with a named maintainer who owns it | May be upstream-EOL — must carry `[deprecation] reason = "upstream-eol"` (§8) |
| Tests | Working `tests.star` smoke test, passing in CI on at least one OS × flavor — **no test, no merge** | Strongly encouraged; required for libraries with dependents in core |
| `[livecheck]` | **Required** (§9) | Encouraged |
| Reproducibility | Working toward `reproducible: true` (§15); nondeterminism is a tracked defect | Best-effort |
| Vendor binaries | Only if `redistribute = true` **and** payload-only by construction — or graft-bearing with a farm-rehearsed, signed behavior manifest (§12) | Allowed with verifiable signature and honest OS/arch tags |
| System software (`[system]`) | Only when the platform genuinely requires it — none at launch (§13) | Allowed with a `[system]` declaration, named maintainer, signed kexts where offered, trust-gated serving (§13) |
| System patches (`[system-patch]`) | Only when the platform genuinely requires it — the frozen-TLS-CLI patch family is the founding case (§13) | Allowed with a `[system-patch]` declaration, named maintainer, per-target justification, demonstrated byte-exact restore, official/local serving, or verified serving under an explicit per-repo grant (§13) |
| Security posture | CVE flags are blocking work items for the named maintainer (§16) | CVE flags surface in `audit`; fixed best-effort |

**Hard rejections — both tiers, no exceptions, no override flags:**

- **Anything that patches or modifies macOS system files *outside the declared `[system-patch]` category*** ([DESIGN §13.1](DESIGN.md#package-acceptance-policy)). The default stands: aslice installs alongside the OS and never edits `/System`, `/usr`, or Apple's binaries — not silently, not incidentally, not as a side effect of anything else. The single exception is §13's system-patch category ([DESIGN §12.11](DESIGN.md#system-patches-flagged-reversible-replacement-of-apple-provided-files)): declared targets, the original backed up, replacement by profile symlink, rollback to the byte, consent at every decision point, official and local repositories only, refused paths blocked by construction. What survives is the guarantee in its defensible form: aslice never patches your system *behind your back*. (Kernel extensions and SIP-disabled development software are likewise **not** rejections — they are the restricted system-software category of §13: declared, warned, consent-gated, trust-gated.)
- **Anything whose installation requires executing *undeclared* vendor or maintainer scripts.** Binary installs execute zero package code by default; the sole exception is the declared, rehearsed, user-approved graft (§12; [DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)). A `.pkg`/`.dmg` whose function requires its `preinstall`/`postinstall` scripts belongs in the orchard only with those scripts declared as grafts, and an accepted package *discovered* to have undeclared ones is removed, not accommodated (§12).
- **Runtime dependencies on `/usr/lib` dylibs or `/usr/bin` tools** — the codified rejection of Homebrew's `uses_from_macos` (§6).
- **HEAD / unpinned builds in core.** Both reproducibility and the lock model rest on pins. Extended strongly discourages unpinned builds; third-party orchards answer to their own trust level.
- **Software that is itself hostile** — known malware, scareware, or packages whose primary function is deception. Obscurity is never a reason for exclusion (charter); hostility always is.
- **License-less content.** Every package carries an SPDX `license` (§12 for vendor terms).

**The acceptance review for a new core package** is answered in the PR body: who maintains it (a name, not "the community"), what its `[livecheck]` strategy is, why it belongs in core rather than extended, and what its test proves.

**Infrastructure packages.** Tooling the farm itself depends on is **core by definition**: the farm dogfoods the orchard, so everything in the quarantine and signing pipeline is a package we ship, never a private dependency. The founding case is `clamav` ([BUILD-INFRA §7.5](BUILD-INFRA.md#the-malware-signature-gate)), the signature scanner every staged slice passes before signing. It declares `min_os = "10.12"` — its real floor — and opts out of the v1 flavor with the reason named: its Rust toolchain, ≥1.74, cannot target 10.11. That is the honesty rule applied to ourselves. Users who want on-demand scanning install the very package the farm runs. Nothing about it is mandatory on a user's machine, and no client-side scan-on-install machinery exists to make it so.

---

<a id="naming-versioning-and-revisions"></a>

## 3. Naming, versioning, and revisions

- **Names** are lowercase ASCII letters, digits, and hyphens, starting with a letter; they match the upstream project's own name unless that name collides or is misleading. Aliases for historical renames live in the orchard's alias table, so `adopt --from-homebrew` and old locks keep resolving.
- **Versioned packages** (`openssl3`) exist when two majors are simultaneously maintained and depended upon; they default to `link = false` (§6). Creating one is a review decision, because each additional versioned lineage is a maintenance obligation, not a convenience.
- **`version`** is the upstream version string — no `v` prefix, no suffixes. **`revision`** is an integer starting at 0, reset on every version bump, and bumped when the recipe changes the produced bits without an upstream version change: a new patch, a dependency change, a default-variant or build-flag default change.
- **A revision bump that changes what a library exports is an ABI event** and passes through the ABI gate (§10) like any version bump. When in doubt, treat it as one.
- **`min_os` / `max_os`** are claims CI verifies (§4); `arch` tags on vendor artifacts follow §12.

---

<a id="os-and-flavor-declarations-the-honesty-rule"></a>

## 4. OS and flavor declarations: the honesty rule

The entire platform story rests on tags users can trust. Hence the rules:

- **`min_os` is the oldest release CI actually builds and smoke-runs on.** The merge gate builds at the formula's `min_os` and tests across `[min_os, 12]` on the farm VMs (§10), so claiming a floor you don't test is impossible by construction; claiming one you don't *build* at is a lint error.
- **Declare the real floor, skip the heroics** ([DESIGN §4.1](DESIGN.md#the-os-axis-collapses--at-1011)). A package that *could* be patched down to 10.11, but is not worth the effort, declares its real floor — 10.12, 10.14, whatever it is — and moves on. Users plan around accurate tags; they file angry issues around optimistic ones. Genuine patch heroics to lower a floor are still welcome: as patches (§7), with the floor lowered only when CI proves it.
- **Flavors** default to all three (v1/v2/v3). A formula may opt out of a flavor only when support is genuinely impossible — source that *requires* AVX intrinsics, upstream that dropped 32-bit-era CPU support — and the opt-out names the reason in review. "The tests are slow on v1" is not such a reason; skipping tests is a flavor-CI flag, not a flavor removal.
- **`max_os`** exists for real upper bounds: vendor artifacts containing 32-bit code (`max_os = "10.14"`, §12), APIs removed before Monterey. It is never a way to dodge a build failure. A package that fails on 12 gets fixed, or declares why, in the open.

---

<a id="variant-discipline"></a>

## 5. Variant discipline

Variants are aslice's answer to Homebrew's options disaster; the discipline below is what keeps the answer from becoming a second disaster ([DESIGN §13.2](DESIGN.md#variant-discipline)):

- **`abi = true` variants carry no cap.** Each must name the exported interface it changes — review checks the tag against the ABI scan, not the worthiness of the request. ffmpeg-class packages legitimately carry many codec combinations, uncommon ones included; which variants a user enables is the user's call, not the project's (owner decision, September 2026). Variants that may be compiled but not redistributed work like any other non-default variant: the client builds them locally from source, and the farm never prebuilds them (§11).
- **`abi = false` variants are unconstrained** — they never spawn binary flavors, so they cost the project nothing.
- **Defaults serve the overwhelming majority, securely.** The default variant set is what the farm prebuilds; it should be what 95% of installs want, and it turns secure options on — TLS on, deprecated protocols off — even when upstream defaults differ.
- **Naming:** short, lowercase, positive (`x265`, not `no-x264`). Negative variants exist only when the *default* is on and disabling is the exceptional need.
- **Conflicts fail fast.** Mutually exclusive variants error at configure time with a message naming both — never a broken build discovered at link time.
- **Popular non-default variants** may receive prebuilt slices when community requests show demand (§11) — the prebuild matrix grows by demonstrated need, not speculation.

---

<a id="dependencies-and-system-software"></a>

## 6. Dependencies and system software

- **Runtime dependencies resolve to aslice packages only.** Never `/usr/lib` dylibs, never `/usr/bin` tools, never "whatever the system ships." This is the codified rejection of Homebrew's `uses_from_macos` ([HOMEBREW-REVIEW §5](HOMEBREW-REVIEW.md#what-aslice-should-deliberately-not-copy)), and the rationale is foundational: on 10.11 the system libraries *are the problem*, and OpenSSL 0.9.8-era TLS is why the machines are stranded. Lint enforces the rule.
- **The only exceptions are system *frameworks***: `Accelerate`, `SystemConfiguration`, `CoreAudio`, `CoreFoundation`, and the other always-present dyld-shared-cache frameworks enumerated in the lint allowlist. Frameworks are the platform's ABI, not its bundled software — the Accelerate-shim BLAS provider depends on exactly this distinction. Additions to the allowlist are policy PRs against this file and the lint table together.
- **`link = false` — the principled keg-only** ([HOMEBREW-REVIEW §4.5](HOMEBREW-REVIEW.md#p1--the-keg-only-decision-shadowing-system-software)). A package installs into the store without linking into profiles when it would shadow macOS-provided tools, or when a versioned lineage demands it. The policy, concretely: in core, versioned packages (`openssl3` style) and anything shipping `bin/` names that collide with `/usr/bin` or `/bin` default to `link = false`, and `link_reason` is mandatory and lint-enforced. Dependents never need the profile link, because dependency resolution is store-path-based — "unlinked but depended upon" is a normal state, not a hack. Users opt in per profile with `aslice link <pkg>`.

---

<a id="patches"></a>

## 7. Patches

Patches are how a legacy platform stays alive, and also how orchards rot. The rules:

- **Every patch carries a header comment** naming its origin (an upstream commit/PR/issue URL, or the distro it was borrowed from), what it fixes, and the condition under which it can be removed — "drop when upstream ≥ 7.2", "drop if min_os rises to 10.13". Undocumented patches are a lint error.
- **Preference order:** an upstream backport first, then another maintainer's battle-tested patch (Debian, MacPorts, pkgsrc — credited), then local authorship. Write local patches to be upstreamable; upstreaming them is part of the work.
- **Patches fix builds, portability, and security — never features.** A patch that adds functionality is a fork; if upstream won't take it and the platform needs it, the conversation is "should this be a different package," not "apply it quietly."
- **Patch count is a health signal.** A formula accumulating double-digit patches triggers a review conversation: is this package maintainable here, should its `min_os` rise, is it time for `[deprecation]`? The goal is not zero patches — it is *accounted-for* patches.

---

<a id="deprecation-and-removal-lifecycle"></a>

## 8. Deprecation and removal lifecycle

Packages have a life cycle, and the orchard states where each one is in it ([HOMEBREW-REVIEW §4.3](HOMEBREW-REVIEW.md#p1--package-lifecycle-states)):

```toml
[deprecation]
date         = "2027-03-01"    # when deprecation starts
reason       = "upstream-eol"  # upstream-eol | security | renamed | unmaintainable | takedown | other
replacement  = "ffmpeg7"       # optional pointer
disable_date = "2027-09-01"    # optional: new installs refuse after this
```

- **active → deprecated:** installs and `info`/`audit` warn with the reason and replacement; existing installs unaffected; the package still receives slices.
- **deprecated → disabled** (at `disable_date`): new installs refuse without `--force-disabled`; existing installs keep working, remain in locks, and keep their generations.
- **disabled → tombstoned:** the formula leaves orchard HEAD, but the index keeps a **permanent tombstone** — name, final version, reason, replacement — so historical snapshots and old locks resolve forever. This is where aslice's snapshot model does genuinely *better* than git-tap archaeology. Never delete the record.
- **Renames** are deprecations with `reason = "renamed"` and a mandatory `replacement`, plus an alias-table entry.
- **Security fast path:** a package with an unfixable, actively dangerous vulnerability may skip straight to disabled by owner approval during single-owner launch, with the reason recorded. User safety outranks process.
- **EOL-in-extended is normal life**, not a failure: upstream-EOL packages live in extended with `reason = "upstream-eol"` indefinitely, as long as they still build and someone answers for them ([DESIGN §13.1](DESIGN.md#package-acceptance-policy)). Nobody else ships for these machines — hosting the honorable dead is part of the mission.
- **Abandonware stays hosted; only the real rights holder can take it down.** A disappeared vendor is not a complaint: software whose upstream or vendor is gone is served indefinitely (owner decision, September 2026). Removal for a rights claim requires a takedown request served to the project (the SECURITY.md contact) by the verifiable copyright owner, with proof of ownership or of authority to act; the project verifies the claimant before anything moves. Anonymous, third-party, or unverifiable complaints change nothing. On a verified complaint the package is disabled with `reason = "takedown"`, its hosted slices stop being served, and the tombstone records the takedown; if the proof later fails, the package is restored.
- **The lifecycle is edited by command.** `aslice orchard deprecate` / `disable` / `undeprecate` / `tombstone` / `rename` ([DESIGN §12.14](DESIGN.md#orchard-maintenance-the-maintainers-cli)) rewrite the `[deprecation]` table, validate it against [PACKAGE-FORMAT §3.14](PACKAGE-FORMAT.md#deprecation--the-package-lifecycle-declared-v06)'s rules, lint the formula, and open the PR. Hand-edited lifecycle tables have no excuse to drift from this section.

---

<a id="freshness-livecheck-and-autobump"></a>

## 9. Freshness: livecheck and autobump

The platform is frozen; upstreams are not. Freshness automation is *the* ongoing workload, and policy treats it as such ([HOMEBREW-REVIEW §4.2](HOMEBREW-REVIEW.md#p0--upstream-freshness-livecheck-and-autobump)):

- **Every core package carries `[livecheck]`**; extended packages should. A core package whose livecheck strategy rots — upstream moved forges, changed its tag scheme — is a bug filed against the named maintainer.
- **Defaults:** `skip_prerelease = true`, `throttle_days = 3`, `cooldown_days = 2`. The cooldown is the supply-chain poisoning window: time for a malicious upstream release to get caught before aslice ships it. For the historically risky ecosystems (npm, PyPI, RubyGems, crates) the cooldown may be raised; it is never lowered below 2.
- **Autobump** opens PRs mechanically: new `version`, bot-fetched `sha256`, `revision` reset, changelog link. Patch bumps get lightweight review. **Major bumps always get human review** — sonames, `min_os` floors, and variant surfaces all move on majors.
- **`aslice bump-pr <pkg> <version>`** is the human path, and it is held to the same gates.
- **The trust-store slices are ordinary packages.** `ca-certificates` and `apple-roots` ([DESIGN §12.10](DESIGN.md#trust-store-modern-ca-certificates-on-a-frozen-platform)) are pinned, data-only core packages under this section's rules: `[livecheck]` required, cooldown honored, hash-pinned fetch, the same six merge gates. Their upstreams are the Mozilla root program (via curl's caextract) and Apple's published PKI roots respectively. A missed upstream update here is the platform's day-one TLS failure returning — so their days-behind-upstream is a first-class dashboard number, not a footnote.
- **The metric is public:** median days-behind-upstream for core, on the farm dashboard (aslice.sh/dashboard). It is a workload gauge for maintainers, computed from orchard state — never from user machines (charter §1). `aslice orchard freshness` ([DESIGN §12.14](DESIGN.md#orchard-maintenance-the-maintainers-cli)) computes the same number locally — per package, worst first.
- **A dead upstream is not a dead package.** Every source the farm fetches is vendored into the repository ([DESIGN §9.6](DESIGN.md#the-repository-system)), so an upstream that vanishes or reshuffles its downloads breaks nothing already built. When a formula's canonical URL dies, the maintainer records the death in the formula — a comment naming the date and the mirror situation — and either livecheck adapts or the package moves toward §8.

---

<a id="merge-gates-what-ci-must-prove"></a>

## 10. Merge gates: what CI must prove

Every orchard change PR clears the same six gates ([HOMEBREW-REVIEW §4.7](HOMEBREW-REVIEW.md#p1--orchard-ci-merge-gates-specified)). Promotion PRs reuse the candidate's authenticated build evidence and verify unchanged content under §18.1–§18.2; they do not rebuild served artifacts. There is no maintainer override; the gates are what make review a question of policy rather than compilation:

1. **Lint** — schema, this policy (`link_reason`, patch headers, license, description rules), plus the `--new-package` ruleset for additions.
2. **Matrix build** — sandboxed build on **every declared flavor** at the formula's `min_os`, then smoke-run on **each OS release in `[min_os, 12]`** on the farm VMs. Tests may be flagged flavor/OS-irrelevant (pure data packages), with the flag visible in the PR.
3. **Smoke test** — `tests.star` passes on at least one OS × flavor for core; the test must exercise the installed artifact, not just `--version` where more is possible.
4. **ABI gate** — for any PR changing a library's version or revision, CI diffs the ABI scan between the old and the new slice. A `compatibility_version` or symbol-fingerprint regression must be resolved one of two ways: an explicit version/soname bump, or marking and scheduling **dependent rebuilds** — which the farm executes on merge and publishes *in the same index snapshot*, so clients never see the "everything's broken until rebuilds land" window.
5. **Graft rehearsal** — for a `type = "binary"` package declaring grafts ([PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software)), the farm rehearses each graft in a per-OS VM on every OS the artifact targets, diffs the observed writes, kext loads, daemon installs, and network access against the declared behavior manifest, and fails the PR on any deviation or under-declaration. Only a rehearsed, verified manifest is signed into the index ([DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)). A package without grafts skips this gate entirely.
6. **Post-merge signing** — slice and metadata signing happen automatically only after owner-approved merge and all required gates, on the dedicated networked release Pi; the publisher verifies the returned candidate before atomic publication ([KEY-RUNBOOK §2.1](runbooks/KEY-RUNBOOK.md#automatic-orchard-to-client-publication)). No PR, however trusted, touches keys.

The gates run locally as `aslice orchard ci [pkg…]` ([DESIGN §12.14](DESIGN.md#orchard-maintenance-the-maintainers-cli)) — the same harness the farm runs, with the cross-OS smoke tier and graft rehearsal honestly marked deferred — so a PR can arrive with the machines already convinced. Passing locally merges nothing; the farm re-runs all six.

Review *humans* decide: policy fit, variant justification, patch quality, tier placement. Review *machines* decide: builds, tests, ABI. Neither does the other's job.

---

<a id="prebuild-policy-what-gets-slices"></a>

## 11. Prebuild policy: what gets slices

- **Core:** every flavor compatible with the formula's `min_os`, default variants, rebuilt promptly on merge.
- **Extended:** every compatible flavor, default variants, on a rolling cadence as farm capacity allows.
- **Popular non-default variants:** prebuilt when community requests demonstrate demand; each addition is a farm-capacity decision recorded in the PR.
- **Vendor binaries:** hosted slices only when `redistribute = true`; otherwise the formula is a pointer and the client fetches the vendor artifact itself (§12).
- **Prioritization when capacity forces choices** follows the four signals of [DESIGN §9.4](DESIGN.md#what-gets-prebuilt), in order: **dependency centrality** (what the build graph unblocks), **build pain** (the farm-measured hours and failure rate a slice saves), **irreplaceability** (nobody else ships this for these machines), **direct community requests** (orchard issues, in the open). Download counts are explicitly *not* a signal: on a deprecated-OS platform the rarest library may be the most valuable one (charter §1).

---

<a id="vendor-binary-packages-pkgdmg"></a>

## 12. Vendor binary packages (pkg/dmg)

Some software exists only as an installer. The policy for it ([DESIGN §12.4](DESIGN.md#vendor-binaries-pkgdmg-and-gui-apps) and [DESIGN §13.1](DESIGN.md#package-acceptance-policy)):

- **Payload-only by default; grafts are the declared exception.** `preinstall`/`postinstall` scripts never execute and `.dmg` autolaunch mechanics never run — unless the formula declares the script as a graft ([PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software); mechanism in [DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)): hash-pinned, described by an exhaustive behavior manifest, approved by the user before it runs, sandboxed to exactly that manifest, and captured so rollback and uninstall reverse its footprint. A package whose function requires *undeclared* scripts is still out of scope, and an accepted package discovered to have them is **removed, not accommodated** — the graft is the accommodation, and it happens in the open.
- **Grafts meet the rehearsal bar.** A graft's behavior manifest is authored from evidence — the script read line by line, its writes observed under instrumentation — and reviewed like code. The farm rehearses every graft on each OS its artifact targets and signs the verified manifest into the index (§10 gate 5; [DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)); core and extended ship no unsigned manifest. Under-declaration discovered at rehearsal or in the field is a policy violation: the package is fixed or removed, never waved through. Third-party orchards may carry graft-bearing packages only with unsigned manifests, and the client shows the unsigned warning at every install decision ([REPOSITORIES §3](REPOSITORIES.md#trust-levels)) — that risk is the user's, stated loudly.
- **Signer pinning is mandatory for signed artifacts.** The formula records the expected signing identity (`Developer ID Application: Vendor (TEAMID)`) and the notarization expectation; a silent signer change upstream is a hard failure. Non-notarized-but-signed software may ship, flagged as such. Unsigned software ships in the **extended orchard only** — `signer` omitted, announced at every install ([PACKAGE-FORMAT §3.11](PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software)) — and never in core (owner decision, September 2026).
- **Honest tags, verified.** `min_os`/`max_os`/`arch` are checked at pack time against the bundle's `LSMinimumSystemVersion` and, where present, the pkg Distribution requirements; a mismatch is a lint error.
- **32-bit and universal payloads** are first-class on the releases that execute them (10.11–10.14). Required i386-only execution forces `max_os = "10.14"` or lower; an unused i386 member alongside a usable x86_64 member does not ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)). Universal payloads install **whole**: `lipo`-thinning would invalidate the vendor signature, and signature integrity outranks disk savings.
- **Licensing is documented.** The SPDX `license` field and the redistribution terms a vendor publishes are recorded in the formula, so the user can see them; `redistribute = false` yields a pointer formula. A vendor pulling or mutating an artifact produces a hash failure by design, never a silent install of different bits.
- **Every payload is signature-scanned at repack.** The farm's quarantine gate ([BUILD-INFRA §7.5](BUILD-INFRA.md#the-malware-signature-gate)) scans vendor payloads against current malware definitions before packing. A detection either rejects the package or produces a maintainer-documented exclusion recorded in the formula — never a silently "cleaned" payload, which would break byte-integrity against the pinned signer. Bundled adware and PUPs are the documented pathology of this ecosystem; the scanner is the tripwire, and human review is the decision.
- **Core tier:** vendor binaries enter core only if hosted by the farm (`redistribute = true`) **and** payload-only — or, when graft-bearing, rehearsed on the farm with a signed behavior manifest ([DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)) — core must never depend on a vendor's server being up.

---

<a id="system-software-packages-kexts-sip-disabled-tools-and-system-patches"></a>

## 13. System software packages (kexts, SIP-disabled tools, and system patches)

[DESIGN §12.7](DESIGN.md#system-software-kexts-and-sip-disabled-development-tools) is the mechanism; this section is what maintainers may accept.

- **The category exists because reality does.** Audio-interface drivers, filesystem kexts, hypervisors, debuggers and DTrace tooling on 10.11–12 development machines: users install these today, by hand, with no warnings, no provenance, and no rollback. The choice was between pretending they don't exist and bringing their installation under the rules — declared requirements, verified payloads, per-operation elevation, mandatory warnings, and rollback that actually removes the kext.
- **Acceptance requirements:** a named maintainer; a `[system]` declaration with a mandatory human-readable `reason` — it *is* the warning text, so write it like one; **signed kexts wherever the vendor or upstream offers them** (kext signing is enforced on SIP-enabled 10.11+); `sip_off_required = true` only when the software genuinely cannot function otherwise, with the formula documenting *why*; and a manual validation note in the PR. Kernel software can't be smoke-tested in CI the normal way — say what machine and OS release it was loaded on.
- **Tier placement:** extended by default. Core accepts a system package only when the platform story genuinely requires it — the bar is "the orchard is worse without it" — and at launch, no package meets it.
- **Trust gating is policy.** Only official and verified repositories may serve system packages (the `system` capability, [REPOSITORIES §3](REPOSITORIES.md#trust-levels)). **Third-party repositories cannot**: talking a user into a kernel extension is precisely the social-engineering attack the trust levels exist to block. Local `file://` development trees may serve them, on the maintainer's own machine, with the same warnings.
- **The warnings are not decoration.** A PR that weakens, shortens, or routinizes the [DESIGN §12.7](DESIGN.md#system-software-kexts-and-sip-disabled-development-tools) warning flow is rejected on sight. The day users click through kext warnings without reading them is the day this category becomes the project's worst decision — so review the warning text in every system-package PR as carefully as the payload.
- **Vendor-binary kexts** combine §12 and this section: payload-only extraction (vendor scripts still never execute unless declared, rehearsed grafts — [DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)), signer pinning, and `[system]` installation of the extracted kext by `aslice-system`.
- **Uninstall and rollback must be demonstrated in review:** the kext unloads and is removed, `kextcache` refreshes, and rolling back a generation restores the previous state. A system package that cannot cleanly leave is not accepted.
- **Root-domain services meet the same bar.** A `[service]` with `domain = "system"` ([DESIGN §12.8](DESIGN.md#services-launchd-native-lifecycle-and-safe-upgrades)) runs code as root, so its acceptance follows this section: a named maintainer, justification for why a user agent is insufficient, manual validation on a real machine, and demonstrated start–stop–uninstall via `aslice service`. User-domain agents need no special review beyond the tier bar; they are unprivileged processes the user can stop, and the orchard prefers them. A PR that declares `domain = "system"` where a user agent would do is sent back with "run it as the user."

**System patches (`[system-patch]`) — the stricter sibling (DESIGN v1.7 [DESIGN §12.11](DESIGN.md#system-patches-flagged-reversible-replacement-of-apple-provided-files)).** A `[system-patch]` package replaces an Apple-provided file — the frozen 0.9.8-era `/usr/bin/openssl` is the founding case — through backup, profile symlink, and byte-exact restore. Nothing else in this file steps further outside the sandbox story, and the acceptance bar says so:

- **The category exists because the alternative is worse.** Users patch these files today by hand — `curl | sudo sh`, a downloaded "TLS fixer" — with no provenance, no backup, and no way back. The declared mechanism gives them the fix with the receipt.
- **Acceptance requirements:** a named maintainer; a `[system-patch]` declaration with a mandatory `reason` written as warning text; **every target path individually justified in the PR** — why this file, and why no store-side alternative (`link = false`, a shim, a differently-named tool) can do the job; `sip_off_required` set only when genuinely required, with the reason documented; and **byte-exact restore demonstrated in review**: install, then restore, on a real machine, with the restored file's hash matching the pre-install original. A patch package that cannot cleanly give the machine its byte back is not accepted.
- **Targets are tools, configs, and data — never the shared library space.** The refused-by-construction list (kernel, `dyld`, `libSystem`, anything under `/System`, any dylib or framework in a platform binary's load path) is lint-enforced and not negotiable in review; a PR arguing for an exception is rejected without discussion. The list exists because failures there brick machines, or crash Apple's own binaries against library validation.
- **Tier placement:** extended by default; core only when the platform story genuinely requires it. The founding core case is the frozen-TLS-CLI family (`/usr/bin/openssl` and kin, [DESIGN §12.10](DESIGN.md#trust-store-modern-ca-certificates-on-a-frozen-platform)) — the fix the platform was built to deliver. Every additional core patch argues the same bar: "the orchard is worse without it."
- **Trust gating is policy, and it is the strictest in the system.** Only **official and local** repositories serve `[system-patch]` packages by default. A **verified** repository may serve them only after the machine's owner grants it explicitly — `aslice repo allow-system-patch <name>`, refused by default, revocable (the `system-patch` capability, [REPOSITORIES §3](REPOSITORIES.md#trust-levels)). **Third-party: never.** A verified community repository is vetted to distribute software; rewriting the OS warrants one more decision from the machine's owner beyond that vetting (DESIGN open question #10, resolved in DESIGN v1.8).
- **Drift is the maintainer's problem, planned in advance.** macOS updates can restore the Apple original, or ship a newer file under our symlink. The formula's review records the expectation: `doctor.systempatch` reports both cases and never silently re-patches, and the PR states the maintainer's commitment to re-validate the patch after each Apple update on the oldest supported release. A patch package whose maintainer disappears follows §17's orphan rule with the flag raised to 30 days, not 90 — an unmaintained system patch is a liability with a symlink.
- **The warnings are not decoration** — the [DESIGN §12.7](DESIGN.md#system-software-kexts-and-sip-disabled-development-tools) rule applies verbatim: a PR that weakens, shortens, or routinizes the [DESIGN §12.11](DESIGN.md#system-patches-flagged-reversible-replacement-of-apple-provided-files) consent flow (pre-download target list, per-decision `--accept-system-changes`, no "always allow") is rejected on sight.

---

<a id="package-documentation-standards"></a>

## 14. Package documentation standards

- **`description`:** one line, no leading article, no repeating the package name, no marketing ("blazing fast"), ends with a period. It is what `search` shows — write it for someone who has never heard of the software.
- **`license`** is SPDX, `homepage` must be reachable at review time, `keywords` power search.
- **`notes`** (the caveats field): post-install guidance a user genuinely needs — "config lives in …", "run `aslice service start postgresql` to …" — printed at install and shown in `info`. If it is not actionable, it is not a note.
- **`tests.star`:** the smoke test proves the installed artifact works — link a binary against the library, run the tool on real input. `--version` alone is a last resort, and using it says so in a comment.

---

<a id="reproducibility-and-the-build-environment"></a>

## 15. Reproducibility and the build environment

- Builds run in the normalized environment (fixed `LC_ALL`, `TZ`, `SOURCE_DATE_EPOCH`, prefix-mapping; BUILD-INFRA.md) on farm and laptop alike.
- **Core works toward `reproducible: true`**: bit-identical rebuilds on a second, independent builder (Phase 3 cross-checks). Nondeterminism discovered in a core package is a tracked defect with an owner, not a shrug.
- **Never hide nondeterminism** by freezing outputs or skipping the check. The badge means something because losing it is visible.

---

<a id="security-response"></a>

## 16. Security response

- **CVE flow:** the OSV/advisory feed flags an installed-version overlap; `audit` surfaces it to users immediately (the authenticated SBOM is associated with the artifact); the named maintainer patches, backports (§7), or bumps. Security PRs jump the review queue, but they never skip the merge gates.
- **Embargoed fixes** land via a private orchard branch and publish with a coordinated snapshot at embargo lift. The freeze is a TUF-metadata event, not a secret.
- **Unfixable and dangerous** → the §8 security fast path.
- **Owner merge authorizes release processing, not direct key access.** The dedicated signer verifies the authorized commit, artifact digests, required gate receipts, versions, and expected state before signing automatically ([KEY-RUNBOOK §2.1](runbooks/KEY-RUNBOOK.md#automatic-orchard-to-client-publication)). Other maintainer accounts can propose changes but cannot authorize launch releases. Compromise of the owner’s merge authority can authorize malicious changes that pass automated gates; compromise of the online signer can authorize malicious releases outright.

---

<a id="governance-and-review-process"></a>

## 17. Governance and review process

- **Single-owner launch:** the project owner approves decisions and merges. Silence is not release authorization. Maintainer votes and mandatory second-reviewer requirements are superseded for this phase; agree a new review policy when independent maintainers participate ([DESIGN §13.4](DESIGN.md#governance)).
- **Owner approval covers every tier:** patch and major bumps, new extended and core packages, versioned lineages, `abi = true` variant additions, system-software and system-patch packages, and policy changes. The owner may author and approve a change. All required automated gates remain mandatory; missing build/test or independent-rebuild capacity leaves the affected release pending. No further per-release approval is required after merge.
- **Every package in core has a named maintainer.** Orphaned core packages get 90 days flagged on the dashboard, then move to extended or to deprecation. The tier promise (§2) is only real if someone keeps it.
- **Maintainers are expected to** keep their livechecks green, answer CVE flags, and work the review queue. Stepping back is honorable; disappearing is a signal to reassign.

---

<a id="release-cadence"></a>

## 18. Release cadence

- **The index publishes automatically within the authorized environment:** eligible owner-approved merges proceed through CI, quarantine, authenticated signing, and serialized atomic activation ([KEY-RUNBOOK §2.1](runbooks/KEY-RUNBOOK.md#automatic-orchard-to-client-publication)). A merge to `develop` authorizes dev publication only; staging and prod require their own authorized promotion merges. Failures leave the previous repository available; retries are idempotent and stale candidates reconcile before signing again. Targets/snapshot renew automatically below 30 days using the last approved content in that environment; daily timestamps maintain freshness without promoting pending changes. Clients discover releases at normal metadata refresh and can search, install, or upgrade; publication forces no installation.
- **Environments:** `dev`, `staging`, and `prod` follow §18.1. This replaces the proposed `edge`/`stable` channel split. Production is the default; development and staging are explicit selections, never automatic fallback sources.
- **Snapshot retention:** all published snapshots and their referenced hosted artifacts, recipes, and source objects indefinitely, with historical downloads authorized by the current archive catalog ([STATE-AND-RECOVERY §8](STATE-AND-RECOVERY.md#plans-locks-archives-and-offline-use)). Historical installs (`--index-snapshot`) are a feature, and retention is what makes the promise real.
- **Dependent rebuilds ride the triggering snapshot** (§10 gate 4) — no separate "rebuild wave" days.
- **aslice itself** releases through the same machinery, as package zero (self-update, [HOMEBREW-REVIEW §4.1](HOMEBREW-REVIEW.md#p0--self-distribution-self-update-and-bootstrap-trust)). Client releases join the same signed batches and are generation-swapped like everything else.

<a id="environments-branching-and-promoted-builds"></a>

### 18.1. Environments, branching, and promoted builds

This contract applies to aslice development, the core and extended orchards, and every third-party orchard. Third-party maintainers use their own release authorities and infrastructure under their existing repository trust level; following this workflow grants no additional trust or capabilities.

| Environment | Required branch | Purpose |
|---|---|---|
| `dev` | `develop` | Integrate changes and build release candidates. |
| `staging` | `beta` | Validate the exact candidate intended for production. |
| `prod` | `master` | Serve the candidate that passed staging. |

**One repository identity per project or orchard.** All three branches live in the same Git repository and its mirrors. Environment selection may change the branch pointer only; it must not select a separate repository, fork, or environment-specific mirror URL. Different orchards naturally have different repository identities. Mirrors replicate the same repository, branch names, pinned commits, and immutable objects; selecting a transport mirror does not change the environment. Feature and review branches may exist, but published environments use exactly the names above.

**Build once, promote twice.** Changes enter `develop`. Freeze a candidate at an exact commit, resolve all inputs to immutable identities, and build the complete artifact set there. Record its source tree, recipes, patches, dependency locks, toolchain and build configuration, artifact inventory (paths, lengths, and SHA-256 digests), and authenticated gate receipts. Include required provider/dependent builds in that set. Finalize any byte-changing signing or packaging before freezing the inventory. Keep the candidate and evidence available by immutable identity even after `develop` advances.

Promote that specific candidate from `develop` to `beta`, then from `beta` to `master`. Promotion moves branch/release pointers and publishes the existing immutable objects; it never compiles, repacks, substitutes dependency builds, or edits embedded versions. A merge commit may differ, but its release content must match the frozen source tree exactly; resolving a merge conflict by changing content creates a new candidate under §18.2. Do not promote a moving branch tip or skip staging. Validation may rerun tests, scans, or required independent reproducibility checks against the same inventory; evidence rebuilds never replace the served artifacts.

**No environment-specific hardcoded values.** Source, recipes, build flags, embedded configuration, and artifacts must not contain separate dev/staging/prod endpoints, credentials, repository identities, paths, or behavior switches. Supply operational configuration and secrets externally at deployment or runtime without rewriting the artifacts. Repository references retain one identity and vary only the environment branch. Resolve branch references to commits when freezing a candidate: a moving dependency branch cannot silently change the candidate's content during promotion. Test externally supplied configuration in the destination environment and retain the result with the promotion record.

**Promotion is a checked release operation.** Before activation, verify the repository identity, required source/destination branches, authorized promotion commit, base version, source/input identity, complete artifact inventory, and required gate receipts. Staging validates the selected dev candidate; prod requires the successful staging record for that same candidate. Missing objects or evidence, changed content, an incorrect branch, or a different repository blocks promotion and leaves the destination's previous release active. Retrying an unchanged candidate after a transient outage is allowed; bypassing a failed gate is not.

Keep publication state, caches, locks, metadata version counters, and signing authorization scoped to the repository and environment. Renewing dev metadata cannot publish into prod, and selecting dev cannot overwrite prod's rollback-protection state. Publish each environment atomically through the existing signing flow. TUF metadata and detached promotion attestations may receive new signatures, versions, and expiries; they must reference the same frozen artifact bytes and content digests. This metadata activity is not an artifact rebuild.

<a id="release-versioning-and-unchanged-content-enforcement"></a>

### 18.2. Release versioning and unchanged-content enforcement

The aslice release and each orchard release have a base version `x.y.z` and exactly these environment labels:

| Environment | Release version | Example |
|---|---|---|
| `dev` | `x.y.z-develop` | `1.0.0-develop` |
| `staging` | `x.y.z-beta` | `1.0.0-beta` |
| `prod` | `x.y.z` | `1.0.0` |

**`1.0.0-develop` → `1.0.0-beta` → `1.0.0` contains no release-content changes.** The suffix is a release label in external publication metadata, not a value patched into a binary, archive, formula, or embedded manifest. Embedded version information uses the unchanged base version and immutable build identity. Only the environment label, branch/promotion pointers, and publication bookkeeping described in §18.1 may change. This release numbering is separate from upstream package `version`/`revision` (§3) and TUF's monotonic metadata counters; promoting an orchard does not rewrite its packages' upstream versions.

Once a base version has a frozen candidate, it identifies exactly one source/input set and artifact inventory. Any change to source, recipes, patches, dependencies, toolchain, build configuration, or artifact bytes requires a **new base version**, even if the fix is made during staging or produces apparently equivalent behavior. Increment patch for a compatible fix, minor for compatible added functionality, or major for an incompatible change. A package revision bump alone does not permit reuse of the orchard release version. Do not overwrite a published label, add an ad hoc suffix, or use build metadata to conceal changed content under the same base version.

For example, if testing `1.0.0-beta` reveals a defect, record the failed candidate, make the correction on `develop`, and build `1.0.1-develop` (or an appropriate larger bump). It must pass through `1.0.1-beta` before `1.0.1`. Neither the correction nor a production hotfix may be inserted into the old promotion chain. A test infrastructure outage or missing receipt requires a documented retry of the same content, not a version bump; any content change made to resolve a failure does require the bump.

**Every refusal explains why.** Retain a failure record with the candidate/base version, repository and source/destination branches, expected and observed commit/tree/input identities and artifact digests where relevant, the failed check and evidence, and the required remedy. Publish the reason in the release/CI report, redacting secrets. For a changed candidate, name the changed files or inputs and the replacement version; link the replacement's release notes to the failure. For example: “Promotion of `1.0.0-beta` to `1.0.0` refused: dependency lock changed after candidate freeze; build and validate `1.0.1-develop`.” A bare “promotion failed” is insufficient.

**Implementation acceptance:** the shared workflow must demonstrate an unchanged dev → staging → prod promotion with identical artifact hashes and no promotion build jobs; rejection of altered inputs or bytes under the same base version; rejection of wrong branches, cross-repository pointers, missing evidence, and prod promotion without staging; and successful retry after a transient failure without mutating the candidate. Run these checks for aslice and a third-party orchard as well as the official orchards. This repository is currently a design specification; executable promotion automation and its metadata representation remain implementation work.

---

<a id="amending-this-policy"></a>

## 19. Amending this policy

- Amendments are PRs against this file, decided like any other policy change (§17). Every amendment states its rationale in the PR and, when merged, in this section's running history. The file is the project's institutional memory.
- **Charter items (§1) are not amendable here.** No telemetry, no download-count metrics, the 10.11–12 Intel scope: those are founding commitments, and a package manager that revisits its founding commitments by committee stops being trusted by the people it was founded for.
- **When a rule is consistently broken in practice,** amend the rule or enforce it — but never let the file and the orchard drift apart. A policy document nobody follows is worse than none, because it teaches contributors that written words are decorative here.

---

## History

Historical labels and ordering below are preserved as recorded, including repeated version labels. They do not override the current specification.

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v1.15 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v1.13 | September 2026 | one dev/staging/prod workflow for aslice and all orchards, including third-party: `develop`/`beta`/`master` in the same repository, immutable promoted builds, external environment configuration, and `x.y.z-develop` → `x.y.z-beta` → `x.y.z` release labels. Content changes require a base-version bump and a recorded failure reason. Supersedes the proposed edge/stable split; automation remains implementation work. |
| v1.12 | September 2026 | owner merge becomes the final human release approval, with automatic signing on a dedicated networked Pi and serialized atomic publication. Automatic targets/snapshot renewal replaces manual renewal; the root remains offline. The manual-release design above is superseded. Services and acceptance drills remain implementation work (KEY-RUNBOOK §2.1, §7); schemas and client signature formats are unchanged. |
| v1.11 | September 2026 | **Superseded design record:** initial signing uses a single owner, separate offline root and release Pis, encrypted backups, and manual release batches. The Mac Pro VM prepares and publishes; multi-party custody and hardware tokens are deferred. KEY-RUNBOOK defines renewal, rotation, recovery, and pre-launch drills; prior custody requirements are superseded. |
| v1.10 | Not recorded | TOOLCHAIN.md v0.1 joins the companions; companion versions refreshed — DESIGN v1.21, PACKAGE-FORMAT v0.16, BUILD-INFRA v0.15; no policy changes |
| v1.10 | September 2026 | TOOLCHAIN.md v0.1 joins the companions; companion versions refreshed — DESIGN v1.21, PACKAGE-FORMAT v0.16, BUILD-INFRA v0.15; no policy changes. |
| v1.9 | Not recorded | prose review pass — the register was already clean, no prose changes; companion versions refreshed — DESIGN v1.20, BUILD-INFRA v0.14, REPOSITORIES v1.7; no policy changes. |
| v1.9 | September 2026 | prose review pass: the register survived unchanged (gems kept deliberately: 'hosting the honorable dead is part of the mission', 'User safety outranks process', 'an unmaintained system patch is a liability with a symlink', 'written words are decorative here'); companion versions refreshed — DESIGN v1.20, BUILD-INFRA v0.14, REPOSITORIES v1.7; no policy changes. |
| v1.8 | Not recorded | review correction — the §14 `notes` example's `aslice services start` becomes `aslice service start` (the command is singular, DESIGN §12.1); companion versions refreshed — BUILD-INFRA v0.13, REPOSITORIES v1.6, HOMEBREW-REVIEW v0.21. |
| v1.8 | September 2026 | the §14 `notes` example's command typo corrected (`aslice service`, singular); companions refreshed to BUILD-INFRA v0.13, REPOSITORIES v1.6, HOMEBREW-REVIEW v0.21. |
| v1.7 | Not recorded | grafts land (mechanism DESIGN v1.19 §12.15; schema PACKAGE-FORMAT v0.15 §3.11) — §12's payload-only rule becomes the default with the declared-graft exception and the rehearsal bar, §10's merge gates become six (farm graft rehearsal), §13's vendor-kext bullet crosses over, and §2's core-acceptance row follows; owner decision, September 2026. |
| v1.7 | September 2026 | grafts, by owner decision: vendor installer scripts become a declared, rehearsed, signed, user-approved exception to the payload-only default. §2's hard rejection now targets *undeclared* scripts; §12 gains the graft exception and the rehearsal bar (manifests authored from evidence, farm-rehearsed per OS, signed into the index — core and extended ship no unsigned manifest); §10's merge gates become six, gate 5 rehearsing grafts in per-OS VMs; §13's vendor-kext bullet crosses over; third-party orchards carry grafts only unsigned, under the client's loud warning (mechanism DESIGN v1.19 §12.15; schema PACKAGE-FORMAT v0.15 §3.11). |
| v1.6 | Not recorded | §9 names the farm dashboard's public home — aslice.sh/dashboard; the project domain carries the human pages as paths on the apex and the machine endpoints as subdomains, per the owner's layout decision (September 2026); no policy changes. |
| v1.1–v1.6 | September 2026 | prose rewrite in the project's voice; NOMENCLATURE vocabulary header; the maintainer's `aslice orchard` CLI for lifecycle edits, freshness, and local gate runs (§8, §9, §10); the variant-cap retirement, license-gate removal, and the abandonware stance with the `takedown` reason (§5, §8); the farm dashboard's public home at aslice.sh/dashboard (§9). The status header carries the full per-version record. |
| v1.5 | Not recorded | the `abi = true` variant cap is retired — variants are governed by need and honest ABI tags, not quota, and compile-only licenses are served as non-default local builds (§5); the license-policing gates drop out of §2 and §12, leaving documentation duties; §8 states the abandonware stance — hosted indefinitely, removable only by a verified complaint from the real copyright owner, with `takedown` as a new lifecycle reason; companion versions refreshed (DESIGN v1.17, PACKAGE-FORMAT v0.13, BUILD-INFRA v0.12, REPOSITORIES v1.5, HOMEBREW-REVIEW v0.19). |
| v1.4 | Not recorded | the maintainer's CLI lands (DESIGN v1.16 §12.14) — §8's lifecycle gains the `aslice orchard` deprecate/disable/undeprecate/tombstone/rename verbs, §9's public freshness metric gains its local computation (`aslice orchard freshness`), and §10's five gates gain their local run (`aslice orchard ci`); companion versions refreshed (DESIGN v1.16, PACKAGE-FORMAT v0.12, BUILD-INFRA v0.11, REPOSITORIES v1.4, HOMEBREW-REVIEW v0.18); no policy changes. |
| v1.3 | Not recorded | NOMENCLATURE.md vocabulary reference added to the header; companion versions refreshed (DESIGN v1.15, PACKAGE-FORMAT v0.12, BUILD-INFRA v0.10, REPOSITORIES v1.3, HOMEBREW-REVIEW v0.17); no policy changes. |
| v1.2 | Not recorded | review pass — §13's warning-rule references name DESIGN §12.7/§12.11 explicitly; companion versions refreshed; no policy changes. |
| v1.1 | Not recorded | prose rewrite throughout — chapters reworded in the project's technical-writing voice; no policy changes. |
| v1.0 | Not recorded | editorial pass — prose revised for directness; no policy changes. |
| v1.0 | September 2026 | editorial pass: prose revised for directness throughout; no policy changes. |
| v0.9 | Not recorded | owner decision — unsigned vendor artifacts may ship in the **extended orchard only**, `signer` omitted, announced loudly at every install; §12 now matches PACKAGE-FORMAT §3.11, core stays signed-only (DESIGN v1.10 §12.4). |
| v0.8 | Not recorded | dead-upstream policy — every fetched source is vendored in the repository's `blobs/sha256/` (DESIGN v1.9 §9.6), so a vanished upstream breaks nothing already built; §9 gains the dead-URL bookkeeping rule; companions refreshed. |
| v0.8 | September 2026 | dead-upstream policy: the repository vendors every fetched source artifact (DESIGN v1.9 §9.6, BUILD-INFRA v0.6), mirrors replicate the whole tree sources-included (REPOSITORIES v0.8), and §9 gains the rule for noting dead canonical URLs in formulas — the archive carries the past, policy tracks the future. |
| v0.7 | Not recorded | the farm's malware-signature gate lands (BUILD-INFRA v0.4 §7.5) — `clamav` joins core as an infrastructure package with an honest 10.12 floor and a v1 flavor opt-out (§2), and every vendor payload is signature-scanned at repack (§12); client-side scanning stays the user's decision. |
| v0.7 | September 2026 | the malware-signature gate, following BUILD-INFRA v0.4 §7.5: the farm scans every staged slice against current definitions before signing-host promotion; the scanner ships as the `clamav` core package under the new infrastructure-package rule (§2) — farm tooling is core by definition, with an honest 10.12 floor and v1 opt-out; §12 requires a scan of every vendor payload at repack, with detections rejecting the package or producing a documented exclusion, never silent cleaning. Client-side scanning remains a user decision: install the package or don't. |
| v0.6 | Not recorded | DESIGN open question #10 resolved (DESIGN v1.8) — a verified repository may serve `[system-patch]` under an explicit per-repo `allow-system-patch` grant; §13's trust-gating paragraph updated; third-party still never. |
| v0.6 | September 2026 | DESIGN open question #10 resolved (DESIGN v1.8): a verified repository may serve `[system-patch]` packages under an explicit per-repo `allow-system-patch` grant (refused by default, recorded, revocable); §13's trust-gating paragraph updated; third-party repositories remain never. |
| v0.5 | Not recorded | the pending schema references of §1 land in PACKAGE-FORMAT v0.6 (`[deprecation]`, `[livecheck]`, `link`/`link_reason`, `notes`, `ctx.replace`, `[system-patch]`) and the `system-patch` capability lands in REPOSITORIES v0.6 §3 — no policy change, bookkeeping that the specifications caught up. |
| v0.5 | September 2026 | bookkeeping: §1's pending schema references land in PACKAGE-FORMAT v0.6 and the `system-patch` capability lands in REPOSITORIES v0.6 §3; no policy content changed. |
| v0.4 | Not recorded | the system-file hard rejection becomes the declared `[system-patch]` category — §2, §13; mechanism in DESIGN v1.7 §12.11 — and the trust-store slices (`ca-certificates`, `apple-roots`) are recorded as ordinary pinned data-only core packages — §9; mechanism in DESIGN v1.7 §12.10. |
| v0.4 | September 2026 | the system-file hard rejection becomes the declared `[system-patch]` category, following DESIGN v1.7 §12.11 and the project owner's charter amendment: original backed up, profile-symlink replacement, byte-exact restore demonstrated in review, official/local-only serving, refused paths by construction; v0.2's "rejected forever" line is amended to the honest form — never *behind your back*. Also records DESIGN v1.7 §12.10's trust-store extensions: `ca-certificates` and `apple-roots` are ordinary pinned data-only core slices under §9's freshness rules and §10's gates. |
| v0.3 | Not recorded | service-package acceptance — root-domain daemons meet §13's bar, user agents meet the normal tier bar — §13; mechanism in DESIGN v1.3 §12.8. |
| v0.3 | September 2026 | service-package acceptance, following DESIGN v1.3 §12.8: root-domain daemons (`domain = "system"`) meet §13's bar; user agents meet the normal tier bar and are preferred. |
| v0.2 | Not recorded | kernel extensions and SIP-disabled development software move from hard rejection to the restricted, warned, trust-gated system-software category — §2, new §13; mechanism in DESIGN v1.2 §12.7. |
| v0.2 | September 2026 | the SIP/kext hard rejection becomes the restricted system-software category (§2, new §13), following DESIGN v1.2: declared requirements, per-operation elevation, mandatory warnings, trust-gated serving, demonstrated rollback; patching system files stays rejected forever. |
| v0.1 | September 2026 | initial rulebook, commissioned by HOMEBREW-REVIEW.md §8: consolidates the acceptance bar (DESIGN §13.1), variant discipline (§13.2), the deprecation lifecycle, patch documentation, merge gates, and release cadence proposed across the review into one maintainer-facing document. |
| Not recorded | September 2026 | corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending. |
| v1.16 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |

</details>
