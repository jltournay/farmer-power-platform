# Story 0.75.12: RAG Embedding Configuration (Pinecone Inference)

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer implementing RAG functionality**,
I want Pinecone Inference configured for embedding generation,
So that documents are automatically vectorized when stored in Pinecone with a single API.

## Acceptance Criteria

1. **AC1: Pinecone SDK Integration** - Add `pinecone>=5.0.0` dependency to `services/ai-model/pyproject.toml` with async support
2. **AC2: Pinecone Settings** - Extend `config.py` with Pinecone configuration (API key, environment, index name, model)
3. **AC3: Embedding Service** - Create `EmbeddingService` class using Pinecone Inference API with `multilingual-e5-large` model
4. **AC4: Batch Embedding** - Support batch embedding with automatic chunking (max 96 texts per batch, 1024 tokens per text)
5. **AC5: Input Type Handling** - Support both `passage` and `query` input types for appropriate embedding context
6. **AC6: Async Operations** - All embedding operations MUST be async using `asyncio`
7. **AC7: Error Handling** - Implement retry logic with tenacity for transient Pinecone API failures
8. **AC8: Cost Tracking** - Persist embedding cost events to MongoDB collection `ai_model.embedding_cost_events` (informational only - Pinecone Inference cost is included in index pricing)
9. **AC9: Unit Tests** - Minimum 20 unit tests covering embedding service operations
10. **AC10: Integration Contract** - Service method signatures compatible with Story 0.75.13b vectorization pipeline
11. **AC11: CI Passes** - All lint checks and tests pass in CI

## Tasks / Subtasks

