# curl Mozilla CA Extraction

## Source identity

- Original source: https://curl.se/docs/caextract.html
- Author/publisher: curl project
- Source version/date: CA extraction documentation retrieved 2026-09-26
- Retrieved: 2026-09-26 (UTC date; web and HTTP capture)
- Capture type: technical account of the material used; not a verbatim archive
- Rights: Technical paraphrase; upstream attribution above. No full-original redistribution permission asserted.
- Used by:
  - [STATE-AND-RECOVERY §9. Certificate trust lifecycle](../STATE-AND-RECOVERY.md#9-certificate-trust-lifecycle): PEM extraction loses browser constraints and is not equivalent to system-wide trust policy.
  - [DESIGN §12.10 Trust store: modern CA certificates on a frozen platform](../DESIGN.md#1210-trust-store-modern-ca-certificates-on-a-frozen-platform): A certificate update does not update the TLS implementation.
  - [MANUAL §8. Keeping TLS alive on an old OS](../MANUAL.md#8-keeping-tls-alive-on-an-old-os): Private bundle use and System-keychain import have different trust effects.

## Captured material

The service converts Mozilla's certificate store into a PEM bundle for applications such as curl. It checks for changes and publishes dated bundles and a SHA-256 digest. The PEM file does not carry all additional constraints applied by Firefox, including restrictions limiting some authorities to particular domains.

Importing these certificates as unrestricted system trust anchors therefore does not reproduce the browser's complete trust policy. The certificate bundle is data; it does not itself add TLS protocol or cipher implementations.

## Decision-relevant context

Source locator: CA certificates extracted from Mozilla; Missing Name Constraints; CA certificate store license; Automated downloads from here.

The service checks daily but regenerates only when its script or source changes. Each PEM includes a conversion date; the page links dated revisions and SHA-256 digests. The extraction retains certificates but omits browser-side restrictions such as allowed domains.

For efficient downloads the page describes an ETag comparison/save pair; older curl versions can use a local file's modification time as a conditional request. These mechanisms reduce transfers; neither a cache validator nor a digest fetched alongside a bundle establishes independent publisher authorization. `mk-ca-bundle` converts the Mozilla source, while `certutil` with a separate extraction script offers a local Firefox-store alternative.

## Applicability and limits

The bundle's MPL-2.0 notice does not automatically license all website text. No live bundle is archived here or presented as current trust. A released certificate package needs its own complete policy inventory and dated evidence.

## Project interpretation

Archive the actual released bundle, conversion inputs, policy inventory, and authorization separately when packaging certificates. Do not import every PEM entry as an unrestricted anchor merely because the file is accepted by curl.

## Omissions and evidence gaps

No current CA bundle or trust recommendation is frozen here. ETag support on the project's legacy curl versions and the local extraction scripts have not been validated. MPL-2.0 applies to the bundle, not automatically to this website.

## Preservation

This UTF-8 Markdown record is readable without a browser, script, account, or network. Preserve it with the repository and `SHA256SUMS`; retain superseded records when replacing a source version. Original URLs identify provenance, not a runtime dependency.

Review: 2026-09-26 UTC. Original source re-read against the cited local sections; added locators, conditions, and explicit gaps. No runtime validation is inferred. This account expands the earlier summary without replacing its historical date.
