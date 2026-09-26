# aslice Repositories — Sources, Trust Levels, and Signing Keys

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

- **Status:** Design draft, v1.14 — September 2026
- **Companion to:** [DESIGN.md](DESIGN.md), [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md), [BUILD-INFRA.md](BUILD-INFRA.md), [ORCHARD-POLICY.md](ORCHARD-POLICY.md)
- **Scope:** the shipped official source list, adding third-party repositories, the inherent trust-level model, and the dual signature scheme (Ed25519 canonical, OpenPGP supported).
- **Vocabulary:** [NOMENCLATURE.md](NOMENCLATURE.md) — project terms, acronyms, and the Homebrew translation table.

---

Navigation: [1. Axioms](#axioms) · [2. The shipped source list](#the-shipped-source-list) · [3. Trust levels](#trust-levels) · [4. Adding a third-party repository](#adding-a-third-party-repository) · [5. Signing keys: two schemes, one verification pipeline](#signing-keys-two-schemes-one-verification-pipeline) · [6. Repository tree addition: `keys/`](#repository-tree-addition-keys) · [7. `aslice repo` command surface, completed](#aslice-repo-command-surface-completed) · [8. Failure and edge cases](#failure-and-edge-cases) · [9. Amendments carried into the other documents](#amendments-carried-into-the-other-documents) · [10. Overlapping packages across repositories](#overlapping-packages-across-repositories) · [11. The state database's role](#the-state-databases-role)

<a id="axioms"></a>

## 1. Axioms

1. **Trust is per-repository, never global** ([DESIGN §9.6](DESIGN.md#the-repository-system)). When you add a repository, it acquires the capabilities of its trust level, and nothing beyond them.
2. **Trust levels are inherent, not labels.** A level is a set of *enforced capabilities*: which namespaces the repo may serve, whether its binaries may install, whether it may serve `[system]` packages. The checks live in the solver and the verifier, in code — not in documentation. A repository cannot talk its way into a higher level; only the user (or the project's countersignature, for verified repos) can raise one.
3. **Every served artifact is signed.** No trust level permits unsigned binaries to install. What varies between levels is *whose* signature is required and *what the repo is allowed to offer*; what never varies is that verification happens.
4. **No repository can execute code at install time outside the graft mechanism**, regardless of level ([DESIGN §10.1](DESIGN.md#declarative-packages-hermetic-builds) and [DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)). The only package code that can ever run is a declared, approved, manifest-sandboxed graft — and §3's table says who may serve even that. Trust levels govern distribution, not the structural guarantees.
5. **The official list is data, signed and versioned** — not hardcoded logic. aslice ships a source list file; you can inspect it, diff it, and — if you are the paranoid sort — replace it wholesale with a pinned copy.

<a id="the-shipped-source-list"></a>

## 2. The shipped source list

An aslice installation carries `/opt/aslice/etc/sources.toml`. The file is part of the bootstrap package and updates through the normal TUF channel — it is a TUF target like any other metadata: versioned, rollback-protected, and diffable with `aslice repo list --sources-diff`.

```toml
# aslice official source list — ships with the bootstrap, updated via TUF.
# Schema versioned; unknown fields rejected.

[sources.core]
url          = "https://repo.aslice.sh/core"
mirrors      = ["https://ghcr.io/aslice/core", "https://mirror.example.org/core"]
trust        = "official"
namespace    = "core"
tuf_root_fingerprint = "ed25519:ROOT0…" # initial TUF anchor
key_fingerprint = "ed25519:RWQ0…"       # separate package-signing key
enabled      = true

[sources.extended]
url          = "https://repo.aslice.sh/extended"
trust        = "official"
namespace    = "extended"
tuf_root_fingerprint = "ed25519:ROOT1…"
key_fingerprint = "ed25519:RWQ1…"
enabled      = true

[sources.audio-lab]
url          = "https://repo.audio-lab.example/aslice"
trust        = "verified"           # project-countersigned community repo (§3)
namespace    = "audiolab"
tuf_root_fingerprint = "ed25519:ROOT2…"
key_fingerprint = "openpgp:9F3C 77AA …"
countersigned_by = "ed25519:RWQ0…"  # the core key vouches for this repo's key
enabled      = false                # listed for discovery; off until the user opts in
```

The properties that matter:

- **The initial TUF root fingerprint is compiled into bootstrap.** It authenticates the initial anchor. Authenticated sequential root transitions establish the current root; discovery-file edits cannot bypass that chain or reset trusted metadata versions ([STATE-AND-RECOVERY §7](STATE-AND-RECOVERY.md#persistent-trust-and-initial-bootstrap)).
- The list is also where **verified community repositories** are advertised (§3): known, project-vouched, and disabled by default. Discovery without implicit trust.
- You may edit the file directly or through `aslice repo add/remove/enable/disable`. Both paths validate against the schema. Discovery cannot replace retained trust: authenticated root rotation follows the existing chain; an unauthenticated replacement blocks updates and requires independently verified rebootstrap or re-pinning.
- A completely offline or air-gapped machine works with the shipped file plus `file://` mirrors. The list is plain data (§8), and plain data travels.
- **Mirrors replicate the whole tree, sources included.** The `blobs/sha256/` area vendors every source artifact the farm has ever fetched ([DESIGN §9.6](DESIGN.md#the-repository-system)); a mirror is therefore a full survival copy of the orchard's inputs, not just its outputs.

<a id="trust-levels"></a>

## 3. Trust levels

Four levels, ordered by what a repository is permitted to do:

| Level | Admission | Binaries | System effects | System patches | Grafts |
|---|---|---|---|---|---|
| `official` | Bootstrap-pinned project authority | Yes | Yes | Yes | Rehearsed, signed manifest |
| `verified` | Project countersignature and explicit enable | Yes | Yes | Explicit per-repo grant | Manifest signed by vouched authority |
| `third-party` | User-added, initial trust verified/pinned | Yes | No | No | Unsigned manifest; fresh approval each time |
| `local` | Explicit local development tree | Source only unless signed and pinned | Own machine, consent required | Own machine, consent required | Same containment and consent rules |

Every repository serving binaries uses Ed25519 TUF metadata. Package signatures are additionally verified: minisign-format Ed25519 for official releases, or the declared supported package-signature scheme for other repositories. An OpenPGP package key never replaces a TUF root ([STATE-AND-RECOVERY §7](STATE-AND-RECOVERY.md#persistent-trust-and-initial-bootstrap)). Unsigned local recipes remain a separate local-only source-build path. The rules below define capabilities and their conditions; a short table cell does not waive them.

Some rules hold at every level:

- **A level can only be lowered by the user, and raised only by the defined path.** There is no `--trust-just-this-once` flag that bypasses a level's capability set — a bypass flag would make the levels decorative.
- **Only core has bare package names.** `ffmpeg` identifies the core package. Every other repository, including extended and local repositories, requires its registered name as a prefix: `extended:vendorcli`, `audiolab:convolver`. Equal suffixes in different namespaces are different package identities. There is no cross-repository fallback, overlap prompt, or remembered repository preference (§10).
- **Vendor-binary packages (`type = "binary"`) follow the same levels.** A `third-party` repo may serve vendor slices — payload-only, or graft-bearing under the unsigned-manifest warning below — subject to the signer-pinning rules of [DESIGN §12.4](DESIGN.md#vendor-binaries-pkgdmg-and-gui-apps) unchanged. Note that the Apple code-signing identity pin is *additional* to the repo signature, never a substitute for it.
- **Graft behavior manifests are signed index metadata ([DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)).** For `official` repos the farm rehearses every graft in per-OS VMs and the project signs the verified manifest ([ORCHARD-POLICY §10](ORCHARD-POLICY.md#merge-gates-what-ci-must-prove) gate 5). A `verified` repo signs its own manifests with its vouched key — behavior signing is part of what the vouch covers. `third-party` manifests are unsigned by construction: the client shows the unsigned-graft warning — provenance, the full declared behavior, a per-decision prompt that is never persisted — and the install proceeds only through it. `local` trees answer to the machine's owner alone. A manifest signature is additional to both the slice signature and any Apple signer pin, never a substitute.
- **System packages (`[system]`, [DESIGN §12.7](DESIGN.md#system-software-kexts-and-sip-disabled-development-tools)) are a per-level capability, not a package property.** `official` and `verified` repositories may serve them. `third-party` repositories never may — no warning flow makes a stranger's kernel extension acceptable. `local` repositories may, on the user's own machine, with the same warnings. The solver refuses a `[system]` package from a non-capable repository with a message that names the level and the remedy, not a generic error. The same capability gates **root-domain services** (`domain = "system"` in the `[service]` table, [DESIGN §12.8](DESIGN.md#services-launchd-native-lifecycle-and-safe-upgrades)): running code as root is the privilege that matters, so a third-party repository may declare user agents but never root daemons. The refusal happens at solve time, with the same named-level message.
- **System patches (`[system-patch]`, [DESIGN §12.11](DESIGN.md#system-patches-flagged-reversible-replacement-of-apple-provided-files)) carry their own, stricter capability — the strictest gate in the system.** The reason for the extra gate is the blast radius: a `[system-patch]` package replaces an Apple-provided file for every user and every process on the machine. Serving one therefore requires the `system-patch` capability: **official and local repositories have it; third-party never does.** A `verified` repository receives it only through an explicit per-repo grant from the machine's owner — `aslice repo allow-system-patch <name>`, refused by default, recorded in the state DB, revocable with `aslice repo deny-system-patch <name>` (DESIGN open question #10, resolved in DESIGN v1.8). Contrast this with `system`, which rides on `verified` with no grant: the countersignature vets a repository to *distribute software*, and rewriting the OS warrants one more decision beyond that vetting. The grant gates *serving*; the [DESIGN §12.11](DESIGN.md#system-patches-flagged-reversible-replacement-of-apple-provided-files) consent flow is unchanged and applies whoever serves the package. A non-capable or ungranted repository that serves a `[system-patch]` package gets a solver refusal naming the level and the remedy.
- **Demotion of a verified repo is a blocking event.** If a `verified` repo's countersignature is revoked, or its key rotates without a re-vouch, the client freezes the repo at its last good snapshot and refuses updates. Every operation that touches the repo prints the reason, and keeps printing it, until the user re-pins or removes it.

<a id="adding-a-third-party-repository"></a>

## 4. Adding a third-party repository

All orchards, including third-party orchards, follow the [shared environment and promotion contract](ORCHARD-POLICY.md#181-environments-branching-and-promoted-builds): dev → `develop`, staging → `beta`, prod → `master`. These branches belong to one repository identity, replicated by its mirrors; environment selection changes the branch pointer, not the repository or mirror URL. Production is the default, and dev/staging require explicit selection with no automatic cross-environment fallback. Each environment has isolated cached metadata and rollback-protection state. Promotion reuses immutable artifacts under the [release-version rules](ORCHARD-POLICY.md#182-release-versioning-and-unchanged-content-enforcement). Third-party publishers use their own authorities; this workflow does not alter trust levels or capabilities. Environment selection and promotion metadata still need implementation and schema design; no new keys are implied in the existing closed schemas.

```console
$ aslice repo add https://repo.example.org/aslice
Fetching TUF root metadata…
Repository:  example.org community repo
Namespace:   example
TUF root:    ed25519:ROOT…
Package key: openpgp:7A3F 19C2 88E4 0D1B …
Trust level: third-party (binaries allowed; cannot shadow core packages)

Verify this fingerprint out-of-band — project website, release notes,
a signed email. Anyone can serve a repository; the fingerprint IS the
identity. Pin it? [y/N]
```

- The initial TUF anchor and package-signing identity are displayed separately and retained in authoritative trust state, with a read-only DB cache. Sequential TUF root updates satisfying the old and new thresholds need no manual re-pin. An unauthenticated replacement blocks updates; `aslice repo re-pin` requires independent verification ([STATE-AND-RECOVERY §7](STATE-AND-RECOVERY.md#persistent-trust-and-initial-bootstrap)).
- `aslice repo add --trust local file:///…` is the only way to obtain the `local` level. `official` and `verified` cannot be granted by the CLI at all: `verified` requires the project's countersignature, which arrives through the official source list. That indirection is the point — it is how the project can vouch for a repository without holding anyone's keys.
- Removal is `aslice repo remove example`. Packages installed from the repo remain in the store — they are content-addressed and generation-pinned — but the namespace stops resolving, and `doctor` offers to reparent surviving leaves to core equivalents where those exist.

<a id="signing-keys-two-schemes-one-verification-pipeline"></a>

## 5. Signing keys: two schemes, one verification pipeline

<a id="why-two-schemes"></a>

### 5.1 Why two schemes

The canonical scheme is **Ed25519 in minisign-compatible format under TUF** ([DESIGN §10.2](DESIGN.md#signatures-and-repository-integrity-tuf)). The virtues are practical: tiny keys, tiny signatures, a verification routine small enough to audit in an afternoon, and no dependency on the GnuPG ecosystem. This remains the scheme for the official repositories and for aslice's own releases.

Repositories exist, however, so that *other* ecosystems can distribute through aslice — and those ecosystems already sign with **OpenPGP**: upstream release tarballs, vendor checksum files, existing project keyrings. Telling every third-party operator to re-key into minisign would amount to telling the platform's most valuable niche communities (audio, lab, retro) to change their release process for our sake. OpenPGP verification is therefore a first-class, built-in scheme:

- **Implementation:** a self-contained OpenPGP verifier inside aslice, in the Sequoia-PGP style, linked in. There is *no* dependency on a `gpg` binary and no keyserver lookup at verify time. The supported subset is the modern one: Ed25519 and ECDSA/RSA OpenPGP keys, detached and cleartext signatures, SHA-256+ digest algorithms only. SHA-1 signatures are rejected.
- **Key acquisition:** fingerprints are pinned in the source entry or at `repo add` (TOFU, §4). Full keys are fetched from the repository itself (`keys/` in the repo tree, §6) or via WKD as a convenience. Verification, however, always runs against the *pinned fingerprint* — so a hostile keyserver or a swapped `keys/` file produces a hard failure, not a wrong key.
- **No web of trust.** aslice evaluates exactly two things: whether the key matches the pinned fingerprint, and whether it produced a valid signature over the artifact. WoT pathfinding is explicitly out of scope; TOFU plus (for `verified`) the project's countersignature replaces it.

<a id="where-each-signature-lives"></a>

### 5.2 Where each signature lives

| Layer | Scheme | Checked when |
|---|---|---|
| TUF repo metadata (root/snapshot/timestamp/targets) | Ed25519 (spec-native), initially 1-of-1 per official role | Every index update |
| Slice signatures | minisign-format Ed25519 (official) **or** OpenPGP detached signature (third-party), scheme recorded per-repo in its TUF targets | Before extraction, always ([DESIGN §6.2](DESIGN.md#binary-package-format-slice)) |
| `verified` countersignature | Ed25519, core key over the repo's root key fingerprint | At enable time and on every source-list update |
| Vendor artifacts | Apple code-signing identity pin (unchanged, [DESIGN §12.4](DESIGN.md#vendor-binaries-pkgdmg-and-gui-apps)) — orthogonal layer | Before payload extraction |
| Upstream source tarballs in formulas | sha256 pins always; OpenPGP verification where the formula declares `[source.pgp]` — `key_url` plus pinned `fingerprint` ([PACKAGE-FORMAT §3.4](PACKAGE-FORMAT.md#source--where-the-bits-come-from); [BUILD-INFRA §3](BUILD-INFRA.md#the-pipeline-shared-at-both-scales) "PGP where declared") | At fetch/verify phase of builds |

The client's rule is uniform: **the scheme is a property of the repository, the fingerprint is a property of the pin, and both are enforced before content is trusted.** A mixed ecosystem — an OpenPGP vendor repo alongside the Ed25519 official repos — is the expected steady state, not an edge case.

<a id="rotation-and-revocation"></a>

### 5.3 Rotation and revocation

- **Official keys:** an initial 1-of-1 root on an offline Pi, distinct targets, snapshot, and slice-signing keys on a dedicated networked release Pi, and the timestamp key on the publisher (KEY-RUNBOOK). Planned rotations and later multi-party adoption use sequential TUF roots satisfying both old and new root thresholds; all intermediate versions remain available. Replacing any top-level role key requires a root update; refreshing metadata with unchanged keys does not. Root compromise or loss without a usable backup requires explicit trust rebootstrap, not a silent pin change. The compiled-in bootstrap pin is updated through self-update ([DESIGN §12.12](DESIGN.md#self-update-aslice-is-package-zero)), and each rotation is announced.
- **Third-party keys:** every repository follows the same sequential TUF root-update rules. Package-key transitions must be authenticated by trusted metadata. A transition signature alone cannot bypass TUF thresholds, revocation, or a required project countersignature. Unauthenticated replacement requires an independently verified re-pin; root compromise requires rebootstrap ([STATE-AND-RECOVERY §7](STATE-AND-RECOVERY.md#persistent-trust-and-initial-bootstrap)).
- **Revocation:** expired TUF metadata blocks repository updates; stopping publication does not instantly revoke client trust. Installed software keeps running. On top of that mechanism, official source-list updates can carry a `revoked_keys` list: a kill switch for a `verified` repo's countersignature that does not require a client release.

<a id="repository-tree-addition-keys"></a>

## 6. Repository tree addition: `keys/`

The repository tree of [DESIGN §9.6](DESIGN.md#the-repository-system) gains one directory:

```text
repo.example.org/
 ├── tuf/
 ├── index/
 ├── formulas/
 ├── keys/           # full public keys for every fingerprint the repo asks clients to pin
 └── blobs/sha256/
```

One characterization covers `keys/`: convenience distribution, not authority. Its contents verify against the pinned fingerprint or are rejected. For `verified` repos, `keys/` additionally holds the project's countersignature file, refreshed by source-list updates.

<a id="aslice-repo-command-surface-completed"></a>

## 7. `aslice repo` command surface, completed

```sh
aslice repo list [--json]                 # namespaces, levels, key fingerprints, health
aslice repo add <url|file://> [--trust local]
aslice repo remove <name>
aslice repo enable / disable <name>       # verified repos ship disabled; user opts in
aslice repo re-pin <name>                 # guided fingerprint change with transition proof
aslice repo keys <name>                   # show the pinned keyring, scheme, countersignatures
aslice repo audit <name>                  # signature coverage report: every target signed? by which key?
aslice repo allow-system-patch / deny-system-patch <name>  # the per-repo verified grant (§3)
aslice repo build / sign / publish        # authoring side (DESIGN §9.6); --sign-with ed25519|openpgp
aslice repo list --sources-diff           # what the last source-list TUF update changed
```

Official authoring retains `repo build / sign / publish`: after owner-approved merge and all gates, the publisher sends an authenticated candidate to the dedicated networked release Pi for automatic signing, verifies the returned signatures and complete staged content, then publishes atomically. [KEY-RUNBOOK §2.1](runbooks/KEY-RUNBOOK.md#automatic-orchard-to-client-publication) defines authorization, serialized activation, signing-state persistence, stale-candidate reconciliation, and idempotent retries. Root metadata is valid for one year, targets/snapshot for 90 days, and timestamps for 48 hours with daily refresh. Targets/snapshot renew automatically when fewer than 30 days remain using the last approved content; root renewal and top-level key replacement remain deliberate offline operations. Timestamp refresh cannot extend targets/snapshot expiry. Normal client metadata refresh discovers published slices for search, install, and upgrade; publication forces no installation. These services remain implementation work; no client signature-format, schema, or command-group change is introduced.

`aslice repo audit` re-verifies the signature over *every* target in a repo's current snapshot and reports scheme, key, and coverage. It exists so that an operator can prove "everything is signed" is true today — not at some ceremony in the past.

<a id="failure-and-edge-cases"></a>

## 8. Failure and edge cases

| Case | Behavior |
|---|---|
| Source-list update fails/tampered | Client keeps the last good list; core/extended keep working; warning surfaced by `doctor` |
| Repo serves a key that doesn't match the pin | Hard refusal before any content is fetched; event logged |
| `verified` repo's countersignature revoked | Repo frozen at last good snapshot, updates refused, persistent banner until re-pin/remove |
| `local` repo contains binary targets | Binaries refused (source-build formulas only) unless the local repo is signed and the machine's user pinned its key |
| A `third-party` repo serves a `[system]` package | Solve-time refusal naming the trust level and the remedy; the `system` capability is never granted to third-party (§3) |
| A `third-party` repo serves a graft-bearing package | Only effects permitted to third-party repositories are allowed; privileged categories are refused even with graft consent. The manifest is unsigned: the client shows the unsigned-graft warning with the full declared behavior, and approval is per decision, never persisted (§3; [DESIGN §12.15](DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)) |
| A `third-party` repo declares `domain = "system"` in `[service]` | Solve-time refusal naming the trust level and the remedy; user-domain agents from third-party repos remain allowed (§3) |
| A `third-party` repo — or a `verified` repo without the per-repo grant — serves a `[system-patch]` package | Solve-time refusal naming the trust level and the remedy (`aslice repo allow-system-patch <name>` for a verified repo; the capability is never available to third-party) (§3) |
| Two third-party repos claim the same namespace | Second `add` is refused; namespaces are unique per client |
| GPG key uses SHA-1 self-signatures / legacy packets outside the supported subset | Clear rejection message naming the unsupported feature; the answer is a modern key, not a looser verifier |
| User deletes `sources.toml` | Bootstrap-embedded defaults regenerate it at next run (user edits are in `sources.toml.d/`-style drop-ins, so deletion loses nothing) |

<a id="amendments-carried-into-the-other-documents"></a>

## 9. Amendments carried into the other documents

- **DESIGN §9.6:** the "Trust is per-repository" bullet is superseded by the level model of §3 here; the bullet now points at this document.
- **DESIGN §10.2:** the signature section now reads as dual-scheme — Ed25519/minisign canonical for official infrastructure, OpenPGP as a built-in first-class scheme for third-party repositories and formula-declared upstream verification.
- **README:** vocabulary gains nothing (a repository is still a repository); the security bullet now mentions trust levels and dual signature schemes.
- **§3 trust levels (v0.4):** the capability sets gain `system` — serving declared system-software packages (kexts, SIP-off development tools; DESIGN §12.7). official and verified may; third-party never may; local may on the user's own machine.
- **§3 trust levels (v0.5):** the `system` capability now also covers root-domain services (DESIGN v1.3 §12.8, PACKAGE-FORMAT v0.4 `[service]` with `domain = "system"`): user agents are ungated; root daemons require official, verified, or local.
- **§3 trust levels (v0.6):** the capability sets gain `system-patch` — serving declared system-patch packages (flagged replacement of Apple-provided files; DESIGN v1.7 §12.11, PACKAGE-FORMAT v0.6 §3.16). official and local may; **verified and third-party never may** — a deliberately stricter gate than `system`, because the countersignature vets a repository to distribute software, not to rewrite the OS. *(Amended by v0.7 below.)*
- **§3 trust levels (v0.7):** DESIGN open question #10 resolved (DESIGN v1.8 §15) — a `verified` repository may receive the `system-patch` capability through an explicit per-repo grant: `aslice repo allow-system-patch <name>`, refused by default, recorded in the state DB, revocable with `aslice repo deny-system-patch <name>`. Third-party repositories: never. The grant gates serving; the per-decision consent flow of DESIGN §12.11 is unchanged.
- **Open question #6:** ~~should `verified` repos be installable-binary-capable immediately at enable time, or should enabling one additionally require a per-repo `--accept-binaries` step?~~ **Resolved (DESIGN v1.8 §15): enable implies binaries stands** — the countersignature ceremony is the consent; the extra click was judged ceremony without security content.

---

<a id="overlapping-packages-across-repositories"></a>

## 10. Overlapping packages across repositories

Only core packages can be addressed by a bare name. Every other repository requires its registered namespace, including `extended:package`. Names are resolved exactly; enabling another repository never changes what a bare name means.

<a id="when-overlap-is-detected"></a>

### 10.1 When overlap is detected

A duplicate complete package identity within a repository is an index error. The same suffix in two repositories is permitted because `audiolab:convolver` and `plugins:convolver` are distinct identities. Registering a second repository with an existing namespace is refused.

<a id="the-prompt"></a>

### 10.2 The prompt

There is no overlap prompt. A bare name absent from core fails with an actionable error. Search may list qualified alternatives, but installing one requires the user to name it explicitly.

<a id="decisions-are-remembered--in-the-state-database"></a>

### 10.3 Decisions are remembered — in the state database

No repository-resolution preference is stored. Plans, locks, request roots, and dependency bindings retain the repository identity and qualified package name. Installing or enabling a repository cannot reparent existing packages.

<a id="pre-seeding-and-fleets"></a>

### 10.4 Pre-seeding and fleets

Machine files, recipes, and scripts use the same naming rule. Use `extended:vendorcli` or `audiolab:convolver` explicitly. The previously proposed preference/resolution commands and table are superseded; they are not part of the current interface.

<a id="the-state-databases-role"></a>

## 11. The state database's role

SQLite separates [client state](DATABASE.md#3-client-state) from the
[disposable cache](DATABASE.md#4-disposable-client-cache). Protected system state,
the farm coordinator, publisher, and release signer have distinct owner databases.
[DATABASE](DATABASE.md) owns their executable schemas, lifecycles, maintenance
commands, and disaster recovery; this section summarizes repository interactions.

| Projection | Contents | Written by |
|---|---|---|
| Client `artifacts`, `bindings`, `members`, `requests` | Exact installed origins, generation membership, dependency bindings, and requested roots | Journaled install/uninstall/rollback/mark |
| Client `holds`, `runtime_defaults`, `profile_priorities`, `history` | Durable choices, collision-provider priorities, and compact operation history | Journaled mutations, including those without a generation change |
| Cache `snapshots`, `packages`, `solve_cache`, `solve_inputs` | Verified index and recipe projections and solves bound to their complete inputs | Authenticated refresh and solver |
| Cache `trust_projections` | Non-authoritative descriptions of retained trust records | Authenticated trust-state reconciliation |

- **WAL and prepared statements apply within each owner database.** Use the pinned SQLite build and connection policy in [DATABASE](DATABASE.md#10-sqlite-connection-and-migration-policy). There is no cross-database atomic commit; journals coordinate projections and external effects.
- **Security authority lives in `trust/`.** Pins, root chains, grants, revocations, version high-water marks, and offline receipts remain independently retained per repository/environment. Database reconstruction preserves that authority; missing trust fails closed and never silently restarts TOFU ([STATE-AND-RECOVERY §7](STATE-AND-RECOVERY.md#persistent-trust-and-initial-bootstrap)).
- **Inspection is read-only.** [aslice db](../man/aslice-db.1.md) lists roles, shows schemas, queries bounded snapshots, checks integrity and records, and performs owner-authorized backup/restore. Deleting the cache loses no choices; deleting durable projections stops mutations until reconstruction and recovery finish.

## History

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v1.13 | September 2026 | Replace the single-file database summary with six owner roles, durable choices, disposable cache, and DATABASE command/recovery contracts; public formats and trust boundaries are unchanged. |
| v1.11 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v1.9 | September 2026 | owner merge becomes the final human release approval, with automatic signing on a dedicated networked Pi and serialized atomic publication. Automatic targets/snapshot renewal replaces manual renewal; the root remains offline. The manual-release design above is superseded. Services and acceptance drills remain implementation work (KEY-RUNBOOK §2.1, §7); schemas and client signature formats are unchanged. |
| v1.8 | September 2026 | **Superseded design record:** initial signing uses a single owner, separate offline root and release Pis, encrypted backups, and manual release batches. The Mac Pro VM prepares and publishes; multi-party custody and hardware tokens are deferred. KEY-RUNBOOK defines renewal, rotation, recovery, and pre-launch drills; prior custody requirements are superseded. |
| v1.7 | Not recorded | prose review pass — one meta-announcement removed (§3); gems kept deliberately ('the binary pin is the root of the root', 'that way lies prompt fatigue', 'no warning flow makes a stranger's kernel extension acceptable'); companion versions refreshed (DESIGN v1.20, PACKAGE-FORMAT v0.15, BUILD-INFRA v0.14, ORCHARD-POLICY v1.8); no semantic or trust-model changes |
| v1.6 | Not recorded | grafts gain their trust-level row — the §3 table answers "may serve grafts?" per level, and graft behavior manifests become signed index metadata: farm-rehearsed and project-signed for official, own-key-signed for verified, unsigned-only under the client's loud per-decision warning for third-party, own-machine for local (mechanism DESIGN v1.19 §12.15; schema PACKAGE-FORMAT v0.15 §3.11; acceptance ORCHARD-POLICY v1.7 §12) — owner decision, September 2026. |
| v1.5 | Not recorded | the canonical endpoint moves to repo.aslice.sh — the project domain (aslice.sh) carries the homepage, documentation, dashboard, installer, repository, and farm, with human pages as paths on the apex and machine endpoints as subdomains (owner decision, September 2026); companion versions refreshed (DESIGN v1.17, PACKAGE-FORMAT v0.13, BUILD-INFRA v0.12, ORCHARD-POLICY v1.6); no trust-model changes. |
| v1.4 | Not recorded | companion versions refreshed (DESIGN v1.16, PACKAGE-FORMAT v0.12, BUILD-INFRA v0.11, ORCHARD-POLICY v1.4); no semantic or trust-model changes. |
| v1.3 | Not recorded | NOMENCLATURE.md vocabulary reference added to the header; companion versions refreshed (DESIGN v1.15, PACKAGE-FORMAT v0.12, BUILD-INFRA v0.10, ORCHARD-POLICY v1.3); no semantic or trust-model changes. |
| v1.2 | Not recorded | review pass — companion versions refreshed; no semantic or trust-model changes. |
| v1.1 | Not recorded | prose rewrite throughout — chapters reworded in the project's technical-writing voice; no semantic or trust-model changes. |
| v1.0 | Not recorded | editorial pass — prose revised for directness; no semantic or trust-model changes. |
| v0.9 | Not recorded | review corrections — §5.2 names the declared PGP schema (`[source.pgp]` with `key_url` plus pinned `fingerprint`, PACKAGE-FORMAT §3.4) instead of a loose `pgp_fingerprint`; §7's command block gains the overlap-resolution and grant commands (`prefer`, `resolutions` / `forget`, `re-resolve`, `allow-system-patch` / `deny-system-patch`, `list --overlaps`). |
| v0.8 | Not recorded | the tree's vendored-source role made explicit — every fetched source artifact lives in `blobs/sha256/`, mirrors replicate it, and the client fetch order is upstream → formula `mirrors` → the repository's own blob area (DESIGN v1.9 §9.6); companions refreshed. |
| v0.7 | Not recorded | DESIGN open question #10 **resolved** — a `verified` repository may receive the `system-patch` capability through an explicit per-repo grant (`aslice repo allow-system-patch <name>`, refused by default, recorded in the state DB, revocable); third-party still never — §3, §8; mechanism in DESIGN v1.8 §12.11. |
| v0.6 | Not recorded | the **`system-patch` capability** — serving `[system-patch]` packages (flagged replacement of Apple-provided files) is the strictest gate in the system: official and local repositories only, verified and third-party never — §3, §8; mechanism in DESIGN v1.7 §12.11, schema in PACKAGE-FORMAT v0.6 §3.16. |
| v0.5 | Not recorded | the same capability gates **root-domain services** (`domain = "system"` in PACKAGE-FORMAT v0.4's `[service]` table); user-domain agents stay ungated — §3; mechanism in DESIGN v1.3 §12.8. |
| v0.4 | Not recorded | the `system` capability — serving `[system]` packages (kexts, SIP-off development tools) is gated by trust level; third-party repositories never may — §3; mechanism in DESIGN v1.2 §12.7. |
| v0.3 | Not recorded | `history` rows carry the operation ID that correlates with the operation log — DESIGN §12.5. |
| v0.2 | Not recorded | cross-repository overlap resolution with remembered decisions — §10; the state database's role — §11. |
| Not recorded | September 2026 | corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending. |
| v1.12 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |
| v1.14 | September 2026 | Remove retired comparison references and competitive framing; retain aslice requirements and link their owning specifications. Align affected contract summaries where applicable. |

</details>
