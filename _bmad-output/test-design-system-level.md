# System-Level Test Design: Farmer Power Platform

**Date:** 2025-12-23
**Author:** Test Engineering Architect (TEA)
**Phase:** Phase 3 - Solutioning (Testability Review)
**Status:** Draft

---

## Executive Summary

**System Scope:** Complete Farmer Power Cloud Platform - 9 Domain Models + Infrastructure

**Team Context:**
- **Testing Maturity:** Low (new to automated testing)
- **Primary Risk Focus:** AI/LLM accuracy
- **Framework Choice:** pytest + pytest-asyncio

**Key Findings:**

| Area | Testability Score | Risk Level | Recommendation |
|------|-------------------|------------|----------------|
| AI/LLM Accuracy | Medium | HIGH | Golden sample testing critical |
| Inter-service Communication | Medium | MEDIUM | Contract testing for DAPR events |
| External API Integration | High | MEDIUM | Mock boundaries well-defined |
| Data Integrity | Medium | MEDIUM | State management patterns needed |

**Critical Path:**
1. Establish golden sample testing for all AI agents
2. Implement contract tests for DAPR Pub/Sub events
3. Create fixture library for MongoDB test data
4. Define mock boundaries for external APIs

---

## Architecture Testability Assessment

### 1. Component Testability Matrix

| Component | Unit | Integration | E2E | Testability Notes |
|-----------|------|-------------|-----|-------------------|
| **Collection Model** | HIGH | HIGH | MEDIUM | Clear input/output contracts, stateless MCP |
| **Plantation Model** | HIGH | HIGH | HIGH | CRUD operations, well-defined schema |
| **Knowledge Model** | MEDIUM | MEDIUM | LOW | Complex AI orchestration, parallel analyzers |
| **Action Plan Model** | MEDIUM | MEDIUM | LOW | Multi-output generation (SMS, Voice, Dashboard) |
| **Notification Model** | HIGH | MEDIUM | LOW | External API mocking required |
| **Market Analysis** | MEDIUM | LOW | LOW | External Starfish API dependency |
| **AI Model** | MEDIUM | LOW | LOW | LLM non-determinism, prompt sensitivity |
| **Conversational AI** | LOW | LOW | LOW | Multi-turn dialogue, context management |
| **RAG Retrieval** | MEDIUM | HIGH | LOW | Deterministic retrieval, vector DB dependency |
| **RAG Ranking** | HIGH | MEDIUM | LOW | Pure logic, easily unit tested |

### 2. Communication Pattern Testability

| Pattern | Technology | Testability | Approach |
|---------|------------|-------------|----------|
| **Inter-service gRPC** | DAPR Service Invocation | HIGH | Mock DAPR client, use stubs |
| **Event Publishing** | DAPR Pub/Sub | MEDIUM | In-memory pubsub for tests |
| **MCP Tool Calls** | gRPC | HIGH | Mock at client level |
| **LLM Calls** | OpenRouter | MEDIUM | Record/replay, golden samples |
| **External APIs** | REST (Starfish, Weather, AT) | HIGH | Mock at HTTP level |

### 3. Test Boundary Recommendations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TEST BOUNDARY ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EXTERNAL (ALWAYS MOCK)                                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  • OpenRouter/LLM Providers (record/replay + golden samples)         │  │
│  │  • Starfish Network API (HTTP mocks)                                 │  │
│  │  • Weather APIs (fixture data)                                       │  │
│  │  • Africa's Talking SMS/Voice (stub responses)                       │  │
│  │  • Google Elevation API (fixture data)                               │  │
│  │  • Pinecone Vector DB (in-memory mock OR sandbox index)              │  │
│  │  • Pinecone Inference API (mock embedding responses)                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  INTERNAL (REAL FOR INTEGRATION, MOCK FOR UNIT)                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  • MongoDB (testcontainers or in-memory for unit)                    │  │
│  │  • DAPR Pub/Sub (in-memory pubsub component)                         │  │
│  │  • DAPR Service Invocation (mock or real depending on scope)         │  │
│  │  • MCP Servers (mock responses for unit, real for integration)       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ALWAYS REAL                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  • Business logic functions                                           │  │
│  │  • Pydantic model validation                                          │  │
│  │  • Schema transformations                                             │  │
│  │  • Error handling paths                                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Risk Assessment (System-Level)

### High-Priority Risks (Score >= 6)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
|---------|----------|-------------|-------------|--------|-------|------------|-------|----------|
| R-001 | BUS | AI extraction produces incorrect farmer data | 3 | 3 | 9 | Golden sample testing for all extractors | AI Team | Sprint 1 |
| R-002 | BUS | Diagnosis accuracy below acceptable threshold | 3 | 3 | 9 | Expert-validated golden samples + triage feedback loop testing | AI Team | Sprint 1 |
| R-003 | DATA | Cross-model event data inconsistency | 2 | 3 | 6 | Contract testing for DAPR events | Platform Team | Sprint 2 |
| R-004 | SEC | Prompt injection vulnerabilities in LLM agents | 2 | 3 | 6 | Input sanitization tests + adversarial testing | Security | Sprint 2 |
| R-005 | PERF | LLM latency exceeds SLA under load | 2 | 3 | 6 | Load testing with OpenRouter timeout simulation | Platform Team | Sprint 3 |
| R-006 | BUS | SMS/Voice messages fail to deliver to farmers | 2 | 3 | 6 | Delivery assurance integration tests | Notification Team | Sprint 2 |
| R-016 | BUS | RAG retrieval returns irrelevant documents | 2 | 3 | 6 | RAG retrieval golden samples (50+ expert-validated) | AI Team | Sprint 2 |

### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
|---------|----------|-------------|-------------|--------|-------|------------|-------|
| R-007 | TECH | DAPR sidecar communication failures | 2 | 2 | 4 | Circuit breaker and retry tests | Platform Team |
| R-008 | DATA | MongoDB replication lag affects consistency | 2 | 2 | 4 | Read-after-write tests | Platform Team |
| R-009 | OPS | Prompt A/B testing produces regressions | 2 | 2 | 4 | A/B test validation framework | AI Team |
| R-010 | PERF | Parallel analyzer timeout handling | 2 | 2 | 4 | Timeout scenario tests | AI Team |
| R-011 | BUS | Grading model calculation errors | 2 | 2 | 4 | Property-based testing for grade calculations | Collection Team |
| R-012 | DATA | RAG knowledge versioning causes retrieval issues | 2 | 2 | 4 | Namespace isolation tests + RAG golden samples | AI Team |
| R-017 | BUS | RAG ranking prioritizes wrong documents | 2 | 2 | 4 | RAG ranking golden samples with domain boosting tests | AI Team |
| R-018 | TECH | Embedding model drift affects retrieval quality | 2 | 2 | 4 | Baseline accuracy samples re-run on model updates | AI Team |

### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
|---------|----------|-------------|-------------|--------|-------|--------|
| R-013 | OPS | Log aggregation gaps | 1 | 2 | 2 | Monitor |
| R-014 | TECH | MCP server scaling under load | 1 | 2 | 2 | Monitor |
| R-015 | BUS | Voice IVR audio quality issues | 1 | 2 | 2 | Manual testing |

---

## Test Strategy by Domain Model

### Collection Model

**Test Pyramid Recommendation:**

| Level | Coverage | Tools | Focus |
|-------|----------|-------|-------|
| Unit | 70% | pytest, unittest.mock | Schema validation, ingestion pipeline steps |
| Integration | 20% | pytest + testcontainers | MongoDB operations, MCP tool responses |
| E2E | 10% | pytest + DAPR test harness | Full ingestion flow with event publishing |

**Golden Sample Requirements:**
- QC event extraction accuracy tests
- Validation warning generation tests
- Farmer linkage accuracy tests

**Key Test Scenarios:**

```
P0 (Critical):
□ QC event ingestion with valid payload → extracts correct fields
□ QC event with missing farmer_id → stores with warning, not rejection
□ QC event publishes DAPR event after storage

P1 (High):
□ Bulk ZIP upload processes all files
□ Schema validation rejects malformed payloads
□ MCP tool get_document returns correct data

P2 (Medium):
□ Search API returns filtered results
□ Query API pagination works correctly
```

---

### Knowledge Model

**Test Pyramid Recommendation:**

| Level | Coverage | Tools | Focus |
|-------|----------|-------|-------|
| Unit | 50% | pytest, unittest.mock | Triage classification, analyzer logic |
| Integration | 30% | pytest + mock LLM | Full saga workflow, parallel analyzer orchestration |
| Golden Sample | 20% | pytest + real LLM | Diagnosis accuracy validation |

**Golden Sample Requirements (CRITICAL):**
- 50+ expert-validated diagnosis cases
- Triage classification accuracy tests
- Weather correlation accuracy tests
- Disease identification accuracy tests

**Key Test Scenarios:**

```
P0 (Critical):
□ Triage agent correctly classifies issue type (disease/weather/technique/handling/soil)
□ Disease analyzer produces accurate diagnosis for known disease images
□ Parallel analyzer timeout doesn't block saga completion
□ Diagnosis deduplication prevents duplicate processing

P1 (High):
□ Weather lag correlation (3-7 day lookback) produces relevant insights
□ RAG retrieval returns relevant knowledge documents
□ Low-confidence triage triggers multiple analyzers in parallel
□ Triage feedback loop updates improve classification

P2 (Medium):
□ Trend analyzer identifies quality patterns over time
□ Explorer agent query produces useful insights
```

---

### Plantation Model

**Test Pyramid Recommendation:**

| Level | Coverage | Tools | Focus |
|-------|----------|-------|-------|
| Unit | 60% | pytest | CRUD operations, performance summary calculations |
| Integration | 30% | pytest + testcontainers | MongoDB operations, MCP tools |
| E2E | 10% | pytest | Full farmer registration flow |

**Key Test Scenarios:**

```
P0 (Critical):
□ Farmer registration with valid data succeeds
□ Factory creation with grading model configuration works
□ Region altitude band calculation is accurate
□ MCP tool get_farmer returns correct farmer data

P1 (High):
□ Performance summary computation is accurate
□ Farmer batch upload processes correctly
□ Weather data per region is correctly associated

P2 (Medium):
□ Farmer search and filtering works
□ Lead farmer assignment propagates correctly
```

---

### AI Model (Central AI Orchestration)

**Test Pyramid Recommendation:**

| Level | Coverage | Tools | Focus |
|-------|----------|-------|-------|
| Unit | 40% | pytest, unittest.mock | Agent workflow steps, prompt rendering |
| Golden Sample | 40% | pytest + real LLM | Accuracy validation for all agent types |
| Integration | 20% | pytest + mock DAPR | Event handling, MCP client calls |

**Golden Sample Requirements (CRITICAL):**

| Agent Type | Sample Count | Source |
|------------|--------------|--------|
| qc-event-extractor | 100+ | QC analyzer payloads |
| quality-triage | 100+ | Expert-classified cases |
| disease-diagnosis | 50+ | Agronomist-validated diagnoses |
| weather-impact-analyzer | 30+ | Regional weather correlation cases |
| technique-assessment | 30+ | Technique-related quality issues |
| weekly-action-plan | 20+ | Sample action plan outputs |
| market-analyzer | 20+ | Market insight cases |

**Key Test Scenarios:**

```
P0 (Critical):
□ Extractor agents extract correct fields from QC payloads
□ Explorer agents produce accurate diagnoses
□ Generator agents produce valid action plans
□ LLM fallback chain works when primary model fails
□ Prompt loading from MongoDB works with cache

P1 (High):
□ Tiered vision processing routes correctly (Haiku screen → Sonnet full)
□ RAG knowledge retrieval returns relevant documents
□ Agent workflow checkpointing enables crash recovery
□ Prompt A/B testing routes traffic correctly

P2 (Medium):
□ Cost tracking per agent/model is accurate
□ Token usage stays within limits
```

---

### RAG Infrastructure (Retrieval & Ranking)

**Test Pyramid Recommendation:**

| Level | Coverage | Tools | Focus |
|-------|----------|-------|-------|
| Unit | 30% | pytest, unittest.mock | Embedding generation, vector operations, ranking logic |
| Integration | 40% | pytest + Pinecone sandbox | End-to-end retrieval with real vectors |
| Golden Sample | 30% | pytest + seeded vector DB | Accuracy validation for retrieval & ranking |

**Golden Sample Requirements (CRITICAL):**

| Component | Development (Synthetic) | Production (Expert) | Validation Focus |
|-----------|------------------------|---------------------|------------------|
| RAG Retrieval | 10 samples | 50+ samples | Query → expected chunks in top-k |
| RAG Ranking | 10 samples | 30+ samples | Relevance ordering correctness |
| Domain Boosting | 5 samples | 20+ samples | Cross-domain priority validation |
| Deduplication | 5 samples | 10+ samples | Near-duplicate removal accuracy |

