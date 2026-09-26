# libcxx Vendor Configuration

## Source identity

- Original source: https://libcxx.llvm.org/VendorDocumentation.html
- Author/publisher: LLVM project
- Source version/date: Live vendor documentation retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Original technical account; upstream text not reproduced. Upstream copyright remains with its authors.
- Used by: TOOLCHAIN §5 and §10; STATE-AND-RECOVERY §10

## Captured material

Vendors can build libc++, libc++abi, and unwind runtimes with an installed compiler or a newly built Clang. Static and shared library production are configurable. LIBCXX_HERMETIC_STATIC_LIBRARY hides static runtime symbols when embedding the runtime in a shared library. ABI version, ABI namespace, and configuration macros must match the built runtime.

Availability markup and deployment configuration affect whether library facilities can be used on older systems. A private installation prefix avoids replacing the operating system's own libc++. Merely choosing static linkage does not prove support for every old OS or compatibility of C++ objects crossing module boundaries.

## Applicability and limits

Pin the exact LLVM revision, build configuration, SDK, and patches before claiming support. This captured account is not a complete compiler bootstrap recipe; the required recipe and per-OS execution evidence are release gates.

## Project interpretation

The source supports the facts above. Project policy and acceptance gates remain in the linked specification; they are not attributed to the source. No successful aslice runtime test is implied by archiving this reference.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.
