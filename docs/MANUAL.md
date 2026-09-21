# aslice Manual

**The user guide for aslice — a package manager for Intel macOS.**

- **Status:** v0.8 — September 2026 (v0.2: review corrections — §2.3 covers bash alongside zsh, §2.5 lists the three outside-prefix exceptions to a clean removal instead of claiming none exist, §3's man-page claim is softened to what actually ships, §3.1 documents `link`/`unlink` for `link = false` packages, and §7.1's root-daemon gate includes local repositories. v0.3: new chapter 10 — declarative whole-machine setup with `setup.toml`, `aslice apply`, `aslice export`, and `aslice import --from-brewfile` (SETUP.md); chapters 10–13 renumber to 11–14. v0.4: editorial pass — prose revised for directness throughout; no factual or behavioral changes. v0.5: second editorial pass — sentence-level revision for readability; no factual or behavioral changes. v0.6: prose rewrite throughout — chapters reworded in the project's technical-writing voice; no factual or behavioral changes. v0.7: review pass — the lock-file pointer in §10.2 now cites PACKAGE-FORMAT §7; no factual or behavioral changes. v0.8: NOMENCLATURE.md vocabulary reference added to the header; no factual or behavioral changes)
- **Audience:** people who install and run software with aslice; that is most of what follows. If you *write* packages, read chapters 1–4 and then move to [AUTHORING.md](AUTHORING.md). If you want to know *why* things are the way they are, the rationale lives in [DESIGN.md](DESIGN.md).
- **Companions:** the man pages in [man/](../man/) (also available as `aslice help <command>`), [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md), [ORCHARD-POLICY.md](ORCHARD-POLICY.md), [REPOSITORIES.md](REPOSITORIES.md), [GENESIS.md](GENESIS.md).
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md) — project terms, acronyms, and the Homebrew translation table.

---

## 1. Overview

aslice is a package manager for Intel Macs running macOS 10.11 (El Capitan) through 12 (Monterey). It exists because Homebrew is leaving this platform: no new Intel bottles, no CI, and an announced date for dropping Intel entirely. The machines are still good. The software pipeline is what's disappearing, so this project rebuilds it.

Three facts about aslice explain almost everything else:

**It installs binaries, and it never runs them at install time.** Packages arrive as *slices* — prebuilt, signed, compressed archives. To install one, aslice verifies the signature, checks every file against the manifest, and links the result into place. At no point does the package get to run a script on your machine. Homebrew's `post_install` has no equivalent here, and never will.

**Old states of your system are kept, and you can go back to them.** Installed packages live in an immutable store; what you actually use is a *generation*, a view of the store made of symlinks. Every install, upgrade, or uninstall builds a new generation and then flips a single symlink. When an upgrade breaks something, `aslice rollback` puts the old state back in seconds. Nix proved this idea at scale; aslice keeps it small enough to stay understandable.

**It accounts for old machines.** aslice detects your CPU and serves the fastest build that CPU can execute; there are three *flavors* — baseline, SSE4.2, and AVX2. It ships a current CA certificate bundle, because the one in your OS expired years ago. And when it cannot do something — a package needs SIP disabled, a vendor binary can't be redistributed, Safari's TLS stack is too old for a site no matter what it installs — it tells you so, instead of failing mysteriously later.

Finally, a fact about the project rather than the software: **aslice collects nothing.** No telemetry, no analytics, no install IDs, no crash reporting — not even opt-in. There is no switch to turn off because there is no wiring. It is infrastructure, not a product.

### 1.1 The vocabulary

The project uses its own words, partly to avoid confusion with Homebrew's beer terms:

| Term | What it is |
|---|---|
| **slice** | A binary package: a signed archive plus a manifest describing its contents |
| **orchard** | A git repository of package recipes (*formulae*) — the authoring format |
| **repository** | A compiled, signed, static tree of formulae and slices — the distribution format |
| **formula** | One package's recipe: a `package.toml` (data) and a `build.star` (build script) |
| **flavor** | Which x86-64 level a slice is built for: `v1` (baseline), `v2` (SSE4.2), `v3` (AVX2) |
| **store** | `/opt/aslice/store/` — every installed package version, immutable, side by side |
| **generation** | One complete state of your installed software; switching is atomic |
| **profile** | The symlink forest (`bin/`, `lib/`, …) that points into the current generation |

These words appear in every message aslice prints, so they are worth learning once.

### 1.2 The five-minute mental model

1. The **store** holds every version of every package you've installed, each in its own directory. Nothing inside it ever changes after registration.
2. Your **generation** is a directory of symlinks into the store, and it is what your `PATH` actually points at.
3. Installing or upgrading builds a *new* generation and then swaps one symlink. The old generation is untouched, which is why rollback is instant and a crash mid-install breaks nothing.
4. Packages are **binary by default**. Source builds happen only when you ask for non-default variants or custom compiler flags, and even then the result interoperates with the prebuilt world: compatibility is checked against the libraries' actual interfaces, not their provenance.
5. Everything aslice fetches — slices, index metadata, the CA bundle, aslice itself — is signed and hash-pinned. A verification failure blocks the operation and is always reported; it cannot be silenced.

If you remember store + generations + signed everything, the rest of this manual is details.

---

## 2. Installing aslice

### 2.1 What you need

- An Intel Mac (2007 or later, 64-bit — every Mac that runs these releases qualifies) running macOS 10.11 through 12.
- A few hundred megabytes of disk for the toolchain and the core packages, plus room to grow. Because the store keeps old generations, plan on gigabytes if you install a lot.
- An internet connection for the install itself. Afterwards, aslice works offline against its cache and degrades gracefully (§9.5).

