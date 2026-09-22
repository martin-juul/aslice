# aslice vs Homebrew — Capability Review and Gap Analysis

- **Status:** Review v0.21 — September 2026 (v0.2: vendor-binary packages supersede the cask deferral — §3.4, §5, §9 rows updated; v0.3: 32-bit/universal vendor payloads on 10.11–10.14; v0.4: companions — DESIGN v1.2 opens the declared `[system]` category for kexts and SIP-off dev tools, ORCHARD-POLICY.md delivered; the installer-script rejection stands unchanged; v0.5: §4.4 Services UX **closed** — DESIGN v1.3 §12.8 delivers the launchd-native `aslice service` CLI and adds stop–swap–restart upgrade orchestration beyond the proposal; PACKAGE-FORMAT v0.4 replaces `[[install.service]]` with the generated `[service]` table; v0.6: multi-version runtime management **delivered** — DESIGN v1.5 §12.9 adds the shim layer with session/project/default selection (`use`/`pin`/`default`), riding tools, and ABI-epoch-bound extension slices; PACKAGE-FORMAT v0.5 §3.13 adds `[runtime]`/`[extension]`/`[ride]`; v0.7: trust-store management **delivered** — DESIGN v1.6 §12.10 adds `aslice ca-update`: a signed, generation-managed `ca-certificates` slice (configurable source, Mozilla-via-curl default), profile env wiring for userland TLS, and an opt-in System-keychain import through `aslice-system`, recorded and reversible to the certificate); v0.8: `ca-update` extended — `--crypto` (crypto-provider stack upgrade, SecureTransport's frozen limits printed, never hidden) and `--apple-certs` (Apple's own roots via a pinned `apple-roots` slice into the System keychain); DESIGN v1.7 also amends the never-touch-system charter line into the declared, flagged `[system-patch]` category — original backed up, profile-symlink replacement, generation-integrated rollback, official/local trust gate, refused paths by construction (§12.11). v0.9: the §8 checklist's remaining PACKAGE-FORMAT amendments land — `[deprecation]`, `[livecheck]`, `link`/`link_reason`, `notes`, `ctx.replace`, `[system-patch]` are PACKAGE-FORMAT v0.6; the `system-patch` repository capability is REPOSITORIES v0.6 §3; delivered-status markers added to §4.2, §4.3, §4.5; v0.10: companions — DESIGN v1.8 lands this review's remaining operational machinery (self-update §12.12, `on_request`/`clean` §8.4, the day-two CLI §12.1, framework allowlist §13.1, merge gates §13.4, roadmap §14) and resolves all eight remaining open questions; the `system-patch` repository capability gains the verified-with-grant path (REPOSITORIES v0.7); v0.11: companions — DESIGN v1.9 (genesis audit, installer TLS-dead fallback, vendored sources), BUILD-INFRA v0.6 (source vendoring, VM image genesis), REPOSITORIES v0.8, ORCHARD-POLICY v0.8, docs/GENESIS.md lands the from-nothing runbook; no review content change; v0.12: review corrections — the §2 freshness row and the §3 matrices gain the status the specs earned (livecheck/autobump/bump-pr/cooldowns specified in PACKAGE-FORMAT v0.6 §3.15 and ORCHARD-POLICY §9; self-update, bootstrap trust, SECURITY.md, services, exec, test, create delivered in DESIGN v1.3–v1.8; `link`/`unlink` delivered in DESIGN v1.10 §12.1); §4.1, §4.6, §4.9–§4.13 gain status markers; §4.12 records the owner rejection of the code-of-conduct proposal; v0.13: §4.6 **closed** — the wishlist and Brewfile import are delivered whole-machine by DESIGN v1.11 §12.13 and SETUP.md (`setup.toml`, the unified `aslice apply`, `aslice export`, `aslice import --from-brewfile`); §2, §3, §7 rows updated; the header number also catches up with the v0.12 entry it had not reflected; v0.14: editorial pass — prose revised for directness; no findings, statuses, or proposals changed; v0.15: prose rewrite throughout — reworded in the project's technical-writing voice; companion versions updated; no findings, statuses, or proposals changed. v0.16: review pass — companion versions refreshed (DESIGN v1.14, PACKAGE-FORMAT v0.11, BUILD-INFRA v0.9, REPOSITORIES v1.2, ORCHARD-POLICY v1.2); no review content changes. v0.17: NOMENCLATURE.md vocabulary reference added to the header; companion versions refreshed (DESIGN v1.15, PACKAGE-FORMAT v0.12, BUILD-INFRA v0.10, REPOSITORIES v1.3, ORCHARD-POLICY v1.3); no review content changes. v0.18: §3.3 rows updated — the Formula importer is named `aslice orchard port --from-homebrew` and the test-bot row records the locally-runnable merge gate `aslice orchard ci` (both DESIGN v1.16 §12.14); companion versions refreshed (DESIGN v1.16, PACKAGE-FORMAT v0.12, BUILD-INFRA v0.11, REPOSITORIES v1.4, ORCHARD-POLICY v1.4). v0.19: §4.8's web index proposal names its home — aslice.sh/packages, part of the owner's layout decision that aslice.sh carries the human pages as paths on the apex and the machine endpoints as subdomains (September 2026); companion versions refreshed (DESIGN v1.17, PACKAGE-FORMAT v0.13, BUILD-INFRA v0.12, REPOSITORIES v1.5, ORCHARD-POLICY v1.6). v0.20: the declarative-setup file is renamed `aslice-machine.toml` — a reserved, self-describing name — and its verbs move under the `aslice machine` group (`aslice machine apply` / `export` / `import --from-brewfile`); top-level `aslice apply` keeps saved plans and lock files (owner decision, September 2026) — the §3.3 bundle rows, §4.6's delivered-status paragraph, and the §9 roadmap row updated; companion versions refreshed (DESIGN v1.18, PACKAGE-FORMAT v0.14, BUILD-INFRA v0.12, REPOSITORIES v1.5, ORCHARD-POLICY v1.6); v0.21: grafts — the installer-script execution rejection is narrowed by owner decision (September 2026): vendor installer scripts are in scope as declared, hash-pinned, user-approved, farm-rehearsed grafts (DESIGN v1.19 §12.15; schema PACKAGE-FORMAT v0.15 §3.11; acceptance ORCHARD-POLICY v1.7 §12); the §2 install-time-code row, the §3.4 cask row, the §5 "rejected forever" row, and the §9 post-review note are amended to the narrowed claim — undeclared vendor code still never runs; companion versions refreshed (DESIGN v1.19, PACKAGE-FORMAT v0.15, REPOSITORIES v1.6, ORCHARD-POLICY v1.7)
- **Companion to:** [DESIGN.md](DESIGN.md) v1.19, [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) v0.15, [BUILD-INFRA.md](BUILD-INFRA.md) v0.12, [REPOSITORIES.md](REPOSITORIES.md) v1.6, [ORCHARD-POLICY.md](ORCHARD-POLICY.md) v1.7
- **Method:** aslice's two specifications compared feature-by-feature against Homebrew's living feature set as of Homebrew 7.0.0 (September 2026). Apple-Silicon-specific work and Homebrew's Intel deprecation/removal machinery are excluded per review scope; everything else Homebrew does today is fair game.
- **Sources:** Homebrew release notes 4.6.0 → 7.0.0, docs.brew.sh (Security and Supply Chain, Tap Trust), Homebrew/brew issue #17019 (attestation verification). Links in §10.
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md) — project terms, acronyms, and the Homebrew translation table.

