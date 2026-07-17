#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENV="$ROOT/.venv/linux-arm64"
WORK_DIR="$ROOT/build/linux-arm64"
DIST_DIR="$ROOT/dist/linux-arm64"
RELEASE_DIR="$ROOT/release/linux-arm64"
BUNDLE="$DIST_DIR/PRANA_ELEX"
STAGE="$WORK_DIR/debian-root"

fail() {
    echo "[ERROR] $*" >&2
    exit 1
}

# All platform checks deliberately happen before any clean operation.
[[ "$(uname -s)" == "Linux" ]] || fail "buildlinux can only run on Linux."
[[ "$(uname -m)" == "aarch64" ]] || fail "Expected aarch64, found $(uname -m)."
[[ -r /proc/device-tree/model ]] || fail "Raspberry Pi model information is unavailable."
MODEL="$(tr -d '\0' </proc/device-tree/model)"
[[ "$MODEL" == *"Raspberry Pi 4 Model B"* ]] || fail "Expected Raspberry Pi 4B, found: $MODEL"
[[ -r /etc/os-release ]] || fail "Cannot identify the operating system."
# shellcheck disable=SC1091
source /etc/os-release
[[ "${VERSION_CODENAME:-}" == "bookworm" ]] || fail "Raspberry Pi OS Bookworm is required."

AVAILABLE_KB="$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')"
[[ "$AVAILABLE_KB" -ge 12582912 ]] || fail "At least 12 GiB free disk space is required."
MEM_SWAP_KB="$(awk '/MemTotal|SwapTotal/ {sum += $2} END {print sum}' /proc/meminfo)"
[[ "$MEM_SWAP_KB" -ge 4194304 ]] || fail "At least 4 GiB combined RAM and swap is required."

APT_PACKAGES=(
    python3-venv python3-dev build-essential portaudio19-dev libsndfile1-dev
    fakeroot dpkg-dev desktop-file-utils libasound2-dev libportaudio2 libsndfile1
    libgl1 libegl1 libxkbcommon-x11-0 libxcb-cursor0
)
MISSING=()
for package in "${APT_PACKAGES[@]}"; do
    dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q "install ok installed" || MISSING+=("$package")
done
if ((${#MISSING[@]})); then
    echo "[SETUP] Installing system packages: ${MISSING[*]}"
    sudo apt-get update
    sudo apt-get install -y "${MISSING[@]}"
fi

if [[ ! -x "$VENV/bin/python" ]]; then
    echo "[1/7] Creating Linux ARM64 virtual environment..."
    python3 -m venv "$VENV"
else
    echo "[1/7] Virtual environment ready."
fi

echo "[2/7] Installing project and PyInstaller..."
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -e "$ROOT" pyinstaller

echo "[CHECK] Validating production client configuration..."
"$VENV/bin/python" "$ROOT/scripts/packaging/common/validate_client_config.py" \
    "$ROOT/config/profiles/raspberry-pi.toml"

echo "[3/7] Cleaning Linux ARM64 outputs only..."
rm -rf -- "$WORK_DIR" "$DIST_DIR" "$RELEASE_DIR"
mkdir -p "$WORK_DIR" "$DIST_DIR" "$RELEASE_DIR"

echo "[4/7] Building Linux ARM64 bundle..."
"$VENV/bin/python" -m PyInstaller \
    --noconfirm --clean \
    --workpath "$WORK_DIR" \
    --distpath "$DIST_DIR" \
    "$SCRIPT_DIR/PRANA_ELEX.spec"
cp "$SCRIPT_DIR/debian/prana-elex.desktop" "$BUNDLE/prana-elex.desktop"

echo "[5/7] Validating Linux ARM64 bundle..."
"$VENV/bin/python" "$ROOT/scripts/packaging/common/validate_release.py" \
    --platform linux-arm64 --bundle "$BUNDLE"

VERSION="$("$VENV/bin/python" "$ROOT/scripts/packaging/common/project_metadata.py" --field version)"
VENDOR="$("$VENV/bin/python" "$ROOT/scripts/packaging/common/project_metadata.py" --field vendor)"
[[ -n "$VENDOR" ]] || VENDOR="DLV Corporation"

echo "[6/7] Staging Debian package..."
mkdir -p "$STAGE/DEBIAN" "$STAGE/opt/prana-elex" "$STAGE/usr/bin" "$STAGE/usr/share/applications"
cp -a "$BUNDLE/." "$STAGE/opt/prana-elex/"
cp "$SCRIPT_DIR/debian/prana-elex.desktop" "$STAGE/usr/share/applications/prana-elex.desktop"
cat >"$STAGE/usr/bin/prana-elex" <<'LAUNCHER'
#!/bin/sh
exec /opt/prana-elex/PRANA_ELEX "$@"
LAUNCHER
chmod 0755 "$STAGE/usr/bin/prana-elex" "$STAGE/opt/prana-elex/PRANA_ELEX"
install -m 0755 "$SCRIPT_DIR/debian/postinst" "$STAGE/DEBIAN/postinst"
install -m 0755 "$SCRIPT_DIR/debian/postrm" "$STAGE/DEBIAN/postrm"
INSTALLED_SIZE="$(du -sk "$STAGE" | awk '{print $1}')"
sed \
    -e "s/@VERSION@/$VERSION/g" \
    -e "s/@VENDOR@/$VENDOR/g" \
    -e "s/@INSTALLED_SIZE@/$INSTALLED_SIZE/g" \
    "$SCRIPT_DIR/debian/control.in" >"$STAGE/DEBIAN/control"

echo "[7/7] Building .deb..."
DEB="$RELEASE_DIR/prana-elex_${VERSION}_arm64.deb"
dpkg-deb --build --root-owner-group "$STAGE" "$DEB"
dpkg-deb --info "$DEB" >/dev/null
sha256sum "$DEB" >"$DEB.sha256"

echo "[OK] Bundle: $BUNDLE"
echo "[OK] Package: $DEB"
