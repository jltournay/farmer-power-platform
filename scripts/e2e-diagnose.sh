#!/bin/bash
# =============================================================================
# E2E Diagnostic Script
# =============================================================================
#
# Story 0.6.16: AC2 - Diagnostic Script
#
# Run this script AFTER an E2E test failure to produce a structured diagnostic
# report. Helps AI agents (and humans) identify the root cause without manually
# checking each service.
#
# Usage:
#   bash scripts/e2e-diagnose.sh
#
# Output:
#   Structured diagnostic report with:
#   - Image build dates with stale image detection
#   - Service health status
#   - MongoDB collection counts and sample documents
#   - DAPR subscription status
#   - Recent errors from all service logs
#   - Event flow trace
#   - Auto-diagnosis with likely issue and suggested investigation
#
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

COMPOSE_FILE="tests/e2e/infrastructure/docker-compose.e2e.yaml"

# Track findings for auto-diagnosis
declare -A FINDINGS
FINDINGS[stale_images]=""
FINDINGS[unhealthy_services]=""
FINDINGS[missing_env_vars]=""
FINDINGS[empty_collections]=""
FINDINGS[recent_errors]=""
FINDINGS[missing_events]=""

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}$1${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
}

print_section() {
    echo ""
    echo -e "${CYAN}┌─── $1 ───${NC}"
}

print_subsection() {
    echo -e "${CYAN}│${NC} $1"
}

print_success() {
    echo -e "${CYAN}│${NC} ${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${CYAN}│${NC} ${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${CYAN}│${NC} ${RED}✗${NC} $1"
}

print_info() {
    echo -e "${CYAN}│${NC}   $1"
}

# =============================================================================
# Section 1: Docker Image Build Dates & Stale Detection
# =============================================================================

