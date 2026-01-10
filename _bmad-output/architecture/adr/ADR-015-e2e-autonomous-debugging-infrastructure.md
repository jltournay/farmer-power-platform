# ADR-015: E2E Autonomous Debugging Infrastructure

**Status:** Accepted
**Date:** 2026-01-10
**Deciders:** Winston (Architect), Jeanlouistournay
**Related Stories:** Story 0.75.18 (E2E Weather Extraction - blocked), Epic 0.6
**Problem Observed:** AI agents require human supervision to debug E2E failures

## Context

During Story 0.75.18 implementation, an AI agent spent 2+ days debugging an E2E test failure without identifying the root cause. The agent:

1. Made 3 valid bug fixes in AI Model service
2. But the actual blocker was in Collection Model (documents not being created)
3. Required human intervention to identify the correct debugging direction

### Root Cause Analysis

| Gap | Impact |
|-----|--------|
| No diagnostic tooling | Agent reads code instead of querying actual state |
| No checkpoint-based tests | Single 90s timeout with 12 possible failure points |
| No pre-flight validation | Tests run against broken infrastructure |
| Insufficient logging | Agent can't observe event flow between services |
| No stuck detection | Agent spins for hours without escalating |
| **Environment variable confusion** | Agent doesn't know how to properly pass env vars to Docker |
| **Local vs CI differences** | Agent uses CI patterns locally or vice versa |
| **No env verification** | Agent can't confirm env vars are set inside containers |

### Environment Variable Problem (Critical)

Agents consistently struggle with environment variable handling because they don't understand **how Docker Compose resolves environment variables**.

#### Docker Compose Environment Resolution (How It Actually Works)

```yaml
# docker-compose.e2e.yaml
services:
  ai-model:
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}  # Substitution from shell
      # OR
      - OPENROUTER_API_KEY  # Inherits from shell if variable exists
```

**Resolution order:**
1. Docker Compose reads `environment:` section
2. `${VAR}` or bare `VAR` → looks in the **shell environment** of the process running `docker compose`
3. If not found → empty string (silent failure!)

#### The Same docker-compose.yaml Works for Both CI and Local

The difference is **how the shell environment gets populated**, not the docker-compose configuration:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENVIRONMENT VARIABLE FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LOCAL:                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │    .env      │───►│ set -a &&    │───►│    Shell     │───►│  Docker   │  │
│  │    file      │    │ source .env  │    │ Environment  │    │ Compose   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘  │
│                                                                              │
│  CI (GitHub Actions):                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │   GitHub     │───►│  env: block  │───►│    Shell     │───►│  Docker   │  │
│  │   Secrets    │    │  in workflow │    │ Environment  │    │ Compose   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘  │
│                                                                              │
│  SAME docker-compose.yaml in both cases!                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Why Agents Fail

| What Agent Does | Why It Fails |
|-----------------|--------------|
| `source .env && docker compose up` | `source` without `set -a` doesn't export variables |
| `docker compose up` (no env loading) | Shell has no variables to pass |
| Checks `$OPENROUTER_API_KEY` in shell | Variable may be set in shell but container started before it was exported |
| **Fixes code, runs `docker compose up` without `--build`** | **Tests stale image, fix not included** |

### Stale Docker Image Problem (Critical)

Agents frequently make code fixes but forget to rebuild images:

```
Agent workflow:
1. E2E test fails
2. Agent finds bug in services/ai-model/src/...
3. Agent fixes the code
4. Agent runs: docker compose up -d          ← WRONG! No --build
5. E2E test still fails
6. Agent thinks fix didn't work, tries something else
7. ... hours of wasted debugging ...
```

**The fix was correct, but it was never built into the image.**

#### How to Detect Stale Images

```bash
# Check when image was built
docker inspect e2e-ai-model --format='{{.Created}}'
# Output: 2026-01-10T08:30:00Z

# Check when code was last modified
ls -la services/ai-model/src/ai_model/main.py
# Output: -rw-r--r-- 1 user staff 5000 Jan 10 10:45 main.py

# If code modified AFTER image created → STALE IMAGE!
```

#### Image Age Check (Added to Diagnostic Script)

