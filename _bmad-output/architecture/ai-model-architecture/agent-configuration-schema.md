# Agent Configuration Schema

Agent configurations follow the same pattern as `SourceConfig` in Collection Model, with **MongoDB Change Streams for cache invalidation** (see ADR-013).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AGENT CONFIGURATION FLOW                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  GIT (Source of Truth)                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  config/agents/                                                  │   │
│  │  ├── disease-diagnosis.yaml                                      │   │
│  │  ├── weekly-action-plan.yaml                                     │   │
│  │  └── dialogue-responder.yaml                                     │   │
│  │                                                                  │   │
│  │  Benefits: Version controlled, PR reviewable, IDE support        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ CI/CD: farmer-cli agent publish          │
│                              ▼                                          │
│  MONGODB (Runtime Storage)                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Collection: agent_configs                                       │   │
│  │  { agent_id: "disease-diagnosis", type: "explorer", ... }        │   │
│  │                                                                  │   │
│  │  Benefits: Hot-reloadable, no redeploy for config changes        │   │
│  └──────────────────────────┬──────────────────────────────────────┘   │
│                              │                                          │
│            ┌─────────────────┴─────────────────┐                        │
│            │      MongoDB Change Stream         │                        │
│            │   (insert, update, delete watch)   │                        │
│            └─────────────────┬─────────────────┘                        │
│                              │ Invalidate on change                     │
│                              ▼                                          │
│  AI MODEL RUNTIME (AgentConfigService)                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Agent Config Cache (ADR-013 Pattern)                           │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │  • Warmed on startup (before accepting requests)          │  │   │
│  │  │  • Invalidated via Change Stream (real-time)              │  │   │
│  │  │  • TTL fallback: 5 minutes (safety net)                   │  │   │
│  │  │  • Metrics: hits, misses, invalidations, age, size        │  │   │
│  │  │  • Base class: MongoChangeStreamCache[AgentConfig]        │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  │                                                                  │   │
│  │  class AgentConfig(BaseModel):                                   │   │
│  │      agent_id: str                                               │   │
│  │      type: Literal["extractor", "explorer", "generator",         │   │
│  │                    "conversational", "tiered-vision"]            │   │
│  │      version: str                                                │   │
│  │      input: InputConfig                                          │   │
│  │      output: OutputConfig                                        │   │
│  │      llm: LLMConfig                                              │   │
│  │      ...                                                         │   │
│  │                                                                  │   │
│  │  Benefits: Type-safe, validated, IDE autocomplete                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Agent Config Cache Behavior (ADR-013)

| Event | Behavior |
|-------|----------|
| Service starts | Cache warmed immediately before accepting requests |
| Config inserted | Change Stream fires → cache invalidated → next request loads fresh |
| Config updated | Change Stream fires → cache invalidated → next request loads fresh |
| Config deleted | Change Stream fires → cache invalidated → next request loads fresh |
| TTL expires (fallback) | Next request reloads from database |

**OpenTelemetry Metrics:**

| Metric | Type | Purpose |
|--------|------|---------|
| `agent_config_cache_hits_total` | Counter | Track cache efficiency |
| `agent_config_cache_misses_total` | Counter | Alert on high miss rate |
| `agent_config_cache_invalidations_total` | Counter | Monitor change frequency |
| `agent_config_cache_age_seconds` | Gauge | Detect stale cache |
| `agent_config_cache_size` | Gauge | Verify configs loaded |

**YAML Schemas by Agent Type:**

Each agent type has common fields plus type-specific configuration. Below are complete examples for each type.

---

## Extractor YAML Schema

```yaml
# config/agents/qc-event-extractor.yaml
agent:
  id: "qc-event-extractor"
  type: extractor
  version: "1.0.0"
  description: "Extracts structured data from QC analyzer payloads"

  input:
    event: "collection.document.received"
    schema:
      required: [doc_id]
      optional: [source, event_type]

  output:
    event: "ai.extraction.complete"
    schema:
      fields: [farmer_id, grade, quality_score, validation_warnings]

  mcp_sources:
    - server: collection
      tools: [get_document]

  # ═══════════════════════════════════════════════════════════════════
  # EXTRACTOR: Single LLM, fast model for structured extraction
  # ═══════════════════════════════════════════════════════════════════
  llm:
    model: "anthropic/claude-3-haiku"    # Fast, cheap for extraction
    temperature: 0.1                      # Very deterministic
    max_tokens: 500

  # NOTE: Prompts are stored separately in MongoDB (see Prompt Management section)
  # Loaded at runtime by agent_id lookup

  # EXTRACTOR-SPECIFIC: Schema for extraction validation
  extraction_schema:
    required_fields: [farmer_id, grade]
    validation_rules:
      - field: farmer_id
        pattern: "^WM-\\d+$"
      - field: quality_score
        range: [0, 100]

  # EXTRACTOR-SPECIFIC: Value normalization
  normalization_rules:
    - field: grade
      uppercase: true
    - field: farmer_id
      prefix: "WM-"

  error_handling:
    max_attempts: 3
    backoff_ms: [100, 500, 2000]
    on_failure: "publish_error_event"
```