---

## 1. Verdict up front

aslice's **architecture is ahead of Homebrew** on the axes the project was founded on — security model, binary provenance, variant interop, rollback, µarch targeting, startup performance. On several of these, Homebrew 6.0/7.0 is visibly *converging toward* aslice's founding positions (declarative install steps replacing `post_install` Ruby, tap trust gating arbitrary tap code, a built-in vulnerability database, stronger sandboxing) — which validates the thesis: aslice starts where Homebrew is migrating to, without fifteen years of legacy to drag along.

The gaps found are almost all **operational machinery, not core design**. Homebrew's real product was never the installer — it is the *freshness pipeline* and the corpus. The review found the aslice spec strongest on what was designed first (security, ABI, store) and thinnest on the unglamorous automation that keeps a package collection alive day to day.

**The five most important missing pieces, in order:**

1. **Upstream release tracking and bump automation** — a `livecheck`/autobump equivalent. The OS platform is frozen; upstreams are not. Package churn is the *entire* ongoing workload, and Homebrew runs it with heavy automation (livecheck DSL, scheduled autobump, `bump-formula-pr`, supply-side cooldowns). Without an equivalent planned from day one, the orchard rots on a schedule. **(P0)**
2. **Self-distribution** — no specified mechanism for aslice to update *itself*, and no signing/notarization story for the bootstrap binary users are asked to `curl | sh` into existence. **(P0)**
3. **Package lifecycle states** — Homebrew's `deprecate!`/`disable!` with dates and reasons, pinning, `outdated`. aslice has a boolean and a lock file where a lifecycle is needed. **(P1)**
4. ~~**Services UX**~~ — **delivered (DESIGN v1.3 §12.8, PACKAGE-FORMAT v0.4):** `[service]` declares the service and aslice generates the plist, `aslice service` is the launchd-native CLI, env overrides live outside the immutable store, and upgrades stop–swap–restart running services as part of the transaction (§4.4).
5. **The "keg-only" decision** — no policy for packages that shadow macOS-provided tools/libraries (curl, sqlite3, openssl). Homebrew's answer is ugly but load-bearing; aslice needs its principled equivalent. **(P1)**

