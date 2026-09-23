#!/usr/bin/env bash
# Turn a plain Debian container into the userspace a Raspberry Pi station is
# built in, then run the ordinary package build inside it.
#
# Called by .github/workflows/pi-release.yml as the container entrypoint. Run it
# nowhere else: it rewrites apt sources and drops a sudo shim, which is fine in
# a throwaway container and destructive on a real machine.
#
# The container must be debian:bookworm on arm64. PyInstaller links the bundle
# against the build machine's glibc, so the package runs on that release and
# newer but never older -- bookworm (2.36) covers Raspberry Pi OS Bookworm and
# Trixie, while a newer base would silently drop Bookworm support.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

fail() {
    echo "[ERROR] $*" >&2
    exit 1
}

[[ "$(id -u)" -eq 0 ]] || fail "Expected to run as root inside a container."
[[ "$(uname -m)" == "aarch64" ]] || fail "Expected aarch64, found $(uname -m)."
[[ -r /etc/os-release ]] || fail "Cannot identify the container image."
# shellcheck disable=SC1091
source /etc/os-release
[[ "${VERSION_CODENAME:-}" == "bookworm" ]] \
    || fail "Expected a bookworm container, found: ${VERSION_CODENAME:-unknown}."
[[ -f /.dockerenv ]] || fail "Refusing to rewrite apt sources outside a container."

export DEBIAN_FRONTEND=noninteractive

echo "[CI 1/4] Installing apt transport tooling..."
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg

echo "[CI 2/4] Adding the Raspberry Pi archive for lgpio..."
# lgpio is in no Debian suite at all. It ships from Raspberry Pi's own archive,
# which is where Raspberry Pi OS itself resolves it, so that is the honest
# source. The pin keeps everything else coming from Debian: a stray upgrade out
# of this archive would quietly build against libraries the target OS lacks.
curl -fsSL https://archive.raspberrypi.com/debian/raspberrypi.gpg.key \
    | gpg --dearmor -o /usr/share/keyrings/raspberrypi.gpg
echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] http://archive.raspberrypi.com/debian/ bookworm main" \
    >/etc/apt/sources.list.d/raspberrypi.list
cat >/etc/apt/preferences.d/raspberrypi <<'PIN'
Package: *
Pin: origin archive.raspberrypi.com
Pin-Priority: 100

Package: liblgpio1 liblgpio-dev
Pin: origin archive.raspberrypi.com
Pin-Priority: 600
PIN
apt-get update

echo "[CI 3/4] Installing the sudo shim..."
# build.sh reaches for sudo to install its apt dependencies. A container is
# already root and carries no sudo, so give it a pass-through rather than
# pulling in the real package and a PAM stack with it.
printf '#!/bin/sh\nexec "$@"\n' >/usr/local/bin/sudo
chmod 0755 /usr/local/bin/sudo

echo "[CI 4/4] Building the package..."
df -Pk "$ROOT" | awk 'NR==2 {printf "[CI] Free disk: %.1f GiB\n", $4 / 1048576}'
export PRANA_BUILD_ALLOW_NON_PI=1
exec "$ROOT/apps/linux/packaging/build.sh" "$@"
