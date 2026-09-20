# aslice Manual

**The user guide for aslice — a package manager for Intel macOS.**

- **Status:** v0.1 — September 2026
- **Audience:** people who install and run software with aslice. That's most of what follows. If you *write* packages, read chapters 1–4 and then move to [AUTHORING.md](AUTHORING.md). If you want to know *why* things are the way they are, the rationale lives in [DESIGN.md](DESIGN.md).
- **Companions:** the man pages in [man/](../man/) (also available as `aslice help <command>`), [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md), [ORCHARD-POLICY.md](ORCHARD-POLICY.md), [REPOSITORIES.md](REPOSITORIES.md), [GENESIS.md](GENESIS.md).

---

## 1. Overview

aslice is a package manager for Intel Macs running macOS 10.11 (El Capitan) through 12 (Monterey). It exists because Homebrew is leaving this platform: no new Intel bottles, no CI, and an announced date for dropping Intel entirely. The machines are still good. The software pipeline is what's disappearing, so this project rebuilds it.

Three facts about aslice explain almost everything else:

**It installs binaries, and it never runs them at install time.** Packages arrive as *slices* — prebuilt, signed, compressed archives. Installing a slice means verifying its signature, checking its contents against a manifest, and linking it into place. No package ever gets to execute a script on your machine during install. There is no equivalent of Homebrew's `post_install`, and there never will be.

**Nothing is overwritten — every state of your system is kept and you can go back.** Installed packages live in an immutable store. What you actually use is a *generation* — a view made of symlinks into that store. Every install, upgrade, or uninstall builds a new generation and flips one symlink. If an upgrade breaks something, `aslice rollback` puts the old state back in seconds. This is the idea Nix proved out, kept small enough to stay understandable.

**It's honest about old machines.** aslice detects your CPU and serves the fastest build it can actually run (there are three *flavors*: baseline, SSE4.2, and AVX2). It ships a modern CA certificate bundle because the one in your OS expired years ago. When it can't do something — when a package needs SIP disabled, when a vendor binary can't be redistributed, when Safari's TLS stack is too old for a site no matter what it installs — it says so plainly instead of failing mysteriously later.

And one fact about the project: **aslice collects nothing.** No telemetry, no analytics, no install IDs, no crash reporting — not even opt-in. There is no switch to turn off because there is no wiring. It's infrastructure, not a product.

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

You'll see these in every message aslice prints, so they're worth learning once.

### 1.2 The five-minute mental model

1. The **store** holds every version of every package you've installed, each in its own directory. Nothing inside it ever changes after registration.
2. Your **generation** is a directory of symlinks into the store — this is what's on your `PATH`.
3. Installing or upgrading builds a *new* generation, then swaps one symlink. The old one is untouched, so rollback is instant and a crash mid-install breaks nothing.
4. Packages are **binary by default**. Source builds happen when you ask for non-default variants or custom compiler flags — and the result still works with the prebuilt world, because compatibility is checked against the libraries' actual interfaces, not their provenance.
5. Everything aslice fetches — slices, index metadata, the CA bundle, aslice itself — is signed and hash-pinned. Verification failures are loud and blocking, always.

If you remember store + generations + signed everything, the rest of this manual is details.

---

## 2. Installing aslice

### 2.1 What you need

- An Intel Mac (2007 or later, 64-bit — every Mac that runs these releases qualifies) running macOS 10.11 through 12.
- A few hundred megabytes of disk for the toolchain and the core packages, plus room to grow. The store keeps old generations; plan on gigabytes if you install a lot.
- An internet connection for the install itself. After that, aslice works offline against its cache, degrading gracefully (§9.5).

You do **not** need Xcode or the Command Line Tools. aslice brings its own toolchain.

### 2.2 The installer

The installer is a short shell script — short enough to read before you run it, which you should:

```
curl -O https://get.aslice.sh/install.sh
less install.sh          # it's about 200 lines; read it
sh install.sh
```

