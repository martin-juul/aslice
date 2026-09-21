# aslice Setup — Declarative Whole-Machine Setup with `setup.toml`

- **Status:** Design draft, v0.3 — September 2026 (v0.2: editorial pass — prose revised for directness; no schema or semantic changes. v0.3: second editorial pass — sentence-level revision for readability; no schema or semantic changes)
- **Companion to:** DESIGN.md v1.12 §12.13 (architecture and rationale), MANUAL.md §10 (user guide), aslice-apply(1) (command reference). This document is the schema and semantics specification.

## 1. The scenario

A Mac comes back from system recovery blank. Today, getting from *blank* to *ready to work* is an afternoon of remembering: install the package manager, remember which packages mattered, redo the Dock, redo Finder, change the shell, re-add that one repository, re-enable the services, rediscover the runtime versions the projects expect. The knowledge exists — in the previous machine, in shell history nobody saved, in muscle memory.

`setup.toml` moves that knowledge into one declarative file:

```sh
# on a blank Mac, after the aslice installer (MANUAL §2):
aslice apply https://example.org/my/setup.toml      # or a local path, or ./setup.toml
```

One command installs the packages, selects the runtime streams, enables the services, writes the Dock/Finder/etc. preferences, enrolls and sets the login shell, and configures aslice itself — each step planned, shown, and consented before anything changes. Because the file is plain data, it is also the shareable artifact: a common language for "this is how my machine is set up" that can be diffed, reviewed, and version-controlled.

The inverse command captures a machine that already exists:

```sh
aslice export > setup.toml
aslice export --defaults com.apple.dock,com.apple.finder > setup.toml
```

## 2. The file

`setup.toml` is TOML — the same data language as `package.toml`, `aslice.toml`, `sources.toml`, and the lock file. It is **data, never code**: there are no hooks, no script blocks, no evaluated expressions. (Homebrew's Brewfile is a Ruby DSL executed by `brew bundle`; anything Ruby can do, a Brewfile can do. aslice's setup file cannot execute anything — §7.)

### 2.1 Schema overview

```toml
# setup.toml — declarative system setup for aslice. Apply: aslice apply setup.toml
schema = 1                     # required; unknown schema versions are a hard error

[aslice]                       # optional: aslice's own configuration (MANUAL §13)
flavor = "v3"                  # any key from the configuration reference is allowed

[[repos]]                      # optional: repositories beyond the pre-pinned official one
name = "audiolab"
url  = "https://repo.example.org"

packages = [                   # the wishlist: constraints, not exact state
  "ffmpeg@7",                  #   version constraint (§12.1 syntax)
  "postgresql +ssl",           #   variants
  "audiolab:convolver",        #   repository-namespaced (REPOSITORIES.md)
]

[runtimes.default]             # profile-wide runtime stream selections (DESIGN §12.9)
php    = "8.4"
python = "3.12"

[services]                     # launchd services to enable (DESIGN §12.8)
start = ["postgresql", "redis"]

[shell]
default = "zsh"                # login shell; package names resolve through the profile (§2.5)

[defaults.user."com.apple.dock"]      # current-user preferences — no privileges
autohide = true
tilesize = 48

[defaults.user."com.apple.finder"]
ShowPathbar   = true
FXPreferredViewStyle = "Nlsv"

[defaults.system."com.apple.loginwindow"]   # /Library/Preferences — consent-gated (§3.4)
# …
```

Unknown top-level keys are a hard error: a file written for a newer aslice must fail on an older one, never half-apply. The `schema` key versions the whole document; incompatible future changes bump it.

### 2.2 `packages`

The wishlist: name, optional `@version` constraint, optional `+variant`/`-variant` flags, optional `repo:` namespace — the same syntax `aslice install` accepts. This is the *constraint* layer, not the *state* layer: the file says "ensure ffmpeg 7", and the solver picks the exact build against the current index snapshot. For exact reproduction of a machine bit-for-bit, that is what the **lock file** is for (`aslice lock export`; PACKAGE-FORMAT §7) — the difference is `package.json` vs. `package-lock.json`, and both flow through the same verb (§3.1).

