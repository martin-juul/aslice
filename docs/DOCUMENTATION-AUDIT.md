# Documentation audit — 26 September 2026

Remediation: see [DOCUMENTATION-REMEDIATION](DOCUMENTATION-REMEDIATION.md) for the applied decisions, fixes, and validation. This report retains the original review findings as historical evidence.
- **Status:** Review and proposal; no source-document rewrites or checker implementation.
- **Baseline:** `a020aa6879896d92c6b9acdcac5d1475c00b8df8`.
- **Scope:** 72 Markdown documents: 37 project documents and 35 archive documents. This report and its coverage checklist are new deliverables, outside that baseline count.
- **Method:** Read project prose, examples, command summaries, and histories; inspect archive wrappers, navigation, provenance, notices, and inventory. Compare shared requirements with their named owners and selected schema declarations. Captured originals were preserved, not independently revalidated against live sources.
- **Coverage:** [Per-document checklist](DOCUMENTATION-AUDIT-COVERAGE.md).

The highest-priority repairs are substantive. Several summaries still describe behavior superseded by STATE-AND-RECOVERY: HTTP bootstrap, root execution through user-owned profiles, graft network access, compatibility-based artifact substitution, and recovery. Formatting these passages without reconciling their requirements would make conflicting instructions easier to follow.

Navigation and presentation also need a common standard. Bare section references have several possible owners, numbered heading fragments are fragile, and current companion-version pins have drifted. The archive is structurally consistent and passes its existing verifier; its evidence gaps must remain visible.

## 1. Priority and authority

**P1** means a conflicting requirement or misleading operational instruction that should be resolved before examples are presented as usable. **P2** means a navigation, example, or status defect that can misdirect a reader. **P3** means readability or maintenance improvement. These priorities describe documentation risk, not confirmed runtime vulnerabilities: the project identifies its runtime as unimplemented.

| Contract | Owner and supporting documents | Review rule |
|---|---|---|
| Artifact identity, exact bindings, privileged ownership, recovery, retained trust, replay | [STATE-AND-RECOVERY](STATE-AND-RECOVERY.md), especially §§1–8 | Explicit authority declaration takes precedence over older summaries and examples. |
| Archive representation | [SLICE-FORMAT](SLICE-FORMAT.md), STATE-AND-RECOVERY §1 | Distinguish canonical artifact, delivered archive, and detached evidence. |
| Protected system volumes | [SYSTEM-VOLUMES](SYSTEM-VOLUMES.md), STATE-AND-RECOVERY §3 | Platform preparation, reboot verification, and restoration are not a generic symlink operation. |
| Author input and recipe API | [PACKAGE-FORMAT](PACKAGE-FORMAT.md), [schematics](../schematics/README.md) | Reconcile examples with schemas and state contracts; do not invent API corrections editorially. |
| Acceptance, promotion, and trust tiers | [ORCHARD-POLICY](ORCHARD-POLICY.md), [REPOSITORIES](REPOSITORIES.md) | Preserve explicit owner decisions; report internal contradictions requiring a decision. |
| Signing and farm operations | [KEY-RUNBOOK](KEY-RUNBOOK.md), [BUILD-INFRA](BUILD-INFRA.md) | Separate specified procedures from completed drills and deployed services. |
| Vocabulary, user procedures, and command reference | [NOMENCLATURE](NOMENCLATURE.md), [MANUAL](MANUAL.md), [man pages](../man/README.md) | Summarize owning contracts and link them; summaries cannot weaken refusal conditions. |
| Archived evidence | [Archive catalog](refs/README.MD), [inventory](refs/SOURCE-INVENTORY.MD) | Preserve source identity, dates, capture limits, originals, licenses, and checksums. |

## 2. Contract findings

Each finding identifies the conflicting locations, the authority, and the proposed correction. A request for a decision is deliberately distinct from an editorial repair.

### C01 — P1: bootstrap fallback still promises an unsafe first step