- [ ] **Task 1: Add Pinecone Dependency** (AC: #1)
  - [ ] Add `pinecone>=5.0.0` to `services/ai-model/pyproject.toml`
  - [ ] Add `pinecone-plugin-records>=1.0.0` for inference API support
  - [ ] Verify SDK version supports `pc.inference.embed()` method
  - [ ] Run `poetry lock` and `poetry install` to update lockfile

- [ ] **Task 2: Extend Service Configuration** (AC: #2)
  - [ ] Add Pinecone settings to `config.py`:
    - `pinecone_api_key: SecretStr` (required for Pinecone operations)
    - `pinecone_environment: str` (e.g., "us-east-1")
    - `pinecone_index_name: str` (default: "farmer-power-rag")
    - `pinecone_embedding_model: str` (default: "multilingual-e5-large")
  - [ ] Add batch configuration:
    - `embedding_batch_size: int = 96` (Pinecone limit)
    - `embedding_max_tokens: int = 1024` (per text limit)
  - [ ] Add `pinecone_enabled` property to check if API key is configured

- [ ] **Task 3: Create Embedding Domain Models** (AC: #3, #10)
  - [ ] Create `services/ai-model/src/ai_model/domain/embedding.py`:
    - `EmbeddingInputType` enum: `PASSAGE`, `QUERY`
    - `EmbeddingRequest` model: texts, input_type, truncate_strategy
    - `EmbeddingResult` model: embeddings list, model used, dimensions, usage stats
  - [ ] Add `EmbeddingCostEvent` model for cost tracking (extends LlmCostEvent pattern)

- [ ] **Task 4: Create Embedding Service** (AC: #3, #4, #5, #6)
  - [ ] Create `services/ai-model/src/ai_model/services/embedding_service.py`
  - [ ] Implement `EmbeddingService` class:
    - `__init__(settings: Settings, publisher: EventPublisher)` - dependency injection
    - `async def embed_texts(texts: list[str], input_type: EmbeddingInputType) -> EmbeddingResult`
    - `async def embed_query(query: str) -> list[float]` - convenience for single query
    - `async def embed_passages(passages: list[str]) -> list[list[float]]` - convenience for documents
  - [ ] Implement automatic batching for lists exceeding 96 texts
  - [ ] Configure Pinecone client with `pc.inference.embed()` method
  - [ ] Set `input_type` parameter for E5 model prompting

- [ ] **Task 5: Implement Retry Logic** (AC: #7)
  - [ ] Add tenacity retry decorator to embed methods:
    - Max attempts: 3
    - Exponential backoff: 1s, 2s, 4s
    - Retry on: connection errors, rate limit (429), server errors (5xx)
  - [ ] Log retry attempts with structlog
  - [ ] Emit warning telemetry on retry

- [ ] **Task 6: Implement Cost Tracking** (AC: #8)
  - [ ] Create `EmbeddingCostEvent` Pydantic model in `domain/embedding.py`:
    - `id: str` - UUID
    - `timestamp: datetime`
    - `request_id: str` - correlation ID
    - `texts_count: int` - number of texts embedded
    - `tokens_total: int` - estimated tokens (chars / 4)
    - `model: str` - embedding model used
    - `knowledge_domain: str | None` - for attribution
    - `success: bool`
  - [ ] Create `EmbeddingCostEventRepository` in `infrastructure/repositories/`
  - [ ] Persist to MongoDB collection `ai_model.embedding_cost_events`
  - [ ] **NO gRPC service extension** - CostService is LLM-specific; Dashboard (Epic 9) is backlog
  - [ ] **NO DAPR pub/sub** - follows Story 0.75.5 architecture decision
  - [ ] **Cost is informational** - Pinecone Inference is included in index pricing (no separate billing)

- [ ] **Task 7: Create Unit Tests** (AC: #9)
  - [ ] Create `tests/unit/ai_model/services/test_embedding_service.py`
  - [ ] Test single text embedding (2 tests)
  - [ ] Test batch embedding within limit (3 tests)
  - [ ] Test batch embedding exceeding limit - auto-chunking (3 tests)
  - [ ] Test passage vs query input types (3 tests)
  - [ ] Test retry on transient errors (3 tests)
  - [ ] Test cost event emission (3 tests)
  - [ ] Test configuration validation (3 tests)

- [ ] **Task 8: CI Verification** (AC: #11)
  - [ ] Run lint checks: `ruff check . && ruff format --check .`
  - [ ] Run unit tests locally with mocked Pinecone
  - [ ] Push to feature branch and verify CI passes
  - [ ] E2E CI: N/A (embedding service doesn't modify Docker services)

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.12: RAG Embedding Configuration"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-12-rag-embedding-configuration
  ```

**Branch name:** `feature/0-75-12-rag-embedding-configuration`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-12-rag-embedding-configuration`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.12: RAG Embedding Configuration" --base main`
- [ ] CI passes on PR (including lint and unit tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-12-rag-embedding-configuration`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src:services/ai-model/src" pytest tests/unit/ai_model/services/test_embedding_service.py -v
```
**Output:**
```
(paste test summary here - e.g., "24 passed in 2.15s")
```

### 2. E2E Tests (OPTIONAL for this story)

> This story adds embedding service but doesn't modify Docker services.
> E2E validation will be covered by Story 0.75.13b (vectorization pipeline).

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/0-75-12-rag-embedding-configuration

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-12-rag-embedding-configuration --limit 3
```
**CI Run ID:** _______________
**CI Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### CRITICAL: Pinecone Inference API Pattern (NOT OpenAI)

**This story uses Pinecone Inference API, NOT a separate embedding provider.**

Key benefits of this approach:
- **Single API**: Pinecone handles both embedding AND vector storage
- **No separate OpenAI API key**: Embedding is included in Pinecone service
- **Simplified architecture**: One client, one billing, one set of credentials

### Pinecone SDK v5+ Pattern (2025)

**IMPORTANT: The Pinecone Python SDK v8 (latest) requires Python 3.10+.**

```python
from pinecone import Pinecone, EmbedModel

# Initialize client
pc = Pinecone(api_key=settings.pinecone_api_key.get_secret_value())

# Embed passages (for documents)
embeddings = pc.inference.embed(
    model=EmbedModel.Multilingual_E5_Large,  # Built-in enum
    inputs=["Your document text here", "Another document"],
    parameters={
        "input_type": "passage",  # CRITICAL: E5 requires this for documents
        "truncate": "END",        # Truncate long texts at end
    },
)

# Embed queries (for search)
query_embedding = pc.inference.embed(
    model=EmbedModel.Multilingual_E5_Large,
    inputs=["user search query"],
    parameters={
        "input_type": "query",  # CRITICAL: E5 requires this for queries
        "truncate": "END",
    },
)
```

### Why multilingual-e5-large?

| Model | Dimension | Context | Multilingual | Use Case |
|-------|-----------|---------|--------------|----------|
| `multilingual-e5-large` | 1024 | 512 tokens | Yes (100+ languages) | Swahili/English RAG content |
| `text-embedding-3-small` | 1536 | 8192 tokens | Limited | English-only content |

**Reference:** [Pinecone E5 Guide](https://www.pinecone.io/learn/the-practitioners-guide-to-e5/)

### Batch Limits

| Limit | Value | Handling |
|-------|-------|----------|
| Max texts per request | 96 | Auto-chunk into batches |
| Max tokens per text | 1024 | Truncate at END |
| Recommended batch size | 50-96 | Balance throughput vs latency |

### Input Type Parameter (E5 Requirement)

**E5 models require specifying input type for optimal embeddings:**

| Operation | `input_type` | Why |
|-----------|--------------|-----|
| Document embedding | `"passage"` | E5 trained with passage prompts |
| Query embedding | `"query"` | E5 trained with query prompts |

**Failure to set this correctly will degrade retrieval accuracy!**

### Service Interface (Contract for Story 0.75.13b)

```python
class EmbeddingService:
    """Embedding service using Pinecone Inference API."""

    async def embed_texts(
        self,
        texts: list[str],
        input_type: EmbeddingInputType = EmbeddingInputType.PASSAGE,
    ) -> EmbeddingResult:
        """Embed multiple texts with automatic batching.

        Args:
            texts: List of texts to embed (any length - will be batched)
            input_type: Whether texts are passages (documents) or queries

        Returns:
            EmbeddingResult with embeddings, dimensions, and usage stats
        """

    async def embed_query(self, query: str) -> list[float]:
        """Convenience method for single query embedding.

        Args:
            query: Search query text

        Returns:
            Single embedding vector (1024 dimensions for E5)
        """

    async def embed_passages(self, passages: list[str]) -> list[list[float]]:
        """Convenience method for document passages.

        Args:
            passages: List of document chunks/passages

        Returns:
            List of embedding vectors
        """
```

### Cost Tracking Architecture (IMPORTANT)

**Key Architecture Decisions (from Story 0.75.5):**

| Decision | Rationale |
|----------|-----------|
| **NO DAPR pub/sub** | No services subscribe to cost events |
| **NO gRPC CostService extension** | CostService is LLM-specific; Epic 9 (Dashboard) is backlog |
| **MongoDB persistence only** | Informational tracking for future Dashboard |
| **No cost_usd field** | Pinecone Inference is included in index pricing |

```python
class EmbeddingCostEvent(BaseModel):
    """Embedding cost event for tracking/attribution.

    Stored in: ai_model.embedding_cost_events
    Purpose: Visibility and attribution (not billing - Pinecone Inference is free)
    """
    id: str                           # UUID
    timestamp: datetime               # When embedding completed
    request_id: str                   # Correlation ID for tracing
    model: str                        # "multilingual-e5-large"
    texts_count: int                  # Number of texts embedded
    tokens_total: int                 # Estimated tokens (chars / 4)
    knowledge_domain: str | None      # For per-domain attribution
    success: bool
```

**Why no `cost_usd`?** Pinecone Inference API embedding is **included in index pricing** - there's no separate per-embed charge to track.

### Future Work: gRPC CostService Extension

> **OUT OF SCOPE for this story.** When Epic 9 (Platform Admin Dashboard) is implemented, extend `CostService` to include embedding costs.

**Required changes (future story):**
- Add `GetEmbeddingCostSummary` RPC to `CostService` in `ai_model.proto`
- Add `GetCostByKnowledgeDomain` RPC for embedding attribution
- Query `ai_model.embedding_cost_events` collection
- Consider unified cost view combining LLM + embedding costs

### Directory Structure After Story

```
services/ai-model/src/ai_model/
├── domain/
│   ├── embedding.py                    # EmbeddingInputType, EmbeddingRequest, EmbeddingResult, EmbeddingCostEvent (NEW)
│   └── ...
├── infrastructure/repositories/
│   ├── embedding_cost_repository.py    # EmbeddingCostEventRepository (NEW)
│   └── ...
├── services/
│   ├── embedding_service.py            # EmbeddingService (NEW)
│   └── ...
└── config.py                           # Extended with Pinecone settings

tests/unit/ai_model/
├── domain/
│   └── test_embedding.py               # Domain model tests (NEW)
├── infrastructure/repositories/
│   └── test_embedding_cost_repository.py  # Repository tests (NEW)
└── services/
    └── test_embedding_service.py       # Service tests (NEW)
```

### Previous Story Intelligence (Story 0.75.11)

**Key learnings from CLI story:**

1. **Retry Pattern** - Use tenacity with exponential backoff for all external API calls
2. **Async Patterns** - All I/O must be async - embedding is I/O bound
3. **Test Mocking** - Mock external APIs (Pinecone) in unit tests, not integration tests
4. **Settings Pattern** - Use Pydantic Settings with `SecretStr` for API keys

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Using OpenAI embeddings API | Use Pinecone Inference (single API) |
| Synchronous embedding calls | Async with `await pc.inference.embed()` |
| Hardcoding model name | Use `settings.pinecone_embedding_model` |
| Missing input_type | ALWAYS set `input_type` for E5 models |
| Single text per request | Batch up to 96 texts for efficiency |
| Ignoring retry logic | Use tenacity for transient failures |

### Dependencies

**Required Stories (complete):**
- Story 0.75.9: RagDocument Pydantic model (provides domain models)
- Story 0.75.10d: Semantic chunking (provides chunks to embed)

**Dependent Stories (next):**
- Story 0.75.13: RAG Vector Storage (Pinecone client for upsert)
- Story 0.75.13b: RAG Vectorization Pipeline (orchestrates embed → store)

### References

- [Source: `_bmad-output/architecture/ai-model-architecture/rag-engine.md`] - RAG architecture overview
- [Source: `_bmad-output/architecture/ai-model-architecture/rag-document-api.md`] - Document vectorization flow
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md#story-07512`] - Story requirements
- [Source: `services/ai-model/src/ai_model/config.py`] - Settings pattern reference
- [Source: `services/ai-model/src/ai_model/domain/cost_event.py`] - Cost event pattern reference
- [Source: `_bmad-output/sprint-artifacts/0-75-11-cli-rag-document.md`] - Previous story learnings
- [External: Pinecone Inference API](https://docs.pinecone.io/guides/inference/understanding-inference)
- [External: E5 Model Guide](https://www.pinecone.io/learn/the-practitioners-guide-to-e5/)

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
