/# Story 0.75.13: RAG Vector Storage (Pinecone Repository)

**Status:** review
**GitHub Issue:** #129

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer implementing RAG functionality**,
I want a Pinecone client/repository for vector operations,
So that embeddings can be stored and queried efficiently for knowledge retrieval.

## Acceptance Criteria

1. **AC1: PineconeVectorStore Class** - Create `PineconeVectorStore` class in `services/ai-model/src/ai_model/infrastructure/` with async CRUD operations
2. **AC2: Upsert Operation** - Implement `upsert(vectors: list[VectorUpsertRequest]) -> UpsertResult` for storing vectors with metadata
3. **AC3: Query Operation** - Implement `query(embedding: list[float], top_k: int, filters: dict | None, namespace: str | None) -> QueryResult` for similarity search
4. **AC4: Delete Operations** - Implement `delete(ids: list[str], namespace: str | None)` and `delete_all(namespace: str)` for vector removal
5. **AC5: Namespace Management** - Support namespace parameter for version isolation (staged, active, archived)
6. **AC6: Metadata Storage** - Store vectors with metadata (doc_id, chunk_id, domain, title, region, season, tags) per RAG knowledge versioning requirements
7. **AC7: Stats Operation** - Implement `get_stats(namespace: str | None) -> IndexStats` for monitoring vector counts
8. **AC8: Async Operations** - All Pinecone operations MUST be async using `run_in_executor` (SDK is synchronous)
9. **AC9: Retry Logic** - Implement retry with tenacity for transient Pinecone API failures (PineconeException, ConnectionError, TimeoutError)
10. **AC10: Index Configuration** - Reuse Pinecone client from EmbeddingService (singleton pattern) with index reference; validate index exists on first operation
11. **AC11: Unit Tests** - Minimum 20 unit tests covering CRUD, batching, filtering, and error handling
12. **AC12: Integration Contract** - Method signatures compatible with Story 0.75.13b vectorization pipeline and Story 0.75.14 retrieval service
13. **AC13: CI Passes** - All lint checks and tests pass in CI

## Tasks / Subtasks

