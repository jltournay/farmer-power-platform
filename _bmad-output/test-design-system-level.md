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
│  │  • Pinecone Vector DB (in-memory mock)                               │  │
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

### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
|---------|----------|-------------|-------------|--------|-------|------------|-------|
| R-007 | TECH | DAPR sidecar communication failures | 2 | 2 | 4 | Circuit breaker and retry tests | Platform Team |
| R-008 | DATA | MongoDB replication lag affects consistency | 2 | 2 | 4 | Read-after-write tests | Platform Team |
| R-009 | OPS | Prompt A/B testing produces regressions | 2 | 2 | 4 | A/B test validation framework | AI Team |
| R-010 | PERF | Parallel analyzer timeout handling | 2 | 2 | 4 | Timeout scenario tests | AI Team |
| R-011 | BUS | Grading model calculation errors | 2 | 2 | 4 | Property-based testing for grade calculations | Collection Team |
| R-012 | DATA | RAG knowledge versioning causes retrieval issues | 2 | 2 | 4 | Namespace isolation tests | AI Team |

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

### 3. Directory Structure

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
│   ├── qc-event-extractor/
│   │   └── samples.json           # 100+ validated samples
│   ├── quality-triage/
│   │   └── samples.json           # 100+ validated samples
│   ├── disease-diagnosis/
│   │   └── samples.json           # 50+ validated samples
│   └── action-plan-generator/
│       └── samples.json           # 20+ validated samples
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