**RAG vs Agent Golden Samples - Key Differences:**

| Aspect | Agent Golden Samples | RAG Golden Samples |
|--------|---------------------|-------------------|
| **What's tested** | LLM output quality | Retrieval/ranking accuracy |
| **Determinism** | Non-deterministic (LLM variance) | Deterministic (same query → same results) |
| **Pass criteria** | Semantic similarity to expected | Exact match (document ID in top-k) |
| **Variance tolerance** | 0.15 confidence tolerance | Zero tolerance (binary: found or not) |
| **Generation source** | LLM generates input + expected output | Query generated, expected doc IDs known |

**Synthetic RAG Sample Generation:**

Unlike agent samples, RAG samples require a **seeded knowledge base** first:

```python
# tests/golden/rag/generator.py

class RagRetrievalSample(BaseModel):
    query: str                           # Natural language query
    domain_filter: Optional[str]         # e.g., "disease", "weather"
    expected_doc_ids: list[str]          # Document IDs that MUST appear
    expected_chunk_ids: list[str]        # Chunk IDs in top-k
    top_k: int = 5                       # How many results to check
    min_expected_in_topk: int = 1        # At least N expected docs in top-k
    metadata: RagSampleMetadata

class RagRankingSample(BaseModel):
    query: str
    candidate_doc_ids: list[str]         # Docs to rank (pre-retrieved)
    expected_order: list[str]            # Expected ranking order
    domain_boost: Optional[str]          # Domain to boost
    allow_position_variance: int = 1     # Allow ±1 position variance
    metadata: RagSampleMetadata

async def generate_rag_retrieval_samples(
    seed_documents: list[dict],
    queries_per_doc: int = 3,
) -> list[RagRetrievalSample]:
    """
    Generate synthetic RAG retrieval samples from seeded documents.

    Unlike agent samples, RAG samples are GROUNDED in real documents.
    The LLM generates queries, but the expected results are deterministic.
    """
    samples = []

    for doc in seed_documents:
        # LLM generates queries that should retrieve this doc
        prompt = f"""
        Document ID: {doc['id']}
        Domain: {doc['domain']}
        Content: {doc['content'][:500]}...

        Generate {queries_per_doc} natural language questions that a
        Kenyan tea farmer might ask that should retrieve this document.

        Requirements:
        - Vary complexity (simple factual, complex analytical)
        - Use farmer-appropriate language (not technical jargon)
        - Include at least one Swahili-influenced phrasing

        Return as JSON array of strings.
        """

        queries = await llm_client.complete(prompt)

        for query in json.loads(queries.content):
            samples.append(RagRetrievalSample(
                query=query,
                expected_doc_ids=[doc['id']],
                top_k=5,
                min_expected_in_topk=1,
                metadata=RagSampleMetadata(
                    source="llm_generated",
                    seed_doc_id=doc['id'],
                    priority="P2",
                )
            ))

    return samples
```

**Key Test Scenarios:**

```
P0 (Critical):
□ Known agronomic query returns expected disease document in top-5
□ Query with domain filter excludes unrelated domain results
□ Confidence threshold correctly filters results below threshold
□ Duplicate/near-duplicate chunks are deduplicated in results

P1 (High):
□ Domain-specific boost ranks disease docs higher for disease queries
□ Recency weighting ranks newer documents higher (same relevance)
□ Multi-domain query returns balanced cross-domain results
□ Empty result handling returns appropriate response (not error)

P2 (Medium):
□ Large result set pagination works correctly
□ Metadata filtering (date range, source type) works
□ Query embedding caching reduces redundant API calls
```

**CI Gate Thresholds:**

| Sample Type | Dev Gate | Release Gate | Rationale |
|------------|----------|--------------|-----------|
| RAG Retrieval (Synthetic) | 85% pass | N/A | Deterministic, higher bar than agents |
| RAG Retrieval (Expert) | N/A | 95% pass | Production accuracy requirement |
| RAG Ranking (Synthetic) | 80% pass | N/A | Ordering has some tolerance |
| RAG Ranking (Expert) | N/A | 90% pass | Domain boost validation |

**Reference:** Stories 0.75.14 (RAG Retrieval Service) and 0.75.15 (RAG Ranking Logic) in Epic 0.75.

---

### Action Plan Model

**Test Pyramid Recommendation:**

| Level | Coverage | Tools | Focus |
|-------|----------|-------|-------|
| Unit | 50% | pytest | Selector logic, format generation |
| Integration | 30% | pytest + mock AI Model | Full action plan generation |
| E2E | 20% | pytest + mock Notification | End-to-end farmer action plan |

**Key Test Scenarios:**

```
P0 (Critical):
□ Selector agent correctly prioritizes insights
□ Action plan generator produces valid multi-format output
□ SMS summary stays within 300 chars
□ Voice script follows VoiceScript model structure
□ Dashboard format includes all required fields

P1 (High):
□ Empty state handling produces appropriate message
□ Translation to Swahili maintains meaning
□ Simplification produces 6th-grade reading level
□ Farmer communication preferences are respected

P2 (Medium):
□ Weekly digest aggregation works correctly
□ Action plan versioning tracks changes
```

---

### Notification Model

**Test Pyramid Recommendation:**

| Level | Coverage | Tools | Focus |
|-------|----------|-------|-------|
| Unit | 50% | pytest | Message formatting, delivery logic |
| Integration | 40% | pytest + HTTP mocks | Africa's Talking API interactions |
| E2E | 10% | pytest + stub providers | Full delivery flow |

**Key Test Scenarios:**

```
P0 (Critical):
□ SMS delivery to Africa's Talking API succeeds
□ Voice IVR call initiation works
□ Delivery status webhook processing works
□ Retry logic for failed deliveries works

P1 (High):
□ SMS character count optimization (GSM-7 vs Unicode)
□ Voice IVR TTS generation produces valid audio
□ Multi-channel fallback for critical alerts works
□ Inbound SMS keyword command processing works

P2 (Medium):
□ Delivery assurance "catch-up" messaging works
□ Lead farmer escalation for unreachable farmers works
```

---

### Conversational AI Model

**Test Pyramid Recommendation:**

| Level | Coverage | Tools | Focus |
|-------|----------|-------|-------|
| Unit | 40% | pytest | Session management, adapter logic |
| Integration | 40% | pytest + mock AI Model | Multi-turn conversation flow |
| E2E | 20% | pytest + mock channels | Full voice/text interaction |

