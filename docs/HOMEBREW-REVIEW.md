# aslice vs Homebrew — Capability Review and Gap Analysis

- **Status:** Review v0.18 — September 2026 (v0.2: vendor-binary packages supersede the cask deferral — §3.4, §5, §9 rows updated; v0.3: 32-bit/universal vendor payloads on 10.11–10.14; v0.4: companions — DESIGN v1.2 opens the declared `[system]` category for kexts and SIP-off dev tools, ORCHARD-POLICY.md delivered; the installer-script rejection stands unchanged; v0.5: §4.4 Services UX **closed** — DESIGN v1.3 §12.8 delivers the launchd-native `aslice service` CLI and adds stop–swap–restart upgrade orchestration beyond the proposal; PACKAGE-FORMAT v0.4 replaces `[[install.service]]` with the generated `[service]` table; v0.6: multi-version runtime management **delivered** — DESIGN v1.5 §12.9 adds the shim layer with session/project/default selection (`use`/`pin`/`default`), riding tools, and ABI-epoch-bound extension slices; PACKAGE-FORMAT v0.5 §3.13 adds `[runtime]`/`[extension]`/`[ride]`; v0.7: trust-store management **delivered** — DESIGN v1.6 §12.10 adds `aslice ca-update`: a signed, generation-managed `ca-certificates` slice (configurable source, Mozilla-via-curl default), profile env wiring for userland TLS, and an opt-in System-keychain import through `aslice-system`, recorded and reversible to the certificate); v0.8: `ca-update` extended — `--crypto` (crypto-provider stack upgrade, SecureTransport's frozen limits printed, never hidden) and `--apple-certs` (Apple's own roots via a pinned `apple-roots` slice into the System keychain); DESIGN v1.7 also amends the never-touch-system charter line into the declared, flagged `[system-patch]` category — original backed up, profile-symlink replacement, generation-integrated rollback, official/local trust gate, refused paths by construction (§12.11). v0.9: the §8 checklist's remaining PACKAGE-FORMAT amendments land — `[deprecation]`, `[livecheck]`, `link`/`link_reason`, `notes`, `ctx.replace`, `[system-patch]` are PACKAGE-FORMAT v0.6; the `system-patch` repository capability is REPOSITORIES v0.6 §3; delivered-status markers added to §4.2, §4.3, §4.5; v0.10: companions — DESIGN v1.8 lands this review's remaining operational machinery (self-update §12.12, `on_request`/`clean` §8.4, the day-two CLI §12.1, framework allowlist §13.1, merge gates §13.4, roadmap §14) and resolves all eight remaining open questions; the `system-patch` repository capability gains the verified-with-grant path (REPOSITORIES v0.7); v0.11: companions — DESIGN v1.9 (genesis audit, installer TLS-dead fallback, vendored sources), BUILD-INFRA v0.6 (source vendoring, VM image genesis), REPOSITORIES v0.8, ORCHARD-POLICY v0.8, docs/GENESIS.md lands the from-nothing runbook; no review content change; v0.12: review corrections — the §2 freshness row and the §3 matrices gain the status the specs earned (livecheck/autobump/bump-pr/cooldowns specified in PACKAGE-FORMAT v0.6 §3.15 and ORCHARD-POLICY §9; self-update, bootstrap trust, SECURITY.md, services, exec, test, create delivered in DESIGN v1.3–v1.8; `link`/`unlink` delivered in DESIGN v1.10 §12.1); §4.1, §4.6, §4.9–§4.13 gain status markers; §4.12 records the owner rejection of the code-of-conduct proposal; v0.13: §4.6 **closed** — the wishlist and Brewfile import are delivered whole-machine by DESIGN v1.11 §12.13 and SETUP.md (`setup.toml`, the unified `aslice apply`, `aslice export`, `aslice import --from-brewfile`); §2, §3, §7 rows updated; the header number also catches up with the v0.12 entry it had not reflected; v0.14: editorial pass — prose revised for directness; no findings, statuses, or proposals changed; v0.15: prose rewrite throughout — reworded in the project's technical-writing voice; companion versions updated; no findings, statuses, or proposals changed. v0.16: review pass — companion versions refreshed (DESIGN v1.14, PACKAGE-FORMAT v0.11, BUILD-INFRA v0.9, REPOSITORIES v1.2, ORCHARD-POLICY v1.2); no review content changes. v0.17: NOMENCLATURE.md vocabulary reference added to the header; companion versions refreshed (DESIGN v1.15, PACKAGE-FORMAT v0.12, BUILD-INFRA v0.10, REPOSITORIES v1.3, ORCHARD-POLICY v1.3); no review content changes. v0.18: §3.3 rows updated — the Formula importer is named `aslice orchard port --from-homebrew` and the test-bot row records the locally-runnable merge gate `aslice orchard ci` (both DESIGN v1.16 §12.14); companion versions refreshed (DESIGN v1.16, PACKAGE-FORMAT v0.12, BUILD-INFRA v0.11, REPOSITORIES v1.4, ORCHARD-POLICY v1.4)
- **Companion to:** [DESIGN.md](DESIGN.md) v1.16, [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) v0.12, [BUILD-INFRA.md](BUILD-INFRA.md) v0.11, [REPOSITORIES.md](REPOSITORIES.md) v1.4, [ORCHARD-POLICY.md](ORCHARD-POLICY.md) v1.4
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
| Install-time package code | `post_install` Ruby deprecated in 7.0, migrating to `*_steps` DSL; third-party taps still arbitrary Ruby, now gated by tap trust (6.0) — trust prompts, not elimination | **Zero** package code at binary install, from day one, for every orchard | Ahead — aslice starts where Homebrew converges |
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
| Environments | `brew bundle` (Brewfile), `brew exec` (npx-like, 6.0) | Lock files (exact reproduction); `aslice exec` temporary views (§4.6 — delivered, DESIGN v1.8 §12.1); `setup.toml` wishlist with whole-machine `apply`/`export` (§4.6 — delivered, DESIGN v1.11 §12.13) | Delivered |
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
| Tap trust (explicit trust before code runs, 6.0) | ⚡ | Orchard trust levels + zero-install-code model obsoletes the entire category |
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
| brew bundle (Brewfile wishlist, dump) | ⚡ | `setup.toml` + `aslice apply`/`export` — delivered broader than the wishlist: packages, runtime selections, services, `defaults`, login shell; data-not-Ruby where the Brewfile executes (§4.6, SETUP.md) |
| brew exec (npx-like ephemeral environments, 6.0) | ⚡ delivered | `aslice exec <pkg> -- <cmd>` — temporary profile view, discarded on exit (DESIGN v1.8 §12.1); §4.6 |
| Brewfile import for migration | ⚡ | `aslice import --from-brewfile` translates a Brewfile into a setup.toml with a printed skip list for cask/mas/vscode (§4.6, SETUP.md §5) |
| brew shellenv / completions / man pages | ⚠ partially | `shellenv`/`init` delivered (DESIGN v1.8 §12.1, MANUAL §2.3); man pages exist (man/); completions open — §4.13 |
| HOMEBREW_* env contract, brew config/env | ⚠ | `aslice config` exists; publish a stable `ASLICE_*` environment contract — see §4.13 |
| Offline mode | ⚡ delivered | Cache-and-snapshot offline operation specified — cached slices install, `doctor --offline` reports snapshot age (MANUAL §9.5); the `ASLICE_*` contract remains open (§4.13) |
| Analytics (opt-out) | ⚡ | **None, ever** — resolved decision (DESIGN §2.2 N7): aslice collects no telemetry or analytics of any kind, not even opt-in. The project is infrastructure, not a product |
| formulae.brew.sh web index | ❌ | See §4.8 |
| BrewUI native GUI (7.0) | ❌ | Acceptable to defer; note as opportunity for the retro-Mac community |
| Casks (GUI apps/fonts) | ⚠ partially superseded | Vendor-binary packages are **in scope** per the repository/vendor-binary decision (PACKAGE-FORMAT v0.2+ §3.11, DESIGN §12.4): `.pkg`/`.dmg`-only software installs payload-only — installer scripts never execute — with pinned signers and per-artifact OS/arch tags, **including 32-bit and universal payloads on 10.11–10.14** (the last releases that execute 32-bit code — a population Homebrew never served even at its peak), hosted or vendor-fetched. What remains deferred is app *polish* (icon chrome, `~/Applications` integration), and the declarative `.app` schema reservation stands for that |

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

