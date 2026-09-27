"""Present capture provenance separately from the preserved documentation."""

from collections import Counter
from html import escape
from urllib.parse import urlsplit


def document(title, content):
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title></head><body><main>"
        f"<h1>{escape(title)}</h1>{content}</main></body></html>"
    )


def gap_reason(entry):
    if entry is None:
        return "This URL is not recorded in the capture manifest."
    status = entry.get("http_status")
    if status == 200:
        return "The retrieved response was excluded from this edition."
    if status:
        return f"The archive retrieval returned HTTP {status}."
    return "The archive retrieval did not complete."


def provenance(entry):
    fields = (
        ("Historical capture", "memento_datetime"),
        ("Retrieved at (UTC)", "retrieved_utc"),
        ("Requested archive URL", "requested_archive"),
        ("Resolved archive URL", "effective_url"),
        ("Retrieval error", "error"),
    )
    rows = [
        f"<dt>{label}</dt><dd>{escape(str(entry[key]))}</dd>"
        for label, key in fields
        if entry.get(key)
    ]
    return f'<dl>{"".join(rows)}</dl>' if rows else ""


def gap_page(url, entry):
    return document(
        "Not available in this capture",
        f"<p>{escape(url)}</p><p>{escape(gap_reason(entry))}</p>"
        + (provenance(entry) if entry else "")
        + "<p>No live request was made.</p>"
        '<p><a href="/__library/">Capture index</a> · '
        '<a href="/__library/gaps/">Recorded gaps</a></p>',
    )


def gap_index(replay):
    rows = []
    for url, entry in sorted(replay.records.items()):
        if entry["status"] == "captured":
            continue
        link = escape(replay.local_url(url, url))
        rows.append(
            f'<li><p><a href="{link}">{escape(url)}</a></p>'
            f"<p>{escape(gap_reason(entry))}</p>{provenance(entry)}</li>"
        )
    return document(
        "Recorded capture gaps",
        '<p><a href="/__library/">Capture index</a></p>'
        "<p>These retrievals are recorded but unavailable for replay. "
        "Unrecorded URLs are not included in this list.</p>"
        f'<p>{len(rows)} recorded gaps.</p><ul>{"".join(rows)}</ul>',
    )


def capture_index(replay):
    counts = Counter(
        entry["kind"]
        for entry in replay.records.values()
        if entry["status"] == "captured"
    )
    missing = sum(entry["status"] != "captured" for entry in replay.records.values())
    rows = []
    for url, entry in sorted(replay.records.items()):
        if entry["kind"] != "page":
            continue
        label = escape(urlsplit(url).path)
        link = escape(replay.local_url(url, url))
        date = escape(entry.get("memento_datetime") or "no capture")
        rows.append(
            f'<li><a href="{link}">{label}</a> '
            f'— {escape(entry["status"])}; {date}</li>'
        )
    entry_url = replay.metadata["entry_url"]
    entry_link = escape(replay.local_url(entry_url, entry_url))
    return document(
        replay.metadata["title"],
        f'<p><a href="{entry_link}">Open documentation</a></p>'
        "<p>Local replay. Source files are unchanged; served URLs are mapped "
        "to this capture. Uncaptured paths return an archive gap page.</p>"
        f'<p>{counts["page"]} captured pages; {counts["asset"]} captured assets; '
        f'<a href="/__library/gaps/">{missing} recorded gaps</a>.</p>'
        "<p>Historical dates vary by resource. See the "
        '<a href="/__library/manifest.json">capture manifest</a> and '
        '<a href="/__library/SHA256SUMS">file checksums</a> for provenance.</p>'
        f'<h2>Sections</h2><ul>{"".join(rows)}</ul>',
    )
