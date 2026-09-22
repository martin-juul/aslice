# aslice Setup — Declarative Whole-Machine Setup with `aslice-machine.toml`

- **Status:** Design draft, v0.9 — September 2026 (v0.2: editorial pass — prose revised for directness; no schema or semantic changes. v0.3: second editorial pass — sentence-level revision for readability; no schema or semantic changes. v0.4: prose rewrite throughout — chapters reworded in the project's technical-writing voice; no schema or semantic changes. v0.5: review pass — the trust-stickiness reference retargeted to REPOSITORIES.md §4; companion refreshed to DESIGN v1.14; no schema or semantic changes. v0.6: NOMENCLATURE.md vocabulary reference added to the header; companion refreshed to DESIGN v1.15; no schema or semantic changes. v0.7: companion refreshed to DESIGN v1.16; no schema or semantic changes. v0.8: companion refreshed to DESIGN v1.17; no schema or semantic changes. v0.9: the file is renamed `aslice-machine.toml` — a reserved, self-describing name that other tools can recognize — and the command surface splits by document kind: `aslice machine apply` / `export` / `import --from-brewfile` for the machine file, while top-level `aslice apply` keeps plans and lock files (owner decision, September 2026); no schema changes)
- **Companion to:** DESIGN.md v1.18 §12.13 (architecture and rationale), MANUAL.md §10 (user guide), aslice-machine(1) (command reference). This document is the schema and semantics specification.
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md) — project terms, acronyms, and the Homebrew translation table.

## 1. The scenario

Start with the situation the feature exists for. A Mac comes back from system recovery with nothing on it, and getting from *blank* to *ready to work* costs an afternoon of archaeology: install the package manager, recall which packages actually mattered, redo the Dock, redo Finder, change the shell, re-add that one repository, re-enable the services, dig up the runtime versions the projects expect. None of this knowledge is lost, exactly — it lives in the previous machine, in shell history nobody saved, in muscle memory. It is simply not written down anywhere.

`aslice-machine.toml` is where that knowledge gets written down — one declarative file:

```sh
# on a blank Mac, after the aslice installer (MANUAL §2):
aslice machine apply https://example.org/my/aslice-machine.toml      # or a local path, or ./aslice-machine.toml
```

That one command installs the packages, selects the runtime streams, enables the services, writes the Dock/Finder/etc. preferences, enrolls and sets the login shell, and configures aslice itself. Every step is planned, shown, and consented before anything changes. And because the file is plain data, it doubles as the shareable artifact: a common language for "this is how my machine is set up" that can be diffed, reviewed, and version-controlled.

There is an inverse, for the machine that already exists:

```sh
aslice machine export > aslice-machine.toml
aslice machine export --defaults com.apple.dock,com.apple.finder > aslice-machine.toml
```

## 2. The file

`aslice-machine.toml` is TOML, the same data language as `package.toml`, `aslice.toml`, `sources.toml`, and the lock file. The property that matters most is what it is not: **data, never code**. No hooks, no script blocks, no evaluated expressions. For contrast, Homebrew's Brewfile is a Ruby DSL executed by `brew bundle` — anything Ruby can do, a Brewfile can do. The setup file can execute nothing (§7), which is precisely why you can read one before you run it.

### 2.1 Schema overview

