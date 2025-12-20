---
stepsCompleted: [1]
inputDocuments: ['_bmad-output/analysis/product-brief-farmer-power-platform-2025-12-16.md']
workflowType: 'architecture'
lastStep: 1
project_name: 'farmer-power-platform'
user_name: 'Jeanlouistournay'
date: '2025-12-16'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

---

## Collection Model Architecture

### Overview

The Collection Model is the **data gateway** for the Farmer Power Cloud Platform. It receives data from external sources (QC Analyzers, Weather APIs, etc.), processes it through an intelligent ingestion pipeline, and provides retrieval mechanisms for downstream consumers.

**Core Responsibility:** Collect, validate, transform, link, store, and serve documents.

**Does NOT:** Generate action plans, make business decisions, or verify farmer existence.

### Architecture Diagram

```
External Sources ──▶ COLLECTION MODEL
                         │
                    ┌────┴────┐
                    │ Ingest  │
                    │ Pipeline│
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │Schema  │ │  LLM   │ │ Store  │
         │Validate│─▶│Extract │─▶│Document│
         │        │ │+Validate│ │        │
         └────────┘ └────────┘ └────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
               ┌────────┐     ┌────────┐     ┌────────┐
               │Query   │     │Search  │     │  MCP   │
               │  API   │     │  API   │     │ Server │
               └────────┘     └────────┘     └────────┘
```

### Configured Sources

Each data source is configured with its own ingestion rules:

```yaml
source: qc-analyzer
  endpoint: /api/v1/ingest/qc-analyzer
  events:
    - END_BAG
    - POOR_QUALITY_DETECTED
  validation:
    schema: qc-analyzer-event.json
  transformation:
    agent: qc-extraction-agent
    extract_fields:
      - farmer_id
      - bag_id
      - factory_id
      - grade
      - leaf_distribution
      - quality_issues
      - timestamp
    link_field: farmer_id
  storage:
    blob_container: quality-events
    mongo_collection: quality_events_index
```

### Ingestion Pipeline

#### Step 1: Schema Validation
- Fast, deterministic JSON schema validation
- Rejects malformed payloads immediately
- Returns structured error responses

#### Step 2: LLM Agent Extraction + Validation
The LLM Agent performs dual-purpose processing:

**Extraction:**
- Locates and extracts required fields from payload
- Handles format variations without code changes
- Adapts to schema drift in source systems

**Semantic Validation:**
- Cross-field consistency checks (e.g., grade vs. quality_score alignment)
- Reasonableness checks (e.g., bag weight within expected range)
- Domain rule validation (e.g., valid grade values)

**Output:**
```python
ProcessingResult(
    extracted_fields: dict,        # Normalized field values
    validation_warnings: list,     # Semantic issues found (non-blocking)
    validation_passed: bool,       # Overall assessment
    confidence: float              # LLM confidence score
)
```

#### Step 3: Farmer Linkage
- Extracts `farmer_id` from processed data
- Stores reference directly (no Plantation Model verification)
- Missing farmer ID stored as warning, not rejection

#### Step 4: Document Storage
- **Raw payload** → Azure Blob Storage (immutable)
- **Index metadata** → MongoDB (queryable)
- **Validation warnings** → Stored with document metadata

### Trust Model

| Aspect                  | Decision            | Rationale                                         |
|-------------------------|---------------------|---------------------------------------------------|
| **Source Trust**        | Trust provided IDs  | Fast ingestion, no cross-model dependency         |
| **Farmer Verification** | None on ingest      | Plantation Model lookup is downstream concern     |
| **Validation Failures** | Store with warnings | Best-effort semantic checking, not hard rejection |
| **Data Integrity**      | Source responsible  | Collection Model is intake, not police            |

### Retrieval APIs

#### Query API
```
GET /api/v1/documents/{document_id}
GET /api/v1/documents?farmer_id={id}&date_range={range}
```

#### Search API
```
POST /api/v1/documents/search
{
  "query": "quality issues moisture",
  "filters": {
    "factory_id": "F001",
    "grade_category": "low_quality",       // Semantic filter (recommended)
    // OR: "grade": ["C", "D"]             // Labels from factory's Grading Model
  },
  "limit": 50
}
```

#### MCP Server Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get_farmer_documents` | Retrieve all documents for a farmer | `farmer_id`, `date_range?`, `source_type?` |
| `get_quality_events` | Get quality grading events | `farmer_id`, `factory_id?`, `grade_filter?` |
| `search_documents` | Semantic or criteria-based search | `query`, `filters`, `limit` |
| `get_document_by_id` | Retrieve specific document | `document_id` |

### Testing Strategy

| Test Type | Scope | Examples |
|-----------|-------|----------|
| **Schema Validation** | Unit | Valid/invalid JSON against schemas |
| **Extraction Accuracy** | Golden samples | Known payloads → expected extractions |
| **Semantic Validation** | Edge cases | Inconsistent grades, unreasonable weights |
| **API Contracts** | Integration | Request/response schema compliance |
| **MCP Tools** | Functional | Tool selection, response interpretation |

### Data Flow Example

```
QC Analyzer sends END_BAG event:
{
  "event_type": "END_BAG",
  "bag_id": "BAG-2025-001234",
  "qr_data": { "farmer_national_id": "12345678", ... },
  "grading_result": { "grade": "B", "score": 78, ... }
}

Collection Model processes:
1. Schema validation ✓
2. LLM extracts: farmer_id="WM-4521", grade="B", score=78
3. LLM validates: grade/score consistent ✓
4. Store: Blob (raw) + Mongo (index with farmer_ref)
5. Available via Query API, Search API, MCP

Downstream consumer (Action Plan Model):
- Calls MCP: get_farmer_documents("WM-4521", last_7_days)
- Receives quality history
- Generates personalized action plan
```

---

## Knowledge Model Architecture

### Overview

The Knowledge Model is an **active analysis engine** that diagnoses situations based on collected data. It does NOT prescribe solutions - that's the Action Plan Model's responsibility.

**Core Responsibility:** DIAGNOSE situations (what's wrong? what's happening?)

**Does NOT:** Prescribe solutions, generate action plans, or tell farmers what to do.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE MODEL                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    EXPLORER AGENT                                │   │
│  │  • Maintains tracking of what needs analysis                     │   │
│  │  • Receives events and scheduled triggers                        │   │
│  │  • Routes to Triage (events) or directly to Analyzers (scheduled)│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│              ┌───────────────┴───────────────┐                          │
│              ▼                               ▼                          │
│  ┌───────────────────────┐       ┌───────────────────────┐             │
│  │  EVENT PATH           │       │  SCHEDULED PATH       │             │
│  │  (POOR_QUALITY_       │       │  (Daily/Weekly)       │             │
│  │   DETECTED)           │       │                       │             │
│  └───────────┬───────────┘       │  Direct to Analyzer:  │             │
│              │                   │  • Weather (daily)    │             │
│              ▼                   │  • Trend (weekly)     │             │
│  ┌───────────────────────┐       └───────────┬───────────┘             │
│  │    TRIAGE AGENT       │                   │                          │
│  │    (Haiku - fast)     │                   │                          │
│  │                       │                   │                          │
│  │  Examines:            │                   │                          │
│  │  • quality_issues[]   │                   │                          │
│  │  • moisture readings  │                   │                          │
│  │  • image indicators   │                   │                          │
│  │  • farmer history     │                   │                          │
│  │  • weather context    │                   │                          │
│  │                       │                   │                          │
│  │  Output:              │                   │                          │
│  │  { route_to: [...],   │                   │                          │
│  │    also_check: [...], │                   │                          │
│  │    confidence: 0.82 } │                   │                          │
│  └───────────┬───────────┘                   │                          │
│              │                               │                          │
│              ▼                               │                          │
│  ┌───────────────────────────────────────────┴──────────────────────┐  │
│  │                   SPECIALIZED ANALYZERS                           │  │
│  │                                                                   │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │  │
│  │  │  Disease    │ │  Weather    │ │  Technique  │ │   Trend     │ │  │
│  │  │  Analyzer   │ │  Analyzer   │ │  Analyzer   │ │  Analyzer   │ │  │
│  │  │             │ │             │ │             │ │             │ │  │
│  │  │ Vision+RAG  │ │ RAG+Weather │ │ RAG+History │ │ Statistical │ │  │
│  │  │ Sonnet      │ │ Sonnet      │ │ Haiku       │ │ Haiku       │ │  │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ │  │
│  └─────────┼───────────────┼───────────────┼───────────────┼────────┘  │
│            │               │               │               │            │
│            │    ┌──────────┴───────────────┴───────────────┘            │
│            │    │                                                       │
│            │    │        VECTOR DB (Pinecone)                           │
│            │    │        ┌─────────────────────────────────┐            │
│            │    │        │ Knowledge Domains:              │            │
│            │    │        │ • plant_diseases                │            │
│            │    │        │ • weather_patterns              │            │
│            │    │        │ • harvesting_techniques         │            │
│            │    │        │ • soil_nutrition                │            │
│            │    │        │ • regional_practices            │            │
│            │    │        └─────────────────────────────────┘            │
│            │    │                                                       │
│            └────┴──────────────────┬────────────────────────────────────│
│                                    ▼                                    │
│              ┌─────────────────────────────────────┐                    │
│              │         ANALYSIS DB (MongoDB)       │                    │
│              │  All diagnoses stored with:         │                    │
│              │  • type, confidence, severity       │                    │
│              │  • triage_reasoning (if applicable) │                    │
│              │  • source_documents, farmer_id      │                    │
│              └───────────────┬─────────────────────┘                    │
│                              │                                          │
│           ┌──────────────────┼──────────────────┐                       │
│           ▼                  ▼                  ▼                       │
│     ┌──────────┐      ┌──────────┐      ┌──────────┐                   │
│     │Query API │      │MCP Server│      │  Events  │                   │
│     └──────────┘      └──────────┘      └──────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Three-Tier Agent Pattern

The Knowledge Model uses a **Hybrid Triage** architecture to intelligently route quality issues to the appropriate specialized analyzer(s).

#### Tier 1: Explorer Agent
- **Responsibility:** Receive events and scheduled triggers, maintain analysis tracking
- **Event path:** Routes `POOR_QUALITY_DETECTED` to Triage Agent
- **Scheduled path:** Routes directly to Weather (daily) or Trend (weekly) Analyzers

#### Tier 2: Triage Agent (Event Path Only)
- **Responsibility:** Classify probable cause of quality issues before deep analysis
- **Model:** Claude Haiku (fast, cheap ~$0.001/call)
- **Input:** Quality event data, farmer history, weather context
- **Output:** Routing decision with confidence score

```yaml
# Triage Agent Configuration
agent:
  id: "quality-triage"
  type: extractor                    # Fast classification

  input:
    event: "collection.poor_quality_detected"

  llm:
    task_type: "extraction"
    model_override: "anthropic/claude-3-haiku"
    temperature: 0.1

  mcp_sources:
    - server: collection
      tools: [get_document]
    - server: plantation
      tools: [get_farmer_summary]

  output:
    schema:
      route_to: string[]              # Primary analyzer(s)
      also_check: string[]            # Secondary if confidence < 0.7
      confidence: number
      reasoning: string
```

**Triage Classification Categories:**

| Category | Indicators | Routes To |
|----------|------------|-----------|
| `disease` | Visual symptoms (spots, discoloration, lesions) | Disease Analyzer |
| `weather` | Moisture/timing patterns, recent weather events | Weather Analyzer |
| `technique` | Leaf characteristics, plucking issues | Technique Analyzer |
| `handling` | Post-harvest indicators, contamination | Technique Analyzer |
| `soil` | Consistent patterns across deliveries | Trend Analyzer |

**Routing Logic:**
- If `confidence >= 0.7`: Route to `route_to` analyzer(s) only
- If `confidence < 0.7`: Route to `route_to` AND `also_check` analyzers (parallel)
- Multiple diagnoses stored; Action Plan uses highest confidence

### LangGraph Saga Pattern (Parallel Analyzer Orchestration)

When multiple analyzers run in parallel (confidence < 0.7), the system uses a **LangGraph Saga** to orchestrate, wait, and aggregate results.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH QUALITY ANALYSIS WORKFLOW                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   START (event: collection.poor_quality_detected)                         │
│     │                                                                     │
│     ▼                                                                     │
│  ┌──────────────────┐                                                     │
│  │   FETCH CONTEXT  │ ─── MCP calls: document, farmer, region, weather    │
│  └────────┬─────────┘                                                     │
│           │                                                               │
│           ▼                                                               │
│  ┌──────────────────┐                                                     │
│  │     TRIAGE       │ ─── Classify probable cause (Haiku, fast)           │
│  │                  │     Output: route_to[], also_check[], confidence    │
│  └────────┬─────────┘                                                     │
│           │                                                               │
│           ▼                                                               │
│  ┌──────────────────┐     confidence >= 0.7?                              │
│  │    DECISION      │ ─────────────────────────────┐                      │
│  └────────┬─────────┘                              │                      │
│           │ NO (< 0.7)                             │ YES                  │
│           ▼                                        ▼                      │
│  ┌────────────────────────────────┐    ┌──────────────────────┐          │
│  │   PARALLEL ANALYZERS           │    │   SINGLE ANALYZER    │          │
│  │   (LangGraph fan-out)          │    │   (route_to only)    │          │
│  │                                │    └───────────┬──────────┘          │
│  │  ┌─────────┐ ┌─────────┐ ┌───────────┐         │                      │
│  │  │ Disease │ │ Weather │ │ Technique │         │                      │
│  │  │ Branch  │ │ Branch  │ │  Branch   │         │                      │
│  │  │         │ │         │ │           │         │                      │
│  │  │ Sonnet  │ │ Sonnet  │ │  Haiku    │         │                      │
│  │  │ +Vision │ │ +RAG    │ │  +RAG     │         │                      │
│  │  └────┬────┘ └────┬────┘ └─────┬─────┘         │                      │
│  │       │           │            │               │                      │
│  │       └───────────┴────────────┘               │                      │
│  │                   │                            │                      │
│  └───────────────────┼────────────────────────────┘                      │
│                      │                                                    │
│                      ▼                                                    │
│  ┌──────────────────────────────────────┐                                │
│  │           AGGREGATE                   │                                │
│  │   (LangGraph join node)               │                                │
│  │                                       │                                │
│  │   • Wait for all branches (timeout)   │                                │
│  │   • Select primary (highest conf)     │                                │
│  │   • Include secondary (conf >= 0.5)   │                                │
│  │   • Handle failures gracefully        │                                │
│  └───────────────────┬──────────────────┘                                │
│                      │                                                    │
│                      ▼                                                    │
│  ┌──────────────────────────────────────┐                                │
│  │           OUTPUT                      │                                │
│  │   Emit: ai.diagnosis.complete         │                                │
│  │   {                                   │                                │
│  │     primary_diagnosis: {...},         │                                │
│  │     secondary_diagnoses: [...],       │                                │
│  │     combined_confidence: 0.82,        │                                │
│  │     analyzers_completed: [...]        │                                │
│  │   }                                   │                                │
│  └──────────────────────────────────────┘                                │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

**LangGraph Workflow Configuration:**

