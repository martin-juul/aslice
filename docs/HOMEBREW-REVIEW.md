# aslice vs Homebrew — Capability Review and Gap Analysis

- **Status:** Review v0.10 — September 2026 (v0.2: vendor-binary packages supersede the cask deferral — §3.4, §5, §9 rows updated; v0.3: 32-bit/universal vendor payloads on 10.11–10.14; v0.4: companions — DESIGN v1.2 opens the declared `[system]` category for kexts and SIP-off dev tools, ORCHARD-POLICY.md delivered; the installer-script rejection stands unchanged; v0.5: §4.4 Services UX **closed** — DESIGN v1.3 §12.8 delivers the launchd-native `aslice service` CLI and adds stop–swap–restart upgrade orchestration beyond the proposal; PACKAGE-FORMAT v0.4 replaces `[[install.service]]` with the generated `[service]` table; v0.6: multi-version runtime management **delivered** — DESIGN v1.5 §12.9 adds the shim layer with session/project/default selection (`use`/`pin`/`default`), riding tools, and ABI-epoch-bound extension slices; PACKAGE-FORMAT v0.5 §3.13 adds `[runtime]`/`[extension]`/`[ride]`; v0.7: trust-store management **delivered** — DESIGN v1.6 §12.10 adds `aslice ca-update`: a signed, generation-managed `ca-certificates` slice (configurable source, Mozilla-via-curl default), profile env wiring for userland TLS, and an opt-in System-keychain import through `aslice-system`, recorded and reversible to the certificate); v0.8: `ca-update` extended — `--crypto` (crypto-provider stack upgrade, SecureTransport's frozen limits printed, never hidden) and `--apple-certs` (Apple's own roots via a pinned `apple-roots` slice into the System keychain); DESIGN v1.7 also amends the never-touch-system charter line into the declared, flagged `[system-patch]` category — original backed up, profile-symlink replacement, generation-integrated rollback, official/local trust gate, refused paths by construction (§12.11). v0.9: the §8 checklist's remaining PACKAGE-FORMAT amendments land — `[deprecation]`, `[livecheck]`, `link`/`link_reason`, `notes`, `ctx.replace`, `[system-patch]` are PACKAGE-FORMAT v0.6; the `system-patch` repository capability is REPOSITORIES v0.6 §3; delivered-status markers added to §4.2, §4.3, §4.5; v0.10: companions — DESIGN v1.8 lands this review's remaining operational machinery (self-update §12.12, `on_request`/`clean` §8.4, the day-two CLI §12.1, framework allowlist §13.1, merge gates §13.4, roadmap §14) and resolves all eight remaining open questions; the `system-patch` repository capability gains the verified-with-grant path (REPOSITORIES v0.7))
- **Companion to:** [DESIGN.md](DESIGN.md) v1.8, [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) v0.6, [BUILD-INFRA.md](BUILD-INFRA.md) v0.3, [REPOSITORIES.md](REPOSITORIES.md) v0.7, [ORCHARD-POLICY.md](ORCHARD-POLICY.md) v0.6
- **Method:** aslice's two specifications compared feature-by-feature against Homebrew's living feature set as of Homebrew 7.0.0 (September 2026). Apple-Silicon-specific work and Homebrew's Intel deprecation/removal machinery are excluded per review scope; everything else Homebrew does today is fair game.
- **Sources:** Homebrew release notes 4.6.0 → 7.0.0, docs.brew.sh (Security and Supply Chain, Tap Trust), Homebrew/brew issue #17019 (attestation verification). Links in §10.

---

## 1. Verdict up front

aslice's **architecture is ahead of Homebrew** on the axes the project was founded on — security model, binary provenance, variant interop, rollback, µarch targeting, startup performance. On several of these, Homebrew 6.0/7.0 is visibly *converging toward* aslice's founding positions (declarative install steps replacing `post_install` Ruby, tap trust gating arbitrary tap code, a built-in vulnerability database, stronger sandboxing) — which validates the thesis: aslice simply starts where Homebrew is migrating to, without fifteen years of legacy to drag along.

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
| **Freshness pipeline** | **livecheck DSL, autobump, bump-formula-pr, cooldowns** | **Nothing** | **Behind — biggest gap** |
| **Corpus** | ~15 years of formulae encoding macOS quirk knowledge | 0 today; 300 core planned | **Behind — the real moat** |
| Services UX | `brew services` mature; per-service env overrides (7.0) | Declarative `[service]` + launchd-native CLI + stop–swap–restart upgrades (§4.4 — delivered, DESIGN v1.3) | **Ahead** on upgrade safety |
| Multi-version runtimes | Separate `php@x.y`/`python@x.y` formulae, keg-only juggling; the real answer is external managers (nvm, pyenv, rbenv, Volt