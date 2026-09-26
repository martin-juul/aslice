# libcxx Vendor Configuration

## Source identity

- Original source: https://libcxx.llvm.org/VendorDocumentation.html
- Author/publisher: LLVM project
- Source version/date: Live vendor documentation retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [TOOLCHAIN §5. Linkage rules](../TOOLCHAIN.md#5-linkage-rules): Runtime linkage and symbol visibility are configurable, but configuration must match headers and libraries.
  - [TOOLCHAIN §10. Genesis](../TOOLCHAIN.md#10-genesis): A bootstrap build can compile runtimes with the newly built compiler.
  - [STATE-AND-RECOVERY §10. Acceptance and implementation order](../STATE-AND-RECOVERY.md#10-acceptance-and-implementation-order): Old-OS support requires pinned build inputs and execution evidence.

## Captured material

Vendors can build libc++, libc++abi, and unwind runtimes with an installed compiler or a newly built Clang. Static and shared library production are configurable. LIBCXX_HERMETIC_STATIC_LIBRARY hides static runtime symbols when embedding the runtime in a shared library. ABI version, ABI namespace, and configuration macros must match the built runtime.

Availability markup and deployment configuration affect whether library facilities can be used on older systems. A private installation prefix avoids replacing the operating system's own libc++. Merely choosing static linkage does not prove support for every old OS or compatibility of C++ objects crossing module boundaries.

## Decision-relevant context

Source locator: The default build; The Bootstrapping build; General purpose options; ABI Specific Options; Availability Markup.

The default CMake entry is `runtimes`, with `LLVM_ENABLE_RUNTIMES` selecting libc++, libc++abi, and libunwind. The bootstrap entry is `llvm`, enabling Clang and runtime targets before building/testing/installing them. These are alternative build arrangements, not proof that the current sources accept an old Apple compiler.

`LIBCXX_ENABLE_SHARED` and `LIBCXX_ENABLE_STATIC` both default on; at least one is required. `LIBCXX_HERMETIC_STATIC_LIBRARY` defaults off and suppresses exported static-libc++ symbols when enabled. ABI version/namespace choices need matching builds. Changing corresponding header macros without rebuilding can create mismatches.

`CMAKE_INSTALL_PREFIX` selects a private installation. LLVM warns that replacing the OS copy may break the system. Availability markup constrains use of facilities absent on the deployment OS; suppressing a diagnostic cannot supply a missing runtime function.

## Applicability and limits

Pin the exact LLVM revision, build configuration, SDK, and patches before claiming support. This captured account is not a complete compiler bootstrap recipe; the required recipe and per-OS execution evidence are release gates.

## Project interpretation

A private runtime is a toolchain input whose revision, flags, headers, ABI, and deployment target must travel together. Hiding symbols limits collisions; it is not a general guarantee for C++ objects crossing independently built module boundaries.

## Omissions and evidence gaps

No pinned LLVM source checkout, full configuration recipe, SDK, compiler patches, or per-OS test logs are archived. Windows and alternative Linux ABI-provider instructions are outside the project decision.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
