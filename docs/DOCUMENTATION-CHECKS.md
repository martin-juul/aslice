# Documentation checks and house conventions

- **Status:** Offline tooling implemented; runtime specifications remain unimplemented.
- **Audience:** Documentation authors and reviewers.
- **Authority:** This page defines documentation validation. It does not override package, trust, or recovery contracts.

## Writing and navigation

Use a status/audience/authority block where it helps readers distinguish specification, implementation, platform testing, and operation. Keep charter language and the force of requirements. Guides explain mechanisms; runbooks give precise prerequisites and steps; specifications state contracts and their owners.

Use tables for compact comparisons and mappings. Put extended conditions in adjacent paragraphs or subsections. Keep numbered headings and existing destinations. Long documents with at least ten second-level headings have compact navigation. Cited sections have explicit semantic anchors, placed immediately before their unchanged headings. Do not derive explicit IDs from section numbers; retain published IDs when wording changes.

Active cross-document citations name and link their document and section. Same-document bare section citations must resolve locally. Link each destination separately; a range cannot point only to its first section. Reference-style links are supported. Histories and literal examples retain their original citations. Archive wrappers are project prose, but their bare source-section locators describe the captured edition, not local headings. Original captures and source assets retain upstream links and source bytes.

Separate headings, paragraphs, lists, fences, and tables with blank lines. Label command fences `sh`, transcripts `console`, data by its language, and trees or pseudocode `text`. Preserve command bytes except for explicitly approved contract corrections. Escape table pipes. Man pages retain Pandoc title blocks, definition lists, and `name(section)` cross-references; quote or escape angle-bracket placeholders so they render visibly.

## Offline gate

Install `tests/requirements.txt`, then run:

```sh
python tests/check_docs.py
python -m unittest discover -s tests -p test_docs.py
python tests/check_contracts.py
python .agents/skills/ref-curator/scripts/refs.py verify --root .
git diff --check
```

`check_docs.py --json` emits machine-readable findings. Errors fail the gate; style warnings remain visible. The parser uses CommonMark plus GFM tables and Pandoc-style definition lists. Generated heading IDs follow the documented GitHub-style slug algorithm; explicit anchors and duplicate heading suffixes are indexed too. Local targets are checked with exact case even on Windows. Links outside the repository, missing files/fragments, duplicate IDs, citation-label disagreements, unlinked cross-document citations, unresolved reference-style links, and unclosed fences are errors.

The checker does not contact external URLs, execute commands, validate factual claims, or prove that a rendering looks good. It cannot infer a writer's intended list nesting from valid Markdown. Review list layout and paragraph/table readability in rendered output. A clean parse is not proof of a correct contract.

## Bounded preservation exceptions

The checker retains link checks but exempts citation modernization inside History sections, HOMEBREW-REVIEW's section 8 preserved proposals, REPOSITORIES' section 9 historical amendment record, and the dated DOCUMENTATION-AUDIT reports. These are named historical evidence, not active instructions. Fenced/indented code and inline literals are not prose. Archive originals begin at the Full captured source heading; wrappers remain checked. Bare archive source-section numbers refer to the identified original edition. These exceptions are implemented explicitly in the checker; new exceptions need a documented reason and a focused regression case.

## Rendered and preservation review

Before accepting structural changes, render NOMENCLATURE's glossary, REPOSITORIES' capability table, DESIGN's navigation/runtime explanation, and a man page such as aslice-use(1). Inspect wrapping, literal placeholders, heading destinations, tables, and definition lists. Use both the web Markdown profile and Pandoc's man output where applicable.

Compare edited files against a working-file baseline, including histories, normative language, code examples, and source assets. Review content preservation and explain intentional differences. Archive wrapper changes require inspection before checksum regeneration; compare original captures and notices byte-for-byte. Never refresh checksums merely to hide an unexplained mismatch.
