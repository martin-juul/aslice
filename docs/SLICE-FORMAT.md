# Slice container format

- **Status:** Specification v0.4 — September 2026. Packing and extraction implementations remain acceptance work.
- **Schematic:** [slice.schema.json](../schematics/json/slice.schema.json) validates the container descriptor; [artifact-manifest.schema.json](../schematics/json/artifact-manifest.schema.json) validates its manifest.

<a id="byte-layout"></a>

## 1. Byte layout

The underlying encodings are preserved locally in [RFC 8878](refs/RFC_8878_ZSTANDARD.MD) and the [libarchive tar format manual](refs/LIBARCHIVE_TAR_FORMAT.MD), including their complete original text and notices.

A `.slice` is one Zstandard frame containing a POSIX pax tar archive. Concatenated frames, trailing non-padding data, sparse files, and unlisted archive members are rejected. The decoded archive contains exactly these roots, in order:

```text
slice.json             UTF-8 canonical JSON container descriptor
manifest.json          UTF-8 canonical JSON artifact manifest
payload/               directory
payload/<entry>        entries listed by manifest.files, sorted by path
```

Only per-entry pax headers needed for UTF-8 paths, link paths, or size are allowed. Global headers, alternate names with conflicting meanings, arbitrary xattrs, and implementation-specific extraction directives are refused. Header uid/gid are zero, user/group names empty, timestamps zero; the manifest determines normalized payload modes. The packer fixes its zstd parameters and records the packer revision in detached provenance. A different compression result may have the same artifact identity but a different archive digest.

`slice.json` follows the container schematic. Its manifest digest equals the signed index's `artifact_id`, and its length is checked against both the actual bytes and the index's `manifest_size`. `payload_entries` counts the manifest inventory, excluding the `payload/` root and metadata headers. `payload_bytes` is the sum of regular-file sizes. These fields declare resource usage within fixed bounds; they do not justify unchecked memory allocation. An implementation may impose lower configured limits and must explain a refusal before extraction.

<a id="content-identity-and-signatures"></a>

## 2. Content identity and signatures

The canonical manifest binds the file inventory, dependency artifacts, recipe, exact flags, CPU requirements, and ABI evidence. It does not contain its own digest. SHA-256 of those canonical manifest bytes is `artifact_id`; the file hashes bind the payload. SHA-256 of the complete compressed `.slice` is `blob_digest`. The signed index binds both digests and their byte lengths, with the exact recipe digest and length.

Detached minisign-compatible Ed25519 or the repository's configured OpenPGP signature authenticates the complete archive bytes, under the repository's package-signing authority. TUF independently authorizes that archive and its manifest/recipe records. The signature is a sibling transport object, never an archive member that signs itself. Builder identities, timestamps, SBOMs, receipts, and notarization evidence are separate authenticated objects bound to the frozen artifact/archive digests. Apple signing that changes executable bytes is completed before the served manifest and archive are frozen; unsigned reproducibility evidence remains separate.

Relocation follows [STATE-AND-RECOVERY §1](STATE-AND-RECOVERY.md#1-compatibility-and-artifact-identity). A signed vendor executable is not silently rewritten, thinned, or re-signed. A manifest cannot authorize extraction outside the staged artifact or mutate another installed artifact.

<a id="verification-and-extraction"></a>

## 3. Verification and extraction

1. Authenticate current TUF target metadata or an eligible retained offline receipt. Check archive length, full digest, configured package signature, repository capabilities, and known revocations before parsing the compressed archive.
2. Decode with bounded window/memory, total expanded bytes, entry count, path length, and time. Absolute limits: descriptor 64 KiB; manifest 16 MiB; one million payload entries; 1 TiB regular-file bytes. Disk-space preflight includes staging and rollback reserves. A declared limit cannot raise a configured lower bound.
3. Require descriptor and manifest first, validate both schemas, canonical encoding, digest/length bindings, and supported format versions. Reject duplicate JSON keys. Verify recipe and index agreement for name, repository, version, CPU/OS requirements, and exact dependency bindings.
4. Extract through directory descriptors without following untrusted links. Reject absolute paths, parent traversal, duplicate entries, destination-filesystem case/Unicode collisions, device nodes, setuid/setgid, hardlinks, and symlinks escaping the staged artifact. Only regular files, directories, and internal symlinks are supported. Symlink target resolution is checked transitively, including cycles and dangling targets. Do not extract as root into live paths.
5. Check every entry's kind, size, mode, and SHA-256 or symlink target against the manifest; reject missing or extra files. Confirm totals and end-of-archive padding. Apply authorized relocation in staging, verify installed-byte receipts, then register the immutable artifact through the transaction journal.

Schema validation alone establishes none of the cryptographic, filesystem, or resource-limit properties above. They require extractor tests and fuzzing on both HFS+ and APFS. File metadata unsupported by this normalized payload format must be expressed as a separate declared helper operation or refused; it is never smuggled through tar headers.

<a id="fixtures-and-evolution"></a>

## 4. Fixtures and evolution

[slice.json](../tests/fixtures/slice.json) is a structural descriptor fixture. Its matching artifact fixture uses illustrative hashes; it is not an installable signed release. Contract checks reject missing manifest bindings, unknown fields, unsupported versions, and unsafe manifest paths. Extractor acceptance additionally needs actual compressed-archive cases for traversal, links, collisions, decompression bombs, truncation, hash mismatch, and unexpected members.

`slice_version` and `manifest_version` are independent integer format versions. Unknown versions fail before payload extraction. Breaking wire changes require a new version and migration/export guidance; retaining a filename or compatibility key does not authorize reinterpretation of old bytes.

Run the structural checks with `python -m unittest discover -s tests -p test_slice_contract.py` after installing `tests/requirements.txt`. These checks use illustrative fixtures; they do not validate archive bytes or prove extractor safety.

## History

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v0.4 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |
| v0.3 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v0.2 | September 2026 | prose rewrite of the container resource-limit explanation; no content changes. |

</details>
