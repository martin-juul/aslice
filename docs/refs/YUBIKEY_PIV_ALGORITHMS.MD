# YubiKey PIV Algorithms

## Source identity

- Original source: https://developers.yubico.com/PIV/Introduction/YubiKey_and_PIV.html
- Author/publisher: Yubico
- Source version/date: PIV implementation documentation retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [KEY-RUNBOOK §5. Future independent custody and hardware](../KEY-RUNBOOK.md#5-future-independent-custody-and-hardware): PIV Ed25519 requires firmware 5.7+, so owned YubiKey 4 devices cannot supply it through PIV.

## Captured material

YubiKey 4, YubiKey 5, and NEO implement PIV. The usual signing slots support RSA-1024, RSA-2048, and the P-256/P-384 elliptic curves. Firmware 5.7 and later adds RSA-3072, RSA-4096, Ed25519, and X25519. Existing older devices cannot be assumed to support the newly listed algorithms. Default administrative secrets must be changed before operational use.

## Decision-relevant context

Source locator: YubiKey and PIV, supported devices/algorithms and default credentials.

Firmware 5.7 adds algorithms to the PIV application; the model name alone is insufficient to infer that revision. RSA sizes and NIST elliptic curves on earlier devices do not imply Ed25519 support. X25519 is a key-agreement algorithm, not an Ed25519 signing substitute.

PIV separates PIN/PUK and management authorization from the private key's algorithm. Administrative defaults require replacement before operational use. Successful authentication to a token is still separate from producing the byte format expected by a package-signature verifier.

## Applicability and limits

This establishes the PIV application's capability boundary, not all YubiKey applications. Ed25519 support alone does not establish compatibility with minisign's wire format or a working backup/restore path.

## Project interpretation

Inventory the actual device and application before designing a signing adapter. Continue using the existing signing design until signature encoding, key backup/custody, and recovery are demonstrated; the vendor capability table alone does not establish those properties.

## Omissions and evidence gaps

Other YubiKey applications, APDU/PKCS#11 integration, minisign encoding, and a key-recovery procedure are not captured. This is a PIV capability boundary, not a claim about every operation the device can perform.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
