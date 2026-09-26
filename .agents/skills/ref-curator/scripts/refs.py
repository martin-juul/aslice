"""Offline archive checks. See ../references/archive-checks.md for limits."""
import argparse
from collections import Counter
import hashlib
import html
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

SUBJECTS = (
    "Apple platforms and system behavior",
    "Hardware compatibility and CPU architecture",
    "Homebrew releases, support, and history",
    "Build infrastructure and runner availability",
    "Signing, trust, and supply-chain security",
    "Formats, schemas, and serialization",
    "Libraries, ABI, and toolchain behavior",
)
ADMIN = {"README.MD", "TEMPLATE.MD", "SOURCE-INVENTORY.MD"}


def archive_files(root):
    directory = root / "docs/refs"
    if directory.is_symlink() or not directory.resolve().is_relative_to(root.resolve()):
        raise ValueError("Archive must be inside the repository, not a symlink")
    result = {}
    for path in sorted(directory.iterdir(), key=lambda p: p.name):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Unsupported archive entry: {path.name}")
        if any(c in path.name for c in "\r\n\\"):
            raise ValueError(f"Unsupported archive filename: {path.name!r}")
        result[path.name] = path
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh(root):
    files = archive_files(root)
    data = "".join(f"{digest(path)}  {name}\n" for name, path in files.items()
                   if name != "SHA256SUMS")
    (root / "docs/refs/SHA256SUMS").write_bytes(data.encode("utf-8"))


