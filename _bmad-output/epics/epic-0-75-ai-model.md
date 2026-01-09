# Epic 0.75: AI Model Foundation

Cross-cutting AI infrastructure that enables all AI-powered domain models. These stories establish the LLM gateway, agent framework, RAG engine, and prompt management patterns used across Knowledge Model, Action Plan Model, and Conversational AI.

**Priority:** P1

**Dependencies:** Epic 0 (Infrastructure), Epic 1 (Plantation Model), Epic 2 (Collection Model)

**Blocks:** Epic 5 (Knowledge Model), Epic 6 (Action Plans), Epic 8 (Voice Advisor), Epic 12 (Engagement Model)

**FRs covered:** FR45, FR46, FR47, FR48

---

## Overview

The AI Model is the most complex and strategic module of the Farmer Power Platform. It provides:

- **LLM Gateway** — OpenRouter integration with cost management and model routing
- **Agent Framework** — Five agent types (Extractor, Explorer, Generator, Conversational, Tiered-Vision) with LangGraph orchestration
- **RAG Infrastructure** — Document storage, embedding, vector storage, retrieval, and ranking
- **Prompt Management** — MongoDB storage with versioning and CLI tooling
- **Event-Driven Architecture** — DAPR pub/sub for agent triggering and result publishing
- **LangSmith Integration** — Dev/eval observability for LangGraph workflow debugging and golden sample evaluation (disabled in production)

### Key Principle: Generic Agent Framework

**The agent framework is generic — no code is created for specific analyzers.**

| Epic 0.75 Provides | Domain Epics Provide |
|--------------------|----------------------|
| Agent types (Extractor, Explorer, etc.) | Agent configurations (YAML) |
| LangGraph workflows | Prompts per agent |
| RAG infrastructure | Knowledge domain content |
| CLI to deploy configs | Specific agent configs (disease-diagnosis, weather-analyzer, etc.) |

Specific agents like `disease-diagnosis` or `weather-analyzer` are **configurations** of the generic Explorer type — deployed via CLI, not coded as separate implementations.

### Testing Strategy

All AI agents require **golden sample testing** to validate accuracy. During development, LLM-generated **synthetic samples** bootstrap testing without agronomist dependency. Expert-validated samples are collected post-platform-completion for production readiness.

**Reference:** `_bmad-output/test-design-system-level.md` § *Synthetic Golden Sample Generation*

### CLI Standards

All CLI tools in this epic follow consistent command vocabulary:

| Command | Purpose | Used By |
|---------|---------|---------|
| `deploy` | Upload/create new config | All CLIs |
| `validate` | Validate config file | All CLIs |
| `list` | List all configs | All CLIs |
| `get` | Get specific config | All CLIs |
| `stage` | Stage new version | All CLIs |
| `promote` | Promote staged → active | All CLIs |
| `rollback` | Revert to previous | All CLIs |
| `versions` | List version history | All CLIs |
| `enable` | Enable at runtime | `fp-agent-config` only |
| `disable` | Disable at runtime | `fp-agent-config` only |
| `job-status` | Poll async job progress | `fp-knowledge` only |

**Async Operations:**
- `--async` flag returns immediately with `job_id`
- `job-status {job_id}` polls progress
- Progress output: `[##########..........] 50% (500/1000 chunks)`

**Error Handling:**
- Exit code 0 = success, 1 = error
- Error messages format: `Error: <message>` to stderr
- `--verbose` flag for detailed output
- `--quiet` flag for minimal output (errors only)

### Success Metrics

Epic 0.75 is considered complete when:

| Metric | Target | Validation |
|--------|--------|------------|
| Agent golden samples | All 5 agent types pass ≥90% of synthetic samples | Story 0.75.17-22 test suites |
| RAG retrieval accuracy | Top-5 results contain expected document ≥85% | Story 0.75.14 test suite |
| E2E pipeline | Weather extraction flow passes end-to-end | Story 0.75.18 |
| LLM cost tracking | Tracked cost within ±5% of actual OpenRouter invoice | Manual verification |
| RAG retrieval latency | < 500ms p95 | Load test or production metrics |
| Tiered-Vision skip rate | ≥35% of images skip Tier 2 | Story 0.75.22 metrics |

---

## Stories

### Story 0.75.1: AI Model Setup

**Story File:** Not yet created | Status: Backlog

As a **platform operator**,
I want the AI Model service deployed with DAPR sidecar and basic infrastructure,
So that AI workflows can be built on a solid foundation.

**Scope:**
- Python FastAPI + grpcio service scaffold
- DAPR sidecar integration
- MongoDB connection
- Health endpoints (`/health`, `/ready`)
- OpenTelemetry tracing setup
- Proto package scaffold:
  - Create `proto/ai_model/v1/ai_model.proto`
  - Package declaration: `farmer_power.ai_model.v1`
  - `HealthService` RPCs (health check endpoints)

**Note:** This story creates the proto file structure. Story 0.75.10 adds RAG document definitions to the same proto file.

---

