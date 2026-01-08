# Story 0.75.13c: RAG Vectorization gRPC Wiring

**Status:** backlog
**GitHub Issue:** (to be created)

## Story

As a **developer using the RAG API**,
I want the VectorizationPipeline exposed via gRPC endpoints,
So that documents can be vectorized through the standard API and CLI.

## Context

Story 0.75.13b created the `VectorizationPipeline` orchestration class and proto definitions, but the gRPC service implementation was deferred (Task 6b marked "PENDING SERVICE IMPLEMENTATION"). This story completes the wiring to make vectorization accessible end-to-end.

**Current State:**
- ✅ Proto definitions exist (`VectorizeDocument`, `GetVectorizationJob` RPCs)
- ✅ `VectorizationPipeline` class exists and is tested (29 unit tests)
- ❌ `RAGDocumentServiceServicer` only accepts `RagDocumentRepository`
- ❌ `VectorizeDocument` RPC not implemented
- ❌ `GetVectorizationJob` RPC not implemented
- ❌ CLI `fp-knowledge promote` doesn't trigger vectorization

## Acceptance Criteria

1. **AC1: Dependency Injection** - `RAGDocumentServiceServicer` accepts all required dependencies:
   - `RagDocumentRepository`
   - `RagChunkRepository`
   - `ChunkingWorkflow`
   - `ExtractionWorkflow` (if extraction endpoints need it)
   - `VectorizationPipeline`

2. **AC2: grpc_server.py Wiring** - `GrpcServer.start()` creates and injects all dependencies:
   - Create `EmbeddingService` with Pinecone client
   - Create `PineconeVectorStore` with index connection
   - Create `VectorizationPipeline` with all dependencies
   - Inject into `RAGDocumentServiceServicer`

3. **AC3: VectorizeDocument RPC** - Implement `VectorizeDocument` in `rag_document_service.py`:
   - Validate document exists and has chunks
   - Call `VectorizationPipeline.vectorize_document()`
   - Support async mode (return job_id immediately)
   - Return `VectorizeDocumentResponse` with progress/result

4. **AC4: GetVectorizationJob RPC** - Implement `GetVectorizationJob` in `rag_document_service.py`:
   - Look up job by ID from pipeline
   - Return `VectorizationJobResponse` with status and progress
   - Return NOT_FOUND if job doesn't exist

5. **AC5: CLI Integration** - Update `fp-knowledge` CLI:
   - Add `vectorize` command to trigger vectorization
   - Support `--async` flag for background execution
   - Add `job-status` command to poll vectorization jobs
   - Update `promote` command to optionally trigger vectorization

6. **AC6: Unit Tests** - Minimum 10 unit tests covering:
   - VectorizeDocument RPC success path
   - VectorizeDocument async mode
   - GetVectorizationJob status polling
   - Error handling (document not found, no chunks, etc.)
   - Dependency injection verification

7. **AC7: E2E Test** - Add E2E test scenario for vectorization flow:
   - **Replace mock-ai with real ai-model service** in E2E docker-compose
   - Create document → Stage → Chunk → Vectorize → Verify vectors in Pinecone
   - **Test isolation:** Clean up vectors created in Pinecone after test (use unique namespace per test run)
   - **Skip mock-ai dependent test:** Mark `test_05_weather_ingestion.py` as `skip` (requires AI agent - Story 0.75.18)
   - Pinecone credentials must be available in E2E environment (via secrets or `.env`)

8. **AC8: CI Passes** - All lint checks and tests pass in CI

## Tasks / Subtasks

