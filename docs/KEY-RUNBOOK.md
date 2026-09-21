# Key Ceremony and Rotation Runbook

This runbook governs every cryptographic key aslice trusts; DESIGN §10.2 calls for it by name ("revocation and rotation is a practiced runbook, not a hope"). Its purpose can be stated in one sentence: the worst day of the project should be a procedure, not an improvisation.

Four rules govern everything below, and no procedure in this document suspends them:

- **Keys are generated on the hardware that holds them.** A private key that has ever touched a networked machine, a disk, or a backup medium is treated as compromised for root purposes.
- **Every ceremony produces a written record** — who attended, what was generated, fingerprints, where each artifact went — committed to the private maintainer vault and summarized (public keys and fingerprints only) in the repository.
- **Nobody acts alone on key material.** Every procedure below requires at least two custodians physically or verifiably present, including the ones marked "solo-runnable" — the second person is the witness, not a rubber stamp.
- **Drills are real.** A rotation that has never been executed end-to-end is assumed not to work. See §7.

---

## 1. Key inventory

| Key | Scheme | Custody | Lifetime | What a compromise can do |
|---|---|---|---|---|
| **TUF root** | Ed25519, 3-of-5 threshold | 5 YubiKeys, 5 founding maintainers, geographically distributed, offline | Years (rotate on custodian change, compromise, or drill failure) | Everything. This is the keys to the kingdom — hence offline, thresholded, and slow to use by design |
| **TUF targets** | Ed25519 | Signing host, YubiKey | ~1 year, or on suspicion | Sign index metadata naming malicious slices — mitigated by minisign per-slice verification and the transparency log |
| **TUF snapshot + timestamp** | Ed25519 | Signing host, online (the only online keys) | Hours–days, rotated automatically | Freeze or rollback attacks for the key's lifetime — short-lived so the blast radius self-heals |
| **Slice-signing (minisign)** | Ed25519 (minisign-compatible) | Signing host, YubiKey | ~1 year, or on suspicion | Sign individual slices — caught by the transparency log on next publish; clients reject unknown signers |
| **Coordinator job-signing** | Ed25519 | Coordinator host | ~6 months | Inject build jobs into the farm — results die in quarantine without signing-host promotion (BUILD-INFRA §7.1), so this buys noise, not compromise |
| **Per-agent identities** | Ed25519 | Each agent, generated at `farm enroll` | Until revoked | Forge *evidence* (build results). Never authority: agents cannot ship slices by construction (BUILD-INFRA §7.2) |
| **Security-contact PGP** | OpenPGP, modern algorithms only | Project owner, hardware token | ~2 years | Intercept/spoof vulnerability reports — bad, recoverable, and cross-signed into the repo so tampering shows |

The asymmetry is deliberate: the keys that can hurt users the most are the hardest to use, and the keys used constantly can hurt the least.

## 2. The initial root ceremony

This ceremony is performed exactly once, before the first public snapshot; it is repeated in full only on the disaster path (§6).

1. **Attendees:** at least 4 of the 5 root custodians, physically present or verifiably co-present on video with screen share. One is designated operator, one scribe.
2. **Machine:** a clean, air-gapped Mac — fresh OS install, network interfaces disabled and verified off (`ifconfig`, no routes), never previously used. It is wiped or retired after the ceremony.
3. **Generate:** each custodian generates their root key share on their own YubiKey (non-exportable). Public keys are exported to the air-gapped machine and every fingerprint is read aloud and confirmed against the hardware display.
4. **Assemble:** construct TUF root metadata with threshold 3-of-5, signed on the YubiKeys. Set the root expiry far out (years) with a calendar reminder — an expired root is a self-inflicted outage.
5. **Publish:** root public metadata + fingerprints go to (a) the repository, (b) the second transport (Release asset + Pages, per DESIGN §10.3), (c) the installer's pinned hash. Three placements, compared byte-for-byte before the ceremony closes.
6. **Record:** the ceremony report — attendees, fingerprints, YubiKey serials, metadata hash, timestamp — is signed by each custodian's key and archived. The genesis entry of the transparency log references this hash.
7. **Distribute:** YubiKeys return to their custodians' separate physical locations. No two root shares may live in the same building.

## 3. Routine rotation

| Key | Cadence | Procedure | User-visible? |
|---|---|---|---|
| timestamp / snapshot | automated, hours–days | Signing host rotates on schedule; old keys destroyed | No — TUF chaining handles it |
| targets | yearly, or on suspicion | Signing host generates a successor; root signs the delegation rollover at the next root-use event | No |
| slice-signing (minisign) | yearly, or on suspicion | Generate successor on the signing host's YubiKey; the new public key ships in the next TUF snapshot's trusted-key set **before** the first slice signed with it; old key remains accepted for previously published slices (digests are immutable; history is not re-signed) | No — clients learn keys through TUF |
| coordinator | ~6 months | Generate successor, agents pin the new coordinator key on next lease | No |
| agent | on demand | `farm enroll` reissue; the old identity is revoked at the coordinator | No |
| **root** | custodian change, compromise, or failed drill | §4 and §5 | **Yes** — see below |

### 3.1 Root rotation (planned)

