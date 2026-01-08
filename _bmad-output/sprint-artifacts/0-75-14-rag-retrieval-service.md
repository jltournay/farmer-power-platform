# Story 0.75.14: RAG Retrieval Service

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer building AI agents**,
I want a retrieval service for RAG queries,
So that agents can find relevant knowledge to augment their responses.

## Context

The RAG Retrieval Service is the consumer-facing component that enables agents to search for relevant knowledge. It builds on:
- **Story 0.75.12:** `EmbeddingService` - generates query embeddings
- **Story 0.75.13:** `PineconeVectorStore` - performs similarity queries
- **Story 0.75.10d:** `RagChunkRepository` - retrieves chunk content from MongoDB

The retrieval service orchestrates these components to provide a high-level API for knowledge retrieval with configurable parameters.

## Acceptance Criteria

1. **AC1: RetrievalService Class** - Create `RetrievalService` that orchestrates retrieval:
   - Accept `EmbeddingService`, `PineconeVectorStore`, `RagChunkRepository` as dependencies
   - `retrieve(query, domains, top_k, confidence_threshold, namespace)` method
   - Coordinate: embed query -> search vectors -> fetch chunk content

2. **AC2: Query Embedding** - Use `EmbeddingService.embed_query()`:
   - Input type must be `QUERY` (not `PASSAGE`) for optimal E5 performance
   - Handle `PineconeNotConfiguredError` gracefully

3. **AC3: Vector Search** - Use `PineconeVectorStore.query()`:
   - Support domain filtering via Pinecone filter syntax: `{"domain": {"$in": domains}}`
   - Configurable `top_k` parameter (default: 5)
   - Configurable namespace for version isolation

