"""Check active-content removal without changing document examples or SVG geometry."""

import unittest
from bs4 import BeautifulSoup
from tools.pages.build import clean_html, clean_svg, prepare_diagrams


class ExportTests(unittest.TestCase):
    def test_diagrams_keep_source_and_use_relative_assets(self):
        soup = BeautifulSoup(
            '<h2>Data flow</h2><pre><code class="language-mermaid">'
            'graph LR\n A[&lt;owner&gt;] --&gt; B\n</code></pre>'
            '<pre><code class="language-python">print(1)</code></pre>',
            "html.parser",
        )
        original = soup.code.get_text()
        diagrams = {}
        prepare_diagrams(soup, "docs/nested/example.html", diagrams)
        self.assertEqual(list(diagrams.values()), [original])
        self.assertEqual(soup.details.code.get_text(), original)
        self.assertEqual(soup.summary.get_text(), "Diagram source")
        self.assertEqual(soup.select_one(".diagram-viewport")["tabindex"], "0")
        for image in soup.find_all("img"):
            self.assertTrue(image["src"].startswith("../../assets/diagrams/"))
            self.assertEqual(image["alt"], "Diagram 1: Data flow")
        self.assertEqual(soup.select_one("code.language-python").get_text(), "print(1)")

    def test_html_removes_active_content_and_routes_resources(self):
        source = """<html><head><base href="https://example.com/">
        <meta http-equiv="refresh" content="0;url=https://example.com">
        <script>window.executed=true</script></head><body onload="alert(1)">
        <iframe srcdoc="active"></iframe><object data="remote"></object>
        <form action="remote"><input></form><img src=picture.png onerror=alert(1)>
        <a href="page.html" ping="remote" target="_top">Read</a>
        <pre>https://example.com/code-example</pre></body></html>"""
        html = clean_html(source, lambda value: "local/" + value)
        soup = BeautifulSoup(html, "html.parser")
        self.assertFalse(soup.find(["script", "base", "iframe", "object", "form"]))
        self.assertFalse(soup.find("meta", attrs={"http-equiv": "refresh"}))
        self.assertEqual(soup.img["src"], "local/picture.png")
        self.assertNotIn("onerror", soup.img.attrs)
        self.assertNotIn("onload", soup.body.attrs)
        self.assertNotIn("target", soup.a.attrs)
        self.assertNotIn("ping", soup.a.attrs)
        self.assertIn("script-src 'none'", soup.head.meta["content"])
        self.assertEqual(soup.pre.text, "https://example.com/code-example")

    def test_svg_keeps_case_sensitive_geometry(self):
        body = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">
        <script>alert(1)</script><foreignObject><div>active</div></foreignObject>
        <path onload="alert(1)" d="M0 0 L40 40"/></svg>"""
        result = clean_svg(body, lambda value: value).decode()
        self.assertIn('viewBox="0 0 40 40"', result)
        self.assertNotIn("script", result)
        self.assertNotIn("foreignObject", result)
        self.assertNotIn("onload", result)
        self.assertIn("M0 0 L40 40", result)
