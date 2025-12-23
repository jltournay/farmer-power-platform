# Knowledge Model Architecture

## Overview

The Knowledge Model is an **active analysis engine** that diagnoses situations based on collected data. It does NOT prescribe solutions - that's the Action Plan Model's responsibility.

**Core Responsibility:** DIAGNOSE situations (what's wrong? what's happening?)

**Does NOT:** Prescribe solutions, generate action plans, or tell farmers what to do.

## Architecture Diagram

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

## Three-Tier Agent Pattern

The Knowledge Model uses a **Hybrid Triage** architecture to intelligently route quality issues to the appropriate specialized analyzer(s).

### Tier 1: Explorer Agent
- **Responsibility:** Receive events and scheduled triggers, maintain analysis tracking
- **Event path:** Routes `POOR_QUALITY_DETECTED` to Triage Agent
- **Scheduled path:** Routes directly to Weather (daily) or Trend (weekly) Analyzers

### Tier 2: Triage Agent (Event Path Only)
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

## LangGraph Saga Pattern (Parallel Analyzer Orchestration)

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

### Tier 3: Specialized Analyzer Agents

| Analyzer | Trigger | Model | RAG Domains | Purpose |
|----------|---------|-------|-------------|---------|
| Disease Detection | Triage routes | Sonnet (Vision) | plant_diseases, regional_patterns | Identify plant diseases from quality issues + images |
| Weather Impact | Triage routes OR Daily scheduled | Sonnet | weather_patterns, tea_cultivation | Assess weather effects on crop quality |
| Technique Assessment | Triage routes | Haiku | harvesting_techniques, regional_practices | Identify harvesting/handling issues |
| Quality Trend | Weekly scheduled | Haiku | None (statistical) | Analyze patterns in farmer's history |

## Weather Lag Correlation

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

## Two Databases

### Analysis DB (MongoDB)
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

### Vector DB (Pinecone)
**Purpose:** Expert knowledge for RAG enrichment

**Content:**
- Industry best practices
- Tea cultivation guidelines
- Disease/pest identification
- Regional patterns and seasonal factors

**Curated by:** Domain experts (agronomists)

## RAG Pattern

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

## Trigger Configuration

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

## MCP Server Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get_farmer_analyses` | Get all analyses for a farmer | `farmer_id`, `date_range?`, `type?` |
| `get_analysis_by_id` | Retrieve specific analysis | `analysis_id` |
| `search_analyses` | Search analyses by criteria | `query`, `filters`, `limit` |
| `get_recent_diagnoses` | Get diagnoses needing action | `farmer_id`, `since_date` |

**Primary Consumer:** Action Plan Model queries weekly: "Get all analyses for farmer X in past week"

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | DIAGNOSE only | Clean separation from prescribing |
| **Agent Architecture** | Multiple specialized workflows | Different analyses need different approaches |
| **Trigger Mechanism** | Configurable (event OR scheduled) | Flexibility per analysis type |
| **Tracking** | Self-maintained | No dependency on Collection Model |
| **Analysis Storage** | Single collection + type field | Generic, dynamic extensibility |
| **Expert Knowledge** | Vector DB for RAG | Enriches diagnosis with domain expertise |

## Diagnosis Deduplication Strategy

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

## Testing Strategy

| Test Type | Scope |
|-----------|-------|
| **Explorer Agent** | Correctly identifies unanalyzed items, no duplicates |
| **Analyzer Accuracy** | Diagnoses match expert-validated cases |
| **RAG Relevance** | Vector search returns useful context |
| **New Type Addition** | Can add analysis type without deployment |
| **MCP Queries** | Type filtering works correctly |

## Triage Feedback Loop

The Triage Agent improves over time through a structured feedback loop that converts agronomist corrections into better few-shot examples.

### Feedback Loop Architecture

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

### Feedback Storage Schema

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

### Improvement Pipeline

| Step | Trigger | Process | Output |
|------|---------|---------|--------|
| **1. Aggregate** | Dapr Job (weekly) | Group corrections by pattern, filter ≥5 similar with >80% agreement | Candidate patterns |
| **2. Generate** | Automatic | Select representative cases, format as few-shot examples | New prompt examples |
| **3. A/B Test** | Automatic (1 week) | Shadow mode: run old + new prompt, compare accuracy | Test results |
| **4. Promote** | Manual approval | If improved → update production prompt | New prompt version |

### Dapr Job Configuration

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

### Few-Shot Example Generation

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

### Metrics Tracked

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| **Correction Rate** | % of diagnoses corrected by agronomists | >20% triggers review |
| **Pattern Detection** | New correction patterns identified | Weekly report |
| **Prompt Version Accuracy** | Precision/recall per category per version | Degradation >5% |
| **A/B Test Results** | New vs old prompt performance | Auto-reject if worse |

---
