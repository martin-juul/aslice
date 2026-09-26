# YubiKey PIV Algorithms

## Source identity

- Original source: https://developers.yubico.com/PIV/Introduction/YubiKey_and_PIV.html
- Author/publisher: Yubico
- Source version/date: PIV implementation documentation retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Original technical account; upstream text not reproduced. Upstream copyright remains with its authors.
- Used by: KEY-RUNBOOK §5

## Captured material

YubiKey 4, YubiKey 5, and NEO implement PIV. The usual signing slots support RSA-1024, RSA-2048, and the P-256/P-384 elliptic curves. Firmware 5.7 and later adds RSA-3072, RSA-4096, Ed25519, and X25519. Existing older devices cannot be assumed to support the newly listed algorithms. Default administrative secrets must be changed before operational use.

## Applicability and limits

This establishes the PIV application's capability boundary, not all YubiKey applications. Ed25519 support alone does not establish compatibility with minisign's wire format or a working backup/restore path.

## Project interpretation

The source supports the facts above. Project policy and acceptance gates remain in the linked specification; they are not attributed to the source. No successful aslice runtime test is implied by archiving this reference.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.
