# AI Model Architecture

## Overview

The AI Model is the **6th Domain Model** - the centralized intelligence layer for the Farmer Power Cloud Platform. Unlike the previous design where AI agents were embedded in each domain model, all AI logic is centralized here.

**Core Responsibility:** Execute AI workflows (extraction, diagnosis, content generation) on behalf of other domain models.

**Does NOT:** Own business data, make business decisions about when to run, or store results persistently.

## Document Boundaries

> **This is the source of truth for HOW AI works.** Other domain model documents define WHAT and WHEN; this document defines HOW.

```
┌─────────────────────────────────────────────────────────────────────────┐
│              ARCHITECTURE DOCUMENT RESPONSIBILITIES                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  KNOWLEDGE MODEL ARCHITECTURE                                           │
│  ├── Owns: WHAT to diagnose, WHEN to trigger, WHERE to store results   │
│  ├── Owns: Business requirements for analysis outputs                   │
│  ├── Owns: MCP tools exposed to other models                           │
│  └── References: AI Model for agent implementation details              │
│                                                                         │
│  ACTION PLAN MODEL ARCHITECTURE                                         │
│  ├── Owns: WHAT to generate, WHEN to run (weekly), WHO receives        │
│  ├── Owns: Output formats (detailed report + farmer message)           │
│  ├── Owns: Translation/simplification requirements                      │
│  └── References: AI Model for generator implementation details          │
│                                                                         │
│  CONVERSATIONAL AI MODEL ARCHITECTURE                                   │
│  ├── Owns: Channel adapters (voice, WhatsApp, web chat)                │
│  ├── Owns: Persona configurations (tone, language, constraints)        │
│  ├── Owns: Session management, turn coordination                        │
│  ├── Owns: Intent handlers (plugin registry)                           │
│  └── References: AI Model for conversational agent implementation       │
│                                                                         │
│  AI MODEL ARCHITECTURE (this document)                                  │
│  ├── Owns: Agent types (5: Extractor, Explorer, Generator,             │
│  │         Conversational, Tiered-Vision)                              │
│  ├── Owns: Agent instance configurations (YAML specs)                  │
│  ├── Owns: LLM gateway configuration (OpenRouter, model routing)       │
│  ├── Owns: RAG engine (Pinecone, knowledge domains, versioning)        │
│  ├── Owns: Prompt management (MongoDB, A/B testing, lifecycle)         │
│  ├── Owns: LangGraph workflows (saga patterns, checkpointing)          │
│  ├── Owns: Tiered processing (vision cost optimization)                │
│  └── Owns: Observability (tracing, cost tracking)                      │
│                                                                         │
│  CROSS-REFERENCES:                                                      │
│  • Knowledge Model → AI Model: "Analyzer implementation in AI Model"   │
│  • Action Plan → AI Model: "Generator implementation in AI Model"      │
│  • Conversational → AI Model: "Conversational agent implementation"    │
│  • AI Model → Knowledge Model: "Business context for diagnosis agents" │
│  • AI Model → Action Plan: "Business context for generator agents"     │
│  • AI Model → Conversational: "Channel/persona context for dialogue"   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why this separation matters:**
- **Avoid duplication:** Agent specs live in ONE place (here)
- **Clear ownership:** Business logic vs implementation logic
- **Easier maintenance:** Change prompts here, not in 3 documents
- **Reduced confusion:** Developers know where to look

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AI MODEL                                       │
│                   (6th Domain Model)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    WORKFLOW ENGINE                               │   │
│  │                                                                  │   │
│  │  Agent Types (in code):                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │  EXTRACTOR  │  │  EXPLORER   │  │  GENERATOR  │              │   │
│  │  │             │  │             │  │             │              │   │
│  │  │ • Extract   │  │ • Analyze   │  │ • Create    │              │   │
│  │  │ • Validate  │  │ • Diagnose  │  │ • Translate │              │   │
│  │  │ • Normalize │  │ • Pattern   │  │ • Format    │              │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │   │
│  │  ┌───────────────────────────────────────────────┐              │   │
│  │  │  CONVERSATIONAL                               │              │   │
│  │  │                                               │              │   │
│  │  │ • Intent classify  • Dialogue respond        │              │   │
│  │  │ • Context manage   • Persona adapt           │              │   │
│  │  └───────────────────────────────────────────────┘              │   │
│  │                                                                  │   │
│  │  Agent Instances (YAML → MongoDB → Pydantic):                                  │   │
│  │  • qc-event-extractor                                            │   │
│  │  • quality-triage (fast cause classification)                    │   │
│  │  • disease-diagnosis                                             │   │
│  │  • weather-impact-analyzer                                       │   │
│  │  • technique-assessment                                          │   │
│  │  • trend-analyzer                                                │   │
│  │  • weekly-action-plan                                            │   │
│  │  • market-analyzer                                               │   │
│  │  • dialogue-responder (multi-turn conversation)                  │   │
│  │  • intent-classifier (fast intent detection)                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│            ┌─────────────┴─────────────┐                                │
│            ▼                           ▼                                │
│  ┌──────────────────┐       ┌──────────────────────┐                   │
│  │   LLM GATEWAY    │       │     RAG ENGINE       │                   │
│  │                  │       │                      │                   │
│  │  • OpenRouter    │       │  ┌────────────────┐  │                   │
│  │  • Model routing │       │  │  Vector DB     │  │                   │
│  │  • Cost tracking │       │  │  (Pinecone)    │  │                   │
│  │  • Retry/fallback│       │  │                │  │                   │
│  │                  │       │  │  • Tea diseases│  │                   │
│  └──────────────────┘       │  │  • Best practices│ │                   │
│                             │  │  • Weather patterns│                   │
│                             │  │  • Regional knowledge                  │
│                             │  └────────────────┘  │                   │
│                             │                      │                   │
│                             │  Access: internal    │                   │
│                             │  Curation: Admin UI  │                   │
│                             └──────────────────────┘                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    MCP CLIENTS (gRPC via DAPR)                   │   │
│  │  • Collection MCP (fetch documents)                              │   │
│  │  • Plantation MCP (fetch farmer context)                         │   │
│  │  • Knowledge MCP (fetch analyses)                                │   │
│  │                                                                  │   │
│  │  Protocol: gRPC (not JSON-RPC) - see infrastructure-decisions   │   │
│  │  Transport: DAPR service invocation                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Persistence: STATELESS (results published via events)                  │
│  MCP Server: NONE (domain models don't query AI Model)                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Communication Pattern

The AI Model uses **event-driven async communication** via DAPR:

```
Domain Models                          AI Model
┌─────────────────┐                   ┌─────────────────────────────┐
│                 │   publish event   │                             │
│  Collection     │──────────────────▶│   1. Receive event (ref)    │
│  Knowledge      │   { doc_id }      │   2. Fetch data via MCP     │
│  Action Plan    │                   │   3. Run agent workflow     │
│  Plantation     │◀──────────────────│   4. Publish result event   │
│  Market         │   result event    │                             │
│                 │   { result }      │                             │
└─────────────────┘                   └─────────────────────────────┘
     No AI logic                           All AI logic here
     No RAG access
```

**Event Flow Example - Quality Document Processing:**

```
1. Collection Model receives QC payload via API
2. Collection stores raw document → doc_id = "doc-123"
3. Collection publishes via DAPR Pub/Sub:
   topic: "collection.document.received"
   payload: { doc_id: "doc-123", source: "qc-analyzer", event_type: "END_BAG" }

4. AI Model subscribes, receives event
5. AI Model calls Collection MCP: get_document("doc-123")
6. AI Model runs extraction agent workflow
7. AI Model publishes via DAPR Pub/Sub:
   topic: "ai.extraction.complete"
   payload: {
     doc_id: "doc-123",
     success: true,
     result: {
       farmer_id: "WM-4521",
       grade: "B",
       quality_score: 78,
       validation_warnings: []
     }
   }