**Locations:** MANUAL §12.3, installer-failure row; GENESIS §2, installer inventory. The manual says “Nothing — it falls back to plain HTTP”; the genesis summary also describes an HTTPS-to-HTTP fallback. **Authority:** STATE-AND-RECOVERY §7, DESIGN §10.3, and MANUAL §2.2 distinguish authenticated first execution from subsequent pinned downloads.

**Correction:** State that a TLS-dead machine needs an independently authenticated offline bootstrap kit before executing anything. HTTP can transport later files only after exact pins have been authenticated. Keep genesis sequencing and its validation caveats; repair the active inventory description rather than historical entries.

### C02 — P1: service summaries bypass protected execution and omit label scope

**Locations:** PACKAGE-FORMAT §3.8 describes generated `org.aslice.<name>` plists and execution through the profile; DESIGN §12.8's status example and aslice-service(1) retain simplified labels. **Authority:** STATE-AND-RECOVERY §3 requires root-owned complete execution closures; DESIGN §12.8 requires prefix/profile distinction. HELPERS §6 leaves concrete label encoding unspecified.

**Correction:** Separate user and root service execution. Link the protected-root contract, including environment and configuration ownership. Mark labels illustrative until their encoding is settled; do not invent a public label format during cleanup.

### C03 — P1: graft declarations, approvals, and summaries retain superseded powers

**Locations:** PACKAGE-FORMAT §3.11 permits `network = true` in its comment and describes effects such as kext/daemon operations and elevated scripts without the staging boundary. MANUAL §4.5 summarizes approval with version/script hashes and broad rollback language. SETUP §2.8's name allow-list does not explain binding to reviewed manifests. NOMENCLATURE §4's behavior-manifest definition describes network/elevation and treats the manifest as containment.

**Authority:** STATE-AND-RECOVERY §4 and DESIGN §12.15: isolated staging, helper-committed validated deltas, no live privileged script execution, v1 refusal of network access, and approval bound to repository, version, script digests, and complete effective manifest digest. Rehearsal is not proof of containment.

**Correction:** Align all summaries and examples; retain capability checks regardless of the mechanism expressing an effect. AUTHORING §8 and ORCHARD-POLICY §12 should link the refusal conditions alongside rehearsal. **Decision:** explain how a machine allow-list selects the reviewed binding without silently adding schema fields. aslice-graft(1)'s stronger boundary is useful existing wording to retain.

### C04 — P1: ABI summary permits substitution that exact bindings forbid

**Locations:** PACKAGE-FORMAT §5.1 uses provider `compatibility_version` and a covering symbol fingerprint to justify no rebuild; AUTHORING §5.2's summary uses the older shorthand. **Authority:** STATE-AND-RECOVERY §2 distinguishes provider `current_version`, client requirements, symbol lists versus equality hashes, unknown evidence, and exact runtime artifact bindings.

**Correction:** Explain loader checks separately from ABI evidence and rebinding. A profile switch cannot retarget absolute dependency bindings; rebuilding or verified relocation produces a new artifact and reruns tests. Replace repeated abbreviated algorithms with a concise explanation and authority link.

### C05 — P1: store paths, build identities, and recipe prefixes disagree

**Locations:** DESIGN §5.2's store component uses `<name>-<version>-<buildid>`; DESIGN §12.6 and MANUAL §12.1 retain old-style example paths. PACKAGE-FORMAT §6.3 calls `ctx.prefix` the final store path. BUILD-INFRA §2.1 calls the job hash the expected result identity.

**Authority:** STATE-AND-RECOVERY §1 and DESIGN §8.1 use `<prefix>/store/<artifact-hex>/`, distinguish compatibility keys from artifact identity, and require canonical relocation placeholders to avoid a self-hash cycle.

**Correction:** Update explanatory paths using clearly marked full-digest placeholders; distinguish scheduling/cache keys from output identity. **Decision:** settle the documented meaning of `ctx.prefix` during canonical builds and materialization before editing API language. This review proposes no API change.

### C06 — P1: provenance and SBOM placement conflicts with artifact identity

**Locations:** DESIGN §9.5 places provenance in the manifest; §10.6 describes embedded SBOMs; MANUAL §4.1 puts SBOM/builder information in the manifest; ORCHARD-POLICY §16 describes SBOMs in slices. BUILD-INFRA §7.3's bitwise-slice reproducibility language also needs scope.