**Key Test Scenarios:**

```
P0 (Critical):
□ Voice adapter handles STT/TTS correctly
□ Session context persists across turns
□ AI Model invocation returns valid response
□ Handoff to Notification Model works

P1 (High):
□ Session timeout after 30 minutes works
□ Language selection DTMF handling works
□ Conversation history retrieval works

P2 (Medium):
□ WhatsApp adapter media support works
□ SMS chat 160-char limit handling works
```

---

## Test Infrastructure Requirements

### 0. RAG Testing Prerequisites (Stories 0.75.12-0.75.15)

RAG golden sample generation is a **task within each RAG story**, not a separate operation. The developer implementing the story generates samples as part of the story deliverables.

**Infrastructure Dependencies:**

RAG stories require Pinecone access for:
1. Storing seed documents as vectors (test fixtures)
2. Executing retrieval queries to validate samples
3. Generating golden samples with actual Pinecone responses

**Environment Variables (from `services/ai-model/src/ai_model/config.py`):**

| Setting | Environment Variable | Required | Default |
|---------|---------------------|----------|---------|
| `pinecone_api_key` | `AI_MODEL_PINECONE_API_KEY` | **Yes** | None |
| `pinecone_environment` | `AI_MODEL_PINECONE_ENVIRONMENT` | No | `us-east-1` |
| `pinecone_index_name` | `AI_MODEL_PINECONE_INDEX_NAME` | No | `farmer-power-rag` |
| `pinecone_embedding_model` | `AI_MODEL_PINECONE_EMBEDDING_MODEL` | No | `multilingual-e5-large` |

**Developer Setup (Before Story 0.75.12):**

1. Obtain Pinecone API key from https://www.pinecone.io/ (free tier available)
2. Add to `.env`:
   ```bash
   AI_MODEL_PINECONE_API_KEY=pc-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   AI_MODEL_PINECONE_ENVIRONMENT=us-east-1
   AI_MODEL_PINECONE_INDEX_NAME=farmer-power-dev
   ```
3. Verify connection: `python -c "from ai_model.config import settings; print(settings.pinecone_enabled)"`

**Golden Sample Generation Workflow (Per Story):**

```
┌─────────────────────────────────────────────────────────────────────┐
│           RAG STORY IMPLEMENTATION (Single PR)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Story Tasks Include:                                                │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  1. Implement production code (retrieval/ranking service)       │ │
│  │  2. Create seed_documents.json (5+ test documents)              │ │
│  │  3. Upload seed docs to Pinecone test namespace                 │ │
│  │  4. Generate synthetic samples using LLM + real Pinecone        │ │
│  │  5. Commit samples.json (10+ samples)                           │ │
│  │  6. Write golden sample test suite                              │ │
│  │  7. Achieve ≥85% pass rate on synthetic samples                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ARTIFACTS COMMITTED IN PR:                                          │
│  • Production code                                                   │
│  • tests/golden/rag/seed_documents.json                             │
│  • tests/golden/rag/generator.py                                     │
│  • tests/golden/rag/{component}/samples.json  ← Generated output    │
│  • tests/golden/rag/{component}/test_golden.py                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**CI Configuration:**

| Environment | Pinecone Access | Purpose |
|-------------|-----------------|---------|
| Local Dev | Real (via `.env`) | Generate samples, validate retrieval |
| CI Unit Tests | Uses committed `samples.json` | Fast, deterministic regression |
| CI Integration | Real (via `secrets.PINECONE_API_KEY`) | Optional: validate actual behavior |

**Note:** CI runs tests against **committed samples.json** - it does NOT regenerate samples on each run.

---

### 1. pytest Configuration

```python
# conftest.py - Root level
import pytest
import asyncio
from unittest.mock import AsyncMock

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_dapr_client():
    """Mock DAPR client for service invocation."""
    client = AsyncMock()
    client.invoke_method = AsyncMock(return_value={})
    client.publish_event = AsyncMock()
    return client

@pytest.fixture
def mock_openrouter():
    """Mock OpenRouter LLM gateway."""
    # Record/replay pattern for LLM responses
    pass

@pytest.fixture
async def mongodb_test_client():
    """MongoDB client with test database."""
    # Use testcontainers or in-memory mock
    pass
```

### 2. Golden Sample Framework

```python
# tests/golden/framework.py
import json
from pathlib import Path
from typing import TypedDict

class GoldenSample(TypedDict):
    input: dict
    expected_output: dict
    acceptable_variance: dict
    metadata: dict

def load_golden_samples(agent_name: str) -> list[GoldenSample]:
    """Load golden samples for an agent."""
    path = Path(f"tests/golden/{agent_name}/samples.json")
    return json.loads(path.read_text())

def validate_against_golden(actual: dict, expected: dict, variance: dict) -> bool:
    """Validate actual output against expected with acceptable variance."""
    # Implement field-by-field comparison with variance tolerance
    pass
```

### 3. Synthetic Golden Sample Generation

During development, expert-validated samples are not available. The platform uses **LLM-generated synthetic samples** to bootstrap testing without agronomist dependency.

#### Why Synthetic Samples?

| Challenge | Solution |
|-----------|----------|
| Agronomists not available during development | LLM generates realistic samples |
| Chicken-and-egg: can't test without samples, can't get samples without agent | Synthetic samples bootstrap the cycle |
| Need 50-100 samples per agent | LLM can generate unlimited samples quickly |
| Expert time is expensive | Reserve expert validation for production readiness |

#### Two-Tier Sample Strategy

| Tier | Source | Priority | Pass Rate Gate | When Used |
|------|--------|----------|----------------|-----------|
| **Synthetic** | LLM-generated | P2 | 70% | Development, CI during build |
| **Expert-validated** | Agronomist-approved | P0 | 90% | Production release gate |

#### Synthetic Sample Generator

```python
# tests/golden/generator.py

from pydantic import BaseModel
from tests.golden.framework import GoldenSampleSchema, GoldenSampleMetadata, AgentType

