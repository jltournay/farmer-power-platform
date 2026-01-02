# Story 0.5.1a: Collection Model gRPC Service Layer

**Status:** ready-for-dev
**GitHub Issue:** #65
**Story Points:** 2

<!-- Note: This is part 1 of 4 from the original Story 0.5.1 split -->

## Story

As a **BFF developer**,
I want Collection Model to expose a gRPC service layer,
So that the BFF can query documents via DAPR service invocation.

## Acceptance Criteria

### AC1: Collection Model gRPC Service Definition
**Given** Collection Model exists with REST/MCP only
**When** I add gRPC service layer
**Then** `CollectionService` is defined in `proto/collection/v1/collection_service.proto`
**And** Service implements document queries only (mirrors MCP tools):
  - `GetDocument` - Single document by ID
  - `ListDocuments` - Query documents with filters (source_id, farmer_id, linkage, date_range)
  - `SearchDocuments` - Full-text search across document content/attributes
  - `GetFarmerDocuments` - All documents for a farmer across sources
**And** gRPC server runs on port 50051 alongside existing FastAPI health endpoints
**And** Unit tests cover all gRPC handlers

> **Architecture Note:** Collection Model does NOT compute aggregations (summaries, statistics).
> Aggregation logic belongs in BFF's `services/` layer which combines data from multiple backends.

### AC2: E2E Verification
**Given** the gRPC service is implemented
**When** I run the E2E test suite
**Then** Collection Model gRPC service responds to requests via DAPR sidecar
**And** Proto messages are correctly serialized/deserialized

## Tasks / Subtasks

- [ ] **Task 1: Proto Definition** (AC: #1)
  - [ ] Create `proto/collection/v1/collection_service.proto` with CollectionService
  - [ ] Define request/response messages for 4 document query methods
  - [ ] Generate Python stubs via `scripts/generate_proto.sh`
  - [ ] Update `libs/fp-proto` package

- [ ] **Task 2: Collection Model gRPC Server** (AC: #1)
  - [ ] Create `services/collection-model/src/collection_model/api/grpc_service.py`
  - [ ] Implement 4 gRPC handler methods: GetDocument, ListDocuments, SearchDocuments, GetFarmerDocuments
  - [ ] Wire gRPC server to existing service startup (port 50051)
  - [ ] Ensure FastAPI health endpoints continue on port 8000 (ADR-011)

- [ ] **Task 3: Unit Tests** (AC: #1)
  - [ ] `tests/unit/collection_model/test_grpc_service.py`
  - [ ] Mock MongoDB queries, test all 4 handlers

- [ ] **Task 4: E2E Test Update** (AC: #2)
  - [ ] Update E2E docker-compose with Collection Model gRPC port
  - [ ] Add basic gRPC connectivity test

## Git Workflow (MANDATORY)

**Branch name:** `story/0-5-1a-collection-grpc-service`

### Story Start
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-1a-collection-grpc-service
  ```

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.5.1a: Collection gRPC Service" --base main`
- [ ] CI passes on PR
- [ ] Code review completed
- [ ] PR merged

**PR URL:** _______________

---

## Local Test Run Evidence (MANDATORY)

### 1. Unit Tests
```bash
pytest tests/unit/collection_model/test_grpc_service.py -v
```
**Output:**
```
(paste test summary here)
```

### 2. E2E Tests
```bash
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

---

## Dev Notes

### Architecture Compliance

**Two-Port Service Architecture (ADR-011):**
| Port | Purpose |
|------|---------|
| **8000** | FastAPI health endpoints (`/health`, `/ready`) - direct, no DAPR |
| **50051** | gRPC API server - domain operations via DAPR sidecar |

### Proto Definition (CollectionService)

```protobuf
// proto/collection/v1/collection_service.proto
syntax = "proto3";

package farmer_power.collection.v1;

import "google/protobuf/struct.proto";
import "google/protobuf/timestamp.proto";

service CollectionService {
  rpc GetDocument(GetDocumentRequest) returns (Document);
  rpc ListDocuments(ListDocumentsRequest) returns (ListDocumentsResponse);
  rpc SearchDocuments(SearchDocumentsRequest) returns (ListDocumentsResponse);
  rpc GetFarmerDocuments(GetFarmerDocumentsRequest) returns (ListDocumentsResponse);
}

message GetDocumentRequest {
  string document_id = 1;
  bool include_files = 2;
}

message ListDocumentsRequest {
  string source_id = 1;
  string farmer_id = 2;
  map<string, string> linkage = 3;
  google.protobuf.Timestamp start_date = 4;
  google.protobuf.Timestamp end_date = 5;
  int32 page_size = 6;
  string page_token = 7;
}

message SearchDocumentsRequest {
  string query = 1;
  repeated string source_ids = 2;
  string farmer_id = 3;
  int32 page_size = 4;
  string page_token = 5;
}

message GetFarmerDocumentsRequest {
  string farmer_id = 1;
  repeated string source_ids = 2;
  google.protobuf.Timestamp start_date = 3;
  google.protobuf.Timestamp end_date = 4;
}

message Document {
  string document_id = 1;
  string source_id = 2;
  string farmer_id = 3;
  map<string, string> linkage = 4;
  google.protobuf.Struct attributes = 5;
  repeated FileReference files = 6;
  google.protobuf.Timestamp source_timestamp = 7;
  google.protobuf.Timestamp ingested_at = 8;
}

message FileReference {
  string path = 1;
  string role = 2;
  string blob_uri = 3;
  string mime_type = 4;
}

message ListDocumentsResponse {
  repeated Document documents = 1;
  string next_page_token = 2;
  int32 total_count = 3;
}
```

### Type Safety Requirements (CRITICAL)

**DO NOT use `dict[str, Any]`** - Use fp-common domain models:

```python
# WRONG - Untyped dictionary
async def get_document(document_id: str) -> dict[str, Any]:
    ...

# CORRECT - Use domain models from fp-common
from fp_common.domain.collection import Document, DocumentQuery

async def get_document(document_id: str) -> Document:
    ...
```

**All gRPC handlers MUST:**
- Accept typed Pydantic models or proto-generated request types
- Return typed Pydantic models or proto-generated response types
- Convert between proto and domain models using explicit mapping functions
- Never pass raw dicts between layers

**Reference:** `libs/fp-common/fp_common/domain/` for existing domain models

### Dependencies

**This story requires:**
- Collection Model existing codebase (Epic 0.4 complete)
- `libs/fp-common` domain models

**This story blocks:**
- Story 0.5.1d: BFF CollectionClient

---

## Dev Agent Record

### Agent Model Used
{{agent_model_name_version}}

### File List

**Created:**
- `proto/collection/v1/collection_service.proto`
- `services/collection-model/src/collection_model/api/grpc_service.py`
- `tests/unit/collection_model/test_grpc_service.py`

**Modified:**
- `services/collection-model/src/collection_model/main.py` (add gRPC server startup)
- `libs/fp-proto/` (regenerate proto stubs)