**Homebrew:** `deprecate! date:, because:` → `disable! date:, because:` → removal; `brew pin`/`unpin`; `brew outdated`; `info` marks disabled/deprecated packages (7.0 polishes this display).

**aslice today:** `[package] deprecated = true` and `[audit] eol` — booleans without a lifecycle.

**Proposal — replace the booleans with:**

```toml
[deprecation]
date        = "2027-03-01"    # when deprecation starts
reason      = "upstream-eol"  # upstream-eol | security | renamed | unmaintainable | other
replacement = "ffmpeg7"       # optional pointer
disable_date = "2027-09-01"   # optional: after this, new installs refuse without --force-disabled
```

Semantics: **active → deprecated** (installs warn, `audit`/`info` surface it) **→ disabled** (new installs refused, existing installs keep working and remain in locks) **→ tombstoned** (formula removed from orchard HEAD; the index keeps a permanent tombstone so old locks still resolve against historical snapshots — something Homebrew's git-tap model does *worse* than aslice's snapshot model can). Add `aslice pin <pkg>` / `unpin` (recorded in the DB, honored by `upgrade`, surfaced in `outdated`), and `aslice outdated [--json]`.

**Status: delivered (PACKAGE-FORMAT v0.6 §3.14; `pin`/`unpin` and `outdated` in DESIGN v1.8 §8.4, §12.1).** The `[deprecation]` table landed as proposed, replacing the `[package] deprecated` boolean; the tombstone guarantee and the security fast path are policy in ORCHARD-POLICY §8.

