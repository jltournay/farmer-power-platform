---
project_name: 'farmer-power-platform'
user_name: 'Jeanlouistournay'
date: '2025-12-23'
sections_completed: ['technology_stack', 'python_rules', 'code_design_principles', 'framework_rules', 'architecture_rules', 'testing_rules', 'ui_ux_rules', 'critical_rules']
status: 'complete'
rule_count: 192
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Repository Structure

> **Full Details:** See `_bmad-output/architecture/repository-structure.md`

### Top-Level Layout (Monorepo)

```
farmer-power-platform/
├── services/                    # All microservices (9 domain models + BFF)
│   ├── collection-model/
│   ├── plantation-model/
│   ├── knowledge-model/
│   ├── action-plan-model/
│   ├── notification-model/
│   ├── market-analysis-model/
│   ├── ai-model/
│   ├── conversational-ai/
│   ├── engagement-model/
│   └── bff/
├── mcp-servers/                 # MCP Server implementations
│   ├── collection-mcp/
│   ├── plantation-mcp/
│   ├── knowledge-mcp/
│   ├── action-plan-mcp/
│   └── engagement-mcp/
├── proto/                       # Shared Protocol Buffer definitions
│   ├── collection/v1/
│   ├── plantation/v1/
│   ├── common/v1/
│   └── ...
├── libs/                        # Shared Python libraries
│   ├── fp-common/               # Common utilities (config, tracing, dapr)
│   ├── fp-proto/                # Generated proto stubs
│   └── fp-testing/              # Test utilities and fixtures
├── deploy/                      # Deployment configurations
│   ├── kubernetes/              # Kustomize base + overlays (qa/preprod/prod)
│   └── docker/                  # Dockerfiles, docker-compose
├── tests/                       # Cross-service tests
│   ├── unit/                    # Per-domain-model unit tests
│   ├── integration/             # Cross-model integration tests
│   ├── golden/                  # Golden sample tests (CRITICAL for AI)
│   ├── contracts/               # DAPR event and MCP contract tests
│   └── fixtures/                # Test data, LLM responses, API mocks
└── scripts/                     # Build, deploy, proto-gen scripts
```

### Service Folder Template

```
services/{service-name}/
├── src/{service_name}/          # Python package (snake_case)
│   ├── main.py                  # Entrypoint
│   ├── config.py                # Service configuration
│   ├── api/                     # gRPC/REST handlers
│   ├── domain/                  # Business logic, models
│   └── infrastructure/          # MongoDB, DAPR, external APIs
├── tests/                       # Service-specific tests
├── Dockerfile
└── pyproject.toml
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Service folder | kebab-case | `collection-model/` |
| Python package | snake_case | `collection_model/` |
| gRPC service | PascalCase | `CollectionService` |
| Proto package | snake_case | `farmer_power.collection.v1` |
| Docker image | kebab-case | `farmer-power/collection-model` |
| K8s deployment | kebab-case | `collection-model` |

### Shared Library Usage

```python
# In service's pyproject.toml
[tool.poetry.dependencies]
fp-common = { path = "../../libs/fp-common" }
fp-proto = { path = "../../libs/fp-proto" }
fp-testing = { path = "../../libs/fp-testing", optional = true }

