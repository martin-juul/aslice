---
name: ref-curator
description: Create, update, verify, and maintain aslice's offline reference archive in docs/refs. Use for source capture, citation and evidence review, historical revisions, catalog and inventory maintenance, link repair, licenses, assets, and checksums. Not for Git refs or ordinary bibliography formatting outside this archive.
---

# Reference Curator

Make each supported decision understandable and assessable offline. Read
`docs/refs/TEMPLATE.MD` for the content contract, `docs/refs/README.MD` for the catalog,
and `docs/refs/SOURCE-INVENTORY.MD` for coverage and unresolved evidence. Read affected
records and citing project sections. Do not freeze current counts or duplicate the
template in this skill.

## Select the operation

| Request | Action |
|---|---|
| Verify, audit, review | Read-only review. Separate offline integrity/completeness from online source comparison; disclose unavailable checks. |
| Create, capture, add | Search for duplicates. Retrieve the source, write from the template, add permitted assets, and reconcile catalog, inventory, and checksums. |
| Update, refresh, expand | Compare with the archived edition and citing claims. Preserve relied-upon history; record changes, provenance, and remaining gaps. |
| Repair, organize, maintain | Reconcile links, assets, notices, catalog, and inventory within scope. Identify uncaptured evidence and unused records without treating every example URL as a dependency. |
| Supersede, consolidate, retire | Trace incoming citations and preserve historical evidence and stable filenames. Record successors; being uncited is not sufficient reason to delete a record. |

For substantive review or capture, read [the evidence workflow](references/evidence-workflow.md).
For tools and maintenance, read [archive checks](references/archive-checks.md).
An unqualified request to verify refs includes the whole archive and comparison
with available original sources. Explicitly offline review uses local material
only. Named records limit substantive review to those records; the mechanical
checker still checks archive-wide consistency.

## Preserve evidence and scope

Inspect repository instructions and working-tree changes. Before editing, save
affected working files outside the tracked tree as a baseline. Preserve user edits,
original asset bytes, source notices, filenames, and relied-upon revisions. Report
contradictions with exact locators; do not silently replace historical evidence
with current guidance or change project decisions.

Retain full originals only when redistribution permits. Otherwise write attributed
accounts of relevant facts, permitted quotations, and explicit omissions. Public
availability and technical subject matter do not grant copying permission. Keep
license metadata concise while retaining required notices.

Creation and update include necessary local catalog, inventory, and checksum work.
Verification remains read-only. Commit, push, publication, and remote edits follow
the active task's authorization, not the presence of this skill.

## Finish

Run the checker before edits to establish existing failures. After reviewing
intended changes, refresh checksums explicitly and verify again:

```text
python "<skill-dir>/scripts/refs.py" verify --root "<repo-root>"
python "<skill-dir>/scripts/refs.py" refresh-checksums --root "<repo-root>"
python "<skill-dir>/scripts/refs.py" verify --root "<repo-root>"
```

Use the available Python interpreter. Investigate unexpected checksum mismatches
before refreshing; regeneration is not evidence repair. Run
`python tests/check_contracts.py` from the repo root with its documented dependencies,
then `git diff --check`. For rewritten reference prose, compare against the working-file baseline. Account for intentional
evidence additions rather than claiming semantic equivalence. Check quotations,
notices, and original bytes directly.

Report what was reviewed or changed, source-comparison and offline results
separately, checks run, and unresolved gaps or decision conflicts. Mechanical
success does not establish source accuracy, copying rights, or runtime behavior.