### 4.4 P1 — Services UX

**Homebrew:** `brew services start|stop|restart|run|list|info|cleanup`; 7.0 added persistent per-service env overrides from `$HOMEBREW_USER_CONFIG_HOME/services/<formula>.env`, surviving upgrades.

**aslice today (pre-v1.3):** `[install.service]` declared the plist; aslice applied it at link time. No CLI, no override story.

**Proposal:**
- `aslice services list|start|stop|restart|run|info <pkg>` — thin, correct layer over launchd, reading the declarative plist. `run` (foreground, no registration) is worth copying — it's how people debug.
- **Override file:** `$XDG_CONFIG_HOME/aslice/services/<pkg>.env` (or `~/.aslice/etc/services/`), applied by the *launcher* at `start` time — never by editing the store's plist (store immutability §8.1 makes this forced, which is good: Homebrew mutates generated files, aslice can't, so the design lands in the right place automatically).
- Services are per-profile: `aslice services list` shows which profile each service belongs to.

**Status: delivered (DESIGN v1.3 §12.8, PACKAGE-FORMAT v0.4).** The design went further than this proposal: `[service]` is generated-plist — the formula ships no plist file at all — and the upgrade transaction itself quiesces affected services (stop, atomic swap, restart, health-checked), so a running nginx is never updated out from under itself. Root-domain daemons go through `aslice-system` and the repository `system` capability; user agents stay unprivileged.

### 4.5 P1 — The keg-only decision (shadowing system software)

**Homebrew:** `keg_only` — packages shadowing macOS-provided software (openssl, sqlite, curl, ruby…) install but don't link into the prefix, with a reason string; versioned formulae (`openssl@3`) are keg-only by default.

**aslice today:** no equivalent. Versioned packages like `openssl@3` are named (PACKAGE-FORMAT §5.2) and `links_priority` exists (§3.8), but nothing says "don't link by default."

**Why it matters even with a private prefix:** `/opt/aslice/bin` on PATH ahead of `/usr/bin` means aslice's `curl`, `sqlite3`, `python3` shadow Apple's — usually desired, sometimes breaking (system scripts hardcode BSD behaviors; `lldb`, security tools). The failure mode is subtle and support-heavy.