It fetches exactly two things: the aslice bootstrap binary and the root of aslice's update metadata. Both are pinned by hash inside the script and cross-checked against a signed checksums file on a second, independent transport. Everything after that first step is verified by aslice's own update framework. The script does not ask for your password, with one optional exception: it offers to run `sudo` once to create `/opt/aslice` and hand it to your user account. If you'd rather not — or you don't have admin rights — say no, and it installs to `~/.aslice` instead. Both layouts are fully supported and behave identically; the only difference is the path.

**If your Mac's TLS is too old for the modern web**, the script may be unable to complete an HTTPS handshake at all — this is the day-one condition of a frozen OS, and it's expected. The installer detects the failure and retries over plain HTTP, fetching *the same hash-pinned files*, verifying them against the same pins and signatures, and printing a prominent banner telling you the transport was downgraded and why that's safe. The hashes and signatures are the trust; HTTPS was only ever a privacy layer for the download.

### 2.3 After the install

Add aslice to your shell. For zsh (the default since Catalina):

```
eval "$(/opt/aslice/bin/aslice init zsh)"     # or ~/.aslice/bin/aslice for a per-user install
```

Add that line to your `~/.zshrc` to make it permanent. Then verify the installation:

```
aslice doctor
```

`doctor` runs a battery of checks — CPU flavor, store integrity, repository freshness, trust-store state — and prints either a one-line "healthy" or a list of findings, each with the exact command that fixes it. On a fresh install of an old OS, it will usually have one suggestion: `aslice ca-update`. Run it. Chapter 8 explains what it does; the short version is that it replaces your OS's long-expired certificate trust store with a current one, so `curl`, `git`, and `python` can talk to the modern web.

### 2.4 Updating aslice itself

aslice updates itself like any other package:

```
aslice self-update
```

It's signed, verified, installed as a new generation, and health-checked after the swap; if the new binary fails its own smoke test, aslice rolls itself back automatically. `aslice self-update --check` reports without installing. If you never want it to move, `aslice pin aslice` holds it like any other package.

### 2.5 Removing aslice

```
aslice uninstall aslice        # removes the manager's registration
sudo rm -rf /opt/aslice        # or rm -rf ~/.aslice — this is the whole footprint
```

aslice never installs anything outside its prefix (the `/opt/aslice/apps/` directory included), so removing the prefix removes it completely. If you used `ca-update --keychain`, run `aslice ca-update --keychain-remove` first — it deletes exactly the certificates aslice imported into the System keychain, recorded one by one, and nothing else.

---

## 3. Everyday commands

This chapter covers the dozen commands that make up daily use. Every one of them has a man page — `man aslice-install`, `man aslice-upgrade`, and so on — and `aslice help <command>` prints the same text in your terminal.

### 3.1 Finding and installing software

```
aslice search ffmpeg          # names and descriptions matching "ffmpeg"
aslice info ffmpeg            # versions, variants, dependencies, size, provenance
aslice install ffmpeg
```

`install` is binary-first: it resolves your request against the index, picks the newest version that runs on your OS release and the fastest flavor your CPU executes, downloads the slices, verifies them, and links a new generation. A typical install prints the plan, then the result:

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

Custom-flag builds interoperate with prebuilt packages — your `-march=native` ffmpeg links fine against the farm's x264, because compatibility is verified against the libraries' published interfaces, not their origin (§4.3). Non-default *feature* variants (`--variant`) may or may not have prebuilt slices; when they don't, aslice says so and builds locally. Either way the plan tells you before anything is downloaded.

### 3.2 Upgrading

```
aslice outdated               # what would change, and why
aslice upgrade                # everything, honoring your pins
aslice upgrade ffmpeg         # one package (and what depends on it)
```

Upgrades build a complete new generation before touching anything you can see, so a failed download or a power cut leaves your current software untouched. If an upgraded package runs a service, aslice stops the service, swaps, and starts it again — and if the new version won't start, it *asks you* whether to roll back rather than guessing (§7.2).

`upgrade` never crosses certain lines without being told:

- **Pinned packages don't move.** See the next section.
- **Runtime streams don't move.** If you selected PHP 8.4, `aslice upgrade php` installs 8.4 patches, never 8.5. New streams are a separate, deliberate `aslice install php@8.5` (§6).
- **Major aslice self-updates ask first**, printing the changelog.

### 3.3 Holding a package: pin and unpin

