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

if [ ! -x "$ROOT/venv/bin/python" ]; then
    "$PYTHON" -m venv "$ROOT/venv"
fi

"$ROOT/venv/bin/python" -m pip install --upgrade pip
"$ROOT/venv/bin/python" -m pip install -e "$ROOT"
mkdir -p "$ROOT/data/audio" "$ROOT/data/results"

echo "[OK] Setup complete. Run: ./scripts/dev/run-cli.sh"
