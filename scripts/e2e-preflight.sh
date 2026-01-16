#!/bin/bash
# =============================================================================
# E2E Pre-Flight Check Script
# =============================================================================
#
# Story 0.6.16: AC1 - Pre-Flight Script
#
# Run this script BEFORE executing E2E tests to validate that the infrastructure
# is in a healthy state. Catches issues early without waiting for test timeouts.
#
# Usage:
#   bash scripts/e2e-preflight.sh
#
# Exit Codes:
#   0 - All checks passed
#   1 - One or more checks failed
#
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

COMPOSE_FILE="tests/e2e/infrastructure/docker-compose.e2e.yaml"
FAILED=0

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
}

print_section() {
    echo ""
    echo -e "${CYAN}─── $1 ───${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    FAILED=1
}

# =============================================================================
# Check 1: Required Containers Running
# =============================================================================

check_containers() {
    print_section "Check 1: Required Containers Running"

    local required_containers=(
        "e2e-mongodb"
        "e2e-redis"
        "e2e-azurite"
        "e2e-plantation-model"
        "e2e-collection-model"
        "e2e-ai-model"
        "e2e-plantation-mcp"
        "e2e-collection-mcp"
        "e2e-bff"
        "e2e-platform-cost"
    )

    local dapr_sidecars=(
        "e2e-plantation-model-dapr"
        "e2e-collection-model-dapr"
        "e2e-ai-model-dapr"
        "e2e-plantation-mcp-dapr"
        "e2e-collection-mcp-dapr"
        "e2e-bff-dapr"
        "e2e-platform-cost-dapr"
    )

    local running_containers
    running_containers=$(docker ps --format '{{.Names}}' 2>/dev/null || echo "")

    # Check main containers
    for container in "${required_containers[@]}"; do
        if echo "$running_containers" | grep -q "^${container}$"; then
            print_success "$container is running"
        else
            print_error "$container is NOT running"
        fi
    done

    # Check DAPR sidecars
    for sidecar in "${dapr_sidecars[@]}"; do
        if echo "$running_containers" | grep -q "^${sidecar}$"; then
            print_success "$sidecar is running"
        else
            print_warning "$sidecar is NOT running (may affect pub/sub)"
        fi
    done
}

# =============================================================================
# Check 2: Service Health Endpoints
# =============================================================================

check_health_endpoints() {
    print_section "Check 2: Service Health Endpoints"

    local health_endpoints=(
        "http://localhost:8001/health|Plantation Model"
        "http://localhost:8002/health|Collection Model"
        "http://localhost:8091/health|AI Model"
        "http://localhost:8083/health|BFF"
        "http://localhost:8084/health|Platform Cost"
    )

    for endpoint_info in "${health_endpoints[@]}"; do
        local url="${endpoint_info%%|*}"
        local name="${endpoint_info##*|}"

        local status
        status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

        if [[ "$status" == "200" ]]; then
            print_success "$name: HTTP 200 OK"
        else
            print_error "$name: HTTP $status (expected 200)"
        fi
    done

    # gRPC health checks (using grpc channel ready)
    local grpc_services=(
        "localhost:50051|Plantation Model gRPC"
        "localhost:50052|Plantation MCP gRPC"
        "localhost:50053|Collection MCP gRPC"
        "localhost:50054|Collection Model gRPC"
        "localhost:50055|Platform Cost gRPC"
        "localhost:8090|AI Model gRPC"
    )

    for service_info in "${grpc_services[@]}"; do
        local host="${service_info%%|*}"
        local name="${service_info##*|}"

        # Use grpcurl if available, otherwise skip
        if command -v grpcurl &> /dev/null; then
            if grpcurl -plaintext "$host" list &>/dev/null; then
                print_success "$name: gRPC responding"
            else
                print_warning "$name: gRPC not responding (may be normal if no reflection)"
            fi
        else
            # Skip gRPC check if grpcurl not available
            print_warning "$name: Skipped (grpcurl not installed)"
        fi
    done
}

# =============================================================================
# Check 3: MongoDB Seed Data Counts
# =============================================================================

