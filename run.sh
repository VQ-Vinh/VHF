#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Check venv
if [ ! -d "$DIR/venv" ]; then
    echo "[ERROR] Virtual environment not found."
    echo "[!] Run setup.sh first, then try again."
    exit 1
fi

export PYTHONPATH="$DIR/src"
if [ $# -eq 0 ]; then
    exec "$DIR/venv/bin/python" -u -m prana_elex.app.cli "$DIR/config/rpi.toml"
else
    exec "$DIR/venv/bin/python" -u -m prana_elex.app.cli "$@"
fi
