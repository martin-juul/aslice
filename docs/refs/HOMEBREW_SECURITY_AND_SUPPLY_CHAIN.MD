# Homebrew Security and Supply Chain

## Source identity

- Original source: https://docs.brew.sh/Homebrew-Security-and-Supply-Chain
- Author/publisher: Homebrew project
- Source version/date: Documentation retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Original technical account; upstream text not reproduced. Upstream copyright remains with its authors.
- Used by: HOMEBREW-REVIEW security comparison

## Captured material

Homebrew describes layered supply-chain controls, signed API metadata, package checksums, provenance/attestation work, and trust boundaries around third-party contributions. These controls authenticate origin and distribution; they do not prove the absence of malicious behavior in software the user chooses to run. Installation sandboxing and tap trust are distinct layers.

## Applicability and limits

Exact opt-in defaults, verifier dependencies, and rollout status are version-sensitive. Comparisons must name their release and should not characterize all Homebrew content as unsigned or all executable packages as sandboxed at runtime.

## Project interpretation

The source supports the facts above. Project policy and acceptance gates remain in the linked specification; they are not attributed to the source. No successful aslice runtime test is implied by archiving this reference.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.