You do **not** need Xcode or the Command Line Tools. aslice brings its own toolchain.

### 2.2 The installer

The installer is a short shell script — short enough to read before running, which you should do:

```
curl -O https://get.aslice.sh/install.sh
less install.sh          # it's about 200 lines; read it
sh install.sh
```

The script fetches two things: the aslice bootstrap binary, and the root of aslice's update metadata. Both are pinned by hash inside the script and cross-checked against a signed checksums file served over a second, independent transport; everything after that first step is verified by aslice's own update framework. It does not ask for your password, with one optional exception — it offers to run `sudo` once, to create `/opt/aslice` and hand it to your user account. Say no if you'd rather not (or don't have admin rights), and it installs to `~/.aslice` instead. The two layouts are fully supported and behave identically; only the path differs.

**If your Mac's TLS is too old for the modern web** — the day-one condition of a frozen OS — the script may be unable to complete an HTTPS handshake at all. This is expected. The installer detects the failure and retries over plain HTTP, fetching *the same hash-pinned files* and verifying them against the same pins and signatures, with a prominent banner announcing the downgrade and why it is safe. What you are trusting is the hashes and signatures; for this download, HTTPS was only ever a privacy layer.

### 2.3 After the install

Add aslice to your shell. For zsh (the default since Catalina):

```
eval "$(/opt/aslice/bin/aslice init zsh)"     # or ~/.aslice/bin/aslice for a per-user install
```

For bash (the default on 10.11–10.14):

```
eval "$(/opt/aslice/bin/aslice init bash)"    # same per-user path applies
```

To make it permanent, add that line to your `~/.zshrc` or `~/.bash_profile`. Then verify:

```
aslice doctor
```

`doctor` runs a battery of checks — CPU flavor, store integrity, repository freshness, trust-store state — and prints either a one-line "healthy" or a list of findings, each paired with the command that fixes it. On a fresh install of an old OS it will usually have one suggestion: `aslice ca-update`. Run it. The short version of what that does: it replaces your OS's long-expired certificate trust store with a current one, so `curl`, `git`, and `python` can talk to the modern web. Chapter 8 gives the long version.

### 2.4 Updating aslice itself

aslice updates itself like any other package:

```
aslice self-update
```

The update is signed and verified like any package, installed as a new generation, and health-checked after the swap — if the new binary fails its own smoke test, aslice rolls itself back automatically. `aslice self-update --check` reports without installing, and `aslice pin aslice` holds the manager in place if you never want it to move.

### 2.5 Removing aslice

```
aslice uninstall aslice        # removes the manager's registration
sudo rm -rf /opt/aslice        # or rm -rf ~/.aslice — this is the whole footprint
```

aslice keeps everything inside its prefix — `/opt/aslice/apps/` included — with three declared exceptions, and each should be closed out before removal. If you installed a `[system-patch]` package, restore the Apple originals first: `aslice system-patch list` shows what is patched, and `aslice system-patch restore <path>` puts each byte-exact original back (§8.4). If you installed a `[system]` package (kernel extensions, SIP-disabled development tools), uninstall it first. If you used `ca-update --keychain`, run `aslice ca-update --keychain-remove`: it deletes exactly the certificates aslice imported into the System keychain, each one recorded at import time, and nothing else. Once those are closed out, deleting the prefix removes everything else completely.

---

## 3. Everyday commands

This chapter covers the dozen commands that make up daily use. Each command family has its own man page — `man aslice-repo`, `man aslice-service`, `man aslice-system-patch`, and so on, all indexed on `man aslice` — and `aslice help <command>` prints the same text in your terminal.

### 3.1 Finding and installing software

```
aslice search ffmpeg          # names and descriptions matching "ffmpeg"
aslice info ffmpeg            # versions, variants, dependencies, size, provenance
aslice install ffmpeg
```

`install` is binary-first. It resolves your request against the index, picks the newest version that runs on your OS release and the fastest flavor your CPU executes, downloads the slices, verifies them, and links a new generation. A typical run prints the plan, then the result:

```
$ aslice install ffmpeg
==> Plan: install ffmpeg 7.1 (v3, 14.2 MB) + 6 dependencies (31.8 MB total)
==> Fetching 7 slices... done (4.1s)
==> Verifying signatures and hashes... done
==> Linking generation 43... done
ffmpeg 7.1 installed. Run `aslice rollback` to return to generation 42.
```

Useful variations:

```
aslice install ffmpeg@v6              # a specific major version
aslice install ffmpeg --dry-run       # print the full plan, change nothing
aslice install ffmpeg --explain       # show why the solver chose each version
aslice install audiolab:convolver     # a package from a specific added repository
```

**Building from source.** You never need to, but you can:

```
aslice install ffmpeg --build-from-source                  # compile it here
aslice install ffmpeg --variant +x265 --cflags="-O3"       # non-default options
aslice install ffmpeg --cflags="-O3 -march=native" --lto   # tuned to your machine
```

Custom-flag builds interoperate with prebuilt packages: your `-march=native` ffmpeg links fine against the farm's x264, because compatibility is checked against the libraries' published interfaces, not their origin (§4.3). A non-default *feature* variant (`--variant`) may or may not have a prebuilt slice; when it doesn't, aslice says so and builds locally. Either way, the plan tells you which before anything downloads.

