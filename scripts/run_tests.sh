#!/usr/bin/env bash
# scripts/run_tests.sh - Run PPM test suite
# Usage: bash scripts/run_tests.sh

set -euo pipefail

echo "🧪 Running PPM Test Suite..."
echo ""

python -m pytest tests/ \
    --tb=short \
    -v \
    --cov=ppm \
    --cov-report=term-missing \
    --cov-report=html:docs/coverage \
    -m "not slow" \
    "$@"

echo ""
echo "✅ Tests complete!"
