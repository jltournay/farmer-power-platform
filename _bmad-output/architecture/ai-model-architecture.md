# AI Model Architecture

## Overview

The AI Model is the **6th Domain Model** - the centralized intelligence layer for the Farmer Power Cloud Platform. Unlike the previous design where AI agents were embedded in each domain model, all AI logic is centralized here.

**Core Responsibility:** Execute AI workflows (extraction, diagnosis, content generation) on behalf of other domain models.

**Does NOT:** Own business data, make business decisions about when to run, or store results persistently.

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
│  │                                                                  │   │
│  │  Agent Instances (YAML config):                                  │   │
│  │  • qc-event-extractor                                            │   │
│  │  • quality-triage (fast cause classification)                    │   │
│  │  • disease-diagnosis                                             │   │
│  │  • weather-impact-analyzer                                       │   │
│  │  • technique-assessment                                          │   │
│  │  • trend-analyzer                                                │   │
│  │  • weekly-action-plan                                            │   │
│  │  • market-analyzer                                               │   │
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
│  │                    MCP CLIENTS                                   │   │
│  │  • Collection MCP (fetch documents)                              │   │
│  │  • Plantation MCP (fetch farmer context)                         │   │
│  │  • Knowledge MCP (fetch analyses)                                │   │
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

Three agent types are implemented in code, each with a specific workflow pattern:

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
    task_type: "extraction"
    temperature: 0.1           # Very deterministic
    output_format: "json"
  rag:
    enabled: false             # Extractors typically don't need RAG
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
    task_type: "diagnosis"
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
    task_type: "generation"
    temperature: 0.5           # More creative
    output_format: "markdown"
  rag:
    enabled: true              # For best practices
```

## Agent Configuration Schema

Agent instances are defined in YAML files in Git:

```yaml
agent:
  # ═══════════════════════════════════════════════════════════════════
  # IDENTITY
  # ═══════════════════════════════════════════════════════════════════
  id: "disease-diagnosis"
  type: explorer                     # Uses explorer workflow
  version: "1.0.0"
  description: "Analyzes quality issues and produces diagnosis"

  # ═══════════════════════════════════════════════════════════════════
  # INPUT / OUTPUT CONTRACT
  # ═══════════════════════════════════════════════════════════════════
  input:
    event: "collection.poor_quality_detected"
    schema:
      required: [doc_id, farmer_id]
      optional: [quality_issues, grade]

  output:
    event: "ai.diagnosis.complete"
    schema:
      fields: [diagnosis, confidence, severity, details, recommendations]

  # ═══════════════════════════════════════════════════════════════════
  # DATA SOURCES (MCP)
  # ═══════════════════════════════════════════════════════════════════
  mcp_sources:
    - server: collection
      tools: [get_document, get_farmer_documents]
    - server: plantation
      tools: [get_farmer, get_farmer_summary]

  # ═══════════════════════════════════════════════════════════════════
  # LLM CONFIGURATION
  # ═══════════════════════════════════════════════════════════════════
  llm:
    task_type: "diagnosis"          # Routes to appropriate model
    model_override: null            # Or specific: "anthropic/claude-3-5-sonnet"
    temperature: 0.3
    max_tokens: 2000

  # ═══════════════════════════════════════════════════════════════════
  # PROMPT CONFIGURATION
  # ═══════════════════════════════════════════════════════════════════
  prompt:
    system_file: "prompts/explorers/disease-diagnosis.system.md"
    template_file: "prompts/explorers/disease-diagnosis.template.md"
    output_format: "json"
    output_schema:
      type: object
      properties:
        diagnosis:
          type: object
          properties:
            condition: { type: string }
            confidence: { type: number, min: 0, max: 1 }
            severity: { enum: [low, moderate, high, critical] }
            details: { type: string }
        recommendations: { type: array, items: { type: string } }

  # ═══════════════════════════════════════════════════════════════════
  # RAG CONFIGURATION
  # ═══════════════════════════════════════════════════════════════════
  rag:
    enabled: true
    query_template: "tea leaf quality issues {{quality_issues}} {{grade}}"
    knowledge_domains: [plant_diseases, tea_cultivation, quality_standards]
    top_k: 5
    min_similarity: 0.7

  # ═══════════════════════════════════════════════════════════════════
  # ERROR HANDLING
  # ═══════════════════════════════════════════════════════════════════
  error_handling:
    retry:
      max_attempts: 3
      backoff_ms: [100, 500, 2000]
    on_failure: "publish_error_event"
    dead_letter_topic: "ai.errors.dead_letter"
