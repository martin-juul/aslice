# Security Policy

This document states how to report a vulnerability **in aslice itself** — the package manager, its helpers, the installer, the repository and signing infrastructure, and the farm tooling. Vulnerabilities in packaged software go elsewhere; see "Out of scope" below.

aslice is security infrastructure for machines that no longer receive security updates from anyone else; reports are taken accordingly seriously.

*Project terms, acronyms, and the Homebrew translation table: [docs/NOMENCLATURE.md](docs/NOMENCLATURE.md).*

## Reporting a vulnerability

**Email: martin@juul.xyz** — subject line prefix `[aslice security]`.

Please include:

- The aslice version (`aslice --version`) and macOS release you tested on.
- What you can make happen, and the steps to make it happen. A reproducer beats a write-up; a write-up beats a pointer.
- Which part of the trust model you believe is broken (signature verification, TUF metadata, the sandbox, the store, `aslice-system`, the installer, the farm/signing pipeline, …).
- Whether you consider the issue embargoed, and any disclosure timeline you are bound by.

Once the project cuts its first release, a PGP key for encrypted reports will be published here and cross-signed into the repository. Until then, if your report is too hot for plaintext email, say so in a short plaintext mail and we will agree a channel.

Do **not** file security reports as public GitHub issues.

## What to expect

This is a spare-time project, not a corporation, so these are commitments, not SLAs:

- **Acknowledgement within a few days.** If a week passes with no reply, resend — the mail was lost, not ignored.
- **A straight answer.** Either "confirmed, here is the fix plan and a rough timeline" or "we don't think this is exploitable, and here is why." You are welcome to argue; technical arguments win here, whoever makes them.
- **Coordinated disclosure.** We fix, ship a release, and publish what the issue was and who found it. We will not sit on a confirmed vulnerability to save face, and we ask you not to publish before users have a fix — the target machines cannot be patched by anyone else.
- **Credit** in the release notes and the commit message, under whatever name you choose, unless you ask to remain anonymous.

## Scope

In scope, roughly ordered by how much each class matters:

1. **Signature and metadata verification bypasses** — getting aslice to install or trust content that did not come from a pinned, verified source (TUF rollback/freeze/mix-and-match, minisign or OpenPGP verification, source-hash pinning, vendor signer pinning).
2. **Sandbox escapes** — package build code (Starlark phases) reaching the network, the live store, the user's profile, or anything outside its phase-scoped Seatbelt profile.
3. **`aslice-system` privilege escalation** — the elevated helper performing anything beyond the declared, consented actions, or being invoked into doing so.
4. **Store and generation integrity** — anything that silently mutates installed content or defeats rollback, including paths through `gc`, `clean`, or self-update.
5. **The installer and trust bootstrap** — the curl'd first step: hash pinning, the second-transport checksum cross-check, the `/opt/aslice` creation.
6. **The farm and signing pipeline** — job-manifest forgery, quarantine bypass, agent-to-signing-host trust boundaries, the transparency log.
7. **Denial of service against a user's machine** — e.g. a malicious repository or package wedging the resolver, the database, or disk watermarks.

### Rules of engagement

- Test against **your own machines and your own repositories only**. Do not attack other users, the project's infrastructure, mirrors, or the farm.
- Do not exfiltrate, modify, or destroy data that is not yours. Demonstrate with the minimum access necessary.
- Act within the law. If you follow these rules we will not pursue or support legal action against you for the research.

## Out of scope

- **Vulnerabilities in packaged software** (ffmpeg has a CVE, openssl has a CVE). Those flow through the orchard: file an issue on the orchard repository or, better, a bump/backport PR — the advisory feed and `aslice audit` already surface them to users (ORCHARD-POLICY §16). Report here only if aslice's *handling* of such a package is the problem (e.g. `audit` fails to flag it).
- **Vulnerabilities in macOS itself.** Apple does not patch these OS releases; that is the reason aslice exists. We document and route around what we can (see `aslice ca-update`, `[system-patch]`), but we cannot fix the kernel.
- **Attacks that already have root**, or physical access. The threat model starts below that line.
- **Social engineering of maintainers**, and reports about the content of third-party orchards — those are governed by their own trust level and are explicitly not vouched for by aslice.
- **Missing hardening suggestions without an exploit path** are welcome as ordinary issues, not security reports.

## Supported versions

Pre-1.0: **the latest release only**. Self-update is a first-class, rollback-complete path (DESIGN §12.12), so "are you current?" is always the first question and the answer is always cheap. After 1.0 this document will name a supported window; do not expect long support tails — the platform is frozen, the manager is not.

## If a key is compromised

That is our incident, not your report — but it is handled in the open, per the practiced runbook: **[docs/KEY-RUNBOOK.md](docs/KEY-RUNBOOK.md)**. The short version: root is 3-of-5 threshold with YubiKey custody, online keys are short-lived, and rotation is drilled, not hoped for.

---

*History: September 2026 — editorial pass: prose revised for directness; no policy changes. September 2026 — prose rewrite throughout: the policy reworded in the project's technical-writing voice; no policy changes. September 2026 — NOMENCLATURE.md vocabulary pointer added; no policy changes.*
