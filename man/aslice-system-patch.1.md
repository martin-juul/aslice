% ASLICE-SYSTEM-PATCH(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-system-patch — inspect and reverse declared replacements of Apple-provided files

# SYNOPSIS

`aslice system-patch list`

`aslice system-patch status` [*path*]

`aslice system-patch restore` *path* [`--accept-system-changes`]

`aslice system-patch prepare` [`--accept-system-changes`]

`aslice system-patch finalize` [`--accept-system-changes`]

# DESCRIPTION

Declared `[system-patch]` packages replace narrowly allowed Apple-provided files with explicit consent and a mandatory reason. The helper preserves byte-exact originals and their metadata in protected storage, scoped by OS build and volume UUID. Executable replacements use a root-owned dependency closure; root execution never follows a user-writable profile.

The kernel, `dyld`, `libSystem`, `/System`, and platform load-path libraries remain refused targets. SIP-disabled does not imply that a volume is writable. Writable targets use journaled replacement; Catalina uses the Recovery backend; Big Sur and Monterey use the base-volume and boot-snapshot backend. SYSTEM-VOLUMES defines preparation, Recovery application, pending-reboot state, and finalization. Unsupported or untested OS adapters refuse application.

**list** shows managed patches. **status** reports hashes, OS/volume baseline, pending reboot, and external drift. **restore** plans the compatible backend's restoration; it may require Recovery and reboot. Missing backups, changed security state, and OS-baseline conflicts stop restoration with a remedy.

**prepare** validates the complete patch plan and persists protected recovery material before entering the OS-specific Recovery workflow. **finalize** verifies the booted volume/snapshot and resulting bytes before committing; it cannot mark a failed or unverified reboot successful. [SYSTEM-VOLUMES §2](../docs/SYSTEM-VOLUMES.md#enrollment-and-preflight) and [SYSTEM-VOLUMES §4](../docs/SYSTEM-VOLUMES.md#activation-rollback-and-os-updates) owns the workflow; platform adapters remain unimplemented.

# TRUST

Serving `[system-patch]` packages requires the repository `system-patch` capability ([REPOSITORIES §3](../docs/REPOSITORIES.md#trust-levels)): official and local repositories have it by default; a verified repository receives it only through the user's explicit per-repo grant (`aslice repo allow-system-patch <name>`, refused by default, revocable with `aslice repo deny-system-patch <name>`); third-party repositories never.

# OS UPDATES

An OS update establishes a new baseline. aslice reports drift and never reapplies a patch silently. Reinstallation requires fresh consent and a new baseline backup; restoration never places an older OS original over the newly installed OS file.

# LIMITS

Rollback is a journaled restoration plan. Protected-volume rollback can require Recovery and reboot, and service data is outside its scope. Uninstall is refused until managed patches are restored or a restoration is durably pending with its recovery tools retained. Originals and prior snapshots remain retained while referenced by an installed patch or unresolved operation.

# ARGUMENTS, CONSENT, AND EXAMPLES

*path* names the managed Apple-provided file to inspect or restore. Omitting it
from status requests the overall patch state. Prepare and finalize act on the
protected transition; additional plan/path selectors are not yet specified.
Every mutation requires explicit system-change consent. Unattended system changes
require **--accept-system-changes**; authentication, repository capability, and
validated platform-adapter requirements still apply. No command-specific dry-run
grammar is established here.

```sh
aslice system-patch list
aslice system-patch status
aslice system-patch status /usr/bin/rsync
aslice system-patch restore /usr/bin/rsync
aslice system-patch prepare
# Complete the prescribed Recovery and reboot workflow before finalizing:
aslice system-patch finalize
```

# EXIT STATUS

The common [aslice(1)](aslice.1.md#exit-status) statuses apply. Pending reboot or
unresolved recovery returns 1, not successful restoration; consent refusal returns 2.
Status reporting does not itself finalize a pending transition.

# FILES

**/Library/Application Support/aslice/system/**
:   Helper-owned dependency closures, receipts, and versioned backups. Before restoration, the helper verifies hashes, ownership, OS build, and volume identity.

# SEE ALSO

aslice(1), aslice-doctor(1), aslice-repo(1), [MANUAL §8.4](../docs/MANUAL.md#replacing-apples-fossilized-tools), [DESIGN §12.11](../docs/DESIGN.md#system-patches-flagged-reversible-replacement-of-apple-provided-files), [PACKAGE-FORMAT §3.16](../docs/PACKAGE-FORMAT.md#system-patch--flagged-replacement-of-apple-provided-files-v06)
