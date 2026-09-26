# SmartCard HSM Algorithms

## Source identity

- Original source: https://www.cardlogix.com/product/smartcard-hsm-4k-usb-token/
- Author/publisher: CardLogix
- Source version/date: product page retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [KEY-RUNBOOK §5. Future independent custody and hardware](../runbooks/KEY-RUNBOOK.md#5-future-independent-custody-and-hardware): The advertised algorithms do not establish compatibility with Ed25519/minisign or TUF thresholds.

## Captured material

The URL retains 4k in its name but the retrieved page describes a SmartCard-HSM 180K USB Token. It lists RSA through 4096 bits, ECC through 521 bits, AES-256, and ECDSA. This does not establish Ed25519 or minisign support. Backup/restore key domains and threshold authentication concern token operations; they are not automatically equivalent to TUF requiring signatures by distinct keys. Hardware selection must verify the delivered model, firmware, algorithm API, backup behavior, and recovery procedure before adoption.

## Decision-relevant context

Source locator: SmartCard-HSM 180K USB Token product description, cryptographic capabilities, backup/restore, and authentication features; URL still says 4k.

The retrieved product identifies a 180K token although the URL names 4k. The listed RSA, ECC/ECDSA, and AES capabilities describe different cryptographic operations; an ECC bit-size ceiling is not an assertion that every curve or signing format is supported. Backup/restore through key domains addresses token key custody, while threshold authentication controls access to token operations.

Neither feature is equivalent to a client verifying signatures from independently authorized TUF keys. The advertised feature list does not supply a minisign integration, signature encoding test, or recovery demonstration on the proposed release host.

## Applicability and limits

Only the facts used by this repository are captured in this original-word account. This is not a full transcript or current-version implementation guarantee.

## Project interpretation

Keep this as a future hardware alternative, with delivered model and firmware verification before selection. A change of signature algorithm or custody arrangement remains a separate decision; the product page does not authorize it.

## Omissions and evidence gaps

Pricing, accessory offers, full datasheets, firmware/API manuals, and measured recovery behavior are not captured. The ambiguous URL/model relationship requires supplier confirmation rather than an assumption that older devices gained these features.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