```bash
echo "=== IMAGE BUILD DATES ==="
for container in e2e-ai-model e2e-collection-model e2e-plantation-model; do
    IMAGE_DATE=$(docker inspect $container --format='{{.Created}}' 2>/dev/null | cut -d'T' -f1,2 | tr 'T' ' ' | cut -d'.' -f1)
    echo "$container: Built at $IMAGE_DATE"
done

echo ""
echo "=== RECENT CODE CHANGES ==="
echo "Last modified files in services/:"
find services/*/src -name "*.py" -mmin -60 -exec ls -la {} \; 2>/dev/null | head -5
echo ""
echo "⚠ If code was modified AFTER image build time, run: docker compose up -d --build"
```

#### The Correct Pattern

**Local:**
```bash
# set -a = auto-export all variables, source = load file, set +a = stop auto-export
set -a && source .env && set +a && docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
```

**CI (GitHub Actions):**
```yaml
jobs:
  e2e:
    env:
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
    steps:
      - run: docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
      # env vars automatically available to docker compose
```

#### How to Verify (Critical for Debugging)

The agent must verify env vars **inside the container**, not in the shell:

```bash
# WRONG - checks shell, not container
echo $OPENROUTER_API_KEY

# CORRECT - checks what the container actually has
docker exec e2e-ai-model printenv OPENROUTER_API_KEY
```

If the container doesn't have the variable, the problem is in the loading step, not docker-compose.

### The Debugging Spiral Pattern

```
E2E Test Fails (timeout)
       │
       ├── Agent examines code in Service A
       ├── Finds and fixes bugs in Service A
       ├── Test still fails
       ├── Agent examines more code in Service A
       ├── ...hours pass...
       │
       └── Human intervenes: "Have you checked Service B?"
           └── Root cause was in Service B all along
```

The agent lacks tools to **observe actual system state** and **isolate failure points**.

## Decision

**Implement E2E Autonomous Debugging Infrastructure: diagnostic scripts, pre-flight checks, and checkpoint-based test helpers that enable AI agents to debug E2E failures without human supervision.**

### Design Principles

1. **Scripts over instructions** - Executable tools, not documentation that pollutes context
2. **Scoped to E2E** - Infrastructure lives in `tests/e2e/` and `scripts/`, not in global CLAUDE.md
3. **Observable state** - Query actual MongoDB, service health, event flow
4. **Checkpoint isolation** - Tests fail at specific points with actionable messages
5. **Pre-flight validation** - Verify infrastructure before running tests

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    E2E AUTONOMOUS DEBUGGING INFRASTRUCTURE                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  LAYER 1: PRE-FLIGHT VALIDATION                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  scripts/e2e-preflight.sh                                               │ │
│  │  - Verify all containers running and healthy                            │ │
│  │  - Verify MongoDB seed data counts                                      │ │
│  │  - Verify environment variables set                                     │ │
│  │  - Verify DAPR sidecars connected                                       │ │
│  │  - Verify no port conflicts                                             │ │
│  │  EXIT: Fail fast if infrastructure broken                               │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  LAYER 2: DIAGNOSTIC TOOLING                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  scripts/e2e-diagnose.sh                                                │ │
│  │  - Service health status (all endpoints)                                │ │
│  │  - MongoDB collection counts and sample documents                       │ │
│  │  - DAPR subscription status                                             │ │
│  │  - Recent errors from all service logs                                  │ │
│  │  - Event flow trace (grep for event names in logs)                      │ │
│  │  OUTPUT: Structured diagnostic report                                   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  LAYER 3: CHECKPOINT-BASED TEST HELPERS                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  tests/e2e/helpers/checkpoints.py                                       │ │
│  │  - wait_for_documents_created() → Checkpoint 1                          │ │
│  │  - wait_for_event_published() → Checkpoint 2                            │ │
│  │  - wait_for_event_received() → Checkpoint 3                             │ │
│  │  - wait_for_processing_complete() → Checkpoint 4                        │ │
│  │  FAILURE: Specific checkpoint + diagnostic context                      │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  LAYER 4: SERVICE-SPECIFIC DIAGNOSTICS                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  tests/e2e/helpers/diagnostics.py                                       │ │
│  │  - diagnose_collection_model() → Pull job, iteration, document storage  │ │
│  │  - diagnose_ai_model() → Event receipt, config loading, LLM calls       │ │
│  │  - diagnose_plantation_model() → Event handling, data updates           │ │
│  │  - diagnose_event_flow() → End-to-end event trace                       │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Implementation

