% ASLICE-NEEDS-RESTARTING(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-needs-restarting — report remaining actions after package updates

# SYNOPSIS

`aslice needs-restarting` [**--json**]

# DESCRIPTION

Inspect visible processes and their exact mapped artifact closures. Report obsolete
closures needing **restart**, vulnerable static or embedded inputs needing
**consumer-rebuild**, evidenced boot-bound effects needing **reboot**, and
**unknown** inspection coverage. Restart cannot repair a statically embedded
vulnerability. This command reports actions without terminating processes or
starting builds.

Each finding names its reason, artifact/advisory bindings, and visible process or
service identity. Inaccessible processes, inspection races, and unsupported OS
inspection produce partial or unknown coverage, not a clean bill of health.
Inspection and reporting stay local; no telemetry is sent.

# OPTIONS

**--json**
:   Emit the version-2 operation-outcome envelope, including restart findings and inspection coverage.

# EXIT STATUS

**0** complete inspection, no actions. **3** actions remain or coverage is incomplete.
**1** inspection/invocation failure. A reboot recommendation does not authorize a reboot.

# IMPLEMENTATION STATUS

Specified interface. Process inspection on macOS 10.11–12 and integration with
service and protected-effect receipts remain pending.

# SEE ALSO

aslice(1), aslice-upgrade(1), aslice-service(1),
[DESIGN](../docs/DESIGN.md#vulnerability-and-sbom-pipeline)
