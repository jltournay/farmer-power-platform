# Story 0.6.16: E2E Autonomous Debugging Infrastructure

**Status:** done
**GitHub Issue:** #152
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADR:** [ADR-015: E2E Autonomous Debugging Infrastructure](../architecture/adr/ADR-015-e2e-autonomous-debugging-infrastructure.md)
**Depends On:** Story 0.6.15 (Service Logging Migration) - for meaningful log output
**Story Points:** 5

---

## Context

During Story 0.75.18 implementation, an AI agent spent 2+ days debugging an E2E test failure without identifying the root cause. The agent required human intervention to discover that:

1. The agent was debugging AI Model (symptom)
2. The actual blocker was in Collection Model (root cause: no documents created)

**Root causes identified:**
- No diagnostic tooling to query actual system state
- No checkpoint-based tests to isolate failure points
- No pre-flight validation to verify infrastructure
- Insufficient logging to observe event flow

**This story implements ADR-015: E2E Autonomous Debugging Infrastructure.**

---

## Story

As a **platform developer using AI agents**,
I want E2E debugging infrastructure with diagnostic scripts and checkpoint-based tests,
So that AI agents can debug E2E failures autonomously without human supervision.

---

## Acceptance Criteria

### AC0: E2E Launcher Script

**Given** I need to start E2E infrastructure with correct environment variables
**When** I execute `bash scripts/e2e-up.sh --build`
**Then** it:
- Loads and EXPORTS variables from `.env` (using `set -a`)
- Starts Docker Compose with the correct context
- Verifies environment variables are set INSIDE containers
- Provides clear feedback if OPENROUTER_API_KEY is missing

### AC1: Pre-Flight Script

**Given** I need to run E2E tests
**When** I execute `bash scripts/e2e-preflight.sh`
**Then** it validates:
- All required containers are running
- All service health endpoints respond 200
- MongoDB has expected seed data counts
- Required environment variables are set
- DAPR sidecars are connected
**And** exits with code 0 if all pass, code 1 if any fail

### AC2: Diagnostic Script

**Given** an E2E test has failed
**When** I execute `bash scripts/e2e-diagnose.sh`
**Then** it produces a structured report showing:
- **Image build dates** with stale image detection (code modified after build)
- Service health status (all endpoints)
- MongoDB collection counts and sample documents
- DAPR subscription status
- Recent errors from all service logs (last 5 per service)
- Event flow trace (AgentRequestEvent, AgentCompletedEvent)
- Auto-diagnosis with likely issue and suggested investigation

### AC3: Checkpoint Test Helpers

**Given** I'm writing an E2E test with multiple async steps
**When** I use checkpoint helpers from `tests/e2e/helpers/checkpoints.py`
**Then** each checkpoint:
- Has a specific name (e.g., `1-DOCUMENTS_CREATED`)
- Has an appropriate timeout (short for fast ops, long for LLM)
- Raises `CheckpointFailure` with diagnostic context on timeout
- Identifies which layer failed (Collection, AI Model, Plantation)

### AC4: Weather E2E Test Refactored

**Given** the existing `test_05_weather_ingestion.py` has a single 90s timeout
**When** I refactor it to use checkpoint helpers
**Then** it has distinct checkpoints:
- Checkpoint 1: Documents created (15s timeout)
- Checkpoint 2: AgentRequestEvent published (10s timeout)
- Checkpoint 3: Extraction complete (90s timeout)
**And** each checkpoint failure includes diagnostic context

### AC5: E2E Mental Model Documentation Updated

