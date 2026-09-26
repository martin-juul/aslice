# Project structure

This document is the authority for organizing the aslice repository. It defines
where contributors place durable project material and how the C++ implementation
will be organized. The project is in its design phase; planned paths below do not
yet exist in the tracked tree.

## Directory responsibilities

| Path | Status | Responsibility |
|---|---|---|
| `docs/` | Existing | Durable aslice specifications, guides, policies, and operational documentation. |
| `docs/runbooks/` | Existing | Standalone operational runbooks for project bring-up, signing, and recovery. See the [runbooks index](docs/runbooks/README.md). |
| `docs/refs/` | Existing | Supporting source archive, with captured references, provenance, licenses, and checksums. See the [archive guide](docs/refs/README.MD). |
| `man/` | Existing | Command manuals. See the [manual index](man/README.md). |
| `schematics/` | Existing | Machine-readable contracts for project formats and build interfaces. See the [schematics guide](schematics/README.md). |
| `tests/` | Existing | Validation code, regression tests, and fixtures. |
| `.agents/skills/` | Existing | Repository automation skills and their supporting instructions and scripts. |
| `src/` | Planned | C++ implementation and private headers, grouped by subsystem. |
| `include/aslice/` | Planned | Headers deliberately exposed to consumers outside the implementation. |
| `tools/` | Planned | Reusable developer utilities, including the planned Homebrew formula importer. |

## Durable documentation and work records

Reserve `docs/` for documentation that continues to describe aslice after a task
ends. Keep task plans, documentation audits, coverage reports, remediation
tracking, and scratch output outside the tracked tree. Use issues, pull requests,
or external temporary storage for these work records. Record lasting decisions
in the relevant specification, guide, or policy so readers can find the current
rules without reconstructing a task's history.

Place standalone operational runbooks under `docs/runbooks/`. Keep procedures
embedded in specifications with the contracts they explain. The source archive under
`docs/refs/` supports that documentation and retains its own preservation rules.
Writing conventions and checker instructions are maintained in
[CONTRIBUTING.md](CONTRIBUTING.md#documentation-style).

## Planned implementation layout

Organize `src/` by subsystem, keeping implementation files and private headers
together. Place a header under `include/aslice/` only when it is deliberately
exposed beyond the implementation; this reserved path does not establish a public
C++ API. Keep tests and fixtures in `tests/`, and reusable developer utilities in
`tools/`.

Create planned directories when they contain real implementation. Do not add
placeholder folders to reproduce this layout. Generated build output belongs in
ignored build directories, such as `build/`, `out/`, or `cmake-build-*/`, already
covered by [`.gitignore`](.gitignore). These guidelines do not select a build
system or define a dependency-management policy.

## Root-level files and new directories

Keep root-level files limited to project entry points, contributor policies,
licensing, and repository or build configuration. The existing `README.md`,
`CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`, and Git configuration files serve
those purposes; this document supplies the repository organization policy.

Every new top-level directory must have a distinct purpose documented here when
it is introduced. Extend an existing directory when its responsibility already
covers the new material.