### Story 0.75.2: Pydantic Model for Prompt + Mongo Repository

**Story File:** `_bmad-output/sprint-artifacts/0-75-2-pydantic-model-prompt-mongo-repository.md` | Status: Ready for Dev

As a **developer**,
I want Pydantic models and repository pattern for prompt storage,
So that prompts are type-safe and properly managed in MongoDB.

**Scope:**
- `Prompt` Pydantic model with versioning fields
- `PromptRepository` with CRUD operations
- MongoDB collection: `ai_model.prompts`
- Prompt schema: `prompt_id`, `agent_id`, `version`, `status`, `content`, `metadata`

**Key Decision:** Single `prompts` collection with `prompt_type` discriminator field. All 5 agent types share one collection. See `key-decisions.md`.

---

### Story 0.75.3: Pydantic Model for Agent Configuration + Mongo Repository

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want Pydantic models and repository pattern for agent configuration,
So that agent configs are type-safe and properly managed in MongoDB.

**Scope:**
- `AgentConfig` Pydantic model matching architecture spec
- `AgentConfigRepository` with CRUD operations
- MongoDB collection: `ai_model.agent_configs`
- Support for all 5 agent types: extractor, explorer, generator, conversational, tiered-vision
- LLM configuration fields per agent (model, temperature, max_tokens, fallback chain)

**Key Decision:** Single `agent_configs` collection with `agent_type` discriminator field. Pydantic discriminated unions handle 5 agent types. See `key-decisions.md`.

---

### Story 0.75.4: Source Cache for Agent Types and Prompt Config

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want in-memory caching with MongoDB change streams for agent and prompt configs,
So that configuration lookups are fast without stale data.

**Scope:**
- Extract cache pattern from Collection Model (`SourceConfigService`) into shared library:
  - Create `libs/fp-common/fp_common/cache/mongo_change_stream_cache.py`
  - Implement `MongoChangeStreamCache` abstract base class (ADR-013)
- Refactor Collection Model to use the shared base class
- Implement AI Model caches using the shared base class:
  - `AgentConfigCache` for `agent_configs` collection
  - `PromptCache` for `prompts` collection
- Change stream listeners for real-time invalidation
- Startup cache warming from MongoDB
- OpenTelemetry metrics for cache hits/misses/invalidations

**Reference:** ADR-013 (AI Model Configuration Cache)

---

### Story 0.75.5: OpenRouter LLM Gateway with Cost Observability

**Story File:** Not yet created | Status: Backlog

As a **developer implementing AI agents**,
I want a unified LLM gateway with cost tracking, observability, and resilience,
So that agents can reliably call LLMs with automatic retry, fallback, and full cost visibility.

**Scope:**

**LLM Gateway Core:**
- OpenRouter API integration
- Execute LLM requests per agent configuration (model + fallback chain)
- Validate model availability via OpenRouter API
- Retry with exponential backoff
- Fallback execution when primary model fails

**Cost Observability:**
- Cost tracking per request (input/output tokens, USD)
- Cost event emission via DAPR pub/sub (`ai.cost.recorded`)
- Cost persistence to MongoDB collection: `ai_model.llm_cost_events`
- gRPC `CostService` API for querying costs (contract for Epic 5 dashboard)
- Budget threshold alerting (configurable daily/monthly limits)

**Cost Event Schema:**
```python
class LlmCostEvent(BaseModel):
    timestamp: datetime
    request_id: str           # Correlation ID
    agent_type: str           # "extractor", "explorer", "generator", etc.
    agent_id: str             # Specific agent configuration ID
    model: str                # "gpt-4o-mini", "claude-3-5-sonnet", etc.
    tokens_in: int
    tokens_out: int
    cost_usd: Decimal
    factory_id: Optional[str] # For future per-factory attribution
    success: bool             # Whether the request succeeded
    retry_count: int          # Number of retries before success/failure
```

**gRPC CostService API (Contract for Epic 5 Dashboard):**
```protobuf
service CostService {
    // Summary queries
    rpc GetDailyCostSummary(DateRangeRequest) returns (DailyCostSummaryResponse);
    rpc GetCurrentDayCost(Empty) returns (CostSummary);

    // Breakdown queries
    rpc GetCostByAgentType(DateRangeRequest) returns (CostByAgentTypeResponse);
    rpc GetCostByModel(DateRangeRequest) returns (CostByModelResponse);

    // Alerts
    rpc GetCostAlerts(Empty) returns (CostAlertsResponse);
    rpc ConfigureCostThreshold(ThresholdConfig) returns (Empty);
}
```

**OpenTelemetry Metrics:**
- `llm_request_cost_usd` (histogram) - Cost per request
- `llm_tokens_total` (counter) - Total tokens by model
- `llm_daily_cost_usd` (gauge) - Running daily total
- `llm_cost_alert_triggered` (counter) - Alert trigger count

