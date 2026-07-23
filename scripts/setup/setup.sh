#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "============================================================"
echo "  PRANA ELEX - Setup"
echo "============================================================"

PYTHON="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python 3.11 or newer is required."
    exit 1
fi

"$PYTHON" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' || {
    echo "[ERROR] Python 3.11 or newer is required."
    exit 1
}

if [ ! -x "$ROOT/.venv/dev/bin/python" ]; then
    "$PYTHON" -m venv "$ROOT/.venv/dev"
fi

"$ROOT/.venv/dev/bin/python" -m pip install --upgrade pip
"$ROOT/.venv/dev/bin/python" -m pip install --no-build-isolation -e "$ROOT/packages/prana_core"
"$ROOT/.venv/dev/bin/python" -m pip install --no-build-isolation -e "$ROOT/apps/linux"
mkdir -p "$ROOT/VHF_Storage/audio" "$ROOT/VHF_Storage/results"

echo "[OK] Linux station setup complete. Run: ./apps/linux/run.sh"
