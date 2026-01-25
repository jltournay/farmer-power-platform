# Story 9.11a: SourceConfigService gRPC in Collection Model

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Platform Administrator**,
I want **read-only gRPC endpoints for source configurations in the Collection Model service**,
so that **the Admin UI can display source config data without direct MongoDB access, enabling auditability and debugging of ingestion configurations**.

## Use Case Context

**Epic:** 9 - Platform Admin Portal
**Use Case:** UC9.1: View Source Configurations
**Steps Covered:** Step 1 (backend gRPC layer)
**Input (from preceding steps):** None (first story in ADR-019 implementation chain)
**Output (for subsequent steps):** SourceConfigService gRPC endpoints accessible via DAPR service invocation from BFF
**E2E Verification:** BFF client can invoke `ListSourceConfigs` via DAPR and receive paginated list of source configs with summaries; `GetSourceConfig` returns full config detail as JSON

## Acceptance Criteria

### AC 9.11a.1: Proto Service Definition

**Given** the Collection Model proto file exists
**When** I add the SourceConfigService definition
**Then** the proto file contains:
- `service SourceConfigService` with `ListSourceConfigs` and `GetSourceConfig` RPCs
- Request/Response messages per ADR-019 Decision 2
- Timestamp imports for `updated_at` and `created_at` fields
- NO write methods (read-only service per ADR-019)

### AC 9.11a.2: ListSourceConfigs RPC

**Given** source configs exist in MongoDB
**When** I call `ListSourceConfigs` with optional filters
**Then** I receive:
- Paginated `SourceConfigSummary` records (source_id, display_name, description, enabled, ingestion_mode, ai_agent_id, updated_at)
- `next_page_token` for pagination (empty if no more results)
- `total_count` of matching records
- Filter by `enabled_only=true` returns only enabled configs
- Filter by `ingestion_mode` returns only matching mode ("blob_trigger" or "scheduled_pull")
- Default page_size=20, max=100

### AC 9.11a.3: GetSourceConfig RPC

**Given** a source config exists with source_id "qc-analyzer-result"
**When** I call `GetSourceConfig(source_id="qc-analyzer-result")`
**Then** I receive:
- `SourceConfigResponse` with all summary fields
- `config_json` field containing the full SourceConfig as JSON string
- `created_at` and `updated_at` timestamps
- NOT_FOUND error if source_id doesn't exist

### AC 9.11a.4: gRPC Server Registration

**Given** the Collection Model service starts
**When** the gRPC server initializes
**Then** `SourceConfigServiceServicer` is registered alongside existing `CollectionServiceServicer`
**And** both services are accessible on port 50051

### AC 9.11a.5: Unit Tests

**Given** the SourceConfigService implementation
**When** unit tests run
**Then** all tests pass covering:
- ListSourceConfigs with no filters
- ListSourceConfigs with `enabled_only=true`
- ListSourceConfigs with `ingestion_mode` filter
- ListSourceConfigs pagination
- GetSourceConfig success case
- GetSourceConfig NOT_FOUND case
- Invalid page_token handling

### AC-E2E (from Use Case)

**Given** the Collection Model service is running with seed data containing at least 2 source configs
**When** an external client (simulating BFF) invokes `ListSourceConfigs` via DAPR service invocation
**Then** the response contains `total_count >= 2` and `configs[]` with `source_id` fields populated

## Tasks / Subtasks

### Task 1: Add Proto Service Definition (AC: 1)

- [ ] Add `SourceConfigService` to `proto/collection/v1/collection.proto`
- [ ] Define `ListSourceConfigsRequest` and `ListSourceConfigsResponse` messages
- [ ] Define `GetSourceConfigRequest` and `SourceConfigResponse` messages
- [ ] Define `SourceConfigSummary` message with key fields
- [ ] Regenerate proto stubs: `bash scripts/proto-gen.sh`
- [ ] Verify generated files in `libs/fp-proto/src/fp_proto/collection/v1/`

### Task 2: Extend SourceConfigRepository (AC: 2, 3)

- [ ] Add `list_all()` method with pagination support to `SourceConfigRepository`
- [ ] Add optional filters: `enabled_only`, `ingestion_mode`
- [ ] Add `count()` method for total count queries
- [ ] Return Pydantic `SourceConfig` models (existing pattern)

### Task 3: Create Source Config Converters in fp_common (AC: 2, 3)

