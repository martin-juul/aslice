# Apple default login shell

## Source identity

- Original source: https://support.apple.com/en-us/102360
- Author/publisher: Apple, Use zsh as the default shell on Mac
- Source version/date: published June 15, 2026
- Retrieved: 2026-09-26 UTC
- Capture type: technical account in original wording; not a complete original
- Rights: Apple retains rights in the source article. This record paraphrases the relevant technical facts; no source text or images are reproduced.
- Used by: SETUP §2.5 and §4.1, OS defaults versus account login-shell state.

## Captured material

Apple identifies bash as the default through macOS 10.14. Beginning with macOS 10.15, new user accounts default to zsh. An account can instead be configured for bash or another shell. The command-line change uses chsh with a shell path listed in /etc/shells. Terminal can separately launch a specified shell without changing the account's login shell.

## Applicability and limits

The project applies these facts to macOS 10.11–12. The article does not validate aslice's enrollment, rollback, or export implementation. This account omits unrelated profile migration and shell-script advice.

## Project interpretation

Read the actual account login-shell record when planning a change; an OS default is not evidence of that account's current choice. An unchanged selection is a no-op. Preserve the prior value for rollback under STATE-AND-RECOVERY §5. Per-OS execution tests remain required.

## Preservation

The retrieval URL and source publication date identify this technical account. Its UTF-8 bytes are covered by SHA256SUMS. No original article asset is archived or claimed here.
