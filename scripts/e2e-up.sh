#!/bin/bash
# =============================================================================
# E2E Infrastructure Launcher Script
# =============================================================================
#
# Story 0.6.16: AC0 - E2E Launcher Script
#
# This script starts the E2E infrastructure with correct environment variable
# handling, ensuring variables are available INSIDE Docker containers.
#
# Usage:
#   bash scripts/e2e-up.sh          # Start without rebuilding images
#   bash scripts/e2e-up.sh --build  # Rebuild images before starting
#   bash scripts/e2e-up.sh --down   # Stop infrastructure
#
# Environment Variables:
#   The following variables are required for full E2E functionality:
#   - OPENROUTER_API_KEY: Required for AI extraction tests
#   - PINECONE_API_KEY: Required for RAG vectorization tests
#   - AZURE_DOCUMENT_ENDPOINT: Optional, for Azure Document Intelligence
#   - AZURE_DOCUMENT_KEY: Optional, for Azure Document Intelligence
#
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

COMPOSE_FILE="tests/e2e/infrastructure/docker-compose.e2e.yaml"
ENV_FILE=".env"

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

# =============================================================================
# Step 1: Load Environment Variables
# =============================================================================

load_env_vars() {
    print_header "Step 1: Loading Environment Variables"

    if [[ -f "$ENV_FILE" ]]; then
        print_success "Found $ENV_FILE"

        # Use set -a to export all variables, then source, then set +a
        # This pattern ensures variables are available to docker-compose
        set -a
        # shellcheck source=/dev/null
        source "$ENV_FILE"
        set +a

        print_success "Exported environment variables from $ENV_FILE"
    else
        print_warning "No $ENV_FILE found - using existing shell environment"
    fi
}

# =============================================================================
# Step 2: Validate Required Environment Variables
# =============================================================================