```yaml
# ai-model/workflows/quality-analysis.yaml
workflow:
  id: "quality-analysis-saga"
  type: langgraph

  # ═══════════════════════════════════════════════════════════════════════
  # CHECKPOINTING (Crash Recovery)
  # ═══════════════════════════════════════════════════════════════════════
  checkpointer:
    type: mongodb                    # Survives crashes
    collection: workflow_checkpoints
    ttl_hours: 24

  # ═══════════════════════════════════════════════════════════════════════
  # NODES
  # ═══════════════════════════════════════════════════════════════════════
  nodes:
    fetch_context:
      type: mcp_fetch
      sources:
        - server: collection
          tools: [get_document, get_image_base64]
        - server: plantation
          tools: [get_farmer, get_region, get_region_weather]

    triage:
      type: llm
      model: anthropic/claude-3-haiku
      temperature: 0.1
      output_schema: triage_result

    decision:
      type: conditional
      condition: "state.triage.confidence >= 0.7"
      true_branch: single_analyzer
      false_branch: parallel_analyzers

    parallel_analyzers:
      type: fan_out
      branches:
        disease:
          agent: disease-diagnosis
          enabled_if: "'disease' in state.triage.route_to + state.triage.also_check"
        weather:
          agent: weather-impact-analyzer
          enabled_if: "'weather' in state.triage.route_to + state.triage.also_check"
        technique:
          agent: technique-assessment
          enabled_if: "'technique' in state.triage.route_to + state.triage.also_check"
      timeout_ms: 30000
      on_branch_timeout: proceed_without
      on_branch_error: proceed_without
      min_successful: 1

    single_analyzer:
      type: dynamic_agent
      agent_selector: "state.triage.route_to[0]"

    aggregate:
      type: aggregator
      strategy: confidence_weighted

  # ═══════════════════════════════════════════════════════════════════════
  # EDGES
  # ═══════════════════════════════════════════════════════════════════════
  edges:
    - from: START
      to: fetch_context
    - from: fetch_context
      to: triage
    - from: triage
      to: decision
    - from: decision
      to: [single_analyzer, parallel_analyzers]  # Conditional
    - from: single_analyzer
      to: aggregate
    - from: parallel_analyzers
      to: aggregate
    - from: aggregate
      to: END
```

**Aggregation Rules:**

```yaml
# ai-model/config/aggregation-rules.yaml
aggregation:
  # ═══════════════════════════════════════════════════════════════════════
  # PRIMARY DIAGNOSIS SELECTION
  # ═══════════════════════════════════════════════════════════════════════
  primary:
    strategy: highest_confidence
    min_confidence: 0.5              # Below this → "inconclusive"
    tie_breaker: severity            # If equal confidence, pick higher severity

  # ═══════════════════════════════════════════════════════════════════════
  # SECONDARY DIAGNOSES
  # ═══════════════════════════════════════════════════════════════════════
  secondary:
    include_if:
      confidence_gte: 0.5
      not_primary: true              # Don't duplicate primary
    max_count: 2                     # Limit secondary diagnoses

  # ═══════════════════════════════════════════════════════════════════════
  # TIMEOUT & FAILURE HANDLING
  # ═══════════════════════════════════════════════════════════════════════
  timeout:
    per_branch_ms: 30000             # 30 seconds per analyzer
    total_workflow_ms: 60000         # 60 seconds total

  failure_handling:
    on_branch_timeout: proceed_without
    on_branch_error: proceed_without
    min_successful_branches: 1       # Need at least 1 result
    on_all_failed: emit_inconclusive # Special "needs_manual_review" status

  # ═══════════════════════════════════════════════════════════════════════
  # OUTPUT SCHEMA
  # ═══════════════════════════════════════════════════════════════════════
  output:
    primary_diagnosis:
      type: object
      fields: [condition, sub_type, confidence, severity, details, recommendations]
    secondary_diagnoses:
      type: array
      items: diagnosis
    combined_confidence:
      calculation: weighted_average   # Weight by individual confidence
    metadata:
      analyzers_invoked: string[]
      analyzers_completed: string[]
      analyzers_failed: string[]
      triage_reasoning: string
      workflow_duration_ms: number
```

**Crash Recovery:**

LangGraph checkpointing ensures workflow survives AI Model crashes:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CRASH RECOVERY FLOW                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Normal Flow:                                                            │
│  Event → Fetch → Triage → Parallel → Aggregate → Output                 │
│                              │                                           │
│                          CHECKPOINT                                      │
│                          (MongoDB)                                       │
│                                                                          │
│  Crash during parallel analyzers:                                        │
│  1. AI Model restarts                                                    │
│  2. Loads checkpoint from MongoDB                                        │
│  3. Resumes from last completed node                                     │
│  4. Re-runs only failed/incomplete branches                              │
│  5. Continues to Aggregate → Output                                      │
│                                                                          │
│  Result: No duplicate LLM calls, no lost work                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Tier 3: Specialized Analyzer Agents

| Analyzer | Trigger | Model | RAG Domains | Purpose |
|----------|---------|-------|-------------|---------|
| Disease Detection | Triage routes | Sonnet (Vision) | plant_diseases, regional_patterns | Identify plant diseases from quality issues + images |
| Weather Impact | Triage routes OR Daily scheduled | Sonnet | weather_patterns, tea_cultivation | Assess weather effects on crop quality |
| Technique Assessment | Triage routes | Haiku | harvesting_techniques, regional_practices | Identify harvesting/handling issues |
| Quality Trend | Weekly scheduled | Haiku | None (statistical) | Analyze patterns in farmer's history |

### Weather Lag Correlation

**Key Insight:** Weather affects tea quality with a delay of 3-7 days. Heavy rain on Monday impacts quality in Thursday-Sunday deliveries.

The Weather Analyzer accounts for this lag when correlating weather events to quality issues:

```yaml
# Weather Analyzer Configuration
agent:
  id: "weather-impact-analyzer"
  type: explorer

  weather_correlation:
    # ═══════════════════════════════════════════════════════════════════
    # WEATHER LAG SETTINGS
    # ═══════════════════════════════════════════════════════════════════
    lookback_days: 7                    # Analyze weather from past 7 days
    peak_impact_days: [3, 4, 5]         # Highest correlation at days 3-5

    # Weight weather events by recency
    day_weights:
      day_1: 0.3                        # Very recent - minimal impact yet
      day_2: 0.5
      day_3: 0.9                        # Peak impact window
      day_4: 1.0                        # Peak impact
      day_5: 0.9                        # Peak impact window
      day_6: 0.6
      day_7: 0.4                        # Fading impact

    # Weather events that correlate with quality issues
    tracked_events:
      - heavy_rain:
          impact: ["moisture_excess", "fungal_risk"]
          severity_threshold: ">50mm/day"
      - frost:
          impact: ["leaf_damage", "growth_stunting"]
          severity_threshold: "<2°C"
      - drought_spell:
          impact: ["moisture_deficit", "leaf_stress"]
          severity_threshold: ">5 consecutive days without rain"
      - temperature_extreme:
          impact: ["heat_stress", "growth_issues"]
          severity_threshold: ">35°C or <5°C"
      - high_humidity:
          impact: ["fungal_risk", "pest_proliferation"]
          severity_threshold: ">90% for >12 hours"

  mcp_sources:
    - server: collection
      tools: [get_regional_weather]     # Fetch from Region's weather data
    - server: plantation
      tools: [get_farmer, get_region]   # Get farmer's region for weather context

  context_enrichment:
    include_seasonal_context: true      # Include current flush from Region
    include_altitude_adjustment: true   # Adjust expectations by altitude band
```

**How Weather Lag Works in Analysis:**

```
Quality issue detected on Thursday (Day 0):
┌─────────────────────────────────────────────────────────────────┐
│  WEATHER LOOKBACK                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Day -7 (Last Thursday)  ░░░░░░░░░░░ weight: 0.4                │
│  Day -6 (Friday)         ░░░░░░░░░░░░ weight: 0.6               │
│  Day -5 (Saturday)       ░░░░░░░░░░░░░░░░░ weight: 0.9 ◀─ PEAK  │
│  Day -4 (Sunday)         ░░░░░░░░░░░░░░░░░░░ weight: 1.0 ◀─ PEAK│
│  Day -3 (Monday)         ░░░░░░░░░░░░░░░░░ weight: 0.9 ◀─ PEAK  │
│  Day -2 (Tuesday)        ░░░░░░░░░ weight: 0.5                   │
│  Day -1 (Wednesday)      ░░░░░ weight: 0.3                       │
│  Day 0 (Thursday)        [QUALITY ISSUE DETECTED]                │
│                                                                  │
│  Heavy rain on Sunday (Day -4) → Strongest correlation          │
│  to Thursday's quality issue                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Seasonal Context Integration:**

The Weather Analyzer also considers the current flush (from Region entity) when assessing impact:

| Flush Period | Weather Sensitivity | Notes |
|--------------|---------------------|-------|
| First Flush | High | Delicate growth, rain can damage quality |
| Monsoon Flush | Medium | Expected moisture, focus on excess |
| Autumn Flush | Medium-High | Transitional, variable weather impact |
| Dormant | Low | Minimal growth, weather less critical |

### Two Databases

#### Analysis DB (MongoDB)
**Purpose:** Store diagnoses created by Knowledge Model

**Schema:** Single collection with `type` field for extensibility

```json
{
    "_id": "analysis-uuid",
    "type": "disease_detection",
    "farmer_id": "WM-4521",
    "source_documents": ["doc-123", "doc-456"],
    "diagnosis": {
        "condition": "fungal_infection",
        "confidence": 0.87,
        "details": "Leaf spots consistent with Cercospora...",
        "severity": "moderate"
    },
    "rag_context_used": true,
    "created_at": "2025-12-16T14:30:00Z",
    "agent_workflow": "disease-detection-v2"
}
```

**Design Choice:** Generic schema allows adding new analysis types dynamically without code changes.

#### Vector DB (Pinecone)
**Purpose:** Expert knowledge for RAG enrichment

**Content:**
- Industry best practices
- Tea cultivation guidelines
- Disease/pest identification
- Regional patterns and seasonal factors

**Curated by:** Domain experts (agronomists)

### RAG Pattern

Analyzer Agents use Retrieval-Augmented Generation:

```
Input: Poor quality document (image, grade D, moisture issues)
         │
         ▼
Query Vector DB: "tea leaf moisture problems causes"
         │
         ▼
Retrieved: Expert knowledge about moisture, common causes
         │
         ▼
LLM generates diagnosis WITH expert context:
"Diagnosis: Excessive moisture likely caused by late harvesting
 after morning dew. Pattern consistent with Nyeri region
 during October rains."
         │
         ▼
Store in Analysis DB (linked to farmer)
```

### Trigger Configuration

```yaml
analysis_triggers:
  - name: poor-quality-analysis
    type: event
    event: "collection.poor_quality_detected"
    agent: disease-detection-agent
    rag_enabled: true
    rag_query_template: "tea leaf quality issues {quality_issues}"

  - name: weather-impact-analysis
    type: scheduled
    cron: "0 6 * * *"  # Daily at 6 AM
    agent: weather-impact-agent
    rag_enabled: true

  - name: trend-analysis
    type: scheduled
    cron: "0 0 * * 0"  # Weekly Sunday midnight
    agent: trend-analysis-agent
    rag_enabled: false
```

### MCP Server Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get_farmer_analyses` | Get all analyses for a farmer | `farmer_id`, `date_range?`, `type?` |
| `get_analysis_by_id` | Retrieve specific analysis | `analysis_id` |
| `search_analyses` | Search analyses by criteria | `query`, `filters`, `limit` |
| `get_recent_diagnoses` | Get diagnoses needing action | `farmer_id`, `since_date` |

**Primary Consumer:** Action Plan Model queries weekly: "Get all analyses for farmer X in past week"

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | DIAGNOSE only | Clean separation from prescribing |
| **Agent Architecture** | Multiple specialized workflows | Different analyses need different approaches |
| **Trigger Mechanism** | Configurable (event OR scheduled) | Flexibility per analysis type |
| **Tracking** | Self-maintained | No dependency on Collection Model |
| **Analysis Storage** | Single collection + type field | Generic, dynamic extensibility |
| **Expert Knowledge** | Vector DB for RAG | Enriches diagnosis with domain expertise |

### Diagnosis Deduplication Strategy

When a farmer delivers multiple poor-quality batches in a short period, the system uses **pre-analysis aggregation** to avoid duplicate diagnoses and provide richer context.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PRE-ANALYSIS AGGREGATION                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  EVENT FLOW (Multiple poor quality events for same farmer)              │
│                                                                         │
│  Mon 8:00  POOR_QUALITY_DETECTED (farmer WM-4521) ──┐                   │
│  Mon 9:30  POOR_QUALITY_DETECTED (farmer WM-4521) ──┤                   │
│  Mon 14:00 POOR_QUALITY_DETECTED (farmer WM-4521) ──┼──▶ QUEUE          │
│  Tue 7:00  POOR_QUALITY_DETECTED (farmer WM-4521) ──┤    (pending)      │
│  Tue 10:00 POOR_QUALITY_DETECTED (farmer WM-4521) ──┘                   │
│                                                                         │
│                                    │                                    │
│                                    ▼                                    │
│  DAILY AGGREGATION JOB (2 AM via Dapr Jobs)                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  1. Query pending events grouped by farmer_id                    │   │
│  │  2. For each farmer with events:                                 │   │
│  │     a. Fetch all images + metadata                               │   │
│  │     b. Run SINGLE diagnosis with full context                    │   │
│  │     c. Store diagnosis linked to ALL source events               │   │
│  │     d. Mark events as processed                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  RESULT: 1 diagnosis referencing 5 source events                        │
│  {                                                                      │
│    diagnosis_id: "diag-001",                                            │
│    farmer_id: "WM-4521",                                                │
│    source_events: ["evt-1", "evt-2", "evt-3", "evt-4", "evt-5"],        │
│    condition: "fungal_infection",                                       │
│    confidence: 0.91,  // Higher due to multiple evidence sources        │
│    evidence_summary: "5 samples over 2 days show consistent pattern"   │
│  }                                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Aggregation Configuration:**

```yaml
# knowledge-model/config/aggregation.yaml
diagnosis_aggregation:
  enabled: true
  window_hours: 24              # Aggregate events within 24-hour window
  schedule: "0 2 * * *"         # Run at 2 AM daily

  grouping:
    primary_key: farmer_id
    secondary_key: quality_issue_category  # Optional: separate fungal vs technique

  thresholds:
    min_events_for_aggregation: 1    # Always aggregate (even single events)
    max_events_per_diagnosis: 10     # Split if too many events

  priority_override:
    # Critical issues bypass aggregation for immediate analysis
    immediate_analysis_if:
      - severity_indicator: "critical"
      - grade_category: "rejection"     # Grading Model semantic: lowest tier (e.g., D, Rejected)
      - quality_score_below: 0.3        # Alternative: threshold-based (normalized 0-1)
      - confidence_hint: "disease_outbreak"
```

**Benefits:**

| Aspect | Without Aggregation | With Aggregation |
|--------|---------------------|------------------|
| **LLM Calls** | 5 calls (5 events) | 1 call |
| **Diagnosis Quality** | Limited context per event | Full picture (all 5 images) |
| **Action Plan** | Must dedupe 5 similar diagnoses | Single comprehensive diagnosis |
| **Cost** | ~$0.06 (5 × Sonnet) | ~$0.015 (1 × Sonnet + more tokens) |

**Edge Cases:**

