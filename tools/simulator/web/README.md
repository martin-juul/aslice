# Simulator console browser build

The shipped console targets Safari 9 on OS X 10.11. It retains the current npm
versions of xterm and noVNC. Actual Safari 9 qualification still requires an
OS X 10.11 machine; ES5 parsing and browser fallback tests do not replace that gate.

Run `npm ci --ignore-scripts`, then:

- `npm run dev`: develop the standalone UI with sample machines in a modern browser.
- `npm run dev:live`: develop against a loopback controller configured through
  `SIMULATOR_CONTROLLER_URL`.
- `npm run build` and `npm run build:demo`: compile the live and standalone consoles.
- `npm run preview` or `npm run preview:demo`: serve the compiled console at
  `http://127.0.0.1:4173/static/`, including for older browsers.
- `npm run check`: type checking, lint, formatting, and unit tests.
- `npm run check:browser`: check both built outputs for ES5 syntax, classic script
  loading, unsupported CSS constructs, and static WOFF font fallbacks.

Vite's development server requires a modern browser. Use the built preview for
Safari 9; the production build does not require ES modules or a module loader.

## Styles

`src/styles/main.scss` composes the palette, base layout, controls, and workspace
feature styles. Sass resolves both appearance palettes into ordinary CSS;
Autoprefixer targets Safari 9. Layout uses Flexbox without flex gap or CSS Grid.
Open-panel layout state comes from the workspace feature, without `:has()`.
Static Geist, Geist Mono, and Space Grotesk fonts include WOFF files.

Mojave remains the primary design reference. The default appearance is light;
dark appearance is an explicit saved choice, independent of OS preferences.

The console applies the [captured Mojave HIG](../../../docs/refs/APPLE_MACOS_HIG_2018.MD)
to its workspace controls:

- **Split Views:** adjoining content panes use a one-pixel divider with two pixels
  of additional pointer area on each side. Existing minimum and maximum sizes,
  keyboard resizing, and pane hiding remain available.
- **Toolbars and Segmented Controls:** pane controls share compact, textured
  surfaces. The workspace selector has equal-width segments and a subdued selected
  state. Arrow keys, Home, and End change views while focus is in the selector;
  the selected view is saved without unmounting sessions or the guest display.
- **Pop-Up Buttons:** selectors use double-arrow indicators and retain native
  keyboard and menu behavior. Their text and menu surfaces follow the chosen
  appearance.
- **Dark Mode:** surrounding controls recede, separators use dark lines, and guest
  pixels retain their own appearance. Both palettes are explicit Sass definitions.
- **Labels and Disclosure Controls:** machine resources and reported compatibility
  have labeled rows. Selectable identifiers and raw capability data are under
  Technical details. Missing or unfamiliar data never implies a passed check.

Machine lifecycle controls follow the last successful controller status and stay
disabled during a pending machine operation. Failed status refreshes mark the
displayed state unavailable until a successful refresh. These UI checks supplement
the controller's validation; they do not replace it.

These are browser adaptations of the source guidance, not native AppKit controls
or a claim of complete HIG conformance. The project's font stack and manual theme
selection remain deliberate project choices.

## JavaScript and browser services

Vite emits one classic `app.js`; Babel transforms the application and dependencies
to ES5. Acorn rejects incompatible syntax during every build. Polyfills are bundled
locally for language features, fetch, abort signals, text encoding, resize
observation, pointer events, and DOM operations. Event listener adaptation preserves
`once`, capture, removal, and abort cleanup on older WebKit. SHA-256 verification
does not depend on WebCrypto availability.

The noVNC build uses an exact-integer JSBI adapter and negotiates ordinary VNC
encodings instead of WebCodecs H.264. The adapter and guarded build transform live
in the repository; installed dependencies are not edited. Guest pixels are not
modified by these adaptations.

The build also guards Zod's unused BigInt range initialization. The JSON control
protocol does not use bigint schemas. Dependency transforms fail when their
expected source changes, so package upgrades require an explicit compatibility
review.

WebGL falls back to the standard terminal renderer. Inline terminal images need
WebAssembly and are explicitly unavailable when the browser lacks it. On browsers
without the download attribute, completed exports provide a link to open the file
and save it through the browser's File menu.

## Qualification

Run `python tests/simulator/test_web_demo.py` after building the demo and the
controller tests in `tests/simulator/test_runtime.py` after building the live UI.
Fallback tests deliberately remove newer browser APIs. They test compatibility
paths, not the rendering engine or security behavior of Safari 9 itself.

On an actual OS X 10.11 installation, verify both appearances, terminal input and
resize, reconnect, VNC rendering and input, file import/export, keyboard navigation,
and narrow layouts. Record the exact Safari version and any unsupported optional
capabilities. Do not mark this platform qualified from a user-agent override or a
current Playwright WebKit run.