```
aslice pin openssl            # hold: upgrades skip it, outdated says so
aslice unpin openssl
```

A pin is a note in aslice's state database, not a freeze of the files — rollback and reinstall still work normally. Pins exist for the classic reason: "everything may move except this one thing production depends on."

One warning about overloaded words: `aslice pin php 8.4` (a runtime, two arguments) pins a *project directory* to a PHP stream — that's chapter 6. `aslice pin openssl` (a library, one argument) is the hold described here. The two never collide in practice, but the man page for each spells out which is which.

### 3.4 Removing software

```
aslice uninstall x264         # remove one package
aslice autoremove             # remove anything nothing needs anymore
```

aslice records whether you asked for a package or it arrived as a dependency. `autoremove` collects the second kind once nothing reachable from your explicitly-requested set needs them — the same model as `apt autoremove`. If it ever disagrees with you about a package's status:

```
aslice mark ffmpeg --on-request       # "I want this; stop calling it a dependency"
```

Uninstalling removes the package from future generations. Old generations still reference it, so rollback keeps working until the garbage collector eventually reclaims it (§5.3).

### 3.5 Reclaiming disk: clean and gc

Two different things fill up, and two different commands empty them:

- **The cache** — downloaded slices, source tarballs, index snapshots — is pure redundancy. `aslice clean` evicts it, least-recently-used first, when it grows past a watermark (10 GB by default), never touching anything younger than 30 days. `--dry-run` shows exactly what would go.
- **The store** — your installed package versions, including the ones only old generations reference — is what makes rollback possible. `aslice gc` removes store paths no retained generation can reach (it keeps the last 5 generations by default). `--dry-run` here too, and `gc` will never collect a store path a running process is using.

Both commands print what they're doing and why. If disk pressure is chronic, lower the watermarks in `etc/aslice.toml` (§12) rather than running the commands by hand.

---

## 4. How installs actually work

You can use aslice happily knowing nothing in this chapter. Read it when you want to understand what you're looking at.

### 4.1 What a slice is

A slice is aslice's binary package: a zstd-compressed archive of files, a manifest, and a signature. The manifest records the package's identity (name, version, revision, flavor, OS floor), the hash of every file it contains, the libraries it provides and requires, a bill of materials, and its provenance — who built it, from what source, with what toolchain. `aslice provenance ffmpeg` shows you all of this for anything installed.

Installing a slice is six steps, and none of them runs code from the package:

1. Verify the slice's signature against the repository's pinned key.
2. Verify every file against the manifest's hashes.
3. Extract into a fresh store path.
4. Check the package's library interfaces against the things that will link to it.
5. Register it in the state database.
6. Build the new generation and flip the profile symlink.

If any step fails, nothing changes. That's not a promise, it's the structure: the live generation isn't touched until the new one is complete.

### 4.2 Flavors: why aslice asks what CPU you have

It doesn't ask — it detects, once, at install time. Three flavors exist:

- **v1** runs on every 64-bit Intel Mac, down to the 2007 Core 2 Duo.
- **v2** uses SSE4.2 and POPCNT (Nehalem and later, ~2009+).
- **v3** uses AVX2 (Haswell and later, ~2014+) and is measurably faster on crypto, codecs, and compression — the workloads that dominate real package use.

The solver treats flavor as a hard constraint: a v3 slice is never offered to a machine that can't execute it, so there's no "illegal instruction" surprise. The farm builds all three flavors of everything in the core orchard, so the fast path is the default path, not an enthusiast option. `aslice flavors ffmpeg` shows the matrix for your machine; `aslice config set flavor v1` forces a lower one (the reason to do this is preparing an external drive for an older Mac).

### 4.3 Mixing binary and source builds

The reason Homebrew removed build options was combinatorial explosion: every option combination would have needed its own binaries, and local builds broke against prebuilt ones. aslice's answer is to check compatibility where it actually lives — in the libraries' published interfaces. Every built package records which libraries it provides (with versions and symbol fingerprints) and which it requires. Substitution is allowed when a provider's interface covers a consumer's requirements, regardless of who compiled what with which optimization flags.

The practical consequences:

- `--cflags="-O3 -march=native"` affects only the package you name; its dependencies stay binary.
- A locally-built library with the same interface *is* the same package as far as everything else is concerned. The database remembers it was locally built (`aslice info` shows this), but nothing treats it as second-class.
- If a rebuilt library would break its dependents — a symbol set that regressed, a compatibility version that went backwards — the solver refuses the combination at install time and names the exact interface that changed, instead of letting you discover it three weeks later at runtime.

### 4.4 Variants, briefly

Packages can declare *variants*: optional features like `+x265` or `+ssl`. Variants the author marked as interface-changing get their own builds and coexist in the store; build-flavor variants (debug symbols and the like) just trigger a local compile. The full model — including the rules package authors follow so variants don't sprawl — is in [AUTHORING.md](AUTHORING.md) §5. As a user you only need: `aslice info <pkg>` lists a package's variants, `--variant +name` enables one, and aslice tells you whether a prebuilt slice exists for the combination before it starts compiling anything.

---

## 5. Rollback and generations

### 5.1 What a generation is

A generation is one complete, self-consistent state of your installed software: a directory of symlinks into the store. Your profile — the thing on your `PATH` — is a symlink to the current generation. Every mutating operation (install, upgrade, uninstall, rollback itself) creates a new generation and atomically retargets the profile. macOS guarantees the retarget is atomic on both APFS and HFS+, so there is no moment where your `PATH` points at a half-built state.

### 5.2 Using it

```
aslice history                # generations: when, what changed, how big
aslice rollback               # back one generation
aslice rollback 41            # back to a specific one
aslice switch-generation 44   # and forward again — rollback is not destructive
```

Rollback is the answer to "the upgrade broke it." Because old generations are intact, going back is exact — you get the precise files you had, not a re-download of what the index currently thinks the old version was.

This also makes experiments cheap. `aslice exec ffmpeg -- ffprobe in.mov` runs a command inside a temporary view with extra packages present, discarded on exit — try something without committing to it.

### 5.3 Housekeeping

Generations cost disk, so aslice keeps the last 5 by default and `aslice gc` reclaims what nothing references (§3.5). Two guarantees are worth repeating: `gc` never touches a store path a running process is using, and `--dry-run` always shows the full list before anything is deleted.

The store is supposed to be immutable, and aslice treats drift as a security signal, not a housekeeping issue:

```
aslice store verify                    # re-hash everything against the manifests
aslice store verify --quarantine x264  # pull a failing path out of service
```

A file in the store that no longer matches its manifest means disk corruption or tampering; there is no legitimate third option. Quarantine removes the path from all future generations (dependents are reported), and reinstalling restores a verified copy.

---

## 6. Managing runtimes: PHP, Python, Ruby, Node

Runtimes are the packages people keep in several versions at once, and they're where version managers (nvm, pyenv, rbenv) grew up as separate tools fighting the package manager over your `PATH`. aslice builds that job in. If you never touch PHP, Python, Ruby, or Node, skip this chapter.

### 6.1 Streams, and installing them

A runtime is one formula with several maintained *streams* — PHP has 8.3, 8.4, 8.5; Python has 3.11, 3.12, 3.13. Streams coexist:

```
aslice install php@8.4        # ordinary install, sits next to every other stream
aslice install php@8.5
```

Installing a stream never changes which `php` you get. Selection is always explicit, which is what makes `aslice upgrade` safe on a machine that serves things: upgrades move within your selected stream, never across streams.

### 6.2 Selecting: session, project, default

Three levels, resolved in this order, first match wins:

```
aslice use php 8.5            # this shell only (session)
aslice pin php 8.4            # this project tree, recorded in ./aslice.toml — commit it
aslice default php 8.4        # everything else: cron, services, stray shells
```

- **Session** selection is an environment variable (`ASLICE_USE_PHP`). `aslice use` prints it and, with the shell integration from `aslice init`, sets it for you. It dies with the shell and is visible in `env` — no hidden state.
- **Project** selection is a file, `aslice.toml`, found by walking up from your working directory. One file pins every runtime in the repo — PHP and Node side by side — and it's meant to be committed, next to `composer.json` or `package.json`.
- **Default** is the fallback, recorded in aslice's state database.

