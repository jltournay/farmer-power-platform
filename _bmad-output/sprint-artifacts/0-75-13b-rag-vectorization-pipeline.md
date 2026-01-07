# Story 0.75.13b: RAG Vectorization Pipeline (Orchestration)

**Status:** in-progress
**GitHub Issue:** #131

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer implementing RAG functionality**,
I want a vectorization pipeline that coordinates embedding generation and vector storage,
So that document chunks become searchable after ingestion.

## Acceptance Criteria

1. **AC1: VectorizationPipeline Class** - Create `VectorizationPipeline` class in `services/ai-model/src/ai_model/services/` that orchestrates the full vectorization flow
2. **AC2: Chunk Reading** - Read un-vectorized chunks from MongoDB via `RagChunkRepository.get_chunks_without_vectors()`
3. **AC3: Embedding Generation** - Call `EmbeddingService.embed_passages()` (Story 0.75.12) to generate vector embeddings
4. **AC4: Vector Storage** - Call `PineconeVectorStore.upsert()` (Story 0.75.13) to store vectors with metadata
5. **AC5: Chunk Status Update** - Update `RagChunk.pinecone_id` in MongoDB after successful vectorization via `RagChunkRepository.update_pinecone_id()`
6. **AC6: Document Status Update** - Update `RagDocument` fields (`pinecone_namespace`, `pinecone_ids`, `content_hash`) after full vectorization
7. **AC7: Batch Processing** - Process chunks in configurable batches (default: 50) for memory efficiency
8. **AC8: Error Handling** - Handle partial failures gracefully; continue processing remaining chunks if some fail
9. **AC9: Progress Tracking** - Return `VectorizationJob` with progress metrics (`chunks_total`, `chunks_embedded`, `chunks_stored`, `failed_count`)
10. **AC10: Async Job Support** - Support `--async` flag via job_id tracking; provide `get_job_status()` method
11. **AC11: Namespace Strategy** - Generate namespace based on document status: `knowledge-v{version}` (active), `knowledge-v{version}-staged` (staged)
12. **AC12: Content Hash** - Generate SHA256 hash of chunk contents for change detection
13. **AC13: Unit Tests** - Minimum 15 unit tests covering orchestration, batching, error handling, and progress tracking
14. **AC14: CLI Integration** - Wire pipeline into `fp-knowledge promote` command for document promotion workflow
15. **AC15: CI Passes** - All lint checks and tests pass in CI

## Tasks / Subtasks

