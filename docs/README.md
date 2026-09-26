# aslice documentation

[Back to the project overview](../README.md).

aslice is in the design phase; there is no release to install yet. These documents
describe the intended system. Implementation and platform validation remain work
to be done.

## Suggested reading paths

- **Users:** [User manual](MANUAL.md) → [Declarative setup](SETUP.md) → [Command reference](../man/).
- **Package authors:** [User manual, chapters 1–4](MANUAL.md) → [Authoring guide](AUTHORING.md) → [Package format](PACKAGE-FORMAT.md) → [Orchard policy](ORCHARD-POLICY.md).
- **Implementers:** [Design](DESIGN.md) → [State and recovery](STATE-AND-RECOVERY.md) → the subsystem specifications relevant to your work in the catalog below.

## Document catalog

### Guides and vocabulary

| Document | Purpose |
|---|---|
| [Manual](MANUAL.md) | User workflows for installing, running, and managing software. |
| [Authoring](AUTHORING.md) | Writing, testing, and shipping packages. |
| [Nomenclature](NOMENCLATURE.md) | Project terms, acronyms, and their Homebrew equivalents. |

### Architecture and contracts

| Document | Purpose |
|---|---|
| [Design](DESIGN.md) | Platform scope, architecture, security model, and roadmap. |
| [State and recovery](STATE-AND-RECOVERY.md) | Artifact identity, privilege boundaries, transactions, replay, and acceptance gates. |
| [Slice format](SLICE-FORMAT.md) | Binary archive layout, manifests, verification, and extraction limits. |
| [Package format](PACKAGE-FORMAT.md) | Package definitions, dependency and version semantics, lock files, and the build API. |
| [Setup](SETUP.md) | Declarative machine configuration and the semantics of applying, exporting, and importing it. |
| [Helpers](HELPERS.md) | Client process roles, privileged operations, runtime shims, and package services. |
| [System volumes](SYSTEM-VOLUMES.md) | Protected-volume patching, Recovery procedures, boot snapshots, and undo. |

### Build and operations

| Document | Purpose |
|---|---|
| [Build infrastructure](BUILD-INFRA.md) | The shared local and farm build harness, scheduling, worker trust, testing, and publication. |
| [Toolchain](TOOLCHAIN.md) | The compiler bundle, build integration, bootstrap, and version updates. |
| [Repositories](REPOSITORIES.md) | Official sources, third-party repositories, trust levels, and signing. |
| [Orchard policy](ORCHARD-POLICY.md) | Package acceptance, variants, maintenance, review gates, and release policy. |
| [Genesis](GENESIS.md) | Bringing the project into existence and rebuilding it after a total loss. |
| [Key runbook](KEY-RUNBOOK.md) | Signing-key setup, rotation, recovery, and drills. |

### Design context

| Document | Purpose |
|---|---|
| [Homebrew review](HOMEBREW-REVIEW.md) | Capability comparison, design gaps, and resulting specification amendments. |

## Supporting resources

- [Command manuals](../man/) — command syntax, options, examples, and exit statuses.
- [Machine-readable schematics](../schematics/README.md) — schemas and examples for data contracts.
- [Reference archive](refs/README.MD) — locally preserved sources and their catalog.
- [Contributing guidelines](../CONTRIBUTING.md) — contribution workflow and checks.
- [Repository structure](../STRUCTURE.md) — where content belongs and the planned C++ layout.
- [Security policy](../SECURITY.md) — reporting vulnerabilities and the project's security boundaries.
