# curl Mozilla CA Extraction

## Source identity

- Original source: https://curl.se/docs/caextract.html
- Author/publisher: curl project
- Source version/date: CA extraction documentation retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Original technical account; upstream text not reproduced. Upstream copyright remains with its authors.
- Used by: STATE-AND-RECOVERY §9; DESIGN §12.10; MANUAL §8

## Captured material

The service converts Mozilla's certificate store into a PEM bundle for applications such as curl. It checks for changes and publishes dated bundles and a SHA-256 digest. The PEM file does not carry all additional constraints applied by Firefox, including restrictions limiting some authorities to particular domains.

Importing these certificates as unrestricted system trust anchors therefore does not reproduce the browser's complete trust policy. The certificate bundle is data; it does not itself add TLS protocol or cipher implementations.

## Applicability and limits

The bundle's MPL-2.0 notice does not automatically license all website text. No live bundle is archived here or presented as current trust. A released certificate package needs its own complete policy inventory and dated evidence.

## Project interpretation

The source supports the facts above. Project policy and acceptance gates remain in the linked specification; they are not attributed to the source. No successful aslice runtime test is implied by archiving this reference.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.