### 0. E2E Launcher Script (`scripts/e2e-up.sh`)

A single command that handles environment variables correctly:

```bash
#!/bin/bash
# scripts/e2e-up.sh - Correct way to start E2E infrastructure
# Usage: bash scripts/e2e-up.sh [--build]

set -e

# Load and EXPORT .env variables (set -a makes all variables exported)
if [ -f .env ]; then
    echo "Loading .env file..."
    set -a
    source .env
    set +a
else
    echo "WARNING: No .env file found. API keys may not be available."
fi

# Build flag
BUILD_FLAG=""
if [ "$1" = "--build" ]; then
    BUILD_FLAG="--build"
    echo "Building images..."
fi

# Start infrastructure
echo "Starting E2E infrastructure..."
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d $BUILD_FLAG

# Wait for services
echo "Waiting for services to be healthy..."
sleep 5

# Verify environment variables inside containers
echo ""
echo "=== ENVIRONMENT VERIFICATION ==="
echo "Checking OPENROUTER_API_KEY in ai-model container:"
OPENROUTER_CHECK=$(docker exec e2e-ai-model printenv OPENROUTER_API_KEY 2>/dev/null | head -c 10)
if [ -n "$OPENROUTER_CHECK" ]; then
    echo "  ✓ OPENROUTER_API_KEY is set (starts with: ${OPENROUTER_CHECK}...)"
else
    echo "  ❌ OPENROUTER_API_KEY is NOT set in container"
    echo "  → AI extraction tests will fail"
    echo "  → Ensure .env contains OPENROUTER_API_KEY and restart with: bash scripts/e2e-up.sh --build"
fi

echo ""
echo "=== E2E INFRASTRUCTURE READY ==="
echo "Run tests with: PYTHONPATH=\"\${PYTHONPATH}:.:libs/fp-proto/src\" pytest tests/e2e/scenarios/ -v"
```

**Why this matters:**
- `set -a` makes all sourced variables automatically exported
- `set +a` turns off auto-export after sourcing
- Script verifies env vars are actually inside the container
- Provides clear feedback if something is wrong

### 1. Pre-Flight Script (`scripts/e2e-preflight.sh`)

```bash
#!/bin/bash
# E2E Pre-Flight Check - Run before E2E tests
set -e

echo "=== E2E PRE-FLIGHT CHECK ==="

FAILED=0

# Check containers
echo -e "\n[1/5] Checking containers..."
REQUIRED_CONTAINERS="e2e-mongodb e2e-redis e2e-plantation-model e2e-collection-model e2e-ai-model"
for container in $REQUIRED_CONTAINERS; do
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "  ❌ Missing: $container"
        FAILED=1
    else
        echo "  ✓ Running: $container"
    fi
done

# Check health endpoints
echo -e "\n[2/5] Checking service health..."
HEALTH_ENDPOINTS="http://localhost:8001/health http://localhost:8002/health http://localhost:8003/health"
for endpoint in $HEALTH_ENDPOINTS; do
    if curl -sf "$endpoint" > /dev/null 2>&1; then
        echo "  ✓ Healthy: $endpoint"
    else
        echo "  ❌ Unhealthy: $endpoint"
        FAILED=1
    fi
done

# Check MongoDB seed data
echo -e "\n[3/5] Checking MongoDB seed data..."
SEED_CHECK=$(docker exec e2e-mongodb mongosh --quiet --eval "
    db = db.getSiblingDB('collection_e2e');
    sc = db.source_configs.countDocuments();
    db = db.getSiblingDB('plantation_e2e');
    r = db.regions.countDocuments();
    db = db.getSiblingDB('ai_model_e2e');
    ac = db.agent_configs.countDocuments();
    p = db.prompts.countDocuments();
    print('source_configs:' + sc + ',regions:' + r + ',agent_configs:' + ac + ',prompts:' + p);
")
echo "  Counts: $SEED_CHECK"

# Check environment variables IN SHELL
echo -e "\n[4/6] Checking shell environment variables..."
if [ -n "$OPENROUTER_API_KEY" ]; then
    echo "  ✓ OPENROUTER_API_KEY is set in shell"
else
    echo "  ⚠ OPENROUTER_API_KEY not set in shell"
    echo "    → Run: set -a && source .env && set +a"
fi

# Check environment variables INSIDE CONTAINERS (critical!)
echo -e "\n[5/6] Checking environment variables INSIDE containers..."
AI_MODEL_KEY=$(docker exec e2e-ai-model printenv OPENROUTER_API_KEY 2>/dev/null || echo "")
if [ -n "$AI_MODEL_KEY" ]; then
    echo "  ✓ OPENROUTER_API_KEY is set inside e2e-ai-model container"
else
    echo "  ❌ OPENROUTER_API_KEY is NOT set inside e2e-ai-model container"
    echo "    → This is the actual problem! Container doesn't have the key."
    echo "    → Fix: bash scripts/e2e-up.sh --build"
    FAILED=1
fi

# Check DAPR sidecars
echo -e "\n[6/6] Checking DAPR sidecars..."
DAPR_PORTS="3501 3502 3503"
for port in $DAPR_PORTS; do
    if curl -sf "http://localhost:$port/v1.0/healthz" > /dev/null 2>&1; then
        echo "  ✓ DAPR sidecar on port $port"
    else
        echo "  ❌ DAPR sidecar not responding on port $port"
        FAILED=1
    fi
done

# Summary
echo -e "\n=== PRE-FLIGHT RESULT ==="
if [ $FAILED -eq 0 ]; then
    echo "✓ All checks passed - ready for E2E tests"
    exit 0
else
    echo "❌ Pre-flight failed - fix issues before running tests"
    exit 1
fi
```

