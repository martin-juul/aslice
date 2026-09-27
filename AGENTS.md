# GUI design foundation

All GUI work in this repository follows Apple's macOS Human Interface Guidelines
through Mojave (2018). Mojave is the primary reference for both light and dark
appearances. The 2008–2015 guidelines provide historical context; do not substitute
newer macOS design languages for this foundation.

- Default to light appearance. Offer an explicit, persistent dark appearance
  toggle. Never follow the operating system's appearance automatically.
- Use familiar Mac controls, compact toolbars, clear pane boundaries, restrained
  decoration, and visible keyboard focus. Keep navigation easy to learn.
- Keep layouts responsive. In the simulator, terminal and application display
  take priority over configuration, inspectors, and diagnostics.
- Use Geist for UI text, controls, and menus; Geist Mono for technical text,
  metadata, timecodes, and durations; Space Grotesk for display headings.
- Do not use emojis as GUI content or controls. Guest application output remains
  unmodified.
- Define colors by purpose and provide coherent light and dark palettes. Do not
  invert guest images or application displays to implement dark appearance.
- Verify both appearances, keyboard operation, narrow layouts, and content
  preservation when changing appearance or layout.

Period references: [Apple's archived window guidance (2008)](https://leopard-adc.pepas.com/documentation/UserExperience/Conceptual/AppleHIGuidelines/XHIGWindows/XHIGWindows.html)
and [What's New in Cocoa for macOS, WWDC 2018](https://developer.apple.com/videos/play/wwdc2018/209/).

The [Mojave HIG source record](docs/refs/APPLE_MACOS_HIG_2018.MD) identifies the
historical edition. Browse its original pages through the
[documentation library](docs/library/README.md), and check recorded capture gaps
before relying on a section or asset.

# Console implementation conventions

Use feature-based TypeScript with single quotes, semicolons, readable multiline
functions, and blank lines between functions. Use `private`, never `#` private
fields. Use native DOM APIs and explicit helpers, not jQuery-style abstractions.
Keep `node_modules` and generated build output ignored.

The compiled simulator console targets Safari 9 on OS X 10.11. Compile application
and dependency JavaScript to ES5, bundle required browser API fallbacks locally,
and compile Sass to CSS supported by that browser. Preserve this floor when
upgrading packages. Vite development mode may require a modern browser; use the
compiled preview on Safari 9. See `tools/simulator/web/README.md` for verification
and the distinction between fallback tests and actual platform qualification.
