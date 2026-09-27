"""Check generated local links and verify copied archive bytes."""

import re
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

from build import ROOT, OUT, verify


def main():
    failures = []
    checked = 0
    documents = {}
    fragment_links = []
    for path in sorted(OUT.rglob("*.html")):
        # Raw source downloads are not generated portal pages.
        if path.relative_to(OUT).as_posix().startswith("docs/refs/"):
            if "assets/portal.js" not in path.read_text(
                encoding="utf-8", errors="replace"
            ):
                continue
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        archived = "/resources/" in path.as_posix()
        if not archived:
            documents[path.resolve()] = {
                tag.get("id") for tag in soup.find_all(id=True)
            } | {tag.get("name") for tag in soup.find_all("a", attrs={"name": True})}
        if archived:
            if soup.find("script") or soup.find(
                ["iframe", "object", "embed", "base", "form"]
            ):
                failures.append(f"{path}: active archived content")
            if any(
                name.lower().startswith("on")
                for tag in soup.find_all(True)
                for name in tag.attrs
            ):
                failures.append(f"{path}: archived event handler")
            if not soup.find(
                "meta", attrs={"content": re.compile("script-src 'none'")}
            ):
                failures.append(f"{path}: missing script-blocking policy")
        for tag in soup.find_all(True):
            for attr in ("href", "src", "poster"):
                if not tag.has_attr(attr):
                    continue
                value = tag[attr]
                url = urlsplit(value)
                if url.scheme or url.netloc:
                    if archived and url.scheme in ("http", "https"):
                        failures.append(f"{path}: external archive URL: {value}")
                    continue
                target = (
                    (path.parent / unquote(url.path)).resolve()
                    if url.path
                    else path.resolve()
                )
                if not archived and url.fragment and attr == "href":
                    if re.fullmatch(
                        r"[a-f0-9]{64}\.html(?:#.*)?", url.fragment
                    ) and soup.find(id="capture"):
                        target = path.parent / "resources" / url.fragment.split("#")[0]
                    else:
                        fragment_links.append((path, target, unquote(url.fragment)))
                if not target.is_relative_to(OUT) or not target.is_file():
                    failures.append(f"{path.relative_to(OUT)}: missing {value}")
                checked += 1
    for source, target, fragment in fragment_links:
        if target in documents and fragment not in documents[target]:
            failures.append(
                f"{source.relative_to(OUT)}: missing fragment {target.name}#{fragment}"
            )
    for path in (OUT / "library").rglob("*.css"):
        css = path.read_text(encoding="utf-8")
        urls = re.findall(r"url\(\s*[\"\x27]?([^\)\"\x27]+)", css)
        urls += re.findall(r"@import\s+[\"\x27]([^\"\x27]+)", css)
        for value in urls:
            url = urlsplit(value.strip())
            if url.scheme == "data" or not url.path:
                continue
            target = (path.parent / unquote(url.path)).resolve()
            if (
                url.scheme
                or url.netloc
                or not target.is_relative_to(OUT)
                or not target.is_file()
            ):
                failures.append(
                    f"{path.relative_to(OUT)}: unavailable CSS resource {value}"
                )
            checked += 1
    for directory in (ROOT / "docs/library").iterdir():
        if not (directory / "capture.json").is_file():
            continue
        verify(directory)
        verify(OUT / directory.relative_to(ROOT))
    if failures:
        raise SystemExit("\n".join(failures))
    print(
        f"Passed {checked} generated local links; archive copies verify byte for byte."
    )


if __name__ == "__main__":
    main()
