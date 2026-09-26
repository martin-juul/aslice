# SmartCard HSM Algorithms

## Source identity

- Original source: https://www.cardlogix.com/product/smartcard-hsm-4k-usb-token/
- Author/publisher: CardLogix
- Source version/date: product page retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Original technical account; upstream text not reproduced. Upstream copyright remains with its authors.
- Used by: DESIGN platform/flavor rationale; HOMEBREW-REVIEW comparison; KEY-RUNBOOK hardware alternatives as applicable

## Captured material

The URL retains 4k in its name but the retrieved page describes a SmartCard-HSM 180K USB Token. It lists RSA through 4096 bits, ECC through 521 bits, AES-256, and ECDSA. This does not establish Ed25519 or minisign support. Backup/restore key domains and threshold authentication concern token operations; they are not automatically equivalent to TUF requiring signatures by distinct keys. Hardware selection must verify the delivered model, firmware, algorithm API, backup behavior, and recovery procedure before adoption.

## Applicability and limits

Only the facts used by this repository are captured in this original-word account. This is not a full transcript or current-version implementation guarantee.

## Project interpretation

The source supports the facts above. Project policy and acceptance gates remain in the linked specification; they are not attributed to the source. No successful aslice runtime test is implied by archiving this reference.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.