### 2. Diagnostic Script (`scripts/e2e-diagnose.sh`)

```bash
#!/bin/bash
# E2E Diagnostic Report - Run when tests fail

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                     E2E DIAGNOSTIC REPORT                             ║"
echo "║                     $(date '+%Y-%m-%d %H:%M:%S')                              ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

echo -e "\n━━━ 0. IMAGE BUILD DATES (Check for Stale Images) ━━━"
STALE_WARNING=0
for container in e2e-ai-model e2e-collection-model e2e-plantation-model; do
    IMAGE_DATE=$(docker inspect $container --format='{{.Created}}' 2>/dev/null | cut -d'.' -f1)
    if [ -n "$IMAGE_DATE" ]; then
        echo "$container: $IMAGE_DATE"
    else
        echo "$container: NOT RUNNING"
    fi
done

echo -e "\nRecent code changes (last 60 min):"
RECENT_CHANGES=$(find services/*/src -name "*.py" -mmin -60 2>/dev/null | wc -l | tr -d ' ')
if [ "$RECENT_CHANGES" -gt 0 ]; then
    echo "  ⚠ $RECENT_CHANGES files modified in last hour"
    find services/*/src -name "*.py" -mmin -60 -exec ls -la {} \; 2>/dev/null | head -3
    echo "  → If you modified code, rebuild with: docker compose up -d --build"
else
    echo "  ✓ No recent code changes"
fi

echo -e "\n━━━ 1. SERVICE HEALTH ━━━"
echo "Collection Model: $(curl -sf http://localhost:8002/health | jq -c . 2>/dev/null || echo 'UNREACHABLE')"
echo "AI Model:         $(curl -sf http://localhost:8003/health | jq -c . 2>/dev/null || echo 'UNREACHABLE')"
echo "Plantation Model: $(curl -sf http://localhost:8001/health | jq -c . 2>/dev/null || echo 'UNREACHABLE')"

echo -e "\n━━━ 2. MONGODB STATE ━━━"
docker exec e2e-mongodb mongosh --quiet --eval "
    print('--- collection_e2e ---');
    db = db.getSiblingDB('collection_e2e');
    print('  source_configs: ' + db.source_configs.countDocuments());
    print('  weather_documents: ' + db.weather_documents.countDocuments());
    print('  documents: ' + db.documents.countDocuments());

    print('--- ai_model_e2e ---');
    db = db.getSiblingDB('ai_model_e2e');
    print('  agent_configs: ' + db.agent_configs.countDocuments());
    print('  prompts: ' + db.prompts.countDocuments());

    print('--- plantation_e2e ---');
    db = db.getSiblingDB('plantation_e2e');
    print('  regions: ' + db.regions.countDocuments());
    print('  farmers: ' + db.farmers.countDocuments());
"

echo -e "\n━━━ 3. RECENT WEATHER DOCUMENTS ━━━"
docker exec e2e-mongodb mongosh --quiet --eval "
    db = db.getSiblingDB('collection_e2e');
    docs = db.weather_documents.find().sort({_id: -1}).limit(2).toArray();
    if (docs.length === 0) {
        print('NO WEATHER DOCUMENTS FOUND');
    } else {
        docs.forEach(d => {
            print('ID: ' + d._id);
            print('  Status: ' + (d.extraction ? d.extraction.status : 'no extraction field'));
            print('  Source: ' + (d.ingestion ? d.ingestion.source_id : 'unknown'));
        });
    }
"

echo -e "\n━━━ 4. DAPR SUBSCRIPTIONS ━━━"
echo "AI Model subscriptions:"
curl -sf http://localhost:3503/dapr/subscribe 2>/dev/null | jq -c '.[] | {topic, route}' || echo "  Unable to fetch"

echo -e "\n━━━ 5. RECENT ERRORS ━━━"
echo "--- Collection Model ---"
docker logs e2e-collection-model 2>&1 | grep -i "error\|exception\|traceback" | tail -5 || echo "  No recent errors"

echo -e "\n--- AI Model ---"
docker logs e2e-ai-model 2>&1 | grep -i "error\|exception\|traceback" | tail -5 || echo "  No recent errors"

echo -e "\n━━━ 6. EVENT FLOW TRACE ━━━"
echo "AgentRequestEvent published (Collection Model):"
docker logs e2e-collection-model 2>&1 | grep -i "AgentRequest\|ai.agent.requested" | tail -3 || echo "  No events found"

echo -e "\nAgentRequestEvent received (AI Model):"
docker logs e2e-ai-model 2>&1 | grep -i "AgentRequest\|ai.agent.requested\|received event" | tail -3 || echo "  No events found"

echo -e "\nAgentCompletedEvent published (AI Model):"
docker logs e2e-ai-model 2>&1 | grep -i "AgentCompleted\|completed\|publishing" | tail -3 || echo "  No events found"

echo -e "\n━━━ 7. DIAGNOSIS ━━━"
# Auto-diagnosis based on findings
WEATHER_DOCS=$(docker exec e2e-mongodb mongosh --quiet --eval "db.getSiblingDB('collection_e2e').weather_documents.countDocuments()")
if [ "$WEATHER_DOCS" = "0" ]; then
    echo "⚠ LIKELY ISSUE: No weather documents created"
    echo "  → Check Collection Model pull job execution"
    echo "  → Verify iteration resolver returns regions"
    echo "  → Check plantation-mcp connectivity"
fi

echo -e "\n╔══════════════════════════════════════════════════════════════════════╗"
echo "║                     END DIAGNOSTIC REPORT                              ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
```

