"""Regression tests for offline navigation and preservation boundaries."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from check_docs import check, inventory

class DocumentationChecks(unittest.TestCase):
    def test_inventory_ignores_unstaged_deletions(self):
        with tempfile.TemporaryDirectory(prefix='aslice-doc-test-') as tmp:
            root=Path(tmp)
            (root/'kept.md').write_text('# Kept\n',encoding='utf-8')
            with patch('check_docs.subprocess.check_output',return_value='kept.md\ndeleted.md\n'):
                self.assertEqual([root/'kept.md'],inventory(root))

    def run_case(self, files):
        with tempfile.TemporaryDirectory(prefix='aslice-doc-test-') as tmp:
            root=Path(tmp)
            for name,text in files.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
            paths=[root/n for n in files if n.endswith(('.md','.MD'))]
            findings,_=check(root,paths)
            return [f.rule for f in findings if f.severity=='error']

    def test_relative_reference_style_encoded_path(self):
        self.assertEqual([],self.run_case({'docs/a.md':'[target][t]\n\n[t]: <../Target File.md#one>\n','Target File.md':'# One\n'}))

    def test_shortcut_and_collapsed_references(self):
        self.assertEqual([],self.run_case({'a.md':'[one] and [one][]\n\n[one]: b.md#title\n','b.md':'Title\n=====\n'}))

    def test_missing_case_and_fragment(self):
        rules=self.run_case({'a.md':'[x](missing.md) [y](B.md) [z](b.md#no)\n','b.md':'# Title\n'})
        self.assertEqual(2,rules.count('local-file'));self.assertIn('fragment',rules)

    def test_punctuation_code_unicode_and_duplicates(self):
        self.assertEqual([],self.run_case({'a.md':'[a](b.md#café-code_name) [b](b.md#café-code_name-1)\n','b.md':'# Café: `code_name`!\n\n# Café: `code_name`!\n'}))

    def test_semantic_anchor_tracks_number(self):
        rules=self.run_case({'a.md':'[DESIGN §2](DESIGN.md#stable)\n','DESIGN.md':'<a id="stable"></a>\n\n## 3. Changed heading\n'})
        self.assertEqual(['citation-number'],rules)

    def test_duplicate_and_generated_collision(self):
        self.assertIn('duplicate-anchor',self.run_case({'a.md':'<a id="one"></a>\n\n# One\n\n<a id="one"></a>\n'}))

    def test_ranges_and_external_labels(self):
        rules=self.run_case({'a.md':'[DESIGN §1–§2](DESIGN.md#1-one) [§1](DESIGN.md#1-one)\n','DESIGN.md':'# 1. One\n'})
        self.assertIn('citation-range',rules);self.assertIn('citation-label',rules)

    def test_separate_destinations(self):
        self.assertEqual([],self.run_case({'a.md':'[DESIGN §1](DESIGN.md#1-one) and [DESIGN §2](DESIGN.md#2-two)\n','DESIGN.md':'# 1. One\n\n## 2. Two\n'}))

    def test_unlinked_citations_and_local_owner(self):
        rules=self.run_case({'a.md':'# 1. Local\n\n§1 is local. DESIGN §2 is not linked. §8 has no owner.\n'})
        self.assertEqual(['unlinked-citation','citation-owner'],rules)

    def test_history_and_literals(self):
        self.assertEqual([],self.run_case({'a.md':'# One\n\n`DESIGN §99`\n\n```text\n[bad](missing.md)\n```\n\n    DESIGN §99\n\n## History\n\nDESIGN §99 was historical.\n'}))

    def test_archive_wrapper_and_original(self):
        rules=self.run_case({'docs/refs/A.MD':'# Record\n\nSource locator: §99.\n\n[wrapper](missing.md)\n\n## Full captured source\n\n[original](upstream.md)\n'})
        self.assertEqual(['local-file'],rules)

    def test_fence_and_reference_failures(self):
        self.assertIn('fence',self.run_case({'a.md':'```sh\necho ok\n'}))
        self.assertIn('link-syntax',self.run_case({'a.md':'[unresolved][ref]\n'}))

    def test_pandoc_title_and_definition_list(self):
        self.assertEqual([],self.run_case({'man/a.1.md':'% A(1)\n% Authors\n% Date\n\n# FILES\n\n`path/<pkg>`\n:   Definition with aslice-install(1).\n'}))

    def test_escaped_table_pipe(self):
        self.assertEqual([],self.run_case({'a.md':'| A | B |\n|---|---|\n| `a\\|b` | text |\n'}))
        self.assertIn('table-columns',self.run_case({'a.md':'| A | B |\n|---|---|\n| a | b | c |\n'}))

    def test_escape_repository(self):
        self.assertIn('path-escape',self.run_case({'a.md':'[escape](../outside.md)\n'}))

if __name__=='__main__':unittest.main()