**Authority:** STATE-AND-RECOVERY §1 separates variable provenance and signatures from the canonical manifest; SLICE-FORMAT §§1–2 defines archive members. STATE-AND-RECOVERY §10 distinguishes unsigned reproducibility evidence from served artifacts.

**Correction:** Name the precise object in each passage. Explain which bytes are compared and which authenticated evidence binds them. Do not equate unsigned build reproducibility with identical detached signatures or publication metadata.

### C07 — P1: repository discovery and rotation conflate different keys

**Locations:** REPOSITORIES §§2, 4, and 5.3 describe a single fingerprint, an OpenPGP root example, and blocking/re-pinning on key change. MANUAL §12.3's key-pin row also treats rotation and hijack as indistinguishable.

**Authority:** STATE-AND-RECOVERY §7 and KEY-RUNBOOK §3.1 require Ed25519 TUF metadata and authenticated sequential root rotation for every repository; OpenPGP package signatures are additional. `schematics/toml/sources.tosd` already distinguishes `tuf_root_fingerprint` from `key_fingerprint`.

**Correction:** Show the two identities separately; distinguish authenticated rotation, unauthenticated replacement, and compromise rebootstrap. A normal verified root transition does not require manual re-pinning.

### C08 — P1: machine application has inconsistent planning and recovery boundaries

**Locations:** SETUP §3.2 promises a complete confirmed plan, then resolves packages after repository/configuration mutation; its elevation summary omits other privileged effects. SETUP §3.6 says completed steps stand while §3.5 describes rollback. Serialized machine-plan wording borrows the package-plan format.

**Authority:** STATE-AND-RECOVERY §§3, 5, and 8 require effect-based authorization, recovery of uncommitted transactions, and explicitly defer serialized machine-wide operation plans until their schema exists.

**Decision:** specify whether the apply is one transaction or several committed transactions, the planning prerequisites, and the consent shown for partial completion. Then align SETUP, MANUAL §10, and aslice-machine(1). Do not solve this by changing the existing package-plan schema in an editorial PR.

### C09 — P2: overlap policy and command argument order are internally inconsistent

**Locations:** REPOSITORIES §10.1 limits overlap prompts to equal effective trust, while §10.2's example prompts across verified and third-party sources. §7 lists `repo prefer <name> <pkg>`; §10.4 uses `repo prefer convolver plugins` in the opposite apparent order. aslice-repo(1)'s abbreviated synopsis does not settle this.

**Decision:** choose the intended resolution rule and argument order, record them in the owning contract, and update summaries together. No new command is proposed.

### C10 — P2: leaves and explicitly requested packages are conflated

**Locations:** SETUP §4.1 and aslice(1) describe leaves as explicitly requested packages; machine export summaries use “leaves.” **Authority:** NOMENCLATURE §2 distinguishes graph leaves from `on_request`; DESIGN §8.4 tracks request roots separately. MANUAL §10's export explanation correctly says explicitly installed packages.

**Correction:** use “explicitly requested packages” for export intent. **Decision:** settle whether the `leaves` command reports graph leaves or request roots, then align its reference. A requested package can also be another package's dependency.

### C11 — P2: lifecycle reference strengthens an optional field into a prohibition

**Locations:** aslice-orchard(1), DESCRIPTION: replacement is present “if and only if” the reason is renamed. **Authority:** PACKAGE-FORMAT §3.14 makes replacement optional generally and required for renames.

**Correction:** say “required when `reason = "renamed"`; when supplied, it must resolve.” Preserve other lifecycle requirements.

### C12 — P1: rollback shorthand omits service-data eligibility

**Locations:** MANUAL §7.2's quick rollback assurance and aslice-upgrade(1)'s statement that noninteractive runs without the rollback flag are refused. **Authority:** STATE-AND-RECOVERY §5 and aslice-service(1) distinguish readiness, persistent-data compatibility, authorized backup/restore, and failure behavior.