**Given** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md` exists
**When** I add the autonomous debugging protocol section
**Then** it includes:

**Tool Usage Documentation:**
- `scripts/e2e-up.sh` - When and how to use (always for starting E2E)
- `scripts/e2e-preflight.sh` - Run before tests to validate infrastructure
- `scripts/e2e-diagnose.sh` - Run when tests fail to identify root cause
- Checkpoint helpers - How to interpret checkpoint failure messages

**Environment Variable Handling:**
- Diagram showing Local vs CI env var flow
- The correct `set -a && source .env && set +a` pattern
- How to verify env vars inside containers (`docker exec ... printenv`)

**Stale Image Detection:**
- How to check image build dates vs code modification times
- When to use `--build` flag (always after code changes)

**Debugging Protocol:**
1. Run pre-flight check
2. If tests fail, run diagnostics FIRST (before changing code)
3. Check for stale images
4. Check for missing env vars inside containers
5. Identify which checkpoint failed
6. Fix at the correct layer

**Stuck Detection:**
- If debugging > 30 minutes without progress, run full diagnostics
- Document findings and ask for help with diagnostic output attached

**Regression Ownership (CRITICAL):**
- Document that if a test was passing before and fails after changes, it's the agent's responsibility
- Include investigation steps for "unrelated" test failures
- How to verify test was passing before (compare CI runs)

### AC6: Regression Ownership Documentation

**Given** an agent makes changes and a previously-passing test now fails
**When** the agent says "this test failure is not related to my changes"
**Then** the E2E Mental Model documents that this is WRONG behavior
**And** explains that:
- Tests don't fail randomly
- Side effects are still the agent's responsibility
- Story is NOT done if any previously-passing test is failing
- Agent must investigate the connection, even if not obvious

**Investigation checklist to document:**
1. What did the test verify?
2. What shared code/config/data might connect to this test?
3. Did you modify shared fixtures, conftest.py, or seed data?
4. Did you change imports, dependencies, or initialization order?
5. How to verify test was passing before (compare main vs branch CI runs)

### AC7: Local Before CI Documentation

**Given** an agent is ready to push changes to GitHub
**When** the E2E Mental Model is consulted
**Then** it documents that all tests MUST pass locally before pushing
**And** includes:
- The wrong workflow (push → wait → fail → repeat)
- The correct workflow (local tests → all green → push)
- Why local-first matters (faster feedback, easier debugging)
- Local validation checklist (unit tests, lint, E2E)

---

## Tasks / Subtasks

- [x] **Task 0: Create E2E Launcher Script** (AC: #0)
  - [x] Create `scripts/e2e-up.sh`
  - [x] Implement `set -a && source .env && set +a` pattern
  - [x] Add `--build` flag support
  - [x] Add container environment variable verification
  - [x] Provide clear error messages for missing keys
  - [x] Make script executable: `chmod +x scripts/e2e-up.sh`

- [x] **Task 1: Create Pre-Flight Script** (AC: #1)
  - [x] Create `scripts/e2e-preflight.sh`
  - [x] Implement container running checks
  - [x] Implement health endpoint checks
  - [x] Implement MongoDB seed data count checks
  - [x] Implement environment variable checks
  - [x] Implement DAPR sidecar checks
  - [x] Add clear pass/fail output with exit codes
  - [x] Make script executable: `chmod +x scripts/e2e-preflight.sh`

- [x] **Task 2: Create Diagnostic Script** (AC: #2)
  - [x] Create `scripts/e2e-diagnose.sh`
  - [x] Implement **image build date check** with stale detection
  - [x] Compare image creation time vs recent code modifications
  - [x] Warn if code modified after image was built
  - [x] Implement service health section
  - [x] Implement MongoDB state section with counts
  - [x] Implement recent documents section
  - [x] Implement DAPR subscriptions section
  - [x] Implement recent errors section (grep logs)
  - [x] Implement event flow trace section
  - [x] Add auto-diagnosis logic based on findings
  - [x] Make script executable: `chmod +x scripts/e2e-diagnose.sh`

- [x] **Task 3: Create Checkpoint Helpers** (AC: #3)
  - [x] Create `tests/e2e/helpers/checkpoints.py`
  - [x] Implement `CheckpointFailure` exception class
  - [x] Implement `checkpoint_documents_created()` helper
  - [x] Implement `checkpoint_event_published()` helper
  - [x] Implement `checkpoint_extraction_complete()` helper
  - [x] Implement `run_diagnostics(focus: str)` function (in checkpoints.py)

- [x] **Task 4: Refactor Weather E2E Test** (AC: #4)
  - [x] Import checkpoint helpers in `test_05_weather_ingestion.py`
  - [x] Added new `TestWeatherIngestionWithCheckpoints` class
  - [x] Implemented `test_end_to_end_weather_flow_with_checkpoints` test
  - [x] Kept existing tests for backward compatibility
  - [x] Verify failure messages include diagnostic context

- [x] **Task 5: Update Mental Model Documentation** (AC: #5, #6, #7)
  - [x] Add "E2E Debugging Infrastructure (Story 0.6.16)" section
  - [x] Document all scripts: `e2e-up.sh`, `e2e-preflight.sh`, `e2e-diagnose.sh`
  - [x] Document checkpoint-based testing pattern with examples
  - [x] Document checkpoint failure output format
  - [x] Document available checkpoints table
  - [x] **Added "E2E Workflow: Local Before CI" section (MANDATORY)**
  - [x] Document correct workflow (local → green → push)
  - [x] Added local vs CI detection time comparison table
  - [x] **Added "Regression Ownership" section (CRITICAL)**
  - [x] Document investigation order
  - [x] Document common regressions table
  - [x] Updated summary with diagnostic tools and local-first guidelines

- [x] **Task 6: Verification** (AC: All)
  - [x] Run lint: `ruff check . && ruff format --check .`
  - [x] Run pre-flight script: `bash scripts/e2e-preflight.sh` (validated infrastructure detection)
  - [x] Start E2E infrastructure: `bash scripts/e2e-up.sh --build` (validated)
  - [x] Run diagnostics: `bash scripts/e2e-diagnose.sh` (fixed bash 3.2 compat, validated)
  - [x] Run weather E2E tests with new checkpoints: PASSED
  - [x] Stop infrastructure: `bash scripts/e2e-up.sh --down` (validated)
  - [x] E2E CI verification (Step 9c) - PASSED (run 20881002755)

---

## Unit Tests Required

### Scripts (Manual Testing)

Scripts are validated manually by running them against E2E infrastructure.

### Checkpoint Helpers

```python
# tests/unit/e2e_helpers/test_checkpoints.py
class TestCheckpointHelpers:
    async def test_checkpoint_documents_created_returns_docs_on_success(self):
        """Given documents exist, checkpoint returns them."""
        pass

    async def test_checkpoint_documents_created_raises_on_timeout(self):
        """Given no documents, checkpoint raises CheckpointFailure."""
        pass

    async def test_checkpoint_failure_includes_diagnostics(self):
        """CheckpointFailure exception includes diagnostic dict."""
        pass

    async def test_checkpoint_extraction_complete_detects_failed_status(self):
        """Given extraction.status='failed', raises immediately."""
        pass
