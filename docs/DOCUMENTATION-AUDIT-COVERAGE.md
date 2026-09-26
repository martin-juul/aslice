# Documentation audit coverage — 26 September 2026

Remediation: see [DOCUMENTATION-REMEDIATION](DOCUMENTATION-REMEDIATION.md) for the applied decisions, fixes, and validation. This report retains the original review findings as historical evidence.
Companion to the [findings and proposal](DOCUMENTATION-AUDIT.md). Baseline: `a020aa6879896d92c6b9acdcac5d1475c00b8df8`. All 72 baseline Markdown documents are listed below; the two audit deliverables are excluded from that count.

“Reviewed” means project prose, examples, navigation, and history were inspected, or archive wrappers/presentation were inspected under the archive scope. It does not mean runtime behavior, live upstream claims, or every line of a captured standard was independently validated. Finding IDs refer to the report. Shared citation/style proposals do not imply that every occurrence in a listed file is defective. “No specific finding” is an explicit clean review result within this scope, not proof of correctness.

## 1. Project documents — 37 of 37 reviewed

| Document | Result and relevant sections |
|---|---|
| [README](../README.md) | Reviewed; no specific finding. Retain clear pre-release status and project premise. |
| [CONTRIBUTING](../CONTRIBUTING.md) | Reviewed; N01–N02 cross-document labels; N07 history convention. Preserve conduct, charter, and historical wording. |
| [SECURITY](../SECURITY.md) | Reviewed; no specific finding. Keep disclosure process and design/operational distinction. |
| [AUTHORING](AUTHORING.md) | Reviewed; C03 §8 graft evidence; C04 §5.2 ABI shorthand; C15 §3 examples; N01/N03 citation and companion conventions. |
| [BUILD-INFRA](BUILD-INFRA.md) | Reviewed; C05 §2.1 job identity; C06 §7.3 reproducibility; N02 §9 range link; N03 companion pins. Keep capacity limitations and pending gates. |
| [DESIGN](DESIGN.md) | Reviewed; C01–C06, C13–C16 at report locations; N01/N03/N05/N06 citations, pins, §12.9 density, fences. Preserve charter and recorded decisions. |
| [GENESIS](GENESIS.md) | Reviewed; C01 §2 installer fallback. Preserve from-nothing sequencing, exceptions, and required validation receipts. |
| [HELPERS](HELPERS.md) | Reviewed; no specific contract defect. Retain §6's explicit unresolved service-label encoding and helper boundaries; apply shared N01 citation standard. |
| [HOMEBREW-REVIEW](HOMEBREW-REVIEW.md) | Reviewed; C14 status boundaries; N01 citation ownership; N02 §4.14 range link; N03 pins; N07 preserved §8 proposals. External freshness not checked. |
| [KEY-RUNBOOK](KEY-RUNBOOK.md) | Reviewed; N02 §2.1 range link; shared N01 citation standard. No specific signing-contract defect identified; retain uncompleted drill status. |
| [MANUAL](MANUAL.md) | Reviewed; C01 §12.3; C03 §4.5; C05 §12.1; C06 §4.1; C07 §12.3; C08 §10; C12 §7.2; C16 GC summary; N01/N05–N07 presentation/history. |
| [NOMENCLATURE](NOMENCLATURE.md) | Reviewed; C03 §4; C10 §2; N01 §8; N03 header; N04 §§5–7; N07 duplicate v0.6 labels. |
| [ORCHARD-POLICY](ORCHARD-POLICY.md) | Reviewed; C03 §12; C06 §16; C13 §§2/13; C15 §3; N01/N03; N07 duplicate v1.10 labels. |
| [PACKAGE-FORMAT](PACKAGE-FORMAT.md) | Reviewed; C02 §3.8; C03 §3.11; C04 §5.1; C05 §6.3; C11 §3.14 authority; C15 examples/name syntax; C16 Appendix; N03/N06 metadata/fences. |
| [REPOSITORIES](REPOSITORIES.md) | Reviewed; C07 §§2/4/5.3; C09 §§7/10; N01/N03/N05, especially §3 matrix. |
| [SETUP](SETUP.md) | Reviewed; C03 §§2.8/4.1 approval summaries; C08 §§3.2–3.6; C10 §4.1; N01 external §12.8. |
| [SLICE-FORMAT](SLICE-FORMAT.md) | Reviewed; no specific finding. Retain exact wire-format/identity distinction and implementation caveat. |
| [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md) | Reviewed; no specific internal defect identified; authority used throughout C01–C16. Keep unimplemented status and acceptance requirements. |
| [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md) | Reviewed; no specific contract defect. Authority for C13/N08; preserve platform-specific pending states and refusal conditions. |
| [TOOLCHAIN](TOOLCHAIN.md) | Reviewed; C14 §§4–5 claim scope; N03 companion metadata. |
| [schematics/README](../schematics/README.md) | Reviewed; C16 repository vocabulary and schema-summary consistency. Preserve validator limitations. |
| [man/README](../man/README.md) | Reviewed; C14 build/help status claims; N06 Pandoc dialect must be preserved. |
| [aslice(1)](../man/aslice.1.md) | Reviewed; C10 leaves; N08 recovery/decommission navigation; shared N01 citations. |
| [aslice-apply(1)](../man/aslice-apply.1.md) | Reviewed; no specific contract defect identified; retain exact-plan/replay constraints; shared N01 citations. |
| [aslice-ca-update(1)](../man/aslice-ca-update.1.md) | Reviewed; no specific contract defect identified; retain policy/constraint and removal limits; shared N01 citations. |
| [aslice-doctor(1)](../man/aslice-doctor.1.md) | Reviewed; N02 SEE ALSO troubleshooting section. |
| [aslice-gc(1)](../man/aslice-gc.1.md) | Reviewed; no specific contract defect identified; retain reachability roots and conservative process handling; C16 policy reconciliation may affect summaries. |
| [aslice-graft(1)](../man/aslice-graft.1.md) | Reviewed; no specific contract defect identified; useful aligned boundary for C03; shared N01 citations. |
| [aslice-install(1)](../man/aslice-install.1.md) | Reviewed; no specific contract defect identified; preserve consent/capability requirements; shared N01 citations. |
| [aslice-machine(1)](../man/aslice-machine.1.md) | Reviewed; C08 apply/recovery alignment; C10 export vocabulary; N02 prune reference. |
| [aslice-orchard(1)](../man/aslice-orchard.1.md) | Reviewed; C11 DESCRIPTION replacement condition. |
| [aslice-repo(1)](../man/aslice-repo.1.md) | Reviewed; C09 synopsis needs settled prefer argument order; shared N01 citations. |
| [aslice-service(1)](../man/aslice-service.1.md) | Reviewed; C02 DESCRIPTION labels; retain data/readiness restrictions used by C12; N06 rendered FILES inspection. |
| [aslice-system-patch(1)](../man/aslice-system-patch.1.md) | Reviewed; C13/N08 navigation to preparation/finalization; preserve recovery limitations. |
| [aslice-uninstall(1)](../man/aslice-uninstall.1.md) | Reviewed; no specific contract defect identified; shared N01 citations. |
| [aslice-upgrade(1)](../man/aslice-upgrade.1.md) | Reviewed; C12 rollback flag/refusal scope. |
| [aslice-use(1)](../man/aslice-use.1.md) | Reviewed; N06 FILES placeholders and Pandoc rendering; shared N01 citations. |