```toml
# aslice-machine.toml — declarative system setup for aslice. Apply: aslice machine apply
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

Unknown top-level keys are a hard error. The reasoning: a file written for a newer aslice must fail on an older one — fail outright, never half-apply. The `schema` key versions the document as a whole, and incompatible future changes bump it.

### 2.2 `packages`

Each entry is a name with optional decoration — an `@version` constraint, `+variant`/`-variant` flags, a `repo:` namespace — the same syntax `aslice install` accepts on the command line. Note what the file asks for, though. This is the *constraint* layer, not the *state* layer: it says "ensure ffmpeg 7", and the solver picks the exact build against the current index snapshot. If what you want is a machine reproduced bit-for-bit, that is the **lock file**'s job (`aslice lock export`; PACKAGE-FORMAT §7). The difference is `package.json` vs. `package-lock.json`, and both flow through the convergence verbs of §3.1.

Resolution follows the ordinary rules: binary-first, flavor auto-detected. One consequence of the wishlist being *reproducible*: a package that exists only as a local build is a plan error unless its repository is reachable. "Rely on something only my old disk had" is refused by construction.

### 2.3 `runtimes`

`[runtimes.default]` maps runtime names to streams, applied as `aslice default <runtime> <stream>` (DESIGN §12.9): recorded in the state DB, consumed by the shim layer. Two kinds of selection deliberately stay out of this file. Project pins (`aslice.toml` in a project tree) belong to projects — commit `aslice.toml` there. Session selections (`aslice use`) are by definition not machine setup.

### 2.4 `services`

`start` lists packages whose declared launchd services should be enabled, exactly as `aslice service start <pkg>` would enable them (DESIGN §12.8). Enabling happens after the packages install, and each generated plist binds the runtime alias selected at enable time — so a `[runtimes.default]` change in a later apply never silently moves a running service out from under you. Root-domain services (`domain = "system"`) remain trust-gated per REPOSITORIES.md §3: a file cannot enable what the repository's trust level forbids.

### 2.5 `shell`

`default` sets the user's login shell. The value is either an aslice package name (`zsh`, `fish`, `bash`) or an absolute path. Package names resolve to the **profile path** (`/opt/aslice/profiles/default/bin/zsh`), never a raw store path — deliberately, so that a generation rollback which removes the shell also moves the login shell back (§3.5).

Two facts about the OS conspire to make this a privileged operation on 10.11–12:

1. `chsh(1)` refuses any shell not listed in `/etc/shells` — a system file aslice does not otherwise touch. Enrolling an aslice shell means appending one line to `/etc/shells`. The write is performed by the `aslice-system` helper (DESIGN §10.4) under the §3.4 consent gate, recorded in the state DB, and undone if aslice added the line and the shell is later unset or uninstalled. The line is *appended*, never reordered; Apple's entries are never modified.
2. The default shell on every in-scope release is `/bin/bash`, so a `[shell]` section is almost always a real change, not a formality. Note that `chsh` itself runs unprivileged: it edits the user's own directory record and may prompt for the login password. That prompt is macOS's, not aslice's.

If the requested shell package is not installed yet, the plan installs it first; if it is not in any configured repository, the plan fails before anything changes.

### 2.6 `defaults`

macOS preference keys, written with `defaults(1)` semantics:

- **`[defaults.user."<domain>"]`** — the current user's domains (`~/Library/Preferences`). No privileges required, and no consent gate beyond the decision to apply the file at all.
- **`[defaults.system."<domain>"]`** — system-wide domains (`/Library/Preferences`). Written by `aslice-system` as root, consent-gated (§3.4), recorded, reversible (§3.5).

Schema 1 supports **string, integer, float, boolean, and arrays of those**. Deferred to a later schema version: `dict` values, `data` (raw plist blobs), `date`, and by-host (`-currentHost`) domains. Look at the deferred list and a pattern emerges — these are the types that share poorly. Opaque blobs and machine-bound settings have no place in a file meant to travel between machines (§6).

One thing to know about preferences: applications read them at launch, not continuously. So after applying, aslice tells you what to restart — for a small set of well-known system domains it names the application (`com.apple.dock` → Dock, `com.apple.finder` → Finder, `com.apple.controlcenter`/`com.apple.systemuiserver` → SystemUIServer, etc.), and for anything else it prints a generic "log out or restart the affected apps" note. It never kills processes on its own.

Writing a default for an application that is not installed yet is fine, and common: the key sits in the domain's plist until the application picks it up at first launch. Which means the ordering between `[defaults]` entries and `packages` is not the user's problem.

### 2.7 `[aslice]` and `[[repos]]`

`[aslice]` carries ordinary configuration keys (MANUAL §13) — `flavor`, `mirrors`, `gc.*`, and friends — applied exactly as `aslice config set` would apply them. The section exists so that a machine prepared for an older Mac (`flavor = "v1"`) or an offline mirror fleet can say so in the same file as everything else.

`[[repos]]` declares additional repositories. Applying one is `aslice repo add <url>`: TOFU key pinning, with its interactive confirmation (REPOSITORIES.md §7). One rule is absolute: a file **cannot elevate trust**. `verified` status comes only from the normal grant flow, never from a document. And a declared repo whose URL is already configured under another name — or whose name is configured with another URL — is a conflict error, not a silent override.

## 3. `aslice machine apply`

### 3.1 One operation, three documents

The operation predates the feature. `aslice apply` already replayed an exported lock file (`aslice apply aslice.lock`, PACKAGE-FORMAT §7) and executed a saved plan (`aslice plan install ffmpeg > plan.json && aslice apply plan.json`, DESIGN §12.1). Declarative setup is the same operation at a third fidelity — *make reality match this document* — and the spelling is split by document kind: plans and locks keep top-level `aslice apply`; the machine file gets `aslice machine apply`, so the command names what it converges:

| Document | Fidelity | What apply does |
|---|---|---|
| `plan.json` | exact, pre-resolved | execute the saved plan |
| `aslice.lock` | exact state | replay the locked profile (PACKAGE-FORMAT §7) |
| `aslice-machine.toml` | constraints + preferences | plan (resolve wishlist, diff preferences), show, confirm, execute |

The file kind is detected, never guessed: JSON is a plan, `lock_version = N` is a lock, `schema = N` with setup tables is a machine file, and anything else is an error that names what was actually found. With no argument, `aslice machine apply` reads `./aslice-machine.toml` if it exists; a machine file passed to top-level `aslice apply` is refused with a pointer here — the split is by document kind, with no overlap. The argument may also be an `https://` URL. In that case the file is fetched through the ordinary TLS stack (DESIGN §12.10), hash-printed, and planned before any consent is asked — you always review the *resolved* plan rather than trusting the URL blindly.

