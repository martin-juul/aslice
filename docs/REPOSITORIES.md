# aslice Repositories — Sources, Trust Levels, and Signing Keys

- **Status:** Design draft, v1.1 — September 2026 (v0.2: cross-repository overlap resolution with remembered decisions — §10; the state database's role — §11. v0.3: `history` rows carry the operation ID that correlates with the operation log — DESIGN §12.5. v0.4: the `system` capability — serving `[system]` packages (kexts, SIP-off development tools) is gated by trust level; third-party repositories never may — §3; mechanism in DESIGN v1.2 §12.7. v0.5: the same capability gates **root-domain services** (`domain = "system"` in PACKAGE-FORMAT v0.4's `[service]` table); user-domain agents stay ungated — §3; mechanism in DESIGN v1.3 §12.8. v0.6: the **`system-patch` capability** — serving `[system-patch]` packages (flagged replacement of Apple-provided files) is the strictest gate in the system: official and local repositories only, verified and third-party never — §3, §8; mechanism in DESIGN v1.7 §12.11, schema in PACKAGE-FORMAT v0.6 §3.16. v0.7: DESIGN open question #10 **resolved** — a `verified` repository may receive the `system-patch` capability through an explicit per-repo grant (`aslice repo allow-system-patch <name>`, refused by default, recorded in the state DB, revocable); third-party still never — §3, §8; mechanism in DESIGN v1.8 §12.11. v0.8: the tree's vendored-source role made explicit — every fetched source artifact lives in `blobs/sha256/`, mirrors replicate it, and the client fetch order is upstream → formula `mirrors` → the repository's own blob area (DESIGN v1.9 §9.6); companions refreshed. v0.9: review corrections — §5.2 names the declared PGP schema (`[source.pgp]` with `key_url` plus pinned `fingerprint`, PACKAGE-FORMAT §3.4) instead of a loose `pgp_fingerprint`; §7's command block gains the overlap-resolution and grant commands (`prefer`, `resolutions` / `forget`, `re-resolve`, `allow-system-patch` / `deny-system-patch`, `list --overlaps`). v1.0: editorial pass — prose revised for directness; no semantic or trust-model changes. v1.1: prose rewrite throughout — chapters reworded in the project's technical-writing voice; no semantic or trust-model changes)
- **Companion to:** [DESIGN.md](DESIGN.md) v1.12 (§8 store/state, §9.6 repository system, §10.2 signatures, §12.5 logging, §12.6 doctor, §12.7 system software, §12.8 services, §12.10 trust store, §12.11 system patches, §12.12 self-update), [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) v0.9, [BUILD-INFRA.md](BUILD-INFRA.md) v0.6 (§9 result→repository), [ORCHARD-POLICY.md](ORCHARD-POLICY.md) v0.8
- **Scope:** the shipped official source list, adding third-party repositories, the inherent trust-level model, and the dual signature scheme (Ed25519 canonical, OpenPGP supported).

---

## 1. Axioms