validate_env_vars() {
    print_header "Step 2: Validating Environment Variables"

    local missing_critical=0
    local missing_optional=0

    # Critical variables (required for AI tests)
    if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
        print_error "OPENROUTER_API_KEY is NOT set"
        print_error "  → AI extraction tests WILL FAIL"
        print_error "  → Set in .env or export before running this script"
        missing_critical=1
    else
        print_success "OPENROUTER_API_KEY is set (${#OPENROUTER_API_KEY} chars)"
    fi

    if [[ -z "${PINECONE_API_KEY:-}" ]]; then
        print_warning "PINECONE_API_KEY is not set (RAG vectorization tests will be skipped)"
        missing_optional=1
    else
        print_success "PINECONE_API_KEY is set"
    fi

    # Optional variables
    if [[ -z "${AZURE_DOCUMENT_ENDPOINT:-}" ]]; then
        print_warning "AZURE_DOCUMENT_ENDPOINT is not set (Azure OCR tests will be skipped)"
    else
        print_success "AZURE_DOCUMENT_ENDPOINT is set"
    fi

    if [[ $missing_critical -eq 1 ]]; then
        echo ""
        print_error "═══════════════════════════════════════════════════════════════════════════"
        print_error "CRITICAL: Missing required environment variables!"
        print_error ""
        print_error "To fix:"
        print_error "  1. Create .env file with required variables, OR"
        print_error "  2. Export variables in your shell before running:"
        print_error "     export OPENROUTER_API_KEY=your-key"
        print_error "═══════════════════════════════════════════════════════════════════════════"
        echo ""

        # Don't exit - let user decide if they want to proceed
        read -p "Continue anyway? Tests requiring AI will fail. (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# =============================================================================
# Step 3: Start Docker Compose
# =============================================================================

start_infrastructure() {
    local build_flag=""

    print_header "Step 3: Starting E2E Infrastructure"

    # Check for --build flag
    if [[ "${1:-}" == "--build" ]]; then
        build_flag="--build"
        print_success "Will rebuild Docker images before starting"
    else
        print_warning "Starting WITHOUT rebuilding images"
        print_warning "If you modified service code, use: bash scripts/e2e-up.sh --build"
    fi

    echo ""
    echo "Running: docker compose -f $COMPOSE_FILE up -d $build_flag"
    echo ""

    # Run docker compose with environment variables exported
    docker compose -f "$COMPOSE_FILE" up -d $build_flag

    print_success "Docker Compose started"
}

# =============================================================================
# Step 4: Verify Environment Variables Inside Containers
# =============================================================================

verify_container_env() {
    print_header "Step 4: Verifying Environment Variables in Containers"

    local containers=("e2e-ai-model" "e2e-collection-model" "e2e-plantation-model")
    local all_verified=1

    # Wait for containers to start
    echo "Waiting 5s for containers to start..."
    sleep 5

    for container in "${containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            # Check if OPENROUTER_API_KEY is set inside container
            local openrouter_set
            openrouter_set=$(docker exec "$container" printenv OPENROUTER_API_KEY 2>/dev/null || echo "")

            if [[ -n "$openrouter_set" ]]; then
                print_success "$container: OPENROUTER_API_KEY is set (${#openrouter_set} chars)"
            else
                print_error "$container: OPENROUTER_API_KEY is NOT set inside container"
                all_verified=0
            fi
        else
            print_warning "$container: Container not running yet"
        fi
    done

    if [[ $all_verified -eq 0 ]]; then
        echo ""
        print_warning "Some containers are missing environment variables."
        print_warning "This can happen if you started docker-compose before loading .env"
        print_warning ""
        print_warning "To fix:"
        print_warning "  1. Stop infrastructure: docker compose -f $COMPOSE_FILE down -v"
        print_warning "  2. Reload: bash scripts/e2e-up.sh --build"
    fi
}

# =============================================================================
# Step 5: Wait for Health Checks
# =============================================================================

wait_for_health() {
    print_header "Step 5: Waiting for Services to be Healthy"

    local max_wait=120  # seconds
    local interval=5
    local elapsed=0

    while [[ $elapsed -lt $max_wait ]]; do
        local all_healthy=1
        local status_output=""

        # Check each service health
        while IFS= read -r line; do
            status_output+="$line"$'\n'
            if [[ "$line" != *"healthy"* ]] && [[ "$line" == *"running"* ]]; then
                all_healthy=0
            fi
        done < <(docker compose -f "$COMPOSE_FILE" ps --format "{{.Name}}: {{.Status}}" 2>/dev/null || echo "")

        if [[ $all_healthy -eq 1 ]] && [[ -n "$status_output" ]]; then
            print_success "All services are healthy!"
            return 0
        fi

        echo "Waiting for services to be healthy... (${elapsed}s / ${max_wait}s)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done

    print_warning "Timeout waiting for all services to be healthy"
    print_warning "Some tests may fail - check: docker compose -f $COMPOSE_FILE ps"
}

# =============================================================================
# Handle --down flag
# =============================================================================

stop_infrastructure() {
    print_header "Stopping E2E Infrastructure"

    docker compose -f "$COMPOSE_FILE" down -v

    print_success "Infrastructure stopped and volumes removed"
}

# =============================================================================
# Main
# =============================================================================

main() {
    # Handle --down flag
    if [[ "${1:-}" == "--down" ]]; then
        stop_infrastructure
        exit 0
    fi

    print_header "E2E Infrastructure Launcher"
    echo "Script: scripts/e2e-up.sh"
    echo "Story: 0.6.16 - E2E Autonomous Debugging Infrastructure"
    echo ""

    load_env_vars
    validate_env_vars
    start_infrastructure "${1:-}"
    verify_container_env
    wait_for_health

    print_header "E2E Infrastructure Ready"
    echo ""
    echo "Next steps:"
    echo "  1. Run pre-flight check:  bash scripts/e2e-preflight.sh"
    echo "  2. Run E2E tests:"
    echo '     PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v'
    echo "  3. If tests fail, diagnose: bash scripts/e2e-diagnose.sh"
    echo "  4. When done, stop:        bash scripts/e2e-up.sh --down"
    echo ""
}

main "$@"
