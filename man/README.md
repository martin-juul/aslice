# aslice man pages

This directory holds the man page sources. Two rules define the system:

1. **The man pages and the CLI help are one source.** `aslice help <command>` renders the same text as `man aslice-<command>`. There is no separate help text to drift out of sync — if a command's behavior changes, this file changes, and both views update together.
2. **Pages are written for people.** The reader is tired, something is broken, and the page's job is to be the shortest correct path back.

## Format and building

Pages are Markdown in pandoc's man-page dialect: a three-line `%` title block, then `NAME`, `SYNOPSIS`, `DESCRIPTION`, and the sections the page needs. Build them with:

```
pandoc -s -t man man/aslice-install.1.md -o share/man/man1/aslice-install.1
```

The aslice build does this for every `*.1.md` here and installs the results into the prefix's `share/man/man1/`, which `aslice shellenv` puts on `MANPATH`. No other tooling is involved — the source stays readable as plain Markdown on the web and in editors.

## Writing style

- **Start with what it does, then how to drive it, then the edge cases.** NAME answers "what is this" in one line; DESCRIPTION answers "why do I care" in a short paragraph before any option appears. Overview before deep dive — the same shape as the manual.
- **Options are documented, not narrated.** One entry per flag, what it changes, what it costs. No filler ("This option allows the user to…").
- **Say what a command will *not* do.** The most valuable sentences on these pages are the honest limits: "never auto-rollback," "cannot touch the OS's own stack," "there is no always-allow." If a page doesn't state its command's limits, it's unfinished.
- **Examples are realistic.** Real package names, real flags, in the order a person would type them.
- **Cross-reference aggressively.** Every related command gets a SEE ALSO entry; the manual and the design docs get cited by section where the page is a summary of deeper material.
- **Plain, direct English.** Second person is fine, imperative is better. No marketing words, no hedging, no throat-clearing. If a sentence could appear in a blog post about "streamlining workflows," it doesn't belong here.

## Conventions

- One page per user-facing command family: `aslice-use(1)` covers `use`/`pin`/`default`/`versions`/`which` because they're one mental operation.
- Overloaded spellings are called out on both pages (see `pin` in aslice-use(1) and aslice-uninstall(1)).
- Exit statuses and files get their own sections whenever they're non-obvious.
- When behavior differs between interactive and non-interactive runs, the page says so explicitly — scripts are readers too.

When you add a command, add its page in the same PR. A command without a page doesn't ship.
