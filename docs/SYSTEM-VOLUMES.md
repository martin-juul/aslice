# Protected system-volume patches

- **Status:** Specification v0.2 — September 2026. Support is designed for Intel macOS 10.11–12; each OS build/filesystem/security configuration remains blocked from release until the acceptance matrix passes.
- **Authority:** This document owns the protected-volume backend for DESIGN §12.11. [State and recovery](STATE-AND-RECOVERY.md) owns authorization, protected storage, and the operation journal.

## 1. Three backends

| Target | Backend | Activation and undo |
|---|---|---|
| Writable Data-volume paths on supported releases; permitted system paths on 10.11–10.14 after required SIP changes | Journaled file replacement, protected originals, protected execution closure | Helper transaction; processes may need restart |
| Catalina 10.15 read-only System volume | Recovery-assisted mount and offline journaled replacement on the identified System volume | Explicit reboot into the patched installation; restore from its recorded originals in Recovery |
| Big Sur 11 and Monterey 12 signed System volume | Stage the complete patch set in the writable underlying System volume, create and select a new boot snapshot | Pending until reboot and verification; undo by selecting a compatible retained snapshot or preparing a restoration snapshot |

SIP and signed-system-volume protection are separate preconditions. [Apple documents the read-only volume introduced in 10.15 and the SSV introduced in 11](refs/APPLE_SIGNED_SYSTEM_VOLUME_SECURITY.MD). A SIP check alone never authorizes mounting or patching either volume. Only declared tools, configurations, and data are eligible: the kernel, dyld, libSystem, `/System`, platform-binary libraries, boot-critical consumers, and paths needed before the protected Data-volume closure is available remain refused. Alias and symlink resolution cannot bypass those refusals.

## 2. Enrollment and preflight

`aslice system-patch prepare` builds a patch plan from installed, authenticated declarations. For protected volumes it records the exact OS build, hardware/T2 class, filesystem and APFS volume-group UUIDs, System/Data roles, current boot snapshot UUID, security settings, FileVault state, free-space requirement, and the complete desired patch set. Never infer a device by stripping a suffix from `/dev/disk...`, or identify it only by its display name.

Before changes, verify a working Recovery environment and a separately stored recovery kit containing the verified helper, plan, original inventory, snapshot identifiers, and restoration instructions. The kit contains no private signing key. Bind authorization to its plan digest and the measured OS/volume identities. Test restore before enabling that configuration for public use. Keep a verified whole-system backup as well as per-file originals; APFS snapshots on the same disk are not protection against disk loss.

The user makes security-setting changes in Recovery; aslice prints their exact effect and never toggles them itself. On 10.11–10.15 this includes SIP state where required. On 11–12 it additionally includes authenticated-root state and any model-specific Startup Security restrictions. FileVault/security combinations disallowed by the OS are refused with a remedy and a fresh preflight; the manager never decrypts a disk or changes startup security automatically. [Apple's SIP configuration procedure](refs/APPLE_CONFIGURING_SYSTEM_INTEGRITY_PROTECTION.MD) explains the Recovery requirement.

## 3. Recovery-assisted application

The recovery kit's helper offers `aslice-system volume-apply <plan>` only in the matching Recovery environment, with mounted-volume identity and authorization checked again. It mounts the identified System and Data volumes at private mountpoints, confirms that the System volume is writable and that no OS updater or competing transaction owns it, and retains the existing boot selection. Mount commands and options come from an OS-build-specific tested adapter using the target's own utilities; unsupported utility behavior fails before writes.

For Catalina, persist exact originals and metadata before each replacement, apply the full plan, rehash every output, flush, and unmount. An interruption leaves a Recovery-resumable journal; partial changes are restored before the installation is booted. For Big Sur/Monterey, preserve the prior bootable snapshot, modify only the writable base volume, and create a new boot snapshot only after the staged tree passes verification. Select the new snapshot with the OS's snapshot-aware bless operation, recording both UUIDs durably. Snapshot creation or selection failure leaves the prior boot selection intact or restores it before exit. Never write through the mounted live snapshot or promise to recreate Apple's seal.

The adapter must verify the exact supported `bless` snapshot-selection and creation interfaces on the target release. Apple's [developer discussion of writable root volumes](refs/APPLE_WRITABLE_ROOT_VOLUME_DISCUSSION.MD) provides background; it is not a substitute for recorded per-release command fixtures and a boot/restore drill. Hardcoded universal command strings are not a supported adapter.

Replacement executables and their dependencies come from the protected closure defined in STATE-AND-RECOVERY §3. Where a permitted symlink crosses to Data, preflight proves that the consumer starts only after that closure is mounted. Otherwise refuse the target. The complete closure stays pinned until all snapshots referencing it are retired. The original inventory preserves ownership, modes, ACLs, xattrs, flags, and file kind as well as bytes.

## 4. Activation, rollback, and OS updates

The result before reboot is `pending-reboot`, not success or a committed package generation. `aslice system-patch status` reports the selected snapshot and pending transaction. On the next boot, `aslice system-patch finalize` verifies the actual boot snapshot, OS build, patch tree, closure, and required service tests, then commits the journal. Until finalization, affected package mutations and GC are blocked. An unsuccessful boot is recovered from the kit in Recovery, without depending on the patched manager or shell.

`aslice rollback` of a generation spanning protected-volume changes creates a restoration plan and reports `pending-reboot`; it does not silently claim an instant whole-machine rollback. `aslice-system volume-restore <plan>` in Recovery checks the recorded volume identities and selects the retained compatible prior snapshot on 11–12, or restores the recorded Catalina before-images. If other managed patches must remain, prepare a new snapshot of the entire desired set instead of undoing them accidentally. Service data is outside this snapshot contract.

Restoring a sealed snapshot and re-enabling authenticated root are separate user-authorized steps, verified after the restored system boots. Never enable verification while an unsigned patched snapshot remains selected. Snapshot deletion is forbidden while referenced by recovery state. If the snapshot or original inventory is missing or damaged, stop with the recovery-kit and system-backup procedure; do not improvise a partial restore.

An Apple OS update changes the baseline. Compare the OS build, volume/snapshot identities, and original fingerprints before every action. Retain originals per OS baseline; never copy an old OS's tool over a newer one. A changed baseline invalidates outstanding plans and requires a fresh authenticated package plan, fresh originals, and renewed consent. Old journals remain auditable. Decommission cannot delete the prefix, protected closure, or recovery kit while a snapshot still references them or a reboot is pending.

## 5. Acceptance matrix

Record one successful patch, reboot, finalize, rollback, and restore drill for each claimed OS build, filesystem, and security/hardware configuration, including supported T2 configurations. Also exercise: wrong volume selection, locked Data volume, insufficient space, failed remount, failed snapshot creation/selection, interruption at each journal boundary, failed boot, missing previous snapshot, and an intervening Apple OS update. Verify refusal of early-boot consumers and forbidden paths, and demonstrate decommission after restoring a protected-volume patch.

Until an adapter passes these gates, the client reports that exact configuration as unsupported before mutation. The gates define the runtime evidence needed to support the configuration; this specification does not establish that the procedure has passed them.

*History: v0.2 (September 2026) — prose rewrite of the adapter acceptance explanation; no content changes.*