**Correction:** scope refusal and rollback to their actual conditions. The absence of a rollback flag does not by itself prohibit every unattended upgrade. Generation rollback does not restore databases or remote effects. Keep the diagnostic evidence and default failure behavior explicit.

### C13 — P1: system-patch summaries retain ordinary-profile semantics

**Locations:** ORCHARD-POLICY §2's category summary and §13's profile-symlink description; DESIGN §15's OS-update risk row. The category summary also omits the verified-repository grant allowed later in the policy.

**Authority:** STATE-AND-RECOVERY §3, SYSTEM-VOLUMES, and DESIGN §12.11 require protected closures and platform-specific recovery, with verified repositories admitted only under an explicit grant.

**Correction:** replace blanket profile-link/rollback assurances with the owning contracts. Keep refusal paths and pending reboot verification. Expand man-page navigation to already specified prepare/finalize workflows without creating command semantics.

### C14 — P2: toolchain and status claims need a precise subject

**Locations:** TOOLCHAIN §5's “only dynamic dependency” wording can encompass all slices despite packaged dylibs/runtimes; §4's deployment-target assurance reads as execution proof. **Authority:** PACKAGE-FORMAT's dependency model and STATE-AND-RECOVERY §10's platform acceptance requirements.

**Correction:** identify which binary the dependency claim describes; separate target selection from validated execution. **Decision:** confirm intended scope before narrowing the statement. Across man/README and HOMEBREW-REVIEW, distinguish planned generated help/build behavior and proposed parity from completed implementation. Keep HOMEBREW-REVIEW §8's explicitly historical proposals intact.

### C15 — P2: names and examples need explicit validity boundaries

**Locations:** ORCHARD-POLICY §3 uses `openssl@3` as a naming lineage while PACKAGE-FORMAT §3.1's name grammar excludes `@`; §5.2 mixes `openssl3` and `openssl@4`. DESIGN §6.1's apparent complete recipe omits required context such as `spec`, uses `[source]`, and illustrates non-normalized versioning. AUTHORING §3 and PACKAGE-FORMAT §3.11 also need a completeness review (required revision/CPU fields and the scope of `[[binary.payload]]` after array entries).

**Authority:** PACKAGE-FORMAT, `schematics/toml/package.tosd`, and state CPU/identity requirements.

**Correction:** distinguish package identifiers from selector syntax. Mark excerpts and placeholders explicitly; use validated complete fixtures where readers are invited to copy a whole file. In TOML, a nested table after an array entry belongs to that entry, not all preceding entries. **Decision:** resolve naming intent before editing examples. Do not silently turn illustrative hashes into purported real source hashes.

### C16 — P2: schema summaries and GC policy have drifted

**Locations:** PACKAGE-FORMAT's Appendix field index retains `index_snapshot`; `schematics/toml/lock.tosd` uses per-repository bindings. schematics/README's repository description invokes an older Git-oriented definition. DESIGN §8.4's automatic GC wording differs from MANUAL's watermark/suggestion description.

**Correction:** generate or manually reconcile the field index with the owned schema; distinguish orchard Git trees from signed repositories. **Decision:** resolve automatic-versus-suggested GC behavior before prose changes. Existing schema checks do not adjudicate this policy choice.

## 3. Navigation, presentation, and archive findings

### N01 — P2: citation ownership is ambiguous

NOMENCLATURE §8 permits bare numbers to refer to other documents. HOMEBREW-REVIEW's blanket DESIGN convention collides with its local §4.x references. CONTRIBUTING has policy/package references whose document identity must be inferred; SETUP's bare §12.8 points outside SETUP.

Resolve active citations one at a time, then remove the implicit cross-document convention. External labels name the destination document; local `§N` remains acceptable when unambiguous. History and literal examples are scoped exceptions, not permission to leave active instructions ambiguous.

### N02 — P2: existing links and references can land on the wrong section

aslice-doctor(1)'s MANUAL §11 troubleshooting pointer should identify §12. aslice-machine(1)'s prune pointer to REPOSITORIES §10 points at overlap resolution; use SETUP §3.3 for pruning and a separately identified repository-retention rule where needed. BUILD-INFRA §9, KEY-RUNBOOK §2.1, and HOMEBREW-REVIEW §4.14 label a link ORCHARD-POLICY §§18.1–18.2 but land only on §18.1. CONTRIBUTING's external `§18.2` label omits the document name.

