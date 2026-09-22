# tests.schema.star — starlarkschema v1.0.0 for tests.star
#
# Target:  tests.star in a package directory (package.toml build.test = true)
# Corpus:  AUTHORING §6 ("Testing"), PACKAGE-FORMAT §6.4
#
# tests.star defines exactly one entry point, test(ctx), which aslice
# invokes after build.star install() has staged the package. The script
# asserts that the staged result works: run a binary, check output, compare
# files. A test script that raises (fail()) or exits non-zero fails the
# package build.
#
# Environment guarantees (PACKAGE-FORMAT §6.4):
#   - no network by default; network only when package.toml declares
#     [build].test_network = true (and the user permits it)
#   - the package's staged install tree is read-only outside the test
#     scratch directory
#   - the build sandbox is gone: tests see the *result*, not the recipe
#
# The host ctx here is deliberately minimal — tests are assertions over a
# finished artifact, not build logic. The full build surface lives in
# build.schema.star.

schema = {
    "version": "1.0.0",
    "target": "tests.star",
    "description": "aslice package test script: one test(ctx) entry point, run after install staging; no network unless [build].test_network",

    "entry_points": {
        # def test(ctx): — the only entry point. Typically:
        #     ctx.run(ctx.prefix + "/bin/ffmpeg", "-version")
        "test": {
            "required": True,
            "params": [{"name": "ctx", "type": "ctx"}],
            "returns": "none",
        },
    },

    "host": {
        "ctx": {
            "kind": "object",
            "members": {
                # Absolute path of the staged install tree (what install()
                # produced under the destdir). Read-only.
                "prefix": "string",

                # Run a program and require exit status 0. argv0 may be an
                # absolute path (usually ctx.prefix + "/bin/<tool>") or a
                # bare name resolved on PATH. Non-zero exit fails the test.
                # Examples:
                #     ctx.run(ctx.prefix + "/bin/ffmpeg", "-version")
                #     ctx.run("grep", "-q", "needle", path)
                "run": {
                    "kind": "function",
                    "params": [
                        {"name": "argv0", "type": "string"},
                        {"varargs": True},
                    ],
                    "returns": "none",
                },
            },
        },
    },

    # tests.star files occasionally define small local helper functions;
    # that is idiomatic and allowed.
    "allow_unknown_globals": True,
}
