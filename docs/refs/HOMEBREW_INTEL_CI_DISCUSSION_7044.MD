# Homebrew Intel CI Discussion 7044

## Source identity

- Original source: https://github.com/orgs/Homebrew/discussions/7044
- Author/publisher: Homebrew discussion participants and maintainers
- Source version/date: discussion snapshot retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [DESIGN §1.1 The gap that is opening](../DESIGN.md#11-the-gap-that-is-opening): Missing Intel bottles preceded the planned execution cutoff.
  - [DESIGN §9.2 The GitHub CI problem](../DESIGN.md#92-the-github-ci-problem): Maintainers reported infrastructure failures behind early bottle cessation.

## Captured material

The discussion concerns missing Intel bottles after Intel CI was disabled. Maintainer explanations distinguish stopping bottle builds from the later date when Homebrew itself stops running. Users may encounter absent binaries before that execution cutoff. Reported operational difficulties with Intel CI explain the decision but do not prove that every package or old bottle is unusable. The dated support-tier policy is the authority for the announced schedule.

## Decision-relevant context

Source locator: Discussion #7044, August 31–September 1, 2026; answered and locked at retrieval.

ewenmcneill opened the thread on August 31, reporting runners disabled on August 28 and an `htmldoc` upgrade without a bottle. The posted environment was Intel macOS 15.7.7, Homebrew 6.0.20-69-g6bf9a47. Source compilation was suggested by the error, not reported successful.

[botantony, August 31](https://github.com/orgs/Homebrew/discussions/7044#discussioncomment-18216300), said August cessation was unplanned. [SMillerDev, August 31](https://github.com/orgs/Homebrew/discussions/7044#discussioncomment-18216870), reported pre-test setup exceeding two hours, unexplained VM slowdown, and a queue blocking other platforms. ewenmcneill clarified that the complaint concerned discoverability of the early change; mojotx also criticized communication rather than demanding reversal.

[MikeMcQuaid's accepted answer, September 1](https://github.com/orgs/Homebrew/discussions/7044#discussioncomment-18231338), cited volunteer capacity, Apple's transition, GitHub's schedule, and builds taking at least ten times longer; it recommended MacPorts. This records maintainer explanations, not independent CI measurements.

## Applicability and limits

Only the facts used by this repository are captured in this original-word account. This is not a full transcript or current-version implementation guarantee.

## Project interpretation

The incident supports maintaining an independent build/test capability. It does not show that every old Intel bottle stopped working. The project's September shorthand omits the reported August 28 operational cutoff; retain that distinction for a separate wording decision.

## Omissions and evidence gaps

No complete CI logs, affected-formula inventory, or root-cause diagnosis is archived. Nested replies are summarized selectively; the complete conversation is not claimed.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
