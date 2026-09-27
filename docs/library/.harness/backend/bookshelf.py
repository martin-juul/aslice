"""Read-only catalog and per-collection loopback replay origins."""

import argparse
from collections import Counter
from html import unescape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
from threading import Thread
from urllib.parse import urlsplit

from .archive import LIBRARY
from .replay import Replay, make_server


class Bookshelf:
    def __init__(self, library, viewer_origin):
        self.servers = []
        self.books = []
        presentation = json.loads(
            (Path(__file__).parents[1] / 'covers.json').read_text(encoding='utf-8')
        )
        for directory in sorted(Path(library).iterdir()):
            if (directory.name.startswith('.') or directory.name == 'node_modules'
                    or directory.is_symlink() or not directory.is_dir()
                    or not (directory / 'capture.json').is_file()):
                continue
            book = {'id': directory.name, 'title': directory.name, 'error': None}
            try:
                # Never read response bodies until the complete archive verifies.
                server = make_server(directory, 0, viewer_origin)
                self.servers.append(server)
                Thread(target=server.serve_forever, daemon=True).start()
                replay = Replay(directory)
                origin = f'http://127.0.0.1:{server.server_port}'
                sections = []
                for url, entry in replay.records.items():
                    if entry['kind'] != 'page' or entry['status'] != 'captured':
                        continue
                    body = (directory / 'originals' / entry['body']).read_text(encoding='utf-8')
                    title = re.search(r'<title[^>]*>(.*?)</title>', body, re.I | re.S)
                    sections.append({
                        'title': unescape(re.sub('<[^>]+>', '', title[1])).strip() if title else urlsplit(url).path,
                        'path': urlsplit(url).path,
                        'url': url,
                        'replay': origin + replay.local_url(url, url),
                    })
                book.update(replay.metadata)
                book.update({
                    'edition': presentation.get(directory.name, {}).get('edition', 'Captured edition'),
                    'coverTitle': presentation.get(directory.name, {}).get('title', book['title']),
                    'origin': origin,
                    'entry': origin + replay.local_url(replay.metadata['entry_url'], replay.metadata['entry_url']),
                    'sections': sorted(sections, key=lambda section: section['title'].lower()),
                    'counts': dict(Counter(entry['kind'] for entry in replay.records.values() if entry['status'] == 'captured')),
                    'gaps': sum(entry['status'] != 'captured' for entry in replay.records.values()),
                })
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                book['error'] = str(error)
            self.books.append(book)

    def close(self):
        for server in self.servers:
            server.shutdown()
            server.server_close()


def catalog_server(shelf):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/api/catalog':
                self.send_error(404)
                return
            body = json.dumps(shelf.books).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    return ThreadingHTTPServer(('127.0.0.1', 0), Handler)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--viewer-origin', required=True)
    parser.add_argument('--library', type=Path, default=LIBRARY)
    args = parser.parse_args()
    if not re.fullmatch(r'http://127\.0\.0\.1:\d+', args.viewer_origin):
        parser.error('The viewer must use a loopback HTTP origin.')
    shelf = Bookshelf(args.library, args.viewer_origin)
    server = catalog_server(shelf)
    Thread(target=server.serve_forever, daemon=True).start()
    print(json.dumps({'port': server.server_port}), flush=True)
    try:
        # Parent owns stdin. EOF also cleans up after an unexpected parent exit.
        sys.stdin.read()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        shelf.close()


if __name__ == '__main__':
    main()