8. Collection Model subscribes, receives result
9. Collection updates document with extracted fields
```

## Agent Types

Five agent types are implemented in code, each with a specific workflow pattern.

> **Implementation details:** See `ai-model-developer-guide/3-agent-development.md` for creating new agents and `ai-model-developer-guide/1-sdk-framework.md` for LangChain vs LangGraph usage patterns.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AGENT TYPES (5)                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                     │
│  │  EXTRACTOR  │  │  EXPLORER   │  │  GENERATOR  │                     │
│  │             │  │             │  │             │                     │
│  │ • Extract   │  │ • Analyze   │  │ • Create    │                     │
│  │ • Validate  │  │ • Diagnose  │  │ • Translate │                     │
│  │ • Normalize │  │ • Pattern   │  │ • Format    │                     │
│  │             │  │             │  │             │                     │
│  │ LLM: 1      │  │ LLM: 1      │  │ LLM: 1      │                     │
│  └─────────────┘  └─────────────┘  └─────────────┘                     │
│                                                                         │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐      │
│  │  CONVERSATIONAL             │  │  TIERED-VISION              │      │
│  │                             │  │                             │      │
│  │ • Intent classify           │  │ • Screen (Tier 1)           │      │
│  │ • Dialogue respond          │  │ • Diagnose (Tier 2)         │      │
│  │ • Context manage            │  │ • Conditional routing       │      │
│  │                             │  │                             │      │
│  │ LLM: 2 (intent + response)  │  │ LLM: 2 (screen + diagnose)  │      │
│  └─────────────────────────────┘  └─────────────────────────────┘      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Extractor Type

**Purpose:** Extract structured data from unstructured/semi-structured input

```yaml
agent_type: extractor
workflow:
  1_fetch: "Fetch document via MCP"
  2_extract: "LLM extracts fields per schema"
  3_validate: "Validate extracted data"
  4_normalize: "Normalize values (dates, IDs, etc.)"
  5_output: "Publish extraction result"

defaults:
  llm:
    model: "anthropic/claude-3-haiku"   # Fast, cheap for structured extraction
    temperature: 0.1                     # Very deterministic
    output_format: "json"
  rag:
    enabled: false                       # Extractors typically don't need RAG
```

### Explorer Type

**Purpose:** Analyze data, find patterns, produce diagnoses

```yaml
agent_type: explorer
workflow:
  1_fetch: "Fetch relevant documents via MCP"
  2_context: "Build context (farmer history, regional data)"
  3_rag: "Retrieve expert knowledge if enabled"
  4_analyze: "LLM analyzes with full context"
  5_output: "Publish analysis result"

defaults:
  llm:
    model: "anthropic/claude-3-5-sonnet"   # Complex reasoning, accuracy critical
    temperature: 0.3
    output_format: "json"
  rag:
    enabled: true
    top_k: 5
```

### Generator Type

**Purpose:** Create content (plans, reports, messages)

```yaml
agent_type: generator
workflow:
  1_fetch: "Fetch source analyses via MCP"
  2_context: "Build farmer/recipient context"
  3_prioritize: "Rank and prioritize inputs"
  4_generate: "LLM generates content"
  5_format: "Apply output formatting"
  6_output: "Publish generated content"

defaults:
  llm:
    model: "anthropic/claude-3-5-sonnet"   # Translation, simplification, cultural context
    temperature: 0.5                        # More creative
    output_format: "markdown"
  rag:
    enabled: true                           # For best practices
```

### Conversational Type

**Purpose:** Handle multi-turn dialogue with intent classification, context management, and persona-adapted responses

```yaml
agent_type: conversational
workflow:
  1_classify: "Classify user intent (fast model)"
  2_context: "Build/update conversation context"
  3_fetch: "Fetch relevant data via MCP if needed"
  4_rag: "Retrieve knowledge for response grounding"
  5_generate: "Generate persona-adapted response"
  6_state: "Update conversation state"
  7_output: "Return response to channel adapter"

defaults:
  llm:
    intent_model: "anthropic/claude-3-haiku"     # Fast classification
    response_model: "anthropic/claude-3-5-sonnet" # Quality responses
    temperature: 0.4
    output_format: "text"
  rag:
    enabled: true
    top_k: 3
  state:
    max_turns: 5
    session_ttl_minutes: 30
    checkpoint_backend: "mongodb"
```

**Integration with Conversational AI Model:**

The Conversational AI Model (8th domain) delegates agent logic here:

```
Conversational AI Model                    AI Model
+---------------------------+             +---------------------------+
| • Channel adapters        |             | • Conversational agent    |
| • Session management      |  ──gRPC──>  | • Intent classification   |
| • Persona selection       |             | • Response generation     |
| • Turn coordination       |             | • RAG retrieval           |
+---------------------------+             | • State checkpointing     |
                                          +---------------------------+
```

### Tiered-Vision Type

**Purpose:** Cost-optimized image analysis with two-tier LLM processing

```yaml
agent_type: tiered-vision
workflow:
  1_fetch_thumbnail: "Fetch pre-generated thumbnail via MCP"
  2_screen: "Quick classification with cheap model (Tier 1)"
  3_route: "Conditional routing based on screen result"
  4_fetch_original: "Fetch full image if escalated (Tier 2 only)"
  5_diagnose: "Deep analysis with capable model + RAG (Tier 2 only)"
  6_output: "Publish diagnosis result"

defaults:
  llm:
    screen:                              # Tier 1: Fast, cheap
      model: "anthropic/claude-3-haiku"
      temperature: 0.1
      max_tokens: 200
    diagnose:                            # Tier 2: Capable, expensive
      model: "anthropic/claude-3-5-sonnet"
      temperature: 0.3
      max_tokens: 2000
  rag:
    enabled: true                        # Used in Tier 2 only
    top_k: 5
  routing:
    screen_threshold: 0.7                # Escalate if confidence < 0.7
```

**Key Characteristics:**

| Aspect | Tiered-Vision |
|--------|---------------|
| **Trigger** | Event (single invocation) |
| **State** | Stateless (single request) |
| **LLM Calls** | 2 (screen + diagnose, conditional) |
| **Cost Optimization** | 40% skip Tier 2, 57% cost savings at scale |
| **Output** | Event with diagnosis result |

**Routing Logic:**

```
Screen Result      Confidence    Action
─────────────────────────────────────────────────────
"healthy"          ≥ 0.85        → Output: no_issue (skip Tier 2)
"healthy"          < 0.85        → Escalate to Tier 2 (uncertain)
"obvious_issue"    ≥ 0.75        → Output: Haiku diagnosis (skip Tier 2)
"obvious_issue"    < 0.75        → Escalate to Tier 2
"needs_expert"     any           → Always Tier 2 (Sonnet + RAG)
```

### Agent Types Comparison

| Type | LLM Calls | Pattern | Framework | Use Case |
|------|-----------|---------|-----------|----------|
| **Extractor** | 1 | Linear | LangChain | Parse documents, extract fields |
| **Explorer** | 1 | RAG + iterate | LangGraph | Diagnose issues, analyze patterns |
| **Generator** | 1 | RAG + format | LangGraph | Create reports, translate messages |
| **Conversational** | 2 | Intent → Response | LangGraph | Multi-turn dialogue |
| **Tiered-Vision** | 2 | Screen → Diagnose | LangGraph | Cost-optimized image analysis |

## Agent Configuration Schema

Agent configurations follow the same pattern as `SourceConfig` in Collection Model:

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
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Load at startup + TTL cache              │
│                              ▼                                          │
│  PYDANTIC MODELS (Application Code)                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
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

**YAML Schemas by Agent Type:**

Each agent type has common fields plus type-specific configuration. Below are complete examples for each type.

---

### Extractor YAML Schema

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

### Explorer YAML Schema

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

### Generator YAML Schema

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

### Conversational YAML Schema

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

### Tiered-Vision YAML Schema

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

### Schema Comparison Summary

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

## Agent Type Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Number of types** | 5 (Extractor, Explorer, Generator, Conversational, Tiered-Vision) | Covers fundamental AI patterns including dialogue and cost-optimized image analysis |
| **Type location** | In code | Workflow logic requires conditionals, loops, error handling |
| **Instance location** | YAML → MongoDB → Pydantic | Git source, MongoDB runtime, type-safe loading |
| **Model selection** | Explicit per agent | No indirection; agent config shows exact model used |
| **Inheritance** | Flat (Type → Instance only) | Avoids complexity; use parameters for variations |
| **Prompts** | Separate .md files | Better diffs, easier review, can be long |

## LangGraph Workflow Orchestration

The AI Model uses **LangGraph** for complex multi-step workflows that require:

- **Parallel execution** — Run multiple analyzers concurrently (e.g., disease + weather + technique)
- **Saga pattern** — Coordinate parallel branches with compensation on failure
- **Checkpointing** — Save state to MongoDB for long-running or resumable workflows
- **Conditional routing** — Triage results determine which analyzers to invoke

**Primary use case:** When triage confidence is low, the saga pattern orchestrates parallel analyzers and aggregates their findings into a unified diagnosis.

```
Triage (Haiku)
     │
     ├── confidence ≥ 0.8 → Single analyzer
     │
     └── confidence < 0.8 → Saga: parallel analyzers
                                  ├── Disease Analyzer
                                  ├── Weather Analyzer
                                  └── Technique Analyzer
                                           │
                                           ▼
                                    Aggregator (combine findings)
