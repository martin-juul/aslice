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

Bare **ca-update** refreshes the signed private CA bundle for compatible aslice clients. `shellenv` configures their certificate paths. A root refresh does not itself supply new ciphers or TLS protocols; **--crypto** separately upgrades compatible aslice crypto providers. **--check** reports staleness without changing anything.

**--keychain** requires a signed certificate-policy inventory, not just a PEM bundle. The protected helper distinguishes roots and intermediates, preserves declared purposes and restrictions, and refuses entries whose constraints the OS cannot represent. It asks for admin authorization each run and records ownership. Policy retirement removes only aslice-owned imports after conflict checks; Apple and independently installed user entries remain untouched. **--keychain-remove** removes the managed imports with the same checks.

**--apple-certs** applies the separately signed Apple certificate inventory under those rules. Each named service needs chain validation and per-OS tests. Certificate import cannot guarantee that an obsolete service protocol works.

**--from-file** installs a local private bundle and records its SHA-256 without fetching. It grants no authority to import unrestricted system trust. PEM extraction omits some browser trust restrictions; the private bundle is not a complete reproduction of browser policy. See STATE-AND-RECOVERY §9.

# SEE ALSO

aslice(1), aslice-doctor(1), MANUAL.md §8
