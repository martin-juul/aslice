"""Build the Pages portal without changing source documents or archive bytes."""

import hashlib
import json
import mimetypes
import os
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from html import escape
from urllib.parse import quote, unquote, urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup
import markdown

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/pages"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "docs/library/.harness"))
from backend.archive import verify
from backend.replay import Replay
from backend.rewrite import rewrite_css
from backend.catalog import gap_reason, provenance

REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "martin-juul/aslice")
SOURCE = f"https://github.com/{REPOSITORY}/blob/master/"
POLICY = "default-src 'self' data:; script-src 'none'; connect-src 'none'; object-src 'none'; frame-src 'none'; style-src 'self' 'unsafe-inline'; base-uri 'none'; form-action 'none'"


def write(path, text):
    target = OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def relative(target, page):
    return quote(posixpath.relpath(target, posixpath.dirname(page) or "."), safe="/#")


def shell(page, title, content, reader=False):
    links = [
        ("index.html", "aslice"),
        ("docs/README.html", "Documentation"),
        ("man/README.html", "Commands"),
        ("library/index.html", "Library"),
        ("simulator/index.html", "Simulator"),
    ]
    nav = "".join(
        f'<a href="{relative(path, page)}">{label}</a>' for path, label in links
    )
    css = relative("assets/style.css", page)
    js = relative("assets/portal.js", page)
    policy = "default-src 'self' data:; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{policy}">
<title>{escape(title)} · aslice</title><link rel="stylesheet" href="{css}">
<script defer src="{js}"></script></head><body><a class="skip" href="#main">Skip to content</a>
<header class="toolbar"><nav aria-label="Main navigation">{nav}</nav>
<button id="appearance" aria-pressed="false">Dark appearance</button></header>
<main id="main" tabindex="-1" class="{'reader' if reader else 'article'}">{content}</main>
<footer>aslice is in the design phase. Specifications describe intended behavior; platform validation remains outstanding.</footer></body></html>"""


def clean_html(text, resolve):
    """Defense in depth for direct resource visits as well as sandboxed reading."""
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup.find_all(["script", "base", "iframe", "object", "embed", "form"]):
        tag.decompose()
    for tag in soup.find_all("meta"):
        if tag.get("http-equiv", "").lower() in ("refresh", "content-security-policy"):
            tag.decompose()
    for tag in soup.find_all(True):
        for name in list(tag.attrs):
            if name.lower().startswith("on") or name in ("srcdoc", "target", "ping"):
                del tag[name]
            elif name in (
                "href",
                "src",
                "poster",
                "xlink:href",
                "background",
                "action",
            ):
                tag[name] = resolve(str(tag[name]))
            elif name == "srcset":
                tag[name] = ", ".join(
                    " ".join([resolve(p[0])] + p[1:])
                    for p in (s.strip().split() for s in tag[name].split(","))
                    if p
                )
            elif name == "style":
                tag[name] = rewrite_css(tag[name], resolve)
        if tag.name == "style" and tag.string:
            tag.string.replace_with(rewrite_css(str(tag.string), resolve))
    if soup.head is None:
        head = soup.new_tag("head")
        soup.insert(0, head)
    policy = soup.new_tag("meta")
    policy["http-equiv"] = "Content-Security-Policy"
    policy["content"] = POLICY
    soup.head.insert(0, policy)
    return str(soup)


def clean_svg(body, resolve):
    root = ET.fromstring(body)
    for parent in root.iter():
        for child in list(parent):
            if child.tag.split("}")[-1] in ("script", "foreignObject"):
                parent.remove(child)
        for name in list(parent.attrib):
            local = name.split("}")[-1]
            if local.startswith("on"):
                del parent.attrib[name]
            elif local in ("href", "src"):
                parent.attrib[name] = resolve(parent.attrib[name])
            elif local == "style":
                parent.attrib[name] = rewrite_css(parent.attrib[name], resolve)
        if parent.tag.split("}")[-1] == "style" and parent.text:
            parent.text = rewrite_css(parent.text, resolve)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def export_collection(directory):
    count = verify(directory)
    replay = Replay(directory)
    base = "library/" + directory.name
    resources = {}
    pending = {}
    extensions = {
        "text/html": ".html",
        "text/css": ".css",
        "image/svg+xml": ".svg",
        "application/javascript": ".js",
        "text/javascript": ".js",
    }

    def route(url):
        key = urldefrag(url)[0]
        if key not in resources:
            entry = replay.resources.get(key)
            mime = entry.get("content_type", "").split(";")[0] if entry else ""
            ext = (
                (extensions.get(mime) or mimetypes.guess_extension(mime) or ".bin")
                if entry and entry["status"] == "captured"
                else ".html"
            )
            resources[key] = hashlib.sha256(key.encode()).hexdigest() + ext
            pending[key] = entry
        return resources[key]

    def resolve(value, source):
        if value.startswith("#"):
            return value
        target = urljoin(source, value)
        parsed = urlsplit(target)
        if parsed.scheme == "data":
            return value
        if parsed.scheme not in ("http", "https"):
            return "#"
        key, fragment = urldefrag(target)
        return route(key) + (("#" + fragment) if fragment else "")

    for url in replay.resources:
        route(url)
    sections = {}
    gaps = []
    processed = set()
    while pending:
        url, entry = pending.popitem()
        if url in processed:
            continue
        processed.add(url)
        destination = base + "/resources/" + resources[url]
        if not entry or entry["status"] != "captured":
            content = f"<h1>Not available in this capture</h1><p>{escape(url)}</p><p>{escape(gap_reason(entry))}</p>"
            if entry:
                content += provenance(entry)
                gaps.append(
                    f'<li><a href="resources/{resources[url]}">{escape(url)}</a>: {escape(gap_reason(entry))}</li>'
                )
            write(
                destination,
                clean_html(
                    "<html><head><title>Capture gap</title></head><body>"
                    + content
                    + "<p>No live request was made.</p></body></html>",
                    lambda v: v,
                ),
            )
            continue
        body = (directory / "originals" / entry["body"]).read_bytes()
        mime = entry["content_type"]
        if "svg" in mime:
            body = clean_svg(body, lambda v: resolve(v, replay.resolved_url(entry)))
        elif "html" in mime:
            text = body.decode("utf-8")
            if "html" in mime and entry["kind"] == "page":
                soup = BeautifulSoup(text, "html.parser")
                title = (
                    soup.title.get_text().strip().split(" - macOS -")[0]
                    if soup.title
                    else urlsplit(url).path
                )
                sections.setdefault(entry["body"], (title, resources[entry["url"]]))
            body = clean_html(
                text, lambda v: resolve(v, replay.resolved_url(entry))
            ).encode()
        elif "css" in mime:
            body = rewrite_css(
                body.decode("utf-8"), lambda v: resolve(v, replay.resolved_url(entry))
            ).encode()
        elif "javascript" in mime:
            body = b"/* Archived scripts are disabled in the static reader. */"
        target = OUT / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)

    rows = "".join(
        f'<li data-search><a href="#{name}">{escape(title)}</a></li>'
        for title, name in sorted(sections.values())
    )
    title = replay.metadata["title"]
    entry = resources[replay.metadata["entry_url"]]
    content = f"""<aside class="contents"><h2>Contents</h2><label for="filter">Find a section</label><input id="filter" type="search"><ul>{rows}</ul></aside>
