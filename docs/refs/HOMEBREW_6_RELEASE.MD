# Homebrew 6 Release

## Source identity

- Original source: https://brew.sh/2026/06/11/homebrew-6.0.0/
- Author/publisher: Homebrew / Mike McQuaid
- Source version/date: 2026-06-11
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account plus complete upstream Markdown source asset.
- Rights: BSD-2-Clause, Homebrew contributors; [license and notice](HOMEBREW_LICENSE.txt).
- Used by:
  - [HOMEBREW-REVIEW §3.2 Security and trust](../HOMEBREW-REVIEW.md#32-security-and-trust): Tap trust gates evaluation of third-party Ruby.
  - [HOMEBREW-REVIEW §3.3 Orchard / maintainer machinery](../HOMEBREW-REVIEW.md#33-orchard--maintainer-machinery): Cooldown and install-step features are release-level evidence.
  - [HOMEBREW-REVIEW §3.4 Environments, services, ecosystem](../HOMEBREW-REVIEW.md#34-environments-services-ecosystem): Bundle parallelism and brew exec are distinct environment features.

## Captured material

Version 6 requires explicit trust before evaluating or running third-party tap code, binds trust lists to remotes, and trusts official taps by default. Its smaller internal JSON API becomes the default. It describes Linux sandboxing, hardened install phases, parallel bundle installs, developer-default confirmation prompts, and new brew exec environments. It announces initial macOS 27 support and reiterates Intel CI/bottle retirement in September 2026, with Intel execution removal in September 2027. Security fixes address insecure download redirects, installer Git hooks, and a user-controlled installer plist. SBOM generation becomes opt-in. These are release-level comparison facts; exact command semantics and later defaults require their own versioned contracts.

## Decision-relevant context

Source locator: Tap trust; Default internal JSON API; Linux sandbox; Cooldowns, livecheck and bumping; Install steps framework; New commands, flags and output.

Third-party taps and qualified formula/cask items require trust before evaluation. Trust/allow/forbid lists are tied to remotes, and untrusted taps are no longer implicitly added. Official taps remain trusted. This limits which Ruby is admitted; it does not make trusted arbitrary Ruby harmless.

The smaller combined internal JSON API becomes the default. Bubblewrap sandboxing on Linux is on by default for developers; the post does not say every Linux installation gains identical protection. Developer-default ask mode prints dependency plans and confirmation prompts. Bundle formula installation runs concurrent jobs automatically.

Install steps express common file preparation as ordered literal data delivered through the API. Conversion covers a large share of official postinstall/flight blocks, with more operations planned; it is not complete elimination of arbitrary install code. Cooldowns cover several ecosystem download and bump paths, while livecheck throttling controls checks. `brew exec` introduces formula environments. `brew vulns` is introduced as a tap/subcommand, and SBOM support becomes opt-in via `HOMEBREW_SBOM`.

The security section separately identifies redirect, installer Git-hook, and user-controlled plist fixes. Their descriptions are evidence of fixed incident classes, not a complete threat model.

## Applicability and limits

Dated account of the relevant facts, not a full original or an implementation test.

## Project interpretation

Keep trust admission, sandbox containment, and declarative steps separate in comparisons. Each addresses a different execution boundary. A release feature list does not establish aslice parity until its own equivalent is implemented and tested.

## Omissions and evidence gaps

The web reader failed for this URL, but direct HTTP and the source Markdown both succeeded. Full post text is retained; linked PRs, exact cooldown values, and runtime acceptance tests are not.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Complete original: [HOMEBREW_6_RELEASE.source.txt](HOMEBREW_6_RELEASE.source.txt). Retrieval URL: https://raw.githubusercontent.com/Homebrew/brew.sh/master/_posts/2026-06-11-homebrew-6.0.0.md. Retrieved 2026-09-26 UTC; SHA-256: `9ed296a3ef16b9e37698c7c4be27804bd646e2f277b0ce7af964edb9794c2d51`. Branch snapshot; no immutable commit is claimed. The bytes are unmodified UTF-8 Markdown; include this asset and [HOMEBREW_LICENSE.txt](HOMEBREW_LICENSE.txt) in offline copies. Relative upstream links in the asset retain upstream meaning and are not promises of local coverage.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
