# Homebrew Provenance Beta Sigstore

## Source identity

- Original source: https://blog.sigstore.dev/homebrew-build-provenance/
- Author/publisher: William Woodruff and Hayden Blauzvern
- Source version/date: 2024-05-14
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [HOMEBREW-REVIEW §10. Sources](../HOMEBREW-REVIEW.md#10-sources): The May 2024 announcement establishes the start of the public provenance beta.

## Captured material

The beta announcement says official homebrew-core CI bottle builds receive Sigstore attestations binding artifact content to the producing workflow, commit, and GitHub Actions run. It describes these as SLSA Build L2-compatible. At publication this was early beta with active dependencies under development. This announcement establishes the historical provenance rollout; it does not establish the current client verification default or prove source correctness.

## Decision-relevant context

Source locator: May 14, 2024 announcement by William Woodruff (Trail of Bits) and Hayden Blauzvern (Google), paragraphs following the beta announcement.

The announcement follows the previous November's Alpha-Omega/Trail of Bits collaboration. It scopes attestation generation to bottles built in official homebrew-core CI. The statement binds content to the producing workflow, commit, and Actions run rather than merely attaching an unauthenticated label. The authors describe the result as compatible with SLSA Build L2 and direct experimenters to the longer implementation article.

Generation of attestations is distinct from client verification. The post calls the rollout early beta with dependencies still under development; it contains no claim that every user verifies by default, or that historical bottles were rebuilt.

## Applicability and limits

Only the facts used by this repository are captured in this original-word account. This is not a full transcript or current-version implementation guarantee.

## Project interpretation

Pair this rollout evidence with the implementation record for verification prerequisites and backfill limits. SLSA compatibility is the authors' characterization; this archive does not independently certify the service.

## Omissions and evidence gaps

Screenshots, linked SLSA requirements, and supporting GitHub service documentation are omitted. No complete attestation bundle is preserved; the announcement alone cannot implement verification.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
