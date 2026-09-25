# Signing, Recovery, and Key Rotation Runbook

This runbook governs every cryptographic key aslice trusts; DESIGN §10.2 calls for it by name. Its purpose is one sentence: the worst day of the project should be a procedure, not an improvisation.

**Status: design, September 2026.** The initial release uses one accountable operator, two existing Raspberry Pis, and encrypted software keys. Hardware validation and the drills below remain launch requirements, not completed work. Independent custodians and hardware tokens are future options, not launch prerequisites.

*Project terms, acronyms, and the Homebrew translation table: [NOMENCLATURE.md](NOMENCLATURE.md).*

Four rules govern everything below:

- **Root and release keys stay offline.** Generate them on their dedicated Pis; encrypt private material at rest and in offline backups. Never copy it to the farm or publisher. Store recovery secrets separately from backup media.
- **Every key event produces a record.** Record operator, device identities, public fingerprints, metadata versions and hashes, time, and backup locations in the private recovery archive. Publish a signed summary without private keys, recovery secrets, or sensitive storage details.
- **Trust is explicit.** Initial users trust the project owner. Multiple owner-controlled devices provide separation and recovery, not independent-party oversight. Software keys are extractable if a Pi or its unlocked storage is compromised; backups are additional key copies requiring protection.
- **Drills are real.** Complete §7 before launch and retain receipts. Written procedures are not evidence that recovery works.

## 1. Key inventory and machines

The **root Pi** holds only root signing authority. The **signing host** is a separate offline **release Pi**, holding distinct targets, snapshot, and slice-signing keys. Neither runs package builds. Disable wired and wireless networking, verify no active network connections or routes, and keep both disconnected during use. Check the clock against a trusted time reference before signing metadata.

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

Separate release keys on one Pi are not independent compromise barriers. A transparency log supports detection and audit; it cannot prevent an authorized malicious signature or guarantee detection.

### 1.1 Metadata validity and renewal

| Role | Validity from signing | Renewal |
|---|---|---|
| Root | One year | Offline root session before expiry |
| Targets | 90 days | Each release, or an offline renewal session |
| Snapshot | 90 days | Each release or offline renewal, binding targets versions, lengths, and hashes |
| Timestamp | 48 hours | Daily online refresh, binding only the approved snapshot version, length, and hash |

Alert the operator 30 days before root, targets, or snapshot expiry; keep alerts active until renewed. Monitor daily timestamp refresh failures. Renewals increment metadata versions and do not change keys. Timestamp refresh never renews targets or snapshot metadata; refuse refresh against expired targets or snapshot metadata. Clients reject expired metadata and rollback attempts according to TUF, including its sequential root-update rules. Installed software keeps running, but repository updates can become unavailable.

Key rotation is different: replacing any top-level TUF role key requires a root update, including timestamp-key replacement. Daily timestamp signing needs no root session.

## 2. Initial root setup

One operator can perform this procedure; no witness or additional custodian is required.

1. Prepare clean root and release Pis with verified OS and signing tools. Archive installation media, tool versions, hashes, and setup instructions. Validate the chosen Pi architecture and tools before relying on them; Linux signing tools do not add Linux package builds to the orchard.
2. Generate the root key on the root Pi and three distinct release keys on the release Pi. Generate the timestamp key on the publisher; take only its public key to the root Pi. Compare exported fingerprints against each generating device's output.
3. Create version 1 root metadata with threshold 1 for each top-level role and the role keys above. Sign on the root Pi with expiry per §1.1. Archive signed root metadata and public keys.
4. Make encrypted offline backups of root and release keys, signing state, and recovery instructions. Keep a backup in a separate physical location from the active devices. Keep recovery secrets separately, recoverable after loss of the primary site. Never include private material in a public archive or release bundle.
5. Restore onto a clean spare Pi and verify fingerprints and test signatures before launch (§7). Remove temporary restored private material after the drill; any retained backup device is inventoried as another key copy.
6. Publish root metadata and fingerprints through the repository and second transport; pin the root hash in the installer. Compare bytes across placements. Sign and archive the setup report; the transparency log's genesis entry references its hash when the log is brought up.

### 2.1 Offline release batches

The existing `aslice repo build / sign / publish` stages exchange a portable release bundle. This is an authoring workflow specification; client signature formats remain unchanged.

