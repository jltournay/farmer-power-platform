#!/bin/bash
# =============================================================================
# E2E Test Runner Script
# =============================================================================
#
# Story 0.6.16: Wrapper script that handles environment variables transparently
#
# This script loads .env, sets PYTHONPATH, and runs pytest so users don't have
# to manually manage environment variables.
#
# Usage:
#   bash scripts/e2e-test.sh                    # Run all E2E tests
#   bash scripts/e2e-test.sh test_05_weather    # Run specific test file
#   bash scripts/e2e-test.sh -k "checkpoint"    # Run tests matching pattern
#
# =============================================================================

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ENV_FILE=".env"

# =============================================================================
# Load Environment Variables
# =============================================================================

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "E2E Test Runner"
echo "═══════════════════════════════════════════════════════════════════════════"

if [[ -f "$ENV_FILE" ]]; then
    echo -e "${GREEN}✓${NC} Loading environment variables from $ENV_FILE"
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
else
    echo -e "${YELLOW}⚠${NC} No .env file found - using existing shell environment"
fi

# Validate critical env vars
if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
    echo -e "${YELLOW}⚠${NC} OPENROUTER_API_KEY not set - AI extraction tests will be skipped"
else
    echo -e "${GREEN}✓${NC} OPENROUTER_API_KEY is set"
fi

# =============================================================================
# Set PYTHONPATH
# =============================================================================

export PYTHONPATH="${PYTHONPATH:-}:.:libs/fp-proto/src"
echo -e "${GREEN}✓${NC} PYTHONPATH configured"

# =============================================================================
# Run pytest
# =============================================================================

echo ""
echo "Running: pytest tests/e2e/scenarios/ $*"
echo ""

pytest tests/e2e/scenarios/ -v "$@"