1. **Trust is per-repository, never global** (DESIGN §9.6). When you add a repository, it acquires the capabilities of its trust level, and nothing beyond them.
2. **Trust levels are inherent, not labels.** A level is a set of *enforced capabilities*: which namespaces the repo may serve, whether its binaries may install, whether it may shadow core package names, whether it may serve `[system]` packages. The checks live in the solver and the verifier, in code — not in documentation. A repository cannot talk its way into a higher level; only the user (or the project's countersignature, for verified repos) can raise one.
3. **Every served artifact is signed.** No trust level permits unsigned binaries to install. What varies between levels is *whose* signature is required and *what the repo is allowed to offer*; what never varies is that verification happens.
4. **No repository can execute code at install time** regardless of level (DESIGN §10.1). Trust levels govern distribution, not the structural guarantees.
5. **The official list is data, signed and versioned** — not hardcoded logic. aslice ships a source list file; you can inspect it, diff it, and — if you are the paranoid sort — replace it wholesale with a pinned copy.

## 2. The shipped source list

An aslice installation carries `/opt/aslice/etc/sources.toml`. The file is part of the bootstrap package and updates through the normal TUF channel — it is a TUF target like any other metadata: versioned, rollback-protected, and diffable with `aslice repo list --sources-diff`.

```toml
# aslice official source list — ships with the bootstrap, updated via TUF.
# Schema versioned; unknown fields rejected.

[sources.core]
url          = "https://repo.aslice.org/core"
mirrors      = ["https://ghcr.io/aslice/core", "https://mirror.example.org/core"]
trust        = "official"
namespace    = "core"
key_fingerprint = "ed25519:RWQ0…"   # pre-pinned in the bootstrap binary itself
enabled      = true

[sources.extended]
url          = "https://repo.aslice.org/extended"
trust        = "official"
namespace    = "extended"
key_fingerprint = "ed25519:RWQ1…"
enabled      = true

[sources.audio-lab]
url          = "https://repo.audio-lab.example/aslice"
trust        = "verified"           # project-countersigned community repo (§3)
namespace    = "audiolab"
key_fingerprint = "openpgp:9F3C 77AA …"
countersigned_by = "ed25519:RWQ0…"  # the core key vouches for this repo's key
enabled      = false                # listed for discovery; off until the user opts in
```

The properties that matter:

- **The core key fingerprint is compiled into the bootstrap binary**, in addition to being listed here. A tampered `sources.toml` therefore cannot, by itself, redirect the core namespace: the client refuses a core entry whose fingerprint differs from the compiled-in pin. The file is the *discovery* layer; the binary pin is the root of the root.
- The list is also where **verified community repositories** are advertised (§3): known, project-vouched, and disabled by default. Discovery without implicit trust.
- You may edit the file directly or through `aslice repo add/remove/enable/disable`. Both paths validate against the schema, and any fingerprint change triggers a visible re-pin notice.
- A completely offline or air-gapped machine works with the shipped file plus `file://` mirrors. The list is plain data (§8), and plain data travels.
- **Mirrors replicate the whole tree, sources included.** The `blobs/sha256/` area vendors every source artifact the farm has ever fetched (DESIGN §9.6); a mirror is therefore a full survival copy of the orchard's inputs, not just its outputs.

## 3. Trust levels

Four levels, ordered by what a repository is permitted to do:

| Level | How a repo gets it | May serve binaries? | May shadow core names? | May serve `[system]`? | May serve `[system-patch]`? | Signature requirement |
|---|---|---|---|---|---|---|
| `official` | Compiled-in fingerprint pin; only core/extended ship this way | Yes | n/a (it *is* the namespace) | Yes | Yes | Ed25519, threshold TUF root (DESIGN §10.2) |
| `verified` | Listed in the official source list **with a project countersignature** over the repo's key; user enables explicitly | Yes | No — solver treats shadowing as a conflict with an explicit message | Yes | **With an explicit per-repo grant** — `aslice repo allow-system-patch <name>` (refused by default, recorded in the state DB, revocable); never implicit (§3) | Ed25519 **or** OpenPGP; key vouched by the core key |
| `third-party` | `aslice repo add <url>` by the user, TOFU key pinning | Yes — installs show an unambiguous `third-party/<name>` provenance line | Never silently; `doctor` reports; solver prefers core/extended unconditionally | **Never** | **Never** | Ed25519 or OpenPGP; fingerprint displayed at add, out-of-band verification recommended |
| `local` | `aslice repo add file:///path --trust local` (development trees) | **No.** Formulas resolve for source builds only; any binary target in the repo is refused | No | Yes — own tree, own machine, same warnings | Yes — own tree, own machine, same consent flow | Unsigned trees permitted *for formulas only*; a signed local repo (minisign or GPG) may additionally serve binaries to this machine only |

Some rules hold at every level:

- **A level can only be lowered by the user, and raised only by the defined path.** There is no `--trust-just-this-once` flag that bypasses a level's capability set — a bypass flag would make the levels decorative.
- **Namespaces are mandatory** for non-official repos (DESIGN §9.6): explicit addressing `audiolab:convolver`, resolution order core > extended > verified > third-party in add order.
- **Vendor-binary packages (`type = "binary"`) follow the same levels.** A `third-party` repo may serve payload-only vendor slices, subject to the signer-pinning rules of DESIGN §12.4 unchanged. Note that the Apple code-signing identity pin is *additional* to the repo signature, never a substitute for it.
- **System packages (`[system]`, DESIGN §12.7) are a per-level capability, not a package property.** `official` and `verified` repositories may serve them. `third-party` repositories never may — no warning flow makes a stranger's kernel extension acceptable. `local` repositories may, on the user's own machine, with the same warnings. The solver refuses a `[system]` package from a non-capable repository with a message that names the level and the remedy, not a generic error. The same capability gates **root-domain services** (`domain = "system"` in the `[service]` table, DESIGN §12.8): running code as root is the privilege that matters, so a third-party repository may declare user agents but never root daemons. The refusal happens at solve time, with the same named-level message.
- **System patches (`[system-patch]`, DESIGN §12.11) carry their own, stricter capability — the strictest gate in the system.** The reason for the extra gate is the blast radius: a `[system-patch]` package replaces an Apple-provided file for every user and every process on the machine. Serving one therefore requires the `system-patch` capability: **official and local repositories have it; third-party never does.** A `verified` repository receives it only through an explicit per-repo grant from the machine's owner — `aslice repo allow-system-patch <name>`, refused by default, recorded in the state DB, revocable with `aslice repo deny-system-patch <name>` (DESIGN open question #10, resolved in DESIGN v1.8). Contrast this with `system`, which rides on `verified` with no grant: the countersignature vets a repository to *distribute software*, and rewriting the OS warrants one more decision beyond that vetting. Two things are worth separating here. The grant gates *serving*; the DESIGN §12.11 consent flow is unchanged and applies whoever serves the package. A non-capable or ungranted repository that serves a `[system-patch]` package gets a solver refusal naming the level and the remedy.
- **Demotion of a verified repo is a blocking event.** If a `verified` repo's countersignature is revoked, or its key rotates without a re-vouch, the client freezes the repo at its last good snapshot and refuses updates. Every operation that touches the repo prints the reason, and keeps printing it, until the user re-pins or removes it.

## 4. Adding a third-party repository

```
$ aslice repo add https://repo.example.org/aslice
Fetching TUF root metadata…
Repository:  example.org community repo
Namespace:   example
Root key:    openpgp:7A3F 19C2 88E4 0D1B  …  (Ed25519 equivalents shown identically)
Trust level: third-party (binaries allowed; cannot shadow core packages)

Verify this fingerprint out-of-band — project website, release notes,
a signed email. Anyone can serve a repository; the fingerprint IS the
identity. Pin it? [y/N]
```

- The fingerprint is displayed and stored in the DB; any later change is a **blocking event** that requires `aslice repo re-pin` with an explicit confirmation. This is the TOFU contract of DESIGN §9.6, made concrete.
- `aslice repo add --trust local file:///…` is the only way to obtain the `local` level. `official` and `verified` cannot be granted by the CLI at all: `verified` requires the project's countersignature, which arrives through the official source list. That indirection is the point — it is how the project can vouch for a repository without holding anyone's keys.
- Removal is `aslice repo remove example`. Packages installed from the repo remain in the store — they are content-addressed and generation-pinned — but the namespace stops resolving, and `doctor` offers to reparent surviving leaves to core equivalents where those exist.

## 5. Signing keys: two schemes, one verification pipeline

### 5.1 Why two schemes

The canonical scheme is **Ed25519 in minisign-compatible format under TUF** (DESIGN §10.2). The virtues are practical: tiny keys, tiny signatures, a verification routine small enough to audit in an afternoon, and no dependency on the GnuPG ecosystem. This remains the scheme for the official repositories and for aslice's own releases.

Repositories exist, however, so that *other* ecosystems can distribute through aslice — and those ecosystems already sign with **OpenPGP**: upstream release tarballs, vendor checksum files, existing project keyrings. Telling every third-party operator to re-key into minisign would amount to telling the platform's most valuable niche communities (audio, lab, retro) to change their release process for our sake. OpenPGP verification is therefore a first-class, built-in scheme:

- **Implementation:** a self-contained OpenPGP verifier inside aslice, in the Sequoia-PGP style, linked in. There is *no* dependency on a `gpg` binary and no keyserver lookup at verify time. The supported subset is the modern one: Ed25519 and ECDSA/RSA OpenPGP keys, detached and cleartext signatures, SHA-256+ digest algorithms only. SHA-1 signatures are rejected.
- **Key acquisition:** fingerprints are pinned in the source entry or at `repo add` (TOFU, §4). Full keys are fetched from the repository itself (`keys/` in the repo tree, §6) or via WKD as a convenience. Verification, however, always runs against the *pinned fingerprint* — so a hostile keyserver or a swapped `keys/` file produces a hard failure, not a wrong key.
- **No web of trust.** aslice evaluates exactly two things: whether the key matches the pinned fingerprint, and whether it produced a valid signature over the artifact. WoT pathfinding is explicitly out of scope; TOFU plus (for `verified`) the project's countersignature replaces it.

### 5.2 Where each signature lives

| Layer | Scheme | Checked when |
|---|---|---|
| TUF repo metadata (root/snapshot/timestamp/targets) | Ed25519 (spec-native), threshold for official | Every index update |
| Slice signatures | minisign-format Ed25519 (official) **or** OpenPGP detached signature (third-party), scheme recorded per-repo in its TUF targets | Before extraction, always (DESIGN §6.2) |
| `verified` countersignature | Ed25519, core key over the repo's root key fingerprint | At enable time and on every source-list update |
| Vendor artifacts | Apple code-signing identity pin (unchanged, DESIGN §12.4) — orthogonal layer | Before payload extraction |
| Upstream source tarballs in formulas | sha256 pins always; OpenPGP verification where the formula declares `[source.pgp]` — `key_url` plus pinned `fingerprint` (PACKAGE-FORMAT §3.4; BUILD-INFRA §3 "PGP where declared") | At fetch/verify phase of builds |

The client's rule is uniform: **the scheme is a property of the repository, the fingerprint is a property of the pin, and both are enforced before content is trusted.** A mixed ecosystem — an OpenPGP vendor repo alongside the Ed25519 official repos — is the expected steady state, not an edge case.

### 5.3 Rotation and revocation

- **Official keys:** a threshold root (3-of-5, YubiKey custody) with the practiced rotation runbook of DESIGN §10.2. Rotations arrive as ordinary TUF root updates. The compiled-in bootstrap pin is *itself* updated through the self-update path (REVIEW §4.1), and each rotation is announced in the changelog.
- **Third-party keys:** rotation means fingerprint change, and fingerprint change means blocking event (§4). The authoring docs tell repo operators to publish transition signatures — the old key signs the new fingerprint — so that users can re-pin with evidence instead of blind trust. `aslice repo re-pin example` displays the transition proof when one is present.
- **Revocation:** TUF timestamp and snapshot expiry already freeze stale repos. On top of that mechanism, official source-list updates can carry a `revoked_keys` list: a kill switch for a `verified` repo's countersignature that does not require a client release.

## 6. Repository tree addition: `keys/`

The repository tree of DESIGN §9.6 gains one directory:

```
repo.example.org/
 ├── tuf/
 ├── index/
 ├── formulas/
 ├── keys/           # full public keys for every fingerprint the repo asks clients to pin
 └── blobs/sha256/
```

One characterization covers `keys/`: convenience distribution, not authority. Its contents verify against the pinned fingerprint or are rejected. For `verified` repos, `keys/` additionally holds the project's countersignature file, refreshed by source-list updates.

## 7. `aslice repo` command surface, completed

```
aslice repo list [--json]                 # namespaces, levels, key fingerprints, health
aslice repo add <url|file://> [--trust local]
aslice repo remove <name>
aslice repo enable / disable <name>       # verified repos ship disabled; user opts in
aslice repo re-pin <name>                 # guided fingerprint change with transition proof
aslice repo keys <name>                   # show the pinned keyring, scheme, countersignatures
aslice repo audit <name>                  # signature coverage report: every target signed? by which key?
aslice repo prefer <name> <pkg>           # record an overlap decision without the prompt (§10)
aslice repo resolutions / forget <pkg>    # show / clear remembered overlap decisions (§10)
aslice repo re-resolve <pkg>              # re-open the overlap prompt on demand (§10)
aslice repo allow-system-patch / deny-system-patch <name>  # the per-repo verified grant (§3)
aslice repo list --overlaps               # every current overlap with its resolution state (§10)
aslice repo build / sign / publish        # authoring side (DESIGN §9.6); --sign-with ed25519|openpgp
aslice repo list --sources-diff           # what the last source-list TUF update changed
```

`aslice repo audit` re-verifies the signature over *every* target in a repo's current snapshot and reports scheme, key, and coverage. It exists so that an operator can prove "everything is signed" is true today — not at some ceremony in the past.

## 8. Failure and edge cases

| Case | Behavior |
|---|---|
| Source-list update fails/tampered | Client keeps the last good list; core/extended keep working; warning surfaced by `doctor` |
| Repo serves a key that doesn't match the pin | Hard refusal before any content is fetched; event logged |
| `verified` repo's countersignature revoked | Repo frozen at last good snapshot, updates refused, persistent banner until re-pin/remove |
| `local` repo contains binary targets | Binaries refused (source-build formulas only) unless the local repo is signed and the machine's user pinned its key |
| A `third-party` repo serves a `[system]` package | Solve-time refusal naming the trust level and the remedy; the `system` capability is never granted to third-party (§3) |
| A `third-party` repo declares `domain = "system"` in `[service]` | Solve-time refusal naming the trust level and the remedy; user-domain agents from third-party repos remain allowed (§3) |
| A `third-party` repo — or a `verified` repo without the per-repo grant — serves a `[system-patch]` package | Solve-time refusal naming the trust level and the remedy (`aslice repo allow-system-patch <name>` for a verified repo; the capability is never available to third-party) (§3) |
| Two third-party repos claim the same namespace | Second `add` is refused; namespaces are unique per client |
| GPG key uses SHA-1 self-signatures / legacy packets outside the supported subset | Clear rejection message naming the unsupported feature; the answer is a modern key, not a looser verifier |
| User deletes `sources.toml` | Bootstrap-embedded defaults regenerate it at next run (user edits are in `sources.toml.d/`-style drop-ins, so deletion loses nothing) |

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

## 10. Overlapping packages across repositories

Namespaces make collisions *addressable* (`audiolab:convolver` vs `core:convolver`), but addressing is not what most people type — they type `aslice install convolver`. When more than one enabled repository serves the same bare package name, that bare name is **ambiguous**, and aslice never resolves ambiguity silently.

### 10.1 When overlap is detected

Overlap is computed at index-snapshot time, not at install time. After every repo metadata update, the client builds the set of package names served by more than one enabled repository; a name enters the set when any two enabled repos serve it, regardless of version. Three classes of overlap are distinguished:

| Class | Meaning | Default posture |
|---|---|---|
| **shadow** | a non-official repo serves a name that core/extended also serves | core/extended wins automatically; the shadow is reported by `doctor` (DESIGN §9.6) — never prompted, never silently taken |
| **peer overlap** | two non-official repos (`verified` or `third-party`) serve the same name | **prompt on first encounter** (§10.2) |
| **version divergence** | same name, same repo preference, but the chosen repo's version is older than a loser's | noted in `--explain` output; no prompt — this is normal |

Trust levels still dominate the classification: a `third-party` repo can never shadow a `verified` one, and neither can shadow official. Prompts occur only between repos at the *same* effective level, which is where the genuine ambiguity lives.

### 10.2 The prompt

```
$ aslice install convolver
The package "convolver" is provided by two repositories:

  1. audiolab:convolver  2.3.1   (verified, enabled 2026-09-12)
  2. plugins:convolver   2.4.0   (third-party, added 2026-09-18)

Which repository should bare "convolver" resolve to?
  [1] audiolab (recommended: higher trust level)
  [2] plugins
  [n] namespace-only — always require audiolab:convolver / plugins:convolver
  [a] abort

Choice [1]: 2
Remember this decision? [Y/n/once]
```

- The prompt shows trust level, version, and provenance for each candidate: the inputs to the decision, not just the names.
- `[n]` (namespace-only) is a real choice, not an escape hatch: the user can declare that this bare name should *never* auto-resolve, which forces explicit namespaces forever.
- Non-interactive contexts (scripts, `--json`, no TTY) never prompt. A bare ambiguous name there is a solve error carrying a machine-readable `ambiguous_name` code that lists the candidates; scripts must pin explicitly or pre-seed a decision (§10.4).

### 10.3 Decisions are remembered — in the state database

The answer is persisted in a dedicated table of the client's SQLite state database (DESIGN §8.1, `db/state.sqlite`):

```sql
CREATE TABLE repo_resolutions (
    name        TEXT NOT NULL,          -- bare package name
    chosen_repo TEXT,                   -- namespace chosen, NULL for namespace-only
    decided_at  TEXT NOT NULL,          -- ISO-8601
    snapshot    TEXT NOT NULL,          -- index snapshot hash at decision time
    reason      TEXT NOT NULL DEFAULT 'user-prompt',
    PRIMARY KEY (name)
);
```

A stored decision has the following semantics:

- **It survives upgrades, repo metadata refreshes, and reboots.** A decision is profile-independent machine state, in the same category as the repo key pins (§4) and the installed-set records.
- **It is revalidated, not blindly trusted.** If the chosen repo is removed, disabled, demoted (§3), or stops serving the name, the decision lapses, and the next encounter prompts again — with a line noting the expired decision and the reason. A decision never resurrects a repository the user removed.
- **It is one level of indirection, not a lock.** `aslice install plugins:convolver` always bypasses the stored decision — an explicit namespace wins — and the decision governs only the *bare* name.
- **New entrant invalidates.** If a third repo begins serving an already-decided name, the decision is *not* re-prompted by default — that way lies prompt fatigue. Instead, `aslice repo list --overlaps` and `doctor` show every current overlap with its resolution state, and `aslice repo re-resolve convolver` re-opens the prompt on demand.
- **Auditability.** `aslice repo resolutions` lists every stored decision with its timestamp and the snapshot it was made against; `aslice repo forget convolver` deletes one. Decisions appear in `--json` output everywhere they apply.

### 10.4 Pre-seeding and fleets

Decisions are rows in a documented table, which makes them scriptable without ever driving the interactive prompt:

```
aslice repo prefer convolver plugins            # insert/update a decision non-interactively
aslice repo prefer convolver --namespace-only   # the [n] choice, scripted
aslice repo prefer --import resolutions.json    # fleet/lab provisioning
```

A lab that images fifty machines writes its resolution policy once and distributes the result: the same SQLite file, with the same semantics as if a human had answered fifty prompts.

## 11. The state database's role

DESIGN §8.1 lists `db/state.sqlite` as "the only mutable state besides the store." This section makes the repository-facing half of that claim concrete. The database holds — and is the single source of truth for:

| Table (indicative) | Contents | Written by |
|---|---|---|
| `installed` | installed set: build_id, origin, `on_request`, generation membership | install/uninstall/rollback |
| `repo_pins` | per-repo pinned key fingerprints, scheme, trust level, TOFU timestamp | `repo add` / `re-pin` |
| `repo_resolutions` | remembered overlap decisions (§10.3) | the prompt / `repo prefer` |
| `solve_cache` | memoized resolutions keyed by index snapshot hash | the solver |
| `history` | every mutating operation with timestamp, operation ID, and generation delta | every transaction |

Three properties carry the design:

- **WAL mode, prepared statements, single file** (DESIGN §5.2). Concurrent `aslice` processes serialize cleanly, and a crash leaves the file consistent.
- **Nothing in the DB is needed to *verify* anything.** Trust derives from signatures and pins re-checked against content; the DB only records decisions and state. Deleting the database loses the installed-set record and the remembered prompts — both recoverable, by rediscovery from the store and by re-prompting — but it cannot *weaken* verification, because verification never consults the database for authority. The pins it does consult are themselves checked against live content.
- **Inspectable.** `aslice db query` (read-only, schema-documented) exists so that power users and fleet tooling can see their own state. The format is SQLite, chosen precisely because standard tools already read it.