**Testing Requirements:**
- Unit tests for retry logic with simulated transient failures (429, 503)
- Unit tests for exponential backoff timing
- Integration test for fallback chain execution (primary fails → fallback succeeds)
- Test that cost tracking works even after retries/fallback
- Test cost event persistence to MongoDB
- Test gRPC CostService query methods
- Test budget threshold alerting triggers

**Note:** The Platform Admin Dashboard UI for cost visualization is defined in Epic 9 (Story 9.6). This story provides the backend infrastructure and API contract.

---

### Story 0.75.6: CLI to Manage Prompt Type Configuration

**Story File:** Not yet created | Status: Backlog

As a **platform operator**,
I want a CLI to manage prompt configurations,
So that prompts can be deployed and versioned without code changes.

**Scope:**
- `fp-prompt-config` CLI using Typer
- Commands: `deploy`, `validate`, `list`, `get`, `stage`, `promote`, `rollback`, `versions`
- YAML-based prompt definition files
- Version management (staged, active, archived)
- Built-in `--help` with usage examples for each command

**Validation Rules:**
- `agent_id` validation: When publishing with status `staged` or `active`, validate that the referenced `agent_id` exists in `agent_configs` collection
- `draft` status prompts skip agent validation (allows prompt development before agent config)
- See: `_bmad-output/architecture/ai-model-architecture/prompt-management.md` § *Prompt-Agent Validation Rules*

**Command vocabulary:** See CLI Standards below.

---

### Story 0.75.7: CLI to Manage Agent Configuration

**Story File:** Not yet created | Status: Backlog

As a **platform operator**,
I want a CLI to manage agent configurations,
So that agents can be deployed and updated without code changes.

**Scope:**
- `fp-agent-config` CLI using Typer
- Commands: `deploy`, `validate`, `list`, `get`, `stage`, `promote`, `rollback`, `versions`, `enable`, `disable`
- YAML-based agent definition files
- Validation against agent type schemas
- Built-in `--help` with usage examples for each command

**Command vocabulary:** See CLI Standards below.

---

### Story 0.75.8: Event Flow, Subscriber, and Publisher

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want DAPR pub/sub integration for agent triggering and result publishing,
So that agents can be invoked via events and publish results.

**Scope:**
- DAPR pub/sub component configuration
- Event subscription handlers
- Event publisher utilities
- Dead letter queue for failed events (ADR-006)
- Topics: `ai.agent.{agent_id}.requested`, `ai.agent.{agent_id}.completed`

---

### Story 0.75.8b: MCP Client Integration for Agent Workflows

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want AI Model agents to use existing MCP client infrastructure,
So that agents can fetch data from Collection, Plantation, and other domain models.

**Scope:**
- Integrate existing `libs/fp-common/fp_common/mcp/` with AI Model:
  - `GrpcMcpClient` - already exists
  - `McpToolRegistry` - already exists
  - `GrpcMcpTool` - already exists (LangChain compatible)
- Register MCP servers at AI Model startup based on agent configurations
- Parse `mcp_sources` from agent config and register servers:
  ```yaml
  mcp_sources:
    - server: collection
      tools: [get_document, get_farmer_context]
    - server: plantation
      tools: [get_plantation_details]
  ```
- Make registered MCP tools available to LangGraph agent workflows
- Discover tools from registered servers on agent initialization

**Note:** MCP client infrastructure already exists in fp-common. This story integrates it with AI Model agent workflows.

---

### Story 0.75.9: Pydantic Model for RAG Document Storage

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want Pydantic models for RAG document storage,
So that knowledge documents are type-safe and properly structured.

**Scope:**
- `RagDocument` Pydantic model
- `RagChunk` model for document chunks
- `SourceFile` model for PDF extraction metadata (method, confidence, page count)
- MongoDB collection: `ai_model.rag_documents`
- Support for versioning and status (staged, active, archived)

---

### Story 0.75.10: gRPC Model for RAG Document

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want gRPC service definitions for RAG document management,
So that documents can be managed via API.

**Scope:**
- Add RAG definitions to `proto/ai_model/v1/ai_model.proto`:
  - `RagDocument`, `RagChunk` messages
  - `RagDocumentService` with CRUD RPCs
- gRPC service implementation
- DAPR service invocation integration
- Document metadata storage in MongoDB
- Document status management (staged, active, archived)

**Note:** This story handles document metadata only. PDF ingestion (0.75.10b) and vectorization (0.75.13b) are separate concerns.

---

### Story 0.75.10b: Basic PDF/Markdown Extraction

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want basic document extraction for RAG documents,
So that digital PDF and Markdown content can be extracted and stored.

**Scope:**
- Document format detection (Markdown, PDF)
- PDF text extraction using PyMuPDF (for digital/text-based PDFs)
- Markdown parsing
- Azure Blob Storage integration for original file storage
- Extraction metadata (method used, page count)

**Progress Feedback:**
- Return `job_id` for async tracking
- Status endpoint: `GET /jobs/{job_id}` returns `{status, progress_percent, pages_processed, total_pages}`
- Support `--async` flag in CLI for background execution
- Log progress at 10% intervals