<section class="document" aria-label="Archived documentation"><p><strong>{escape(title)}</strong><br>
<a href="information.html">Capture information and gaps</a> · Scripts disabled. Original page colors preserved.</p>
<iframe id="capture" title="Archived documentation" sandbox="allow-same-origin" src="resources/{entry}"></iframe></section>"""
    write(base + "/index.html", shell(base + "/index.html", title, content, True))
    raw = "../../docs/library/" + directory.name + "/"
    info = f'<h1>{escape(title)}</h1><p>{count} preserved files verified before export. {len(set(sections))} captured section routes.</p><p><a href="index.html">Open reader</a></p><p>URL changes and script removal apply only to generated output. The local replay retains its existing behavior. Historical dates vary by resource; missing resources remain gaps.</p>'
    for name in ("capture.json", "manifest.json", "SHA256SUMS"):
        info += f'<p><a href="{raw}{name}">{name}</a></p>'
    info += '<p><a href="../../docs/refs/README.html">Reference catalog and source records</a></p>'
    info += "<h2>Recorded gaps</h2><ul>" + "".join(sorted(gaps)) + "</ul>"
    write(
        base + "/information.html",
        shell(base + "/information.html", "Capture information", info),
    )
    return f'<a class="card" href="{directory.name}/index.html"><h2>{escape(title)}</h2><p>{len(set(sections))} sections · {len(gaps)} recorded gap routes</p></a>'


def main():
    # Only this fixed generated directory is ever removed.
    if OUT.exists():
        if OUT.resolve() != ROOT / "build/pages" or OUT.is_symlink():
            raise ValueError("Unexpected output directory")
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    tracked = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    documents = {
        p
        for p in tracked
        if p.lower().endswith(".md")
        and "/originals/" not in p
        and not p.startswith("tools/pages/")
    }
    documents.add("tools/pages/README.md")
    files = set(
        p
        for p in tracked
        if p
        and (
            p.startswith(("docs/", "man/", "schematics/"))
            and "/.harness/" not in p
            and not p.endswith(("package.json", "package-lock.json"))
        )
    )
    # Preserve source downloads, including the complete library archive.
    for path in sorted(files):
        target = OUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)

    screenshot_routes = {
        path.relative_to(ROOT).as_posix(): "assets/screenshots/" + path.name
        for path in (HERE / "screenshots").iterdir()
        if path.is_file()
    }

    def mapped(value, source, page):
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return value
        target = posixpath.normpath(
            posixpath.join(posixpath.dirname(source), unquote(parsed.path))
        )
        if target == ".":
            target = "README.md"
        if (ROOT / target).is_dir():
            target = next(
                (
                    target + "/" + n
                    for n in ("README.md", "README.MD")
                    if target + "/" + n in documents
                ),
                target,
            )
        suffix = ("?" + parsed.query if parsed.query else "") + (
            "#" + parsed.fragment if parsed.fragment else ""
        )
        if target in documents:
            return relative(target[:-3] + ".html", page) + suffix
        if target in screenshot_routes:
            return relative(screenshot_routes[target], page) + suffix
        if target in files:
            return relative(target, page) + suffix
        return SOURCE + quote(target, safe="/") + suffix

    def rewrite_links(soup, source, page):
        for tag in soup.find_all(True):
            for attr in ("href", "src"):
                if tag.has_attr(attr):
                    tag[attr] = mapped(tag[attr], source, page)
        return soup

    for source in sorted(documents):
        text = (ROOT / source).read_text(encoding="utf-8")
        page = source[:-3] + ".html"
        if source.startswith("man/") and text.startswith("% "):
            lines = text.splitlines()
            metadata = " · ".join(
                line.removeprefix("% ").strip() for line in lines[1:3]
            )
            text = (
                "# " + lines[0][2:] + "\n\n" + metadata + "\n\n" + "\n".join(lines[3:])
            )
        rendered = markdown.markdown(
            text, extensions=["tables", "fenced_code", "def_list", "toc", "sane_lists"]
        )
        soup = BeautifulSoup(rendered, "html.parser")
        # Retain GitHub-style heading bookmarks alongside Markdown's IDs.
        ids = {tag["id"] for tag in soup.find_all(id=True)}
        for heading in soup.find_all(re.compile("^h[1-6]$")):
            slug = re.sub(r"[^\w -]", "", heading.get_text().lower()).replace(" ", "-")
            if slug and slug not in ids:
                heading.insert_before(soup.new_tag("span", id=slug))
                ids.add(slug)
        rewrite_links(soup, source, page)
        title = soup.h1.get_text() if soup.h1 else source
        write(
            page,
            shell(
                page,
                title,
                str(soup)
                + f'<p class="muted"><a href="{SOURCE}{quote(source)}">Source document</a></p>',
            ),
        )
    cards = []
    for directory in sorted((ROOT / "docs/library").iterdir()):
        if (directory / "capture.json").is_file():
            cards.append(export_collection(directory))
    write(
        "library/index.html",
        shell(
            "library/index.html",
            "Documentation library",
            '<h1>Documentation library</h1><p>Read the captured editions with their original layouts and artwork. The static reader disables archived scripts and external resource requests. Capture information records historical dates and missing evidence.</p><div class="cards">'
            + "".join(cards)
            + '</div><p><a href="../docs/library/README.html">Use the full local replay</a> · <a href="../docs/refs/README.html">Reference catalog</a></p>',
        ),
    )
    home = '<h1>aslice documentation</h1><p>A package-management design for macOS. Read the guides, inspect the command contracts, and explore the historical sources behind the interface.</p><div class="cards">'
    for path, title, detail in [
        (
            "docs/README.html",
            "Documentation",
            "Manuals, architecture, specifications, and runbooks.",
        ),
        (
            "man/README.html",
            "Command reference",
            "Syntax, options, examples, and exit statuses.",
        ),
        (
            "library/index.html",
            "Documentation library",
            "Full captured pages, artwork, provenance, and gaps.",
        ),
        (
            "simulator/index.html",
            "Simulator",
            "A tour of the console and instructions for local use.",
        ),
    ]:
        home += f'<a class="card" href="{path}"><h2>{title}</h2><p>{detail}</p></a>'
    home += '</div><h2>Start reading</h2><p><a href="docs/MANUAL.html">User manual</a> · <a href="docs/AUTHORING.html">Package authoring</a> · <a href="docs/DESIGN.html">System design</a> · <a href="README.html">Project overview</a></p>'
    write("index.html", shell("index.html", "Documentation", home))
    intro = markdown.markdown((HERE / "simulator.md").read_text(encoding="utf-8"))
    intro = str(
        rewrite_links(
            BeautifulSoup(intro, "html.parser"),
            "tools/pages/simulator.md",
            "simulator/index.html",
        )
    )
    write(
        "simulator/index.html",
        shell("simulator/index.html", "Simulator introduction", intro),
    )
    shutil.copytree(HERE / "screenshots", OUT / "assets/screenshots")
    shutil.copytree(ROOT / "build/pages-assets", OUT / "assets", dirs_exist_ok=True)
    fonts = OUT / "assets/fonts"
    fonts.mkdir()
    for family in ("geist", "geist-mono", "space-grotesk"):
        package = HERE / "node_modules/@fontsource" / family
        shutil.copyfile(package / "LICENSE", fonts / f"{family}-LICENSE.txt")
    write(".nojekyll", "")
    print(f"Built {len(documents)} documents and {len(cards)} collections in {OUT}")


if __name__ == "__main__":
    main()
