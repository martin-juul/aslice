"""Cloud-init seeds and pinned guest provisioning, separate from app execution."""

import base64
import io
import json
from pathlib import Path
import secrets
import os
import subprocess
import sys
import urllib.request
import uuid

from .model import atomic_json
from .vm import private

HERE = Path(__file__).parent
CLOUD_URL = "https://cloud-images.ubuntu.com/releases/resolute/release-20260918/ubuntu-26.04-server-cloudimg-amd64.img"
CLOUD_SHA256 = "4908fb59ccd4e87ae4e8e973b7ef56f535448eacb24a87fd787270c0048987bc"


def iso(path, files):
    import pycdlib

    disc = pycdlib.PyCdlib()
    disc.new(interchange_level=3, vol_ident="cidata", joliet=3, rock_ridge="1.09")
    for index, (name, content) in enumerate(files.items()):
        data = content.encode()
        disc.add_fp(
            io.BytesIO(data),
            len(data),
            iso_path=f"/F{index}.;1",
            rr_name=name,
            joliet_path="/" + name,
        )
    disc.write(str(path))
    disc.close()


def machine_seed(directory, build=False):
    directory = Path(directory)
    control = directory / "control"
    control.mkdir(exist_ok=True)
    private(control)
    for filename in ("ssh-client", "ssh-host"):
        key = control / filename
        if not key.exists():
            subprocess.run(
                ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
                check=True,
                capture_output=True,
            )
            private(key)
    token_file = control / "guest-token"
    if not token_file.exists():
        token_file.write_text(secrets.token_urlsafe(32))
        private(token_file)
    files = []

    def add(path, content, permissions="0644"):
        files.append(
            {
                "path": path,
                "content": base64.b64encode(content.encode()).decode(),
                "encoding": "b64",
                "permissions": permissions,
            }
        )

    add("/opt/aslice/guest_agent.py", (HERE / "guest_agent.py").read_text())
    add("/opt/aslice/guest_logs.py", (HERE / "guest_logs.py").read_text())
    add("/etc/aslice-agent.token", token_file.read_text(), "0600")
    add("/etc/ssh/ssh_host_ed25519_key", (control / "ssh-host").read_text(), "0600")
    add("/etc/ssh/ssh_host_ed25519_key.pub", (control / "ssh-host.pub").read_text())
    add(
        "/etc/ssh/sshd_config.d/40-aslice.conf",
        """PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
HostKey /etc/ssh/ssh_host_ed25519_key
Match User aslice-control
  AllowTcpForwarding local
  PermitOpen 127.0.0.1:9971 127.0.0.1:5900
  X11Forwarding no
  PermitTTY no
  ForceCommand /bin/false
""",
    )
    add(
        "/etc/systemd/system/aslice-agent.service",
        """[Unit]
After=network.target
[Service]
ExecStart=/usr/bin/python3 /opt/aslice/guest_agent.py
Restart=on-failure
KillMode=process
[Install]
WantedBy=multi-user.target
""",
    )
    add(
        "/etc/systemd/system/aslice-display.service",
        """[Unit]
After=network.target
[Service]
User=aslice
Environment=DISPLAY=:0
Environment=LIBGL_ALWAYS_SOFTWARE=1
ExecStart=/opt/aslice/display.sh
Restart=on-failure
[Install]
WantedBy=multi-user.target
""",
    )
    add(
        "/opt/aslice/display.sh",
        """#!/bin/sh
set -eu
# Darling applications and Xvfb occupy different IPC namespaces. Disable the
# shared-memory extension so Mesa transfers rendered pixels over the X socket.
Xvfb :0 -screen 0 1280x800x24 -nolisten tcp -extension MIT-SHM &
trap 'kill $(jobs -p) 2>/dev/null || true' EXIT
sleep 1
fluxbox &
exec x11vnc -display :0 -localhost -rfbport 5900 -forever -shared -nopw -noxdamage -noshm
""",
        "0755",
    )
    add(
        "/etc/systemd/system/aslice-runtime.service",
        """[Unit]
Description=Persistent Darling compatibility runtime
After=aslice-display.service
Wants=aslice-display.service
[Service]
User=aslice
Environment=HOME=/home/aslice
Environment=DPREFIX=/home/aslice/.darling
Environment=DISPLAY=:0
Environment=LIBGL_ALWAYS_SOFTWARE=1
ExecStart=/usr/local/bin/darling shell /bin/sleep 2147483647
ExecStop=/usr/local/bin/darling shutdown
Restart=on-failure
TimeoutStopSec=15
KillMode=control-group
[Install]
WantedBy=multi-user.target
""",
    )
    add(
        "/etc/sysctl.d/90-aslice.conf",
        "kernel.apparmor_restrict_unprivileged_userns=0\nkernel.yama.ptrace_scope=0\n",
    )
    add("/opt/aslice/build-runtime.sh", (HERE / "guest_build.sh").read_text(), "0755")
    for patch in sorted((HERE / "runtime-patches").glob("*.patch")):
        add("/opt/aslice/patches/" + patch.name, patch.read_text())
    # Cloud-init accepts JSON as its YAML subset. Seed contains only public
    # host-login credentials and guest-scoped keys; never a controller token.
    user_data = {
        "users": [
            {"name": "aslice", "shell": "/bin/bash", "lock_passwd": True},
            {
                "name": "aslice-admin",
                "shell": "/bin/bash",
                "lock_passwd": True,
                "sudo": "ALL=(ALL) NOPASSWD:ALL",
            },
            {
                "name": "aslice-control",
                "shell": "/bin/bash",
                "lock_passwd": True,
                "ssh_authorized_keys": [
                    "restrict,port-forwarding "
                    + (control / "ssh-client.pub").read_text().strip()
                ],
            },
        ],
        "ssh_deletekeys": False,
        "write_files": files,
        "runcmd": [
            ["sysctl", "--system"],
            ["systemctl", "daemon-reload"],
            ["systemctl", "restart", "ssh"],
            ["systemctl", "enable", "--now", "aslice-agent.service"],
        ],
    }
    if build:
        user_data["runcmd"].append(
            [
                "systemd-run",
                "--unit=aslice-runtime-build",
                "/opt/aslice/build-runtime.sh",
            ]
        )
    else:
        user_data["runcmd"].append(
            [
                "systemctl",
                "enable",
                "--now",
                "aslice-display.service",
                "aslice-runtime.service",
            ]
        )
    network = {
        "version": 2,
        "ethernets": {
            "management": {
                "match": {"macaddress": "52:54:00:12:34:01"},
                "dhcp4": True,
                "dhcp4-overrides": {"use-routes": False, "use-dns": False},
            },
            "applications": {
                "match": {"macaddress": "52:54:00:12:34:02"},
                "dhcp4": True,
            },
        },
    }
    iso(
        control / "seed.iso",
        {
            "user-data": "#cloud-config\n" + json.dumps(user_data),
            "meta-data": json.dumps(
                {
                    "instance-id": "aslice-" + uuid.uuid4().hex,
                    "local-hostname": "aslice-guest",
                }
            ),
            "network-config": json.dumps(network),
        },
    )
    private(control / "seed.iso")
    atomic_json(
        control / "provision.json",
        {
            "version": 1,
            "build": build,
            "cloud_url": CLOUD_URL,
            "cloud_sha256": CLOUD_SHA256,
        },
    )