**Shadowed packages and `link`.** A package can be installed into the store without being linked into your profile — the principled keg-only case, declared `link = false` in the formula with a mandatory `link_reason`, usually because the package shadows something macOS ships (OpenSSL, curl). `aslice info` shows the reason. `aslice link openssl@3` opts in per profile, `aslice unlink openssl@3` backs out, and each flip is a new generation, so `rollback` undoes it like anything else. Packages that declared the dependency build and run against the store copy either way (PACKAGE-FORMAT §3.8, DESIGN §12.1).

### 3.2 Upgrading

```
aslice outdated               # what would change, and why
aslice upgrade                # everything, honoring your pins
aslice upgrade ffmpeg         # one package (and what depends on it)
```

An upgrade builds its complete new generation before touching anything you can see, so a failed download or a power cut leaves your current software untouched. If an upgraded package runs a service, aslice stops the service, swaps, and starts it again; and if the new version won't start, it *asks you* whether to roll back instead of guessing (§7.2).

There are three lines `upgrade` never crosses without being told:

- **Pinned packages don't move.** See the next section.
- **Runtime streams don't move.** If you selected PHP 8.4, `aslice upgrade php` installs 8.4 patch releases and never 8.5. Moving to a new stream is a separate decision: `aslice install php@8.5` (§6).
- **Major aslice self-updates ask first**, printing the changelog.

### 3.3 Holding a package: pin and unpin

```
aslice pin openssl            # hold: upgrades skip it, outdated says so
aslice unpin openssl
```

A pin is a note in aslice's state database — the files are not frozen, and rollback and reinstall work normally. Pins exist for the classic reason: "everything may move except this one thing production depends on."

One warning about an overloaded word: `aslice pin php 8.4` — a runtime, two arguments — pins a *project directory* to a PHP stream; that is chapter 6. `aslice pin openssl` — a library, one argument — is the hold described here. The two never collide in practice, and each man page spells out which is which.

### 3.4 Removing software

```
aslice uninstall x264         # remove one package
aslice autoremove             # remove anything nothing needs anymore
```

aslice records whether you asked for a package by name or it arrived as a dependency. Once nothing reachable from your explicitly requested set needs a dependency, `autoremove` collects it — the same model as `apt autoremove`. If it ever disagrees with you about a package's status:

```
aslice mark ffmpeg --on-request       # "I want this; stop calling it a dependency"
```

Uninstalling removes a package from future generations; old generations still reference it, so rollback keeps working until the garbage collector eventually reclaims it (§5.3).

### 3.5 Reclaiming disk: clean and gc

Two different things fill up, and two different commands empty them:

- **The cache** — downloaded slices, source tarballs, index snapshots — is pure redundancy. When it grows past a watermark (10 GB by default), `aslice clean` evicts it least-recently-used first, never touching anything younger than 30 days. `--dry-run` shows what would go.
- **The store** — your installed package versions, including ones only old generations still reference — is what makes rollback possible. `aslice gc` removes store paths that no retained generation can reach, keeping the last 5 generations by default. `--dry-run` here too; and `gc` never collects a store path a running process is using.

Both commands announce what they are doing and why. If disk pressure is chronic, lower the watermarks in `etc/aslice.toml` (§13) instead of running these by hand.

---

## 4. How installs actually work

You can use aslice happily knowing nothing in this chapter. Read it when you want to understand what you're looking at.

### 4.1 What a slice is

A slice is aslice's binary package: a zstd-compressed archive of files, a manifest, and a signature. The manifest records the package's identity (name, version, revision, flavor, OS floor), the hash of every file, the libraries the package provides and requires, a bill of materials, and the provenance — who built it, from what source, with what toolchain. `aslice provenance ffmpeg` shows all of this for anything you have installed.

Installing a slice is six steps, and none of them runs code from the package:

1. Verify the slice's signature against the repository's pinned key.
2. Verify every file against the manifest's hashes.
3. Extract into a fresh store path.
4. Check the package's library interfaces against the things that will link to it.
5. Register it in the state database.
6. Build the new generation and flip the profile symlink.

If any step fails, nothing changes: the live generation is not touched until the new one is complete.

### 4.2 Flavors: matching builds to your CPU

aslice detects the CPU once, at install time. Three flavors exist:

- **v1** runs on every 64-bit Intel Mac, down to the 2007 Core 2 Duo.
- **v2** uses SSE4.2 and POPCNT (Nehalem and later, ~2009+).
- **v3** uses AVX2 (Haswell and later, ~2014+) and is measurably faster on crypto, codecs, and compression — the workloads that dominate real package use.

The solver treats flavor as a hard constraint: a v3 slice is never offered to a machine that cannot execute it, so there is no "illegal instruction" surprise waiting at run time. Because the farm builds all three flavors of everything in the core orchard, the fastest build your machine can run is simply the default. `aslice flavors ffmpeg` shows the matrix for your machine. `aslice config set flavor v1` forces a lower flavor — useful when you are preparing an external drive for an older Mac.

### 4.3 Mixing binary and source builds

Homebrew removed build options because of combinatorial explosion: every combination of options would have needed its own binaries, and local builds broke against prebuilt ones. aslice's answer is to check compatibility where it actually lives — in the libraries' published interfaces. Every built package records which libraries it provides (with versions and symbol fingerprints) and which it requires, and substitution is allowed whenever a provider's interface covers a consumer's requirements, regardless of who compiled what with which optimization flags.

The practical consequences:

- `--cflags="-O3 -march=native"` affects only the package you name; its dependencies stay binary.
- A locally built library with the same interface *is* the same package as far as everything else is concerned. The database remembers that it was locally built (`aslice info` shows this), but nothing treats it as second-class.
- If a rebuilt library would break its dependents — a symbol set that regressed, a compatibility version that went backwards — the solver refuses the combination at install time and names the interface that changed. You find out now, not three weeks from now at runtime.