```

## Agent Type Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Number of types** | 3 (Extractor, Explorer, Generator) | Covers fundamental AI patterns; add more when needed |
| **Type location** | In code | Workflow logic requires conditionals, loops, error handling |
| **Instance location** | YAML in Git | Declarative, version controlled, PR reviewable |
| **Inheritance** | Flat (Type → Instance only) | Avoids complexity; use parameters for variations |
| **Prompts** | Separate .md files | Better diffs, easier review, can be long |

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
| **Model Flexibility** | Switch models per task without code changes |
| **Cost Optimization** | Route simple tasks to cheaper models, complex to capable ones |
| **Fallback** | Automatic failover if one provider is down |
| **Unified Billing** | Single invoice, per-model cost breakdown |
| **No Vendor Lock-in** | Can switch providers without changing integration |

**Model Routing Strategy:**

| Task Type | Recommended Model | Rationale |
|-----------|-------------------|-----------|
| **Extraction** | Claude Haiku / GPT-4o-mini | Fast, cheap, structured output |
| **Diagnosis** | Claude Sonnet / GPT-4o | Complex reasoning, accuracy critical |
| **Generation** | Claude Sonnet | Translation, simplification, cultural context |
| **Market Analysis** | GPT-4o | Data synthesis, pattern recognition |
| **RAG Queries** | Claude Haiku | Fast retrieval augmentation |

**Configuration:**

```yaml
# ai-model/config/llm-gateway.yaml
openrouter:
  api_key: ${OPENROUTER_API_KEY}
  base_url: https://openrouter.ai/api/v1

  default_models:
    extraction: "anthropic/claude-3-haiku"
    diagnosis: "anthropic/claude-3-5-sonnet"
    generation: "anthropic/claude-3-5-sonnet"
    market_analysis: "openai/gpt-4o"
    rag_query: "anthropic/claude-3-haiku"

  fallback_chain:
    - "anthropic/claude-3-5-sonnet"
    - "openai/gpt-4o"
    - "google/gemini-pro"

  retry:
    max_attempts: 3
    backoff_ms: [100, 500, 2000]
```

## Tiered Vision Processing (Cost Optimization)

To optimize vision model costs at scale, the Disease Diagnosis agent uses a two-tier approach:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TIERED VISION PROCESSING                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INCOMING IMAGE (POOR_QUALITY_DETECTED event)                           │
│                          │                                              │
│                          ▼                                              │
│  TIER 1: QUICK SCREEN (Claude Haiku)                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Input: Low-res thumbnail (256x256) + basic metadata            │   │
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
│                                    ┌─────────────────────────────┐    │
│                                    │  Full-res image + context   │    │
│                                    │  + RAG + farmer history     │    │
│                                    │  Cost: ~$0.012/image        │    │
│                                    └─────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Cost Impact at Scale (10,000 images/day):**

| Approach | Calculation | Daily Cost | Annual Cost |
|----------|-------------|------------|-------------|
| **All Sonnet** | 10,000 × $0.012 | $120 | ~$43,800 |
| **Tiered** | 10,000 × $0.001 + 3,500 × $0.012 | $52 | ~$19,000 |
| **Savings** | | **57%** | **~$24,800** |

**Tier 1 Screening Agent:**

```yaml
agent:
  id: "vision-screen"
  type: extractor

  input:
    event: "collection.poor_quality_detected"

  llm:
    model_override: "anthropic/claude-3-haiku"
    temperature: 0.1

  preprocessing:
    image:
      resize: [256, 256]
      quality: 60                    # JPEG quality

  output:
    schema:
      classification: enum           # healthy, obvious_issue, needs_expert
      confidence: number
      reason: string
      skip_full_analysis: boolean
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

The RAG (Retrieval-Augmented Generation) engine is internal to the AI Model:

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

## Prompt Management

**Decision:** Prompts are externalized to MongoDB, enabling hot-reload and A/B testing without redeployment.

**Problem:** Storing prompts in source code requires rebuild and redeploy for every prompt change:
- Slow iteration during prompt tuning
- Risky deployments for text-only changes
- Cannot A/B test prompts in production
- Cannot rollback prompts independently of code

**Solution:** Externalized prompt management with the same versioning pattern as RAG knowledge.

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
│          │                                                              │
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

**DAPR provides OpenTelemetry instrumentation out of the box:**

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
| **Agent Types** | 3 (Extractor, Explorer, Generator) | Covers patterns, extensible when needed |
| **Type Implementation** | In code | Workflow logic is code |
| **Instance Config** | YAML in Git | Declarative, version controlled |
| **Prompts** | Separate .md files | Better review, can be long |
| **Observability** | DAPR OpenTelemetry | Backend-agnostic |

## Testing Strategy

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

> **See:** `ai-model-developer-guide.md` for comprehensive developer guidelines including:
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
