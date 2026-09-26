# aslice Manual

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

**The user guide for aslice — a package manager for Intel macOS.**

- **Status:** v0.22 — September 2026
- **Project home:** [aslice.sh](https://aslice.sh) — homepage, documentation (aslice.sh/docs), and the public dashboard (aslice.sh/dashboard); the installer is served from get.aslice.sh (§2).
- **Audience:** people who install and run software with aslice; that is most of what follows. If you *write* packages, read chapters 1–4 and then move to [AUTHORING.md](AUTHORING.md). If you want to know *why* things are the way they are, the rationale lives in [DESIGN.md](DESIGN.md).
- **Companions:** the man pages in [man/](../man/) (also available as `aslice help <command>`), [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md), [ORCHARD-POLICY.md](ORCHARD-POLICY.md), [REPOSITORIES.md](REPOSITORIES.md), [GENESIS.md](runbooks/GENESIS.md), [TOOLCHAIN.md](TOOLCHAIN.md).
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md) — project terms, acronyms, and the Homebrew translation table.

---

Navigation: [1. Overview](#overview) · [2. Installing aslice](#installing-aslice) · [3. Everyday commands](#everyday-commands) · [4. How installs actually work](#how-installs-actually-work) · [5. Rollback and generations](#rollback-and-generations) · [6. Managing runtimes: PHP, Python, Ruby, Node](#managing-runtimes-php-python-ruby-node) · [7. Running services](#running-services) · [8. Keeping TLS alive on an old OS](#keeping-tls-alive-on-an-old-os) · [9. Repositories, trust, and staying offline](#repositories-trust-and-staying-offline) · [10. One file, one command: rebuilding a machine](#one-file-one-command-rebuilding-a-machine) · [11. aslice and Homebrew](#aslice-and-homebrew) · [12. When something goes wrong](#when-something-goes-wrong) · [13. Configuration reference](#configuration-reference) · [14. Getting help](#getting-help) · [Appendix. Command quick reference](#appendix-command-quick-reference)

<a id="overview"></a>

## 1. Overview

aslice is a package manager for Intel Macs running macOS 10.11 (El Capitan) through 12 (Monterey). It exists because Homebrew is leaving this platform: no new Intel bottles, no CI, and an announced date for dropping Intel entirely. The machines are still good. The software pipeline is what's disappearing, so this project rebuilds it.

Three facts about aslice explain almost everything else:

**Binary installation is payload-only by default.** Packages arrive as *slices* — prebuilt, signed, compressed archives. To install one, aslice verifies the signature, checks every file against the manifest, and links the result into place. Undeclared package scripts never execute. There is one declared exception — the *graft*, for software whose installer script genuinely cannot be declarative (audio DSP drivers, pro-video plugins): it runs only after you have read its declared behavior and approved it, confined to exactly what it declared, with everything it changes recorded for rollback (§4.5).

**Old states of your system are kept, and you can go back to them.** Installed packages live in an immutable store; what you actually use is a *generation*, a view of the store made of symlinks. Every install, upgrade, or uninstall builds a new generation and then flips a single symlink. When an upgrade breaks something, `aslice rollback` restores managed state through a journal; conflicts or reboot requirements can leave recovery pending.

**It accounts for old machines.** aslice detects your CPU and serves the fastest build that CPU can execute; there are three *flavors* — baseline, SSE4.2, and AVX2. It ships a current CA certificate bundle, because the one in your OS expired years ago. And when it cannot do something — a package needs SIP disabled, a vendor binary is pointer-only and comes from the vendor's own server, Safari's TLS stack is too old for a site no matter what it installs — it tells you so, instead of failing mysteriously later.

Finally, a fact about the project rather than the software: **aslice collects nothing.** No telemetry, no analytics, no install IDs, no crash reporting — not even opt-in. There is no switch to turn off because there is no wiring. It is infrastructure, not a product.

<a id="the-vocabulary"></a>

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

<a id="the-five-minute-mental-model"></a>

### 1.2 The five-minute mental model

1. The **store** holds every version of every package you've installed, each in its own directory. Nothing inside it ever changes after registration.
2. Your **generation** is a directory of symlinks into the store, and it is what your `PATH` actually points at.
3. Installing or upgrading builds a *new* generation and then swaps one symlink. The old generation remains available. External writes use a durable journal; a crash during activation requires recovery, and rollback can require conflict resolution or reboot.
4. Packages are **binary by default**. Source builds happen only when you ask for non-default variants or custom compiler flags, and even then the result interoperates with the prebuilt world: compatibility is checked against the libraries' actual interfaces, not their provenance.
5. Everything aslice fetches — slices, index metadata, the CA bundle, aslice itself — is signed and hash-pinned. A verification failure blocks the operation and is always reported; it cannot be silenced.

If you remember store + generations + signed everything, the rest of this manual is details.

<a id="helpers-and-background-services"></a>

### 1.3 Helpers and background services

During an install, the client starts temporary helpers to fetch, extract, and link
packages; source builds also use a sandboxed build helper. Ordinary operations run
as your user. Declared privileged changes go through `aslice-system`, with
per-operation authorization and independently verified code and dependencies in
protected root-owned storage.

Those helpers finish with their work. A package service, such as PostgreSQL, can
keep running under launchd after the command exits: user agents run as you, while
root daemons require the privileged helper. A runtime shim has a shorter job: it
selects an installed runtime and replaces itself with that program. The current
design requires no persistent aslice daemon; the proposed multi-user daemon is
future work.

[HELPERS.md](HELPERS.md) describes each role, its access boundaries, and how managed
effects are removed. Service commands are in §7 and decommission is in §2.5. These
are design contracts, not claims of completed implementation or platform validation.

---

<a id="installing-aslice"></a>

## 2. Installing aslice

<a id="what-you-need"></a>

### 2.1 What you need

- An Intel Mac (2007 or later, 64-bit — every Mac that runs these releases qualifies) running macOS 10.11 through 12.
- A few hundred megabytes of disk for the toolchain and the core packages, plus room to grow. Because the store keeps old generations, plan on gigabytes if you install a lot.
- An internet connection for the install itself. Afterwards, aslice works offline against its cache and degrades gracefully (§9.5).

You do **not** need Xcode or the Command Line Tools. aslice brings its own toolchain ([TOOLCHAIN.md](TOOLCHAIN.md)).

<a id="the-installer"></a>

### 2.2 The installer

The installer is a short shell script — short enough to read before running, which you should do:

```sh
curl -O https://get.aslice.sh/install.sh
less install.sh          # it's about 200 lines; read it
sh install.sh
```

The script fetches two things: the aslice bootstrap binary, and the root of aslice's update metadata. Both are pinned by hash inside the script and cross-checked against a signed checksums file served over a second, independent transport; everything after that first step is verified by aslice's own update framework. It does not ask for your password, with one optional exception — it offers to run `sudo` once, to create `/opt/aslice` and hand it to your user account. Say no if you'd rather not (or don't have admin rights), and it installs to `~/.aslice` instead. The two layouts are fully supported and behave identically; only the path differs.

**If your Mac's TLS cannot fetch the installer**, download the bootstrap kit on a supported machine and transfer it offline. Verify its SHA-256 with `/usr/bin/shasum -a 256` against an independently authenticated published digest before running anything. The verified bootstrap binary checks signatures. HTTP is permitted only for later files whose authentic hashes are already established; it cannot authenticate the first script. See [STATE-AND-RECOVERY §7](STATE-AND-RECOVERY.md#persistent-trust-and-initial-bootstrap).

<a id="after-the-install"></a>

### 2.3 After the install

Add aslice to your shell. For zsh (the default since Catalina):

```sh
eval "$(/opt/aslice/bin/aslice init zsh)"     # or ~/.aslice/bin/aslice for a per-user install
```

For bash (the default on 10.11–10.14):

```sh
eval "$(/opt/aslice/bin/aslice init bash)"    # same per-user path applies
```