None of these require rearchitecting anything. All of them are cheaper to spec now than to retrofit.

---

## 2. Where aslice is already ahead

| Dimension | Homebrew 7.0 reality | aslice spec | Verdict |
|---|---|---|---|
| Install-time package code | `post_install` Ruby deprecated in 7.0, migrating to `*_steps` DSL; third-party taps still arbitrary Ruby, now gated by tap trust (6.0) — trust prompts, not elimination | **Zero undeclared** package code at binary install, from day one, for every orchard — vendor installer scripts run only as declared, approved, sandboxed, rehearsed grafts (DESIGN v1.19 §12.15) | Ahead — aslice starts where Homebrew converges |
| Binary provenance | Sigstore/GitHub attestations; verification **opt-in** (`HOMEBREW_VERIFY_ATTESTATIONS`, default off), depends on the `gh` CLI and authenticated GitHub API; backfill waterfall for pre-2024 bottles | minisign/Ed25519 signatures verified **before extraction on every slice**, no external tool, plus SLSA-style provenance in the manifest | Ahead — always-on, self-contained |
| Index/metadata integrity | JWS-signed JSON API (a real improvement; signed metadata) | Full **TUF**: offline threshold root, snapshot/timestamp keys — rollback, freeze, and mix-and-match protection | Ahead |
| Feature variants/flags | Removed from `homebrew-core` in 2019; options live only in third-party taps and break bottle assumptions | ABI-aware variant model: optimization never enters identity; `abi = true` variants do | Ahead — the founding insight |
| Rollback | None; old kegs linger until `cleanup`, no atomic switch | Generations with atomic `rename(2)` swap; `rollback`, `switch-generation` | Ahead |
| µarch targeting | None (one build per OS/arch) | v1/v2/v3 flavors, solver-enforced | Ahead |
| Startup / solve speed | Ruby + Bootsnap; 7.0 reduced subprocess overhead | <10 ms startup, <50 ms solve targets | Ahead (must be proven, not just claimed) |
| Build sandboxing | `sandbox-exec` on builds for years; 7.0 strengthened profiles; superenv shim environment | Seatbelt phase profiles + deterministic environment (`LC_ALL`, `TZ`, `SOURCE_DATE_EPOCH`, prefix-mapping) | Parity, arguably ahead on determinism |
| Vulnerability checking | `brew vulns` + advisory DB (new in 6.0/7.0) | `aslice audit` with CPE + OSV, SPDX SBOM per slice, EOL surfacing | Parity-to-ahead |
| Prefix hygiene | `/usr/local` chowned to user (historic, criticized) | `/opt/aslice` user-owned, no sudo in steady state | Ahead |
| Downloads | Concurrent by default since 5.0 | HTTP/2, 8-way parallel, resumable ranges, zstd | Parity |
| Relocation | Relocation metadata recorded, poured bottles rewritten; prefix length constraints bite on Linux; non-/usr/local prefixes degrade bottle coverage | Fixed default prefix = zero rewriting in the common case; relocation metadata for custom prefixes | Parity, simpler common case |
| Index updates | Internal JSON API (no git taps needed by default) — fast | TUF snapshot diffs — comparable, signed harder | Parity-to-ahead |
| **Freshness pipeline** | **livecheck DSL, autobump, bump-formula-pr, cooldowns** | **Specified** — `[livecheck]`, scheduled autobump, `bump-pr`, cooldowns (PACKAGE-FORMAT §3.15, ORCHARD-POLICY §9): parity on paper | **Behind — the gap now is execution, not design** |
| **Corpus** | ~15 years of formulae encoding macOS quirk knowledge | 0 today; 300 core planned | **Behind — the real moat** |
| Services UX | `brew services` mature; per-service env overrides (7.0) | Declarative `[service]` + launchd-native CLI + stop–swap–restart upgrades (§4.4 — delivered, DESIGN v1.3) | **Ahead** on upgrade safety |
| Multi-version runtimes | Separate `php@x.y`/`python@x.y` formulae, keg-only juggling; the real answer is external managers (nvm, pyenv, rbenv, Volta) shadowing brew with their own shims and state | Release streams in one formula; shim layer with session/project/default selection (`use`/`pin`/`default`); tools ride the selected runtime; extensions ABI-epoch-bound (§4.15 — delivered, DESIGN v1.5) | **Ahead** — version management as a package-manager feature, not a second tool |
| Environments | `brew bundle` (Brewfile), `brew exec` (npx-like, 6.0) | Lock files (exact reproduction); `aslice exec` temporary views (§4.6 — delivered, DESIGN v1.8 §12.1); `aslice-machine.toml` wishlist with whole-machine `aslice machine apply`/`export` (§4.6 — delivered, DESIGN v1.18 §12.13) | Delivered |
| GUI | BrewUI native app (7.0) | None (CLI-first audience) | Behind, acceptably |