### 4.4 Variants, briefly

Packages can declare *variants* — optional features like `+x265` or `+ssl`. A variant the author marked as interface-changing gets its own builds, which coexist in the store; a build-flavor variant (debug symbols and the like) triggers a local compile. The full model, including the rules that keep variants from sprawling, is in [AUTHORING.md](AUTHORING.md) §5. As a user, three things suffice: `aslice info <pkg>` lists a package's variants, `--variant +name` enables one, and aslice tells you whether a prebuilt slice exists for the combination before it starts compiling.

---

## 5. Rollback and generations

### 5.1 What a generation is

A generation is one complete, self-consistent state of your installed software — concretely, a directory of symlinks into the store. Your profile, the thing on your `PATH`, is itself a symlink to the current generation. Every mutating operation (install, upgrade, uninstall, rollback itself) creates a new generation and then atomically retargets the profile. The retarget is atomic on both APFS and HFS+, so there is no moment at which your `PATH` points at a half-built state.

### 5.2 Using it

```
aslice history                # generations: when, what changed, how big
aslice rollback               # back one generation
aslice rollback 41            # back to a specific one
aslice switch-generation 44   # and forward again — rollback is not destructive
```

Rollback is the answer to "the upgrade broke it." Because old generations are intact, going back is exact: you get the precise files you had, not a re-download of whatever the index currently thinks the old version was.

This also makes experiments cheap. `aslice exec ffmpeg -- ffprobe in.mov` runs a command inside a temporary view with extra packages present and discards the view on exit — you can try something without committing to it.

### 5.3 Housekeeping

Generations cost disk, so aslice keeps the last 5 by default, and `aslice gc` reclaims what nothing references (§3.5). Two guarantees are worth repeating here: `gc` never touches a store path a running process is using, and `--dry-run` always shows the full list before anything is deleted.

The store is supposed to be immutable, and aslice treats drift as a security signal:

```
aslice store verify                    # re-hash everything against the manifests
aslice store verify --quarantine x264  # pull a failing path out of service
```

A store file that no longer matches its manifest means disk corruption or tampering — there is no legitimate third option. Quarantine removes the path from all future generations (dependents are reported), and reinstalling restores a verified copy.

---

## 6. Managing runtimes: PHP, Python, Ruby, Node

Runtimes are the packages people keep in several versions at once — and historically the place where version managers (nvm, pyenv, rbenv) grew up as separate tools, fighting the package manager over your `PATH`. aslice builds that job in. If you never touch PHP, Python, Ruby, or Node, skip this chapter.

### 6.1 Streams, and installing them

A runtime is a single formula with several maintained *streams*: PHP has 8.3, 8.4, 8.5; Python has 3.11, 3.12, 3.13. Streams coexist:

```
aslice install php@8.4        # ordinary install, sits next to every other stream
aslice install php@8.5
```

Installing a stream never changes which `php` you get — selection is always explicit. That is what makes `aslice upgrade` safe on a machine that serves things: upgrades move within your selected stream, never across streams.

### 6.2 Selecting: session, project, default

Three levels, resolved in this order, first match wins:

```
aslice use php 8.5            # this shell only (session)
aslice pin php 8.4            # this project tree, recorded in ./aslice.toml — commit it
aslice default php 8.4        # everything else: cron, services, stray shells
```

- **Session** selection is an environment variable, `ASLICE_USE_PHP`. `aslice use` prints it and, with the shell integration from `aslice init`, sets it for you. It dies with the shell, and it is visible in `env`.
- **Project** selection is a file, `aslice.toml`, found by walking up from your working directory. One file pins every runtime in the repo — PHP and Node side by side — and it is meant to be committed, alongside `composer.json` or `package.json`.
- **Default** is the fallback, recorded in aslice's state database.

`aslice which php` traces the whole resolution — which level matched and why, down to the store path — so "what am I actually running?" is always one command away. `aslice versions php` shows the matrix: installed streams, current selections, and which extensions each stream has.

Under the hood, a directory of small *shims* sits ahead of the profile on your `PATH`. A shim resolves the selection and `exec`s the real binary — no wrapper process, sub-millisecond overhead. Services and scripts that must name an exact version use the versioned aliases (`php8.4`) instead; those never move under you.

### 6.3 Extensions and ecosystem tools

Compiled extensions — `php-redis`, `ruby-pg` — are ordinary aslice packages bound to one runtime stream. Installing one builds (or downloads) it against your currently selected stream. A patch upgrade within the stream leaves extensions alone; installing a new stream offers to provision your previous stream's extension set for it. And because runtime and extensions live in the same generation, a rollback restores them together.

The ecosystems' own installers keep working too: `pip install`, `gem install`, `npm i -g`, `pecl install`, `composer global require`. The shim routes each into a per-stream, per-user directory (`~/.aslice/runtimes/php/8.4/` and friends), so a `pip install` under Python 3.12 is invisible to 3.13. aslice never manages, audits, or deletes those directories; when you uninstall a stream, it warns you about the orphaned directory rather than removing it.

Tools that run *on* a runtime without compiling against it — composer, yarn, prettier, poetry — install once and follow your selection: composer always runs under your selected PHP and switches when you switch. That behavior is a property of the tool's formula; there is nothing to configure.

---

## 7. Running services

### 7.1 The command

Packages that provide services — nginx, PostgreSQL, Redis, dnsmasq — declare them in their formula, and aslice manages them as real launchd jobs:

```
aslice service list                 # everything aslice manages
aslice service status postgresql    # pid, state, last exit — launchd's truth, not a pidfile
aslice service start redis
aslice service stop redis
aslice service restart redis
aslice service run redis            # foreground, unregistered — for debugging
```

User-level services run as you, need no sudo, and may come from any repository. Root-level daemons are the privileged exception: they install and run through aslice's audited privileged helper, with explicit per-operation consent, and only official, verified, or local repositories may offer them (§9.2).

Per-service environment overrides live in `~/.config/aslice/services/<pkg>.env` and are applied when aslice generates the launchd job. You never edit the generated plist, and upgrades never clobber your overrides.

### 7.2 Upgrades and the rollback prompt

An upgrade never replaces the binary out from under a running service. The sequence: build the complete new generation while the service keeps running; stop the affected jobs — and only those, so an ffmpeg upgrade never bounces your database; swap the generation; start the jobs; health-check them.

If a service fails to start after an upgrade, aslice shows you the failure and asks:

```
error: service nginx failed to start after the upgrade (launchd exit status 78;
log: /opt/aslice/profiles/default/var/log/nginx/error.log)
The previous generation (nginx 1.26.2, generation 41) is intact and can be restored in seconds.
Roll back and restart the previous version? [y/N]
```

Answer Yes and aslice swaps back and restarts the old version. Answer No (the default) and the new generation stays live with the service down and the evidence in place; `aslice rollback` remains available whenever you are done reading logs. Scripts and other non-interactive runs never see the prompt — they fail with a machine-readable error, and automation that wants automatic rollback passes `--rollback-on-service-failure`. There is no flag that reports a downed service as success.

---

## 8. Keeping TLS alive on an old OS

The most common day-one failure on 10.11–10.13 is not a missing library — it is TLS itself. The system's certificate trust store froze years ago: roots expired, modern roots never arrived, and everything that relies on the store — the curl and git you just installed, but also Safari and Mail — inherits the rot. `aslice ca-update` is the fix, applied in layers; every layer after the first is optional, and each says what it can and cannot do.

### 8.1 The bundle (the layer everyone wants)

```
aslice ca-update
```

The CA certificate bundle is an ordinary aslice package: `ca-certificates`, built from the Mozilla root program (the same trust decisions Debian, Fedora, and Homebrew ship), signed, indexed, and kept fresh by the same update machinery as every other package. Installing or refreshing it is an ordinary, rollback-able transaction. `aslice shellenv` and the shell integration point `curl`, `git`, and `python` at the bundle, so command-line TLS heals completely — modern roots, modern ciphers, TLS 1.3 — regardless of what the OS believes. `aslice ca-update --check` reports staleness without changing anything; `aslice doctor` warns when the bundle falls behind.

If your organization intercepts TLS, `aslice config set ca.source <name>` selects a different bundle source, and `aslice ca-update --from-file ./corp-bundle.pem` installs a local file directly. Every bundle is validated before activation — it must parse completely and contain no already-expired certificates — and a bundle that fails validation is refused.

### 8.2 The System keychain (Safari, Mail, and friends)

The bundle heals command-line tools. Safari, Mail, Calendar, and everything else built on the OS's security framework trust the **System keychain**, which the bundle does not touch. This does:

```
aslice ca-update --keychain
```

The import is additive: the bundle's missing roots go into the System keychain fingerprint by fingerprint, each import recorded in aslice's database. It asks for admin authorization every time — there is no "always allow." It never removes or distrusts anything already present; expired Apple-shipped roots are reported but left alone. `aslice ca-update --keychain-remove` deletes the recorded set, and nothing else.

**Understand what this fixes.** The import repairs *trust*, not *crypto*. The OS's own TLS stack on 10.11–10.12 predates TLS 1.3, so a site that requires TLS 1.3 stays unreachable in Safari no matter what the keychain holds. The command says so when you run it; the remedy is aslice's curl, or a browser with its own TLS stack.

### 8.3 The crypto stack and Apple's own roots

Two more flags, same machinery:

- `aslice ca-update --crypto` upgrades the crypto-provider packages themselves (OpenSSL and kin) to the newest the index offers; modern roots are no use to a TLS stack from 2015. It cannot touch the OS's own stack, and says so.
- `aslice ca-update --apple-certs` imports Apple's *own* certificate roots, which the Mozilla program does not carry and which Software Update, the App Store, iCloud, and Developer ID validation all chain to, from a second pinned, signed package. Aging Apple intermediates break things on a frozen OS the same way expired public roots do.

### 8.4 Replacing Apple's fossilized tools

Part of the OS's TLS surface is beyond trust stores entirely: the `/usr/bin/openssl` on 10.11 is from the 0.9.8 era and cannot speak modern TLS at all. For that, the core orchard ships `[system-patch]` packages — a declared, consent-gated, fully reversible mechanism that backs up the Apple original byte for byte and replaces it with a symlink into your aslice generation. You opt in per package and per operation. `aslice system-patch list` shows what is currently replaced; `aslice system-patch restore <path>` puts the original back and verifies its hash. This is the most tightly gated category in the system; `man aslice-system-patch`, and DESIGN §12.11, give the full accounting of what it does and does not guarantee.

---

## 9. Repositories, trust, and staying offline

### 9.1 Where packages come from

Out of the box, aslice is configured with the project's own repository: the core and extended orchards, compiled, signed, and pre-pinned into the bootstrap. There is nothing to configure, and no reason to think about this chapter at all until you add a second source.

A **repository** is a static, signed tree: metadata, the package index, formulae, and the blobs — slices, plus a copy of every source archive the farm ever fetched, so an upstream vanishing breaks nothing already published. Anyone can host one, including you (AUTHORING §11). Mirrors are full copies, and if the project's host is unreachable, aslice fails over across the repository's declared mirrors automatically.

