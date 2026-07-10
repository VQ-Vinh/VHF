#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Kiểm tra venv
if [ ! -d "$DIR/venv" ]; then
    echo "[ERROR] Virtual environment not found."
    echo "[!] Run setup.sh first, then try again."
    exit 1
fi

export PYTHONPATH="$DIR/src"
if [ $# -eq 0 ]; then
    exec "$DIR/venv/bin/python" -u "$DIR/src/vhf_processor/main.py" "$DIR/config/rpi.toml"
else
    exec "$DIR/venv/bin/python" -u "$DIR/src/vhf_processor/main.py" "$@"
fi