def begin(directory, acceleration="auto", cloud_image=None):
    from . import vm
    from .darwin import preflight

    probe = preflight(acceleration)
    if probe["blockers"]:
        raise ValueError("; ".join(probe["blockers"]))
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    private(directory)
    (directory / "evidence").mkdir()
    atomic_json(
        directory / "preparation.json",
        {
            "version": 1,
            "state": "downloading",
            "accelerator": probe["accelerator"],
            "cloud_image": cloud_image,
        },
    )
    with (directory / "provision.log").open("wb") as log:
        vm.detached(
            [sys.executable, "-m", "tools.simulator.provision", str(directory)], log
        )
    return {
        "state": "provisioning",
        "path": str(directory),
        "downloads": True,
        "network": "enabled in disposable builder only",
        "accelerator": probe["accelerator"],
    }


def build(directory):
    from . import vm
    from .darwin import sha256, checked_copy

    directory = Path(directory).resolve()
    config = json.loads((directory / "preparation.json").read_text())
    with vm.Lease(directory / ".provision-lease"):
        source = directory / "ubuntu.qcow2"
        try:
            if config.get("cloud_image"):
                checked_copy(Path(config["cloud_image"]), source, CLOUD_SHA256)
            else:
                partial = source.with_suffix(".partial")
                with urllib.request.urlopen(
                    CLOUD_URL, timeout=60
                ) as response, partial.open("xb") as output:
                    total = 0
                    while block := response.read(1024 * 1024):
                        total += len(block)
                        if total > 2 * 1024**3:
                            raise ValueError("cloud image exceeds 2 GiB download bound")
                        output.write(block)
                    output.flush()
                    os.fsync(output.fileno())
                if sha256(partial) != CLOUD_SHA256:
                    raise ValueError("cloud image SHA-256 mismatch")
                os.replace(partial, source)
            subprocess.run(
                [
                    "qemu-img",
                    "create",
                    "-f",
                    "qcow2",
                    "-F",
                    "qcow2",
                    "-b",
                    str(source),
                    str(directory / "disk.qcow2"),
                    "64G",
                ],
                check=True,
                capture_output=True,
            )
            machine_seed(directory, build=True)
            launch = {
                "name": directory.name,
                "uuid": str(uuid.uuid4()),
                "disk": str(directory / "disk.qcow2"),
                "seed": str(directory / "control/seed.iso"),
                "acceleration": config["accelerator"],
                "network": True,
                "cpus": 4,
                "memory_mib": 8192,
                "ssh_port": vm.port(),
                "token": secrets.token_urlsafe(32),
                "operation": uuid.uuid4().hex,
            }
            atomic_json(directory / "control/launch.json", launch)
            config["state"] = "building-in-guest"
            atomic_json(directory / "preparation.json", config)
        except BaseException as error:
            config.update(state="failed", error=str(error))
            atomic_json(directory / "preparation.json", config)
            raise
    vm.supervise(directory)


if __name__ == "__main__":
    build(sys.argv[1])
