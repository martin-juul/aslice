# aslice Orchard Policy — The Maintainer Rulebook

- **Status:** Policy v0.9 — September 2026 (v0.2: kernel extensions and SIP-disabled development software move from hard rejection to the restricted, warned, trust-gated system-software category — §2, new §13; mechanism in DESIGN v1.2 §12.7. v0.3: service-package acceptance — root-domain daemons meet §13's bar, user agents meet the normal tier bar — §13; mechanism in DESIGN v1.3 §12.8. v0.4: the system-file hard rejection becomes the declared `[system-patch]` category — §2, §13; mechanism in DESIGN v1.7 §12.11 — and the trust-store slices (`ca-certificates`, `apple-roots`) are recorded as ordinary pinned data-only core packages — §9; mechanism in DESIGN v1.7 §12.10. v0.5: the pending schema references of §1 land in PACKAGE-FORMAT v0.6 (`[deprecation]`, `[livecheck]`, `link`/`link_reason`, `notes`, `ctx.replace`, `[system-patch]`) and the `system-patch` capability lands in REPOSITORIES v0.6 §3 — no policy change, bookkeeping that the specifications caught up. v0.6: DESIGN open question #10 resolved (DESIGN v1.8) — a verified repository may serve `[system-patch]` under an explicit per-repo `allow-system-patch` grant; §13's trust-gating paragraph updated; third-party still never. v0.7: the farm's malware-signature gate lands (BUILD-INFRA v0.4 §7.5) — `clamav` joins core as an infrastructure package with an honest 10.12 floor and a v1 flavor opt-out (§2), and every vendor payload is signature-scanned at repack (§12); client-side scanning stays the user's decision. v0.8: dead-upstream policy — every fetched source is vendored in the repository's `blobs/sha256/` (DESIGN v1.9 §9.6), so a vanished upstream breaks nothing already built; §9 gains the dead-URL bookkeeping rule; companions refreshed. v0.9: owner decision — unsigned vendor artifacts may ship in the **extended orchard only**, `signer` omitted, announced loudly at every install; §12 now matches PACKAGE-FORMAT §3.11, core stays signed-only (DESIGN v1.10 §12.4))
- **Companion to:** [DESIGN.md](DESIGN.md) v1.9, [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) v0.6, [BUILD-INFRA.md](BUILD-INFRA.md) v0.6, [REPOSITORIES.md](REPOSITORIES.md) v0.8, [HOMEBREW-REVIEW.md](HOMEBREW-REVIEW.md) v0.11
- **Audience:** orchard maintainers, reviewers, and contributors
- **Commissioned by:** HOMEBREW-REVIEW.md §8 — one file where Homebrew scattered dozens of docs pages and tribal knowledge

---

## 1. Purpose and precedence

This file is the single rulebook for what may live in aslice's orchards, how packages are born, maintained, deprecated, and buried, and what bars a pull request must clear to merge. Homebrew accumulated these rules across dozens of documentation pages, review folklore, and maintainer memory; aslice writes them down while the project is young enough to fit them in one file.

**Precedence.** The specifications define *mechanism* — what fields exist, what the solver does, what CI can check. This file defines *policy* — what maintainers accept, require, and refuse. Where the two appear to conflict, the conflict is a bug: file an issue against whichever document is wrong. Every schema field this file references is landed: `[deprecation]` §3.14, `[livecheck]` §3.15, `link`/`link_reason` and `notes` §3.8, `ctx.replace` §6.3, `[system-patch]` §3.16 — all in PACKAGE-FORMAT v0.6, alongside `[system]` (v0.4 §3.12, with the `[service]` table of §3.8) and `[runtime]`/`[extension]`/`[ride]` (v0.5 §3.13).

**Charter — not amendable by this document.** Three founding decisions outrank any policy edit (DESIGN §2.2 N7, §9.4, §1):

1. aslice collects no telemetry or analytics of any kind, ever — the project is infrastructure, not a product.
2. Download statistics are rejected as a value signal: obscure libraries downloaded once a month may have immense value precisely because we supply deprecated operating systems.
3. Scope is macOS 10.11–12 on Intel. No Apple Silicon, no newer macOS, no Linux — no matter how convenient a given PR would find it.

**The one-sentence test for every rule below:** does this make aslice more worthy of the trust of people running machines nobody else serves? If a rule stops answering yes, amend it (§19) rather than quietly ignoring it.

---

## 2. Orchard tiers and the acceptance bar

Two project orchards, two bars. (Third-party orchards set their own policy under their own trust level — REPOSITORIES.md §3; this file binds the project's orchards only.)

| | **core** (~300 packages) | **extended** (~2,000 packages) |
|---|---|---|
| Purpose | The platform stratum: shells, toolchains, VCS, TLS, runtimes, editors, the libraries everything links against | Everything else worth having: applications, niche libraries, legacy tools |
| Upstream status | Actively maintained, or maintained-by-aslice with a named maintainer who owns it | May be upstream-EOL — must carry `[deprecation] reason = "upstream-eol"` (§8) |
| Tests | Working `tests.star` smoke test, passing in CI on at least one OS × flavor — **no test, no merge** | Strongly encouraged; required for libraries with dependents in core |
| `[livecheck]` | **Required** (§9) | Encouraged |
| Reproducibility | Working toward `reproducible: true` (§15); nondeterminism is a tracked defect | Best-effort |
| Vendor binaries | Only if `redistribute = true` **and** payload-only by construction (§12) | Allowed with verifiable signature and honest OS/arch tags |
| System software (`[system]`) | Only when the platform genuinely requires it — none at launch (§13) | Allowed with a `[system]` declaration, named maintainer, signed kexts where offered, trust-gated serving (§13) |
| System patches (`[system-patch]`) | Only when the platform genuinely requires it — the frozen-TLS-CLI patch family is the founding case (§13) | Allowed with a `[system-patch]` declaration, named maintainer, per-target justification, demonstrated byte-exact restore, official/local-only serving (§13) |
| Security posture | CVE flags are blocking work items for the named maintainer (§16) | CVE flags surface in `audit`; fixed best-effort |

**Hard rejections — both tiers, no exceptions, no override flags:**

- **Anything that patches or modifies macOS system files *outside the declared `[system-patch]` category*** (DESIGN §13.1). The default stands — aslice installs alongside the OS and never edits `/System`, `/usr`, or Apple's binaries silently, incidentally, or as a side effect of anything else. The one exception is §13's system-patch category (DESIGN §12.11): declared targets, the original backed up, replacement by profile symlink, rollback to the byte, consent at every decision point, official and local repositories only, refused paths blocked by construction. The marketing feature survives, stated honestly: aslice never patches your system *behind your back*. (Kernel extensions and SIP-disabled development software are likewise **not** rejections — they are the restricted system-software category of §13: declared, warned, consent-gated, trust-gated.)
- **Anything whose installation requires executing vendor or maintainer scripts.** Binary installs execute zero package code, for every package, forever (DESIGN §10.1). A `.pkg`/`.dmg` whose function requires its `preinstall`/`postinstall` scripts is out of scope; an accepted package *discovered* to require them is removed, not accommodated (§12).
- **Runtime dependencies on `/usr/lib` dylibs or `/usr/bin` tools** — the codified rejection of Homebrew's `uses_from_macos` (§6).
- **HEAD / unpinned builds in core.** Reproducibility and the lock model both depend on pins. Extended strongly discourages them; third-party orchards answer to their own trust level.
- **Software that is itself hostile** — known malware, scareware, or packages whose primary function is deception. Obscurity is never a reason for exclusion (charter); hostility always is.
- **License-less or license-violating content.** Every package carries an SPDX `license`; core binaries must be redistributable by the project (§12 for vendor terms).

**The acceptance review for a new core package** answers, in the PR body: who maintains it (a name, not "the community"), what its `[livecheck]` strategy is, why it belongs in core rather than extended, and what its test proves.

**Infrastructure packages.** Tooling the farm itself depends on is **core by definition** — the farm dogfoods the orchard, so everything in the quarantine and signing pipeline is a package we ship, never a private dependency. The founding case is `clamav` (BUILD-INFRA §7.5), the signature scanner every staged slice passes before signing. It declares `min_os = "10.12"` honestly and opts out of the v1 flavor with the reason named (its Rust toolchain, ≥1.74, cannot target 10.11) — the honesty rule applied to ourselves. Users who want on-demand scanning install the very package the farm runs; nothing about it is mandatory on a user's machine, and no client-side scan-on-install machinery exists to make it so.

---

## 3. Naming, versioning, and revisions

- **Names** are lowercase ASCII letters, digits, and hyphens, starting with a letter, and match the upstream project's own name unless that name collides or is misleading. Aliases for historical renames live in the orchard's alias table so `adopt --from-homebrew` and old locks keep resolving.
- **Versioned packages** (`openssl@3`) exist when two majors are simultaneously maintained and depen