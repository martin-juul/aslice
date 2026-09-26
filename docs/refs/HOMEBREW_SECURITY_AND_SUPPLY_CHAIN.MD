# Homebrew Security and Supply Chain

## Source identity

- Original source: https://docs.brew.sh/Homebrew-Security-and-Supply-Chain
- Author/publisher: Homebrew project
- Source version/date: Documentation retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account plus complete upstream Markdown source asset.
- Rights: BSD-2-Clause, Homebrew contributors; [license and notice](HOMEBREW_LICENSE.txt).
- Used by:
  - [HOMEBREW-REVIEW §2. Where aslice is already ahead](../HOMEBREW-REVIEW.md#2-where-aslice-is-already-ahead): Homebrew authenticates API metadata and applies several independent checks.
  - [HOMEBREW-REVIEW §3.2 Security and trust](../HOMEBREW-REVIEW.md#32-security-and-trust): Attestation verification and sandboxing have explicit conditions and exclusions.

## Captured material

Homebrew describes layered supply-chain controls, signed API metadata, package checksums, provenance/attestation work, and trust boundaries around third-party contributions. These controls authenticate origin and distribution; they do not prove the absence of malicious behavior in software the user chooses to run. Installation sandboxing and tap trust are distinct layers.

## Decision-relevant context

Source locator: Signed JSON API metadata; Bottle provenance attestations; Layered infrastructure with cross-checks; No arbitrary code execution on install by default; Casks have a different trust model; Local trust model.

Default official installs use precomputed JWS-signed JSON rather than locally evaluating package Ruby. This includes formula, cask, and internal package API files; `HOMEBREW_NO_INSTALL_FROM_API` opts out. Reviewed download hashes reject changed bytes, while attestations add the expected build identity. The captured documentation says `HOMEBREW_VERIFY_ATTESTATIONS` enables verification with GitHub tooling and describes default verification as future work pending a pure-Ruby implementation. Supported third-party GitHub taps can publish verifiable attestations under their own identity.

The pipeline separates client releases, package definitions, metadata publishing, and bottle storage, but most remain on GitHub. The Sigstore transparency log supplies a cross-check outside that hosting dependency. Compromising storage alone is different from compromising reviewed metadata and build identity together.

Official package changes receive maintainer review and checksums; third-party tap evaluation needs explicit trust. Structured install steps reduce evaluation of Ruby, but a vendor cask installer and the installed application retain their own execution risks. Sandbox controls target installation/build damage; they cannot certify arbitrary software safe to run. Cooldowns delay selected ecosystem updates rather than proving them benign.

## Applicability and limits

Exact opt-in defaults, verifier dependencies, and rollout status are version-sensitive. Comparisons must name their release and should not characterize all Homebrew content as unsigned or all executable packages as sandboxed at runtime.

## Project interpretation

This dated source provides stronger evidence for the review's opt-in row than the 2024 proposal alone. Do not generalize that default to a different release without a new capture. TUF freshness protections, JWS authenticity, and build provenance answer distinct questions.

## Omissions and evidence gaps

The complete documentation text is retained, including its qualifications. Linked threat reports, Tap Trust command reference, implementation files, and independent security assessments are not all captured.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Complete original: [HOMEBREW_SECURITY_AND_SUPPLY_CHAIN.source.txt](HOMEBREW_SECURITY_AND_SUPPLY_CHAIN.source.txt). Retrieval URL: https://raw.githubusercontent.com/Homebrew/brew/main/docs/Homebrew-Security-and-Supply-Chain.md. Retrieved 2026-09-26 UTC; SHA-256: `2b7134b816e05cf3ebbbdb1a13800a3ccf9f86adca45bc5ffaa272bf22dec9e3`. Branch snapshot; no immutable commit is claimed. The bytes are unmodified UTF-8 Markdown; include this asset and [HOMEBREW_LICENSE.txt](HOMEBREW_LICENSE.txt) in offline copies. Relative upstream links in the asset retain upstream meaning and are not promises of local coverage.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