check_mongodb_seed_data() {
    print_section "Check 3: MongoDB Seed Data Counts"

    # Check if mongodb container is running
    if ! docker ps --format '{{.Names}}' | grep -q "e2e-mongodb"; then
        print_error "MongoDB container not running - cannot check seed data"
        return
    fi

    # Expected collections and minimum counts
    local collections=(
        "plantation_e2e.factories|1|Factories"
        "plantation_e2e.regions|1|Regions"
        "plantation_e2e.farmers|0|Farmers"
        "collection_e2e.source_configs|1|Source Configs"
        "ai_model_e2e.agent_configs|1|Agent Configs"
        "ai_model_e2e.prompts|1|Prompts"
    )

    for collection_info in "${collections[@]}"; do
        IFS='|' read -r db_collection min_count name <<< "$collection_info"
        IFS='.' read -r db collection <<< "$db_collection"

        local count
        count=$(docker exec e2e-mongodb mongosh --quiet --eval "db.getSiblingDB('$db').$collection.countDocuments()" 2>/dev/null || echo "-1")

        # Clean up the output (remove any whitespace)
        count=$(echo "$count" | tr -d '[:space:]')

        if [[ "$count" -ge "$min_count" ]]; then
            print_success "$name ($db.$collection): $count documents"
        else
            print_error "$name ($db.$collection): $count documents (expected >= $min_count)"
        fi
    done
}

# =============================================================================
# Check 4: Required Environment Variables
# =============================================================================

check_environment_variables() {
    print_section "Check 4: Required Environment Variables (in shell)"

    # Critical variables
    if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
        print_success "OPENROUTER_API_KEY is set (${#OPENROUTER_API_KEY} chars)"
    else
        print_error "OPENROUTER_API_KEY is NOT set - AI extraction tests will fail"
    fi

    # Optional but useful
    if [[ -n "${PINECONE_API_KEY:-}" ]]; then
        print_success "PINECONE_API_KEY is set"
    else
        print_warning "PINECONE_API_KEY is not set (RAG tests will be skipped)"
    fi

    # Check inside AI Model container
    print_section "Check 4b: Environment Variables Inside Containers"

    if docker ps --format '{{.Names}}' | grep -q "e2e-ai-model"; then
        local container_key
        container_key=$(docker exec e2e-ai-model printenv OPENROUTER_API_KEY 2>/dev/null || echo "")

        if [[ -n "$container_key" ]]; then
            print_success "OPENROUTER_API_KEY is set inside e2e-ai-model (${#container_key} chars)"
        else
            print_error "OPENROUTER_API_KEY is NOT set inside e2e-ai-model container"
            print_error "  → Restart with: bash scripts/e2e-up.sh --down && bash scripts/e2e-up.sh --build"
        fi
    else
        print_warning "e2e-ai-model not running - cannot verify container env"
    fi
}

# =============================================================================
# Check 5: DAPR Sidecar Connectivity
# =============================================================================

check_dapr_connectivity() {
    print_section "Check 5: DAPR Sidecar Connectivity"

    # Check DAPR HTTP endpoints via the sidecars
    local dapr_endpoints=(
        "3502|Collection Model DAPR"
    )

    for endpoint_info in "${dapr_endpoints[@]}"; do
        local port="${endpoint_info%%|*}"
        local name="${endpoint_info##*|}"

        # DAPR metadata endpoint
        local status
        status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${port}/v1.0/metadata" 2>/dev/null || echo "000")

        if [[ "$status" == "200" ]]; then
            print_success "$name: DAPR sidecar responding on port $port"
        else
            print_warning "$name: DAPR sidecar not responding on port $port (HTTP $status)"
        fi
    done

    # Check pub/sub component via DAPR
    if docker ps --format '{{.Names}}' | grep -q "e2e-collection-model-dapr"; then
        # Check if pubsub component is loaded
        local pubsub_check
        pubsub_check=$(docker exec e2e-collection-model curl -s "http://localhost:3500/v1.0/metadata" 2>/dev/null | grep -o '"pubsub"' || echo "")

        if [[ -n "$pubsub_check" ]]; then
            print_success "DAPR pub/sub component is loaded"
        else
            print_warning "DAPR pub/sub component may not be loaded"
        fi
    fi
}

# =============================================================================
# Summary
# =============================================================================

print_summary() {
    print_header "Pre-Flight Check Summary"

    if [[ $FAILED -eq 0 ]]; then
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}✓ All pre-flight checks PASSED${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo "You can now run E2E tests:"
        echo '  PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v'
        echo ""
    else
        echo -e "${RED}═══════════════════════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}✗ Some pre-flight checks FAILED${NC}"
        echo -e "${RED}═══════════════════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo "Fix the issues above before running E2E tests."
        echo ""
        echo "Common fixes:"
        echo "  1. Start infrastructure: bash scripts/e2e-up.sh --build"
        echo "  2. Set environment vars: source .env"
        echo "  3. Check logs: docker compose -f $COMPOSE_FILE logs <service>"
        echo ""
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    print_header "E2E Pre-Flight Check"
    echo "Script: scripts/e2e-preflight.sh"
    echo "Story: 0.6.16 - E2E Autonomous Debugging Infrastructure"

    check_containers
    check_health_endpoints
    check_mongodb_seed_data
    check_environment_variables
    check_dapr_connectivity
    print_summary

    exit $FAILED
}

main "$@"