```

> **Implementation details:** See `ai-model-developer-guide/1-sdk-framework.md` § *LangGraph Saga Pattern* for workflow code, checkpointing configuration, and error compensation strategies.

## Triggering

**Key Decision:** Triggering is the responsibility of domain models, NOT the AI Model.

Domain models configure triggers that specify when to invoke AI workflows:

```yaml
# In Knowledge Model configuration
triggers:
  - name: poor-quality-analysis
    type: event
    event: "collection.poor_quality_detected"
    workflow: "diagnose-quality-issue"

  - name: daily-weather-analysis
    type: schedule
    cron: "0 6 * * *"
    workflow: "analyze-weather-impact"
    params: { region: "all" }

  - name: weekly-trend-analysis
    type: schedule
    cron: "0 0 * * 0"
    workflow: "analyze-trends"
    params: { scope: "all_farmers" }
```

**Trigger Schema:**

```yaml
trigger:
  name: string              # Unique identifier
  type: event | schedule    # Trigger mechanism

  # If type: event
  event: string             # Event topic to subscribe to

  # If type: schedule
  cron: string              # Cron expression

  workflow: string          # AI Model workflow to invoke
  params: object            # Optional parameters to pass
  enabled: boolean          # Can disable without removing
```

**Infrastructure:**

| Trigger Type | DAPR Component | Agnostic Of |
|--------------|----------------|-------------|
| Event | DAPR Pub/Sub | Message broker (Azure SB, Kafka, Redis...) |
| Schedule | DAPR Jobs | Scheduler backend |

## LLM Gateway

[OpenRouter.ai](https://openrouter.ai) serves as the unified LLM gateway:

| Benefit | Description |
|---------|-------------|
| **Multi-Provider** | Access OpenAI, Anthropic, Google, Meta, Mistral through single API |
| **Model Flexibility** | Switch models per agent without code changes |
| **Fallback** | Automatic failover if one provider is down |
| **Unified Billing** | Single invoice, per-model cost breakdown |
| **No Vendor Lock-in** | Can switch providers without changing integration |

**Model Configuration Strategy:**

Models are configured **explicitly per agent** (not via centralized task-type routing). This provides:

- **Clarity:** Agent config shows exactly what model it uses
- **Flexibility:** Each agent can use any model without override patterns
- **Self-contained:** No need to check gateway config to understand agent behavior

**Recommended Models by Use Case:**

| Use Case | Recommended Model | Rationale |
|----------|-------------------|-----------|
| **Extraction** | Claude Haiku / GPT-4o-mini | Fast, cheap, structured output |
| **Diagnosis** | Claude Sonnet / GPT-4o | Complex reasoning, accuracy critical |
| **Generation** | Claude Sonnet | Translation, simplification, cultural context |
| **Market Analysis** | GPT-4o | Data synthesis, pattern recognition |
| **Intent Classification** | Claude Haiku | Fast, low-latency classification |

**Gateway Configuration:**

The gateway handles **resilience and operational concerns**, not model selection.

Configuration follows the **established project pattern**: Pydantic Settings loaded from environment variables.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LLM GATEWAY CONFIGURATION FLOW                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SOURCE OF TRUTH: Environment Variables                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  # .env (local) or K8s ConfigMap/Secrets (deployed)            │   │
│  │  AI_MODEL_OPENROUTER_API_KEY=sk-or-...                          │   │
│  │  AI_MODEL_OPENROUTER_BASE_URL=https://openrouter.ai/api/v1      │   │
│  │  AI_MODEL_LLM_FALLBACK_MODELS=claude-3-5-sonnet,gpt-4o,gemini   │   │
│  │  AI_MODEL_LLM_RETRY_MAX_ATTEMPTS=3                              │   │
│  │  AI_MODEL_LLM_RATE_LIMIT_RPM=100                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Loaded at startup                        │
│                              ▼                                          │
│  PYDANTIC SETTINGS: services/ai-model/src/ai_model/config.py           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Validated, typed, with defaults                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Dependency injection                     │
│                              ▼                                          │
│  LLM GATEWAY CLASS: Retry, fallback, rate limiting, cost tracking      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Pydantic Settings (config.py):**

```python
# services/ai-model/src/ai_model/config.py
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AI Model service configuration.

    Follows project pattern: env vars with AI_MODEL_ prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="AI_MODEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service identification
    service_name: str = "ai-model"
    service_version: str = "0.1.0"
    environment: str = "development"

    # Server configuration (ADR-011: Two-port pattern)
    host: str = "0.0.0.0"
    port: int = 8000
    grpc_port: int = 50051

    # MongoDB configuration
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "ai_model"

    # ═══════════════════════════════════════════════════════════════════
    # LLM GATEWAY CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════

    # OpenRouter connection
    openrouter_api_key: SecretStr  # Required, no default
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Fallback chain (comma-separated in env var)
    llm_fallback_models: list[str] = [
        "anthropic/claude-3-5-sonnet",
        "openai/gpt-4o",
        "google/gemini-pro",
    ]

    # Retry configuration
    llm_retry_max_attempts: int = 3
    llm_retry_backoff_ms: list[int] = [100, 500, 2000]

    # Rate limiting
    llm_rate_limit_rpm: int = 100      # Requests per minute
    llm_rate_limit_tpm: int = 100000   # Tokens per minute

    # Cost tracking
    llm_cost_tracking_enabled: bool = True
    llm_cost_log_per_call: bool = True
    llm_cost_alert_daily_usd: float = 100.0

    # ═══════════════════════════════════════════════════════════════════
    # PINECONE (RAG)
    # ═══════════════════════════════════════════════════════════════════

    pinecone_api_key: SecretStr  # Required, no default
    pinecone_environment: str = "us-east-1"
    pinecone_index_name: str = "farmer-power-knowledge"

    # ═══════════════════════════════════════════════════════════════════
    # DAPR
    # ═══════════════════════════════════════════════════════════════════

    dapr_host: str = "localhost"
    dapr_http_port: int = 3500
    dapr_pubsub_name: str = "pubsub"

    # ═══════════════════════════════════════════════════════════════════
    # OBSERVABILITY
    # ═══════════════════════════════════════════════════════════════════

    log_level: str = "INFO"
    otel_enabled: bool = True
    otel_exporter_endpoint: str = "http://localhost:4317"


# Global settings instance
settings = Settings()
```

**LLM Gateway Class:**

```python
# services/ai-model/src/ai_model/llm/gateway.py
from ai_model.config import Settings


