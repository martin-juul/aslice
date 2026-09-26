# Homebrew Provenance Beta Implementation

## Source identity

- Original source: https://blog.trailofbits.com/2024/05/14/a-peek-into-build-provenance-for-homebrew/
- Author/publisher: Joe Sweeney and William Woodruff / Trail of Bits
- Source version/date: 2024-05-14
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [HOMEBREW-REVIEW §2. Where aslice is already ahead](../HOMEBREW-REVIEW.md#2-where-aslice-is-already-ahead): May 2024 verification used opt-in settings, gh, authenticated APIs, and a backfill.
  - [HOMEBREW-REVIEW §3.2 Security and trust](../HOMEBREW-REVIEW.md#32-security-and-trust): Build provenance authenticates build identity, not package safety or update freshness.

## Captured material

The beta binds bottle content to a GitHub Actions identity through an in-toto statement. Verification first checks Homebrew/homebrew-core with publish-commit-bottles.yml, then a dated backfill from trailofbits/homebrew-brew-verify with backfill_signatures.yml; absence of both fails. The cutoff prevents new artifacts masquerading as historical backfills. The beta offers brew verify and opt-in install verification through HOMEBREW_VERIFY_ATTESTATIONS=1. Both use gh and authenticated GitHub APIs; missing credentials can prevent verification. Provenance does not prevent malicious source, downgrade attacks, or confusion without additional policy. Coverage concerns homebrew-core; extending to other taps and source provenance is future work in this article. These historical details must not be presented as verified current defaults.

## Decision-relevant context

Source locator: Our implementation; Verifying provenance today; Looking forward, May 14, 2024.

The authors reject rebuilding all historical bottles because old runners/toolchains are unavailable, and reject verifying only when attestations happen to exist because stripping them would bypass the check. A distinct backfill identity plus a cutoff permits mandatory failure when neither acceptable evidence path exists.

The historical example installs the external tap `trailofbits/homebrew-brew-verify`, then verifies a named formula such as bash. The install integration sets `HOMEBREW_VERIFY_ATTESTATIONS=1`. Both paths bootstrap `gh` when missing; authentication can be supplied through `gh auth login` or `HOMEBREW_GITHUB_API_TOKEN`. The authors warn ordinary users away during beta because performance and UX are unsettled.

The article links the cutoff's implementation but does not state its timestamp in prose. That exact constant is not recovered here; do not implement the backfill policy from this account alone.

## Applicability and limits

Only the facts used by this repository are captured in this original-word account. This is not a full transcript or current-version implementation guarantee.

## Project interpretation

The alternatives explain why a digest match is weaker than expected-build-identity verification. aslice's separate freshness and signature requirements address additional risks; they are not proven superior by this historical beta account.

## Omissions and evidence gaps

No beta verifier source, exact cutoff value, sample credential, complete in-toto statement, or backfill inventory is archived. Images and proposed future DSL are omitted. These gaps block reproducing the verifier, not understanding its stated policy.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
