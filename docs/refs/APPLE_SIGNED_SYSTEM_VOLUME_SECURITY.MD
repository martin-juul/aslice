# Apple Signed System Volume Security

## Source identity

- Original source: https://support.apple.com/guide/security/secd698747c9/web
- Author/publisher: Apple
- Source version/date: Platform Security article, published 2022-05-13
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Original technical account; upstream text not reproduced. Upstream copyright remains with its authors.
- Used by: SYSTEM-VOLUMES §1–§4; STATE-AND-RECOVERY §5

## Captured material

Catalina 10.15 separates system content onto a read-only volume. macOS 11 adds a signed system volume: filesystem content is authenticated through a tree of hashes and a signed seal. APFS snapshots participate in startup and update recovery. A file rename on an ordinary writable volume is therefore not a complete system-patching mechanism.

On Intel T2 machines, startup includes verification of the system seal. Disabling the protection requires a separately selected security configuration; SIP state alone does not describe it. Apple describes restrictions involving FileVault and disabling SSV protection. Code signing remains a distinct control. Replacing bytes does not reproduce an Apple-authorized seal.

## Applicability and limits

The article is a security model, not a command recipe for every OS build. Hardware-specific policy and actual Recovery utilities require acceptance tests. Preserve an original bootable snapshot and external backup independently.

## Project interpretation

The source supports the facts above. Project policy and acceptance gates remain in the linked specification; they are not attributed to the source. No successful aslice runtime test is implied by archiving this reference.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.
