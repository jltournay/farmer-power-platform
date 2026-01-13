# Story 13.4: gRPC UnifiedCostService

**Status:** review
**GitHub Issue:** #169

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

- [x] Task 1: Create proto definition (AC: #1)
  - [x] 1.1: Create `proto/platform_cost/v1/` directory structure
  - [x] 1.2: Create `platform_cost.proto` with service definition
  - [x] 1.3: Define all 9 RPC methods per ADR-016
  - [x] 1.4: Define all request/response messages
  - [x] 1.5: Run `bash scripts/proto-gen.sh` to generate Python stubs
  - [x] 1.6: Verify stubs appear in `libs/fp-proto/src/fp_proto/platform_cost/v1/`

- [x] Task 2: Create gRPC server setup (AC: #1)
  - [x] 2.1: Create `platform_cost/api/grpc_server.py`
  - [x] 2.2: Implement `GrpcServer` class with async start/stop
  - [x] 2.3: Configure reflection for service discovery
  - [x] 2.4: Add graceful shutdown handling
  - [x] 2.5: Register UnifiedCostService servicer

- [x] Task 3: Implement UnifiedCostService servicer (AC: #1, #2, #3)
  - [x] 3.1: Create `platform_cost/api/unified_cost_service.py`
  - [x] 3.2: Implement `GetCostSummary()` - calls `cost_repository.get_summary_by_type()`
  - [x] 3.3: Implement `GetDailyCostTrend()` - calls `cost_repository.get_daily_trend()` with `data_available_from`
  - [x] 3.4: Implement `GetCurrentDayCost()` - calls `cost_repository.get_current_day_cost()`
  - [x] 3.5: Implement `GetLlmCostByAgentType()` - calls `cost_repository.get_llm_cost_by_agent_type()`
  - [x] 3.6: Implement `GetLlmCostByModel()` - calls `cost_repository.get_llm_cost_by_model()`
  - [x] 3.7: Implement `GetDocumentCostSummary()` - calls `cost_repository.get_document_cost_summary()`
  - [x] 3.8: Implement `GetEmbeddingCostByDomain()` - calls `cost_repository.get_embedding_cost_by_domain()`
  - [x] 3.9: Implement `GetBudgetStatus()` - calls `budget_monitor.get_status()`
  - [x] 3.10: Implement `ConfigureBudgetThreshold()` - updates both MongoDB and in-memory

- [x] Task 4: Add missing repository methods (AC: #1, #2)
  - [x] 4.1: Implement `get_document_cost_summary()` in cost_repository.py (deferred from Story 13.3)
  - [x] 4.2: Implement `get_embedding_cost_by_domain()` in cost_repository.py (deferred from Story 13.3)

- [x] Task 5: Update main.py for gRPC server (AC: #1, #3)
  - [x] 5.1: Add gRPC server initialization in lifespan startup
  - [x] 5.2: Pass cost_repository and budget_monitor to servicer
  - [x] 5.3: Pass threshold_repository to servicer for persistence
  - [x] 5.4: Start gRPC server on port 50054 (per config)
  - [x] 5.5: Add graceful shutdown in lifespan cleanup

- [x] Task 6: Write unit tests for proto conversions
  - [x] 6.1: Create `tests/unit/platform_cost/test_unified_cost_service.py`
  - [x] 6.2: Test proto message serialization (Decimal → string)
  - [x] 6.3: Test all RPC method implementations with mock repository
  - [x] 6.4: Test ConfigureBudgetThreshold persists and updates in-memory

- [x] Task 7: Write unit tests for new repository methods
  - [x] 7.1: Add tests for `get_document_cost_summary()` aggregation
  - [x] 7.2: Add tests for `get_embedding_cost_by_domain()` aggregation

- [x] Task 8: Run lint and format checks
  - [x] 8.1: Run `ruff check .` and fix any issues
  - [x] 8.2: Run `ruff format --check .` and fix any issues

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
======================== 92 passed, 1 warning in 2.14s =========================
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
(pending - will run after committing)
```
**E2E passed:** [ ] Yes / [ ] No / [x] N/A (no platform-cost E2E scenarios yet - gRPC service only)

### 3. Lint Check
```bash
ruff check services/platform-cost/ tests/unit/platform_cost/ proto/ && ruff format --check services/platform-cost/ tests/unit/platform_cost/
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/13-4-grpc-unified-cost-service

# Wait ~30s, then check CI status
gh run list --branch feature/13-4-grpc-unified-cost-service --limit 3
```
**CI Run ID:** 20949443136
**CI E2E Run ID:** 20949702988
**CI E2E Status:** [x] Passed / [ ] Failed / [ ] N/A
**Verification Date:** 2026-01-13

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

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 9 gRPC RPC methods implemented per ADR-016
- Proto definition follows existing patterns (string for Decimal values)
- DomainCost model updated to use tokens_total/texts_count instead of query_count
- proto-gen.sh updated to fix imports for platform_cost domain
- gRPC server starts on port 50054 per config.py

### File List

**Created:**
- `proto/platform_cost/v1/platform_cost.proto` - Proto definition for UnifiedCostService
- `services/platform-cost/src/platform_cost/api/grpc_server.py` - gRPC server wrapper
- `services/platform-cost/src/platform_cost/api/unified_cost_service.py` - Servicer implementation
- `tests/unit/platform_cost/test_unified_cost_service.py` - Unit tests for servicer
- `libs/fp-proto/src/fp_proto/platform_cost/v1/` - Generated proto stubs

**Modified:**
- `services/platform-cost/src/platform_cost/main.py` - Added gRPC server startup/shutdown
- `services/platform-cost/src/platform_cost/api/__init__.py` - Export new classes
- `services/platform-cost/src/platform_cost/infrastructure/repositories/cost_repository.py` - Added get_document_cost_summary(), get_embedding_cost_by_domain()
- `services/platform-cost/src/platform_cost/domain/cost_event.py` - Updated DomainCost model (tokens_total, texts_count)
- `scripts/proto-gen.sh` - Added platform_cost to import fix patterns
- `tests/unit/platform_cost/test_cost_repository.py` - Added tests for new repository methods
- `tests/unit/platform_cost/test_domain_models.py` - Updated DomainCost test