def project_lines(text, wrapper=False):
    """Retain line numbers while excluding fenced code and embedded originals."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^\s*(\x60{3,}|~{3,})(.*)$", line)
        if fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= fence[1] and not match[2].strip():
                fence = None
            continue
        if wrapper and line.strip() == "## Full captured source":
            yield number, line
            break
        if match:
            fence = (match[1][0], len(match[1]))
            continue
        yield number, line


def without_code(line):
    return re.sub(r"(\x60+)(.+?)\1(?!\x60)", lambda m: " " * len(m[0]), line)


def destination(raw):
    """Accept a destination with optional quoted title; reject ambiguous syntax."""
    raw = raw.strip()
    match = re.fullmatch(r'(<[^<>\n]*>|(?:\\.|[^\s])+?)(?:\s+(?:"[^"]*"|\'[^\']*\'))?', raw)
    if not match:
        raise ValueError("unsupported link destination")
    value = match[1]
    if value.startswith("<"):
        value = value[1:-1]
    return html.unescape(re.sub(r"\\([^\w\s])", r"\1", value))


def links(lines, errors, context):
    definitions = {}
    for n, line in lines:
        match = re.match(r"^\s{0,3}\[([^\]]+)\]:\s*(.+)$", line)
        if match:
            try:
                definitions[" ".join(match[1].casefold().split())] = destination(match[2])
            except ValueError as exc:
                errors.append(f"{context}:{n}: {exc}")
    found = []
    for n, original in lines:
        if re.match(r"^\s{0,3}\[[^\]]+\]:", original):
            continue
        line = without_code(original)
        if re.search(r"<(?:a|img)\b", line, re.I) and not re.fullmatch(r'\s*<a id="[a-z0-9_-]+"></a>\s*', line):
            errors.append(f"{context}:{n}: unsupported HTML link/anchor; review manually")
        position = 0
        consumed = []
        for match in re.finditer(r"(?<!\\)\[([^\[\]\n]+)\]", line):
            if match.start() < position:
                continue
            label, end = match[1], match.end()
            raw = None
            if line[end:end + 1] == "(":
                depth, cursor, escaped, angle = 1, end + 1, False, False
                while cursor < len(line):
                    char = line[cursor]
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == "<":
                        angle = True
                    elif char == ">":
                        angle = False
                    elif not angle and char == "(":
                        depth += 1
                    elif not angle and char == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    cursor += 1
                if depth:
                    errors.append(f"{context}:{n}: unterminated inline link")
                    continue
                raw = line[end + 1:cursor]
                position = cursor + 1
            elif line[end:end + 1] == "[":
                ref = re.match(r"\[([^\]]*)\]", line[end:])
                if not ref:
                    errors.append(f"{context}:{n}: unsupported reference link")
                    continue
                key = " ".join((ref[1] or label).casefold().split())
                position = end + len(ref[0])
                if key not in definitions:
                    errors.append(f"{context}:{n}: undefined reference link {key!r}")
                    continue
                found.append((n, label, definitions[key]))
                consumed.append((match.start(), position))
                continue
            else:
                key = " ".join(label.casefold().split())
                if key in definitions:
                    found.append((n, label, definitions[key]))
                continue
            consumed.append((match.start(), position))
            try:
                found.append((n, label, destination(raw)))
            except ValueError as exc:
                errors.append(f"{context}:{n}: {exc}")
        remainder = line
        for start, end in reversed(consumed):
            remainder = remainder[:start] + " " * (end - start) + remainder[end:]
        if re.search(r"(?<!\\)\]\(", remainder):
            errors.append(f"{context}:{n}: unsupported or malformed link syntax")
    return found


def anchors(path, errors, root):
    result, used = set(), set()
    lines = list(project_lines(path.read_text(encoding="utf-8"),
                               path.parent == root / "docs/refs"))
    previous = ""
    explicit = set()
    for n, line in lines:
        anchor = re.fullmatch(r'\s*<a id="([a-z0-9_-]+)"></a>\s*', line)
        if anchor:
            if anchor[1] in explicit:
                errors.append(f"{path.relative_to(root)}:{n}: duplicate explicit anchor {anchor[1]}")
            explicit.add(anchor[1])
            result.add(anchor[1])
            continue
        if previous.strip() and re.fullmatch(r"\s{0,3}(?:=+|-+)\s*", line):
            errors.append(f"{path.relative_to(root)}:{n}: unsupported setext heading")
        previous = line
        match = re.match(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        title = match[1]
        if re.search(r"<[^>]+>|\]\[", title):
            errors.append(f"{path.relative_to(root)}:{n}: unsupported heading markup")
        title = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", title)
        # Protect code spans: underscores there are literal, not emphasis.
        code = {}
        def preserve_code(match):
            token = f"REFCURATORCODE{len(code)}TOKEN"
            code[token] = match[2]
            return token
        title = re.sub(r"(\x60+)(.+?)\1(?!\x60)", preserve_code, title)
        title = re.sub(r"(?<!\w)(_+)([^_]+)\1(?!\w)", r"\2", title)
        for token, content in code.items():
            title = title.replace(token, content)
        title = html.unescape(title).lower()
        slug = re.sub(r"[^\w\- ]", "", title).replace(" ", "-")
        candidate, counter = slug, 0
        while candidate in used:
            counter += 1
            candidate = f"{slug}-{counter}"
        used.add(candidate)
        result.add(candidate)
    return result


def local_target(source, url, root, errors, number):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return None
    path = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source
    context = f"{source.relative_to(root)}:{number}"
    if not path.is_relative_to(root):
        errors.append(f"{context}: link outside repository: {url}")
        return None
    if not path.exists():
        errors.append(f"{context}: missing link target: {url}")
        return None
    if parsed.query:
        errors.append(f"{context}: unsupported query on local link: {url}")
    return path, unquote(parsed.fragment)


def check_attributes(root, files, errors):
    paths = [p.relative_to(root).as_posix() for p in files.values()]
    proc = subprocess.run(["git", "-C", str(root), "check-attr", "-z", "--stdin", "text"],
                          input="\0".join(paths) + "\0", text=True,
                          capture_output=True, timeout=30, check=True)
    fields = proc.stdout.rstrip("\0").split("\0")
    if len(fields) != len(paths) * 3:
        raise ValueError("Unexpected git check-attr response")
    for path, attribute, value in zip(fields[::3], fields[1::3], fields[2::3]):
        if attribute != "text" or value != "unset":
            errors.append(f"{path}: effective text attribute is {value!r}, expected 'unset'")


def verify(root):
    root = root.resolve()
    files = archive_files(root)
    errors = []
    for name in sorted(ADMIN | {"SHA256SUMS"}):
        if name not in files:
            errors.append(f"Missing archive file: {name}")
    manifest = files.get("SHA256SUMS")
    listed = set()
    if manifest:
        for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
            match = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
            if not match:
                errors.append(f"SHA256SUMS:{number}: malformed entry")
                continue
            checksum, name = match.groups()
            if name in listed:
                errors.append(f"SHA256SUMS:{number}: duplicate entry {name}")
            listed.add(name)
            if name not in files or name == "SHA256SUMS":
                errors.append(f"SHA256SUMS:{number}: unexpected entry {name}")
            elif digest(files[name]) != checksum:
                errors.append(f"SHA256SUMS:{number}: checksum mismatch: {name}")
        for name in sorted(set(files) - {"SHA256SUMS"} - listed):
            errors.append(f"SHA256SUMS: missing entry {name}")
    records = {name for name in files if name.upper().endswith(".MD") and name.upper() not in ADMIN}
    parsed, all_lines = {}, {}
    for name, path in files.items():
        if path.suffix.lower() == ".md":
            all_lines[name] = list(project_lines(path.read_text(encoding="utf-8"), True))
            parsed[name] = links(all_lines[name], errors, name)

    catalog_count = Counter()
    groups, titles, group = [], [], None
    in_catalog = False
    for n, line in all_lines.get("README.MD", []):
        if line.startswith("## "):
            in_catalog = line == "## Catalog"
        if not in_catalog:
            continue
        if line.startswith("### "):
            if titles != sorted(titles, key=str.casefold):
                errors.append(f"Catalog: entries out of order in {group}")
            group, titles = line[4:], []
            groups.append(group)
        if re.match(r"^- ", line):
            entries = [(label, url) for ln, label, url in parsed.get("README.MD", []) if ln == n]
            if len(entries) != 1:
                errors.append(f"README.MD:{n}: expected one primary catalog link")
            for label, url in entries:
                if group not in SUBJECTS or url not in records:
                    errors.append(f"README.MD:{n}: invalid primary catalog entry: {url}")
                titles.append(label)
                catalog_count[url] += 1
    if titles != sorted(titles, key=str.casefold):
        errors.append(f"Catalog: entries out of order in {group}")
    if groups != list(SUBJECTS):
        errors.append("Catalog: subject headings/order differ from the seven archive subjects")
    for name in sorted(records):
        if catalog_count[name] != 1:
            errors.append(f"Catalog: {name} has {catalog_count[name]} primary entries")

    inventory, in_coverage = Counter(), False
    for n, line in all_lines.get("SOURCE-INVENTORY.MD", []):
        if line.startswith("## "):
            in_coverage = line == "## Catalog coverage"
        if in_coverage and line.startswith("|"):
            # Only the record column establishes coverage. Gap columns can link
            # related records without creating duplicate inventory entries.
            first_column = line.split("|")[1]
            entries = links([(n, first_column)], errors, "SOURCE-INVENTORY.MD")
            inventory.update(url for _, _, url in entries)
    for name in sorted(records):
        if inventory[name] != 1:
            errors.append(f"Inventory: {name} has {inventory[name]} coverage entries")
    for name in sorted(inventory.keys() - records):
        errors.append(f"Inventory: unexpected coverage entry {name}")

    anchor_cache, referenced_assets = {}, set()
    for name, entries in parsed.items():
        source = files[name]
        for number, _, url in entries:
            target = local_target(source, url, root, errors, number)
            if target is None:
                continue
            path, fragment = target
            if name in records and path.parent == root / "docs/refs":
                referenced_assets.add(path.name)
            if fragment:
                if path.suffix.lower() != ".md":
                    errors.append(f"{name}:{number}: unsupported fragment target: {url}")
                else:
                    if path not in anchor_cache:
                        anchor_cache[path] = anchors(path, errors, root)
                    if fragment not in anchor_cache[path]:
                        errors.append(f"{name}:{number}: missing anchor: {url}")
    for name in sorted(set(files) - set(parsed) - {"SHA256SUMS"} - referenced_assets):
        errors.append(f"Asset not linked from a record: {name}")
    check_attributes(root, files, errors)
    return errors, len(records), len(files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify", "refresh-checksums"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4])
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        if args.command == "refresh-checksums":
            refresh(root)
            print("Updated SHA256SUMS from current bytes; run verify after reviewing the diff.")
            return 0
        errors, records, files = verify(root)
        for error in errors:
            print(error)
        print(f"Checked {records} records and {files} archive files; {len(errors)} findings.")
        print("Offline mechanical checks only; source accuracy, rights, and completeness require review.")
        return 1 if errors else 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Archive check failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
