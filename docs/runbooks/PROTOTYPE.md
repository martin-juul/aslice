# Building the prototype

The prototype exercises portable C++20 code on development hosts. It implements
`aslice --help`, `aslice --version`, and `aslice db schema [--role ROLE]`.
Schema defaults to `client-state`; the other roles are `client-cache`,
`system-state`, `coordinator`, `publisher`, and `release-signer`.

`aslice dev fixture` runs an unsigned fixture package lifecycle in a disposable
prefix. It exercises package selection, dependency resolution, the store, profile
links, generation activation, upgrade, rollback, and removal together.

Bare invocation and command groups print help without opening a prefix. For a
command's arguments, options, examples, and platform limits, use
`aslice help artifact verify` or `aslice artifact verify --help`. Missing required
leaf arguments and unknown options return exit 2. The former unreleased
`prototype` command group has been removed; stored `.prototype.json` markers,
`aslice-prototype-1` data, and fixture artifact identities remain unchanged.

## Portable package and container commands

These commands run with CLion's bundled MinGW as well as on POSIX hosts:

```sh
aslice version normalize v7.1
aslice version compare 1.1.1.11 1.1.1
aslice version matches 1.6.43 ">=1.6, <1.7"
aslice dev fixture resolve --catalog tests/fixtures/prototype/catalog-v1.json hello
aslice artifact inspect tests/fixtures/artifact-manifest.json
```

`resolve` requires no prefix and writes no files. It accepts simulated
`--target-os`, `--flavor`, and `--prerelease` options. Version ordering implements
epoch, three or four numeric components, and SemVer prereleases. Normalization
accepts the upstream forms in PACKAGE-FORMAT, including lettered patches.
Constraints support equality, comparisons, caret, tilde, comma intersections, and
`||` unions. Prereleases require explicit admission; a prerelease bound admits
prereleases of that same numeric version. Numeric core components are bounded by
unsigned 64-bit integers. Resolver package revisions, provider variants, and
conditional dependencies remain pending.

Manifest inspection validates the artifact-manifest fields and semantic checks:
OS ranges, unique dependencies, file inventory, case collisions, transitive
symlinks, and relocation bounds and bindings. It computes the artifact identity
from canonical JSON, including UTF-16 object-key ordering. ABI records are checked
structurally; this does not inspect Mach-O binaries or prove ABI compatibility.
The illustrative repository fixture can be inspected but does not match a real
payload. For a manifest with actual file hashes:

```sh
aslice artifact verify manifest.json --payload payload
aslice slice pack manifest.json payload example.slice
aslice slice inspect example.slice
```

Payload verification checks kinds, file sizes and SHA-256, link targets, unlisted
entries, and relocation expected bytes. POSIX also checks file/directory modes;
Windows reports `posix_modes_verified: false`. Paths currently use a conservative
ASCII subset. Unicode normalization remains pending. Local manifest input is
capped at 4 MiB, nesting at 64 levels, inventory at 100,000 entries, and regular
payload bytes at 1 GiB. These are lower prototype limits than the release contract.

`slice pack` creates a new output file exclusively, after validating the payload. It
emits canonical metadata, sorted inventory members, normalized POSIX tar headers,
and one zstd frame at level 3. Its JSON output records the packer and zstd version;
this is not signed provenance. Existing output is never overwritten. A write or
flush failure may leave a partial new output file; it is not registered or installed.

`slice inspect` verifies the container, canonical descriptor/manifest bindings, member
order, checksums, payload hashes and relocation bytes, and archive termination.
It rejects extra members, hardlinks, special files, special mode bits, concatenated
frames, and trailing compressed bytes. The current tar subset uses short ASCII
names (at most 100 bytes including `payload/`); pax extension and prefix headers
are refused. Packing and inspection cap compressed input/output at 16 MiB and
expanded tar at 64 MiB. Decoding uses an 8 MiB window ceiling and a cooperative
five-second check. The archive is buffered in memory; these are not total process
memory or hard execution deadlines.

All artifact/container results report `authenticated: false`. These are local
inspection tools and do not extract into a prefix or authorize installation.
TUF, package signatures, index/recipe agreement, descriptor-based extraction,
relocation application, and installed receipts remain pending. Same-user filesystem
races and hostile-prefix access are outside this adapter's guarantees.

Run a complete portable packing demonstration from the checkout:

```powershell
python tools/demo-slice.py build/windows-clion/aslice.exe
```

