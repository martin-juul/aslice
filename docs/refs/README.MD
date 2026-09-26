# Source archive

This directory preserves the sources used to make implementation decisions. A printed or offline copy must include the records, their linked source/license assets, and SHA256SUMS. Start new records from [TEMPLATE.MD](TEMPLATE.MD). Original URLs remain provenance; specification citations point here.

Capture all material relevant to a relied-upon claim, including limits and recovery conditions. Archive full originals when redistribution permits; otherwise preserve the relevant technical facts in a clearly labeled account. Never present a paraphrase, unverified command, or forum report as a complete authoritative original. Exact per-OS utility manuals and successful runtime transcripts belong here when adapters are implemented; until captured, those adapters remain unvalidated.

Use UTF-8 plain text, meaningful filenames, local links, explicit dates, and versioned records. Keep multiple independent copies, print the catalog and checksums, and periodically verify and migrate storage media. No file format or medium alone guarantees a century of preservation. Hashes detect byte changes; they do not establish authorship or durability. Printouts must include the captured text, not just an asset URL.

## Catalog

Each source has one primary entry. Related records link across subjects; original filenames remain stable. Descriptions identify evidence, not successful implementation tests.

### Apple platforms and system behavior

- [Apple Configuring System Integrity Protection](APPLE_CONFIGURING_SYSTEM_INTEGRITY_PROTECTION.MD) — NVRAM scope, Recovery changes, and limits of the 2015 SIP guide.
- [Apple default login shell](APPLE_DEFAULT_LOGIN_SHELL.MD) — OS defaults, account state, and separate Terminal settings.
- [Apple Signed System Volume Security](APPLE_SIGNED_SYSTEM_VOLUME_SECURITY.MD) — Hash-tree integrity, boot snapshots, T2 boundaries, and FileVault prerequisites.
- [Apple Writable Root Volume Discussion](APPLE_WRITABLE_ROOT_VOLUME_DISCUSSION.MD) — Big Sur failures, snapshot reports, and the writable-data alternative.

### Hardware compatibility and CPU architecture

- [Mac Pro 2013 Compatible Operating System](MAC_PRO_2013_COMPATIBLE_OPERATING_SYSTEM.MD) — Model identification and the supported Monterey ceiling for MacPro6,1.
- [OWC Intel Mac Transition Report](OWC_INTEL_MAC_TRANSITION_REPORT.MD) — Dated secondary report on macOS 27 and affected Intel owners.
- [X86 64 Microarchitecture Levels](X86_64_MICROARCHITECTURE_LEVELS.MD) — Cumulative CPU features and OS register-state requirements.

### Homebrew releases, support, and history

- [Homebrew 5 Release](HOMEBREW_5_RELEASE.MD) — Download concurrency, API opt-in, and the announced Intel schedule.
- [Homebrew 6 Release](HOMEBREW_6_RELEASE.MD) — Tap trust, API defaults, sandbox scope, cooldowns, and install steps.
- [Homebrew 7 Release and Intel Support](HOMEBREW_7_RELEASE_AND_INTEL_SUPPORT.MD) — Intel Tier 3, execution cutoff, services, GUI, and installation safeguards.
- [Homebrew Historical Overview](HOMEBREW_HISTORICAL_OVERVIEW.MD) — Secondary release chronology and the Monterey date discrepancy.
- [Homebrew Monterey Discussion 5603](HOMEBREW_MONTEREY_DISCUSSION_5603.MD) — September 2024 CI reallocation and later support/communication debate.
- [Homebrew Support Tiers](HOMEBREW_SUPPORT_TIERS.MD) — Configuration-dependent support, bottles, and scheduled removal.

### Build infrastructure and runner availability

- [GitHub Intel Runner Retirement](GITHUB_INTEL_RUNNER_RETIREMENT.MD) — Hosted labels, brownouts, migration, and Intel retirement schedule.
- [Homebrew Intel CI Discussion 7044](HOMEBREW_INTEL_CI_DISCUSSION_7044.MD) — Reported CI slowdown and August 2026 bottle cessation ahead of schedule.

### Signing, trust, and supply-chain security

