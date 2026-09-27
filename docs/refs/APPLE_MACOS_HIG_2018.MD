# Apple macOS Human Interface Guidelines (Mojave, 2018)

## Source identity

- Original source: https://developer.apple.com/design/human-interface-guidelines/macos/overview/themes/
- Historical entry: https://web.archive.org/web/20181119085424/https://developer.apple.com/design/human-interface-guidelines/macos/overview/themes/
- Author/publisher: Apple Inc.; historical responses preserved by the Internet Archive.
- Source version/date: macOS guidelines during the Mojave period. The entry page was captured on 2018-11-19 at 08:54:24 UTC. Apple's publication/revision date is not independently known. Linked pages resolve to their own historical captures; this is not a single simultaneous website snapshot.
- Retrieved: 2026-09-27 UTC, using Wayback's original-response `id_` endpoint with Windows certificate validation. Initial requests used curl; resumed requests use urllib3 with truststore. Per-resource retrieval dates, redirects, response headers, and checksums are retained.
- Capture type: original HTML responses and supporting assets, served through local URL mapping. Retrieval coverage is recorded below and in the archive manifest.
- Rights: Apple copyright and source notices remain in the original files. This capture does not change their terms or assert a redistribution license.
- Used by: [GUI design foundation](../../AGENTS.md#gui-design-foundation), which selects Mojave as the primary reference for both appearances. The project's font choices, explicit appearance toggle, and browser compatibility floor remain project decisions.

## Captured material

The source is a multi-page website, not a PDF. The capture follows the macOS navigation from the supplied Themes page, including architecture, interaction, system capabilities, visual design, images, windows, menus, controls, indicators, Touch Bar, and extensions. It preserves complete retrieved pages, including their examples and notices, rather than replacing them with summaries.

The collection contains 115 accepted HTML pages and 1,173 supporting assets, including poster images discovered during original-script replay. All 114 macOS section routes linked from the supplied Themes page were recovered. Accepted pages have 2018 capture dates. Supporting assets comprise 472 captures from 2018, 452 from 2019, 248 from 2020, and one from 2022.

Browse the collection using the command in [the documentation library](../library/README.md#browse-a-capture). The replay server uses the captured HTML, styles, scripts, and images. It changes URL routing in served responses, not the preserved source files or the page's layout. External subresource requests are blocked, and missing paths produce local gap pages instead of live-site fallbacks.

## Section guide

| Source section | Relevance to the console review |
|---|---|
| Overview / Themes and Visual Index | Overall Mac conventions and the source's visual taxonomy. |
| Visual Design / Dark Mode and Color | Appearance-specific surfaces, content contrast, and semantic color choices. |
| Windows and Views / Sidebars, Split Views, Toolbars, and Window Anatomy | Navigation, pane boundaries, and compact window controls. |
| Buttons / Pop-Up Buttons, Pull-Down Buttons, and Push Buttons | Control roles, labels, and appearance. |
| Selectors / Segmented Controls | Selection among related views. |
| Fields and Labels; User Interaction / Keyboard | Form presentation and keyboard operation. |

These are source locators, not a claim that the current console conforms. The local capture index links all recorded sections and displays each section's capture date and retrieval status.

## Applicability and limits

This edition concerns native Mac applications during the Mojave period. Applying its conventions to a browser console requires implementation and interaction testing. The source alone does not establish Safari 9 compatibility or reproduce the macOS Server application's exact layout.

Some supporting assets resolve to 2019 or 2020 captures; the high-resolution Share Extensions modal illustration resolves to 2022. Their actual dates remain in the manifest; they are not evidence of identical appearance in November 2018. The replay follows the recovered resource graph rather than claiming a contemporaneous capture of every asset.

The Mojave-era website includes material beyond the simulator's initial scope, such as Touch Bar and app extensions. Those sections remain part of the source record; retaining them does not add simulator requirements.

## Project interpretation

Use the preserved edition when reviewing the console's light and dark appearances. Keep source guidance separate from the project's requested Server-style layout, custom font stack, and explicit theme selection. Do not silently replace this edition with Apple's current cross-platform guidelines.

## Omissions and evidence gaps

Retrieval completed with 100 unavailable candidates: two linked page routes and 98 supporting-resource URLs. Tabbed Windows resolves to a 2020 Fullscreen Mode page; Authentication resolves to a 2021 Auto Save page. Both responses are retained for provenance but are rejected as Mojave pages and produce local gap pages.

The 98 asset failures are Wayback HTTP 404 responses: 87 shared Apple-site CSS resource paths, nine inferred high-resolution macOS illustrations, and two Apple TV logo variants outside the macOS content. The missing macOS variants are `TB_bar_2x.png`, seven `TB_layout_*_2x.png` illustrations, and `visualDesign_Typography_2x.png`. Their standard-resolution originals are captured. Inferred high-resolution URLs are candidates, not proof those files existed. The manifest retains the exact URLs and responses; replay does not silently replace missing files.

Other platform guidelines, linked API documentation, videos, and downloadable design-tool packages are separate sources. They are not included merely because a captured page links to them.

## Preservation

The [capture manifest](../library/apple-macos-hig-2018/manifest.json) identifies original response bodies and headers in the collection's `originals/` directory. [Collection checksums](../library/apple-macos-hig-2018/SHA256SUMS) cover the preserved files. The reference archive's checksum manifest covers this record; library verification checks the separate source collection.

The Themes entry matches the original response retrieved from the supplied snapshot byte for byte: SHA-256 `4aae2aea937587c1724c2dff9f42973637d1236736614d1a4e387b12fd1a0ab6`. The collection's `acquisition/` directory retains the capture script, Wayback image-index responses, and their source URLs. These records describe retrieval, not a claim that every linked site or later-edition asset belongs to the 2018 HIG.