- [ ] Create `libs/fp-common/fp_common/converters/source_config_converters.py`
- [ ] Implement `source_config_summary_to_proto(config: SourceConfig) -> SourceConfigSummary` (Pydantic → Proto)
- [ ] Implement `source_config_response_to_proto(config: SourceConfig) -> SourceConfigResponse` (Pydantic → Proto)
- [ ] Implement `source_config_summary_from_proto(proto: SourceConfigSummary) -> dict` (Proto → dict, for BFF in 9.11b)
- [ ] Implement `source_config_response_from_proto(proto: SourceConfigResponse) -> dict` (Proto → dict, for BFF in 9.11b)
- [ ] Add helper `_datetime_to_proto_timestamp()` if not already shared
- [ ] Export converters in `libs/fp-common/fp_common/converters/__init__.py`
- [ ] Follow existing converter patterns (see `plantation_converters.py`, `cost_converters.py`)

### Task 4: Implement ListSourceConfigs RPC (AC: 2)

- [ ] Create `services/collection-model/src/collection_model/api/source_config_service.py`
- [ ] Implement `SourceConfigServiceServicer` class skeleton
- [ ] Implement `ListSourceConfigs` RPC with:
  - Pagination via skip/limit (page_token is skip encoded as string)
  - Filter by `enabled_only`
  - Filter by `ingestion_mode`
  - Return `SourceConfigSummary` for each config
- [ ] Use `source_config_summary_to_proto()` from `fp_common.converters`

### Task 5: Implement GetSourceConfig RPC (AC: 3)

- [ ] Implement `GetSourceConfig` RPC in `SourceConfigServiceServicer`:
  - Lookup by `source_id` using `repository.get_by_source_id()`
  - Return full config as JSON in `config_json` field via `config.model_dump_json()`
  - Return NOT_FOUND gRPC error if source_id doesn't exist
- [ ] Use `source_config_response_to_proto()` from `fp_common.converters`

### Task 6: Register gRPC Service (AC: 4)

- [ ] Update `serve_grpc()` in `grpc_service.py` to register `SourceConfigServiceServicer`
- [ ] Pass MongoDB database to the servicer (same pattern as `CollectionServiceServicer`)
- [ ] Verify both services accessible on port 50051

### Task 7: Unit Tests (AC: 5)

- [ ] Create `tests/unit/collection/api/test_source_config_service.py`
- [ ] Test `ListSourceConfigs` with no filters
- [ ] Test `ListSourceConfigs` with `enabled_only=true`
- [ ] Test `ListSourceConfigs` with `ingestion_mode="blob_trigger"`
- [ ] Test `ListSourceConfigs` with `ingestion_mode="scheduled_pull"`
- [ ] Test `ListSourceConfigs` pagination (page_size, page_token)
- [ ] Test `ListSourceConfigs` empty result set
- [ ] Test `GetSourceConfig` success case
- [ ] Test `GetSourceConfig` NOT_FOUND case
- [ ] Test invalid `page_token` handling (reset to 0)
- [ ] Mock `SourceConfigRepository` in tests
- [ ] Create `tests/unit/fp_common/converters/test_source_config_converters.py` for converter unit tests

### Task 8: Create New E2E Tests for AC-E2E (MANDATORY - DO NOT SKIP)

> **⛔ CRITICAL: This task is NON-NEGOTIABLE and BLOCKS story completion.**
> - Story CANNOT be marked "review" or "done" without E2E tests
> - Unit tests alone are NOT sufficient - E2E validates real infrastructure
> - Skipping this task violates the Definition of Done

**File to create:** `tests/e2e/scenarios/test_12_source_config_service.py`

**Why this matters:** E2E tests validate the full stack (gRPC → MongoDB → Response) with real DAPR service invocation. Unit tests with mocks cannot catch integration issues.

#### 8.1 Verify Seed Data Exists
- [ ] Check `tests/e2e/infrastructure/seed_data/` for source_configs
- [ ] Verify at least 2 source configs exist in seed data (one `blob_trigger`, one `scheduled_pull`)
- [ ] If missing, create seed data file before writing tests

#### 8.2 Create E2E Test File
- [ ] Create `tests/e2e/scenarios/test_12_source_config_service.py`
- [ ] Follow existing E2E test patterns (see `test_01_plantation_service.py`)
- [ ] Import `SourceConfigClient` from BFF (or use direct gRPC for this story)