**Dependencies:** Story 0.75.10 (gRPC Model)

---

### Story 0.75.10c: Azure Document Intelligence Integration

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want Azure Document Intelligence for scanned PDF extraction,
So that scanned/image-based PDFs can be processed with OCR.

**Scope:**
- Azure Document Intelligence API integration
- API key and endpoint configuration (Pydantic Settings)
- Automatic detection of scanned vs digital PDFs
- Fallback to PyMuPDF if Azure DI unavailable
- Cost tracking per Azure DI call
- Confidence scoring from Azure DI response

**Progress Feedback:**
- Reuse `job_id` tracking from Story 0.75.10b
- Azure DI is async by nature — poll Azure operation status
- Surface Azure operation progress in job status endpoint
- Log OCR page completion events

**Dependencies:** Story 0.75.10b (Basic Extraction)

---

### Story 0.75.10d: Semantic Chunking

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want semantic chunking for extracted document content,
So that documents are split into meaningful chunks for vectorization.

**Scope:**
- Content chunking by semantic boundaries (headings, paragraphs)
- Configurable chunk size and overlap
- Chunk storage in MongoDB with parent document reference
- Chunk metadata (position, section title, word count)

**Progress Feedback:**
- Reuse `job_id` tracking from Story 0.75.10b
- Status includes `{chunks_created, estimated_total_chunks}`
- Chunking is fast but report progress for large documents (100+ pages)
- Log chunk creation milestones (every 50 chunks)

**Dependencies:** Story 0.75.10c (Azure DI)

**Note:** Chunks are stored in MongoDB but NOT vectorized. Vectorization is handled by Story 0.75.13b after embedding/vector infrastructure is ready.

---

### Story 0.75.11: CLI for RAG Document

**Story File:** Not yet created | Status: Backlog

As a **platform operator**,
I want a CLI to manage RAG knowledge documents,
So that agronomists can upload and version knowledge content.

**Scope:**
- `fp-knowledge` CLI using Typer
- Commands: `deploy`, `validate`, `list`, `get`, `stage`, `promote`, `rollback`, `versions`
- Thin CLI wrapper calling gRPC document API
- Chunking configuration passthrough
- Built-in `--help` with usage examples for each command

**Command vocabulary:** See CLI Standards below.

---

### Story 0.75.12: RAG Embedding Configuration (Pinecone Inference)

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want Pinecone Inference configured for embedding generation,
So that documents are automatically vectorized when stored in Pinecone.

**Scope:**
- Configure Pinecone Inference embedding model (e.g., `multilingual-e5-large`)
- No separate OpenAI API call needed — Pinecone handles embedding generation
- Embedding model selection per knowledge domain (if needed)
- Query embedding generation for similarity search (also via Pinecone Inference)

**Benefits:**
- Single API (Pinecone) instead of two (OpenAI + Pinecone)
- No separate OpenAI API key required
- Simplified architecture

---

### Story 0.75.13: RAG Vector Storage (Pinecone Repository)

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want a Pinecone client/repository for vector operations,
So that embeddings can be stored and queried efficiently.

**Scope:**
- Pinecone Python SDK integration and connection management
- `PineconeVectorStore` class with async CRUD operations:
  - `upsert(vectors)` - store vectors with metadata
  - `query(embedding, top_k)` - similarity search
  - `delete(ids)` - remove vectors
- Index configuration per knowledge domain
- Namespace management (staged, active) for A/B testing
- Metadata storage with vectors (doc_id, chunk_id, domain)

**Note:** This is the low-level Pinecone client. The orchestration of "embed then store" is handled by Story 0.75.13b.

---

### Story 0.75.13b: RAG Vectorization Pipeline (Orchestration)

**Story File:** `_bmad-output/sprint-artifacts/0-75-13b-rag-vectorization-pipeline.md` | Status: Done

As a **developer**,
I want a vectorization pipeline that coordinates embedding generation and vector storage,
So that document chunks become searchable after ingestion.

**Scope:**
- `VectorizationPipeline` class that orchestrates the full flow:
  1. Read chunks from MongoDB (created by Story 0.75.10b)
  2. Call Embedding Service (Story 0.75.12) to generate vectors
  3. Call Vector Storage (Story 0.75.13) to store in Pinecone
  4. Update document status to `vectorized` in MongoDB
- Batch processing for efficiency (configurable batch size)
- Error handling and retry for failed chunks
- Progress tracking and logging

**Progress Feedback (Critical - longest running operation):**
- Return `job_id` for async tracking (separate from ingestion job)
- Detailed status: `{status, chunks_total, chunks_embedded, chunks_stored, failed_count, eta_seconds}`
- Status endpoint: `GET /vectorization-jobs/{job_id}`
- Batch progress events published to DAPR pub/sub for monitoring
- CLI `fp-knowledge promote --async` returns immediately with job_id
- CLI `fp-knowledge job-status {job_id}` polls vectorization progress
- Log progress every batch (default: 100 chunks)

**Dependencies:** Stories 0.75.10d, 0.75.12, 0.75.13

