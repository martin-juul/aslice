#!/bin/bash
# Dedicated provisioning VM only. Downloads finish before isolated app execution.
set -euo pipefail
exec > >(tee -a /opt/aslice/build.log) 2>&1
trap 'printf "failed at line %s\n" "$LINENO" > /opt/aslice/build-status' ERR
echo provisioning > /opt/aslice/build-status
export DEBIAN_FRONTEND=noninteractive
mkdir -p /opt/aslice/inputs/debs

packages=(cmake ninja-build automake clang bison flex bzip2 libfuse-dev libudev-dev pkg-config
  libc6-dev-i386 gcc-multilib libcairo2-dev libgl1-mesa-dev curl libglu1-mesa-dev libtiff-dev
  libfreetype6-dev git git-lfs libelf-dev libxml2-dev libegl1-mesa-dev libfontconfig1-dev
  libbsd-dev libxrandr-dev libxcursor-dev libgif-dev libavutil-dev libpulse-dev libavformat-dev
  libavcodec-dev libswresample-dev libdbus-1-dev libxkbfile-dev libssl-dev libstdc++-15-dev
  libvulkan-dev libcurl4-openssl-dev libedit-dev llvm-dev libcap2-bin python3
  xvfb fluxbox x11vnc xterm dbus-x11 mesa-utils openssh-server gdb lldb)

apt-get update
apt-get -o Dir::Cache::archives=/opt/aslice/inputs/debs --download-only install -y "${packages[@]}"
apt-get -o Dir::Cache::archives=/opt/aslice/inputs/debs install -y "${packages[@]}"
dpkg-query -W > /opt/aslice/inputs/packages.txt
clang --version > /opt/aslice/inputs/compiler.txt

git lfs install --system
export GIT_LFS_SKIP_SMUDGE=1
git clone --no-checkout https://github.com/darlinghq/darling.git /opt/aslice/inputs/darling
cd /opt/aslice/inputs/darling
git checkout --detach 60ba801decee7a00782f74f6be4c8ffb013f79ff
git submodule update --init --recursive --jobs 4
unset GIT_LFS_SKIP_SMUDGE
git lfs pull
git submodule foreach --recursive 'if test "$name" != "src/external/swift"; then git lfs pull; fi'
git submodule status --recursive > /opt/aslice/inputs/submodules.txt
git apply /opt/aslice/patches/*.patch

cmake -S . -B /opt/aslice/runtime-build -G Ninja \
  -DTARGET_i386=OFF \
  -DENABLE_METAL=OFF \
  -DCOMPONENTS=cli,python,gui_frameworks,gui_stubs \
  -DCMAKE_BUILD_TYPE=Debug
cmake --build /opt/aslice/runtime-build --parallel 4
cmake --install /opt/aslice/runtime-build

curl --fail --location \
  https://darling-misc.s3.eu-central-1.amazonaws.com/lldb.tar.bz2 \
  -o /opt/aslice/inputs/lldb.tar.bz2
echo 'b4352bc2ddcc88cd5309836b129d197b8522d47595917ec2e823162436fbda97  /opt/aslice/inputs/lldb.tar.bz2' | sha256sum -c -
mkdir -p /usr/local/libexec/darling/usr/local/libexec/aslice-lldb
tar -xjf /opt/aslice/inputs/lldb.tar.bz2 --strip-components=1 \
  -C /usr/local/libexec/darling/usr/local/libexec/aslice-lldb

runuser -u aslice -- env HOME=/home/aslice DPREFIX=/home/aslice/.darling \
  /usr/local/bin/darling shell /bin/true

# Remove convenience links into the Linux guest. The VM boundary separately
# excludes the actual host filesystem, devices, clipboard and credentials.
find /home/aslice/.darling/Users -type l -lname '*SystemRoot*' -delete
runuser -u aslice -- /usr/local/bin/darling shutdown

python3 - <<'PY'
import hashlib
import json
import pathlib

root = pathlib.Path("/opt/aslice/inputs")


def digest(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


artifacts = {str(p.relative_to(root)): digest(p) for p in (root / "debs").glob("*.deb")}
for n in ("packages.txt", "compiler.txt", "submodules.txt", "lldb.tar.bz2"):
    artifacts[n] = digest(root / n)
for p in pathlib.Path("/opt/aslice/patches").glob("*.patch"):
    artifacts["patches/" + p.name] = digest(p)

subs = {}
for line in (root / "submodules.txt").read_text().splitlines():
    parts = line.split()
    subs[parts[1]] = parts[0].lstrip("+-")

identity = {
    "version": 1,
    "guest": "ubuntu-26.04-x86_64",
    "darling_commit": "60ba801decee7a00782f74f6be4c8ffb013f79ff",
    "submodules": subs,
    "artifacts": artifacts,
    "build": {
        "compiler": (root / "compiler.txt").read_text(),
        "packages": artifacts["packages.txt"],
        "command": (
            "cmake -DTARGET_i386=OFF -DENABLE_METAL=OFF "
            "-DCOMPONENTS=cli,python,gui_frameworks,gui_stubs "
            "-DCMAKE_BUILD_TYPE=Debug; ninja -j4; cmake --install; "
            "optional Swift excluded"
        ),
        "source_tree": "60ba801decee7a00782f74f6be4c8ffb013f79ff",
    },
}
pathlib.Path("/opt/aslice/runtime.json").write_text(json.dumps(identity, indent=2))
PY

systemctl enable --now aslice-display.service aslice-runtime.service
echo ready > /opt/aslice/build-status