### 3.2 The plan and the order of operations

Every apply is a plan first. The plan is computed in full, rendered in the same format as `aslice plan` (`--json` for machines), and confirmed before anything executes. The steps run in this order, and the order is load-bearing:

1. **Validate** — schema, keys, package specs, domain syntax. Everything parses, or nothing happens.
2. **Repositories** — add declared repos (TOFU confirmation), refresh metadata.
3. **Configuration** — `[aslice]` keys.
4. **Packages** — resolve the wishlist against the current index snapshot; one generation for the whole set (DESIGN §8.3), so a failed apply never leaves a half-installed package list.
5. **Runtime selections** — the `[runtimes.default]` entries.
6. **Services** — enable declared services, verify they came up.
7. **User preferences** — the `[defaults.user]` writes.
8. **System preferences and shell** — the `[defaults.system]` writes, `/etc/shells` enrollment, `chsh` (§3.4 gate).
9. **Report** — what changed, what was already so, what needs restarting.

Why this order? Because privileges are needed only at step 8. A plan that cannot get consent still lands everything unprivileged, and reports the remainder as skipped-refused rather than failed.

### 3.3 Idempotence, convergence, and `--prune`

Apply is convergent. Run the same file twice and the second run is a no-op ("0 changes"); run it against a partially-configured machine and it does only the missing work. The default posture is additive: `aslice machine apply` never removes a package or a preference merely because the file doesn't mention it. Your machine may legitimately have more than your shared file describes, and the file makes no claim on the difference.

`aslice machine apply --prune` opts into the other direction of convergence: anything **recorded as file-managed** (§3.5) but no longer declared gets retracted — packages uninstalled (only if they are still leaves that nothing else needs), preference keys restored to their recorded pre-apply values, services disabled. Two hard limits keep this safe:

- Prune touches only file-managed records. Packages you installed by hand and keys you set by hand are invisible to it.
- Repositories are never pruned. Trust decisions are sticky by policy (REPOSITORIES.md §4), and removing a repo remains `aslice repo remove` — a deliberate act, not a side effect of editing a file.

### 3.4 Consent gates

Two parts of a setup file write to OS territory. N5 (DESIGN §2.2) forbids that in general; here it is allowed through the same declared, flagged, reversible model as `[system-patch]` (DESIGN §12.11):

- `[defaults.system.*]` — root writes to `/Library/Preferences`.
- `[shell]` enrollment — appending to `/etc/shells`.

Run interactively, each gated step prompts with what will be written and why. Run non-interactively — scripts, `--json`, pipes, the recovery-terminal scenario — gated steps are **refused** (exit 2) unless you pass `--accept-system-changes`: the same flag and the same contract as system packages and system patches (DESIGN §12.7, §12.11). `--dry-run` shows the complete plan, gated steps included, and changes nothing.

The upshot: a file fetched from someone else is safe to *plan* unconditionally. Consent is per-gate, informed, and never bundled into a blanket "trust this file".

### 3.5 Recorded inverses: preferences ride generations