async def generate_synthetic_samples(
    agent_name: str,
    agent_type: AgentType,
    input_schema: type[BaseModel],
    output_schema: type[BaseModel],
    domain_context: str,
    count: int = 10,
) -> list[GoldenSampleSchema]:
    """
    Generate synthetic golden samples using LLM.

    Args:
        agent_name: Name of the agent (e.g., "disease_diagnosis")
        agent_type: Type of agent (extractor, explorer, generator, etc.)
        input_schema: Pydantic model defining input structure
        output_schema: Pydantic model defining expected output structure
        domain_context: Domain description for realistic generation
        count: Number of samples to generate

    Returns:
        List of GoldenSampleSchema ready to save
    """
    prompt = f"""
    Generate {count} realistic test cases for a {agent_type.value} AI agent.

    Domain Context: {domain_context}

    Input Schema:
    {input_schema.model_json_schema()}

    Expected Output Schema:
    {output_schema.model_json_schema()}

    Requirements:
    - Vary conditions realistically (different diseases, weather, severity levels)
    - Include edge cases (low confidence, multiple issues, ambiguous symptoms)
    - Make inputs realistic for Kenyan tea farmers
    - Ensure outputs are plausible expert responses

    Return as JSON array of objects with "input" and "expected_output" keys.
    """

    response = await llm_client.complete(
        model="anthropic/claude-3-5-sonnet",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,  # Higher creativity for diverse samples
    )

    raw_samples = json.loads(response.content)

    # Validate and convert to GoldenSampleSchema
    samples = []
    for raw in raw_samples:
        # Validate against schemas
        input_schema.model_validate(raw["input"])
        output_schema.model_validate(raw["expected_output"])

        samples.append(GoldenSampleSchema(
            input=raw["input"],
            expected_output=raw["expected_output"],
            acceptable_variance={"confidence": 0.15},  # Wider variance for synthetic
            metadata=GoldenSampleMetadata(
                sample_id=generate_sample_id(raw["input"]),
                agent_name=agent_name,
                agent_type=agent_type,
                source="llm_generated",
                validated_by="synthetic",
                priority="P2",
                tags=["synthetic", "bootstrap"],
            )
        ))

    return samples
```

#### CLI for Sample Generation

```bash
# Generate 20 synthetic samples for disease diagnosis agent
python -m tests.golden.generator generate \
    --agent disease_diagnosis \
    --type explorer \
    --count 20 \
    --domain "Kenyan tea farming: diseases, pests, weather impact, nutrient deficiency"

# Output:
# ✓ Generated 20 synthetic samples
# ✓ Validated against schemas
# ✓ Saved to tests/golden/disease_diagnosis/samples.json
# ⚠ Samples marked as P2 (synthetic) - expert validation required for P0
```

#### Sample Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GOLDEN SAMPLE LIFECYCLE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PHASE 1: DEVELOPMENT (No agronomist needed)                            │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  1. Developer defines input/output Pydantic schemas                 │ │
│  │  2. LLM generates 10-20 synthetic samples per agent                 │ │
│  │  3. Samples marked: source="llm_generated", priority="P2"           │ │
│  │  4. CI gate: 70% pass rate on synthetic samples                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  PHASE 2: INTEGRATION (Still no agronomist)                             │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  1. Run agent on real production-like inputs                        │ │
│  │  2. Capture actual LLM outputs (record mode)                        │ │
│  │  3. Add to sample collection for consistency testing                │ │
│  │  4. Synthetic samples ensure no regressions                         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  PHASE 3: PRODUCTION READINESS (Agronomist validates)                   │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  1. Export recorded samples to review spreadsheet                   │ │
│  │  2. Agronomist reviews: ✅ Correct | ✏️ Corrects | ❌ Wrong          │ │
│  │  3. Approved samples promoted: priority="P0", validated_by="Name"   │ │
│  │  4. CI gate increases: 90% pass rate on expert-validated samples    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  PHASE 4: CONTINUOUS IMPROVEMENT                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  1. Production errors become new test cases                         │ │
│  │  2. Edge cases discovered → added to samples                        │ │
│  │  3. Model updates validated against full sample library             │ │
│  │  4. Accuracy tracked over time via metrics dashboard                │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### CI Configuration for Two-Tier Testing

```yaml
# .github/workflows/ci.yaml (golden sample section)

golden-sample-tests:
  runs-on: ubuntu-latest
  steps:
    - name: Run synthetic sample tests (P2)
      run: |
        pytest tests/golden/ -m "golden and synthetic" -v
      env:
        GOLDEN_MIN_PASS_RATE: 0.70  # 70% for synthetic

    - name: Run expert-validated sample tests (P0)
      run: |
        pytest tests/golden/ -m "golden and not synthetic" -v
      env:
        GOLDEN_MIN_PASS_RATE: 0.90  # 90% for expert
      continue-on-error: true  # Warning only until expert samples exist
```

#### Minimum Sample Requirements

| Component | Development (Synthetic) | Production (Expert) |
|-----------|------------------------|---------------------|
| Extractor agents | 10 samples | 100+ samples |
| Explorer agents | 10 samples | 50+ samples |
| Generator agents | 10 samples | 20+ samples |
| Conversational | 10 samples | 30+ samples |
| Tiered-Vision | 10 samples | 50+ samples |
| **RAG Retrieval** | 10 samples | 50+ samples |
| **RAG Ranking** | 10 samples | 30+ samples |
| **RAG Domain Boosting** | 5 samples | 20+ samples |

### 4. Directory Structure

```
tests/
├── conftest.py                    # Global fixtures
├── unit/
│   ├── collection/
│   │   ├── test_ingestion_pipeline.py
│   │   ├── test_schema_validation.py
│   │   └── test_mcp_tools.py
│   ├── plantation/
│   │   └── test_farmer_crud.py
│   ├── knowledge/
│   │   ├── test_triage_agent.py
│   │   └── test_analyzer_logic.py
│   └── ai_model/
│       ├── test_extractor_workflow.py
│       ├── test_explorer_workflow.py
│       └── test_generator_workflow.py
├── integration/
│   ├── test_dapr_events.py
│   ├── test_mcp_integration.py
│   └── test_mongodb_operations.py
├── golden/
│   ├── framework.py
│   ├── generator.py               # Synthetic sample generator utility
│   ├── qc-event-extractor/
│   │   └── samples.json           # 100+ validated samples
│   ├── quality-triage/
│   │   └── samples.json           # 100+ validated samples
│   ├── disease-diagnosis/
│   │   └── samples.json           # 50+ validated samples
│   ├── action-plan-generator/
│   │   └── samples.json           # 20+ validated samples
│   └── rag/                       # RAG-specific golden samples
│       ├── generator.py           # RAG sample generator (seeded docs → queries)
│       ├── seed_documents.json    # Seeded knowledge base for RAG testing
│       ├── retrieval/
│       │   └── samples.json       # 50+ retrieval accuracy samples
│       ├── ranking/
│       │   └── samples.json       # 30+ ranking order samples
│       └── domain-boosting/
│           └── samples.json       # 20+ domain priority samples
├── contracts/
│   ├── test_event_schemas.py      # DAPR event contract tests
│   └── test_mcp_contracts.py      # MCP tool contract tests
└── fixtures/
    ├── llm_responses/             # Recorded LLM responses
    ├── mongodb_data/              # Test data fixtures
    └── external_api_mocks/        # Starfish, Weather, AT mocks
