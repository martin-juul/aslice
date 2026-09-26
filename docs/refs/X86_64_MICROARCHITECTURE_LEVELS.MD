# X86 64 Microarchitecture Levels

## Source identity

- Original source: https://gitlab.com/x86-psABIs/x86-64-ABI/-/raw/master/x86-64-ABI/low-level-sys-info.tex
- Author/publisher: x86-64 psABI contributors
- Source version/date: master snapshot retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [DESIGN §4.2 The µarch axis grows: three flavors](../DESIGN.md#42-the-µarch-axis-grows-three-flavors): Flavor selection checks every cumulative feature and OS-enabled AVX state.
  - [TOOLCHAIN §6. Flavors and the `-march` floor](../TOOLCHAIN.md#6-flavors-and-the--march-floor): Compiler CPU floors and native builds carry different execution requirements.

## Captured material

The levels are cumulative. Baseline requires CMOV, CX8, FPU, FXSR, MMX, OSFXSR, SCE, SSE, SSE2. v2 adds CMPXCHG16B, LAHF-SAHF, POPCNT, SSE3, SSE4_1, SSE4_2, SSSE3. v3 adds AVX, AVX2, BMI1, BMI2, F16C, FMA, LZCNT, MOVBE, OSXSAVE. v3 availability also requires that the operating system fully enables the relevant state, including XCR0 checks using xgetbv. CPUID alone is insufficient. aslice uses these feature names for selection; Linux loader search paths and the ELF ABI are not imported into macOS. Native compilation can require features beyond these levels, which must be recorded separately.

## Decision-relevant context

Source locator: low-level-sys-info.tex, Micro-Architecture Levels table and notes on operating-system support.

A level is a conjunction of requirements, not a model-name heuristic. A processor with one prominent instruction such as SSE4.2 or AVX2 can still lack another required feature or usable extended-register state. Software must consider OS support as well as hardware CPUID results before selecting an AVX-dependent level.

The source also defines v4, adding AVX512F, AVX512BW, AVX512CD, AVX512DQ, and AVX512VL to lower levels. aslice's three prebuilt flavors stop at v3; this is a project scope choice. A native build may use a different or larger feature set and cannot be labeled portable v3 merely because AVX2 is present.

## Applicability and limits

Only the facts used by this repository are captured in this original-word account. This is not a full transcript or current-version implementation guarantee.

## Project interpretation

Reuse the feature taxonomy for Mach-O package selection without importing ELF loader rules. The project still needs a detector with negative tests for missing cumulative features and disabled OS register state, plus payload-derived requirements for native builds.

## Omissions and evidence gaps

The full psABI document and its ELF calling/linking conventions are not archived. The retained account does not supply CPUID leaf/bit mappings, a complete XCR0 detector, or a verified mapping from every owned CPU to a level.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