`aslice which php` traces the whole resolution — which level matched, why, down to the exact store path — so "what am I actually running?" is always one command. `aslice versions php` shows the matrix: installed streams, current selections, and which extensions each stream has.

How it works under the hood: a directory of tiny *shims* sits ahead of the profile on your `PATH`. A shim resolves the selection and `exec`s the real binary — no wrapper process, sub-millisecond. Services and scripts that must name an exact version use versioned aliases (`php8.4`) instead, which never move under you.

### 6.3 Extensions and ecosystem tools

Compiled extensions — `php-redis`, `ruby-pg` — are ordinary aslice packages, but bound to exactly one runtime stream. Install one and it builds (or downloads) against your currently selected stream; a PHP patch upgrade within the stream leaves extensions alone; installing a new stream offers to provision your previous stream's extension set for it. Rollback restores runtime and extensions together, because they're all in the generation.

The ecosystems' own installers keep working too. `pip install`, `gem install`, `npm i -g`, `pecl install`, `composer global require` — the shim routes each into a per-stream, per-user directory (`~/.aslice/runtimes/php/8.4/` and friends), so a `pip install` under Python 3.12 is simply invisible to 3.13. aslice never manages, audits, or deletes those directories; uninstalling a stream warns about the orphaned directory instead of removing it.

Tools that run *on* a runtime without compiling against it — composer, yarn, prettier, poetry — install once and follow your selection: composer always runs under your selected PHP, switching when you switch. That's a property of the tool's formula, not something you configure.

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

User-level services run as you, need no sudo, and any repository may provide one. Root-level daemons are the privileged exception: they install and run through aslice's audited privileged helper with explicit, per-operation consent, and only official or verified repositories may offer them (§9.3).

Per-service environment overrides live in `~/.config/aslice/services/<pkg>.env` and are applied when aslice generates the launchd job — you never edit the generated plist, and upgrades never clobber your overrides.

### 7.2 Upgrades and the rollback prompt

An upgrade never replaces the binary under a running service. The sequence is: build the complete new generation while the service keeps running, stop the affected jobs (and only those — an ffmpeg upgrade never bounces your database), swap the generation, start the jobs, and health-check them.

If a service fails to start after an upgrade, aslice shows you the failure and asks:

```
error: service nginx failed to start after the upgrade (launchd exit status 78;
log: /opt/aslice/profiles/default/var/log/nginx/error.log)
The previous generation (nginx 1.26.2, generation 41) is intact and can be restored in seconds.
Roll back and restart the previous version? [y/N]
```

Yes swaps back and restarts the old version; No (the default) leaves the new generation live, the service down, and the evidence in place — `aslice rollback` remains available whenever you're done reading logs. Scripts and other non-interactive runs never get the prompt: they fail loudly with a machine-readable error, and automation that wants automatic rollback passes `--rollback-on-service-failure`. There is deliberately no flag that reports a downed service as success.

---

## 8. Keeping TLS alive on an old OS

The most common day-one failure on 10.11–10.13 isn't a missing library — it's TLS itself. The system's certificate trust store froze years ago: roots expired, modern ones never arrived, and everything that relies on it — the curl and git you just installed, but also Safari and Mail — inherits the rot. `aslice ca-update` is the fix, in layers. Each layer is optional after the first, and each says exactly what it can and cannot do.

### 8.1 The bundle (the layer everyone wants)

```
aslice ca-update
```

The CA certificate bundle is an ordinary aslice package — `ca-certificates`, built from the Mozilla root program (the same trust decisions Debian, Fedora, and Homebrew ship), signed, indexed, and kept fresh by the same update machinery as every other package. Installing or refreshing it is an ordinary, rollback-able transaction; `aslice shellenv` and the shell integration point `curl`, `git`, and `python` at it, so command-line TLS heals completely — modern roots, modern ciphers, TLS 1.3 — regardless of what the OS believes. `aslice ca-update --check` reports staleness without changing anything, and `aslice doctor` warns when the bundle falls behind.