To make it permanent, add that line to your `~/.zshrc` or `~/.bash_profile`. Then verify:

```sh
aslice doctor
```

`doctor` runs a battery of checks — CPU flavor, store integrity, repository freshness, trust-store state — and prints either a one-line "healthy" or a list of findings, each paired with the command that fixes it. On a fresh install of an old OS it will usually have one suggestion: `aslice ca-update`. Run it. The short version of what that does: it replaces your OS's long-expired certificate trust store with a current one, so `curl`, `git`, and `python` can talk to the modern web. Chapter 8 gives the long version.

<a id="updating-aslice-itself"></a>

### 2.4 Updating aslice itself

aslice updates itself like any other package:

```sh
aslice self-update
```

The update is signed and verified like any package, installed as a new generation, and health-checked after tentative activation but before commit. A failed manager smoke test reverses tentative activation; restoration after a durable commit is a new transaction preserving trust and history. `aslice self-update --check` reports without installing, and `aslice pin aslice` holds the manager in place if you never want it to move.

<a id="removing-aslice"></a>

### 2.5 Removing aslice

Keep the manager and its backups until managed external effects have been removed:

```sh
aslice decommission --dry-run
aslice decommission
```

The plan restores the previous login shell, unregisters services, reverses supported grafts and patches, removes managed kexts and owned certificate changes, and lists remaining data and shell-integration lines. Conflicts or a required Recovery/reboot leave cleanup pending; do not delete the prefix. Protected-volume restoration follows [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md).

After successful cleanup, decommission prints the exact prefix that can be deleted and any retained user data. It never deletes application databases or ecosystem userbases merely because the manager is removed. See [STATE-AND-RECOVERY §6](STATE-AND-RECOVERY.md#6-self-update-and-decommission).

<a id="everyday-commands"></a>

## 3. Everyday commands

This chapter covers the dozen commands that make up daily use. Each command family has its own man page — `man aslice-repo`, `man aslice-service`, `man aslice-system-patch`, and so on, all indexed on `man aslice` — and `aslice help <command>` prints the same text in your terminal.

<a id="finding-and-installing-software"></a>

### 3.1 Finding and installing software

```sh
aslice search ffmpeg          # names and descriptions matching "ffmpeg"
aslice info ffmpeg            # versions, variants, dependencies, size, provenance
aslice install ffmpeg
```

`install` selects the newest eligible requested version, then prefers a binary for that selection. It resolves your request against the index, picks the newest version that runs on your OS release and the fastest flavor your CPU executes, downloads the slices, verifies them, and links a new generation. A typical run prints the plan, then the result:

```console
$ aslice install ffmpeg
==> Plan: install ffmpeg 7.1 (v3, 14.2 MB) + 6 dependencies (31.8 MB total)
==> Fetching 7 slices... done (4.1s)
==> Verifying signatures and hashes... done
==> Linking generation 43... done
ffmpeg 7.1 installed. Run `aslice rollback` to return to generation 42.
```

You can install a space-separated batch from several orchards in one transaction:

```sh
aslice install ffmpeg audiolab:convolver --variant ffmpeg:+x265
```

The plan shows each package's effective settings. Package-specific options must
identify their package in a batch; ambiguous options refuse before changes.
A pre-commit failure rolls back the whole managed-state batch. A service health
failure after commit returns nonzero and says the installation committed.

Useful variations:

```sh
aslice install ffmpeg@v6              # a specific major version
aslice install ffmpeg --dry-run       # print the full plan, change nothing
aslice install ffmpeg --explain       # show why the solver chose each version
aslice install audiolab:convolver     # a package from a specific added repository
```

**Building from source.** You never need to, but you can:

```sh
aslice install ffmpeg --build-from-source                  # compile it here
aslice install ffmpeg --variant +x265 --cflags="-O3"       # non-default options
aslice install ffmpeg --cflags="-O3 -march=native" --lto   # tuned to your machine
```

Custom-flag builds can use prebuilt dependencies when their ABI evidence, dependent tests, and CPU/OS requirements permit it (§4.3). A `-march=native` ffmpeg records the selected CPU features; sharing a compatibility key does not make it usable on every machine. Unsupported ABI-changing flags are rejected unless covered by a declared ABI variant, and unknown effects require an isolated build and explicit dependency validation ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)). A non-default *feature* variant (`--variant`) may or may not have a prebuilt slice; when it doesn't, aslice discloses the source work and obtains consent before building locally. Either way, the plan tells you which before anything downloads.

