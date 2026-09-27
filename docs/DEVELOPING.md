# Developing aslice

Use `python dev.py` from the repository root to build, run tests, and launch the
simulator. It orchestrates CMake, CTest, LLVM tools, Docker, and the two web
projects. The optional Makefile delegates to the same commands; it owns no
separate recipes. On Linux, substitute `python3` if necessary.

## First run

Use Python 3.11 or newer. Native C++ development needs CMake, Ninja, a C++20
compiler, and LLVM 22's formatter and analyzer. Windows uses the existing CLion
MinGW preset and [dependency bootstrap](runbooks/PROTOTYPE.md). Linux dependencies
and compiler selection are described in that guide. Docker Desktop must use
Linux containers. Node is needed to build the console, not to run packaged assets;
the web projects declare their supported Node versions in `package.json`.

```sh
python dev.py doctor
python dev.py build
python dev.py test core
python dev.py check
```

`doctor` reports executable locations and missing prerequisites. It does not boot
a VM or claim platform qualification. `build` configures a missing build tree.
Use `configure` after changing configuration, or `--build-dir PATH` before the
command to select another tree. Defaults are `build/windows-clion` on Windows and
`build/native` elsewhere. Tool overrides use `ASLICE_CMAKE`, `ASLICE_CTEST`,
`ASLICE_CLANG_FORMAT`, and `ASLICE_CLANG_TIDY`.

## Which code is real?

The simulator exercises shared implementation through different platform adapters.
The normal executable cannot switch to the modeled backend through an environment
variable. Fixture installation remains a prototype, even when run on a native OS.

| Component | Code | What runs |
|---|---|---|
| Normal CLI | `src/cli/main.cpp`, shared subsystem libraries | Native `aslice`; production-directed implementation with explicitly limited fixture commands. |
| Modeled executable | `src/cli/simulator_main.cpp`, `src/platform/*simulator*` | `aslice-simulator`; the shared C++ operations call a modeled filesystem and process/channel boundary. |
| Model and test orchestration | `tools/simulator/model.py`, `server.py`, `harness.py` | Python model, seeded faults, trace recording, and replay; never shipped as package-manager implementation. |
| Compatibility runtime | `tools/simulator/darwin.py`, `vm.py`, `controller.py`, `guest_agent.py` | Persistent Linux VM running Darwin binaries through Darling, hosted on Windows or Linux. |
| Simulator application | `tools/simulator/application.py`, `tools/simulator/web/` | Launcher, controller connection, terminal, application display, machine controls, and diagnostics. |
| Developer entrypoint | `dev.py`, `tools/dev/` | Build/test/quality/package recipes; delegates to the component owners above. |
| Test peers and probes | `tests/*driver.cpp`, `tests/simulator/`, `tests/simulator/corpus/` | Test-only executables and input programs. These are not installer code. |

The application display has an optional 2015 iMac-style bezel and silver chin,
without a stand. The frame toggle persists independently of the explicit light
and dark appearance toggle. Neither presentation changes guest pixels.

CTest labels make the existing source boundaries selectable without renaming
Python modules used by recorded workflows. Further source moves should split
modeled and runtime tests into separate packages, then move the modeled Python
backend under `tools/simulator/modeled/` and VM/controller code under
`tools/simulator/runtime/`, retaining compatibility imports. Do these as separate
changes with replay checks; changing directories alone does not change evidence.

## Tests and quality checks

| Command | Scope |
|---|---|
| `python dev.py test core` | Shared C++ and native-adapter tests. |
| `python dev.py test modeled` | Shared C++ through modeled boundaries, faults, lifecycle, and replay. |
| `python dev.py test runtime` | VM preparation, controller, and guest-agent tests; unavailable external prerequisites may cause skips. |
| `python dev.py test requirements` | Requirement inventory and evidence rules. |
| `python dev.py test developer` | CLI recipes, packaging, preview, and application lifecycle. |
| `python dev.py test all` | All configured CTests, including archive checks and the developer harness. |
| `python dev.py test web` | Simulator TypeScript, lint, formatting, and unit tests. |
| `python dev.py test library` | Documentation library checks. |
| `python dev.py test browser` | Compiled console browser smoke: appearances, frame, keyboard, narrow layout, content preservation, Console filters, and offline resources. |
| `python dev.py format` | Rewrite owned C++ formatting. |
| `python dev.py format-check` | Check formatting without rewriting. |
| `python dev.py tidy` | Analyze the configured C++ compilation database. |
| `python dev.py check --with-web` | Configure, build, format-check, tidy, CTest, and both web checks. |

