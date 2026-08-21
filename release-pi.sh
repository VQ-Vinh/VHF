#!/usr/bin/env bash
# Build the Raspberry Pi package and publish it as a GitHub release.
#
#   curl -fsSL https://raw.githubusercontent.com/VQ-Vinh/VHF/main/release-pi.sh | bash
#
# Run this once per version, on a Raspberry Pi 4B -- apps/linux/packaging/build.sh
# refuses to run anywhere else. Every other device then installs with install.sh
# and never needs the repository.
set -euo pipefail

REPO="VQ-Vinh/VHF"
CLONE_URL="https://github.com/$REPO.git"
SRC_DIR="${HOME}/prana-elex-src"
TAG=""
SKIP_BUILD=0

say() { printf '\033[36m[PRANA]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[PRANA]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[31m[PRANA] LOI:\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
    cat <<'USAGE'
Usage: release-pi.sh [options]

  --dir <path>     Where to keep the build checkout (default: ~/prana-elex-src).
  --tag <tag>      Release tag (default: v<VERSION> from the repository).
  --skip-build     Publish the .deb already present in installers/linux.
  -h, --help       Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir) SRC_DIR="${2:-}"; shift 2 ;;
        --tag) TAG="${2:-}"; shift 2 ;;
        --skip-build) SKIP_BUILD=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) fail "Tham so khong hop le: $1" ;;
    esac
done

# build.sh calls sudo itself for apt; running the whole build as root would leave
# the checkout and the venv owned by root.
[[ "$(id -u)" -ne 0 ]] || fail "Dung chay bang sudo. Chay bang user thuong."
[[ "$(uname -m)" == "aarch64" ]] || fail "Can Raspberry Pi 4B 64-bit, dang chay: $(uname -m)."
command -v git >/dev/null || fail "Thieu git. Chay: sudo apt-get install -y git"
command -v gh >/dev/null || fail "Thieu GitHub CLI. Chay: sudo apt-get install -y gh"
gh auth status >/dev/null 2>&1 || fail "Chua dang nhap GitHub CLI. Chay: gh auth login"

# --- Checkout ----------------------------------------------------------------
if [[ -d "$SRC_DIR/.git" ]]; then
    say "Cap nhat ma nguon tai $SRC_DIR..."
    git -C "$SRC_DIR" fetch --quiet origin
    git -C "$SRC_DIR" checkout --quiet main
    git -C "$SRC_DIR" pull --quiet --ff-only origin main
else
    say "Tai ma nguon ve $SRC_DIR..."
    git clone --quiet "$CLONE_URL" "$SRC_DIR"
fi
cd "$SRC_DIR"

VERSION="$(tr -d '[:space:]' <packages/prana_core/src/prana_core/VERSION)"
[[ -n "$VERSION" ]] || fail "Khong doc duoc so phien ban."
[[ -n "$TAG" ]] || TAG="v$VERSION"
DEB="installers/linux/prana-elex_${VERSION}_arm64.deb"

# --- Build -------------------------------------------------------------------
if [[ "$SKIP_BUILD" -eq 1 ]]; then
    say "Bo qua build theo yeu cau."
else
    say "Build goi $VERSION. Lan dau mat 15-30 phut (bien dich torch, lgpio)."
    ./buildlinux
fi

[[ -f "$DEB" ]] || fail "Khong thay $DEB sau khi build."
[[ -f "$DEB.sha256" ]] || fail "Khong thay $DEB.sha256. install.sh can file nay de doi chieu."

# --- Publish -----------------------------------------------------------------
if gh release view "$TAG" >/dev/null 2>&1; then
    say "Tag $TAG da ton tai; ghi de file dinh kem."
    gh release upload "$TAG" "$DEB" "$DEB.sha256" --clobber
else
    say "Tao ban phat hanh $TAG..."
    gh release create "$TAG" "$DEB" "$DEB.sha256" \
        --title "PRANA ELEX $VERSION" \
        --notes "Raspberry Pi station package for arm64.

Cai dat:

    curl -fsSL https://raw.githubusercontent.com/$REPO/main/install.sh | sudo bash"
fi

echo
say "DA PHAT HANH $TAG"
say "Tu gio moi Raspberry Pi chi can chay:"
echo
echo "    curl -fsSL https://raw.githubusercontent.com/$REPO/main/install.sh | sudo bash"
echo
say "Ma nguon build giu tai $SRC_DIR de lan sau build lai nhanh hon."