Packages are resolved binary-first with flavor auto-detection, per the ordinary rules. A package that exists only as a local build is a plan error unless its repository is reachable — the file is a *reproducible* wishlist, so "rely on something only my old disk had" is refused by construction.

### 2.3 `runtimes`

`[runtimes.default]` maps runtime names to streams and is applied as `aslice default <runtime> <stream>` (DESIGN §12.9): recorded in the state DB, consumed by the shim layer. Project pins (`aslice.toml` in a project tree) and session selections (`aslice use`) are not part of this file: project pins belong to projects (commit `aslice.toml` there), and session state is by definition not machine setup.

### 2.4 `services`

`start` lists packages whose declared launchd services are enabled, as `aslice service start <pkg>` would do (DESIGN §12.8). Services are enabled after their packages install, and each generated plist binds the runtime alias selected at enable time — so a `[runtimes.default]` change in a later apply never silently moves a running service. Root-domain services (`domain = "system"`) remain trust-gated per REPOSITORIES.md §3: a file cannot enable what the repository's trust level forbids.

### 2.5 `shell`

`default` sets the user's login shell. The value is an aslice package name (`zsh`, `fish`, `bash`) or an absolute path; package names resolve to the **profile path** (`/opt/aslice/profiles/default/bin/zsh`), never a raw store path, so a generation rollback that removes the shell also moves the login shell back (§3.5).

Two OS facts make this a privileged operation on 10.11–12:

1. `chsh(1)` refuses any shell not listed in `/etc/shells` — a system file aslice does not otherwise touch. Enrolling an aslice shell appends one line to `/etc/shells`, executed by the `aslice-system` helper (DESIGN §10.4) under the §3.4 consent gate, recorded in the state DB, and removed again if aslice added it and the shell is unset or uninstalled. The line is *appended*, never reordered; Apple's entries are never modified.
2. The default shell on every in-scope release is `/bin/bash`, so a `[shell]` section is almost always a real change. `chsh` itself runs unprivileged (it edits the user's own directory record and may prompt for the login password — that prompt is macOS's, not aslice's).

If the requested shell package is not installed, the plan installs it first; if it is not in any configured repository, the plan fails before anything changes.

### 2.6 `defaults`

macOS preference keys, written with `defaults(1)` semantics:

- **`[defaults.user."<domain>"]`** — the current user's domains (`~/Library/Preferences`). No privileges required, no consent gate beyond applying the file at all.
- **`[defaults.system."<domain>"]`** — system-wide domains (`/Library/Preferences`). Written by `aslice-system` as root, consent-gated (§3.4), recorded, reversible (§3.5).

Value types in schema 1: **string, integer, float, boolean, and arrays of those**. Deferred to a later schema version: `dict` values, `data` (raw plist blobs), `date`, and by-host (`-currentHost`) domains. The deferred types are the ones that share poorly — opaque blobs and machine-bound settings have no place in a file meant to travel between machines (§6).

Preferences are read by applications at launch, not continuously. After applying, aslice prints the affected applications worth restarting for a small set of well-known system domains (`com.apple.dock` → Dock, `com.apple.finder` → Finder, `com.apple.controlcenter`/`com.apple.systemuiserver` → SystemUIServer, etc.) and a generic "log out or restart the affected apps" note otherwise. It never kills processes on its own.

Writing a default for an application that is not installed yet is fine and common: the key sits in the domain's plist and the application picks it up at first launch. Ordering between `[defaults]` entries and `packages` is therefore not the user's problem.

### 2.7 `[aslice]` and `[[repos]]`

`[aslice]` carries ordinary configuration keys (MANUAL §13) — `flavor`, `mirrors`, `gc.*`, and friends — applied as `aslice config set` would. It exists so a machine prepared for an older Mac (`flavor = "v1"`) or an offline mirror fleet can say so in the same file.

`[[repos]]` declares additional repositories. Applying one is `aslice repo add <url>`: TOFU key pinning with its interactive confirmation (REPOSITORIES.md §7). A file **cannot elevate trust**: `verified` status comes only from the normal grant flow, never from a document. A declared repo whose URL is already configured under another name — or whose name is configured with another URL — is a conflict error, not a silent override.

## 3. `aslice apply`

### 3.1 One verb, three documents

`aslice apply` already existed before this feature: it replays an exported lock file (`aslice apply aslice.lock`, PACKAGE-FORMAT §7) and executes a saved plan (`aslice plan install ffmpeg > plan.json && aslice apply plan.json`, DESIGN §12.1). Declarative setup is the same operation at a third fidelity — *make reality match this document* — so it is the same verb:

| Document | Fidelity | What apply does |
|---|---|---|
| `plan.json` | exact, pre-resolved | execute the saved plan |
| `aslice.lock` | exact state | replay the locked profile (PACKAGE-FORMAT §7) |
| `setup.toml` | constraints + preferences | plan (resolve wishlist, diff preferences), show, confirm, execute |

The file kind is detected, never guessed: JSON is a plan, `lock_version = N` is a lock, `schema = N` with setup tables is a setup file; anything else is an error naming what was found. With no argument, `aslice apply` reads `./setup.toml` if it exists. The argument may also be an `https://` URL — fetched through the ordinary TLS stack (DESIGN §12.10), hash-printed, and planned before any consent is asked, so the user always reviews the *resolved* plan rather than trusting the URL blindly.

### 3.2 The plan and the order of operations

Every apply is a plan first. The plan is computed in full, rendered in the same format as `aslice plan` (`--json` for machines), and confirmed before execution. Ordering inside the plan:

1. **Validate** — schema, keys, package specs, domain syntax. Everything parseable or nothing happens.
2. **Repositories** — add declared repos (TOFU confirmation), refresh metadata.
3. **Configuration** — `[aslice]` keys.
4. **Packages** — resolve the wishlist against the current index snapshot; one generation for the whole set (DESIGN §8.3), so a failed apply never leaves a half-installed package list.
5. **Runtime selections** — `[runtimes.default]` entries.
6. **Services** — enable declared services, verify they came up.
7. **User preferences** — `[defaults.user]` writes.
8. **System preferences and shell** — `[defaults.system]` writes, `/etc/shells` enrollment, `chsh` (§3.4 gate).
9. **Report** — what changed, what was already so, what to restart.

The order matters: privileges are needed only at step 8, so a plan that cannot get consent still lands everything unprivileged and reports the remainder as skipped-refused, not failed.

### 3.3 Idempotence, convergence, and `--prune`

Apply is convergent: applying the same file twice is a no-op ("0 changes"), and applying it to a partially-configured machine does only the missing work. Assertions are additive by default — `aslice apply` never removes a package or a preference merely because the file doesn't mention it (your machine may legitimately have more than your shared file describes).

`aslice apply --prune` is the opt-in convergence direction: anything **recorded as file-managed** (§3.5) but no longer declared is retracted — packages uninstalled (only if still leaves that nothing else needs), preference keys restored to their recorded pre-apply values, services disabled. Two hard limits:

- Prune touches only file-managed records. Packages you installed by hand, keys you set by hand, are invisible to it.
- Repositories are never pruned. Trust decisions are sticky by policy (REPOSITORIES.md §10); removing a repo is `aslice repo remove`, a deliberate act.

### 3.4 Consent gates

Two parts of a setup file write to OS territory — otherwise forbidden by N5 (DESIGN §2.2), here allowed through the same declared, flagged, reversible model as `[system-patch]` (DESIGN §12.11):

- `[defaults.system.*]` — root writes to `/Library/Preferences`.
- `[shell]` enrollment — appending to `/etc/shells`.

Interactively, each gated step is prompted with what will be written and why. Non-interactively — scripts, `--json`, pipes, the recovery-terminal scenario — gated steps are **refused** (exit 2) unless `--accept-system-changes` is passed, the same flag and the same contract as system packages and system patches (DESIGN §12.7, §12.11). `--dry-run` shows the complete plan including gated steps, changing nothing.

A file fetched from someone else is therefore safe to *plan* unconditionally: consent is per-gated-step, informed, and never bundled into "trust this file".

### 3.5 Recorded inverses: preferences ride generations

Package changes are already generation-managed (DESIGN §8.3). Setup extends the same discipline to everything else it touches: before each preference write, shell change, or `/etc/shells` enrollment, the **pre-change value** (or the key's absence) is recorded in the state DB against the new generation. `aslice rollback` then restores not just the profile symlinks and the lock, but the preferences and login shell as they were — one operation, whole machine — the same way §12.11's backup discipline makes patch rollback automatic.

The record is also what powers `--prune` (§3.3) and `aslice history`: every setup-applied change is attributable — which file, which apply, which generation.

### 3.6 Failure handling

A failed step aborts the plan at that point; completed earlier steps stand (they are each coherent: packages are one generation, preferences are individually atomic), and the report says where the plan stopped. Re-running the same file resumes by convergence — already-done steps are no-ops. A failed *package* resolution aborts before anything is installed; a failed service start surfaces §12.8's rollback prompt; a refused consent gate skips the gated remainder with exit 2.

## 4. `aslice export`

### 4.1 What it captures

`aslice export` writes a `setup.toml` for the current machine to stdout (redirect to taste). Captured:

- **Packages** — the leaves (`aslice leaves`: explicitly requested, not dependencies), with `@stream` where a stream selection matters, non-default variants as `+flags`, and non-official origins as `repo:` namespaces. Locally-built packages are included but commented out with a note — they cannot be reproduced from a repository, and pretending otherwise is how shared files rot.
- **Runtime selections** — the profile-wide defaults (§2.3). Session variables and project pins are not machine state and are not exported.
- **Services** — the enabled set.
- **Login shell** — exported only if it differs from the OS default (`/bin/bash` on every in-scope release). An aslice-managed shell path maps back to its package name; a foreign path (e.g. a Homebrew-installed shell) is commented out with the raw path and a note.
- **Repositories** — configured non-official repositories, name + URL. Keys are re-pinned by the applying machine through normal TOFU; exported files carry no key material.
- **Configuration** — `[aslice]` keys whose values differ from defaults.

The output is deterministic (sorted, stable formatting) so two exports diff cleanly — the file is meant for version control.

### 4.2 `--defaults`: on demand, never automatic

Packages, selections, services, and shell are *knowable*: aslice manages them, so it can enumerate them. Preferences are not. There is no baseline to diff a user's `~/Library/Preferences` against — tens of thousands of keys per machine, written by every app ever launched, most of them meaningless to reproduce. An export that "captures your current setup" by dumping domains would be mostly noise, and worse: application preference domains can contain account tokens, server addresses, recent-file lists, and internal identifiers. Auto-capturing them would leak what a shared file must not contain.

So `export` captures preferences only for domains the user names:

```sh
aslice export --defaults com.apple.dock,com.apple.finder          # user domains
aslice export --defaults com.apple.dock --system-defaults com.apple.loginwindow
```

Named domains are read with `defaults read` and emitted as `[defaults.user."…"]` / `[defaults.system."…"]` tables, with a generated header comment naming the capture date and a standing warning: **review before sharing — application domains can contain account- or machine-specific values.** Values of deferred types (dict, data, date — §2.6) are emitted as comments with a note, never silently dropped.

### 4.3 What it cannot capture

This is where "export my setup" usually overpromises:

- Application state outside `defaults` (`~/Library/Application Support`, containers, keychains) is invisible to this feature.
- Dotfiles are out of scope entirely (§8).
- Anything not knowable from aslice's own state — manually installed software, Apple-ID-signed apps, system settings made in System Settings panes that don't map to named domains you export.
- Secrets. Keychain items are never read, never written. If your workflow needs credentials, they enter the machine by a different, deliberate path.

## 5. `aslice import --from-brewfile`

The existing common language for Mac setup is the Brewfile, and many users' source of truth is one (HOMEBREW-REVIEW §4.6). Import is mechanical translation, complementing `aslice adopt --from-homebrew` (which reads the Cellar):

```sh
aslice import --from-brewfile Brewfile > setup.toml
```

- `brew "name"` entries become `packages` entries. Names that differ in the orchard are reported as unknown at apply time by the normal solver diagnostics.
- `tap "name"` entries become comments — aslice repositories are not Homebrew taps; add the equivalent with `[[repos]]`.
- `cask`, `mas`, and `vscode` entries are skipped with a printed list. Cask software often exists as a vendor-binary package (DESIGN §12.4) — the skip list suggests searching the orchard; Mac App Store and VS Code extension installs are out of scope (§8).

Import is a starting point for hand-tuning, not a fidelity guarantee; the output says so in its header comment.

## 6. Sharing setups

The file is the artifact: small, diffable, reviewable, data-only. A team can keep `setup.toml` in a repo next to onboarding docs; a forum post can be one file instead of forty screenshots of System Settings. Convergence makes sharing safe in both directions — applying a stranger's file never removes your extras without `--prune`, and gated steps ask you personally, every time.

Two rules keep shared files healthy:

1. **No secrets, ever.** There is nothing in the schema that legitimately holds a credential; export's defaults capture warns at generation time (§4.2). Treat any token-shaped value in a shared file as a leak.
2. **Machine-specific values stay out.** Hostnames, hardware serials, per-display layouts: if a value names *this* machine rather than *how I like machines*, it does not belong in the file. The deferred by-host domains (§2.6) exist as a category partly so the boundary stays clear.

## 7. Security and trust

- **Data, not code.** No evaluation, no hooks, no shell-outs declared by the file. The attack surface of applying a hostile file is limited to: installing packages (ordinary solver + trust levels), naming repositories (TOFU-pinned, never elevated), and writing preferences (user ones unprivileged, system ones consent-gated). Compare `brew bundle`, where the Brewfile is Ruby and `brew "x"` can carry arbitrary code paths.
- **Trust levels bind as usual.** A setup file cannot make a third-party repository serve root daemons, system packages, or system patches; the repository capabilities of REPOSITORIES.md §3 apply unchanged.
- **Consent is per-gate, informed, and replayable.** The plan shows every write before any happens; `--dry-run` is always available; gated steps name their target files.
- **Attribution.** Every applied change is recorded with the file's hash and the generation that carried it (§3.5), so "what did that file do to me" is always answerable with `aslice history`.

## 8. What this is not

- **Not a dotfiles manager.** `~/.zshrc`, `~/.gitconfig`, editor configs: chezmoi, GNU Stow, and plain git already solve this well. aslice manages the machine's software and its `defaults` surface; your home directory's files are yours. (The shell *integration* line — `eval "$(aslice init zsh)"` — still goes in your dotfiles by your hand.)
- **Not a system imager.** FileVault, SIP state, firmware, disk layout, user accounts, and System Settings panes without `defaults` domains are untouched. Recovery-then-apply assumes a working macOS user account already exists.
- **Not a configuration-management fleet tool.** No agent, no daemon, no drift detection loop, no remote push. `aslice apply` is a command you run, on the machine, when you choose. If a fleet wants periodic enforcement, `cron`/`launchd` running `aslice apply` is the entire story.
- **Not exact reproduction.** Exact reproduction is the lock file's job (§3.1). `setup.toml` is the human layer above it.

## 9. Command reference

```
aslice apply [setup.toml | aslice.lock | plan.json | https://…]
                                  # converge the machine to the document (default: ./setup.toml)
  --dry-run                       # print the full plan, change nothing
  --prune                         # also retract file-managed items no longer declared (§3.3)
  --accept-system-changes         # consent to [defaults.system] and /etc/shells enrollment, non-interactive
  --json                          # machine-readable plan and report
aslice export                     # write this machine's setup.toml to stdout
  --defaults <domain,…>           # also capture these user preference domains (§4.2)
  --system-defaults <domain,…>    # also capture these system preference domains
aslice import --from-brewfile <Brewfile>
                                  # translate a Brewfile into a setup.toml on stdout (§5)
```

Exit status: **0** applied (or nothing to do); **1** error (schema, resolution, execution); **2** refused at a consent or trust gate. The plan is always printed before execution; security events are logged unsuppressibly per DESIGN §12.5.