---

## 3. Detailed comparison matrix

Legend: ✅ spec covers it · ⚡ aslice is ahead · ⚠ partial / under-specified · ❌ missing

### 3.1 Install / upgrade / day-two UX

| Homebrew capability | aslice status | Notes |
|---|---|---|
| install (binary-first), uninstall, upgrade | ⚡ | Binary-first is the default in both; aslice adds flavor selection |
| reinstall | ✅ | `aslice reinstall` — same version, fresh link, repairs a damaged profile entry (DESIGN v1.8 §12.1) |
| outdated (list upgradeable) | ✅ | `aslice outdated [--json]` — what would upgrade, and why; honors pins (DESIGN v1.8 §12.1) |
| pin / unpin (hold a package) | ✅ | `aslice pin` / `unpin` — upgrade skips held packages, `outdated` says so (DESIGN v1.8 §8.4, §12.1); §4.3 closed |
| leaves / deps / uses / why | ✅ | `leaves`, `why` specified; add `uses --installed` (reverse edges) explicitly |
| autoremove (orphan deps) | ✅ | `on_request` tracking delivered — every DB install record carries it, `aslice mark` repairs the record (DESIGN v1.8 §8.4); §4.9 closed |
| cleanup (cache scrubbing) | ✅ | `aslice clean` owns the cache — watermark-driven LRU eviction, `--dry-run` symmetry with `gc` (DESIGN v1.8 §8.4, §12.1); §4.10 closed |
| fetch (standalone prefetch, retry/resume) | ⚠ | Resumable ranges specified in perf model; no user-facing `fetch` command |
| doctor | ⚡ | Fully specified (DESIGN §12.6): check battery with stable IDs, `--json`, scriptable exit codes, curated narrow `--fix`, Homebrew-coexistence checks — ahead of Homebrew's |
| shellenv (emit PATH setup) | ✅ | `aslice shellenv` — pure echo, no writes (DESIGN v1.8 §12.1); `aslice init` covers zsh and bash (MANUAL §2.3) |
| info/search with rich metadata | ⚠ | `--json` on everything is specified; `keywords` field powers search. Missing: a **public web index** — see §4.8 |
| install specific version (`install foo@1.2`, version-install) | ⚡ | `aslice install ffmpeg@v6` + index snapshots give *arbitrary historical* installs — better than Homebrew's versioned-formula hacks |
| link / unlink / switch between installed versions | ✅ | Generations supersede `switch`; per-profile `aslice link`/`unlink` for `link = false` shadowing packages delivered (DESIGN v1.10 §12.1, PACKAGE-FORMAT §3.8); §4.5 closed |