## Run the package lifecycle

After building the development image, run the complete demonstration:

```sh
docker run --rm --network none --entrypoint sh aslice-prototype /src/tools/demo-prototype.sh
```

The demonstration creates a temporary prefix, installs `hello` and its `greeting`
dependency, executes the installed program, upgrades both, rolls back, verifies
the store, uninstalls `hello`, and removes its orphaned dependency. It prints
`hello 1.0.0: dependency 1.0.0`, then version 2.0.0, then version 1.0.0 again.
Its temporary prefix is removed on exit.

To explore manually inside the container:

```sh
docker run --rm -it --network none --entrypoint sh aslice-prototype
/build/aslice dev fixture init --prefix /tmp/aslice-play
/build/aslice dev fixture install hello --prefix /tmp/aslice-play --catalog /src/tests/fixtures/prototype/catalog-v1.json
/tmp/aslice-play/profiles/default/bin/hello
/build/aslice dev fixture list --prefix /tmp/aslice-play
```

Commands also include `search`, `info`, `plan`, `why`, `leaves`, `history`, and
`verify`. Mutations accept `--dry-run` except initialization. `plan` is always
read-only. Prefixes must be new, private, and explicitly selected. A marker
distinguishes these disposable prefixes from future production installations.

The fixture catalog has its own `aslice-prototype-1` format, with inline text
payloads. It is neither an authenticated index nor a `.slice` archive. It uses
the portable version and constraint implementation described above. Namespaces,
OS floors, and v1/v2/v3 selection are exercised. Initialize
with `--target-os` and `--flavor` to simulate a target; these options do not detect
host capabilities or establish package executability on that target.

The bounded backtracking solver is an experiment, not the specified PubGrub
implementation. Fixture identities hash normalized fixture JSON, not production
RFC 8785 artifact manifests. Files are imported into separate read-only store
trees and generations link to exact fixture identities. Case-insensitive ASCII
path collisions refuse. Install prefers existing selections; upgrade selects the
newest compatible requested closure. Uninstall retains orphaned dependencies until
autoremove. All complete generations are retained; garbage collection is absent.

Generation activation uses a flushed symlink rename under a prefix lock.
`ASLICE_PROTOTYPE_FAILPOINT=before-switch` and `after-switch` exercise the two
activation boundaries. Prepared generations may remain after a failed activation;
history lists available generations, not a proven committed operation log.
These checks do not establish power-loss recovery. Signed repositories, archive
extraction, TOML/Starlark builds, variants, relocation, ABI checks, privilege
separation, production journals, services, machine setup, and self-update remain
unimplemented. The fixture lifecycle currently uses generation JSON rather than
the production state database. Same-user filesystem races and hostile-prefix
recovery are not supported by this adapter.

## CLion on Windows

For CLion's bundled MinGW, install matching development headers and libraries:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/bootstrap-windows.ps1
```

The script pins vcpkg to the revision in `vcpkg.json`, disables its telemetry, and
installs JSON, OpenSSL, zstd, and tl-expected 1.3.1 into `build/windows-deps/x64-mingw-static`. CMake detects
that location for MinGW builds, including the ordinary CLion Debug profile.
Reload the CMake project after installation. The `windows-clion` CMake preset
also names the bundled compiler and Ninja at the default per-user CLion location.
For another installation location, pass `-ClionRoot` to the bootstrap and use
CLion's configured toolchain instead of that preset.

CMake copies the bundled MinGW runtime DLLs beside the executables, so the
development build also runs from an ordinary terminal without CLion's compiler
directory on `PATH`. Keep those DLLs with the executable when moving this build.

OpenSSL stays a real required dependency in Windows builds; its declarations and
portable callers are compiled and linked. The same holds for zstd. Native Windows
builds support CLI, version/resolver, manifest, container, and query tests.
The POSIX filesystem lifecycle runs in Docker/WSL;
a native Windows invocation reports that limitation. A CLion WSL or Docker
toolchain can compile and debug the POSIX implementation as well.

An installed JSON package is preferred; if absent, CMake downloads the
checksum-pinned 3.12.0 release. Linux local builds require OpenSSL development
headers and libraries, plus the zstd development package. These host development dependencies do not establish the
release linkage or macOS toolchain contract.

CMake embeds the SQL from [docs/sqlite](../sqlite) into the executable at configure
time and reconfigures when those files change. The executable needs no checkout,
prefix, database, or network to print a schema. It rejects unsupported arguments
before printing SQL, with exit 2. Output failures return 1; successful output
returns 0. Examples put role selection after `schema`; the existing
`aslice db --role ROLE schema` ordering is also accepted.

## Docker Desktop

Use Linux containers and run from the repository root:

```sh
docker build -t aslice-prototype .
docker run --rm aslice-prototype --version
docker run --rm aslice-prototype db schema --role publisher
docker run --rm --entrypoint ctest aslice-prototype --test-dir /build --output-on-failure
```

The build downloads Ubuntu packages for LLVM 20 (compiler, formatter, and analyzer),
libc++, CMake, Ninja, and Python.
CMake downloads SQLite 3.51.3 and checks both the pinned archive SHA-256 and the
published source SHA3-256 before compiling it as a static library. Extension
loading is compiled out. Compiler, VFS, and macOS release qualification remain
pending; the source pin alone does not establish a release build.
The Dockerfile is a development environment with distribution-managed versions;
it is not a pinned release toolchain. Rebuild the image after source changes.

## Local build

On a Linux development host with Clang, libc++, CMake 3.20 or newer, Ninja, and
Python 3 installed (network access is required for the initial SQLite download):

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_CXX_FLAGS=-stdlib=libc++
cmake --build build
cmake --build build --target format-check tidy
ctest --test-dir build --output-on-failure
./build/aslice db schema
```