Package changes are already generation-managed (DESIGN §8.3); setup extends the same discipline to everything else it touches. Before each preference write, shell change, or `/etc/shells` enrollment, the **pre-change value** (or the key's absence) is recorded in the state DB against the new generation. The payoff is in `aslice rollback`: it restores not just the profile symlinks and the lock, but the preferences and the login shell as they were. One operation, whole machine — the same way §12.11's backup discipline makes patch rollback automatic.

The same record powers `--prune` (§3.3) and `aslice history`. Every setup-applied change is attributable: which file, which apply, which generation.

### 3.6 Failure handling

If a step fails, the plan aborts at that point. The steps that completed stand — each is individually coherent: packages are one generation, preferences are individually atomic — and the report says where the plan stopped. Re-running the same file resumes by convergence, since already-done steps are no-ops. Three failure shapes are worth naming: a failed *package* resolution aborts before anything is installed; a failed service start surfaces §12.8's rollback prompt; a refused consent gate skips the gated remainder with exit 2.

## 4. `aslice machine export`

### 4.1 What it captures

`aslice machine export` writes an `aslice-machine.toml` describing the current machine to stdout — redirect it wherever you like. What gets captured:

- **Packages** — the leaves (`aslice leaves`: explicitly requested, not dependencies), with `@stream` where a stream selection matters, non-default variants as `+flags`, and non-official origins as `repo:` namespaces. Locally-built packages are included but commented out, with a note explaining why: they cannot be reproduced from a repository, and pretending otherwise is how shared files rot.
- **Runtime selections** — the profile-wide defaults (§2.3). Session variables and project pins are not machine state, so they are not exported.
- **Services** — the enabled set.
- **Login shell** — exported only when it differs from the OS default (`/bin/bash` on every in-scope release). An aslice-managed shell path maps back to its package name; a foreign path (a Homebrew-installed shell, say) is commented out with the raw path and a note.
- **Repositories** — the configured non-official repositories, name + URL. Keys are re-pinned by the applying machine through normal TOFU; exported files carry no key material.
- **Configuration** — `[aslice]` keys whose values differ from defaults.

The output is deterministic — sorted, stable formatting — so two exports diff cleanly. The file is meant for version control, and diffability is the price of admission.

### 4.2 `--defaults`: on demand, never automatic

Why are preferences not exported by default? Because packages, selections, services, and shell are *knowable* — aslice manages them, so it can enumerate them — and preferences are not. There is no baseline to diff a user's `~/Library/Preferences` against: tens of thousands of keys per machine, written by every app ever launched, most of them meaningless to reproduce. An export that "captured your current setup" by dumping domains would be mostly noise. Worse, application preference domains can contain account tokens, server addresses, recent-file lists, and internal identifiers — auto-capturing them would leak exactly what a shared file must not contain.

So `export` captures preferences only for domains the user names explicitly:

```sh
aslice machine export --defaults com.apple.dock,com.apple.finder          # user domains
aslice machine export --defaults com.apple.dock --system-defaults com.apple.loginwindow
```

Named domains are read with `defaults read` and emitted as `[defaults.user."…"]` / `[defaults.system."…"]` tables. The output carries a generated header comment naming the capture date and a standing warning: **review before sharing — application domains can contain account- or machine-specific values.** Values whose types are deferred (dict, data, date — §2.6) are emitted as comments with a note, never silently dropped.

### 4.3 What it cannot capture

This is the section where "export my setup" tools usually overpromise. The honest list:

- Application state outside `defaults` (`~/Library/Application Support`, containers, keychains) is invisible to this feature.
- Dotfiles are out of scope entirely (§8).
- Anything not knowable from aslice's own state — manually installed software, Apple-ID-signed apps, system settings made in System Settings panes that don't map to named domains you export.
- Secrets. Keychain items are never read, never written. If your workflow needs credentials, they enter the machine by a different, deliberate path.

## 5. `aslice machine import --from-brewfile`

The existing common language for Mac setup is the Brewfile; for many users it is the source of truth (HOMEBREW-REVIEW §4.6). Import is mechanical translation — no cleverness — complementing `aslice adopt --from-homebrew` (which reads the Cellar):

```sh
aslice machine import --from-brewfile Brewfile > aslice-machine.toml
```

- `brew "name"` entries become `packages` entries. Names that differ in the orchard are reported as unknown at apply time by the normal solver diagnostics.
- `tap "name"` entries become comments — aslice repositories are not Homebrew taps; add the equivalent with `[[repos]]`.
- `cask`, `mas`, and `vscode` entries are skipped with a printed list. Cask software often exists as a vendor-binary package (DESIGN §12.4) — the skip list suggests searching the orchard; Mac App Store and VS Code extension installs are out of scope (§8).

Treat the import as a starting point for hand-tuning, not a fidelity guarantee. The output says so itself, in its header comment.

## 6. Sharing setups

The file is the artifact: small, diffable, reviewable, data-only. A team can keep `aslice-machine.toml` in a repo next to its onboarding docs; a forum answer can be one file instead of forty screenshots of System Settings. And convergence makes sharing safe in both directions: applying a stranger's file never removes your extras without `--prune`, and gated steps ask you personally, every time.

Two rules keep shared files healthy:

1. **No secrets, ever.** Nothing in the schema legitimately holds a credential, and export's defaults capture warns at generation time (§4.2). Treat any token-shaped value in a shared file as a leak — because it is one.
2. **Machine-specific values stay out.** Hostnames, hardware serials, per-display layouts: the test is whether a value names *this* machine rather than *how I like machines*. If it names this machine, it does not belong in the file. The deferred by-host domains (§2.6) exist as a category partly to keep that boundary visible.

## 7. Security and trust

- **Data, not code.** No evaluation, no hooks, no shell-outs declared by the file. So the attack surface of applying a hostile file is limited to three things: installing packages (ordinary solver + trust levels), naming repositories (TOFU-pinned, never elevated), and writing preferences (user ones unprivileged, system ones consent-gated). Compare `brew bundle`, where the Brewfile is Ruby and `brew "x"` can carry arbitrary code paths.
- **Trust levels bind as usual.** A setup file cannot make a third-party repository serve root daemons, system packages, or system patches. The repository capabilities of REPOSITORIES.md §3 apply unchanged.
- **Consent is per-gate, informed, and replayable.** The plan shows every write before any happens, `--dry-run` is always available, and gated steps name their target files.
- **Attribution.** Every applied change is recorded with the file's hash and the generation that carried it (§3.5). "What did that file do to me" is always answerable, with `aslice history`.

## 8. What this is not

- **Not a dotfiles manager.** `~/.zshrc`, `~/.gitconfig`, editor configs: chezmoi, GNU Stow, and plain git already solve this problem well, and there is no prize for solving it again. aslice manages the machine's software and its `defaults` surface; your home directory's files are yours. (The shell *integration* line — `eval "$(aslice init zsh)"` — still goes in your dotfiles, by your hand.)
- **Not a system imager.** FileVault, SIP state, firmware, disk layout, user accounts, and System Settings panes without `defaults` domains are all untouched. Recovery-then-apply assumes a working macOS user account already exists.
- **Not a configuration-management fleet tool.** No agent, no daemon, no drift detection loop, no remote push. `aslice machine apply` is a command you run, on the machine, when you choose. If a fleet wants periodic enforcement, `cron` or `launchd` running `aslice machine apply` is the entire story — there is nothing else to buy.
- **Not exact reproduction.** Exact reproduction is the lock file's job (§3.1); `aslice-machine.toml` is the human layer above it.

## 9. Command reference

```
aslice machine apply [aslice-machine.toml | https://…]
                                  # converge the machine to the file (default: ./aslice-machine.toml)
  --dry-run                       # print the full plan, change nothing
  --prune                         # also retract file-managed items no longer declared (§3.3)
  --accept-system-changes         # consent to [defaults.system] and /etc/shells enrollment, non-interactive
  --json                          # machine-readable plan and report
aslice machine export             # write this machine's aslice-machine.toml to stdout
  --defaults <domain,…>           # also capture these user preference domains (§4.2)
  --system-defaults <domain,…>    # also capture these system preference domains
aslice machine import --from-brewfile <Brewfile>
                                  # translate a Brewfile into an aslice-machine.toml on stdout (§5)
```

Plans and lock files keep the top-level verb: `aslice apply plan.json` executes a saved plan (DESIGN §12.1) and `aslice apply aslice.lock` replays a locked profile (PACKAGE-FORMAT §7).

Exit status: **0** applied (or nothing to do); **1** error (schema, resolution, execution); **2** refused at a consent or trust gate. The plan is always printed before execution, and security events are logged unsuppressibly per DESIGN §12.5.