**Trigger:** Called when document is promoted from `staged` to `active` status.

**Why separate from 0.75.13?** Separation of concerns — 0.75.13 is the Pinecone client (reusable), 0.75.13b is the business workflow (specific to document lifecycle).

---

### Story 0.75.13c: RAG Vectorization gRPC Wiring

**Story File:** `_bmad-output/sprint-artifacts/0-75-13c-rag-vectorization-grpc-wiring.md` | Status: Backlog

As a **developer using the RAG API**,
I want the VectorizationPipeline exposed via gRPC endpoints,
So that documents can be vectorized through the standard API and CLI.

**Context:** Story 0.75.13b created the `VectorizationPipeline` class but deferred gRPC wiring (Task 6b). This story completes the integration.

**Scope:**
- Extend `RAGDocumentServiceServicer` to accept all dependencies (repositories, workflows, pipeline)
- Wire dependencies in `grpc_server.py` (create EmbeddingService, PineconeVectorStore, VectorizationPipeline)
- Implement `VectorizeDocument` RPC (sync and async modes)
- Implement `GetVectorizationJob` RPC (status polling)
- CLI integration: `fp-knowledge vectorize`, `fp-knowledge job-status`
- Unit tests and E2E test for vectorization flow

**Dependencies:** Story 0.75.13b (VectorizationPipeline class)

**Enables:** Story 0.75.14 (RAG Retrieval can query vectorized content)

---

### Story 0.75.13d: Vectorization Job Persistence (Redis/MongoDB)

**Story File:** Not yet created | Status: Backlog

As a **platform operator**,
I want vectorization job status persisted to Redis or MongoDB,
So that job tracking survives pod restarts and works across multiple replicas.

**Context:** Story 0.75.13c implemented in-memory job tracking (`self._jobs: dict[str, VectorizationResult]`) which has the following production limitations documented in `vectorization_pipeline.py`:
1. Job status is lost on pod restart
2. With multiple replicas, `get_job_status()` may miss jobs on other pods
3. No automatic cleanup - jobs accumulate over time

**Scope:**
- Migrate job storage from in-memory dict to Redis (preferred) or MongoDB
- Implement `VectorizationJobRepository` with CRUD operations
- Job TTL configuration (default: 24 hours) for automatic cleanup
- Update `VectorizationPipeline` to use repository instead of in-memory dict
- Update gRPC `GetVectorizationJob` to query from persistent storage
- Support job listing/filtering (e.g., by status, document_id)

**Acceptance Criteria:**
1. Job status survives AI Model pod restart
2. Job status queryable from any replica in multi-replica deployment
3. Jobs automatically expire after configurable TTL
4. CLI `fp-knowledge job-status` works across pod restarts
5. Unit tests for repository operations
6. Integration test for job persistence across restarts (if feasible)

**Dependencies:** Story 0.75.13c (Vectorization gRPC Wiring)

**Note:** This is a production hardening story. The in-memory implementation from 0.75.13c is sufficient for single-replica development environments.

---

### Story 0.75.14: RAG Retrieval Service

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want a retrieval service for RAG queries,
So that agents can find relevant knowledge.

**Prerequisites:**
- Story 0.75.12 (Embedding Service) complete
- Story 0.75.13 (Pinecone Repository) complete
- Pinecone credentials in `.env` (PINECONE_API_KEY, PINECONE_INDEX_NAME)

**Scope:**
- Similarity search with configurable top-k
- Confidence threshold filtering
- Multi-domain queries
- Query embedding generation (using EmbeddingService from 0.75.12)

**Golden Sample Test Suite (MANDATORY):**

The dev agent implementing this story will:

1. **Create seed documents** (`tests/golden/rag/seed_documents.json`):
   - Write 5+ realistic tea farming documents directly (no external LLM call needed - dev agent generates content)
   - Include at least 2 domains: disease, weather
   - Each document 200-500 words with realistic agronomic content

2. **Create golden samples** (`tests/golden/rag/retrieval/samples.json`):
   - Write 2-3 queries per seed document directly (dev agent generates queries)
   - Minimum 10 samples total

3. **Create test suite** (`tests/golden/rag/retrieval/test_retrieval_golden.py`):
   - Test that known queries return expected document chunks
   - Test confidence threshold filtering
   - Test multi-domain retrieval accuracy
   - Achieve ≥85% retrieval accuracy

**Test Isolation (CRITICAL):**

Each test suite must be **self-contained** - no dependency on other test suites having run first.

```python
# tests/golden/rag/retrieval/conftest.py
@pytest.fixture(scope="module")
def seeded_pinecone(pinecone_client, embedding_service):
    """Setup: Upload seeds to Pinecone. Teardown: Delete them."""
    namespace = "golden-retrieval"  # Unique namespace for this test suite

    # Setup: Load seeds and upload to Pinecone
    seeds = load_seed_documents("tests/golden/rag/seed_documents.json")
    vectors = embed_and_upload(seeds, namespace)

    yield namespace

    # Teardown: Clean up vectors
    pinecone_client.delete(namespace=namespace, delete_all=True)
```

