# Agent Types

Five agent types are implemented in code, each with a specific workflow pattern.

> **Implementation details:** See `ai-model-developer-guide/3-agent-development.md` for creating new agents and `ai-model-developer-guide/1-sdk-framework.md` for LangChain vs LangGraph usage patterns.

---

## Critical Principle: Configuration-Driven Agents (NO CODE Required)

> **⚠️ ARCHITECTURAL DECISION: Agent types are generic, reusable patterns. Specific analyses are created ENTIRELY through configuration.**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION-DRIVEN AGENTS                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  IMPLEMENTED ONCE IN CODE (5 types):                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • Extractor   - Generic extraction workflow                    │   │
│  │  • Explorer    - Generic analysis workflow                      │   │
│  │  • Generator   - Generic content generation workflow            │   │
│  │  • Conversational - Generic dialogue workflow                   │   │
│  │  • Tiered-Vision - Generic two-tier image analysis workflow     │   │
│  │                                                                  │   │
│  │  ⚠️ NO NEW CODE is written for these types                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Instances created via                    │
│                              ▼                                          │
│  CONFIGURATION ONLY (YAML + MongoDB):                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  config/agents/disease-diagnosis.yaml  ─► Explorer instance     │   │
│  │  config/agents/weather-analyzer.yaml   ─► Explorer instance     │   │
│  │  config/agents/technique-advisor.yaml  ─► Explorer instance     │   │
│  │  config/agents/qc-event-extractor.yaml ─► Extractor instance    │   │
│  │  config/agents/leaf-quality-screen.yaml ─► Tiered-Vision inst.  │   │
│  │  config/agents/farmer-voice-advisor.yaml ─► Conversational inst.│   │
│  │                                                                  │   │
│  │  ⚠️ NO NEW CODE - only YAML configuration + prompts in MongoDB   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  WHAT CONFIGURATION PROVIDES:                                           │
│  • Which agent type to use (type: explorer, extractor, etc.)           │
│  • Input/output event contracts                                         │
│  • MCP data sources to fetch from                                       │
│  • LLM model selection and parameters                                   │
│  • RAG knowledge domains                                                │
│  • Routing thresholds (for tiered-vision)                              │
│  • Session settings (for conversational)                                │
│                                                                         │
│  PROMPTS (stored in MongoDB, NOT in code):                              │
│  • System prompts per agent instance                                    │
│  • Output schema definitions                                            │
│  • Few-shot examples                                                    │
│  • Hot-reloadable without deployment                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### To Add a New Analysis (e.g., "Soil Quality Analyzer")

| Step | Action | Code Required? |
|------|--------|----------------|
| 1 | Create `config/agents/soil-quality-analyzer.yaml` | ❌ No |
| 2 | Set `type: explorer` (reuses existing Explorer workflow) | ❌ No |
| 3 | Configure MCP sources, LLM model, RAG domains | ❌ No |
| 4 | Add prompts to MongoDB via CLI: `fp-prompt-config deploy` | ❌ No |
| 5 | Deploy config via CI/CD: `fp-agent-config deploy` | ❌ No |

**Result:** New "Soil Quality Analyzer" agent is live - zero lines of Python written.

### When IS Code Required?

| Scenario | Code Required? |
|----------|----------------|
| New analysis using existing agent type | ❌ No - configuration only |
| New prompt for existing agent | ❌ No - MongoDB only |
| Changing LLM model or parameters | ❌ No - YAML only |
| Adding new MCP data source | ❌ No - YAML only |
| **New agent TYPE with different workflow** | ✅ Yes - new LangGraph workflow |
| **New MCP server (new domain model)** | ✅ Yes - new gRPC service |

**Rule:** If the workflow pattern exists (extract, analyze, generate, converse, tiered-vision), use configuration. Only write code for fundamentally new workflow patterns.

---

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

## Extractor Type

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

## Explorer Type

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

## Generator Type

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

## Conversational Type

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

## Tiered-Vision Type

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

## Agent Types Comparison

| Type | LLM Calls | Pattern | Framework | Use Case |
|------|-----------|---------|-----------|----------|
| **Extractor** | 1 | Linear | LangChain | Parse documents, extract fields |
| **Explorer** | 1 | RAG + iterate | LangGraph | Diagnose issues, analyze patterns |
| **Generator** | 1 | RAG + format | LangGraph | Create reports, translate messages |
| **Conversational** | 2 | Intent → Response | LangGraph | Multi-turn dialogue |
| **Tiered-Vision** | 2 | Screen → Diagnose | LangGraph | Cost-optimized image analysis |