### 9.2 Adding repositories and trust levels

```
aslice repo add https://repo.example.org
```

Adding a repository pins its signing key's fingerprint on first use, displays the fingerprint, and recommends that you verify it out of band. Any later change to that key blocks the repository and is reported: a key change is the moment a hijack would announce itself, so aslice treats it as one until you explicitly re-pin (`aslice repo re-pin`).

Every repository carries an enforced trust level — a set of capabilities, not a label:

| Level | What it means | Binaries? | Root daemons, kexts? | `[system-patch]`? |
|---|---|---|---|---|
| **official** | The project's own; pre-pinned | yes | yes | yes |
| **verified** | Community repos countersigned by the project; ship disabled | yes, once enabled | yes | only with an explicit per-repo grant from you |
| **third-party** | You added it; key pinned on first use | yes | never | never |
| **local** | Your own `file://` tree | formulae by default | yes (your machine, your authority) | yes |

`aslice repo enable <name>` turns on a verified repo; enabling *is* the consent, so its binaries install immediately afterwards. `aslice repo list`, `repo keys`, and `repo audit <name>` show the state of your sources. One thing no repository at any level can do is make aslice execute package code at install time — that door is closed structurally.

When two repositories offer the same package name, aslice asks you once, remembers the answer, and asks again if the situation changes. `aslice repo resolutions` shows your answers; `repo:pkg` addressing (`audiolab:convolver`) bypasses the question entirely.

### 9.3 What "verified" and "signed" do and don't mean

Signatures and trust levels answer narrow questions precisely: *are these bits exactly what this repository published, and how much did I decide to trust this repository?* They do not make claims about the software's behavior — a signed, verified slice of malicious software is still malicious software, now with better paperwork. The design document's limitations section (DESIGN §10.7) says this at length; the short version is that aslice's guarantees are about provenance and integrity, and it never pretends otherwise in its messages.

### 9.4 Checking what you're running

```
aslice audit                  # known vulnerabilities (CVEs) in your installed set
aslice provenance ffmpeg      # who built this, from what source, with what toolchain
```

`audit` matches your installed set against public vulnerability feeds, works offline against a cached copy of the feeds, and reports affected-version ranges. Packages past their upstream's end-of-life are surfaced here too; they need `--allow-eol` to install in the first place.

### 9.5 Working offline

aslice assumes connectivity will be intermittent; many of its users are audio rigs and lab machines that are offline by policy. Everything already downloaded — cached slices, the index snapshot — works without a network, and cached slices install fine. `aslice doctor --offline` checks health without touching the network and reports the age of your cached index instead of failing on unreachable repositories. A stale index never blocks operations against the cache; it just means that "newest" means "newest as of" the snapshot date, which aslice prints.

---

## 10. One file, one command: rebuilding a machine

### 10.1 The idea

A Mac that comes back from system recovery is blank. Getting from blank to *ready to work* is normally an afternoon of remembering — which packages mattered, how the Dock was set up, which shell, which services, which PHP the projects expect. aslice can hold all of that in one declarative file, `setup.toml`, and replay it with one command:

```
# on the blank Mac: install aslice itself first (§2), then:
aslice apply setup.toml          # or: aslice apply https://example.org/my/setup.toml
```

Packages install, runtime streams are selected, services start, Dock and Finder preferences are written, the login shell is enrolled and set — each step planned and shown to you before anything changes. Because the file is plain text, it is also something to *share*: one file instead of forty screenshots of System Settings, diffable and version-controlled like any code.

The other direction exists too: `aslice export` captures a machine you have already set up into a fresh `setup.toml` (§10.4).

The full schema and the precise semantics live in [SETUP.md](SETUP.md); this chapter is the tour.

### 10.2 The file

```
# setup.toml — declarative system setup. Apply: aslice apply setup.toml
schema = 1

packages = [
  "ffmpeg@7",                # the same names and constraints as aslice install
  "postgresql +ssl",         # variants included
]

[runtimes.default]           # like aslice default php 8.4 (§6.2)
php = "8.4"

[services]
start = ["postgresql"]       # like aslice service start (§7)

[shell]
default = "zsh"              # login shell — installed, enrolled, and set

[defaults.user."com.apple.dock"]     # your preferences — no privileges needed
autohide = true
tilesize = 48

[defaults.system."com.apple.loginwindow"]   # system-wide — consent-gated (§10.3)
# …
```

Two properties are worth knowing before you trust it. First, the file is **data, never code**: unlike a Homebrew Brewfile, which is Ruby and can do anything Ruby can, nothing in a `setup.toml` executes. Applying a stranger's file has a bounded blast radius, and you see the plan first. Second, the file is a *wishlist*, not an exact snapshot — "ffmpeg 7" resolves against today's index. For bit-exact reproduction there is the lock file (PACKAGE-FORMAT §7), and `aslice apply` replays those too: it is one verb for "make reality match this document", whether the document is a plan, a lock, or a setup file.

### 10.3 Applying it

With no argument, `aslice apply` reads `./setup.toml`. Every apply is a plan first: the wishlist is resolved, preferences are diffed, and the complete plan is printed for confirmation before anything changes. `--dry-run` prints the plan without asking.

Applying is **convergent**: apply the same file twice and the second run reports "0 changes". It is also **additive**: apply never removes something merely because the file doesn't mention it. If you *do* want the file to be the whole truth, `aslice apply --prune` retracts what the file previously applied but no longer declares — and nothing else. Your hand-installed packages and hand-set preferences are invisible to prune.

