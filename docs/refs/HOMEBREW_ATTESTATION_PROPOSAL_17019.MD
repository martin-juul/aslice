# Homebrew Attestation Proposal 17019

## Source identity

- Original source: https://github.com/Homebrew/brew/issues/17019
- Author/publisher: woodruffw / Homebrew issue participants
- Source version/date: opened 2024-04-03; retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [HOMEBREW-REVIEW §3.2 Security and trust](../HOMEBREW-REVIEW.md#32-security-and-trust): The historical proposal distinguishes opt-in bottle verification from an independent verify command.
  - [HOMEBREW-REVIEW §10. Sources](../HOMEBREW-REVIEW.md#10-sources): Proposal status is not proof of shipped defaults.

## Captured material

The proposal discusses opt-in attestation checks during install and an independent verify command. It identifies existing CI attestations and one-time backfills for older reachable bottles, a beta default of false, and the gh bootstrap dependency. The retrieved issue is closed as not planned. Issue state and proposed flag spelling do not establish the shipped implementation; the dated beta implementation account records the actual published opt-in spelling.

## Decision-relevant context

Source locator: Issue #17019, woodruffw opening body dated 2024-04-03: Proposal, Outstanding considerations, motivation, alternatives.

woodruffw credits josephsweeney as co-implementer and reports that reachable core bottles have either CI attestations or a one-time backfill. The proposal names `BREW_VERIFY_ATTESTATIONS`, initially false, for downloaded and cached bottles; a separate `brew verify` would work independently of that setting. It leaves beta duration and secure bootstrapping of `gh` unresolved and lists no alternative design.

The retrieved issue is closed as not planned and labeled stale. Its activity timeline was not exposed, so no closure date, participant consensus, or closure rationale is inferred. The [May implementation account](HOMEBREW_PROVENANCE_BETA_IMPLEMENTATION.MD) later documents `HOMEBREW_VERIFY_ATTESTATIONS=1`; the proposal's spelling is historical, not an installation instruction.

## Applicability and limits

Only the facts used by this repository are captured in this original-word account. This is not a full transcript or current-version implementation guarantee.

## Project interpretation

Use the issue for design chronology and unresolved bootstrap questions. A closed issue cannot by itself prove that verification shipped, failed, or became default; the implementation article and dated security documentation provide different evidence.

## Omissions and evidence gaps

Comment chronology and individual comment permalinks are unavailable in the retrieved activity view. The opening issue URL is the locator; later discussion and backfill artifact inventories are not captured.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