**Why self-contained?**
- CI runs test suites independently (no guaranteed order)
- Parallel test execution must not interfere
- Each run starts with clean state

**Directory Structure:**
```
tests/golden/rag/
├── seed_documents.json          # Created in this story, reused by 0.75.15+
├── retrieval/
│   ├── conftest.py              # Setup/teardown fixtures
│   ├── samples.json             # Queries + expected results
│   └── test_retrieval_golden.py # Golden sample tests
```

**Reusable:** The seed documents JSON file is reused by Stories 0.75.15, 0.75.17, 0.75.19, 0.75.20, 0.75.21, and 0.75.22 (each with its own namespace and setup/teardown).

---

### Story 0.75.15: RAG Ranking Logic

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want ranking logic for RAG results,
So that the most relevant documents are prioritized.

**Prerequisites:**
- Story 0.75.14 (RAG Retrieval Service) complete
- Seed documents file exists (`tests/golden/rag/seed_documents.json` created by 0.75.14)

**Scope:**
- Re-ranking based on relevance scores
- Domain-specific boosting
- Recency weighting (optional)
- Result deduplication

**Golden Sample Test Suite (MANDATORY):**

The dev agent implementing this story will:

1. **Reuse seed documents file from Story 0.75.14**:
   - DO NOT create new seed documents
   - Read from existing `tests/golden/rag/seed_documents.json`
   - Test suite uploads seeds to its OWN namespace (see Test Isolation below)

2. **Create ranking samples** (`tests/golden/rag/ranking/samples.json`):
   - Write queries that test ranking behavior directly (dev agent generates queries)
   - Include queries where domain boosting should affect results
   - Include queries to test deduplication
   - Minimum 10 samples total

3. **Create test suite** (`tests/golden/rag/ranking/test_ranking_golden.py`):
   - Test that most relevant document ranks first
   - Test domain-specific boosting effects
   - Test deduplication removes near-duplicates
   - Achieve ≥90% ranking accuracy

**Test Isolation (CRITICAL):**

This test suite must be **self-contained** - it uploads seeds itself, does not depend on Story 0.75.14 tests having run.

```python
# tests/golden/rag/ranking/conftest.py
@pytest.fixture(scope="module")
def seeded_pinecone(pinecone_client, embedding_service):
    """Setup: Upload seeds to Pinecone. Teardown: Delete them."""
    namespace = "golden-ranking"  # DIFFERENT namespace from retrieval tests

    # Setup: Load same seeds, upload to OUR namespace
    seeds = load_seed_documents("tests/golden/rag/seed_documents.json")
    vectors = embed_and_upload(seeds, namespace)

    yield namespace

    # Teardown: Clean up vectors
    pinecone_client.delete(namespace=namespace, delete_all=True)
```

**Why separate namespaces?**
- `golden-retrieval` (Story 0.75.14) and `golden-ranking` (this story) are isolated
- Tests can run in parallel without interference
- Each test suite manages its own Pinecone state

**Directory Structure:**
```
tests/golden/rag/
├── seed_documents.json          # REUSED from Story 0.75.14 (do not modify)
├── retrieval/                   # Created by Story 0.75.14
│   ├── conftest.py              # namespace: golden-retrieval
│   ├── samples.json
│   └── test_retrieval_golden.py
├── ranking/                     # Created in THIS story
│   ├── conftest.py              # namespace: golden-ranking
│   ├── samples.json             # Ranking-specific queries
│   └── test_ranking_golden.py   # Ranking golden sample tests
```

**Why reuse seed documents file?** Same seed documents ensure consistent test data. Each test suite uploads independently to its own namespace, so there's no runtime dependency between test suites.

---

### Story 0.75.16: LangGraph SDK Integration & Base Workflows

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want LangGraph base workflows and patterns,
So that agents can reuse common orchestration logic.

**Scope:**
- LangGraph SDK integration
- Saga pattern with compensation handlers
- MongoDB checkpointing (async via `langgraph-checkpoint-mongodb` package)
- Conditional routing utilities
- Base workflow classes for each agent type
- Error handling and retry logic

**LangSmith Integration (Dev/Eval Only):**
- Configure LangSmith tracing via environment variables:
  - `LANGCHAIN_TRACING_V2=true` (dev/eval environments only)
  - `LANGCHAIN_API_KEY` (from secrets)
  - `LANGCHAIN_PROJECT=farmer-power-ai-model`
- Visual debugging of LangGraph multi-step workflows
- Automatic trace capture for all LLM calls and tool invocations
- Integration with golden sample evaluation datasets
- **Production:** `LANGCHAIN_TRACING_V2=false` (disabled to avoid cost/latency)

**LangSmith Benefits:**
| Use Case | Value |
|----------|-------|
| Workflow debugging | Visual trace of each LangGraph node with inputs/outputs |
| Prompt iteration | Test prompt changes before deployment |
| Golden sample eval | Automated evaluation against test datasets |
| Failure analysis | Root cause analysis for failed agent runs |