4. **AC4: Confidence Threshold Filtering** - Filter results below threshold:
   - Configurable `confidence_threshold` parameter (default: 0.0 = no filtering)
   - Filter applied AFTER vector query (Pinecone doesn't support score filtering)

5. **AC5: Chunk Content Retrieval** - Fetch full content from MongoDB:
   - Use `RagChunkRepository.get_by_id()` for each matched chunk
   - Return `RetrievalResult` with: chunk content, score, metadata

6. **AC6: Multi-Domain Queries** - Support querying multiple domains:
   - Accept `domains: list[str]` parameter
   - Single query searches across all specified domains
   - Results ordered by similarity score regardless of domain

7. **AC7: Domain Models** - Create Pydantic models in `ai_model/domain/retrieval.py`:
   - `RetrievalQuery`: query, domains, top_k, confidence_threshold, namespace
   - `RetrievalMatch`: chunk_id, content, score, document_id, title, domain, metadata
   - `RetrievalResult`: matches, query, namespace, total_matches

8. **AC8: Golden Sample Test Suite (MANDATORY)** - Create test suite in `tests/golden/rag/retrieval/`:
   - Create seed documents JSON file (if not existing): `tests/golden/rag/seed_documents.json`
   - Create golden samples: `tests/golden/rag/retrieval/samples.json`
   - Create test file: `tests/golden/rag/retrieval/test_retrieval_golden.py`
   - Test isolation: each test suite uploads seeds to its OWN namespace (`golden-retrieval`)
   - Minimum 10 golden samples with query + expected document matches
   - Target: >= 85% retrieval accuracy

9. **AC9: Unit Tests** - Minimum 8 unit tests covering:
   - RetrievalService orchestration (embed -> query -> fetch)
   - Domain filtering behavior
   - Confidence threshold filtering
   - Multi-domain queries
   - Error handling (Pinecone not configured, chunk not found)
   - Empty results handling

10. **AC10: E2E Regression (MANDATORY)** - All existing E2E tests continue to pass:
    - Run full E2E suite with `--build` flag to rebuild ai-model container
    - All 99 existing tests must pass (8 skipped is acceptable)
    - No modifications to existing E2E test files

11. **AC11: CI Passes** - All lint checks and tests pass in CI

## Tasks / Subtasks

- [ ] **Task 1: Create Domain Models** (AC: #7)
  - [ ] Create `ai_model/domain/retrieval.py`
  - [ ] Implement `RetrievalQuery` Pydantic model
  - [ ] Implement `RetrievalMatch` Pydantic model
  - [ ] Implement `RetrievalResult` Pydantic model

- [ ] **Task 2: Implement RetrievalService** (AC: #1, #2, #3, #4, #5, #6)
  - [ ] Create `ai_model/services/retrieval_service.py`
  - [ ] Implement constructor with DI pattern (EmbeddingService, PineconeVectorStore, RagChunkRepository)
  - [ ] Implement `retrieve()` method with full orchestration
  - [ ] Add query embedding with `input_type=QUERY`
  - [ ] Add Pinecone filter construction for domain filtering
  - [ ] Add confidence threshold filtering post-query
  - [ ] Add chunk content retrieval from MongoDB
  - [ ] Add comprehensive error handling and logging

- [ ] **Task 3: Create Seed Documents** (AC: #8)
  - [ ] Create `tests/golden/rag/seed_documents.json` (if not exists)
  - [ ] Write 5+ realistic tea farming documents
  - [ ] Include at least 2 domains: plant_diseases, tea_cultivation
  - [ ] Each document 200-500 words with realistic agronomic content

- [ ] **Task 4: Create Golden Sample Test Suite** (AC: #8)
  - [ ] Create `tests/golden/rag/retrieval/conftest.py` with setup/teardown fixtures
  - [ ] Create `tests/golden/rag/retrieval/samples.json` with 10+ query samples
  - [ ] Create `tests/golden/rag/retrieval/test_retrieval_golden.py`
  - [ ] Implement namespace isolation (`golden-retrieval`)
  - [ ] Test retrieval accuracy >= 85%

- [ ] **Task 5: Create Unit Tests** (AC: #9)
  - [ ] Create `tests/unit/ai_model/test_retrieval_service.py`
  - [ ] Test orchestration flow
  - [ ] Test domain filtering
  - [ ] Test confidence threshold filtering
  - [ ] Test multi-domain queries
  - [ ] Test error handling
  - [ ] Minimum 8 tests

- [ ] **Task 6: E2E Regression Testing (MANDATORY)** (AC: #10)
  - [ ] Rebuild and start E2E infrastructure with `--build` flag
  - [ ] Verify Docker images were rebuilt (NOT cached) for ai-model
  - [ ] Run full E2E test suite
  - [ ] Verify: 99 passed, 8 skipped (or better)
  - [ ] Capture output in "Local Test Run Evidence" section
  - [ ] Tear down infrastructure

- [ ] **Task 7: CI Verification** (AC: #11)
  - [ ] Run lint: `ruff check . && ruff format --check .`
  - [ ] Run unit tests locally
  - [ ] Push and verify CI passes
  - [ ] Trigger E2E CI workflow
  - [ ] Verify E2E CI passes before code review

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.14: RAG Retrieval Service"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-14-rag-retrieval-service
  ```

**Branch name:** `feature/0-75-14-rag-retrieval-service`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-14-rag-retrieval-service`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.14: RAG Retrieval Service" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-14-rag-retrieval-service`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH=".:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/test_retrieval_service.py -v
```
**Output:**
```
(paste test summary here - e.g., "15 passed in 2.23s")
```

### 2. Golden Sample Tests
```bash
PYTHONPATH=".:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/golden/rag/retrieval/ -v
```
**Output:**
```
(paste golden sample test output here)
```
**Retrieval Accuracy:** [ ] >= 85%

### 3. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
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

### 4. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 5. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/0-75-14-rag-retrieval-service

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-14-rag-retrieval-service --limit 3
```
**CI Run ID:** _______________
**CI Status:** [ ] Passed / [ ] Failed
**E2E CI Run ID:** _______________
**E2E CI Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Pattern

The RetrievalService follows the established AI Model patterns:
- **Dependency Injection:** All dependencies (EmbeddingService, PineconeVectorStore, RagChunkRepository) injected via constructor
- **Async Operations:** All I/O operations are async (embedding, vector query, MongoDB)
- **Domain Models:** Pydantic models for request/response types
- **Structured Logging:** Use `structlog` with correlation IDs

### Component Relationships

```
RetrievalService
    ├── EmbeddingService.embed_query(query) → list[float]
    │       └── Pinecone Inference API (multilingual-e5-large)
    │
    ├── PineconeVectorStore.query(embedding, top_k, filters, namespace) → QueryResult
    │       └── Pinecone Index query with metadata filtering
    │
    └── RagChunkRepository.get_by_id(chunk_id) → RagChunk
            └── MongoDB ai_model.rag_chunks collection
```

### Key Implementation Details

**Query Embedding (E5 Input Types):**
```python
# CRITICAL: Use QUERY input type for search queries, not PASSAGE
# E5 models are trained to distinguish query vs document embeddings
embedding = await self._embedding_service.embed_query(query)  # Uses QUERY type
```

**Domain Filtering (Pinecone Filter Syntax):**
```python
# Pinecone filter syntax for domain filtering
filters = {"domain": {"$in": domains}} if domains else None
result = await self._vector_store.query(
    embedding=embedding,
    top_k=top_k,
    filters=filters,
    namespace=namespace,
)
```

**Confidence Threshold (Post-Query Filtering):**
```python
# Pinecone doesn't support score filtering in query
# Apply threshold after results returned
filtered_matches = [
    m for m in result.matches
    if m.score >= confidence_threshold
]
```

### Existing Code to Reuse

| Component | Location | Purpose |
|-----------|----------|---------|
| `EmbeddingService` | `ai_model/services/embedding_service.py` | Query embedding |
| `PineconeVectorStore` | `ai_model/infrastructure/pinecone_vector_store.py` | Vector similarity query |
| `RagChunkRepository` | `ai_model/infrastructure/repositories/rag_chunk_repository.py` | Chunk content retrieval |
| `VectorMetadata` | `ai_model/domain/vector_store.py` | Metadata model for query results |
| `QueryMatch` | `ai_model/domain/vector_store.py` | Individual match from query |
| `QueryResult` | `ai_model/domain/vector_store.py` | Container for query matches |
| `RagChunk` | `ai_model/domain/rag_document.py` | Chunk content model |
| `KnowledgeDomain` | `ai_model/domain/rag_document.py` | Enum: PLANT_DISEASES, TEA_CULTIVATION, WEATHER_PATTERNS, QUALITY_STANDARDS, REGIONAL_CONTEXT |

### Knowledge Domain Enum (MUST USE)

```python
# ai_model/domain/rag_document.py - KnowledgeDomain enum
# REUSE this - DO NOT create your own domain strings

from ai_model.domain.rag_document import KnowledgeDomain

# Valid domains:
# - KnowledgeDomain.PLANT_DISEASES ("plant_diseases")
# - KnowledgeDomain.TEA_CULTIVATION ("tea_cultivation")
# - KnowledgeDomain.WEATHER_PATTERNS ("weather_patterns")
# - KnowledgeDomain.QUALITY_STANDARDS ("quality_standards")
# - KnowledgeDomain.REGIONAL_CONTEXT ("regional_context")
```

### Golden Sample Test Isolation Pattern

Each test suite must be self-contained:

```python
# tests/golden/rag/retrieval/conftest.py
@pytest.fixture(scope="module")
def seeded_pinecone(embedding_service, vector_store, chunk_repository):
    """Setup: Vectorize and upload seeds to Pinecone. Teardown: Delete them."""
    namespace = "golden-retrieval"  # Unique namespace for this test suite

    # Setup: Load seeds, chunk them, embed them, upload to Pinecone
    seeds = load_seed_documents("tests/golden/rag/seed_documents.json")
    # ... vectorization logic ...

    yield namespace

    # Teardown: Clean up vectors
    await vector_store.delete_all(namespace=namespace)
```

### Seed Document Structure

```json
{
  "documents": [
    {
      "document_id": "blister-blight-guide",
      "title": "Blister Blight Disease Guide",
      "domain": "plant_diseases",
      "content": "## Overview\n\nBlister blight is a fungal disease...",
      "metadata": {
        "author": "Golden Sample Generator",
        "region": "Kenya",
        "tags": ["fungal", "disease", "tea"]
      }
    }
  ]
}
```

### Success Metrics (from Epic)

| Metric | Target | Validation |
|--------|--------|------------|
| RAG retrieval accuracy | Top-5 results contain expected document >= 85% | Golden sample tests |
| RAG retrieval latency | < 500ms p95 | Unit test timing assertions |

### Required Settings (from config.py)

The RetrievalService depends on Pinecone configuration in `ai_model/config.py`:

| Setting | Default | Required for |
|---------|---------|--------------|
| `pinecone_api_key` | None | All operations (check `settings.pinecone_enabled`) |
| `pinecone_index_name` | "farmer-power-rag" | Vector store queries |
| `pinecone_embedding_model` | "multilingual-e5-large" | Query embedding |
| `embedding_batch_size` | 96 | Query embedding (not used for single queries) |

### Error Handling

Handle these error cases gracefully:

| Error | Source | Handling |
|-------|--------|----------|
| `PineconeNotConfiguredError` | EmbeddingService/VectorStore | Return empty results with warning log |
| `PineconeIndexNotFoundError` | VectorStore | Raise with clear error message |
| Chunk not found in MongoDB | RagChunkRepository | Skip match, log warning, continue |
| Empty query | RetrievalService | Return empty results immediately |
| No domains specified | RetrievalService | Query all domains (no filter) |

### Project Structure Notes

```
services/ai-model/src/ai_model/
├── domain/
│   ├── retrieval.py          # NEW: RetrievalQuery, RetrievalMatch, RetrievalResult
│   ├── vector_store.py       # EXISTING: VectorMetadata, QueryMatch, QueryResult
│   └── rag_document.py       # EXISTING: RagChunk
├── services/
│   ├── retrieval_service.py  # NEW: RetrievalService class
│   ├── embedding_service.py  # EXISTING: EmbeddingService
│   └── ...
├── infrastructure/
│   ├── pinecone_vector_store.py  # EXISTING: PineconeVectorStore
│   └── repositories/
│       └── rag_chunk_repository.py  # EXISTING: RagChunkRepository

tests/golden/rag/
├── seed_documents.json       # NEW: Shared seed documents for all RAG tests
└── retrieval/
    ├── conftest.py           # NEW: Test fixtures with namespace isolation
    ├── samples.json          # NEW: Golden sample queries
    └── test_retrieval_golden.py  # NEW: Golden sample tests

tests/unit/ai_model/
└── test_retrieval_service.py  # NEW: Unit tests
```

### References

- [Source: `_bmad-output/epics/epic-0-75-ai-model.md` - Story 0.75.14 definition]
- [Source: `_bmad-output/ai-model-developer-guide/10-rag-knowledge-management.md` - RAG architecture]
- [Source: `_bmad-output/project-context.md` - Repository patterns and testing rules]
- [Source: `services/ai-model/src/ai_model/services/embedding_service.py` - EmbeddingService implementation]
- [Source: `services/ai-model/src/ai_model/infrastructure/pinecone_vector_store.py` - PineconeVectorStore implementation]
- [Source: `services/ai-model/src/ai_model/infrastructure/repositories/rag_chunk_repository.py` - RagChunkRepository implementation]

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
