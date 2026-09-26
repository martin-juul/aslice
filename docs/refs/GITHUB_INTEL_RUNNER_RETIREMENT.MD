# GitHub Intel Runner Retirement

## Source identity

- Original source: https://github.blog/changelog/2025-09-19-github-actions-macos-13-runner-image-is-closing-down/
- Author/publisher: GitHub
- Source version/date: 2025-09-19
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [DESIGN §1.1 The gap that is opening](../DESIGN.md#11-the-gap-that-is-opening): Hosted Intel runner availability has a dated endpoint.
  - [DESIGN §9.2 The GitHub CI problem](../DESIGN.md#92-the-github-ci-problem): External hosted CI cannot be the permanent legacy testing foundation.

## Captured material

GitHub announces retirement of its macOS 13 image by December 4, 2025, with scheduled brownouts preceding removal. It directs Intel users to the macOS 15 Intel image and states that macOS x86_64 support ends when that image retires in fall 2027. This concerns GitHub-hosted images, not the ability to run self-hosted Intel runners. A fixed external CI lifecycle motivates owned hardware; it does not validate the project farm.

## Decision-relevant context

Source locator: September 19, 2025 announcement: opening retirement notice, What you need to do, Notice of macOS x86_64 (Intel) architecture deprecation.

The retired labels are `macos-13`, `macos-13-large`, and `macos-13-xlarge`. Announced brownouts run from 14:00 UTC to 00:00 UTC the next day on November 4, 11, 18, and 25, 2025; affected jobs deliberately fail during those intervals. Retirement is by December 4.

The migration list separates architecture-agnostic jobs, which can use arm64 labels, from Intel jobs, including the new standard `macos-15-intel` label and available large Intel labels. The notice gives fall 2027 for retirement of macOS 15 and hosted Intel support. Moving labels can change architecture and installed tools; the announcement supplies no equivalence test for an existing workflow.

## Applicability and limits

Dated account of the relevant facts, not a full original or an implementation test.

## Project interpretation

Owned hardware avoids dependence on the hosted-image schedule, but capacity, maintenance, and guest compatibility remain project obligations. The notice is evidence of an announced lifecycle; it is not a record of an aslice run or a prohibition on self-hosted Intel runners.

## Omissions and evidence gaps

Runner-image software inventories and subsequent schedule changes are not captured. This record retains the dated announcement, not a live service-availability check.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
