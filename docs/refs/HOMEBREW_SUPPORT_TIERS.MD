# Homebrew Support Tiers

## Source identity

- Original source: https://docs.brew.sh/Support-Tiers
- Author/publisher: Homebrew project
- Source version/date: Policy snapshot retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account plus complete upstream Markdown source asset.
- Rights: BSD-2-Clause, Homebrew contributors; [license and notice](HOMEBREW_LICENSE.txt).
- Used by:
  - [DESIGN §1.1 The gap that is opening](../DESIGN.md#11-the-gap-that-is-opening): Unsupported OS/architecture configurations lose CI and support independently of execution.
  - [DESIGN — Appendix B. References](../DESIGN.md#appendix-b-references): Published tier conditions qualify the Intel schedule.

## Captured material

Homebrew distinguishes support tiers by platform and environment. Tier 3 does not provide the routine support and bottle expectations of supported configurations. Intel macOS transitions to Tier 3 in September 2026; the published schedule anticipates removal of Intel support in or after September 2027. Older macOS releases may be unsupported independently of CPU architecture.

## Decision-relevant context

Source locator: Tier 1; Tier 2; Tier 3; Future macOS support, in the complete policy snapshot.

A tier describes the whole configuration, not just its processor. Tier 1 combines supported systems, normal installation paths, current tools, tests, and bottle coverage. Tier 2 is a reduced-support condition in which CI or bottles may be incomplete and community support may be the available route. Tier 3 has no maintainer commitment to fix bugs, may regress to benefit supported systems, prints warnings, and has no CI coverage; bottles are rarely produced.

Tier 3 changes require a high standard and low continuing maintenance cost, including upstreamed fixes rather than accumulating local workarounds. The policy recommends moving to a supported configuration or another package manager. Its future macOS schedule distinguishes Intel bottle/CI withdrawal from the later removal of code needed to run on Intel.

The [CI discussion](HOMEBREW_INTEL_CI_DISCUSSION_7044.MD) records actual bottle shutdown slightly before the scheduled month. Policy and incident evidence therefore answer different questions: intended support terms versus reported operational timing.

## Applicability and limits

A support-tier policy is not proof that every command immediately stops working. Distinguish support, binary production, and execution cutoff dates.

## Project interpretation

The project targets configurations outside this support window. That choice creates its own maintenance obligation; Tier 3 does not establish automatic failure of every existing package or justify a claim that source builds are always impossible.

## Omissions and evidence gaps

The entire policy file is retained, but linked environment requirements and historical policy revisions are not. A live branch snapshot is not evidence of policy on an earlier date.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Complete original: [HOMEBREW_SUPPORT_TIERS.source.txt](HOMEBREW_SUPPORT_TIERS.source.txt). Retrieval URL: https://raw.githubusercontent.com/Homebrew/brew/main/docs/Support-Tiers.md. Retrieved 2026-09-26 UTC; SHA-256: `5905e1b47de98283e20edf31697922fb82d6f9dced20dc6e929cf587a49ee23c`. Branch snapshot; no immutable commit is claimed. The bytes are unmodified UTF-8 Markdown; include this asset and [HOMEBREW_LICENSE.txt](HOMEBREW_LICENSE.txt) in offline copies. Relative upstream links in the asset retain upstream meaning and are not promises of local coverage.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
