# Requirement review metadata

`registry.json` version 2 is a partial review of the current contracts, not a completion
claim. Records have stable IDs, an owning contract, reviewed source ranges,
implementation paths, platform dependencies, required environments, four kinds
of test scenarios, and evidence links. Empty implementation and evidence lists
mean work remains. Existing bounded simulator mappings are retained separately
in `bounded_scenarios`; they do not satisfy production requirements.

Source discovery includes specifications, manuals, schemas, runbooks, and the
reference archive. It uses no normative keywords. Every nonblank source line
without a reviewed requirement or a reasoned context/history classification
remains unreviewed. Genesis's current procedures remain in scope; only its
explicit history section has been excluded.
The helper contract, Genesis, and service, database and recovery manuals have complete line classification. Their
requirements remain unimplemented and lack acceptance evidence. The helper
document's explicitly deferred multi-user daemon is classified as future context;
current per-operation helpers and persistent package services remain requirements.

Source SHA-256 values normalize CRLF to LF except in `docs/refs`, whose bytes are
preserved. Adding, deleting, or changing a source invalidates the development
gate. Each requirement separately binds its clause sources and owning contract in
`reviewed_sources`; each context/history classification binds its own source hash.
Refreshing the inventory never refreshes those review decisions. Review the
changed text and every dependent record before updating their hashes. Invalidated
clauses return to the unreviewed ranges even when the inventory itself is current.
There is deliberately no automatic command to approve changed source hashes.
New records must follow documented contract ownership. Record contradictions
under `specification_defects` with an ID, contract links, and a description;
unresolved defects block release acceptance.
Defect IDs must be unique (for example, `CONFLICT-1`), descriptions nonempty, and
contract links must resolve to inventoried files and existing section anchors.
Unknown fields, including a self-declared resolution flag, invalidate metadata.
Resolve a defect by reviewing the corrected contracts and removing the blocking
record; a status flag cannot override contradictory requirements.

Run the metadata validator during development:

```sh
python -m tools.simulator coverage --gate development --output build/coverage-development.json
python -m unittest discover -s tests -p test_requirements.py
```

The default `coverage` gate is release acceptance and fails while requirements,
command contracts, or physical qualification remain incomplete. Development
validity only checks inventory consistency; it never means release readiness.
Command family tables in `man/README.md` and `man/aslice.1.md` must agree.
Every manual synopsis paragraph is inventoried intact, including multiline
syntax and selectors between command words. Each command has explicit synopsis
bindings pinned to both the paragraph and complete manual, plus covering reviewed
requirements. The root invocation is a separately reviewed global contract.
Cross-family references, such as database recovery, require an explicit reason
and a covering requirement owned by the canonical command family.

All current manual synopsis blocks are mapped. This establishes syntax inventory,
not implementation or complete behavioral review. Generic option groups,
permitted option combinations, effects, authority, output and exit contracts still
need their owning requirements. The DESIGN syntax index and most manual bodies
retain unreviewed ranges. The overloaded `pin` spelling keeps separate package-hold
and runtime-stream synopsis bindings.

`run --suite full --native-evidence PATH` accepts a version 1 JSON bundle with a
`receipts` array. Each receipt identifies physical qualification, machine, OS
build, filesystem, security settings, configuration, executable and source
SHA-256 values, authority, and signature. Input is bounded and checked before
launch. Receipt ingestion currently grants **no qualification credit**: a
configured authority verifier and freshness/build matching are still missing.
Supplied signatures and claims alone cannot pass acceptance. Simulated receipts
are refused as native evidence.

Reports keep `implemented`, `tested`, and `operational` separate. Test references
are planned scenarios; they are not passing execution evidence. Evidence links
currently remain unverified. Generated reports belong under ignored `build/`
output, not in `docs/` or in this metadata directory.
