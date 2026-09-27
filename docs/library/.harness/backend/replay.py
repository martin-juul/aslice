"""Serve preserved pages with local URL routing; never fetch live resources."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

from .archive import verify
from .catalog import capture_index, gap_index, gap_page
from .rewrite import HtmlRoutes, rewrite_css


class Replay:
    def __init__(self, directory):
        self.directory = directory
        self.metadata = json.loads(
            (directory / "capture.json").read_text(encoding="utf-8")
        )
        self.records = json.loads(
            (directory / "manifest.json").read_text(encoding="utf-8")
        )
        self.origin = urlsplit(self.metadata["entry_url"])
        self.resources = {
            urldefrag(url)[0]: entry for url, entry in self.records.items()
        }
        for entry in self.records.values():
            if entry["status"] == "captured":
                self.resources.setdefault(self.resolved_url(entry), entry)

    @staticmethod
    def resolved_url(entry):
        match = re.match(
            r"https?://web\.archive\.org/web/\d+[a-z_]*?/(https?://.+)",
            entry.get("effective_url", ""),
        )
        return urldefrag(match[1] if match else entry["url"])[0]

    def local_url(self, value, source):
        if value.startswith(("#", "data:", "blob:", "javascript:", "mailto:")):
            return value
        target = urlsplit(urljoin(source, value))
        if target.scheme not in ("http", "https"):
            return value
        route = target.path or "/"
        if target.netloc != self.origin.netloc or target.scheme != self.origin.scheme:
            route = f"/__origins/{target.scheme}/{target.netloc}{route}"
        return urlunsplit(("", "", route, target.query, target.fragment))

    def original_url(self, request_path):
        target = urlsplit(request_path)
        if target.path.startswith("/__origins/"):
            parts = target.path.split("/", 4)
            if len(parts) < 5 or parts[2] not in ("http", "https"):
                return None
            return urlunsplit((parts[2], parts[3], "/" + parts[4], target.query, ""))
        return urlunsplit(
            (self.origin.scheme, self.origin.netloc, target.path, target.query, "")
        )

    def rewrite(self, text, source, content_type):
        def resolve(value):
            return self.local_url(value, source)

        if "html" in content_type:
            return HtmlRoutes(text, resolve).rewritten()
        return rewrite_css(text, resolve)


def make_server(directory, port=8765, viewer_origin=None):
    verify(directory)
    replay = Replay(directory)
    ancestors = viewer_origin or "'none'"

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body, content_type, extra_headers=None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self' data: blob:; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
                "object-src 'none'; form-action 'self'; base-uri 'self'; "
                f"frame-ancestors {ancestors}",
            )
            self.send_header("X-Content-Type-Options", "nosniff")
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self):
            if self.path == "/__library/":
                self.respond(
                    200, capture_index(replay).encode(), "text/html; charset=utf-8"
                )
                return
            if self.path == "/__library/gaps/":
                self.respond(
                    200, gap_index(replay).encode(), "text/html; charset=utf-8"
                )
                return
            metadata_files = {
                "/__library/manifest.json": ("manifest.json", "application/json"),
                "/__library/SHA256SUMS": ("SHA256SUMS", "text/plain; charset=utf-8"),
            }
            if self.path in metadata_files:
                filename, content_type = metadata_files[self.path]
                self.respond(200, (directory / filename).read_bytes(), content_type)
                return
            url = replay.original_url(self.path)
            entry = replay.resources.get(url)
            if not entry or entry["status"] != "captured":
                body = gap_page(url or self.path, entry)
                self.respond(404, body.encode(), "text/html; charset=utf-8")
                return
            resolved_url = replay.resolved_url(entry)
            if entry["kind"] == "page" and url != resolved_url:
                self.respond(
                    302,
                    b"",
                    "text/html",
                    {"Location": replay.local_url(resolved_url, url)},
                )
                return
            body = (directory / "originals" / entry["body"]).read_bytes()
            content_type = entry.get("content_type") or "application/octet-stream"
            if "html" in content_type or "css" in content_type:
                body = replay.rewrite(
                    body.decode("utf-8"), resolved_url, content_type
                ).encode("utf-8")
                content_type = content_type.split(";")[0] + "; charset=utf-8"
            requested_range = self.headers.get("Range")
            if (
                requested_range
                and "html" not in content_type
                and "css" not in content_type
            ):
                match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested_range)
                size = len(body)
                if match and (match[1] or match[2]):
                    start = int(match[1]) if match[1] else max(0, size - int(match[2]))
                    end = (
                        min(size - 1, int(match[2]))
                        if match[1] and match[2]
                        else size - 1
                    )
                    if 0 <= start <= end < size:
                        self.respond(
                            206,
                            body[start : end + 1],
                            content_type,
                            {
                                "Accept-Ranges": "bytes",
                                "Content-Range": f"bytes {start}-{end}/{size}",
                            },
                        )
                        return
                self.respond(
                    416, b"", content_type, {"Content-Range": f"bytes */{size}"}
                )
                return
            self.respond(200, body, content_type, {"Accept-Ranges": "bytes"})

        do_HEAD = do_GET

        def log_message(self, *_arguments):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
