#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$APP_ROOT/../.." && pwd)"
PYTHON="$ROOT/.venv/dev/bin/python"
[[ -x "$PYTHON" ]] || { echo "[ERROR] Run scripts/setup/setup.sh first." >&2; exit 1; }
export PYTHONPATH="$ROOT/packages/prana_core/src:$ROOT/apps/linux/src"
exec "$PYTHON" -m prana_linux.station "$@"