- [x] **Task 1: Create Domain Models** (AC: #6, #7, #12) ✅
  - [x] Create `services/ai-model/src/ai_model/domain/vector_store.py`:
    - [x] `VECTOR_DIMENSIONS = 1024` constant (E5-large dimensionality)
    - [x] `VectorMetadata` model: document_id, chunk_id, chunk_index, domain, title, region, season, tags
    - [x] `VectorUpsertRequest` model: id, values (embedding), metadata
    - [x] `UpsertResult` model: upserted_count
    - [x] `QueryMatch` model: id, score, metadata
    - [x] `QueryResult` model: matches list, namespace
    - [x] `IndexStats` model: total_vector_count, namespaces dict
    - [x] `NamespaceStats` model: vector_count per namespace
  - [x] Export models in `domain/__init__.py`

- [x] **Task 2: Create PineconeVectorStore Class** (AC: #1, #8, #10) ✅
  - [x] Create `services/ai-model/src/ai_model/infrastructure/pinecone_vector_store.py`
  - [x] Implement `__init__(settings: Settings)` - reuse Pinecone client pattern from EmbeddingService
  - [x] Implement `_get_index()` method - lazy initialization with `pc.Index(index_name)`
  - [x] Validate index exists on first operation; raise `PineconeIndexNotFoundError` if missing
  - [x] Run all synchronous Pinecone SDK calls in thread pool via `run_in_executor`

- [x] **Task 3: Implement Upsert Operation** (AC: #2, #5, #6, #8) ✅
  - [x] Implement `async def upsert(vectors: list[VectorUpsertRequest], namespace: str | None = None) -> UpsertResult`
  - [x] Format vectors for Pinecone: `{"id": str, "values": list[float], "metadata": dict}`
  - [x] Batch upsert (100 vectors per batch - Pinecone limit)
  - [x] Add retry decorator with tenacity (same pattern as EmbeddingService)
  - [x] Log upsert progress for large batches

- [x] **Task 4: Implement Query Operation** (AC: #3, #5, #8) ✅
  - [x] Implement `async def query(embedding: list[float], top_k: int = 5, filters: dict | None = None, namespace: str | None = None) -> QueryResult`
  - [x] Support metadata filtering with Pinecone filter syntax: `{"domain": {"$in": ["plant_diseases", "weather_patterns"]}}`
  - [x] Include metadata in results (`include_metadata=True`)
  - [x] Add retry decorator

- [x] **Task 5: Implement Delete Operations** (AC: #4, #5, #9) ✅
  - [x] Implement `async def delete(ids: list[str], namespace: str | None = None) -> int` - returns deleted count
  - [x] Implement `async def delete_all(namespace: str) -> None` - deletes all vectors in namespace
  - [x] Batch delete (1000 IDs per batch - Pinecone limit)
  - [x] Add retry decorator

- [x] **Task 6: Implement Stats Operation** (AC: #7) ✅
  - [x] Implement `async def get_stats(namespace: str | None = None) -> IndexStats`
  - [x] Use `index.describe_index_stats()` to get vector counts per namespace
  - [x] Add retry decorator

- [x] **Task 7: Create Unit Tests** (AC: #11) ✅
  - [x] Create `tests/unit/ai_model/test_pinecone_vector_store.py`
  - [x] 52 tests covering: upsert (single, batch, chunking), query (top_k, filters, namespace), delete (by IDs, all), stats, error handling, domain models

- [x] **Task 8: Export and Wire Up** (AC: #12) ✅
  - [x] Export `PineconeVectorStore` in `infrastructure/__init__.py`
  - [x] Export domain models in `domain/__init__.py`

- [x] **Task 9: CI Verification** (AC: #13) ✅
  - [x] Run lint checks: `ruff check . && ruff format --check .`
  - [x] Run unit tests locally with mocked Pinecone
  - [x] Push to feature branch and verify CI passes (CI Run ID: 20797593277)
  - [x] E2E CI: N/A (vector store doesn't modify Docker services - E2E covered by 0.75.13b)

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: #129
- [x] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-13-rag-vector-storage
  ```

**Branch name:** `feature/0-75-13-rag-vector-storage`

### During Development
- [x] All commits reference GitHub issue: `Relates to #129`
- [x] Commits are atomic by type (production, test - not mixed)
- [x] Push to feature branch: `git push -u origin feature/0-75-13-rag-vector-storage`

### Story Done
- [x] Create Pull Request: `gh pr create --title "Story 0.75.13: RAG Vector Storage (Pinecone Repository)" --base main`
- [x] CI passes on PR (including lint and unit tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-13-rag-vector-storage`

**PR URL:** https://github.com/jltournay/farmer-power-platform/pull/130

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH=".:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/test_pinecone_vector_store.py -v
```
**Output:**
```
======================== 52 passed, 8 warnings in 2.81s ========================
```

### 2. E2E Tests (OPTIONAL for this story)

> This story adds Pinecone vector store client but doesn't modify Docker services.
> E2E validation will be covered by Story 0.75.13b (vectorization pipeline).

**E2E Status:** N/A - vector store is a client library, not a Docker service.

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Output:**
```
All checks passed!
491 files already formatted
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/0-75-13-rag-vector-storage

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-13-rag-vector-storage --limit 3
```
**CI Run ID:** 20797593277
**CI Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-07

---

## Dev Notes

### CRITICAL: This is the LOW-LEVEL Pinecone Client

**This story creates the Pinecone vector storage client (CRUD operations only).**

The orchestration of "embed then store" is handled by **Story 0.75.13b** (Vectorization Pipeline).

| Story | Responsibility |
|-------|----------------|
| 0.75.12 (done) | `EmbeddingService` - Generate embeddings via Pinecone Inference |
| **0.75.13 (this)** | `PineconeVectorStore` - Store/query/delete vectors in Pinecone index |
| 0.75.13b (next) | `VectorizationPipeline` - Orchestrate: read chunks -> embed -> store -> update status |
| 0.75.14 | `RetrievalService` - Query vectors and return RAG context |

### Pinecone SDK Patterns (Established in Story 0.75.12)

**CRITICAL: The Pinecone Python SDK v8.0.0 is synchronous.** Use `run_in_executor` for async:

```python
from pinecone import Pinecone

class PineconeVectorStore:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: Pinecone | None = None
        self._index = None

    def _get_client(self) -> Pinecone:
        """Get or create Pinecone client (singleton)."""
        if not self._settings.pinecone_enabled:
            raise PineconeNotConfiguredError(...)

        if self._client is None:
            self._client = Pinecone(
                api_key=self._settings.pinecone_api_key.get_secret_value(),
            )
        return self._client

    def _get_index(self):
        """Get or create index reference (lazy init)."""
        if self._index is None:
            client = self._get_client()
            self._index = client.Index(self._settings.pinecone_index_name)
        return self._index

    async def upsert(self, vectors: list[VectorUpsertRequest], namespace: str | None = None) -> UpsertResult:
        index = self._get_index()
        loop = asyncio.get_running_loop()

        # Format for Pinecone
        pinecone_vectors = [
            {
                "id": v.id,
                "values": v.values,
                "metadata": v.metadata.model_dump() if v.metadata else {},
            }
            for v in vectors
        ]

        # Run in executor (SDK is sync)
        result = await loop.run_in_executor(
            None,
            lambda: index.upsert(vectors=pinecone_vectors, namespace=namespace),
        )
        return UpsertResult(upserted_count=result.upserted_count)


class PineconeNotConfiguredError(Exception):
    """Raised when Pinecone API key is not configured."""
    pass


class PineconeIndexNotFoundError(Exception):
    """Raised when the configured Pinecone index does not exist."""
    pass
```

### Pinecone Index Operations

| Operation | Method | Batch Limit | Notes |
|-----------|--------|-------------|-------|
| **Upsert** | `index.upsert(vectors=[], namespace=)` | 100 vectors | Include metadata |
| **Query** | `index.query(vector=[], top_k=, filter=, namespace=, include_metadata=True)` | 1 query | Returns matches with scores |
| **Delete by IDs** | `index.delete(ids=[], namespace=)` | 1000 IDs | Returns empty response |
| **Delete All** | `index.delete(delete_all=True, namespace=)` | N/A | Deletes entire namespace |
| **Stats** | `index.describe_index_stats()` | N/A | Vector counts per namespace |

### Namespace Strategy (RAG Knowledge Versioning)

Namespaces isolate document versions per the architecture:

| Status | Namespace Pattern | Example |
|--------|-------------------|---------|
| Active | `knowledge-v{version}` | `knowledge-v12` |
| Staged | `knowledge-v{version}-staged` | `knowledge-v13-staged` |
| Archived | `knowledge-v{version}-archived` | `knowledge-v11-archived` |

**Reference:** `_bmad-output/architecture/ai-model-architecture/rag-knowledge-versioning.md`

### Metadata Schema (Aligned with RAGDocument)

Store vectors with metadata for filtering and retrieval:

```python
class VectorMetadata(BaseModel):
    """Metadata stored with each vector in Pinecone.

    This schema enables filtering and attribution in queries.
    Pinecone metadata limit: 40KB per vector.
    """
    document_id: str           # Stable ID from RAGDocument
    chunk_id: str              # Unique chunk identifier (for MongoDB lookup)
    chunk_index: int           # Position within document
    domain: str                # plant_diseases, tea_cultivation, etc.
    title: str                 # Document title for display
    region: str | None = None  # Geographic filter
    season: str | None = None  # Seasonal filter (dry_season, monsoon, etc.)
    tags: list[str] = []       # Searchable tags
```

### Content Retrieval Strategy (IMPORTANT)

**Chunk text is NOT stored in Pinecone metadata** (40KB limit would bloat storage).

After `query()` returns matches, retrieve chunk content from MongoDB:

```python
# In RetrievalService (Story 0.75.14):
matches = await vector_store.query(embedding, top_k=5, namespace="knowledge-v12")
chunk_ids = [m.metadata.chunk_id for m in matches.matches]
chunks = await rag_chunk_repository.get_by_ids(chunk_ids)  # MongoDB lookup
```

The `RagChunk` model (in `domain/rag_document.py:156`) stores the actual text content.

### Filter Syntax (Pinecone Query)

Pinecone supports MongoDB-style filter syntax:

```python
# Single value filter
filter = {"domain": "plant_diseases"}

# Multiple values (OR)
filter = {"domain": {"$in": ["plant_diseases", "weather_patterns"]}}

# Combined filters (AND)
filter = {
    "domain": {"$in": ["plant_diseases"]},
    "region": "Kenya-Highland",
}

# Tag filtering
filter = {"tags": {"$in": ["blister-blight", "fungal"]}}
```

### Retry Configuration (Same as EmbeddingService)

```python
from pinecone.exceptions import PineconeException, ServiceException
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# Retry on transient failures (network, Pinecone service issues)
RETRYABLE_EXCEPTIONS = (ConnectionError, TimeoutError, OSError, PineconeException, ServiceException)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,
)
async def _do_operation():
    ...
```

**Note:** `NotFoundException` (index doesn't exist) should NOT be retried - raise immediately.

### Directory Structure After Story

```
services/ai-model/src/ai_model/
├── domain/
│   ├── vector_store.py               # VectorMetadata, VectorUpsertRequest, QueryResult (NEW)
│   ├── embedding.py                  # EmbeddingService models (Story 0.75.12)
│   └── ...
├── infrastructure/
│   ├── pinecone_vector_store.py      # PineconeVectorStore class (NEW)
│   └── repositories/
│       ├── embedding_cost_repository.py  # (Story 0.75.12)
│       └── ...
├── services/
│   └── embedding_service.py          # (Story 0.75.12) - reuse client pattern
└── config.py                         # Pinecone settings (already configured)

tests/unit/ai_model/
├── test_pinecone_vector_store.py     # Vector store tests (NEW)
├── test_embedding_service.py         # (Story 0.75.12)
└── ...
```

### Previous Story Intelligence (Story 0.75.12)

**Key patterns to reuse:**
1. **Async via `run_in_executor`** - Pinecone SDK is synchronous; wrap in thread pool
2. **Client singleton** - `_get_client()` with lazy init and `pinecone_enabled` check
3. **Tenacity retry** - Same retry config across all Pinecone operations

**Reference files:** `embedding_service.py` (client pattern), `embedding.py` (domain models)

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Direct sync calls to Pinecone | Use `run_in_executor` for async |
| Creating new client per operation | Singleton pattern via `_get_client()` |
| Hardcoding index name | Use `settings.pinecone_index_name` |
| Missing namespace parameter | Always pass namespace for version isolation |
| Large batch without chunking | Chunk upserts (100) and deletes (1000) |
| Ignoring metadata | Always include metadata for filtering |

### Dependencies

**Required Stories (complete):**
- Story 0.75.12: EmbeddingService (provides client pattern and embeddings)
- Story 0.75.10d: Semantic chunking (provides chunks to vectorize)

**Existing models to integrate with:**
- `RagChunk` (domain/rag_document.py:156) - has `pinecone_id` field for vectorization tracking
- `KnowledgeDomain` enum (domain/rag_document.py:37) - use for metadata.domain values

**Dependent Stories (next):**
- Story 0.75.13b: RAG Vectorization Pipeline (orchestrates embed -> store)
- Story 0.75.14: RAG Retrieval Service (uses query method)
- Story 0.75.15: RAG Ranking Logic (uses query method)

### Interface Contract (for Dependent Stories)

| Consumer Story | Method | Purpose |
|----------------|--------|---------|
| 0.75.13b (Vectorization) | `upsert(vectors, namespace)` | Store embedded chunks |
| 0.75.14 (Retrieval) | `query(embedding, top_k, filters, namespace)` | Similarity search |
| 0.75.14/15 (Tests) | `delete_all(namespace)` | Cleanup test data |
| 0.75.14 (Monitoring) | `get_stats(namespace)` | Verify upsert success |

### References

- [Source: `_bmad-output/epics/epic-0-75-ai-model.md#story-07513`] - Story requirements
- [Source: `_bmad-output/architecture/ai-model-architecture/rag-engine.md`] - RAG architecture overview
- [Source: `_bmad-output/architecture/ai-model-architecture/rag-knowledge-versioning.md`] - Namespace strategy
- [Source: `_bmad-output/ai-model-developer-guide/10-rag-knowledge-management.md`] - Vectorization process
- [Source: `services/ai-model/src/ai_model/services/embedding_service.py`] - Pinecone client pattern
- [Source: `services/ai-model/src/ai_model/config.py`] - Pinecone settings
- [Source: `_bmad-output/sprint-artifacts/0-75-12-rag-embedding-configuration.md`] - Previous story learnings
- [External: Pinecone Python SDK](https://docs.pinecone.io/reference/python-sdk)
- [External: Pinecone Upsert](https://docs.pinecone.io/guides/data/upsert-data)
- [External: Pinecone Query](https://docs.pinecone.io/guides/data/query-data)

---

## Dev Agent Record

> _This section is populated by the dev-story workflow upon implementation._

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References
- N/A - no issues encountered

### Completion Notes List
1. Implemented `PineconeVectorStore` with full async CRUD operations
2. Created 8 domain models for vector operations (VectorMetadata, VectorUpsertRequest, UpsertResult, QueryMatch, QueryResult, NamespaceStats, IndexStats)
3. Implemented retry logic using tenacity for transient failures
4. Auto-batching for upsert (100 vectors) and delete (1000 IDs) operations
5. Singleton client pattern matching EmbeddingService implementation
6. All async operations use `run_in_executor` for synchronous Pinecone SDK
7. Index validation on first operation to catch configuration errors early
8. 52 comprehensive unit tests covering all operations and edge cases

### File List
**New Files:**
- `services/ai-model/src/ai_model/domain/vector_store.py` - Domain models for vector operations
- `services/ai-model/src/ai_model/infrastructure/pinecone_vector_store.py` - PineconeVectorStore class
- `tests/unit/ai_model/test_pinecone_vector_store.py` - Unit tests (52 tests)

**Modified Files:**
- `services/ai-model/src/ai_model/domain/__init__.py` - Added vector store model exports
- `services/ai-model/src/ai_model/infrastructure/__init__.py` - Added PineconeVectorStore exports
- `_bmad-output/sprint-artifacts/sprint-status.yaml` - Updated story status
