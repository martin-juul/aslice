"""Discovery failures must not compromise healthy books or their origins."""

import json
import shutil
import urllib.request

import unittest
import test_archive
from tools.library import _backend

Bookshelf = _backend('bookshelf').Bookshelf


class BookshelfTests(unittest.TestCase):
    setUp = test_archive.LibraryTests.setUp
    add_record = test_archive.LibraryTests.add_record

    def test_discovery_isolation_and_framing(self):
        library = self.directory.parent
        shutil.copytree(self.directory, library / 'second-guide')
        broken = library / 'broken-guide'
        shutil.copytree(self.directory, broken)
        (broken / 'capture.json').write_text('{}')
        shutil.copytree(self.directory, library / '.harness')
        shutil.copytree(self.directory, library / 'node_modules')
        (library / 'not-a-collection').mkdir()
        shelf = Bookshelf(library, 'http://127.0.0.1:8765')
        try:
            self.assertEqual(len(shelf.books), 3)
            self.assertIn('Checksum mismatch', shelf.books[0]['error'])
            healthy = [book for book in shelf.books if not book['error']]
            self.assertEqual(len(healthy), 2)
            self.assertNotEqual(healthy[0]['origin'], healthy[1]['origin'])
            self.assertEqual(healthy[0]['counts'], {'page': 1, 'asset': 2})
            for book in healthy:
                with urllib.request.urlopen(book['entry']) as response:
                    policy = response.headers['Content-Security-Policy']
                    self.assertIn('frame-ancestors http://127.0.0.1:8765', policy)
                    self.assertNotIn('Access-Control-Allow-Origin', response.headers)
                    self.assertIn(b'Next', response.read())
        finally:
            shelf.close()

    def test_empty_catalog(self):
        shutil.rmtree(self.directory)
        shelf = Bookshelf(self.directory.parent, 'http://127.0.0.1:8765')
        self.assertEqual(shelf.books, [])
        shelf.close()

    def test_catalog_is_read_only(self):
        from threading import Thread
        from urllib.error import HTTPError
        shelf = Bookshelf(self.directory.parent, 'http://127.0.0.1:8765')
        server = _backend('bookshelf').catalog_server(shelf)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/api/catalog'
            with urllib.request.urlopen(url) as response:
                self.assertEqual(json.load(response)[0]['id'], 'test-guide')
            with self.assertRaises(HTTPError) as failure:
                urllib.request.urlopen(urllib.request.Request(url, data=b'{}'))
            self.assertEqual(failure.exception.code, 501)
            failure.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            shelf.close()