### 3.2 Security and trust

| Homebrew capability | aslice status | Notes |
|---|---|---|
| Tap trust (explicit trust before code runs, 6.0) | ⚡ | Orchard trust levels + the no-undeclared-install-code model obsoletes the entire category — the one execution path, grafts, is declared, approved, and rehearsed (DESIGN v1.19 §12.15) |
| Bottle attestations (Sigstore, opt-in) | ⚡ | Always-on minisign + TUF; consider *also* emitting GitHub Artifact Attestations for GHCR-hosted slices (free, defense-in-depth) |
| Signed JSON API (JWS) | ⚡ | TUF supersedes |
| Vulnerability DB (`brew vulns`) | ⚡ | `audit` + CPE + SBOM; add advisory-index caching for offline audit (Homebrew generates one from formulae.brew.sh — same trick works for the aslice index) |
| Build sandbox | ⚡ | Phase-scoped Seatbelt profiles + hermetic env |
| **Self-update security** | ⚡ delivered | `aslice self-update` — signed, verified, installed as a new generation, health-checked after the swap, automatic rollback on a failed smoke test (DESIGN v1.8 §12.12); §4.1 closed |
| **Bootstrap binary trust** | ⚡ delivered | Minisign-signed *and* Apple-notarized bootstrap (DESIGN §10.3), hash-pinned in the installer with a second transport; §4.1 closed |
| SECURITY.md / vuln reporting for aslice itself | ⚡ delivered | SECURITY.md, CONTRIBUTING.md, and the key-ceremony/rotation runbook (docs/KEY-RUNBOOK.md) shipped; the code-of-conduct proposal was owner-rejected (§4.12) |
| Stale system trust store (expired/missing roots — this platform's day-one failure) | ⚡ delivered | Homebrew: nothing — the keg-only `ca-certificates` formula helps CLI tools only, the system store rots untouched. aslice: `aslice ca-update` — signed, generation-managed bundle (configurable source, Mozilla-via-curl default) + profile env wiring + opt-in System-keychain import via `aslice-system`, recorded and reversible to the certificate (DESIGN v1.6 §12.10); v1.7 adds `--crypto` (upgrades the crypto-provider slices — modern ciphers/TLS 1.3 for aslice userland; SecureTransport's frozen limits printed, never hidden) and `--apple-certs` (Apple's own roots — not in Mozilla's program — from a pinned `apple-roots` slice, same consent/recording/reversibility rules) |
| System file modification (patching the OS itself) | ⚡ | Homebrew: Cask pkg scripts and `installer script:` — arbitrary code, often as root, with no backup and no rollback. aslice: declared `[system-patch]` — the original is backed up, the replacement is a symlink through the profile (generation rollback *is* patch rollback), restore is byte-verified, consent is per-decision, serving is gated to official and local repositories (verified only via the user's explicit per-repo grant), and catastrophic paths plus platform-binary dylibs are refused by construction (DESIGN v1.7 §12.11) |

### 3.3 Orchard / maintainer machinery

| Homebrew capability | aslice status | Notes |
|---|---|---|
| livecheck DSL (detect upstream releases) | ⚡ specified | `[livecheck]` delivered (PACKAGE-FORMAT v0.6 §3.15); §4.2 closed on paper — execution remains |
| autobump (scheduled automatic version bumps) | ⚡ specified | Scheduled autobump is policy (ORCHARD-POLICY §9); PR merges gate on the matrix (§4.7) |
| bump-formula-pr / bump-revision | ⚡ specified | `aslice bump-pr <pkg> <version>` — edit, lint, smoke-build one flavor, open the PR (DESIGN v1.8 §12.1) |
| Supply-side cooldowns (npm/PyPI/RubyGems delay before bumping, 6.0) | ⚡ specified | Cooldown floor of 2 days, raisable for the historically risky ecosystems (PACKAGE-FORMAT §3.15, ORCHARD-POLICY §9) |
| brew create (formula scaffolding from URL) | ⚡ specified | `aslice create <url>` — fetch, hash, sniff the build system, emit a package.toml draft (DESIGN v1.8 §12.1); §4.11 |
| audit --new / style checks | ⚠ | `aslice lint` covers schema + policy; add a `--new-package` ruleset (homepage reachable, license present, description rules) |
| test-bot CI (build, test, bottle, merge-gate) | ⚡ | Merge gates specified: full declared flavor × OS matrix, ABI-diff gates on provider revisions, dependent-rebuild cascade (DESIGN v1.8 §13.4); the gate also runs pre-PR as `aslice orchard ci` (DESIGN v1.16 §12.14); §4.7 closed |
| brew test (run formula's test block on installed package) | ⚡ | `aslice test <pkg>` runs tests.star against the installed slice, on demand (DESIGN v1.8 §12.1) |
| Formula importer | ⚡ | §13.3 Ruby→TOML/Starlark importer, shipped as `aslice orchard port --from-homebrew` (DESIGN v1.16 §12.14) — ahead of Homebrew (which has no such thing because it never needed one) |

### 3.4 Environments, services, ecosystem

| Homebrew capability | aslice status | Notes |
|---|---|---|
| brew services (start/stop/restart/list, env overrides) | ⚡ delivered | Declarative `[service]` + launchd-native `aslice service` CLI + stop–swap–restart upgrades + per-service env overrides (§4.4 — DESIGN v1.3 §12.8, PACKAGE-FORMAT v0.4) |
| Versioned runtimes (php@x.y, python@x.y) + the nvm/pyenv/rbenv/Volta ecosystem around them | ⚡ delivered | One formula with release streams; shims resolve session → project → default; `aslice use/pin/default`; tools ride the selected runtime; extension slices bind to the runtime's ABI epoch; pip/gem/npm installs bind per-version through shim-injected userbases (§4.15 — DESIGN v1.5 §12.9, PACKAGE-FORMAT v0.5 §3.13) |
| brew bundle (Brewfile wishlist, dump) | ⚡ | `aslice-machine.toml` + `aslice machine apply`/`export` — delivered broader than the wishlist: packages, runtime selections, services, `defaults`, login shell; data-not-Ruby where the Brewfile executes (§4.6, SETUP.md) |
| brew exec (npx-like ephemeral environments, 6.0) | ⚡ delivered | `aslice exec <pkg> -- <cmd>` — temporary profile view, discarded on exit (DESIGN v1.8 §12.1); §4.6 |
| Brewfile import for migration | ⚡ | `aslice machine import --from-brewfile` translates a Brewfile into an aslice-machine.toml with a printed skip list for cask/mas/vscode (§4.6, SETUP.md §5) |
| brew shellenv / completions / man pages | ⚠ partially | `shellenv`/`init` delivered (DESIGN v1.8 §12.1, MANUAL §2.3); man pages exist (man/); completions open — §4.13 |
| HOMEBREW_* env contract, brew config/env | ⚠ | `aslice config` exists; publish a stable `ASLICE_*` environment contract — see §4.13 |
| Offline mode | ⚡ delivered | Cache-and-snapshot offline operation specified — cached slices install, `doctor --offline` reports snapshot age (MANUAL §9.5); the `ASLICE_*` contract remains open (§4.13) |
| Analytics (opt-out) | ⚡ | **None, ever** — resolved decision (DESIGN §2.2 N7): aslice collects no telemetry or analytics of any kind, not even opt-in. The project is infrastructure, not a product |
| formulae.brew.sh web index | ❌ | See §4.8 |
| BrewUI native GUI (7.0) | ❌ | Acceptable to defer; note as opportunity for the retro-Mac community |
| Casks (GUI apps/fonts) | ⚠ partially superseded | Vendor-binary packages are **in scope** per the repository/vendor-binary decision (PACKAGE-FORMAT v0.2+ §3.11, DESIGN §12.4): `.pkg`/`.dmg`-only software installs payload-only by default — installer scripts never execute unless declared as grafts (DESIGN v1.19 §12.15) — with pinned signers and per-artifact OS/arch tags, **including 32-bit and universal payloads on 10.11–10.14** (the last releases that execute 32-bit code — a population Homebrew never served even at its peak), hosted or vendor-fetched. What remains deferred is app *polish* (icon chrome, `~/Applications` integration), and the declarative `.app` schema reservation stands for that |

---

## 4. The gaps, in detail

Each gap gets the same treatment: what Homebrew has, why it matters *specifically for aslice*, and the concrete proposal.

### 4.1 P0 — Self-distribution: self-update and bootstrap trust

**Homebrew:** updates itself via `brew update` (git pull of Homebrew/brew against tagged stable releases); ships a signed, notarized `.pkg` installer (Apple Silicon only — the Intel-era answer was the install script plus CLT).

**aslice today:** the installer script (§10.3) bootstraps the binary pinned by hash — and then the spec is silent on how aslice updates thereafter.

**Why it matters:** a package manager that cannot safely update itself either rots or trains users to re-run a curl-pipe script — the exact pattern the security model exists to kill. On 10.11–10.13 the system trust store is unusable (§4.1), so the bootstrap binary must carry everything.

**Proposal:**
- **aslice is package zero.** It lives in its own store (`/opt/aslice/store/aslice-x.y.z-…/`) and updates through the same TUF-verified, generation-swapped path as everything else. `aslice self-update` = resolve → fetch slice → verify → build new generation → atomic swap → re-exec. A failed self-update rolls back like any other generation. This is the strongest possible dogfood of the design.
- **One wrinkle to spec:** the generation swap renames the running binary's symlink; the running process must finish the transaction before re-exec (standard, but write it down).
- **Bootstrap trust:** sign the release binaries (minisign, project key) *and* Apple-notarize them. Notarization costs an Apple Developer account (~$99/yr) and removes the Gatekeeper friction + "unidentified developer" scariness that will otherwise greet every new user on 10.15+. The install script verifies the minisign signature itself, so notarization is defense-in-depth and UX, not the root of trust.
- **Pin policy:** `self-update` honors channels if/when added (§4.14), and refuses to update across a `spec`/format major without printing the changelog first.

**Status: delivered (DESIGN v1.8 §12.12, §10.3).** `self-update` is package zero — signed, verified, generation-swapped, health-checked with automatic rollback; the bootstrap binary is minisign-signed and Apple-notarized.

### 4.2 P0 — Upstream freshness: livecheck and autobump

**Homebrew:** `livecheck` DSL per formula (strategies: git tags, homepage regex, directory listing, crates/npm/PyPI APIs, sparkle feeds), `brew livecheck` to query, scheduled **autobump** opening PRs for hundreds of formulae, `bump-formula-pr` for humans, and (6.0) **cooldowns** that delay bumps of supply-chain-risky ecosystems (npm/PyPI/RubyGems) to let poisoned releases get caught.

**aslice today:** nothing. Versions change by hand.

**Why it matters more for aslice than for Homebrew:** DESIGN §9.3's core economic claim is "the platform is frozen, so volunteer effort goes to packages, not platform firefighting." That inverts the workload: freshness automation *is* the project. Homebrew's autobump exists because humans don't scale to thousands of upstreams; aslice's 300-package core is the size where automation pays immediately and manual bumps quietly stop happening in year two.

**Proposal — add to PACKAGE-FORMAT.md:**

```toml
[livecheck]
strategy   = "git-tags"            # git-tags | homepage-regex | directory-index | crates | npm | pypi | sparkle
url        = "https://github.com/FFmpeg/FFmpeg/tags"   # strategy-specific
regex      = "^n([\\d.]+)$"        # optional pattern → version capture
throttle_days = 3                  # don't bump more often than this
cooldown_days = 2                  # wait after upstream release (supply-chain poisoning window)
skip_prerelease = true             # default true
```

- `aslice livecheck [pkg|--all]` — query, machine-readable.
- **Orchard CI runs a scheduled livecheck sweep** and opens bump PRs automatically: new `version`, computed `sha256` (fetched + hashed by the bot), `revision` reset to 0, changelog link in the PR body. PR merges only after the matrix gate (§4.7). Human review can be lightweight for patch bumps, mandatory for major bumps — Homebrew's autobump experience shows most patch bumps are mechanical.
- **Cooldowns and throttle from day one** — cheap insurance, and a differentiator to advertise.
- `brew bump-formula-pr` equivalent: `aslice bump-pr <pkg> <version>` — does the local edit, lints, builds one flavor as a smoke test, opens the PR.

**Status: delivered (PACKAGE-FORMAT v0.6 §3.15).** The `[livecheck]` block landed as proposed — strategies, throttle, and the cooldown floor of 2 days, raisable for the historically risky ecosystems. Freshness policy (required in core, days-behind-upstream as the dashboard number) is ORCHARD-POLICY §9.

### 4.3 P1 — Package lifecycle states

**Homebrew:**