# Mac Pro 2013 Compatible Operating System

## Source identity

- Original source: https://support.apple.com/en-au/102887
- Author/publisher: Apple
- Source version/date: Identify your Mac Pro; retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [TOOLCHAIN §10. Genesis](../TOOLCHAIN.md#10-genesis): Monterey is the supported OS ceiling for the proposed owned bootstrap host.
  - [BUILD-INFRA §5. Farm topology](../BUILD-INFRA.md#5-farm-topology): The late-2013 Mac Pro must be distinguished from newer models.

## Captured material

Apple lists macOS Monterey as the newest compatible operating system for the late-2013 Mac Pro. This constrains the owned machine's supported bootstrap host. It does not certify that a selected compiler, Command Line Tools release, SDK, hypervisor, or guest-image combination will work.

## Decision-relevant context

Source locator: Identify your Mac Pro, Mac Pro (Late 2013) model entry.

Apple's entry identifies the late-2013 machine as `MacPro6,1` and lists Monterey as its newest compatible operating system. The identification page separates this model from later towers; an OS maximum for a different Mac Pro cannot be applied to the cylindrical 2013 model. Model identification can be checked through About This Mac or System Information rather than relying on appearance alone.

## Applicability and limits

Record the actual machine model and installed build in bootstrap evidence. Unofficial patches that boot a newer OS are not evidence of Apple-supported compatibility.

## Project interpretation

The supported OS ceiling constrains stage0 planning on the owned machine. It leaves the compiler/CLT/SDK compatibility combination to be demonstrated; a source-compatible compiler release may still require a newer bootstrap compiler or build tool.

## Omissions and evidence gaps

Other model entries, serial-number lookup assets, and photographs are omitted. The page supplies no CPU instruction-set inventory, hypervisor matrix, or successful aslice bootstrap.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