```

---

## Quality Gate Criteria

### Phase Gate: Ready for Implementation

Before implementation begins, ALL of the following must be true:

- [ ] **Golden sample framework** is implemented and documented
- [ ] **Test directory structure** is created
- [ ] **conftest.py** with core fixtures is in place
- [ ] **Mock boundaries** are defined and documented
- [ ] **DAPR event schemas** are defined for contract testing
- [ ] **At least 10 golden samples** exist for each extractor agent
- [ ] **CI/CD pipeline** runs tests on PR

### Ongoing Quality Gates

| Gate | P0 Pass | P1 Pass | Golden Sample Accuracy | Timeline |
|------|---------|---------|------------------------|----------|
| PR to feature branch | 100% | N/A | N/A | Every PR |
| PR to main | 100% | 95% | 90%+ | Every PR |
| Release candidate | 100% | 100% | 95%+ | Before release |

---

## Recommended Test Implementation Order

### Sprint 1: Foundation

1. **Set up test infrastructure**
   - pytest + pytest-asyncio configuration
   - conftest.py with core fixtures
   - Golden sample framework

2. **Collection Model unit tests**
   - Schema validation tests
   - Ingestion pipeline step tests

3. **AI Model golden samples**
   - qc-event-extractor (first 20 samples)
   - quality-triage (first 20 samples)

### Sprint 2: Core Coverage

4. **Plantation Model unit tests**
   - CRUD operation tests
   - Performance summary tests

5. **Knowledge Model tests**
   - Triage agent tests
   - Parallel analyzer orchestration tests

6. **DAPR contract tests**
   - Event schema validation
   - Service invocation contracts

### Sprint 3: Integration & Accuracy

7. **Golden sample expansion**
   - disease-diagnosis (50+ samples)
   - Complete extractor coverage (100+ samples)

8. **Integration tests**
   - Cross-model event flows
   - MCP tool integration

9. **Notification Model tests**
   - Africa's Talking API mocks
   - Delivery assurance tests

---

## Mitigation Plans for High-Priority Risks

### R-001 & R-002: AI Extraction & Diagnosis Accuracy (Score: 9)

**Mitigation Strategy:**
1. Implement golden sample testing framework (Sprint 1)
2. Create 100+ expert-validated samples per agent (Sprint 1-2)
3. Run golden sample tests on every PR
4. Track accuracy metrics over time
5. Set accuracy threshold gates: 90% for extraction, 85% for diagnosis

**Verification:**
- Golden sample pass rate reported in CI/CD
- Accuracy dashboard in monitoring
- Weekly accuracy review meetings

**Owner:** AI Team
**Timeline:** Sprint 1-2

### R-003: Cross-Model Event Data Inconsistency (Score: 6)

**Mitigation Strategy:**
1. Define JSON schemas for all DAPR events
2. Implement contract tests using pydantic models
3. Fail CI if event schema changes without version bump
4. Document all events in event catalog

**Verification:**
- Contract tests pass in CI
- Event catalog is up-to-date
- No runtime schema validation errors in logs

**Owner:** Platform Team
**Timeline:** Sprint 2

### R-004: Prompt Injection Vulnerabilities (Score: 6)

**Mitigation Strategy:**
1. Implement input sanitization layer
2. Create adversarial test cases (prompt injection attempts)
3. Use output validation to detect injection leakage
4. Regular security review of prompt templates

**Verification:**
- Adversarial tests pass
- No prompt injection in golden sample outputs
- Security review sign-off

**Owner:** Security Team
**Timeline:** Sprint 2

---

## Assumptions and Dependencies

### Assumptions

1. OpenRouter API will be available for golden sample testing (real LLM calls)
2. Agronomists will provide expert-validated diagnosis samples within Sprint 1
3. DAPR test harness supports in-memory pubsub for integration tests
4. Team will allocate 30% of sprint capacity to testing infrastructure

### Dependencies

1. **Golden sample data** - Required by end of Sprint 1
   - Source: Agronomist team
   - Format: JSON with input payload + expected output

2. **DAPR test components** - Required by Sprint 2
   - Source: Platform team
   - Format: Docker-compose for local testing

3. **Africa's Talking sandbox** - Required by Sprint 2
   - Source: Account setup with AT
   - Format: Test credentials for SMS/Voice testing

---

## Next Steps

1. **Approve this document** - Product Manager + Tech Lead + QA Lead sign-off
2. **Create Jira epics** for test infrastructure setup
3. **Schedule golden sample collection** workshop with agronomists
4. **Set up CI/CD pipeline** with test execution
5. **Begin Sprint 1** test implementation

---

## Approval

**System-Level Test Design Approved By:**

- [ ] Product Manager: _________________ Date: _______
- [ ] Tech Lead: _________________ Date: _______
- [ ] QA Lead: _________________ Date: _______

**Comments:**

---

---

## E2E Test Infrastructure

### Overview

The E2E test infrastructure provides a complete local deployment of all Farmer Power Platform services using Docker Compose. Tests run against real services with DAPR sidecars, MongoDB, Redis, and Azurite (Azure Storage emulator).

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         E2E TEST ARCHITECTURE                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  TEST CLIENT (pytest)                                                           │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │  • PlantationClient (HTTP → localhost:8001)                                │ │
│  │  • CollectionClient (HTTP → localhost:8002)                                │ │
│  │  • PlantationMCPClient (gRPC → localhost:50052)                            │ │
│  │  • CollectionMCPClient (gRPC → localhost:50053)                            │ │
│  │  • AzuriteClient (Blob → localhost:10000)                                  │ │
│  │  • MongoDBDirectClient (MongoDB → localhost:27017)                         │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                      ↓                                           │
│  DOCKER COMPOSE STACK                                                            │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │ │
│  │  │ plantation-model│    │ collection-model│    │ plantation-mcp  │        │ │
│  │  │     :8001       │    │     :8002       │    │    :50052       │        │ │
│  │  │ (+ DAPR sidecar)│    │ (+ DAPR sidecar)│    │ (+ DAPR sidecar)│        │ │
│  │  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘        │ │
│  │           │                      │                      │                  │ │
│  │           └──────────────────────┼──────────────────────┘                  │ │
│  │                                  ↓                                          │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │ │
│  │  │    mongodb      │    │      redis      │    │    azurite      │        │ │
│  │  │    :27017       │    │     :6379       │    │    :10000       │        │ │
│  │  │ (plantation_e2e)│    │ (DAPR pubsub)   │    │ (blob storage)  │        │ │
│  │  │ (collection_e2e)│    │ (DAPR state)    │    │                 │        │ │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘        │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
tests/e2e/
├── conftest.py                      # Fixtures and E2ETestDataFactory
├── helpers/
│   ├── api_clients.py               # HTTP clients for Model services
│   ├── mcp_clients.py               # gRPC clients for MCP servers
│   ├── azure_blob.py                # Azurite blob storage client
│   ├── mongodb_direct.py            # Direct MongoDB client for verification
│   └── cleanup.py                   # Post-test cleanup utilities
├── infrastructure/
│   ├── docker-compose.e2e.yaml      # Full stack deployment
│   ├── dapr-components/
│   │   ├── pubsub.yaml              # Redis pubsub config
│   │   └── statestore.yaml          # Redis state store config
│   ├── mock-servers/
│   │   └── google-elevation/        # Mock Google Elevation API
│   │       ├── Dockerfile
│   │       └── main.py
│   └── seed/
│       ├── regions.json             # Required: Region seed data
│       ├── grading_models.json      # Required: Grading model configs
│       └── source_configs.json      # Required: Collection Model ingestion configs
└── scenarios/
    ├── test_01_factory_farmer_flow.py
    ├── test_02_quality_ingestion_flow.py
    ├── test_03_weather_integration.py
    └── test_04_mcp_verification.py
```

