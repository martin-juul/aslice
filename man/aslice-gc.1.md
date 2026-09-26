% ASLICE-GC(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-gc, aslice-clean, aslice-store — reclaim disk and verify the store

# SYNOPSIS

`aslice gc` [**--dry-run**] [**--older-than** *30d*]

`aslice clean` [**--dry-run**]

`aslice store verify` [**--quarantine** *package*]

# DESCRIPTION

Installed package trees occupy the store; downloaded and intermediate files occupy the cache. Each has its own cleanup command.

**gc** owns the *store* — the immutable package trees your generations reference, which is what makes rollback possible. It removes store paths unreachable from any retained generation (the last 5 are kept by default). A store path referenced by a running process's generation is never collected.

**clean** owns the *cache* — downloaded slices, source tarballs, index snapshots, compiler cache: pure redundancy. It evicts least-recently-used entries when the cache exceeds its watermark (10 GB by default), never touching anything younger than 30 days.

Both print what would go, and why, with **--dry-run**; the watermarks are configurable in `etc/aslice.toml`.

**store verify** re-hashes store paths against their manifests — the immutability tripwire. A mismatch means corruption or tampering and is treated as a security event. With **--quarantine**, the offending path is pulled from all future generations (dependents are reported); reinstall restores a verified copy.

Keep the last 5 generations by default. `gc.store_watermark` is the store limit (default 20 GB); `gc.warning_margin_percent` is the warning margin below it (default 10, range 0–100). Warn when usage reaches `limit × (1 - margin / 100)`. At or above the limit, ask `Run garbage collection? [y/N]`; No is the default. Never run GC automatically from the size check. Non-interactive checks print the warning and the `aslice gc` remedy without collecting. Explicit `aslice gc` remains available. Collection retains every root required by [STATE-AND-RECOVERY §2](../docs/STATE-AND-RECOVERY.md#abi-and-execution-requirements) and [STATE-AND-RECOVERY §5](../docs/STATE-AND-RECOVERY.md#durable-transactions-and-recovery); a threshold does not make reachable artifacts collectible.

# SEE ALSO

aslice(1), aslice-doctor(1), [MANUAL §3.5](../docs/MANUAL.md#reclaiming-disk-clean-and-gc) and [MANUAL §5.3](../docs/MANUAL.md#housekeeping)
