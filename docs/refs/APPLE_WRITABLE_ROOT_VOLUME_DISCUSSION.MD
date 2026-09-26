# Apple Writable Root Volume Discussion

## Source identity

- Original source: https://developer.apple.com/forums/thread/649832
- Author/publisher: Apple Developer Forums; individual participants, not a normative Apple specification
- Source version/date: Thread 649832; retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Original technical account; upstream text not reproduced. Upstream copyright remains with its authors.
- Used by: SYSTEM-VOLUMES §3

## Captured material

The discussion distinguishes the booted snapshot from the underlying System volume. Participants describe disabling authenticated-root protection in Recovery, mounting the underlying volume for changes, and creating/selecting a snapshot for a subsequent boot. They discuss snapshot tools and failures that vary with OS releases.

The relevant mechanism is a staged filesystem and boot-selection transition, rather than modifying the current immutable boot snapshot. Recovery must remain accessible if the selected snapshot fails to boot.

## Applicability and limits

Forum reports are implementation leads only. Commands quoted by participants are not validated universal instructions. No aslice adapter is accepted from this thread alone; obtain exact utility help/man pages from each target OS and retain its successful boot and restore transcript.

## Project interpretation

The source supports the facts above. Project policy and acceptance gates remain in the linked specification; they are not attributed to the source. No successful aslice runtime test is implied by archiving this reference.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.
