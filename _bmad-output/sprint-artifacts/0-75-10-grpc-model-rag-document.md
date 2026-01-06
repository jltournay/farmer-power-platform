# Story 0.75.10: gRPC Model for RAG Document

**Status:** in-progress
**GitHub Issue:** #117

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want gRPC service definitions for RAG document management,
So that documents can be managed via API.

## Acceptance Criteria

1. **AC1: Proto RAGDocument Message** - Add `RAGDocument` message to `proto/ai_model/v1/ai_model.proto` matching the Pydantic model schema from Story 0.75.9
2. **AC2: Proto RAGDocumentMetadata Message** - Add `RAGDocumentMetadata` message with author, source, region, season, tags fields
3. **AC3: Proto SourceFile Message** - Add `SourceFile` message for extraction metadata
4. **AC4: Proto RAGDocumentService** - Add `RAGDocumentService` with CRUD RPCs: CreateDocument, GetDocument, UpdateDocument, DeleteDocument
5. **AC5: Proto ListDocuments RPC** - Add ListDocuments RPC with pagination and filtering (domain, status, author)
6. **AC6: Proto SearchDocuments RPC** - Add SearchDocuments RPC for full-text search capability
7. **AC7: Proto Lifecycle RPCs** - Add lifecycle management RPCs: StageDocument, ActivateDocument, ArchiveDocument, RollbackDocument
8. **AC8: gRPC Service Implementation** - Create `RagDocumentServiceServicer` class in `services/ai-model/src/ai_model/api/rag_document_service.py`
9. **AC9: CRUD Operations** - Implement CreateDocument, GetDocument (by ID or latest), UpdateDocument, DeleteDocument using RagDocumentRepository
10. **AC10: Listing Operations** - Implement ListDocuments with pagination and filtering, SearchDocuments
11. **AC11: Lifecycle Operations** - Implement StageDocument, ActivateDocument, ArchiveDocument, RollbackDocument with proper state transitions
12. **AC12: DAPR Integration** - Service is accessible via DAPR service invocation pattern
13. **AC13: Proto Generation** - Run proto generation script and verify fp-proto package exports new messages
14. **AC14: gRPC Server Registration** - Register RagDocumentServiceServicer in grpc_server.py
15. **AC15: Unit Tests** - Minimum 15 unit tests covering service methods and error handling
16. **AC16: CI Passes** - All lint checks and unit tests pass in CI

## Tasks / Subtasks

