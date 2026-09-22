# aslice Nomenclature — The Words of the Project

- **Status:** Reference v0.3 — September 2026 (v0.2: the **tombstone** entry gains its second sense — the permanent index record of a removed formula (PACKAGE-FORMAT §3.14, ORCHARD-POLICY §8), alongside the setup.toml negated declaration — prompted by the `aslice orchard tombstone` verb (DESIGN v1.16 §12.14); companion versions refreshed — DESIGN v1.16, AUTHORING v0.7, BUILD-INFRA v0.11, ORCHARD-POLICY v1.4, REPOSITORIES v1.4, SETUP v0.7, HOMEBREW-REVIEW v0.18. v0.3: the **vendor binary / redistribute** entry now describes the two modes (hosted vs vendor-fetched) and points at ORCHARD-POLICY §12 where the vendor-binary policy lives; the **dashboard** entry gains its second sense — the farm's public web dashboard at aslice.sh/dashboard, part of the owner's domain layout (September 2026); companion versions refreshed — DESIGN v1.17, AUTHORING v0.8, BUILD-INFRA v0.12, ORCHARD-POLICY v1.6, REPOSITORIES v1.5, MANUAL v0.9, SETUP v0.8, HOMEBREW-REVIEW v0.19)
- **Companions:** [DESIGN.md](DESIGN.md) v1.17, [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) v0.13, [AUTHORING.md](AUTHORING.md) v0.8, [BUILD-INFRA.md](BUILD-INFRA.md) v0.12, [ORCHARD-POLICY.md](ORCHARD-POLICY.md) v1.6, [REPOSITORIES.md](REPOSITORIES.md) v1.5, [MANUAL.md](MANUAL.md) v0.9, [SETUP.md](SETUP.md) v0.8, [HOMEBREW-REVIEW.md](HOMEBREW-REVIEW.md) v0.19
- **Audience:** every reader. When a document uses a word you do not know, it is defined here — or should be.

A project that names everything owes its readers a place where the names are explained. This is that place. Terms are defined once, in one line where possible, with a pointer to the document that owns the term. Section numbers refer to the September 2026 corpus listed above.

## 1. Conventions

- **Bold** introduces the term being defined.
- *(DOC §x)* names the document that defines the term authoritatively; the definition here is a summary, and the pointer wins on any disagreement.
- *cf.* points at a related term you probably also want.
- *Not to be confused with* separates terms that collide in casual speech.

## 2. Project vocabulary

The words we made up, or made ours.

**slice** — the binary package: a universal payload plus metadata, delivered as a signed tarball. Also the ecosystem's name and the pun the project is built on. *(DESIGN §2.1, §9.)*

**orchard** — the network of repositories as a whole: the trees the slices grow on. *(DESIGN §2.1.)*

**formula** — the build description: a TOML file naming source, dependencies, phases, and invariants. Lives in a repository; produces slices. *(DESIGN §4; PACKAGE-FORMAT §3.)*

**repository** — a Git repository of formulas with a `repo.toml`, a trust level, and a signature-verification policy. *(ORCHARD-POLICY §2.)*

**official / core / overlay** — the three kinds of repository by content: official is the tiered core set, core is its maintained subset, overlays extend it. *(DESIGN §2.2.)*

**flavor** — the payload schema epoch: v1 (Intel, the shipping format), v2 (reserved), v3 (the extension point). A slice declares its flavor; the installer refuses what it does not understand. *(PACKAGE-FORMAT §1.4, §8.)*

**store** — `/usr/local/aslice/store`, the content-addressed home of installed payloads. Nothing else writes there. *(DESIGN §2.4.)*

**generation** — one atomic snapshot of the live tree: a directory of symlinks into the store, swapped by rename. Rollback is pointing at the previous generation. *(DESIGN §2.4, §10.7.)*

**profile** — `~/.aslice/profile`, the per-user symlink to the current generation. What your shell's PATH actually sees. *(DESIGN §2.4.)*

**shim** — the small sudo-authorized wrapper that performs the privileged half of an operation and nothing more. *(DESIGN §2.4, §7.)*