TUF makes this survivable by design; the runbook makes it practiced.

1. Convene at least 3 custodians — the threshold — plus the incoming or outgoing custodian where one is involved.
2. On the air-gapped machine, build root metadata version N+1: the new key set, threshold, and expiry, **signed by the old threshold keys**.
3. Publish N+1 through the normal TUF channel. Clients chain-trust it automatically — this is the mechanism working as intended.
4. Update the three placements (repository, second transport, installer pin) and the ceremony archive.
5. The outgoing share is destroyed on its custodian's hardware token, witnessed.
6. Announce in the release notes. Planned root rotation is a non-event for users and should be announced as one — calm is the goal of the exercise.

## 4. Compromise response

The clock starts the moment any custodian has reason to believe a key may be compromised: a lost YubiKey, an unexplained signature, a transparency-log mismatch, an investigation event from the farm that points at key material. The response has the same shape regardless of which key is in question:

1. **Freeze.** The current timestamp key is revoked first — one command on the signing host. Clients pin the last good snapshot, the repository stops moving, and freshness pauses while users stay unaffected and safe (BUILD-INFRA §11).
2. **Assess, in the open.** A public security advisory goes up within 24 hours saying what is known, what is frozen, and what users should do (usually: nothing, don't panic-install from random sources). Silence during a key event is how trust dies.
3. **Rotate** per the table: snapshot, timestamp, targets, and slice-signing rotations are signing-host operations, plus a threshold-signed root update if the delegation changed. For the root itself, §4.1.
4. **Audit the window.** Every snapshot and slice published between last-known-good and the freeze is re-verified against the transparency log and, where the reproducibility class demands it, rebuilt for digest comparison by evidence builders. Findings are published either way.
5. **Unfreeze and postmortem.** The advisory is updated with the full timeline. Postmortems are blameless, public, and result in at least one concrete runbook or tooling change.

### 4.1 Root compromise or loss of threshold

The remaining cases concern the root itself: a share compromised, or shares lost until fewer than 3 remain valid.

1. Freeze (§4 — online keys die first; a root event freezes everything downstream).
2. Convene every reachable custodian. With at least 3 valid shares, rotate as in §3.1, revoke the bad share in metadata N+1, and treat the window since the share was last verifiably safe as suspect: the audit of §4 step 4 extends to the root metadata itself.
3. With **fewer than 3 valid shares**, the root is unrecoverable. This is the disaster path (§6).

## 5. Custodian changes

- **Joining:** the incoming custodian generates their share at a convened ceremony (≥3 existing custodians present), and a planned root rotation (§3.1) moves to the new 5-key set. No share is ever transferred person-to-person — a share that changed hands is compromised by definition.
- **Leaving:** planned root rotation to a set without the departing share; the departing custodian destroys their share, witnessed, and the destruction is recorded.
- **Unreachable custodian:** 90 days of documented unreachability starts the same rotation. Shares held by the unreachable are revoked in metadata, not presumed malicious.

## 6. The disaster path: root unrecoverable

With fewer than 3 valid root shares, TUF chaining is impossible: no metadata signed by the old root can be produced, and existing clients will — correctly — refuse to trust anything new. There is exactly one recovery, and it is executed in the open:

1. Full freeze and advisory (§4). The advisory says: the root is dead, here is what happened.
2. A new initial ceremony (§2) with the surviving + replacement custodians: new root, new fingerprints, new installer pins, new second-transport placement.
3. Existing users re-run the installer (or a dedicated `aslice doctor --fix` path that walks them through pinning the new root **with the fingerprints shown from two independent transports**). There is no silent path past this — a silent root swap is the attack the design exists to prevent.
4. Re-sign and re-publish the repository under the new root. Slice digests are content-addressed and unchanged; the transparency log shows continuity of content across the root change.
5. Postmortem — and this runbook is amended with whatever the drill or disaster taught.

This path will be embarrassing if it ever happens. It is written down so that it is *only* embarrassing.

## 7. Drills

- **Annually (calendar-scheduled, minuted):** a full planned root rotation (§3.1) executed end-to-end on the real infrastructure. If that ever proves impossible, the finding *is* the drill's output, and it triggers custodian replacement until the rotation works. The same sitting rehearses a freeze/unfreeze and audits a random week of the transparency log.
- **On every custodian change:** the rotation doubles as that year's drill.
- **On every new signing host:** restore-from-archive rehearsal — the host is rebuilt from the ceremony archive and must reproduce the expected key set and config before it may sign anything.

## 8. What this runbook does not cover

- **Users' machines.** There are no user accounts, no per-user keys, and no telemetry to protect (DESIGN §2.2 N7) — the data we hold about users is none.
- **Third-party orchards' keys.** Their trust level, their problem, their runbook; REPOSITORIES.md §5 governs how clients pin them.
- **Upstream/vendor signing keys.** Detected by signer pinning (DESIGN §10.2) as a hard failure, handled as an orchard security event (ORCHARD-POLICY §16), not a key event of ours.

---

*History: September 2026 — editorial pass: prose revised for directness; no procedural changes. September 2026 — prose rewrite throughout: the runbook reworded in the project's technical-writing voice; no procedural changes.*