**Proposal — add to `[install]`:**
- `link = false` (default true) with mandatory `link_reason = "shadows-macos"` — the principled keg-only. Installed into the store, absent from the profile; `aslice link openssl@3` opts in per-profile; dependents use `ctx.deps` paths and never need the profile link at all (this is where aslice's model is *cleaner* than keg-only: dependency resolution is store-path-based, so "unlinked but depended upon" is natural, not a hack).
- **Policy:** versioned packages (`openssl@3` style) and anything shipping `bin/` names that collide with `/usr/bin` or `/bin` default to `link = false` in core. Lint enforces the reason string.

**Status: delivered (PACKAGE-FORMAT v0.6 §3.8).** `link`/`link_reason` landed with lint enforcement of the reason; the core-default policy is ORCHARD-POLICY §6, which adopted this proposal's wording.

### 4.6 P1 — Environment wishlists and ephemeral exec

**Homebrew:** `brew bundle` (Brewfile: declarative *wishlist*, `bundle dump` from reality), `brew exec` (6.0: run a command inside a package's environment, npx-style).

**aslice today:** lock files are *exact state*, not a wishlist — `aslice apply aslice.lock` replays a captured profile, but there's no human-authored "ensure ffmpeg, python, postgresql (I don't care how)" document, and no ephemeral execution.

**Proposal:**
- **`aslice.toml` project wishlist** (name it `aslice-bundle.toml`? bikeshed later): `packages = ["ffmpeg ^7", "postgresql", "openssl@3 (link=false)"]` + `aslice bundle install/check/dump`. It differs from the lock the way `package.json` differs from `package-lock.json` — constraints vs. exact state. The lock file section (§7) already draws this analogy; complete it.
- **`aslice adopt --from-brewfile`** — parse a Brewfile's `brew` entries into a wishlist (trivially mechanical; ignore `cask`/`mas` with a printed skip list).
- **`aslice exec <pkg> -- <cmd>`** — build a temporary profile view (symlink forest into a tmp generation), run, discard. Nearly free given generations; very useful for testing tools without polluting the default profile.

**Status: delivered (DESIGN v1.11 §12.13, SETUP.md).** The wishlist landed broader than proposed: `setup.toml` covers not just packages but runtime selections, services, `defaults` preferences, and the login shell — one `aslice apply` from blank Mac to working machine, `aslice export` to capture one — as data-not-Ruby where the Brewfile executes. The verb is `apply` (unified with lock replay and plan execution), not `bundle`; the Brewfile path is `aslice import --from-brewfile`. `aslice exec` had landed earlier (DESIGN v1.8 §12.1).

### 4.7 P1 — Orchard CI merge gates, specified

**Homebrew:** test-bot builds, tests, bottles, and gates merges; bottle upload happens only post-merge; dependency-impact annotations on PRs.

**aslice today:** §13.4 says CI "builds the package in the sandbox on both flavors" (now three). Under-specified at the points where the ABI model creates new obligations.

**Proposal — the merge gate for an orchard PR is:**
1. `lint` (schema + policy + `--new-package` ruleset for additions).
2. Sandboxed build on **every declared flavor** (v1/v2/v3) at the formula's `min_os`, plus smoke-run on **each OS release in `[min_os, 12]`** via the farm VMs (tests can be flavor/OS-skippable where genuinely irrelevant, e.g., pure data packages).
3. `tests.star` passes on at least one OS × flavor (core) — already policy, make it mechanical.
4. **ABI gate for provider bumps:** if the PR changes a library's version/revision, CI runs the ABI scan diff between old and new slice; if `compatibility_version` or the symbol fingerprint regresses, the PR must either bump the soname-bearing version, or mark and schedule **dependent rebuilds** (which the farm does automatically on merge, publishing dependents' revision bumps in the same index snapshot — so clients never see the window Homebrew users know as "everything's broken until the rebuilds land").
5. Slice signing and index snapshot update happen only post-merge, on the signing host.

### 4.8 P1 — Discovery: the public web index

**Homebrew:** formulae.brew.sh — searchable web catalog + JSON API + analytics dashboards; it is quietly a major adoption driver (people google "ffmpeg mac" and land there).

**Proposal:** generate a static site from the signed index in the same CI pass that publishes snapshots — package pages (description, versions, flavors, min_os, install command), JSON API mirroring the index. Pure static files, mirrorable like the index itself. Cheap, and it doubles as the transparency surface §13.4 promises (publish build-farm status and the snapshot log there too).

### 4.9 P1 — Installed-on-request tracking

**Homebrew:** distinguishes user-requested installs from dependencies (7.0: `brew list --no-installed-on-request`); `autoremove` correctness depends on it.

**aslice today:** `autoremove` is listed (§12.1) but the DB requirement is implicit.

**Proposal:** every DB install record carries `on_request = true|false` (install command vs. pulled-in). `autoremove` = garbage-collect runtime-reachable nothing-from-`on_request` roots, cross-checked against retained generations. One column; spec it now or retro-fit it painfully. Also add `aslice mark <pkg> --on-request/--as-dependency` for fixing the record (Homebrew has no clean equivalent and users notice).

**Status: delivered (DESIGN v1.8 §8.4).** Every DB install record carries `on_request`; `autoremove` collects nothing reachable from an `on_request` root, cross-checked against retained generations, and `aslice mark` repairs the record.

### 4.10 P1 — Cache eviction policy

**Homebrew:** `brew cleanup [--prune=N] [-s]` scrubs old downloads and stale kegs; 7.0 sped it up.

**aslice today:** §8.4 specs GC for the *store*; `cache/` (slices, sources, index snapshots, ccache) has no policy.

**Proposal:** `aslice clean` (name it `clean`, keep `gc` for the store): LRU eviction of slice/source tarballs not referenced by any installed package or retained generation, watermark-driven (default: evict when cache > 10 GB, keep anything younger than 30 days), `--dry-run` symmetry with `gc`. Source tarballs are the sleeper category — `--build-from-source` users accumulate them silently.

**Status: delivered (DESIGN v1.8 §8.4, §12.1).** `aslice clean` owns the cache with watermark-driven LRU eviction and `--dry-run` symmetry; `gc` owns the store.

### 4.11 P2 — Author and contributor tooling

