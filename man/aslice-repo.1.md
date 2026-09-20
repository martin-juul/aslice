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
`aslice repo prefer`|`resolutions`|`forget`
`aslice repo allow-system-patch`|`deny-system-patch` *name*
`aslice repo build`|`sign`|`publish` *path*

# DESCRIPTION

aslice consumes packages from repositories — static, signed trees of metadata, index, formulae, and blobs. The project's official repository is pre-pinned at bootstrap; others are added explicitly. Every repository has an enforced trust level, which is a capability set, not a label:

**official**
:   The project's own. Pre-pinned; may serve binaries, root daemons, kexts, and `[system-patch]`.

**verified**
:   Community repositories countersigned by the project. Ship listed-but-disabled; `enable` turns one on, and enabling is the consent — its binaries install immediately. May serve the privileged categories; `[system-patch]` only under an explicit per-repo grant (`allow-system-patch`, refused by default, revocable).

**third-party**
:   Added by you. Key fingerprint pinned on first use (TOFU) and displayed for out-of-band verification; any later change is a loud, blocking event until deliberately re-pinned. Binaries install after enabling; the privileged categories are closed to it by construction.

**local**
:   Your own `file://` tree. Formulae by default; on your own machine it carries the same authority as acting by hand, including the privileged categories.

**audit** shows a repository's trust state, countersignature validity, and staleness. **resolutions** shows remembered answers to same-name overlaps between peer repositories; **prefer** sets one explicitly; **forget** clears it. Explicit addressing (`repo:pkg`) bypasses overlap resolution entirely.

**build**, **sign**, **publish** compile an orchard into a repository tree, apply keys, and push to a transport — the same pipeline the project itself runs. See AUTHORING.md §11.

# SEE ALSO

aslice(1), MANUAL.md §9, REPOSITORIES.md
