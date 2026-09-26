# Archive checks

`scripts/refs.py` uses Python's standard library and Git. It locates the repo from
its installed location; `--root` selects another checkout or fixture. Both commands
operate on flat `docs/refs`. Unexpected subdirectories or symlinks fail explicitly.

`verify` is offline and read-only. It checks manifest coverage/bytes, one catalog
entry per record, the seven subjects and alphabetical order within them, inventory
coverage, local links/anchors, asset references, unreferenced assets, and effective
Git `text=unset` attributes. Exit zero means these checks passed; findings return
one, and invocation or I/O/tool failures return two.

Records are Markdown files other than README, TEMPLATE, and SOURCE-INVENTORY.
Project wrappers end at `## Full captured source`. Embedded originals and source
assets are not project Markdown. The parser supports inline and reference-style
links, fenced/inline code exclusion, percent-encoded paths, and GitHub-style heading
fragments with duplicate suffixes. Unsupported HTML links, setext headings in
anchor targets, and unsupported link syntax produce diagnostics; review or extend
the parser instead of suppressing findings to obtain a green result.

Subject choice and rights sufficiency need substantive review. The checker does
not verify quotations, external source locators, attribution, discussion completeness,
embedded-source equivalence, or factual support. Template headings alone do not
establish complete content. Follow the evidence workflow for these checks.

`refresh-checksums` writes only SHA256SUMS, sorted by filename, using actual-byte
SHA-256, two spaces before filenames, and LF terminators. It includes all archive
files except itself. It does not retrieve, repair, or stage anything. Investigate
initial mismatches and review intended changes first; never bless an unexplained
mismatch through regeneration. Run verify afterward.

The effective Git attributes must preserve archive bytes. The `docs/refs/** -text`
rule must follow general extension rules. Do not normalize originals to fix an
attribute failure. Hashes establish manifest consistency, not authenticity.

Run focused tests against disposable fixtures:

```text
python -m unittest discover -s "<skill-dir>/scripts" -p "test_refs.py"
```