Run `python dev.py web simulator setup` and `python dev.py web library setup`
before their first checks. `python dev.py web simulator build` builds live and
demo assets and checks ES5/CSS compatibility. Development Vite requires a modern
browser; compiled assets retain the Safari 9 floor. Automated fallback checks
and compatibility-runtime tests do not establish native OS X acceptance.

For browser checks, install `tools/dev/browser-requirements.txt` with pip and run
`python -m playwright install chromium`. The tests use sample guest data and
write screenshots to `build/reports/console-browser/`.

Commands stop on failure and retain output under `build/reports/<run>/`.
Authentication URLs and machine-command output are not retained by the developer
runner. Ctrl+C terminates an active build/test process tree. A successfully
launched simulator controller has a separate lifetime.

```sh
python dev.py --dry-run check
python dev.py docker check
python dev.py docker check --sanitizers
python dev.py docker application
```

Docker builds use the tracked Dockerfile, including formatting, analysis, and
CTest. Initial builds download dependencies. To reuse a provisioned image,
pass `--reuse-image --image IMAGE`: current source is mounted read-only, networking
is disabled, and build writes remain inside the disposable container. Choose an
image with the required compiler and cached CMake dependencies. Use
`python dev.py compare-coverage --image IMAGE` to compare the complete decoded
native and container requirement reports; matching reports grant no acceptance
credit.

`docker application` uses a disposable Python Linux image, installs the pinned
runtime dependencies, and runs the developer and extracted-package tests against
current source and compiled assets. This command needs network access for image
and Python dependency acquisition; the application browser check separately
verifies that UI resources stay offline.

## Run the simulator application

```sh
python dev.py simulator setup
python dev.py simulator open
```

Setup installs pinned controller dependencies and builds the console. Launch
checks assets, starts or reconnects to the loopback controller, waits for its
authenticated readiness response, and opens the application in your browser.
Use `--no-browser` to print the connection URL. Treat that URL as a credential.
Readiness failure points to `.controller/startup.log`; the failed launch attempt
reaps only the child it created, never a process identified solely by a saved PID.

The browser is the application window on both Windows and Linux. No native Mac
shell is required. Terminal and guest application display take priority over
configuration and diagnostics. Closing a window disconnects that client while
the controller, machine supervisors, and guest sessions remain available.

The Console pane reads the guest's ASL store with `syslog`, unified logging with
`log show`, or `/var/log/system.log`. These are the guest logging sources, separate
from host controller diagnostics and terminal stdout. A missing facility is shown
as unavailable; Darling does not thereby acquire macOS logging compatibility.
New provisioning includes the reader. Existing guests need the updated
`guest_agent.py` and `guest_logs.py` deployed together under `/opt/aslice`, followed
by a guest agent service restart during a maintenance window.

Console provides the source sidebar, Type/Time/Process/Message table, selected
message details, refresh, pause, and Clear view. Queries accept `process:` (`p:`),
`message:` (`m:`), `type:` (`t:`), `subsystem:` (`s:`), `category:` (`c:`), and
`pid:`; quote phrases. Alternatives for one property are ORed, while different
properties are ANDed. Reads cover five minutes, retain at most 500 rows, and have
time/output bounds. Clear view never erases the guest store. This implements the
main Console workflow, not every Console.app capability such as activity tracing
or saved searches.

Verify ingestion on the host that owns the machine with:

```sh
python dev.py simulator logs-probe --machine-dir STATE/machines/NAME --output build/reports/guest-logs.json
```

The probe uploads a uniquely named reader into guest Imports, writes a tagged
message through `logger` and `syslog`, and checks whether a logging store returns
it. It uses a temporary administrative session and closes only that session. It
does not replace or restart the agent. The report includes source availability,
the reader hash, daemon configuration, and whether pre-existing active sessions
remain active. Success requires observing the marker; a write command returning
zero is insufficient. Run with the same host account that owns the VM credentials.

The current Darling runtime disables `com.apple.syslogd` in its launch plist,
with an upstream comment identifying a crash under `darlingserver`. It also lacks
`/usr/bin/log` and `/var/log/system.log` in the observed environment. The Console
reader detects the disabled, unloaded ASL daemon and reports it as unavailable.
Enabling that daemon and qualifying ingestion require an isolated runtime fix;
do not enable its crashing KeepAlive job in a machine with active sessions.