**stream** — a tier's release cadence: stable, rolling, edge. *(DESIGN §2.3.)*

**leaf** — an installed package that nothing installed depends on; a removal candidate. *(DESIGN §10.4.)* *cf.* wishlist.

**tombstone** — two permanent records share the word. In a repository index: what a removed formula leaves behind — name, final version, reason, replacement — so historical snapshots and old locks resolve forever; the `aslice orchard tombstone` verb writes one. *(PACKAGE-FORMAT §3.14; ORCHARD-POLICY §8; DESIGN §12.14.)* In setup.toml: a negated declaration, "this shall not be present," enforced by apply. *(SETUP §2; DESIGN §12.6.)*

**wishlist** — the set of implicit roots: installed leaves the user has not declared but has not removed either. The resolver keeps them honest. *(DESIGN §10.5, §12.4.)*

**lock** — `setup.lock.pins`, the recorded resolution of a setup.toml: exact versions and hashes, replayable. *(SETUP §5; DESIGN §12.5.)*

**index snapshot** — `index.snapshot.json`, a repository's frozen view of its formulas at a commit. Apply resolves against snapshots, not against moving Git heads. *(REPOSITORIES §7; DESIGN §12.3.)*

**plan** — the output of resolution: the exact set of fetch, build, link, and remove steps an apply will perform, shown before anything happens. *(PACKAGE-FORMAT §7; DESIGN §12.2.)*

**farm** — the CI build fleet as a whole. *(BUILD-INFRA §1.)*

**coordinator** — the farm's scheduler: hands out jobs, collects results, keeps the ledger. *(BUILD-INFRA §3.)*

**agent** — a build host: a real Mac of a known µarch that executes jobs under Seatbelt. *(BUILD-INFRA §4.)*

**signing host** — the machine holding the farm's Ed25519 key; signs results, never builds them. *(BUILD-INFRA §3.)*

**job / result** — the JSONL work unit handed to an agent and the signed outcome handed back. *(BUILD-INFRA §5.)*

**evidence builder** — the independent second builder whose output is compared bitwise against the first: the reproducibility oracle. *(BUILD-INFRA §8.)*

**quarantine** — where a slice waits between first signature and countersignature; installable only with explicit consent. *(DESIGN §5.3.)*

**genesis** — the from-nothing bootstrap: building the toolchain that builds the toolchain, from a golden image upward. *(GENESIS §2; DESIGN §13.)*

**vendored sources** — the blob archive of upstream tarballs the project keeps so that dead URLs cannot kill old builds. *(DESIGN §13.4; GENESIS §3.)*

**dashboard** — two things share the word: the curses UI for watching and driving the machinery without a browser *(DESIGN §13.6)*, and the farm's public web dashboard at aslice.sh/dashboard *(BUILD-INFRA §10, ORCHARD-POLICY §9)*.

**transparency log** — the append-only, signed record of everything published; the public answer to "who released this, when." *(DESIGN §5.6; BUILD-INFRA §9.4.)*

**build_id** — the content digest identifying a build output; the primary key of provenance. *(DESIGN §9.4.)*

**ABI epoch** — a declared break in binary compatibility for a package (`abi = true` variants rebuild the reverse-dependency cone). *(DESIGN §9.8; AUTHORING §6.)*

**provenance** — the recorded lineage of a slice: source hash, formula commit, builder, evidence. Checked at the pre-gate. *(BUILD-INFRA §7.)*

**origin=local-build** — the attribution label on a slice built on your machine rather than fetched; never confused with a farm build. *(BUILD-INFRA §9.4; REPOSITORIES §7.)*

**state DB** — the SQLite database (WAL mode) recording what is installed, why, and from where. *(DESIGN §10.1.)*

**pin** — two meanings, both deliberate: a *version pin* in setup.lock.pins holds a package at an exact release (SETUP §5); a *project pin* in AUTHORING holds a formula to an upstream version policy (AUTHORING §12). Context distinguishes them.

**ride** — a ride-along utility: a small package that installs alongside another and is governed by the parent's lifecycle. *(DESIGN §12.9.)*

**extension** — an optional, declared build stage beyond the standard phases. *(DESIGN §9.7.)*