- [ ] **Task 1: Add Proto Definitions** (AC: #1, #2, #3, #4, #5, #6, #7)
  - [ ] Edit `proto/ai_model/v1/ai_model.proto` - add RAGDocumentService
  - [ ] Add `RAGDocument` message with all fields from Pydantic model
  - [ ] Add `RAGDocumentMetadata` message
  - [ ] Add `SourceFile` message with extraction metadata fields
  - [ ] Add CRUD RPCs: CreateDocument, GetDocument, UpdateDocument, DeleteDocument
  - [ ] Add ListDocumentsRequest/Response with pagination
  - [ ] Add SearchDocumentsRequest/Response
  - [ ] Add lifecycle RPCs: StageDocument, ActivateDocument, ArchiveDocument, RollbackDocument

- [ ] **Task 2: Generate Proto Stubs** (AC: #13)
  - [ ] Run proto generation: `scripts/generate-proto.sh` or equivalent
  - [ ] Verify `libs/fp-proto/src/fp_proto/ai_model/v1/` contains updated stubs
  - [ ] Verify imports work: `from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc`

- [ ] **Task 3: Create RagDocumentServiceServicer** (AC: #8, #9, #10, #11)
  - [ ] Create `services/ai-model/src/ai_model/api/rag_document_service.py`
  - [ ] Implement class extending `ai_model_pb2_grpc.RAGDocumentServiceServicer`
  - [ ] Implement CreateDocument - auto-generate document_id (UUID4) if not provided, version=1, status=draft
  - [ ] Implement GetDocument - if version specified use `get_by_version()`, else use `get_active()` (returns active version, NOT highest version)
  - [ ] Implement UpdateDocument - creates new version (version = max_version + 1), copies document_id
  - [ ] Implement DeleteDocument - soft delete (archives all versions via `list_versions()` + update loop)
  - [ ] Implement ListDocuments - pagination (page 1-indexed, page_size default=20, max=100), use skip/limit
  - [ ] Implement SearchDocuments - use MongoDB $regex on title/content (NOT text index for MVP)
  - [ ] Implement StageDocument - transition draft → staged (validate current status)
  - [ ] Implement ActivateDocument - transition staged → active (archive current active first)
  - [ ] Implement ArchiveDocument - transition any → archived
  - [ ] Implement RollbackDocument - create new draft version copying content from specified old version

- [ ] **Task 4: Register Service in gRPC Server** (AC: #12, #14)
  - [ ] Edit `services/ai-model/src/ai_model/api/grpc_server.py`
  - [ ] Add import for RagDocumentServiceServicer
  - [ ] Register servicer with gRPC server in `serve()` function
  - [ ] Verify DAPR invocation pattern works (metadata: dapr-app-id)

- [ ] **Task 5: Update Package Exports** (AC: #8)
  - [ ] Update `services/ai-model/src/ai_model/api/__init__.py` - export RagDocumentServiceServicer

- [ ] **Task 6: Unit Tests** (AC: #15)
  - [ ] Create `tests/unit/ai_model/test_rag_document_service.py`
  - [ ] Test CreateDocument creates document correctly - 2 tests
  - [ ] Test GetDocument returns correct version - 2 tests
  - [ ] Test UpdateDocument creates new version - 2 tests
  - [ ] Test DeleteDocument archives document - 1 test
  - [ ] Test ListDocuments with filters and pagination - 3 tests
  - [ ] Test SearchDocuments returns matching documents - 2 tests
  - [ ] Test lifecycle transitions (StageDocument, ActivateDocument, etc.) - 3 tests

- [ ] **Task 7: CI Verification** (AC: #16)
  - [ ] Run lint checks: `ruff check . && ruff format --check .`
  - [ ] Run unit tests with correct PYTHONPATH
  - [ ] Push to feature branch and verify CI passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.10: gRPC Model for RAG Document"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-10-grpc-model-rag-document
  ```

**Branch name:** `feature/0-75-10-grpc-model-rag-document`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-10-grpc-model-rag-document`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.10: gRPC Model for RAG Document" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-10-grpc-model-rag-document`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/test_rag_document_service.py -v
```
**Output:**
```
(paste test summary here - e.g., "15 passed in 2.34s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure (--build is MANDATORY)
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
git push origin feature/0-75-10-grpc-model-rag-document

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-10-grpc-model-rag-document --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### CRITICAL: Follow Existing Patterns - DO NOT Reinvent

**This story follows the EXACT same pattern as Story 0.75.5 (CostService). Reuse patterns from:**

| Component | Reference | Pattern |
|-----------|-----------|---------|
| Proto service definition | `proto/ai_model/v1/ai_model.proto` (CostService) | Service with request/response messages |
| gRPC servicer implementation | `services/ai-model/src/ai_model/api/cost_service.py` | Async servicer with repository dependency |
| gRPC server registration | `services/ai-model/src/ai_model/api/grpc_server.py` | Server setup pattern |
| Unit test pattern | `tests/unit/ai_model/` | Mock repository, test service methods |

### Architecture Reference: RAG Document API

**From `_bmad-output/architecture/ai-model-architecture/rag-document-api.md`:**

The gRPC API is fully defined. Key extracts:

```protobuf
service RAGDocumentService {
  // CRUD Operations
  rpc CreateDocument(CreateDocumentRequest) returns (CreateDocumentResponse);
  rpc GetDocument(GetDocumentRequest) returns (RAGDocument);
  rpc UpdateDocument(UpdateDocumentRequest) returns (RAGDocument);
  rpc DeleteDocument(DeleteDocumentRequest) returns (DeleteDocumentResponse);

  // List & Search
  rpc ListDocuments(ListDocumentsRequest) returns (ListDocumentsResponse);
  rpc SearchDocuments(SearchDocumentsRequest) returns (SearchDocumentsResponse);

  // Lifecycle Management
  rpc StageDocument(StageDocumentRequest) returns (RAGDocument);
  rpc ActivateDocument(ActivateDocumentRequest) returns (RAGDocument);
  rpc ArchiveDocument(ArchiveDocumentRequest) returns (RAGDocument);
  rpc RollbackDocument(RollbackDocumentRequest) returns (RAGDocument);
}
```

### Story 0.75.10 Scope Clarification

**This story handles document METADATA only:**
- gRPC service for CRUD operations on RAG documents
- Status lifecycle management (draft → staged → active → archived)
- Listing and searching documents

**NOT in scope (separate stories):**
- PDF ingestion → Story 0.75.10b
- Azure Document Intelligence → Story 0.75.10c
- Semantic chunking → Story 0.75.10d
- Vectorization → Stories 0.75.12-13b
- A/B testing RPCs → Can be deferred (marked optional in architecture)

### Previous Story Intelligence (Story 0.75.9)

**From completed Story 0.75.9:**
1. **Pydantic models exist** at `services/ai-model/src/ai_model/domain/rag_document.py`:
   - `RagDocument`, `RagChunk`, `SourceFile`, `RAGDocumentMetadata`
   - `RagDocumentStatus` enum: draft, staged, active, archived
   - `KnowledgeDomain` enum: plant_diseases, tea_cultivation, weather_patterns, quality_standards, regional_context
   - `ExtractionMethod` enum: manual, text_extraction, azure_doc_intel, vision_llm
   - `FileType` enum: pdf, docx, md, txt

2. **Repository exists** at `services/ai-model/src/ai_model/infrastructure/repositories/rag_document_repository.py`:
   - `RagDocumentRepository` with CRUD + specialized queries
   - Methods: `get_active()`, `get_by_version()`, `list_versions()`, `list_by_domain()`, `list_by_status()`

3. **Architecture deviation documented**: Added `id` field to `RagDocument` (format: `{document_id}:v{version}`) for MongoDB `_id` mapping

4. **GetDocument semantics clarification**:
   - `GetDocument(document_id)` without version → uses `get_active()` (returns document with status=ACTIVE)
   - `GetDocument(document_id, version=N)` → uses `get_by_version(document_id, N)`
   - If no active version exists and no version specified → return NOT_FOUND
   - This means "latest" = "currently active", NOT "highest version number"

### File Structure After Story

```
proto/ai_model/v1/
└── ai_model.proto                    # MODIFIED - add RAGDocumentService

services/ai-model/
├── src/ai_model/
│   ├── api/
│   │   ├── __init__.py               # MODIFIED - add export
│   │   ├── cost_service.py           # EXISTING - reference pattern
│   │   ├── grpc_server.py            # MODIFIED - register service
│   │   └── rag_document_service.py   # NEW - RagDocumentServiceServicer
│   ├── domain/
│   │   └── rag_document.py           # EXISTING from 0.75.9
│   └── infrastructure/repositories/
│       └── rag_document_repository.py # EXISTING from 0.75.9
└── ...

libs/fp-proto/src/fp_proto/ai_model/v1/
├── ai_model_pb2.py                   # REGENERATED
└── ai_model_pb2_grpc.py              # REGENERATED

tests/unit/ai_model/
└── test_rag_document_service.py      # NEW - service tests
```

### Proto Message Design

**Key design decisions matching existing CostService pattern:**

> **ARCHITECTURE DEVIATION NOTE:** The proto includes `id` field (field 1) which is NOT in the architecture spec but IS required by our Pydantic model (Story 0.75.9). This field provides MongoDB `_id` mapping with format `{document_id}:v{version}`.

```protobuf
// In proto/ai_model/v1/ai_model.proto

message RAGDocument {
  string id = 1;                                // {document_id}:v{version} - DEVIATION from arch spec
  string document_id = 2;                       // Stable ID across versions
  int32 version = 3;
  string title = 4;
  string domain = 5;                            // String value from KnowledgeDomain enum
  string content = 6;                           // Markdown text
  string status = 7;                            // String value from RagDocumentStatus enum
  RAGDocumentMetadata metadata = 8;
  optional SourceFile source_file = 9;
  optional string change_summary = 10;
  google.protobuf.Timestamp created_at = 11;
  google.protobuf.Timestamp updated_at = 12;
  optional string pinecone_namespace = 13;
  repeated string pinecone_ids = 14;
  optional string content_hash = 15;
}

message RAGDocumentMetadata {
  string author = 1;
  optional string source = 2;
  optional string region = 3;
  optional string season = 4;
  repeated string tags = 5;
}

message SourceFile {
  string filename = 1;
  string file_type = 2;                         // Allowed values: "pdf", "docx", "md", "txt" (match FileType enum)
  string blob_path = 3;
  int64 file_size_bytes = 4;
  optional string extraction_method = 5;        // Allowed: "manual", "text_extraction", "azure_doc_intel", "vision_llm"
  optional float extraction_confidence = 6;
  optional int32 page_count = 7;
}
```

**Proto String ↔ Pydantic Enum Mapping:**
| Proto Field | Type | Pydantic Enum | Allowed Values |
|-------------|------|---------------|----------------|
| `domain` | string | `KnowledgeDomain` | plant_diseases, tea_cultivation, weather_patterns, quality_standards, regional_context |
| `status` | string | `RagDocumentStatus` | draft, staged, active, archived |
| `file_type` | string | `FileType` | pdf, docx, md, txt |
| `extraction_method` | string | `ExtractionMethod` | manual, text_extraction, azure_doc_intel, vision_llm |

### Lifecycle State Transitions

```
                    ┌─────────────────────────────────────────────┐
                    │              LIFECYCLE STATES                │
                    ├─────────────────────────────────────────────┤
                    │                                             │
                    │    CreateDocument()                         │
                    │          │                                  │
                    │          ▼                                  │
                    │    ┌──────────┐                             │
                    │    │  DRAFT   │                             │
                    │    └────┬─────┘                             │
                    │         │                                   │
                    │    StageDocument()                          │
                    │         │                                   │
                    │         ▼                                   │
                    │    ┌──────────┐                             │
                    │    │  STAGED  │◄── RollbackDocument()       │
                    │    └────┬─────┘         │                   │
                    │         │               │                   │
                    │    ActivateDocument()   │                   │
                    │    (archives current    │                   │
                    │     active version)     │                   │
                    │         │               │                   │
                    │         ▼               │                   │
                    │    ┌──────────┐         │                   │
                    │    │  ACTIVE  │─────────┘                   │
                    │    └────┬─────┘                             │
                    │         │                                   │
                    │    ArchiveDocument()                        │
                    │    (or new version activated)               │
                    │         │                                   │
                    │         ▼                                   │
                    │    ┌──────────┐                             │
                    │    │ ARCHIVED │                             │
                    │    └──────────┘                             │
                    │                                             │
                    └─────────────────────────────────────────────┘
```

**Transition Rules:**
- `StageDocument`: draft → staged (only from draft)
- `ActivateDocument`: staged → active (archives current active version first)
- `ArchiveDocument`: any → archived
- `RollbackDocument`: creates new draft version from specified old version

**gRPC Error Codes for Invalid Transitions:**
```python
# Invalid transition → FAILED_PRECONDITION
# Example error messages:
# - "Cannot stage document: current status is 'active', expected 'draft'"
# - "Cannot activate document: current status is 'draft', expected 'staged'"
# - "Cannot rollback: version 5 not found for document 'disease-guide'"

await context.abort(
    grpc.StatusCode.FAILED_PRECONDITION,
    f"Cannot stage document: current status is '{doc.status.value}', expected 'draft'"
)
```

### gRPC Service Implementation Pattern

Follow the CostService pattern exactly:

```python
# services/ai-model/src/ai_model/api/rag_document_service.py

from datetime import UTC, datetime
import grpc
import structlog
from ai_model.domain.rag_document import RagDocument, RagDocumentStatus, KnowledgeDomain
from ai_model.infrastructure.repositories import RagDocumentRepository
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc
from google.protobuf import timestamp_pb2

logger = structlog.get_logger(__name__)


def _datetime_to_timestamp(dt: datetime) -> timestamp_pb2.Timestamp:
    """Convert datetime to protobuf Timestamp."""
    ts = timestamp_pb2.Timestamp()
    ts.FromDatetime(dt)
    return ts


def _pydantic_to_proto(doc: RagDocument) -> ai_model_pb2.RAGDocument:
    """Convert Pydantic RagDocument to Proto RAGDocument."""
    proto_doc = ai_model_pb2.RAGDocument(
        id=doc.id,
        document_id=doc.document_id,
        version=doc.version,
        title=doc.title,
        domain=doc.domain.value,  # Enum → string
        content=doc.content,
        status=doc.status.value,  # Enum → string
        change_summary=doc.change_summary or "",
        pinecone_namespace=doc.pinecone_namespace or "",
        pinecone_ids=doc.pinecone_ids,
        content_hash=doc.content_hash or "",
    )
    proto_doc.created_at.FromDatetime(doc.created_at)
    proto_doc.updated_at.FromDatetime(doc.updated_at)
    # Handle nested messages...
    return proto_doc


def _proto_to_pydantic(
    request: ai_model_pb2.CreateDocumentRequest,
    document_id: str | None = None,
) -> RagDocument:
    """Convert Proto CreateDocumentRequest to Pydantic RagDocument.

    Used for CreateDocument and UpdateDocument operations.
    If document_id not provided, generates UUID4.
    """
    import uuid
    doc_id = document_id or str(uuid.uuid4())
    version = 1  # New documents start at version 1

    return RagDocument(
        id=f"{doc_id}:v{version}",
        document_id=doc_id,
        version=version,
        title=request.title,
        domain=KnowledgeDomain(request.domain),  # String → enum
        content=request.content,
        status=RagDocumentStatus.DRAFT,  # Always start as draft
        metadata=RAGDocumentMetadata(
            author=request.metadata.author,
            source=request.metadata.source or None,
            region=request.metadata.region or None,
            season=request.metadata.season or None,
            tags=list(request.metadata.tags),
        ),
    )


class RAGDocumentServiceServicer(ai_model_pb2_grpc.RAGDocumentServiceServicer):
    """gRPC RAGDocumentService implementation."""

    def __init__(self, repository: RagDocumentRepository) -> None:
        self._repository = repository
        logger.info("RAGDocumentService initialized")

    async def GetDocument(
        self,
        request: ai_model_pb2.GetDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.RAGDocument:
        """Get document by ID or latest version."""
        try:
            # Implementation
            pass
        except Exception as e:
            logger.error("GetDocument failed", error=str(e))
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise
```

### gRPC Server Registration Pattern

```python
# In services/ai-model/src/ai_model/api/grpc_server.py

from ai_model.api.rag_document_service import RAGDocumentServiceServicer
from ai_model.infrastructure.repositories import RagDocumentRepository

async def serve(settings: Settings, db: AsyncIOMotorDatabase) -> None:
    server = grpc.aio.server()

    # Existing services
    cost_repo = LlmCostEventRepository(db)
    ai_model_pb2_grpc.add_CostServiceServicer_to_server(
        CostServiceServicer(cost_repo, budget_monitor), server
    )

    # NEW: Add RAGDocumentService
    rag_doc_repo = RagDocumentRepository(db)
    ai_model_pb2_grpc.add_RAGDocumentServiceServicer_to_server(
        RAGDocumentServiceServicer(rag_doc_repo), server
    )

    # ... rest of server setup
```

### Testing Strategy

**Unit Tests Required (minimum 15 tests):**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_rag_document_service.py` | 15+ | All service methods |

**Test Categories:**
- CreateDocument: 2 tests (success, validation error)
- GetDocument: 2 tests (by ID, by version)
- UpdateDocument: 2 tests (creates new version, preserves old)
- DeleteDocument: 1 test (archives all versions)
- ListDocuments: 3 tests (pagination, domain filter, status filter)
- SearchDocuments: 2 tests (title match, content match)
- Lifecycle transitions: 3 tests (stage, activate with archive, rollback)

**Mock Strategy:**
- Mock `RagDocumentRepository` using `unittest.mock.AsyncMock`
- DO NOT mock gRPC context - use actual `grpc.aio.ServicerContext` stub

### Pagination Implementation (ListDocuments)

```python
# Pagination defaults and validation:
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

async def ListDocuments(self, request, context):
    page = max(1, request.page or 1)  # 1-indexed, minimum 1
    page_size = min(MAX_PAGE_SIZE, request.page_size or DEFAULT_PAGE_SIZE)
    skip = (page - 1) * page_size

    # Build query filter
    query = {}
    if request.domain:
        query["domain"] = request.domain
    if request.status:
        query["status"] = request.status
    if request.author:
        query["metadata.author"] = request.author

    # Execute with skip/limit (repository needs new method or direct collection access)
    cursor = self._repository._collection.find(query).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)
    total_count = await self._repository._collection.count_documents(query)

    return ai_model_pb2.ListDocumentsResponse(
        documents=[_pydantic_to_proto(RagDocument.model_validate(d)) for d in docs],
        total_count=total_count,
        page=page,
        page_size=page_size,
    )
```

### SearchDocuments Implementation (MVP - $regex)

```python
# For MVP, use $regex (simple, no index required)
# Text index can be added in optimization story if needed

async def SearchDocuments(self, request, context):
    query = request.query
    filter_query = {
        "$or": [
            {"title": {"$regex": query, "$options": "i"}},      # Case-insensitive
            {"content": {"$regex": query, "$options": "i"}},
        ]
    }
    if request.domain:
        filter_query["domain"] = request.domain
    if request.status:
        filter_query["status"] = request.status

    limit = min(100, request.limit or 20)
    cursor = self._repository._collection.find(filter_query).limit(limit)
    docs = await cursor.to_list(length=limit)

    return ai_model_pb2.SearchDocumentsResponse(
        documents=[_pydantic_to_proto(RagDocument.model_validate(d)) for d in docs]
    )
```

### A/B Testing RPCs (DEFERRED - Return UNIMPLEMENTED)

The architecture spec includes A/B testing RPCs (StartABTest, GetABTestStatus, EndABTest). These are **deferred** to a future story. If called, return UNIMPLEMENTED:

```python
async def StartABTest(self, request, context):
    await context.abort(
        grpc.StatusCode.UNIMPLEMENTED,
        "A/B testing RPCs are not implemented in this version"
    )

# Same for GetABTestStatus and EndABTest
```

### What This Story Does NOT Include

| Not in Scope | Implemented In |
|--------------|----------------|
| PDF extraction logic | Story 0.75.10b |
| Azure Document Intelligence | Story 0.75.10c |
| Semantic chunking implementation | Story 0.75.10d |
| CLI for RAG documents | Story 0.75.11 |
| Vectorization/Pinecone integration | Stories 0.75.12-13b |
| A/B testing RPCs | Deferred (return UNIMPLEMENTED if called) |
| RagChunk repository | Story 0.75.10d |

**This story provides the gRPC API layer only. PDF ingestion comes in Story 0.75.10b.**

### Dependencies

**Already installed (from previous stories):**
- `pydantic` ^2.0
- `motor` (async MongoDB)
- `grpcio`
- `grpcio-tools`
- `structlog`

**No new dependencies required.**

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Returning dicts from service methods | Return Proto messages |
| Synchronous repository calls | Use `await` for all repository methods |
| Bare `except:` clauses | Catch specific exceptions, log, and abort |
| Direct MongoDB access in service | Use RagDocumentRepository |
| Hardcoding status/domain strings | Use enum values from Pydantic models |
| Missing error handling | Always handle exceptions with proper gRPC status codes |

### gRPC Error Handling Pattern

```python
async def GetDocument(self, request, context):
    try:
        # Validation
        if not request.document_id:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "document_id is required"
            )
            return  # Never reached, but for type checker

        # Business logic
        doc = await self._repository.get_active(request.document_id)
        if doc is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Document not found: {request.document_id}"
            )
            return

        return _pydantic_to_proto(doc)

    except Exception as e:
        logger.error("GetDocument failed", error=str(e), document_id=request.document_id)
        await context.abort(grpc.StatusCode.INTERNAL, str(e))
        raise  # For type checker; abort() raises
```

### Proto Generation Script

```bash
# Generate proto stubs (run from project root)
python -m grpc_tools.protoc \
  -I=proto \
  --python_out=libs/fp-proto/src \
  --grpc_python_out=libs/fp-proto/src \
  proto/ai_model/v1/ai_model.proto

# Or use existing script if available
./scripts/generate-proto.sh
```

### References

- [Source: `proto/ai_model/v1/ai_model.proto`] - Existing proto file to extend
- [Source: `services/ai-model/src/ai_model/api/cost_service.py`] - Reference gRPC service pattern
- [Source: `services/ai-model/src/ai_model/api/grpc_server.py`] - Server registration pattern
- [Source: `services/ai-model/src/ai_model/domain/rag_document.py`] - Pydantic models (Story 0.75.9)
- [Source: `services/ai-model/src/ai_model/infrastructure/repositories/rag_document_repository.py`] - Repository (Story 0.75.9)
- [Source: `_bmad-output/architecture/ai-model-architecture/rag-document-api.md`] - Complete API specification
- [Source: `_bmad-output/architecture/ai-model-architecture/rag-engine.md`] - RAG engine overview
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md#story-07510`] - Story requirements
- [Source: `_bmad-output/project-context.md`] - Critical rules (gRPC patterns, async requirements)

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
