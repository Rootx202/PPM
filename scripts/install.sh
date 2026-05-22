#!/usr/bin/env bash
# scripts/install.sh - Bootstrap PPM installation
# Usage: bash scripts/install.sh

set -euo pipefail

echo "╔══════════════════════════════════════╗"
echo "║     PPM - Python Package Manager     ║"
echo "║          Installation Script         ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check Python version
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo "❌ Python not found. Please install Python 3.12+"
    exit 1
fi

PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PY_VERSION found at $PYTHON"

if $PYTHON -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
    echo "✅ Python version OK (>= 3.12)"
else
    echo "⚠️  Warning: Python 3.12+ recommended. Found $PY_VERSION"
fi

# Install PPM
echo ""
echo "→ Installing PPM in development mode..."
$PYTHON -m pip install -e ".[dev]" --quiet

echo ""
echo "✅ PPM installed successfully!"
echo ""
echo "Try it with:"
echo "  ppm --help"
echo "  ppm doctor"
echo "  ppm init"