- **`aslice create <url>`** — fetch the tarball, hash it, sniff the build system (configure script? CMakeLists? meson.build? Cargo.toml?), emit a `package.toml` draft with `[build].system` guessed. Homebrew's `brew create` does this and it is a real contribution funnel; combined with the §13.3 Ruby-formula importer it covers both net-new and ported packages.
- **`aslice test <pkg>`** — run `tests.star` against an *installed* package, on demand (Homebrew `brew test`). Spec tests.star to run in both contexts.
- **`aslice audit-formula --new`** — the new-package policy ruleset (§3.3 above).
- **Documentation stubs:** `aslice home <pkg>` (open homepage) — one-liner that people actually use.

**Status: mostly delivered (DESIGN v1.8 §12.1).** `aslice create`, `aslice test`, and `aslice bump-pr` landed as proposed; the `audit-formula --new` ruleset and `aslice home` remain open.

### 4.12 P2 — Project hygiene documents

**Homebrew:** SECURITY.md, governance docs, code of conduct, maintainer guides — the trust scaffolding §13.4 gestures at.

**Proposal:** before public launch: `SECURITY.md` (how to report a vulnerability *in aslice itself*, key-contact runbook), `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md` (formula style guide: when a variant is justified, `min_os` accuracy, patch documentation requirements), and the key-ceremony/rotation runbook referenced in §10.2 written down rather than implied.

**Status: delivered, with one owner amendment.** SECURITY.md, CONTRIBUTING.md, and the key-ceremony/rotation runbook (docs/KEY-RUNBOOK.md) shipped. The code-of-conduct proposal was rejected by the owner — conduct norms live in CONTRIBUTING.md instead, recorded in DESIGN §13.4.

### 4.13 P2 — Operator surface

- **`aslice shellenv`** — print the PATH/MANPATH/INFOPATH exports for the current profile (Homebrew 7.0 made this avoid path_helper; copy the insight: pure `echo`, no subprocess, no config-file writes).
- **Completions and man pages for aslice itself** — ship zsh/bash/fish completions in the bootstrap package; generate man pages from the CLI's own help definitions so they can't drift.
- **`ASLICE_*` environment contract** — `ASLICE_PREFIX`, `ASLICE_CACHE`, `ASLICE_NO_AUTO_UPDATE`, `ASLICE_OFFLINE`, `ASLICE_FLAVOR`… documented and stable, mirrored by `aslice config`/`aslice env` introspection. Homebrew's `HOMEBREW_*` namespace is how power users and CI actually drive it; aslice should have the same from day one (it also heads off the classic "wrapper script forks behavior" mess).
- **`--offline` / `ASLICE_OFFLINE`** — resolve and install from cache only; paired with cached OSV data, makes `audit` and `install` work on air-gapped lab machines (a real slice of the target audience: audio rigs and lab boxes that never touch the internet).
- **Auto-update policy** — Homebrew auto-updates the index on install (annoying enough that `HOMEBREW_NO_AUTO_UPDATE` is folklore). aslice spec: index auto-refreshes only if older than N hours (default 24), never on `install` of an already-resolvable plan, and `doctor` warns on staleness instead of forcing a wait.

**Status: partially delivered.** `aslice shellenv` and `aslice init` landed (DESIGN v1.8 §12.1; MANUAL §2.3 covers zsh and bash), and aslice's own man pages exist (man/). Still open: shell completions, the stable `ASLICE_*` environment contract, and the index auto-refresh policy.

### 4.14 P2 — Opportunities Homebrew doesn't have (not gaps, but cheap differentiators surfaced by the review)

- **Channels.** TUF snapshots make "stable" vs "edge" almost free: `stable` tracks a snapshot delayed N days with a soak report, `edge` tracks latest. Homebrew's git-tap rolling model can't express this; aslice's snapshot model can. `aslice config set channel stable`.
- **Delta updates between revisions.** zstd `--long` payloads already help; true binary deltas (bsdiff-style) between successive revisions of the same package would cut bandwidth for the upgrade-heavy use case. Farm-side only, client falls back to full slices.
- **Historical installs as a feature.** `aslice install ffmpeg --index-snapshot 2026-09-01` — the snapshot is content-addressed and retained, so "the exact package set from the day this paper's results were produced" is a one-liner. Homebrew can approximate this only by archaeology. Worth marketing to the lab/CI audience.
- **`aslice why --explain` everywhere.** The derivation-tree rendering is already spec'd for solves; extend it to `outdated` and `audit` ("why is this flagged") — explainability as the house style.

### 4.15 P1 — Multi-version runtime management (version managers)