# In code
from fp_common.config import load_config
from fp_common.dapr import DaprClient
from fp_proto.collection.v1 import collection_pb2
```

### Where to Put Code

| Need | Location |
|------|----------|
| New domain model service | `services/{model-name}/` |
| New MCP server | `mcp-servers/{model-name}-mcp/` |
| Shared utility | `libs/fp-common/fp_common/` |
| Proto definition | `proto/{domain}/v1/{domain}.proto` |
| Unit test | `tests/unit/{model_name}/` OR `services/{model}/tests/` |
| Golden sample | `tests/golden/{agent-name}/samples.json` |
| K8s manifest | `deploy/kubernetes/base/services/` |
| Environment overlay | `deploy/kubernetes/overlays/{env}/` |

---

## Technology Stack & Versions

| Technology | Version | Critical Notes |
|------------|---------|----------------|
| Python | 3.12 | Use 3.12 features (type hints, match statements) |
| Pydantic | 2.0 | V2 syntax required - NOT compatible with V1 |
| FastAPI | Latest | Async endpoints required for all I/O operations |
| LangChain | Latest | Use for simple linear chains ONLY |
| LangGraph | Latest | Use for stateful/conditional workflows |
| DAPR | Latest | ALL inter-service communication via DAPR sidecar |
| MongoDB | Managed | Atlas or CosmosDB - NOT self-hosted |
| Pinecone | Latest | Namespace-per-version for knowledge versioning |
| OpenRouter | N/A | Single LLM gateway - NO direct provider calls |

### Version Constraints

- **Pydantic 2.0**: V1 models will NOT work - use `model_dump()` not `dict()`
- **Python 3.12**: Required for type hint features used throughout
- **DAPR**: All events, state, secrets MUST go through DAPR components
- **OpenTelemetry**: Supported via DAPR - no manual instrumentation needed

---

## Python-Specific Rules

### Async/Await Requirements

- ALL I/O operations MUST be async (database, HTTP, MCP calls)
- Use `async def` for FastAPI endpoints
- Use `asyncio.gather()` for parallel operations, NOT sequential awaits
- Use `asyncio.wait()` with timeout for parallel analyzers

### Type Hints

- ALL function signatures MUST have type hints
- Use `TypedDict` for LangGraph state definitions
- Use Pydantic models for API request/response schemas
- Use `Optional[T]` not `T | None` for compatibility

### Pydantic 2.0 Patterns

- Use `model_dump()` NOT `dict()` (V1 syntax)
- Use `model_validate()` NOT `parse_obj()`
- Use `Field(description=...)` for LLM output schemas
- Define `model_config` as class attribute, NOT `Config` inner class

### Error Handling

- Use custom exception classes per error category (TransientError, DataError)
- Use `tenacity` for retry logic with exponential backoff
- Catch specific exceptions, NOT bare `except:`
- Log errors with structlog including trace_id and agent_id

### Import Conventions

- Absolute imports only (no relative imports)
- Group: stdlib, third-party, local
- One class/function per import line for clarity

---

## Code Design Principles

### Open/Closed Principle (OCP) - MANDATORY

Code must be **open for extension, closed for modification**. When adding new variants (channels, analyzers, grading types), you MUST NOT modify existing code.

### When OCP Applies

| Scenario | Use OCP Pattern |
|----------|-----------------|
| Adding new delivery channel (SMS, WhatsApp, Voice) | Channel Adapter |
| Adding new analyzer type (disease, weather, technique) | Analyzer Strategy |
| Adding new agent type (extractor, explorer, generator) | Agent Base Class |
| Adding new grading model | Configurable via MongoDB |
| Adding new data source | Ingestion Adapter |

### Pattern 1: Channel Adapter (Notification Model)

```python
# domain/channels/base.py - CLOSED (never modify)
from abc import ABC, abstractmethod
from pydantic import BaseModel

class DeliveryResult(BaseModel):
    success: bool
    channel: str
    message_id: str | None = None
    error: str | None = None

class ChannelAdapter(ABC):
    """Base adapter - extend this, never modify."""

    @abstractmethod
    async def send(self, recipient: str, message: str) -> DeliveryResult:
        """Send message via this channel."""
        pass

    @abstractmethod
    def supports_media(self) -> bool:
        """Whether channel supports images/audio."""
        pass
```

```python
# domain/channels/sms.py - OPEN (add new adapters here)
from .base import ChannelAdapter, DeliveryResult

class SMSAdapter(ChannelAdapter):
    """SMS delivery via Africa's Talking."""

    def __init__(self, client: AfricasTalkingClient):
        self._client = client

    async def send(self, recipient: str, message: str) -> DeliveryResult:
        result = await self._client.send_sms(recipient, message)
        return DeliveryResult(
            success=result.status == "sent",
            channel="sms",
            message_id=result.message_id,
        )

    def supports_media(self) -> bool:
        return False
```

```python
# domain/channels/whatsapp.py - Adding new channel = new file only
class WhatsAppAdapter(ChannelAdapter):
    """WhatsApp delivery - added without touching SMSAdapter."""

    async def send(self, recipient: str, message: str) -> DeliveryResult:
        # Implementation here
        pass

    def supports_media(self) -> bool:
        return True  # WhatsApp supports images
```

```python
# domain/channels/registry.py - Registry pattern for discovery
class ChannelRegistry:
    """Register adapters - add new channels without modifying existing."""

    _adapters: dict[str, type[ChannelAdapter]] = {}

    @classmethod
    def register(cls, channel_name: str):
        def decorator(adapter_cls: type[ChannelAdapter]):
            cls._adapters[channel_name] = adapter_cls
            return adapter_cls
        return decorator

    @classmethod
    def get(cls, channel_name: str) -> ChannelAdapter:
        return cls._adapters[channel_name]()

# Usage: @ChannelRegistry.register("whatsapp")
```

### Pattern 2: Analyzer Strategy (Knowledge Model)

```python
# domain/analyzers/base.py - CLOSED
from abc import ABC, abstractmethod
from pydantic import BaseModel

class AnalysisResult(BaseModel):
    category: str
    confidence: float
    findings: list[str]
    recommendations: list[str]

class Analyzer(ABC):
    """Base analyzer - extend for new analysis types."""

    @property
    @abstractmethod
    def category(self) -> str:
        """Analyzer category (disease, weather, technique, etc.)"""
        pass

    @abstractmethod
    async def analyze(self, context: dict) -> AnalysisResult:
        """Perform analysis and return findings."""
        pass
```

```python
# domain/analyzers/disease.py - OPEN
class DiseaseAnalyzer(Analyzer):
    """Analyzes quality issues related to plant diseases."""

    @property
    def category(self) -> str:
        return "disease"

    async def analyze(self, context: dict) -> AnalysisResult:
        # Use LLM via AI Model to diagnose disease
        diagnosis = await self._ai_client.diagnose_disease(context)
        return AnalysisResult(
            category=self.category,
            confidence=diagnosis.confidence,
            findings=diagnosis.findings,
            recommendations=diagnosis.actions,
        )