**Shadowed packages and `link`.** A package can be installed into the store without being linked into your profile — the principled keg-only case, declared `link = false` in the formula with a mandatory `link_reason`, usually because the package shadows something macOS ships (OpenSSL, curl). `aslice info` shows the reason. `aslice link openssl3` opts in per profile, `aslice unlink openssl3` backs out, and each flip is a new generation, so `rollback` undoes it like anything else. Packages that declared the dependency build and run against the store copy either way ([PACKAGE-FORMAT §3.8](PACKAGE-FORMAT.md#install--declarative-post-install-behavior), [DESIGN §12.1](DESIGN.md#commands)).

A newer eligible source-only version is not skipped for an older cached binary. The plan shows compilation and its dependency reasons before execution. Interactive runs ask for source-build consent; unattended runs require `--allow-source-builds`, including when applying a saved plan. Unknown build durations are shown as unknown.

`aslice upgrade --security` applies the newest eligible fixes; add `--minimal` for the lowest eligible fixed versions satisfying the advisory and dependency constraints. Holds and runtime streams still apply. Every blocked, held, unavailable, or unknown advisory is reported, and exit 3 means remediation remains incomplete, even after a partial successful update. `aslice audit` includes exact active dependencies and embedded components and lists vulnerable retained generations separately. Stale or absent advisories do not establish safety.

After an update, `aslice needs-restarting [--json]` reports restart, consumer rebuild, reboot, and unknown inspection coverage separately. It does not stop processes. See [aslice-needs-restarting(1)](../man/aslice-needs-restarting.1.md) for outcomes.

<a id="upgrading"></a>

### 3.2 Upgrading

```sh
aslice outdated               # what would change, and why
aslice upgrade                # everything, honoring your pins
aslice upgrade ffmpeg         # one package (and what depends on it)
```

An upgrade stages the complete new generation before activation, so a failed download leaves the current software untouched. Power loss during activation or external writes requires journal recovery. If an upgraded package runs a service, aslice stops the service, swaps, and starts it again; and if the new version won't start, it *asks you* whether to roll back instead of guessing (§7.2).

There are three lines `upgrade` never crosses without being told:

- **Pinned packages don't move.** See the next section.
- **Runtime streams don't move.** If you selected PHP 8.4, `aslice upgrade php` installs 8.4 patch releases and never 8.5. Moving to a new stream is a separate decision: `aslice install php@8.5` (§6).
- **Major aslice self-updates ask first**, printing the changelog.

<a id="holding-a-package-pin-and-unpin"></a>

### 3.3 Holding a package: pin and unpin

```sh
aslice pin openssl            # hold: upgrades skip it, outdated says so
aslice unpin openssl
```

A pin is a note in aslice's state database — the files are not frozen, and rollback and reinstall work normally. Pins exist for the classic reason: "everything may move except this one thing production depends on."

One warning about an overloaded word: `aslice pin php 8.4` — a runtime, two arguments — pins a *project directory* to a PHP stream; that is chapter 6. `aslice pin openssl` — a library, one argument — is the hold described here. The two never collide in practice, and each man page spells out which is which.

<a id="removing-software"></a>

### 3.4 Removing software

```sh
aslice uninstall x264         # remove one package
aslice autoremove             # remove anything nothing needs anymore
```

aslice records whether you asked for a package by name or it arrived as a dependency. Once nothing reachable from your explicitly requested set needs a dependency, `autoremove` collects it — the same model as `apt autoremove`. If it ever disagrees with you about a package's status:

```sh
aslice mark ffmpeg --on-request       # "I want this; stop calling it a dependency"
```

Uninstalling removes a package from future generations; old generations still reference it, so rollback keeps working until the garbage collector eventually reclaims it (§5.3).

<a id="reclaiming-disk-clean-and-gc"></a>

### 3.5 Reclaiming disk: clean and gc

Two different things fill up, and two different commands empty them:

- **The cache** — downloaded slices, source tarballs, index snapshots — is pure redundancy. When it grows past a watermark (10 GB by default), `aslice clean` evicts it least-recently-used first, never touching anything younger than 30 days. `--dry-run` shows what would go.
- **The store** — installed artifacts retained by generations, exact dependency bindings, protected closures, transactions, and execution leases. `aslice gc` collects only unreachable artifacts and keeps the last 5 generations by default. A store-size warning begins within the configured margin (10% below the limit by default). At the limit, ask `Run garbage collection? [y/N]`; declining or non-interactive operation performs no collection. See [DESIGN §8.4](DESIGN.md#garbage-collection-discipline) for thresholds and [STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements) and [STATE-AND-RECOVERY §5](STATE-AND-RECOVERY.md#durable-transactions-and-recovery) for retention roots.

Both commands announce what they are doing and why. If disk pressure is chronic, lower the watermarks in `etc/aslice.toml` (§13) instead of running these by hand.

---

<a id="how-installs-actually-work"></a>

## 4. How installs actually work

You can use aslice happily knowing nothing in this chapter. Read it when you want to understand what you're looking at.

<a id="what-a-slice-is"></a>

### 4.1 What a slice is

A slice is a zstd-compressed archive containing its container descriptor, canonical manifest, and payload. The manifest binds file hashes, exact dependencies, recipe, flags, CPU requirements, and ABI evidence. Detached signatures authenticate the delivered archive; SBOMs and variable builder provenance are separate authenticated objects bound to the artifact or archive digest ([SLICE-FORMAT §1](SLICE-FORMAT.md#byte-layout) and [SLICE-FORMAT §2](SLICE-FORMAT.md#content-identity-and-signatures); [STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#compatibility-and-artifact-identity)). `aslice provenance ffmpeg` shows the associated evidence.

Installing a slice has six stages. Materialization runs no undeclared package code;
post-commit readiness checks execute declared services:

1. Authenticate repository metadata and verify the complete archive's length, digest, and package signature.
2. Validate the container descriptor and canonical manifest, then extract into bounded staging.
3. Verify every staged file against the manifest, apply authorized relocation, and register the immutable artifact.
4. Check exact dependency bindings, ABI evidence, and CPU/OS requirements for the proposed package set.
5. Prepare the complete generation, backups, and durable transaction intent before live changes.
6. Apply journaled operations, switch the profile, record the generation in the state database, and commit after reconciliation, then run service health checks while retaining mutation ownership.

Preparation failures leave the live generation unchanged. Before commit, failures after live changes require journal recovery; intervening external edits can require attention, and protected-volume restoration may require Recovery and reboot. Post-commit health failure reports the committed installation. Package rollback does not restore application data ([STATE-AND-RECOVERY §5](STATE-AND-RECOVERY.md#durable-transactions-and-recovery); [SYSTEM-VOLUMES §4](SYSTEM-VOLUMES.md#activation-rollback-and-os-updates)). A graft-bearing package adds one declared, approved, sandboxed step of its own, covered in §4.5.

<a id="flavors-matching-builds-to-your-cpu"></a>

### 4.2 Flavors: matching builds to your CPU

aslice detects the CPU once, at install time. Three flavors exist:

- **v1** runs on every 64-bit Intel Mac, down to the 2007 Core 2 Duo.
- **v2** uses SSE4.2 and POPCNT (Nehalem and later, ~2009+).
- **v3** uses AVX2 (Haswell and later, ~2014+) and is measurably faster on crypto, codecs, and compression — the workloads that dominate real package use.

The solver treats flavor as a hard constraint: a v3 slice is never offered to a machine that cannot execute it, so there is no "illegal instruction" surprise waiting at run time. Because the farm builds all three flavors of everything in the core orchard, the fastest build your machine can run is simply the default. `aslice flavors ffmpeg` shows the matrix for your machine. `aslice config set flavor v1` forces a lower flavor — useful when you are preparing an external drive for an older Mac.

<a id="mixing-binary-and-source-builds"></a>

### 4.3 Mixing binary and source builds

Build variants require compatibility checks against the libraries' published interfaces. Every built package records its provided and required interfaces, exact dependency artifacts, CPU requirements, and evidence quality. Substitution requires adequate ABI evidence and dependent tests on a compatible machine. Incomplete evidence retains the exact provider or requires rebuilding and testing dependents ([STATE-AND-RECOVERY §2](STATE-AND-RECOVERY.md#abi-and-execution-requirements)).

The practical consequences:

- `--cflags="-O3 -march=native"` affects only the package you name; its dependencies stay binary where their contracts are satisfied.
- A locally built library may be a compatible provider while retaining its own artifact identity. Existing consumers keep exact artifact bindings until an explicit rebuild or verified relocation creates a new artifact and reruns dependency tests. `aslice info` records the local-build origin; origin alone neither grants nor prevents substitution.
- If the recorded evidence shows an incompatible interface, the solver refuses the combination and names the mismatch. A scanner cannot detect every ABI or behavioral break; unknown evidence does not count as compatibility.

<a id="variants-briefly"></a>

### 4.4 Variants, briefly

Packages can declare *variants* — optional features like `+x265` or `+ssl`. A variant the author marked as interface-changing gets its own builds, which coexist in the store; a build-flavor variant (debug symbols and the like) triggers a local compile. The full model, including the rules that keep variants from sprawling, is in [AUTHORING §5](AUTHORING.md#variants-and-the-abi-contract). As a user, three things suffice: `aslice info <pkg>` lists a package's variants, `--variant +name` enables one, and aslice tells you whether a prebuilt slice exists for the combination before it starts compiling.

<a id="grafts-when-installing-takes-a-script"></a>

### 4.5 Grafts: when installing takes a script

Some software cannot be reduced to files in a payload. An audio DSP suite registers a plugin with CoreAudio's hardware abstraction layer; a pro-video plugin framework installs a component the host application scans for; a driver bundle loads a kext. Their installers carry scripts, and banning scripts would ban the software — so aslice puts the script under the project's own rules instead. A vendor installer script is a **graft**, and a graft never runs unannounced, unapproved, or unrecorded.

When a package carries grafts, you see them before anything executes:

```console
$ aslice install convolver
convolver 3.1 declares 1 graft:

  Scripts/postinstall  (sha256: 9f2c…d4, runs after payload)
    writes:   /Library/Audio/Plug-Ins/HAL/VendorDSP.driver
    kexts:    none
    daemons:  none
    network:  no
    elevated: yes (via aslice-system)
  manifest: signed (core orchard — farm-rehearsed)

Allow convolver 3.1 to run its script? [y/N]
```

The list you are shown is the whole truth about the script, and it is enforced, not advisory: if the script tries to write outside the listed paths, load an unlisted kext, register an unlisted daemon, or touch the network without declaring it, the sandbox blocks the attempt, the install aborts, and the generation rolls back — with the deviation logged whether or not you asked for verbosity. You are not being asked to trust the script; you are being shown its leash.

Answering no stops the install before execution. Approval binds the repository identity, package version, script hashes, and complete effective behavior-manifest digest; a change to any binding asks again. `aslice graft approvals` lists approvals and `aslice graft revoke <pkg>` withdraws one. Machine-file names select only an existing matching approval; a fresh machine needs a fresh decision ([SETUP §2.8](SETUP.md#grafts)). Scripts run in isolated staging. An elevated effect requires a separately authorized helper commit, never live root execution of the vendor script. Non-interactive installs require `--accept-grafts` where no matching approval exists; privileged effects additionally require the ordinary system capability and consent. Unsigned manifests never receive persistent approval.

One warning matters more than the others. A graft's behavior manifest is normally **signed** — for core and extended packages, the build farm has rehearsed the script in a VM on every OS the package targets and verified that it does exactly what the manifest declares. A third-party repository can serve a graft whose manifest is **unsigned**: nobody has rehearsed anything, and aslice says so in letters you cannot miss before it asks. The decision is yours, taken with open eyes — and approval of an unsigned manifest is never remembered, so you are asked every time.

Supported graft deltas are journaled with before-images and restored through transaction recovery. External edits, missing backups, or inaccessible protected state require attention rather than a silent overwrite. Network, remote, firmware, and other effects outside the supported staging boundary are refused in v1 ([STATE-AND-RECOVERY §4](STATE-AND-RECOVERY.md#graft-execution-boundary) and [STATE-AND-RECOVERY §5](STATE-AND-RECOVERY.md#durable-transactions-and-recovery)).

---

<a id="rollback-and-generations"></a>

## 5. Rollback and generations

<a id="what-a-generation-is"></a>

### 5.1 What a generation is

A generation is one complete, self-consistent state of your installed software — concretely, a directory of symlinks into the store. Your profile, the thing on your `PATH`, is itself a symlink to the current generation. Every mutating operation (install, upgrade, uninstall, rollback itself) creates a new generation and then atomically retargets the profile. The retarget is atomic on both APFS and HFS+, so there is no moment at which your `PATH` points at a half-built state.

<a id="using-it"></a>

### 5.2 Using it

```sh
aslice history                # generations: when, what changed, how big
aslice rollback               # back one generation
aslice rollback 41            # back to a specific one
aslice switch-generation 44   # and forward again — rollback is not destructive
```

Rollback is the answer to "the upgrade broke it." Because old generations are intact, going back is exact: you get the precise files you had, not a re-download of whatever the index currently thinks the old version was.

This also makes experiments cheap. `aslice exec ffmpeg -- ffprobe in.mov` runs a command inside a temporary view with extra packages present and discards the view on exit — you can try something without committing to it.

<a id="housekeeping"></a>

### 5.3 Housekeeping

Generations cost disk, so aslice keeps the last 5 by default, and `aslice gc` reclaims what nothing references (§3.5). Two guarantees are worth repeating here: `gc` never touches a store path a running process is using, and `--dry-run` always shows the full list before anything is deleted.

The store is supposed to be immutable, and aslice treats drift as a security signal:

```sh
aslice store verify                    # re-hash everything against the manifests
aslice store verify --quarantine x264  # pull a failing path out of service
```

A store file that no longer matches its manifest means disk corruption or tampering — there is no legitimate third option. Quarantine removes the path from all future generations (dependents are reported), and reinstalling restores a verified copy.

---

<a id="managing-runtimes-php-python-ruby-node"></a>

## 6. Managing runtimes: PHP, Python, Ruby, Node

Runtimes are the packages people keep in several versions at once — and historically the place where version managers (nvm, pyenv, rbenv) grew up as separate tools, fighting the package manager over your `PATH`. aslice builds that job in. If you never touch PHP, Python, Ruby, or Node, skip this chapter.

<a id="streams-and-installing-them"></a>

### 6.1 Streams, and installing them

A runtime is a single formula with several maintained *streams*: PHP has 8.3, 8.4, 8.5; Python has 3.11, 3.12, 3.13. Streams coexist:

```sh
aslice install php@8.4        # ordinary install, sits next to every other stream
aslice install php@8.5
```

Installing a stream never changes which `php` you get — selection is always explicit. That is what makes `aslice upgrade` safe on a machine that serves things: upgrades move within your selected stream, never across streams.

<a id="selecting-session-project-default"></a>

### 6.2 Selecting: session, project, default

Three levels, resolved in this order, first match wins:

```sh
aslice use php 8.5            # this shell only (session)
aslice pin php 8.4            # this project tree, recorded in ./aslice.toml — commit it
aslice default php 8.4        # everything else: cron, services, stray shells
```

- **Session** selection is an environment variable, `ASLICE_USE_PHP`. `aslice use` prints it and, with the shell integration from `aslice init`, sets it for you. It dies with the shell, and it is visible in `env`.
- **Project** selection is a file, `aslice.toml`, found by walking up from your working directory. One file pins every runtime in the repo — PHP and Node side by side — and it is meant to be committed, alongside `composer.json` or `package.json`.
- **Default** is the fallback, recorded in aslice's state database.

`aslice which php` traces the whole resolution — which level matched and why, down to the store path — so "what am I actually running?" is always one command away. `aslice versions php` shows the matrix: installed streams, current selections, and which extensions each stream has.

Under the hood, a directory of small *shims* sits ahead of the profile on your `PATH`. A shim resolves the selection and `exec`s the real binary — no wrapper process, sub-millisecond overhead. Services and scripts that must name an exact version use the versioned aliases (`php8.4`) instead; those never move under you.

<a id="extensions-and-ecosystem-tools"></a>

### 6.3 Extensions and ecosystem tools

Compiled extensions — `php-redis`, `ruby-pg` — are ordinary aslice packages bound to one runtime stream. Installing one builds (or downloads) it against your currently selected stream. A patch upgrade within the stream leaves extensions alone; installing a new stream offers to provision your previous stream's extension set for it. And because runtime and extensions live in the same generation, a rollback restores them together.

The ecosystems' own installers keep working too: `pip install`, `gem install`, `npm i -g`, `pecl install`, `composer global require`. The shim routes each into a per-stream, per-user directory (`~/.aslice/runtimes/php/8.4/` and friends), so a `pip install` under Python 3.12 is invisible to 3.13. aslice never manages, audits, or deletes those directories; when you uninstall a stream, it warns you about the orphaned directory rather than removing it.

Tools that run *on* a runtime without compiling against it — composer, yarn, prettier, poetry — install once and follow your selection: composer always runs under your selected PHP and switches when you switch. That behavior is a property of the tool's formula; there is nothing to configure.

---

<a id="running-services"></a>

## 7. Running services

<a id="the-command"></a>

### 7.1 The command

Packages that provide services — nginx, PostgreSQL, Redis, dnsmasq — declare them in their formula, and aslice manages them as real launchd jobs:

```sh
aslice service list                 # everything aslice manages
aslice service status postgresql    # pid, state, last exit — launchd's truth, not a pidfile
aslice service start redis
aslice service stop redis
aslice service restart redis
aslice service run redis            # foreground, unregistered — for debugging
```

User-level services run as you, need no sudo, and may come from any repository. Root-level daemons are the privileged exception: they install and run through aslice's audited privileged helper, with explicit per-operation consent, and only official, verified, or local repositories may offer them (§9.2).

User-service overrides live in `~/.config/aslice/services/<pkg>.env`. Root services use separately validated, helper-owned configuration and a protected executable/library closure; they never execute from a user-writable profile. You never edit the generated plist, and upgrades never clobber your overrides.

<a id="upgrades-and-the-rollback-prompt"></a>

### 7.2 Upgrades and the rollback prompt

An upgrade never replaces the binary out from under a running service. The sequence: build the complete new generation while the service keeps running; stop the affected jobs — and only those, so an ffmpeg upgrade never bounces your database; swap the generation; reconcile and commit; start the jobs and health-check them. Checks default to 60 seconds per service, with positive finite overrides. A failed or timed-out check returns nonzero and explicitly reports committed installation.

If a service fails to start after an upgrade, aslice shows you the failure and asks:

```text
error: installation committed; service nginx failed to start after the upgrade (launchd exit status 78;
log: /opt/aslice/profiles/default/var/log/nginx/error.log)
The previous generation (nginx 1.26.2, generation 41) is retained.
Rollback is available only after service-data compatibility has been verified.
Roll back and restart the previous version? [y/N]
```

Before a service upgrade that can migrate data, require a declared backward-compatibility contract or an authorized tested backup/restore procedure. Otherwise refuse the automated upgrade of the running service. After readiness failure, offer rollback only when that contract permits it. Yes starts a journaled rollback; No retains failure evidence. Non-interactive failures return failure unless `--rollback-on-service-failure` explicitly selects an eligible rollback. Generation rollback does not restore application databases by itself ([STATE-AND-RECOVERY §5](STATE-AND-RECOVERY.md#durable-transactions-and-recovery)). Machine apply also rolls back its entire managed-state transaction on pre-commit failure; a post-commit health failure reports committed installation ([SETUP §3.6](SETUP.md#failure-handling)).

---

<a id="keeping-tls-alive-on-an-old-os"></a>

## 8. Keeping TLS alive on an old OS

The most common day-one failure on 10.11–10.13 is not a missing library — it is TLS itself. The system's certificate trust store froze years ago: roots expired, modern roots never arrived, and everything that relies on the store — the curl and git you just installed, but also Safari and Mail — inherits the rot. `aslice ca-update` is the fix, applied in layers; every layer after the first is optional, and each says what it can and cannot do.

<a id="the-bundle-the-layer-everyone-wants"></a>

### 8.1 The bundle (the layer everyone wants)

`aslice ca-update` updates the signed private CA bundle. `shellenv` points compatible aslice clients at it; certificate refresh does not itself add TLS protocols. `--crypto` separately upgrades aslice's crypto providers. PEM extraction omits some browser trust restrictions and is not equivalent to Firefox's trust policy. `--check` reports age without changing anything. See [STATE-AND-RECOVERY §9](STATE-AND-RECOVERY.md#certificate-trust-lifecycle).

<a id="the-system-keychain-safari-mail-and-friends"></a>

### 8.2 The System keychain (Safari, Mail, and friends)

`aslice ca-update --keychain` asks the protected helper to apply a signed certificate-policy inventory. The inventory distinguishes roots from intermediates and records purposes, restrictions, and retirement. If an OS cannot represent a required restriction, the import is refused. A raw PEM bundle is not sufficient authority for system trust.

Admin authorization is required each time. The helper records entries it owns and retires only those entries when policy changes. `--keychain-remove` removes its recorded imports after checking for external changes; Apple and independently installed user entries remain untouched. This updates trust, not the OS's TLS implementation. It cannot guarantee that an old browser or service protocol will work.

<a id="the-crypto-stack-and-apples-own-roots"></a>

### 8.3 The crypto stack and Apple's own roots

`aslice ca-update --crypto` upgrades compatible aslice crypto-provider packages without replacing the OS TLS stack. `--apple-certs` applies the separately signed Apple certificate inventory under the same purpose, role, constraint, ownership, and retirement rules. Importing an intermediate never promotes it to a root. Named Apple services require chain validation and per-OS integration tests; certificate import alone is not a repair guarantee.

<a id="replacing-apples-fossilized-tools"></a>

### 8.4 Replacing Apple's fossilized tools

Declared `[system-patch]` packages replace narrowly allowed Apple-provided tools or data with explicit per-operation consent. Originals and replacement dependency closures live in protected helper-owned storage, outside a user-writable profile. Backups are identified by OS build and volume baseline.

Writable targets use journaled file replacement. Catalina's read-only system volume requires the Recovery workflow; Big Sur and Monterey additionally require preparation and verification of a new boot snapshot. A patch remains pending until reboot verification succeeds. `aslice system-patch restore <path>` selects the appropriate restoration backend and refuses to overwrite a newer OS baseline with an older backup. See [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md) and aslice-system-patch(1) for the consent, backup, security-state, and recovery requirements.

<a id="repositories-trust-and-staying-offline"></a>

## 9. Repositories, trust, and staying offline

<a id="where-packages-come-from"></a>

### 9.1 Where packages come from

Out of the box, aslice is configured with the project's own repository: the core and extended orchards, compiled, signed, and pre-pinned into the bootstrap. There is nothing to configure, and no reason to think about this chapter at all until you add a second source.

A **repository** is a static, signed tree: metadata, the package index, formulae, and the blobs — slices, plus a copy of every source archive the farm ever fetched, so an upstream vanishing breaks nothing already published. Anyone can host one, including you ([AUTHORING §11](AUTHORING.md#publishing-your-own-orchard-and-repository)). Mirrors are full copies, and if the project's host is unreachable, aslice fails over across the repository's declared mirrors automatically.

<a id="adding-repositories-and-trust-levels"></a>

### 9.2 Adding repositories and trust levels

```sh
aslice repo add https://repo.example.org
```

Adding a repository pins its signing key's fingerprint on first use, displays the fingerprint, and recommends that you verify it out of band. Authenticated TUF root rotation follows the old and new signature thresholds from the retained anchor. An unauthenticated key replacement blocks the repository; explicit re-pinning requires independent verification ([STATE-AND-RECOVERY §7](STATE-AND-RECOVERY.md#persistent-trust-and-initial-bootstrap)).

Every repository carries an enforced trust level — a set of capabilities, not a label:

| Level | What it means | Binaries? | Root daemons, kexts? | `[system-patch]`? |
|---|---|---|---|---|
| **official** | The project's own; pre-pinned | yes | yes | yes |
| **verified** | Community repos countersigned by the project; ship disabled | yes, once enabled | yes | only with an explicit per-repo grant from you |
| **third-party** | You added it; key pinned on first use | yes | never | never |
| **local** | Your own `file://` tree | formulae by default | yes (your machine, your authority) | yes |

`aslice repo enable <name>` turns on a verified repo; enabling *is* the consent, so its binaries install immediately afterwards. `aslice repo list`, `repo keys`, and `repo audit <name>` show the state of your sources. One thing no repository at any level can do is make aslice execute package code at install time outside the graft mechanism (§4.5) — and even a graft needs your explicit approval, so the door stays closed to surprise.

Only core packages use bare names. Every other repository requires its prefix, including `extended:package`. `audiolab:convolver` and `plugins:convolver` are different identities; there is no overlap prompt, preference, or automatic fallback. Search shows qualified alternatives, and you choose one explicitly ([REPOSITORIES §10](REPOSITORIES.md#overlapping-packages-across-repositories)).

<a id="what-verified-and-signed-do-and-dont-mean"></a>

### 9.3 What "verified" and "signed" do and don't mean

Signatures and trust levels answer narrow questions precisely: *are these bits exactly what this repository published, and how much did I decide to trust this repository?* They do not make claims about the software's behavior — a signed, verified slice of malicious software is still malicious software, now with better paperwork. The design document's limitations section ([DESIGN §10.7](DESIGN.md#what-this-does-not-solve)) says this at length; the short version is that aslice's guarantees are about provenance and integrity, and it never pretends otherwise in its messages. For graft-bearing packages (§4.5) the question extends to the behavior manifest: a signed manifest means the farm — or, one trust level down, a verified repository under its own vouched key — rehearsed the script and verified it behaves as declared, while an unsigned manifest means nobody did, and the client says so loudly at the install decision.

<a id="checking-what-youre-running"></a>

### 9.4 Checking what you're running

```sh
aslice audit                  # known vulnerabilities (CVEs) in your installed set
aslice provenance ffmpeg      # who built this, from what source, with what toolchain
```

`audit` matches your installed set against public vulnerability feeds, works offline against a cached copy of the feeds, and reports affected-version ranges. Packages past their upstream's end-of-life are surfaced here too; they need `--allow-eol` to install in the first place.

<a id="working-offline"></a>

### 9.5 Working offline

Offline mode reuses cached bytes only with retained receipts proving verification while metadata was valid. It rehashes those bytes, respects known revocations, prints verification time and index age, and makes no freshness claim. New metadata or uncached targets require current TUF authorization; losing trust receipts is a recovery event, not permission to accept expired metadata. Historical installs use a currently authorized archive catalog ([STATE-AND-RECOVERY §8](STATE-AND-RECOVERY.md#plans-locks-archives-and-offline-use)).

---

<a id="one-file-one-command-rebuilding-a-machine"></a>

## 10. One file, one command: rebuilding a machine

<a id="the-idea"></a>

### 10.1 The idea

A Mac that comes back from system recovery is blank. Getting from blank to *ready to work* is normally an afternoon of remembering — which packages mattered, how the Dock was set up, which shell, which services, which PHP the projects expect. aslice can hold all of that in one declarative file, `aslice-machine.toml`, and replay it with one command:

```text
# on the blank Mac: install aslice itself first (§2), then:
aslice machine apply aslice-machine.toml          # or: aslice machine apply https://example.org/my/aslice-machine.toml
```

Packages install, runtime streams are selected, services start, Dock and Finder preferences are written, the login shell is enrolled and set — each step planned and shown to you before anything changes. Because the file is plain text, it is also something to *share*: one file instead of forty screenshots of System Settings, diffable and version-controlled like any code.

The other direction exists too: `aslice machine export` captures a machine you have already set up into a fresh `aslice-machine.toml` (§10.4).

The full schema and the precise semantics live in [SETUP.md](SETUP.md); this chapter is the tour.

<a id="the-file"></a>

### 10.2 The file

```text
# aslice-machine.toml — declarative system setup. Apply: aslice machine apply
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

Two properties are worth knowing before you trust it. First, the file is **data, never code**: nothing in an `aslice-machine.toml` executes. Applying a stranger's file has a bounded blast radius, and you see the plan first. Second, the file is a *wishlist*, not an exact snapshot — "ffmpeg 7" resolves against today's index. For bit-exact reproduction there is the lock file ([PACKAGE-FORMAT §7](PACKAGE-FORMAT.md#lock-files)), replayed with `aslice apply` — the same convergence operation as `aslice machine apply`, spelled by document kind: plans and locks go to `aslice apply`, the machine file to `aslice machine apply`.

<a id="applying-it"></a>

### 10.3 Applying it

With no argument, `aslice machine apply` reads `./aslice-machine.toml`. Every apply is a plan first: the wishlist is resolved, preferences are diffed, and the complete plan is printed for confirmation before anything changes. `--dry-run` prints the plan without asking.

Applying is **convergent**: apply the same file twice and the second run reports "0 changes". It is also **additive**: apply never removes something merely because the file doesn't mention it. If you *do* want the file to be the whole truth, `aslice machine apply --prune` retracts what the file previously applied but no longer declares — and nothing else. Your hand-installed packages and hand-set preferences are invisible to prune.

Two kinds of step write to OS territory and are therefore **consent-gated**: system-wide preference domains (`/Library/Preferences`), and enrolling an aslice-provided login shell in `/etc/shells`. Interactively, you are shown what will be written and asked. In a script or a recovery terminal, pass `--accept-system-changes` — the same flag as for system packages (§8.4) — or the whole apply is refused before managed state changes. Graft-bearing packages keep their own approval step (§4.5): a machine file may carry a `[grafts]` allow-list so a known set applies without prompting ([SETUP §2.8](SETUP.md#grafts)); anything not listed asks in the usual way, and `--accept-grafts` is the non-interactive escape.

The safety net is the one you already know: before each preference write or shell change, aslice records the old value against the new **generation**, so `aslice rollback` (§5) restores preferences and login shell along with the packages. `aslice history` shows which file applied what, and when.

<a id="capturing-a-machine-export"></a>

### 10.4 Capturing a machine: export

```sh
aslice machine export > aslice-machine.toml
aslice machine export --defaults com.apple.dock,com.apple.finder > aslice-machine.toml
```

Export writes what aslice can *know*: your explicitly installed packages (with variants and non-default streams), your runtime selections, enabled services, your login shell if it isn't the OS default, any repositories you added, and any configuration you changed from defaults. The output is sorted and stable, so exports diff cleanly under version control.

Preferences are the exception. There is no baseline to diff your whole preferences folder against, and application preference domains can contain account tokens, server addresses, and recent-file lists — exactly what a shared file must not leak. Export therefore captures preferences only for domains you name with `--defaults` (or `--system-defaults` for system-wide ones) and stamps the result with a review-before-sharing warning. Value types the schema cannot represent (dictionaries, raw data blobs, dates) are written as comments, never silently dropped.

<a id="sharing-and-coming-from-homebrew"></a>

### 10.5 Sharing, and coming from Homebrew

The file is meant to travel: a team can keep one next to its onboarding docs, and "how do you have your Mac set up?" becomes a link instead of a memoir. Two rules keep shared files healthy — no secrets, ever (nothing in the schema legitimately holds one), and no machine-specific values (hostnames and serials say *this machine*, not *how I like machines*).

If your current source of truth is a Homebrew Brewfile, `aslice machine import --from-brewfile Brewfile > aslice-machine.toml` translates it mechanically: `brew` entries become packages, `tap` entries become comments (an aslice repository is a different, signed thing — §9), and `cask`/`mas`/`vscode` entries are listed as skipped, with a nudge to search the orchard for a vendor-binary package instead. Treat the result as a draft to hand-tune, not a finished file. (For the packages themselves, `aslice adopt --from-homebrew` reads what Homebrew actually installed — §11.)

<a id="what-it-doesnt-do"></a>

### 10.6 What it doesn't do

- **Dotfiles.** `~/.zshrc` and friends stay yours — chezmoi, Stow, or plain git do that job well.
- **Imaging.** FileVault, SIP, user accounts, and System Settings panes without preference domains are untouched; recovery-then-apply assumes a working macOS account already exists.
- **Fleet management.** No agent, no daemon, no drift detection. If you want periodic enforcement, a `launchd` job that runs `aslice machine apply` is enough.
- **Secrets.** Keychain items are never read or written, on apply or export.

---

<a id="aslice-and-homebrew"></a>

## 11. aslice and Homebrew

The two coexist: aslice lives in `/opt/aslice` and never touches `/usr/local`, in either direction. Run both for as long as you like. `aslice doctor` notices a Homebrew installation and advises on `PATH` ordering; that is the full extent of the interaction.

When you're ready to move:

```sh
aslice adopt --from-homebrew
```

It reads your Homebrew installation, maps the packages you explicitly installed (not their dependencies) to aslice formulae — translating old `--with-*` options into aslice variants where an equivalent exists, and Casks into vendor-binary packages where one is packaged — and produces an install plan. It recreates *intent*, not bytes: Homebrew's files are never reused or modified, and whether you remove Homebrew afterwards is your call.

---

<a id="when-something-goes-wrong"></a>

## 12. When something goes wrong

<a id="start-with-doctor"></a>

### 12.1 Start with doctor

After a crash, the guided workflow offers **recover and continue** in one
interaction. Scripts must authorize recovery explicitly. Recovery inventories
affected files, services, registrations, permissions, and transaction progress.
If interrupted again, it resumes saved progress when the evidence still agrees;
it asks about actual conflicts rather than asking you to acknowledge the crash again.

Conflicts appear in repository, package, or service groups with a recommendation
and expandable details. You can restore recorded state, keep validated current
state, or choose manual repair where applicable. Displaced content is preserved.
Manual repair waits for helpers to stop and keeps a mutation gate across exits and
reboots, while your external repair tools remain usable. Returning to recovery
validates the repair before clearing that gate.

If the prefix needs rebuilding, recovery uses independent Application Support
records outside it and prepares a replacement beside the original. Keep an exported
recovery set on separate storage for disk loss: an outside-prefix copy on the same
disk is not enough. Recovery reconstructs your selections, then independently
verifies the artifacts. Lost security history requires repository-level trust
re-establishment; acknowledging a fingerprint alone does not authorize a rebuild.

One salvage plan shows missing artifacts, verified replacements, and omissions for
review. You may explicitly run an isolated verified package closure while unrelated
repairs remain pending. Its dependencies, paths, and configuration must avoid the
damaged prefix; normal activation and affected privileged integration stay blocked
until their requirements are met. Shims do not silently choose another stream or
switch to the replacement.

The result says **repaired**, **usable with listed unresolved repairs**, or
**replacement prepared but activation blocked**, with the remaining actions.
For unattended recovery, first inspect `aslice recover --salvage --dry-run --json`
(or the intended recovery action), then pass that action with
`--confirm-plan sha256:HEX` using the returned plan digest. Changed plans refuse
before mutation. Unattended stopping requires `aslice operation stop --operation-id ID`.
System/graft consent and administrator authorization remain separate requirements.

Use `aslice operation status` to inspect the owner and phase, and
`aslice operation stop` to request safe stopping as the initiator or an authenticated
administrator. `aslice recover --continue` authorizes recovery and continuation;
`--manual`, `--salvage`, and `--activate` select manual repair, replacement preparation,
and separately reviewed activation. Run a validated replacement closure explicitly
with `aslice exec --replacement PATH -- PACKAGE COMMAND...`.
These are specified workflows, not implemented recovery commands. The detailed
contract and command decisions are in
[STATE-AND-RECOVERY §5.1](STATE-AND-RECOVERY.md#51-guided-recovery-and-trusted-prefix-rebuilding)
and [STATE-AND-RECOVERY §10.2](STATE-AND-RECOVERY.md#102-recovery-engineering-contracts).

```sh
aslice doctor
```

`doctor` is read-only, fast, and offline-capable, and every finding names its remedy — not "store integrity error" but "store path `x264-0.164-0+core.v3` fails manifest hash (1 file) — quarantine with `aslice store verify --quarantine x264` and reinstall." Exit codes are scriptable: 0 healthy, 1 warnings, 2 failures. `doctor --fix` performs only the repairs that cannot lose data — pruning dangling cache entries, re-linking a broken generation symlink to its recorded target, refreshing stale index snapshots — announcing each before it acts; for anything else, it hands you the command.

<a id="read-the-log"></a>

### 12.2 Read the log

Everything aslice does is logged to `log/` inside the prefix — structured, local, and never transmitted anywhere; the no-telemetry charter applies to logs as it does to metrics.

```sh
aslice log --last-op          # exactly what the last operation did
aslice log --follow           # live
aslice log --level debug      # more
```

`doctor`'s footer points at the relevant log files and the last operation ID. When you file an issue, `aslice log --last-op` is the excerpt maintainers need; it is generated locally, attached by you, and never auto-submitted.

<a id="common-problems"></a>

### 12.3 Common problems

| Symptom | What's happening | The fix |
|---|---|---|
| `curl`/`git` fail with certificate errors on a fresh install | The OS trust store expired years ago | `aslice ca-update`, then open a new shell (or `aslice shellenv`) |
| Safari can't reach a site even after `ca-update --keychain` | The site's TLS requirements exceed the OS's crypto stack; keychain imports fix trust, not crypto | Use aslice's curl, or a browser with its own TLS stack |
| The installer can't fetch anything at all | TLS-dead machine: expected on old releases | Obtain an independently authenticated bootstrap kit on a supported machine and transfer it offline; verify the digest before execution ([STATE-AND-RECOVERY §7](STATE-AND-RECOVERY.md#persistent-trust-and-initial-bootstrap)). Without that trust anchor, stop. HTTP is allowed only for later artifacts whose exact hashes are already authenticated |
| A service won't start after an upgrade | aslice health-checked it and is waiting for your decision | Read the shown log path; answer the rollback prompt, or `aslice rollback` later |
| "repository key pin changed" | The replacement lacks a valid authenticated transition from retained trust | Normal sequential TUF root rotation needs no re-pin. For unauthenticated replacement, independently verify the new authority before `aslice repo re-pin` ([STATE-AND-RECOVERY §7](STATE-AND-RECOVERY.md#persistent-trust-and-initial-bootstrap)) |
| A package wants SIP disabled | It's a declared `[system]` package (kexts, low-level dev tools) | Follow the printed Recovery instructions, or don't install it — the warning is intentional |
| `php` resolves to the wrong version | Session, project, or default selection, in that order | `aslice which php` traces the resolution |
| aslice and Homebrew binaries shadow each other | `PATH` ordering | `aslice doctor` (coexistence group) prints the exact edit |
| Disk pressure | Cache or old generations | `aslice clean --dry-run`, `aslice gc --dry-run`, then lower the watermarks (§13) |
| Something in the store fails verification | Corruption or tampering; both are treated as security events | `aslice store verify --quarantine <pkg>`, reinstall, and keep the log |
| After a macOS update, a `[system-patch]` behaves oddly | The update restored or replaced the Apple file under the symlink | `aslice doctor` reports the drift with reapply/restore options — it never silently re-patches |

---

<a id="configuration-reference"></a>

## 13. Configuration reference

aslice's configuration file is `etc/aslice.toml` inside the prefix (`~/.aslice/etc/aslice.toml` for per-user installs). Edit it directly, or via `aslice config set <key> <value>`. The keys, as of this writing:

| Key | Values | Default | Meaning |
|---|---|---|---|
| `db.lock_timeout` | nonnegative integer with `ms`, `s`, or `m` | `"30s"` | Allowance for explicitly authorized foreground owner/SQLite lock waiting; `--lock-timeout DURATION` overrides it, `0s` disables waiting. |
| `flavor` | `v1`, `v2`, `v3` | detected | CPU flavor ceiling. Lower it when preparing an install for an older machine. |
| `ca.source` | a configured bundle source | `mozilla` | Where `ca-certificates` bundles come from (§8.1). |
| `mirrors` | list of URLs | project defaults | Extra full-tree mirrors for a repository, tried in order. |
| `gc.keep_generations` | integer | 5 | How many generations rollback can reach. |
| `gc.store_watermark` | size | 20 GB | Store limit; at or above it, ask whether to run GC with `y/N`. |
| `gc.warning_margin_percent` | integer, 0–100 | 10 | Warn this percentage below the store limit; 10 means warnings begin at 90% usage. Never collect automatically. |
| `clean.cache_watermark` | size | 10 GB | Cache size that triggers LRU eviction. |
| `log.keep_days` / `log.keep_size` | integer / size | 14 / 256 MB | Log rotation bounds. |

Environment variables that matter:

- `ASLICE_USE_<RUNTIME>` — the session runtime selection, set by `aslice use` (§6.2).
- `SSL_CERT_FILE`, `CURL_CA_BUNDLE`, `GIT_SSL_CAINFO` — pointed at the aslice bundle by `aslice shellenv` / `aslice init` (§8.1).
- `XDG_CONFIG_HOME` — governs where per-service environment overrides live (`<xdg>/aslice/services/`, §7.1).

The environment group in `aslice doctor` lists every `ASLICE_*` variable currently overriding configuration — overrides are shown, never hidden.

The prefix layout, for orientation: `store/` (immutable packages), `profiles/generations/` (the symlink forests), `shims/` (runtime multiplexing, ahead of the profile on `PATH`), `apps/` (vendor `.app` bundles), `cache/`, `log/`, `db/state.sqlite` (client state), `cache/db/cache.sqlite` (disposable projections), `records/` (durable choices and compact history), `etc/aslice.toml`.

Use `aslice db list` to inspect configured database roles and `aslice db check` to
check client state. `aslice db query 'SELECT * FROM installed'` reads a bounded
snapshot. `aslice db backup <destination>` captures a coordinated backup set;
`aslice db restore <set> --dry-run` validates and previews it before explicit
confirmation. `--role` selects another owner boundary; it grants no permissions.
`aslice recover` reconstructs missing projections from retained records and resolves
interrupted operations. Cache rebuilding preserves trust. See
[aslice-db(1)](../man/aslice-db.1.md) for refusal conditions and output contracts.
If another command holds a lock, an interactive run shows the owner and offers
wait or exit. Unattended commands wait only with `--wait`. Authorized
waits use a cumulative 30-second allowance by default, with progress after one
second and updates every five seconds. `--lock-timeout` changes that allowance;
a configured timeout alone does not authorize unattended waiting. Cancellation waits for a safe
stopping point; a committed operation stays committed even if reconciliation is
pending. `needs-attention` blocks conflicting mutations while recovery is pending;
working packages and external repair tools remain accessible.
The phase outcomes are specified in
[DATABASE §10.1](DATABASE.md#101-contention-and-safe-stopping).

Normal use also attempts maintenance with a 100 ms work budget after successful
mutations and during service idle time; storage synchronization can take longer.
It adds no background client service or housekeeping elevation prompt. A busy
cache is bypassed only with verified inputs. `aslice db maintain --dry-run` shows
eligible database cleanup; omit `--dry-run` to run it. Deleted pages remain reusable
inside SQLite. To shrink the database file, explicitly run `aslice db compact`
after reviewing its space estimate with `--dry-run`. The old database is retained
for recovery. `aslice db check` shows maintenance status and reclaimable-space
estimates. These database operations do not replace store GC or delete payloads.

Compact choices and operation history are retained indefinitely; the log rotation
bounds above apply to verbose logs.

---

<a id="getting-help"></a>

## 14. Getting help

- **`aslice help <command>`** prints the same text as `man aslice-<command>`; the man pages and the CLI help are one source, so they cannot drift apart. `man aslice` is the index of all of them.
- **This manual** is the prose version; [DESIGN.md](DESIGN.md) is the why; [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) is the schema.
- **Bugs and package requests** go to the project tracker. Attach the output of `aslice log --last-op` and `aslice doctor --json`; both are generated locally and contain nothing you haven't seen. Expect the conduct norms in [CONTRIBUTING.md](../CONTRIBUTING.md): be decent, assume good faith, and say so when something is wrong.

---

## Appendix. Command quick reference

| Command | What it does |
|---|---|
| `install` / `reinstall` / `link` / `unlink` | Install the newest eligible packages; repair a damaged profile entry; flip a `link = false` package into/out of a profile (§3.1) |
| `uninstall` / `autoremove` / `mark` | Remove packages; collect unneeded dependencies; fix request records |
| `upgrade` / `outdated` | Move everything (or one package) forward; preview what would move |
| `pin` / `unpin` | Hold a package against upgrades (one argument) — or pin a project to a runtime stream (two, §6) |
| `search` / `info` / `flavors` / `why` / `leaves` | Find packages and inspect them |
| `history` / `rollback` / `switch-generation` | Travel through generations |
| `gc` / `clean` / `store verify` | Reclaim store, reclaim cache, tripwire store integrity |
| `db maintain` / `db compact` | Run eligible database maintenance or explicitly reclaim database-file space; both support `--dry-run` (§13) |
| `use` / `default` / `versions` / `which` | Runtime stream selection and introspection |
| `service list/status/start/stop/restart/run` | launchd service lifecycle |
| `ca-update` (+ `--keychain`, `--crypto`, `--apple-certs`) | Heal TLS: bundle, keychain, crypto stack, Apple's roots |
| `repo add/list/enable/keys/audit` | Manage package sources and trust |
| `repo allow-system-patch/deny-system-patch` | Explicit per-repo system-patch grants (§9.2) |
| `audit` / `provenance` | CVE report; build provenance |
| `doctor` / `log` | Health battery; the local operation log |
| `adopt --from-homebrew` | Migrate an existing Homebrew leaf set |
| `apply` | Replay a lock file or execute a saved plan |
| `machine apply` / `export` / `import --from-brewfile` | Converge the machine to an `aslice-machine.toml`; capture this machine as one; translate a Brewfile (§10) |
| `self-update` | Update aslice itself (health-checked, auto-rollback) |
| `shellenv` / `init` | Print shell environment; print shell integration |
| `exec` / `test` / `livecheck` | Run in a temporary view; run a package's smoke tests; check for newer upstream releases |
| `system-patch list/status/restore` | Inspect and reverse declared system-file replacements |
| `graft approvals` / `graft revoke` | Review and withdraw recorded installer-script approvals (§4.5) |
| `help` | The man page for any command, in your terminal |

## History

Historical labels and ordering below are preserved as recorded, including repeated version labels. They do not override the current specification.

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v0.22 | September 2026 | Specify dependency-driven security remediation, explicit update and origin decisions, and the applicable farm, maintenance, and evidence contracts. Supersedes ABI-only rebuild and cost-first selection policies where previously stated; runtime and measured acceptance remain pending. |
| v0.21 | September 2026 | Remove retired comparison references and competitive framing; retain aslice requirements and link their owning specifications. Align affected contract summaries where applicable. |
| v0.20 | September 2026 | Explain guided recovery, preserved working access, trusted replacement preparation, batch options, explicit waiting, and committed health failures; align whole-machine refusal and rollback guidance. |
| v0.19 | September 2026 | Document configurable lock waits, safe cancellation, automatic database maintenance, and explicit compaction. |
| v0.18 | September 2026 | Add database inspection, coordinated backup/restore, reconstruction, role selection, and durable-history guidance; update the client layout. |
| v0.17 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |
| v0.16 | September 2026 | Add §1.3 and the helper reference link, explaining temporary helpers, package services, runtime shims, and the future multi-user daemon; no runtime changes. |
| v0.15 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v0.14 | September 2026 | resolve install-failure and custom-build summaries against STATE-AND-RECOVERY §1–§2, §5 and SYSTEM-VOLUMES: staged preparation, journal recovery, exact artifact bindings, ABI evidence, dependent tests, CPU/OS checks, and unsupported/unknown flag handling. |
| v0.12 | Not recorded | TOOLCHAIN.md joins the companions and §2.1's no-Xcode sentence links it; no behavioral changes |
| v0.11 | Not recorded | grafts — §1's no-code-at-install claim gains the declared-graft exception, §4 gains §4.5 (the user-facing graft approval flow: the manifest you are shown, the prompt, the allow-list, the unsigned warning, and why rollback still holds), §9.2's no-code-from-repositories sentence and §9.3's signature-scope note gain the graft scope, §10.3's consent gates gain the graft approval step, and the appendix quick reference gains the `graft` row; model in DESIGN v1.19 §12.15; no other behavioral changes. |
| v0.10 | Not recorded | the setup file is renamed `aslice-machine.toml` and its commands move under `aslice machine` (apply / export / import --from-brewfile); top-level `aslice apply` keeps plans and lock files (owner decision, September 2026); no behavioral changes. |
| v0.9 | Not recorded | §1's honesty sentence gains the pointer-mode mechanics — a vendor binary that cannot be hosted is fetched from the vendor's own server at install; the header gains the project-home line — aslice.sh carries the homepage, documentation, and public dashboard, with the installer served from get.aslice.sh (owner decision, September 2026); no behavioral changes. |
| v0.8 | Not recorded | NOMENCLATURE.md vocabulary reference added to the header; no factual or behavioral changes. |
| v0.7 | Not recorded | review pass — the lock-file pointer in §10.2 now cites PACKAGE-FORMAT §7; no factual or behavioral changes. |
| v0.6 | Not recorded | prose rewrite throughout — chapters reworded in the project's technical-writing voice; no factual or behavioral changes. |
| v0.5 | Not recorded | second editorial pass — sentence-level revision for readability; no factual or behavioral changes. |
| v0.4 | Not recorded | editorial pass — prose revised for directness throughout; no factual or behavioral changes. |
| v0.3 | Not recorded | new chapter 10 — declarative whole-machine setup with `setup.toml`, `aslice apply`, `aslice export`, and `aslice import --from-brewfile` (SETUP.md); chapters 10–13 renumber to 11–14. |
| v0.2 | Not recorded | review corrections — §2.3 covers bash alongside zsh, §2.5 lists the three outside-prefix exceptions to a clean removal instead of claiming none exist, §3's man-page claim is softened to what actually ships, §3.1 documents `link`/`unlink` for `link = false` packages, and §7.1's root-daemon gate includes local repositories. |
| Not recorded | September 2026 | corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending. |

</details>
