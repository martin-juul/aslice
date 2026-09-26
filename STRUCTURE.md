# Project structure

This document is the authority for organizing the aslice repository. It defines
where contributors place durable project material and how the C++ implementation
is organized. Paths marked planned below do not yet exist in the tracked tree.

## Directory responsibilities

| Path | Status | Responsibility |
|---|---|---|
| `docs/` | Existing | Durable aslice specifications, guides, policies, and operational documentation. |
| `docs/sqlite/` | Existing | Executable SQLite schema companions owned by [DATABASE](docs/DATABASE.md); these are specification assets, not runtime services. |
| `docs/runbooks/` | Existing | Standalone operational runbooks for project bring-up, signing, and recovery. See the [runbooks index](docs/runbooks/README.md). |
| `docs/refs/` | Existing | Supporting source archive, with captured references, provenance, licenses, and checksums. See the [archive guide](docs/refs/README.MD). |
| `man/` | Existing | Command manuals. See the [manual index](man/README.md). |
| `schematics/` | Existing | Machine-readable contracts for project formats and build interfaces. See the [schematics guide](schematics/README.md). |
| `tests/` | Existing | Validation code, regression tests, and fixtures. |
| `.agents/skills/` | Existing | Repository automation skills and their supporting instructions and scripts. |
| `src/` | Existing | C++ implementation and private headers, grouped by the subsystem responsibilities below. |
| `include/aslice/` | Planned | Headers deliberately exposed to consumers outside the implementation. |
| `.github/workflows/` | Existing | Required Linux quality/sanitizer, native Windows analysis/test, and documentation CI gates. |
| `tools/` | Existing | Reusable developer utilities, including Windows dependency bootstrap; the Homebrew formula importer remains planned. |

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

## Implementation layout

| Path | Responsibility |
|---|---|
| `src/cli/` | Command registry, generated help, argument validation, exit statuses, and JSON output. |
| `src/core/` | Bounded JSON/file reads, shared errors, and SHA-256 support. |
| `src/package/` | Validated identities, targets, candidates, versions, constraints, artifact manifests, and slice containers. |
| `src/adapters/` | Unsigned fixture catalog, inline payload, and retained-generation JSON translation. |
| `src/resolver/` | Candidate selection, dependency consistency, and profile collision checks. |
| `src/store/` | Immutable fixture payload import and verification. |
| `src/profile/` | Generation construction, activation, inspection, and rollback checks. |
| `src/platform/` | Native file creation and POSIX directory synchronization, ownership, and locking. |
| `src/db/` | Bounded read-only database snapshot queries. |

Portable package, resolver, store, and profile sources compile on both Windows
and POSIX hosts. Platform operations live in separate translation units selected
by CMake. Windows supports exclusive archive output; installation prefix locking
and activation currently require POSIX. These are internal interfaces, not a
public SDK or completed production installer. CMake follows those dependencies: core
package and resolver libraries do not link the fixture adapter; store and profile
libraries use it explicitly.

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
