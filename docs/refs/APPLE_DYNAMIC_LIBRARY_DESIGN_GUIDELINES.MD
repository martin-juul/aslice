# Apple Dynamic Library Design Guidelines

## Source identity

- Original source: https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryDesignGuidelines.html
- Author/publisher: Apple
- Source version/date: Archived Dynamic Library Programming Topics; retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [STATE-AND-RECOVERY §2. ABI and execution requirements](../STATE-AND-RECOVERY.md#2-abi-and-execution-requirements): A provider current version is compared with the client-recorded compatibility requirement.
  - [DESIGN §7.3 The ABI contract (the Mach-O insight)](../DESIGN.md#73-the-abi-contract-the-mach-o-insight): Exported interfaces and loader metadata provide separate ABI evidence.

## Captured material

A dylib has an install name, current version, and compatibility version. A linked client records the library requirement. At load time the installed library's current version is compared with the compatibility version recorded for the client. A library too old for that requirement cannot satisfy it. Runtime loading with dlopen does not supply the same version check.

Compatibility also depends on exported symbols, data layouts, signatures, and behavior. Keeping a symbol name does not prove the interface remains usable. Libraries must preserve interfaces expected by existing clients or introduce a distinct incompatible version.

## Decision-relevant context

Source locator: Managing Client Compatibility With Dependent Libraries; Defining Client Compatibility; Specifying Version Information; Specifying Your Library's Interface; Design Guidelines Checklist.

Apple distinguishes the library's filename/major version from its current and compatibility versions. `-current_version` records the release version; `-compatibility_version` records the oldest release suitable for clients linked against that interface. `otool -L` displays these values. A dependent library whose current version is below the client's recorded requirement aborts launch or loading; `dlopen` bypasses this particular check.

For example, if a client needs a function introduced in release 1.2, release 1.1 cannot satisfy it just because it has the same major name. Conversely, passing the version test does not establish compatible argument types, structures, or semantics. Apple's interface guidance treats changes that break existing clients differently from additive evolution.

## Applicability and limits

This describes Mach-O/dyld conventions, not a complete ABI proof algorithm. Test the actual supported loaders. The source does not establish libabigail support for Mach-O or the adequacy of stripped debug information.

## Project interpretation

Record the client requirement and both provider versions without substituting one field for another. The solver needs symbol and interface evidence in addition to these numbers; a version declaration is a producer claim, not proof of ABI equivalence.

## Omissions and evidence gaps

The chapter's complete sample library and symbol-visibility tutorial are omitted. It does not provide a Mach-O ABI-diff implementation or verify the project's proposed analysis tools.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