**service** — a package-managed launchd unit, declared by the formula and driven by `aslice service`. *(MANUAL §9; DESIGN §11.)*

**system package / system patch** — the capability to write outside the prefix, up to and including `/System`, granted per-repository and never by default. *(DESIGN §11.4.)*

**setup.toml / apply / export / adopt** — the declarative core: the file that says what you want, the command that makes it so, the command that writes the file from reality, the command that claims an existing install into the file. *(SETUP §2; DESIGN §12; MANUAL §7.)*

## 3. Trust and security

**TUF** — The Update Framework: the roles-and-thresholds design our repository metadata signing follows. *(DESIGN §5.)*

**TOFU** — trust on first use: the first fetch of a repository key is the moment of trust; afterwards, changes must be explained. *(ORCHARD-POLICY §4.)*

**countersignature** — the second, independent signature that moves a slice out of quarantine. *(DESIGN §5.3.)*

**trust level** — a repository's standing: official, verified, third-party, or local. Capabilities follow the level. *(ORCHARD-POLICY §3.)*

**capability** — a named permission a formula may request (system-package, system-patch); granted per repository, per level, never silently. *(DESIGN §11.4.)*

**per-repo grant** — the recorded user decision that this repository may exercise that capability on this machine. *(ORCHARD-POLICY §6.)*

**signer pinning** — remembering which keys may sign a repository's metadata and refusing surprises. *(ORCHARD-POLICY §5.)*

**notarization** — Apple's server-side ticket stapling for Developer-ID software; where it still exists in our range, the runbook says how to use it. *(KEY-RUNBOOK §2.)*

**Gatekeeper** — macOS's first-launch policy layer; on 10.11–12 it still decides what may open. *(DESIGN §7.2.)*

**XProtect** — Apple's built-in signature-based malware list; present on all supported systems. *(DESIGN §7.2.)*

**key ceremony** — the scripted, witnessed generation of the project's root keys. *(KEY-RUNBOOK §3.)*

**threshold root** — the root key split so that k-of-n holders are needed to use it. *(DESIGN §5.2.)*

**minisign** — the small Ed25519 signature tool used for human-legible signatures. *(KEY-RUNBOOK §2.)*

**Ed25519** — the elliptic-curve signature scheme used throughout; small keys, fast verification. *(DESIGN §5.1.)*

**OpenPGP / WKD** — the older signature ecosystem and its Web Key Directory discovery; used where upstreams already speak it. *(ORCHARD-POLICY §5.)*

**revocation / blocking event / re-pin / repo frozen** — the failure vocabulary: a key is revoked, a blocking event halts publishes, users re-pin to successor keys, a compromised repository is frozen. *(KEY-RUNBOOK §5; ORCHARD-POLICY §7.)*

## 4. Building and packaging

**variant** — a formula flavor switch; `abi = true` selects the ABI-epoch variant, `abi = false` the compatible one. *(AUTHORING §6.)*

**livecheck** — the formula stanza that knows how to ask upstream "is there a newer release?" *(AUTHORING §9.)*

**autobump / bump-pr** — the machinery that turns a livecheck hit into a version-bump pull request. *(BUILD-INFRA §6.)*

**cooldown / throttle** — the rate limits that keep autobump polite: minimum time between bumps of one formula, maximum bumps per sweep. *(BUILD-INFRA §6.)*

**revision vs version** — version is upstream's number; revision is ours, bumped when the formula changes but the source does not. *(PACKAGE-FORMAT §2.)*

**min_os / max_os** — the macOS range a slice claims to support; enforced at install. *(PACKAGE-FORMAT §3.)*

**payload-only** — a slice with no build phase: repackaged upstream bits. *(PACKAGE-FORMAT §4.)*

**vendor binary / redistribute** — upstream's own build, repackaged and hosted by the farm (`redistribute = true`) or fetched from the vendor at install (`redistribute = false`); the cask-shaped case. *(ORCHARD-POLICY §12.)*

**pointer formula** — a formula whose whole job is depending on another name, for renames and aliases. *(AUTHORING §11.)*