#### 8.3 Implement Required Test Cases
- [ ] `test_list_source_configs_returns_all()` - ListSourceConfigs returns configs from seed
- [ ] `test_list_source_configs_with_enabled_filter()` - Filter by enabled_only=true works
- [ ] `test_list_source_configs_with_mode_filter()` - Filter by ingestion_mode works
- [ ] `test_get_source_config_returns_full_json()` - GetSourceConfig returns valid config_json
- [ ] `test_get_source_config_not_found()` - GetSourceConfig returns NOT_FOUND for invalid ID

#### 8.4 Run E2E Tests Locally (BEFORE marking story complete)
```bash
# Start E2E infrastructure
bash scripts/e2e-up.sh --build

# Run pre-flight validation
bash scripts/e2e-preflight.sh

# Run the new E2E tests specifically
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_12_source_config_service.py -v

# Run FULL E2E suite to check for regressions
bash scripts/e2e-test.sh --keep-up

# Tear down
bash scripts/e2e-up.sh --down
```

#### 8.5 Capture Evidence
- [ ] Paste test output in "Local Test Run Evidence" section below
- [ ] All 5 test cases must PASS
- [ ] No regressions in other E2E tests

**⛔ BLOCKER:** Do NOT proceed to Git Workflow until Task 8 is 100% complete with passing tests.

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.11a: SourceConfigService gRPC in Collection Model"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/9-11a-source-config-grpc
  ```

**Branch name:** `story/9-11a-source-config-grpc`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/9-11a-source-config-grpc`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.11a: SourceConfigService gRPC in Collection Model" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/9-11a-source-config-grpc`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

> **REGRESSION RULE - NO EXCEPTIONS:**
> - Run the **FULL** test suite, not just tests you think are related to your change.
> - A previously passing test that now fails **IS a regression caused by your change**.
> - **Zero failures** is the only acceptable outcome. Fix all regressions before proceeding.

### 1. Unit Tests
```bash
pytest tests/unit/ -v
```
**Output:**
```
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
bash scripts/e2e-up.sh --build

# Pre-flight validation
bash scripts/e2e-preflight.sh

# Run E2E tests
bash scripts/e2e-test.sh --keep-up

# Tear down
bash scripts/e2e-up.sh --down
```
**Output:**
```
(paste E2E test output here - story is NOT ready for review without this)
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/9-11a-source-config-grpc

# Trigger E2E CI workflow
gh workflow run e2e.yaml --ref story/9-11a-source-config-grpc

# Wait and check status
sleep 10
gh run list --workflow=e2e.yaml --branch story/9-11a-source-config-grpc --limit 1
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Compliance

**This is a backend-only story.** No frontend changes required.

**Layer Architecture (ADR-019):**
```
Admin UI (future 9.11c) → BFF (future 9.11b) → Collection Model gRPC → MongoDB
                                                 ↑ THIS STORY
```

### Critical: Read-Only Service

Per ADR-019, this service is **READ-ONLY**. All write operations (create, update, delete) are handled by the `source-config` CLI tool.

| Operation | Tool | Rationale |
|-----------|------|-----------|
| **Create/Update/Delete** | `source-config` CLI | Complex validation, version management |
| **Read/List** | SourceConfigService gRPC | Simple queries for Admin UI |

### Proto Definition (from ADR-019 Decision 2)

Add to `proto/collection/v1/collection.proto` after existing `CollectionService`:

```protobuf
// ============================================================================
// Source Config Service - Read-only admin visibility (ADR-019)
// Write operations handled by source-config CLI
// ============================================================================

service SourceConfigService {
  // List all source configurations with optional filters
  rpc ListSourceConfigs(ListSourceConfigsRequest) returns (ListSourceConfigsResponse);

  // Get a single source configuration by ID
  rpc GetSourceConfig(GetSourceConfigRequest) returns (SourceConfigResponse);
}

message ListSourceConfigsRequest {
  int32 page_size = 1;         // Max 100, default 20
  string page_token = 2;       // Pagination cursor
  bool enabled_only = 3;       // Filter to enabled configs only
  string ingestion_mode = 4;   // Filter: "blob_trigger" or "scheduled_pull"
}

message ListSourceConfigsResponse {
  repeated SourceConfigSummary configs = 1;
  string next_page_token = 2;
  int32 total_count = 3;
}

message GetSourceConfigRequest {
  string source_id = 1;
}

