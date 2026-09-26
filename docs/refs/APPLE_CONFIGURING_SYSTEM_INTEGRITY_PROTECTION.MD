# Apple Configuring System Integrity Protection

## Source identity

- Original source: https://developer.apple.com/library/archive/documentation/Security/Conceptual/System_Integrity_Protection_Guide/ConfiguringSystemIntegrityProtection/ConfiguringSystemIntegrityProtection.html
- Author/publisher: Apple
- Source version/date: Archived System Integrity Protection Guide
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [SYSTEM-VOLUMES §2. Enrollment and preflight](../SYSTEM-VOLUMES.md#2-enrollment-and-preflight): Recovery and machine security state are prerequisites for protected writes.
  - [DESIGN §12.7 System software: kexts and SIP-disabled development tools](../DESIGN.md#127-system-software-kexts-and-sip-disabled-development-tools): Root privileges alone do not disable SIP.

## Captured material

SIP configuration is changed from Recovery OS using csrutil. The configuration affects the machine's supported macOS installations and persists across them. A normal application cannot treat its own root privileges as permission to change SIP. The setting and the target volume must be inspected before performing protected operations.

## Decision-relevant context

Source locator: Configuring System Integrity Protection, configuration storage paragraph and Recovery steps; updated 2015-09-16.

The setting lives in NVRAM, not on an individual filesystem. `csrutil status` reports its state from Terminal; changes require Recovery OS, reached on the described Macs with Command-R at startup. The article demonstrates `csrutil enable` in Recovery Terminal and requires a reboot after a change. Its enterprise exception points to NetBoot/NetInstall/NetRestore guidance rather than granting ordinary applications another switching mechanism.

The archived guide also restricts programmatic startup-disk selection using `bless(8)`. That statement belongs to this 2015 SIP guide; it does not specify the later snapshot interfaces discussed in the [writable-root thread](APPLE_WRITABLE_ROOT_VOLUME_DISCUSSION.MD).

## Applicability and limits

This source predates SSV and does not define authenticated-root behavior. Capture SIP and SSV prerequisites separately; enabling or disabling one is not evidence about the other.

## Project interpretation

Preflight must measure the machine setting and target volume independently. The project leaves security-setting changes to the user in Recovery; that authorization policy is aslice's, not a procedure supplied by Apple.

## Omissions and evidence gaps

The linked enterprise deployment procedure is not captured. SSV, authenticated-root, and per-build Recovery utility behavior are outside this 2015 chapter; see the separate SSV record.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