check_image_build_dates() {
    print_header "1. Docker Image Build Dates & Stale Detection"

    local services=(
        "e2e-plantation-model|services/plantation-model"
        "e2e-collection-model|services/collection-model"
        "e2e-ai-model|services/ai-model"
        "e2e-plantation-mcp|mcp-servers/plantation-mcp"
        "e2e-collection-mcp|mcp-servers/collection-mcp"
        "e2e-bff|services/bff"
    )

    print_section "Image Build Dates vs Code Modification Times"

    for service_info in "${services[@]}"; do
        local container="${service_info%%|*}"
        local code_path="${service_info##*|}"

        # Get image creation time
        local image_created=""
        local image_created_ts=0
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            local image_id
            image_id=$(docker inspect "$container" --format '{{.Image}}' 2>/dev/null || echo "")
            if [[ -n "$image_id" ]]; then
                image_created=$(docker inspect "$image_id" --format '{{.Created}}' 2>/dev/null | cut -d'T' -f1,2 | tr 'T' ' ' | cut -d'.' -f1 || echo "unknown")
                image_created_ts=$(date -j -f "%Y-%m-%d %H:%M:%S" "$image_created" "+%s" 2>/dev/null || date -d "$image_created" "+%s" 2>/dev/null || echo "0")
            fi
        fi

        # Get latest code modification time
        local code_modified=""
        local code_modified_ts=0
        if [[ -d "$code_path/src" ]]; then
            code_modified=$(find "$code_path/src" -name "*.py" -type f -exec stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" {} \; 2>/dev/null | sort -r | head -1 || \
                           find "$code_path/src" -name "*.py" -type f -printf '%T+ %p\n' 2>/dev/null | sort -r | head -1 | cut -d' ' -f1 || \
                           echo "unknown")
            code_modified_ts=$(date -j -f "%Y-%m-%d %H:%M:%S" "$code_modified" "+%s" 2>/dev/null || date -d "$code_modified" "+%s" 2>/dev/null || echo "0")
        fi

        # Compare and detect staleness
        if [[ "$image_created" == "unknown" ]] || [[ -z "$image_created" ]]; then
            print_warning "$container: Image not found (container not running?)"
        elif [[ "$code_modified" == "unknown" ]] || [[ -z "$code_modified" ]]; then
            print_info "$container: Built $image_created (code path not found)"
        elif [[ $code_modified_ts -gt $image_created_ts ]]; then
            print_error "$container: STALE IMAGE DETECTED"
            print_info "  Image built:    $image_created"
            print_info "  Code modified:  $code_modified"
            print_info "  → Rebuild with: docker compose -f $COMPOSE_FILE build --no-cache $container"
            FINDINGS[stale_images]+="$container "
        else
            print_success "$container: Image is up-to-date"
            print_info "  Image built:    $image_created"
            print_info "  Code modified:  $code_modified"
        fi
    done
}

# =============================================================================
# Section 2: Service Health Status
# =============================================================================

check_service_health() {
    print_header "2. Service Health Status"

    print_section "Container Status"

    docker compose -f "$COMPOSE_FILE" ps 2>/dev/null | while IFS= read -r line; do
        if echo "$line" | grep -q "unhealthy\|Exit\|Restarting"; then
            print_error "$line"
            FINDINGS[unhealthy_services]+="$(echo "$line" | awk '{print $1}') "
        elif echo "$line" | grep -q "healthy"; then
            print_success "$line"
        else
            print_info "$line"
        fi
    done

    print_section "HTTP Health Endpoints"

    local endpoints=(
        "http://localhost:8001/health|Plantation Model"
        "http://localhost:8002/health|Collection Model"
        "http://localhost:8091/health|AI Model"
        "http://localhost:8083/health|BFF"
    )

    for endpoint_info in "${endpoints[@]}"; do
        local url="${endpoint_info%%|*}"
        local name="${endpoint_info##*|}"

        local response
        response=$(curl -s "$url" 2>/dev/null || echo "CONNECTION_REFUSED")
        local status
        status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

        if [[ "$status" == "200" ]]; then
            print_success "$name: HTTP 200"
        else
            print_error "$name: HTTP $status"
            print_info "  Response: $response"
            FINDINGS[unhealthy_services]+="$name "
        fi
    done
}

# =============================================================================
# Section 3: MongoDB State
# =============================================================================

check_mongodb_state() {
    print_header "3. MongoDB State"

    if ! docker ps --format '{{.Names}}' | grep -q "e2e-mongodb"; then
        print_error "MongoDB container not running!"
        FINDINGS[unhealthy_services]+="mongodb "
        return
    fi

    print_section "Collection Counts"

    local collections=(
        "plantation_e2e|factories"
        "plantation_e2e|regions"
        "plantation_e2e|farmers"
        "collection_e2e|source_configs"
        "collection_e2e|weather_documents"
        "collection_e2e|quality_events"
        "ai_model_e2e|agent_configs"
        "ai_model_e2e|prompts"
        "ai_model_e2e|workflow_checkpoints"
    )

    for collection_info in "${collections[@]}"; do
        local db="${collection_info%%|*}"
        local collection="${collection_info##*|}"

        local count
        count=$(docker exec e2e-mongodb mongosh --quiet --eval "db.getSiblingDB('$db').$collection.countDocuments()" 2>/dev/null || echo "-1")
        count=$(echo "$count" | tr -d '[:space:]')

        if [[ "$count" == "-1" ]]; then
            print_error "$db.$collection: Error querying"
        elif [[ "$count" == "0" ]]; then
            print_warning "$db.$collection: 0 documents"
            FINDINGS[empty_collections]+="$db.$collection "
        else
            print_success "$db.$collection: $count documents"
        fi
    done

    print_section "Recent Documents (weather_documents)"

    local recent_docs
    recent_docs=$(docker exec e2e-mongodb mongosh --quiet --eval "
        JSON.stringify(
            db.getSiblingDB('collection_e2e').weather_documents
              .find({}, {_id:1, 'ingestion.source_id':1, 'extraction.status':1})
              .sort({_id:-1})
              .limit(3)
              .toArray()
        )
    " 2>/dev/null || echo "[]")

    if [[ "$recent_docs" == "[]" ]]; then
        print_warning "No weather documents found"
    else
        echo "$recent_docs" | python3 -m json.tool 2>/dev/null | head -20 | while IFS= read -r line; do
            print_info "$line"
        done
    fi

    print_section "Agent Request Events (Last 3)"

    local recent_events
    recent_events=$(docker exec e2e-mongodb mongosh --quiet --eval "
        JSON.stringify(
            db.getSiblingDB('ai_model_e2e').workflow_checkpoints
              .find({})
              .sort({_id:-1})
              .limit(3)
              .toArray()
        )
    " 2>/dev/null || echo "[]")

    if [[ "$recent_events" == "[]" ]]; then
        print_warning "No workflow checkpoints found (AI Model may not have received events)"
        FINDINGS[missing_events]+="workflow_checkpoints "
    else
        echo "$recent_events" | python3 -m json.tool 2>/dev/null | head -30 | while IFS= read -r line; do
            print_info "$line"
        done
    fi
}

# =============================================================================
# Section 4: DAPR Subscriptions
# =============================================================================

check_dapr_subscriptions() {
    print_header "4. DAPR Subscription Status"

    print_section "DAPR Metadata"

    if docker ps --format '{{.Names}}' | grep -q "e2e-collection-model"; then
        local metadata
        metadata=$(docker exec e2e-collection-model curl -s "http://localhost:3500/v1.0/metadata" 2>/dev/null || echo "{}")

        if [[ "$metadata" == "{}" ]]; then
            print_error "Could not fetch DAPR metadata from Collection Model"
        else
            local app_id
            app_id=$(echo "$metadata" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','unknown'))" 2>/dev/null || echo "unknown")
            print_success "Collection Model DAPR app-id: $app_id"

            local subscriptions
            subscriptions=$(echo "$metadata" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('subscriptions',[])))" 2>/dev/null || echo "[]")
            if [[ "$subscriptions" != "[]" ]]; then
                print_success "Active subscriptions found"
            else
                print_warning "No DAPR subscriptions registered"
            fi
        fi
    fi

    if docker ps --format '{{.Names}}' | grep -q "e2e-ai-model"; then
        local ai_metadata
        ai_metadata=$(docker exec e2e-ai-model curl -s "http://localhost:3500/v1.0/metadata" 2>/dev/null || echo "{}")

        if [[ "$ai_metadata" != "{}" ]]; then
            local ai_app_id
            ai_app_id=$(echo "$ai_metadata" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','unknown'))" 2>/dev/null || echo "unknown")
            print_success "AI Model DAPR app-id: $ai_app_id"
        fi
    fi
}

# =============================================================================
# Section 5: Recent Errors from Logs
# =============================================================================

check_recent_errors() {
    print_header "5. Recent Errors from Logs (Last 5 per Service)"

    local services=("e2e-plantation-model" "e2e-collection-model" "e2e-ai-model" "e2e-bff")

    for service in "${services[@]}"; do
        print_section "$service"

        if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
            local errors
            errors=$(docker logs "$service" 2>&1 | grep -iE "error|exception|traceback|failed|critical" | tail -5 || echo "")

            if [[ -n "$errors" ]]; then
                print_error "Errors found:"
                echo "$errors" | while IFS= read -r line; do
                    print_info "${line:0:120}"
                done
                FINDINGS[recent_errors]+="$service "
            else
                print_success "No recent errors in logs"
            fi
        else
            print_warning "Container not running"
        fi
    done
}

# =============================================================================
# Section 6: Event Flow Trace
# =============================================================================

check_event_flow() {
    print_header "6. Event Flow Trace"

    print_section "AgentRequestEvent Flow"

    # Check Collection Model logs for AgentRequestEvent publishing
    if docker ps --format '{{.Names}}' | grep -q "e2e-collection-model"; then
        local agent_requests
        agent_requests=$(docker logs e2e-collection-model 2>&1 | grep -i "AgentRequestEvent\|agent_request\|publish.*event" | tail -3 || echo "")

        if [[ -n "$agent_requests" ]]; then
            print_success "AgentRequestEvent activity found in Collection Model"
            echo "$agent_requests" | while IFS= read -r line; do
                print_info "${line:0:120}"
            done
        else
            print_warning "No AgentRequestEvent activity in Collection Model logs"
            FINDINGS[missing_events]+="AgentRequestEvent "
        fi
    fi

    print_section "AgentCompletedEvent Flow"

    # Check AI Model logs for AgentCompletedEvent
    if docker ps --format '{{.Names}}' | grep -q "e2e-ai-model"; then
        local completed_events
        completed_events=$(docker logs e2e-ai-model 2>&1 | grep -i "AgentCompletedEvent\|agent_completed\|publish.*completed\|extraction.*complete" | tail -3 || echo "")

        if [[ -n "$completed_events" ]]; then
            print_success "AgentCompletedEvent activity found in AI Model"
            echo "$completed_events" | while IFS= read -r line; do
                print_info "${line:0:120}"
            done
        else
            print_warning "No AgentCompletedEvent activity in AI Model logs"
            FINDINGS[missing_events]+="AgentCompletedEvent "
        fi
    fi

    print_section "LLM API Calls"

    # Check for OpenRouter/LLM calls
    if docker ps --format '{{.Names}}' | grep -q "e2e-ai-model"; then
        local llm_calls
        llm_calls=$(docker logs e2e-ai-model 2>&1 | grep -i "openrouter\|llm\|claude\|haiku\|api.*call" | tail -3 || echo "")

        if [[ -n "$llm_calls" ]]; then
            print_success "LLM API activity found"
            echo "$llm_calls" | while IFS= read -r line; do
                print_info "${line:0:120}"
            done
        else
            print_warning "No LLM API activity in AI Model logs"
            print_info "This may indicate OPENROUTER_API_KEY is not set inside container"
        fi
    fi
}

# =============================================================================
# Section 7: Auto-Diagnosis
# =============================================================================

auto_diagnosis() {
    print_header "7. Auto-Diagnosis"

    print_section "Likely Issues and Suggested Investigations"

    local has_issues=0

    # Check for stale images
    if [[ -n "${FINDINGS[stale_images]}" ]]; then
        has_issues=1
        print_error "LIKELY ISSUE: Stale Docker images detected"
        print_info "  Affected: ${FINDINGS[stale_images]}"
        print_info "  Impact: Tests are running against old code"
        print_info "  Fix: docker compose -f $COMPOSE_FILE up -d --build"
        echo ""
    fi

    # Check for unhealthy services
    if [[ -n "${FINDINGS[unhealthy_services]}" ]]; then
        has_issues=1
        print_error "LIKELY ISSUE: Services not healthy"
        print_info "  Affected: ${FINDINGS[unhealthy_services]}"
        print_info "  Impact: Service calls will fail or timeout"
        print_info "  Fix: Check logs with: docker logs <service-name>"
        echo ""
    fi

    # Check for missing environment variables
    if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
        has_issues=1
        print_error "LIKELY ISSUE: OPENROUTER_API_KEY not set"
        print_info "  Impact: AI extraction will fail"
        print_info "  Fix: export OPENROUTER_API_KEY=your-key && bash scripts/e2e-up.sh --build"
        echo ""
    fi

    # Check for empty critical collections
    if [[ -n "${FINDINGS[empty_collections]}" ]]; then
        has_issues=1
        print_warning "POTENTIAL ISSUE: Empty collections"
        print_info "  Affected: ${FINDINGS[empty_collections]}"
        print_info "  Impact: Tests may fail due to missing seed data or processing issues"
        print_info "  Check: Verify seed data and event flow"
        echo ""
    fi

    # Check for missing events
    if [[ -n "${FINDINGS[missing_events]}" ]]; then
        has_issues=1
        print_warning "POTENTIAL ISSUE: Missing event activity"
        print_info "  Missing: ${FINDINGS[missing_events]}"
        print_info "  Impact: Async processing pipeline may be broken"
        print_info "  Check: DAPR sidecars, Redis pub/sub, event handlers"
        echo ""
    fi

    # Check for recent errors
    if [[ -n "${FINDINGS[recent_errors]}" ]]; then
        has_issues=1
        print_warning "POTENTIAL ISSUE: Errors in service logs"
        print_info "  Affected: ${FINDINGS[recent_errors]}"
        print_info "  Impact: Services may be partially working"
        print_info "  Check: docker logs <service-name> | grep -i error"
        echo ""
    fi

    if [[ $has_issues -eq 0 ]]; then
        print_success "No obvious issues detected"
        print_info "If tests are still failing, check:"
        print_info "  1. Test assertions match expected behavior"
        print_info "  2. Seed data is correct for test scenarios"
        print_info "  3. Timeouts are sufficient for async processing"
    fi

    print_section "Debugging Commands"
    print_info "View all container logs:"
    print_info "  docker compose -f $COMPOSE_FILE logs --tail=50"
    print_info ""
    print_info "View specific service logs:"
    print_info "  docker logs e2e-ai-model --tail=100"
    print_info ""
    print_info "Check environment in container:"
    print_info "  docker exec e2e-ai-model printenv | grep -i key"
    print_info ""
    print_info "Query MongoDB directly:"
    print_info "  docker exec e2e-mongodb mongosh --eval \"db.getSiblingDB('collection_e2e').weather_documents.find().limit(5)\""
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo ""
    echo -e "${BOLD}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║                     E2E DIAGNOSTIC REPORT                                 ║${NC}"
    echo -e "${BOLD}║                                                                           ║${NC}"
    echo -e "${BOLD}║  Story: 0.6.16 - E2E Autonomous Debugging Infrastructure                 ║${NC}"
    echo -e "${BOLD}║  Script: scripts/e2e-diagnose.sh                                         ║${NC}"
    echo -e "${BOLD}║  Generated: $(date '+%Y-%m-%d %H:%M:%S')                                         ║${NC}"
    echo -e "${BOLD}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"

    check_image_build_dates
    check_service_health
    check_mongodb_state
    check_dapr_subscriptions
    check_recent_errors
    check_event_flow
    auto_diagnosis

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}End of Diagnostic Report${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

main "$@"