### 3. Checkpoint Helpers (`tests/e2e/helpers/checkpoints.py`)

```python
"""Checkpoint-based E2E test helpers.

Provides wait functions that fail at specific checkpoints with
diagnostic context, enabling AI agents to isolate failure points.
"""

import asyncio
import time
from typing import Any

from tests.e2e.helpers.diagnostics import run_diagnostics


class CheckpointFailure(Exception):
    """Raised when a checkpoint times out with diagnostic context."""

    def __init__(self, checkpoint: str, message: str, diagnostics: dict):
        self.checkpoint = checkpoint
        self.diagnostics = diagnostics
        super().__init__(f"CHECKPOINT {checkpoint} FAILED: {message}\nDiagnostics: {diagnostics}")


async def checkpoint_documents_created(
    mongodb_direct,
    collection: str,
    query: dict,
    checkpoint_name: str = "1-DOCUMENTS_CREATED",
    timeout: float = 15.0,
) -> list[dict]:
    """Checkpoint: Wait for documents to be created in MongoDB.

    This checkpoint verifies that the initial processing step
    (e.g., pull job, blob ingestion) created documents.

    Timeout is short (15s) because document creation should be fast.
    If this fails, the issue is in the ingestion layer, not AI processing.
    """
    start = time.time()
    while time.time() - start < timeout:
        docs = await mongodb_direct.find_documents(collection, query)
        if docs:
            return docs
        await asyncio.sleep(0.5)

    # Checkpoint failed - gather diagnostics
    diagnostics = await run_diagnostics(focus="collection_model")
    raise CheckpointFailure(
        checkpoint=checkpoint_name,
        message=f"No documents found in {collection} matching {query}",
        diagnostics=diagnostics,
    )


async def checkpoint_event_published(
    service_logs: str,
    event_pattern: str,
    checkpoint_name: str = "2-EVENT_PUBLISHED",
    timeout: float = 10.0,
) -> bool:
    """Checkpoint: Verify event was published by checking logs.

    This checkpoint verifies that the publishing service
    actually sent the event to DAPR.
    """
    # Implementation would grep service logs for event pattern
    pass


async def checkpoint_extraction_complete(
    mongodb_direct,
    collection: str,
    query: dict,
    checkpoint_name: str = "3-EXTRACTION_COMPLETE",
    timeout: float = 90.0,
) -> dict:
    """Checkpoint: Wait for AI extraction to complete.

    This checkpoint has a longer timeout (90s) because it involves
    LLM calls which can be slow.
    """
    start = time.time()
    while time.time() - start < timeout:
        docs = await mongodb_direct.find_documents(collection, query)
        for doc in docs:
            status = doc.get("extraction", {}).get("status")
            if status == "complete":
                return doc
            if status == "failed":
                diagnostics = await run_diagnostics(focus="ai_model")
                raise CheckpointFailure(
                    checkpoint=checkpoint_name,
                    message=f"Extraction failed: {doc.get('extraction', {}).get('error')}",
                    diagnostics=diagnostics,
                )
        await asyncio.sleep(1.0)

    # Timeout - gather diagnostics
    diagnostics = await run_diagnostics(focus="ai_model")
    last_status = "unknown"
    docs = await mongodb_direct.find_documents(collection, query)
    if docs:
        last_status = docs[0].get("extraction", {}).get("status", "no extraction field")

    raise CheckpointFailure(
        checkpoint=checkpoint_name,
        message=f"Extraction did not complete. Last status: {last_status}",
        diagnostics=diagnostics,
    )
```