**universal payload / 32-bit** — a slice carrying both i386 and x86_64 slices of a library, for the shrinking set that still needs i386. *(DESIGN §8.3.)*

**ABI gate / symbol fingerprint** — the automated check that a rebuilt library still exports what it exported; the fingerprint is the sorted symbol list it compares. *(BUILD-INFRA §7.)*

**install name / compatibility version** — the Mach-O dylib identity and its declared ABI number; both must survive a rebuild. *(DESIGN §8.2.)*

**reproducibility classes** — bitwise (identical output), normalized (identical after known fix-ups), unreproducible (declared, tracked, not hidden). *(BUILD-INFRA §8.)*

**ctx / phases** — the build context object passed through the formula's ordered phases (fetch, patch, configure, build, check, install). *(AUTHORING §4.)*

**Seatbelt profile** — the sandbox policy a build runs under; the filesystem and network it may touch. *(BUILD-INFRA §4; DESIGN §7.3.)*

**buildroot / DESTDIR staging** — the throwaway tree a build installs into before the payload is harvested. *(AUTHORING §5.)*

**ccache / SOURCE_DATE_EPOCH / prefix-mapping** — the reproducibility toolkit: compiler cache, clamped timestamps, rewritten embedded paths. *(BUILD-INFRA §8.)*

**smoke test** — the post-install "does it run at all" check a formula declares. *(AUTHORING §8.)*

**matrix / lanes** — the farm's build grid (µarch × macOS) and its queues: freshness, trunk, backfill. *(BUILD-INFRA §3.)*

**lease / pre-gate / backlog sweep** — the coordinator's work mechanics: a job's exclusive claim, the checks before publish, the periodic mop-up of stale work. *(BUILD-INFRA §3, §7.)*

## 5. macOS platform terms

**SIP** — System Integrity Protection: the kernel policy that makes `/System` and friends read-only even to root. Present but older on our systems; the system-patch capability exists because of it. *(DESIGN §11.4.)*

**kext** — a kernel extension; signing rules tighten across our range. *(DESIGN §7.4.)*

**launchd / plist / user vs root domain** — Apple's service manager, its XML/JSON property lists, and the per-user versus system-wide contexts a service may live in. *(MANUAL §9.)*

**defaults domain** — a preferences namespace addressed by `defaults(1)`. *(MANUAL §9.)*

**/etc/shells / chsh** — the list of valid login shells and the tool that changes yours; both matter when aslice ships a shell. *(MANUAL §6.)*

**System keychain / SecureTransport** — the OS credential store and Apple's TLS stack, which the tools use rather than dragging in their own. *(DESIGN §6.3.)*

**dyld / dyld shared cache** — the dynamic linker and its prelinked cache of system libraries. *(DESIGN §8.)*

**Mach-O / dylib / framework** — the executable format, the shared-library form, and the bundled-library directory form. *(DESIGN §8.)*

**universal binary** — one file containing several architectures' code, `lipo`-ed together. *(DESIGN §8.3.)*

**i386 / x86_64** — 32-bit and 64-bit Intel; 10.11–12 is the last range where both matter. *(DESIGN §1.)*

**SSE4.2 / POPCNT / AVX2 / µarch** — instruction-set levels and microarchitecture: the farm builds per-µarch so a Core 2 Duo and a Coffee Lake each get code that fits. *(BUILD-INFRA §4.)*

**Core 2 Duo / Nehalem / Ivy Bridge / Haswell / Coffee Lake** — the Intel generations our µarch lanes are named for. *(BUILD-INFRA §4.)*

**APFS / HFS+ / rename(2)** — the two filesystems in range and the atomic-swap syscall generations rely on. *(DESIGN §2.4.)*

**golden image / createinstallmedia / Recovery** — the pristine OS install the farm starts from, Apple's installer-to-USB tool, and the recovery partition. *(GENESIS §3; BUILD-INFRA §4.)*

**Developer ID / pkg / dmg / LSMinimumSystemVersion** — Apple's signing program, its installer package and disk-image containers, and the Info.plist floor for what an app will launch on. *(KEY-RUNBOOK §2; GENESIS §5.)*

## 6. Acronyms