| Scenario | Handling |
|----------|----------|
| **Critical issue detected** | Bypass aggregation, analyze immediately |
| **Events span multiple days** | Include all within 24h window; older events in next batch |
| **Mixed issue types** | Group by `quality_issue_category` if configured |
| **10+ events** | Split into multiple diagnoses with cross-references |

### Testing Strategy

| Test Type | Scope |
|-----------|-------|
| **Explorer Agent** | Correctly identifies unanalyzed items, no duplicates |
| **Analyzer Accuracy** | Diagnoses match expert-validated cases |
| **RAG Relevance** | Vector search returns useful context |
| **New Type Addition** | Can add analysis type without deployment |
| **MCP Queries** | Type filtering works correctly |

### Triage Feedback Loop

The Triage Agent improves over time through a structured feedback loop that converts agronomist corrections into better few-shot examples.

#### Feedback Loop Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     TRIAGE FEEDBACK LOOP                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐       │
│  │  Triage  │────▶│ Analyzer │────▶│ Diagnosis│────▶│Agronomist│       │
│  │  Agent   │     │ Routing  │     │ Generated│     │  Review  │       │
│  └──────────┘     └──────────┘     └──────────┘     └────┬─────┘       │
│       ▲                                                  │             │
│       │              FEEDBACK TYPES                      │             │
│       │         ┌────────────────────────┐               │             │
│       │         │ ✓ Confirm routing      │◀──────────────┘             │
│       │         │ ✗ Correct category     │                             │
│       │         │ + Add missing analyzer │                             │
│       │         │ - Remove unnecessary   │                             │
│       │         └──────────┬─────────────┘                             │
│       │                    ▼                                           │
│       │         ┌────────────────────────┐                             │
│       │         │   MongoDB Collection   │                             │
│       │         │   triage_feedback      │                             │
│       │         └──────────┬─────────────┘                             │
│       │                    ▼                                           │
│       │         ┌────────────────────────┐                             │
│       │         │  Dapr Job (Weekly)     │                             │
│       │         │  feedback-aggregator   │                             │
│       │         └──────────┬─────────────┘                             │
│       │                    ▼                                           │
│       │         ┌────────────────────────┐                             │
│       │         │  Generate Few-Shot     │                             │
│       │         │  Examples + A/B Test   │                             │
│       └─────────┴────────────────────────┘                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Feedback Storage Schema

```yaml
# MongoDB: triage_feedback collection
triage_feedback:
  _id: ObjectId
  diagnosis_id: string           # Links to original diagnosis
  quality_event_id: string       # Original event that triggered triage

  # Original triage decision
  original_classification:
    category: string             # "disease", "weather", "technique", etc.
    routed_analyzers: string[]   # ["disease_detection", "weather_impact"]
    confidence: float            # 0.0-1.0
    reasoning: string            # Triage agent's explanation

  # Agronomist feedback
  feedback:
    action: enum                 # "confirm", "correct", "add_analyzer", "remove_analyzer"
    correct_category: string?    # If action = "correct"
    correct_analyzers: string[]? # If action = "correct"
    notes: string?               # Optional explanation
    agronomist_id: string
    timestamp: datetime

  # Learning status
  learning_status: enum          # "pending", "incorporated", "rejected"
  incorporated_at: datetime?
```

#### Improvement Pipeline

| Step | Trigger | Process | Output |
|------|---------|---------|--------|
| **1. Aggregate** | Dapr Job (weekly) | Group corrections by pattern, filter ≥5 similar with >80% agreement | Candidate patterns |
| **2. Generate** | Automatic | Select representative cases, format as few-shot examples | New prompt examples |
| **3. A/B Test** | Automatic (1 week) | Shadow mode: run old + new prompt, compare accuracy | Test results |
| **4. Promote** | Manual approval | If improved → update production prompt | New prompt version |

#### Dapr Job Configuration

```yaml
# dapr/jobs/feedback-aggregator.yaml
apiVersion: dapr.io/v1alpha1
kind: Job
metadata:
  name: triage-feedback-aggregator
spec:
  schedule: "0 2 * * 0"  # Weekly, Sunday 2 AM
  job:
    apiVersion: batch/v1
    kind: Job
    metadata:
      name: feedback-aggregator
    spec:
      template:
        spec:
          containers:
            - name: aggregator
              image: farmer-power/feedback-aggregator:latest
              env:
                - name: MONGO_URI
                  valueFrom:
                    secretKeyRef:
                      name: knowledge-secrets
                      key: mongo-uri
                - name: MIN_CORRECTIONS
                  value: "5"
                - name: MIN_AGREEMENT
                  value: "0.8"
          restartPolicy: OnFailure
```

#### Few-Shot Example Generation

When patterns are validated, they become prompt examples:

```yaml
# Generated from feedback pattern
# Source: 12 corrections, 92% agronomist agreement
# Pattern: "disease" → "weather" for highland frost cases

new_example:
  input: |
    Symptoms: Brittle stems, brown leaf edges, wilting
    Location: Kericho County, altitude 2100m
    Recent weather: Frost warning 3 days ago, min temp 2°C
  output:
    category: "weather"
    analyzers: ["weather_impact"]
    confidence: 0.85
  explanation: |
    Highland frost damage often misclassified as disease.
    Key indicators: brittle (not soft) stems, recent sub-5°C temps,
    altitude >2000m increases frost risk.
```

#### Metrics Tracked

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| **Correction Rate** | % of diagnoses corrected by agronomists | >20% triggers review |
| **Pattern Detection** | New correction patterns identified | Weekly report |
| **Prompt Version Accuracy** | Precision/recall per category per version | Degradation >5% |
| **A/B Test Results** | New vs old prompt performance | Auto-reject if worse |

---

## Plantation Model Architecture

### Overview

The Plantation Model is the **master data registry** for the Farmer Power Cloud Platform. It stores core entities (regions, farmers, factories), configuration (payment policies, grading model references), and pre-computed performance summaries.

**Core Responsibility:** Manage master data, store configuration, provide pre-computed summaries.

**Does NOT:** Collect raw data, perform analysis, or generate action plans.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       PLANTATION MODEL                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STATIC DATA (via Admin UI):                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐         │
│  │   REGION    │  │   FARMER    │  │   FACTORY               │         │
│  │             │  │             │  │                         │         │
│  │ • region_id │  │ • farmer_id │  │ • factory_id            │         │
│  │ • name      │  │ • name      │  │ • name                  │         │
│  │ • county    │  │ • phone     │  │ • location              │         │
│  │ • country   │  │ • national_id│ │ • payment_policy        │         │
│  │             │  │ • gps_coords│  │                         │         │
│  │ GEOGRAPHY:  │  │ • altitude  │  │                         │         │
│  │ • center_gps│  │   (Google   │  │                         │         │
│  │ • radius_km │  │    Elevation│  │                         │         │
│  │ • altitude  │  │    API)     │  │                         │         │
│  │   _band     │  │ • farm_size │  │                         │         │
│  │   (min/max) │  │ • region_id │◀─┼── assigned by altitude  │         │
│  │             │  │ • factory_id│  │                         │         │
│  │ FLUSH       │  │             │  │                         │         │
│  │ CALENDAR:   │  │ COMMUNICATION:│ │                         │         │
│  │ • first     │  │ • pref_channel│ │                         │         │
│  │   _flush    │  │   (SMS/Voice/ │ │                         │         │
│  │ • monsoon   │  │    WhatsApp)  │ │                         │         │
│  │   _flush    │  │ • pref_lang   │ │                         │         │
│  │ • autumn    │  │ • literacy_lvl│ │                         │         │
│  │   _flush    │  │             │  │                         │         │
│  │ • dormant   │  └─────────────┘  │                         │         │
│  │             │                   │                         │         │
│  │ AGRONOMIC:  │  ┌─────────────────────────────────────────┐│         │
│  │ • soil_type │  │  GRADING MODEL REF                      ││         │
│  │ • typical   │  │  • model_id, version                    ││         │
│  │   _diseases │  │  • active_at_factory[]                  ││         │
│  │ • weather   │  │  (Definition in farmer-power-training)  ││         │
│  │   _api_loc  │  └─────────────────────────────────────────┘│         │
│  └─────────────┘                                             │         │
│                                                                         │
│  COMPUTED DATA (via Scheduler - daily batch):                           │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐      │
│  │  FARMER PERFORMANCE         │  │  FACTORY PERFORMANCE        │      │
│  │                             │  │                             │      │
│  │  • avg_grade (30/90/yr)     │  │  • intake_quality_avg       │      │
│  │  • delivery_count           │  │  • farmer_improvement_rate  │      │
│  │  • improvement_trend        │  │  • rejection_rate           │      │
│  │  • last_delivery            │  │  • premium_percentage       │      │
│  └─────────────────────────────┘  └─────────────────────────────┘      │
│                                                                         │
│  EXTERNAL DATA (via Market Analysis Model):                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  BUYER PROFILES                                                  │   │
│  │  • buyer_id, preferences, quality_requirements                   │   │
│  │  • Created/updated by Market Analysis Model                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                         APIs + MCP                                │  │
│  │  REST API (Admin UI)  │  Internal API (Services)  │  MCP Server  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Region Entity

The Region entity enables efficient weather collection and seasonal context management by grouping farms with similar agronomic conditions.

**Key Design Decision:** Regions are defined by **county + altitude band**, not just geographic proximity. Two farms 5 km apart at the same altitude have similar weather; two farms 500m apart with 400m altitude difference have significantly different conditions.

```yaml
# Region Entity Schema
region:
  # ═══════════════════════════════════════════════════════════════════
  # IDENTITY
  # ═══════════════════════════════════════════════════════════════════
  region_id: "nyeri-highland"           # Pattern: {county}-{altitude_band}
  name: "Nyeri Highland"
  county: "Nyeri"
  country: "Kenya"

  # ═══════════════════════════════════════════════════════════════════
  # GEOGRAPHY
  # ═══════════════════════════════════════════════════════════════════
  geography:
    center_gps:
      lat: -0.4197
      lng: 36.9553
    radius_km: 25                       # Approximate coverage
    altitude_band:
      min_meters: 1800
      max_meters: 2200
      label: "highland"                 # highland | midland | lowland

  # ═══════════════════════════════════════════════════════════════════
  # FLUSH CALENDAR (Tea Seasons)
  # ═══════════════════════════════════════════════════════════════════
  flush_calendar:
    first_flush:
      start: "03-15"
      end: "05-15"
      characteristics: "Highest quality, delicate flavor"
    monsoon_flush:
      start: "06-15"
      end: "09-30"
      characteristics: "High volume, robust flavor"
    autumn_flush:
      start: "10-15"
      end: "12-15"
      characteristics: "Balanced quality"
    dormant:
      start: "12-16"
      end: "03-14"
      characteristics: "Minimal growth"

  # ═══════════════════════════════════════════════════════════════════
  # AGRONOMIC FACTORS
  # ═══════════════════════════════════════════════════════════════════
  agronomic:
    soil_type: "volcanic_red"
    typical_diseases:
      - "blister_blight"
      - "grey_blight"
      - "red_rust"
    harvest_peak_hours: "06:00-10:00"
    frost_risk: true                    # Highland regions

  # ═══════════════════════════════════════════════════════════════════
  # WEATHER CONFIGURATION
  # ═══════════════════════════════════════════════════════════════════
  weather_config:
    api_location:
      lat: -0.4197
      lng: 36.9553
    altitude_for_api: 1950              # Representative altitude
    collection_time: "06:00"            # Daily weather fetch time
```

**Altitude Band Definitions (Kenya Tea Regions):**

| Altitude Band | Elevation Range | Characteristics |
|---------------|-----------------|-----------------|
| **Highland** | 1800m+ | Cooler, more rainfall, later flushes, frost risk |
| **Midland** | 1400m - 1800m | Moderate conditions, typical patterns |
| **Lowland** | Below 1400m | Warmer, earlier flushes, different disease profile |

**Farm-to-Region Assignment:**

When a farmer is registered, their GPS coordinates and altitude (via Google Elevation API) determine their region:

```python
def assign_farm_to_region(farm_gps: GPS, farm_altitude: int) -> str:
    """
    Assigns a farm to the appropriate region based on location and altitude.
    Returns region_id in format: {county}-{altitude_band}
    """
    county = geocode_to_county(farm_gps)  # e.g., "nyeri"

    if farm_altitude >= 1800:
        band = "highland"
    elif farm_altitude >= 1400:
        band = "midland"
    else:
        band = "lowland"

    return f"{county}-{band}"  # e.g., "nyeri-highland"
```

**Weather Collection Optimization:**

| Approach | API Calls/Day | Annual Cost (at $0.001/call) |
|----------|---------------|------------------------------|
| Per Farm (800,000 farms) | 800,000 | ~$292,000 |
| Per Region (~50 regions) | 50 | ~$18 |

### Data Ownership

| Entity | Writer | Mechanism | Frequency |
|--------|--------|-----------|-----------|
| Region | Admin UI | REST API (manual) | On region setup |
| Farmer | Admin UI | REST API (manual) | On registration/update |
| Factory | Admin UI | REST API (manual) | On setup/config change |
| Grading Model Ref | Admin UI | REST API (manual) | On model deployment |
| Farmer Performance | Scheduler | Batch job (automated) | Daily |
| Factory Performance | Scheduler | Batch job (automated) | Daily |
| Regional Weather | Collection Model | Scheduled job | Daily per region |
| Buyer Profiles | Market Analysis Model | Internal API (automated) | On market analysis |

### Farmer Power Ecosystem Context

The Plantation Model references grading models but does NOT store their definitions:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FARMER POWER ECOSYSTEM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │  CLOUD PLATFORM │  │  QC ANALYZER    │  │  CV TRAINING    │         │
│  │  (this project) │  │  (edge device)  │  │  (ML pipeline)  │         │
│  │                 │  │                 │  │                 │         │
│  │  Plantation     │  │  Uses grading   │  │  Defines grading│         │
│  │  stores REF to  │  │  model for      │  │  model (weights,│         │
│  │  grading model  │  │  inference      │  │  thresholds)    │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│                                                                         │
│  github.com/farmerpower-ai/farmer-power-platform                        │
│  github.com/farmerpower-ai/farmer-power-qc-analyzer                     │
│  github.com/farmerpower-ai/farmer-power-training                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Performance Summary Computation (Hybrid Approach)

The system uses a **hybrid approach** combining batch processing for historical aggregates with real-time streaming for same-day visibility.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HYBRID PERFORMANCE SUMMARIES                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  BATCH JOB (Daily 2 AM via Dapr Jobs)                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Source: Collection Model (raw quality events)                   │   │
│  │                                                                  │   │
│  │  Computes historical aggregates:                                 │   │
│  │  • avg_grade_30d, avg_grade_90d, avg_grade_year                 │   │
│  │  • delivery_count_30d, delivery_count_90d                       │   │
│  │  • improvement_trend (stable, improving, declining)             │   │
│  │  • computed_at: timestamp                                        │   │
│  │                                                                  │   │
│  │  Updates: Plantation Model (farmer_performance, factory_performance)│
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  STREAMING (Real-time via Dapr Pub/Sub)                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Event: collection.document_stored                               │   │
│  │                                                                  │   │
│  │  Updates "today" counters (per farmer):                          │   │
│  │  • today_deliveries: number                                      │   │
│  │  • today_grades: object (dynamic, keyed by Grading Model labels) │   │
│  │    Example A/B/C/D model: { "A": 2, "B": 1, "C": 0, "D": 0 }     │   │
│  │    Example ternary model: { "premium": 3, "standard": 2, "rejected": 0 } │
│  │  • today_avg_score: number (0.0-1.0, normalized)                 │   │
│  │  • last_delivery: timestamp                                      │   │
│  │                                                                  │   │
│  │  Note: Grade labels are dynamic - fetched from factory's Grading Model │
│  │  Behavior: Resets at midnight (batch job incorporates into history) │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Farmer Performance Schema:**