**Risk:** Verify `AsyncMongoDBSaver` compatibility with LangGraph 1.0+ — there's a [known issue](https://github.com/langchain-ai/langgraph/issues/6506) with async imports. May need to use sync version or wait for fix.

**Reference:** `_bmad-output/architecture/ai-model-architecture/langgraph-workflow-orchestration.md`

---

### Story 0.75.17: Extractor Agent Implementation

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want the Extractor agent type implemented,
So that structured data can be extracted from unstructured input.

**Scope:**
- LangChain linear workflow: fetch -> extract -> validate -> normalize -> output
- Temperature: 0.1 (deterministic)
- JSON output format
- Golden sample test suite (LLM-generated synthetic samples, minimum 10)

**Note:** Synthetic samples are generated by LLM based on input/output schemas and domain context. Expert-validated samples replace synthetic samples post-platform-completion. Reuses synthetic sample generator from Story 0.75.14.

**References:**
- Agent types: `_bmad-output/architecture/ai-model-architecture/agent-types.md`
- Synthetic sample generation: `_bmad-output/test-design-system-level.md` § *Synthetic Golden Sample Generation*

---

### Story 0.75.18: E2E: Weather Observation Extraction Flow

**Story File:** Not yet created | Status: Blocked
**Blocked By:** Story 2-12 (Collection Event-Driven), Story 2-13 (Thumbnail Generation)

As a **developer**,
I want end-to-end validation of the weather extraction flow,
So that the AI Model integration is proven before building more agents.

**Scope (Revised 2026-01-09):**
1. Create weather-extractor agent configuration (YAML), inject to MongoDB via `fp-agent-config`
2. Create working prompt (YAML), inject to MongoDB via `fp-prompt-config`
3. Adapt agent_id in collection model source config (YAML), inject to MongoDB via `fp-source-config`
4. Rewrite E2E test tests/e2e/scenarios/test_05_weather_ingestion.py to work with real AI Model container (same scope as existing mock test, but with real prompt and real LLM call)