Two kinds of step write to OS territory and are therefore **consent-gated**: system-wide preference domains (`/Library/Preferences`), and enrolling an aslice-provided login shell in `/etc/shells`. Interactively, you are shown what will be written and asked. In a script or a recovery terminal, pass `--accept-system-changes` — the same flag as for system packages (§8.4) — or those steps are refused while everything unprivileged still lands.

The safety net is the one you already know: before each preference write or shell change, aslice records the old value against the new **generation**, so `aslice rollback` (§5) restores preferences and login shell along with the packages. `aslice history` shows which file applied what, and when.

### 10.4 Capturing a machine: export

```
aslice export > setup.toml
aslice export --defaults com.apple.dock,com.apple.finder > setup.toml
```

Export writes what aslice can *know*: your explicitly installed packages (with variants and non-default streams), your runtime selections, enabled services, your login shell if it isn't the OS default, any repositories you added, and any configuration you changed from defaults. The output is sorted and stable, so exports diff cleanly under version control.

Preferences are the exception. There is no baseline to diff your whole preferences folder against, and application preference domains can contain account tokens, server addresses, and recent-file lists — exactly what a shared file must not leak. Export therefore captures preferences only for domains you name with `--defaults` (or `--system-defaults` for system-wide ones) and stamps the result with a review-before-sharing warning. Value types the schema cannot represent (dictionaries, raw data blobs, dates) are written as comments, never silently dropped.

### 10.5 Sharing, and coming from Homebrew

The file is meant to travel: a team can keep one next to its onboarding docs, and "how do you have your Mac set up?" becomes a link instead of a memoir. Two rules keep shared files healthy — no secrets, ever (nothing in the schema legitimately holds one), and no machine-specific values (hostnames and serials say *this machine*, not *how I like machines*).

If your current source of truth is a Homebrew Brewfile, `aslice import --from-brewfile Brewfile > setup.toml` translates it mechanically: `brew` entries become packages, `tap` entries become comments (an aslice repository is a different, signed thing — §9), and `cask`/`mas`/`vscode` entries are listed as skipped, with a nudge to search the orchard for a vendor-binary package instead. Treat the result as a draft to hand-tune, not a finished file. (For the packages themselves, `aslice adopt --from-homebrew` reads what Homebrew actually installed — §11.)

### 10.6 What it doesn't do

- **Dotfiles.** `~/.zshrc` and friends stay yours — chezmoi, Stow, or plain git do that job well.
- **Imaging.** FileVault, SIP, user accounts, and System Settings panes without preference domains are untouched; recovery-then-apply assumes a working macOS account already exists.
- **Fleet management.** No agent, no daemon, no drift detection. If you want periodic enforcement, a `launchd` job that runs `aslice apply` is enough.
- **Secrets.** Keychain items are never read or written, on apply or export.

---

## 11. aslice and Homebrew

The two coexist: aslice lives in `/opt/aslice` and never touches `/usr/local`, in either direction. Run both for as long as you like. `aslice doctor` notices a Homebrew installation and advises on `PATH` ordering; that is the full extent of the interaction.

When you're ready to move:

```
aslice adopt --from-homebrew
```

It reads your Homebrew installation, maps the packages you explicitly installed (not their dependencies) to aslice formulae — translating old `--with-*` options into aslice variants where an equivalent exists, and Casks into vendor-binary packages where one is packaged — and produces an install plan. It recreates *intent*, not bytes: Homebrew's files are never reused or modified, and whether you remove Homebrew afterwards is your call.

---

## 12. When something goes wrong

### 12.1 Start with doctor

```
aslice doctor
```

`doctor` is read-only, fast, and offline-capable, and every finding names its remedy — not "store integrity error" but "store path `x264-0.164-0+core.v3` fails manifest hash (1 file) — quarantine with `aslice store verify --quarantine x264` and reinstall." Exit codes are scriptable: 0 healthy, 1 warnings, 2 failures. `doctor --fix` performs only the repairs that cannot lose data — pruning dangling cache entries, re-linking a broken generation symlink to its recorded target, refreshing stale index snapshots — announcing each before it acts; for anything else, it hands you the command.

### 12.2 Read the log

Everything aslice does is logged to `log/` inside the prefix — structured, local, and never transmitted anywhere; the no-telemetry charter applies to logs as it does to metrics.

```
aslice log --last-op          # exactly what the last operation did
aslice log --follow           # live
aslice log --level debug      # more
```

`doctor`'s footer points at the relevant log files and the last operation ID. When you file an issue, `aslice log --last-op` is the excerpt maintainers need; it is generated locally, attached by you, and never auto-submitted.

### 12.3 Common problems

