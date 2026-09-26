# Homebrew 7 Release and Intel Support

## Source identity

- Original source: https://brew.sh/2026/09/13/homebrew-7.0.0/
- Author/publisher: Homebrew project
- Source version/date: 7.0.0 release, 2026-09-13
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account plus complete upstream Markdown source asset.
- Rights: BSD-2-Clause, Homebrew contributors; [license and notice](HOMEBREW_LICENSE.txt).
- Used by:
  - [DESIGN §1.1 The gap that is opening](../DESIGN.md#11-the-gap-that-is-opening): Intel Tier 3, bottle cessation, and execution removal are separate events.
  - [HOMEBREW-REVIEW §2. Where aslice is already ahead](../HOMEBREW-REVIEW.md#2-where-aslice-is-already-ahead): Performance, security, services, and GUI comparison claims are dated to this release.
  - [HOMEBREW-REVIEW §3.2 Security and trust](../HOMEBREW-REVIEW.md#32-security-and-trust): Installation protection has vendor-installer and runtime boundaries.

## Captured material

The release moves Intel macOS to Tier 3, ends Catalina support, and reports no routine new Intel bottles; the planned Intel execution cutoff is September 2027. It describes parallel installation work, security advisories and vulnerability checking, stronger installation sandboxing, and migration of third-party formula/cask hooks toward declarative install steps.

The release also describes services environment overrides and changes to shell environment handling. These observations motivate aslice's legacy platform scope and operational feature comparison. They do not establish that an unimplemented replacement is faster or safer.

## Decision-relevant context

Source locator: Upgrading; Performance; Installation and tap protection; macOS users; Security teams and auditors; Install steps.

The platform table removes Catalina immediately, retains Intel execution until 2027-09-01, and distinguishes existing bottles from new builds: updated formulae may require source compilation. MacPorts is the suggested Intel alternative. The post attributes the early end of routine bottles to unreliable CI; see the separate August discussion.

Performance work overlaps downloads and preparation, reuses parsed metadata while checking signatures on every load, and reduces subprocesses. It is not a benchmark against aslice. Installation protection limits home-directory reads and moves downloads into a network-enabled fetch phase, followed by an offline install phase for migrated formulae. Migration is ongoing. Vendor `.pkg` installers remain outside the sandbox, and installed applications run with user privileges.

Service environment overrides persist under `$HOMEBREW_USER_CONFIG_HOME/services/<formula>.env` and take effect on restart. `brew doctor --json` supplies structured diagnostics. BrewUI requires macOS Tahoe 26 or later. Built-in vulnerability checks distinguish fixes and coverage gaps, including skipped taps. Third-party attestation verification requires taps to publish suitable attestations.

Official taps reject legacy Ruby install hooks; third-party hooks warn until 2027-12-11 and migrate to `*_steps`. Linux changes from Bubblewrap to Landlock, with advisory-only missing protection on kernels without it. These qualifications matter when comparing security across platforms.

## Applicability and limits

This is a dated release comparison. Preserve the date when printing; future support policy can change. Per-feature implementation claims require the individual upstream contract, not inference from marketing language.

## Project interpretation

The post supports the legacy-platform opportunity and particular comparison rows. It does not support universal claims that Homebrew installation is unsandboxed, that all bottles disappear, or that aslice is faster. Any such broader comparison needs separate evidence and a project review.

## Omissions and evidence gaps

The full post is retained. Linked advisories, DSL manuals, implementation PRs, and benchmarks are not transitively archived; release-level statements cannot substitute for their detailed contracts.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Complete original: [HOMEBREW_7_RELEASE_AND_INTEL_SUPPORT.source.txt](HOMEBREW_7_RELEASE_AND_INTEL_SUPPORT.source.txt). Retrieval URL: https://raw.githubusercontent.com/Homebrew/brew.sh/master/_posts/2026-09-13-homebrew-7.0.0.md. Retrieved 2026-09-26 UTC; SHA-256: `f2fde4426ebe5e9ab0f81fc4c2ca771c048a8d48b7668f33c5eeb775e21922ca`. Branch snapshot; no immutable commit is claimed. The bytes are unmodified UTF-8 Markdown; include this asset and [HOMEBREW_LICENSE.txt](HOMEBREW_LICENSE.txt) in offline copies. Relative upstream links in the asset retain upstream meaning and are not promises of local coverage.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
