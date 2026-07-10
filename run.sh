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

# Load .env
if [ -f "$DIR/.env" ]; then
    set -a
    source "$DIR/.env"
    set +a
fi

# Kiểm tra API key
if [ -z "$GEMINI_API_KEY" ]; then
    echo "[WARNING] GEMINI_API_KEY is empty."
    echo "[!] Edit .env and set your GEMINI_API_KEY"
    echo ""
fi

export PYTHONPATH="$DIR"
if [ $# -eq 0 ]; then
    exec "$DIR/venv/bin/python" -u "$DIR/vhf_processor/main.py" "$DIR/vhf_processor/config/rpi.toml"
else
    exec "$DIR/venv/bin/python" -u "$DIR/vhf_processor/main.py" "$@"
fi
