#!/usr/bin/env bash
# PRANA ELEX Station installer for Raspberry Pi.
#
#   curl -fsSL https://raw.githubusercontent.com/VQ-Vinh/VHF/main/install.sh | sudo bash
#
# Installs the prebuilt .deb, provisions the device, and prints the QR label to
# the terminal. Safe to re-run: it upgrades in place and reprints the same code.
set -euo pipefail

REPO="VQ-Vinh/VHF"
SERVICE_USER="prana-elex"
SERVICE_HOME="/var/lib/prana-elex"
# Must match Environment=XDG_CONFIG_HOME in debian/prana-station.service.
SERVICE_CONFIG_HOME="/var/lib/prana-elex/.config"
LABEL_DIR="/var/lib/prana-elex/label"
MIC_GAIN=18

DEB_PATH=""
VERSION=""
SKIP_PROVISION=0
SKIP_AUDIO_GAIN=0

say() { printf '\033[36m[PRANA]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[PRANA]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[31m[PRANA] LOI:\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
    cat <<'USAGE'
Usage: install.sh [options]

  --deb <path>        Install this .deb instead of downloading a release.
  --version <tag>     Install this release tag instead of the latest.
  --skip-provision    Install only; do not provision or print the QR.
  --skip-audio-gain   Do not touch the ALSA capture gain.
  -h, --help          Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --deb) DEB_PATH="${2:-}"; shift 2 ;;
        --version) VERSION="${2:-}"; shift 2 ;;
        --skip-provision) SKIP_PROVISION=1; shift ;;
        --skip-audio-gain) SKIP_AUDIO_GAIN=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) fail "Tham so khong hop le: $1" ;;
    esac
done

# --- Platform guards, before touching anything -------------------------------
[[ "$(id -u)" -eq 0 ]] || fail "Can quyen root. Chay lai voi sudo."
[[ "$(uname -s)" == "Linux" ]] || fail "Script nay chi chay tren Linux."
ARCH="$(uname -m)"
[[ "$ARCH" == "aarch64" ]] || fail "Can Raspberry Pi OS 64-bit (aarch64), dang chay: $ARCH."
if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    case "${VERSION_CODENAME:-}" in
        bookworm|trixie) ;;
        *) warn "Da kiem thu tren Raspberry Pi OS Bookworm va Trixie; dang chay '${VERSION_CODENAME:-unknown}'." ;;
    esac
fi
command -v curl >/dev/null || fail "Thieu curl. Chay: apt-get install -y curl"

WORK_DIR=""
cleanup() { [[ -n "$WORK_DIR" ]] && rm -rf -- "$WORK_DIR"; }
trap cleanup EXIT

# --- Obtain the package ------------------------------------------------------
if [[ -n "$DEB_PATH" ]]; then
    [[ -f "$DEB_PATH" ]] || fail "Khong tim thay file: $DEB_PATH"
    say "Dung goi co san: $DEB_PATH"
    if [[ -f "$DEB_PATH.sha256" ]]; then
        expected="$(awk '{print $1}' "$DEB_PATH.sha256")"
        actual="$(sha256sum "$DEB_PATH" | awk '{print $1}')"
        [[ "$expected" == "$actual" ]] || fail "sha256 khong khop cho $DEB_PATH."
        say "sha256 hop le."
    else
        warn "Khong co $DEB_PATH.sha256 di kem; bo qua buoc doi chieu."
    fi
else
    WORK_DIR="$(mktemp -d)"
    if [[ -n "$VERSION" ]]; then
        api="https://api.github.com/repos/$REPO/releases/tags/$VERSION"
    else
        api="https://api.github.com/repos/$REPO/releases/latest"
    fi
    say "Tim ban phat hanh moi nhat..."
    release="$(curl -fsSL "$api")" \
        || fail "Khong doc duoc thong tin phat hanh tu GitHub. Kiem tra mang, hoac dung --deb."
    deb_url="$(printf '%s' "$release" \
        | grep -o '"browser_download_url": *"[^"]*_arm64\.deb"' \
        | head -n 1 | sed 's/.*"\(https[^"]*\)"/\1/')"
    [[ -n "$deb_url" ]] || fail "Ban phat hanh nay khong co file _arm64.deb."
    DEB_PATH="$WORK_DIR/$(basename "$deb_url")"
    say "Tai $(basename "$deb_url")..."
    curl -fsSL -o "$DEB_PATH" "$deb_url" || fail "Tai goi that bai."

    # Verify before install: an unchecked .deb runs postinst as root.
    if curl -fsSL -o "$DEB_PATH.sha256" "$deb_url.sha256" 2>/dev/null; then
        expected="$(awk '{print $1}' "$DEB_PATH.sha256")"
        actual="$(sha256sum "$DEB_PATH" | awk '{print $1}')"
        [[ "$expected" == "$actual" ]] || fail "sha256 khong khop. Goi tai ve co the bi hong."
        say "sha256 hop le."
    else
        warn "Ban phat hanh khong kem file .sha256; bo qua buoc doi chieu."
    fi
fi

# --- Install -----------------------------------------------------------------
say "Cai goi (apt tu giai phu thuoc)..."
apt-get update -qq || warn "apt-get update that bai; van thu cai tiep."
apt-get install -y "$DEB_PATH"

# --- ALSA capture gain -------------------------------------------------------
# The verified USB SoundCard setting is Mic Capture +15 dB (18/28). Left manual,
# it gets forgotten and RX comes through too quiet to transcribe.
if [[ "$SKIP_AUDIO_GAIN" -eq 0 ]]; then
    card="$(arecord -l 2>/dev/null | grep -i 'USB' | head -n 1 | sed 's/^card \([0-9]*\):.*/\1/')"
    if [[ -n "$card" ]]; then
        if amixer -c "$card" cset name='Mic Capture Volume' "$MIC_GAIN" >/dev/null 2>&1; then
            alsactl store "$card" >/dev/null 2>&1 || warn "Khong luu duoc cau hinh ALSA."
            say "Da dat gain micro = $MIC_GAIN tren card $card."
        else
            warn "Card $card khong co 'Mic Capture Volume'; hay dat gain thu cong."
        fi
    else
        warn "Chua thay USB SoundCard. Cam thiet bi roi chay lai voi --skip-provision."
    fi
fi

# --- Provision ---------------------------------------------------------------
if [[ "$SKIP_PROVISION" -eq 1 ]]; then
    say "Bo qua provision theo yeu cau."
else
    install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0700 "$LABEL_DIR"
    say "Provision thiet bi..."
    echo
    # Must run exactly as the service does. Provisioning as root would write the
    # identity to /root/.config and the printed QR would belong to a station the
    # service never uses -- pairing would silently never complete.
    sudo -u "$SERVICE_USER" env "XDG_CONFIG_HOME=$SERVICE_CONFIG_HOME" \
        /usr/bin/prana-station-provision --output "$LABEL_DIR" \
        || fail "Provision that bai. Kiem tra mang roi chay lai script nay."
    echo
fi

systemctl restart prana-station.service || fail "Khong khoi dong duoc prana-station.service."

echo
say "CAI THANH CONG"
say "Quet ma QR o tren bang app PRANA ELEX (dang nhap truoc khi quet)."
say "Nhan in: $LABEL_DIR"
say "Trang thai: systemctl status prana-station"
say "Nhat ky:   journalctl -u prana-station -f"
say "Chay lai script nay se nang cap goi va in lai dung ma cu."
