# Knowledge Model Architecture

## Overview

The Knowledge Model is an **active analysis engine** that diagnoses situations based on collected data. It does NOT prescribe solutions - that's the Action Plan Model's responsibility.

**Core Responsibility:** DIAGNOSE situations (what's wrong? what's happening?)

**Does NOT:** Prescribe solutions, generate action plans, or tell farmers what to do.

## Document Boundaries

> **This document defines WHAT to diagnose and WHEN.** For HOW agents are implemented (LLM config, prompts, LangGraph workflows), see [`ai-model-architecture.md`](./ai-model-architecture.md).

| This Document Owns | AI Model Architecture Owns |
|-------------------|---------------------------|
| Analysis types needed (disease, weather, technique, trend) | Agent implementations (Triage, Disease Analyzer, etc.) |
| Trigger conditions (events, schedules) | LangGraph workflow orchestration |
| Output schemas (what diagnosis must contain) | LLM selection (Haiku vs Sonnet) |
| Storage location (Analysis DB) | RAG configuration and knowledge domains |
| MCP tools exposed to Action Plan Model | Prompt engineering and A/B testing |
| Business rules (when to aggregate, severity levels) | Vision processing tiers |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE MODEL                                  │
│                    (Business Flow - WHAT happens)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TRIGGERS (WHEN to analyze)                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  EVENT: collection.poor_quality_detected                         │   │
│  │  SCHEDULE: Daily weather analysis (6 AM)                         │   │
│  │  SCHEDULE: Weekly trend analysis (Sunday midnight)               │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│                                 ▼                                       │
│  ANALYSIS TYPES (WHAT to diagnose)                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│   │
│  │  │  Disease    │ │  Weather    │ │  Technique  │ │   Trend     ││   │
│  │  │  Detection  │ │  Impact     │ │  Assessment │ │  Analysis   ││   │
│  │  │             │ │             │ │             │ │             ││   │
│  │  │ Visual      │ │ Weather-to- │ │ Harvesting  │ │ Historical  ││   │
│  │  │ symptoms    │ │ quality     │ │ and handling│ │ patterns    ││   │
│  │  │ from images │ │ correlation │ │ issues      │ │ over time   ││   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│   │
│  │                                                                  │   │
│  │  Implementation: See ai-model-architecture.md                    │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│                                 ▼                                       │
│  STORAGE (WHERE results go)                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ANALYSIS DB (MongoDB)                         │   │
│  │  • diagnosis type, confidence, severity                          │   │
│  │  • source documents, farmer_id                                   │   │
│  │  • recommendations (what's wrong, not what to do)                │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│                                 ▼                                       │
│  CONSUMERS (WHO uses diagnoses)                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │ Action Plan Model│  │  Admin Dashboard │  │  Events (Pub/Sub)│      │
│  │ (via MCP)        │  │  (via Query API) │  │  (ai.diagnosis.*)│      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Analysis Requirements

The Knowledge Model requires intelligent routing of quality issues to specialized analyzers.

### Analysis Categories

| Category | Business Purpose | Trigger |
|----------|-----------------|---------|
| **Disease Detection** | Identify plant diseases from visual symptoms | Event: poor quality with image |
| **Weather Impact** | Correlate weather events with quality issues | Event OR Daily schedule |
| **Technique Assessment** | Identify harvesting/handling problems | Event: technique indicators |
| **Trend Analysis** | Detect patterns in farmer's history | Weekly schedule |

### Routing Requirements

When a `collection.poor_quality_detected` event occurs:
1. **Triage first** — Quickly classify the probable cause
2. **Route to specialist** — Send to appropriate analyzer(s)
3. **Handle uncertainty** — If confidence is low, run multiple analyzers in parallel

> **Implementation:** See [`ai-model-architecture.md`](./ai-model-architecture.md) for Triage Agent configuration, LangGraph workflow orchestration, and parallel analyzer saga pattern.

### Diagnosis Output Requirements

Each diagnosis must include:

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | disease_detection, weather_impact, technique_assessment, trend_analysis |
| `condition` | Yes | What was identified (e.g., "fungal_infection", "moisture_excess") |
| `confidence` | Yes | 0.0-1.0 score |
| `severity` | Yes | low, moderate, high, critical |
| `details` | Yes | Human-readable explanation |
| `recommendations` | No | What's wrong (NOT what to do — that's Action Plan's job) |
| `source_documents` | Yes | References to Collection Model documents |

### Weather Correlation Business Rule

**Key Insight:** Weather affects tea quality with a 3-7 day delay. The Weather Analyzer must account for this lag.

| Weather Event | Impact Window | Quality Impact |
|---------------|---------------|----------------|
| Heavy rain (>50mm/day) | Days 3-5 after | Moisture excess, fungal risk |
| Frost (<2°C) | Days 3-5 after | Leaf damage, stunting |
| Drought (>5 days no rain) | Days 4-7 after | Moisture deficit, stress |
| High humidity (>90%) | Days 2-4 after | Fungal risk, pest proliferation |

> **Implementation:** See [`ai-model-architecture.md`](./ai-model-architecture.md) for Weather Analyzer agent configuration with day weights and seasonal adjustments.

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
**Purpose:** Expert knowledge for RAG enrichment (curated by agronomists)

| Knowledge Domain | Content |
|-----------------|---------|
| Plant Diseases | Symptoms, identification, treatment guidance |
| Tea Cultivation | Best practices, seasonal guidance |
| Weather Patterns | Regional climate impacts on tea |
| Harvesting Techniques | Proper plucking, handling methods |

> **Implementation:** RAG engine configuration, versioning, and A/B testing are defined in [`ai-model-architecture.md`](./ai-model-architecture.md).

## Trigger Requirements

| Analysis | Trigger Type | Schedule/Event | RAG Required |
|----------|--------------|----------------|--------------|
| Disease Detection | Event | `collection.poor_quality_detected` | Yes |
| Weather Impact | Event + Schedule | Event OR Daily 6 AM | Yes |
| Technique Assessment | Event | `collection.poor_quality_detected` | Yes |
| Trend Analysis | Schedule | Weekly Sunday midnight | No (statistical) |

> **Implementation:** Trigger configuration (Dapr Jobs, event subscriptions) is defined in [`ai-model-architecture.md`](./ai-model-architecture.md).

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

## Diagnosis Deduplication Business Rules

When a farmer delivers multiple poor-quality batches in a short period, events are aggregated before analysis:

**Business Rule:** Aggregate events within a 24-hour window per farmer, then run a single diagnosis with all evidence. This produces higher-confidence diagnoses and reduces costs.

| Scenario | Behavior |
|----------|----------|
| 5 events from same farmer in 24h | Single diagnosis referencing all 5 events |
| Critical issue detected | Bypass aggregation, analyze immediately |
| 10+ events | Split into multiple diagnoses with cross-references |
| Mixed issue types | Optionally group by category before aggregating |

**Benefits:**
- Higher diagnosis quality (more evidence)
- Lower cost (~75% reduction in LLM calls)
- Simpler Action Plan input (no deduplication needed)

## Testing Strategy

| Test Type | Scope |
|-----------|-------|
| **Explorer Agent** | Correctly identifies unanalyzed items, no duplicates |
| **Analyzer Accuracy** | Diagnoses match expert-validated cases |
| **RAG Relevance** | Vector search returns useful context |
| **New Type Addition** | Can add analysis type without deployment |
| **MCP Queries** | Type filtering works correctly |

## Continuous Improvement

### Triage Feedback Loop

Agronomist corrections improve triage accuracy over time:

1. **Agronomist reviews** diagnosis and routing decision
2. **Feedback stored** (confirm, correct category, add/remove analyzer)
3. **Weekly aggregation** identifies patterns (≥5 similar corrections, >80% agreement)
4. **New few-shot examples** generated from validated patterns
5. **A/B tested** before promoting to production

> **Implementation:** Feedback storage schema, aggregation jobs, and prompt A/B testing are defined in [`ai-model-architecture.md`](./ai-model-architecture.md).

### Metrics Tracked

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| Correction Rate | % of diagnoses corrected by agronomists | >20% triggers review |
| Pattern Detection | New correction patterns identified | Weekly report |
| Prompt Version Accuracy | Precision/recall per category per version | Degradation >5% |

---
