# aslice Schematics — Machine-Readable File Schemas

- **Status:** v0.1 — September 2026
- **Scope:** one schema for every file format aslice reads or writes, kept beside the prose specifications that define those formats.
- **Vocabulary:** [../docs/NOMENCLATURE.md](../docs/NOMENCLATURE.md).

## What this directory is

Every file aslice parses — formulas, lock files, machine documents, configuration, plans, index snapshots — has a prose specification in `docs/`, and now a machine-readable schema here. The prose owns the semantics; the schematic owns the structure. The pairing rule, per format:

| File | Format | Schematic | Prose specification |
|---|---|---|---|
| `package.toml` | TOML | [`toml/package.tosd`](toml/package.tosd) | PACKAGE-FORMAT.md §3 |
| `aslice.lock` | TOML | [`toml/lock.tosd`](toml/lock.tosd) | PACKAGE-FORMAT.md §7 |
| `aslice-machine.toml` | TOML | [`toml/machine.tosd`](toml/machine.tosd) | SETUP.md §2 |
| `etc/aslice.toml` (config) | TOML | [`toml/config.tosd`](toml/config.tosd) | MANUAL.md §13 |
| `./aslice.toml` (project pins) | TOML | [`toml/project.tosd`](toml/project.tosd) | DESIGN.md §12.9 |
| `/opt/aslice/etc/sources.toml` | TOML | [`toml/sources.tosd`](toml/sources.tosd) | REPOSITORIES.md §2 |
| `repo.toml` | TOML | [`toml/repo.tosd`](toml/repo.tosd) | *proposed — see below* |
| `plan.json` | JSON | [`json/plan.schema.json`](json/plan.schema.json) | DESIGN.md §12.2 |
| index snapshot | JSON | [`json/index-snapshot.schema.json`](json/index-snapshot.schema.json) | DESIGN.md §9.6 |
| TUF metadata | JSON | [`json/tuf/*.schema.json`](json/tuf/) | upstream TUF 1.0 specification |
| `build.star` | Starlark | [`starlark/build.schema.star`](starlark/build.schema.star) | PACKAGE-FORMAT.md §6.3 |
| `tests.star` | Starlark | [`starlark/tests.schema.star`](starlark/tests.schema.star) | AUTHORING.md §6 |

## The three schema languages

One rule picks the language: **the schema is written in the file's own family.** TOML files get [TOML Schema](https://tomlschema.org) (`.tosd` — TOML documents describing TOML documents). JSON files get [JSON Schema](https://json-schema.org) draft 2020-12 (JSON describing JSON). Starlark files get **starlarkschema**, defined below — Starlark describing Starlark, built for this project because nothing off the shelf does the job.

The TUF schematics under `json/tuf/` are local copies derived from the upstream TUF 1.0 specification, shipped so a validator never has to fetch a schema to check repository metadata. Where they and the upstream spec disagree, upstream wins and the copy is a bug — report it.

## Authority and precedence

The prose specifications in `docs/` are authoritative for semantics; the schematics here are the machine-checkable structural companion. If a schematic and its prose specification disagree, the disagreement is a bug — file an issue against whichever is wrong. This mirrors ORCHARD-POLICY.md §1's mechanism/policy split.

Three honesty rules govern the directory:

1. **A schematic never invents a field.** Every key, enum, and pattern traces to a prose specification section, named in the file's own metadata. Where the prose is silent — see *Derived schematics* below — the schematic says so in its metadata and in this README.
2. **Unknown keys are errors everywhere.** Every TOML schematic here is a closed table at every level, matching the house rule (PACKAGE-FORMAT §3, SETUP §2.1): a file written for a newer aslice fails on an older one, outright, never half-applied. The JSON schematics set `additionalProperties: false` to the same end.
3. **What a schema cannot say, lint still checks.** Cross-field and cross-file rules — the `type = "binary"` exclusions of PACKAGE-FORMAT §3.11, the derived 32-bit `max_os` ceiling, `[grafts] allow` entries naming packages the machine file installs — are beyond both schema languages' expressiveness (TOML Schema 1.0 has no cross-path rules by design). They remain `aslice lint` semantic checks; the schematics list the important ones in their metadata so nobody mistakes schema-valid for valid.

## Derived schematics

Four schematics cover ground the prose specifies only in part. Each is faithful to every field the prose names, and each names the gap in its metadata:

- **`json/plan.schema.json`** — DESIGN §12.2 establishes the plan/apply split and that plans are JSON; the field layout is derived from the lock-file record (PACKAGE-FORMAT §7.2) plus the consent gates a plan must surface (DESIGN §12.11, §12.15).
- **`json/index-snapshot.schema.json`** — DESIGN §9.6 fixes the transport (zstd JSON snapshots + diffs) and the per-package tags (versions, build identities, OS bounds, flavors, arch, source hashes); ORCHARD-POLICY §8 adds permanent tombstones; REPOSITORIES §3 adds signed graft manifests. The concrete JSON layout is derived from those statements.
- **`toml/repo.tosd`** — NOMENCLATURE defines a repository as "a Git repository of formulas with a `repo.toml`", but no prose section enumerates its keys yet. This schematic is the proposed minimal shape: the `namespace` the repository serves (REPOSITORIES §2) plus human-facing metadata. It deliberately contains no trust level — trust is assigned by the client, never claimed by the file (REPOSITORIES §1, axiom 2).
- **`toml/project.tosd`** — DESIGN §12.9 and aslice-use(1) fix the content (one file pinning every runtime to a stream; streams like `8.4`, never exact patches) but not the table header. This schematic fixes it as `[pins]`, the project-layer sibling of the machine file's `[runtimes.default]`.