- [curl Mozilla CA Extraction](CURL_MOZILLA_CA_EXTRACTION.MD) — PEM conversion, omitted browser constraints, and trust limits.
- [Homebrew Attestation Proposal 17019](HOMEBREW_ATTESTATION_PROPOSAL_17019.MD) — Historical proposal, flag spelling, and unresolved bootstrap questions.
- [Homebrew Provenance Beta Implementation](HOMEBREW_PROVENANCE_BETA_IMPLEMENTATION.MD) — Verification identities, backfill alternatives, credentials, and beta limits.
- [Homebrew Provenance Beta Sigstore](HOMEBREW_PROVENANCE_BETA_SIGSTORE.MD) — Public rollout and the generation/verification distinction.
- [Homebrew Security and Supply Chain](HOMEBREW_SECURITY_AND_SUPPLY_CHAIN.MD) — Signed metadata, provenance, shared infrastructure, and execution boundaries.
- [SmartCard HSM Algorithms](SMARTCARD_HSM_ALGORITHMS.MD) — Token capabilities versus minisign and TUF compatibility requirements.
- [The Update Framework Specification](THE_UPDATE_FRAMEWORK_SPECIFICATION.MD) — Complete roles, metadata, root updates, freshness, and client workflow.
- [YubiKey PIV Algorithms](YUBIKEY_PIV_ALGORITHMS.MD) — Firmware-specific PIV capabilities and older-device limits.

### Formats, schemas, and serialization

- [JSON Schema 2020 12 Core](JSON_SCHEMA_2020_12_CORE.MD) — Complete fixed draft: dialects, resources, references, applicators, and closure.
- [JSON Schema 2020 12 Validation](JSON_SCHEMA_2020_12_VALIDATION.MD) — Complete fixed draft: assertions, presence, formats, and annotations.
- [libarchive tar format manual](LIBARCHIVE_TAR_FORMAT.MD) — Complete tar(5): records, pax overrides, checksums, and extensions.
- [RFC 8785 JSON Canonicalization Scheme](RFC_8785_JSON_CANONICALIZATION_SCHEME.MD) — Complete JCS algorithm, Unicode/numeric rules, sorting, and vectors.
- [SQLite storage, compatibility, and recovery](SQLITE_STORAGE_AND_RECOVERY.MD) — Official WAL fixes, synchronization, backup, salvage, schema compatibility, query controls, contention, optimization, and compaction.
- [TOML 1 0 Specification](TOML_1_0_SPECIFICATION.MD) — Complete language syntax, distinct from project semantics.
- [TOML Schema Specification](TOML_SCHEMA_SPECIFICATION.MD) — Complete schema language, effective constraints, closure, and evaluation.
- [Zstandard Compression and the application/zstd Media Type](RFC_8878_ZSTANDARD.MD) — Complete compression format, frames, dictionaries, and resource considerations.

### Libraries, ABI, and toolchain behavior

- [Apple Dynamic Library Design Guidelines](APPLE_DYNAMIC_LIBRARY_DESIGN_GUIDELINES.MD) — Loader versions, interface evolution, and the dlopen exception.
- [libcxx Vendor Configuration](LIBCXX_VENDOR_CONFIGURATION.MD) — Runtime builds, matching ABI settings, visibility, and private installation.

## Coverage

The catalog contains 33 records. Thirteen have complete source assets: eight retained standards/manuals and five Homebrew release/policy originals added in the 2026-09-26 review. The other twenty are attributed technical or discussion accounts, including the SQLite documentation account added for DATABASE. Complete assets retain their notices; [the inventory](SOURCE-INVENTORY.MD) names uncaptured dependencies and unresolved evidence.

The review recovered content from every primary source using direct HTTP or the web reader. Direct HTTP recovered Homebrew 6 after the web reader failed; Apple's forum returned an HTTP security challenge, so its account uses the web reader's visible thread. All eight existing complete assets matched fresh downloads byte for byte. Live branch/page accounts without immutable revision IDs remain dated snapshots, not evidence of earlier content. Discussion pages with collapsed comments remain partial even when their opening page loads successfully.

Read each record's claim links, source locators, context, interpretation, and omissions together. A link inside a complete source remains external unless separately captured. Full specification text does not imply that its dependencies, implementation, or runtime acceptance evidence is present. Historical comparison and package-download examples are tracked in the inventory.

## Maintenance and verification

Use [TEMPLATE.MD](TEMPLATE.MD) for new records and substantive revisions. Preserve older relied-upon editions when upstream changes. The archive grants no blanket copying exemption for technical documents. Retain per-source permissions and notices, including [Homebrew's BSD-2-Clause notice](HOMEBREW_LICENSE.txt) for the added originals.

Sources marked incomplete cannot establish a validated implementation. New external implementation dependencies must add a record, applicable license, exact revision, and offline content in the same change.

Regenerate `SHA256SUMS` over every file in this directory except itself, sorted by filename. Run `python tests/check_contracts.py` and `git diff --check`. The contract check verifies asset coverage and bytes, not attribution, source accuracy, validator conformance, or runtime safety; those require the record-level review described in the template.