```yaml
# MongoDB: farmer_performance (embedded in farmer document or separate collection)
farmer_performance:
  farmer_id: string

  # Historical (updated by batch job)
  historical:
    avg_grade_30d: number
    avg_grade_90d: number
    avg_grade_year: number
    delivery_count_30d: number
    delivery_count_90d: number
    improvement_trend: enum      # "improving" | "stable" | "declining"
    computed_at: datetime        # When batch job ran

  # Today (updated by streaming)
  today:
    deliveries: number
    grades: object               # Dynamic map keyed by Grading Model labels
                                 # Example A/B/C/D: { "A": 2, "B": 1, "C": 0, "D": 0 }
                                 # Example ternary: { "premium": 3, "standard": 2, "rejected": 0 }
    avg_score: number            # Normalized 0.0-1.0 (not grade label)
    last_delivery: datetime
    date: date                   # Resets when date changes
    grading_model_id: string     # Reference to Grading Model for label lookup
```

**Dashboard Display Example:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Farmer WM-4521 Performance                                              │
│  ─────────────────────────────────────────────────────────────────────   │
│                                                                          │
│  TODAY: 3 deliveries (A, A, B) - avg: A-        Last: 8:15 AM           │
│                                                                          │
│  HISTORICAL (as of Dec 16, 2:00 AM):                                     │
│  • 30-day avg: B+        • 90-day avg: B        • Year avg: B-          │
│  • Trend: Improving ↑    • Total deliveries (30d): 12                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- Real-time visibility into same-day activity
- Clear "as of" timestamps prevent confusion
- Historical trends remain accurate (complex aggregations done in batch)
- Minimal additional complexity (reuses existing Dapr pub/sub)

### API Structure

#### Admin UI Endpoints (authenticated, role-based)

```
# Region Management
POST   /api/v1/regions              # Create region
GET    /api/v1/regions              # List regions (filter: county, altitude_band)
GET    /api/v1/regions/{id}         # Get region details
PUT    /api/v1/regions/{id}         # Update region (flush calendar, agronomic)
DELETE /api/v1/regions/{id}         # Deactivate region (soft delete)

# Farmer Management
POST   /api/v1/farmers              # Create farmer (auto-assigns region)
GET    /api/v1/farmers/{id}         # Get farmer
PUT    /api/v1/farmers/{id}         # Update farmer
DELETE /api/v1/farmers/{id}         # Deactivate farmer

# Factory Management
POST   /api/v1/factories            # Create factory
GET    /api/v1/factories/{id}       # Get factory
PUT    /api/v1/factories/{id}       # Update factory config
```

#### Internal Endpoints (service-to-service)

```
PUT    /api/v1/internal/farmer-summary/{id}     # Scheduler writes
PUT    /api/v1/internal/factory-summary/{id}    # Scheduler writes
PUT    /api/v1/internal/buyer-profiles/{id}     # Market Analysis writes
```

### MCP Server Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get_farmer` | Farmer profile | `farmer_id` |
| `get_farmer_summary` | Performance summary | `farmer_id`, `period?` |
| `get_factory` | Factory details + payment_policy | `factory_id` |
| `get_factory_config` | Grading model ref, thresholds | `factory_id` |
| `get_buyer_profiles` | Market preferences | `region?`, `factory_id?` |
| `get_farmer_context` | Combined view (convenience) | `farmer_id` |
| `get_region` | Region details + flush calendar | `region_id` |
| `get_region_weather` | Weather data for region (7-day history) | `region_id`, `days?` |
| `get_current_flush` | Current flush period for a region | `region_id` |
| `list_regions` | All regions with summary | `county?`, `altitude_band?` |

**Primary Consumer:** Action Plan Model queries via MCP for complete farmer context when generating recommendations.

**Weather Analyzer:** Uses `get_region`, `get_region_weather`, and `get_current_flush` to correlate weather events with quality issues using the 7-day lookback pattern.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | Master data + summaries | Single source of truth for entities |
| **Performance Summaries** | Pre-computed (daily batch) | Fast access, no real-time computation |
| **Grading Model** | Reference only | Definition in separate training project |
| **Buyer Profiles** | Stored here, written by Market Analysis | Centralized profile storage |
| **MCP Server** | Yes | AI agents need rich farmer/factory context |
| **Data Ownership** | Clear per-entity | Admin UI, Scheduler, Market Analysis |

### Testing Strategy

| Test Type | Focus |
|-----------|-------|
| **Admin API** | Input validation, authorization, audit trail |
| **Scheduler Job** | Reliability, computation accuracy, idempotency |
| **Market Analysis Integration** | API contract, data integrity |
| **MCP Tools** | Correct data retrieval, access control |
| **Performance Summaries** | Aggregation accuracy vs. raw data |

---

## Action Plan Model Architecture

### Overview

The Action Plan Model is the **prescription engine** that transforms diagnoses from the Knowledge Model into actionable recommendations for farmers. It generates dual-format outputs: detailed reports for experts and simplified communications for farmers.

**Core Responsibility:** PRESCRIBE actions (what should the farmer do?)

**Does NOT:** Diagnose problems, collect data, or deliver messages (SMS delivery is infrastructure).

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       ACTION PLAN MODEL                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUTS (via MCP):                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │ Knowledge MCP   │    │ Plantation MCP  │    │ Collection MCP  │     │
│  │ (analyses)      │    │ (farmer context)│    │ (raw data)      │     │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘     │
│           │                      │                      │               │
│           └──────────────────────┼──────────────────────┘               │
│                                  ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      SELECTOR AGENT                              │   │
│  │  • Runs weekly (scheduled)                                       │   │
│  │  • Queries: "What analyses were created for farmer X this week?" │   │
│  │  • Routes to Action Plan Generator with combined context         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                  │                                       │
│                                  ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                 ACTION PLAN GENERATOR AGENT                      │   │
│  │                                                                   │   │
│  │  INPUT: Combined analyses + farmer context                        │   │
│  │                                                                   │   │
│  │  OUTPUT:                                                          │   │
│  │  ┌──────────────────────┐  ┌──────────────────────┐              │   │
│  │  │  DETAILED REPORT     │  │  FARMER MESSAGE      │              │   │
│  │  │  (Markdown)          │  │  (Simplified)        │              │   │
│  │  │                      │  │                      │              │   │
│  │  │  • Full analysis     │  │  • Local language    │              │   │
│  │  │  • Expert details    │  │  • Simple actions    │              │   │
│  │  │  • Confidence scores │  │  • SMS-ready format  │              │   │
│  │  │  • Source references │  │  • Cultural context  │              │   │
│  │  └──────────────────────┘  └──────────────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                  │                                       │
│                                  ▼                                       │
│              ┌─────────────────────────────────────┐                    │
│              │         ACTION PLAN DB              │                    │
│              │         (MongoDB)                   │                    │
│              │                                     │                    │
│              │  Both formats stored per plan       │                    │
│              └─────────────────────────────────────┘                    │
│                                  │                                       │
│                                  ▼                                       │
│              ┌─────────────────────────────────────┐                    │
│              │      INFRASTRUCTURE LAYER           │                    │
│              │      (Message Delivery - External)  │                    │
│              │                                     │                    │
│              │  SMS Gateway, Push Notifications    │                    │
│              └─────────────────────────────────────┘                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Two-Agent Pattern

#### Selector Agent
- **Trigger:** Weekly scheduled (e.g., every Monday at 6 AM)
- **Responsibility:** For each active farmer, query Knowledge MCP for analyses created in past 7 days
- **Logic:**
  - Has analyses → Route to Action Plan Generator with combined context
  - No analyses → Can trigger informational message (no action plan created)

#### Action Plan Generator Agent
- **Input:** All analyses for one farmer (combined) + farmer context from Plantation MCP
- **Output:** Dual-format action plan stored in MongoDB
- **Behavior:** Combines multiple diagnoses into a coherent, prioritized action plan

### Dual-Format Output

Both formats are generated in the same workflow and stored together:

```json
{
    "_id": "action-plan-uuid",
    "farmer_id": "WM-4521",
    "week": "2025-W51",
    "created_at": "2025-12-16T06:00:00Z",
    "source_analyses": ["analysis-123", "analysis-456", "analysis-789"],

    "detailed_report": {
        "format": "markdown",
        "content": "# Weekly Action Plan for WM-4521\n\n## Summary\nBased on 3 analyses this week...\n\n## Priority Actions\n1. **Fungal Treatment Required** (High Priority)\n   - Diagnosis: Cercospora leaf spot detected\n   - Confidence: 87%\n   - Action: Apply copper-based fungicide within 3 days...\n\n## Full Analysis Details\n...",
        "priority_actions": 2,
        "analyses_summarized": 3
    },

    "farmer_message": {
        "language": "sw",
        "content": "Habari! Wiki hii tuligundua ugonjwa wa majani. Tafadhali...",
        "sms_segments": 2,
        "character_count": 280,
        "delivery_status": "pending"
    }
}
```

### Farmer Communication Preferences

The Action Plan Generator queries Plantation MCP for farmer profile including:
- **pref_channel:** SMS, Voice, WhatsApp - determines output format
- **pref_lang:** Swahili, Kikuyu, English, etc. - determines translation target
- **literacy_lvl:** Low, Medium, High - determines simplification level

### Translation and Simplification

The Action Plan Generator Agent handles (based on farmer preferences):
- **Language Translation:** From English analysis to farmer's `pref_lang`
- **Simplification:** Adjusted to farmer's `literacy_lvl` (low = very simple, high = more detail)
- **Prioritization:** Multiple issues → Ordered by urgency/impact
- **Cultural Context:** Region-appropriate recommendations
- **Format Adaptation:** Based on `pref_channel` (SMS length, voice script, WhatsApp rich text)

### Empty State Handling

When Selector Agent finds no analyses for a farmer:
- **No action plan created** (nothing to prescribe)
- **Optional:** Trigger informational message ("No issues detected this week, keep up the good work!")
- **Tracking:** Record that farmer was checked but had no analyses

### No MCP Server

**Decision:** Action Plan Model does NOT expose an MCP Server.

**Rationale:**
- This is the **final output** of the analysis pipeline
- Consumers are the messaging infrastructure and dashboard UI
- No downstream AI agents need to query action plans
- Direct database access or REST API is sufficient

### Message Delivery Separation

**Architecture Decision:** Message delivery is NOT part of Action Plan Model - it's handled by a **Unified Notification Infrastructure Component**.

```
Action Plan Model                 NOTIFICATION INFRASTRUCTURE
┌─────────────────┐               ┌─────────────────────────────────────────┐
│ Generates plans │──────────────▶│           Notification Service          │
│ Stores in DB    │   publish     │                                         │
│                 │   event       │  ┌─────────────────────────────────┐    │
└─────────────────┘               │  │   Unified Channel Abstraction   │    │
                                  │  │                                 │    │
                                  │  │  notify(farmer_id, message)     │    │
                                  │  │  → Reads pref_channel from      │    │
                                  │  │    Plantation Model             │    │
                                  │  │  → Routes to appropriate        │    │
                                  │  │    channel adapter              │    │
                                  │  └─────────────────────────────────┘    │
                                  │                  │                      │
                                  │    ┌─────────────┼─────────────┐        │
                                  │    ▼             ▼             ▼        │
                                  │  ┌─────┐     ┌─────┐     ┌─────┐       │
                                  │  │ SMS │     │Whats│     │Tele │       │
                                  │  │     │     │App  │     │gram │       │
                                  │  └─────┘     └─────┘     └─────┘       │
                                  │    ▼             ▼             ▼        │
                                  │  ┌─────┐     ┌─────┐     ┌─────┐       │
                                  │  │Email│     │Mobile│    │Future│      │
                                  │  │     │     │ App  │    │Channel│     │
                                  │  └─────┘     └─────┘     └─────┘       │
                                  └─────────────────────────────────────────┘
```

### Unified Notification Infrastructure

**Purpose:** Generic infrastructure component providing unified abstraction for farmer communication across all channels.

**Supported Channels:**

| Channel    | Adapter                       | Use Case                   |
|------------|-------------------------------|----------------------------|
| SMS        | Twilio, Africa's Talking      | Basic phones, low literacy |
| WhatsApp   | WhatsApp Business API         | Rich media, most farmers   |
| Telegram   | Telegram Bot API              | Tech-savvy farmers         |
| Email      | SendGrid / SMTP               | Factory managers, reports  |
| Mobile App | Push Notifications (FCM/APNs) | App users                  |

**Unified Interface:**
```typescript
interface NotificationService {
  // Simple: auto-routes based on farmer preference
  notify(farmerId: string, message: NotificationPayload): Promise<DeliveryResult>;

  // Explicit: override channel if needed
  notifyVia(farmerId: string, channel: Channel, message: NotificationPayload): Promise<DeliveryResult>;

  // Bulk: weekly action plan distribution
  notifyBatch(notifications: BatchNotification[]): Promise<BatchResult>;
}

interface NotificationPayload {
  content: string;           // Pre-formatted for channel (from Action Plan)
  priority: 'low' | 'normal' | 'high';
  metadata: {
    source: 'action_plan' | 'alert' | 'info';
    actionPlanId?: string;
    farmerId: string;
  };
}
```

**Channel Selection Logic:**
1. Query Plantation MCP for farmer's `pref_channel`
2. Check channel availability (e.g., WhatsApp requires opt-in)
3. Fallback chain: preferred → SMS → store for later

**Benefits:**
- Action Plan Model focuses on content generation only
- Single abstraction for all notification consumers
- Easy to add new channels without changing producers
- Centralized delivery tracking, retry logic, rate limiting
- Channel-specific formatting handled by adapters

### SMS Cost Optimization Strategy

At scale (800,000 farmers), SMS costs are a critical concern. The platform uses a **tiered SMS strategy** to optimize costs while maintaining effective communication.

#### SMS Character Economics

| Character Set | Chars/Segment | Use Case |
|---------------|---------------|----------|
| **GSM-7** (ASCII + basic Latin) | 160 | English, transliterated Swahili |
| **Unicode** (full character set) | 70 | Native scripts, special characters |

**Cost Impact:** A 480-character message costs $0.15 (3 segments GSM-7) vs $0.35 (7 segments Unicode).

#### Tiered Message Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SMS TIER STRATEGY                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TIER 1: CRITICAL ALERTS (max 160 chars, 1 segment)                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Trigger: Urgent issues (disease outbreak, Grade D)              │   │
│  │  Format: GSM-7 (English + transliterated Swahili keywords)       │   │
│  │  Cost: $0.05/message                                             │   │
│  │                                                                  │   │
│  │  Example:                                                        │   │
│  │  "URGENT: Fungal disease found. Spray copper NOW.                │   │
│  │   Ugonjwa wa kuvu. Reply HELP for details."                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  TIER 2: WEEKLY SUMMARY (max 320 chars, 2 segments)                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Trigger: Monday weekly action plan                              │   │
│  │  Format: GSM-7 (transliterated Swahili)                          │   │
│  │  Cost: $0.10/message                                             │   │
│  │                                                                  │   │
│  │  Example:                                                        │   │
│  │  "Habari John! Wiki hii: 1) Nyunyiza dawa ndani ya siku 2        │   │
│  │   2) Vuna baada ya saa 3 asubuhi. Grade B - vizuri!"             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  TIER 3: RICH CONTENT (WhatsApp/App - unlimited)                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Trigger: Detailed recommendations, images                       │   │
│  │  Format: Full Unicode, rich media                                │   │
│  │  Cost: ~$0.02/message (WhatsApp Business API)                    │   │
│  │                                                                  │   │
│  │  For farmers with WhatsApp opt-in - full detailed plans          │   │
│  │  with native language and treatment images                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Transliteration Strategy