## starlarkschema — the Starlark schema format (v1.0.0)

Starlark is a language, not a data format, so "the schema is a document in the same family" means: a starlarkschema is a **Starlark module that evaluates to data** — one global named `schema`, a dict. Starlark's determinism (no network, no file access, no recursion bomb, no `eval`) makes it safe to evaluate an untrusted schema; a validator loads it in an empty environment and reads the `schema` global.

A starlarkschema describes a **module surface**, not a syntax tree: which top-level functions the harness calls, their signatures, and which host-provided names (the `ctx` object) the module may touch. Helper functions are idiomatic Starlark, so unknown top-level definitions are allowed by default; the schema's job is to pin the *contract* — entry points and host surface — not to forbid helpers.

### Document shape

```python
schema = {
    "version": "1.0.0",          # required; starlarkschema language version
    "target": "build.star",      # required; the file this schema governs
    "description": "...",        # optional
    "entry_points": { ... },     # required; functions the harness calls
    "host": { ... },             # required; host-provided names (ctx and friends)
    "types": { ... },            # optional; named reusable type descriptors
    "allow_unknown_globals": True,  # optional; default True
}
```

Unknown keys inside `schema` are schema-load errors, as are unknown keys inside any descriptor (the optional `description` excepted). Schema files use the extension `.schema.star`.

### Entry points

`entry_points` maps a function name to a descriptor:

- `"required"` — bool, default False. A required entry point missing from the target module is a validation error.
- `"params"` — list of parameter descriptors, in order: `{"name": "ctx", "type": "ctx"}`. A parameter may carry `"default"` (any literal) to mark it optional. A descriptor `{"varargs": True}` as the last entry permits arbitrary extra positional arguments (the `ctx.run(argv…)` shape).
- `"returns"` — a type descriptor; default `"none"`.
- `"description"` — optional; any descriptor at any level may carry one.

A target module's entry point must match its signature exactly: same positional parameter names in the same order, no extra required parameters. `def build(ctx):` satisfies a one-parameter `ctx` signature; `def build(ctx, extra):` does not.

### Host surface

`host` maps a host-provided global name to a descriptor. Objects use `"kind": "object"` with a `"members"` dict; member values are type descriptors, or nested objects, or callables:

```python
"ctx": {
    "kind": "object",
    "members": {
        "prefix": "string",
        "jobs": "int",
        "run": {
            "kind": "function",
            "params": [{"name": "argv0", "type": "string"}, {"varargs": True}],
            "returns": "none",
        },
        "env": {
            "kind": "object",
            "members": {
                "set": {"kind": "function", "params": [
                    {"name": "key", "type": "string"},
                    {"name": "value", "type": "string"},
                ]},
            },
        },
    },
},
```

A member access not present in the surface — `ctx.network()`, say — is a validation error. That is the sandbox story made checkable: the schema *is* the capability list (PACKAGE-FORMAT §6.3), so an attempt to reach beyond it fails statically, before the sandbox ever has to.

### Type descriptors

A type descriptor is a string: `"string"`, `"int"`, `"float"`, `"bool"`, `"none"`, `"any"`, `"list"`, `"dict"`, or a name defined in the schema's own `"types"` table. `"types"` maps a name to a descriptor or to an object/callable shape; references are local to the document, and there is no cross-file import (the TOML Schema 1.0 boundary, kept deliberately).

### Validation semantics

Validation has two phases, matching the family convention:

1. **Schema load.** The schema module is evaluated in an empty environment; the result must contain a `schema` dict conforming to this section. Unknown keys, missing required keys, unresolvable type names, and malformed signatures are schema-load errors. A schema that fails to load validates nothing.
2. **Module validation.** The target module is parsed (never executed). Checks, in order: every required entry point exists and is a function; every entry-point signature matches; every host-global member access resolves against `host`; if `allow_unknown_globals` is False, every top-level definition is declared. Keyword arguments at call sites are matched by name against the callee's declared parameters where the callee is a host function.

Validation never executes target code, and a validator never evaluates a schema with the target's `ctx` present. Diagnostics carry the phase, a code, and the target's source position; the CLI exit contract follows the family: 0 valid, 1 invalid, 2 unusable invocation or schema-load failure.

### What starlarkschema deliberately does not check

Data flow, argument *values*, sandbox policy (enforced at runtime by the sandbox itself, DESIGN §10.5), and helper-function internals. The schema pins the contract between harness and module; everything behind that contract is the author's business.

## Versioning

Each schematic versions with the prose specification it tracks, and its metadata names that specification's version at time of writing. The directory's own version (top of this file) bumps when any schematic changes.
