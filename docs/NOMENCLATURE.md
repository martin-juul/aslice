# aslice Nomenclature — The Words of the Project

- **Status:** Reference v0.6 — September 2026 (v0.2: the **tombstone** entry gains its second sense — the permanent index record of a removed formula (PACKAGE-FORMAT §3.14, ORCHARD-POLICY §8), alongside the setup.toml negated declaration — prompted by the `aslice orchard tombstone` verb (DESIGN v1.16 §12.14); companion versions refreshed — DESIGN v1.16, AUTHORING v0.7, BUILD-INFRA v0.11, ORCHARD-POLICY v1.4, REPOSITORIES v1.4, SETUP v0.7, HOMEBREW-REVIEW v0.18. v0.3: the **vendor binary / redistribute** entry now describes the two modes (hosted vs vendor-fetched) and points at ORCHARD-POLICY §12 where the vendor-binary policy lives; the **dashboard** entry gains its second sense — the farm's public web dashboard at aslice.sh/dashboard, part of the owner's domain layout (September 2026); companion versions refreshed — DESIGN v1.17, AUTHORING v0.8, BUILD-INFRA v0.12, ORCHARD-POLICY v1.6, REPOSITORIES v1.5, MANUAL v0.9, SETUP v0.8, HOMEBREW-REVIEW v0.19. v0.4: the declarative-setup entries follow the rename — the machine file is `aslice-machine.toml` and its verbs are the `aslice machine` group (owner decision, September 2026); the tombstone entry's negated-declaration sense is corrected — the machine file has no such declaration, apply asserts and retraction is the bounded `--prune` mode; the lock and pin entries name the real lock file (`aslice.lock`, PACKAGE-FORMAT §7); companion versions refreshed — DESIGN v1.18, PACKAGE-FORMAT v0.14, MANUAL v0.10, SETUP v0.9, HOMEBREW-REVIEW v0.20. v0.5: grafts — new entries **graft** (§2), **behavior manifest** and **rehearsal** (§4); the **payload-only** and **vendor binary** entries gain the graft nuance; the translation table's `post_install` and cask rows are nuanced and the cask `pkg`-script row added (§7); companion versions refreshed — DESIGN v1.19, PACKAGE-FORMAT v0.15, AUTHORING v0.9, ORCHARD-POLICY v1.7, REPOSITORIES v1.6, MANUAL v0.11, SETUP v0.10. v0.6: the full-corpus citation re-anchor — every pointer re-verified against the current section maps after a project-wide review, and the many that had drifted with renumbering corrected; factual fixes — the store is `/opt/aslice/store`, profiles live at `<prefix>/profiles/<name>`; **shim** is redefined as the exec-only runtime multiplexer (DESIGN §8.5) and the privileged helper breaks out as **aslice-system**; **stream** is redefined as the runtime stream (DESIGN §12.9) — the stable/rolling/edge cadence sense exists nowhere in the corpus; **flavor** is corrected to the µarch flavors v1/v2/v3 (DESIGN §4.2), never a payload schema epoch; **dashboard** loses its unattested curses sense; **quarantine** and **countersignature** corrected to the real pipeline (BUILD-INFRA §7.1, REPOSITORIES §3); **index snapshot**, **pin**, **extension**, and the official/core/extended tiers rewritten to the attested meanings; the **pointer formula** entry dropped — no such mechanism exists; §8's renumbering rule corrected to match reality; companion versions refreshed — BUILD-INFRA v0.13, HOMEBREW-REVIEW v0.21)
- **Companions:** [DESIGN.md](DESIGN.md) v1.19, [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) v0.15, [AUTHORING.md](AUTHORING.md) v0.9, [BUILD-INFRA.md](BUILD-INFRA.md) v0.13, [ORCHARD-POLICY.md](ORCHARD-POLICY.md) v1.7, [REPOSITORIES.md](REPOSITORIES.md) v1.6, [MANUAL.md](MANUAL.md) v0.11, [SETUP.md](SETUP.md) v0.10, [HOMEBREW-REVIEW.md](HOMEBREW-REVIEW.md) v0.21
- **Audience:** every reader. When a document uses a word you do not know, it is defined here — or should be.

A project that names everything owes its readers a place where the names are explained. This is that place. Terms are defined once, in one line where possible, with a pointer to the document that owns the term. Section numbers refer to the September 2026 corpus listed above.

## 1. Conventions

- **Bold** introduces the term being defined.
- *(DOC §x)* names the document that defines the term authoritatively; the definition here is a summary, and the pointer wins on any disagreement.
- *cf.* points at a related term you probably also want.
- *Not to be confused with* separates terms that collide in casual speech.

## 2. Project vocabulary

The words we made up, or made ours.

**slice** — the binary package: a universal payload plus metadata, delivered as a signed tarball. Also the ecosystem's name and the pun the project is built on. *(DESIGN §6.2, §9.)*

**orchard** — the network of repositories as a whole: the trees the slices grow on. *(DESIGN §12.3; ORCHARD-POLICY §2.)*

**formula** — the build description: a TOML file naming source, dependencies, phases, and invariants. Lives in a repository; produces slices. *(DESIGN §6.1; PACKAGE-FORMAT §3.)*

**repository** — a Git repository of formulas with a `repo.toml`, a trust level, and a signature-verification policy. *(REPOSITORIES §1; ORCHARD-POLICY §2.)*

**official / core / extended** — the official orchard is the project-run repository (and the top trust level, REPOSITORIES §3); **core** (~300 packages) and **extended** (~2,000) are its two tiers, with different acceptance bars and prebuild guarantees. *(ORCHARD-POLICY §2; DESIGN §9.4.)*

**flavor** — the µarch build of a slice: v1 (SSE2 baseline, every 64-bit Intel Mac), v2 (SSE4.2/POPCNT), v3 (AVX2). A formula declares which flavors it ships; the installer picks the best one your CPU understands, detected by sysctl at install time. *(DESIGN §4.2; PACKAGE-FORMAT §3.3; MANUAL §4.2.)* *Not to be confused with* variant.

**store** — `/opt/aslice/store`, the content-addressed home of installed payloads. Nothing else writes there. *(DESIGN §8.1.)*

**generation** — one atomic snapshot of the live tree: a directory of symlinks into the store, swapped by rename. Rollback is pointing at the previous generation. *(DESIGN §8.3.)*

**profile** — `<prefix>/profiles/<name>`, the merged symlink forest (bin/, lib/, share/, …) that points at the current generation: `/opt/aslice/profiles/default/bin` is what your shell's PATH actually sees. *(DESIGN §8.1, §8.2.)*

**shim** — the multicall executable that sits ahead of the profile on PATH and dispatches a bare tool name (`php`) to the selected runtime stream; exec-only, with no package knowledge and no state of its own. *(DESIGN §8.5, §12.9.)* *Not to be confused with* aslice-system.

**aslice-system** — the privileged helper: the small sudo-authorized executable that performs the privileged half of an operation — kext placement, system patches, elevated grafts — and nothing more. *(DESIGN §10.4, §12.7.)*

**stream** — one version line of a multi-version runtime: php 8.4 is a stream. Streams are selected per session, per project, or per profile default, and extensions bind to one. *(DESIGN §12.9; MANUAL §6.1; SETUP §2.3.)*

**leaf** — an installed package that nothing installed depends on; a removal candidate — `aslice autoremove` takes it when nothing reachable needs it. *(DESIGN §8.4; MANUAL §3.4.)* *cf.* wishlist.

**tombstone** — the permanent record a removed formula leaves in a repository index: name, final version, reason, replacement — so historical snapshots and old locks resolve forever; the `aslice orchard tombstone` verb writes one. *(PACKAGE-FORMAT §3.14; ORCHARD-POLICY §8; DESIGN §12.14.)* *(An earlier edition of this entry used the word for a negated declaration in the setup file — "this shall not be present." That feature does not exist: `aslice machine apply` asserts what the file declares and never removes what it does not mention, except under the bounded `--prune` mode. SETUP §3; DESIGN §12.13.)*

**wishlist** — the set of implicit roots: installed leaves the user has not declared but has not removed either. The resolver keeps them honest. *(DESIGN §8.4, §12.13.)*

**lock** — `aslice.lock`, the recorded resolution of a profile: exact versions and hashes, replayable with `aslice apply`. *(PACKAGE-FORMAT §7.)*

**index snapshot** — a repository's frozen index at a commit, shipped as zstd JSON snapshots plus diffs. Apply resolves against snapshots, not against moving Git heads. *(DESIGN §9.6; SETUP §3.2.)*

**plan** — the output of resolution: the exact set of fetch, build, link, and remove steps an apply will perform, shown before anything happens. *(DESIGN §12.1, §12.2; SETUP §3.2.)*

**farm** — the CI build fleet as a whole. *(BUILD-INFRA §1, §5.)*

**coordinator** — the farm's scheduler: hands out jobs, collects results, keeps the ledger. *(BUILD-INFRA §5, §6.)*

**agent** — a build host: a real Mac of a known µarch that executes jobs under Seatbelt. *(BUILD-INFRA §5, §7.2.)*

**signing host** — the machine holding the farm's Ed25519 key; signs results, never builds them. *(BUILD-INFRA §5, §7.)*

**job / result** — the JSONL work unit handed to an agent and the signed outcome handed back. *(BUILD-INFRA §2.)*

**evidence builder** — the independent second builder whose output is compared bitwise against the first: the reproducibility oracle. *(BUILD-INFRA §7.4.)*

**quarantine** — the untrusted staging area every agent result lands in; nothing is ever served from it, and promotion to the repository happens only on the signing host, after the six gates. *(BUILD-INFRA §7.1.)*

**genesis** — the from-nothing bootstrap: building the toolchain that builds the toolchain, from a golden image upward. *(GENESIS §1–§2; DESIGN §14.)*

**vendored sources** — the blob archive of upstream tarballs the project keeps so that dead URLs cannot kill old builds. *(DESIGN §9.6; GENESIS §3.)*

**dashboard** — the farm's public web dashboard at aslice.sh/dashboard: build status, freshness, quarantine — farm-side metrics only; there is no user telemetry to show. *(DESIGN §13.4; BUILD-INFRA §10; ORCHARD-POLICY §9.)*

**transparency log** — the append-only, signed record of everything published; the public answer to "who released this, when." *(DESIGN §13.4; BUILD-INFRA §7.5.)*

**build_id** — the content digest identifying a build output; the primary key of provenance. *(DESIGN §7.2.)*

**ABI epoch** — a declared break in binary compatibility for a package (`abi = true` variants rebuild the reverse-dependency cone). *(DESIGN §7.3; AUTHORING §5.)*

**provenance** — the recorded lineage of a slice: source hash, formula commit, builder, evidence. Checked at the pre-gate. *(DESIGN §9.5; BUILD-INFRA §7.)*

**origin=local-build** — the attribution label on a slice built on your machine rather than fetched; never confused with a farm build. *(BUILD-INFRA §3, §4.)*

**state DB** — the SQLite database (WAL mode) recording what is installed, why, and from where. *(DESIGN §8.1; REPOSITORIES §11.)*

**pin** — a *version pin* (`aslice pin`) holds an installed package at its exact release, and the lock records it (MANUAL §3.3; PACKAGE-FORMAT §7). *Not to be confused with* hash-pinning: every source artifact's sha256 is declared in the formula and countersigned in the index (AUTHORING §1; DESIGN §10.2).

**ride** — a ride-along utility: a small package that installs alongside another and is governed by the parent's lifecycle. *(DESIGN §12.9; PACKAGE-FORMAT §3.13.)*

**extension** — a package bound to one runtime stream: php-redis, ruby-pg. Declared with `[extension]`, loaded through the runtime's scan dir, rebuilt when the stream's extension-ABI epoch bumps. *(PACKAGE-FORMAT §3.13; DESIGN §12.9; MANUAL §6.3.)*

**service** — a package-managed launchd unit, declared by the formula and driven by `aslice service`. *(MANUAL §7; DESIGN §12.8.)*

**system package / system patch** — the capability to write outside the prefix, up to and including `/System`, granted per-repository and never by default. *(DESIGN §12.7, §12.11; REPOSITORIES §3.)*

**aslice-machine.toml / machine apply / machine export / machine import / adopt** — the declarative core: the file that says what you want, the command that makes it so, the command that writes the file from reality, the command that translates a Brewfile into the file, the command that claims an existing Homebrew install as a plan. *(SETUP §2–§5; DESIGN §12.13; MANUAL §10–§11.)*

**graft** — a vendor installer script, declared in the formula (`[[binary.graft]]`), hash-pinned, approved by the user per package, sandboxed to its declared behavior, and recorded for rollback; the sole exception to "no package code at install". *(DESIGN §12.15; PACKAGE-FORMAT §3.11; MANUAL §4.5.)* *cf.* behavior manifest, rehearsal.

## 3. Trust and security

**TUF** — The Update Framework: the roles-and-thresholds design our repository metadata signing follows. *(DESIGN §10.2; REPOSITORIES §5.)*

**TOFU** — trust on first use: the first fetch of a repository key is the moment of trust; afterwards, changes must be explained. *(REPOSITORIES §4.)*

**countersignature** — a second, project-held signature: over a community repository's key it earns the `verified` trust level, and the index countersigns every source hash. *(REPOSITORIES §3; DESIGN §10.2.)*

**trust level** — a repository's standing: official, verified, third-party, or local. Capabilities follow the level. *(REPOSITORIES §3; DESIGN §12.3.)*

**capability** — a named permission a formula may request (system-package, system-patch); granted per repository, per level, never silently. *(DESIGN §12.7, §12.11; REPOSITORIES §3.)*

**per-repo grant** — the recorded user decision that this repository may exercise that capability on this machine. *(REPOSITORIES §3, §7.)*

**signer pinning** — remembering which keys may sign a repository's metadata, or which Developer ID may sign a vendor artifact, and refusing surprises. *(REPOSITORIES §5; ORCHARD-POLICY §12.)*

**notarization** — Apple's server-side ticket stapling for Developer-ID software; aslice's own bootstrap trust is notarization plus signature, and a vendor artifact's notarization status is pinned in provenance. *(DESIGN §12.12, §9.5.)*

**Gatekeeper** — macOS's first-launch policy layer; on 10.11–12 it still decides what may open. *(DESIGN §12.12.)*

**XProtect** — Apple's built-in signature-based malware list; present on all supported systems. *(BUILD-INFRA §7.5.)*

**key ceremony** — the scripted, witnessed generation of the project's root keys. *(KEY-RUNBOOK §2.)*

**threshold root** — the root key split so that k-of-n holders are needed to use it. *(DESIGN §10.2; KEY-RUNBOOK §1.)*

**minisign** — the small Ed25519 signature tool used for human-legible signatures. *(KEY-RUNBOOK §1; DESIGN §10.2.)*

**Ed25519** — the elliptic-curve signature scheme used throughout; small keys, fast verification. *(DESIGN §10.2; KEY-RUNBOOK §1.)*

**OpenPGP / WKD** — the older signature ecosystem and its Web Key Directory discovery; used where upstreams already speak it. *(REPOSITORIES §5.)*

**revocation / blocking event / re-pin / repo frozen** — the failure vocabulary: a key is revoked, a blocking event halts publishes, users re-pin to successor keys, a compromised repository is frozen. *(KEY-RUNBOOK §4; REPOSITORIES §4, §8.)*

## 4. Building and packaging

**variant** — a formula's declared feature switch: `+ssl`, `+x265`. Marked `abi = true`, a variant joins the build identity and its flip rebuilds the reverse-dependency cone; `abi = false` stays link-compatible. *(AUTHORING §5; PACKAGE-FORMAT §3.5; DESIGN §7.1.)* *Not to be confused with* flavor.

**livecheck** — the formula stanza that knows how to ask upstream "is there a newer release?" *(PACKAGE-FORMAT §3.15; AUTHORING §7.1.)*

**autobump / bump-pr** — the machinery that turns a livecheck hit into a version-bump pull request. *(ORCHARD-POLICY §9; BUILD-INFRA §6.2; AUTHORING §7.1.)*

**cooldown / throttle** — the rate limits that keep autobump polite: minimum time between bumps of one formula, maximum bumps per sweep. *(ORCHARD-POLICY §9.)*

**revision vs version** — version is upstream's number; revision is ours, bumped when the formula changes but the source does not. *(PACKAGE-FORMAT §4.4.)*

**min_os / max_os** — the macOS range a slice claims to support; enforced at install. *(PACKAGE-FORMAT §3.2.)*

**payload-only** — a slice with no build phase and no grafts: repackaged upstream bits. The default even for vendor binaries. *(ORCHARD-POLICY §12; PACKAGE-FORMAT §3.11.)*

**vendor binary / redistribute** — upstream's own build, repackaged and hosted by the farm (`redistribute = true`) or fetched from the vendor at install (`redistribute = false`); the cask-shaped case. An installer script the software genuinely needs is declared as a graft, never run silently. *(ORCHARD-POLICY §12; DESIGN §12.4, §12.15.)*

**universal payload / 32-bit** — a slice carrying both i386 and x86_64 slices of a library, for the shrinking set that still needs i386. *(DESIGN §2.2, §12.4; PACKAGE-FORMAT §3.11.)*

**ABI gate / symbol fingerprint** — the automated check that a rebuilt library still exports what it exported; the fingerprint is the sorted symbol list it compares. *(BUILD-INFRA §6.1, §7.1; AUTHORING §5.2.)*

**install name / compatibility version** — the Mach-O dylib identity and its declared ABI number; both must survive a rebuild. *(DESIGN §7.3.)*

**reproducibility classes** — bitwise (identical output), normalized (identical after known fix-ups), unreproducible (declared, tracked, not hidden). *(BUILD-INFRA §7.3.)*

**ctx / phases** — the build context object passed through the formula's ordered phases (fetch, patch, configure, build, check, install). *(AUTHORING §4; PACKAGE-FORMAT §6.1.)*

**Seatbelt profile** — the sandbox policy a build runs under; the filesystem and network it may touch. *(DESIGN §10.5; BUILD-INFRA §2.)*

**behavior manifest** — the exhaustive declaration of what a graft may do: the paths it may write, the kexts it may load, the daemons it may register, whether it may touch the network, whether it needs elevation. Doubles as the graft's Seatbelt profile, and is signed into the index only after rehearsal. *(PACKAGE-FORMAT §3.11; DESIGN §12.15.)*

**rehearsal** — the farm running a graft-bearing install in a per-OS VM under instrumentation and diffing the observed behavior against the declared behavior manifest; only an exact match gets the manifest signed. Also runnable locally via `aslice orchard ci`. *(ORCHARD-POLICY §10; DESIGN §12.15; BUILD-INFRA §6.4.)*

**buildroot / DESTDIR staging** — the throwaway tree a build installs into before the payload is harvested. *(AUTHORING §4.)*

**ccache / SOURCE_DATE_EPOCH / prefix-mapping** — the reproducibility toolkit: compiler cache, clamped timestamps, rewritten embedded paths. *(ORCHARD-POLICY §15; BUILD-INFRA §3; DESIGN §11.)*

**smoke test** — the post-install "does it run at all" check a formula declares. *(AUTHORING §6.)*

**matrix / lanes** — the farm's build grid (µarch × macOS) and its queues: freshness, trunk, backfill. *(BUILD-INFRA §8, §6.2.)*

**lease / pre-gate / backlog sweep** — the coordinator's work mechanics: a job's exclusive claim, the checks before publish, the periodic mop-up of stale work. *(BUILD-INFRA §6.3, §7.5.)*

## 5. macOS platform terms

**SIP** — System Integrity Protection: the kernel policy that makes `/System` and friends read-only even to root. Present but older on our systems; the system-patch capability exists because of it. *(DESIGN §12.7, §12.11.)*

**kext** — a kernel extension; signing rules tighten across our range. *(DESIGN §12.7; PACKAGE-FORMAT §3.12.)*

**launchd / plist / user vs root domain** — Apple's service manager, its XML/JSON property lists, and the per-user versus system-wide contexts a service may live in. *(MANUAL §7; DESIGN §12.8.)*

**defaults domain** — a preferences namespace addressed by `defaults(1)`. *(SETUP §2.6.)*

**/etc/shells / chsh** — the list of valid login shells and the tool that changes yours; both matter when aslice ships a shell. *(SETUP §2.5.)*

**System keychain / SecureTransport** — the OS credential store and Apple's TLS stack, which the tools use rather than dragging in their own. *(DESIGN §12.10; MANUAL §8.)*

**dyld / dyld shared cache** — the dynamic linker and its prelinked cache of system libraries. *(DESIGN §7.3, §11.)*

**Mach-O / dylib / framework** — the executable format, the shared-library form, and the bundled-library directory form. *(DESIGN §7.3.)*

**universal binary** — one file containing several architectures' code, `lipo`-ed together. *(PACKAGE-FORMAT §3.11; DESIGN §12.4.)*

**i386 / x86_64** — 32-bit and 64-bit Intel; 10.11–12 is the last range where both matter. *(DESIGN §1.2, §2.2.)*

**SSE4.2 / POPCNT / AVX2 / µarch** — instruction-set levels and microarchitecture: the farm builds per-µarch so a Core 2 Duo and a Coffee Lake each get code that fits. *(DESIGN §4.2.)*

**Core 2 Duo / Nehalem / Ivy Bridge / Haswell / Coffee Lake** — the Intel generations our µarch lanes are named for. *(DESIGN §4.2; BUILD-INFRA §5.)*

**APFS / HFS+ / rename(2)** — the two filesystems in range and the atomic-swap syscall generations rely on. *(DESIGN §4.1, §8.3.)*

**golden image / createinstallmedia / Recovery** — the pristine OS install the farm starts from, Apple's installer-to-USB tool, and the recovery partition. *(GENESIS §2; BUILD-INFRA §8.)*

**Developer ID / pkg / dmg / LSMinimumSystemVersion** — Apple's signing program, its installer package and disk-image containers, and the Info.plist floor for what an app will launch on. *(DESIGN §12.4; PACKAGE-FORMAT §3.11; ORCHARD-POLICY §12.)*

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
| cask | a vendor-binary package — payload-only by default, graft-bearing when the installer script is genuinely required |
| keg-only | `link = false` in the formula |
| cask `pkg` installer scripts | grafts — declared `[[binary.graft]]` with a behavior manifest, approved per package, sandboxed |
| `post_install` | nothing for arbitrary code — rejected; do it in a service or an extension. A vendor installer script the payload cannot replace ships as a graft |
| `deprecate!` / `disable!` | the `[deprecation]` table, edited by `aslice orchard deprecate` / `disable` |
| `uses_from_macos` | nothing — rejected; we never borrow from the OS |
| `brew services` | `aslice service` |
| Brewfile | `aslice-machine.toml` |
| `brew bundle` | `aslice machine apply` |
| `brew cleanup` | `aslice clean` / `aslice gc` |
| `HOMEBREW_*` env vars | `ASLICE_*` |
| formulae.brew.sh | the static web index |
| test-bot | the farm and its merge gates |

## 8. The §-citation conventions

Documents cite each other by section, and the citations follow fixed rules so that "§" never leaves you guessing which book you are in:

- A **bare §N** refers to the document you are reading, with three standing exceptions: in HOMEBREW-REVIEW a bare §N is DESIGN; in CONTRIBUTING a bare §N is ORCHARD-POLICY or PACKAGE-FORMAT as context dictates; in SETUP a bare §12.x is DESIGN's declarative chapter.
- **DOC §N** (the document's name, then the number) is a cross-document reference: DESIGN §12.7, PACKAGE-FORMAT §7.
- **REVIEW §N** is a corpus-wide alias for HOMEBREW-REVIEW §N.
- Section numbers drift as documents accrete chapters; each revision of this reference re-anchors its pointers to the current maps, and historical changelog entries are never rewritten to chase a renumbering.

---

*History: v0.1 (September 2026) — initial nomenclature, covering the corpus as of DESIGN v1.15, PACKAGE-FORMAT v0.12, BUILD-INFRA v0.10, ORCHARD-POLICY v1.3, REPOSITORIES v1.3, HOMEBREW-REVIEW v0.17, SETUP v0.6, AUTHORING v0.6, MANUAL v0.8. v0.2 (September 2026) — the tombstone entry gains its index sense; the translation table gains the `deprecate!`/`disable!` row; companions refreshed to DESIGN v1.16, PACKAGE-FORMAT v0.12, AUTHORING v0.7, BUILD-INFRA v0.11, ORCHARD-POLICY v1.4, REPOSITORIES v1.4, MANUAL v0.8, SETUP v0.7, HOMEBREW-REVIEW v0.18. v0.3 (September 2026) — the vendor-binary entry describes both modes and cites ORCHARD-POLICY §12; the dashboard entry gains its web sense (aslice.sh/dashboard); companions refreshed to DESIGN v1.17, PACKAGE-FORMAT v0.13, AUTHORING v0.8, BUILD-INFRA v0.12, ORCHARD-POLICY v1.6, REPOSITORIES v1.5, MANUAL v0.9, SETUP v0.8, HOMEBREW-REVIEW v0.19. v0.4 (September 2026) — the declarative-setup entries follow the rename: `aslice-machine.toml` and the `aslice machine` group; the tombstone entry's negated-declaration sense is corrected to the actual `--prune` semantics (SETUP §3, DESIGN §12.13); the lock and pin entries name the real lock file, `aslice.lock` (PACKAGE-FORMAT §7); companions refreshed to DESIGN v1.18, PACKAGE-FORMAT v0.14, AUTHORING v0.8, BUILD-INFRA v0.12, ORCHARD-POLICY v1.6, REPOSITORIES v1.5, MANUAL v0.10, SETUP v0.9, HOMEBREW-REVIEW v0.20. v0.5 (September 2026) — grafts: new entries **graft**, **behavior manifest**, **rehearsal**; **payload-only** and **vendor binary** entries nuanced; translation table rows for `post_install` and cask nuanced, cask `pkg`-script row added; companions refreshed to DESIGN v1.19, PACKAGE-FORMAT v0.15, AUTHORING v0.9, BUILD-INFRA v0.12, ORCHARD-POLICY v1.7, REPOSITORIES v1.6, MANUAL v0.11, SETUP v0.10, HOMEBREW-REVIEW v0.20. v0.6 (September 2026) — the full-corpus citation re-anchor: every §-pointer re-verified against the current section maps after the project-wide review, and the drifted ones corrected; factual fixes — store `/opt/aslice/store`, profiles `<prefix>/profiles/<name>`; **shim** redefined as the runtime multiplexer and **aslice-system** broken out; **stream** redefined as the runtime stream; **flavor** corrected to the µarch flavors; **dashboard** loses its unattested curses sense; **quarantine**, **countersignature**, **index snapshot**, **pin**, **extension**, and the official/core/extended tiers rewritten to attested meanings; the **pointer formula** entry dropped; §8's renumbering rule corrected; companions refreshed to BUILD-INFRA v0.13, HOMEBREW-REVIEW v0.21.*
