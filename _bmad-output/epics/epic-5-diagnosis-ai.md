# Epic 5: Knowledge Model (Quality Diagnosis)

**Priority:** P3

**Dependencies:** Epic 0.75 (AI Model Foundation), Epic 1 (Plantation Model), Epic 2 (Collection Model)

**FRs covered:** FR24, FR25, FR26, FR27, FR28

## Overview

The Knowledge Model is an **active analysis engine** that diagnoses quality issues. It determines WHAT is wrong with a farmer's tea quality but does NOT prescribe solutions — that's the Action Plan Model's responsibility.

This epic defines the **business logic** for quality diagnosis: what triggers analysis, what types of analysis are needed, what the outputs must contain, and how diagnoses are exposed to consumers.

> **Implementation Note:** All agent implementations (LangGraph workflows, LLM selection, RAG queries, prompt engineering) are defined in Epic 0.75 (AI Model Foundation). This epic focuses on WHAT to diagnose and WHEN, not HOW agents work internally.

## Document Boundaries

| This Epic Owns | Epic 0.75 (AI Model) Owns |
|----------------|---------------------------|
| Analysis types needed (disease, weather, technique, trend) | Agent implementations (Triage, Disease Analyzer, etc.) |
| Trigger conditions (events, schedules) | LangGraph workflow orchestration |
| Output schemas (what diagnosis must contain) | LLM selection (Haiku vs Sonnet) |
| Storage location (Analysis DB) | RAG configuration and knowledge domains |
| MCP tools exposed to Action Plan Model | Prompt engineering and A/B testing |
| Business rules (aggregation, severity levels) | Vision processing tiers |

## Scope

- Knowledge Model service setup (Dapr subscriptions, Analysis DB)
- Event aggregation engine with business rules
- Analysis type definitions: Disease, Weather, Technique, Trend
- Diagnosis output schemas and severity mapping
- Knowledge Model MCP Server for Action Plan Model access

**NOT in scope:** Agent implementations, LLM configuration, RAG infrastructure, prompt management — these belong in Epic 0.75.

---

## Stories

### Story 5.1: Knowledge Model Service Setup

As a **platform operator**,
I want the Knowledge Model service deployed with Dapr integration,
So that quality events can trigger diagnosis workflows.

**Acceptance Criteria:**

**Given** the Kubernetes cluster is running with Dapr installed
**When** the Knowledge Model service is deployed
**Then** the service starts successfully with health check endpoint returning 200
**And** the Dapr sidecar is injected and connected
**And** MongoDB connection is established for Analysis DB
**And** OpenTelemetry traces are emitted for all operations

**Given** the service is running
**When** subscribed to Dapr pub/sub
**Then** `collection.poor_quality_detected` events trigger the triage flow
**And** scheduled jobs trigger analysis per configured schedules

**Given** a diagnosis is completed
**When** results are stored
**Then** the diagnosis is persisted to Analysis DB (MongoDB)
**And** a `knowledge.diagnosis.created` event is published
**And** the event includes: `farmer_id`, `diagnosis_type`, `severity`

**Given** the AI Model service is unavailable
**When** a diagnosis is requested
**Then** the request is queued for retry (exponential backoff)
**And** an alert is logged for monitoring
**And** previous diagnoses remain unaffected

**Technical Notes:**
- Python FastAPI service
- Dapr service invocation to AI Model for agent execution
- Analysis DB: `knowledge_model.analyses` collection
- Environment: farmer-power-{env} namespace

> **Implementation:** Agent execution delegated to AI Model service (Epic 0.75).

---

### Story 5.2: Event Aggregation Engine

As a **Knowledge Model system**,
I want to aggregate quality events before analysis,
So that diagnoses have more evidence and analysis costs are reduced.

**Acceptance Criteria:**

**Given** a `collection.poor_quality_detected` event is received
**When** the farmer has no pending events in the aggregation window
**Then** a new aggregation bucket is created with 24-hour TTL
**And** the event is added to the bucket
**And** a delayed analysis trigger is scheduled (30 minutes)

**Given** additional events arrive for the same farmer within 24 hours
**When** the aggregation bucket exists
**Then** events are added to the existing bucket
**And** the analysis trigger is reset (30-minute delay from latest event)
**And** a maximum of 10 events are held before forced analysis

**Given** the aggregation window expires (30 min of no new events)
**When** the analysis is triggered
**Then** all events in the bucket are passed to the triage flow
**And** the diagnosis references all source event_ids
**And** the bucket is cleared

**Given** a critical priority event is detected (primary_percentage < 40%)
**When** the event arrives
**Then** aggregation is bypassed
**And** immediate analysis is triggered
**And** existing bucket events are included in the analysis

**Given** the aggregation engine fails
**When** events cannot be bucketed
**Then** events are processed individually (fallback)
**And** an alert is logged
**And** no events are lost

**Technical Notes:**
- Aggregation state: Redis with TTL
- Bucket key: farmer_id
- Scheduled triggers: Dapr Jobs
- Critical threshold: configurable per factory

---

### Story 5.3: Analysis Type - Disease Detection

