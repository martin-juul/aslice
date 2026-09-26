# Homebrew 5 Release

## Source identity

- Original source: https://brew.sh/2025/11/12/homebrew-5.0.0/
- Author/publisher: Homebrew / Mike McQuaid
- Source version/date: 2025-11-12
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account plus complete upstream Markdown source asset.
- Rights: BSD-2-Clause, Homebrew contributors; [license and notice](HOMEBREW_LICENSE.txt).
- Used by: retained historical evidence; no current normative consumer.

## Captured material

Version 5 enables automatic parallel downloads by default; concurrency 1 disables them. It promotes Linux ARM64 to Tier 1 and announces Intel macOS deprecation: Tier 3 and no new CI bottles from September or later 2026, and no Intel execution from September or later 2027. It removes execution on Mojave and older. The release also describes a smaller opt-in internal API, additional bundle support, immutable releases, selective prefix relocation, and a compatibility_version formula declaration. These are dated release facts, not guarantees of future policy.

## Decision-relevant context

Source locator: Major changes and deprecations since 4.6.0; Other changes since 4.6.0, in the complete source asset.

`HOMEBREW_DOWNLOAD_CONCURRENCY=auto` enables parallel downloads by default; setting it to `1` returns to serial downloads. This concerns download scheduling, not a promise of parallel execution for every installation phase. `HOMEBREW_USE_INTERNAL_API` opts into the smaller metadata API in this release; the default changes in version 6.

The announcement schedules Intel Tier 3 and the end of new Intel bottles for September or later 2026, and removal of Intel execution for September or later 2027. It deprecates unsigned casks and quarantine-bypass flags, with Gatekeeper-failing official casks scheduled for disablement in September 2026. Bundle Go support and its opt-outs, immutable brew releases, and prefix relocation are separately listed features.

The full post records exact flags and linked implementation changes. The `compatibility_version` declaration concerns Homebrew's dependent-upgrade decisions; it is not automatically the Mach-O loader field described in Apple's library record.

## Applicability and limits

Only the facts used by this repository are captured in this original-word account. This is not a full transcript or current-version implementation guarantee.

## Project interpretation

Use the post to date release features and distinguish download concurrency from install concurrency. Its planned retirement dates should be read alongside the later Intel CI incident; retain both accounts rather than rewriting the announcement to match events.

## Omissions and evidence gaps

The source asset includes the complete post but not every linked pull request. The 4.6.0 and 5.1.0 posts are still missing independent captures.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Complete original: [HOMEBREW_5_RELEASE.source.txt](HOMEBREW_5_RELEASE.source.txt). Retrieval URL: https://raw.githubusercontent.com/Homebrew/brew.sh/master/_posts/2025-11-12-homebrew-5.0.0.md. Retrieved 2026-09-26 UTC; SHA-256: `b83b6dd0e69c47f6e5a00fd652f4def09eb538abf696cc698dbba2151d9b601a`. Branch snapshot; no immutable commit is claimed. The bytes are unmodified UTF-8 Markdown; include this asset and [HOMEBREW_LICENSE.txt](HOMEBREW_LICENSE.txt) in offline copies. Relative upstream links in the asset retain upstream meaning and are not promises of local coverage.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