---

## Explorer YAML Schema

```yaml
# config/agents/disease-diagnosis.yaml
agent:
  id: "disease-diagnosis"
  type: explorer
  version: "1.0.0"
  description: "Analyzes quality issues and produces diagnosis"

  input:
    event: "collection.poor_quality_detected"
    schema:
      required: [doc_id, farmer_id]
      optional: [quality_issues, grade]

  output:
    event: "ai.diagnosis.complete"
    schema:
      fields: [diagnosis, confidence, severity, details, recommendations]

  mcp_sources:
    - server: collection
      tools: [get_document, get_farmer_documents]
    - server: plantation
      tools: [get_farmer, get_farmer_summary]

  # ═══════════════════════════════════════════════════════════════════
  # EXPLORER: Single LLM, capable model for analysis
  # ═══════════════════════════════════════════════════════════════════
  llm:
    model: "anthropic/claude-3-5-sonnet"   # Complex reasoning
    temperature: 0.3
    max_tokens: 2000

  # NOTE: Prompts are stored separately in MongoDB (see Prompt Management section)
  # Loaded at runtime by agent_id lookup

  # EXPLORER-SPECIFIC: RAG for expert knowledge
  rag:
    enabled: true
    query_template: "tea leaf quality issues {{quality_issues}} {{grade}}"
    knowledge_domains: [plant_diseases, tea_cultivation, quality_standards]
    top_k: 5
    min_similarity: 0.7

  error_handling:
    max_attempts: 3
    backoff_ms: [100, 500, 2000]
    on_failure: "publish_error_event"
    dead_letter_topic: "ai.errors.dead_letter"
```

---

## Generator YAML Schema

```yaml
# config/agents/weekly-action-plan.yaml
agent:
  id: "weekly-action-plan"
  type: generator
  version: "1.0.0"
  description: "Generates personalized weekly action plans for farmers"

  input:
    event: "action_plan.generation.requested"
    schema:
      required: [farmer_id, week_start]
      optional: [priority_issues]

  output:
    event: "ai.action_plan.complete"
    schema:
      fields: [plan_markdown, farmer_message, priority_actions]

  mcp_sources:
    - server: knowledge
      tools: [get_farmer_diagnoses, get_open_issues]
    - server: plantation
      tools: [get_farmer, get_farm_details]
    - server: market
      tools: [get_upcoming_auctions]

  # ═══════════════════════════════════════════════════════════════════
  # GENERATOR: Single LLM, creative for content generation
  # ═══════════════════════════════════════════════════════════════════
  llm:
    model: "anthropic/claude-3-5-sonnet"   # Translation, cultural context
    temperature: 0.5                        # More creative
    max_tokens: 3000

  # NOTE: Prompts are stored separately in MongoDB (see Prompt Management section)
  # Loaded at runtime by agent_id lookup

  # GENERATOR-SPECIFIC: RAG for best practices
  rag:
    enabled: true
    query_template: "tea farming best practices {{season}} {{region}}"
    knowledge_domains: [tea_cultivation, regional_context, seasonal_guidance]
    top_k: 5

  # GENERATOR-SPECIFIC: Output format
  output_format: markdown

  error_handling:
    max_attempts: 3
    backoff_ms: [100, 500, 2000]
    on_failure: "publish_error_event"
```

---

## Conversational YAML Schema

```yaml
# config/agents/dialogue-responder.yaml
agent:
  id: "dialogue-responder"
  type: conversational
  version: "1.0.0"
  description: "Handles multi-turn dialogue with farmers via voice/WhatsApp"

  input:
    event: "conversation.turn.received"
    schema:
      required: [session_id, user_message, channel]
      optional: [farmer_id, locale]

  output:
    event: "conversation.turn.response"
    schema:
      fields: [response_text, suggested_actions, session_state]

  mcp_sources:
    - server: plantation
      tools: [get_farmer, get_farm_summary]
    - server: knowledge
      tools: [get_recent_diagnoses]
    - server: action_plan
      tools: [get_current_plan]

  # ═══════════════════════════════════════════════════════════════════
  # CONVERSATIONAL: Two LLMs (intent + response)
  # ═══════════════════════════════════════════════════════════════════
  intent_model: "anthropic/claude-3-haiku"      # Fast classification
  response_model: "anthropic/claude-3-5-sonnet"  # Quality responses

  llm:
    temperature: 0.4
    max_tokens: 500

  # NOTE: Prompts are stored separately in MongoDB (see Prompt Management section)
  # Loaded at runtime by agent_id lookup

  # CONVERSATIONAL-SPECIFIC: RAG for knowledge grounding
  rag:
    enabled: true
    query_template: "{{user_intent}} {{context_summary}}"
    knowledge_domains: [tea_cultivation, common_questions, troubleshooting]
    top_k: 3

  # CONVERSATIONAL-SPECIFIC: Session state management
  state:
    max_turns: 5
    session_ttl_minutes: 30
    checkpoint_backend: mongodb
    context_window: 3                  # Keep last N turns in context

  error_handling:
    max_attempts: 2
    backoff_ms: [100, 300]
    on_failure: "graceful_fallback"    # Return helpful error message
```