Link each distinct section separately. Missing-file checks alone cannot detect any of these semantic errors. Add stable semantic anchors only after mapping the actual intended destinations.

### N03 — P3: current companion pins age without adding useful authority

NOMENCLATURE's header names DESIGN v1.24, PACKAGE-FORMAT v0.16, and TOOLCHAIN v0.2, while those documents identify later versions. Similar current companion inventories appear in the main specifications and guides.

Remove incidental version pins from current navigation. Retain a version when it deliberately identifies a historical baseline, and label that purpose. Do not update historical version mentions to the latest release.

### N04 — P3 layout, P2 definitions: glossary compression hides independent terms

NOMENCLATURE §6 compresses acronyms into one paragraph. Convert it to an alphabetized two-column term/expansion table, splitting grouped terms such as CA/TLS and CVE/CPE/OSV into searchable rows.

Review factual corrections separately: §5's System keychain/SecureTransport entry implies tools use the OS stack rather than their own despite DESIGN §12.10's distinction; §7's Homebrew mapping collapses orchard/tap/repository distinctions; the generic slice/universal wording needs the vendor scope of PACKAGE-FORMAT §3.11. Preserve meanings during the layout-only change, and attach separate decisions to definition changes.

### N05 — P3: long paragraphs and tables mix several jobs

DESIGN §12.9 combines runtime selection, mechanisms, examples, and exceptions in long paragraphs. REPOSITORIES §3's capability matrix contains explanations better handled immediately below a compact matrix. Keep every gate and exception while separating mechanism, example, and refusal conditions. Use an explanatory register for guides, procedural register for runbooks, and declarative register for contracts. Preserve effective direct language, including README's premise and the no-telemetry charter.

Add compact section navigation to documents with at least ten second-level headings. Keep existing numbering and headings. Do not add a giant index to short man pages or every archive wrapper.

### N06 — P2 rendering risk, P3 consistency: Markdown needs dialect-aware rules

Unlabeled fences recur in DESIGN and MANUAL. PACKAGE-FORMAT's adjacent metadata lines can render as one paragraph. Man-page FILES examples containing raw `<pkg>`, `<runtime>`, or `<stream>` need rendered inspection because angle-bracket words may be interpreted as HTML.

Use `sh` for commands, `console` for transcripts, `text` for trees/grammar, and appropriate existing labels for JSON/TOML/Starlark examples. Preserve command bytes. Use a metadata list and consistent blank lines, heading hierarchy, and indentation. Escape literal table pipes even within code spans where the renderer requires it. Preserve Pandoc `%` title blocks and definition lists: generic Markdown lint must not rewrite that dialect.

### N07 — P3: history presentation must not become history rewriting

NOMENCLATURE repeats v0.6 and ORCHARD-POLICY repeats v1.10 with different notes. These are not evidence that either note is redundant. MANUAL's v0.16 placement differs from the usual newest-first convention. Historical companion pins and superseded proposals are evidence, not current instructions.

Keep the contents and order intact in an editorial pass. If helpful, add a current explanatory note outside the preserved history identifying duplicate labels or recorded ordering. Resolve any future history-layout policy separately; do not silently delete, renumber, reorder, or modernize old entries.

### N08 — P2: command summaries omit specified recovery entry points

STATE-AND-RECOVERY §6 specifies `recover` and `decommission`, while the main man-page command summary does not guide readers to them. SYSTEM-VOLUMES specifies preparation and finalization steps beyond aslice-system-patch(1)'s abbreviated command list. Add navigation and summaries for these already specified operations after confirming their owning contracts; do not invent missing flags, schemas, or implementation claims.

### A01 — P3: archive navigation can improve without editing originals

The 35 Markdown archive documents comprise 32 source records plus catalog, inventory, and template. The inventory distinguishes complete originals/assets from technical accounts. Existing source locators, applicability limits, omissions, and licenses are useful and should remain.