**Homebrew:** versioned runtimes are separate formulae (`php@8.1`, `python@3.12`), keg-only or fighting over the unversioned link; switching means `brew link --overwrite` incantations. The ecosystem's real answer is external version managers — nvm, pyenv, rbenv, Volta — each with its own shims, its own state, and no knowledge of the package manager underneath: two sources of truth for what `python3` resolves to, and PATH-ordering bugs as the support load. Worse, every one of them abandons the extension problem — pecl/pip/gem/npm installs land wherever the *first* resolved runtime put them, and silently cross version boundaries.

**Why it matters for aslice:** this platform's audience keeps old runtimes *on purpose* — a php 7.4 site that may never be ported, a python pinned by a frozen lab pipeline, a ruby held by an ancient Rails app. Version management is not a power-user extra here; it is the daily workflow.

**Status: delivered (DESIGN v1.5 §12.9, PACKAGE-FORMAT v0.5 §3.13).** The design takes the Volta model as the baseline and extends it in three directions Volta doesn't reach. Selection is three-layered — `aslice use` (session, via a shim-visible env var and optional shell integration), `aslice pin` (project `aslice.toml`: Volta's `package.json` pin made ecosystem-neutral), `aslice default` (profile-wide) — resolved by a multicall shim layer ahead of the profile on PATH, exec-only, sub-millisecond. Tools that are pure interpreter-target artifacts (composer, yarn, poetry) declare `[ride]` and launch under the *currently selected* runtime — Volta's best idea, generalized beyond node. And the extension problem is solved structurally: compiled extensions are slices keyed to the runtime's declared ABI epoch (`[extension] runtime = "php"` → `php-redis+php8.4` and `+php8.3` coexist as distinct store paths, generation-managed and rollback-complete), while pip/gem/npm/pecl installs bind per-version through shim-injected userbase environments. Upgrades never cross streams: `aslice upgrade php` patches within 8.4, and moving to 8.5 is an explicit `install` + `use`/`pin`/`default` decision.

---

## 5. What aslice should deliberately NOT copy

| Homebrew feature | Verdict | Why |
|---|---|---|
| `post_install` / arbitrary Ruby at install | Rejected (already) | Homebrew itself is migrating away (`*_steps`); aslice starts declarative-only |
| `uses_from_macos` (lean on system libs to dedupe) | **Rejected, codified** | On 10.11 the system libs are the problem (OpenSSL 0.9.8-era). Lint rule: runtime deps resolve to aslice packages only; exceptions are *frameworks* (Accelerate, SystemConfiguration, CoreAudio…) enumerated in an allowlist, never `/usr/lib` dylibs or `/usr/bin` tools. The Accelerate-shim BLAS provider example already assumes this — write it down as policy |
| keg-only as a post-hoc hack | Rejected; replaced by principled `link = false` (§4.5) | Store-path dependency resolution makes "unlinked but depended upon" natural |
| Auto-update on every command | Rejected | Staleness policy + `doctor` warnings instead (§4.13) |
| Opt-out analytics | Rejected, absolutely | **No telemetry or analytics of any kind, ever — not even opt-in** (DESIGN §2.2 N7). The project is not a product; prebuild prioritization runs on dependency centrality, build pain, irreplaceability, and direct community requests — never on usage volume, which mismeasures value on a legacy platform where the rarest library may be the one nobody else ships |
| HEAD builds in core | Rejected | Reproducibility and the lock model both depend on pins; third-party orchards may do what they like under their own trust level |
| `/usr/local` ownership, sudo in steady state | Rejected (already) | — |
| Casks at launch | Superseded in part; installer-script execution **rejected forever** | Vendor `.pkg`/`.dmg` software is now in scope via `type = "binary"` (§3.4 row above) — but aslice's cask equivalent is strictly payload-only extraction. Homebrew casks' ability to run `installer script:` blocks is a supply-chain hole aslice permanently rejects (DESIGN §10.1); the remaining deferral is GUI-app polish, and the declarative `.app` reservation (§12.4) is the right shape for it |
| BrewUI-style native GUI | Defer | Wrong audience at launch; revisit when the orchard is deep — the index being clean, signed JSON makes a GUI an evening project later |

---

## 6. Additions to the DESIGN.md §15 risk table