For an offline build, extract the same SQLite amalgamation archive into a local
directory and add `-DFETCHCONTENT_SOURCE_DIR_SQLITE=/path/to/sqlite-amalgamation-3510300`
to the configure command. The source checksum remains mandatory. Initial downloads require network access. The expected library is pinned to 1.3.1
with its reviewed archive checksum; an installed matching package is preferred.

CTest runs the compiled executable from temporary directories, compares all six
schemas to the specification, executes each in SQLite, and tests argument
refusals. Python's SQLite library creates test fixtures only; query-engine tests
execute against the pinned C library.

## Query engine

The internal `aslice_db` library reads a supplied standalone snapshot in memory.
It checks the application ID, role/schema version, and identity against an
independently supplied instance and owner. It uses defensive mode, query-only
connections, disabled trusted schema, an SQL authorizer with a function allowlist,
and a read-only deserialized database. Virtual tables, writes, PRAGMAs, transaction
control, unbound parameters, EXPLAIN, and non-whitespace statement tails refuse.
SELECT, read-only CTEs, and ordinary views are tested.

Queries have ceilings of 5 seconds, 10,000 rows, and 16 MiB of serialized data.
The engine buffers output and returns an explicit error on failure, discarding partial rows. Its
JSON data object preserves duplicate column names, nulls, base64 BLOBs, and large
integers as decimal strings. Invalid UTF-8 and non-finite floating-point values
refuse instead of silently changing data. Limits may be lowered for tests.

Prototype resource limits also cap snapshot input at 32 MiB, SQLite heap at
64 MiB, SQL at 64 KiB, columns at 128, expression depth at 100, compound SELECTs
at 10, and compiled VM instructions at 25,000. Output buffering uses separate C++
memory. The SQLite heap ceiling is process-wide, so this component belongs in a
dedicated inspection process. A progress handler bounds SQLite execution; it is
not a hard real-time deadline for every allocation or built-in function.

`tests/query_driver.cpp` supplies a test-only adapter for synthetic snapshots.
It does not authorize access to an installation. The public `aslice db query`
command remains unavailable until owner-approved snapshot export, provisioning,
filesystem ownership checks, process isolation, and the command envelope exist.
The engine is not a database health check or a recovery authority.

## macOS validation

Linux execution does not establish the macOS 10.11–12 contract. The release build
still needs the [self-hosted toolchain](../TOOLCHAIN.md), static libc++, the v1 CPU
floor, and execution on each claimed OS. Installation, recovery, trust, and
self-update remain unimplemented.

The supplied [WSL walkthrough](https://dev.to/nicole/running-macos-on-windows-10-with-wsl2-kvm-and-qemu-21e1)
now reports that its procedure no longer works. Use
[OSX-KVM](https://github.com/kholia/OSX-KVM) as a separate VM investigation:
first verify KVM access and guest creation, then QEMU/OpenCore and the intended
guest OS. A visible `/dev/kvm` alone does not prove a usable macOS guest. No VM,
installer, SDK, or Windows/WSL configuration change is part of this prototype.