For long records containing a full original, add compact wrapper navigation to the account, section guide, original, and catalog if rendered inspection confirms a benefit. Keep captured original fences/text and separate source assets byte-for-byte. Upstream-relative links inside originals retain upstream meaning; do not repair them as if they were broken project links.

### A02 — P2 label clarity: archive backlinks should name the right README

The JSON Schema and TOML/TOSD records have Used-by labels beginning “README” that target `schematics/README.md`. Use “schematics/README” in those labels to distinguish it from the project README and archive catalog. The target itself need not be changed.

### A03 — evidence limits, not a new formatting defect

SOURCE-INVENTORY already records incomplete discussions, unpinned historical revisions, missing related release posts, uncaptured dependencies, and absent platform validation. Keep those qualifications attached to the relevant claims. A denser omission table can link to record details, but must not imply complete coverage by hiding its caveats. This audit did not check live URLs or confirm present external policies. Existing retrieval/review dates describe prior archive work, not new online verification here.

Any later wrapper repair follows ref-curator: preserve originals/notices, review Used-by destinations, update inventory/catalog only where warranted, regenerate checksums for intentional archive changes, then run integrity checks. Never rehash unexplained source-byte changes just to make verification pass.

## 4. Proposed house standards and examples

### 4.1 Metadata, structure, and register

Use a short status/audience/authority block where useful, rather than requiring every small page to carry bureaucracy. A specification says what it owns and links overlapping owners. An operational procedure states its validation status and required receipts. A user guide links its command contracts. Distinguish **specified**, **implemented**, **tested on named platforms**, and **operational**; none implies the next.

Use tables for comparisons and mappings with compact cells. Use paragraphs or subsections for mechanisms and exceptions. Keep numbered headings, normative strength, examples, command text, and charter language. Split only where doing so exposes a useful logical boundary. Blank lines separate headings, paragraphs, lists, tables, and fences; list continuation indentation must retain the intended nesting.

### 4.2 Semantic anchors and citation syntax

Place a unique explicit anchor directly before each cited section, for example `<a id="runtime-management"></a>`, while keeping the existing numbered heading. Names are lowercase semantic identifiers, independent of numbers and editorial heading wording. Check collisions with both explicit and generated IDs. Retain previously published explicit IDs as aliases if a destination moves; verify old generated links still resolve in the target renderer.

Proposed source syntax, shown literally because these anchors are not yet installed:

```markdown
Before: See §12.9 for runtime selection.
After: See [DESIGN §12.9](DESIGN.md#runtime-management) for runtime selection.

Before: [ORCHARD-POLICY §18.1–§18.2](ORCHARD-POLICY.md#181-environments-branching-and-promoted-builds)
After: [ORCHARD-POLICY §18.1](ORCHARD-POLICY.md#release-environments) and
       [ORCHARD-POLICY §18.2](ORCHARD-POLICY.md#release-versions)
```

The names above are proposals, not usable destinations in the baseline. Same-document citations may use `§N`, preferably linked for long documents. Active cross-document labels always identify the document. Link separate destinations separately; do not hide a range behind its first endpoint. Reference-style Markdown links are equally valid.

Exceptions are narrow: preserve historical citations, literal syntax/examples, captured originals, and Pandoc command cross-references such as `aslice-install(1)`. Archive wrappers remain checked; archived originals retain their original reference conventions. A date somewhere in a paragraph does not make active guidance historical.

### 4.3 Glossary layout example

Before, schematic compression: `ABI — Application Binary Interface; CA — Certificate Authority; TLS — Transport Layer Security.`

After, layout only:

| Term | Expansion |
|---|---|
| ABI | Application Binary Interface |
| CA | Certificate Authority |
| TLS | Transport Layer Security |

Apply the same one-term-per-row rule to every §6 acronym. Definition corrections remain a separate review item under N04.

### 4.4 Contract correction example

Before, MANUAL §12.3: “Nothing — it falls back to plain HTTP”.

