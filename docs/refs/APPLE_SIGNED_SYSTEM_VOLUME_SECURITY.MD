# Apple Signed System Volume Security

## Source identity

- Original source: https://support.apple.com/guide/security/secd698747c9/web
- Author/publisher: Apple
- Source version/date: Platform Security article, published 2022-05-13
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [SYSTEM-VOLUMES §1. Three backends](../SYSTEM-VOLUMES.md#1-three-backends): Read-only Catalina volumes and Big Sur SSV need different backends.
  - [SYSTEM-VOLUMES §2. Enrollment and preflight](../SYSTEM-VOLUMES.md#2-enrollment-and-preflight): FileVault and startup-security conditions must be checked before a patch.
  - [SYSTEM-VOLUMES §4. Activation, rollback, and OS updates](../SYSTEM-VOLUMES.md#4-activation-rollback-and-os-updates): Activation and rollback depend on boot selection and retained snapshots.
  - [STATE-AND-RECOVERY §5. Durable transactions and recovery](../STATE-AND-RECOVERY.md#5-durable-transactions-and-recovery): Snapshot activation and recovery require more than an ordinary rename.

## Captured material

Catalina 10.15 separates system content onto a read-only volume. macOS 11 adds a signed system volume: filesystem content is authenticated through a tree of hashes and a signed seal. APFS snapshots participate in startup and update recovery. A file rename on an ordinary writable volume is therefore not a complete system-patching mechanism.

On Intel T2 machines, startup includes verification of the system seal. Disabling the protection requires a separately selected security configuration; SIP state alone does not describe it. Apple describes restrictions involving FileVault and disabling SSV protection. Code signing remains a distinct control. Replacing bytes does not reproduce an Apple-authorized seal.

## Decision-relevant context

Source locator: Signed system volume security; SSV and FileVault; SSV and a Mac with an Apple T2 Security Chip. Publication date remains May 13, 2022.

SSV authenticates filesystem data with SHA-256 hashes collected into a tree whose root is the seal. The boot process checks that seal; reads verify data against it. A seal failure interrupts startup and leads to reinstallation guidance, rather than accepting altered system bytes. APFS snapshots support recovering the previous system after an unsuccessful update.

The FileVault subsection explicitly says SSV cannot be turned off while FileVault is enabled: an altered unprotected system could expose encrypted user data at the next startup. The Data volume remains encrypted under FileVault while SSV provides integrity for system content. On T2 Macs, SSV protects macOS; secure boot separately protects the T2 software that verifies it.

## Applicability and limits

The article is a security model, not a command recipe for every OS build. Hardware-specific policy and actual Recovery utilities require acceptance tests. Preserve an original bootable snapshot and external backup independently.

## Project interpretation

These mechanisms justify separate measured preconditions and pending-until-reboot activation. The aslice refusal rules, backup requirements, and Recovery acceptance matrix are additional project constraints, not guarantees that Apple supports custom system images.

## Omissions and evidence gaps

No per-build commands, successful restoration transcript, or patched-seal signing capability is supplied. This account retains the 2022 security model, not a claim that every later OS has identical controls.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
