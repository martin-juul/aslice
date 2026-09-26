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

* Declared in the formula as `[[binary.graft]]` with the script's path, SHA-256, and an exhaustive **behavior manifest**: what it may write, which kexts or daemons it may install, whether it requests elevation. Network access is reserved but refused in v1.
* Shown before anything is extracted or executed. The approval prompt names the script, its hash, and every declared capability; answering no stops the install on the spot.
* Sandboxed to its declaration. The script runs in an isolated staged filesystem view. The helper validates and commits the declared delta; the script receives no direct privileged RPC. Undeclared effects abort staging and are logged.
* Recorded. The committed delta and before-images enter the durable journal. Reversal checks intervening edits and may require attention; it cannot reverse remote effects or application data migrations.
* Rehearsed. For the core and extended orchards the build farm runs each graft in a per-OS VM and publishes authenticated recipe and behavior-manifest digests only after the required per-OS rehearsal succeeds. A graft whose manifest is unsigned — third-party orchards — prints a prominent warning, and its approval is never remembered: you are asked every time, and it cannot be allow-listed.

**approvals** lists recorded approvals: package, version, graft hashes, when granted, and whether the manifest was signed. An approval binds to the script hashes and complete behavior-manifest digest; a change to either asks again. Effective operations also require the repository system or system-patch capability where applicable; graft approval cannot bypass those gates.

**revoke** withdraws recorded approvals for the named packages. The next install of a revoked package asks again.

There is no "always allow" and no global switch. The nearest thing is the `[grafts]` allow-list in `aslice-machine.toml` ([SETUP §2.8](../docs/SETUP.md#grafts)), which suppresses the prompt for named packages whose manifests are signed — never the display, and never for unsigned manifests. For non-interactive installs, `aslice install --accept-grafts` (aslice-install(1)) consents for that run only; refusal is exit status 2.

# EXIT STATUS

**0** success; **1** error.

# EXAMPLES

```sh
aslice graft approvals --json
aslice graft revoke audiolab:convolver
```

# SEE ALSO

aslice(1), aslice-install(1), aslice-machine(1), [MANUAL §4.5](../docs/MANUAL.md#grafts-when-installing-takes-a-script), [SETUP §2.8](../docs/SETUP.md#grafts), [PACKAGE-FORMAT §3.11](../docs/PACKAGE-FORMAT.md#binary--vendor-binaries-pkgdmg-only-software), [DESIGN §12.15](../docs/DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)