If your organization intercepts TLS, `aslice config set ca.source <name>` selects a different source, and `aslice ca-update --from-file ./corp-bundle.pem` installs a local file directly. Every bundle is validated before activation — must parse completely, no already-expired certificates — and a bundle that fails validation is refused, never linked.

### 8.2 The System keychain (Safari, Mail, and friends)

The bundle heals command-line tools. Safari, Mail, Calendar, and everything else using the OS's security framework trust the **System keychain**, and the bundle doesn't touch it. This does:

```
aslice ca-update --keychain
```

It imports the bundle's missing roots into the System keychain — additively, fingerprint by fingerprint, each import recorded in aslice's database. It asks for admin authorization, every time; there is no "always allow." It never removes or distrusts anything already there — expired Apple-shipped roots are reported, not touched. `aslice ca-update --keychain-remove` deletes exactly the recorded set and nothing else.

**Understand what this fixes.** The import repairs *trust*, not *crypto*. On 10.11–10.12 the OS's own TLS stack predates TLS 1.3, so a site that requires it stays unreachable in Safari no matter what the keychain holds — the command says so when you run it, and the remedy is aslice's curl or a browser with its own TLS stack. Honest limits, printed, not implied.

### 8.3 The crypto stack and Apple's own roots

Two more flags, same machinery:

- `aslice ca-update --crypto` upgrades the crypto-provider packages themselves (OpenSSL and kin) to the newest the index offers — modern roots are no use to a TLS stack from 2015. It cannot touch the OS's own stack, and says so.
- `aslice ca-update --apple-certs` imports Apple's *own* certificate roots — which the Mozilla program doesn't carry, and which Software Update, the App Store, iCloud, and Developer ID validation all chain to — from a second pinned, signed package. Aging Apple intermediates break things on a frozen OS exactly like expired public roots do.

### 8.4 Replacing Apple's fossilized tools

Some of the OS's TLS surface is beyond trust stores entirely: the `/usr/bin/openssl` on 10.11 is from the 0.9.8 era and cannot speak modern TLS, full stop. For that, the core orchard ships `[system-patch]` packages — a declared, consent-gated, fully reversible mechanism that backs up the Apple original to the byte and replaces it with a symlink into your aslice generation. You opt in per package, per operation; `aslice system-patch list` shows what's currently replaced; `aslice system-patch restore <path>` puts the original back and verifies its hash. It's the narrowest, loudest category in the system, and `man aslice-system-patch` — plus DESIGN §12.11 — is the honest accounting of what it does and doesn't guarantee.

---

## 9. Repositories, trust, and staying offline

### 9.1 Where packages come from

Out of the box, aslice is configured with the project's own repository — the core and extended orchards, compiled, signed, and pre-pinned into the bootstrap. You don't have to configure anything, and you shouldn't have to think about this chapter at all until you add a second source.

A **repository** is a static, signed tree: metadata, the package index, formulae, and the blobs (slices, plus a copy of every source archive the farm ever fetched — so an upstream vanishing breaks nothing already published). Anyone can host one, including you (AUTHORING §11), and mirrors are just full copies: if the project's host is unreachable, aslice fails over across the repository's declared mirrors automatically.

### 9.2 Adding repositories and trust levels

```
aslice repo add https://repo.example.org
```

Adding a repository pins its signing key's fingerprint on first use, displays it, and recommends you verify it out of band. Any later change to that key is a loud, blocking event — that is precisely the moment a hijack would announce itself, so aslice treats it as one until you re-pin deliberately (`aslice repo re-pin`).

Every repository has an enforced trust level, which is a set of capabilities, not a label:

| Level | What it means | Binaries? | Root daemons, kexts? | `[system-patch]`? |
|---|---|---|---|---|
| **official** | The project's own; pre-pinned | yes | yes | yes |
| **verified** | Community repos countersigned by the project; ship disabled | yes, once enabled | yes | only with an explicit per-repo grant from you |
| **third-party** | You added it; key pinned on first use | yes | never | never |
| **local** | Your own `file://` tree | formulae by default | yes (your machine, your authority) | yes |

`aslice repo enable <name>` turns on a verified repo — enabling *is* the consent, so its binaries install immediately. `aslice repo list`, `repo keys`, and `repo audit <name>` show the state of your sources. The one thing no repository at any level can do is make aslice execute package code at install time; that door is closed structurally.

