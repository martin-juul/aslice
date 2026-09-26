# Homebrew Monterey Discussion 5603

## Source identity

- Original source: https://github.com/orgs/Homebrew/discussions/5603
- Author/publisher: Homebrew discussion participants
- Source version/date: discussion snapshot retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [DESIGN §1.1 The gap that is opening](../DESIGN.md#11-the-gap-that-is-opening): OS support and bottle testing can end while brew still runs.
  - [DESIGN — Appendix B. References](../DESIGN.md#appendix-b-references): The Monterey warning is a dated operational report.

## Captured material

This discussion records users encountering unsupported-macOS warnings on Monterey. It illustrates that a package manager may still execute on an OS outside its supported testing matrix; successful local use does not imply supported bottle availability or maintainer support. Treat individual experiences as reports, with the archived support-tier policy providing the project-level requirements.

## Decision-relevant context

Source locator: Discussion #5603, opened September 14, 2024; accepted answer and February 2025 exchange.

Jmuccigr reported an unsupported warning on September 14, 2024, with Homebrew 4.3.21 on macOS 12.4 arm64. [Bo98's accepted answer that day](https://github.com/orgs/Homebrew/discussions/5603#discussioncomment-10647978) said CI covered three macOS versions and Monterey capacity had moved to macOS 15 the previous day. The expectation that 12.7.6 would be Monterey's final update is a participant forecast, not an Apple guarantee.

On February 22, 2025, [filpedroso](https://github.com/orgs/Homebrew/discussions/5603#discussioncomment-12287797) asked for clearer, less harsh warnings. [p-linnane](https://github.com/orgs/Homebrew/discussions/5603#discussioncomment-12288471) cited hardware cost, volunteer effort, and fewer duplicate issues, while distinguishing brew execution from bottle coverage. [filpedroso's February 23 reply](https://github.com/orgs/Homebrew/discussions/5603#discussioncomment-12290785) accepted the explanation. This outcome concerns that exchange, not universal agreement.

Other users discuss patching macOS or switching systems. Their successes and failures are reports, not supported migration procedures.

## Applicability and limits

Only the facts used by this repository are captured in this original-word account. This is not a full transcript or current-version implementation guarantee.

## Project interpretation

This evidence motivates a legacy platform scope without promising that a particular unsupported install fails immediately. The opening report is arm64; it illustrates an OS-window policy, not an Intel-specific defect.

## Omissions and evidence gaps

The page reports 8 comments and 52 replies, with some previous replies collapsed. This capture covers the relevant visible exchange; it cannot establish complete discussion chronology or endorse third-party patchers.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