### 4. Update E2E-TESTING-MENTAL-MODEL.md

Add comprehensive "Autonomous Debugging Protocol" section to the existing document:

```markdown
## Autonomous Debugging Protocol

This section documents tools and procedures for debugging E2E tests without human supervision.

### Available Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `scripts/e2e-up.sh --build` | Start E2E infrastructure with correct env vars | Always when starting E2E |
| `scripts/e2e-preflight.sh` | Validate infrastructure before tests | Before running tests |
| `scripts/e2e-diagnose.sh` | Generate diagnostic report | When tests fail |

### Environment Variable Handling

**How env vars flow to containers:**

```
LOCAL:  .env file → set -a && source .env → Shell → Docker Compose → Container
CI:     Secrets → env: block → Shell → Docker Compose → Container
```

**The correct pattern (local):**
```bash
# set -a = auto-export, source = load file, set +a = stop auto-export
set -a && source .env && set +a && docker compose -f ... up -d --build
```

**Verify env vars INSIDE container (not shell):**
```bash
# WRONG - checks shell
echo $OPENROUTER_API_KEY

# CORRECT - checks container
docker exec e2e-ai-model printenv OPENROUTER_API_KEY
```

### Stale Image Detection

**After modifying code, you MUST rebuild:**
```bash
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
```

**Check if images are stale:**
```bash
# When was image built?
docker inspect e2e-ai-model --format='{{.Created}}'

