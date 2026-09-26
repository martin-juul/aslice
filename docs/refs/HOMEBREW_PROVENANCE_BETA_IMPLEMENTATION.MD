# Homebrew Provenance Beta Implementation

## Source identity

- Original source: https://blog.trailofbits.com/2024/05/14/a-peek-into-build-provenance-for-homebrew/
- Author/publisher: Joe Sweeney and William Woodruff / Trail of Bits
- Source version/date: 2024-05-14
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Original technical account; upstream text not reproduced. Upstream copyright remains with its authors.
- Used by: DESIGN platform/flavor rationale; HOMEBREW-REVIEW comparison; KEY-RUNBOOK hardware alternatives as applicable

## Captured material

The beta binds bottle content to a GitHub Actions identity through an in-toto statement. Verification first checks Homebrew/homebrew-core with publish-commit-bottles.yml, then a dated backfill from trailofbits/homebrew-brew-verify with backfill_signatures.yml; absence of both fails. The cutoff prevents new artifacts masquerading as historical backfills. The beta offers brew verify and opt-in install verification through HOMEBREW_VERIFY_ATTESTATIONS=1. Both use gh and authenticated GitHub APIs; missing credentials can prevent verification. Provenance does not prevent malicious source, downgrade attacks, or confusion without additional policy. Coverage concerns homebrew-core; extending to other taps and source provenance is future work in this article. These historical details must not be presented as verified current defaults.

## Applicability and limits

Only the facts used by this repository are captured in this original-word account. This is not a full transcript or current-version implementation guarantee.

## Project interpretation

The source supports the facts above. Project policy and acceptance gates remain in the linked specification; they are not attributed to the source. No successful aslice runtime test is implied by archiving this reference.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.
