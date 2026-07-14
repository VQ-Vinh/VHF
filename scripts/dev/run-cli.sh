#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [ ! -x "$ROOT/venv/bin/python" ]; then
    echo "[ERROR] Virtual environment not found."
    echo "[!] Run ./scripts/setup/setup.sh first, then try again."
    exit 1
fi

export PYTHONPATH="$ROOT/src"
if [ $# -eq 0 ]; then
    exec "$ROOT/venv/bin/python" -u -m prana_elex.app.cli "$ROOT/config/profiles/raspberry-pi.toml"
else
    exec "$ROOT/venv/bin/python" -u -m prana_elex.app.cli "$@"
fi