Proposed replacement: “Obtain the bootstrap kit on a supported machine over authenticated HTTPS and transfer it offline. Authenticate its published digest independently and verify the kit before execution; see STATE-AND-RECOVERY §7. If that trust anchor is unavailable, stop.” Link the authority when applying the change. This is a substantive alignment under C01, not a wording preference.

### 4.5 Dense-prose restructuring example

For DESIGN §12.9, use separate paragraphs or short subheadings for selection precedence, shim execution, extensions, and riding tools. Keep the existing precedence and exceptions verbatim during the structural pass. Move no requirement into an example or a footnote. For the REPOSITORIES capability matrix, retain compact allowed/refused/explicit-grant cells and place the full conditions in adjacent named subsections with links from the cells.

## 5. Offline checker specification — implementation deferred

The checker should take a repository root and tracked Markdown inventory, operate without network access, and emit file, line, rule ID, severity, destination, and suggested action. It should return nonzero for errors, report warnings separately, and produce a machine-readable result alongside readable diagnostics. Use a Markdown parser with source positions and a defined renderer profile; a regex-only implementation cannot reliably distinguish fences, references, HTML, and escaped pipes.

### 5.1 Required rules

1. **Local targets:** resolve links relative to the containing document, including reference-style links and images. Decode URL paths/fragments appropriately; separate queries; ignore external schemes and mail addresses. Check existence with repository case sensitivity even on Windows. Reject accidental repository escapes unless explicitly allowed. A link to a non-Markdown local file needs existence checking but not invented Markdown heading semantics.
2. **Fragments:** build a heading/explicit-anchor index matching the selected renderer, including duplicate-heading suffixes, punctuation, inline code, Unicode, and setext headings. Validate decoded fragments. Detect duplicate explicit anchors and explicit/generated collisions within each document.
3. **Citation labels:** associate each explicit anchor with the following section. Compare active labels such as `DESIGN §12.9` to destination document and section number. Permit unnumbered named sections. Diagnose ranges pointing at a single section, ambiguous owners, and labels disagreeing with target numbers. Do not infer correctness merely because a fragment exists.
4. **Unlinked citations:** find active prose section references outside links and literals. Bare local numbers can be allowed under the house rule if they identify an existing section in the same document; cross-document references must link. Ambiguous or nonexistent local numbers require human resolution, not an automatic target guess.
5. **Structures:** detect unclosed fences, malformed link/reference definitions, table column inconsistencies after parsing escaped pipes, heading-level jumps, and list indentation that changes intended structure. Report missing fence languages and blank-line consistency as style warnings where parsing remains valid. Do not treat all raw HTML as malformed.
6. **Coverage and suppression:** publish counts of checked files, wrappers, ignored original regions, and intentional exceptions. Exceptions have a precise path/region/rule, reason, and owner; avoid blanket exclusion of an entire specification. Stale exceptions are reported. The audit reports themselves contain literal bad examples and must not trigger active-prose findings inside those examples.

### 5.2 Explicit exception model

History is a bounded history section or declared preserved block, not any `<details>` element. Literal code includes fenced/indented code and inline spans, but prose outside it remains checked. For archive records, check the wrapper and Used-by links while excluding the clearly delimited complete-original region and raw source assets from house-style/citation rewriting. Keep provenance URLs as provenance. Man pages use a Pandoc profile preserving title metadata, definition lists, and `name(section)` references; check their actual Markdown links normally.

### 5.3 Required regression cases

| Fixture | Expected result |
|---|---|
| `../MANUAL.md`, same-page `#fragment`, path with spaces and percent encoding | Resolve relative to the source; preserve repository case rules. |
| Reference-style links, collapsed/shortcut references, angle-bracket destinations | Resolve definitions; report missing or conflicting definitions. |
| Heading with punctuation, inline code, Unicode, or repeated text | Match the selected renderer's actual ID and duplicate suffix. |
| Explicit anchor before numbered heading; number later changes | Stable target still resolves; stale numbered label fails. |
| Duplicate explicit ID or collision with a generated heading ID | Fail with both source locations. |
| `a\|b` inside a table cell and code span | Preserve one cell; do not count the escaped pipe as a separator. |
| Multi-section label linked only to the first destination | Fail; separate correctly labeled links pass. |
| Local `§3`, cross-document bare `§12.8`, linked external section | Validate local owner; report ambiguous external reference; accept correct link. |
| Bad references in fenced examples or preserved history; same text in active prose | Exempt the bounded literal/history region; diagnose active prose. |
| Captured upstream relative URL versus wrapper local backlink | Preserve original semantics; check wrapper target normally. |
| Pandoc title block, definition list, and `aslice-install(1)` | Accept under man profile; malformed actual Markdown links still fail. |
| Missing target, nonexistent fragment, case-only filename mismatch | Fail offline with a useful path/line diagnostic. |

