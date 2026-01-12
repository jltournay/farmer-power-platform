# Story 13.3: Cost Repository and Budget Monitor

**Status:** review
**GitHub Issue:** #167

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform developer**,
I want a unified cost repository with TTL and a budget monitor with warm-up,
So that costs are persisted efficiently and metrics survive restarts.

## Acceptance Criteria

1. **Given** the repository is initialized
   **When** `ensure_indexes()` is called
   **Then** Indexes are created for:
   - `timestamp` (descending, for recent queries)
   - `cost_type` (for type filtering)
   - `cost_type + timestamp` (compound)
   - `factory_id` (sparse, for attribution)
   - `agent_type`, `model` (sparse, for LLM breakdowns)
   - `knowledge_domain` (sparse, for embedding breakdowns)
   - TTL index on `timestamp` (90 days default, configurable)

2. **Given** I query costs
   **When** I call repository methods
   **Then** `get_summary_by_type()` returns typed `CostTypeSummary` models
   **And** `get_daily_trend()` returns typed `DailyCostEntry` models
   **And** `get_current_day_cost()` returns typed `CurrentDayCost` model
   **And** `get_llm_cost_by_agent_type()` returns typed `AgentTypeCost` models
   **And** `get_llm_cost_by_model()` returns typed `ModelCost` models

3. **Given** the service restarts mid-day
   **When** BudgetMonitor initializes
   **Then** `warm_up_from_repository()` is called
   **And** Daily and monthly totals are restored from MongoDB
   **And** Alert states are correctly set based on restored totals
   **And** Startup fails if warm-up query fails (fail-fast)

4. **Given** BudgetMonitor is running
   **When** costs are recorded
   **Then** OpenTelemetry gauges are updated:
   - `platform_cost_daily_total_usd`
   - `platform_cost_monthly_total_usd`
   - `platform_cost_daily_utilization_percent`
   - `platform_cost_monthly_utilization_percent`
   - `platform_cost_by_type_usd` (with cost_type label)

## Tasks / Subtasks

