#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "============================================================"
echo "  VHF Radio Processor - Setup"
echo "============================================================"
echo ""

# 1. Check Python >= 3.11
echo "[*] Checking Python version..."
PYVER=$(python3 --version 2>/dev/null || python --version 2>/dev/null || true)
if [ -z "$PYVER" ]; then
    echo "[ERROR] Python not found. Install Python 3.11+"
    exit 1
fi
echo "[OK] $PYVER"

# Extract major.minor
PYNUM=$(echo "$PYVER" | grep -oP '\d+\.\d+' | head -1)
PYMAJOR=${PYNUM%.*}
PYMINOR=${PYNUM#*.}
if [ "$PYMAJOR" -lt 3 ] || { [ "$PYMAJOR" -eq 3 ] && [ "$PYMINOR" -lt 11 ]; }; then
    echo "[ERROR] Python 3.11+ required. Found: $PYVER"
    exit 1
fi

PYTHON=$(command -v python3 || command -v python)

# 2. Create virtual environment
if [ -d "$DIR/venv" ]; then
    echo "[*] Virtual environment already exists, skipping..."
else
    echo "[*] Creating virtual environment..."
    $PYTHON -m venv "$DIR/venv"
    echo "[OK] Virtual environment created"
fi

# 3. Install dependencies (editable install)
echo "[*] Installing dependencies..."
"$DIR/venv/bin/pip" install --upgrade pip -q
"$DIR/venv/bin/pip" install -e .
echo "[OK] Dependencies installed"

# 4. Create data directories
mkdir -p "$DIR/data/audio" "$DIR/data/results"
echo "[OK] Data directories ready"

echo ""
echo "============================================================"
echo "  Setup complete!"
echo "============================================================"
echo ""
echo "  Run: ./run.sh"
echo ""
