# starlarkschema for build.star — a formula's custom build logic.
# Format: schematics/README.md, "starlarkschema" (v1.0.0). This file is data:
# a validator evaluates it in an empty environment and reads the `schema` global.
# Prose specification: docs/PACKAGE-FORMAT.md §6 (v0.15), docs/AUTHORING.md §4.
#
# The harness calls the phase functions in order (configure → build → install),
# inside the sandbox of DESIGN §10.5. A build.star that defines none of them is
# dead weight — that is a lint finding, not a schema rule, because which phases
# a package needs is the package's business.

schema = {
    "version": "1.0.0",
    "target": "build.star",
    "description": "Custom build logic for [build] system = \"custom\" (PACKAGE-FORMAT §6.3). Runs only at build time, in the sandbox: no network, filesystem confined to the build directory.",
    "allow_unknown_globals": True,  # helper functions are idiomatic Starlark

    "entry_points": {
        "configure": {
            "params": [{"name": "ctx", "type": "ctx"}],
            "description": "Prepare the build tree; called after unpack/patch.",
        },
        "build": {
            "params": [{"name": "ctx", "type": "ctx"}],
            "description": "Compile; called after configure.",
        },
        "install": {
            "params": [{"name": "ctx", "type": "ctx"}],
            "description": "Stage the payload into ctx.staging; the pack phase turns staging into the slice.",
        },
    },

    "types": {
        # The entire capability surface of the script (PACKAGE-FORMAT §6.3).
        # Anything beyond this table is a sandbox escape; file a bug against
        # aslice instead of reaching for one.
        "ctx": {
            "kind": "object",
            "members": {
                "prefix": "string",        # final store path this build will occupy
                "staging": "string",       # DESTDIR staging directory
                "jobs": "int",             # parallelism granted by the scheduler
                "flavor": "string",        # "v1" / "v2" / "v3"; the -march floor is already in CC/CXX
                "min_os": "string",        # deployment target; already exported as MACOSX_DEPLOYMENT_TARGET
                "user_cflags": "string",   # install-time user flags (DESIGN §7.4); recorded, never identity-affecting
                "user_ldflags": "string",
                "deps": "dict",            # name -> store path of each resolved build+runtime dependency
                "variant": {
                    "kind": "function",
                    "params": [{"name": "name", "type": "string"}],
                    "returns": "bool",
                    "description": "Variant assignment for this build.",
                },
                "env": {
                    "kind": "object",
                    "description": "Controlled environment; reads of the host env are denied.",
                    "members": {
                        "set": {
                            "kind": "function",
                            "params": [
                                {"name": "key", "type": "string"},
                                {"name": "value", "type": "string"},
                            ],
                        },
                        "append": {
                            "kind": "function",
                            "params": [
                                {"name": "key", "type": "string"},
                                {"name": "value", "type": "string"},
                            ],
                        },
                    },
                },
                "run": {
                    "kind": "function",
                    "params": [
                        {"name": "argv0", "type": "string"},
                        {"varargs": True},
                    ],
                    "description": "Exec, argv-array only — no shell, no string interpolation.",
                },
                "make": {
                    "kind": "function",
                    "params": [
                        {"varargs": True},
                        {"name": "jobs", "type": "int", "default": 0},
                        {"name": "destdir", "type": "string", "default": ""},
                    ],
                    "description": "Tool helper with correct defaults (§6.3).",
                },
                "cmake": {
                    "kind": "function",
                    "params": [{"varargs": True}],
                    "description": "Tool helper with correct defaults (§6.3).",
                },
                "meson": {
                    "kind": "function",
                    "params": [{"varargs": True}],
                    "description": "Tool helper with correct defaults (§6.3).",
                },
                "patch": {
                    "kind": "function",
                    "params": [{"name": "file", "type": "string"}],
                    "description": "Apply a checksummed patch from patches/.",
                },
                "replace": {
                    "kind": "function",
                    "params": [
                        {"name": "file", "type": "string"},
                        {"name": "pattern", "type": "string"},
                        {"name": "replacement", "type": "string"},
                    ],
                    "description": "In-place text substitution for trivial fixups; count-checked — zero replacements is a build error (§6.3).",
                },
            },
        },
    },

    # The harness provides one global: ctx, of the shape declared in "types".
    "host": {
        "ctx": "ctx",
    },
}