### Seed Data Requirements

E2E tests require seed data to be present before tests run. The `seed_data` fixture loads these automatically.

#### 1. Regions (`seed/regions.json`)

Regions must exist before farmers can be created (farmers are auto-assigned to regions based on GPS + altitude).

```json
[
  {
    "region_id": "kericho-highland",
    "name": "Kericho Highland",
    "county": "Kericho",
    "country": "Kenya",
    "geography": {
      "center_gps": {"lat": -0.3667, "lng": 35.2833},
      "radius_km": 25,
      "altitude_band": {
        "min_meters": 1800,
        "max_meters": 2200,
        "label": "highland"
      }
    },
    "flush_calendar": {
      "first_flush": {"start": "03-15", "end": "05-15", "characteristics": "..."},
      "monsoon_flush": {"start": "06-15", "end": "09-30", "characteristics": "..."},
      "autumn_flush": {"start": "10-15", "end": "12-15", "characteristics": "..."},
      "dormant": {"start": "12-16", "end": "03-14", "characteristics": "..."}
    },
    "agronomic": {
      "soil_type": "volcanic_red",
      "typical_diseases": ["blister_blight", "grey_blight"],
      "harvest_peak_hours": "06:00-10:00",
      "frost_risk": true
    },
    "weather_config": {
      "api_location": {"lat": -0.3667, "lng": 35.2833},
      "altitude_for_api": 2000,
      "collection_time": "06:00"
    }
  }
]
```

#### 2. Grading Models (`seed/grading_models.json`)

Grading models define how quality is graded. Two types exist:
- **TBK (binary)**: Primary / Secondary
- **KTDA (ternary)**: Grade A / Grade B / Rejected

```json
[
  {
    "model_id": "tbk_kenya_tea_v1",
    "name": "TBK Kenya Tea Standard",
    "version": "1.0.0",
    "grades": ["Primary", "Secondary"],
    "is_active": true
  },
  {
    "model_id": "ktda_standard_v1",
    "name": "KTDA Standard Grading",
    "version": "1.0.0",
    "grades": ["Grade A", "Grade B", "Rejected"],
    "is_active": true
  }
]
```

#### 3. Source Configs (`seed/source_configs.json`)

**CRITICAL**: Collection Model has NO direct document creation API. All documents are ingested via:
1. Blob triggers (Azure Event Grid events)
2. Scheduled pull jobs (DAPR Jobs API)

Source configs define how each ingestion source is processed:

For example (just one example)

```json
[
  {
    "source_id": "e2e-qc-analyzer-json",
    "enabled": true,
    "description": "E2E Test - QC Analyzer JSON results",
    "config": {
      "ingestion": {
        "mode": "blob_trigger",
        "processor_type": "json-extraction",
        "landing_container": "quality-events-e2e",
        "path_pattern": {
          "pattern": "results/{factory_id}/{farmer_id}/{batch_id}.json",
          "extract_fields": ["factory_id", "farmer_id", "batch_id"]
        }
      },
      "transformation": {
        "ai_agent_id": "qc_event_extractor",
        "link_field": "farmer_id",
        "extract_fields": ["farmer_id", "factory_id", "grading_model_id", "bag_summary"]
      },
      "storage": {
        "index_collection": "quality_documents",
        "raw_bucket": "raw-documents-e2e"
      },
      "events": {
        "on_success": {"topic": "collection.quality_result.received"}
      }
    }
  }
]
```

Plantation client is accessible at `http://localhost:8001`.



#### CollectionClient (HTTP)



```python
async with CollectionClient("http://localhost:8002") as client:
    # Trigger blob ingestion (simulates Azure Event Grid)
    accepted = await client.trigger_blob_event(
        container="quality-events-e2e",
        blob_path="results/FAC-001/WM-001/batch-001.json",
        content_length=1024
    )

    # Trigger pull job (DAPR scheduled job callback)
    result = await client.trigger_pull_job(source_id="e2e-qc-analyzer-json")

    # Health
    health = await client.health()
```

#### AzuriteClient (Blob Storage)

```python
async with AzuriteClient(connection_string) as client:
    # Upload quality event with correct path pattern
    blob_url, blob_path = await client.upload_quality_event(
        farmer_id="WM-0001",
        factory_id="KEN-FAC-001",
        event_data={
            "grading_model_id": "tbk_kenya_tea_v1",
            "bag_summary": {"total_bags": 5, "grade_distribution": {"Primary": 3}}
        }
    )
    # Path: results/{factory_id}/{farmer_id}/{batch_id}.json

    # List blobs
    blobs = await client.list_blobs("quality-events-e2e")
```

#### MongoDBDirectClient (Verification)

Use for direct database verification (bypassing API):