When two repositories offer the same package name, aslice asks you once, remembers the answer, and re-asks if the situation changes; `aslice repo resolutions` shows your answers, and `repo:pkg` addressing (`audiolab:convolver`) bypasses the question entirely.

### 9.3 What "verified" and "signed" do and don't mean

Signatures and trust levels answer narrow questions precisely: *are these bits exactly what this repository published, and how much did I decide to trust this repository?* They do not make claims about the software's behavior — a signed, verified slice of malicious software is still malicious software, now with better paperwork. The design's honesty section (DESIGN §10.7) says this at length; the short version is that aslice's guarantees are about provenance and integrity, and it never pretends otherwise in its messages.

### 9.4 Checking what you're running

```
aslice audit                  # known vulnerabilities (CVEs) in your installed set
aslice provenance ffmpeg      # who built this, from what source, with what toolchain
```

`audit` matches your installed set against public vulnerability feeds, works offline against a cached copy of the feed, and reports affected-version ranges. Packages past their upstream's end-of-life are surfaced here too, and need `--allow-eol` to install in the first place.

### 9.5 Working offline

aslice assumes connectivity will be intermittent — many of its users are audio rigs and lab machines that are offline by policy. Everything already downloaded (slices in the cache, the index snapshot) works without a network. Installs of cached slices work. `aslice doctor --offline` checks health without trying the network, and reports the age of your cached index instead of failing on unreachable repositories. A stale index never blocks operations against the cache; it just means "newest" means "newest as of" the snapshot date, which aslice prints.

---

## 10. aslice and Homebrew

The two coexist by construction: aslice lives in `/opt/aslice` and never touches `/usr/local`, in either direction. Run both as long as you like. `aslice doctor` notices a Homebrew installation and advises on `PATH` ordering — that's the extent of the interaction.

When you're ready to move:

```
aslice adopt --from-homebrew
```

It reads your Homebrew installation, maps the packages you explicitly installed (not their dependencies) to aslice formulae — translating old `--with-*` options to aslice variants where an equivalent exists, and Casks to vendor-binary packages where one is packaged — and produces an install plan. It recreates *intent*, not bytes: Homebrew's files are never reused or modified, and removing Homebrew afterwards (or not) is your call.

---

## 11. When something goes wrong

### 11.1 Start with doctor

```
aslice doctor
```

Read-only, fast, offline-capable, and every finding names its remedy — not "store integrity error" but "store path `x264-0.164-0+core.v3` fails manifest hash (1 file) — quarantine with `aslice store verify --quarantine x264` and reinstall." Exit codes are scriptable: 0 healthy, 1 warnings, 2 failures. `doctor --fix` performs only the repairs that can't lose data (pruning dangling cache entries, re-linking a broken generation symlink to its recorded target, refreshing stale index snapshots), announcing each before it acts; anything else, it hands you the command.

### 11.2 Read the log

aslice logs everything it does to `log/` inside the prefix — structured, local, and never transmitted anywhere (the no-telemetry charter applies to logs exactly as to metrics).

```
aslice log --last-op          # exactly what the last operation did
aslice log --follow           # live
aslice log --level debug      # more
```

`doctor`'s footer points at the relevant log files and the last operation ID. When you file an issue, `aslice log --last-op` is the excerpt maintainers need — generated locally, attached by you, never auto-submitted.

### 11.3 Common problems