message SourceConfigSummary {
  string source_id = 1;
  string display_name = 2;
  string description = 3;
  bool enabled = 4;
  string ingestion_mode = 5;      // "blob_trigger" or "scheduled_pull"
  string ai_agent_id = 6;         // Linked AI agent (nullable)
  google.protobuf.Timestamp updated_at = 7;
}

message SourceConfigResponse {
  string source_id = 1;
  string display_name = 2;
  string description = 3;
  bool enabled = 4;

  // Full config as JSON for detail view
  // Using JSON string to avoid duplicating complex nested proto definitions
  string config_json = 5;

  google.protobuf.Timestamp created_at = 6;
  google.protobuf.Timestamp updated_at = 7;
}
```

### Implementation Pattern (Follow Existing CollectionService)

The new `SourceConfigServiceServicer` should follow the pattern in `grpc_service.py`:

```python
# services/collection-model/src/collection_model/api/source_config_service.py
"""SourceConfig gRPC Service - Read-only admin visibility (ADR-019)."""

import json
from datetime import datetime

import grpc
import structlog
from collection_model.infrastructure.repositories.source_config_repository import SourceConfigRepository
from fp_common.models.source_config import SourceConfig
from fp_proto.collection.v1 import collection_pb2, collection_pb2_grpc
from google.protobuf import timestamp_pb2
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = structlog.get_logger(__name__)


def _datetime_to_proto_timestamp(dt: datetime) -> timestamp_pb2.Timestamp:
    """Convert Python datetime to protobuf Timestamp."""
    ts = timestamp_pb2.Timestamp()
    ts.FromDatetime(dt)
    return ts


def _source_config_to_summary(config: SourceConfig) -> collection_pb2.SourceConfigSummary:
    """Convert SourceConfig Pydantic model to proto SourceConfigSummary."""
    return collection_pb2.SourceConfigSummary(
        source_id=config.source_id,
        display_name=config.display_name,
        description=config.description,
        enabled=config.enabled,
        ingestion_mode=config.ingestion.mode,
        ai_agent_id=config.transformation.get_ai_agent_id() or "",
        updated_at=_datetime_to_proto_timestamp(config.updated_at) if hasattr(config, 'updated_at') and config.updated_at else timestamp_pb2.Timestamp(),
    )


