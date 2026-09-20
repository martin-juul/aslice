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

Two spaces fill up; two commands empty them.

**gc** owns the *store* — the immutable package trees your generations reference, which is what makes rollback possible. It removes store paths unreachable from any retained generation (the last 5 are kept by default). A store path referenced by a running process's generation is never collected.

**clean** owns the *cache* — downloaded slices, source tarballs, index snapshots, compiler cache: pure redundancy. It evicts least-recently-used entries when the cache exceeds its watermark (10 GB by default), never touching anything younger than 30 days.

Both print exactly what would go, and why, with **--dry-run**; the watermarks are configurable in `etc/aslice.toml`.

**store verify** re-hashes store paths against their manifests — the immutability tripwire. A mismatch means corruption or tampering and is treated as a security event. With **--quarantine**, the offending path is pulled from all future generations (dependents are reported); reinstall restores a verified copy.

# SEE ALSO

aslice(1), aslice-doctor(1), MANUAL.md §3.5, §5.3
