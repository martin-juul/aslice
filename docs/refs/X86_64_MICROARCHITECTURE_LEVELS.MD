# X86 64 Microarchitecture Levels

## Source identity

- Original source: https://gitlab.com/x86-psABIs/x86-64-ABI/-/raw/master/x86-64-ABI/low-level-sys-info.tex
- Author/publisher: x86-64 psABI contributors
- Source version/date: master snapshot retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Original technical account; upstream text not reproduced. Upstream copyright remains with its authors.
- Used by: DESIGN platform/flavor rationale; HOMEBREW-REVIEW comparison; KEY-RUNBOOK hardware alternatives as applicable

## Captured material

The levels are cumulative. Baseline requires CMOV, CX8, FPU, FXSR, MMX, OSFXSR, SCE, SSE, SSE2. v2 adds CMPXCHG16B, LAHF-SAHF, POPCNT, SSE3, SSE4_1, SSE4_2, SSSE3. v3 adds AVX, AVX2, BMI1, BMI2, F16C, FMA, LZCNT, MOVBE, OSXSAVE. v3 availability also requires that the operating system fully enables the relevant state, including XCR0 checks using xgetbv. CPUID alone is insufficient. aslice uses these feature names for selection; Linux loader search paths and the ELF ABI are not imported into macOS. Native compilation can require features beyond these levels, which must be recorded separately.

## Applicability and limits

Only the facts used by this repository are captured in this original-word account. This is not a full transcript or current-version implementation guarantee.

## Project interpretation

The source supports the facts above. Project policy and acceptance gates remain in the linked specification; they are not attributed to the source. No successful aslice runtime test is implied by archiving this reference.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.
