#!/bin/bash
# =============================================================================
# E2E Test Runner Script - Complete Workflow
# =============================================================================
#
# Story 0.6.16: Single script to run E2E tests with transparent env var handling
#
# This script handles EVERYTHING:
# 1. Loads .env automatically
# 2. Starts E2E infrastructure (with --build)
# 3. Waits for services to be healthy
# 4. Runs pytest with correct PYTHONPATH
# 5. Stops infrastructure when done
#
# Usage:
#   bash scripts/e2e-test.sh                    # Run all E2E tests
#   bash scripts/e2e-test.sh test_05_weather    # Run specific test file
#   bash scripts/e2e-test.sh -k "checkpoint"    # Run tests matching pattern
#   bash scripts/e2e-test.sh --no-build         # Skip rebuilding images
#   bash scripts/e2e-test.sh --keep-up          # Don't stop infrastructure after
#
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

COMPOSE_FILE="tests/e2e/infrastructure/docker-compose.e2e.yaml"
ENV_FILE=".env"
BUILD_FLAG="--build"
KEEP_UP=false
PYTEST_ARGS=()

# Parse arguments
for arg in "$@"; do
    case $arg in
        --no-build)
            BUILD_FLAG=""
            ;;
        --keep-up)
            KEEP_UP=true
            ;;
        *)
            PYTEST_ARGS+=("$arg")
            ;;
    esac
done

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════"
    echo "$1"
    echo "═══════════════════════════════════════════════════════════════════════════"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

cleanup() {
    if [[ "$KEEP_UP" == false ]]; then
        print_header "Stopping E2E Infrastructure"
        docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
        print_success "Infrastructure stopped"
    else
        print_warning "Infrastructure left running (--keep-up)"
        echo "To stop: docker compose -f $COMPOSE_FILE down -v"
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# =============================================================================
# Step 1: Load Environment Variables
# =============================================================================

print_header "E2E Test Runner - Complete Workflow"
echo "Script: scripts/e2e-test.sh"
echo "Story: 0.6.16 - E2E Autonomous Debugging Infrastructure"
echo ""

if [[ -f "$ENV_FILE" ]]; then
    print_success "Loading environment variables from $ENV_FILE"
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
else
    print_warning "No .env file found - using existing shell environment"
fi

# Validate critical env vars
if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
    print_warning "OPENROUTER_API_KEY not set - AI extraction tests will be skipped"
else
    print_success "OPENROUTER_API_KEY is set (${#OPENROUTER_API_KEY} chars)"
fi

# =============================================================================
# Step 2: Start E2E Infrastructure
# =============================================================================

print_header "Starting E2E Infrastructure"

if [[ -n "$BUILD_FLAG" ]]; then
    print_success "Rebuilding Docker images"
else
    print_warning "Using existing images (--no-build)"
fi

docker compose -f "$COMPOSE_FILE" up -d $BUILD_FLAG

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
max_wait=120
elapsed=0
while [[ $elapsed -lt $max_wait ]]; do
    # Check if all services are healthy
    unhealthy=$(docker compose -f "$COMPOSE_FILE" ps 2>/dev/null | grep -v "healthy" | grep -c "running" || echo "0")
    if [[ "$unhealthy" == "0" ]]; then
        print_success "All services are healthy"
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    echo "  Waiting... (${elapsed}s / ${max_wait}s)"
done

if [[ $elapsed -ge $max_wait ]]; then
    print_warning "Some services may not be healthy - continuing anyway"
fi

# Verify env vars in containers
ai_model_key=$(docker exec e2e-ai-model printenv OPENROUTER_API_KEY 2>/dev/null || echo "")
if [[ -n "$ai_model_key" ]]; then
    print_success "OPENROUTER_API_KEY is set inside containers"
else
    print_warning "OPENROUTER_API_KEY not set in containers - AI tests will fail"
fi

# =============================================================================
# Step 3: Run E2E Tests
# =============================================================================

print_header "Running E2E Tests"

export PYTHONPATH="${PYTHONPATH:-}:.:libs/fp-proto/src"

echo ""
if [[ ${#PYTEST_ARGS[@]} -gt 0 ]]; then
    echo "Running: pytest tests/e2e/scenarios/ ${PYTEST_ARGS[*]} -v"
    pytest tests/e2e/scenarios/ "${PYTEST_ARGS[@]}" -v
else
    echo "Running: pytest tests/e2e/scenarios/ -v"
    pytest tests/e2e/scenarios/ -v
fi

print_header "E2E Tests Complete"
