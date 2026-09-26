# Documentation audit remediation — 26 September 2026

- **Status:** Documentation and offline tooling changes; no package-manager runtime implementation.
- **Baseline:** `a020aa6879896d92c6b9acdcac5d1475c00b8df8`, plus the two original audit reports.
- **Review record:** [Findings](DOCUMENTATION-AUDIT.md) and [72-document coverage](DOCUMENTATION-AUDIT-COVERAGE.md) remain dated baseline evidence.
- **Validation guide:** [Documentation checks](DOCUMENTATION-CHECKS.md).

## Decisions confirmed by the owner

| Question | Applied decision |
|---|---|
| Machine setup failure | Roll back the whole managed-state apply. Conflicting external edits or unavailable recovery material leave a recoverable pending/error state, not successful partial completion. Establish repository trust separately before planning; rollback never resets security authority. |
| Package namespace | Only core uses bare package names. Every other repository, including extended, requires `repo:package`. Remove overlap prompts, preferences, and their proposed resolution table/commands. |
| Store-size GC | Warn within a configurable margin, default 10% below the limit. At or above the limit ask `Run garbage collection? [y/N]`, default No. Do not collect automatically. Non-interactive checks warn without collecting. |
| Leaves and export | `aslice leaves` means packages with no installed dependents. Machine export preserves explicitly requested packages, including those that also have dependents. |
| Parallel library names | Use names such as `openssl3` and `openssl4`; reserve `@` for version/stream selection. |
| Build prefix | Build-time `ctx.prefix` is a relocation placeholder. Materialization assigns the final artifact-addressed path after hashing. Test-context paths refer to the materialized installation. |
| Machine-file graft lists | Names select only matching existing local approvals. Repository, version, script hashes, and effective behavior-manifest digest must match. A fresh machine must approve again; exports transfer no authority. |
| Toolchain linkage | The libSystem-only dynamic-linking restriction applies to the manager binary, not every package. |

These are explicit content decisions, not described as meaning-preserving prose edits. The new `gc.warning_margin_percent` field is reflected in both configuration schematics; runtime implementation remains future work. No concrete service-label encoding or machine-operation JSON schema was invented.

## Findings addressed

| Finding | Remediation |
|---|---|
| C01 | MANUAL's troubleshooting fallback and GENESIS's installer inventory now require an independently authenticated kit before first execution; later pinned HTTP transport remains distinguished. |
| C02 | PACKAGE-FORMAT and service summaries distinguish user profiles from protected root execution. Labels are scoped by prefix/profile/package; concrete encoding remains explicitly unspecified in HELPERS. |
| C03 | Graft summaries now describe isolated staging, helper-committed deltas, v1 network refusal, digest-bound approvals, effect-based capability checks, and rehearsal limits. Machine exports cannot transfer approval. |
| C04 | ABI summaries distinguish provider current version, client requirements, symbol lists, equality hashes, exact bindings, and explicit tested rebinding. |
| C05 | Store examples use artifact-addressed paths; job hashes identify inputs, not result hashes. The build-prefix description and schematic comment follow the approved placeholder contract. |
| C06 | Provenance and SBOM summaries identify separate authenticated objects. Reproducibility comparisons distinguish unsigned evidence from served artifacts. |
| C07 | Discovery examples separate TUF anchors and package-signing keys. Authenticated sequential rotation is distinct from unauthenticated replacement/rebootstrap. |
| C08 | SETUP and machine reference now describe preflight, consent, one journaled apply, whole-apply rollback, and the deferred serialized machine-operation format. |
| C09 | Replaced overlap selection with exact namespaces. The old command-order question disappears with the removed preference interface. Numbered headings remain for link compatibility; their text explains the superseding behavior. |
| C10 | Leaves and explicit request roots are distinct in command/export descriptions. |
| C11 | Orchard replacement is required for renames and must resolve whenever supplied; it is not prohibited for other reasons. |
| C12 | Service rollback examples and options require data compatibility or authorized tested restoration and retain failure evidence. Machine apply's whole-transaction rollback is called out separately. |
| C13 | System-patch summaries use protected closures and platform-specific recovery; the policy summary includes the explicit verified-repository grant. |
| C14 | Toolchain claims have the approved manager scope and testing limits. Man-page generation/help integration are labeled specified work. |
| C15 | Library naming is consistent with the approved grammar. Recipe examples distinguish excerpts/placeholders, normalize illustrated versions, and give each binary artifact its own payload map and execution requirements. |
| C16 | Lock-field and repository summaries agree with their schematics. GC warnings and confirmation follow the owner's threshold decision. |
| N01–N02 | Active cross-document citations name/link their owners; semantic anchors preserve numbered headings and existing generated destinations. Stale doctor/prune references and multi-destination links are repaired. |
| N03 | Current companion navigation drops incidental version pins. Historical version mentions remain unchanged. |
| N04–N06 | Acronyms are alphabetized, one term per row. The capability matrix is compact with conditions outside it. Long documents have navigation, runtime prose has clearer paragraph boundaries, fences have labels, metadata renders as a list, and man placeholders/synopses render visibly. |
| N07 | History rows and ordering are preserved. Explanatory notes identify recorded duplicates/order without rewriting evidence. |
| N08 | Command summaries point to the specified recover/decommission and protected-volume prepare/finalize workflows. |
| A01–A02 | Long archive wrappers have navigation to account/context/original/catalog. Schema backlinks identify schematics/README. Source bytes and notices remain unchanged. |
| A03 | Existing source-evidence limits remain disclosed. No online recapture or claim of newly verified external facts was made. |

## Validation and preservation

The offline checker covers local files and case, fragments, explicit/generated anchor collisions, citation labels and owners, section ranges, reference-style links, fenced literals, table columns, and bounded historical/archive exceptions. Its regression suite includes relative and encoded paths, duplicate headings, punctuation/Unicode, escaped table pipes, and Pandoc definition lists. The archive verifier now recognizes semantic anchors and the full-original navigation boundary.

Direct comparisons against the saved working-file baseline preserve all eight full captured originals, 17 source assets/notices, 19 existing history tables, numbered heading text, and HOMEBREW-REVIEW's preserved proposal section. Prose-fix audits were run for each changed Markdown file. Intentional differences are the contract corrections and owner decisions above, obsolete overlap-interface removal, corrected illustrative paths/recipe fields, semantic links/navigation, fence labels, glossary/table layout, and current version/new history entries. Unaffected vendor restrictions and repository capability rules were retained after preservation review.

Representative glossary, capability-table, long-specification, and man-page output was rendered with the CommonMark/GFM profile and Pandoc and inspected in headless Edge. Man output was generated as roff as well as HTML. This review caught and corrected collapsed synopsis lines. Render artifacts and preservation logs were kept in the temporary review baseline, outside the tracked tree.

Validation passed: 76 Markdown documents with zero checker errors or warnings; 15 documentation regression tests; 22 archive-verifier tests; five slice-contract tests; existing contract/fixture checks; archive verification (32 records, 53 files); and whitespace checks. The contract checker separately reports 52 archive files because its inventory differs from the curator's. Mechanical success does not prove TOML-schema semantics, runtime security, platform support, or present external URL availability. Those remain the separately documented implementation and evidence obligations.
