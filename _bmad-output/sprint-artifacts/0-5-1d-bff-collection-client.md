# Story 0.5.1d: BFF CollectionClient

**Status:** backlog
**GitHub Issue:** <!-- To be created -->
**Story Points:** 2

<!-- Note: This is part 4 of 4 from the original Story 0.5.1 split -->

## Story

As a **BFF developer**,
I want a CollectionClient to query documents,
So that the BFF can fetch quality events and delivery records for the dashboard.

## Acceptance Criteria

### AC1: CollectionClient Document Query Methods
**Given** Collection Model gRPC service exists (Story 0.5.1a)
**When** I implement `CollectionClient`
**Then** Client calls `collection-model` via DAPR service invocation
**And** Implements 4 document query methods:
  - `get_document(document_id)` - Single document by ID
  - `list_documents(source_id, farmer_id, linkage, date_range)` - Query with filters
  - `search_documents(query, source_ids, farmer_id)` - Full-text search
  - `get_farmer_documents(farmer_id, source_ids)` - All documents for a farmer

**And** All methods return typed domain models (NOT dict[str, Any])
**And** Pattern matches PlantationClient implementation
**And** Retry logic implemented per ADR-005

### AC2: E2E Verification
**Given** CollectionClient is implemented
**When** I run E2E tests with full infrastructure
**Then** BFF CollectionClient successfully queries Collection Model via DAPR
**And** Document data is correctly retrieved and typed

### AC3: Unit Tests
**Given** CollectionClient methods are implemented
**When** I run unit tests
**Then** All 4 methods have test coverage
**And** DAPR channel is mocked properly

## Tasks / Subtasks

- [ ] **Task 1: CollectionClient Implementation** (AC: #1)
  - [ ] Create `services/bff/src/bff/infrastructure/clients/collection_client.py`
  - [ ] Implement `get_document()` - single document by ID
  - [ ] Implement `list_documents()` - query with filters
  - [ ] Implement `search_documents()` - full-text search
  - [ ] Implement `get_farmer_documents()` - farmer's documents
  - [ ] Use base client pattern from Story 0.5.1b

- [ ] **Task 2: Unit Tests** (AC: #3)
  - [ ] `tests/unit/bff/test_collection_client.py`
  - [ ] Mock DAPR channel, test all 4 operations

- [ ] **Task 3: E2E Test** (AC: #2)
  - [ ] Update E2E infrastructure with BFF service stub
  - [ ] Add BFF→Collection Model connectivity test

## Git Workflow (MANDATORY)

**Branch name:** `story/0-5-1d-bff-collection-client`

### Story Start
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-1d-bff-collection-client
  ```

### Story Done
- [ ] Create Pull Request
- [ ] CI passes on PR
- [ ] Code review completed
- [ ] PR merged

**PR URL:** _______________

---

## Local Test Run Evidence (MANDATORY)

### 1. Unit Tests
```bash
pytest tests/unit/bff/test_collection_client.py -v
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

### Type Safety Requirements (CRITICAL)

**DO NOT use `dict[str, Any]`** - Use fp-common domain models:

```python
# WRONG
async def get_document(document_id: str) -> dict[str, Any]: ...

# CORRECT
from fp_common.domain.collection import Document

async def get_document(document_id: str) -> Document: ...
```

### CollectionClient Pattern

Follow the same pattern as PlantationClient:

```python
import grpc
from tenacity import retry, stop_after_attempt, wait_exponential
from fp_proto.collection.v1 import collection_service_pb2, collection_service_pb2_grpc
from fp_common.domain.collection import Document, DocumentQuery

class CollectionClient:
    def __init__(self, dapr_grpc_port: int = 50001):
        self._port = dapr_grpc_port
        self._channel: grpc.aio.Channel | None = None
        self._stub = None

    async def _get_stub(self):
        if self._channel is None:
            self._channel = grpc.aio.insecure_channel(f"localhost:{self._port}")
            self._stub = collection_service_pb2_grpc.CollectionServiceStub(self._channel)
        return self._stub

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_document(self, document_id: str, include_files: bool = False) -> Document:
        stub = await self._get_stub()
        metadata = [("dapr-app-id", "collection-model")]
        request = collection_service_pb2.GetDocumentRequest(
            document_id=document_id,
            include_files=include_files
        )
        response = await stub.GetDocument(request, metadata=metadata)
        return Document.from_proto(response)
```

### Dependencies

**This story requires:**
- Story 0.5.1a complete (Collection Model gRPC service)
- Story 0.5.1b complete (base client pattern)

**This story blocks:**
- Story 0.5.4: BFF API Routes

---

## Dev Agent Record

### Agent Model Used
{{agent_model_name_version}}

### File List

**Created:**
- `services/bff/src/bff/infrastructure/clients/collection_client.py`
- `tests/unit/bff/test_collection_client.py`

**Modified:**
- `tests/e2e/infrastructure/docker-compose.e2e.yaml` (add BFF service stub)
