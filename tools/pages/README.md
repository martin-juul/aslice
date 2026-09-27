# GitHub Pages portal

The portal publishes repository Markdown, command manuals, the full captured
documentation library, and a static simulator introduction. Source documents and
archive files remain unchanged. It does not deploy the simulator or its controller.

From the repository root, using Python 3.10+ and Node.js 24.15+:

```sh
python -m pip install -r tools/pages/requirements.txt
npm ci --prefix tools/pages --ignore-scripts
npm run build --prefix tools/pages
npm exec --prefix tools/pages -- playwright install chromium
python tools/pages/build.py
python tools/pages/check.py
python tools/pages/preview.py
```

Open `http://127.0.0.1:8767/aslice/`. Preview binds only to loopback and works on
Windows, macOS, and Linux. Use `--prefix /` for a root site, or `--port` to select
another port. Stop with Ctrl+C. Build output stays in ignored `build/pages`.

Browser checks start their own preview under `/aslice/`:

```sh
npm exec --prefix tools/pages -- playwright install chromium
npm run test:browser --prefix tools/pages
python -m unittest discover -s tools/pages/tests -p 'test_*.py'
```

The dedicated Pages workflow builds and checks pull requests. Pushes to `master`
and manual runs on `master` deploy the checked artifact through GitHub Pages.
Select **GitHub Actions** as the repository's Pages source. No publishing branch
or source-document edits are required.

The static reader verifies every collection before export. It renders all captured
pages and supporting assets with local routes, including distinct query URLs and
cross-origin assets. Missing URLs become local gap pages. The generated HTML
removes scripts, event handlers, forms, and embedded browsing contexts; a restrictive
content security policy and a sandboxed frame also disable script execution and
external resource requests. Scripts remain intact in the original archive downloads.
The local library launcher and its script-enabled replay remain unchanged.

Section links and reader navigation are bookmarkable. Search filters the section
list; the shelf links capture information, recorded gaps, manifests, and checksums.
Raw archive bytes remain available beneath `docs/library`, while generated reader
resources live beneath `library`. Copyright notices and source terms still apply.

TypeScript 7 checks the source, Vite bundles it, and Babel lowers the complete
script to ES5. Each build checks ES5 syntax, unsupported CSS constructs, and WOFF
fallbacks. The portal uses repository font families with bundled WOFF fonts and
local font licenses.
It defaults to light appearance and saves explicit dark selection. Tests cover
both appearances, keyboard navigation, narrow layouts, archive isolation, and
project-prefix routing. These browser checks are not Safari 9 qualification.

Mermaid fences render to local SVG images during the Python build, using Mermaid
and Playwright Chromium. Both appearances use embedded Geist fonts; wide diagrams
scroll within a keyboard-focusable pane. Each diagram retains its original text
under **Diagram source**. Rendering errors fail the build. Published diagrams need
no Mermaid runtime or external requests, and remain visible without JavaScript.

## Refresh simulator screenshots

Build the existing console with `npm run build:demo` in `tools/simulator/web`, then
run `npm run preview:demo` there. Install the browser tooling from
`tools/dev/browser-requirements.txt` and Chromium, then run:

```sh
python tools/pages/capture.py
```

The PNGs are direct browser screenshots at 1440 × 1080, using development sample
data. The introduction labels that limitation. Capture both appearances together;
do not retouch the UI or imply the samples are runtime validation.