Most Swahili text is GSM-7 compatible. Transliteration converts the few Unicode characters to ASCII equivalents:

| Native | Transliterated | Meaning | GSM-7 Safe |
|--------|----------------|---------|------------|
| Shamba | Shamba | Farm | ✅ Already safe |
| Ugonjwa | Ugonjwa | Disease | ✅ Already safe |
| Majani ya chai | Majani ya chai | Tea leaves | ✅ Already safe |
| — (em dash) | - | Separator | ✅ Converted |

**Result:** 95%+ of Swahili messages fit in GSM-7 encoding.

#### Cost Projection (800,000 farmers)

| Strategy | Avg Segments | Cost/Farmer | Weekly Cost | Annual Cost |
|----------|--------------|-------------|-------------|-------------|
| **Naive (480 Unicode)** | 7 | $0.35 | $280,000 | $14.5M |
| **Tiered SMS** | 2 | $0.10 | $80,000 | $4.2M |
| **+WhatsApp shift (50%)** | 1.5 | $0.06 | $48,000 | $2.5M |

**Projected savings: ~$10-12M annually at scale.**

#### Message Generation Configuration

```yaml
# action-plan-model/config/message-tiers.yaml
message_tiers:
  critical_alert:
    max_chars: 160
    encoding: gsm7
    segments: 1
    triggers:
      - severity: critical
      - grade_category: rejection       # Semantic: lowest tier per Grading Model
      - quality_score_below: 0.3        # Alternative: normalized threshold
      - condition_type: disease_outbreak

  weekly_summary:
    max_chars: 320
    encoding: gsm7
    segments: 2
    triggers:
      - schedule: weekly
      - type: action_plan

  rich_content:
    max_chars: null              # Unlimited
    encoding: unicode
    channels: [whatsapp, app]
    triggers:
      - pref_channel: whatsapp
      - include_images: true

transliteration:
  enabled: true
  fallback_encoding: gsm7
  character_map:
    "—": "-"
    "'": "'"
    "…": "..."
```

### Two-Way Communication

The platform supports **inbound messages** from farmers, enabling them to ask questions, report actions taken, and provide feedback.

#### Inbound Message Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TWO-WAY COMMUNICATION                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  OUTBOUND (existing)                    INBOUND (new)                   │
│  ┌─────────────────────┐               ┌─────────────────────┐         │
│  │ Action Plan         │               │ SMS Gateway         │         │
│  │ → Notification      │               │ (Africa's Talking   │         │
│  │ → Farmer            │               │  webhook)           │         │
│  └─────────────────────┘               └──────────┬──────────┘         │
│                                                   │                    │
│                                                   ▼                    │
│                                        ┌─────────────────────┐         │
│                                        │ INBOUND HANDLER     │         │
│                                        │ (Notification Svc)  │         │
│                                        └──────────┬──────────┘         │
│                                                   │                    │
│                                                   ▼                    │
│                                        ┌─────────────────────┐         │
│                                        │ KEYWORD DETECTION   │         │
│                                        │ (fast, no LLM)      │         │
│                                        └──────────┬──────────┘         │
│                           ┌───────────────────────┼───────────────────┐│
│                           ▼                       ▼                   ▼│
│                   ┌─────────────┐       ┌─────────────┐     ┌─────────┐│
│                   │ "HELP"      │       │ "DONE"      │     │ Free    ││
│                   │ "MSAADA"    │       │ "NIMEFANYA" │     │ Text    ││
│                   └──────┬──────┘       └──────┬──────┘     └────┬────┘│
│                          │                     │                 │     │
│                          ▼                     ▼                 ▼     │
│              ┌───────────────────┐ ┌─────────────────┐ ┌─────────────┐│
│              │ Send last action  │ │ Log completion  │ │ AI Triage   ││
│              │ plan details      │ │ Update farmer   │ │ (Haiku)     ││
│              │ (WhatsApp rich)   │ │ performance     │ │             ││
│              └───────────────────┘ └─────────────────┘ └──────┬──────┘│
│                                                               │       │
│                                             ┌─────────────────┴─────┐ │
│                                             │   Route by intent:    │ │
│                                             │   • Question → FAQ    │ │
│                                             │   • Problem → Ticket  │ │
│                                             │   • Feedback → Log    │ │
│                                             └───────────────────────┘ │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

#### Keyword Commands (No LLM)

| Keyword | Language | Action | Response |
|---------|----------|--------|----------|
| `HELP` / `MSAADA` | EN/SW | Resend details | Full WhatsApp message with last action plan |
| `DONE` / `NIMEFANYA` | EN/SW | Mark complete | "Asante! Tumepokea. Reply HELP if problem persists" |
| `STOP` / `ACHA` | EN/SW | Opt out | Unsubscribe from messages |
| `STATUS` / `HALI` | EN/SW | Check status | Current grade trend, pending actions |

#### Free Text AI Triage

For messages that don't match keywords, use Haiku for fast intent classification:

```yaml
# notification-service/config/inbound-triage.yaml
inbound_triage:
  keyword_detection:
    enabled: true
    keywords:
      help: ["HELP", "MSAADA", "SAIDIA", "?"]
      done: ["DONE", "NIMEFANYA", "TAYARI", "OK"]
      stop: ["STOP", "ACHA", "SIMAMA"]
      status: ["STATUS", "HALI", "JINSI"]

  free_text:
    enabled: true
    model: "anthropic/claude-3-haiku"
    max_tokens: 100
    temperature: 0.1

    intents:
      - name: clarification_question
        examples: ["what is fungicide?", "dawa hii ni gani?"]
        action: faq_lookup_or_escalate

      - name: problem_report
        examples: ["I did it but still sick", "bado majani yanaugua"]
        action: create_support_ticket

      - name: feedback
        examples: ["it worked!", "vizuri sana"]
        action: log_feedback

      - name: unrelated
        examples: ["hello", "how are you"]
        action: send_menu
```

#### Intent Routing

| Intent | Action | Cost |
|--------|--------|------|
| **clarification_question** | Search FAQ, if no match → create support ticket | $0.001 |
| **problem_report** | Create support ticket, notify agronomist | $0.001 |
| **feedback** | Log to farmer record, update outcome tracking | $0.001 |
| **unrelated** | Send menu: "Reply HELP, DONE, or STATUS" | $0.001 |

#### Cost Projection

| Message Type | Est. Volume/Week | Cost |
|--------------|------------------|------|
| Keywords (no LLM) | ~50,000 | $0 |
| Free text triage (Haiku) | ~5,000 | ~$5 |
| **Total inbound** | 55,000 | **~$5/week** |

#### Inbound Webhook Configuration

```yaml
# notification-service/config/inbound-webhooks.yaml
inbound_webhooks:
  africas_talking:
    endpoint: /api/v1/inbound/sms/at
    auth: hmac_signature
    fields:
      from: "from"
      text: "text"
      date: "date"

  twilio:
    endpoint: /api/v1/inbound/sms/twilio
    auth: signature_validation
    fields:
      from: "From"
      text: "Body"
      date: "DateSent"

  whatsapp:
    endpoint: /api/v1/inbound/whatsapp
    auth: webhook_verification
    supports_media: true
```

### Message Delivery Assurance Strategy

Rural Kenya has significant network gaps (~15% of farmers experience regular connectivity issues). This strategy ensures critical information reaches farmers even in challenging environments.

#### Delivery Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    MESSAGE DELIVERY FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Message Generated] ──► [Send Attempt #1]                      │
│                              │                                  │
│                    ┌────────┴────────┐                          │
│                    ▼                 ▼                          │
│              [Delivered]      [Failed/Pending]                  │
│                    │                 │                          │
│                    ▼                 ▼                          │
│              [Log Success]    [Queue for Retry]                 │
│                                      │                          │
│                         ┌────────────┴────────────┐             │
│                         ▼                         ▼             │
│                   [Standard]              [Critical]            │
│                   Retry: 4h, 8h, 24h      Retry: 1h, 2h, 4h,    │
│                   Max: 3 attempts         8h, 24h, 48h          │
│                                           Max: 6 attempts       │
│                                                                 │
│  [All Retries Exhausted] ──► [Escalation Path]                  │
│                              - Flag farmer as "unreachable"     │
│                              - Alert cooperative lead farmer    │
│                              - Queue for next collection visit  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Delivery Configuration

```yaml
# notification-service/config/message-delivery.yaml
message_delivery:
  standard_messages:
    initial_timeout: 60s
    retry_intervals: [4h, 8h, 24h]
    max_attempts: 3
    on_exhausted: log_and_continue

  critical_alerts:
    initial_timeout: 30s
    retry_intervals: [1h, 2h, 4h, 8h, 24h, 48h]
    max_attempts: 6
    on_exhausted: escalate
    parallel_channels: true  # Try SMS + WhatsApp simultaneously

  escalation:
    notify_cooperative_lead: true
    flag_for_field_visit: true
    aggregate_missed_critical: true

delivery_tracking:
  store_delivery_receipts: true
  track_read_receipts: false  # Not reliable for SMS

  statuses:
    - sent
    - delivered
    - failed
    - pending_retry
    - escalated
```

#### Multi-Channel Fallback (Critical Alerts Only)

| Attempt | Channel | Timing | Rationale |
|---------|---------|--------|-----------|
| 1 | Primary (SMS or WhatsApp) | Immediate | User preference |
| 2 | Alternate channel | +1 hour | Different network path |
| 3 | Both channels | +4 hours | Maximize reach |
| 4+ | SMS only | +8h, +24h, +48h | SMS more reliable in poor coverage |

#### Catch-Up Message for Recovered Farmers

When a farmer becomes reachable again after missing messages:

```yaml
# notification-service/config/catchup-messages.yaml
catchup_message:
  enabled: true
  trigger: first_successful_delivery_after_failure

  template_sw: |
    {FARMER_NAME}, umekosa ujumbe {MISSED_COUNT}.
    MUHIMU ZAIDI: {PRIORITY_SUMMARY}
    Jibu HALI kupata muhtasari kamili.

  template_en: |
    {FARMER_NAME}, you missed {MISSED_COUNT} messages.
    MOST IMPORTANT: {PRIORITY_SUMMARY}
    Reply STATUS for full summary.

  priority_extraction:
    include_critical_alerts: true
    include_action_items: true
    max_items: 3
    max_age_days: 14
```

#### Lead Farmer Escalation

For truly unreachable farmers, escalate to cooperative leadership:

```yaml
# notification-service/config/escalation.yaml
lead_farmer_escalation:
  trigger_after_days: 3
  trigger_on_critical: immediate

  message_template_sw: |
    KIONGOZI: Mkulima {FARMER_NAME} hajafikika siku {DAYS}.
    Taarifa muhimu: {ALERT_SUMMARY}
    Tafadhali wasiliana naye.

  tracking:
    log_escalation: true
    request_confirmation: true
    auto_resolve_on_contact: true
```

#### Delivery Assurance Cost Impact

| Scenario | Additional Cost | Frequency | Monthly Impact |
|----------|-----------------|-----------|----------------|
| Standard retry (3x) | +2 SMS avg | 5% of messages | ~$4,000 |
| Critical retry (6x) | +5 SMS avg | 0.5% of messages | ~$1,500 |
| Lead farmer escalation | +1 SMS | 0.1% of farmers | ~$200 |
| **Total overhead** | | | **~$5,700/month** |

This represents ~4% overhead on base SMS cost - acceptable for reliability assurance.

### Group Messaging Architecture

The platform supports tiered group messaging to optimize communication costs and leverage cooperative structures common in rural Kenya.

#### Messaging Tiers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GROUP MESSAGING TIERS                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TIER 1: INDIVIDUAL (existing)                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  One farmer → One message                                        │   │
│  │  Personalized action plans, diagnoses                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  TIER 2: COOPERATIVE GROUP                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Lead Farmer receives aggregated group message                   │   │
│  │  "5 farmers in your group have fungal issues this week"          │   │
│  │  Includes: member names, summary, shared recommendations         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  TIER 3: REGIONAL BROADCAST                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  All farmers in a region receive same alert                      │   │
│  │  Weather warnings, disease outbreak notices                      │   │
│  │  Triggered by: Weather Analyzer, Knowledge Model patterns        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  TIER 4: FACTORY-WIDE ANNOUNCEMENT                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  All farmers delivering to a factory                             │   │
│  │  Policy changes, pricing updates, collection schedule            │   │
│  │  Triggered by: Admin UI (factory manager)                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Group Entity (Plantation Model)

```yaml
# Plantation Model: farmer_groups collection
farmer_group:
  group_id: string               # "coop-nyeri-001"
  name: string                   # "Nyeri Highland Cooperative"
  type: enum                     # "cooperative" | "collection_point" | "custom"

  lead_farmer:
    farmer_id: string
    name: string
    phone: string

  members:
    - farmer_id: string
      name: string
      role: enum                 # "member" | "deputy_lead"

  region_id: string
  factory_id: string

  messaging_preferences:
    lead_receives_group_summary: true
    members_receive_individual: true
    broadcast_channel: whatsapp    # WhatsApp groups work better
```

#### Broadcast Configuration

```yaml
# notification-service/config/broadcast.yaml
broadcasts:
  regional_alert:
    trigger_sources:
      - event: "knowledge.outbreak_detected"
      - event: "weather.severe_warning"
    audience: region_id
    template_sw: |
      TAHADHARI {REGION_NAME}:
      {ALERT_MESSAGE}
      Ushauri: {RECOMMENDATION}
    channels: [sms, whatsapp]
    throttle:
      max_per_day: 3              # Prevent alert fatigue
      cooldown_minutes: 60

  factory_announcement:
    trigger_sources:
      - manual: admin_ui
    audience: factory_id
    approval_required: true       # Factory manager must approve
    template_sw: |
      TAARIFA: {FACTORY_NAME}
      {ANNOUNCEMENT_BODY}
    channels: [sms]

  cooperative_summary:
    trigger_sources:
      - schedule: "0 7 * * 1"     # Weekly Monday 7 AM
    audience: group_id
    recipient: lead_farmer_only
    template_sw: |
      KIONGOZI - Wiki hii:
      Wakulima {AFFECTED_COUNT} wana matatizo
      Masuala makuu: {TOP_ISSUES}
      Jibu DETAILS kupata orodha kamili.
```

#### Lead Farmer Cascade

When a lead farmer receives a group summary, they can request details and confirm relay:

```yaml
# notification-service/config/lead-farmer-cascade.yaml
lead_farmer_cascade:
  summary_message:
    template_sw: |
      {LEAD_NAME}, wiki hii wakulima {COUNT} wana matatizo:
      {BRIEF_LIST}
      Jibu DETAILS kupata orodha kamili.

  details_response:
    trigger: keyword "DETAILS"
    template_sw: |
      ORODHA KAMILI:
      {FULL_LIST_WITH_PHONES_AND_ACTIONS}

  action_tracking:
    lead_confirms_relay: true     # "NIMEWAAMBIA" → log confirmation
    track_member_outcomes: true   # Monitor if issues improve
    confirmation_template_sw: |
      Asante! Tumepokea. Tutafuatilia maendeleo.
```

