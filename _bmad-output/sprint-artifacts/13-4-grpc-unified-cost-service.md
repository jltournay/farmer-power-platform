# Story 13.4: gRPC UnifiedCostService

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform developer**,
I want a gRPC UnifiedCostService exposing all cost query and budget APIs,
So that the Platform Admin UI can consume cost data.

## Acceptance Criteria

1. **Given** the proto is defined
   **When** I generate Python code
   **Then** `proto/platform_cost/v1/platform_cost.proto` defines:
   - `GetCostSummary` - total costs with type breakdown
   - `GetDailyCostTrend` - daily costs for stacked chart (includes `data_available_from`)
   - `GetCurrentDayCost` - real-time today's cost
   - `GetLlmCostByAgentType` - LLM breakdown by agent
   - `GetLlmCostByModel` - LLM breakdown by model
   - `GetDocumentCostSummary` - document processing costs
   - `GetEmbeddingCostByDomain` - embedding costs by knowledge domain
   - `GetBudgetStatus` - current thresholds and utilization
   - `ConfigureBudgetThreshold` - update thresholds (persisted to MongoDB)

2. **Given** I call `GetDailyCostTrend`
   **When** the response is returned
   **Then** `data_available_from` field indicates earliest available date
   **And** Requests for dates before TTL cutoff return empty entries (not errors)

3. **Given** I call `ConfigureBudgetThreshold`
   **When** thresholds are updated
   **Then** New values are persisted to MongoDB `budget_config` collection
   **And** BudgetMonitor in-memory state is updated immediately
   **And** Next restart loads persisted values

## Tasks / Subtasks

