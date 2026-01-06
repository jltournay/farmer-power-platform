# Story 0.6.13: Replace CollectionClient Direct DB Access with gRPC

**Status:** in-progress
**GitHub Issue:** #113
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADR:** [ADR-010: DAPR Patterns](../architecture/adr/ADR-010-dapr-patterns-configuration.md), [ADR-011: Service Architecture](../architecture/adr/ADR-011-grpc-fastapi-dapr-architecture.md)
**Story Points:** 3
**Wave:** 4 (Type Safety & Service Boundaries)
**Prerequisites:**
- Story 0.6.3/0.6.4 (gRPC Retry Pattern) - DONE - Pattern established in AiModelClient and IterationResolver
- Story 0.6.11/0.6.12 (Proto-to-Pydantic Converters) - DONE - Converters exist in `fp_common.converters`
- Story 0.5.1a (Collection gRPC Service) - DONE - `CollectionService.GetDocument` RPC available

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - Replace direct MongoDB access with gRPC via DAPR!**

### 1. Problem Statement

**`CollectionClient`** (`services/plantation-model/src/plantation_model/infrastructure/collection_client.py`) currently:
- **Connects directly to Collection Model's MongoDB** using `AsyncIOMotorClient`
- Bypasses domain boundaries (Plantation Model should NOT access Collection Model's database)
- Violates ADR-010/011: "ALL inter-service communication via DAPR"
- Creates tight coupling to Collection Model's internal schema

**Evidence from code:**
```python
# CURRENT (lines 65-68):
self._mongodb_uri = mongodb_uri or settings.collection_mongodb_uri  # BAD!
self._client = AsyncIOMotorClient(self._mongodb_uri)  # Direct DB access!
self._db = self._client[self._database_name]
```

### 2. Goal

Replace `CollectionClient` with `CollectionGrpcClient` that:
1. **Calls Collection Model's `GetDocument` RPC** via DAPR service invocation
2. **Uses singleton channel pattern** with retry (matching Stories 0.6.3/0.6.4)
3. **Returns Pydantic model** (consistent with Story 0.6.12)
4. **Removes `collection_mongodb_uri`** from plantation-model settings

### 3. Key Insight - Collection gRPC Service Already Exists!

Story 0.5.1a already created `CollectionService` gRPC service:
- **Proto:** `proto/collection/v1/collection.proto` (lines 20-32)
- **Service:** `services/collection-model/src/collection_model/api/grpc_service.py`
- **Method:** `GetDocument(GetDocumentRequest) -> Document`
- **Port:** 50051 (standard gRPC port per ADR-011)

The RPC is READY TO USE. Plantation Model just needs to call it via DAPR.

### 4. Definition of Done Checklist

- [ ] **CollectionGrpcClient created** - New client using gRPC via DAPR service invocation
- [ ] **Singleton channel pattern** - Same pattern as PlantationClient in plantation-mcp
- [ ] **Retry logic implemented** - Tenacity with 3 attempts, exponential backoff (1-10s)
- [ ] **Proto-to-Pydantic conversion** - Use existing converters from `fp_common.converters`
- [ ] **Old CollectionClient removed** - Delete direct MongoDB client
- [ ] **Settings updated** - Remove `collection_mongodb_uri`, add `collection_app_id`
- [ ] **QualityEventProcessor updated** - Use new CollectionGrpcClient
- [ ] **Unit tests pass** - Verify gRPC calls, not MongoDB
- [ ] **E2E tests pass** - No functional regression (behavior identical)
- [ ] **Lint passes** - ruff check and format

---

## Story

As a **platform engineer**,
I want Plantation Model to fetch documents from Collection Model via gRPC instead of direct MongoDB access,
So that domain boundaries are respected and services communicate through proper DAPR channels.

## Acceptance Criteria

1. **AC1: CollectionGrpcClient Uses gRPC** - Given `CollectionClient` currently uses `AsyncIOMotorClient` to connect to `collection_mongodb_uri`, When I create `CollectionGrpcClient`, Then it calls Collection Model's `GetDocument` RPC via DAPR service invocation, And uses `dapr-app-id` metadata header for routing.

2. **AC2: Singleton Channel Pattern** - Given `PlantationClient` in plantation-mcp uses singleton channel pattern (Story 0.6.3), When I implement `CollectionGrpcClient`, Then it follows the same pattern: lazy channel initialization, reuse across calls, reset on error.

3. **AC3: Retry Logic with Tenacity** - Given gRPC calls can fail transiently, When a call fails with `UNAVAILABLE` or `DEADLINE_EXCEEDED`, Then Tenacity retries 3 times with exponential backoff (1-10s), And raises clear error after exhaustion.

4. **AC4: Returns Pydantic Document Model** - Given Collection converters exist in `fp_common.converters.collection_converters` (Story 0.6.11), When `get_document()` returns, Then it returns a Pydantic `Document` model, Not a `dict[str, Any]`.

5. **AC5: Old MongoDB Connection Removed** - Given Plantation Model currently has `collection_mongodb_uri` in settings, When migration is complete, Then `collection_mongodb_uri` and `collection_mongodb_database` are removed from `config.py`, And `collection_app_id` (DAPR app ID) is used instead.

6. **AC6: No Functional Regression** - Given E2E tests exercise quality event processing, When I run the full E2E test suite, Then all tests pass unchanged (behavior identical, only transport changes).

## Tasks / Subtasks

- [ ] **Task 1: Create Collection Proto Converter** (AC: 4)
  - [ ] Add `document_from_proto()` function to `fp_common.converters.collection_converters`
  - [ ] Convert proto `Document` to Pydantic `Document`
  - [ ] Handle nested messages: `RawDocumentRef`, `ExtractionMetadata`, `IngestionMetadata`
  - [ ] Handle timestamp conversion (proto Timestamp → datetime)
  - [ ] Update `converters/__init__.py` with new export

- [ ] **Task 2: Create CollectionGrpcClient** (AC: 1, 2, 3)
  - [ ] Create `services/plantation-model/src/plantation_model/infrastructure/collection_grpc_client.py`
  - [ ] Implement singleton channel pattern (copy from PlantationClient in plantation-mcp)
  - [ ] Add `@retry` decorator with Tenacity (3 attempts, exponential 1-10s)
  - [ ] Implement `get_document(document_id: str, collection_name: str) -> Document`
  - [ ] Use `dapr-app-id` metadata for DAPR service invocation
  - [ ] Add proper exception handling (`DocumentNotFoundError`, `CollectionClientError`)

- [ ] **Task 3: Update Settings** (AC: 5)
  - [ ] Remove `collection_mongodb_uri` from `plantation_model/config.py`
  - [ ] Remove `collection_mongodb_database` from `plantation_model/config.py`
  - [ ] Add `collection_app_id: str = "collection-model"` to settings
  - [ ] Add `collection_grpc_host: str = ""` for direct connection mode (like plantation_grpc_host)

- [ ] **Task 4: Update QualityEventProcessor** (AC: 1)
  - [ ] Import `CollectionGrpcClient` instead of `CollectionClient`
  - [ ] Update instantiation to use gRPC client
  - [ ] Ensure `get_document()` call passes `collection_name` parameter

- [ ] **Task 5: Delete Old CollectionClient** (AC: 5)
  - [ ] Delete `services/plantation-model/src/plantation_model/infrastructure/collection_client.py`
  - [ ] Update `infrastructure/__init__.py` exports if needed

- [ ] **Task 6: Create Unit Tests** (AC: All)
  - [ ] Test `document_from_proto()` converter with sample proto messages
  - [ ] Test `CollectionGrpcClient.get_document()` calls gRPC (mock stub)
  - [ ] Test retry on `UNAVAILABLE` status triggers retry
  - [ ] Test `NOT_FOUND` status raises `DocumentNotFoundError`
  - [ ] Test singleton channel reuse across multiple calls

- [ ] **Task 7: Update E2E Configuration** (AC: 6)
  - [ ] Remove `PLANTATION_COLLECTION_MONGODB_URI` from E2E docker-compose environment
  - [ ] Remove `PLANTATION_COLLECTION_MONGODB_DATABASE` from E2E environment
  - [ ] Verify Collection Model's gRPC port (50051) is accessible to Plantation Model

- [ ] **Task 8: Run E2E Tests** (AC: 6)
  - [ ] Run full E2E suite with `--build` flag
  - [ ] Verify quality event processing tests pass
  - [ ] Capture test output in story file

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.6.13: Replace CollectionClient Direct DB with gRPC"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-6-13-collection-client-grpc
  ```

**Branch name:** `feature/0-6-13-collection-client-grpc`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-6-13-collection-client-grpc`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.6.13: Replace CollectionClient Direct DB with gRPC" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-6-13-collection-client-grpc`

**PR URL:** _______________ (fill in when created)

---

## Implementation Reference

### File Structure

```
libs/fp-common/fp_common/converters/
├── __init__.py                    # Update with document_from_proto export
├── collection_converters.py       # ADD document_from_proto() for proto → pydantic
└── plantation_converters.py       # EXISTING

services/plantation-model/src/plantation_model/
├── config.py                      # MODIFY - Remove mongodb, add collection_app_id
├── infrastructure/
│   ├── __init__.py
│   ├── collection_client.py       # DELETE (old MongoDB client)
│   └── collection_grpc_client.py  # CREATE (new gRPC client)
└── services/
    └── quality_event_processor.py # MODIFY - Use CollectionGrpcClient
```

### Proto Definition Reference

**Collection Service (`proto/collection/v1/collection.proto:20-32`):**

```protobuf
service CollectionService {
  rpc GetDocument(GetDocumentRequest) returns (Document);
  rpc ListDocuments(ListDocumentsRequest) returns (ListDocumentsResponse);
  rpc GetDocumentsByFarmer(GetDocumentsByFarmerRequest) returns (GetDocumentsByFarmerResponse);
  rpc SearchDocuments(SearchDocumentsRequest) returns (SearchDocumentsResponse);
}

message GetDocumentRequest {
  string document_id = 1;
  string collection_name = 2;  // Collection to search in (from source config)
}
```

### CollectionGrpcClient Pattern (based on PlantationClient)

```python
# services/plantation-model/src/plantation_model/infrastructure/collection_grpc_client.py
"""Collection Model gRPC client for fetching documents.

Story 0.6.13: Replaces direct MongoDB access with gRPC via DAPR.
ADR-010/011: Inter-service communication via DAPR service invocation.
"""

import grpc
import structlog
from fp_common.converters import document_from_proto
from fp_common.models import Document
from fp_proto.collection.v1 import collection_pb2, collection_pb2_grpc
from plantation_model.config import settings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


class DocumentNotFoundError(Exception):
    """Raised when a document is not found."""

    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class CollectionClientError(Exception):
    """Raised when a Collection Model client operation fails."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        self.cause = cause
        super().__init__(message)


class CollectionGrpcClient:
    """Client for Collection Model service via gRPC.

    Uses DAPR sidecar for service discovery when deployed.
    Follows singleton channel pattern (ADR-005).

    Note:
        Returns Pydantic Document model, not dict.
        Call model.model_dump() at serialization boundary if needed.
    """

    def __init__(self, channel: grpc.aio.Channel | None = None) -> None:
        """Initialize the client.

        Args:
            channel: Optional gRPC channel. If not provided, creates one to DAPR sidecar.
        """
        self._channel = channel
        self._stub: collection_pb2_grpc.CollectionServiceStub | None = None

    async def _get_stub(self) -> collection_pb2_grpc.CollectionServiceStub:
        """Get or create the gRPC stub (singleton pattern)."""
        if self._stub is None:
            if self._channel is None:
                if settings.collection_grpc_host:
                    # Direct connection to Collection Model gRPC server
                    target = settings.collection_grpc_host
                    logger.info("Connecting directly to Collection Model gRPC", target=target)
                else:
                    # Connect via DAPR sidecar (localhost:50001 is DAPR's gRPC port)
                    dapr_grpc_port = 50001
                    target = f"localhost:{dapr_grpc_port}"
                    logger.info(
                        "Connecting via DAPR service invocation",
                        target=target,
                        app_id=settings.collection_app_id,
                    )
                self._channel = grpc.aio.insecure_channel(target)
            self._stub = collection_pb2_grpc.CollectionServiceStub(self._channel)
        return self._stub

    def _get_metadata(self) -> list[tuple[str, str]]:
        """Get gRPC call metadata for DAPR service invocation."""
        if settings.collection_grpc_host:
            # Direct connection - no DAPR metadata needed
            return []
        # DAPR service invocation - add app-id metadata
        return [("dapr-app-id", settings.collection_app_id)]

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_document(self, document_id: str, collection_name: str = "quality_documents") -> Document:
        """Get a document by ID from Collection Model.

        Args:
            document_id: The document's unique identifier.
            collection_name: Collection to search in (default: quality_documents).

        Returns:
            Document Pydantic model.

        Raises:
            DocumentNotFoundError: If document not found.
            CollectionClientError: If gRPC call fails after retries.
        """
        try:
            stub = await self._get_stub()
            request = collection_pb2.GetDocumentRequest(
                document_id=document_id,
                collection_name=collection_name,
            )

            logger.debug(
                "Fetching document from Collection Model via gRPC",
                document_id=document_id,
                collection_name=collection_name,
            )

            response = await stub.GetDocument(request, metadata=self._get_metadata())

            logger.info(
                "Document retrieved from Collection Model",
                document_id=document_id,
                source_id=response.ingestion.source_id,
            )

            return document_from_proto(response)

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                logger.warning("Document not found in Collection Model", document_id=document_id)
                raise DocumentNotFoundError(document_id) from e
            logger.error(
                "gRPC call to Collection Model failed",
                document_id=document_id,
                status_code=e.code().name,
                details=e.details(),
            )
            # Reset stub to force reconnection on next call
            self._stub = None
            self._channel = None
            raise CollectionClientError(f"Failed to fetch document {document_id}", cause=e) from e

    async def close(self) -> None:
        """Close the gRPC channel."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
            logger.info("Collection gRPC client connection closed")
```

### Proto-to-Pydantic Converter Pattern

```python
# Add to libs/fp-common/fp_common/converters/collection_converters.py

from fp_proto.collection.v1 import collection_pb2
from google.protobuf.timestamp_pb2 import Timestamp

def _proto_timestamp_to_datetime(ts: Timestamp) -> datetime:
    """Convert protobuf Timestamp to Python datetime."""
    if ts.seconds == 0 and ts.nanos == 0:
        return datetime.now(UTC)
    return ts.ToDatetime(tzinfo=UTC)


def document_from_proto(proto: collection_pb2.Document) -> Document:
    """Convert proto Document to Pydantic Document model.

    Args:
        proto: Proto Document message from Collection Model gRPC.

    Returns:
        Document Pydantic model.
    """
    return Document(
        document_id=proto.document_id,
        raw_document=RawDocumentRef(
            blob_container=proto.raw_document.blob_container,
            blob_path=proto.raw_document.blob_path,
            content_hash=proto.raw_document.content_hash,
            size_bytes=proto.raw_document.size_bytes,
            stored_at=_proto_timestamp_to_datetime(proto.raw_document.stored_at),
        ),
        extraction=ExtractionMetadata(
            ai_agent_id=proto.extraction.ai_agent_id,
            extraction_timestamp=_proto_timestamp_to_datetime(proto.extraction.extraction_timestamp),
            confidence=proto.extraction.confidence,
            validation_passed=proto.extraction.validation_passed,
            validation_warnings=list(proto.extraction.validation_warnings),
        ),
        ingestion=IngestionMetadata(
            ingestion_id=proto.ingestion.ingestion_id,
            source_id=proto.ingestion.source_id,
            received_at=_proto_timestamp_to_datetime(proto.ingestion.received_at),
            processed_at=_proto_timestamp_to_datetime(proto.ingestion.processed_at),
        ),
        extracted_fields=dict(proto.extracted_fields),  # Proto map → dict
        linkage_fields=dict(proto.linkage_fields),
        created_at=_proto_timestamp_to_datetime(proto.created_at),
    )
```

### Settings Update Pattern

```python
# services/plantation-model/src/plantation_model/config.py

# REMOVE these:
# collection_mongodb_uri: str = "mongodb://localhost:27017"
# collection_mongodb_database: str = "collection"

# ADD these:
collection_app_id: str = "collection-model"  # DAPR app ID for service invocation
collection_grpc_host: str = ""  # Direct gRPC host (empty = use DAPR)
```

### E2E Environment Update

```yaml
# tests/e2e/infrastructure/docker-compose.e2e.yaml
# In plantation-model environment section:

# REMOVE:
# - PLANTATION_COLLECTION_MONGODB_URI=...
# - PLANTATION_COLLECTION_MONGODB_DATABASE=...

# Collection Model gRPC is accessed via DAPR, no direct config needed
# DAPR sidecar handles routing to collection-model:50051
```

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="libs/fp-common:libs/fp-proto/src:services/plantation-model/src:." pytest tests/unit/plantation_model/infrastructure/ -v
```
**Output:**
```
(paste test summary here - e.g., "15 passed in 1.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure with --build (MANDATORY)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
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
git push origin feature/0-6-13-collection-client-grpc

# Wait ~30s, then check CI status
gh run list --branch feature/0-6-13-collection-client-grpc --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## E2E Story Checklist

**Read First:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Pre-Implementation
- [ ] Read and understood `E2E-TESTING-MENTAL-MODEL.md`
- [ ] Understand: Proto = source of truth, tests verify (not define) behavior

### This Story's E2E Impact

**This story has LOW E2E impact:**
- No API changes (internal refactoring only)
- Document retrieval behavior should be IDENTICAL
- Existing E2E tests should pass unchanged

The refactoring is **transport-level** - gRPC via DAPR replaces direct MongoDB, but the data returned is identical.

### Production Code Changes (if any)

| File:Lines | What Changed | Why (with evidence) | Type |
|------------|--------------|---------------------|------|
| collection_client.py | DELETED | ADR-010: No direct DB access | Refactor |
| collection_grpc_client.py | CREATED | ADR-010: gRPC via DAPR | Refactor |
| config.py | Removed mongodb settings, added dapr settings | ADR-010 | Refactor |

---

## Dev Notes

### Architecture Context

**Wave 4 Overview:**
1. **Story 0.6.11** - Create converters in fp-common - DONE
2. **Story 0.6.12** - MCP clients use converters, return Pydantic - DONE
3. **Story 0.6.13 (this)** - Replace CollectionClient direct DB with gRPC
4. **Story 0.6.14** - Replace custom DaprPubSubClient with SDK

This story **enforces domain boundaries** by replacing a cross-service database connection with proper gRPC service invocation.

### Key Technical Decisions

1. **Use existing GetDocument RPC** - Collection Model already exposes `GetDocument` (Story 0.5.1a). No new gRPC method needed.

2. **Singleton channel pattern** - Matches Stories 0.6.3/0.6.4 and PlantationClient in plantation-mcp. Avoids per-request channel creation overhead.

3. **Retry on AioRpcError** - Tenacity catches gRPC errors for automatic retry. Resets channel on failure to force reconnection.

4. **collection_name parameter** - GetDocument requires `collection_name`. Default to "quality_documents" for backward compatibility with existing calls.

5. **Proto converter in fp-common** - Document model already exists in `fp_common.models.document`. Add converter `document_from_proto()` to `collection_converters.py`.

### Learnings from Previous Stories

**From Story 0.6.3/0.6.4 (gRPC Retry):**
- Singleton channel pattern with lazy initialization
- Reset `_stub = None` and `_channel = None` on error to force reconnection
- Tenacity retry with exponential backoff (1-10s)

**From Story 0.6.11/0.6.12 (Proto-to-Pydantic):**
- Converters in `fp_common.converters/`
- Import pattern: `from fp_common.converters import document_from_proto`
- Timestamp handling: `_proto_timestamp_to_datetime()`

**From Story 0.5.1a (Collection gRPC Service):**
- `CollectionService.GetDocument` requires `document_id` AND `collection_name`
- Returns `NOT_FOUND` status code if document doesn't exist
- Document proto uses `map<string, string>` for `extracted_fields` and `linkage_fields`

### DAPR Service Invocation Pattern

**Key insight from ADR-010:**
```python
# Connect to DAPR sidecar's gRPC port (50001), NOT the target service directly
channel = grpc.aio.insecure_channel("localhost:50001")
stub = CollectionServiceStub(channel)

# DAPR routes based on metadata header
metadata = [("dapr-app-id", "collection-model")]
response = await stub.GetDocument(request, metadata=metadata)
```

The `dapr-app-id` metadata tells DAPR which service to route to. DAPR handles service discovery and load balancing.

### Files to Modify

**NEW FILES:**
- `services/plantation-model/src/plantation_model/infrastructure/collection_grpc_client.py`
- `tests/unit/plantation_model/infrastructure/test_collection_grpc_client.py`

**MODIFIED FILES:**
- `libs/fp-common/fp_common/converters/collection_converters.py` (add `document_from_proto`)
- `libs/fp-common/fp_common/converters/__init__.py` (export `document_from_proto`)
- `services/plantation-model/src/plantation_model/config.py` (remove mongodb, add dapr)
- `services/plantation-model/src/plantation_model/services/quality_event_processor.py` (use new client)
- `tests/e2e/infrastructure/docker-compose.e2e.yaml` (remove mongodb env vars)

**DELETED FILES:**
- `services/plantation-model/src/plantation_model/infrastructure/collection_client.py`

### Anti-Patterns to Avoid

1. **DO NOT access other service's MongoDB** - Use gRPC service invocation
2. **DO NOT create new channel per request** - Use singleton pattern
3. **DO NOT skip retry logic** - Transient errors are common in distributed systems
4. **DO NOT return dict** - Return Pydantic model, serialize at boundary

### Potential Gotchas

1. **collection_name is REQUIRED** - The proto requires it, default to "quality_documents"
2. **Proto map fields** - `extracted_fields` and `linkage_fields` are `map<string, string>` in proto, convert with `dict(proto.extracted_fields)`
3. **Timestamp handling** - Use `ToDatetime(tzinfo=UTC)` to get timezone-aware datetime
4. **E2E network** - Ensure plantation-model can reach collection-model via DAPR in docker-compose network

### References

- [ADR-010: DAPR Patterns](../architecture/adr/ADR-010-dapr-patterns-configuration.md)
- [ADR-011: Service Architecture](../architecture/adr/ADR-011-grpc-fastapi-dapr-architecture.md)
- [ADR-005: gRPC Client Retry Strategy](../architecture/adr/ADR-005-grpc-client-retry-strategy.md)
- [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
- [Story 0.6.3: gRPC Retry - AiModelClient](./0-6-3-grpc-retry-ai-model-client.md) - DONE
- [Story 0.6.12: MCP Clients Return Pydantic](./0-6-12-mcp-clients-pydantic-models.md) - DONE
- [project-context.md](../project-context.md) - Critical rules reference
- [Existing PlantationClient](../../mcp-servers/plantation-mcp/src/plantation_mcp/infrastructure/plantation_client.py) - Reference pattern

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

**Deleted:**
- (list deleted files)
