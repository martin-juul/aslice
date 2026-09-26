% ASLICE-USE(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-use, aslice-pin, aslice-default, aslice-versions, aslice-which — select runtime streams

# SYNOPSIS

`aslice use` *runtime* *stream* [**--install**]

`aslice use` *runtime* **--clear**

`aslice pin` *runtime* *stream* [**--install**]

`aslice default` [*runtime* [*stream*]]

`aslice versions` *runtime*

`aslice which` *runtime*

# DESCRIPTION

Runtimes (php, python, ruby, nodejs) install as streams — `aslice install php@8.4` — and any number of streams coexist. Installing never changes which one you get; selection is explicit, at three levels, first match wins:

1. **Session** — `use` sets `ASLICE_USE_PHP=8.4` in the current shell. A child process cannot rewrite its parent's environment, so `use` prints the export; with the shell integration from `aslice init` it is applied for you. Dies with the shell; visible in `env`. `--clear` unsets it.
2. **Project** — `pin` writes the stream to `./aslice.toml`, found by walking up from the working directory. One file pins every runtime in the repository; commit it. Pins record streams (`8.4`), never exact patches.
3. **Default** — `default` records the profile-wide fallback; bare `default` lists all selections.

Resolution happens in a shim directory ahead of the profile on `PATH`: a shim resolves the selection and `exec`s the real binary — no wrapper process. Services and scripts that must name an exact version use versioned aliases (`php8.4`), which never move under you.

**which** traces the full resolution — which level matched, why, down to the store path. **versions** shows the matrix: installed streams, current selections, extensions per stream.

If a selected stream is not installed, interactive runs offer to install it; non-interactive runs fail with the suggestion unless **--install** is given. Uninstalling a selected stream refuses until another is selected (`--force` overrides, logged at warn).

Upgrades stay in their lane: `aslice upgrade php` moves within the selected stream only, and a stream that is selected, pinned by a known project, or referenced by an enabled service is never garbage-collected.

# NOTE ON SPELLING

`aslice pin php 8.4` (two arguments) is the project pin described here. `aslice pin openssl` (one argument) is an upgrade hold — see aslice-uninstall(1).

# FILES

**./aslice.toml**
:   Project pins, written by `aslice pin`. Commit it.

`~/.aslice/runtimes/<runtime>/<stream>/`
:   Per-stream userbases for ecosystem installers (`pip install`, `gem install`, …). User territory: aslice never audits or deletes them, and warns about orphans on uninstall.

# EXAMPLES

```sh
aslice use php 8.4
aslice use php --clear
aslice pin php 8.4
aslice default php 8.4
aslice versions php
aslice which php
```

# EXIT STATUS

The common statuses in [aslice(1)](aslice.1.md#exit-status) apply where
relevant: 0 success, 1 error or recovery required, 2 plan refused, 4 contention
without unresolved recovery, and 130 safely completed cancellation. No additional
family-specific numeric statuses are specified.

# SEE ALSO

aslice(1), aslice-install(1), [MANUAL §6](../docs/MANUAL.md#managing-runtimes-php-python-ruby-node)