**Out of Scope (moved to Epic 2):**
- Collection Model async event refactor → Story 2-12 (GitHub #81)
- Thumbnail generation → Story 2-13 (GitHub #88)

**Acceptance Criteria:**
- Use Agent Extraction and real LLM call (openrouter.ai)
- Working extractor agent configuration in MongoDB
- Working prompt configuration in MongoDB
- Working collection model source configuration in MongoDB
- E2E test passes with real AI Model container
- AI Model container starts and passes health checks in E2E infrastructure
- E2E test passes with real AI Model container (not mock)
- Weather data extracted and stored correctly
- Plantation model updated via event flow

---

### Story 0.75.19: Explorer Agent Implementation

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want the Explorer agent type implemented,
So that data can be analyzed and patterns diagnosed.

**Scope:**
- LangGraph workflow: fetch -> context -> rag -> analyze -> output
- Temperature: 0.3
- RAG enabled by default
- Support for iterative analysis
- Golden sample test suite (LLM-generated synthetic samples, minimum 10)

**Reference:** `_bmad-output/architecture/ai-model-architecture/agent-types.md`

---

### Story 0.75.20: Generator Agent Implementation

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want the Generator agent type implemented,
So that content (plans, reports, messages) can be created.

**Scope:**
- LangGraph workflow: fetch -> context -> prioritize -> generate -> format -> output
- Temperature: 0.5 (creative)
- RAG enabled for best practices
- Multi-format output (markdown, SMS, TTS script)
- Golden sample test suite (LLM-generated synthetic samples, minimum 10)

**Reference:** `_bmad-output/architecture/ai-model-architecture/agent-types.md`

---

### Story 0.75.21: Conversational Agent Implementation

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want the Conversational agent type implemented,
So that multi-turn dialogue can be handled.

**Scope:**
- LangGraph workflow: classify -> context -> fetch -> rag -> generate -> state -> output
- Two LLM calls: intent classification + response generation (models per agent config)
- Conversation state management with MongoDB checkpointing
- Session TTL and max turns configuration
- Golden sample test suite (LLM-generated synthetic samples, minimum 10)

**Reference:** `_bmad-output/architecture/ai-model-architecture/agent-types.md`

---

### Story 0.75.22: Tiered-Vision Agent Implementation

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want the Tiered-Vision agent type implemented,
So that images can be analyzed with cost optimization.

**Scope:**
- LangGraph workflow: fetch_thumbnail -> screen -> route -> fetch_original -> diagnose -> output
- Two-tier processing: Tier 1 (fast/cheap model) -> Tier 2 (capable model) — models per agent config
- Conditional routing based on screen confidence
- 40% skip rate target, 57% cost savings at scale
- Golden sample test suite (LLM-generated synthetic samples, minimum 10)

**Routing Logic:**

| Screen Result | Confidence | Action |
|---------------|------------|--------|
| healthy | >= 0.85 | Skip Tier 2 |
| healthy | < 0.85 | Escalate to Tier 2 |
| obvious_issue | >= 0.75 | Haiku diagnosis |
| obvious_issue | < 0.75 | Escalate to Tier 2 |
| needs_expert | any | Always Tier 2 |

**Reference:** `_bmad-output/architecture/ai-model-architecture/tiered-vision-processing-cost-optimization.md`

---

## Story Summary

| #    | Story                                                    | Type           | Status  |
|------|----------------------------------------------------------|----------------|---------|
| 1    | AI Model Setup                                           | Infrastructure | Done    |
| 2    | Pydantic Model for Prompt + Mongo Repository             | Data Model     | Done    |
| 3    | Pydantic Model for Agent Configuration + Mongo Repository| Data Model     | Done    |
| 4    | Source Cache for Agent Types and Prompt Config           | Infrastructure | Done    |
| 5    | OpenRouter LLM Gateway with Cost Observability           | Infrastructure | Done    |
| 6    | CLI to Manage Prompt Type Configuration                  | Tooling        | Done    |
| 7    | CLI to Manage Agent Configuration                        | Tooling        | Done    |
| 8    | Event Flow, Subscriber, and Publisher                    | Infrastructure | Done    |
| 8b   | MCP Client Integration for Agent Workflows               | Infrastructure | Done    |
| 9    | Pydantic Model for RAG Document Storage                  | Data Model     | Done    |
| 10   | gRPC Model for RAG Document                              | API            | Done    |
| 10b  | Basic PDF/Markdown Extraction                            | RAG            | Done    |
| 10c  | Azure Document Intelligence Integration                  | RAG            | Done    |
| 10d  | Semantic Chunking                                        | RAG            | Done    |
| 11   | CLI for RAG Document                                     | Tooling        | Done    |
| 12   | RAG Embedding Configuration (Pinecone Inference)         | RAG            | Done    |
| 13   | RAG Vector Storage (Pinecone Repository)                 | RAG            | Done    |
| 13b  | RAG Vectorization Pipeline (Orchestration)               | RAG            | Done    |
| 13c  | RAG Vectorization gRPC Wiring                            | RAG            | Review  |
| 13d  | Vectorization Job Persistence (Redis/MongoDB)            | RAG            | Backlog |
| 14   | RAG Retrieval Service                                    | RAG            | Backlog |
| 15   | RAG Ranking Logic                                        | RAG            | Backlog |
| 16   | LangGraph SDK Integration & Base Workflows               | Framework      | Backlog |
| 17   | Extractor Agent Implementation                           | Agent          | Backlog |
| 18   | E2E: Weather Observation Extraction Flow                 | Validation     | Blocked |
| 19   | Explorer Agent Implementation                            | Agent          | Backlog |
| 20   | Generator Agent Implementation                           | Agent          | Backlog |
| 21   | Conversational Agent Implementation                      | Agent          | Backlog |
| 22   | Tiered-Vision Agent Implementation                       | Agent          | Backlog |

---

## Dependencies

| This Epic Depends On | Reason |
|---------------------|--------|
| Epic 0 (Infrastructure) | Kubernetes, DAPR, MongoDB, Redis |
| Epic 1 (Plantation Model) | Plantation MCP Server for farmer context |
| Epic 2 (Collection Model) | Collection MCP Server for document access |

| Epics That Depend On This | Reason |
|--------------------------|--------|
| Epic 5 (Knowledge Model) | Uses AI Model for diagnosis agents |
| Epic 6 (Action Plans) | Uses AI Model for plan generation |
| Epic 8 (Voice Advisor) | Uses AI Model for conversational AI |
| Epic 12 (Engagement) | Uses AI Model for motivation engine |

---

## Architecture References

| Topic | Document |
|-------|----------|
| AI Model Overview | `_bmad-output/architecture/ai-model-architecture/index.md` |
| Agent Types | `_bmad-output/architecture/ai-model-architecture/agent-types.md` |
| Agent Configuration Schema | `_bmad-output/architecture/ai-model-architecture/agent-configuration-schema.md` |
| Prompt Management | `_bmad-output/architecture/ai-model-architecture/prompt-management.md` |
| LangGraph Orchestration | `_bmad-output/architecture/ai-model-architecture/langgraph-workflow-orchestration.md` |
| LLM Gateway | `_bmad-output/architecture/ai-model-architecture/llm-gateway.md` |
| RAG Engine | `_bmad-output/architecture/ai-model-architecture/rag-engine.md` |
| Tiered-Vision | `_bmad-output/architecture/ai-model-architecture/tiered-vision-processing-cost-optimization.md` |
| Cache Pattern | `_bmad-output/architecture/adr/ADR-013-ai-model-configuration-cache.md` |
| Key Decisions | `_bmad-output/architecture/ai-model-architecture/key-decisions.md` |
| **Developer Guide** | `_bmad-output/ai-model-developer-guide/index.md` |

---

## Retrospective

**Story File:** Not yet created | Status: Backlog

---

_Last Updated: 2026-01-08_
