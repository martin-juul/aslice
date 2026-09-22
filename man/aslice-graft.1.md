% ASLICE-GRAFT(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-graft — review and withdraw installer-script approvals

# SYNOPSIS

`aslice graft approvals` [`--json`]
`aslice graft revoke` *package*…

# DESCRIPTION

A **graft** is a vendor installer script a package genuinely cannot do without — audio DSP drivers, pro-video plugins, kext installers. It is the sole exception to aslice's no-package-code-at-install rule, and it is fenced:

* Declared in the formula as `[[binary.graft]]` with the script's path, SHA-256, and an exhaustive **behavior manifest**: what it may write, which kexts or daemons it may install, whether it may touch the network, whether it needs elevation.
* Shown before anything is extracted or executed. The approval prompt names the script, its hash, and every declared capability; answering no stops the install on the spot.
* Sandboxed to its declaration. The manifest doubles as the graft's Seatbelt profile; a deviation aborts the install, rolls the generation back, and is logged — unsuppressibly.
* Recorded. Every write the graft makes is captured in the state database, so uninstall and rollback reverse the footprint completely; files the graft overwrote are backed up first.
* Rehearsed. For the core and extended orchards the build farm runs each graft in a per-OS VM and signs the manifest into the index only when observed behavior matches the declaration exactly. A graft whose manifest is unsigned — third-party orchards — prints a prominent warning, and its approval is never remembered: you are asked every time, and it cannot be allow-listed.

**approvals** lists recorded approvals: package, version, graft hashes, when granted, and whether the manifest was signed. An approval binds to the exact script hashes — a changed script asks again.

**revoke** withdraws recorded approvals for the named packages. The next install of a revoked package asks again.

There is no "always allow" and no global switch. The nearest thing is the `[grafts]` allow-list in `aslice-machine.toml` (SETUP.md §2.8), which suppresses the prompt for named packages whose manifests are signed — never the display, and never for unsigned manifests. For non-interactive installs, `aslice install --accept-grafts` (aslice-install(1)) consents for that run only; refusal is exit status 2.

# EXIT STATUS

**0** success; **1** error.

# SEE ALSO

aslice(1), aslice-install(1), aslice-machine(1), MANUAL.md §4.5, SETUP.md §2.8, PACKAGE-FORMAT.md §3.11, DESIGN.md §12.15