```

```python
# domain/analyzers/weather.py - Adding new analyzer = new file only
class WeatherAnalyzer(Analyzer):
    """Correlates quality issues with recent weather patterns."""

    @property
    def category(self) -> str:
        return "weather"

    async def analyze(self, context: dict) -> AnalysisResult:
        # Fetch weather data via Plantation MCP
        weather = await self._plantation_mcp.get_weather_history(
            region=context["region"],
            days=7,  # 3-7 day lookback for lag correlation
        )
        # Analyze correlation
        ...
```

### Pattern 3: Agent Base Class (AI Model)

```python
# domain/agents/base.py - CLOSED
from abc import ABC, abstractmethod
from typing import TypedDict

class AgentConfig(BaseModel):
    name: str
    model: str  # e.g., "haiku", "sonnet"
    max_tokens: int
    temperature: float = 0.0

class BaseAgent(ABC):
    """Base agent class - extend for new agent types."""

    def __init__(self, config: AgentConfig):
        self.config = config

    @abstractmethod
    async def execute(self, input_data: dict) -> dict:
        """Execute the agent's primary task."""
        pass

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM via OpenRouter - shared by all agents."""
        return await self._openrouter.complete(
            model=self.config.model,
            prompt=prompt,
            max_tokens=self.config.max_tokens,
        )
```

```python
# domain/agents/extractor.py - OPEN
class ExtractorAgent(BaseAgent):
    """Extracts structured data from unstructured input."""

    async def execute(self, input_data: dict) -> dict:
        prompt = await self._load_prompt("extractor", input_data)
        response = await self._call_llm(prompt)
        return self._parse_response(response)
```

### Code Clarity Rules

| Rule | Why | Example |
|------|-----|---------|
| One class per file | Easy to find, easy to extend | `sms.py`, `whatsapp.py`, not `channels.py` |
| Descriptive names | Self-documenting | `WeatherImpactAnalyzer` not `Analyzer2` |
| Type hints everywhere | IDE support, catch errors | `async def send(self, recipient: str) -> DeliveryResult` |
| Docstrings on public methods | Explain intent | `"""Correlates quality issues with weather."""` |
| Small functions (< 20 lines) | Easy to understand | Extract helpers for complex logic |
| No magic numbers | Named constants | `LOOKBACK_DAYS = 7` not `7` |

### OCP Anti-Patterns to AVOID

```python
# BAD: Modifying existing code for new channels
class NotificationService:
    async def send(self, channel: str, message: str):
        if channel == "sms":
            return await self._send_sms(message)
        elif channel == "whatsapp":  # Adding this = modifying existing code!
            return await self._send_whatsapp(message)
        elif channel == "voice":  # More modifications!
            return await self._send_voice(message)
```

```python
# GOOD: Extend via new adapter classes
class NotificationService:
    def __init__(self, registry: ChannelRegistry):
        self._registry = registry

    async def send(self, channel: str, message: str):
        adapter = self._registry.get(channel)  # No modification needed
        return await adapter.send(message)
```

### When NOT to Use OCP

- **Simple utilities**: No variants expected (e.g., date formatting)
- **One-off scripts**: Not production code
- **Obvious single implementation**: Only one way to do it

**Rule of thumb**: If you see `if/elif/elif` based on a type/category, refactor to OCP.

---

## Framework-Specific Rules

### LangChain vs LangGraph Decision

| Use Case | Framework | Example |
|----------|-----------|---------|
| Simple extraction | LangChain | QC event extraction, triage classification |
| Stateful workflow | LangGraph | Quality analysis saga, action plan generation |
| Parallel branches | LangGraph | Multi-analyzer fan-out/join |
| Conditional routing | LangGraph | Triage → analyzer selection |

### LangGraph Patterns

- ALWAYS use `StateGraph` with `TypedDict` state
- ALWAYS enable MongoDB checkpointing for crash recovery
- Use `fan_out` node type for parallel analyzers
- Use `conditional` edges for triage routing
- Set `timeout_ms` on parallel branches (default: 30000)
- Handle branch failures with `on_branch_error: proceed_without`

### DAPR Communication Rules

- **Inter-model calls**: gRPC via DAPR Service Invocation
- **Events**: DAPR Pub/Sub (NOT direct HTTP)
- **Scheduling**: DAPR Jobs (NOT cron in code)
- **State**: DAPR State Store (NOT direct MongoDB for cross-model state)
- **Secrets**: DAPR Secret Store (NOT environment variables for sensitive data)

### DAPR Event Naming

- Format: `{source-model}.{entity}.{action}`
- Examples: `collection.quality_event.created`, `ai.diagnosis.complete`
- Use past tense for completed actions

### MCP Server Rules

- MCP servers are STATELESS - no in-memory caching
- Each domain model exposes ONE MCP server
- Tools return data, NOT make decisions
- Use Pydantic models for tool input/output schemas
- Tool names: `get_*`, `search_*`, `list_*` (verbs for read operations)

### FastAPI/BFF Rules

- BFF is the ONLY external-facing API
- Internal cluster: gRPC via DAPR
- External clients: REST + WebSocket via BFF
- Use dependency injection for DAPR client, MongoDB, etc.
- Background tasks for non-blocking operations

---

## Architecture & Domain Model Rules

### Domain Model Boundaries (9 Models)

| Model | Responsibility | Does NOT |
|-------|---------------|----------|
| Collection | Ingest, validate, store documents | Make business decisions |
| Plantation | Farmer/factory digital twin | Store raw documents |
| Knowledge | Diagnose situations | Prescribe solutions |
| Action Plan | Generate recommendations | Store diagnoses, deliver messages |
| Notification | Deliver messages (SMS, WhatsApp, Voice IVR) | Generate content, handle dialogue |
| Market Analysis | Buyer profiles, lot matching | Generate action plans |
| AI Model | Agent orchestration, LLM calls | Own business data |
| Conversational AI | Two-way dialogue (voice chatbot, text chat) | Execute AI logic, deliver final messages |
| Engagement | Track progress, streaks, milestones, motivation | Diagnose issues, deliver messages |

### Cross-Model Communication

- Models communicate via DAPR Pub/Sub events ONLY
- NO direct database access across models
- Use MCP servers for data retrieval between models
- Each model owns its MongoDB collections exclusively

### Data Ingestion Rules (Collection Model)

- **Trust provided IDs** - Do NOT verify farmer_id against Plantation Model on ingest
- **Store with warnings, don't reject** - Validation failures are stored with warnings, not rejected
- **Best-effort semantic checking** - Collection Model is intake, not police
- **Missing farmer ID** - Store document with warning, not rejection

### MongoDB Collection Ownership

- `collection_model`: `quality_events`, `weather_data`, `documents_index`
- `plantation_model`: `farmers`, `factories`, `regions`, `grading_models`, `farmer_performance`
- `knowledge_model`: `diagnoses`, `triage_feedback`
- `action_plan_model`: `action_plans`, `farmer_dashboard_view`
- `ai_model`: `prompts`, `rag_documents`, `workflow_checkpoints`, `agent_configs`
- `conversational_ai_model`: `sessions`, `conversation_history`, `channel_configs`
- `engagement_model`: `engagement_state`, `milestones`, `celebrations`

### Region Definition (Plantation Model)

- Regions are defined by **county + altitude band** combination
- Altitude bands: low (<800m), medium (800-1200m), high (>1200m)
- Use Google Elevation API to determine farm altitude at registration
- Weather data is collected **per region**, NOT per farm (cost optimization)
- Flush calendar (harvest timing) varies by region based on seasonal patterns

### AI Model Agent Types

| Type | Framework | Purpose |
|------|-----------|---------|
| Extractor | LangChain | Data extraction, validation, classification |
| Explorer | LangGraph | Multi-step analysis with conditional routing |
| Generator | LangGraph | Content generation (action plans, reports) |
| Conversational | LangGraph | Multi-turn dialogue with context management |

### Triage-First Pattern

- ALWAYS use Triage Agent (Haiku) before expensive analyzers
- Triage classifies: disease, weather, technique, handling, soil
- If confidence >= 0.7: route to primary analyzer only
- If confidence < 0.7: run multiple analyzers in parallel

### Weather Correlation Pattern (Knowledge Model)

- Weather analyzer uses **3-7 day lookback** for lag correlation
- Coffee quality issues often manifest days after weather events
- Fetch weather history via Plantation Model MCP, NOT direct API
- Correlate: heavy rain → moisture issues, heat waves → stress symptoms

### Triage Feedback Loop (Knowledge Model)

- Store triage predictions with actual analyzer outcomes
- Collection: `triage_feedback` in knowledge_model database
- Periodic evaluation: compare triage confidence vs actual diagnosis match
- Use feedback to improve triage prompt and routing thresholds
- Target: triage accuracy > 85% for primary classification

### Grading Model Flexibility

- **NEVER hardcode grade labels** (A, B, C, D, Premium, Standard, Rejected, etc.)
- Grading models are fully configurable per factory/regulatory authority
- Types: binary (Accept/Reject), ternary (Premium/Standard/Reject), multi-level (A/B/C/D)
- Always include `grading_model_id` + `grading_model_version` reference for label lookup
- **Full grading model definition stored in Plantation Model** (not just reference)

**Grading Model Structure (stored in Plantation Model):**
```yaml
grading_model:
  model_id: "tbk_kenya_tea_v1"
  model_version: "1.0.0"
  grading_type: "binary"  # binary | ternary | multi_level
  attributes:
    leaf_type: { num_classes: 7, classes: ["bud", "one_leaf_bud", ...] }
    coarse_subtype: { num_classes: 4, classes: ["none", "double_luck", ...] }
    banji_hardness: { num_classes: 2, classes: ["soft", "hard"] }
  grade_rules:
    reject_conditions: { leaf_type: ["three_plus_leaves_bud", "coarse_leaf"] }
    conditional_reject: [{ if_attribute: "leaf_type", if_value: "banji", then_attribute: "banji_hardness", reject_values: ["hard"] }]
  grade_labels: { ACCEPT: "Primary", REJECT: "Secondary" }
  active_at_factory: ["factory-001"]
```

**Attribute-Level Tracking (in FarmerPerformance):**
- Track attribute distributions, not just final grades
- Enables root-cause analysis: "Your coarse_leaf count increased from 8% to 15%"
- Structure: `attribute_distributions_30d: { "leaf_type": { "bud": 15, "coarse_leaf": 10 }, "banji_hardness": { "soft": 3, "hard": 2 } }`

**Grade Calculation:**
- Grades are computed from **attribute values** defined in the Grading Model
- Attributes are discrete classes (e.g., leaf_type = "two_leaves_bud"), not weighted scores
- Grade rules define rejection conditions based on attribute values
- Factory-specific display labels via `grade_labels` mapping

| Pattern | Usage | Example |
|---------|-------|---------|
| Semantic category | Trigger conditions | `grade_category: "rejection"` (lowest tier) |
| Normalized threshold | Score-based triggers | `quality_score_below: 0.3` (0.0-1.0 scale) |
| Dynamic object map | Grade distributions | `{ [grading_model_label]: count }` |

- For UI display: lookup grade labels from factory's Grading Model at render time
- For triggers: use semantic categories or normalized thresholds, NOT label matching
- Grade distributions and statistics: store as dynamic objects keyed by Grading Model labels

### Externalized Configuration

- **Prompts**: Stored in MongoDB, NOT in source code
- **RAG Knowledge**: Stored in MongoDB + Pinecone
- **Agent Configs**: YAML files in Git, deployed to MongoDB
- Hot-reload: 5-minute cache TTL for prompts and knowledge

### Triggering Responsibility

- **Domain models own triggers** - NOT the AI Model
- Event triggers: domain model subscribes to event, invokes AI workflow
- Schedule triggers: domain model configures DAPR Jobs, invokes AI workflow
- AI Model is PASSIVE - only executes when invoked by domain models

---

## Testing Rules

### Test Organization

- Tests live in `tests/` directory mirroring `src/` structure
- Unit tests: `tests/unit/{model_name}/`
- Integration tests: `tests/integration/`
- Golden samples: `tests/golden/{agent_name}/`
- Contract tests: `tests/contracts/`
- Fixtures: `tests/fixtures/`

### Test Directory Structure

```
tests/
├── conftest.py              # Core fixtures (ALWAYS import from here)
├── unit/
│   ├── collection/          # Collection Model unit tests
│   ├── plantation/          # Plantation Model unit tests
│   ├── knowledge/           # Knowledge Model unit tests
│   ├── action_plan/         # Action Plan Model unit tests
│   ├── notification/        # Notification Model unit tests
│   ├── market_analysis/     # Market Analysis unit tests
│   ├── ai_model/            # AI Model unit tests
│   └── conversational_ai/   # Conversational AI unit tests
├── integration/             # Cross-model integration tests
├── golden/
│   ├── framework.py         # Golden sample validation framework
│   ├── qc_event_extractor/  # QC extraction golden samples
│   ├── quality_triage/      # Triage classification samples
│   ├── disease_diagnosis/   # Diagnosis accuracy samples
│   └── action_plan_generator/
├── contracts/               # DAPR event schema validation
└── fixtures/
    ├── llm_responses/       # Recorded LLM responses
    ├── mongodb_data/        # Test data fixtures
    └── external_api_mocks/  # Starfish, Weather, AT mocks
```

### Core Test Fixtures (conftest.py)

| Fixture | Purpose | Usage |
|---------|---------|-------|
| `mock_dapr_client` | Mock DAPR service invocation & pub/sub | `await mock_dapr_client.publish_event(...)` |
| `mock_llm_client` | Mock OpenRouter with record/replay | `mock_llm_client.set_default_response({...})` |
| `mock_mongodb_client` | In-memory MongoDB mock | `db = mock_mongodb_client["collection_model"]` |
| `mock_collection_mcp` | Mock Collection Model MCP tools | `mock_collection_mcp.configure_tool_response(...)` |
| `mock_plantation_mcp` | Mock Plantation Model MCP tools | Same pattern as above |
| `mock_knowledge_mcp` | Mock Knowledge Model MCP tools | Same pattern as above |
| `mock_starfish_api` | Mock Starfish Network API | External API mock |
| `mock_weather_api` | Mock Weather API | External API mock |
| `mock_africas_talking_api` | Mock Africa's Talking SMS/Voice | External API mock |
| `test_data_factory` | Factory for test data | `test_data_factory.create_farmer(name="John")` |
| `golden_sample_loader` | Load golden samples | `golden_sample_loader.load_samples("agent_name")` |
| `sample_qc_payload` | Pre-built QC event payload | Direct use in tests |
| `sample_farmer` | Pre-built farmer data | Direct use in tests |

### Agent Testing Strategy

| Test Type | Purpose | Mocking | Location |
|-----------|---------|---------|----------|
| Unit | Individual node functions | Mock LLM, MCP, MongoDB | `tests/unit/` |
| Golden Sample | End-to-end agent accuracy | Real LLM, mock external data | `tests/golden/` |
| Integration | Cross-model workflows | Mock external APIs only | `tests/integration/` |
| Contract | DAPR event schema validation | None | `tests/contracts/` |

### Golden Sample Testing (Critical)

- **ALWAYS** maintain golden samples for each AI agent
- Store in `tests/golden/{agent_name}/samples.json`
- Include: input payload, expected output, acceptable variance
- Run golden tests on every PR that touches agent code
- Minimum samples per agent:

| Agent | Minimum Samples | Priority |
|-------|-----------------|----------|
| `qc_event_extractor` | 100+ | P0 |
| `quality_triage` | 100+ | P0 |
| `disease_diagnosis` | 50+ | P0 |
| `weather_impact_analyzer` | 30+ | P1 |
| `technique_assessment` | 30+ | P1 |
| `action_plan_generator` | 20+ | P1 |

### Test Markers

| Marker | Purpose | Run Command |
|--------|---------|-------------|
| `@pytest.mark.unit` | Fast, isolated unit tests | `pytest -m unit` |
| `@pytest.mark.integration` | Cross-model tests | `pytest -m integration` |
| `@pytest.mark.golden` | Golden sample accuracy tests | `pytest -m golden` |
| `@pytest.mark.contract` | Schema validation tests | `pytest -m contract` |
| `@pytest.mark.slow` | Slow tests (skip in CI fast mode) | `pytest -m "not slow"` |

### LLM Mocking

- Use `mock_llm_client` fixture from conftest.py
- Configure responses with `mock_llm_client.set_default_response({...})`
- Store recorded responses in `tests/fixtures/llm_responses/`
- **NEVER** mock LLM in golden sample tests (defeats purpose)

### MCP Tool Mocking

- Use `mock_collection_mcp`, `mock_plantation_mcp`, `mock_knowledge_mcp` fixtures
- Configure responses: `mock_collection_mcp.configure_tool_response("get_document", {...})`
- Check calls: `mock_collection_mcp.get_tool_calls("get_document")`

### Test Data Factory Usage

```python
# Create test farmer with defaults
farmer = test_data_factory.create_farmer()

# Create with overrides
farmer = test_data_factory.create_farmer(
    name="John Kamau",
    region="Nandi-Medium",
)

# Create QC event
event = test_data_factory.create_qc_event(grade="B", quality_score=78.0)
```

### Test Naming

- Test files: `test_{module_name}.py`
- Test functions: `test_{function_name}_{scenario}`
- Example: `test_triage_agent_routes_to_disease_analyzer`

### Running Tests

```bash
pytest tests/                      # All tests
pytest tests/unit/                 # Unit tests only
pytest tests/golden/ -m golden     # Golden sample tests
pytest tests/ -m "not slow"        # Skip slow tests
pytest tests/ --cov=src            # With coverage
pytest tests/ -x                   # Stop on first failure
```

---

## UI/UX Rules

### Design System Stack

| Technology | Purpose | Critical Notes |
|------------|---------|----------------|
| Tailwind CSS | Utility-first styling | Purge unused CSS for Kenya network conditions |
| shadcn/ui | Component library | Copy-paste components, Radix primitives with ARIA built-in |
| MUI v6 | DataGrid, Charts, Forms | Use with custom theme configuration |
| Inter | Typography | Clean, professional font family |

### Design Tokens (Mandatory)

| Token | Value | Usage |
|-------|-------|-------|
| `--color-win` | #22C55E | Primary ≥85%, success states |
| `--color-watch` | #F59E0B | Primary 70-84%, warnings |
| `--color-action` | #EF4444 | Primary <70%, errors, alerts |
| `--color-primary` | #16A34A | Brand, Forest Green, agriculture theme |
| `--color-secondary` | #5C4033 | Earth Brown |
| `--spacing-unit` | 4px | Base spacing multiplier |
| `--radius-default` | 6px | Cards and containers |
| `--radius-badge` | 16px | Status badges |

### Status Badge Pattern (Critical)

| Status | Color | Icon | Background | Threshold |
|--------|-------|------|------------|-----------|
| WIN | Forest Green `#1B4332` | ✅ | `#D8F3DC` | ≥85% Primary |
| WATCH | Harvest Gold `#D4A03A` | ⚠️ | `#FFF8E7` | 70-84% Primary |
| ACTION | Warm Red `#C1292E` | 🔴 | `#FFE5E5` | <70% Primary |

**Rule**: ALWAYS use color + icon + text label for status (color independence for accessibility)

### Custom Components Required

| Component | Purpose | Notes |
|-----------|---------|-------|
| StatusBadge | Quality category display | WIN/WATCH/ACTION variants |
| TrendIndicator | Quality trajectory | ↑ up, ↓ down, → stable |
| FarmerCard | Single farmer overview | Avatar, Primary %, trend, quick actions |
| LeafTypeTag | Issue identification | Coaching tooltips on hover/focus |
| ActionStrip | Dashboard header counts | Clickable category filters |
| SMSPreview | Template editing | Phone mockup with character count |

### Responsive Breakpoints (MUI v6)

| Breakpoint | Width | Layout |
|------------|-------|--------|
| xs | 0-599px | Single column, bottom navigation, stacked cards |
| sm | 600-899px | Optional 2-column, side-by-side buttons |
| md | 900-1199px | 2-column master-detail, filter sidebar |
| lg | 1200-1535px | Full Command Center, 3-column dashboard |
| xl | 1536px+ | 4-column capability, side-by-side comparison |

**Rule**: Mobile-first CSS, desktop-optimized for Factory/Admin dashboards

### Touch & Accessibility Requirements

| Requirement | Standard | Notes |
|-------------|----------|-------|
| Touch targets | 48x48px minimum | Buttons, icons, list items |
| Focus ring | 3px Forest Green outline | All interactive elements |
| WCAG level | 2.1 AA | Target compliance |
| Contrast ratio | 4.5:1 minimum | Text on backgrounds |

### Accessibility Patterns

- **Focus management**: Return focus to trigger after modal close
- **Skip links**: "Skip to main content" on Tab
- **ARIA labels**: `role="status"` for badges, `aria-live="polite"` for updates
- **Keyboard**: Tab navigation, Escape closes modals, Arrow keys in menus
- **Reduced motion**: Respect `prefers-reduced-motion` media query

### Multi-Channel Consistency

| Channel | Format | Rules |
|---------|--------|-------|
| Dashboard | StatusBadge components | WIN/WATCH/ACTION with icons |
| SMS | Emoji + text (160 chars) | ✅ for WIN, ⚠️ for WATCH, 🔴 for ACTION |
| Voice IVR | Spoken audio | Numbered menus, 0.8s pauses between options |

**SMS Template Pattern**:
```
[Name], chai yako:
[Status Emoji] [Primary %] daraja la kwanza
Tatizo: [Leaf Type Issue]
[Action Tip]
```

### UI Anti-Patterns to Avoid

- **NO hardcoded colors** - Always use design tokens
- **NO status without icons** - Color alone is not accessible
- **NO touch targets < 48px** - Field officers use mobile in field conditions
- **NO hover-only interactions** - Must work with touch
- **NO blocking modals for confirmations** - Use toast/snackbar for success
- **NO infinite scroll without pagination fallback** - Kenya network conditions

### Form Patterns

| Pattern | Rule |
|---------|------|
| Required fields | Red asterisk (*) after label |
| Validation | Inline below field on blur, summary at top on submit |
| Error state | `#C1292E` border + ✕ icon + error text |
| Phone format | Auto-format to +254 XXX XXX XXX |

### Loading & Empty States

| Context | Pattern |
|---------|---------|
| Initial page load | Skeleton screens (match actual layout) |
| Data refresh | Spinner in header after 500ms |
| Button action | Inline spinner after 200ms |
| No results | Illustration + message + action button |
| No farmers need action | "No farmers need action today 🎉" (celebration) |

---

## Critical Don't-Miss Rules

### Anti-Patterns to Avoid

- **NO direct LLM provider calls** - Always use OpenRouter gateway
- **NO synchronous I/O** - All database, HTTP, MCP calls must be async
- **NO cross-model database access** - Use MCP servers for data retrieval
- **NO hardcoded prompts** - All prompts loaded from MongoDB
- **NO in-memory state in MCP servers** - They must be stateless
- **NO cron jobs in code** - Use DAPR Jobs for scheduling
- **NO environment variables for secrets** - Use DAPR Secret Store

### LLM Cost Optimization

- Use Haiku for triage/classification (fast, cheap: ~$0.001/call)
- Use Sonnet for analysis requiring reasoning
- Use Sonnet for vision tasks (image analysis)
- ALWAYS set `max_tokens` to prevent runaway costs
- Cache RAG context - don't re-fetch for same request

### Vision Processing

- Triage images with Haiku at 256x256 resolution first
- Only send full resolution to Sonnet if triage indicates need
- Store images in Azure Blob, pass URLs not base64 when possible

### Farmer Context

- Farmers are often basic users with limited English
- Action plans must be simple, clear, actionable
- Generate triple-format output: detailed (factory), SMS summary (farmer), voice script (farmer via IVR)
- Support SMS + Voice IVR delivery for farmer messages
- Voice IVR enables low-literacy farmers to hear detailed explanations in local languages

### SMS Cost Optimization (Notification Model)

- Target **1-2 SMS segments** per message (160 chars GSM-7, 70 chars Unicode)
- Use GSM-7 encoding when possible (avoid emojis, special characters)
- Action Generator must output `sms_summary` field (max 300 chars)
- Tiered strategy: critical alerts = immediate, routine = batched daily digest
- Two-way SMS: support keyword commands (STOP, HELP, STATUS)
- Include Voice IVR prompt in SMS: "Piga *384# kwa maelezo zaidi" (Call *384# for more details)

### Voice IVR Rules (Notification Model)

- **Purpose**: Provide detailed action plan explanations for low-literacy farmers via spoken audio
- **Providers**: Africa's Talking (primary), Twilio (fallback) for IVR; Google Cloud TTS / Amazon Polly for TTS
- **Languages supported**: Swahili (sw-KE), Kikuyu (ki-KE), Luo (luo-KE)

**Voice Script Generation:**
- Action Generator must output `voice_script` field alongside `sms_summary`
- Voice scripts use `VoiceScript` Pydantic model with: greeting, quality_summary, main_actions (max 3), closing
- Maximum voice script length: 2000 chars (~3 minutes of speech)
- Use simple language (6th-grade reading level equivalent)
- Action items start with verbs: "Anika..." (Dry...), "Usivune..." (Don't harvest...)

**IVR Call Flow:**
1. Farmer dials shortcode (*384#)
2. Caller ID lookup → farmer identification (fallback: enter farmer ID)
3. Language selection via DTMF (1=Swahili, 2=Kikuyu, 3=Luo)
4. TTS plays personalized action plan (2-3 minutes)
5. Options menu: replay (1), help (2), end (9)

**TTS Configuration:**
- Speaking rate: 0.9x (slightly slower for clarity)
- Pauses: 0.5s after greeting, 0.8s between action items
- Audio encoding: MP3, 8kHz sample rate (phone quality)
- Max call duration: 5 minutes (cost control)
- Max replays: 3 per call (abuse prevention)

**Voice IVR Anti-Patterns:**
- **NO hardcoded language strings** - All voice content via templates in MongoDB
- **NO synchronous TTS calls** - Pre-generate audio or stream asynchronously
- **NO storing raw audio** - Generate on-demand or cache with TTL

### Conversational AI Rules

- **Purpose**: Enable interactive two-way dialogue with farmers via voice chatbot and text chat
- **Channels**: Voice chatbot (phone), WhatsApp chat, SMS text
- **Architecture**: Open-Closed Principle - base handler + channel-specific adapters

**Channel Adapters:**
- `VoiceChatbotAdapter`: Real-time voice dialogue, STT/TTS integration
- `WhatsAppChatAdapter`: Async text messaging, media support
- `SMSChatAdapter`: Simple text exchange, 160-char limits

**Session Management:**
- Store sessions in `conversational_ai_model.sessions` collection
- Session timeout: 30 minutes of inactivity
- Persist conversation history for context across turns
- Use `session_id` to link multi-turn conversations

**Integration Pattern:**
- Conversational AI Model invokes AI Model for LLM processing
- Uses existing MCP servers for data retrieval (does NOT expose own MCP)
- Hands off final delivery to Notification Model

**Conversational AI Anti-Patterns:**
- **NO direct LLM calls** - Always invoke via AI Model
- **NO final message delivery** - Hand off to Notification Model
- **NO business data ownership** - Query via MCP servers

### Event Deduplication

- Same farmer may have multiple quality events in short period
- Use DAPR Jobs to aggregate before triggering expensive analysis
- Deduplicate by farmer_id + time window (e.g., 1 hour)

### Confidence Thresholds

- Triage routing: >= 0.7 = single analyzer, < 0.7 = parallel
- Diagnosis aggregation: primary = highest confidence, secondary >= 0.5
- A/B test traffic: typically 10-20% for variant

### Deployment

- Single Kubernetes namespace per environment (qa, preprod, prod)
- ConfigMaps for environment-specific settings
- Secrets for credentials (MongoDB, API keys)
- All models deployed as separate pods in same namespace

---

## Reference Documents

This file contains critical rules. For detailed decisions not covered here:

| Need | Document |
|------|----------|
| **Repository Structure** | `_bmad-output/architecture/repository-structure.md` |
| Decision inventory + traceability | `_bmad-output/architecture-decision-index.md` |
| Full architectural rationale | `_bmad-output/architecture/index.md` |
| AI Model implementation details | `_bmad-output/ai-model-developer-guide/index.md` |
| **Test Architecture & Strategy** | `_bmad-output/test-design-system-level.md` |
| **UX Design Specification** | `_bmad-output/ux-design-specification/index.md` |
| Component specifications | `_bmad-output/ux-design-specification/6-component-strategy.md` |
| UX consistency patterns | `_bmad-output/ux-design-specification/7-ux-consistency-patterns.md` |
| Responsive & accessibility | `_bmad-output/ux-design-specification/8-responsive-design-accessibility.md` |
| **Lessons Learned** | `_bmad-output/lessons-learned/` (code review findings, common mistakes) |

**When to look up more detail:**
- Implementing a specific domain model feature (Plantation, Collection, etc.)
- Unsure about a pattern not explicitly covered here
- Need the "why" behind a decision, not just the "what"
- **Implementing frontend components** - See UX Design Specification for visual patterns, component specs, and accessibility requirements
- **Writing tests** - See Test Architecture for fixtures, golden samples, and test patterns
- **Implementing gRPC services** - See Lessons Learned for common mistakes (referential integrity, input validation, mock patterns)

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Check `architecture-decision-index.md` for decisions not covered here
- Update this file if new patterns emerge

**For Humans:**

- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

---

_Last Updated: 2025-12-23_