#### Cost Optimization via Grouping

| Scenario | Without Groups | With Groups | Savings |
|----------|----------------|-------------|---------|
| Regional weather alert (10,000 farmers) | 10,000 SMS | 10,000 SMS | 0% (critical info) |
| Cooperative summary (20 farmers/group, 1,000 groups) | 20,000 SMS | 1,000 SMS | **95%** |
| Factory announcement (50,000 farmers) | 50,000 SMS | 50,000 SMS | 0% (critical info) |

**Key insight:** Lead farmer summaries reduce weekly message volume by 95% for non-critical updates while maintaining information flow through cooperative structures.

#### Implementation Priority

| Feature | Priority | Rationale |
|---------|----------|-----------|
| Regional broadcasts | MVP | Weather/disease alerts critical for crop protection |
| Lead farmer summaries | MVP | Cost savings, leverages existing cooperative structure |
| Factory announcements | Post-MVP | Less frequent, requires admin UI |
| WhatsApp groups integration | Future | Requires WhatsApp Business API group features |

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | PRESCRIBE only | Clean separation from diagnosis |
| **Agent Architecture** | Two-agent (Selector + Generator) | Separation of routing and content generation |
| **Schedule** | Weekly | Matches farmer planning cycles |
| **Output Format** | Dual (detailed + simplified) | Serves both experts and farmers |
| **Translation** | In-agent workflow | LLM naturally handles translation |
| **Multiple Analyses** | Combined into one plan | One coherent weekly recommendation |
| **MCP Server** | No | Final output, no AI agent consumers |
| **Message Delivery** | Infrastructure layer | Separation of concerns |

### Testing Strategy

| Test Type | Focus |
|-----------|-------|
| **Selector Agent** | Correct weekly aggregation, no duplicates |
| **Plan Generation** | Quality of recommendations, prioritization |
| **Translation Accuracy** | Language correctness, cultural appropriateness |
| **Simplification** | Readability for farmers, SMS length compliance |
| **Empty State** | Correct handling of no-analysis weeks |
| **Multi-Analysis** | Coherent combination of diverse diagnoses |

---

## Market Analysis Model Architecture

> **STATUS: PENDING DISCUSSION** - Details to be confirmed with colleague. Documenting known information below.

### Overview

The Market Analysis Model connects internal plantation data with external market intelligence to create Buyer Profiles and market insights.

**Core Responsibility:** Analyze market conditions, buyer requirements, and match factory output to market opportunities.

**Does NOT:** [TBD]

### Known Data Sources

| Source | Type | Purpose |
|--------|------|---------|
| Plantation Model | Internal | Factory summaries, quality levels, farmer performance |
| Starfish Network API | External | Supply chain traceability, buyer data, market standards |

### Starfish Network Integration