| New risk | Severity | Mitigation |
|---|---|---|
| **Freshness workload underestimated** — orchard falls behind upstreams within a year; users perceive the project as dead even while the architecture is sound | High | Autobump machinery is Phase 1 scope, not Phase 3 (§4.2); measure "median days behind upstream" as a published farm-dashboard metric |
| **ABI blind spots: `dlopen`'d plugins, static archives, non-dylib artifacts** (Python `.so` modules loaded by path, Qt plugins, ffmpeg's module loading) escape install-name/compat-version tracking | Medium | Reverse-dependency smoke tests as a merge gate (§4.7); manifest records `dlopen` evidence found at scan time (`strings`/dyld env scan) as advisory metadata; when a provider major-bumps, CI schedules dependent rebuilds regardless of what the scan says — belt and suspenders, we own the farm |
| **Bootstrap-binary trust perception** — users asked to trust a single curl'd binary on day zero | Medium | Notarized + minisign-signed releases, reproducible bootstrap build (Phase 3 cross-checks start with aslice itself), published build instructions |
| **Self-update bug bricks installations** — the one package whose failure takes the manager down with it | Medium | Self-update is a generation swap with automatic rollback on failed post-swap health check; the *previous* generation's binary remains invocable at a stable path (`/opt/aslice/bin/aslice` is the profile symlink, always pointing at a working generation) |
| Index snapshot retention vs. historical installs | Low | Publish retention policy (recommend: keep all snapshots ≤ 1 year, monthly forever); historical-install marketing claim (§4.14) depends on it |

---

## 7. Priority mapping to the roadmap