As a **Knowledge Model system**,
I want disease detection analysis available,
So that plant diseases can be identified from visual symptoms.

**Acceptance Criteria:**

**Given** aggregated quality events include image references
**When** disease detection analysis is triggered
**Then** the AI Model disease-detection agent is invoked via Dapr
**And** images are passed as references (not inline data)

**Given** disease detection completes
**When** the diagnosis is generated
**Then** the output matches this schema:
```json
{
  "type": "disease_detection",
  "condition": "fungal_infection | bacterial_blight | pest_damage | none_detected",
  "confidence": 0.0-1.0,
  "severity": "low | moderate | high | critical",
  "details": "Human-readable explanation of symptoms observed",
  "affected_area": "percentage of leaves affected",
  "source_documents": ["doc-id-1", "doc-id-2"],
  "image_quality": "sufficient | insufficient"
}
```

**Given** no disease is detected
**When** the analysis completes
**Then** the diagnosis indicates: `condition="none_detected"`, `confidence=high`
**And** alternative cause suggestions may be included in details

**Given** image quality is poor (blurry, too dark)
**When** analysis is attempted
**Then** the diagnosis indicates: `image_quality="insufficient"`
**And** confidence is lowered appropriately
**And** details note that better images would improve diagnosis

**Business Rules:**
- Minimum 1 image required for disease detection
- Maximum 10 images per analysis
- Images resized to max 1024px before analysis

> **Implementation:** Disease detection agent configuration in Epic 0.75.3. Vision LLM selection and RAG knowledge domain (plant_diseases) in Epic 0.75.

---

### Story 5.4: Analysis Type - Weather Impact

As a **Knowledge Model system**,
I want weather impact analysis available,
So that weather-related quality issues are identified with appropriate lag correlation.

**Acceptance Criteria:**

**Given** quality events are ready for weather analysis
**When** weather impact analysis is triggered
**Then** weather data for the farmer's region is requested (past 14 days)
**And** the 3-7 day lag window is applied per weather event type

**Given** the diagnosis is generated
**When** weather correlation is found
**Then** the output matches this schema:
```json
{
  "type": "weather_impact",
  "condition": "moisture_excess | frost_damage | moisture_deficit | fungal_risk | none_detected",
  "confidence": 0.0-1.0,
  "severity": "low | moderate | high | critical",
  "details": "Explanation of weather-quality correlation",
  "weather_event": "heavy_rain | frost | drought | high_humidity",
  "lag_days": 3-7,
  "source_documents": ["doc-id-1"]
}
```

**Weather Correlation Business Rules:**

| Weather Event | Detection Threshold | Impact Window |
|---------------|---------------------|---------------|
| Heavy rain | >50mm/day | Days 3-5 after |
| Frost | <2°C | Days 3-5 after |
| Drought | >5 days no rain | Days 4-7 after |
| High humidity | >90% | Days 2-4 after |

**Given** high humidity is detected with fungal risk
**When** the analysis completes
**Then** disease detection may be triggered as secondary analysis

**Given** no weather correlation is found
**When** the analysis completes
**Then** the diagnosis indicates: `condition="none_detected"`

> **Implementation:** Weather analyzer agent configuration in Epic 0.75.3. Seasonal adjustments and lag weights configured in agent definition.

---

### Story 5.5: Analysis Type - Technique Assessment

As a **Knowledge Model system**,
I want technique assessment analysis available,
So that harvesting and handling problems are identified.

**Acceptance Criteria:**

**Given** quality events are ready for technique assessment
**When** technique analysis is triggered
**Then** leaf_type_distribution from events is analyzed
**And** historical patterns for this farmer are fetched via MCP

**Given** the diagnosis is generated
**When** technique issues are found
**Then** the output matches this schema:
```json
{
  "type": "technique_assessment",
  "condition": "over_plucking | poor_timing | handling_damage | none_detected",
  "confidence": 0.0-1.0,
  "severity": "low | moderate | high | critical",
  "details": "Explanation of technique indicators observed",
  "indicators": ["high_coarse_leaf", "high_banji", "damaged_leaves"],
  "historical_comparison": "consistent | sudden_change | gradual_decline",
  "source_documents": ["doc-id-1"]
}
```

**Technique Indicator Thresholds:**

| Indicator | Threshold | Condition |
|-----------|-----------|-----------|
| Coarse leaf | >30% | over_plucking |
| Banji | >20% | poor_timing |
| Damaged leaves | >15% | handling_damage |

**Given** farmer's technique has been consistent but quality dropped
**When** historical comparison shows sudden change
**Then** the diagnosis notes: `historical_comparison="sudden_change"`
**And** confidence in technique as cause is lowered

**Given** multiple technique issues are detected
**When** generating diagnosis
**Then** issues are prioritized by severity
**And** the primary issue is highlighted in details

> **Implementation:** Technique assessment agent configuration in Epic 0.75.3. RAG knowledge domain (harvesting_techniques) configured in Epic 0.75.5.

---

### Story 5.6: Analysis Type - Trend Analysis

As a **Knowledge Model system**,
I want trend analysis available,
So that recurring or seasonal patterns are identified proactively.