| Symptom | What's happening | The fix |
|---|---|---|
| `curl`/`git` fail with certificate errors on a fresh install | The OS trust store expired years ago | `aslice ca-update`, then open a new shell (or `aslice shellenv`) |
| Safari can't reach a site even after `ca-update --keychain` | The site's TLS requirements exceed the OS's crypto stack; keychain imports fix trust, not crypto | Use aslice's curl, or a browser with its own TLS stack |
| The installer can't fetch anything at all | TLS-dead machine: expected on old releases | Nothing — it falls back to plain HTTP for the same hash-pinned files, loudly, and verifies them identically |
| A service won't start after an upgrade | aslice health-checked it and is waiting for your decision | Read the shown log path; answer the rollback prompt, or `aslice rollback` later |
| "repository key pin changed" | The repo's signing key differs from your pin — rotation or hijack, and aslice can't tell which | Verify the new fingerprint out of band; only then `aslice repo re-pin` |
| A package wants SIP disabled | It's a declared `[system]` package (kexts, low-level dev tools) | Follow the printed Recovery instructions, or don't install it — the warning is the feature |
| `php` resolves to the wrong version | Session, project, or default selection, in that order | `aslice which php` traces the resolution |
| aslice and Homebrew binaries shadow each other | `PATH` ordering | `aslice doctor` (coexistence group) prints the exact edit |
| Disk pressure | Cache or old generations | `aslice clean --dry-run`, `aslice gc --dry-run`, then lower the watermarks (§12) |
| Something in the store fails verification | Corruption or tampering; both are treated as security events | `aslice store verify --quarantine <pkg>`, reinstall, and keep the log |
| After a macOS update, a `[system-patch]` behaves oddly | The update restored or replaced the Apple file under the symlink | `aslice doctor` reports the drift with reapply/restore options — never silently re-patches |

---

## 12. Configuration reference

aslice's configuration file is `etc/aslice.toml` inside the prefix (`~/.aslice/etc/aslice.toml` for per-user installs). Edit it directly or via `aslice config set <key> <value>`. The keys, as of this writing:

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

`aslice doctor`'s environment group lists every `ASLICE_*` variable currently overriding configuration — overrides are shown, never hidden.

The prefix layout, for orientation: `store/` (immutable packages), `profiles/generations/` (the symlink forests), `shims/` (runtime multiplexing, ahead of the profile on `PATH`), `apps/` (vendor `.app` bundles), `cache/`, `log/`, `db/state.sqlite` (the state database), `etc/aslice.toml`.

---

## 13. Getting help

- **`aslice help <command>`** prints the same text as `man aslice-<command>` — the man pages and the CLI help are one source, so they can't drift apart. `man aslice` is the index of all of them.
- **This manual** is the prose version; [DESIGN.md](DESIGN.md) is the why; [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) is the schema.
- **Bugs and package requests** go to the project tracker. Attach the output of `aslice log --last-op` and `aslice doctor --json`; both are generated locally and contain nothing you haven't seen. Expect the conduct norms in [CONTRIBUTING.md](../CONTRIBUTING.md): be decent, assume good faith, say plainly when something is wrong.

---

## Appendix. Command quick reference

| Command | What it does |
|---|---|
| `install` / `reinstall` | Install packages (binary first); repair a damaged profile entry |
| `uninstall` / `autoremove` / `mark` | Remove packages; collect unneeded dependencies; fix request records |
| `upgrade` / `outdated` | Move everything (or one package) forward; preview what would move |
| `pin` / `unpin` | Hold a package against upgrades (one argument) — or pin a project to a runtime stream (two, §6) |
| `search` / `info` / `flavors` / `why` / `leaves` | Find packages and inspect them |
| `history` / `rollback` / `switch-generation` | Travel through generations |
| `gc` / `clean` / `store verify` | Reclaim store, reclaim cache, tripwire store integrity |
| `use` / `default` / `versions` / `which` | Runtime stream selection and introspection |
| `service list/status/start/stop/restart/run` | launchd service lifecycle |
| `ca-update` (+ `--keychain`, `--crypto`, `--apple-certs`) | Heal TLS: bundle, keychain, crypto stack, Apple's roots |
| `repo add/list/enable/keys/audit/prefer` | Manage package sources and trust |
| `audit` / `provenance` | CVE report; build provenance |
| `doctor` / `log` | Health battery; the local operation log |
| `adopt --from-homebrew` | Migrate an existing Homebrew leaf set |
| `self-update` | Update aslice itself (health-checked, auto-rollback) |
| `shellenv` / `init` | Print shell environment; print shell integration |
| `exec` / `test` / `livecheck` | Run in a temporary view; run a package's smoke tests; check for newer upstream releases |
| `system-patch list/status/restore` | Inspect and reverse declared system-file replacements |
| `help` | The man page for any command, in your terminal |
