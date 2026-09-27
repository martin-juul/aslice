# Darwin compatibility environment

This backend runs Intel macOS binaries inside a dedicated Linux VM using Darling.
It is separate from the **modeled platform** used by `run`, `client`, `replay`
and `coverage`. Neither backend substitutes for the other. Production builds
and physical Mac qualification remain unchanged.

Machine management, an authenticated controller, a guest agent and a browser
console are implemented. The initial environment is **incomplete**: Cocoa input,
document persistence, full LLDB debugging, isolation and aslice compatibility
still require acceptance evidence. Infrastructure tests do not pass those gates.

## Feasibility gate

The chosen runtime is [Darling](https://github.com/darlinghq/darling), pinned to
commit `60ba801decee7a00782f74f6be4c8ffb013f79ff`. The guest target is Ubuntu 26.04
x86-64. The commit pins the source tree and its direct gitlinks; a provisioned
runtime must additionally record recursive submodule identities, build commands,
compiler, exact package manifest and hashes of all downloaded/build artifacts.
Provisioning retains downloaded packages, versions and hashes, compiler output,
submodule identities, runtime patches and the debugger archive hash. Initial
package resolution still uses Ubuntu repositories; a recorded manifest does not
by itself provide a complete offline rebuild recipe.
Use the upstream [build instructions](https://docs.darlinghq.org/build-instructions.html)
to investigate build requirements; installing their unversioned package list
does not establish a reproducible runtime identity.

Run preflight without creating a machine:

```sh
python -m tools.simulator machine doctor --output build/darwin-preflight.json
python -m tools.simulator machine doctor --acceleration tcg
```

Windows selects WHPX and Linux selects KVM. Software emulation requires explicit
`--acceleration tcg` and is reported as such. Missing tools, unsupported hosts
and inaccessible KVM are reported with exit status 1. Exit status 0 means the
tool checks passed, not that acceleration can boot a VM. QEMU's advertised
accelerators are not a successful WHPX/KVM initialization probe. Every report
keeps `boot_verified` and `complete` false until execution verification exists.
The current report records host OS, architecture and processor description;
CPUID feature capture still needs implementation in the VM execution lane.

On the implementation host, Darling built and installed in an Ubuntu VM using
KVM under WSL. The unchanged Intel macOS hyperfine 1.20.0 artifact printed its
version, spawned shell children, wrote a file and exported JSON. These measured
CLI results do not qualify Cocoa or debugging. No Mac-built source corpus,
matching symbols, aslice binaries or SDK was supplied.

LLDB initially crashed while launching its shell helper: Darling's `execve`
implementation dereferenced a null environment pointer. The separate runtime
patch `runtime-patches/0002-execve-empty-environment.patch` treats that pointer
as an empty environment. With the patch, LLDB stopped at an address breakpoint
in unchanged hyperfine, stepped an instruction and returned stacks. A runtime-built
probe also allowed attachment and stack inspection. Expression evaluation and
process termination still showed failures; source and child debugging remain
unqualified. Repeated attachment also triggered a Darling server panic while its
launcher service remained active. The health API distinguishes an active launcher
from an observed live server; process presence alone does not prove responsiveness.
The Mac corpus builder includes an empty-environment reproduction
whose native execution is checked by the corpus workflow.

The browser displayed the real guest through noVNC. A Cocoa probe built against
Darling's replacement libraries created a window, but its contents stayed black.
That probe tests infrastructure only. Unchanged Hex Fiend 2.12 failed to load the
Tcl framework; version 2.7 failed on a missing DiskArbitration callback symbol.
These failures leave Cocoa rendering, input and document persistence unqualified.

## Checked corpus

The Apache-2.0 corpus source is in [tests/simulator/corpus](../../tests/simulator/corpus).
Build on a Mac with its own SDK:

```sh
python tests/simulator/corpus/build.py --output build/mac-corpus
python -m tools.simulator machine corpus build/mac-corpus/corpus.json
```

The builder produces four thin x86-64 Mach-O executables, matching dSYM files,
source and license copies, compiler/SDK/command provenance and SHA-256 identities.
The CLI probe writes and renames a file, then forks and execs a child. The Cocoa
probe has a window, input, button and menu action. The document probe adds
open/save dialogs. The debugger probe exposes `parent_marker` and `child_marker`
for source breakpoints. These sources have not yet been compiled or run on a Mac.

The corpus checker validates hashes, Intel executable headers, load-command
bounds and executable/dSYM UUID agreement. It refuses path traversal, links,
universal binaries, missing debugger symbols and artifacts over 512 MiB.
Its zero exit status means all four corpus roles were ingested successfully.
It does not verify the declared build origin, execute code or grant compatibility
credit. Darling-built entries remain infrastructure-only candidates. The checked
manifest's `complete` field stays false even with all artifacts present.

Acceptance must exercise the unchanged Mac-built artifacts inside the dedicated
VM. Record CLI output and file contents, visible rendering and real input for
both GUI probes, and document persistence after restart. LLDB/debugserver must
demonstrate launch, attachment, source mapping, breakpoints, stepping, threads,
stacks and variables in the parent and exec'd child. Logs alone cannot pass GUI
or debugger acceptance. Runtime defects need minimal reproductions and separate,
reproducible patches. No preload hooks, binary rewriting or simulator-specific
application rebuilds may satisfy unchanged-binary acceptance.

## Stopped-image management

Install `qemu-img` on the host. Supply a standalone raw or qcow2 base image plus
a runtime identity JSON object. The identity schema is version 1, with exactly
these fields:

| Field | Required value |
| --- | --- |
| `version` | `1` |
| `guest` | `ubuntu-26.04-x86_64` |
| `darling_commit` | The pinned 40-character commit above |
| `submodules` | Nonempty map of recursive source paths to 40-character Git commits |
| `artifacts` | Nonempty map of build-input names to SHA-256 digests |
| `build` | Nonempty strings `compiler`, `packages`, `command`, `source_tree` |

`packages` must identify the exact guest package manifest; include that manifest
in the hashed artifacts. Include the guest image, compiler, source archives,
dependencies and runtime outputs in the build records. The parser checks the
shape of these declarations. It does not independently attest their completeness
or prove that the declared runtime is installed in the supplied image.

```sh
python -m tools.simulator machine --root build/darwin-machines create dev --image build/guest/base.qcow2 --runtime build/guest/runtime.json
python -m tools.simulator machine --root build/darwin-machines status
python -m tools.simulator machine --root build/darwin-machines snapshot create dev clean
python -m tools.simulator machine --root build/darwin-machines clone dev experiment
python -m tools.simulator machine --root build/darwin-machines snapshot restore dev clean
python -m tools.simulator machine --root build/darwin-machines delete experiment
```

Creation defaults to four virtual CPUs, 8192 MiB RAM and a sparse 64 GiB qcow2
overlay. Override `--cpus`, `--memory-mib` and `--disk-gib` before creation. The
base is copied into the store by content identity and shared by overlays. Base
images with backing chains, external data files or encryption are refused.
Disk size must accommodate the base's virtual size. The Darling prefix resides
inside the guest disk.

All mutations require an exclusive OS lease. Process death releases the lease;
another controller can reopen the store and report interrupted operation records.
Operations journal intent before changing image state. Copies publish only after
completion and file synchronization. This provides host-process interruption
recovery, not a claim about host power-loss durability. Directory fsync and a
physical power-loss validation remain necessary for that milestone.

Snapshots and clones require metadata state `stopped`. Restore verifies base,
runtime and snapshot disk identities, copies into a new disk, then atomically
switches the metadata pointer. The previous disk remains available. Interrupted
copies and incomplete machines remain visible for diagnosis. Deletion moves the
machine into the store's `trash` directory; it does not erase disks or shared
bases. Overlay backing paths are absolute: moving the store is unsupported.
The supervisor holds a machine lease while QEMU runs. The controller discovers
surviving supervisors after restart. Do not boot these disks through external
QEMU commands: external processes do not participate in that ownership protocol.

## Remaining implementation and acceptance

The environment must use one authenticated, versioned control API for CLI and
console. Host credentials must remain outside guest storage. Provision ordinary
and administrative guest accounts, remove Darling's default guest-host directory
exposure, and verify that guest privilege cannot grant host authority. The VM
must expose no host mounts, clipboard, devices or credentials by default. Network
access must default off and provisioning downloads must be separate from app
execution. Explicit imports and exports must be bounded and recoverable.

After the binary/GUI/debugger proof, implement startup, graceful and forced stop,
restart and rediscovery of surviving VMs without duplicate launches. Test actual
VM ownership, controller crashes, transfers and restoration. A stopped-image
unit test is not evidence for those live-machine requirements.

The loopback console must bundle xterm.js and noVNC locally, display the software
rendered guest X11 session and label it as an application display rather than a
macOS desktop. Provide lifecycle controls, terminal, process/service/filesystem/
network inspectors, interactive debugging, a searchable event timeline and
diagnostic bundles. Browser disconnection must leave application processes alive;
debugger detach/terminate must be explicit. Bound captured output and preserve
truncation notices. Guest LLDB/debugserver handles Mach-O debugging; Linux tools
handle the Darling runtime itself.

Fault controls must distinguish requested placement, acknowledged effects,
observed effects and uncertain outcomes. Implement process/service interruption,
network loss, disk-full and VM forced stop. Precise filesystem and durability
faults belong at the runtime/storage boundary; a VM kill is not proof of macOS
power-loss semantics. Keep deterministic replay in the modeled platform. Binary
scenarios initially use snapshot restoration and re-execution with explicit
nondeterministic differences.

Record exact runtime, guest, CPU capabilities, compiler, dependencies, binaries,
symbols and corpus identities in generated evidence under ignored `build/`.
Only a dedicated VM execution lane can qualify representative CLI/Cocoa behavior,
debugging, isolation and lifecycle recovery. The preparation CI lane cannot.
Actual aslice compatibility remains pending until Mac-built aslice binaries and
symbols exist. Missing package features remain application gaps. Finder, Metal-
heavy applications, general GUI compatibility, real kexts and full Recovery are
outside the initial milestone; physical Mac qualification remains separate.

## Troubleshooting and tests

For a missing `qemu-img`, install QEMU image utilities and rerun preflight. For
an identity mismatch, preserve the store and inspect the base/runtime/snapshot
hashes; do not edit metadata to bypass validation. For an incomplete creation or
copy, inspect `operations`, retained `.partial` files and the active disk pointer.
Never delete the lease file to take ownership from another process. Keep the
store private to the host user; path checks do not defend against a hostile
process already running as that user.

```sh
python tests/simulator/test_darwin.py
python tests/simulator/test_runtime.py
python tests/simulator/test_guest_agent.py
python -m tools.simulator coverage --gate development --output build/requirement-coverage.json
```

The host suite tests ownership, process-crash reconciliation, interrupted copies,
identity mismatches, restore retention and corpus refusal. If `qemu-img` is
available it also creates and checks real qcow2 overlays. Otherwise that test
reports an explicit skip. Synthetic disk and Mach-O fixtures never constitute
Darling compatibility evidence.

Controller tests cover authentication, concurrent ownership, supervisor crashes
and fragmented guest responses. Guest PTY and transfer tests require a disposable
Linux environment running as root. For browser formatting and lint checks, run
`npm ci` and `npm run check` in `tools/simulator/web`.
Run `npm run build` there to generate the console in `build/simulator-web`.
The npm manifest and lockfile pin xterm.js, noVNC and the build tools. The Python
controller serves the generated JavaScript, CSS and license notices locally;
browser use needs no CDN or npm connection. Rebuild after changing console source
or dependencies. Both `node_modules` and generated assets are ignored by Git.
Without built assets, the controller API still works and the console reports the
setup commands instead of displaying a broken page.

## Developing the console

Use Node.js 24.15 or later in the 24.x line, or Node.js 26 or later.
From `tools/simulator/web`, run `npm ci`, then
`npm run dev`. Vite serves the UI at `http://127.0.0.1:5173` with hot reload.
This mode requires no simulator: an in-memory adapter supplies sample machines,
sessions, inspectors and file transfers. The banner identifies the demo, terminal
input executes no commands, and reloading resets its state. The sample display
supports text input and a button; it supplies no Cocoa compatibility evidence.
Runtime diagnostic downloads require a live controller.

Demo terminal samples let you exercise Unicode and colors, inline images,
percentage and indeterminate progress, pause/error states, truncated output,
connection interruption and process exit. Start a sample machine and open a
terminal, then expand Demo terminal samples. Enable inline images before using
the image sample. Interrupt output followed by Reconnect output exercises cursor
recovery on the same session. Captured demo output is bounded to 64 KiB and uses
the same absolute byte-cursor contract as the guest agent. These controls and
sample generators are excluded from the live JavaScript build.

Append `?scenario=empty`, `?scenario=error` or `?scenario=slow` to exercise an empty
machine list, failed requests or delayed responses. `npm run build:demo` builds
this preview separately in `build/simulator-web-demo`; `npm run preview:demo`
serves it for review.

For live UI development, start `python -m tools.simulator console` and use the
origin and token from its authenticated URL. In PowerShell:

```powershell
$env:SIMULATOR_CONTROLLER_URL = 'http://127.0.0.1:CONTROLLER_PORT'
npm run dev:live
```

Open `http://127.0.0.1:5173/#TOKEN`, replacing `TOKEN` with the console URL's
fragment. The UI exchanges it for the controller's HTTP-only cookie and removes
the fragment. Keep the token private. Vite proxies HTTP and display WebSocket
traffic to the loopback controller; live mode does not fall back to sample data.
`npm run build` generates the assets served by the Python controller. Plain
`npm run preview` (also `npm run serve`) previews these assets without providing
a controller API; use `dev:live` to work against the simulator.

The source kernel, `src/app.ts`, composes the features and builds to `app.js`.
Each feature owns its model, UI behavior and tests. Machine selection, sessions,
inspection and transfers are separate domains; the shared gateway validates
controller responses before passing them to features. Development adapters live
under `src/development` and are excluded from the live build. Rendering uses DOM
APIs; event subscriptions and polling are disposed when the application unloads
or Vite replaces it. noVNC loads when the display is opened.

TypeScript 7 runs with strict checking. `npm run check` checks types, runs
type-aware Oxlint, checks Prettier formatting and runs Vitest. Use
`npm run typecheck:watch`, `npm run test:watch`, `npm run lint:fix` and
`npm run format` during development. `npm run test:coverage` writes its report
under `build/simulator-web-coverage`. These tests cover UI behavior and controller
contracts, not runtime compatibility.

The terminal uses xterm 6 with Unicode 11 character widths. It fits its panel and
sends size changes to the guest PTY. Reconnect output resumes from the last
received cursor without launching a process or replaying input. Input is ordered;
an uncertain write stops later queued input until the session is reselected.
Debugger buttons require a debugger session.

Terminal options enable WebGL rendering with automatic fallback if initialization
fails or its context is lost. Inline SIXEL and iTerm images are optional: the image
cache is limited to 32 MiB, individual images to four megapixels, and encoded
image sequences to 4 MiB. The controller permits WebAssembly compilation for the
image decoder while retaining its restriction on JavaScript string evaluation.
The progress indicator displays values reported by programs through OSC 9;4;
it does not estimate progress for commands that emit no such information.

Export terminal display downloads up to 4000 scrollback rows, capped at 16 MiB,
with text, colors, dimensions and cursor state. It excludes inline images and
process state and is separate from diagnostic evidence. Headless xterm tests
verify serialization and progress parsing without adding a Node.js service to
the controller. Web fonts remain deferred because the published addon requires
a prerelease xterm version; the console uses local system fonts.

## Pinned upstream CLI acquisition

The first available upstream candidate is
[hyperfine 1.20.0](https://github.com/sharkdp/hyperfine/releases/tag/v1.20.0).
Fetch its unchanged Intel macOS executable, source archive and both upstream
licenses into a fresh output directory:

```sh
python -m tools.simulator machine fetch-corpus --output build/upstream-corpus
python -m tools.simulator machine corpus build/upstream-corpus/corpus.json
```

This is an explicit provisioning download, separate from application execution.
The acquisition pins the release archive SHA-256 and the source commit/archive
SHA-256. Each download is bounded to 16 MiB and published only after hash
verification. It copies only named regular files from the release archive and
never executes the binary. Interrupted or mismatched downloads retain partial
files without publishing them as validated artifacts.

The source workflow declares a macOS build runner. Exact compiler and SDK
versions are not captured in the release archive and remain unverified. The
generated acquisition record and corpus manifest preserve that limitation.
The expected CLI scenario launches a shell child, writes a file and exports a
JSON result. This scenario passed in the development VM. No debugger symbols, Cocoa
probe or document probe are supplied by this acquisition, so the corpus command
returns 1 for missing roles. Successful download is not compatibility acceptance.

## Using the machine and console

Install QEMU, OpenSSH and the controller dependencies, then provision a separate
builder. Windows uses WHPX; replace `kvm` below with `whpx` on Windows or explicitly
select `tcg` when software emulation is intended. Provisioning downloads use the
builder's network; application machines default to networking disabled.

```sh
python -m pip install -r tools/simulator/runtime-requirements.txt
python -m tools.simulator machine provision builder --acceleration kvm
python -m tools.simulator machine provision-status builder
python -m tools.simulator machine provision-finalize builder
```

Finalization requires a completed runtime identity and a stopped builder. Use its
returned image and manifest paths as `BASE` and `RUNTIME` below. The base becomes
immutable input to each machine's overlay.

```sh
python -m tools.simulator machine create dev --image BASE --runtime RUNTIME
python -m tools.simulator machine start dev --acceleration kvm
python -m tools.simulator console
python -m tools.simulator machine import dev ./program program --executable
python -m tools.simulator machine exec dev /Users/aslice/Imports/program --version
python -m tools.simulator machine shell dev
python -m tools.simulator machine inspect dev
python -m tools.simulator machine debug dev --program /Users/aslice/Imports/program
python -m tools.simulator machine export dev result.json ./result.json
python -m tools.simulator machine stop dev
```

Transfer paths are relative to the guest Imports directory. Transfers are bounded
to 64 MiB and verify hashes before publication. For exec/shell, place options such
as `--detach` or `--mode linux` before the machine name. Linux mode inspects the
runtime and is explicitly distinct from Darwin application execution.

The console bundles xterm.js and noVNC. It displays guest X11 application windows,
not an Apple desktop. Terminal processes survive browser disconnects. A persistent
guest service keeps Darling alive when a terminal exits. Debugging uses an LLDB
terminal with commands for stepping, breakpoints, threads, stacks, variables and
source mapping. Detach and termination are explicit. Structured debugger views
and unchanged parent/child breakpoint acceptance remain unfinished.
The process inspector shows Linux PIDs and, for nested processes, namespace PIDs.
Use the runtime PID for Darwin debugger attachment and the Linux PID for Linux
debugging. Session labels identify the Linux launcher PID separately.

Inspect `.controller/startup.log`, each machine's `evidence` directory and
`control/ssh.log` for host failures. Use `machine serial NAME` for guest boot output
and `machine health NAME` for sessions and build status. A shutdown request that
does not finish is not a confirmed stop. `machine stop NAME --force` provides an
explicit forced termination.

No host mounts are attached. Complete adversarial guest isolation testing and
removal of Darling's guest-root exposure remain pending; removing convenience
links alone does not establish that boundary. Inspectors currently report Linux
runtime processes and services, not complete Darwin launchd service behavior.
