# Epic 0.75: AI Model Foundation

Cross-cutting AI infrastructure that enables all AI-powered domain models. These stories establish the LLM gateway, agent framework, RAG engine, and prompt management patterns used across Knowledge Model, Action Plan Model, and Conversational AI.

**Priority:** P1

**Dependencies:** Epic 0 (Infrastructure), Epic 1 (Plantation Model), Epic 2 (Collection Model)

**Blocks:** Epic 5 (Knowledge Model), Epic 6 (Action Plans), Epic 8 (Voice Advisor), Epic 12 (Engagement Model)

**FRs covered:** FR45, FR46, FR47, FR48, FR49

---

## Overview

The AI Model is the most complex and strategic module of the Farmer Power Platform. It provides:

- **LLM Gateway** — OpenRouter integration with cost management and model routing
- **Agent Framework** — Five agent types (Extractor, Explorer, Generator, Conversational, Tiered-Vision) with LangGraph orchestration
- **RAG Infrastructure** — Document storage, embedding, vector storage, retrieval, and ranking
- **Prompt Management** — MongoDB storage with versioning and CLI tooling
- **Event-Driven Architecture** — DAPR pub/sub for agent triggering and result publishing

### Testing Strategy

All AI agents require **golden sample testing** to validate accuracy. During development, LLM-generated **synthetic samples** bootstrap testing without agronomist dependency. Expert-validated samples are collected post-platform-completion for production readiness.

**Reference:** `_bmad-output/test-design-system-level.md` § *Synthetic Golden Sample Generation*

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
- Proto package scaffold (`farmer_power.ai_model.v1`) — package declaration, base service stub, and `HealthService` RPCs

---

### Story 0.75.2: Pydantic Model for Prompt + Mongo Repository

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want Pydantic models and repository pattern for prompt storage,
So that prompts are type-safe and properly managed in MongoDB.

**Scope:**
- `Prompt` Pydantic model with versioning fields
- `PromptRepository` with CRUD operations
- MongoDB collection: `ai_model.prompts`
- Prompt schema: `prompt_id`, `version`, `status`, `content`, `metadata`

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

---

### Story 0.75.4: Source Cache for Agent Types and Prompt Config

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want in-memory caching with MongoDB change streams for agent and prompt configs,
So that configuration lookups are fast without stale data.

**Scope:**
- Implement ADR-013 cache pattern for AI Model
- Change stream listeners for `agent_configs` and `prompts` collections
- Cache invalidation on document changes
- Startup warm-up from MongoDB

**Reference:** ADR-013 (AI Model Configuration Cache)

---

### Story 0.75.5: OpenRouter LLM Gateway with Cost Management

**Story File:** Not yet created | Status: Backlog

As a **developer implementing AI agents**,
I want a unified LLM gateway with cost tracking and resilience,
So that agents can reliably call LLMs with automatic retry and fallback.

**Scope:**
- OpenRouter API integration
- Execute LLM requests per agent configuration (model + fallback chain)
- Validate model availability via OpenRouter API
- Cost tracking per request (input/output tokens, USD)
- OpenTelemetry metrics: `llm_request_cost_usd`, `llm_tokens_total`
- Retry with exponential backoff
- Fallback execution when primary model fails

---

### Story 0.75.6: CLI to Manage Prompt Type Configuration

**Story File:** Not yet created | Status: Backlog

As a **platform operator**,
I want a CLI to manage prompt configurations,
So that prompts can be deployed and versioned without code changes.

**Scope:**
- `fp-prompt-config` CLI using Typer
- Commands: `deploy`, `validate`, `list`, `get`, `promote`, `rollback`
- YAML-based prompt definition files
- Version management (staged, active, archived)

---

### Story 0.75.7: CLI to Manage Agent Configuration

**Story File:** Not yet created | Status: Backlog

As a **platform operator**,
I want a CLI to manage agent configurations,
So that agents can be deployed and updated without code changes.

**Scope:**
- `fp-agent-config` CLI using Typer
- Commands: `deploy`, `validate`, `list`, `get`, `enable`, `disable`
- YAML-based agent definition files
- Validation against agent type schemas

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
- Proto definitions for RAG document CRUD
- gRPC service implementation
- DAPR service invocation integration
- PDF text extraction and parsing (PyMuPDF for digital, Azure Document Intelligence for scanned)
- Document format detection (Markdown, PDF)
- Azure Blob Storage integration for original file storage
- Content chunking by semantic boundaries (headings, paragraphs)

---

### Story 0.75.11: CLI for RAG Document

**Story File:** Not yet created | Status: Backlog

As a **platform operator**,
I want a CLI to manage RAG knowledge documents,
So that agronomists can upload and version knowledge content.

**Scope:**
- `fp-knowledge` CLI using Typer
- Commands: `validate`, `stage`, `promote`, `rollback`, `versions`, `list`
- Thin CLI wrapper calling gRPC document API
- Chunking configuration passthrough

---

### Story 0.75.12: RAG Embedding Service

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want an embedding service for RAG documents,
So that documents can be converted to vectors for similarity search.