```sh
python dev.py simulator machine -- status
python dev.py simulator machine -- start example
python dev.py simulator machine -- stop example
python dev.py simulator shutdown
python dev.py simulator shutdown --stop-machines
```

Machine names are durable handles. Shell/exec/debug operations return session
identifiers; `machine session NAME SESSION` reconnects. The existing CLI remains
available through `python -m tools.simulator`. See the
[runtime guide](../tools/simulator/DARWIN.md) for provisioning, QEMU/SSH prerequisites,
supervisor ownership, debugger support, and known compatibility gaps.

`shutdown` stops the controller and preserves machines. `--stop-machines` first
requests graceful shutdown of each active machine and stops on failure. It does
not force-kill machines or stop separate provisioning builders. Stop a builder
explicitly with `machine provision-stop NAME`. Reopening reconnects to existing
supervisors. The sample UI needs neither a VM nor controller dependencies:

```sh
python dev.py simulator demo
python dev.py simulator model --suite fixture
```

The demo serves compiled sample data on loopback port 8766; `--port` overrides it
and conflicts are errors. Ctrl+C stops that preview server. The model command
requires a C++ build and creates a fresh workspace under `build/runs/modeled/`.
The full modeled suite intentionally reports missing acceptance requirements.

## Package and distribute the application

```sh
python dev.py simulator package
```

This produces `build/packages/aslice-simulator.zip`, containing the Python
controller and launcher, compiled UI and bundled third-party notices, Windows
and Linux launch scripts, and a checksum inventory. Existing output is refused;
select another `--output PATH` for another package. Dependencies, machines,
credentials, and local logs are excluded. After extracting:

```sh
python simulator.py setup
python simulator.py
python simulator.py status
python simulator.py shutdown
```

Setup creates a private `.venv` and installs pinned Python dependencies. Later
launches select that environment automatically. Windows users can launch
`Simulator.cmd`; Linux users can run `sh simulator.sh`. Python 3.11+ remains a
host prerequisite; this is not a frozen binary distribution. Node and the source
checkout are unnecessary. QEMU, SSH, and provisioned images are required for VM
execution, separately from launching the application.

## State and the existing build directory

New application state defaults to `%LOCALAPPDATA%/aslice/simulator` on Windows
and `$XDG_STATE_HOME/aslice/simulator` (or `~/.local/state/aslice/simulator`) on
Linux. Set `ASLICE_SIMULATOR_HOME` or pass `--root PATH` to open another store.
The retained Python CLI still uses its historical default, `build/darwin-machines`.
To reconnect to those machines through the new launcher:

```sh
python dev.py simulator open --root build/darwin-machines
```

Do not treat the current `build/` as disposable. It contains experiments,
diagnostic evidence, and possibly persistent images alongside generated output.
Moving qcow2 images without preserving backing-file references can break them.

```sh
python dev.py audit-build
```

The audit records source candidates, hashes of small source files, protected VM
state, evidence categories, and excluded dependency directories. It neither
executes nor deletes discovered files. Its classifications are review aids;
unclassified files may contain credentials or irreplaceable evidence.

| Existing material | Durable destination or treatment |
|---|---|
| Reusable quality/container recipes in `build/verification/` | Rewritten in `tools/dev/`; the CLI owns future recipes. |
| Requirement-report comparison experiment | Rewritten as `compare-coverage`, with explicit image selection and full-report comparison. |
| Runtime patches and minimal input programs | Maintain in `tools/simulator/runtime-patches/` and `tests/simulator/corpus/`; preserve any unmatched experimental variants until reviewed. |
| Hard-coded VM repair, download, and evidence scripts in `build/darwin-live/` | Retain originals. Extract a reusable operation only with explicit inputs, bounded effects, and a regression test; do not copy the whole directory into production source. |
| Capture experiments | Retain alongside their evidence until compared with the documentation archive tools and preservation records. |
| Logs, screenshots, receipts, machine disks, and credentials | Keep outside source control; preserve separately before any manual cleanup. |
| Compiler caches, installed dependencies, generated headers and console bundles | Regenerate from tracked recipes after confirming they contain no unique work. |

There is deliberately no recursive `clean` command. New reports and model runs
have separate output directories, and new persistent machines live outside the
build tree. This makes future cleanup reviewable without risking legacy state.
