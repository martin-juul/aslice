# Apple Dynamic Library Design Guidelines

## Source identity

- Original source: https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryDesignGuidelines.html
- Author/publisher: Apple
- Source version/date: Archived Dynamic Library Programming Topics; retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Original technical account; upstream text not reproduced. Upstream copyright remains with its authors.
- Used by: DESIGN §7.3; STATE-AND-RECOVERY §2

## Captured material

A dylib has an install name, current version, and compatibility version. A linked client records the library requirement. At load time the installed library's current version is compared with the compatibility version recorded for the client. A library too old for that requirement cannot satisfy it. Runtime loading with dlopen does not supply the same version check.

Compatibility also depends on exported symbols, data layouts, signatures, and behavior. Keeping a symbol name does not prove the interface remains usable. Libraries must preserve interfaces expected by existing clients or introduce a distinct incompatible version.

## Applicability and limits

This describes Mach-O/dyld conventions, not a complete ABI proof algorithm. Test the actual supported loaders. The source does not establish libabigail support for Mach-O or the adequacy of stripped debug information.

## Project interpretation

The source supports the facts above. Project policy and acceptance gates remain in the linked specification; they are not attributed to the source. No successful aslice runtime test is implied by archiving this reference.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.