**Scope:**
- OpenAI `text-embedding-3-small` integration
- Batch embedding generation for pre-chunked content
- Embedding storage in vector database
- Chunk-to-embedding mapping for retrieval

---

### Story 0.75.13: RAG Vector Storage

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want vector storage for RAG embeddings,
So that similarity search can be performed efficiently.

**Scope:**
- Pinecone vector database integration
- Index configuration per knowledge domain
- Namespace management (staged, active)
- Metadata storage with vectors

---

### Story 0.75.14: RAG Retrieval Service

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want a retrieval service for RAG queries,
So that agents can find relevant knowledge.

**Scope:**
- Similarity search with configurable top-k
- Confidence threshold filtering
- Multi-domain queries
- Query embedding generation

---

### Story 0.75.15: RAG Ranking Logic

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want ranking logic for RAG results,
So that the most relevant documents are prioritized.

**Scope:**
- Re-ranking based on relevance scores
- Domain-specific boosting
- Recency weighting (optional)
- Result deduplication

---

### Story 0.75.16: LangGraph SDK Integration & Base Workflows

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want LangGraph base workflows and patterns,
So that agents can reuse common orchestration logic.

**Scope:**
- LangGraph SDK integration
- Saga pattern with compensation handlers
- MongoDB checkpointing (`langgraph.checkpoint.mongodb.MongoDBSaver`)
- Conditional routing utilities
- Base workflow classes for each agent type
- Error handling and retry logic

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
- Synthetic sample generator utility (`tests/golden/generator.py`)
- Golden sample test suite (LLM-generated synthetic samples, minimum 10)

**Note:** Synthetic samples are generated by LLM based on input/output schemas and domain context. Expert-validated samples replace synthetic samples post-platform-completion.

**References:**
- Agent types: `_bmad-output/architecture/ai-model-architecture/agent-types.md`
- Synthetic sample generation: `_bmad-output/test-design-system-level.md` § *Synthetic Golden Sample Generation*

---

### Story 0.75.18: E2E: Weather Observation Extraction Flow

**Story File:** Not yet created | Status: Backlog

As a **developer**,
I want end-to-end validation of the weather extraction flow,
So that the AI Model integration is proven before building more agents.

**Sub-tasks:**
1. Adapt Collection Model for AI Model compliance (GitHub #81, #82)
2. Create working prompts and agent configuration for weather extraction
3. Replace AI mock container with real AI Model container in E2E infrastructure
4. Add test validating weather observation updates plantation model

**Acceptance Criteria:**
- E2E test passes with real AI Model container
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

| # | Story | Type | Status |
|---|-------|------|--------|
| 1 | AI Model Setup | Infrastructure | Backlog |
| 2 | Pydantic Model for Prompt + Mongo Repository | Data Model | Backlog |
| 3 | Pydantic Model for Agent Configuration + Mongo Repository | Data Model | Backlog |
| 4 | Source Cache for Agent Types and Prompt Config | Infrastructure | Backlog |
| 5 | OpenRouter LLM Gateway with Cost Management | Infrastructure | Backlog |
| 6 | CLI to Manage Prompt Type Configuration | Tooling | Backlog |
| 7 | CLI to Manage Agent Configuration | Tooling | Backlog |
| 8 | Event Flow, Subscriber, and Publisher | Infrastructure | Backlog |
| 9 | Pydantic Model for RAG Document Storage | Data Model | Backlog |
| 10 | gRPC Model for RAG Document | API | Backlog |
| 11 | CLI for RAG Document | Tooling | Backlog |
| 12 | RAG Embedding Service | RAG | Backlog |
| 13 | RAG Vector Storage | RAG | Backlog |
| 14 | RAG Retrieval Service | RAG | Backlog |
| 15 | RAG Ranking Logic | RAG | Backlog |
| 16 | LangGraph SDK Integration & Base Workflows | Framework | Backlog |
| 17 | Extractor Agent Implementation | Agent | Backlog |
| 18 | E2E: Weather Observation Extraction Flow | Validation | Backlog |
| 19 | Explorer Agent Implementation | Agent | Backlog |
| 20 | Generator Agent Implementation | Agent | Backlog |
| 21 | Conversational Agent Implementation | Agent | Backlog |
| 22 | Tiered-Vision Agent Implementation | Agent | Backlog |

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
| LangGraph Orchestration | `_bmad-output/architecture/ai-model-architecture/langgraph-workflow-orchestration.md` |
| LLM Gateway | `_bmad-output/architecture/ai-model-architecture/llm-gateway.md` |
| RAG Engine | `_bmad-output/architecture/ai-model-architecture/rag-engine.md` |
| Tiered-Vision | `_bmad-output/architecture/ai-model-architecture/tiered-vision-processing-cost-optimization.md` |
| Cache Pattern | `_bmad-output/architecture/adr/ADR-013-ai-model-configuration-cache.md` |

---

## Retrospective

**Story File:** Not yet created | Status: Backlog

---

_Last Updated: 2026-01-04_