---

## Tiered-Vision YAML Schema

```yaml
# config/agents/leaf-quality-analyzer.yaml
agent:
  id: "leaf-quality-analyzer"
  type: tiered-vision
  version: "1.0.0"
  description: "Cost-optimized image analysis for tea leaf quality"

  input:
    event: "collection.image.received"
    schema:
      required: [doc_id, thumbnail_url, original_url]
      optional: [metadata, farmer_id]

  output:
    event: "ai.vision_analysis.complete"
    schema:
      fields: [classification, confidence, diagnosis, tier_used, cost]

  mcp_sources:
    - server: collection
      tools: [get_document_thumbnail, get_document_original]
    - server: plantation
      tools: [get_farmer, get_farm_context]

  # ═══════════════════════════════════════════════════════════════════
  # TIERED-VISION: Two-tier LLM (screen + diagnose)
  # ═══════════════════════════════════════════════════════════════════
  tiered_llm:
    screen:                              # Tier 1: Fast screening
      model: "anthropic/claude-3-haiku"
      temperature: 0.1
      max_tokens: 200
    diagnose:                            # Tier 2: Deep analysis
      model: "anthropic/claude-3-5-sonnet"
      temperature: 0.3
      max_tokens: 2000

  # NOTE: Prompts are stored separately in MongoDB (see Prompt Management section)
  # Loaded at runtime by agent_id lookup

  # TIERED-VISION-SPECIFIC: Routing thresholds
  routing:
    screen_threshold: 0.7               # Escalate to Tier 2 if confidence < 0.7
    healthy_skip_threshold: 0.85        # Skip Tier 2 for "healthy" above this
    obvious_skip_threshold: 0.75        # Skip Tier 2 for "obvious_issue" above this

  # TIERED-VISION-SPECIFIC: RAG (Tier 2 only)
  rag:
    enabled: true
    query_template: "tea leaf symptoms {{screen_findings}}"
    knowledge_domains: [plant_diseases, visual_symptoms, tea_cultivation]
    top_k: 5

  error_handling:
    max_attempts: 3
    backoff_ms: [100, 500, 2000]
    on_failure: "publish_error_event"
```

---

## Schema Comparison Summary

| Field | Extractor | Explorer | Generator | Conversational | Tiered-Vision |
|-------|-----------|----------|-----------|----------------|---------------|
| `llm` | ✓ (single) | ✓ (single) | ✓ (single) | ✓ (base config) | ✗ |
| `intent_model` | ✗ | ✗ | ✗ | ✓ | ✗ |
| `response_model` | ✗ | ✗ | ✗ | ✓ | ✗ |
| `tiered_llm` | ✗ | ✗ | ✗ | ✗ | ✓ |
| `rag` | ✗ | ✓ | ✓ | ✓ | ✓ (Tier 2) |
| `extraction_schema` | ✓ | ✗ | ✗ | ✗ | ✗ |
| `normalization_rules` | ✓ | ✗ | ✗ | ✗ | ✗ |
| `output_format` | ✗ | ✗ | ✓ | ✗ | ✗ |
| `state` | ✗ | ✗ | ✗ | ✓ | ✗ |
| `routing` | ✗ | ✗ | ✗ | ✗ | ✓ |

**Pydantic Models (application code):**

Uses base class + type-specific models with Pydantic discriminated unions:

```python
from typing import Annotated, Literal
from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════════════════
# SHARED COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════

class LLMConfig(BaseModel):
    """LLM configuration for agent execution."""
    model: str                          # Explicit model, e.g. "anthropic/claude-3-5-sonnet"
    temperature: float = 0.3
    max_tokens: int = 2000

class RAGConfig(BaseModel):
    """RAG retrieval configuration."""
    enabled: bool = True
    query_template: str | None = None
    knowledge_domains: list[str] = []
    top_k: int = 5
    min_similarity: float = 0.7

class InputConfig(BaseModel):
    """Agent input contract."""
    event: str
    schema: dict

class OutputConfig(BaseModel):
    """Agent output contract."""
    event: str
    schema: dict

class MCPSourceConfig(BaseModel):
    """MCP server data source."""
    server: str
    tools: list[str]

class ErrorHandlingConfig(BaseModel):
    """Error handling and retry configuration."""
    max_attempts: int = 3
    backoff_ms: list[int] = [100, 500, 2000]
    on_failure: Literal["publish_error_event", "dead_letter"] = "publish_error_event"
    dead_letter_topic: str | None = None

class StateConfig(BaseModel):
    """Conversation state management (Conversational only)."""
    max_turns: int = 5
    session_ttl_minutes: int = 30
    checkpoint_backend: Literal["mongodb"] = "mongodb"
    context_window: int = 3                 # Number of previous turns to include in prompt

# ═══════════════════════════════════════════════════════════════════════════
# BASE CLASS (common fields)
# ═══════════════════════════════════════════════════════════════════════════

class AgentConfigBase(BaseModel):
    """Base configuration shared by all agent types."""
    agent_id: str
    version: str
    description: str
    input: InputConfig
    output: OutputConfig
    llm: LLMConfig
    mcp_sources: list[MCPSourceConfig] = []
    error_handling: ErrorHandlingConfig = Field(default_factory=ErrorHandlingConfig)

# ═══════════════════════════════════════════════════════════════════════════
# TYPE-SPECIFIC MODELS
# ═══════════════════════════════════════════════════════════════════════════

class ExtractorConfig(AgentConfigBase):
    """Extractor agent: structured data from unstructured input."""
    type: Literal["extractor"] = "extractor"
    extraction_schema: dict
    normalization_rules: list[str] | None = None

class ExplorerConfig(AgentConfigBase):
    """Explorer agent: analyze, diagnose, find patterns."""
    type: Literal["explorer"] = "explorer"
    rag: RAGConfig

class GeneratorConfig(AgentConfigBase):
    """Generator agent: create content (plans, reports, messages)."""
    type: Literal["generator"] = "generator"
    rag: RAGConfig
    output_format: Literal["json", "markdown", "text"] = "markdown"

class ConversationalConfig(AgentConfigBase):
    """Conversational agent: multi-turn dialogue with persona."""
    type: Literal["conversational"] = "conversational"
    rag: RAGConfig
    state: StateConfig = Field(default_factory=StateConfig)
    intent_model: str = "anthropic/claude-3-haiku"
    response_model: str = "anthropic/claude-3-5-sonnet"

class TieredVisionLLMConfig(BaseModel):
    """Two-tier LLM configuration for vision processing."""
    screen: LLMConfig                       # Tier 1: Fast screening (Haiku)
    diagnose: LLMConfig                     # Tier 2: Deep analysis (Sonnet)

class TieredVisionRoutingConfig(BaseModel):
    """Routing configuration for tiered vision processing."""
    screen_threshold: float = 0.7           # Escalate to Tier 2 if confidence < threshold
    healthy_skip_threshold: float = 0.85    # Skip Tier 2 for "healthy" above this
    obvious_skip_threshold: float = 0.75    # Skip Tier 2 for "obvious_issue" above this

class TieredVisionConfig(AgentConfigBase):
    """Tiered-Vision agent: cost-optimized image analysis with two-tier processing."""
    type: Literal["tiered-vision"] = "tiered-vision"
    llm: LLMConfig | None = None            # Override base: not used, tiered_llm replaces it
    rag: RAGConfig                          # Used in Tier 2 only
    tiered_llm: TieredVisionLLMConfig       # Two-tier LLM config (screen + diagnose)
    routing: TieredVisionRoutingConfig = Field(default_factory=TieredVisionRoutingConfig)

# ═══════════════════════════════════════════════════════════════════════════
# DISCRIMINATED UNION (automatic type detection)
# ═══════════════════════════════════════════════════════════════════════════

AgentConfig = Annotated[
    ExtractorConfig | ExplorerConfig | GeneratorConfig | ConversationalConfig | TieredVisionConfig,
    Field(discriminator="type")
]

# Usage: Pydantic automatically selects correct type based on "type" field
# config_dict = {"agent_id": "disease-diagnosis", "type": "explorer", ...}
# agent = AgentConfig.model_validate(config_dict)  # Returns ExplorerConfig
```

**Why this pattern:**

| Benefit | Description |
|---------|-------------|
| **Strong typing** | IDE knows exact fields for each agent type |
| **Clean validation** | Each type validates its required fields, no conditionals |
| **Automatic loading** | Pydantic discriminator selects correct class from `type` field |
| **Extensible** | New agent type = add class + update union |
| **Consistent** | Matches `SourceConfig` pattern in Collection Model |
