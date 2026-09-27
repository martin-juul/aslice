# Documentation library

This directory holds captured documentation sites. Each collection preserves the
original response bodies, response headers, source URLs, capture dates, and
checksums. The corresponding record in [the reference catalog](../refs/README.MD)
describes the edition, its use, and any missing evidence.

## Browse a capture

From `docs/library`, run:

```sh
npm ci
npm start
```

The launcher verifies the collections, starts the replay backend and viewer, and
opens the bookshelf at `http://127.0.0.1:8765`. For subsequent visits, run
`npm start`. No simulator or separate server command is needed. Stop everything
with Ctrl+C.

The host needs Node.js 24.15 or newer in the 24.x line, or Node.js 26 or newer,
and Python 3.10 or newer. The launcher tries `python3`, `python`, then `py -3`.
Set `LIBRARY_PYTHON` to an executable path if Python is installed elsewhere.
Installing dependencies needs network access; browsing an installed library does
not.

The shelf has one book per immediate collection directory containing
`capture.json`. Search finds collection titles, editions, and section titles and
paths. Grid and List change the presentation; the title menu changes the sort
order. Covers are generated with local fonts and text. Their presentation metadata
lives in `.harness/covers.json`, outside the preserved collections.

Open a book to read the original captured website. Contents filters captured
sections by title or path; selecting a section gives it a bookmarkable viewer
address. The site's own navigation also works inside the reader. Information
shows verification status, counts, and links to provenance, recorded gaps, the
manifest, and checksums. Library returns to the previous shelf position and
focused book. Tab moves between controls, Enter opens links, and Escape closes an
open viewer panel when focus is in the viewer. Contents collapses on narrow
screens so the document retains the reading area.

The viewer starts in light appearance. Dark appearance is an explicit choice,
saved in browser storage; it changes the viewer, not the captured pages.

### Troubleshooting

- If port 8765 is occupied, stop its current server or run
  `npm start -- --port 8766`. `LIBRARY_PORT` supplies the same default override.
  The launcher reports conflicts without selecting a different port silently.
- Use `npm start -- --no-open` to leave browser opening to you. The launcher prints
  the address when the catalog is ready.
- A book marked **Verification failed** cannot open. Its error identifies the
  failing check; restore the collection from a known intact copy. Other verified
  books remain available. Restart the launcher after replacing or adding captures.
- If the catalog cannot load, check the launcher's terminal output and use Retry.
- `npm run serve` needs an existing build. Run `npm run build` first.

### Python CLI

The original commands remain available from the repository root:

```text
python -m tools.library serve apple-macos-hig-2018
```

Open [the local capture index](http://127.0.0.1:8765/__library/), then choose a
section. Use `--port` to select another port. Stop the server with Ctrl+C.
For this standalone capture index, Python's standard library is sufficient; the
simulator and Node are not needed. Existing `tools.library` imports and the
`import-capture` command remain compatibility entrypoints for the implementation
in `.harness/backend`.

The index shows captured page and asset counts and links to recorded gaps. Each
gap identifies the retrieval result and available capture dates, including
responses excluded from the selected edition. You can also inspect the unchanged
capture manifest and file checksums through the index. An unrecorded URL has no
retrieval evidence and is identified separately on its gap page.

The server replays the original HTML, styles, scripts, images, and fonts. It maps
resource URLs to local paths in responses without modifying the preserved files.
It never downloads resources while browsing. An uncaptured URL produces a gap
page, and a content security policy blocks external subresource requests. Native
browser rendering can still differ from the browser used in 2018. Preserved scripts
may attempt external requests, including analytics; the browser rejects these
through the replay policy before they reach the network. In the bookshelf,
each collection gets a separate loopback origin. The sandboxed reader permits
original scripts and same-origin resources, blocks popups and top-level navigation,
and the replay response allows framing only by the viewer's exact origin. All
servers bind to `127.0.0.1`; replay ports are assigned for each session. Bookmark
the viewer address, not an ephemeral replay port.

## Viewer development and verification

Viewer source, launch scripts, configurations, backend, and tests live in
`.harness`. The library's package manifest and lockfile live beside this README.
Run these commands from `docs/library`:

| Command | Purpose |
|---|---|
| `npm start` / `npm run dev` | Start Vite and the replay backend; open the shelf. |
| `npm run build` | Typecheck, build into `.harness/dist`, and check ES5/CSS compatibility. |
| `npm run serve` / `npm run preview` | Serve the built viewer and start its replay backend. |
| `npm run typecheck` | Check TypeScript 7 source. |
| `npm run lint` | Lint viewer and launch code. |
| `npm run format` / `npm run format:check` | Format or check harness files. |
| `npm test` / `npm run test:watch` | Run UI, launcher, and Python tests / watch UI tests. |
| `npm run test:browser` | Exercise the built viewer in Chromium. |
| `npm run check` | Run typechecking, lint, formatting checks, tests, and build. |

Before the first browser test, run `npx playwright install chromium`. Build with
`npm run build`, then run `npm run test:browser`. Browser tests cover the shelf,
original site navigation, section bookmarks, information, both appearances,
keyboard operation, narrow layouts, external request monitoring, and missing
native Promise/fetch fallbacks. Python tests cover preservation, replay, discovery,
collection isolation, and framing headers; launcher tests cover missing Python,
port conflicts, and cleanup after termination.

The production build lowers application and dependency JavaScript to a classic
ES5 script with Babel and checks it with Acorn. It bundles browser API fallbacks
and local fonts with WOFF alternatives. Sass and Autoprefixer produce CSS for
Safari 9; the build rejects known unsupported CSS features. Vite development mode
requires a modern browser. Use the compiled viewer for Safari 9 on OS X 10.11.
These automated checks do not constitute qualification on an actual OS X machine;
that platform check remains outstanding.

Full-text indexing, annotations, capture acquisition through the viewer, and editing
are outside this viewer's scope.

## Collections

| Collection | Edition and record |
|---|---|
| `apple-macos-hig-2018` | [Apple macOS Human Interface Guidelines, Mojave period](../refs/APPLE_MACOS_HIG_2018.MD), beginning with the supplied November 19, 2018 Wayback snapshot. |

## Preservation

Within each collection:

- `capture.json` names the collection and its entry URL.
- `manifest.json` maps original URLs to saved responses and records failed
  retrievals and historical dates. A failed entry is not a captured source.
- `originals/` contains unchanged response bodies and retained response headers.
  Filenames are URL hashes so query strings and different origins cannot collide.
- `acquisition/`, when present, retains retrieval scripts and source-index
  responses with their provenance. These describe the capture process.
- `SHA256SUMS` covers every stored file except itself.

Verify a collection without network access:

```text
python -m tools.library verify apple-macos-hig-2018
```

The replay server performs this verification before startup. Preserve the whole
collection when making backups; the source record alone is not the documentation.
Keep copyright notices and historical revisions intact. A local capture does not
change the source's license or establish that its guidance applies to later systems.
