#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi
export PYTHONPATH="$DIR"
if [ $# -eq 0 ]; then
    exec "$DIR/venv/bin/python" -u "$DIR/vhf_processor/main.py" "$DIR/vhf_processor/config/rpi.toml"
else
    exec "$DIR/venv/bin/python" -u "$DIR/vhf_processor/main.py" "$@"
fi
