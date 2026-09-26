# aslice man pages

This directory holds the man page sources. Status: specified interface and build workflow; generated CLI help and installation remain implementation work.

Two rules define the system:

1. **The man pages and the CLI help are one source.** `aslice help <command>` renders the same text as `man aslice-<command>`. There is no separate help text to drift out of sync — if a command's behavior changes, this file changes, and both views update together.
2. **Pages are written for people.** The reader is tired, something is broken, and the page's job is to be the shortest correct path back.

## Format and building

Pages are Markdown in pandoc's man-page dialect: a three-line `%` title block, then `NAME`, `SYNOPSIS`, `DESCRIPTION`, and the sections the page needs. Build them with:

```sh
pandoc -s -f markdown-smart -t man man/aslice-install.1.md -o share/man/man1/aslice-install.1
```

The specified aslice build will run this command for every `*.1.md` here and installs the results into the prefix's `share/man/man1/`. Disabling Pandoc's `smart` extension preserves literal `--` option prefixes and straight quotes in prose and option labels. `aslice shellenv` adds that directory to `MANPATH`. No other tooling is involved, and the source remains readable as plain Markdown on the web and in editors.

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

Database maintenance and reconstruction: [aslice-db(1)](aslice-db.1.md), including role selection, read-only inspection, coordinated backup, and confirmed restore.

## Command families

| Family page | Commands |
|---|---|
| [aslice-install(1)](aslice-install.1.md) | `install`, `reinstall` |
| [aslice-upgrade(1)](aslice-upgrade.1.md) | `upgrade`, `outdated` |
| [aslice-uninstall(1)](aslice-uninstall.1.md) | `uninstall`, `autoremove`, `mark`, `pin`, `unpin` |
| [aslice-apply(1)](aslice-apply.1.md) | `plan install`, `lock export`, `apply` |
| [aslice-adopt(1)](aslice-adopt.1.md) | `adopt --from-homebrew` |
| [aslice-graft(1)](aslice-graft.1.md) | `graft approvals`, `graft revoke` |
| [aslice-inspect(1)](aslice-inspect.1.md) | `search`, `info`, `flavors`, `leaves`, `why`, `provenance`, `audit` |
| [aslice-needs-restarting(1)](aslice-needs-restarting.1.md) | `needs-restarting` |
| [aslice-profile(1)](aslice-profile.1.md) | `history`, `rollback`, `switch-generation`, `link`, `unlink`, `profile prefer`, `exec`, `exec --replacement` |
| [aslice-use(1)](aslice-use.1.md) | `use`, `pin`, `default`, `versions`, `which` |
| [aslice-gc(1)](aslice-gc.1.md) | `gc`, `clean`, `store verify` |
| [aslice-doctor(1)](aslice-doctor.1.md) | `doctor`, `log` |
| [aslice-db(1)](aslice-db.1.md) | `db list`, `db schema`, `db query`, `db check`, `db maintain`, `db compact`, `db backup`, `db restore` |
| [aslice-recover(1)](aslice-recover.1.md) | `recover`, `operation status`, `operation stop` |
| [aslice-self-update(1)](aslice-self-update.1.md) | `self-update`, `decommission` |
| [aslice-repo(1)](aslice-repo.1.md) | `repo add`, `repo list`, `repo enable`, `repo disable`, `repo remove`, `repo re-pin`, `repo keys`, `repo audit`, `repo allow-system-patch`, `repo deny-system-patch`, `repo build`, `repo sign`, `repo publish` |
| [aslice-orchard(1)](aslice-orchard.1.md) | `orchard add`, `orchard pin`, `orchard lint`, `orchard doctor`, `orchard freshness`, `orchard ci`, `orchard dependents`, `orchard deprecate`, `orchard disable`, `orchard undeprecate`, `orchard tombstone`, `orchard rename`, `orchard port` |
| [aslice-author(1)](aslice-author.1.md) | `create`, `lint`, `build`, `test`, `livecheck`, `bump-pr` |
| [aslice-farm(1)](aslice-farm.1.md) | `farm plan`, `farm coordinator`, `farm agent`, `farm enroll` |
| [aslice-machine(1)](aslice-machine.1.md) | `machine apply`, `machine export`, `machine import` |
| [aslice-service(1)](aslice-service.1.md) | `service list`, `service status`, `service start`, `service stop`, `service restart`, `service run` |
| [aslice-ca-update(1)](aslice-ca-update.1.md) | `ca-update`, `ca-update --keychain`, `ca-update --keychain-remove`, `ca-update --crypto`, `ca-update --apple-certs`, `ca-update --from-file` |
| [aslice-system-patch(1)](aslice-system-patch.1.md) | `system-patch list`, `system-patch status`, `system-patch restore`, `system-patch prepare`, `system-patch finalize` |
| [aslice-shell(1)](aslice-shell.1.md) | `shellenv`, `init`, `config get`, `config set`, `help` |

The complete syntax index is [DESIGN §12.1](../docs/DESIGN.md#commands).
Related spellings resolve to their family page; CLI routing and installed man aliases
remain implementation work.
