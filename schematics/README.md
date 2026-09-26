# aslice Schematics — Machine-Readable File Schemas

- **Status:** v0.5 — September 2026
- **Scope:** schemas for the public formats listed below; internal journal/service records require implementation specifications before those features ship, kept beside the prose specifications that define those formats.
- **Vocabulary:** [../docs/NOMENCLATURE.md](../docs/NOMENCLATURE.md).

## What this directory is

Each public format below has a prose contract defining its semantics and a structural schema describing its shape. Internal transaction journals, privileged authorization messages, certificate-policy inventories, and recovery-kit formats still need implementation specifications under STATE-AND-RECOVERY; this directory does not establish their completeness. The table pairs each format with its schema and prose contract:

| File | Format | Schematic | Prose specification |
|---|---|---|---|
| `package.toml` | TOML | [`toml/package.tosd`](toml/package.tosd) | [PACKAGE-FORMAT §3](../docs/PACKAGE-FORMAT.md#packagetoml--full-schema) |
| `aslice.lock` | TOML | [`toml/lock.tosd`](toml/lock.tosd) | [PACKAGE-FORMAT §7](../docs/PACKAGE-FORMAT.md#lock-files) |
| `aslice-machine.toml` | TOML | [`toml/machine.tosd`](toml/machine.tosd) | [SETUP §2](../docs/SETUP.md#the-file) |
| `etc/aslice.toml` (config) | TOML | [`toml/config.tosd`](toml/config.tosd) | [MANUAL §13](../docs/MANUAL.md#configuration-reference) |
| `./aslice.toml` (project pins) | TOML | [`toml/project.tosd`](toml/project.tosd) | [DESIGN §12.9](../docs/DESIGN.md#multi-version-runtimes-use-pin-default--and-version-bound-extensions) |
| `/opt/aslice/etc/sources.toml` | TOML | [`toml/sources.tosd`](toml/sources.tosd) | [REPOSITORIES §2](../docs/REPOSITORIES.md#the-shipped-source-list) |
| `repo.toml` | TOML | [`toml/repo.tosd`](toml/repo.tosd) | *proposed — see below* |
| `plan.json` | JSON | [`json/plan.schema.json`](json/plan.schema.json) | [DESIGN §12.2](../docs/DESIGN.md#interaction-principles) |
| `.slice` container descriptor (`slice.json`) | JSON inside pax tar + Zstandard | [`json/slice.schema.json`](json/slice.schema.json) | [SLICE-FORMAT.md](../docs/SLICE-FORMAT.md) |
| canonical artifact manifest | JSON | [`json/artifact-manifest.schema.json`](json/artifact-manifest.schema.json) | [STATE-AND-RECOVERY §1](../docs/STATE-AND-RECOVERY.md#compatibility-and-artifact-identity) and [STATE-AND-RECOVERY §2](../docs/STATE-AND-RECOVERY.md#abi-and-execution-requirements) |
| exact package record | JSON | [`json/package-record.schema.json`](json/package-record.schema.json) | [STATE-AND-RECOVERY §8](../docs/STATE-AND-RECOVERY.md#plans-locks-archives-and-offline-use) |
| archive catalog | JSON | [`json/archive-catalog.schema.json`](json/archive-catalog.schema.json) | [STATE-AND-RECOVERY §8](../docs/STATE-AND-RECOVERY.md#plans-locks-archives-and-offline-use) |
| index snapshot | JSON | [`json/index-snapshot.schema.json`](json/index-snapshot.schema.json) | [DESIGN §9.6](../docs/DESIGN.md#the-repository-system) |
| TUF metadata | JSON | [`json/tuf/*.schema.json`](json/tuf/) | upstream TUF 1.0 specification |
| `build.star` | Starlark | [`starlark/build.schema.star`](starlark/build.schema.star) | [PACKAGE-FORMAT §6.3](../docs/PACKAGE-FORMAT.md#buildstar--the-custom-api) |
| `tests.star` | Starlark | [`starlark/tests.schema.star`](starlark/tests.schema.star) | [AUTHORING §6](../docs/AUTHORING.md#tests) |

## The three schema languages

One rule picks the language: **the schema is written in the file's own family.** TOML files get [TOML Schema](../docs/refs/TOML_SCHEMA_SPECIFICATION.MD) (`.tosd` — TOML documents describing TOML documents). JSON files get [JSON Schema core](../docs/refs/JSON_SCHEMA_2020_12_CORE.MD) and [validation](../docs/refs/JSON_SCHEMA_2020_12_VALIDATION.MD), draft 2020-12 (JSON describing JSON). Starlark files get **starlarkschema**, defined below — Starlark describing Starlark, built for this project because nothing off the shelf does the job.

The TUF schematics under `json/tuf/` are local copies derived from the upstream TUF 1.0 specification, shipped so a validator never has to fetch a schema to check repository metadata. Where they and the upstream spec disagree, upstream wins and the copy is a bug — report it.

Automatic official publication ([KEY-RUNBOOK §2.1](../docs/runbooks/KEY-RUNBOOK.md#21-automatic-orchard-to-client-publication)) changes orchestration, not these schemas. Merge authorization, gate receipts, candidate/base identity, and durable signing state are internal records whose service formats remain to be implemented; do not add them as top-level TUF or index fields. Renewals use the existing TUF `version` and `expires` fields, snapshot metadata bindings, and timestamp's `snapshot.json` reference. Unchanged-content renewal preserves target bytes, including the index: its `snapshot_version` is a format version, not a TUF release counter. Ed25519/minisign signature formats are unchanged. Schema validation alone cannot verify authorization, freshness, atomic publication, or signing-state consistency; those require the runbook's service checks and acceptance drills.

## Authority and precedence

The prose specifications in `docs/` are authoritative for semantics; the schematics here are the machine-checkable structural companion. If a schematic and its prose specification disagree, the disagreement is a bug — file an issue against whichever is wrong. This mirrors [ORCHARD-POLICY §1](../docs/ORCHARD-POLICY.md#purpose-and-precedence)'s mechanism/policy split.

Three honesty rules govern the directory:

1. **A schematic never invents a field.** Every key, enum, and pattern traces to a prose specification section, named in the file's own metadata. Where the prose is silent — see *Derived schematics* below — the schematic says so in its metadata and in this README.
2. **Unknown structural keys are errors.** Fixed TOML tables and JSON objects reject unknown fields. Declared collections, such as runtime names, environment variables, and variants, intentionally accept dynamic keys under their item rules. A TOML table with no fixed children is open under the archived language specification; it must not be used to claim closed-table enforcement.
3. **Structural validation is only one gate.** Cross-file rules, payload-derived CPU/OS requirements, capability authorization, and artifact verification still require semantic checks. Conditional rules expressible in a schema should also be encoded where practical; schema validity alone never establishes a safe installation.

## Recovery contracts

The version-1 recovery record, receipt, head, initialization, gate, export,
checkpoint, recovery-plan, execution-catalog, operation-request, and operation-outcome schemas
implement the structural contracts in
[STATE-AND-RECOVERY §10.2](../docs/STATE-AND-RECOVERY.md#102-recovery-engineering-contracts).
Their fixtures use illustrative hashes and signatures and are not authenticated
recovery sets. Field descriptions and closed object shapes are normative;
cryptographic authority, canonical bytes, chain continuity, current fingerprints,
cross-owner ordering, and filesystem durability require semantic/runtime checks.
Run `python -m unittest discover -s tests -p test_recovery_contract.py` for structural
and decision-model cases. These models do not execute helper effects or simulate
macOS power loss.

## Derived schematics

Four schematics cover ground the prose specifies only in part. Each is faithful to every field the prose names, and each names the gap in its metadata:

- **`json/plan.schema.json`** — [DESIGN §12.2](../docs/DESIGN.md#interaction-principles) establishes the plan/apply split and that plans are JSON; the field layout is derived from the lock-file record ([PACKAGE-FORMAT §7.2](../docs/PACKAGE-FORMAT.md#format)) plus the consent gates a plan must surface ([DESIGN §12.11](../docs/DESIGN.md#system-patches-flagged-reversible-replacement-of-apple-provided-files) and [DESIGN §12.15](../docs/DESIGN.md#vendor-install-scripts-grafts--declared-approved-monitored-reversible)).
- **`json/index-snapshot.schema.json`** — [DESIGN §9.6](../docs/DESIGN.md#the-repository-system) fixes the transport (zstd JSON snapshots + diffs) and the per-package tags (versions, build identities, OS bounds, flavors, arch, source hashes); [ORCHARD-POLICY §8](../docs/ORCHARD-POLICY.md#deprecation-and-removal-lifecycle) adds permanent tombstones; [REPOSITORIES §3](../docs/REPOSITORIES.md#trust-levels) adds signed graft manifests. The concrete JSON layout is derived from those statements.
- **`toml/repo.tosd`** — NOMENCLATURE distinguishes the Git recipe orchard from its signed static distribution repository. `repo.toml` describes the published repository; its complete field set remains a schema proposal. This schematic is the proposed minimal shape: the `namespace` the repository serves ([REPOSITORIES §2](../docs/REPOSITORIES.md#the-shipped-source-list)) plus human-facing metadata. It deliberately contains no trust level — trust is assigned by the client, never claimed by the file ([REPOSITORIES §1](../docs/REPOSITORIES.md#axioms), axiom 2).
- **`toml/project.tosd`** — [DESIGN §12.9](../docs/DESIGN.md#multi-version-runtimes-use-pin-default--and-version-bound-extensions) and aslice-use(1) fix the content (one file pinning every runtime to a stream; streams like `8.4`, never exact patches) and the `[runtimes]` table header. This schematic uses `[runtimes]`, the project-layer sibling of the machine file's `[runtimes.default]`.

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
- `"params"` — list of parameter descriptors, in order: `{"name": "ctx", "type": "ctx"}`. A parameter may carry `"default"` (any literal) to mark it optional. A descriptor `{"varargs": True}` permits arbitrary extra positional arguments; any following parameters must carry `"keyword_only": True` (the `ctx.run(argv…)` shape).
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

A member access not present in the surface — `ctx.network()`, say — is a validation error. The schema expresses the capability list ([PACKAGE-FORMAT §6.3](../docs/PACKAGE-FORMAT.md#buildstar--the-custom-api)), allowing the validator to reject access outside that list before runtime sandbox enforcement.

### Type descriptors

A type descriptor is a string: `"string"`, `"int"`, `"float"`, `"bool"`, `"none"`, `"any"`, `"list"`, `"dict"`, or a name defined in the schema's own `"types"` table. `"types"` maps a name to a descriptor or to an object/callable shape; references are local to the document, and there is no cross-file import (the TOML Schema 1.0 boundary, kept deliberately).

### Validation semantics

Validation has two phases, matching the family convention:

1. **Schema load.** The schema module is evaluated in an empty environment; the result must contain a `schema` dict conforming to this section. Unknown keys, missing required keys, unresolvable type names, and malformed signatures are schema-load errors. A schema that fails to load validates nothing.
2. **Module validation.** The target module is parsed (never executed). Checks, in order: every required entry point exists and is a function; every entry-point signature matches; every host-global member access resolves against `host`; if `allow_unknown_globals` is False, every top-level definition is declared. Keyword arguments at call sites are matched by name against the callee's declared parameters where the callee is a host function.

Validation never executes target code, and a validator never evaluates a schema with the target's `ctx` present. Diagnostics carry the phase, a code, and the target's source position; the CLI exit contract follows the family: 0 valid, 1 invalid, 2 unusable invocation or schema-load failure.

### What starlarkschema deliberately does not check

Data flow, argument *values*, sandbox policy (enforced at runtime by the sandbox itself, [DESIGN §10.5](../docs/DESIGN.md#sandboxed-builds)), and helper-function internals. The schema pins the contract between harness and module; everything behind that contract is the author's business.

## Versioning

Each schematic versions with the prose specification it tracks, and its metadata names that specification's version at time of writing. The directory's own version (top of this file) bumps when any schematic changes.

## History

<details>
<summary>Document revision history</summary>

| Version | Date | Changes |
|---|---|---|
| v0.3 | September 2026 | Consolidate revision notes into a collapsible history table; no specification changes. |
| v0.2 | September 2026 | prose rewrite of the schema directory introduction and host-member validation explanation; no content changes. |
| v0.4 | September 2026 | Documentation audit repairs: contract summaries aligned; owner-approved namespace, rollback, GC, naming, prefix, and graft decisions applied where relevant; semantic anchors and explicit citations added. Runtime implementation and platform acceptance remain pending. |
| v0.5 | September 2026 | Add version-1 recovery records, receipts, initialization/heads, catalogs, gates, exports, signed checkpoints, recovery plans, and command request/outcome schemas with illustrative fixtures and decision-model tests. Runtime verification remains pending. |

</details>