- [x] **Task 1: Create Domain Models** (AC: #9, #10) ✅
  - [x] Create `services/ai-model/src/ai_model/domain/vectorization.py`:
    - [x] `VectorizationJobStatus` enum: `pending`, `in_progress`, `completed`, `failed`, `partial`
    - [x] `VectorizationJob` model: job_id, status, document_id, document_version, namespace
    - [x] `VectorizationProgress` model: chunks_total, chunks_embedded, chunks_stored, failed_count, eta_seconds
    - [x] `VectorizationResult` model: job_id, status, progress, error_message, started_at, completed_at
    - [x] `FailedChunk` model: chunk_id, chunk_index, error_message
  - [x] Export models in `domain/__init__.py`

- [x] **Task 2: Create VectorizationPipeline Class** (AC: #1, #7, #8, #11, #12) ✅
  - [x] Create `services/ai-model/src/ai_model/services/vectorization_pipeline.py`
  - [x] Implement `__init__()` with dependencies:
    - [x] `RagChunkRepository` - for reading chunks and updating pinecone_id
    - [x] `RagDocumentRepository` - for updating document after vectorization
    - [x] `EmbeddingService` - for generating embeddings
    - [x] `PineconeVectorStore` - for storing vectors
    - [x] `Settings` - for batch size configuration
  - [x] Implement `_generate_namespace(document: RagDocument) -> str` helper
  - [x] Implement `_compute_content_hash(chunks: list[RagChunk]) -> str` helper (SHA256)

- [x] **Task 3: Implement Vectorize Document Method** (AC: #2, #3, #4, #5, #6, #9) ✅
  - [x] Implement `async def vectorize_document(document_id: str, document_version: int, request_id: str | None = None) -> VectorizationResult`
  - [x] Flow implemented:
    1. Get all un-vectorized chunks via `chunk_repo.get_chunks_without_vectors()`
    2. If no chunks, return early with `completed` status
    3. Process chunks in batches (configurable, default 50):
       a. Extract chunk contents for embedding
       b. Call `embedding_service.embed_passages()` with batch
       c. Build `VectorUpsertRequest` list with metadata from chunk/document
       d. Call `vector_store.upsert()` with namespace
       e. Update each chunk's `pinecone_id` in MongoDB
    4. Update `RagDocument` with `pinecone_namespace`, `pinecone_ids`, `content_hash`
    5. Return `VectorizationResult` with progress

- [x] **Task 4: Implement Progress Tracking** (AC: #9, #10) ✅
  - [x] In-memory job storage via `_jobs` dict for async tracking
  - [x] Implement `async def get_job_status(job_id: str) -> VectorizationResult | None`
  - [x] Implement progress logging at batch boundaries
  - [x] Track failed chunk IDs via `FailedChunk` model

- [x] **Task 5: Implement Metadata Building** (AC: #4, #11) ✅
  - [x] Implement `_build_vector_metadata(chunk: RagChunk, document: RagDocument) -> VectorMetadata`
  - [x] Implement `_generate_vector_id(document_id, chunk_index) -> str`

- [x] **Task 6: Add Proto Definitions** ✅
  - [x] Add `VectorizeDocument` RPC to `proto/ai_model/v1/ai_model.proto`
  - [x] Add `GetVectorizationJob` RPC
  - [x] Add `VectorizeDocumentRequest/Response` messages
  - [x] Add `VectorizationJobResponse` message
  - [x] Regenerate proto files via `./scripts/proto-gen.sh`

- [ ] **Task 6b: Wire into CLI** (AC: #14) - PENDING SERVICE IMPLEMENTATION
  - [ ] Implement VectorizeDocument RPC in rag_document_service.py
  - [ ] Add `vectorize` method to KnowledgeClient
  - [ ] Update `promote` command in CLI to trigger vectorization

- [x] **Task 7: Create Unit Tests** (AC: #13) ✅ - 29 TESTS
  - [x] Create `tests/unit/ai_model/test_vectorization_pipeline.py`
  - [x] Test cases (29 total):
    - [x] Progress percentage calculation (3 tests)
    - [x] Job creation and status values (2 tests)
    - [x] Result duration calculation (3 tests)
    - [x] Namespace generation for staged/active/archived/draft (4 tests)
    - [x] Content hash computation and determinism (4 tests)
    - [x] Vector metadata building (2 tests)
    - [x] Full vectorization flow (6 tests)
    - [x] Batch processing (1 test)
    - [x] Job status tracking (3 tests)
    - [x] Configuration settings (2 tests)

- [x] **Task 8: Export and Wire Up** (AC: #14) ✅
  - [x] Export `VectorizationPipeline` in `services/__init__.py`
  - [x] Export domain models in `domain/__init__.py`
  - [x] Add `vectorization_batch_size` setting to `config.py`
  - [x] Add `replace()` method to `RagDocumentRepository`
  - [x] Add `find_one_and_replace` to MockMongoCollection in conftest.py

- [ ] **Task 9: CI Verification** (AC: #15) - IN PROGRESS
  - [x] Run lint checks: `ruff check . && ruff format --check .` ✅
  - [x] Run unit tests locally with mocked dependencies ✅ (628 passed)
  - [ ] Push to feature branch and verify CI passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.13b: RAG Vectorization Pipeline"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-13b-rag-vectorization-pipeline
  ```

**Branch name:** `feature/0-75-13b-rag-vectorization-pipeline`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-13b-rag-vectorization-pipeline`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.13b: RAG Vectorization Pipeline" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-13b-rag-vectorization-pipeline`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH=".:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/test_vectorization_pipeline.py -v
```
**Output:**
```
29 passed in 1.66s
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
102 passed, 1 skipped in 124.53s (0:02:04)
```
**E2E passed:** [x] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/0-75-13b-rag-vectorization-pipeline

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-13b-rag-vectorization-pipeline --limit 3
```
**CI Run ID:** 20799399185 (CI), 20799734665 (E2E)
**CI E2E Status:** [x] Passed / [ ] Failed (passed on retry, initial failure was flaky timeout)
**Verification Date:** 2026-01-07

---

## Dev Notes

### CRITICAL: This is the ORCHESTRATION Layer

**This story creates the VectorizationPipeline that orchestrates "embed then store".**

It USES existing infrastructure from previous stories:

| Story | Component | Role in Pipeline |
|-------|-----------|------------------|
| 0.75.10d (done) | `SemanticChunker` | Creates chunks (already complete) |
| 0.75.12 (done) | `EmbeddingService` | Generates embeddings from text |
| 0.75.13 (done) | `PineconeVectorStore` | Stores vectors in Pinecone |
| **0.75.13b (this)** | `VectorizationPipeline` | Orchestrates the full flow |
| 0.75.14 (next) | `RetrievalService` | Queries vectors for RAG |

### Architecture Reference

```
┌────────────────────────────────────────────────────────────────┐
│                  VECTORIZATION PIPELINE FLOW                    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  RagChunkRepository ──► VectorizationPipeline ──► PineconeVectorStore
│        │                        │                       │
│        │                        │                       │
│   get_chunks_       embed_passages()           upsert()
│   without_vectors()      │                       │
│        │                 │                       │
│        ▼                 ▼                       ▼
│   ┌─────────┐     ┌─────────────┐     ┌──────────────┐
│   │ MongoDB │     │ Pinecone    │     │   Pinecone   │
│   │ chunks  │     │ Inference   │     │   Index      │
│   └─────────┘     └─────────────┘     └──────────────┘
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Existing Dependencies (All Complete)

**1. RagChunkRepository** (`infrastructure/repositories/rag_chunk_repository.py`):
```python
# Key methods used by VectorizationPipeline:
await chunk_repo.get_chunks_without_vectors(document_id, document_version)  # Returns list[RagChunk]
await chunk_repo.update_pinecone_id(chunk_id, pinecone_id)  # Updates after vectorization
```

**2. EmbeddingService** (`services/embedding_service.py`):
```python
# Key method used by VectorizationPipeline:
embeddings = await embedding_service.embed_passages(
    passages=[chunk.content for chunk in batch],
    request_id=request_id,
    knowledge_domain=document.domain.value,
)
# Returns list[list[float]] - one embedding per passage
```

**3. PineconeVectorStore** (`infrastructure/pinecone_vector_store.py`):
```python
# Key method used by VectorizationPipeline:
result = await vector_store.upsert(
    vectors=[VectorUpsertRequest(id=..., values=embedding, metadata=...)],
    namespace="knowledge-v12",
)
# Returns UpsertResult with upserted_count
```

### VectorMetadata Mapping

The pipeline must map from RagChunk + RagDocument to VectorMetadata:

| VectorMetadata Field | Source | Example |
|---------------------|--------|---------|
| `document_id` | `RagDocument.document_id` | "disease-diagnosis-guide" |
| `chunk_id` | `RagChunk.chunk_id` | "disease-guide-v1-chunk-0" |
| `chunk_index` | `RagChunk.chunk_index` | 0 |
| `domain` | `RagDocument.domain.value` | "plant_diseases" |
| `title` | `RagDocument.title` | "Blister Blight Treatment Guide" |
| `region` | `RagDocument.metadata.region` | "Kenya" |
| `season` | `RagDocument.metadata.season` | None |
| `tags` | `RagDocument.metadata.tags` | ["blister-blight", "fungal"] |

### Namespace Strategy (Aligned with Architecture)

Generate namespace based on document status per `rag-knowledge-versioning.md`:

```python
def _generate_namespace(self, document: RagDocument) -> str:
    """Generate Pinecone namespace based on document status."""
    version = document.version
    status = document.status

    if status == RagDocumentStatus.ACTIVE:
        return f"knowledge-v{version}"
    elif status == RagDocumentStatus.STAGED:
        return f"knowledge-v{version}-staged"
    elif status == RagDocumentStatus.ARCHIVED:
        return f"knowledge-v{version}-archived"
    else:
        # Draft documents shouldn't be vectorized
        raise ValueError(f"Cannot vectorize document with status: {status}")
```

### Batch Processing Strategy

Process chunks in batches to manage memory and provide progress:

```python
VECTORIZATION_BATCH_SIZE = 50  # Configurable via settings

async def vectorize_document(self, document_id: str, document_version: int) -> VectorizationResult:
    # 1. Get chunks
    chunks = await self._chunk_repo.get_chunks_without_vectors(document_id, document_version)

    if not chunks:
        return VectorizationResult(status=VectorizationJobStatus.COMPLETED, progress=...)

    # 2. Process in batches
    batches = [chunks[i:i+VECTORIZATION_BATCH_SIZE] for i in range(0, len(chunks), VECTORIZATION_BATCH_SIZE)]

    for batch_idx, batch in enumerate(batches):
        # Embed batch
        embeddings = await self._embedding_service.embed_passages(
            passages=[c.content for c in batch],
        )

        # Build upsert requests
        vectors = [
            VectorUpsertRequest(
                id=f"{document_id}-{chunk.chunk_index}",
                values=embedding,
                metadata=self._build_metadata(chunk, document),
            )
            for chunk, embedding in zip(batch, embeddings)
        ]

        # Store in Pinecone
        await self._vector_store.upsert(vectors, namespace=namespace)

        # Update chunks in MongoDB
        for chunk, vector in zip(batch, vectors):
            await self._chunk_repo.update_pinecone_id(chunk.chunk_id, vector.id)

        # Log progress
        logger.info("Batch vectorized", batch=batch_idx+1, total=len(batches))

    # 3. Update document
    await self._update_document_after_vectorization(document, chunks, namespace)
```

### Content Hash Calculation

Calculate SHA256 hash of all chunk contents for change detection:

```python
import hashlib

def _compute_content_hash(self, chunks: list[RagChunk]) -> str:
    """Compute SHA256 hash of all chunk contents."""
    content = "".join(chunk.content for chunk in sorted(chunks, key=lambda c: c.chunk_index))
    return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
```

### Error Handling Strategy

Handle partial failures gracefully - continue processing remaining chunks:

```python
failed_chunks: list[tuple[str, str]] = []  # (chunk_id, error_message)

for batch in batches:
    try:
        # Process batch...
    except Exception as e:
        logger.error("Batch failed", batch_idx=batch_idx, error=str(e))
        for chunk in batch:
            failed_chunks.append((chunk.chunk_id, str(e)))
        continue  # Continue with next batch

# Return partial success if some chunks failed
if failed_chunks:
    return VectorizationResult(
        status=VectorizationJobStatus.PARTIAL,
        progress=VectorizationProgress(
            chunks_total=len(chunks),
            chunks_stored=len(chunks) - len(failed_chunks),
            failed_count=len(failed_chunks),
        ),
        failed_chunks=failed_chunks,
    )
```

### CLI Integration (fp-knowledge promote)

Update the `promote` command to trigger vectorization after status change:

```python
# scripts/fp-knowledge/fp_knowledge/commands/promote.py (existing)

@app.command()
def promote(
    document_id: str,
    async_mode: bool = typer.Option(False, "--async", help="Return immediately with job_id"),
):
    """Promote document from staged to active, triggering vectorization."""
    # 1. Update document status to ACTIVE
    # ... existing logic ...

    # 2. Trigger vectorization
    if async_mode:
        job_id = vectorization_pipeline.start_async(document_id, version)
        typer.echo(f"Vectorization started. Job ID: {job_id}")
        typer.echo(f"Check status: fp-knowledge job-status {job_id}")
    else:
        result = await vectorization_pipeline.vectorize_document(document_id, version)
        # Display progress...
```

### Directory Structure After Story

```
services/ai-model/src/ai_model/
├── domain/
│   ├── vectorization.py               # VectorizationJob, Progress, Result (NEW)
│   ├── vector_store.py                # VectorMetadata, etc. (Story 0.75.13)
│   ├── embedding.py                   # EmbeddingResult, etc. (Story 0.75.12)
│   └── rag_document.py                # RagDocument, RagChunk (Story 0.75.9)
├── infrastructure/
│   ├── pinecone_vector_store.py       # PineconeVectorStore (Story 0.75.13)
│   └── repositories/
│       ├── rag_chunk_repository.py    # Chunk CRUD (Story 0.75.10d)
│       └── rag_document_repository.py # Document CRUD (Story 0.75.10)
├── services/
│   ├── vectorization_pipeline.py      # VectorizationPipeline (NEW)
│   ├── embedding_service.py           # EmbeddingService (Story 0.75.12)
│   └── semantic_chunker.py            # SemanticChunker (Story 0.75.10d)
└── config.py

tests/unit/ai_model/
├── test_vectorization_pipeline.py     # Pipeline tests (NEW)
├── test_pinecone_vector_store.py      # Vector store tests (Story 0.75.13)
└── test_embedding_service.py          # Embedding tests (Story 0.75.12)
```

### Previous Story Intelligence (Story 0.75.13)

**Key patterns to reuse from Story 0.75.13:**

1. **Async via `run_in_executor`** - Not needed here (EmbeddingService and VectorStore already handle this)
2. **Batching** - Use similar pattern for chunk processing
3. **Retry on dependencies** - EmbeddingService and VectorStore have retry built-in; don't add extra retry at pipeline level
4. **Structured logging** - Use structlog for progress tracking

**Reference files:**
- `embedding_service.py` - embed_passages() usage
- `pinecone_vector_store.py` - upsert() with namespace
- `rag_chunk_repository.py` - get_chunks_without_vectors(), update_pinecone_id()

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Processing all chunks at once | Batch processing with configurable size |
| Failing entire job on single chunk error | Continue processing, track failures |
| Hardcoding batch sizes | Use Settings for configuration |
| Ignoring progress tracking | Log at batch boundaries, provide status endpoint |
| Vectorizing draft documents | Raise error - only staged/active allowed |
| Direct MongoDB access | Use RagChunkRepository and RagDocumentRepository |

### Dependencies

**Required Stories (complete):**
- Story 0.75.10d: Semantic chunking (provides chunks to vectorize)
- Story 0.75.12: EmbeddingService (provides embedding generation)
- Story 0.75.13: PineconeVectorStore (provides vector storage)

**Existing models to integrate with:**
- `RagDocument` (domain/rag_document.py:202) - update `pinecone_namespace`, `pinecone_ids`, `content_hash`
- `RagChunk` (domain/rag_document.py:156) - read chunks, update `pinecone_id`
- `VectorMetadata` (domain/vector_store.py:20) - build from chunk/document

**Dependent Stories (next):**
- Story 0.75.14: RAG Retrieval Service (queries vectorized content)
- Story 0.75.15: RAG Ranking Logic (ranks retrieved results)

### Interface Contract (for Dependent Stories)

| Consumer Story | Method | Purpose |
|----------------|--------|---------|
| 0.75.14 (Retrieval) | N/A | Vectors available in Pinecone after vectorization |
| CLI (fp-knowledge) | `vectorize_document()` | Trigger from promote command |
| CLI (fp-knowledge) | `get_job_status()` | Poll async job progress |

### Settings Configuration (config.py)

Add to existing Settings class:

```python
# Vectorization settings
vectorization_batch_size: int = Field(
    default=50,
    env="AI_MODEL_VECTORIZATION_BATCH_SIZE",
    description="Number of chunks to process per batch",
)
```

### References

- [Source: `_bmad-output/epics/epic-0-75-ai-model.md#story-07513b`] - Story requirements
- [Source: `_bmad-output/architecture/ai-model-architecture/rag-engine.md`] - RAG architecture overview
- [Source: `_bmad-output/architecture/ai-model-architecture/rag-knowledge-versioning.md`] - Namespace strategy
- [Source: `_bmad-output/ai-model-developer-guide/10-rag-knowledge-management.md`] - Vectorization process
- [Source: `services/ai-model/src/ai_model/services/embedding_service.py`] - EmbeddingService pattern
- [Source: `services/ai-model/src/ai_model/infrastructure/pinecone_vector_store.py`] - PineconeVectorStore pattern
- [Source: `services/ai-model/src/ai_model/infrastructure/repositories/rag_chunk_repository.py`] - Chunk repository
- [Source: `_bmad-output/sprint-artifacts/0-75-13-rag-vector-storage.md`] - Previous story learnings
- [External: Pinecone Python SDK](https://docs.pinecone.io/reference/python-sdk)

---

## Dev Agent Record

> _This section is populated by the dev-story workflow upon implementation._

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Unit tests: 29 passed in 1.66s
- Full test suite: 628 passed in 33.16s
- Lint checks: All checks passed

### Completion Notes List

1. **Core Implementation Complete** - VectorizationPipeline with full orchestration flow
2. **29 Unit Tests** - Exceeds AC13 requirement of 15 tests
3. **Proto Definitions Added** - VectorizeDocument and GetVectorizationJob RPCs
4. **CLI Integration Pending** - Requires service RPC implementation (Task 6b)

### Implementation Summary

| AC | Status | Notes |
|----|--------|-------|
| AC1-AC12 | ✅ Complete | Core pipeline, batching, error handling, namespace strategy |
| AC13 | ✅ Complete | 29 unit tests (requirement: 15) |
| AC14 | ⚠️ Partial | Proto added, service implementation pending |
| AC15 | ⚠️ Pending | Awaiting CI verification |

### File List

**Created:**
- `services/ai-model/src/ai_model/domain/vectorization.py` - Domain models (VectorizationJob, Progress, Result, FailedChunk)
- `services/ai-model/src/ai_model/services/vectorization_pipeline.py` - Main orchestration pipeline
- `tests/unit/ai_model/test_vectorization_pipeline.py` - 29 unit tests

**Modified:**
- `services/ai-model/src/ai_model/domain/__init__.py` - Export new domain models
- `services/ai-model/src/ai_model/services/__init__.py` - Export VectorizationPipeline
- `services/ai-model/src/ai_model/config.py` - Add vectorization_batch_size setting
- `services/ai-model/src/ai_model/infrastructure/repositories/rag_document_repository.py` - Add replace() method
- `proto/ai_model/v1/ai_model.proto` - Add VectorizeDocument/GetVectorizationJob RPCs
- `libs/fp-proto/src/fp_proto/ai_model/v1/*` - Regenerated proto stubs
- `tests/conftest.py` - Add find_one_and_replace to MockMongoCollection
- `_bmad-output/sprint-artifacts/sprint-status.yaml` - Update story status
