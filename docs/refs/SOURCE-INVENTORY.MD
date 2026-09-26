# Source coverage and remaining evidence

Reviewed 2026-09-26 UTC. Every catalog record was compared with its primary source and the local sections linked from its identity block. Source content was recovered through direct HTTP or the web reader; Homebrew 6 required direct HTTP after the web reader failed, while Apple's forum required the web reader after an HTTP security challenge. Existing complete source assets matched fresh retrievals. No software interface or project technical decision changed.

## Catalog coverage

The database specification adds a 2026-09-26 UTC comparison of seven official
SQLite documentation pages, preserved in one technical account. This extends the
earlier review above; it does not revise its historical source comparisons.

Complete source means the named document's bytes are local, not that all its links or implementation dependencies are archived. Technical accounts preserve the supported decision context in original wording. Discussion accounts are selective, attributed reports; missing comments and dates are explicit. Each record supplies its canonical URL and exact local claim links.

| Record | Coverage | Omissions and unresolved evidence |
|---|---|---|
| [Apple Configuring System Integrity Protection](APPLE_CONFIGURING_SYSTEM_INTEGRITY_PROTECTION.MD) | Attributed account | The linked enterprise deployment procedure is not captured. SSV, authenticated-root, and per-build Recovery utility behavior are outside this 2015 chapter; see the separate SSV record. |
| [Apple default login shell](APPLE_DEFAULT_LOGIN_SHELL.MD) | Attributed account | Prompt customization, profile translation examples, and changing the interpreter for system shell scripts are omitted because SETUP does not authorize those migrations. |
| [Apple Dynamic Library Design Guidelines](APPLE_DYNAMIC_LIBRARY_DESIGN_GUIDELINES.MD) | Attributed account | The chapter's complete sample library and symbol-visibility tutorial are omitted. It does not provide a Mach-O ABI-diff implementation or verify the project's proposed analysis tools. |
| [Apple Signed System Volume Security](APPLE_SIGNED_SYSTEM_VOLUME_SECURITY.MD) | Attributed account | No per-build commands, successful restoration transcript, or patched-seal signing capability is supplied. This account retains the 2022 security model, not a claim that every later OS has identical controls. |
| [Apple Writable Root Volume Discussion](APPLE_WRITABLE_ROOT_VOLUME_DISCUSSION.MD) | Attributed account | This is a selective thread account, not all 38 replies. Exact reply dates/permalinks and collapsed comments remain gaps. Direct HTTP returned a security-verification page; the web reader supplied the visible thread text. External display tools and social-media instructions are not captured or endorsed. The earlier generic summary remains qualified by the failures recorded here. |
| [curl Mozilla CA Extraction](CURL_MOZILLA_CA_EXTRACTION.MD) | Attributed account | No current CA bundle or trust recommendation is frozen here. ETag support on the project's legacy curl versions and the local extraction scripts have not been validated. MPL-2.0 applies to the bundle, not automatically to this website. |
| [GitHub Intel Runner Retirement](GITHUB_INTEL_RUNNER_RETIREMENT.MD) | Attributed account | Runner-image software inventories and subsequent schedule changes are not captured. This record retains the dated announcement, not a live service-availability check. |
| [Homebrew 5 Release](HOMEBREW_5_RELEASE.MD) | Complete source + account | The source asset includes the complete post but not every linked pull request. The 4.6.0 and 5.1.0 posts cited collectively in the project review are still missing independent captures. |
| [Homebrew 6 Release](HOMEBREW_6_RELEASE.MD) | Complete source + account | The web reader failed for this URL, but direct HTTP and the source Markdown both succeeded. Full post text is retained; linked PRs, exact cooldown values, and runtime acceptance tests are not. |
| [Homebrew 7 Release and Intel Support](HOMEBREW_7_RELEASE_AND_INTEL_SUPPORT.MD) | Complete source + account | The full post is retained. Linked advisories, DSL manuals, implementation PRs, and benchmarks are not transitively archived; release-level statements cannot substitute for their detailed contracts. |
| [Homebrew Attestation Proposal 17019](HOMEBREW_ATTESTATION_PROPOSAL_17019.MD) | Attributed account | Comment chronology and individual comment permalinks are unavailable in the retrieved activity view. The opening issue URL is the locator; later discussion and backfill artifact inventories are not captured. |
| [Homebrew Historical Overview](HOMEBREW_HISTORICAL_OVERVIEW.MD) | Attributed account | No immutable Wikipedia oldid was recovered for the earlier account. The full version table and its cited references are not archived. The record does not resolve discrepancies by choosing the later date. |
| [Homebrew Intel CI Discussion 7044](HOMEBREW_INTEL_CI_DISCUSSION_7044.MD) | Attributed account | No complete CI logs, affected-formula inventory, or root-cause diagnosis is archived. Nested replies are summarized selectively; the complete conversation is not claimed. |
| [Homebrew Monterey Discussion 5603](HOMEBREW_MONTEREY_DISCUSSION_5603.MD) | Attributed account | The page reports 8 comments and 52 replies, with some previous replies collapsed. This capture covers the relevant visible exchange; it cannot establish complete discussion chronology or endorse third-party patchers. |
| [Homebrew Provenance Beta Implementation](HOMEBREW_PROVENANCE_BETA_IMPLEMENTATION.MD) | Attributed account | No beta verifier source, exact cutoff value, sample credential, complete in-toto statement, or backfill inventory is archived. Images and proposed future DSL are omitted. These gaps block reproducing the verifier, not understanding its stated policy. |
| [Homebrew Provenance Beta Sigstore](HOMEBREW_PROVENANCE_BETA_SIGSTORE.MD) | Attributed account | Screenshots, linked SLSA requirements, and supporting GitHub service documentation are omitted. No complete attestation bundle is preserved; the announcement alone cannot implement verification. |
| [Homebrew Security and Supply Chain](HOMEBREW_SECURITY_AND_SUPPLY_CHAIN.MD) | Complete source + account | The complete documentation text is retained, including its qualifications. Linked threat reports, Tap Trust command reference, implementation files, and independent security assessments are not all captured. |
| [Homebrew Support Tiers](HOMEBREW_SUPPORT_TIERS.MD) | Complete source + account | The entire policy file is retained, but linked environment requirements and historical policy revisions are not. A live branch snapshot is not evidence of policy on an earlier date. |
| [JSON Schema 2020 12 Core](JSON_SCHEMA_2020_12_CORE.MD) | Complete source + account | The complete fixed draft is retained without omissions. Referenced external standards and later errata are not automatically included. The header says June 10, 2022; the previous wrapper said published June 16. That discrepancy is recorded rather than altering the source. |
| [JSON Schema 2020 12 Validation](JSON_SCHEMA_2020_12_VALIDATION.MD) | Complete source + account | The complete draft, examples, and notices remain intact. No validator conformance suite or implementation guarantee is included. As with core, the source header is June 10, 2022, despite the earlier wrapper's June 16 publication metadata. |
| [libarchive tar format manual](LIBARCHIVE_TAR_FORMAT.MD) | Complete source + account | The complete v3.8.2 roff source and embedded redistribution notices are retained. This is not the source of the extractor implementation or evidence that legacy system tar behaves identically. |
| [libcxx Vendor Configuration](LIBCXX_VENDOR_CONFIGURATION.MD) | Attributed account | No pinned LLVM source checkout, full configuration recipe, SDK, compiler patches, or per-OS test logs are archived. Windows and alternative Linux ABI-provider instructions are outside the project decision. |
| [Mac Pro 2013 Compatible Operating System](MAC_PRO_2013_COMPATIBLE_OPERATING_SYSTEM.MD) | Attributed account | Other model entries, serial-number lookup assets, and photographs are omitted. The page supplies no CPU instruction-set inventory, hypervisor matrix, or successful aslice bootstrap. |
| [OWC Intel Mac Transition Report](OWC_INTEL_MAC_TRANSITION_REPORT.MD) | Attributed account | Buying advice, product promotions, images, and broader model lists are omitted. No primary Apple support-lifetime announcement is preserved here; do not infer a security end date. |
| [RFC 8785 JSON Canonicalization Scheme](RFC_8785_JSON_CANONICALIZATION_SCHEME.MD) | Complete source + account | The complete Informational RFC and notices are retained. Referenced ECMAScript/I-JSON editions and later errata are not independently archived; the RFC alone is not a parser implementation. |
| [Zstandard Compression and the application/zstd Media Type](RFC_8878_ZSTANDARD.MD) | Complete source + account | The complete RFC is preserved. Later errata and a specific decoder implementation are not included. The previous wrapper's tar-roff sentence was a copy error; roff applies to the separate libarchive asset, not this RFC. |
| [SQLite storage, compatibility, and recovery](SQLITE_STORAGE_AND_RECOVERY.MD) | Attributed technical account | Seven official documentation pages compared on 2026-09-26 UTC; complete HTML, pinned source/build artifacts, VFS details, and power-loss/security/recovery acceptance transcripts remain uncaptured. |
| [SmartCard HSM Algorithms](SMARTCARD_HSM_ALGORITHMS.MD) | Attributed account | Pricing, accessory offers, full datasheets, firmware/API manuals, and measured recovery behavior are not captured. The ambiguous URL/model relationship requires supplier confirmation rather than an assumption that older devices gained these features. |
| [The Update Framework Specification](THE_UPDATE_FRAMEWORK_SPECIFICATION.MD) | Complete source + account | The complete specification and Community Specification License remain intact. The retained master snapshot is identified by content hash, not a recovered commit ID. Linked TAPs/POUF documents, conformance tests, and cryptographic implementation assets are not all archived. |
| [TOML 1 0 Specification](TOML_1_0_SPECIFICATION.MD) | Complete source + account | The entire v1.0.0 specification and MIT license are retained. No later TOML version or parser conformance is implied; project semantic examples remain governed by their own sections. |
| [TOML Schema Specification](TOML_SCHEMA_SPECIFICATION.MD) | Complete source + account | The complete main-branch specification and MIT license are retained. Its exact commit ID was not recorded; the content digest fixes this edition. No conforming validator or execution transcript is supplied. |
| [X86 64 Microarchitecture Levels](X86_64_MICROARCHITECTURE_LEVELS.MD) | Attributed account | The full psABI document and its ELF calling/linking conventions are not archived. The retained account does not supply CPUID leaf/bit mappings, a complete XCR0 detector, or a verified mapping from every owned CPU to a level. |
| [YubiKey PIV Algorithms](YUBIKEY_PIV_ALGORITHMS.MD) | Attributed account | Other YubiKey applications, APDU/PKCS#11 integration, minisign encoding, and a key-recovery procedure are not captured. This is a PIV capability boundary, not a claim about every operation the device can perform. |