```python
async with MongoDBDirectClient("mongodb://localhost:27017") as client:
    # Plantation database (plantation_e2e)
    farmer = await client.get_farmer_direct(farmer_id)
    factory = await client.get_factory_direct(factory_id)
    region = await client.get_region_direct(region_id)

    # Collection database (collection_e2e)
    doc_count = await client.count_quality_documents(farmer_id="WM-0001")
    docs = await client.get_latest_quality_documents(farmer_id="WM-0001")
    source_config = await client.get_source_config(source_id)
```

### Creating a New Test Scenario

Follow these steps to create a new E2E test:

#### Step 1: Identify Required Seed Data

Determine what seed data your test needs:
- [ ] Regions (for farmer registration)
- [ ] Grading models (for quality events)
- [ ] Source configs (for blob ingestion)
- [ ] Collection points (if testing farmer registration)

Add any missing seed data to the appropriate JSON file in `seed/`.

#### Step 2: Create Test File

Create a new file in `tests/e2e/scenarios/`:

```python
"""
E2E Test: [Descriptive Name].

Tests the complete flow of:
1. Step 1 description
2. Step 2 description

Prerequisites:
    docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
"""

import pytest

from tests.e2e.conftest import E2ETestDataFactory
from tests.e2e.helpers.api_clients import PlantationClient, CollectionClient
from tests.e2e.helpers.azure_blob import AzuriteClient
from tests.e2e.helpers.mongodb_direct import MongoDBDirectClient


@pytest.mark.e2e
class TestYourScenario:
    """E2E tests for your scenario."""

    @pytest.mark.asyncio
    async def test_your_flow(
        self,
        plantation_api: PlantationClient,
        collection_api: CollectionClient,
        azurite_client: AzuriteClient,
        mongodb_direct: MongoDBDirectClient,
        e2e_data_factory: type[E2ETestDataFactory],
        seed_data: dict,  # Use this to verify seed data is present
    ):
        """Test: Description of test.

        Given: Preconditions
        When: Actions
        Then: Expected outcomes
        """
        # Verify required seed data
        assert len(seed_data.get("regions", [])) > 0

        # Arrange - Create test data using factory
        farmer_data = e2e_data_factory.create_farmer_data(
            first_name="Test",
            last_name="Farmer",
        )

        # Act - Perform operations via API
        result = await plantation_api.create_farmer(farmer_data)

        # Assert - Verify API response
        assert "id" in result
        assert result["first_name"] == farmer_data["first_name"]

        # Assert - Verify database state (optional)
        db_farmer = await mongodb_direct.get_farmer_direct(result["id"])
        assert db_farmer is not None
```

#### Step 3: Handle Collection Model Documents

Collection Model documents require blob ingestion:

```python
@pytest.mark.asyncio
async def test_quality_document_ingestion(
    self,
    azurite_client: AzuriteClient,
    collection_api: CollectionClient,
    mongodb_direct: MongoDBDirectClient,
    e2e_data_factory: type[E2ETestDataFactory],
    seed_data: dict,
):
    """Test quality document ingestion via blob trigger."""
    # Verify source config is seeded
    assert len(seed_data.get("source_configs", [])) > 0

    # Step 1: Upload blob to Azurite
    event_data = e2e_data_factory.create_quality_event_data(
        farmer_id="WM-0001",
        factory_id="KEN-FAC-001",
    )
    blob_url, blob_path = await azurite_client.upload_quality_event(
        farmer_id="WM-0001",
        factory_id="KEN-FAC-001",
        event_data=event_data,
    )

    # Step 2: Trigger blob event (simulates Azure Event Grid)
    accepted = await collection_api.trigger_blob_event(
        container="quality-events-e2e",
        blob_path=blob_path,
    )
    assert accepted is True

    # Step 3: Wait for async processing
    import asyncio
    await asyncio.sleep(3)

    # Step 4: Verify document was created
    doc_count = await mongodb_direct.count_quality_documents(farmer_id="WM-0001")
    assert doc_count >= 1
```

### Running E2E Tests

#### Start Infrastructure

```bash
# Start all services
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d

# Wait for services to be healthy
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps

# View logs if needed
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml logs -f plantation-model
```

#### Run Tests

```bash
# Run all E2E tests
pytest tests/e2e/scenarios/ -v --tb=short -m e2e

# Run specific test file
pytest tests/e2e/scenarios/test_01_factory_farmer_flow.py -v

# Run with slow tests
pytest tests/e2e/scenarios/ -v -m "e2e and slow"

# Skip slow tests
pytest tests/e2e/scenarios/ -v -m "e2e and not slow"
```

#### Cleanup

```bash
# Stop and remove containers
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down

# Remove volumes (clears all data)
docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Service not healthy | Check logs: `docker-compose logs <service>` |
| MongoDB connection refused | Ensure MongoDB is running and healthy |
| Farmer registration fails | Ensure region seed data exists |
| Blob ingestion not working | Verify source_config matches container/path pattern |
| MCP client timeout | Ensure DAPR sidecar is running for the service |
| Test data conflicts | Run cleanup between test runs |

### Mock Server: Google Elevation API

The Google Elevation mock returns altitude based on latitude:

| Latitude Range | Altitude | Altitude Band |
|----------------|----------|---------------|
| lat > 1.0 | 2000m | highland |
| 0.5 < lat < 1.0 | 1500m | midland |
| lat < 0.5 | 1000m | midland/highland |

This allows deterministic testing of region assignment based on GPS coordinates.

---

## Appendix

### A. Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue)
- **OPS**: Operations (deployment, config, monitoring)

### B. Related Documents

- Product Brief: `_bmad-output/analysis/product-brief-farmer-power-platform-2025-12-16.md`
- Architecture: `_bmad-output/architecture/index.md`
- Project Context: `_bmad-output/project-context.md`
- AI Model Architecture: `_bmad-output/architecture/ai-model-architecture.md`

### C. Knowledge Base References

- `_bmad/bmm/testarch/knowledge/risk-governance.md` - Risk classification framework
- `_bmad/bmm/testarch/knowledge/test-levels-framework.md` - Test level selection
- `_bmad/bmm/testarch/knowledge/test-quality.md` - Quality patterns
- `_bmad/bmm/testarch/knowledge/nfr-criteria.md` - Non-functional requirements

---

**Generated by**: BMad TEA Agent - System-Level Testability Review
**Workflow**: `_bmad/bmm/workflows/testarch/test-design`
**Version**: 4.0 (BMad v6)
**Mode**: System-Level (Phase 3 - Solutioning)