[Starfish Network](https://www.starfish-network.com/) is a supply chain data exchange platform:
- **Protocol:** GS1 standardized traceability data
- **Purpose:** Multi-party data sharing across agricultural supply chains
- **Data Types:** Buyer requirements, compliance standards, trading partner profiles

### Known Outputs

- **Buyer Profiles** → Written to Plantation Model via internal API

### Open Questions (To Discuss)

1. **Trigger Mechanism:** Scheduled batch? Event-driven? On-demand?
2. **Additional Outputs:** Price forecasts? Market trends? Quality-to-price mapping?
3. **MCP Server:** Does it expose one for AI agent queries?
4. **Agent Pattern:** Single agent or two-agent pattern?
5. **Update Frequency:** How often are buyer profiles refreshed?
6. **Starfish API Scope:** Which specific endpoints/data types are consumed?

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     MARKET ANALYSIS MODEL                                │
│                     (Architecture TBD)                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUTS:                                                                │
│  ┌─────────────────┐    ┌─────────────────────────────────────────┐    │
│  │ Plantation MCP  │    │ Starfish Network API                    │    │
│  │ (factory data)  │    │ (traceability, buyer data, GS1 format)  │    │
│  └────────┬────────┘    └──────────────────┬──────────────────────┘    │
│           │                                │                            │
│           └────────────────┬───────────────┘                            │
│                            ▼                                            │
│           ┌────────────────────────────────┐                            │
│           │     MARKET ANALYSIS AGENT      │                            │
│           │     (Pattern TBD)              │                            │
│           └────────────────┬───────────────┘                            │
│                            │                                            │
│                            ▼                                            │
│           ┌────────────────────────────────┐                            │
│           │        OUTPUTS                 │                            │
│           │  • Buyer Profiles → Plantation │                            │
│           │  • [Other outputs TBD]         │                            │
│           └────────────────────────────────┘                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## AI Model Architecture

### Overview

The AI Model is the **6th Domain Model** - the centralized intelligence layer for the Farmer Power Cloud Platform. Unlike the previous design where AI agents were embedded in each domain model, all AI logic is centralized here.

**Core Responsibility:** Execute AI workflows (extraction, diagnosis, content generation) on behalf of other domain models.

**Does NOT:** Own business data, make business decisions about when to run, or store results persistently.

### Architecture Diagram

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

### Communication Pattern

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

### Agent Types

Three agent types are implemented in code, each with a specific workflow pattern:

#### Extractor Type

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

#### Explorer Type

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

#### Generator Type

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

### Agent Configuration Schema

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

### Agent Type Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Number of types** | 3 (Extractor, Explorer, Generator) | Covers fundamental AI patterns; add more when needed |
| **Type location** | In code | Workflow logic requires conditionals, loops, error handling |
| **Instance location** | YAML in Git | Declarative, version controlled, PR reviewable |
| **Inheritance** | Flat (Type → Instance only) | Avoids complexity; use parameters for variations |
| **Prompts** | Separate .md files | Better diffs, easier review, can be long |

### Triggering

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

### LLM Gateway

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

### Tiered Vision Processing (Cost Optimization)

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

### RAG Engine

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

### Prompt Management

**Decision:** Prompts are externalized to MongoDB, enabling hot-reload and A/B testing without redeployment.

**Problem:** Storing prompts in source code requires rebuild and redeploy for every prompt change:
- Slow iteration during prompt tuning
- Risky deployments for text-only changes
- Cannot A/B test prompts in production
- Cannot rollback prompts independently of code

**Solution:** Externalized prompt management with the same versioning pattern as RAG knowledge.

#### Prompt Storage Architecture

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

#### Prompt Document Schema

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

#### Prompt Lifecycle

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

#### Runtime Prompt Loading

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

#### Prompt A/B Testing

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

#### Key Benefits

| Benefit | Description |
|---------|-------------|
| **No Redeploy** | Prompt changes take effect within cache TTL (5 min) |
| **Safe Rollback** | Instant rollback to any previous version |
| **A/B Testing** | Test prompt changes on subset of traffic |
| **Audit Trail** | Full history of all prompt versions |
| **Git Integration** | Prompts still version-controlled in Git |

### RAG Knowledge Versioning

To prevent knowledge updates from degrading prompt effectiveness, the RAG system uses versioned namespaces with A/B testing.

#### Document Lifecycle

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

#### Document Schema

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

#### A/B Testing Configuration

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

#### Rollback Procedure

| Trigger | Action | Duration |
|---------|--------|----------|
| **Manual** | Admin initiates rollback via UI | Immediate |
| **Auto** | Metrics degrade >10% during A/B | Immediate |
| **Mechanism** | Switch active_namespace pointer | <1 second |
| **Retention** | Keep last 5 versions for rollback | 90 days |

#### Version Lifecycle Flow

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

### Configuration Strategy

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

### Observability

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

### Key Decisions

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

### Testing Strategy

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

### Developer Guide

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

## Infrastructure Decisions

### MCP Server Scaling

**Decision:** MCP servers are stateless and deployed as separate Kubernetes pods, enabling horizontal scaling via HPA.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MCP SERVER SCALING (Kubernetes)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  AI MODEL (MCP Client)                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  MCP Client calls → Kubernetes Service (load balanced)           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│          ┌───────────────┼───────────────┐                              │
│          ▼               ▼               ▼                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                    │
│  │ Collection   │ │ Plantation   │ │ Knowledge    │                    │
│  │ MCP Service  │ │ MCP Service  │ │ MCP Service  │                    │
│  │ (ClusterIP)  │ │ (ClusterIP)  │ │ (ClusterIP)  │                    │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘                    │
│         │                │                │                             │
│    ┌────┴────┐      ┌────┴────┐      ┌────┴────┐                       │
│    ▼    ▼    ▼      ▼    ▼    ▼      ▼    ▼    ▼                       │
│  ┌───┐┌───┐┌───┐  ┌───┐┌───┐┌───┐  ┌───┐┌───┐┌───┐                    │
│  │Pod││Pod││Pod│  │Pod││Pod││Pod│  │Pod││Pod││Pod│                    │
│  └───┘└───┘└───┘  └───┘└───┘└───┘  └───┘└───┘└───┘                    │
│         │                │                │                             │
│         ▼                ▼                ▼                             │
│      MongoDB          MongoDB          MongoDB                          │
│      (Read            (Read            (Read                            │
│       Replicas)        Replicas)        Replicas)                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Scaling Configuration:**

```yaml
# kubernetes/mcp-servers/collection-mcp-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: collection-mcp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: collection-mcp-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: mcp_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
```

**Key Points:**
- All state in MongoDB (read replicas for queries)
- Kubernetes Service provides load balancing
- HPA scales based on CPU and request rate
- Each MCP server (Collection, Plantation, Knowledge) scales independently

### External API Resiliency (DAPR Circuit Breaker)

**Decision:** Use DAPR's built-in resiliency policies for external API calls (Starfish Network, Weather APIs, Google Elevation API).

```yaml
# dapr/components/resiliency.yaml
apiVersion: dapr.io/v1alpha1
kind: Resiliency
metadata:
  name: external-api-resiliency
spec:
  policies:
    # ═══════════════════════════════════════════════════════════════════════
    # RETRY POLICIES
    # ═══════════════════════════════════════════════════════════════════════
    retries:
      default-retry:
        policy: constant
        maxRetries: 3
        duration: 1s

      starfish-retry:
        policy: exponential
        maxRetries: 5
        maxInterval: 30s

      weather-retry:
        policy: constant
        maxRetries: 3
        duration: 2s

    # ═══════════════════════════════════════════════════════════════════════
    # CIRCUIT BREAKER POLICIES
    # ═══════════════════════════════════════════════════════════════════════
    circuitBreakers:
      starfish-cb:
        maxRequests: 5              # Max requests when half-open
        interval: 30s               # Time window for counting failures
        timeout: 60s                # Time circuit stays open
        trip: consecutiveFailures >= 3

      weather-cb:
        maxRequests: 3
        interval: 60s
        timeout: 120s
        trip: consecutiveFailures >= 5

    # ═══════════════════════════════════════════════════════════════════════
    # TIMEOUT POLICIES
    # ═══════════════════════════════════════════════════════════════════════
    timeouts:
      starfish-timeout: 10s
      weather-timeout: 5s
      elevation-timeout: 3s

  # ═══════════════════════════════════════════════════════════════════════════
  # TARGET CONFIGURATION
  # ═══════════════════════════════════════════════════════════════════════════
  targets:
    components:
      starfish-api:
        outbound:
          retry: starfish-retry
          circuitBreaker: starfish-cb
          timeout: starfish-timeout

      weather-api:
        outbound:
          retry: weather-retry
          circuitBreaker: weather-cb
          timeout: weather-timeout

      google-elevation-api:
        outbound:
          retry: default-retry
          timeout: elevation-timeout
```

**Circuit Breaker Behavior:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CIRCUIT BREAKER STATES                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   CLOSED (Normal)                                                       │
│   ┌─────────────┐                                                       │
│   │ Requests    │──────▶ External API                                   │
│   │ pass through│                                                       │
│   └──────┬──────┘                                                       │
│          │ 3 consecutive failures                                       │
│          ▼                                                              │
│   OPEN (Protecting)                                                     │
│   ┌─────────────┐                                                       │
│   │ Requests    │──────▶ Fail fast (no API call)                        │
│   │ rejected    │        Return cached/default if available             │
│   └──────┬──────┘                                                       │
│          │ After 60s timeout                                            │
│          ▼                                                              │
│   HALF-OPEN (Testing)                                                   │
│   ┌─────────────┐                                                       │
│   │ Limited     │──────▶ External API (max 5 requests)                  │
│   │ requests    │                                                       │
│   └──────┬──────┘                                                       │
│          │                                                              │
│    ┌─────┴─────┐                                                        │
│    │           │                                                        │
│ Success     Failure                                                     │
│    │           │                                                        │
│    ▼           ▼                                                        │
│  CLOSED     OPEN                                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Benefits:**
- Configuration-driven (no code changes)
- Prevents cascading failures when external APIs are down
- Automatic recovery when services become healthy
- Consistent resilience pattern across all external calls

### Kubernetes Deployment Architecture

**Decision:** Single namespace per environment on a shared Kubernetes cluster, with Backend-for-Frontend (BFF) pattern for external API exposure.

#### Multi-Environment Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SINGLE KUBERNETES CLUSTER - MULTI-ENVIRONMENT            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Namespace: farmer-power-qa                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  All services for QA environment                                    │   │
│  │  ResourceQuota: cpu=4, memory=8Gi                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Namespace: farmer-power-preprod                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  All services for Pre-Production environment                        │   │
│  │  ResourceQuota: cpu=8, memory=16Gi                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Namespace: farmer-power-prod                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  All services for Production environment                            │   │
│  │  ResourceQuota: cpu=32, memory=64Gi (or no limit)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Namespace: dapr-system (shared across all environments)                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Dapr Control Plane (operator, placement, sentry)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- Single cluster reduces infrastructure cost
- Namespace isolation via RBAC, NetworkPolicies, ResourceQuotas
- QA/PreProd can share node pools, Prod uses dedicated nodes
- Simple deployment pipeline per environment

#### Namespace Service Organization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NAMESPACE: farmer-power-{env}                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────── EDGE LAYER ──────────────────────────┐           │
│  │                                                              │           │
│  │  ┌──────────────────────────────────────────────────────┐   │           │
│  │  │           INGRESS (NGINX / Azure App Gateway)         │   │           │
│  │  │  api.farmerpower.io → bff-service                    │   │           │
│  │  │  webhooks.farmerpower.io → inbound-webhook-svc       │   │           │
│  │  └──────────────────────────────────────────────────────┘   │           │
│  │                          │                                   │           │
│  │                          ▼                                   │           │
│  │  ┌──────────────────────────────────────────────────────┐   │           │
│  │  │              BFF (Backend For Frontend)               │   │           │
│  │  │  ┌────────────────────────────────────────────────┐  │   │           │
│  │  │  │  FastAPI + WebSocket                           │  │   │           │
│  │  │  │  - REST API endpoints for React UI             │  │   │           │
│  │  │  │  - WebSocket for real-time updates             │  │   │           │
│  │  │  │  - OAuth2/JWT authentication                   │  │   │           │
│  │  │  │  - Request aggregation & transformation        │  │   │           │
│  │  │  │  + Dapr sidecar (gRPC to internal services)    │  │   │           │
│  │  │  └────────────────────────────────────────────────┘  │   │           │
│  │  │  replicas: 3 (HPA: 2-10)                             │   │           │
│  │  └──────────────────────────────────────────────────────┘   │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                          │                                                  │
│                          │ gRPC via Dapr                                    │
│                          ▼                                                  │
│  ┌─────────────── BUSINESS MODELS (gRPC + Dapr) ───────────────┐           │
│  │                                                              │           │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │           │
│  │  │ collection-  │ │ knowledge-   │ │ plantation-  │        │           │
│  │  │ model        │ │ model        │ │ model        │        │           │
│  │  │ + dapr       │ │ + dapr       │ │ + dapr       │        │           │
│  │  │ gRPC :50051  │ │ gRPC :50051  │ │ gRPC :50051  │        │           │
│  │  └──────────────┘ └──────────────┘ └──────────────┘        │           │
│  │        │                │                │                  │           │
│  │        └────────────────┼────────────────┘                  │           │
│  │                         │ gRPC via Dapr                     │           │
│  │                         ▼                                   │           │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │           │
│  │  │ action-plan- │ │ market-      │ │ ai-model     │        │           │
│  │  │ model        │ │ analysis     │ │ (LLM gateway)│        │           │
│  │  │ + dapr       │ │ + dapr       │ │ + dapr       │        │           │
│  │  │ gRPC :50051  │ │ gRPC :50051  │ │ gRPC :50051  │        │           │
│  │  └──────────────┘ └──────────────┘ └──────────────┘        │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                          │                                                  │
│                          │ gRPC via Dapr                                    │
│                          ▼                                                  │
│  ┌─────────────── MCP SERVERS (gRPC, HPA-enabled) ─────────────┐           │
│  │                                                              │           │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │           │
│  │  │ collection-  │ │ plantation-  │ │ knowledge-   │        │           │
│  │  │ mcp          │ │ mcp          │ │ mcp          │        │           │
│  │  │ HPA: 2-10    │ │ HPA: 2-10    │ │ HPA: 2-10    │        │           │
│  │  │ gRPC :50051  │ │ gRPC :50051  │ │ gRPC :50051  │        │           │
│  │  └──────────────┘ └──────────────┘ └──────────────┘        │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                                                                             │
│  ┌─────────────── MESSAGING (gRPC + Dapr) ─────────────────────┐           │
│  │                                                              │           │
│  │  ┌──────────────┐ ┌──────────────┐                         │           │
│  │  │ notification-│ │ inbound-     │ ← External webhook      │           │
│  │  │ service      │ │ webhook      │   (Africa's Talking)    │           │
│  │  │ + dapr       │ │ + dapr       │                         │           │
│  │  └──────────────┘ └──────────────┘                         │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Communication Protocol Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COMMUNICATION PROTOCOLS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  React UI                                                                   │
│     │                                                                       │
│     │  HTTPS (REST API + WebSocket)                                        │
│     ▼                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  BFF (FastAPI)                                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │   │
│  │  │ REST Endpoints  │  │ WebSocket Hub   │  │ Auth Middleware │     │   │
│  │  │ /api/v1/...     │  │ /ws/events      │  │ JWT Validation  │     │   │
│  │  └────────┬────────┘  └────────┬────────┘  └─────────────────┘     │   │
│  │           │                    │                                    │   │
│  │           └─────────┬──────────┘                                    │   │
│  │                     ▼                                               │   │
│  │           ┌─────────────────────┐                                   │   │
│  │           │ Dapr Sidecar        │                                   │   │
│  │           │ (Service Invocation)│                                   │   │
│  │           └─────────┬───────────┘                                   │   │
│  └─────────────────────│───────────────────────────────────────────────┘   │
│                        │                                                    │
│                        │ gRPC (via Dapr service invocation)                │
│                        ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Internal Services (all with Dapr sidecars)                         │   │
│  │                                                                      │   │
│  │  plantation-model ◄──gRPC──► collection-model ◄──gRPC──► ai-model   │   │
│  │         │                          │                        │        │   │
│  │         └──────────gRPC────────────┼────────────────────────┘        │   │
│  │                                    │                                 │   │
│  │                              knowledge-model                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Protocol Summary:**

| Layer | Protocol | Reason |
|-------|----------|--------|
| UI → BFF | REST + WebSocket | Browser-compatible, real-time updates |
| BFF → Services | gRPC via Dapr | Efficient binary protocol, type-safe |
| Service → Service | gRPC via Dapr | Low latency, streaming support |
| Service → MCP | gRPC | LLM tool invocation |

#### BFF Responsibilities

| Function | Description |
|----------|-------------|
| **Authentication** | Validate JWT tokens, enforce RBAC per endpoint |
| **API Aggregation** | Combine multiple gRPC calls into single REST response |
| **Protocol Translation** | REST/WebSocket ↔ gRPC conversion |
| **Real-time Events** | Push updates to UI via WebSocket (quality events, alerts) |
| **Rate Limiting** | Protect internal services from abuse |
| **Request Validation** | Validate input schemas before forwarding |

#### Deployment Manifest Summary

| Service | Type | Protocol Exposed | Replicas | HPA |
|---------|------|------------------|----------|-----|
| bff | Deployment | REST + WebSocket (external) | 3 | 2-10 |
| collection-model | Deployment | gRPC (internal) | 2 | No |
| knowledge-model | Deployment | gRPC (internal) | 2 | No |
| plantation-model | Deployment | gRPC (internal) | 2 | No |
| action-plan-model | Deployment | gRPC (internal) | 2 | No |
| market-analysis | Deployment | gRPC (internal) | 1 | No |
| ai-model | Deployment | gRPC (internal) | 3 | No |
| collection-mcp | Deployment | gRPC (internal) | 2 | 2-10 |
| plantation-mcp | Deployment | gRPC (internal) | 2 | 2-10 |
| knowledge-mcp | Deployment | gRPC (internal) | 2 | 2-10 |
| notification-service | Deployment | gRPC (internal) | 2 | No |
| inbound-webhook | Deployment | HTTPS (external) | 2 | No |

#### External Managed Services

| Service | Provider | Connection |
|---------|----------|------------|
| MongoDB | Atlas or Azure CosmosDB | Connection string in Secret |
| Pinecone | Pinecone Cloud | API key in Secret |
| Azure OpenAI | Azure | Endpoint + key in Secret |
| Azure Blob Storage | Azure | Connection string in Secret |
| Africa's Talking | AT | API credentials in Secret |

#### Environment Configuration

```yaml
# configmap-prod.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: farmer-power-prod
data:
  ENVIRONMENT: "production"
  MONGODB_DATABASE: "farmerpower_prod"
  PINECONE_INDEX: "knowledge-prod"
  LOG_LEVEL: "info"
  ENABLE_SMS: "true"
  GRPC_PORT: "50051"

---
# configmap-qa.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: farmer-power-qa
data:
  ENVIRONMENT: "qa"
  MONGODB_DATABASE: "farmerpower_qa"
  PINECONE_INDEX: "knowledge-qa"
  LOG_LEVEL: "debug"
  ENABLE_SMS: "false"  # Mock SMS in QA
  GRPC_PORT: "50051"
```

#### Dapr Component Configuration (Per Namespace)

```yaml
# dapr/components/statestore.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: statestore
  namespace: farmer-power-prod
spec:
  type: state.mongodb
  version: v1
  metadata:
    - name: host
      secretKeyRef:
        name: mongodb-connection
        key: host
    - name: databaseName
      value: "farmerpower_prod"

---
# dapr/components/pubsub.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
  namespace: farmer-power-prod
spec:
  type: pubsub.azure.servicebus
  version: v1
  metadata:
    - name: connectionString
      secretKeyRef:
        name: servicebus-connection
        key: connectionString
```

---

## Analytics Architecture

### Cross-Model Data Access Strategy

The platform uses different strategies for different consumers, respecting model boundaries while enabling efficient data access.

#### Consumer-Specific Strategies

| Consumer | Strategy | Rationale |
|----------|----------|-----------|
| **AI Agents** | MCP aggregation | Single farmer queries, parallel calls, production-optimized |
| **Admin Dashboard** | Event-driven materialized views | Pre-joined data, fast reads, uses existing Dapr |
| **Future Analytics** | Migrate to ClickHouse when needed | Don't over-engineer MVP |

#### AI Agent Queries (Production)

AI agents query for **one farmer at a time** using parallel MCP calls:

```
Action Plan Generator needs farmer context:
  → Plantation MCP: get_farmer_context("WM-4521")      ─┐
  → Knowledge MCP: get_farmer_analyses("WM-4521")      ─┼─ Parallel
  → Collection MCP: get_farmer_documents("WM-4521")    ─┘

3 parallel MCP calls, ~100ms total, no joins needed
```

**Why this works:** AI agents have predictable query patterns (farmer_id → get everything about this farmer). No complex cross-model joins needed.

#### Admin Dashboard (Analytics Read Model)

For dashboards and reports requiring cross-model data, use event-driven materialized views via Dapr pub/sub:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ANALYTICS READ MODEL                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Dapr Subscriptions:                                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │ collection.     │  │ knowledge.      │  │ action_plan.    │         │
│  │ document_stored │  │ diagnosis_      │  │ created         │         │
│  │                 │  │ complete        │  │                 │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
│           │                    │                    │                   │
│           └────────────────────┼────────────────────┘                   │
│                                ▼                                        │
│           ┌─────────────────────────────────────┐                       │
│           │      REPORTING SERVICE              │                       │
│           │                                     │                       │
│           │  • Subscribes to domain events      │                       │
│           │  • Updates denormalized views       │                       │
│           │  • Pre-joins farmer + events +      │                       │
│           │    diagnoses + action plans         │                       │
│           │  • Aggregates by factory, region    │                       │
│           └─────────────────────────────────────┘                       │
│                                │                                        │
│                                ▼                                        │
│           ┌─────────────────────────────────────┐                       │
│           │   farmer_dashboard_view (MongoDB)   │                       │
│           │                                     │                       │
│           │   {                                 │                       │
│           │     farmer_id: "WM-4521",           │                       │
│           │     region: "nyeri-highland",       │                       │
│           │     factory: "F001",                │                       │
│           │     recent_deliveries: [...],       │                       │
│           │     recent_diagnoses: [...],        │                       │
│           │     action_plans: [...],            │                       │
│           │     performance_30d: {...},         │                       │
│           │     last_updated: "2025-12-16T10:00:00Z"                    │
│           │   }                                 │                       │
│           └─────────────────────────────────────┘                       │
│                                │                                        │
│                                ▼                                        │
│           ┌─────────────────────────────────────┐                       │
│           │         ADMIN DASHBOARD             │                       │
│           │   Fast queries, no joins needed     │                       │
│           └─────────────────────────────────────┘                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Materialized View Schema

```yaml
# MongoDB: farmer_dashboard_view collection
farmer_dashboard_view:
  _id: string                    # farmer_id
  farmer_id: string
  name: string
  region_id: string
  factory_id: string

  # Denormalized from Collection Model
  recent_deliveries:
    - date: datetime
      grade: string
      quality_score: number
      issues: string[]
  delivery_count_30d: number

  # Denormalized from Knowledge Model
  recent_diagnoses:
    - date: datetime
      type: string
      condition: string
      severity: string
      confidence: number
  active_issues_count: number

  # Denormalized from Action Plan Model
  recent_action_plans:
    - week: string
      priority_actions: number
      delivery_status: string

  # Aggregated metrics
  performance_30d:
    avg_grade: number
    improvement_trend: string    # "improving" | "stable" | "declining"
    grade_distribution: object

  last_updated: datetime
```

#### Why NOT Other Options

| Option | Why Not |
|--------|---------|
| **Shared MongoDB** | Breaks model isolation. Schema changes in one model could break others. MongoDB `$lookup` is slow at scale. |
| **Dedicated Analytics DB (ClickHouse)** | Overkill for MVP. Not doing OLAP queries yet. Can migrate later if needed. |
| **MCP for dashboards** | N+1 query problem for lists. Fine for single-farmer views, slow for "all farmers in region" reports. |

---

## CQRS Architecture Pattern

### Overview

The platform implements an **implicit CQRS (Command Query Responsibility Segregation)** pattern. Rather than introducing explicit CQRS infrastructure, we leverage existing MongoDB capabilities and event-driven architecture to separate read and write concerns.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CQRS IMPLEMENTATION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  COMMAND SIDE (Writes)                 QUERY SIDE (Reads)                   │
│  ┌─────────────────────┐               ┌─────────────────────┐              │
│  │  Ingestion APIs     │               │   MCP Servers       │              │
│  │  - /api/v1/ingest/* │               │   (stateless)       │              │
│  │  - Event processors │               │   - get_farmer_*    │              │
│  │  - Action plan gen  │               │   - search_*        │              │
│  └──────────┬──────────┘               └──────────┬──────────┘              │
│             │                                     │                         │
│             ▼                                     ▼                         │
│  ┌─────────────────────┐               ┌─────────────────────┐              │
│  │   MongoDB PRIMARY   │  ─────────▶   │   MongoDB READ      │              │
│  │                     │  replication  │   REPLICAS          │              │
│  │  Handles all writes │               │   Handles all reads │              │
│  └─────────────────────┘               └─────────────────────┘              │
│             │                                     ▲                         │
│             │ events                              │                         │
│             ▼                                     │                         │
│  ┌─────────────────────┐               ┌─────────────────────┐              │
│  │   Dapr Pub/Sub      │  ─────────▶   │   Materialized      │              │
│  │   Event Bus         │               │   Views             │              │
│  │                     │               │   (farmer_dashboard │              │
│  │  - document_stored  │               │    _view, etc.)     │              │
│  │  - diagnosis_done   │               │                     │              │
│  │  - action_plan_sent │               │   Optimized for     │              │
│  └─────────────────────┘               │   specific queries  │              │
│                                        └─────────────────────┘              │
│                                                   │                         │
│                                                   ▼                         │
│                                        ┌─────────────────────┐              │
│                                        │  Admin Dashboard    │              │
│                                        │  Reporting APIs     │              │
│                                        └─────────────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Read/Write Separation Layers

| Layer | Write Path | Read Path |
|-------|------------|-----------|
| **API Gateway** | Ingestion endpoints (`POST /ingest/*`) | MCP Server methods (`get_*`, `search_*`) |
| **Database** | MongoDB Primary (single writer) | MongoDB Read Replicas (multiple readers) |
| **Analytics** | Domain events via Dapr | Materialized views (pre-computed) |
| **Connection Strings** | `mongodb://primary:27017` | `mongodb://replica1,replica2:27017?readPreference=secondary` |

### MongoDB Read Replica Configuration

```yaml
# Each model's read path configuration
mongodb_read_config:
  readPreference: secondary        # Route reads to replicas
  readPreferenceTags:
    - region: same-az              # Prefer same availability zone
  maxStalenessSeconds: 90          # Accept up to 90s staleness for reads

# Write path always uses primary
mongodb_write_config:
  writeConcern:
    w: majority                    # Wait for majority acknowledgment
    j: true                        # Journal write before acknowledging
```

### Query Patterns by Consumer

| Consumer | Read Path | Write Path | Consistency |
|----------|-----------|------------|-------------|
| **AI Agents (MCP)** | Read replicas | N/A (read-only) | Eventually consistent (90s max) |
| **Admin Dashboard** | Materialized views | N/A (read-only) | Event-driven (~1s delay) |
| **Ingestion APIs** | N/A | Primary only | Strongly consistent |
| **Action Plan Generator** | Read replicas | Primary (plans) | Read: eventual, Write: strong |

### Why Implicit CQRS (Not Explicit)

| Explicit CQRS | Implicit CQRS (Our Approach) |
|---------------|------------------------------|
| Separate read/write databases | MongoDB replicas (same data, different instances) |
| Event sourcing for write model | Standard document updates + Dapr events |
| Dedicated projection services | Lightweight event handlers update materialized views |
| Complex eventual consistency | Simple replication lag (< 100ms typical) |
| High operational overhead | Minimal ops - MongoDB handles replication |

**Our approach gives us:**
- ✅ Read/write load separation
- ✅ Independent scaling of reads vs writes
- ✅ Eventual consistency where acceptable
- ✅ Strong consistency where required (primary reads when needed)
- ✅ No additional infrastructure complexity

### When to Evolve to Explicit CQRS

Consider formal CQRS migration if:

| Trigger | Threshold | Response |
|---------|-----------|----------|
| Read replica lag exceeds SLA | > 500ms consistently | Add more replicas or consider ClickHouse |
| Complex read models needed | > 5 materialized views | Consider dedicated projection service |
| Write throughput bottleneck | > 10,000 writes/sec | Consider event sourcing with write-optimized store |
| Cross-region requirements | Multiple continents | Consider geo-distributed CQRS with conflict resolution |

**Current architecture supports:** ~1,000 writes/sec, ~10,000 reads/sec, < 100ms replica lag.

---

## Validated Use Cases

This section documents key use cases traced through the architecture to validate the design.

### Use Case 1: Batch ZIP Upload (Poor Quality Images)

**Scenario:** QC Analyzer at factory detects tea leaves that don't reach minimum quality. Instead of sending images individually over an unstable network, it batches multiple images with a JSON index into a ZIP archive.

**Flow:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BATCH ZIP INGESTION                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  QC ANALYZER (Factory)                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. Collect poor quality images during intake                     │   │
│  │ 2. Create batch ZIP:                                             │   │
│  │    batch_001.zip                                                 │   │
│  │    ├── index.json (metadata for all images)                      │   │
│  │    ├── img_001.jpg                                               │   │
│  │    ├── img_002.jpg                                               │   │
│  │    └── img_003.jpg ...                                           │   │
│  │ 3. Calculate SHA256 checksum                                     │   │
│  │ 4. Upload via resumable protocol (survives network drops)        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  COLLECTION MODEL                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. Receive ZIP via resumable upload endpoint                     │   │
│  │ 2. Verify SHA256 checksum                                        │   │
│  │ 3. Store original ZIP → Blob (quality-archives) for audit        │   │
│  │ 4. Extract and validate index.json                               │   │
│  │ 5. For each image:                                               │   │
│  │    a. Store image → Blob (quality-images)                        │   │
│  │    b. Create document → MongoDB (quality_events)                 │   │
│  │    c. Emit event → DAPR Pub/Sub                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  DAPR PUB/SUB: N events emitted                                         │
│  topic: "collection.poor_quality_detected"                              │
│  { doc_id, farmer_id, factory_id, grade, quality_score, image_url }     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Collection Model Configuration:**

```yaml
source: qc-analyzer-batch
  endpoint: /api/v1/ingest/qc-analyzer/batch
  content_type: application/zip

  upload:
    resumable: true                   # Survives network drops
    checksum:
      algorithm: sha256
      header: X-Checksum-SHA256
    timeout_seconds: 300

  archive:
    format: zip
    index_file: "index.json"
    index_schema: qc-batch-index.json

  processing:
    mode: expand                      # Expand to individual documents
    document_per: image

  storage:
    archive:
      container: quality-archives
      retention_days: 90
    images:
      container: quality-images
      path_template: "{factory_id}/{date}/{batch_id}/{filename}"
    documents:
      mongo_collection: quality_events

  events:
    per_document:
      topic: "collection.poor_quality_detected"
```

**Resumable Upload API:**

```yaml
endpoints:
  # Initialize upload
  POST /api/v1/ingest/qc-analyzer/batch/init
    → Returns: upload_id

  # Upload chunk (resume from any point)
  PATCH /api/v1/ingest/qc-analyzer/batch/{upload_id}
    Content-Range: bytes {start}-{end}/{total}

  # Check progress (for resume after disconnect)
  HEAD /api/v1/ingest/qc-analyzer/batch/{upload_id}
    → Returns: Upload-Offset header

  # Complete upload
  POST /api/v1/ingest/qc-analyzer/batch/{upload_id}/complete
    → Triggers processing
```

---

### Use Case 2: Image + Metadata Diagnosis

**Scenario:** Poor quality images need to be analyzed to diagnose why they failed quality control. The AI Model analyzes both the image (visual) and metadata (grade, score, farmer history) to produce a comprehensive diagnosis.

**Flow:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DIAGNOSIS FLOW                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  EVENT: "collection.poor_quality_detected"                              │
│  { doc_id: "doc-001", farmer_id: "WM-4521", grade: "D", image_url }     │
│                          │                                              │
│                          ▼                                              │
│  AI MODEL - disease-diagnosis agent (Explorer/LangGraph)                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  1. FETCH DATA (via MCP)                                         │   │
│  │     ┌─────────────────────────────────────────────────────────┐ │   │
│  │     │ Collection MCP:                                          │ │   │
│  │     │ • get_document(doc_id) → metadata, quality_issues        │ │   │
│  │     │ • get_image_base64(image_url) → image for vision LLM     │ │   │
│  │     │ • get_farmer_documents(farmer_id, 30d) → history         │ │   │
│  │     │                                                          │ │   │
│  │     │ Plantation MCP:                                          │ │   │
│  │     │ • get_farmer(farmer_id) → region, farm_size              │ │   │
│  │     │ • get_farmer_summary(farmer_id) → trends, past issues    │ │   │
│  │     └─────────────────────────────────────────────────────────┘ │   │
│  │                                                                  │   │
│  │  2. RAG QUERY (Pinecone)                                         │   │
│  │     Query: "tea leaf disease symptoms {grade} {quality_issues}"  │   │
│  │     Returns: Expert knowledge about diseases, treatments         │   │
│  │                                                                  │   │
│  │  3. VISION LLM ANALYSIS (Claude Sonnet)                          │   │
│  │     ┌─────────────────────────────────────────────────────────┐ │   │
│  │     │ Input:                                                   │ │   │
│  │     │ • [IMAGE] - tea leaf photo                               │ │   │
│  │     │ • Metadata: grade D, score 35, moisture_excess           │ │   │
│  │     │ • Farmer: Nyeri region, declining trend, 2 past fungal   │ │   │
│  │     │ • RAG: Disease symptoms, regional patterns               │ │   │
│  │     │                                                          │ │   │
│  │     │ Output:                                                  │ │   │
│  │     │ • condition: "fungal_infection"                          │ │   │
│  │     │ • sub_type: "cercospora_leaf_spot"                       │ │   │
│  │     │ • confidence: 0.87                                       │ │   │
│  │     │ • severity: "high"                                       │ │   │
│  │     │ • visual_evidence: ["brown spots", "yellow margins"]     │ │   │
│  │     │ • metadata_evidence: ["grade D aligns with fungal..."]   │ │   │
│  │     │ • recommendations: ["copper fungicide within 48h"]       │ │   │
│  │     └─────────────────────────────────────────────────────────┘ │   │
│  │                                                                  │   │
│  │  4. CONFIDENCE CHECK                                             │   │
│  │     confidence >= 0.7 → Output                                   │   │
│  │     confidence < 0.7 → Retry with more context (max 3x)         │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  EVENT: "ai.diagnosis.complete"                                         │
│  { doc_id, farmer_id, diagnosis: { condition, confidence, ... } }       │
│                          │                                              │
│                          ▼                                              │
│  KNOWLEDGE MODEL                                                        │
│  Stores diagnosis in Analysis DB (MongoDB)                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Agent Configuration:**

```yaml
agent:
  id: "disease-diagnosis"
  type: explorer                     # LangGraph

  input:
    event: "collection.poor_quality_detected"

  mcp_sources:
    - server: collection
      tools: [get_document, get_image_base64, get_farmer_documents]
    - server: plantation
      tools: [get_farmer, get_farmer_summary]

  llm:
    task_type: "diagnosis"
    model_override: "anthropic/claude-3-5-sonnet"  # Vision capable
    vision:
      enabled: true
    temperature: 0.3

  rag:
    enabled: true
    knowledge_domains: [plant_diseases, tea_cultivation, regional_patterns]
    top_k: 5

  workflow:
    max_iterations: 3
    confidence_threshold: 0.7
```

**Diagnosis Output Schema:**

```yaml
output_schema:
  condition: string           # Primary diagnosis
  sub_type: string            # Specific variant
  confidence: number          # 0.0 to 1.0
  severity: enum              # low, moderate, high, critical
  visual_evidence: string[]   # What was seen in the image
  metadata_evidence: string[] # Insights from grade, score, history
  contributing_factors: string[]
  recommendations: string[]
  urgency: enum               # immediate, within_48h, within_week, routine
```

---

### Use Case 3: Weekly Action Plan Generation

**Scenario:** Every Monday at 6 AM, the system generates personalized action plans for all farmers who had quality diagnoses in the past week. Each plan includes a detailed report (for experts) and a simplified message (for the farmer, in their preferred language).

**Flow:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 WEEKLY ACTION PLAN GENERATION                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: Scheduled Trigger (Monday 6 AM)                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  DAPR Jobs → triggers Action Plan Model                          │   │
│  │  Action Plan Model queries Knowledge MCP:                        │   │
│  │  "Get farmers with diagnoses in past 7 days" → 47 farmers        │   │
│  │                                                                  │   │
│  │  For each farmer, emit event:                                    │   │
│  │  topic: "actionplan.generation.requested"                        │   │
│  │  { farmer_id: "WM-4521", week: "2025-W51" }                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  STEP 2: AI Model - Generator Agent (LangGraph)                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────────┐  │   │
│  │  │ Fetch   │──▶│ Fetch   │──▶│ Priori- │──▶│ Generate Report │  │   │
│  │  │Diagnoses│   │ Context │   │  tize   │   │   (Detailed)    │  │   │
│  │  └─────────┘   └─────────┘   └─────────┘   └────────┬────────┘  │   │
│  │       │             │             │                  │           │   │
│  │  Knowledge     Plantation     By severity           │           │   │
│  │  MCP           MCP            & urgency              │           │   │
│  │  (3 diagnoses) (profile,                             │           │   │
│  │                 pref_lang)                           │           │   │
│  │                                                      ▼           │   │
│  │                                          ┌─────────────────────┐ │   │
│  │                                          │ Generate Farmer Msg │ │   │
│  │                                          │ (Simplified, 3 max  │ │   │
│  │                                          │  actions)           │ │   │
│  │                                          └──────────┬──────────┘ │   │
│  │                                                     │            │   │
│  │                                          ┌──────────▼──────────┐ │   │
│  │                                          │ Translate to        │ │   │
│  │                                          │ pref_lang (Swahili) │ │   │
│  │                                          └──────────┬──────────┘ │   │
│  │                                                     │            │   │
│  │                                          ┌──────────▼──────────┐ │   │
│  │                                          │ Check Length        │ │   │
│  │                                          │ (max 480 chars)     │ │   │
│  │                                          └──────────┬──────────┘ │   │
│  │                                              OK │    │ Too long  │   │
│  │                                                 │    └──▶ Simplify│  │
│  │                                                 ▼         & retry │  │
│  │                                          ┌─────────────────────┐ │   │
│  │                                          │ Output Both Formats │ │   │
│  │                                          └─────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  STEP 3: Result Published                                               │
│  topic: "ai.action_plan.complete"                                       │
│  {                                                                      │
│    farmer_id: "WM-4521",                                                │
│    detailed_report: { format: "markdown", content: "# Weekly..." },     │
│    farmer_message: { language: "sw", content: "Habari...", chars: 215 } │
│  }                                                                      │
│                          │                                              │
│                          ▼                                              │
│  STEP 4: Action Plan Model stores plan                                  │
│  → MongoDB (action_plans collection)                                    │
│  → Emits: "actionplan.ready_for_delivery"                               │
│                          │                                              │
│                          ▼                                              │
│  STEP 5: Notification Service delivers                                  │
│  → Reads pref_channel (SMS/WhatsApp)                                    │
│  → Sends farmer_message to farmer                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Trigger Configuration (Action Plan Model):**

```yaml
triggers:
  - name: weekly-action-plan-generation
    type: schedule
    cron: "0 6 * * 1"              # Monday 6 AM
    workflow: "generate-action-plans"
```

**Generator Agent Configuration:**

```yaml
agent:
  id: "weekly-action-plan"
  type: generator                    # LangGraph

  mcp_sources:
    - server: knowledge
      tools: [get_farmer_analyses]
    - server: plantation
      tools: [get_farmer, get_farmer_summary, get_farmer_context]

  llm:
    task_type: "generation"
    model_override: "anthropic/claude-3-5-sonnet"
    temperature: 0.5

  rag:
    enabled: true
    knowledge_domains: [tea_cultivation, regional_practices, treatment_protocols]

  outputs:
    detailed_report:
      format: markdown
      audience: expert

    farmer_message:
      format: text
      audience: farmer
      localization:
        translate: true
        language_field: "farmer.pref_lang"
        simplification_field: "farmer.literacy_lvl"
      constraints:
        max_characters: 480
        max_actions: 3
```

**Dual Output Example:**

```json
{
  "detailed_report": {
    "format": "markdown",
    "content": "# Weekly Action Plan - WM-4521\n## Week 51, 2025\n\n### Priority Actions\n\n#### 1. Fungal Infection Treatment (HIGH)\n- Diagnosis: Cercospora leaf spot\n- Confidence: 87%\n- Action: Apply copper-based fungicide within 48 hours\n..."
  },

  "farmer_message": {
    "language": "sw",
    "content": "Habari John! Wiki hii tumegundua ugonjwa wa kuvu. Tafadhali: 1) Nyunyiza dawa ya kuvu ndani ya siku 2 2) Vuna baada ya saa 3 asubuhi. Maswali? Jibu ujumbe huu.",
    "character_count": 178,
    "sms_segments": 2
  }
}
```

---

### Use Case Summary

| Use Case | Trigger | Models Involved | Key Features |
|----------|---------|-----------------|--------------|
| **Batch ZIP Upload** | HTTP (QC Analyzer) | Collection | Resumable upload, checksum, expand to documents |
| **Image Diagnosis** | Event (per image) | Collection → AI → Knowledge | Vision LLM, RAG, confidence retry |
| **Weekly Action Plan** | Schedule (Monday 6 AM) | Action Plan → AI → Notification | Dual output, translation, length check |

### Event Flow Summary

```
BATCH UPLOAD:
QC Analyzer ──HTTP──▶ Collection ──event──▶ DAPR Pub/Sub (N events)

DIAGNOSIS:
Collection event ──▶ AI Model ──MCP──▶ Collection, Plantation
                         │
                         └──event──▶ Knowledge (stores)

ACTION PLAN:
DAPR Jobs ──▶ Action Plan ──event──▶ AI Model ──MCP──▶ Knowledge, Plantation
                                         │
                                         └──event──▶ Action Plan ──event──▶ Notification
```