# Apple Configuring System Integrity Protection

## Source identity

- Original source: https://developer.apple.com/library/archive/documentation/Security/Conceptual/System_Integrity_Protection_Guide/ConfiguringSystemIntegrityProtection/ConfiguringSystemIntegrityProtection.html
- Author/publisher: Apple
- Source version/date: Archived System Integrity Protection Guide
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Original technical account; upstream text not reproduced. Upstream copyright remains with its authors.
- Used by: SYSTEM-VOLUMES §2; DESIGN §12.7

## Captured material

SIP configuration is changed from Recovery OS using csrutil. The configuration affects the machine's supported macOS installations and persists across them. A normal application cannot treat its own root privileges as permission to change SIP. The setting and the target volume must be inspected before performing protected operations.

## Applicability and limits

This source predates SSV and does not define authenticated-root behavior. Capture SIP and SSV prerequisites separately; enabling or disabling one is not evidence about the other.

## Project interpretation

The source supports the facts above. Project policy and acceptance gates remain in the linked specification; they are not attributed to the source. No successful aslice runtime test is implied by archiving this reference.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.