## 2. Archive documents — 35 of 35 inspected

A01 is an optional wrapper-navigation improvement, not a claim that captured text is malformed. A03 identifies existing disclosed evidence limits, not newly established upstream inaccuracies. Records without an individual finding retain the common preservation requirements. Full-original and source-asset integrity was checked with the existing verifier; online recapture and substantive revalidation of originals were outside this audit.

| Archive document | Result |
|---|---|
| [APPLE_CONFIGURING_SYSTEM_INTEGRITY_PROTECTION](refs/APPLE_CONFIGURING_SYSTEM_INTEGRITY_PROTECTION.MD) | Inspected; no specific navigation/presentation finding. Keep applicability limits. |
| [APPLE_DEFAULT_LOGIN_SHELL](refs/APPLE_DEFAULT_LOGIN_SHELL.MD) | Inspected; no specific finding. Preserve migrated-account qualification. |
| [APPLE_DYNAMIC_LIBRARY_DESIGN_GUIDELINES](refs/APPLE_DYNAMIC_LIBRARY_DESIGN_GUIDELINES.MD) | Inspected; no specific presentation finding; local authority supporting C04. |
| [APPLE_SIGNED_SYSTEM_VOLUME_SECURITY](refs/APPLE_SIGNED_SYSTEM_VOLUME_SECURITY.MD) | Inspected; no specific presentation finding; preserve limits on platform claims. |
| [APPLE_WRITABLE_ROOT_VOLUME_DISCUSSION](refs/APPLE_WRITABLE_ROOT_VOLUME_DISCUSSION.MD) | Inspected; no specific presentation finding; A03 discussion evidence limits retained. |
| [CURL_MOZILLA_CA_EXTRACTION](refs/CURL_MOZILLA_CA_EXTRACTION.MD) | Inspected; no specific finding. Keep omitted-constraint caveats. |
| [GITHUB_INTEL_RUNNER_RETIREMENT](refs/GITHUB_INTEL_RUNNER_RETIREMENT.MD) | Inspected; no specific finding. Keep hosted/self-hosted distinction and dated scope. |
| [HOMEBREW_5_RELEASE](refs/HOMEBREW_5_RELEASE.MD) | Inspected; no specific formatting defect; source asset/license intact; A03 missing related releases disclosed. |
| [HOMEBREW_6_RELEASE](refs/HOMEBREW_6_RELEASE.MD) | Inspected; no specific formatting defect; source asset/license and retrieval limits retained. |
| [HOMEBREW_7_RELEASE_AND_INTEL_SUPPORT](refs/HOMEBREW_7_RELEASE_AND_INTEL_SUPPORT.MD) | Inspected; no specific formatting defect; source asset/license and dated-policy scope retained. |
| [HOMEBREW_ATTESTATION_PROPOSAL_17019](refs/HOMEBREW_ATTESTATION_PROPOSAL_17019.MD) | Inspected; no specific finding; A03 missing chronology must remain explicit. |
| [HOMEBREW_HISTORICAL_OVERVIEW](refs/HOMEBREW_HISTORICAL_OVERVIEW.MD) | Inspected; no specific finding; A03 unpinned revision and secondary-source limits retained. |
| [HOMEBREW_INTEL_CI_DISCUSSION_7044](refs/HOMEBREW_INTEL_CI_DISCUSSION_7044.MD) | Inspected; no specific presentation finding; preserve participant attribution and reported/verified distinction. |
| [HOMEBREW_MONTEREY_DISCUSSION_5603](refs/HOMEBREW_MONTEREY_DISCUSSION_5603.MD) | Inspected; no specific presentation finding; A03 partial discussion scope retained. |
| [HOMEBREW_PROVENANCE_BETA_IMPLEMENTATION](refs/HOMEBREW_PROVENANCE_BETA_IMPLEMENTATION.MD) | Inspected; no specific finding; preserve dated beta versus proposal distinction. |
| [HOMEBREW_PROVENANCE_BETA_SIGSTORE](refs/HOMEBREW_PROVENANCE_BETA_SIGSTORE.MD) | Inspected; no specific finding; preserve dated implementation evidence. |
| [HOMEBREW_SECURITY_AND_SUPPLY_CHAIN](refs/HOMEBREW_SECURITY_AND_SUPPLY_CHAIN.MD) | Inspected; no specific finding; full asset/license and applicability limits retained. |
| [HOMEBREW_SUPPORT_TIERS](refs/HOMEBREW_SUPPORT_TIERS.MD) | Inspected; no specific finding; full asset/license and dated support scope retained. |
| [JSON_SCHEMA_2020_12_CORE](refs/JSON_SCHEMA_2020_12_CORE.MD) | Inspected; A01 long-original navigation candidate; A02 schematics README label. Preserve original and notices. |
| [JSON_SCHEMA_2020_12_VALIDATION](refs/JSON_SCHEMA_2020_12_VALIDATION.MD) | Inspected; A01 long-original navigation candidate; A02 schematics README label. Preserve original and notices. |
| [LIBARCHIVE_TAR_FORMAT](refs/LIBARCHIVE_TAR_FORMAT.MD) | Inspected; A01 long-original navigation candidate. No source-text changes proposed. |
| [LIBCXX_VENDOR_CONFIGURATION](refs/LIBCXX_VENDOR_CONFIGURATION.MD) | Inspected; no specific presentation finding; target-platform validation limits retained. |
| [MAC_PRO_2013_COMPATIBLE_OPERATING_SYSTEM](refs/MAC_PRO_2013_COMPATIBLE_OPERATING_SYSTEM.MD) | Inspected; no specific finding; hardware compatibility is not a farm test receipt. |
| [OWC_INTEL_MAC_TRANSITION_REPORT](refs/OWC_INTEL_MAC_TRANSITION_REPORT.MD) | Inspected; no specific finding; preserve attributed secondary-report scope. |
| [Archive README](refs/README.MD) | Inspected; no specific defect. Retain subject catalog, capture classifications, and license links; A01 return-navigation destination. |
| [RFC_8785_JSON_CANONICALIZATION_SCHEME](refs/RFC_8785_JSON_CANONICALIZATION_SCHEME.MD) | Inspected; A01 long-original navigation candidate; preserve original and notices. |
| [RFC_8878_ZSTANDARD](refs/RFC_8878_ZSTANDARD.MD) | Inspected; A01 long-original navigation candidate; preserve original and notices. |
| [SMARTCARD_HSM_ALGORITHMS](refs/SMARTCARD_HSM_ALGORITHMS.MD) | Inspected; no specific finding; preserve algorithm/firmware limits. |
| [SOURCE-INVENTORY](refs/SOURCE-INVENTORY.MD) | Inspected; A03 existing gaps remain explicit. Compact table/detail navigation may improve readability without erasing limits. |
| [TEMPLATE](refs/TEMPLATE.MD) | Inspected; no specific defect. Preserve instructions for provenance, section guides, licenses, and gaps. |
| [THE_UPDATE_FRAMEWORK_SPECIFICATION](refs/THE_UPDATE_FRAMEWORK_SPECIFICATION.MD) | Inspected; A01 long-original navigation candidate; preserve original and notices. |
| [TOML_1_0_SPECIFICATION](refs/TOML_1_0_SPECIFICATION.MD) | Inspected; A01 long-original navigation candidate; A02 schematics README label. |
| [TOML_SCHEMA_SPECIFICATION](refs/TOML_SCHEMA_SPECIFICATION.MD) | Inspected; A01 long-original navigation candidate; A02 schematics README label. |
| [X86_64_MICROARCHITECTURE_LEVELS](refs/X86_64_MICROARCHITECTURE_LEVELS.MD) | Inspected; no specific presentation finding. Preserve ISA evidence limits. |
| [YUBIKEY_PIV_ALGORITHMS](refs/YUBIKEY_PIV_ALGORITHMS.MD) | Inspected; no specific finding; preserve exact firmware/application qualification. |

## 3. Coverage boundaries

The review preserves historical contradictions as history and reports active contradictions separately. It makes no public command, API, schema, or runtime change. Checker design and rendered acceptance requirements are in the report; neither a newly implemented checker nor a completed Pandoc render is claimed.
