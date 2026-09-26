% ASLICE-REPO(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-repo — manage package repositories and their trust

# SYNOPSIS

`aslice repo add` *url* [`--trust local`]

`aslice repo list` [`--sources-diff`] [`--json`]

`aslice repo enable` *name*

`aslice repo disable` *name*

`aslice repo remove` *name*

`aslice repo re-pin` *name*

`aslice repo keys` *name*

`aslice repo audit` *name*

`aslice repo allow-system-patch` *name*

`aslice repo deny-system-patch` *name*

`aslice repo build` *path*

`aslice repo sign` *path* [`--sign-with` *ed25519*|*openpgp*]

`aslice repo publish` *path*

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

# ARGUMENTS AND OPERATIONS

*url* names the signed repository to add. *name* is its registered local name;
list reports the configured repositories. **enable** makes a listed source usable;
**disable** stops using it, and **remove** removes the configured source. These
verbs do not authorize another repository with the same name to inherit its trust.
Installed packages remain in the store and retained generations, but the removed
namespace stops resolving. Doctor may propose an explicit replacement plan; it
cannot reparent packages automatically.

**keys** displays repository keys. **re-pin** explicitly replaces retained key
authority after independent verification; ordinary authenticated sequential TUF
rotation needs no re-pin. It cannot silently repair an unauthenticated key change.

**allow-system-patch** records a verified repository's explicit patch grant;
**deny-system-patch** revokes it. The grant does not waive per-operation system-change
consent. Third-party repositories cannot receive this capability. Revocation does
not itself restore installed patches; use system-patch restore.

For **build**, *path* is the orchard or bare manifest directory; **sign** and
**publish** consume the resulting repository tree. Signing applies configured keys;
publishing pushes to the configured transport. **--sign-with** selects `ed25519`
or `openpgp`; the detailed key-selection and unattended signing syntax are
unspecified. Output-directory and transport-selection options are also unspecified.
Official publication
still requires owner-approved inputs, all gates, verified returned signatures,
and atomic publication; these commands do not bypass that pipeline.

**--trust local** admits a `file://` tree as local. The CLI cannot grant official
or verified trust; verified status requires the project's countersignature.
**--sources-diff** shows changes from the last source-list TUF update. **--json**
renders the list for scripts. Audit re-verifies every target in the current
snapshot and reports signing scheme, key, and coverage, in addition to trust state.

# EXAMPLES

```sh
aslice repo add https://repo.example.org
aslice repo list
aslice repo list --sources-diff
aslice repo add file:///Volumes/Packages/repo --trust local
aslice repo keys audiolab
aslice repo audit audiolab
aslice repo enable audiolab
aslice repo allow-system-patch audiolab
aslice repo deny-system-patch audiolab
aslice repo disable audiolab
aslice repo remove audiolab
aslice repo build ./orchard
aslice repo sign ./repo
aslice repo publish ./repo
```

# EXIT STATUS

The common statuses in [aslice(1)](aslice.1.md#exit-status) apply where
relevant: 0 success, 1 error or recovery required, 2 plan refused, 4 contention
without unresolved recovery, and 130 safely completed cancellation. No additional
family-specific numeric statuses are specified.

# SEE ALSO

aslice(1), [MANUAL §9](../docs/MANUAL.md#repositories-trust-and-staying-offline),
[REPOSITORIES §7](../docs/REPOSITORIES.md#aslice-repo-command-surface-completed)