```

---

## E2E Test Impact

### Expected Behavior

- Pre-flight script catches infrastructure issues before test runs
- Diagnostic script provides actionable information on failures
- Checkpoint-based tests fail at specific points with context
- AI agents can identify root cause without human intervention

### Verification

```bash
# Pre-flight check
bash scripts/e2e-preflight.sh

# Start infrastructure
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Run diagnostics
bash scripts/e2e-diagnose.sh

# Run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_05_weather_ingestion.py -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

---

## Implementation Notes

### Pre-Flight Script Structure

```bash
#!/bin/bash
# scripts/e2e-preflight.sh
set -e

echo "=== E2E PRE-FLIGHT CHECK ==="
FAILED=0

# Check containers
# Check health endpoints
# Check MongoDB seed data
# Check environment variables
# Check DAPR sidecars

if [ $FAILED -eq 0 ]; then
    echo "✓ All checks passed"
    exit 0
else
    echo "❌ Pre-flight failed"
    exit 1
fi
```

### Checkpoint Failure Example

```python
# When a checkpoint times out, the agent sees:
CheckpointFailure: CHECKPOINT 1-DOCUMENTS_CREATED FAILED: No documents found in weather_documents
Diagnostics: {
    "collection_model_health": "healthy",
    "weather_documents_count": 0,
    "source_configs_count": 5,
    "recent_errors": ["No errors in last 5 minutes"],
    "likely_issue": "Pull job not creating documents",
    "suggested_check": "Verify iteration resolver returns regions"
}
```

### Script Locations

| Script | Purpose |
|--------|---------|
| `scripts/e2e-up.sh` | Start E2E infrastructure with correct env vars |
| `scripts/e2e-test.sh` | Run E2E tests (handles .env loading transparently) |
| `scripts/e2e-preflight.sh` | Pre-test infrastructure validation |
| `scripts/e2e-diagnose.sh` | Post-failure diagnostic report |

### Helper Locations

| File | Purpose |
|------|---------|
| `tests/e2e/helpers/checkpoints.py` | Checkpoint wait functions |
| `tests/e2e/helpers/diagnostics.py` | Programmatic diagnostics |

---

## Definition of Done

- [x] E2E launcher script (`e2e-up.sh`) created and executable
- [x] Pre-flight script created and executable
- [x] Diagnostic script created and executable (with stale image detection)
- [x] Checkpoint helpers created with proper exception handling
- [x] Weather E2E test refactored with checkpoints
- [x] E2E-TESTING-MENTAL-MODEL.md updated with:
  - [x] Tool usage documentation
  - [x] Environment variable handling
  - [x] Stale image detection
  - [x] Debugging protocol
  - [x] **Local before CI rules**
  - [x] **Regression ownership rules**
- [x] All E2E tests pass (verified locally with checkpoint test)
- [x] Lint passes
- [x] CI workflow passes (run 20880434931)

---

## References

- [ADR-015: E2E Autonomous Debugging Infrastructure](../architecture/adr/ADR-015-e2e-autonomous-debugging-infrastructure.md)
- [Story 0.6.15: Service Logging Migration](./0-6-15-service-logging-migration.md) (dependency)
- [Story 0.75.18: E2E Weather Extraction](./0-75-18-e2e-weather-observation-extraction-flow.md) (blocked by debugging issues)
- [E2E Testing Mental Model](../../tests/e2e/E2E-TESTING-MENTAL-MODEL.md)