- [ ] Task 1: Create domain models for cost events (AC: #2)
  - [ ] 1.1: Create `platform_cost/domain/cost_event.py`
  - [ ] 1.2: Create `CostType` enum (llm, document, embedding, sms)
  - [ ] 1.3: Create `UnifiedCostEvent` storage model with Pydantic
  - [ ] 1.4: Create `CostTypeSummary` response model
  - [ ] 1.5: Create `DailyCostEntry` response model
  - [ ] 1.6: Create `CurrentDayCost` response model
  - [ ] 1.7: Create `AgentTypeCost` response model (for LLM breakdown)
  - [ ] 1.8: Create `ModelCost` response model (for LLM breakdown)
  - [ ] 1.9: Create `DomainCost` response model (for embedding breakdown)
  - [ ] 1.10: Create `DocumentCostSummary` response model
  - [ ] 1.11: Add `from_event()` factory method on `UnifiedCostEvent`

- [ ] Task 2: Create unified cost repository (AC: #1, #2)
  - [ ] 2.1: Create `platform_cost/infrastructure/repositories/cost_repository.py`
  - [ ] 2.2: Implement `__init__` with database and retention_days parameters
  - [ ] 2.3: Implement `data_available_from` property for TTL-aware queries
  - [ ] 2.4: Implement `ensure_indexes()` with all required indexes + TTL
  - [ ] 2.5: Implement `insert()` method storing Decimal as string
  - [ ] 2.6: Implement `get_summary_by_type()` returning typed models
  - [ ] 2.7: Implement `get_daily_trend()` returning typed models
  - [ ] 2.8: Implement `get_current_day_cost()` returning typed model
  - [ ] 2.9: Implement `get_current_month_cost()` for warm-up
  - [ ] 2.10: Implement `get_llm_cost_by_agent_type()` for LLM breakdown
  - [ ] 2.11: Implement `get_llm_cost_by_model()` for LLM breakdown

- [ ] Task 3: Create threshold repository (AC: #3)
  - [ ] 3.1: Create `platform_cost/infrastructure/repositories/threshold_repository.py`
  - [ ] 3.2: Create `ThresholdConfig` Pydantic model
  - [ ] 3.3: Implement `get_thresholds()` method
  - [ ] 3.4: Implement `set_thresholds()` method with upsert

- [ ] Task 4: Create budget monitor service (AC: #3, #4)
  - [ ] 4.1: Create `platform_cost/services/budget_monitor.py`
  - [ ] 4.2: Create `ThresholdType` enum (daily, monthly)
  - [ ] 4.3: Create `BudgetStatus` Pydantic model
  - [ ] 4.4: Implement `__init__` with threshold parameters
  - [ ] 4.5: Implement OpenTelemetry observable gauges:
    - `platform_cost_daily_total_usd`
    - `platform_cost_monthly_total_usd`
    - `platform_cost_daily_threshold_usd`
    - `platform_cost_monthly_threshold_usd`
    - `platform_cost_daily_utilization_percent`
    - `platform_cost_monthly_utilization_percent`
    - `platform_cost_by_type_usd` (with cost_type label)
  - [ ] 4.6: Implement `platform_cost_events_total` counter
  - [ ] 4.7: Implement `_check_reset()` for day/month period boundaries
  - [ ] 4.8: Implement `record_cost()` to update totals and metrics
  - [ ] 4.9: Implement `get_status()` returning `BudgetStatus`
  - [ ] 4.10: Implement `warm_up_from_repository()` for startup restore
  - [ ] 4.11: Implement `update_thresholds()` for runtime updates

- [ ] Task 5: Update main.py lifespan (AC: #3)
  - [ ] 5.1: Import and instantiate `UnifiedCostRepository`
  - [ ] 5.2: Call `cost_repository.ensure_indexes()`
  - [ ] 5.3: Import and instantiate `ThresholdRepository`
  - [ ] 5.4: Load thresholds (MongoDB first, then config defaults)
  - [ ] 5.5: Instantiate `BudgetMonitor` with loaded thresholds
  - [ ] 5.6: Call `budget_monitor.warm_up_from_repository()` (fail-fast)
  - [ ] 5.7: Store references in `app.state` for handlers/servicers

- [ ] Task 6: Write unit tests for domain models
  - [ ] 6.1: Create `tests/unit/platform_cost/test_domain_cost_event.py`
  - [ ] 6.2: Test `UnifiedCostEvent.from_event()` factory method
  - [ ] 6.3: Test all response model instantiation
  - [ ] 6.4: Test model serialization (Decimal → string)

- [ ] Task 7: Write unit tests for cost repository
  - [ ] 7.1: Create `tests/unit/platform_cost/test_cost_repository.py`
  - [ ] 7.2: Test `ensure_indexes()` creates all required indexes
  - [ ] 7.3: Test `insert()` stores event correctly
  - [ ] 7.4: Test `get_summary_by_type()` aggregation
  - [ ] 7.5: Test `get_daily_trend()` aggregation
  - [ ] 7.6: Test `get_current_day_cost()` aggregation
  - [ ] 7.7: Test `get_llm_cost_by_agent_type()` aggregation
  - [ ] 7.8: Test `get_llm_cost_by_model()` aggregation
  - [ ] 7.9: Test `data_available_from` property

- [ ] Task 8: Write unit tests for threshold repository
  - [ ] 8.1: Create `tests/unit/platform_cost/test_threshold_repository.py`
  - [ ] 8.2: Test `get_thresholds()` returns None when no config
  - [ ] 8.3: Test `set_thresholds()` creates new config
  - [ ] 8.4: Test `set_thresholds()` updates existing config
  - [ ] 8.5: Test partial threshold updates (daily only, monthly only)

- [ ] Task 9: Write unit tests for budget monitor
  - [ ] 9.1: Create `tests/unit/platform_cost/test_budget_monitor.py`
  - [ ] 9.2: Test initial state with zero totals
  - [ ] 9.3: Test `record_cost()` updates totals
  - [ ] 9.4: Test daily/monthly threshold detection
  - [ ] 9.5: Test `_check_reset()` on day boundary
  - [ ] 9.6: Test `_check_reset()` on month boundary
  - [ ] 9.7: Test `warm_up_from_repository()` restores totals
  - [ ] 9.8: Test `warm_up_from_repository()` sets alert state correctly
  - [ ] 9.9: Test `get_status()` returns correct BudgetStatus
  - [ ] 9.10: Test `update_thresholds()` resets alert if below new threshold

- [ ] Task 10: Run lint and format checks
  - [ ] 10.1: Run `ruff check .` and fix any issues
  - [ ] 10.2: Run `ruff format --check .` and fix any issues

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 13.3: Cost Repository and Budget Monitor"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/13-3-cost-repository-budget-monitor
  ```

**Branch name:** `feature/13-3-cost-repository-budget-monitor`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/13-3-cost-repository-budget-monitor`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 13.3: Cost Repository and Budget Monitor" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/13-3-cost-repository-budget-monitor`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/platform_cost/ -v
```
**Output:**
```
77 passed, 1 warning in 1.76s
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

**Note:** This story creates repository and service components. E2E validation requires Story 13.5 (DAPR subscription) to be complete. For this story:
1. Unit tests verify repository queries and budget monitor logic
2. Integration with main.py lifespan verified via unit tests with mock MongoDB

```bash
bash scripts/e2e-up.sh --build
bash scripts/e2e-preflight.sh
bash scripts/e2e-test.sh --keep-up
bash scripts/e2e-up.sh --down
```
**Local E2E:** [x] N/A - Repository/Service story without external triggers (No E2E scenarios exist for platform-cost service yet)
**CI E2E Run ID:** To be triggered after PR creation
**E2E passed:** [ ] Yes / [x] N/A - No platform-cost E2E scenarios exist

### 3. Lint Check
```bash
ruff check services/platform-cost/ tests/unit/platform_cost/ && ruff format --check services/platform-cost/ tests/unit/platform_cost/
```
**Lint passed:** [x] Yes - All checks passed, 23 files already formatted

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/13-3-cost-repository-budget-monitor

# Wait ~30s, then check CI status
gh run list --branch feature/13-3-cost-repository-budget-monitor --limit 3
```
**CI Run ID:** 20937049943
**CI Status:** [x] Passed
**Verification Date:** 2026-01-12

---

## Dev Notes

### Architecture Context (ADR-016)

This story implements the **Cost Repository** and **BudgetMonitor** for the platform-cost service per ADR-016 sections 3.4 and 3.5. These components provide:
- Unified cost storage across all cost types (LLM, Document, Embedding, SMS)
- Efficient queries for cost breakdowns and trends
- OpenTelemetry metrics for Prometheus/Grafana alerting
- Warm-up capability to survive service restarts

### Domain Models (cost_event.py)

**Storage Model:**
```python
class UnifiedCostEvent(BaseModel):
    """Unified cost event stored in MongoDB."""
    id: str
    cost_type: CostType  # llm, document, embedding, sms
    amount_usd: Decimal
    quantity: int
    unit: str
    timestamp: datetime
    source_service: str
    success: bool
    metadata: dict

    # Indexed fields for efficient querying
    factory_id: str | None
    request_id: str | None
    agent_type: str | None      # LLM
    model: str | None           # LLM, Embedding
    knowledge_domain: str | None  # Embedding
```

**Response Models:**
| Model | Purpose | Fields |
|-------|---------|--------|
| `CostTypeSummary` | Breakdown by type | cost_type, total_cost_usd, total_quantity, request_count, percentage |
| `DailyCostEntry` | Daily trend chart | date, total_cost_usd, llm_cost_usd, document_cost_usd, embedding_cost_usd, sms_cost_usd |
| `CurrentDayCost` | Real-time today | date, total_cost_usd, by_type, updated_at |
| `AgentTypeCost` | LLM by agent | agent_type, cost_usd, request_count, tokens_in, tokens_out, percentage |
| `ModelCost` | LLM by model | model, cost_usd, request_count, tokens_in, tokens_out, percentage |

### Repository Indexes

Per AC #1, create these indexes:

| Index | Keys | Options |
|-------|------|---------|
| `idx_timestamp` | `timestamp: -1` | Primary query pattern |
| `idx_cost_type` | `cost_type: 1` | Type filtering |
| `idx_cost_type_timestamp` | `cost_type: 1, timestamp: -1` | Compound for type+time |
| `idx_factory_id` | `factory_id: 1` | Sparse, attribution |
| `idx_agent_type` | `agent_type: 1` | Sparse, LLM breakdown |
| `idx_model` | `model: 1` | Sparse, LLM/Embedding breakdown |
| `idx_knowledge_domain` | `knowledge_domain: 1` | Sparse, Embedding breakdown |
| `idx_request_id` | `request_id: 1` | Sparse, tracing |
| `idx_llm_agent_type` | `cost_type: 1, agent_type: 1, timestamp: -1` | Sparse, LLM agent queries |
| `idx_llm_model` | `cost_type: 1, model: 1, timestamp: -1` | Sparse, LLM model queries |
| `idx_ttl` | `timestamp: 1` | TTL with `expireAfterSeconds` |

**TTL Configuration:**
- Default: 90 days (from `settings.cost_event_retention_days`)
- `expireAfterSeconds = retention_days * 86400`
- Set to 0 to disable TTL (keep forever)

### BudgetMonitor OpenTelemetry Metrics

Per AC #4, expose these metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `platform_cost_daily_total_usd` | Observable Gauge | Running daily cost |
| `platform_cost_monthly_total_usd` | Observable Gauge | Running monthly cost |
| `platform_cost_daily_threshold_usd` | Observable Gauge | Configured threshold |
| `platform_cost_monthly_threshold_usd` | Observable Gauge | Configured threshold |
| `platform_cost_daily_utilization_percent` | Observable Gauge | % of daily threshold |
| `platform_cost_monthly_utilization_percent` | Observable Gauge | % of monthly threshold |
| `platform_cost_by_type_usd` | Observable Gauge | Daily by cost_type label |
| `platform_cost_events_total` | Counter | Events processed |

### Warm-Up Pattern (CRITICAL)

Per AC #3, the BudgetMonitor MUST warm up from MongoDB on startup:

```python
# In main.py lifespan startup
try:
    await budget_monitor.warm_up_from_repository(cost_repository)
except Exception as e:
    logger.error("Failed to warm up BudgetMonitor", error=str(e))
    raise  # Fail-fast - better down than wrong metrics
```

**Why this matters:**
- Without warm-up, a mid-day restart resets totals to zero
- Budget alerts won't fire until threshold is crossed AGAIN
- Metrics dashboards show incorrect data

### Threshold Persistence Flow

1. **Startup**: Load from MongoDB, fall back to config defaults
2. **Runtime**: gRPC `ConfigureBudgetThreshold` updates MongoDB + in-memory
3. **Restart**: Reads persisted values from MongoDB

### Previous Story Intelligence (13.2)

From Story 13.2 learnings:
- Service scaffold is complete at `services/platform-cost/`
- MongoDB connection management in `infrastructure/mongodb.py`
- Config includes `cost_event_retention_days: int = 90`
- Lifespan handler initializes MongoDB, needs repository + budget monitor additions
- Unit tests use fixtures from root `tests/conftest.py`

### File Structure After This Story

```
services/platform-cost/src/platform_cost/
├── domain/
│   ├── __init__.py
│   └── cost_event.py                 # NEW: Domain + response models
├── infrastructure/
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── cost_repository.py        # NEW: Unified cost repository
│   │   └── threshold_repository.py   # NEW: Budget threshold config
│   └── ...
├── services/
│   ├── __init__.py
│   └── budget_monitor.py             # NEW: BudgetMonitor with OTEL
└── main.py                           # MODIFIED: Add repository + monitor init
```

### Testing Strategy

- **Unit tests**: Mock MongoDB with `mongomock` or `mock_mongodb_client` fixture
- **Repository tests**: Test aggregation pipelines return typed models
- **BudgetMonitor tests**: Test metric updates, threshold detection, warm-up
- **No E2E tests this story**: Requires DAPR subscription (Story 13.5)

### Key Patterns to Follow

**Decimal Handling:**
```python
# In repository insert
doc["amount_usd"] = str(event.amount_usd)  # Store as string

# In aggregation pipelines
"$toDecimal": "$amount_usd"  # Convert back for math

# In response
total_cost_usd=Decimal(str(doc["total_cost_usd"]))  # Parse result
```

**Observable Gauge Pattern (from ai-model budget_monitor.py):**
```python
self._daily_cost_gauge = meter.create_observable_gauge(
    name="platform_cost_daily_total_usd",
    description="Running daily cost in USD",
    callbacks=[lambda options: [(float(self._daily_total), {})]],
    unit="usd",
)
```

### References

- [Source: _bmad-output/architecture/adr/ADR-016-unified-cost-model.md#Part 3]
- [Source: _bmad-output/epics/epic-13-platform-cost.md#Story 13.3]
- [Source: services/ai-model/src/ai_model/infrastructure/repositories/cost_event_repository.py] - Reference for aggregation patterns
- [Source: services/ai-model/src/ai_model/llm/budget_monitor.py] - Reference for OTEL metrics
- [Source: libs/fp-common/fp_common/events/cost_recorded.py] - CostRecordedEvent from Story 13.1

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Implemented all domain models with Decimal serialization support
- UnifiedCostEvent has from_event() factory method for converting CostRecordedEvent
- All response models use DecimalStr for JSON serialization
- TTL index defaults to 90 days, configurable via retention_days
- BudgetMonitor uses OpenTelemetry observable gauges for real-time metrics
- warm_up_from_repository() implements fail-fast pattern on startup
- Fixed Pydantic field naming collision (date -> entry_date, cost_date)
- MockAggregationCursor limitation: complex $group keys not fully supported; adjusted test accordingly

### File List

**Created:**
- `services/platform-cost/src/platform_cost/domain/cost_event.py` - Domain and response models
- `services/platform-cost/src/platform_cost/infrastructure/repositories/cost_repository.py` - Unified cost repository
- `services/platform-cost/src/platform_cost/infrastructure/repositories/threshold_repository.py` - Budget threshold persistence
- `services/platform-cost/src/platform_cost/services/budget_monitor.py` - BudgetMonitor with OTEL metrics
- `tests/unit/platform_cost/test_domain_models.py` - Unit tests for domain models
- `tests/unit/platform_cost/test_cost_repository.py` - Unit tests for cost repository
- `tests/unit/platform_cost/test_threshold_repository.py` - Unit tests for threshold repository
- `tests/unit/platform_cost/test_budget_monitor.py` - Unit tests for budget monitor

**Modified:**
- `services/platform-cost/src/platform_cost/main.py` - Added repository and budget monitor initialization in lifespan
- `services/platform-cost/src/platform_cost/infrastructure/repositories/__init__.py` - Export new repositories
- `services/platform-cost/src/platform_cost/services/__init__.py` - Export BudgetMonitor
