# Signing, Recovery, and Key Rotation Runbook

> State, identity, privilege, and recovery contracts: [STATE-AND-RECOVERY](../STATE-AND-RECOVERY.md). Protected-volume patching: [SYSTEM-VOLUMES](../SYSTEM-VOLUMES.md). These specifications do not establish completed implementation or platform validation.

This runbook governs every cryptographic key aslice trusts, as called for in [DESIGN §10.2](../DESIGN.md#signatures-and-repository-integrity-tuf). The worst day of the project should be a procedure, not an improvisation.

**Status: design, September 2026.** The initial release uses one accountable operator, two existing Raspberry Pis, and encrypted software keys. Hardware validation and the drills below remain launch requirements, not completed work. Independent custodians and hardware tokens are future options, not launch prerequisites.

*Project terms, acronyms, and the Homebrew translation table: [NOMENCLATURE.md](../NOMENCLATURE.md).*

Four rules govern everything below:

- **Root stays offline; release signing is automatic.** Keep the root key on its disconnected Pi and distinct targets, snapshot, and slice-signing keys on the dedicated networked release Pi. Encrypt private material at rest and in offline backups. Never copy these keys to the farm or publisher. Store recovery secrets separately from backup media.
- **Every key event produces a record.** Record operator, device identities, public fingerprints, metadata versions and hashes, time, and backup locations in the private recovery archive. Publish a signed summary without private keys, recovery secrets, or sensitive storage details.
- **Trust is explicit.** Initial users trust the project owner. Multiple owner-controlled devices provide separation and recovery, not independent-party oversight. Software keys are extractable if a Pi or its unlocked storage is compromised; backups are additional key copies requiring protection.
- **Drills are real.** Complete §7 before launch and retain receipts. Written procedures are not evidence that recovery works.

<a id="key-inventory-and-machines"></a>

## 1. Key inventory and machines

The **root Pi** holds only root signing authority. Disable its wired and wireless networking, verify no active connections or routes, and keep it disconnected during use. The **signing host** is a separate dedicated networked **release Pi**, holding distinct targets, snapshot, and slice-signing keys. Neither runs package builds or supplied scripts. Restrict the release Pi to authenticated candidate delivery from the publisher, signature return, and necessary administration/time synchronization; build agents cannot submit signing requests. Pin the publisher identity and trusted release-policy authorities during setup. Check clocks against a trusted time reference before signing metadata. Initial provisioning and unlocking encrypted keys after a restart may require the owner; routine releases require no intervention.

The **publisher** is the restricted preparation/publication VM on the owned Mac Pro. It checks quarantine gates, prepares bundles, verifies returned signatures, and publishes. It holds repository credentials and the timestamp key, but no root or release private keys. Persist timestamp versions across refreshes and publisher recovery; if that state is unavailable or untrustworthy, rotate the timestamp key through a root update before resuming. Build guests receive none of these credentials. Host or hypervisor compromise can tamper with evidence and publication and expose the timestamp key; it does not directly expose offline keys. It still triggers §4.

| Key | Scheme and custody | Rotation policy | Authority on compromise |
|---|---|---|---|
| **TUF root** | Ed25519, 1-of-1, encrypted on root Pi | Annual planned rotation drill; on suspicion use §4.1 | Replace all repository authorities |
| **TUF targets** | Ed25519, release Pi | Yearly or on suspicion | Authorize malicious target metadata |
| **TUF snapshot** | Separate Ed25519 key, release Pi | Yearly or on suspicion | Select metadata versions, subject to targets signatures and client checks |
| **TUF timestamp** | Separate Ed25519 key, online publisher | Yearly or on suspicion | Select signed snapshots and interfere with freshness; cannot extend snapshot expiry |
| **Slice signing** | Minisign-compatible Ed25519, release Pi | Yearly or on suspicion | Sign slices; targets metadata also authorizes their digests |
| **Coordinator job signing** | Ed25519, coordinator | About six months or on suspicion | Inject jobs; quarantine gates still apply |
| **Per-agent identities** | Ed25519, generated at `farm enroll` | Until revoked | Forge build evidence, never publication authority |
| **Security-contact PGP** | Modern OpenPGP key, owner custody | About two years or on suspicion | Intercept or spoof vulnerability reports; hardware storage is optional |

The release keys share one Pi, so compromising that online signer can authorize malicious releases despite the keys being separate. Offline root custody supports replacing authority, but cannot undo installations or make compromised content trustworthy. A transparency log supports detection and audit; it cannot prevent an authorized malicious signature or guarantee detection.

<a id="metadata-validity-and-renewal"></a>

### 1.1 Metadata validity and renewal

| Role | Validity from signing | Renewal |
|---|---|---|
| Root | One year | Offline root session before expiry |
| Targets | 90 days | Each release, or automatic renewal when fewer than 30 days remain |
| Snapshot | 90 days | Each release or automatic renewal, binding targets versions, lengths, and hashes |
| Timestamp | 48 hours | Daily online refresh, binding only the approved snapshot version, length, and hash |

Check validity daily. When either targets or snapshot has fewer than 30 days remaining, automatically renew both through §2.1 using the last approved published content and retained authorization/gate records, with no content changes or new approval. Increment metadata versions, preserve target bytes and digests, and bind the renewed targets in the new snapshot. Serialize renewal with releases and timestamp refresh. Alert the operator 30 days before root expiry and on failed automatic renewals or daily timestamp refreshes; keep alerts active until resolved. Renewals do not change keys. Timestamp refresh never renews targets or snapshot metadata; refuse refresh against expired targets or snapshot metadata. Clients reject expired metadata and rollback attempts according to TUF, including its sequential root-update rules. Installed software keeps running, but repository updates can become unavailable.

Key rotation is different: replacing any top-level TUF role key requires a root update, including timestamp-key replacement. Daily timestamp signing needs no root session.

<a id="initial-root-setup"></a>

## 2. Initial root setup

One operator can perform this procedure; no witness or additional custodian is required.

1. Prepare clean root and release Pis with verified OS and signing tools. Archive installation media, tool versions, hashes, and setup instructions. Validate the chosen Pi architecture and tools before relying on them; Linux signing tools do not add Linux package builds to the orchard.
2. Generate the root key on the root Pi and three distinct release keys on the release Pi. Generate the timestamp key on the publisher; take only its public key to the root Pi. Compare exported fingerprints against each generating device's output.
3. Create version 1 root metadata with threshold 1 for each top-level role and the role keys above. Sign on the root Pi with expiry per §1.1. Archive signed root metadata and public keys.
4. Make encrypted offline backups of root and release keys, signing state, and recovery instructions. Keep a backup in a separate physical location from the active devices. Keep recovery secrets separately, recoverable after loss of the primary site. Never include private material in a public archive or release bundle.
5. Restore onto a clean spare Pi and verify fingerprints and test signatures before launch (§7). Remove temporary restored private material after the drill; any retained backup device is inventoried as another key copy.
6. Publish root metadata and fingerprints through the repository and second transport; pin the root hash in the installer. Compare bytes across placements. Sign and archive the setup report; the transparency log's genesis entry references its hash when the log is brought up.

<a id="automatic-orchard-to-client-publication"></a>

### 2.1 Automatic orchard-to-client publication

The owner's merge into the protected environment branch is the final human approval for that environment during single-owner launch, including new core slices: `develop` for dev, `beta` for staging, and `master` for prod. A dev merge does not authorize staging or prod. The existing `aslice repo build / sign / publish` stages exchange a release candidate automatically. This is a design specification: candidate delivery, signer service, publication coordination, and acceptance drills remain implementation work. Client signature formats remain unchanged. Candidate authorization, gate receipts, and signing journals are internal control-plane records, not new fields in the closed TUF or index schemas.

Enforce [ORCHARD-POLICY §18.1](../ORCHARD-POLICY.md#181-environments-branching-and-promoted-builds) and [ORCHARD-POLICY §18.2](../ORCHARD-POLICY.md#182-release-versioning-and-unchanged-content-enforcement) before signing or activation. Bind authorization to repository identity, environment, exact required branch, release base version, and frozen candidate inventory. Staging requires the dev candidate record; prod requires its successful staging record. Reuse the identical finalized artifacts and their signatures; `repo build` prepares publication metadata and does not rebuild or repack promoted payloads. Byte-changing signing, including Apple signing/notarization, precedes the dev inventory freeze. Scope retained state, queues, version reservations, and authorization to each repository/environment so a dev request cannot activate prod. Publication metadata may change under the policy's explicit bookkeeping allowance, but changed release content is refused with a recorded reason and requires a new base version starting in dev. Stale-candidate reconciliation below may rebuild publication metadata only; it cannot substitute artifacts or updated dependencies under the same base version.

1. **Prepare (`repo build`).** After the owner-authorized merge and all required gates, collect artifact bytes, index and targets metadata (including verified graft manifests), existing signatures for retained slices, source blobs, the exact orchard commit, and authenticated gate receipts bound to that commit, build inputs, and artifact digests. Require lint, build, test, ABI, malware, graft-rehearsal, and independent-rebuild gates wherever policy requires them. Failed or missing gates, including unavailable capacity, leave the affected release pending. Include an authenticated merge record from the configured orchard authority, trusted root chain, prior metadata, proposed versions/expiries, and a path/length/hash inventory. Bind a stable candidate identifier and digest to the currently published snapshot and retained signing-state revision. The first candidate declares an empty repository base and uses the root established in §2.
2. **Deliver automatically.** The publisher sends the candidate over an authenticated channel to the release Pi. Transport identity alone is not commit authorization: verify the owner-approved merge record against the configured repository, protected branch, owner identity, and exact commit. Trust anchors and gate policy come from retained configuration, never candidate-supplied keys or policy. Treat paths, archives, metadata, and receipts as untrusted; reject path traversal, unexpected files, inconsistent inventories, unauthorized commits, and unverifiable evidence. Never execute candidate-provided scripts or builds.
3. **Verify and sign (`repo sign`).** Compare against the signer's retained trusted root, last published base, and durable signing journal. Verify artifact hashes, retained signatures, gate receipts, metadata versions, expiry, and expected repository state. Receipt consistency cannot prove that a compromised farm built safe software. Reserve versions durably before signing; sign new slices, then targets, then the snapshot binding those targets. Persist candidate digest, base, reserved versions, exact signed bytes, and outcome before returning signatures. Never sign different bytes at an already reserved version. An identical retry returns the saved result; an interrupted reservation resumes only the same bytes or consumes those versions without reuse. Archive public signing state off-device, including signed but unpublished candidates. If the latest state cannot be established after recovery, stop and reconcile trusted records before signing.
4. **Return and verify automatically.** The publisher re-verifies returned signatures, hashes, versions, expiry, authorization, gates, and expected previous snapshot. Reject changed bytes or a stale base. Serialize signing and activation through one durable publication queue, including renewals and timestamp refreshes, with a fenced writer and a compare-and-swap check on the active repository state. Concurrent or recovered workers cannot activate against an obsolete base. A candidate waiting on gates or an unavailable signer must not hold the publication writer: daily timestamps may still refresh the current valid snapshot. Re-check the active state when resuming the candidate.
5. **Publish (`repo publish`).** Stage the complete verified set, including provider changes, every required dependent rebuild, source blobs, and versioned metadata. Verify staged availability before atomically activating a timestamp referencing the signed snapshot. Readers see a complete old or new set; keep the prior set available on failure and retain immutable objects needed by in-flight clients. Persist activation and acknowledge it to the signer. Lost acknowledgements are reconciled against the active snapshot. Retry identical signed candidates only against their expected base, or report success if that exact candidate is already active. Stale candidates must be reconciled with current published and signed state, rebuilt into a fresh candidate with unused versions, and revalidated before signing again; reconciliation does not require another human approval for already authorized content. Append the public snapshot receipt to the transparency log when deployed and update the dashboard.
6. **Discover on clients.** Normal metadata refresh discovers the published index and slices. Users can search, install, or upgrade through the existing client commands. Publication itself does not install software or bypass client trust, compatibility, or consent checks.

Routine releases and unchanged-content renewals never require the root Pi or per-release approval. Renewal verifies the retained authorization and artifact inventory from the last approved published set; it cannot promote pending content or clear a quarantine. No automation waives a build, test, quarantine, or required independent-rebuild gate. Sign the final bootstrap binary and published checksums on the release Pi too. Apple signing/notarization is separate and must precede the final minisign signature if it changes the bytes. Root renewal and top-level key replacement remain deliberate offline operations (§3).

<a id="routine-key-rotation"></a>

## 3. Routine key rotation

Generate successors on the machine that will hold them. For targets, snapshot, or timestamp replacement, take the successor public key to the root Pi and update its role using §3.1. Stage compatible metadata signed by the successor before activating the new timestamp. Keep intermediate roots available indefinitely.

For slice-key replacement, publish the successor public key in the TUF-authenticated trusted-key set before using it for slices. Planned rotation may retain the old key for previously authorized immutable digests; compromise requires audit and revocation under §4, not unrestricted historical acceptance. Coordinator and agent identity changes retain their enrollment/pinning procedures.

<a id="planned-root-update-or-rotation"></a>

### 3.1 Planned root update or rotation

1. On the root Pi, construct root version N+1 with the intended role keys, thresholds, and expiry. For root-key rotation, generate and back up the successor offline first.
2. Sign N+1 to satisfy **both its predecessor's root threshold and its own root threshold**. With unchanged root keys, a signature may satisfy both. Verify both requirements before publication.
3. Publish sequential versioned roots without gaps. Verify an existing client follows the chain and accepts the compatible release metadata. Preserve intermediate roots for returning clients.
4. Update repository and second-transport placements, installer/bootstrap pins for new installations, and the recovery archive. Announce the change; existing clients follow authenticated rotation without manual re-pinning.
5. After verifying the transition and successor backup restoration, retire superseded private copies, including backups. Retain public metadata and audit records.

<a id="compromise-response"></a>

## 4. Compromise response

Lost devices or backup material, unexplained signatures, and compromised farm or publisher hosts trigger this procedure.

1. **Stop publication and timestamp refresh.** Isolate affected infrastructure and preserve evidence. This is an operational stop, not instant client revocation: clients learn new authority through signed metadata, and an attacker may still serve valid metadata or possess a stolen key. Expiry blocks updates; do not promise unaffected freshness or universal safety.
2. **Publish an advisory within 24 hours.** State what is known, the affected window, and concrete user action. Use independent communication paths if hosting is suspect.
3. **Recover authority.** With a trusted root, rebuild affected infrastructure, replace keys, and publish a root update revoking affected top-level keys. Revoke affected slice authorization through trusted targets metadata. Suspect root authority follows §4.1 instead.
4. **Audit the window.** Inspect published roots, targets, snapshots, slices, and gate evidence since last-known-good. Compare archived receipts and the transparency log where available; rebuild where required. Signature validity cannot clear content signed during compromise.
5. **Resume deliberately.** Publish audited metadata and content with appropriate newer versions, verify with existing and fresh clients, and publish findings and a postmortem. Never bypass client rollback or expiry protection to resume service.

<a id="root-loss-or-compromise"></a>

### 4.1 Root loss or compromise

- **Device failure with a trustworthy backup:** restore offline, verify an independently retained public fingerprint and latest trusted signing state, and rehearse a signature. Possible disclosure requires the compromise path.
- **No usable root key or backup:** use §6. There is no in-band chain without old signing authority.
- **Suspected compromise of the initial 1-of-1 root:** an attacker can authorize replacement roots too. An old-key signature cannot establish legitimate recovery. Use §6 with independently authenticated new pins and an advisory; ordinary rotation alone is insufficient.

<a id="future-independent-custody-and-hardware"></a>

## 5. Future independent custody and hardware

Introduce multi-party custody when independent maintainers actually participate. Each generates a distinct root key under their own custody; TUF requires multiple independent signatures, not shares of one split key. A possible future policy is 3-of-5, but neither five people nor five tokens are launch requirements.

Migrate through §3.1: the first multi-party root must satisfy both the current 1-of-1 authority and its new threshold. Rehearse with a client pinned to the launch root and preserve intermediate roots. Later custodian changes require the then-current and successor thresholds; lost quorum requires §6. Record custody and recovery procedures at that transition.

Hardware is optional. Evaluate exact model, firmware, application, middleware, Pi support, algorithm, signature format, cost, and backup/recovery behavior with actual sign/verify and recovery trials before adoption:

- [SmartCard-HSM USB token](../refs/SMARTCARD_HSM_ALGORITHMS.MD): listed RSA/ECDSA algorithms do not establish Ed25519/minisign compatibility. Backup and threshold-authentication features do not themselves implement TUF's multi-signature threshold. Obtain a quote and confirm the supplied version.
- Existing YubiKey 4 devices: inventory first. [Yubico's PIV documentation](../refs/YUBIKEY_PIV_ALGORITHMS.MD) places PIV Ed25519 support at firmware 5.7+, so these older devices cannot implement the current design through PIV. Other applications require their own compatibility proof.

Keep Ed25519 and minisign for launch. Changing algorithms requires a separate client-compatibility decision. Root-transition requirements follow the [TUF specification](../refs/THE_UPDATE_FRAMEWORK_SPECIFICATION.MD).

<a id="disaster-recovery-trust-rebootstrap"></a>

## 6. Disaster recovery: trust rebootstrap

1. Stop publication and issue the §4 advisory. State whether root authority was lost or compromised.
2. Repeat §2 on clean devices with new keys. Establish new public pins through independently authenticated communication; two copies on compromised hosting are not independent authentication.
3. Existing users explicitly rebootstrap using the new installer or a documented repair flow showing verified fingerprints. No silent root replacement is permitted. A compromised old root's signature alone is not proof of the new one.
4. Audit retained artifacts, re-sign as required, and publish under the new root. Preserve old public history and describe content continuity without implying trust continuity.
5. Publish a postmortem and amend the procedure from observed failures.

<a id="drills-and-acceptance"></a>

## 7. Drills and acceptance

Before launch, record successful runs of:

- Merge a new core slice as owner, complete all CI and quarantine gates, and observe automatic signing and atomic publication with no further approval. On a supported 10.11 test VM, refresh metadata, search for the slice, install it, and run it. Verify bootstrap/checksum signatures too. Record commit, receipts, candidate digest, signed versions, activation, and client output; publication alone leaves installed generations unchanged.
- Failed or missing gates (including unavailable independent rebuild capacity) remain pending. Reject unauthorized commits, modified artifacts, invalid receipts, mismatched metadata hashes, stale bases, and unsafe paths; no supplied script executes and rejected candidates never activate.
- Disconnect the signer, submit concurrent candidates, interrupt signing/staging/activation, and lose the activation acknowledgement. The previous repository stays available while valid. Identical retries are idempotent; stale candidates reconcile against current state, and conflicting bytes or reused versions are rejected. A provider bump with a missing dependent rebuild cannot publish; the completed set activates together.
- Advance a test clock to fewer than 30 days of targets/snapshot validity: automatically renew from the last approved content without owner action, changing versions/expiry and metadata bindings but no target bytes or keys. Check daily 48-hour timestamps. Extend signer/publisher outages through expiry and verify fail-closed updates; a fresh timestamp cannot revive expired targets/snapshot. Recover and reconcile before resuming.
- Client rejection of expired timestamp, snapshot, and targets metadata and rollback attempts. Root update follows TUF's sequential rules; expiry of the final trusted root blocks updates. A fresh timestamp cannot revive expired snapshot or targets metadata.
- Restoration of root and release key backups onto a clean spare Pi using off-site recovery materials and separately stored secrets; compare fingerprints and test signatures. Keep root recovery offline; enable the restored release signer's restricted network only after validation. Restore signing state too, including signed but unpublished reservations, and reject stale restored state and metadata version reuse.
- Release-key replacement and root rotation checking both thresholds. A disposable test repository demonstrates 1-of-1 to multi-party migration, including a returning client and rejection when either threshold is missing.
- Root-loss and root-compromise tabletop exercises ending in explicit rebootstrap without automatic trust bypass.

Repeat backup restoration and planned root rotation annually. Restore and verify every replacement signer before production use. Exercise freeze/resume and publisher recovery, replacing the timestamp key through a root update when the old key is unavailable or suspect. Test fixtures remain separate from production authority; never simulate compromise by exposing real keys.

<a id="boundaries"></a>

## 8. Boundaries

Users' machines have no project-held per-user keys or accounts. Third-party orchards maintain their own keys under [REPOSITORIES §5](../REPOSITORIES.md#signing-keys-two-schemes-one-verification-pipeline). Vendor Apple signatures and source-verification keys remain separate from repository signing. An optional hardware security-contact PGP key does not impose a token requirement on launch.

## History

<details>
<summary>Document revision history</summary>

| Date | Changes |
|---|---|
| September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| September 2026 | the manual offline-release design is superseded by owner-merge authorization, a dedicated networked release signer, automatic metadata renewal, and serialized atomic publication. The offline 1-of-1 root, encrypted backups, recovery drills, Ed25519/minisign formats, and future multi-party migration remain. Services and hardware drills are not yet implemented or validated. |
| September 2026 | corpus review corrections: artifact identity, protected execution, durable recovery, trust persistence, replay, platform limits, and examples aligned with STATE-AND-RECOVERY and SYSTEM-VOLUMES. These are specification changes; runtime acceptance remains pending. |
| September 2026 | prose rewrite of the introduction and signer-compromise explanation; no procedural changes. |
| September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |
| September 2026 | Relocate to `docs/runbooks/` and rebase relative links; no procedural changes. |

</details>