**Acceptance Criteria:**

**Given** the weekly trend analysis job runs (Sunday midnight)
**When** farmers with >=5 deliveries in past 30 days are identified
**Then** trend analysis is triggered for each qualifying farmer

**Given** the diagnosis is generated
**When** trend analysis completes
**Then** the output matches this schema:
```json
{
  "type": "trend_analysis",
  "condition": "quality_decline | seasonal_pattern | below_regional_average | stable_performance",
  "confidence": 0.0-1.0,
  "severity": "low | moderate | high | critical",
  "details": "Explanation of trend patterns observed",
  "trend_direction": "improving | stable | declining",
  "decline_rate": "X%/week (if declining)",
  "yield_percentile": "25th percentile (regional comparison)",
  "seasonal_context": "dry_season_typical | rainy_season_typical | none"
}
```

**Given** a declining trend is detected (>10% drop over 4 weeks)
**When** the diagnosis is generated
**Then** severity is set to "moderate" or higher
**And** a `knowledge.trend_alert` event is published

**Given** a farmer is performing below regional average
**When** percentile is calculated
**Then** `yield_percentile` is included (e.g., "25th percentile")

**Given** a seasonal pattern is detected
**When** current period matches historical low
**Then** `seasonal_context` provides historical comparison

**Given** no significant trends are detected
**When** the farmer has stable quality
**Then** diagnosis indicates: `condition="stable_performance"`
**And** no alert is published

**Technical Notes:**
- Schedule: Dapr Jobs (Sunday 00:00)
- Statistical analysis: Python pandas
- Trend calculation is algorithmic (no LLM needed for basic stats)
- LLM used only for pattern interpretation and context

> **Implementation:** Trend analysis agent configuration in Epic 0.75.3.

---

### Story 5.7: Knowledge Model MCP Server

As an **AI agent (Action Plan Model)**,
I want to access diagnoses via MCP tools,
So that action plans can be generated based on analysis results.

**Acceptance Criteria:**

**Given** the Knowledge MCP Server is deployed
**When** an AI agent calls `get_farmer_analyses(farmer_id, date_range?, type?)`
**Then** all matching diagnoses are returned
**And** each diagnosis includes: type, condition, confidence, severity, details, source_documents

**Given** an analysis_id exists
**When** an AI agent calls `get_analysis_by_id(analysis_id)`
**Then** the full diagnosis is returned

**Given** the Action Plan Model needs recent diagnoses
**When** an AI agent calls `get_recent_diagnoses(farmer_id, since_date)`
**Then** diagnoses created since the specified date are returned
**And** results are sorted by severity (critical first)

**Given** a search query is needed
**When** an AI agent calls `search_analyses(query, filters, limit)`
**Then** text search is performed across diagnosis details
**And** filters can include: farmer_id, type, severity, date_range
**And** results are ranked by relevance

**Given** trend data is needed
**When** an AI agent calls `get_farmer_trend(farmer_id)`
**Then** the latest trend analysis is returned
**And** includes: trend_direction, percentile, seasonal_context

**Given** the MCP Server receives a request
**When** processing completes
**Then** OpenTelemetry traces are emitted
**And** tool usage is logged for cost attribution

**MCP Tools Summary:**

| Tool | Purpose | Primary Consumer |
|------|---------|------------------|
| `get_farmer_analyses` | All analyses for a farmer | Action Plan Model |
| `get_analysis_by_id` | Single analysis by ID | Admin Dashboard |
| `get_recent_diagnoses` | Diagnoses needing action | Action Plan Model |
| `search_analyses` | Search by criteria | Admin Dashboard |
| `get_farmer_trend` | Latest trend analysis | Action Plan Model |

**Technical Notes:**
- MCP Server deployed as separate Kubernetes deployment
- HPA enabled: min 2, max 10 replicas
- Read-only access to Analysis DB (MongoDB)
- gRPC interface following MCP protocol

---

## Dependencies

| This Epic Depends On | Reason |
|---------------------|--------|
| Epic 0.75 (AI Model Foundation) | Agent framework, LLM gateway, RAG infrastructure |
| Epic 1 (Plantation Model) | Farmer context via MCP |
| Epic 2 (Collection Model) | Quality documents and events |

| Epics That Depend On This | Reason |
|--------------------------|--------|
| Epic 6 (Action Plan Model) | Consumes diagnoses via MCP |

---

## Removed from Epic 5

The following content was moved to Epic 0.75 (AI Model Foundation):

| Original Story | New Location | Reason |
|----------------|--------------|--------|
| LangGraph workflow setup | Epic 0.75.3 | Agent framework is cross-cutting |
| LLM selection (Haiku/Sonnet) | Epic 0.75.2 | Model routing is centralized |
| Pinecone/RAG setup | Epic 0.75.5 | RAG infrastructure is shared |
| Story 5.8 (RAG Knowledge Base) | Epic 0.75.5 | Knowledge domains defined in AI Model |

---

## Retrospective

**Story File:** Not yet created | Status: Backlog

---

_Last Updated: 2025-12-28_