# Were files modified recently?
find services/*/src -name "*.py" -mmin -60

# If code modified AFTER image build → STALE! Rebuild with --build
```

### Debugging Protocol

1. **Run pre-flight check**
   ```bash
   bash scripts/e2e-preflight.sh
   ```
   If it fails, fix infrastructure FIRST.

2. **If tests fail, run diagnostics BEFORE changing code**
   ```bash
   bash scripts/e2e-diagnose.sh
   ```

3. **Check diagnostic output for:**
   - Stale images (code modified after build)
   - Missing env vars inside containers
   - Service health failures
   - MongoDB state (missing seed data)
   - Event flow issues

4. **Identify which checkpoint failed:**
   - `CHECKPOINT 1-DOCUMENTS_CREATED` → Collection Model issue
   - `CHECKPOINT 2-EVENT_PUBLISHED` → Event publishing issue
   - `CHECKPOINT 3-EXTRACTION_COMPLETE` → AI Model issue

5. **Fix at the correct layer** - Don't guess, use diagnostic evidence

6. **After fixing, rebuild and retest:**
   ```bash
   docker compose -f ... up -d --build
   pytest tests/e2e/scenarios/... -v
   ```

### Stuck Detection

If debugging > 30 minutes without progress:
1. Run `bash scripts/e2e-diagnose.sh`
2. Document what you've tried
3. Document diagnostic output
4. Ask user for guidance WITH diagnostic output attached

### Local Before CI (MANDATORY)

**All tests MUST pass locally before pushing to GitHub CI.**

```
WRONG workflow:
1. Make changes
2. Push to GitHub
3. Wait for CI
4. CI fails
5. Fix and push again
6. Wait for CI again
7. ... repeat ...

CORRECT workflow:
1. Make changes
2. Run tests locally: pytest tests/unit/ -v
3. Run E2E locally: bash scripts/e2e-up.sh --build && pytest tests/e2e/scenarios/ -v
4. Run lint locally: ruff check . && ruff format --check .
5. All pass? → Push to GitHub
6. CI should pass on first try
```

**Why this matters:**
- CI runs take 5-15 minutes - local runs take seconds to minutes
- Each CI failure wastes time waiting
- Local debugging is faster (you have logs, can add print statements)
- CI failures often have less context than local failures

**Local validation checklist before push:**
```bash
# 1. Unit tests
pytest tests/unit/ -v

# 2. Lint
ruff check . && ruff format --check .

# 3. E2E tests (if E2E-related changes)
bash scripts/e2e-up.sh --build
bash scripts/e2e-preflight.sh
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# 4. All green? Now push
git push
```

### Regression Ownership (CRITICAL)

**If a test was passing before your changes and is now failing, it is YOUR responsibility to fix it.**

```
WRONG agent behavior:
"test_foo is failing but it's not related to my changes. Story is done."

CORRECT agent behavior:
"test_foo was passing before my changes and is now failing.
This is a regression I caused. I must investigate and fix it before marking done."
```

**The Regression Rule:**
1. Tests don't fail randomly - if it passed before and fails now, YOUR changes broke it
2. "Not related to my changes" is almost never true - side effects are still your responsibility
3. A story is NOT done if any previously-passing test is now failing
4. You must investigate the connection, even if it's not obvious

**How to verify it was passing before:**
```bash
# Check if test passed in CI before your branch
gh run list --branch main --workflow ci.yaml --limit 5

# Compare with your branch
gh run list --branch feature/your-branch --workflow ci.yaml --limit 5
```

**Investigation steps when a "unrelated" test fails:**
1. What did the test verify before?
2. What shared code/config/data might connect your changes to this test?
3. Did you modify any shared fixtures, conftest.py, or seed data?
4. Did you change any imports, dependencies, or initialization order?
5. Run the failing test in isolation with verbose output
```

## Consequences

### Positive

- **Autonomous debugging** - Agents can identify root cause without human intervention
- **Faster resolution** - Diagnostic scripts provide answers in seconds
- **Checkpoint isolation** - Tests fail at specific points with context
- **No context pollution** - Tools are scripts, not instructions in CLAUDE.md
- **Reusable infrastructure** - Works for all E2E tests, not just weather

### Negative

- **Initial implementation effort** - Scripts and helpers need to be created
- **Maintenance overhead** - Scripts need updating as services change
- **Docker dependency** - Diagnostic scripts require Docker access

### Neutral

- **Requires Story 0.6.15** - Full observability requires logging migration first

## Dependencies

| Dependency | Reason |
|------------|--------|
| Story 0.6.15 (Logging Migration) | Diagnostic scripts grep logs - logs must contain useful information |
| Docker access | Scripts run `docker exec` and `docker logs` |
| MongoDB mongosh | Scripts query MongoDB directly |

## Revisit Triggers

Re-evaluate this decision if:

1. **AI agents consistently debug autonomously** - May reduce tooling needs
2. **New debugging patterns emerge** - May need additional diagnostics
3. **Test infrastructure changes** - Scripts need corresponding updates

## References

- Story 0.75.18: E2E Weather Extraction (blocked due to debugging issues)
- ADR-009: Logging Standards and Runtime Configuration
- `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`