class SourceConfigServiceServicer(collection_pb2_grpc.SourceConfigServiceServicer):
    """gRPC service implementation for source config read-only queries (ADR-019)."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.repository = SourceConfigRepository(db)

    async def ListSourceConfigs(
        self,
        request: collection_pb2.ListSourceConfigsRequest,
        context: grpc.aio.ServicerContext,
    ) -> collection_pb2.ListSourceConfigsResponse:
        """List source configs with optional filters and pagination."""
        # Implementation here...
        pass

    async def GetSourceConfig(
        self,
        request: collection_pb2.GetSourceConfigRequest,
        context: grpc.aio.ServicerContext,
    ) -> collection_pb2.SourceConfigResponse:
        """Get a single source config by ID."""
        # Implementation here...
        pass
```

### Repository Extension

Add to `SourceConfigRepository`:

```python
async def list_all(
    self,
    page_size: int = 20,
    skip: int = 0,
    enabled_only: bool = False,
    ingestion_mode: str | None = None,
) -> list[SourceConfig]:
    """List source configs with pagination and optional filters."""
    query: dict[str, Any] = {}

    if enabled_only:
        query["enabled"] = True

    if ingestion_mode:
        query["ingestion.mode"] = ingestion_mode

    cursor = self._collection.find(query).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    configs = []
    for doc in docs:
        doc.pop("_id", None)
        configs.append(SourceConfig.model_validate(doc))

    return configs

async def count(
    self,
    enabled_only: bool = False,
    ingestion_mode: str | None = None,
) -> int:
    """Count source configs matching filters."""
    query: dict[str, Any] = {}

    if enabled_only:
        query["enabled"] = True

    if ingestion_mode:
        query["ingestion.mode"] = ingestion_mode

    return await self._collection.count_documents(query)
```

### Existing Repository Methods (DO NOT DUPLICATE)

The `SourceConfigRepository` already has:
- `get_by_source_id(source_id: str) -> SourceConfig | None` - Use for GetSourceConfig
- `get_all_enabled() -> list[SourceConfig]` - Reference for enabled filter pattern

### SourceConfig Model Structure

The `SourceConfig` model in `fp_common.models.source_config` is complex with nested configs:

```python
class SourceConfig(BaseModel):
    source_id: str
    display_name: str
    description: str
    enabled: bool
    ingestion: IngestionConfig      # mode, landing_container, etc.
    validation: ValidationConfig    # schema_name, strict
    transformation: TransformationConfig  # ai_agent_id, extract_fields
    storage: StorageConfig          # raw_container, index_collection
    events: EventsConfig            # on_success, on_failure topics
```

The `config_json` field in `SourceConfigResponse` contains the full model serialized as JSON:
```python
config_json = config.model_dump_json()
```

### Testing Strategy

**Unit tests (mock MongoDB):**
- Mock `SourceConfigRepository` methods
- Test servicer methods directly
- Use `grpc.aio.ServicerContext` mock for error testing

**E2E tests (real infrastructure):**
- Use existing E2E seed data (verify source_configs exist)
- Call gRPC via DAPR service invocation
- Verify response structure and data

### File Structure (Changes)

```
proto/collection/v1/
├── collection.proto                    # MODIFIED - Add SourceConfigService

libs/fp-common/fp_common/converters/
├── __init__.py                         # MODIFIED - Export new converters
├── source_config_converters.py         # NEW - Pydantic↔Proto converters

services/collection-model/src/collection_model/
├── api/
│   ├── grpc_service.py                 # MODIFIED - Register new servicer
│   └── source_config_service.py        # NEW - SourceConfigServiceServicer
├── infrastructure/repositories/
│   └── source_config_repository.py     # MODIFIED - Add list_all, count

libs/fp-proto/src/fp_proto/collection/v1/
├── collection_pb2.py                   # AUTO-GENERATED
├── collection_pb2_grpc.py              # AUTO-GENERATED

tests/
├── unit/fp_common/converters/
│   └── test_source_config_converters.py # NEW - Converter unit tests
├── unit/collection/api/
│   └── test_source_config_service.py   # NEW - gRPC service unit tests
├── e2e/scenarios/
│   └── test_12_source_config_service.py # NEW - E2E tests
```

### Seed Data Verification

Ensure E2E seed data includes source configs. Check:
- `tests/e2e/infrastructure/seed_data/source_configs/`
- Or `tests/fixtures/mongodb_data/source_configs.json`

If missing, create minimal seed:
```json
[
  {
    "source_id": "qc-analyzer-result",
    "display_name": "QC Analyzer Result",
    "description": "Tea leaf quality analysis results",
    "enabled": true,
    "ingestion": { "mode": "blob_trigger", ... },
    ...
  },
  {
    "source_id": "weather-forecast",
    "display_name": "Weather Forecast",
    "description": "Daily weather data",
    "enabled": true,
    "ingestion": { "mode": "scheduled_pull", ... },
    ...
  }
]
```

### Dependencies

- **None** - This is the first story in the ADR-019 chain
- **Blocks:** Story 9.11b (BFF client + REST API)

### Previous Story Intelligence

**From Story 9.10a/9.10b (Platform Cost):**
- Follow the pattern of splitting backend (gRPC/BFF) and frontend stories
- gRPC servicer pattern in ai-model and platform-cost services
- Proto regeneration via `bash scripts/proto-gen.sh`

**From Story 0.5.1a (Collection gRPC):**
- CollectionServiceServicer pattern in `grpc_service.py`
- serve_grpc() function registers servicers
- Timestamp conversion helpers

### Git Intelligence

**Recent commits (context):**
- `9586e9b` fix: Lint errors and test selector conflicts
- `dd46fdd` fix: Ensure consistent MetricCard heights
- `07c3569` Story 9.10b: Platform Cost Dashboard UI (#228)
- `6811ea9` Story 9.10a: Platform Cost BFF REST API (#226)

### References

- [Source: _bmad-output/architecture/adr/ADR-019-admin-configuration-visibility.md] - Full proto definitions, architecture decisions
- [Source: services/collection-model/src/collection_model/api/grpc_service.py] - Existing gRPC service pattern
- [Source: services/collection-model/src/collection_model/infrastructure/repositories/source_config_repository.py] - Repository pattern
- [Source: libs/fp-common/fp_common/models/source_config.py] - SourceConfig Pydantic model
- [Source: _bmad-output/epics/epic-9-admin-portal/story-911a-source-config-grpc-collection-model.md] - Epic story definition
- [Source: _bmad-output/epics/epic-9-admin-portal/use-cases.md#UC9.1] - Use case definition
- [Source: _bmad-output/project-context.md] - Architecture rules and patterns

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