## Content questions for separate resolution

- DESIGN's September Intel-CI shorthand omits the discussion's reported August 28 shutdown. The release schedule and incident are both preserved; project text is unchanged.
- The historical version table associates Monterey deprecation with October 2024/version 4.4, while the discussion records warnings and CI reallocation in September under 4.3.21. These are different evidence dates, not one interchangeable event.
- Apple's 2015 SIP guide restricts programmatic startup selection; later forum users describe snapshot-aware bless operations. This archive does not resolve those accounts into a supported cross-version command contract.
- Current Homebrew security documentation describes opt-in verification and third-party attestation support. The 2024 beta remains historical evidence; neither account silently replaces the other.

## Example URLs and uncaptured supporting sources

Package URLs below are examples, not preserved release artifacts. Publishing a formula requires a pinned archive and its own evidence. URLs inside complete originals are not automatically catalog entries.

| Original URL | Used in | Disposition |
|---|---|---|
| https://ffmpeg.org | docs/AUTHORING.md, docs/DESIGN.md, docs/PACKAGE-FORMAT.md | Example package source/homepage; not used as implementation evidence |
| https://ffmpeg.org/documentation.html | docs/PACKAGE-FORMAT.md | Example package source/homepage; not used as implementation evidence |
| https://ffmpeg.org/download.html | docs/AUTHORING.md | Example package source/homepage; not used as implementation evidence |
| https://ffmpeg.org/releases/ffmpeg-7.1.0.tar.xz | docs/PACKAGE-FORMAT.md | Example package source/homepage; not used as implementation evidence |
| https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz | docs/AUTHORING.md, docs/DESIGN.md | Example package source/homepage; not used as implementation evidence |
| https://ghcr.io/aslice/core | docs/REPOSITORIES.md | Project transport example; not an upstream source or published-service claim |
| https://github.com/FFmpeg/FFmpeg/tags | docs/HOMEBREW-REVIEW.md, docs/PACKAGE-FORMAT.md | Example package source/homepage; not used as implementation evidence |
| https://www.openssl.org/source/old/1.1.1/openssl-1.1.1w.tar.gz | docs/PACKAGE-FORMAT.md | Example package source/homepage; not used as implementation evidence |
| https://zlib.net | docs/PACKAGE-FORMAT.md | Example package source/homepage; not used as implementation evidence |
| https://zlib.net/zlib-1.3.1.tar.gz | docs/PACKAGE-FORMAT.md | Example package source/homepage; not used as implementation evidence |

