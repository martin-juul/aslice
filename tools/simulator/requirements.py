"""Reviewed acceptance metadata; discovery never establishes implementation credit.

Source hashes normalize CRLF to LF, matching Git's text checkout policy. Reference
archive hashes retain exact bytes. Review ranges use one-based inclusive lines.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = "tests/requirements/registry.json"
TEST_KINDS = ("positive", "refusal", "concurrency", "recovery")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_bytes(path, relative):
    data = path.read_bytes()
    if relative.startswith(("docs/refs/", "docs/library/")):
        return data
    return data.replace(b"\r\n", b"\n")


def inventory(root):
    paths = set(root.glob("*.md"))
    for current, directories, files in os.walk(root / "tools"):
        directories[:] = [
            name for name in directories if name not in ("__pycache__", "node_modules")
        ]
        paths.update(Path(current) / name for name in files if name.endswith(".md"))
    for directory in ("docs", "man", "schematics"):
        for current, directories, files in os.walk(root / directory):
            current = Path(current)
            if current == root / "docs/library":
                paths.update(current / name for name in files if name.endswith(".md"))
                paths.update(current / name / "SHA256SUMS" for name in directories
                             if name not in (".harness", "node_modules", "__pycache__"))
                directories[:] = []
                continue
            directories[:] = [name for name in directories
                              if name not in ("__pycache__", "node_modules")]
            paths.update(current / name for name in files)
    result = {}
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        if not path.is_file() or any(
            part in ("__pycache__", "node_modules") for part in path.parts
        ):
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith("docs/library/"):
            parts = path.relative_to(root / "docs/library").parts
            # Bind each source collection through its complete byte inventory.
            # Original websites are evidence, not project requirement clauses.
            # Root package files configure the viewer, not its source contracts.
            if len(parts) == 1 and path.suffix.lower() != ".md":
                continue
            if len(parts) > 1 and parts != (parts[0], "SHA256SUMS"):
                continue
        data = source_bytes(path, relative)
        result[relative] = {"sha256": digest(data), "lines": len(data.splitlines())}
    return result


def repository_path(root, name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError(f"invalid repository path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in (".", "..") for part in name.split("/")):
        raise ValueError(f"invalid repository path: {name!r}")
    resolved = (root / name).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"repository path escapes root: {name}")
    return resolved


def decode_json(data):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value
    return json.loads(data, object_pairs_hook=unique)


def load_json(path):
    return decode_json(path.read_text(encoding="utf-8"))


def documented_commands(root, manual="man/README.md"):
    """Read the explicit family table, not prose keywords or guessed commands."""
    path = root / manual
    if not path.exists():
        return {}
    commands = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"\| \[[^]]+\]\(([^)]+\.1\.md)\) \| (.+) \|", line)
        if match:
            for command in re.findall(r"`([^`]+)`", match[2]):
                commands.setdefault(command, []).append("man/" + match[1])
    return {name: sorted(set(pages)) for name, pages in sorted(commands.items())}


def documented_synopses(root):
    """Inventory complete syntax paragraphs without guessing command semantics."""
    result = {}
    for path in sorted((root / "man").glob("*.1.md"), key=lambda item: item.name):
        name = path.relative_to(root).as_posix()
        lines = source_bytes(path, name).decode("utf-8").splitlines()
        active, start, paragraph = False, None, []

        def flush():
            if paragraph:
                text = "\n".join(paragraph)
                ident = f"{name}:{start}-{start + len(paragraph) - 1}"
                result[ident] = {"id": ident, "path": name, "start": start,
                                 "end": start + len(paragraph) - 1, "text": text,
                                 "sha256": digest(text.encode("utf-8"))}
                paragraph.clear()

        for number, line in enumerate(lines, 1):
            if re.match(r"^#\s+", line):
                flush()
                active = line.strip() == "# SYNOPSIS"
            elif active and line.strip():
                if not paragraph:
                    start = number
                paragraph.append(line)
            elif active:
                flush()
        flush()
    return result


def contract_anchors(text):
    """Resolve the ATX headings and explicit anchors used by owning contracts.

    Full CommonMark link lint remains in check_docs.py. Fenced examples never
    define a contract section, and duplicate headings use GitHub-style suffixes.
    """
    anchors, used = set(), set()
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            continue
        if marker:
            fence = marker[1]
            continue
        explicit = re.fullmatch(r' {0,3}<a (?:id|name)="([^"]+)"></a>\s*', line)
        if explicit:
            anchors.add(explicit[1])
        heading = re.match(r"^ {0,3}#{1,6}\s+(.+?)(?:\s+#+)?\s*$", line)
        if heading:
            title = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", heading[1])
            slug = ''.join(character for character in title.lower()
                           if character in '_- ' or unicodedata.category(character)[0] in 'LN').replace(' ', '-')
            ident, suffix = slug, 0
            while ident in used:
                suffix += 1
                ident = f"{slug}-{suffix}"
            used.add(ident)
            anchors.add(ident)
    return anchors


def evaluate(root=ROOT, registry=None):
    root = Path(root)
    registry = load_json(root / REGISTRY) if registry is None else registry
    if not isinstance(registry, dict) or type(registry.get("version")) is not int or registry["version"] != 2:
        raise ValueError("unsupported requirement registry version")
    expected = {"version", "sources", "requirements", "classifications", "commands",
                "specification_defects", "bounded_scenarios"}
    if set(registry) != expected:
        raise ValueError("requirement registry has missing or unknown fields")
    errors, gaps = [], []
    current = inventory(root)
    sources = registry.get("sources", {})
    if not isinstance(sources, dict):
        raise ValueError("registry sources must be an object")
    if any(not isinstance(item, dict) for item in sources.values()):
        raise ValueError("source records must be objects")
    for name in sorted(set(sources) | set(current)):
        repository_path(root, name)
        if name not in sources:
            errors.append(f"source not inventoried: {name}")
        elif name not in current:
            errors.append(f"source removed: {name}")
        elif sources[name].get("sha256") != current[name]["sha256"]:
            errors.append(f"source changed; review invalidated: {name}")

    records = registry.get("requirements", [])
    if not isinstance(records, list):
        raise ValueError("requirements must be an array")
    identifiers, statuses, ranges = set(), [], {name: set() for name in current}
    anchor_cache = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("requirement records must be objects")
        fields = {"id", "statement", "owner", "review", "reviewed_sources", "clauses", "implementation",
                  "implemented", "platform_dependencies", "environments", "tests", "evidence"}
        if set(record) != fields:
            errors.append("requirement has missing or unknown fields")
        ident = record.get("id", "")
        if not isinstance(ident, str):
            raise ValueError("requirement ID must be a string")
        if not re.fullmatch(r"ASLICE-[A-Z]+-[0-9]{3,}", ident) or ident in identifiers:
            errors.append(f"invalid or duplicate requirement ID: {ident}")
        identifiers.add(ident)
        for field in ("statement", "owner", "review"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                errors.append(f"{ident}: missing {field}")
        owner, separator, fragment = str(record.get("owner", "")).partition("#")
        owner_valid = owner in sources and owner in current
        if owner not in sources:
            errors.append(f"{ident}: owner is not an inventoried contract")
        if separator and owner in current:
            if owner not in anchor_cache:
                anchor_cache[owner] = contract_anchors((root / owner).read_text(encoding="utf-8"))
            if not fragment or fragment not in anchor_cache[owner]:
                errors.append(f"{ident}: unknown owning contract section: {fragment}")
                owner_valid = False
        clauses = record.get("clauses", [])
        if not isinstance(clauses, list) or any(not isinstance(item, dict) for item in clauses):
            raise ValueError(f"{ident}: clauses must be an array of objects")
        if not clauses:
            errors.append(f"{ident}: no reviewed clauses")
        clause_ranges = []
        for clause in clauses:
            name = clause.get("path")
            start, end = clause.get("start"), clause.get("end")
            if (name not in current or type(start) is not int or type(end) is not int
                    or not 1 <= start <= end <= current[name]["lines"]):
                errors.append(f"{ident}: invalid source range")
                continue
            clause_ranges.append((name, start, end))
        reviewed_sources = record.get("reviewed_sources")
        if not isinstance(reviewed_sources, dict):
            raise ValueError(f"{ident}: reviewed_sources must be an object")
        required_sources = {owner} | {name for name, _, _ in clause_ranges}
        if set(reviewed_sources) != required_sources:
            errors.append(f"{ident}: review must bind every clause source and owning contract")
        review_valid = (owner_valid and bool(clauses) and len(clause_ranges) == len(clauses)
                        and set(reviewed_sources) == required_sources)
        for name in sorted(required_sources | set(reviewed_sources)):
            repository_path(root, name)
            expected_hash = reviewed_sources.get(name)
            if (not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
                    or name not in current or expected_hash != current[name]["sha256"]):
                errors.append(f"{ident}: review invalidated: {name}")
                review_valid = False
        if review_valid:
            for name, start, end in clause_ranges:
                ranges[name].update(range(start, end + 1))
        for field in ("implementation", "platform_dependencies", "environments", "evidence"):
            if not isinstance(record.get(field), list):
                raise ValueError(f"{ident}: {field} must be an array")
        if not record.get("environments"):
            errors.append(f"{ident}: no required environments")
        for name in record.get("implementation", []):
            if not repository_path(root, name).is_file():
                errors.append(f"{ident}: missing implementation file: {name}")
        tests = record.get("tests", {})
        if not isinstance(tests, dict):
            raise ValueError(f"{ident}: tests must be an object")
        for kind in TEST_KINDS:
            test = tests.get(kind)
            if not isinstance(test, dict) or not test.get("scenario") or not isinstance(test.get("links"), list):
                errors.append(f"{ident}: missing {kind} scenario")
                continue
            for link in test["links"]:
                path = repository_path(root, link.split("::", 1)[0])
                if not path.is_file():
                    errors.append(f"{ident}: missing test: {link}")
        implemented = record.get("implemented", False)
        if type(implemented) is not bool:
            errors.append(f"{ident}: implemented must be boolean")
        # Evidence ingestion is deliberately fail-closed until the runner binds
        # results to build identities and configured qualification authorities.
        if implemented and not record.get("implementation"):
            errors.append(f"{ident}: implementation claim has no files")
        statuses.append({**record, "implemented": implemented is True and review_valid,
                         "review_valid": review_valid,
                         "tested": False, "operational": False,
                         "evidence": record.get("evidence", []),
                         "evidence_status": "not-validated"})
        if not implemented:
            gaps.append(f"{ident}: implementation missing")
        gaps.append(f"{ident}: acceptance evidence missing or unverified")

    decisions = registry.get("classifications", [])
    if not isinstance(decisions, list) or any(not isinstance(item, dict) for item in decisions):
        raise ValueError("classifications must be an array of objects")
    for decision in decisions:
        name = decision.get("path")
        start, end = decision.get("start"), decision.get("end")
        if (name not in current or type(start) is not int or type(end) is not int
                or not 1 <= start <= end <= current[name]["lines"]):
            errors.append("invalid classification range")
            continue
        if decision.get("kind") not in ("context", "historical") or not decision.get("reason"):
            errors.append(f"{name}: classification needs kind and review reason")
            continue
        if decision.get("sha256") != current[name]["sha256"]:
            errors.append(f"{name}: classification review invalidated")
            continue
        if ranges[name].intersection(range(start, end + 1)):
            errors.append(f"{name}: exclusion overlaps a reviewed requirement or classification")
        ranges[name].update(range(start, end + 1))

    source_report = []
    for name, item in current.items():
        # Blank lines do not need a normative decision. All other text does,
        # including tables, examples, schemas, and incorporated references.
        lines = source_bytes(root / name, name).splitlines()
        valid = sources.get(name, {}).get("sha256") == item["sha256"]
        reviewed = ranges[name] if valid else set()
        unreviewed = [number for number, line in enumerate(lines, 1)
                      if line.strip() and number not in reviewed]
        if unreviewed:
            gaps.append(f"{name}: {len(unreviewed)} nonblank lines await review")
        source_report.append({"path": name, **item, "review_valid": valid,
                              "unreviewed_lines": unreviewed,
                              "classification": "reviewed" if valid and not unreviewed else "unreviewed"})

    commands = registry.get("commands", {})
    if not isinstance(commands, dict) or any(not isinstance(item, dict) for item in commands.values()):
        raise ValueError("commands must be an object of records")
    documented = documented_commands(root)
    if (root / "man/aslice.1.md").exists() and documented_commands(root, "man/aslice.1.md") != documented:
        errors.append("command family tables disagree: man/README.md and man/aslice.1.md")
    synopses = documented_synopses(root)
    syntax_mappings = {ident: [] for ident in synopses}
    by_id = {status["id"]: status for status in statuses}
    command_report = []
    for name in sorted(set(commands) | set(documented)):
        entry = commands.get(name, {})
        if entry.get("manuals") != documented.get(name):
            errors.append(f"command inventory changed: {name}")
        state = entry.get("implementation", "missing")
        if state not in ("missing", "partial", "implemented"):
            errors.append(f"{name}: invalid command implementation status")
        if not entry.get("scope"):
            errors.append(f"{name}: command scope is missing")
        mapped = entry.get("requirements", [])
        if not isinstance(mapped, list) or any(ident not in identifiers for ident in mapped):
            errors.append(f"{name}: unknown command requirement")
        if state == "implemented" and not mapped:
            errors.append(f"{name}: implemented command has no reviewed requirements")
        if state == "implemented" and isinstance(mapped, list):
            if any(ident not in by_id or not by_id[ident]["implemented"] for ident in mapped):
                errors.append(f"{name}: command depends on missing or invalidated implementation")
        syntax = entry.get("synopses", [])
        if not isinstance(syntax, list) or any(not isinstance(item, dict) for item in syntax):
            raise ValueError(f"{name}: synopses must be an array of review bindings")
        seen = set()
        for binding in syntax:
            ident = binding.get("id")
            if not isinstance(ident, str) or ident not in synopses:
                errors.append(f"{name}: unknown synopsis binding: {ident}")
                continue
            if ident in seen:
                errors.append(f"{name}: duplicate synopsis binding: {ident}")
                continue
            seen.add(ident)
            synopsis = synopses[ident]
            source = synopsis["path"]
            if (binding.get("sha256") != synopsis["sha256"]
                    or binding.get("source_sha256") != current[source]["sha256"]):
                errors.append(f"{name}: synopsis review invalidated: {ident}")
                continue
            # Syntax review must have a reviewed requirement covering that
            # complete paragraph, not merely a family-table association.
            covered = set()
            canonical_coverage = set()
            for requirement in mapped if isinstance(mapped, list) else []:
                record = by_id.get(requirement, {})
                if record.get("review_valid"):
                    for clause in record["clauses"]:
                        if clause["path"] == source:
                            covered.update(range(clause["start"], clause["end"] + 1))
                            if record["owner"].split("#", 1)[0] in entry.get("manuals", []):
                                canonical_coverage.update(range(clause["start"], clause["end"] + 1))
            paragraph_lines = set(range(synopsis["start"], synopsis["end"] + 1))
            if source not in entry.get("manuals", []):
                if (binding.get("cross_reference") is not True or not binding.get("reason")
                        or not paragraph_lines.issubset(canonical_coverage)):
                    errors.append(f"{name}: synopsis belongs to another command family: {ident}")
                    continue
            if not paragraph_lines.issubset(covered):
                errors.append(f"{name}: synopsis has no covering reviewed requirement: {ident}")
                continue
            syntax_mappings[ident].append(name)
        if not syntax:
            gaps.append(f"command {name}: syntax review missing")
            if state == "implemented":
                errors.append(f"{name}: implemented command has no reviewed syntax")
        command_report.append({"command": name, **entry})
        if state != "implemented" or not mapped:
            gaps.append(f"command {name}: {state}; contract coverage incomplete")
    synopsis_report = []
    for ident, synopsis in synopses.items():
        global_requirements = []
        if synopsis["path"] == "man/aslice.1.md":
            for status in statuses:
                if status["review_valid"] and status["owner"].split("#", 1)[0] == synopsis["path"]:
                    if any(clause["path"] == synopsis["path"] and clause["start"] <= synopsis["start"]
                           and clause["end"] >= synopsis["end"] for clause in status["clauses"]):
                        global_requirements.append(status["id"])
        reviewed = bool(syntax_mappings[ident] or global_requirements)
        synopsis_report.append({**synopsis, "commands": syntax_mappings[ident],
                                "global_requirements": global_requirements, "reviewed": reviewed})
        if not reviewed:
            gaps.append(f"synopsis {ident}: command mapping unreviewed")
    defects = registry.get("specification_defects", [])
    if not isinstance(defects, list) or any(not isinstance(item, dict) for item in defects):
        raise ValueError("specification defects must be an array of objects")
    defect_ids = set()
    for defect in defects:
        ident = defect.get("id")
        if set(defect) != {"id", "contracts", "description"}:
            errors.append("specification defect has missing or unknown fields")
        if (not isinstance(ident, str) or not re.fullmatch(r"[A-Z][A-Z0-9-]*-[0-9]+", ident)
                or ident in defect_ids):
            errors.append("invalid or duplicate specification defect ID")
        else:
            defect_ids.add(ident)
        description = defect.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{ident}: specification defect needs a description")
        contracts = defect.get("contracts")
        if not isinstance(contracts, list) or not contracts:
            errors.append(f"{ident}: specification defect needs contract links")
            contracts = []
        seen_contracts = set()
        for contract in contracts:
            if not isinstance(contract, str) or not contract or contract in seen_contracts:
                errors.append(f"{ident}: invalid or duplicate defect contract")
                continue
            seen_contracts.add(contract)
            name, separator, fragment = contract.partition("#")
            repository_path(root, name)
            if name not in sources or name not in current:
                errors.append(f"{ident}: defect contract is not inventoried: {name}")
                continue
            if separator:
                if name not in anchor_cache:
                    anchor_cache[name] = contract_anchors((root / name).read_text(encoding="utf-8"))
                if not fragment or fragment not in anchor_cache[name]:
                    errors.append(f"{ident}: unknown defect contract section: {fragment}")
        gaps.append(f"specification defect: {ident}")
    if not records:
        gaps.append("no reviewed requirements")
    if not documented:
        gaps.append("no documented command inventory")
    gaps.append("physical qualification and owner-controlled ceremonies are unverified")
    if errors:
        for status in statuses:
            status["implemented"] = False
    return {"version": 2, "complete": False, "development_valid": not errors,
            "review_summary": {
                "sources": len(source_report),
                "fully_classified_sources": sum(item["classification"] == "reviewed" for item in source_report),
                "unreviewed_nonblank_lines": sum(len(item["unreviewed_lines"]) for item in source_report),
                "requirements": len(statuses),
                "valid_requirement_reviews": sum(item["review_valid"] for item in statuses),
                "implemented": sum(item["implemented"] for item in statuses),
                "tested": sum(item["tested"] for item in statuses),
                "operational": sum(item["operational"] for item in statuses),
                "synopses": len(synopsis_report),
                "reviewed_synopses": sum(item["reviewed"] for item in synopsis_report),
            },
            "registry_sha256": digest(json.dumps(registry, sort_keys=True, separators=(",", ":")).encode()),
            "validation_errors": errors, "mandatory_gaps": errors + gaps,
            "inventory": source_report, "requirements": statuses,
            "scenario_mappings": registry["bounded_scenarios"],
            "commands": command_report, "specification_defects": defects,
            "synopses": synopsis_report,
            "qualification": "unverified; simulated results cannot establish physical qualification"}


def native_evidence(path):
    """Inventory supplied receipts without trusting self-asserted qualification."""
    path = Path(path)
    with path.open("rb") as stream:
        data = stream.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise ValueError("native evidence exceeds 4 MiB")
    value = decode_json(data)
    if (not isinstance(value, dict) or type(value.get("version")) is not int
            or value["version"] != 1 or not isinstance(value.get("receipts"), list)):
        raise ValueError("unsupported native evidence bundle")
    for receipt in value["receipts"]:
        if not isinstance(receipt, dict) or receipt.get("qualification") != "physical":
            raise ValueError("native evidence must contain physical qualification receipts")
        for field in ("machine", "os_build", "filesystem", "security_settings", "configuration",
                      "executable_sha256", "source_sha256", "authority", "signature"):
            if not receipt.get(field):
                raise ValueError(f"native evidence receipt is missing {field}")
        for field in ("executable_sha256", "source_sha256"):
            if not isinstance(receipt[field], str) or not re.fullmatch(r"[0-9a-f]{64}", receipt[field]):
                raise ValueError(f"invalid native evidence {field}")
    return {"sha256": digest(data), "receipts": len(value["receipts"]),
            "accepted": False, "reason": "qualification authority verifier is not configured"}