External URL availability is outside this gate. So are factual contract reconciliation, compiler/runtime correctness, and proof of security or platform support. A clean checker result cannot close C01–C16 without substantive review.

## 6. Ordered remediation backlog and acceptance

| Order | Work | Completion evidence |
|---|---|---|
| 1 | Resolve P1 owner-backed conflicts C01–C08, C12–C13; record decisions where required | Paired review of owning contract and every affected summary/example; no interface or runtime changes hidden in prose. |
| 2 | Settle C09–C10 and C14–C16 decisions; repair C11 and example completeness | Consistent names, argument order, scope, schemas, and command references; complete examples validated or marked excerpts. |
| 3 | Build a citation destination map; repair N01–N02 and install semantic anchors | All active destinations reviewed individually; old links retained and tested; section ranges split. |
| 4 | Remove current incidental pins; add scoped status metadata and long-document navigation | Historical versions and evidence unchanged; no implementation/operation claims inferred. |
| 5 | Apply N04–N06 layout and prose changes in small reviewable groups | Normative words, gates, exceptions, examples, code, and effective prose preserved; definition corrections separate. |
| 6 | Consider N07 and A01–A02 presentation repairs | History/original bytes and licenses preserved; archive inventory and checksums updated only for intended wrapper changes. |
| 7 | Implement the offline checker against §5 fixtures | Offline positive/negative regression suite; documented renderer and exception behavior; useful failure diagnostics. |

Before accepting future edits, render a representative glossary (NOMENCLATURE §6), dense table (REPOSITORIES §3), long specification (DESIGN, including §12.9 and its navigation), and man page (aslice-use(1) or aslice-service(1)). Inspect table wrapping, searchable terms, code, angle-bracket placeholders, definition lists, link destinations, and heading/anchor behavior. Use the project's intended Markdown renderer and Pandoc/roff path; raw-source inspection alone does not establish rendering.

Require a preservation audit of normative requirements, command/example bytes, historical entries, and captured originals. Run the documentation checker when implemented, existing contract checks for affected examples/schemas, archive verification for any archive change, and `git diff --check`. Review any checksum delta against an intentional file change before regenerating manifests.

## 7. Verification performed and limits

- Existing archive verifier: `python .agents/skills/ref-curator/scripts/refs.py verify --root .` — 32 records, 53 archive files, zero findings. This includes archive governance files in its inventory; it is not a check of external URL availability.
- Existing contract check: `python tests/check_contracts.py` with the installed temporary `jsonschema` dependency — passed; checked 10 JSON schemas, 6 JSON fixtures, 9 TOML documents, Starlark data literals, and its reported 52 archived files. Its archive count differs from the curator's inventory; neither count is the 35 Markdown-document count. TOML schema semantics and runtime security properties explicitly require separate validation.
- Baseline source documents, schemas, histories, archive assets, notices, and checksum manifest were left unchanged. Only the two audit deliverables were added.
- Coverage reconciliation against tracked Markdown found exactly 72 unique checklist entries, with no omissions or extras. Local file links in both deliverables resolve. `git diff --check` passed for tracked files; separate no-index whitespace checks of the two new files reported no whitespace errors.
- No checker was implemented and no live URL/freshness check was attempted. No runtime, macOS, or operational claim was validated.
- Pandoc was unavailable in this environment. Representative rendered review is therefore specified as a required acceptance step for subsequent edits, not claimed complete in this review-only pass.
