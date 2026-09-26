# Apple Writable Root Volume Discussion

## Source identity

- Original source: https://developer.apple.com/forums/thread/649832
- Author/publisher: Apple Developer Forums; individual participants, not a normative Apple specification
- Source version/date: Thread 649832; retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [SYSTEM-VOLUMES §3. Recovery-assisted application](../SYSTEM-VOLUMES.md#3-recovery-assisted-application): The base volume, boot snapshot, and next boot selection are distinct; reports alone cannot validate an adapter.

## Captured material

The discussion distinguishes the booted snapshot from the underlying System volume. Participants describe disabling authenticated-root protection in Recovery, mounting the underlying volume for changes, and creating/selecting a snapshot for a subsequent boot. They discuss snapshot tools and failures that vary with OS releases.

The relevant mechanism is a staged filesystem and boot-selection transition, rather than modifying the current immutable boot snapshot. Recovery must remain accessible if the selected snapshot fails to boot.

## Decision-relevant context

Source locator: Thread 649832, opening question and replies named below. The retrieved page exposes month/year dates; exact days and individual reply permalinks were not recovered.

In June 2020, jichi_zhang reported that the Catalina remount method failed on Big Sur with permission error 66. Apple DTS engineer Quinn suggested synthetic links and asked whether display overrides could live under `/Library`; nbelzer reported that alternative worked without disabling protection.

Sarassine proposed authenticated-root and snapshot changes in June; matripat reported failure in August. reploid first reported failure, then success after correcting the display files, and finally recommended a `/Library` approach. These are individual observations, not Apple acceptance results.

November replies by Sir_Prikol and RealNeighbour described mounting a base APFS volume and creating a boot snapshot with `bless`; failures included a misspelled filesystem type and a busy volume. jurijurka reported difficulty re-enabling FileVault. The thread therefore supplies neither a universally successful procedure nor a complete reversal path.

## Applicability and limits

Forum reports are implementation leads only. Commands quoted by participants are not validated universal instructions. No aslice adapter is accepted from this thread alone; obtain exact utility help/man pages from each target OS and retain its successful boot and restore transcript.

## Project interpretation

Prefer the writable-data alternative when the use case permits it. The project rejects inferring a volume identifier by trimming a device-name suffix, even though a participant suggests it. Preserve measured volume identities and tested recovery procedures instead.

## Omissions and evidence gaps

This is a selective thread account, not all 38 replies. Exact reply dates/permalinks and collapsed comments remain gaps. Direct HTTP returned a security-verification page; the web reader supplied the visible thread text. External display tools and social-media instructions are not captured or endorsed. The earlier generic summary remains qualified by the failures recorded here.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
