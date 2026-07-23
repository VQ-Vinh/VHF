#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo "[DEPRECATED] Use ./apps/linux/run.sh" >&2
exec "$ROOT/apps/linux/run.sh" "$@"
