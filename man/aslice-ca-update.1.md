% ASLICE-CA-UPDATE(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-ca-update — refresh CA trust on a frozen OS

# SYNOPSIS

`aslice ca-update` [**--check**]
`aslice ca-update --keychain`
`aslice ca-update --keychain-remove`
`aslice ca-update --crypto`
`aslice ca-update --apple-certs`
`aslice ca-update --from-file` *bundle.pem*

# DESCRIPTION

The system trust store on 10.11–10.13 froze years ago; modern roots never arrived and old ones expired. `ca-update` heals TLS in layers, each saying exactly what it can and cannot do.

Bare **ca-update** refreshes the `ca-certificates` slice — the Mozilla root program's store, shipped as an ordinary signed, generation-managed package — and validates it before activation (parses completely, non-empty, no already-expired certificates). The shell integration points `SSL_CERT_FILE`, `CURL_CA_BUNDLE`, and `GIT_SSL_CAINFO` at it, so aslice's curl, git, and python get modern roots, modern ciphers, and TLS 1.3 regardless of the OS. **--check** reports staleness without changing anything.

**--keychain** imports the bundle's missing roots into the System keychain — additively, by fingerprint, each import recorded in the state database — healing Safari, Mail, and every SecureTransport app. Admin authorization is required every run; there is no "always allow." Apple-shipped and user-added certificates are never removed or distrusted. **--keychain-remove** deletes exactly the recorded set. This fixes *trust*, not *crypto*: on 10.11–10.12 the OS's TLS stack predates TLS 1.3, and sites requiring it stay unreachable in Safari no matter what the keychain holds — the command says so when run.

**--crypto** upgrades the crypto-provider slices (OpenSSL and kin) to the newest the index offers. It cannot and does not touch the OS's own stack, and says so.

**--apple-certs** imports Apple's own roots — not carried by Mozilla's program — from the pinned `apple-roots` slice, for Software Update, the App Store, iCloud, and Developer ID validation. Same additive, recorded, reversible machinery as **--keychain**.

**--from-file** installs a local bundle whose sha256 is recorded; it never fetches. The bundle source is configurable (`aslice config set ca.source`).

# SEE ALSO

aslice(1), aslice-doctor(1), MANUAL.md §8