- [ ] **Task 1: Extend RAGDocumentServiceServicer Constructor** (AC: #1)
  - [ ] Update `__init__` to accept additional dependencies:
    ```python
    def __init__(
        self,
        repository: RagDocumentRepository,
        chunk_repository: RagChunkRepository,
        chunking_workflow: ChunkingWorkflow | None = None,
        extraction_workflow: ExtractionWorkflow | None = None,
        vectorization_pipeline: VectorizationPipeline | None = None,
    ) -> None:
    ```
  - [ ] Store dependencies as instance attributes
  - [ ] Log warning if optional dependencies are None (graceful degradation)

- [ ] **Task 2: Wire Dependencies in grpc_server.py** (AC: #2)
  - [ ] Create `RagChunkRepository` and ensure indexes
  - [ ] Create `EmbeddingService` (requires Pinecone API key check)
  - [ ] Create `PineconeVectorStore` (requires index name check)
  - [ ] Create `VectorizationPipeline` with all dependencies
  - [ ] Create `ChunkingWorkflow` and `SemanticChunker`
  - [ ] Pass all dependencies to `RAGDocumentServiceServicer`
  - [ ] Handle missing Pinecone credentials gracefully (log warning, disable vectorization)

- [ ] **Task 3: Implement VectorizeDocument RPC** (AC: #3)
  - [ ] Add `VectorizeDocument` method to `RAGDocumentServiceServicer`
  - [ ] Validate: pipeline injected, document exists, document has chunks
  - [ ] Handle sync mode: call pipeline, wait for result, return response
  - [ ] Handle async mode: start job, return job_id immediately
  - [ ] Map `VectorizationResult` to proto `VectorizeDocumentResponse`
  - [ ] Handle errors with appropriate gRPC status codes

- [ ] **Task 4: Implement GetVectorizationJob RPC** (AC: #4)
  - [ ] Add `GetVectorizationJob` method to `RAGDocumentServiceServicer`
  - [ ] Call `pipeline.get_job_status(job_id)`
  - [ ] Map `VectorizationResult` to proto `VectorizationJobResponse`
  - [ ] Return NOT_FOUND if job doesn't exist

- [ ] **Task 5: Update CLI** (AC: #5)
  - [ ] Add `vectorize` command to `scripts/fp-knowledge/`:
    ```bash
    fp-knowledge vectorize <document_id> --version <n> [--async]
    ```
  - [ ] Add `job-status` command:
    ```bash
    fp-knowledge job-status <job_id>
    ```
  - [ ] Update `promote` command with `--vectorize` flag
  - [ ] Add progress display for sync mode

- [ ] **Task 6: Create Unit Tests** (AC: #6)
  - [ ] Create `tests/unit/ai_model/test_rag_document_service_vectorization.py`
  - [ ] Test VectorizeDocument success (sync mode)
  - [ ] Test VectorizeDocument async mode returns job_id
  - [ ] Test VectorizeDocument with missing pipeline (graceful error)
  - [ ] Test VectorizeDocument with document not found
  - [ ] Test VectorizeDocument with no chunks
  - [ ] Test GetVectorizationJob success
  - [ ] Test GetVectorizationJob not found
  - [ ] Test dependency injection in grpc_server.py
  - [ ] Test CLI vectorize command
  - [ ] Test CLI job-status command

- [ ] **Task 7: Add E2E Test** (AC: #7)
  - [ ] **7a: Replace mock_ai with real ai-model in E2E infrastructure**
    - [ ] Update `tests/e2e/infrastructure/docker-compose.e2e.yaml`:
      - Remove `mock-ai` service
      - Add `ai-model` service (same pattern as plantation-model, collection-model)
      - Configure Pinecone credentials via environment variables
    - [ ] Update `tests/e2e/infrastructure/.env.e2e.template` with Pinecone vars
    - [ ] Verify ai-model container builds and starts with health check
  - [ ] **7b: Skip tests that depend on mock-ai container**
    - [ ] Mark `test_05_weather_ingestion.py` as `@pytest.mark.skip(reason="Requires AI agent - Story 0.75.18")`
    - [ ] This test uses mock-ai for weather extraction; real ai-model doesn't have agents configured yet
    - [ ] Test will be re-enabled in Story 0.75.18 (E2E: Weather Observation Extraction Flow)
  - [ ] **7c: Create vectorization E2E test scenario**
    - [ ] Create `tests/e2e/scenarios/test_rag_vectorization.py`
    - [ ] Test flow: CreateDocument → StageDocument → ChunkDocument → VectorizeDocument
    - [ ] Verify vectors exist in Pinecone via `PineconeVectorStore.get_stats()` or query
  - [ ] **7d: Implement test isolation for Pinecone**
    - [ ] Generate unique namespace per test run (e.g., `e2e-{uuid}` or `e2e-{timestamp}`)
    - [ ] Cleanup fixture: delete namespace vectors after test via `vector_store.delete_all(namespace)`
    - [ ] Ensure test doesn't pollute production namespaces

- [ ] **Task 8: CI Verification** (AC: #8)
  - [ ] Run lint checks: `ruff check . && ruff format --check .`
  - [ ] Run unit tests locally
  - [ ] Run E2E tests with `--build` flag
  - [ ] Push and verify CI passes

## Git Workflow (MANDATORY)

**Branch name:** `feature/0-75-13c-rag-vectorization-grpc-wiring`

### Story Start
- [ ] GitHub Issue created
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-13c-rag-vectorization-grpc-wiring
  ```

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Push to feature branch regularly

### Story Done
- [ ] Create Pull Request
- [ ] CI passes (including E2E)
- [ ] Code review completed
- [ ] PR merged

## Dev Notes

### Files to Modify

| File | Changes |
|------|---------|
| `services/ai-model/src/ai_model/api/rag_document_service.py` | Extend `__init__`, add `VectorizeDocument`, `GetVectorizationJob` |
| `services/ai-model/src/ai_model/api/grpc_server.py` | Create and inject all dependencies |
| `scripts/fp-knowledge/fp_knowledge/commands/` | Add `vectorize.py`, `job_status.py`, update `promote.py` |
| `scripts/fp-knowledge/fp_knowledge/client.py` | Add `vectorize()`, `get_job_status()` methods |

### Dependency Chain

```
grpc_server.py
    │
    ├── RagDocumentRepository ────────────────────────┐
    ├── RagChunkRepository ───────────────────────────┤
    ├── ChunkingWorkflow ─────────────────────────────┤
    │       └── SemanticChunker                       │
    ├── ExtractionWorkflow ───────────────────────────┤
    └── VectorizationPipeline ────────────────────────┤
            ├── RagChunkRepository ◄──────────────────┤
            ├── RagDocumentRepository ◄───────────────┤
            ├── EmbeddingService                      │
            │       └── Pinecone Inference API        │
            └── PineconeVectorStore                   │
                    └── Pinecone Index API            │
                                                      │
    RAGDocumentServiceServicer ◄──────────────────────┘
```

### Graceful Degradation

If Pinecone credentials are missing:
- Log warning at startup
- `VectorizationPipeline` = None
- `VectorizeDocument` returns `FAILED_PRECONDITION` with message
- Other RAG operations (CRUD, chunking) continue working

### Proto Reference

```protobuf
// Already defined in ai_model.proto (Story 0.75.13b)
rpc VectorizeDocument(VectorizeDocumentRequest) returns (VectorizeDocumentResponse);
rpc GetVectorizationJob(GetVectorizationJobRequest) returns (VectorizationJobResponse);
```

### E2E Infrastructure Changes (CRITICAL)

This story transitions E2E tests from `mock-ai` to **real ai-model service**.

**Before (current state):**
```yaml
# docker-compose.e2e.yaml
services:
  mock-ai:
    image: mock-ai:latest  # Simple stub returning fixed responses
```

**After (this story):**
```yaml
# docker-compose.e2e.yaml
services:
  ai-model:
    build:
      context: ../../../
      dockerfile: services/ai-model/Dockerfile
    environment:
      - AI_MODEL_MONGODB_URI=mongodb://mongodb:27017
      - AI_MODEL_PINECONE_API_KEY=${PINECONE_API_KEY}
      - AI_MODEL_PINECONE_INDEX_NAME=${PINECONE_INDEX_NAME}
      # OpenRouter NOT configured - LLM tests skipped
    depends_on:
      - mongodb
      - dapr-placement
```

**Test Isolation Pattern:**
```python
# tests/e2e/scenarios/test_rag_vectorization.py
import uuid

@pytest.fixture
def e2e_namespace():
    """Generate unique namespace for test isolation."""
    namespace = f"e2e-{uuid.uuid4().hex[:8]}"
    yield namespace
    # Cleanup: delete all vectors in namespace
    vector_store.delete_all(namespace=namespace)

def test_vectorize_document(e2e_namespace, ai_model_client):
    # Create document with namespace override for test
    # ...
```

**Skipped Test:**
- `test_05_weather_ingestion.py` - Uses mock-ai for weather extraction; requires AI agent (Story 0.75.18)

This test will be re-enabled in Story 0.75.18 (E2E: Weather Observation Extraction Flow) when the Extractor agent is implemented and configured.

## Dependencies

**Required Stories (complete):**
- Story 0.75.13b: VectorizationPipeline class and proto definitions

**Enables:**
- Story 0.75.14: RAG Retrieval Service (can query vectorized content)
- CLI-based document promotion workflow

## Estimated Scope

| Component | Effort |
|-----------|--------|
| Task 1-2: Dependency injection | Small |
| Task 3-4: RPC implementation | Medium |
| Task 5: CLI integration | Medium |
| Task 6-7: Testing | Medium |
| Task 8: CI verification | Small |

**Total:** ~1 focused development session

## References

- [Source: `_bmad-output/sprint-artifacts/0-75-13b-rag-vectorization-pipeline.md`] - Task 6b that was deferred
- [Source: `proto/ai_model/v1/ai_model.proto`] - Proto definitions (lines 209-212, 564-623)
- [Source: `services/ai-model/src/ai_model/services/vectorization_pipeline.py`] - Pipeline to wire
- [Source: `services/ai-model/src/ai_model/api/rag_document_service.py`] - Service to extend
- [Source: `services/ai-model/src/ai_model/api/grpc_server.py`] - Server to update

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH=".:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/test_rag_document_service_vectorization.py -v
```
**Output:**
```
(to be filled)
```

### 2. E2E Tests (MANDATORY)

```bash
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
(to be filled)
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

```bash
gh workflow run e2e.yaml --ref feature/0-75-13c-rag-vectorization-grpc-wiring
```
**CI Run ID:** (to be filled)
**CI E2E Status:** [ ] Passed / [ ] Failed

---

## Dev Agent Record

> _This section is populated by the dev-story workflow upon implementation._

### Agent Model Used
(to be filled)

### Completion Notes List
(to be filled)

### File List
(to be filled)

---

## Code Review Record

> _Completed per CLAUDE.md Step 9e requirement_

### Review Date
(to be filled)

### Reviewer Model
(to be filled)

### Review Outcome
(to be filled)

### Issues Found
(to be filled)

### Final Verdict
(to be filled)