| Item | Priority | Phase |
|---|---|---|
| Self-update as package zero + bootstrap signing/notarization | P0 | **Phase 0** (it must ship in the first usable binary; retrofitting update mechanisms is how projects die) |
| livecheck schema + `aslice livecheck` + scheduled autobump + bump-pr | P0 | **Phase 1**, alongside the 300-package core seeding — the tooling *is* how the core gets maintained |
| Lifecycle states (`[deprecation]`, pin, outdated, reinstall) | P1 | Phase 1 (cheap; the DB schema wants `on_request` and pins from birth) |
| Services CLI + per-service env overrides | P1 | Phase 1 — design complete (DESIGN v1.3 §12.8, PACKAGE-FORMAT v0.4 `[service]`) |
| Multi-version runtimes (shim layer, use/pin/default, riding tools, extension slices) | P1 | Phase 2 — design complete (DESIGN v1.5 §12.9, PACKAGE-FORMAT v0.5 §3.13) |
| `link = false` policy + lint rules + system-framework allowlist | P1 | Phase 1 (policy must exist *before* the core orchard accumulates violations) |
| Orchard CI merge gates incl. ABI gate + dependent-rebuild cascade | P1 | Phase 1→2 (gate first, ABI-diff automation as the scanner matures) |
| autoremove correctness (`on_request`), `aslice clean` cache policy | P1 | Phase 1 |
| Web index (static site + JSON API) | P1 | Phase 2 (needs an index worth browsing) |
| Wishlist bundle, adopt --from-brewfile, `aslice exec` | P2 | Phase 2 — design complete (`exec` in DESIGN v1.8 §12.1; `setup.toml`/`apply`/`export`/`import --from-brewfile` in DESIGN v1.11 §12.13, SETUP.md) |
| shellenv, completions, man pages, ASLICE_* contract, --offline | P2 | Phase 1 for shellenv/completions (they're part of "feels finished"), rest Phase 2 |
| SECURITY.md/CoC/CONTRIBUTING/key runbook | P1 | **Phase 0** — shipped; the CoC part of the proposal was owner-rejected (§4.12) |
| Channels, delta updates, historical-install marketing | P2 | Phase 3 |
| GUI | P3 | Post-Phase 3, demand-driven |

---

## 8. Spec amendment checklist

**Landing status (v0.12):** every amendment below has landed. The PACKAGE-FORMAT items are **PACKAGE-FORMAT v0.6** (§3.8 `link`/`link_reason`/`notes`, §3.14 `[deprecation]`, §3.15 `[livecheck]`, §3.16 `[system-patch]`, §6.3 `ctx.replace`, appendix updated); the `system-patch` repository capability is **REPOSITORIES §3** (v0.6, amended v0.7 with the verified-with-grant path); the DESIGN items landed across DESIGN v1.3–v1.10; the commissioned rulebook is ORCHARD-POLICY, now v0.9. The checklist is kept verbatim as the record of what this review proposed. (v1.10 added the §12.1 `link`/`unlink` commands this checklist records; `verify-store` shipped under the name `aslice store verify`.)

Concrete deltas this review proposes to the two specifications:

**PACKAGE-FORMAT.md:**
- §3.1: replace `deprecated` boolean with `[deprecation]` table (`date`, `reason`, `replacement`, `disable_date`) — §4.3 of this review.
- §3.8 `[install]`: add `link` (bool, default true) + `link_reason` (required iff `link = false`); add `notes` (array of strings — the human-readable post-install guidance Homebrew calls *caveats*: "config lives in …", "run `aslice services start postgresql` to…"; printed at install, shown in `info`).
- New §3.x: `[livecheck]` block — §4.2.
- §6.3 ctx API: add `ctx.replace(file, pattern, replacement)` — in-place text substitution for trivial fixups without a patch file (Homebrew's `inreplace` is the most-used formula helper; its absence would be felt immediately).
- New §3.x: `[system-patch]` table (`targets`, `sip_off_required`, mandatory `reason`) — DESIGN v1.7 §12.11. REPOSITORIES.md §3: add the `system-patch` capability — official and local repositories only; verified and third-party never.
- Appendix field index: updated accordingly.

**DESIGN.md:**
- §5.2 components: add the **self-update path** (aslice as package zero) — §4.1.
- §8: DB schema requirement — `on_request` flag; §8.4 companion cache-eviction policy (`aslice clean`).
- §10.3: bootstrap binary is minisign-signed *and* Apple-notarized — §4.1.
- §12.1 CLI: add `self-update`, `services`, `pin/unpin`, `outdated`, `reinstall`, `link/unlink`, `clean`, `livecheck`, `test`, `create`, `bump-pr`, `exec`, `shellenv`, `verify-store` (re-hash store paths against manifests — the tripwire command §8.1's immutability promise implies).
- §13.1: add the system-framework allowlist / `/usr/lib` rejection policy — §5.
- §13.4: add merge-gate specifics (matrix, ABI gate, dependent-rebuild cascade) — §4.7; project hygiene docs — §4.12.
- §14 roadmap: move self-update + livecheck/autobump into Phase 0/1 — §7.
- §15: new risks — §6.
- Open questions: #4 (telemetry) is **resolved (v0.3, sharpened v0.4)** — no telemetry or analytics of any kind, ever, and no download-count-driven prioritization; §9.4's prebuild signal is dependency centrality, build pain, irreplaceability, and community requests.

**New document — commissioned and delivered:** `docs/ORCHARD-POLICY.md` (v0.2) — the maintainer-facing rulebook (acceptance bar, variant discipline, deprecation lifecycle, patch documentation, merge gates, release cadence, system-software category). Homebrew scattered this across dozens of docs pages and tribal knowledge; aslice can fit it in one file while the project is young.

---

## 9. What this review did NOT find

Worth stating explicitly, because a review that only adds things is suspicious:

- **No architectural contradictions.** The variant/ABI model, the store/generation design, the flavor system, and the package format compose cleanly; nothing found in the Homebrew comparison invalidates a founding decision. (The closest call is the ABI scanner's `dlopen` blind spot — a limitation to engineer around, not a flaw in the model.)
- **No security model regressions vs Homebrew 7.0.** Homebrew's recent additions (tap trust, attestations, install steps, vulns DB) each have an aslice equivalent that is same-or-stronger; the two genuine holes are about aslice itself (self-update, bootstrap trust), not about packages.
- **No reason to expand scope.** Nothing in the comparison argues for Apple Silicon, macOS 13+, or Linux. Vendor `.pkg`/`.dmg` software entered scope by a separate decision (§3.4) — in the strict payload-only form — but cask-style GUI-app polish and installer-script execution stay out. Homebrew's breadth is what aslice's scope discipline exists to avoid. *(Post-review: kernel extensions and SIP-disabled development tools entered scope in DESIGN v1.2 as the declared, warned, trust-gated `[system]` category — a project-owner decision, not a review finding. The installer-script execution rejection stands unchanged: `aslice-system` performs the privileged steps declaratively, and vendor code still never runs.)*

---

## 10. Sources

- Homebrew 7.0.0 release notes (Sept 13, 2026): performance/parallelism work, stronger sandboxing, BrewUI, built-in vulnerability checks, `post_install` deprecation → `*_steps`, services env overrides, `doctor --json`, Intel → Tier 3: https://brew.sh/2026/09/13/homebrew-7.0.0/
- Homebrew 6.0.0 release notes (June 11, 2026): tap trust, `brew exec`, `brew vulns`, install steps framework, livecheck cooldowns/throttling: https://brew.sh/2026/06/11/homebrew-6.0.0/
- Homebrew 5.0.0 / 5.1.0 / 4.6.0 release notes (download concurrency by default; bundle expansion, version-install; opt-in concurrency): https://brew.sh/2025/11/12/homebrew-5.0.0/ (and linked posts)
- Homebrew Security and Supply Chain docs (JWS-signed JSON API, attestation status, layered cross-checks): https://docs.brew.sh/Homebrew-Security-and-Supply-Chain
- Attestation verification integration (opt-in, `gh` dependency): https://github.com/Homebrew/brew/issues/17019
- Trail of Bits / Sigstore build provenance beta: https://blog.trailofbits.com/2024/05/14/a-peek-into-build-provenance-for-homebrew/
- Sigstore/Homebrew provenance announcement: https://blog.sigstore.dev/homebrew-build-provenance/