Additional implementation evidence still needed includes target-OS utility manuals and successful protected-volume boot/restore transcripts; a pinned compiler/bootstrap recipe; certificate trust-policy inventories; and real malformed/compressed archive fixtures. The archive records these gates without marking them passed.

## Retrieval and asset provenance

The five added Homebrew `.source.txt` files are unmodified UTF-8 Markdown from the source repositories, retained with `HOMEBREW_LICENSE.txt` (BSD-2-Clause, Homebrew contributors). Their records give retrieval URLs, dates, and content hashes. Branch names locate retrievals; they are not immutable revisions. The eight older complete assets, embedded copies, and older license files remain unchanged. New checksums cover expanded records and every asset.

Review changes add exact local claim links, source-section guides, attributed context, explicit omissions, and concise rights metadata. The JSON Schema wrapper date discrepancy and Zstandard wrapper's erroneous tar-roff sentence are recorded explicitly. No source text or historical original was silently corrected.

License asset: [HOMEBREW_LICENSE.txt](HOMEBREW_LICENSE.txt), retrieved 2026-09-26 UTC from https://api.github.com/repos/Homebrew/brew.sh/license. Transformation: base64-decoded the API content field without changing the decoded bytes. SHA-256: `f80329e58613ad669c0e73cb132d8060b9b2c55e339c73848068e4d1567f4627`. The Homebrew/brew license was also checked for the policy originals.

## Preservation audit

The prose review audit compares all 35 rewritten Markdown files with pre-edit working-file baselines. Added headings, section links, dates, examples, command names, numeric constraints, and qualified source rules are intentional content expansion. Generic Used by entries became exact claims; their section-number and section-sign changes follow those links. Catalog rows moved into the requested subjects, and inventory URL rows became record links whose targets retain the original URLs. Existing package-example rows remain.

Removed generic interpretation paragraphs are replaced by decision-specific explanations. The shell no-op, prior-value rollback, and required per-OS tests remain explicit, as do encoding and extractor-test obligations. Additional normative words express retrieved source conditions or already-existing project requirements; they do not establish new project policy. The complete embedded sources, earlier source assets, license notices, and their code examples remain unchanged. Template expansion deliberately strengthens archival requirements.