1. **Prepare online (`repo build`).** After merge and all required gates, collect artifact bytes, index and target metadata (including verified graft manifests), existing signatures for retained slices, source blobs, orchard commit, and gate receipts bound to artifact digests. Include the trusted root chain, prior metadata, proposed versions and expiries, and an inventory of paths, lengths, and hashes. Bind the bundle to the currently published snapshot so stale parallel releases cannot overwrite newer work. The first batch declares an empty repository base and uses the root established in §2.
2. **Transfer.** Copy the bundle on removable media. Mount input without execution or automatic opening. Treat paths, archives, metadata, and receipts as untrusted; reject path traversal, unexpected files, and inconsistent inventories. Never run bundle-provided scripts or builds on a signer.
3. **Review and sign offline (`repo sign`).** Compare against the release Pi's retained trusted root and last approved metadata state; imported keys cannot establish trust. Verify hashes, existing signatures, gate evidence, versions, and expiry. Display the release inventory and changes for operator approval. Receipt consistency cannot prove that a compromised farm built safe software. Sign new slices, then targets, then the snapshot binding those targets. Retain the approved bundle hash and signed metadata state to prevent version reuse after interruption or restore. Archive this public signing state off-device after each session, including signed but unpublished batches; do not infer the latest signed version solely from the live repository. If the latest state cannot be established after recovery, stop and investigate before signing.
4. **Return and verify.** Transfer the signed bundle to the publisher. Re-verify signatures, hashes, versions, expiry, gates, and expected previous snapshot. Reject changed bytes or a stale base. An interrupted or failed session never authorizes partial publication.
5. **Publish (`repo publish`).** Stage the complete approved set, including dependent rebuilds and source blobs, before atomically activating it with a timestamp referencing its signed snapshot. Keep the prior published set active on failure. Retry identical signed batches only against their expected base, or report success if that exact batch is already active; conflicting work requires a new approved batch. Append the public snapshot receipt to the transparency log when deployed and update the dashboard.

Routine batches never require the root Pi. Renewal with unchanged artifacts follows the same offline metadata checks. Manual handling waives no build, review, quarantine, or independent-rebuild gate. Sign the final bootstrap binary and published checksums on the release Pi too. Apple signing/notarization is separate and must precede the final minisign signature if it changes the bytes.

## 3. Routine key rotation

Generate successors on the machine that will hold them. For targets, snapshot, or timestamp replacement, take the successor public key to the root Pi and update its role using §3.1. Stage compatible metadata signed by the successor before activating the new timestamp. Keep intermediate roots available indefinitely.

For slice-key replacement, publish the successor public key in the TUF-authenticated trusted-key set before using it for slices. Planned rotation may retain the old key for previously authorized immutable digests; compromise requires audit and revocation under §4, not unrestricted historical acceptance. Coordinator and agent identity changes retain their enrollment/pinning procedures.

### 3.1 Planned root update or rotation

1. On the root Pi, construct root version N+1 with the intended role keys, thresholds, and expiry. For root-key rotation, generate and back up the successor offline first.
2. Sign N+1 to satisfy **both its predecessor's root threshold and its own root threshold**. With unchanged root keys, a signature may satisfy both. Verify both requirements before publication.
3. Publish sequential versioned roots without gaps. Verify an existing client follows the chain and accepts the compatible release metadata. Preserve intermediate roots for returning clients.
4. Update repository and second-transport placements, installer/bootstrap pins for new installations, and the recovery archive. Announce the change; existing clients follow authenticated rotation without manual re-pinning.
5. After verifying the transition and successor backup restoration, retire superseded private copies, including backups. Retain public metadata and audit records.

## 4. Compromise response

Lost devices or backup material, unexplained signatures, and compromised farm or publisher hosts trigger this procedure.

1. **Stop publication and timestamp refresh.** Isolate affected infrastructure and preserve evidence. This is an operational stop, not instant client revocation: clients learn new authority through signed metadata, and an attacker may still serve valid metadata or possess a stolen key. Expiry blocks updates; do not promise unaffected freshness or universal safety.
2. **Publish an advisory within 24 hours.** State what is known, the affected window, and concrete user action. Use independent communication paths if hosting is suspect.
3. **Recover authority.** With a trusted root, rebuild affected infrastructure, replace keys, and publish a root update revoking affected top-level keys. Revoke affected slice authorization through trusted targets metadata. Suspect root authority follows §4.1 instead.
4. **Audit the window.** Inspect published roots, targets, snapshots, slices, and gate evidence since last-known-good. Compare archived receipts and the transparency log where available; rebuild where required. Signature validity cannot clear content signed during compromise.
5. **Resume deliberately.** Publish audited metadata and content with appropriate newer versions, verify with existing and fresh clients, and publish findings and a postmortem. Never bypass client rollback or expiry protection to resume service.

### 4.1 Root loss or compromise

