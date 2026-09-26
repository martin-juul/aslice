# Apple default login shell

## Source identity

- Original source: https://support.apple.com/en-us/102360
- Author/publisher: Apple, Use zsh as the default shell on Mac
- Source version/date: published June 15, 2026
- Retrieved: 2026-09-26 UTC
- Capture type: technical account in original wording; not a complete original
- Rights: Apple retains rights in the source article. This record paraphrases the relevant technical facts; no source text or images are reproduced.
- Used by:
  - [SETUP §2.5 `shell`](../SETUP.md#25-shell): Login-shell selection is account state, distinct from the OS default.
  - [SETUP §4.1 What it captures](../SETUP.md#41-what-it-captures): Export records the actual configured shell, including an unchanged selection.
  - [STATE-AND-RECOVERY §5. Durable transactions and recovery](../STATE-AND-RECOVERY.md#5-durable-transactions-and-recovery): A changed login-shell value needs its prior value retained for rollback.

## Captured material

Apple identifies bash as the default through macOS 10.14. Beginning with macOS 10.15, new user accounts default to zsh. An account can instead be configured for bash or another shell. The command-line change uses chsh with a shell path listed in /etc/shells. Terminal can separately launch a specified shell without changing the account's login shell.

## Decision-relevant context

Source locator: How to change your default shell; How to use a different shell without changing the default.

The command form is `chsh -s path`; the eligible path comes from `/etc/shells`. Apple's examples include `/bin/bash` and `/bin/zsh`. On releases before macOS 13, the graphical route is System Preferences, Users & Groups, unlock, then the account's Advanced Options and Login shell. Terminal's General preferences can instead launch a complete command path for new windows and tabs. That Terminal setting does not change account login-shell state.

Profile files are a separate migration: `.zprofile` runs at login and `.zshrc` for interactive sessions. Selecting a shell does not translate existing bash configuration or establish script compatibility.

## Applicability and limits

The project applies these facts to macOS 10.11–12. The article does not validate aslice's enrollment, rollback, or export implementation. This account omits unrelated profile migration and shell-script advice.

## Project interpretation

Enrollment and export should compare the requested path with the account record. An unchanged selection is a no-op. A Terminal preference is insufficient evidence for changing that record. Preserve the prior value for rollback under [STATE-AND-RECOVERY §5](../STATE-AND-RECOVERY.md#durable-transactions-and-recovery). Per-OS execution tests remain required.

## Omissions and evidence gaps

Prompt customization, profile translation examples, and changing the interpreter for system shell scripts are omitted because SETUP does not authorize those migrations.

## Preservation

The retrieval URL and source publication date identify this technical account. Its UTF-8 bytes are covered by SHA256SUMS. No original article asset is archived or claimed here.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