class LLMGateway:
    """Unified LLM access via OpenRouter with resilience.

    Handles: retry, fallback, rate limiting, cost tracking.
    Does NOT handle: model selection (per-agent config).
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = self._create_client()
        self.rate_limiter = RateLimiter(
            rpm=settings.llm_rate_limit_rpm,
            tpm=settings.llm_rate_limit_tpm,
        )

    async def complete(
        self,
        model: str,  # Explicit model from agent config
        messages: list[dict],
        **kwargs,
    ) -> LLMResponse:
        """Execute LLM completion with resilience."""

        await self.rate_limiter.acquire()

        # Try primary model, then fallback chain
        models_to_try = [model] + self.settings.llm_fallback_models

        for attempt_model in models_to_try:
            try:
                response = await self._call_with_retry(
                    attempt_model, messages, **kwargs
                )
                self._track_cost(response)
                return response
            except ModelUnavailableError:
                continue  # Try next in fallback chain

        raise AllModelsUnavailableError(models_to_try)
```

**Why This Pattern:**

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **No YAML file** | Env vars only | Aligns with project pattern (collection, plantation, etc.) |
| **Pydantic Settings** | Type-safe config | Validated at startup, IDE support, clear defaults |
| **SecretStr for keys** | API key protection | Never logged, K8s secrets integration |
| **Flat structure** | Simple env vars | Easy to override per environment |
| **Global instance** | `settings = Settings()` | Consistent with other services |

**Agent-Level Model Configuration:**

Each agent explicitly declares its model in its configuration:

```yaml
# Example: disease-diagnosis agent
agent:
  id: "disease-diagnosis"
  llm:
    model: "anthropic/claude-3-5-sonnet"   # Explicit, no indirection
    temperature: 0.3
    max_tokens: 2000
```

## Tiered Vision Processing (Cost Optimization)

To optimize vision model costs at scale, the Disease Diagnosis workflow uses a two-tier approach with **two agents**.

> **Implementation details:** See `ai-model-developer-guide/8-performance.md` for image preprocessing, batching strategies, and token efficiency.

### Thumbnail Generation (Collection Model Responsibility)

**Key Decision:** Collection Model generates thumbnails at ingestion time, not AI Model on-demand.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    IMAGE INGESTION FLOW                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  QC Analyzer ──────► Collection Model                                   │
│  (sends image)            │                                             │
│                           │ 1. Store original image                     │
│                           │ 2. Generate thumbnail (256x256, JPEG 60%)   │
│                           │ 3. Store thumbnail                          │
│                           ▼                                             │
│                    Azure Blob Storage                                   │
│                    ┌─────────────────────────────────────────────┐     │
│                    │  /documents/{doc_id}/                       │     │
│                    │  ├── original.jpg    (full resolution)      │     │
│                    │  └── thumbnail.jpg   (256x256)              │     │
│                    └─────────────────────────────────────────────┘     │
│                           │                                             │
│                           │ 4. Store metadata in MongoDB                │
│                           ▼                                             │
│                    ┌─────────────────────────────────────────────┐     │
│                    │  { doc_id, original_url, thumbnail_url,     │     │
│                    │    thumbnail_generated: true }              │     │
│                    └─────────────────────────────────────────────┘     │
│                           │                                             │
│                           │ 5. Publish event                            │
│                           ▼                                             │
│                    Event: collection.document.received                  │
│                    Payload: { doc_id, has_thumbnail: true }             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why Collection Model owns thumbnail generation:**

| Aspect | Rationale |
|--------|-----------|
| **Done once** | Generated at ingestion, reused for all analysis |
| **No wasted bandwidth** | AI Model fetches only what it needs |
| **Separation of concerns** | Collection owns blob storage, AI owns analysis |
| **40% savings** | "Healthy" images never need full image fetch |

### Tiered Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TIERED VISION PROCESSING                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Event: collection.poor_quality_detected                                │
│  Payload: { doc_id, thumbnail_url, original_url }                       │
│                          │                                              │
│                          ▼                                              │
│  TIER 1: vision-screen (Extractor, Haiku)                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Input: Fetch THUMBNAIL only (256x256) + basic metadata         │   │
│  │  Cost: ~$0.001/image                                            │   │
│  │                                                                  │   │
│  │  Classification:                                                 │   │
│  │    • "healthy" (40%)         → Skip, log as no_issue            │   │
│  │    • "obvious_issue" (25%)   → Metadata-based diagnosis (Haiku) │   │
│  │    • "needs_expert" (35%)    → Escalate to Tier 2               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│              ┌───────────┴───────────┬───────────────┐                 │
│              ▼                       ▼               ▼                  │
│         "healthy"            "obvious_issue"   "needs_expert"          │
│              │                       │               │                  │
│              ▼                       ▼               ▼                  │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐      │
│  │  No diagnosis   │   │  Haiku analysis │   │  TIER 2: SONNET │      │
│  │  needed         │   │  metadata-only  │   │  Full analysis  │      │
│  │  conf: 0.9      │   │  conf: 0.7-0.85 │   │  conf: 0.85+    │      │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘      │
│                                                     │                  │
│                                                     ▼                  │
│                         disease-diagnosis (Explorer, Sonnet)           │
│                         ┌─────────────────────────────────────────┐   │
│                         │  Input: Fetch ORIGINAL image            │   │
│                         │         + farmer context (MCP)          │   │
│                         │         + RAG knowledge                 │   │
│                         │  Cost: ~$0.012/image                    │   │
│                         └─────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Agent Types Summary

| Tier | Agent ID | Agent Type | Model | Fetches | Purpose |
|------|----------|------------|-------|---------|---------|
| **1** | `vision-screen` | Extractor | Haiku | Thumbnail only | Fast screening, routing |
| **2** | `disease-diagnosis` | Explorer | Sonnet | Original + context | Deep analysis with RAG |

### Cost Impact at Scale (10,000 images/day)

| Approach | Calculation | Daily Cost | Annual Cost |
|----------|-------------|------------|-------------|
| **All Sonnet** | 10,000 × $0.012 | $120 | ~$43,800 |
| **Tiered** | 10,000 × $0.001 + 3,500 × $0.012 | $52 | ~$19,000 |
| **Savings** | | **57%** | **~$24,800** |

**Additional bandwidth savings:** 40% of images ("healthy") never require full image fetch.

### Tier 1 Screening Agent

```yaml
agent:
  id: "vision-screen"
  type: extractor
  version: "1.0.0"
  description: "Fast screening of quality images using thumbnail"

  input:
    event: "collection.poor_quality_detected"
    schema:
      required: [doc_id, thumbnail_url]
      optional: [original_url, metadata]

  # Fetches thumbnail from Collection MCP (pre-generated by Collection Model)
  mcp_sources:
    - server: collection
      tools: [get_document_thumbnail]

  llm:
    model: "anthropic/claude-3-haiku"
    temperature: 0.1
    max_tokens: 200

  output:
    event: "ai.vision_screen.complete"
    schema:
      classification: enum           # healthy, obvious_issue, needs_expert
      confidence: number
      reason: string
      route_to: string               # null, "haiku-metadata", "disease-diagnosis"
```

**Routing Logic:**

| Screen Result | Confidence | Action |
|---------------|------------|--------|
| `healthy` | ≥ 0.85 | Log as no_issue, no further analysis |
| `healthy` | < 0.85 | Escalate to Tier 2 (uncertain) |
| `obvious_issue` | ≥ 0.75 | Haiku metadata analysis (no vision) |
| `obvious_issue` | < 0.75 | Escalate to Tier 2 |
| `needs_expert` | any | Always Tier 2 (Sonnet + vision) |

## RAG Engine

The RAG (Retrieval-Augmented Generation) engine is internal to the AI Model.

> **Implementation details:** See `ai-model-developer-guide/10-rag-knowledge-management.md` for knowledge domain setup and query optimization.

| Aspect | Decision |
|--------|----------|
| **Vector DB** | Pinecone |
| **Access** | Internal only - domain models cannot query directly |
| **Curation (v1)** | Manual upload via Admin UI by agronomists |
| **Curation (future)** | Separate knowledge curation workflow |

**Knowledge Domains:**

| Domain | Content | Used By |
|--------|---------|---------|
| Plant Diseases | Symptoms, identification, treatments | diagnose-quality-issue |
| Tea Cultivation | Best practices, seasonal guidance | analyze-weather-impact, generate-action-plan |
| Weather Patterns | Regional climate, crop impact | analyze-weather-impact |
| Quality Standards | Grading criteria, buyer expectations | extract-and-validate, analyze-market |
| Regional Context | Local practices, cultural factors | generate-action-plan |

## RAG Document API

RAG documents are managed through a gRPC API exposed by the AI Model service. This enables:
- **Admin UI** for agronomists (non-technical experts) to manage knowledge
- **CLI** for Ops team automation and bulk operations

### RAG Document Pydantic Model

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class RAGDocumentMetadata(BaseModel):
    """Metadata for RAG document."""
    author: str                              # Agronomist who created/updated
    source: str | None = None                # Original source (book, research paper, etc.)
    region: str | None = None                # Geographic relevance (e.g., "Kenya", "Rwanda")
    season: str | None = None                # Seasonal relevance (e.g., "dry_season", "monsoon")
    tags: list[str] = []                     # Searchable tags


class SourceFile(BaseModel):
    """Original uploaded file reference (for PDF/DOCX uploads)."""
    filename: str                            # "blister-blight-guide.pdf"
    file_type: Literal["pdf", "docx", "md", "txt"]
    blob_path: str                           # Azure Blob path to original file
    file_size_bytes: int
    extraction_method: Literal[
        "manual",           # User typed content directly
        "text_extraction",  # PyMuPDF for digital PDFs
        "azure_doc_intel",  # Azure Document Intelligence for scanned/complex PDFs
        "vision_llm"        # Vision LLM for diagrams/tables
    ] | None = None
    extraction_confidence: float | None = None  # 0-1 quality score
    page_count: int | None = None


class RAGDocument(BaseModel):
    """RAG knowledge document for expert knowledge storage."""
    document_id: str                         # Stable ID across versions
    version: int = 1                         # Incrementing version number

    # Content
    title: str
    domain: Literal[
        "plant_diseases",
        "tea_cultivation",
        "weather_patterns",
        "quality_standards",
        "regional_context"
    ]
    content: str                             # Extracted/authored markdown text

    # Source file (if uploaded as PDF/DOCX)
    source_file: SourceFile | None = None    # Original file reference

    # Lifecycle
    status: Literal["draft", "staged", "active", "archived"] = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    metadata: RAGDocumentMetadata

    # Change tracking
    change_summary: str | None = None        # What changed from previous version

    # Embedding reference (populated after vectorization)
    pinecone_namespace: str | None = None    # e.g., "knowledge-v12"
    pinecone_ids: list[str] = []             # Vector IDs in Pinecone
    content_hash: str | None = None          # SHA256 for change detection
```

### PDF Ingestion Pipeline

Agronomists can upload PDFs directly. The system auto-detects the PDF type and uses the appropriate extraction method:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PDF INGESTION PIPELINE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PDF Upload                                                         │
│      │                                                              │
│      ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    PDF TYPE DETECTION                        │   │
│  │  • Check if text layer exists                               │   │
│  │  • Detect scanned images                                    │   │
│  │  • Identify tables/diagrams                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│      │                                                              │
│      ├──► Digital PDF (has text layer)                             │
│      │    └─► PyMuPDF extraction                                   │
│      │        • Fast, cheap, accurate                              │
│      │        • ~100ms per page                                    │
│      │                                                              │
│      ├──► Scanned PDF (image-based)                                │
│      │    └─► Azure Document Intelligence                          │
│      │        • OCR + layout analysis                              │
│      │        • Table extraction                                   │
│      │        • ~2-5s per page                                     │
│      │                                                              │
│      └──► Complex PDF (diagrams, mixed content)                    │
│           └─► Vision LLM (Claude/GPT-4V)                           │
│               • Semantic understanding                             │
│               • Diagram description                                │
│               • ~5-10s per page, higher cost                       │
│                                                                     │
│      ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    OUTPUT                                    │   │
│  │  • Markdown content                                         │   │
│  │  • Original PDF stored in Azure Blob                        │   │
│  │  • Extraction confidence score                              │   │
│  │  • Review flag if confidence < 0.8                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Extraction Methods:**

| Method | Use Case | Speed | Cost | Accuracy |
|--------|----------|-------|------|----------|
| **PyMuPDF** | Digital PDFs with text layer | ~100ms/page | Free | 99%+ |
| **Azure Document Intelligence** | Scanned PDFs, forms, tables | ~2-5s/page | $0.01/page | 95%+ |
| **Vision LLM** | Complex diagrams, mixed content | ~5-10s/page | $0.02-0.05/page | 90%+ |

**Azure Document Intelligence Configuration:**

```python
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential


class PDFExtractor:
    """Extract text from PDFs using appropriate method."""

    def __init__(self, settings: Settings):
        self.doc_intel_client = DocumentIntelligenceClient(
            endpoint=settings.azure_doc_intel_endpoint,
            credential=AzureKeyCredential(settings.azure_doc_intel_key)
        )

    async def extract(self, pdf_bytes: bytes, filename: str) -> ExtractionResult:
        """Extract content from PDF, auto-detecting best method."""
        # 1. Try text extraction first (fast, free)
        text_result = await self._try_text_extraction(pdf_bytes)
        if text_result.confidence > 0.9:
            return text_result

        # 2. Fall back to Azure Document Intelligence
        return await self._extract_with_azure(pdf_bytes, filename)

    async def _try_text_extraction(self, pdf_bytes: bytes) -> ExtractionResult:
        """Try PyMuPDF text extraction for digital PDFs."""
        import pymupdf

        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        pages_text = []
        total_chars = 0

        for page in doc:
            text = page.get_text("markdown")
            pages_text.append(text)
            total_chars += len(text)

        # Low char count per page suggests scanned PDF
        avg_chars_per_page = total_chars / len(doc) if doc else 0
        confidence = min(1.0, avg_chars_per_page / 500)  # Expect ~500+ chars/page

        return ExtractionResult(
            content="\n\n---\n\n".join(pages_text),
            method="text_extraction",
            confidence=confidence,
            page_count=len(doc),
            review_recommended=confidence < 0.8
        )

    async def _extract_with_azure(
        self,
        pdf_bytes: bytes,
        filename: str
    ) -> ExtractionResult:
        """Extract using Azure Document Intelligence."""
        poller = await self.doc_intel_client.begin_analyze_document(
            model_id="prebuilt-layout",  # Best for general documents
            body=pdf_bytes,
            content_type="application/pdf"
        )
        result = await poller.result()

        # Convert to markdown
        markdown_content = self._azure_result_to_markdown(result)

        return ExtractionResult(
            content=markdown_content,
            method="azure_doc_intel",
            confidence=0.95,  # Azure is generally reliable
            page_count=len(result.pages),
            review_recommended=False
        )

    def _azure_result_to_markdown(self, result) -> str:
        """Convert Azure Document Intelligence result to markdown."""
        sections = []

        for paragraph in result.paragraphs or []:
            # Handle headings
            if paragraph.role == "title":
                sections.append(f"# {paragraph.content}")
            elif paragraph.role == "sectionHeading":
                sections.append(f"## {paragraph.content}")
            else:
                sections.append(paragraph.content)

        # Handle tables
        for table in result.tables or []:
            sections.append(self._table_to_markdown(table))

        return "\n\n".join(sections)


class ExtractionResult(BaseModel):
    """Result of PDF extraction."""
    content: str
    method: Literal["text_extraction", "azure_doc_intel", "vision_llm"]
    confidence: float
    page_count: int
    review_recommended: bool
    warnings: list[str] = []
```

### gRPC API (Proto Definition)

```protobuf
// proto/ai_model/v1/rag_document.proto
syntax = "proto3";

package farmer_power.ai_model.v1;

import "google/protobuf/timestamp.proto";

service RAGDocumentService {
  // CRUD Operations
  rpc CreateDocument(CreateDocumentRequest) returns (CreateDocumentResponse);
  rpc GetDocument(GetDocumentRequest) returns (RAGDocument);
  rpc UpdateDocument(UpdateDocumentRequest) returns (RAGDocument);
  rpc DeleteDocument(DeleteDocumentRequest) returns (DeleteDocumentResponse);

  // List & Search
  rpc ListDocuments(ListDocumentsRequest) returns (ListDocumentsResponse);
  rpc SearchDocuments(SearchDocumentsRequest) returns (SearchDocumentsResponse);

  // Lifecycle Management
  rpc StageDocument(StageDocumentRequest) returns (RAGDocument);
  rpc ActivateDocument(ActivateDocumentRequest) returns (RAGDocument);
  rpc ArchiveDocument(ArchiveDocumentRequest) returns (RAGDocument);
  rpc RollbackDocument(RollbackDocumentRequest) returns (RAGDocument);

  // A/B Testing
  rpc StartABTest(StartABTestRequest) returns (ABTestStatus);
  rpc GetABTestStatus(GetABTestStatusRequest) returns (ABTestStatus);
  rpc EndABTest(EndABTestRequest) returns (ABTestResult);
}

message RAGDocument {
  string document_id = 1;
  int32 version = 2;
  string title = 3;
  string domain = 4;
  string content = 5;
  string status = 6;
  RAGDocumentMetadata metadata = 7;
  string change_summary = 8;
  google.protobuf.Timestamp created_at = 9;
  google.protobuf.Timestamp updated_at = 10;
  optional SourceFile source_file = 11;      // If created from PDF/DOCX
}

message RAGDocumentMetadata {
  string author = 1;
  optional string source = 2;
  optional string region = 3;
  optional string season = 4;
  repeated string tags = 5;
}

message SourceFile {
  string filename = 1;
  string file_type = 2;                      // "pdf", "docx", "md", "txt"
  string blob_path = 3;                      // Azure Blob path to original
  int64 file_size_bytes = 4;
  string extraction_method = 5;              // "text_extraction", "azure_doc_intel", "vision_llm"
  float extraction_confidence = 6;           // 0-1 quality score
  int32 page_count = 7;
}

message CreateDocumentRequest {
  string title = 1;
  string domain = 2;
  RAGDocumentMetadata metadata = 3;

  // Content source: provide ONE of these
  oneof content_source {
    string content = 4;                      // Direct markdown content
    bytes pdf_file = 5;                      // PDF binary for extraction
    bytes docx_file = 6;                     // DOCX binary for extraction
  }
}

message CreateDocumentResponse {
  RAGDocument document = 1;
  optional ExtractionResult extraction = 2;  // Present if PDF/DOCX was processed
}

message ExtractionResult {
  string method = 1;                         // "text_extraction", "azure_doc_intel", "vision_llm"
  float confidence = 2;                      // 0-1 quality score
  int32 page_count = 3;
  bool review_recommended = 4;               // True if human review advised
  repeated string warnings = 5;              // Any issues detected
}

message GetDocumentRequest {
  string document_id = 1;
  optional int32 version = 2;            // If omitted, returns latest
}

message UpdateDocumentRequest {
  string document_id = 1;
  string title = 2;
  string content = 3;
  RAGDocumentMetadata metadata = 4;
  string change_summary = 5;             // Required: what changed
}

message DeleteDocumentRequest {
  string document_id = 1;
}

message DeleteDocumentResponse {
  bool success = 1;
}

message ListDocumentsRequest {
  optional string domain = 1;            // Filter by domain
  optional string status = 2;            // Filter by status
  optional string author = 3;            // Filter by author
  int32 page = 4;
  int32 page_size = 5;
}

message ListDocumentsResponse {
  repeated RAGDocument documents = 1;
  int32 total_count = 2;
  int32 page = 3;
  int32 page_size = 4;
}

message SearchDocumentsRequest {
  string query = 1;                      // Full-text search
  optional string domain = 2;
  optional string status = 3;
  int32 limit = 4;
}

message SearchDocumentsResponse {
  repeated RAGDocument documents = 1;
}

message StageDocumentRequest {
  string document_id = 1;
}

message ActivateDocumentRequest {
  string document_id = 1;
}

message ArchiveDocumentRequest {
  string document_id = 1;
}

message RollbackDocumentRequest {
  string document_id = 1;
  int32 to_version = 2;
}

message StartABTestRequest {
  string document_id = 1;
  int32 traffic_percentage = 2;          // % of queries using staged version
  int32 duration_days = 3;
}

message ABTestStatus {
  string test_id = 1;
  string document_id = 2;
  string status = 3;                     // "running", "completed", "cancelled"
  int32 staged_queries = 4;
  int32 active_queries = 5;
  google.protobuf.Timestamp started_at = 6;
  google.protobuf.Timestamp ends_at = 7;
}

message GetABTestStatusRequest {
  string test_id = 1;
}

message EndABTestRequest {
  string test_id = 1;
  bool promote = 2;                      // true = activate staged, false = rollback
}

message ABTestResult {
  string test_id = 1;
  bool promoted = 2;
  string outcome = 3;                    // Summary of results
}
```

### Communication Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RAG DOCUMENT MANAGEMENT FLOW                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ADMIN UI (Web)                     BFF                    AI MODEL     │
│  ┌─────────────────┐           ┌──────────┐           ┌──────────────┐ │
│  │  Agronomist     │  GraphQL  │          │   gRPC    │              │ │
│  │  uploads PDF    │──────────▶│  BFF     │──────────▶│  RAGDocument │ │
│  │                 │           │  Service │           │  Service     │ │
│  │  • PDF file     │           │          │           │              │ │
│  │  • Title        │           │          │           │  • Extract   │ │
│  │  • Domain       │           │          │           │  • Store     │ │
│  │  • Metadata     │           │          │           │  • Vectorize │ │
│  └─────────────────┘           └──────────┘           └──────────────┘ │
│                                                              │          │
│                                         ┌────────────────────┼──────┐   │
│                                         │                    │      │   │
│                                         ▼                    ▼      │   │
│  CLI (Ops)                       ┌──────────────┐    ┌────────────┐ │   │
│  ┌─────────────────┐             │ Azure Doc    │    │  MongoDB   │ │   │
│  │ farmer-cli rag  │             │ Intelligence │    │ (documents)│ │   │
│  │   create --pdf  │────────────▶│  (OCR/PDF)   │    └────────────┘ │   │
│  │   list          │ Direct gRPC └──────────────┘           │       │   │
│  │   stage         │                                        ▼       │   │
│  │   activate      │                                 ┌────────────┐ │   │
│  └─────────────────┘                                 │  Pinecone  │ │   │
│                                                      │  (vectors) │ │   │
│                      ┌──────────────┐                └────────────┘ │   │
│                      │ Azure Blob   │◄──────────────────────────────┘   │
│                      │ (original    │   Store original PDF              │
│                      │  PDFs)       │                                   │
│                      └──────────────┘                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### CLI Commands (for Ops)

```bash
# Create document from PDF (auto-extraction)
farmer-cli rag create --title "Blister Blight Treatment" \
  --domain plant_diseases \
  --pdf ./documents/blister-blight-guide.pdf \
  --author "Dr. Wanjiku" \
  --region Kenya

# Output:
# ✓ Uploaded PDF (2.3 MB, 15 pages)
# ✓ Extracted using azure_doc_intel (confidence: 0.96)
# ✓ Document created: doc-789 (status: draft)
# ℹ Review recommended: Found 3 tables, verify formatting

# Create document from markdown file
farmer-cli rag create --title "Frost Protection" \
  --domain weather_patterns \
  --file frost-protection.md \
  --author "Operations"

# Create document with inline content
farmer-cli rag create --title "Quick Tip: Pruning" \
  --domain tea_cultivation \
  --content "When temperatures drop below 4°C..." \
  --author "Operations"

# List documents with filters
farmer-cli rag list --domain plant_diseases --status active
farmer-cli rag list --author "Dr. Wanjiku"

# Get specific document
farmer-cli rag get --id doc-123
farmer-cli rag get --id doc-123 --version 2

# Update document
farmer-cli rag update --id doc-123 \
  --file updated-guide.md \
  --change-summary "Added new treatment protocol for resistant strains"

# Stage for A/B testing
farmer-cli rag stage --id doc-123

# Start A/B test
farmer-cli rag ab-test start --id doc-123 --traffic 20 --duration 7

# Check A/B test status
farmer-cli rag ab-test status --test-id test-456

# Activate (promote to production)
farmer-cli rag activate --id doc-123

# Rollback to previous version
farmer-cli rag rollback --id doc-123 --to-version 2

# Archive document
farmer-cli rag archive --id doc-123

# Bulk import from directory
farmer-cli rag import --dir ./knowledge-base/ --domain tea_cultivation --author "Import"
```

### Vectorization Process

When a document is staged or activated, the AI Model automatically:

1. **Chunk content** - Split into semantic chunks (by heading or paragraph)
2. **Generate embeddings** - Using configured embedding model
3. **Store in Pinecone** - With namespace based on version
4. **Update document record** - Store `pinecone_namespace` and `pinecone_ids`

```python
async def vectorize_document(document: RAGDocument) -> RAGDocument:
    """Vectorize document content and store in Pinecone."""
    # 1. Chunk content
    chunks = chunk_by_heading(document.content)

    # 2. Generate embeddings
    embeddings = await embedding_client.embed(
        texts=[chunk.text for chunk in chunks],
        model="text-embedding-3-small"
    )

    # 3. Store in Pinecone
    namespace = f"knowledge-v{document.version}"
    vectors = [
        {
            "id": f"{document.document_id}-{i}",
            "values": embedding,
            "metadata": {
                "document_id": document.document_id,
                "domain": document.domain,
                "chunk_index": i,
                "title": document.title,
                "region": document.metadata.region,
                "tags": document.metadata.tags,
            }
        }
        for i, embedding in enumerate(embeddings)
    ]
    await pinecone_client.upsert(vectors, namespace=namespace)

    # 4. Update document record
    document.pinecone_namespace = namespace
    document.pinecone_ids = [v["id"] for v in vectors]
    document.content_hash = hashlib.sha256(document.content.encode()).hexdigest()

    return document
```

## Prompt Management

**Decision:** Prompts are externalized to MongoDB, enabling hot-reload and A/B testing without redeployment.

**Problem:** Storing prompts in source code requires rebuild and redeploy for every prompt change:
- Slow iteration during prompt tuning
- Risky deployments for text-only changes
- Cannot A/B test prompts in production
- Cannot rollback prompts independently of code

**Solution:** Externalized prompt management with the same versioning pattern as RAG knowledge.

> **Implementation details:** See `ai-model-developer-guide/4-prompt-engineering.md` for writing effective prompts and `ai-model-developer-guide/5-testing-tuning.md` for prompt validation with golden samples.

### Prompt Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXTERNALIZED PROMPT MANAGEMENT                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SOURCE OF TRUTH: Git Repository                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  prompts/                                                        │   │
│  │  ├── explorers/disease-diagnosis/                               │   │
│  │  │   ├── system.md                                              │   │
│  │  │   ├── template.md                                            │   │
│  │  │   └── prompt.yaml  (metadata, version, A/B config)           │   │
│  │  └── generators/action-plan/                                    │   │
│  │      └── ...                                                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ CI/CD: farmer-cli prompt publish         │
│                              ▼                                          │
│  RUNTIME STORAGE: MongoDB                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Collection: prompts                                             │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │  {                                                         │  │   │
│  │  │    prompt_id: "disease-diagnosis",                         │  │   │
│  │  │    version: "2.1.0",                                       │  │   │
│  │  │    status: "active",                                       │  │   │
│  │  │    system_prompt: "You are an expert...",                  │  │   │
│  │  │    template: "## Context\n{{document}}...",                │  │   │
│  │  │    metadata: { author, updated_at, changelog }             │  │   │
│  │  │  }                                                         │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Load at startup + TTL cache              │
│                              ▼                                          │
│  AI MODEL RUNTIME                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Prompt Cache (TTL: 5 minutes)                                  │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                      │   │
│  │  │ disease-diag    │  │ action-plan     │                      │   │
│  │  │ v2.1.0 (active) │  │ v1.3.0 (active) │                      │   │
│  │  │ v2.2.0 (staged) │  │                 │  ← A/B test          │   │
│  │  └─────────────────┘  └─────────────────┘                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Prompt Document Schema

```yaml
# MongoDB: prompts collection
prompt_document:
  prompt_id: string              # "disease-diagnosis"
  agent_id: string               # "diagnose-quality-issue"
  version: string                # "2.1.0" (semver)
  status: enum                   # "draft" | "staged" | "active" | "archived"

  content:
    system_prompt: string        # Full system prompt text
    template: string             # Template with {{variables}}
    output_schema: object        # JSON schema for validation
    few_shot_examples: array     # Optional examples

  metadata:
    author: string
    created_at: datetime
    updated_at: datetime
    changelog: string            # What changed in this version
    git_commit: string           # Source commit SHA

  ab_test:
    enabled: boolean
    traffic_percentage: number   # 0-100
    test_id: string              # For metrics grouping

  # Compound index: (prompt_id, status) for fast lookups
  # Compound index: (prompt_id, version) for version queries
```

### Prompt Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PROMPT LIFECYCLE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Git: Edit .md file                                                    │
│          │                                                              │
│          │ PR merged to main                                            │
│          ▼                                                              │
│   CI/CD: farmer-cli prompt publish --status staged                      │
│          │                                                              │
│          │ Published to MongoDB with status=staged                      │
│          ▼                                                              │
│   STAGED ──────────────────────────────────────────────────────────────│
│          │                                                              │
│          ├──► Option A: Direct promote                                  │
│          │    farmer-cli prompt promote --id disease-diagnosis          │
│          │                                                                 │
│          └──► Option B: A/B test first                                  │
│               farmer-cli prompt ab-test start --id disease-diagnosis    │
│               --traffic 20 --duration 7d                                │
│                    │                                                    │
│                    │ Monitor metrics                                    │
│                    ▼                                                    │
│               farmer-cli prompt ab-test analyze                         │
│                    │                                                    │
│                    ├──► Success: farmer-cli prompt promote              │
│                    └──► Failure: farmer-cli prompt rollback             │
│                                                                         │
│   ACTIVE ──────────────────────────────────────────────────────────────│
│          │                                                              │
│          │ Issue detected in production                                 │
│          ▼                                                              │
│   farmer-cli prompt rollback --id disease-diagnosis --to-version 2.0.0  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Runtime Prompt Loading

```yaml
# ai-model/config/prompt-loader.yaml
prompt_loader:
  source: mongodb
  connection:
    uri_secret: MONGODB_URI
    database: ai_model
    collection: prompts

  cache:
    enabled: true
    ttl_seconds: 300          # 5 minutes - balance between freshness and performance
    max_entries: 100

  fallback:
    enabled: true
    source: filesystem        # Fall back to bundled prompts if MongoDB unavailable
    path: /app/prompts/fallback/

  ab_test:
    routing_key: farmer_id    # Consistent routing per farmer
    metrics_enabled: true
```

### Prompt A/B Testing

```yaml
# Example: A/B test configuration in MongoDB
prompt_ab_test:
  test_id: "disease-diagnosis-v2.2-test"
  prompt_id: "disease-diagnosis"
  status: active
  started_at: "2024-06-15T00:00:00Z"

  control:
    version: "2.1.0"
    traffic_percentage: 80

  variant:
    version: "2.2.0"
    traffic_percentage: 20

  metrics:
    - diagnosis_accuracy
    - confidence_calibration
    - agronomist_override_rate

  success_criteria:
    diagnosis_accuracy: ">= 0"     # No regression
    confidence_calibration: ">= 0"
    min_samples: 200

  auto_promote:
    enabled: false                 # Require manual review
```

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **No Redeploy** | Prompt changes take effect within cache TTL (5 min) |
| **Safe Rollback** | Instant rollback to any previous version |
| **A/B Testing** | Test prompt changes on subset of traffic |
| **Audit Trail** | Full history of all prompt versions |
| **Git Integration** | Prompts still version-controlled in Git |

## RAG Knowledge Versioning

To prevent knowledge updates from degrading prompt effectiveness, the RAG system uses versioned namespaces with A/B testing.

### Document Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RAG KNOWLEDGE VERSIONING                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DOCUMENT STATES                                                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │   DRAFT     │───▶│   STAGED    │───▶│   ACTIVE    │                 │
│  │             │    │             │    │             │                 │
│  │ Agronomist  │    │ Embeddings  │    │ Production  │                 │
│  │ edits       │    │ generated,  │    │ queries use │                 │
│  │             │    │ A/B ready   │    │ this version│                 │
│  └─────────────┘    └─────────────┘    └──────┬──────┘                 │
│                                               │                         │
│                                               ▼                         │
│                                        ┌─────────────┐                 │
│                                        │  ARCHIVED   │                 │
│                                        │  (rollback) │                 │
│                                        └─────────────┘                 │
│                                                                         │
│  PINECONE NAMESPACE STRATEGY                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  knowledge-v12 (ACTIVE)  ◀── 90% of production queries          │   │
│  │  knowledge-v13 (STAGED)  ◀── 10% A/B test queries               │   │
│  │  knowledge-v11 (ARCHIVED) ◀── Rollback target if needed         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Document Schema

```yaml
# MongoDB: rag_documents collection
rag_document:
  _id: ObjectId
  document_id: string            # Stable ID across versions
  version: int                   # Incrementing version number

  # Content
  title: string
  domain: string                 # plant_diseases, weather_patterns, etc.
  content: string                # Full document text
  content_hash: string           # SHA256 for change detection

  # Embedding reference
  pinecone_namespace: string     # knowledge-v{version}
  pinecone_ids: string[]         # Vector IDs in Pinecone

  # Lifecycle
  status: enum                   # draft, staged, active, archived
  created_at: datetime
  created_by: string             # Agronomist ID
  activated_at: datetime?
  archived_at: datetime?

  # Change tracking
  change_summary: string?        # What changed from previous version
  previous_version_id: ObjectId?
```

### A/B Testing Configuration

```yaml
# ai-model/config/rag-ab-test.yaml
ab_test:
  enabled: true
  staged_namespace: "knowledge-v13"
  active_namespace: "knowledge-v12"

  traffic_split:
    staged: 10                    # 10% of queries use staged
    active: 90                    # 90% use production

  evaluation:
    duration_days: 7
    metrics:
      - diagnosis_confidence_avg
      - agronomist_correction_rate
      - relevance_score_avg

  promotion_criteria:
    min_queries: 500
    confidence_delta: ">= -0.02"  # Can't drop more than 2%
    correction_rate_delta: "<= 0.05"

  auto_promote: false             # Require manual approval
  auto_rollback: true             # Auto rollback if metrics degrade >10%
```

### Rollback Procedure

| Trigger | Action | Duration |
|---------|--------|----------|
| **Manual** | Admin initiates rollback via UI | Immediate |
| **Auto** | Metrics degrade >10% during A/B | Immediate |
| **Mechanism** | Switch active_namespace pointer | <1 second |
| **Retention** | Keep last 5 versions for rollback | 90 days |

### Version Lifecycle Flow

```
Agronomist Updates Document
         │
         ▼
┌─────────────────┐
│  1. Save Draft  │ → MongoDB (status: draft)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Generate    │ → Pinecone (new namespace: knowledge-v13)
│     Embeddings  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. Stage for   │ → MongoDB (status: staged)
│     A/B Test    │ → 10% traffic routes to v13
└────────┬────────┘
         │
         ▼ (after 7 days + metrics OK)
┌─────────────────┐
│  4. Promote     │ → MongoDB (status: active)
│     to Active   │ → 100% traffic routes to v13
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. Archive     │ → MongoDB (v12 status: archived)
│     Previous    │ → Keep for rollback
└─────────────────┘
```

## Configuration Strategy

**Hybrid approach - Git for technical config, Admin UI for business data:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CONFIGURATION STRATEGY                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  GIT (YAML files) - Infrastructure & Technical Config                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • Agent instance definitions                                    │   │
│  │  • Trigger configurations (event mappings, cron schedules)       │   │
│  │  • LLM routing (model per task type)                             │   │
│  │  • DAPR component configs                                        │   │
│  │  • Prompt templates (separate .md files)                         │   │
│  │                                                                  │   │
│  │  Changed by: Developers, Architects                              │   │
│  │  Process: PR → Review → Merge → Deploy                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ADMIN UI + MongoDB - Business & Operational Config                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • RAG knowledge documents (upload interface)                    │   │
│  │  • Farmer/Factory data (Plantation Model)                        │   │
│  │  • Buyer profiles                                                │   │
│  │                                                                  │   │
│  │  Changed by: Operations, Agronomists, Factory managers          │   │
│  │  Process: Login → Edit → Save → Immediate effect                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Observability

**DAPR provides OpenTelemetry instrumentation out of the box.**

> **Implementation details:** See `ai-model-developer-guide/9-observability.md` for logging conventions, custom metrics, and trace correlation.

| Aspect | Approach |
|--------|----------|
| **Tracing** | DAPR automatic trace context propagation |
| **Backend** | Grafana Cloud (OpenTelemetry compatible, swappable) |
| **Cost Tracking** | Per-call logging (tokens, cost, model, farmer_id) |
| **Metrics** | Latency, error rates, token usage per agent/model |

**Trace propagation across events:**

```
Collection ──▶ DAPR ──▶ AI Model ──▶ MCP calls ──▶ DAPR ──▶ Collection
    │            │          │            │           │          │
 span-1      span-2      span-3      span-4       span-5     span-6
    └──────────────────────┴────────────────────────┴──────────┘
                          same trace_id
```

**Infrastructure Agnosticism:**

| Infrastructure | Abstraction | Current Choice | Can Switch To |
|----------------|-------------|----------------|---------------|
| Message Broker | DAPR Pub/Sub | TBD | Azure SB, Kafka, Redis, RabbitMQ |
| Observability | OpenTelemetry | Grafana Cloud | Azure Monitor, Datadog, Jaeger |
| LLM Provider | OpenRouter | Multi-provider | Any supported model |
| Scheduler | DAPR Jobs | TBD | Any DAPR-supported backend |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **AI as Domain Model** | Yes (6th model) | Centralized intelligence, clean separation |
| **Agent Logic** | All in AI Model | Domain models stay simple, no AI dependencies |
| **Communication** | Event-driven async | Non-blocking, scalable, resilient |
| **Event Broker** | DAPR Pub/Sub | Broker-agnostic |
| **Event Payload** | References (IDs) | Small events, MCP for data fetch |
| **Result Delivery** | In completion event | Stateless AI Model, domain owns data |
| **Triggering** | Domain model responsibility | Business logic stays in domain |
| **Scheduler** | DAPR Jobs | Scheduler-backend agnostic |
| **RAG Access** | Internal only | Domain models don't need to know about RAG |
| **RAG Curation** | Admin UI (manual) | Agronomists manage knowledge |
| **Agent Types** | 5 (Extractor, Explorer, Generator, Conversational, Tiered-Vision) | Covers patterns including dialogue and cost-optimized image analysis |
| **Type Implementation** | In code | Workflow logic is code |
| **Instance Config** | YAML → MongoDB → Pydantic | Git source, MongoDB runtime, type-safe |
| **LLM Model Config** | Explicit per agent | Clarity over indirection; no task_type routing |
| **LLM Gateway Role** | Resilience only | Fallback, retry, cost tracking; not model selection |
| **LLM Gateway Config** | Pydantic Settings | Aligns with project pattern; env vars, no YAML |
| **Thumbnail Generation** | Collection Model at ingestion | Done once, AI fetches only what it needs |
| **Tiered Vision Agents** | Extractor (screen) + Explorer (diagnose) | Fast Haiku screen, Sonnet only when needed |
| **Prompts** | Separate .md files | Better review, can be long |
| **Observability** | DAPR OpenTelemetry | Backend-agnostic |

## Testing Strategy

> **Implementation details:** See `ai-model-developer-guide/5-testing-tuning.md` for golden sample creation, LLM mocking, and test fixtures.

| Test Type | Focus |
|-----------|-------|
| **Agent Type Workflows** | Step execution, error handling, retries |
| **Extraction Accuracy** | Golden samples → expected extractions |
| **Diagnosis Quality** | Expert-validated cases |
| **RAG Relevance** | Query → useful context retrieval |
| **Event Contracts** | Input/output schema compliance |
| **MCP Integration** | Correct data fetching |
| **LLM Gateway** | Routing, fallback, cost tracking |
| **End-to-End** | Full event flow through system |

## Developer Guide

> **See:** `ai-model-developer-guide/` directory for comprehensive developer guidelines including:
> - LangChain vs LangGraph usage patterns
> - Project structure and naming conventions
> - Step-by-step agent creation guide
> - Prompt engineering standards
> - Testing strategies (golden samples, mocking)
> - Error handling patterns
> - Security guidelines (prompt injection, PII)
> - Performance optimization (caching, batching, token efficiency)
> - Observability standards (logging, tracing, metrics)

---