- **Device failure with a trustworthy backup:** restore offline, verify an independently retained public fingerprint and latest trusted signing state, and rehearse a signature. Possible disclosure requires the compromise path.
- **No usable root key or backup:** use §6. There is no in-band chain without old signing authority.
- **Suspected compromise of the initial 1-of-1 root:** an attacker can authorize replacement roots too. An old-key signature cannot establish legitimate recovery. Use §6 with independently authenticated new pins and an advisory; ordinary rotation alone is insufficient.

## 5. Future independent custody and hardware

Introduce multi-party custody when independent maintainers actually participate. Each generates a distinct root key under their own custody; TUF requires multiple independent signatures, not shares of one split key. A possible future policy is 3-of-5, but neither five people nor five tokens are launch requirements.

Migrate through §3.1: the first multi-party root must satisfy both the current 1-of-1 authority and its new threshold. Rehearse with a client pinned to the launch root and preserve intermediate roots. Later custodian changes require the then-current and successor thresholds; lost quorum requires §6. Record custody and recovery procedures at that transition.

Hardware is optional. Evaluate exact model, firmware, application, middleware, Pi support, algorithm, signature format, cost, and backup/recovery behavior with actual sign/verify and recovery trials before adoption:

- [SmartCard-HSM USB token](https://www.cardlogix.com/product/smartcard-hsm-4k-usb-token/): listed RSA/ECDSA algorithms do not establish Ed25519/minisign compatibility. Backup and threshold-authentication features do not themselves implement TUF's multi-signature threshold. Obtain a quote and confirm the supplied version.
- Existing YubiKey 4 devices: inventory first. [Yubico's PIV documentation](https://developers.yubico.com/PIV/Introduction/YubiKey_and_PIV.html) places PIV Ed25519 support at firmware 5.7+, so these older devices cannot implement the current design through PIV. Other applications require their own compatibility proof.

Keep Ed25519 and minisign for launch. Changing algorithms requires a separate client-compatibility decision. Root-transition requirements follow the [TUF specification](https://github.com/theupdateframework/specification/blob/master/tuf-spec.md).

## 6. Disaster recovery: trust rebootstrap

1. Stop publication and issue the §4 advisory. State whether root authority was lost or compromised.
2. Repeat §2 on clean devices with new keys. Establish new public pins through independently authenticated communication; two copies on compromised hosting are not independent authentication.
3. Existing users explicitly rebootstrap using the new installer or a documented repair flow showing verified fingerprints. No silent root replacement is permitted. A compromised old root's signature alone is not proof of the new one.
4. Audit retained artifacts, re-sign as required, and publish under the new root. Preserve old public history and describe content continuity without implying trust continuity.
5. Publish a postmortem and amend the procedure from observed failures.

## 7. Drills and acceptance

Before launch, record successful runs of:

- An offline release round trip and client verification, including bootstrap/checksum signing and installation on the supported 10.11 test VM.
- Rejection of modified artifacts, missing or invalid required receipts, mismatched metadata hashes, stale release bases, and unsafe paths; no supplied script executes. Interruptions/retries never expose partial releases.
- Client rejection of expired timestamp, snapshot, and targets metadata and rollback attempts. Root update follows TUF's sequential rules; expiry of the final trusted root blocks updates. A fresh timestamp cannot revive expired snapshot or targets metadata.
- Restoration of both offline key sets onto a clean spare Pi using off-site recovery materials and separately stored secrets; compare fingerprints and test signatures. Restore signing state too, and reject metadata version reuse.
- Release-key replacement and root rotation checking both thresholds. A disposable test repository demonstrates 1-of-1 to multi-party migration, including a returning client and rejection when either threshold is missing.
- Root-loss and root-compromise tabletop exercises ending in explicit rebootstrap without automatic trust bypass.

Repeat backup restoration and planned root rotation annually. Restore and verify every replacement signer before production use. Exercise freeze/resume and publisher recovery, replacing the timestamp key through a root update when the old key is unavailable or suspect. Test fixtures remain separate from production authority; never simulate compromise by exposing real keys.

## 8. Boundaries

Users' machines have no project-held per-user keys or accounts. Third-party orchards maintain their own keys under REPOSITORIES §5. Vendor Apple signatures and source-verification keys remain separate from repository signing. An optional hardware security-contact PGP key does not impose a token requirement on launch.

*History: September 2026 — replaces the mandatory five-custodian YubiKey ceremony and shared-host release signing with owner-operated offline Pis, encrypted backups, manual release batches, explicit expiry behavior, and a future multi-party migration path. Earlier procedures are superseded; implementation and hardware drills remain pending.*