**ABI** — application binary interface. **SBOM** — software bill of materials. **SPDX** — the license-identifier standard. **CVE / CPE / OSV** — vulnerability identifiers, platform identifiers, the Open Source Vulnerabilities database. **SLSA** — supply-chain integrity framework. **CA / TLS** — certificate authority; transport layer security. **EBNF** — extended Backus–Naur form, the grammar notation of PACKAGE-FORMAT. **TOML** — the config format formulas and setup files are written in. **JSONL** — JSON lines, one record per line. **SQLite / WAL** — the embedded database and its write-ahead log mode. **LRU** — least recently used. **HTTP/2** — the fetch transport. **CI** — continuous integration. **DAG** — directed acyclic graph, the shape of dependency relations. **EOL** — end of life. **PUP** — potentially unwanted program. **CLI / TTY** — command-line interface; terminal. **XDG** — the freedesktop directory specification, borrowed for paths. **VM** — virtual machine. **ISO-8601 / UTC** — the date format and the timezone all timestamps use.

## 7. The Homebrew translation table

For readers arriving from the other orchard. The left word is theirs; the right is ours.

| Homebrew | aslice |
|---|---|
| keg | a store path: one version of one package in the store |
| Cellar | the store |
| bottle | a slice (binary package) |
| pour | install a slice from binary |
| tap | a repository (the orchard is all of them) |
| cask | a vendor-binary (payload-only, redistribute) package |
| keg-only | `link = false` in the formula |
| `post_install` | nothing — rejected; do it in a service or an extension |
| `deprecate!` / `disable!` | the `[deprecation]` table, edited by `aslice orchard deprecate` / `disable` |
| `uses_from_macos` | nothing — rejected; we never borrow from the OS |
| `brew services` | `aslice service` |
| Brewfile | setup.toml |
| `brew bundle` | `aslice apply` |
| `brew cleanup` | `aslice clean` / `aslice gc` |
| `HOMEBREW_*` env vars | `ASLICE_*` |
| formulae.brew.sh | the static web index |
| test-bot | the farm and its merge gates |

## 8. The §-citation conventions

Documents cite each other by section, and the citations follow fixed rules so that "§" never leaves you guessing which book you are in:

- A **bare §N** refers to the document you are reading, with three standing exceptions: in HOMEBREW-REVIEW a bare §N is DESIGN; in CONTRIBUTING a bare §N is ORCHARD-POLICY or PACKAGE-FORMAT as context dictates; in SETUP a bare §12.x is DESIGN's declarative chapter.
- **DOC §N** (the document's name, then the number) is a cross-document reference: DESIGN §12.7, PACKAGE-FORMAT §7.
- **REVIEW §N** is a corpus-wide alias for HOMEBREW-REVIEW §N.
- Section numbers are stable; documents renumber only across flavor epochs, and historical changelog entries are never rewritten to chase a renumbering.

---

*History: v0.1 (September 2026) — initial nomenclature, covering the corpus as of DESIGN v1.15, PACKAGE-FORMAT v0.12, BUILD-INFRA v0.10, ORCHARD-POLICY v1.3, REPOSITORIES v1.3, HOMEBREW-REVIEW v0.17, SETUP v0.6, AUTHORING v0.6, MANUAL v0.8. v0.2 (September 2026) — the tombstone entry gains its index sense; the translation table gains the `deprecate!`/`disable!` row; companions refreshed to DESIGN v1.16, PACKAGE-FORMAT v0.12, AUTHORING v0.7, BUILD-INFRA v0.11, ORCHARD-POLICY v1.4, REPOSITORIES v1.4, MANUAL v0.8, SETUP v0.7, HOMEBREW-REVIEW v0.18. v0.3 (September 2026) — the vendor-binary entry describes both modes and cites ORCHARD-POLICY §12; the dashboard entry gains its web sense (aslice.sh/dashboard); companions refreshed to DESIGN v1.17, PACKAGE-FORMAT v0.13, AUTHORING v0.8, BUILD-INFRA v0.12, ORCHARD-POLICY v1.6, REPOSITORIES v1.5, MANUAL v0.9, SETUP v0.8, HOMEBREW-REVIEW v0.19.*
