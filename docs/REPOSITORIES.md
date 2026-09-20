# aslice Repositories — Sources, Trust Levels, and Signing Keys

- **Status:** Design draft, v0.3 — September 2026 (v0.2: cross-repository overlap resolution with remembered decisions — §10; the state database's role — §11. v0.3: `history` rows carry the operation ID that correlates with the operation log — DESIGN §12.5)
- **Companion to:** [DESIGN.md](DESIGN.md) v1.1 (§8 store/state, §9.6 repository system, §10.2 signatures, §12.5 logging, §12.6 doctor), [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) v0.3, [BUILD-INFRA.md](BUILD-INFRA.md) v0.1 (§9 result→repository)
- **Scope:** the shipped official source list, adding third-party repositories, the inherent trust-level model, and the dual signature scheme (Ed25519 canonical, OpenPGP supported).

---

## 1. Axioms

1. **Trust is per-repository, never global** (DESIGN §9.6). Adding a repository grants it exactly the capabilities of its trust level and nothing more.
2. **Trust levels are inherent, not labels.** A level is a set of *enforced capabilities* — what namespaces the repo may serve, whether its binaries may install, whether it may shadow core package names — checked by the solver and the verifier in code. A repo cannot talk its way into a higher level; only the user (or the project's countersignature, for verified repos) can raise one.
3. **Every served artifact is signed.** There is no trust level at which unsigned binaries install. The levels differ in *whose* signature is required and *what the repo is allowed to offer* — never in whether verification happens.
4. **No repository can execute code at install time** regardless of level (DESIGN §10.1). Trust levels govern distribution, not the structural guarantees.
5. **The official list is data, signed and versioned** — not hardcoded logic. aslice ships with a source list file; the file can be inspected, diffed, and (for the paranoid) replaced wholesale with a pinned copy.

## 2. The shipped source list

aslice installs with `/opt/aslice/etc/sources.toml`, part of the bootstrap package and updated through the normal TUF channel (it is a TUF target like any other metadata — versioned, rollback-protected, and diffable with `aslice repo list --sources-diff`):

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

Properties:

- **The core key fingerprint is compiled into the bootstrap binary** as well as listed here, so a tampered `sources.toml` alone cannot redirect the core namespace — the client refuses a core entry whose fingerprint differs from the compiled-in pin. The file is the *discovery* layer; the binary pin is the root of the root.
- The list is where **verified community repositories** are advertised (§3): known, project-vouched, but disabled by default — discovery without implicit trust.
- Users may edit the file directly or via `aslice repo add/remove/enable/disable`; both paths validate against the schema and re-pin fingerprints loudly on any change.
- A completely offline/air-gapped machine works with the shipped file plus `file://` mirrors — the list is plain data (§8).

## 3. Trust levels

Four levels, ordered by what a repository is permitted to do:

| Level | How a repo gets it | May serve binaries? | May shadow core names? | Signature requirement |
|---|---|---|---|---|
| `official` | Compiled-in fingerprint pin; only core/extended ship this way | Yes | n/a (it *is* the namespace) | Ed25519, threshold TUF root (DESIGN §10.2) |
| `verified` | Listed in the official source list **with a project countersignature** over the repo's key; user enables explicitly | Yes | No — solver treats shadowing as a conflict with a loud message | Ed25519 **or** OpenPGP; key vouched by the core key |
| `third-party` | `aslice repo add <url>` by the user, TOFU key pinning | Yes — installs show an unambiguous `third-party/<name>` provenance line | Never silently; `doctor` reports; solver prefers core/extended unconditionally | Ed25519 or OpenPGP; fingerprint displayed at add, out-of-band verification recommended |
| `local` | `aslice repo add file:///path --trust local` (development trees) | **No.** Formulas resolve for source builds only; any binary target in the repo is refused | No | Unsigned trees permitted *for formulas only*; a signed local repo (minisign or GPG) may additionally serve binaries to this machine only |

Rules that hold across all levels:

- **Level can only be lowered by the user, raised only by the defined path.** There is no `--trust-just-this-once` flag that bypasses a level's capability set; bypass flags would make the levels decorative.
- **Namespaces are mandatory** for non-official repos (DESIGN §9.6): explicit addressing `audiolab:convolver`, resolution order core > extended > verified > third-party in add order.
- **Vendor-binary packages (`type = "binary"`) follow the same levels.** A `third-party` repo may serve payload-only vendor slices; the signer-pinning rules of DESIGN §12.4 apply unchanged, and the Apple code-signing identity pin is *additional* to the repo signature, never a substitute.
- **Demotion events are loud.** If a `verified` repo's countersignature is revoked or its key rotates without a re-vouch, the client freezes that repo at its last good snapshot, refuses updates, and prints the reason on every operation that touches it until the user re-pins or removes it.

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

- The fingerprint is displayed, stored in the DB, and any later change is a **blocking event** requiring `aslice repo re-pin` with an explicit confirmation — the TOFU contract of DESIGN §9.6, made concrete.
- `aslice repo add --trust local file:///…` is the only way to get the `local` level; `official` and `verified` cannot be granted by the CLI at all — `verified` requires the project's countersignature to arrive through the official source list, which is how the project can vouch without holding anyone's keys.
- Removal is `aslice repo remove example` — packages installed from it remain in the store (they're content-addressed and generation-pinned) but the namespace stops resolving; `doctor` offers to reparent surviving leaves to core equivalents where they exist.

## 5. Signing keys: two schemes, one verification pipeline

### 5.1 Why two schemes

The project's canonical scheme is **Ed25519 in minisign-compatible format under TUF** (DESIGN §10.2): tiny keys, tiny signatures, a verification routine small enough to audit in an afternoon, and no dependency on the GnuPG ecosystem. That stays the scheme for the official repositories and for aslice's own releases.

But repositories exist to let *other* ecosystems distribute through aslice, and those ecosystems already sign with **OpenPGP** — upstream release tarballs, vendor checksum files, existing project keyrings. Telling every third-party operator to re-key into minisign would be telling the platform's most valuable niche communities (audio, lab, retro) to change their release process for us. So OpenPGP verification is a first-class, built-in scheme:

- **Implementation:** a self-contained OpenPGP verifier inside aslice (Sequoia-PGP-style, linked in — *no* dependency on a `gpg` binary, no keyserver lookups at verify time). Verification supports the modern subset: Ed25519 and ECDSA/RSA OpenPGP keys, detached and cleartext signatures, SHA-256+ digest algorithms only (SHA-1 signatures rejected, loudly).
- **Key acquisition:** fingerprints are pinned in the source entry or at `repo add` (TOFU, §4). Full keys are fetched from the repository itself (`keys/` in the repo tree, §6) or via WKD as a convenience — but verification always happens against the *pinned fingerprint*, so a hostile keyserver or a swapped `keys/` file yields a hard failure, not a wrong key.
- **No web of trust.** aslice evaluates exactly two things: does the key match the pinned fingerprint, and did it produce a valid signature over the artifact. WoT pathfinding is explicitly out of scope — TOFU + (for `verified`) the project's countersignature replaces it.

### 5.2 Where each signature lives

| Layer | Scheme | Checked when |
|---|---|---|
| TUF repo metadata (root/snapshot/timestamp/targets) | Ed25519 (spec-native), threshold for official | Every index update |
| Slice signatures | minisign-format Ed25519 (official) **or** OpenPGP detached signature (third-party), scheme recorded per-repo in its TUF targets | Before extraction, always (DESIGN §6.2) |
| `verified` countersignature | Ed25519, core key over the repo's root key fingerprint | At enable time and on every source-list update |
| Vendor artifacts | Apple code-signing identity pin (unchanged, DESIGN §12.4) — orthogonal layer | Before payload extraction |
| Upstream source tarballs in formulas | sha256 pins always; OpenPGP verification where the formula declares a `pgp_fingerprint` (BUILD-INFRA §3 "PGP where declared") | At fetch/verify phase of builds |

The client's rule is uniform: **the scheme is a property of the repository, the fingerprint is a property of the pin, and both are enforced before content is trusted.** Mixed ecosystems (an OpenPGP vendor repo alongside the Ed25519 official repos) are the expected steady state, not an edge case.

### 5.3 Rotation and revocation

- **Official keys:** threshold root (3-of-5, YubiKey custody) with the practiced rotation runbook of DESIGN §10.2; rotations arrive as ordinary TUF root updates, and the compiled-in bootstrap pin is *itself* updated through the self-update path (REVIEW §4.1) with a loud changelog line.
- **Third-party keys:** rotation = fingerprint change = blocking event (§4). Repo operators are told in the authoring docs to publish transition signatures (old key signs the new fingerprint) so users can re-pin with evidence instead of blind trust: `aslice repo re-pin example` displays the transition proof when present.
- **Revocation:** TUF timestamp/snapshot expiry already freezes stale repos. On top of that, official source-list updates can carry a `revoked_keys` list — a kill switch for a `verified` repo's countersignature that does not require a client release.

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

`keys/` is convenience distribution, not authority: its contents verify against the pinned fingerprint or are rejected. For `verified` repos, `keys/` additionally contains the project's countersignature file, refreshed by source-list updates.

## 7. `aslice repo` command surface, completed

```
aslice repo list [--json]                 # namespaces, levels, key fingerprints, health
aslice repo add <url|file://> [--trust local]
aslice repo remove <name>
aslice repo enable / disable <name>       # verified repos ship disabled; user opts in
aslice repo re-pin <name>                 # guided fingerprint change with transition proof
aslice repo keys <name>                   # show the pinned keyring, scheme, countersignatures
aslice repo audit <name>                  # signature coverage report: every target signed? by which key?
aslice repo build / sign / publish        # authoring side (DESIGN §9.6); --sign-with ed25519|openpgp
aslice repo list --sources-diff           # what the last source-list TUF update changed
```

`aslice repo audit` deserves emphasis: it re-verifies the signature over *every* target in a repo's current snapshot and reports scheme, key, and coverage — the operator-facing proof that "everything is signed" is true today, not at some ceremony in the past.

## 8. Failure and edge cases

| Case | Behavior |
|---|---|
| Source-list update fails/tampered | Client keeps the last good list; core/extended keep working; warning surfaced by `doctor` |
| Repo serves a key that doesn't match the pin | Hard refusal before any content is fetched; event logged |
| `verified` repo's countersignature revoked | Repo frozen at last good snapshot, updates refused, loud banner until re-pin/remove |
| `local` repo contains binary targets | Binaries refused (source-build formulas only) unless the local repo is signed and the machine's user pinned its key |
| Two third-party repos claim the same namespace | Second `add` is refused; namespaces are unique per client |
| GPG key uses SHA-1 self-signatures / legacy packets outside the supported subset | Clear rejection message naming the unsupported feature; the answer is a modern key, not a looser verifier |
| User deletes `sources.toml` | Bootstrap-embedded defaults regenerate it at next run (user edits are in `sources.toml.d/`-style drop-ins, so deletion loses nothing) |

## 9. Amendments carried into the other documents

- **DESIGN §9.6:** the "Trust is per-repository" bullet is superseded by the level model of §3 here; the bullet now points at this document.
- **DESIGN §10.2:** the signature section now reads as dual-scheme — Ed25519/minisign canonical for official infrastructure, OpenPGP as a built-in first-class scheme for third-party repositories and formula-declared upstream verification.
- **README:** vocabulary gains nothing (a repository is still a repository); the security bullet now mentions trust levels and dual signature schemes.
- **Open question #6 (new, for reviewers):** should `verified` repos be installable-binary-capable immediately at enable time, or should enabling one additionally require a per-repo `--accept-binaries` step? Current answer: enable implies binaries (the countersignature is the vetting); the extra click was judged ceremony without security content. Review wanted.

---

## 10. Overlapping packages across repositories

Namespaces make collisions *addressable* (`audiolab:convolver` vs `core:convolver`), but most users don't type namespaces — they type `aslice install convolver`. When more than one enabled repository serves the same bare package name, that bare name is **ambiguous**, and aslice never resolves ambiguity silently.

### 10.1 When overlap is detected

Overlap is computed at index-snapshot time, not at install time: after every repo metadata update, the client builds the set of package names served by more than one enabled repository. A name enters the overlap set when any two enabled repos serve it, regardless of version. Overlaps are classified:

| Class | Meaning | Default posture |
|---|---|---|
| **shadow** | a non-official repo serves a name that core/extended also serves | core/extended wins automatically; the shadow is reported by `doctor` (DESIGN §9.6) — never prompted, never silently taken |
| **peer overlap** | two non-official repos (`verified` or `third-party`) serve the same name | **prompt on first encounter** (§10.2) |
| **version divergence** | same name, same repo preference, but the chosen repo's version is older than a loser's | noted in `--explain` output; no prompt — this is normal |

Trust levels still dominate: a `third-party` repo can never shadow a `verified` one, and neither can shadow official. Prompts happen only between repos at the *same* effective level — that is where genuine ambiguity lives.

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

- The prompt shows trust level, version, and provenance for each candidate — the decision inputs, not just names.
- `[n]` (namespace-only) is a real choice: the user can declare that this bare name should *never* auto-resolve, forcing explicit namespaces forever. Some names deserve that.
- Non-interactive contexts (scripts, `--json`, no TTY) never prompt: bare ambiguous names are a solve error with a machine-readable `ambiguous_name` code listing the candidates. Scripts must pin explicitly or pre-seed a decision (§10.4).

### 10.3 Decisions are remembered — in the state database

The answer is persisted in the client's SQLite state database (DESIGN §8.1, `db/state.sqlite`) in a dedicated table:

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

Semantics of a stored decision:

- **It survives upgrades, repo metadata refreshes, and reboots** — it is profile-independent machine state, like the repo key pins (§4) and the installed-set records.
- **It is revalidated, not blindly trusted.** If the chosen repo is removed, disabled, demoted (§3), or stops serving the name, the decision lapses and the next encounter prompts again — with a line noting the expired decision and why. A decision never resurrects a repo the user removed.
- **It is one level of indirection, not a lock.** `aslice install plugins:convolver` always bypasses the stored decision (explicit namespace wins); the decision only governs the *bare* name.
- **New entrant invalidates.** If a third repo begins serving an already-decided name, the decision is *not* re-prompted by default (that way lies prompt fatigue) — but `aslice repo list --overlaps` and `doctor` show all current overlaps with their resolution state, and `aslice repo re-resolve convolver` re-opens the prompt on demand.
- **Auditability.** `aslice repo resolutions` lists every stored decision with its timestamp and the snapshot it was made against; `aslice repo forget convolver` deletes one. Decisions are included in `--json` everywhere they apply.

### 10.4 Pre-seeding and fleets

Because decisions are rows in a documented table, they are scriptable without ever driving the interactive prompt:

```
aslice repo prefer convolver plugins            # insert/update a decision non-interactively
aslice repo prefer convolver --namespace-only   # the [n] choice, scripted
aslice repo prefer --import resolutions.json    # fleet/lab provisioning
```

A lab that images fifty machines writes its resolution policy once and distributes it — the same SQLite file, the same semantics as if a human had answered fifty prompts.

## 11. The state database's role, stated plainly

DESIGN §8.1 lists `db/state.sqlite` as "the only mutable state besides the store." This document makes the repository-facing half of that concrete. The database holds, and is the single source of truth for:

| Table (indicative) | Contents | Written by |
|---|---|---|
| `installed` | installed set: build_id, origin, `on_request`, generation membership | install/uninstall/rollback |
| `repo_pins` | per-repo pinned key fingerprints, scheme, trust level, TOFU timestamp | `repo add` / `re-pin` |
| `repo_resolutions` | remembered overlap decisions (§10.3) | the prompt / `repo prefer` |
| `solve_cache` | memoized resolutions keyed by index snapshot hash | the solver |
| `history` | every mutating operation with timestamp, operation ID, and generation delta | every transaction |

Properties the design relies on:

- **WAL mode, prepared statements, single file** (DESIGN §5.2) — concurrent `aslice` processes serialize cleanly; a crash leaves the file consistent.
- **Nothing in the DB is needed to *verify* anything.** Trust derives from signatures and pins re-checked against content; the DB records decisions and state. A deleted database loses the installed set record and remembered prompts (recoverable by rediscovery from the store and re-prompting) — it can never *weaken* verification, because verification never consults it for authority, only for pins that are themselves checked against live content.
- **Inspectable.** `aslice db query` (read-only, schema-documented) exists precisely so power users and fleet tooling can see their own state. It's SQLite — the most inspectable database format in existence — on purpose.
