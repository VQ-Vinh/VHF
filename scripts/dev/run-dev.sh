#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [ ! -x "$ROOT/.venv/dev/bin/python" ]; then
    echo "[ERROR] Virtual environment not found."
    echo "[!] Run ./scripts/setup/setup.sh first, then try again."
    exit 1
fi

export PYTHONPATH="$ROOT/src"
exec "$ROOT/.venv/dev/bin/python" -c "from prana_elex.ui.app import run_app; run_app()"
