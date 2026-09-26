% ASLICE-REPO(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-repo — manage package repositories and their trust

# SYNOPSIS

`aslice repo add` *url*

`aslice repo list`

`aslice repo enable`|`disable`|`remove` *name*

`aslice repo re-pin`|`keys`|`audit` *name*

`aslice repo allow-system-patch`|`deny-system-patch` *name*

`aslice repo build`|`sign`|`publish` *path*

# DESCRIPTION

aslice consumes packages from repositories — static, signed trees of metadata, index, formulae, and blobs. The project's official repository is pre-pinned at bootstrap; others are added explicitly. Every repository has an enforced trust level, which is a capability set, not a label:

**official**
:   The project's own. Pre-pinned; may serve binaries, root daemons, kexts, and `[system-patch]`.

**verified**
:   Community repositories countersigned by the project. Ship listed-but-disabled; `enable` turns one on, and enabling is the consent — its binaries install immediately. May serve the privileged categories; `[system-patch]` only under an explicit per-repo grant (`allow-system-patch`, refused by default, revocable).

**third-party**
:   Added by you. Key fingerprint pinned on first use (TOFU) and displayed for out-of-band verification; authenticated sequential TUF root rotation needs no re-pin; unauthenticated replacement blocks updates pending independent verification. Binaries install once added, always with an unambiguous `third-party/<name>` provenance line; the privileged categories are closed to it by construction.

**local**
:   Your own `file://` tree. Formulae by default; on your own machine it carries the same authority as acting by hand, including the privileged categories.

**audit** shows trust state, countersignature validity, and staleness. Only core packages use bare names. All other repositories require `repo:package`, including `extended:package`; equal suffixes are distinct identities. There is no overlap prompt, remembered preference, or automatic fallback ([REPOSITORIES §10](../docs/REPOSITORIES.md#overlapping-packages-across-repositories)).

**build**, **sign**, **publish** compile an orchard into a repository tree, apply keys, and push to a transport — the same pipeline the project itself runs. See [AUTHORING §11](../docs/AUTHORING.md#publishing-your-own-orchard-and-repository).

Refresh uses immutable authenticated indexes, bounded diffs, and staged activation.
Mirror retries retain the same repository and selected release; integrity failures
are reported even after a successful retry. A missing required repository blocks
the transaction. An unrelated outage does not block independently authorized inputs.
Virtual providers, aliases, and replacements cannot cross namespaces without
explicit retained selections; namespace reuse never transfers repository identity.

# SEE ALSO

aslice(1), [MANUAL §9](../docs/MANUAL.md#repositories-trust-and-staying-offline), REPOSITORIES.md
