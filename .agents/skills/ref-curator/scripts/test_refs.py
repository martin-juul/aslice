"""Behavior tests using disposable repositories, never the real archive."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
import refs


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ref-curator-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.archive = self.root / "docs/refs"
        self.archive.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        (self.root / ".gitattributes").write_text("*.txt text\ndocs/refs/** -text\n", encoding="utf-8")
        (self.root / "docs/Guide (old).md").write_text(
            "# Guide\n\n## Claim\n\n## Claim\n\n## Claim-1\n", encoding="utf-8")
        self.write("TEMPLATE.MD", "# Template\n")
        self.write("A.MD", "# Alpha\n\n"
                   "[Claim](../Guide%20%28old%29.md#claim-1)\n"
                   "[Original](A.source.txt) [Notice](LICENSE.txt)\n")
        self.write("A.source.txt", "Original source bytes.\r\n")
        self.write("LICENSE.txt", "Fixture copying notice.\n")
        self.catalog = "# Archive\n\n## Catalog\n\n"
        for i, subject in enumerate(refs.SUBJECTS):
            self.catalog += f"### {subject}\n\n"
            if i == 0:
                self.catalog += "- [Alpha](A.MD) — fixture evidence.\n\n"
        self.write("README.MD", self.catalog)
        self.write("SOURCE-INVENTORY.MD",
                   "# Inventory\n\n## Catalog coverage\n\n"
                   "| Record | Coverage | Gap |\n|---|---|---|\n"
                   "| [Alpha](A.MD) | Complete fixture source | None |\n")
        refs.refresh(self.root)

    def write(self, name, text):
        (self.archive / name).write_bytes(text.encode("utf-8"))

    def append(self, name, text):
        self.write(name, (self.archive / name).read_text(encoding="utf-8") + text)

    def findings(self):
        return refs.verify(self.root)[0]

    def assertFinding(self, substring):
        self.assertTrue(any(substring in finding for finding in self.findings()),
                        f"Expected {substring!r} in {self.findings()}")

    def snapshot(self):
        return {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.archive.iterdir() if p.is_file()}

    def test_explicit_anchor_and_full_source_navigation(self):
        guide = self.root / "docs/Guide (old).md"
        guide.write_text('<a id="stable"></a>\n\n## 2. Current heading\n', encoding="utf-8")
        self.write("A.MD", '# Record\n\n[Section](../Guide%20%28old%29.md#stable)\n'
                   '[Original](A.source.txt) [Notice](LICENSE.txt)\n'
                   '[Full](#full-captured-source)\n\n## Full captured source\n'
                   '[upstream](not-local.md)\n')
        refs.refresh(self.root)
        self.assertEqual(self.findings(), [])

    def test_verify_is_read_only(self):
        before = self.snapshot()
        self.assertEqual(self.findings(), [])
        self.assertEqual(before, self.snapshot())

    def test_refresh_is_deterministic_and_only_writes_manifest(self):
        self.append("A.MD", "\nExpanded context.\n")
        before = self.snapshot()
        refs.refresh(self.root)
        first = (self.archive / "SHA256SUMS").read_bytes()
        after = self.snapshot()
        self.assertEqual({k: v for k, v in before.items() if k != "SHA256SUMS"},
                         {k: v for k, v in after.items() if k != "SHA256SUMS"})
        refs.refresh(self.root)
        self.assertEqual(first, (self.archive / "SHA256SUMS").read_bytes())
        self.assertNotIn(b"\r", first)
        self.assertEqual(self.findings(), [])

    def test_mismatch_is_not_repaired_by_verify(self):
        self.write("A.source.txt", "Changed.\n")
        before = self.snapshot()
        self.assertFinding("checksum mismatch")
        self.assertEqual(before, self.snapshot())

    def test_missing_asset_and_manifest_entry(self):
        (self.archive / "A.source.txt").unlink()
        self.assertFinding("unexpected entry A.source.txt")
        self.assertFinding("missing link target: A.source.txt")

    def test_manifest_duplicate_malformed_and_unlisted(self):
        first = (self.archive / "SHA256SUMS").read_text().splitlines()[0]
        self.append("SHA256SUMS", first + "\ninvalid\n")
        self.write("NEW.txt", "new asset")
        self.assertFinding("duplicate entry")
        self.assertFinding("malformed entry")
        self.assertFinding("missing entry NEW.txt")
        self.assertFinding("Asset not linked from a record: NEW.txt")

    def test_catalog_missing_duplicate_and_unknown(self):
        for replacement, finding in [
            ("", "A.MD has 0 primary entries"),
            ("- [Alpha](A.MD)\n- [Alpha](A.MD)", "A.MD has 2 primary entries"),
            ("- [Gone](GONE.MD)", "invalid primary catalog entry"),
        ]:
            with self.subTest(finding=finding):
                self.write("README.MD", self.catalog.replace(
                    "- [Alpha](A.MD) — fixture evidence.", replacement))
                self.assertFinding(finding)

    def test_catalog_order_and_subjects(self):
        self.write("B.MD", "# Beta\n")
        self.write("README.MD", self.catalog.replace(
            "- [Alpha](A.MD)", "- [Beta](B.MD)\n- [Alpha](A.MD)"))
        self.assertFinding("entries out of order")
        self.write("README.MD", self.catalog.replace(refs.SUBJECTS[0], "Other"))
        self.assertFinding("subject headings/order")

    def test_inventory_coverage(self):
        self.write("SOURCE-INVENTORY.MD", "# Inventory\n")
        self.assertFinding("Inventory: A.MD has 0 coverage entries")

    def test_broken_anchor_and_outside_link(self):
        self.append("A.MD", "\n[Broken](../Guide%20%28old%29.md#absent)\n"
                    "[Outside](../../../outside.md)\n")
        self.assertFinding("missing anchor")
        self.assertFinding("link outside repository")

    def test_code_and_embedded_original_excluded(self):
        self.append("A.MD", "\n\x60[Not a link](absent.md)\x60\n\n"
                    "~~~md\n[Example](missing.md)\n~~~\n\n"
                    "## Full captured source\n\n[Upstream](upstream.md)\n")
        refs.refresh(self.root)
        self.assertEqual(self.findings(), [])

    def test_reference_links_escaped_paths_and_duplicate_headings(self):
        self.append("A.MD", "\n[One][guide] [guide][] [guide]\n"
                    '[guide]: <../Guide (old).md#claim-1-1> "Guide"\n'
                    "[Escaped](../Guide%20\\(old\\).md#claim)\n")
        refs.refresh(self.root)
        self.assertEqual(self.findings(), [])

    def test_unsupported_and_undefined_syntax_is_reported(self):
        self.append("A.MD", '\n<a href="missing.md">HTML</a>\n'
                    "[Nested [label]](missing.md)\n"
                    "[Unknown][undefined]\n")
        self.assertFinding("unsupported HTML")
        self.assertFinding("unsupported or malformed link")
        self.assertFinding("undefined reference link")

    def test_setext_heading_in_target_requires_review(self):
        (self.root / "docs/Guide (old).md").write_text(
            "Guide\n=====\n", encoding="utf-8")
        self.assertFinding("unsupported setext heading")

    def test_effective_attribute_override_detected(self):
        (self.root / ".gitattributes").write_text(
            "docs/refs/** -text\n*.txt text\n", encoding="utf-8")
        self.assertFinding("effective text attribute is 'set'")

    def test_newline_conversion_detected(self):
        original = (self.archive / "A.source.txt").read_bytes()
        self.assertIn(b"\r\n", original)
        (self.archive / "A.source.txt").write_bytes(original.replace(b"\r\n", b"\n"))
        self.assertFinding("checksum mismatch: A.source.txt")

    def test_inventory_cross_links_do_not_duplicate_coverage(self):
        self.append("SOURCE-INVENTORY.MD",
                    "\n## Other notes\n\n[A](A.MD)\n")
        data = (self.archive / "SOURCE-INVENTORY.MD").read_text(encoding="utf-8")
        self.write("SOURCE-INVENTORY.MD", data.replace("| None |", "| See [Alpha](A.MD) |"))
        refs.refresh(self.root)
        self.assertEqual(self.findings(), [])

    def test_heading_emphasis_and_literal_code(self):
        (self.root / "docs/Guide (old).md").write_text(
            "# Guide\n\n## _Claim_\n\n## Claim\n\n## \x60_name_\x60\n", encoding="utf-8")
        self.append("A.MD", "\n[Literal](../Guide%20%28old%29.md#_name_)\n")
        refs.refresh(self.root)
        self.assertEqual(self.findings(), [])

    def test_manifest_uses_filename_sort_order(self):
        self.write("a.source.txt", "lowercase")
        self.write("Z.source.txt", "uppercase")
        refs.refresh(self.root)
        names = [line.split("  ", 1)[1]
                 for line in (self.archive / "SHA256SUMS").read_text().splitlines()]
        self.assertEqual(names, sorted(names))

    def test_new_record_and_historical_revision(self):
        original = (self.archive / "A.source.txt").read_bytes()
        self.write("A-2026.source.txt", "New edition, separate from original.\n")
        self.append("A.MD", "\n[New edition](A-2026.source.txt); original retained.\n")
        self.write("B.MD", "# Beta\n\nSource: https://example.invalid/discussion\n\n"
                   "Retrieval failed; visible earlier replies are only reported experience.\n"
                   "Exact reply dates and collapsed replies remain evidence gaps.\n")
        self.write("README.MD", self.catalog.replace(
            "- [Alpha](A.MD) — fixture evidence.",
            "- [Alpha](A.MD) — fixture evidence.\n- [Beta](B.MD) — partial discussion."))
        self.append("SOURCE-INVENTORY.MD",
                    "| [Beta](B.MD) | Partial | Missing replies; retrieval failed |\n")
        refs.refresh(self.root)
        self.assertEqual(self.findings(), [])
        self.assertEqual(original, (self.archive / "A.source.txt").read_bytes())
        # Mechanical success deliberately says nothing about completeness of Beta.

    def test_nested_archive_rejected_without_manifest_write(self):
        before = (self.archive / "SHA256SUMS").read_bytes()
        (self.archive / "nested").mkdir()
        with self.assertRaisesRegex(ValueError, "Unsupported archive entry"):
            refs.refresh(self.root)
        self.assertEqual(before, (self.archive / "SHA256SUMS").read_bytes())

    def test_cli_from_other_directory_and_exit_status(self):
        script = str(Path(refs.__file__).resolve())
        command = [sys.executable, "-B", script, "verify", "--root", str(self.root)]
        good = subprocess.run(command, cwd=self.root.parent, capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        self.append("A.MD", "unreviewed change")
        bad = subprocess.run(command, cwd=self.root.parent, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
        failed = subprocess.run(command[:-1] + [str(self.root / "absent")],
                                capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)


if __name__ == "__main__":
    unittest.main()