| Symptom | What's happening | The fix |
|---|---|---|
| `curl`/`git` fail with certificate errors on a fresh install | The OS trust store expired years ago | `aslice ca-update`, then open a new shell (or `aslice shellenv`) |
| Safari can't reach a site even after `ca-update --keychain` | The site's TLS requirements exceed the OS's crypto stack; keychain imports fix trust, not crypto | Use aslice's curl, or a browser with its own TLS stack |
| The installer can't fetch anything at all | TLS-dead machine: expected on old releases | Nothing — it falls back to plain HTTP for the same hash-pinned files, with a printed banner, and verifies them identically |
| A service won't start after an upgrade | aslice health-checked it and is waiting for your decision | Read the shown log path; answer the rollback prompt, or `aslice rollback` later |
| "repository key pin changed" | The repo's signing key differs from your pin — rotation or hijack, and aslice can't tell which | Verify the new fingerprint out of band; only then `aslice repo re-pin` |
| A package wants SIP disabled | It's a declared `[system]` package (kexts, low-level dev tools) | Follow the printed Recovery instructions, or don't install it — the warning is intentional |
| `php` resolves to the wrong version | Session, project, or default selection, in that order | `aslice which php` traces the resolution |
| aslice and Homebrew binaries shadow each other | `PATH` ordering | `aslice doctor` (coexistence group) prints the exact edit |
| Disk pressure | Cache or old generations | `aslice clean --dry-run`, `aslice gc --dry-run`, then lower the watermarks (§13) |
| Something in the store fails verification | Corruption or tampering; both are treated as security events | `aslice store verify --quarantine <pkg>`, reinstall, and keep the log |
| After a macOS update, a `[system-patch]` behaves oddly | The update restored or replaced the Apple file under the symlink | `aslice doctor` reports the drift with reapply/restore options — it never silently re-patches |

---

## 13. Configuration reference

aslice's configuration file is `etc/aslice.toml` inside the prefix (`~/.aslice/etc/aslice.toml` for per-user installs). Edit it directly, or via `aslice config set <key> <value>`. The keys, as of this writing:

| Key | Values | Default | Meaning |
|---|---|---|---|
| `flavor` | `v1`, `v2`, `v3` | detected | CPU flavor ceiling. Lower it when preparing an install for an older machine. |
| `ca.source` | a configured bundle source | `mozilla` | Where `ca-certificates` bundles come from (§8.1). |
| `mirrors` | list of URLs | project defaults | Extra full-tree mirrors for a repository, tried in order. |
| `gc.keep_generations` | integer | 5 | How many generations rollback can reach. |
| `gc.store_watermark` | size | 20 GB | Store size that triggers a GC suggestion on install. |
| `clean.cache_watermark` | size | 10 GB | Cache size that triggers LRU eviction. |
| `log.keep_days` / `log.keep_size` | integer / size | 14 / 256 MB | Log rotation bounds. |

Environment variables that matter:

- `ASLICE_USE_<RUNTIME>` — the session runtime selection, set by `aslice use` (§6.2).
- `SSL_CERT_FILE`, `CURL_CA_BUNDLE`, `GIT_SSL_CAINFO` — pointed at the aslice bundle by `aslice shellenv` / `aslice init` (§8.1).
- `XDG_CONFIG_HOME` — governs where per-service environment overrides live (`<xdg>/aslice/services/`, §7.1).

The environment group in `aslice doctor` lists every `ASLICE_*` variable currently overriding configuration — overrides are shown, never hidden.

The prefix layout, for orientation: `store/` (immutable packages), `profiles/generations/` (the symlink forests), `shims/` (runtime multiplexing, ahead of the profile on `PATH`), `apps/` (vendor `.app` bundles), `cache/`, `log/`, `db/state.sqlite` (the state database), `etc/aslice.toml`.

---

## 14. Getting help

- **`aslice help <command>`** prints the same text as `man aslice-<command>`; the man pages and the CLI help are one source, so they cannot drift apart. `man aslice` is the index of all of them.
- **This manual** is the prose version; [DESIGN.md](DESIGN.md) is the why; [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) is the schema.
- **Bugs and package requests** go to the project tracker. Attach the output of `aslice log --last-op` and `aslice doctor --json`; both are generated locally and contain nothing you haven't seen. Expect the conduct norms in [CONTRIBUTING.md](../CONTRIBUTING.md): be decent, assume good faith, and say so when something is wrong.

---

## Appendix. Command quick reference

| Command | What it does |
|---|---|
| `install` / `reinstall` / `link` / `unlink` | Install packages (binary first); repair a damaged profile entry; flip a `link = false` package into/out of a profile (§3.1) |
| `uninstall` / `autoremove` / `mark` | Remove packages; collect unneeded dependencies; fix request records |
| `upgrade` / `outdated` | Move everything (or one package) forward; preview what would move |
| `pin` / `unpin` | Hold a package against upgrades (one argument) — or pin a project to a runtime stream (two, §6) |
| `search` / `info` / `flavors` / `why` / `leaves` | Find packages and inspect them |
| `history` / `rollback` / `switch-generation` | Travel through generations |
| `gc` / `clean` / `store verify` | Reclaim store, reclaim cache, tripwire store integrity |
| `use` / `default` / `versions` / `which` | Runtime stream selection and introspection |
| `service list/status/start/stop/restart/run` | launchd service lifecycle |
| `ca-update` (+ `--keychain`, `--crypto`, `--apple-certs`) | Heal TLS: bundle, keychain, crypto stack, Apple's roots |
| `repo add/list/enable/keys/audit` | Manage package sources and trust |
| `repo prefer/resolutions/forget/re-resolve/allow-system-patch/deny-system-patch` | Overlap decisions and per-repo grants (§9.2) |
| `audit` / `provenance` | CVE report; build provenance |
| `doctor` / `log` | Health battery; the local operation log |
| `adopt --from-homebrew` | Migrate an existing Homebrew leaf set |
| `apply` / `export` / `import --from-brewfile` | Converge the machine to a `setup.toml` (or replay a lock/plan); capture this machine as one; translate a Brewfile (§10) |
| `self-update` | Update aslice itself (health-checked, auto-rollback) |
| `shellenv` / `init` | Print shell environment; print shell integration |
| `exec` / `test` / `livecheck` | Run in a temporary view; run a package's smoke tests; check for newer upstream releases |
| `system-patch list/status/restore` | Inspect and reverse declared system-file replacements |
| `help` | The man page for any command, in your terminal |
