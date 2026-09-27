"""Offline byte preservation and local replay routing."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.library import archive
from tools.library.replay import make_server
from tools.library.rewrite import HtmlRoutes


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.entry = "https://example.test/guide/"
        self.original = (
            b'<link rel="stylesheet" href="https://cdn.test/main.css">'
            b'<a href="/guide/next/">Next</a><img src="/image.svg">'
        )
        self.records = {}
        self.add_record(self.entry, self.original, "text/html", "page")
        self.records[self.entry][
            "effective_url"
        ] = "https://web.archive.org/web/20181119085424id_/https://example.test/guide/start/"
        self.add_record(
            "https://cdn.test/main.css",
            b"body { background: url('/pattern.png'); }",
            "text/css",
            "asset",
        )
        self.add_record(
            "https://example.test/image.svg", b"<svg/>", "image/svg+xml", "asset"
        )
        (self.source / "manifest.json").write_text(
            json.dumps(self.records), encoding="utf-8"
        )
        self.patch = patch.object(archive, "LIBRARY", self.root / "library")
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.directory = archive.import_capture(
            self.source, "test-guide", "Test guide", self.entry
        )

    def add_record(self, url, body, content_type, kind):
        name = hashlib.sha256(url.encode()).hexdigest()
        (self.source / (name + ".body")).write_bytes(body)
        (self.source / (name + ".headers")).write_bytes(b"HTTP/1.1 200 OK\r\n\r\n")
        self.records[url] = {
            "url": url,
            "status": "captured",
            "kind": kind,
            "body": name + ".body",
            "headers": name + ".headers",
            "sha256": hashlib.sha256(body).hexdigest(),
            "content_type": content_type,
            "memento_datetime": "Mon, 19 Nov 2018 08:54:24 GMT",
        }

    def test_replay_maps_origins_and_preserves_source_bytes(self):
        server = make_server(self.directory, 0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            origin = f"http://127.0.0.1:{server.server_port}"
            with urllib.request.urlopen(origin + "/guide/") as response:
                self.assertEqual(response.geturl(), origin + "/guide/start/")
                html = response.read().decode()
                self.assertIn("/__origins/https/cdn.test/main.css", html)
                self.assertIn('href="/guide/next/"', html)
                self.assertIn(
                    "connect-src 'self'", response.headers["Content-Security-Policy"]
                )
            with urllib.request.urlopen(
                origin + "/__origins/https/cdn.test/main.css"
            ) as response:
                self.assertIn(b"/__origins/https/cdn.test/pattern.png", response.read())
            request = urllib.request.Request(
                origin + "/image.svg", headers={"Range": "bytes=1-3"}
            )
            with urllib.request.urlopen(request) as response:
                self.assertEqual(response.status, 206)
                self.assertEqual(response.headers["Content-Range"], "bytes 1-3/6")
                self.assertEqual(response.read(), b"svg")
            with self.assertRaises(urllib.error.HTTPError) as missing:
                urllib.request.urlopen(origin + "/not-captured")
            self.assertEqual(missing.exception.code, 404)
            self.assertIn(b"No live request was made", missing.exception.read())
            missing.exception.close()
            original = self.directory / "originals" / self.records[self.entry]["body"]
            self.assertEqual(original.read_bytes(), self.original)
            archive.verify(self.directory)
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_verify_detects_changed_original_and_extra_file(self):
        original = self.directory / "originals" / self.records[self.entry]["body"]
        original.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            archive.verify(self.directory)
        original.write_bytes(self.original)
        (self.directory / "unexpected.txt").write_text("not indexed")
        with self.assertRaisesRegex(ValueError, "inventory"):
            archive.verify(self.directory)

    def test_browser_exposes_provenance_without_replaying_rejected_responses(self):
        rejected = "https://example.test/rejected/"
        missing = "https://example.test/missing.png"
        self.add_record(rejected, b"Rejected later edition", "text/html", "page")
        self.records[rejected].update(
            status="unavailable",
            http_status=200,
            memento_datetime="Tue, 15 Sep 2020 05:01:42 GMT",
            effective_url="https://web.archive.org/web/20200915050142id_/https://example.test/new/",
        )
        self.add_record(missing, b"Upstream error", "text/html", "asset")
        self.records[missing].update(
            status="unavailable", http_status=404, error="Missing <resource>"
        )
        (self.source / "manifest.json").write_text(
            json.dumps(self.records), encoding="utf-8"
        )
        archive.import_capture(self.source, "test-guide", "Test guide", self.entry)
        server = make_server(self.directory, 0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            origin = f"http://127.0.0.1:{server.server_port}"
            with urllib.request.urlopen(origin + "/__library/") as response:
                index = response.read().decode()
                self.assertIn("1 captured pages; 2 captured assets", index)
                self.assertIn("2 recorded gaps", index)
            with urllib.request.urlopen(origin + "/__library/gaps/") as response:
                gaps = response.read().decode()
                self.assertIn("excluded from this edition", gaps)
                self.assertIn("HTTP 404", gaps)
                self.assertIn("Missing &lt;resource&gt;", gaps)
            for filename in ("manifest.json", "SHA256SUMS"):
                with urllib.request.urlopen(
                    origin + "/__library/" + filename
                ) as response:
                    self.assertEqual(
                        response.read(), (self.directory / filename).read_bytes()
                    )
            with self.assertRaises(urllib.error.HTTPError) as failure:
                urllib.request.urlopen(origin + "/rejected/")
            self.assertEqual(failure.exception.code, 404)
            body = failure.exception.read().decode()
            failure.exception.close()
            self.assertIn("excluded from this edition", body)
            self.assertIn("Tue, 15 Sep 2020", body)
            self.assertNotIn("Rejected later edition", body)
            archive.verify(self.directory)
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_collection_name_cannot_escape_library(self):
        with self.assertRaises(ValueError):
            archive.collection("../outside")

    def test_markup_routing_preserves_examples_and_other_attributes(self):
        example = '<pre>&lt;a href="https://example.test/"&gt;</pre>'
        script = "<script>var example = 'src=\"/example.png\"';</script>"
        title = "<span title='Example href=\"https://example.test/\"'>Text</span>"
        markup = (
            example + "\n" + script + "\n" + title + "\n"
            '<img src = "/image.png?a=1&amp;b=2">'
            '<style>body { background: url("/pattern.png"); }</style>'
        )
        result = HtmlRoutes(markup, lambda value: "/local" + value).rewritten()
        self.assertIn(example, result)
        self.assertIn(script, result)
        self.assertIn(title, result)
        self.assertIn('src = "/local/image.png?a=1&amp;b=2"', result)
        self.assertIn('url("/local/pattern.png")', result)

    def test_import_preserves_an_existing_source_revision(self):
        self.add_record(self.entry, b"a different edition", "text/html", "page")
        (self.source / "manifest.json").write_text(
            json.dumps(self.records), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "new collection"):
            archive.import_capture(self.source, "test-guide", "Test guide", self.entry)
        archive.verify(self.directory)


if __name__ == "__main__":
    unittest.main()