- [ ] Task 1: Create proto definition (AC: #1)
  - [ ] 1.1: Create `proto/platform_cost/v1/` directory structure
  - [ ] 1.2: Create `platform_cost.proto` with service definition
  - [ ] 1.3: Define all 9 RPC methods per ADR-016
  - [ ] 1.4: Define all request/response messages
  - [ ] 1.5: Run `bash scripts/proto-gen.sh` to generate Python stubs
  - [ ] 1.6: Verify stubs appear in `libs/fp-proto/src/farmer_power/platform_cost/v1/`

- [ ] Task 2: Create gRPC server setup (AC: #1)
  - [ ] 2.1: Create `platform_cost/api/grpc_server.py`
  - [ ] 2.2: Implement `serve()` function with gRPC server initialization
  - [ ] 2.3: Configure reflection for service discovery
  - [ ] 2.4: Add graceful shutdown handling
  - [ ] 2.5: Register UnifiedCostService servicer

- [ ] Task 3: Implement UnifiedCostService servicer (AC: #1, #2, #3)
  - [ ] 3.1: Create `platform_cost/api/unified_cost_service.py`
  - [ ] 3.2: Implement `GetCostSummary()` - calls `cost_repository.get_summary_by_type()`
  - [ ] 3.3: Implement `GetDailyCostTrend()` - calls `cost_repository.get_daily_trend()` with `data_available_from`
  - [ ] 3.4: Implement `GetCurrentDayCost()` - calls `cost_repository.get_current_day_cost()`
  - [ ] 3.5: Implement `GetLlmCostByAgentType()` - calls `cost_repository.get_llm_cost_by_agent_type()`
  - [ ] 3.6: Implement `GetLlmCostByModel()` - calls `cost_repository.get_llm_cost_by_model()`
  - [ ] 3.7: Implement `GetDocumentCostSummary()` - calls `cost_repository.get_document_cost_summary()`
  - [ ] 3.8: Implement `GetEmbeddingCostByDomain()` - calls `cost_repository.get_embedding_cost_by_domain()`
  - [ ] 3.9: Implement `GetBudgetStatus()` - calls `budget_monitor.get_status()`
  - [ ] 3.10: Implement `ConfigureBudgetThreshold()` - updates both MongoDB and in-memory

- [ ] Task 4: Add missing repository methods (AC: #1, #2)
  - [ ] 4.1: Implement `get_document_cost_summary()` in cost_repository.py (deferred from Story 13.3)
  - [ ] 4.2: Implement `get_embedding_cost_by_domain()` in cost_repository.py (deferred from Story 13.3)

- [ ] Task 5: Update main.py for gRPC server (AC: #1, #3)
  - [ ] 5.1: Add gRPC server initialization in lifespan startup
  - [ ] 5.2: Pass cost_repository and budget_monitor to servicer
  - [ ] 5.3: Pass threshold_repository to servicer for persistence
  - [ ] 5.4: Start gRPC server on port 50051
  - [ ] 5.5: Add graceful shutdown in lifespan cleanup

- [ ] Task 6: Write unit tests for proto conversions
  - [ ] 6.1: Create `tests/unit/platform_cost/test_unified_cost_service.py`
  - [ ] 6.2: Test proto message serialization (Decimal → string)
  - [ ] 6.3: Test all RPC method implementations with mock repository
  - [ ] 6.4: Test ConfigureBudgetThreshold persists and updates in-memory

- [ ] Task 7: Write unit tests for new repository methods
  - [ ] 7.1: Add tests for `get_document_cost_summary()` aggregation
  - [ ] 7.2: Add tests for `get_embedding_cost_by_domain()` aggregation

- [ ] Task 8: Run lint and format checks
  - [ ] 8.1: Run `ruff check .` and fix any issues
  - [ ] 8.2: Run `ruff format --check .` and fix any issues

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 13.4: gRPC UnifiedCostService"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/13-4-grpc-unified-cost-service
  ```

**Branch name:** `feature/13-4-grpc-unified-cost-service`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/13-4-grpc-unified-cost-service`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 13.4: gRPC UnifiedCostService" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/13-4-grpc-unified-cost-service`

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
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
bash scripts/e2e-up.sh --build
bash scripts/e2e-preflight.sh
bash scripts/e2e-test.sh --keep-up
bash scripts/e2e-up.sh --down
```
**Output:**
```
(paste E2E test output here - story is NOT ready for review without this)
```
**E2E passed:** [ ] Yes / [ ] No / [ ] N/A (no platform-cost E2E scenarios yet)

### 3. Lint Check
```bash
ruff check services/platform-cost/ tests/unit/platform_cost/ proto/ && ruff format --check services/platform-cost/ tests/unit/platform_cost/
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/13-4-grpc-unified-cost-service

# Wait ~30s, then check CI status
gh run list --branch feature/13-4-grpc-unified-cost-service --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed / [ ] N/A
**Verification Date:** _______________

---

## Dev Notes

### Architecture Context (ADR-016)

This story implements the **gRPC UnifiedCostService** for the platform-cost service per ADR-016 section 3.2. The service exposes all cost query and budget management APIs to consumers (primarily BFF for Platform Admin UI).

### Proto Definition Structure

Per ADR-016 section 3.2, create `proto/platform_cost/v1/platform_cost.proto`:

```protobuf
syntax = "proto3";

package farmer_power.platform_cost.v1;

option python_package = "farmer_power.platform_cost.v1";

// UnifiedCostService provides cost aggregation and reporting
service UnifiedCostService {
  rpc GetCostSummary(CostSummaryRequest) returns (CostSummaryResponse);
  rpc GetDailyCostTrend(DailyTrendRequest) returns (DailyTrendResponse);
  rpc GetCurrentDayCost(CurrentDayCostRequest) returns (CurrentDayCostResponse);
  rpc GetLlmCostByAgentType(LlmCostByAgentTypeRequest) returns (LlmCostByAgentTypeResponse);
  rpc GetLlmCostByModel(LlmCostByModelRequest) returns (LlmCostByModelResponse);
  rpc GetDocumentCostSummary(DocumentCostRequest) returns (DocumentCostResponse);
  rpc GetEmbeddingCostByDomain(EmbeddingCostByDomainRequest) returns (EmbeddingCostByDomainResponse);
  rpc GetBudgetStatus(BudgetStatusRequest) returns (BudgetStatusResponse);
  rpc ConfigureBudgetThreshold(ConfigureThresholdRequest) returns (ConfigureThresholdResponse);
}
```

### Message Definitions (Key Patterns)

**Decimal as String:** All monetary values MUST be string-typed in proto:
```protobuf
message CostSummaryResponse {
  string total_cost_usd = 1;  // "123.45" - NOT double
  // ...
}
```

**Data Availability for TTL:** The `GetDailyCostTrend` response includes:
```protobuf
message DailyTrendResponse {
  repeated DailyCostEntry entries = 1;
  string data_available_from = 2;  // ISO date YYYY-MM-DD
}
```

### gRPC Server Pattern

Follow existing service patterns (`plantation-model`, `collection-model`, `ai-model`):

```python
# grpc_server.py
async def serve(
    cost_repository: UnifiedCostRepository,
    budget_monitor: BudgetMonitor,
    threshold_repository: ThresholdRepository,
    port: int = 50051,
) -> grpc.aio.Server:
    """Start gRPC server with UnifiedCostService."""
    server = grpc.aio.server()

    servicer = UnifiedCostServiceServicer(
        cost_repository=cost_repository,
        budget_monitor=budget_monitor,
        threshold_repository=threshold_repository,
    )
    add_UnifiedCostServiceServicer_to_server(servicer, server)

    SERVICE_NAMES = (
        platform_cost_pb2.DESCRIPTOR.services_by_name["UnifiedCostService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)

    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    return server
```

### Servicer Implementation Pattern

```python
# unified_cost_service.py
class UnifiedCostServiceServicer(platform_cost_pb2_grpc.UnifiedCostServiceServicer):
    """gRPC servicer for unified cost queries."""

    def __init__(
        self,
        cost_repository: UnifiedCostRepository,
        budget_monitor: BudgetMonitor,
        threshold_repository: ThresholdRepository,
    ) -> None:
        self._cost_repository = cost_repository
        self._budget_monitor = budget_monitor
        self._threshold_repository = threshold_repository

    async def GetCostSummary(
        self,
        request: platform_cost_pb2.CostSummaryRequest,
        context: grpc.aio.ServicerContext,
    ) -> platform_cost_pb2.CostSummaryResponse:
        """Get total costs with breakdown by type."""
        start_date = date.fromisoformat(request.start_date)
        end_date = date.fromisoformat(request.end_date)
        factory_id = request.factory_id if request.HasField("factory_id") else None

        summaries = await self._cost_repository.get_summary_by_type(
            start_date=start_date,
            end_date=end_date,
            factory_id=factory_id,
        )

        return platform_cost_pb2.CostSummaryResponse(
            total_cost_usd=str(sum(s.total_cost_usd for s in summaries)),
            by_type=[self._to_cost_type_breakdown(s) for s in summaries],
            period_start=request.start_date,
            period_end=request.end_date,
            total_requests=sum(s.request_count for s in summaries),
        )
```

### ConfigureBudgetThreshold Implementation

This method MUST:
1. Persist to MongoDB via `threshold_repository.set_thresholds()`
2. Update in-memory state via `budget_monitor.update_thresholds()`
3. Return the new configuration

```python
async def ConfigureBudgetThreshold(
    self,
    request: platform_cost_pb2.ConfigureThresholdRequest,
    context: grpc.aio.ServicerContext,
) -> platform_cost_pb2.ConfigureThresholdResponse:
    """Configure budget thresholds (persisted to MongoDB)."""
    daily = Decimal(request.daily_threshold_usd) if request.HasField("daily_threshold_usd") else None
    monthly = Decimal(request.monthly_threshold_usd) if request.HasField("monthly_threshold_usd") else None

    # Persist to MongoDB
    await self._threshold_repository.set_thresholds(
        daily_threshold_usd=daily,
        monthly_threshold_usd=monthly,
    )

    # Update in-memory budget monitor
    if daily:
        self._budget_monitor.update_thresholds(daily_threshold_usd=daily)
    if monthly:
        self._budget_monitor.update_thresholds(monthly_threshold_usd=monthly)

    # Return current configuration
    status = self._budget_monitor.get_status()
    return platform_cost_pb2.ConfigureThresholdResponse(
        daily_threshold_usd=str(status.daily_threshold_usd),
        monthly_threshold_usd=str(status.monthly_threshold_usd),
        message="Thresholds updated successfully",
    )
```

### Repository Methods to Implement (Deferred from 13.3)

**get_document_cost_summary():**
```python
async def get_document_cost_summary(
    self,
    start_date: date,
    end_date: date,
) -> DocumentCostSummary:
    """Get document processing cost summary."""
    pipeline = [
        {"$match": {
            "cost_type": CostType.DOCUMENT.value,
            "timestamp": {"$gte": start_ts, "$lt": end_ts},
        }},
        {"$group": {
            "_id": None,
            "total_cost": {"$sum": {"$toDecimal": "$amount_usd"}},
            "total_pages": {"$sum": "$quantity"},
            "total_documents": {"$sum": 1},
        }},
    ]
    # ... aggregation logic
```

**get_embedding_cost_by_domain():**
```python
async def get_embedding_cost_by_domain(
    self,
    start_date: date,
    end_date: date,
) -> list[DomainCost]:
    """Get embedding costs grouped by knowledge domain."""
    pipeline = [
        {"$match": {
            "cost_type": CostType.EMBEDDING.value,
            "timestamp": {"$gte": start_ts, "$lt": end_ts},
            "knowledge_domain": {"$ne": None},
        }},
        {"$group": {
            "_id": "$knowledge_domain",
            "total_cost": {"$sum": {"$toDecimal": "$amount_usd"}},
            "tokens_total": {"$sum": "$quantity"},
            "texts_count": {"$sum": {"$ifNull": ["$metadata.texts_count", 0]}},
        }},
    ]
    # ... aggregation logic
```

### Previous Story Intelligence (13.3)

From Story 13.3:
- Repository is at `platform_cost/infrastructure/repositories/cost_repository.py`
- Uses typed Pydantic models (not dict) for all returns
- Decimal handling: store as string, use `$toDecimal` in aggregations
- BudgetMonitor has `get_status()` returning `BudgetStatus` model
- ThresholdRepository has `get_thresholds()` and `set_thresholds()` methods
- Unit tests use `mock_mongodb_client` fixture from root conftest.py

### File Structure After This Story

```
proto/
└── platform_cost/
    └── v1/
        └── platform_cost.proto              # NEW: Proto definition

services/platform-cost/src/platform_cost/
├── api/
│   ├── __init__.py
│   ├── health.py                            # EXISTS: Health endpoints
│   ├── grpc_server.py                       # NEW: gRPC server setup
│   └── unified_cost_service.py              # NEW: Service implementation
├── infrastructure/
│   └── repositories/
│       └── cost_repository.py               # MODIFIED: Add 2 methods
└── main.py                                  # MODIFIED: Add gRPC server

libs/fp-proto/src/farmer_power/platform_cost/v1/
├── __init__.py                              # GENERATED
├── platform_cost_pb2.py                     # GENERATED
└── platform_cost_pb2_grpc.py                # GENERATED
```

### Testing Strategy

- **Unit tests**: Mock repository, test servicer method implementations
- **Proto tests**: Verify message serialization (Decimal → string)
- **ConfigureBudgetThreshold**: Test both MongoDB persistence and in-memory update
- **No E2E tests this story**: Requires DAPR subscription (Story 13.5) to have events to query

### Key Patterns to Follow

**Two-Port Architecture (ADR-011):**
| Port | Purpose |
|------|---------|
| 8000 | FastAPI health endpoints |
| 50051 | gRPC UnifiedCostService |

**Decimal Serialization:**
```python
# Proto uses string for Decimal
def _decimal_to_proto(value: Decimal) -> str:
    return str(value)

# Parse dates from proto
start = date.fromisoformat(request.start_date)
```

**Optional Fields in Proto3:**
```protobuf
optional string factory_id = 3;  // Use optional keyword
```
```python
factory_id = request.factory_id if request.HasField("factory_id") else None
```

### CI PYTHONPATH Update Required

When adding new proto, update `.github/workflows/ci.yaml`:
```yaml
PYTHONPATH="${PYTHONPATH}:libs/fp-proto/src"
```
This should already be set, but verify the generated stubs are importable.

### References

- [Source: _bmad-output/architecture/adr/ADR-016-unified-cost-model.md#Part 3.2 (Proto Definition)]
- [Source: _bmad-output/epics/epic-13-platform-cost.md#Story 13.4]
- [Source: services/platform-cost/src/platform_cost/infrastructure/repositories/cost_repository.py] - Existing repository
- [Source: services/platform-cost/src/platform_cost/services/budget_monitor.py] - Existing budget monitor
- [Source: services/plantation-model/src/plantation_model/api/grpc_server.py] - Reference for gRPC server pattern
- [Source: proto/plantation/v1/plantation.proto] - Reference for proto structure

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- (list new files)

**Modified:**
- (list modified files with brief description)
