# Epic 5: Quality Diagnosis AI

## Overview

This epic implements the AI-powered quality diagnosis system using LangGraph workflows and RAG (Retrieval Augmented Generation). The Knowledge Model service provides intelligent triage of quality issues, routing to specialized agents for disease detection, weather impact analysis, technique assessment, and trend analysis. All diagnoses are enriched with expert agricultural knowledge via a curated RAG knowledge base.

## Scope

- Knowledge Model service setup with LangGraph and RAG capabilities
- Event aggregation engine to batch quality events for efficient analysis
- Triage Agent for issue classification and routing
- Disease Detection Agent with vision capabilities
- Weather Impact Analyzer with lag correlation
- Technique Assessment Agent for harvesting/handling issues
- Trend Analysis Agent for pattern detection
- RAG Knowledge Base for expert agricultural content
- Knowledge Model MCP Server for cross-service access

---

## Stories

### Story 5.1: Knowledge Model Service Setup

As a **platform operator**,
I want the Knowledge Model service deployed with LangGraph and RAG capabilities,
So that quality issues can be automatically diagnosed.

**Acceptance Criteria:**

**Given** the Kubernetes cluster is running with Dapr installed
**When** the Knowledge Model service is deployed
**Then** the service starts successfully with health check endpoint returning 200
**And** the Dapr sidecar is injected and connected
**And** MongoDB connection is established for Analysis DB
**And** Pinecone connection is established for Vector DB
**And** OpenTelemetry traces are emitted for all operations

**Given** the service is running
**When** subscribed to Dapr pub/sub
**Then** "collection.poor_quality_detected" events trigger triage workflow
**And** scheduled jobs trigger weekly trend analysis

**Given** the service processes a diagnosis request
**When** LangGraph workflow executes
**Then** workflow state is persisted to MongoDB
**And** all LLM calls are traced via LangChain callbacks
**And** RAG queries are logged with retrieved chunks

**Given** the LLM API is unavailable
**When** a diagnosis is requested
**Then** the request is queued for retry (exponential backoff)
**And** an alert is logged for monitoring
**And** previous diagnoses remain unaffected

**Technical Notes:**
- Python with LangChain/LangGraph
- Claude Haiku for triage, Claude Sonnet for specialized analysis
- Pinecone: farmer-power-knowledge index
- Environment: farmer-power-{env} namespace

---

### Story 5.2: Event Aggregation Engine

As a **Knowledge Model system**,
I want to aggregate quality events before analysis,
So that diagnoses have more evidence and LLM costs are reduced.

**Acceptance Criteria:**

**Given** a "collection.poor_quality_detected" event is received
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
**Then** all events in the bucket are passed to the Triage Agent
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

### Story 5.3: Triage Agent

As a **Knowledge Model system**,
I want a Triage Agent to classify quality issues and route to specialists,
So that the right analyzer processes each issue efficiently.

**Acceptance Criteria:**

**Given** aggregated quality events are ready for analysis
**When** the Triage Agent receives them
**Then** it classifies the probable cause: disease, weather, technique, trend, unknown
**And** confidence score (0.0-1.0) is assigned to the classification
**And** the classification and confidence are logged

**Given** the Triage Agent classifies with confidence >= 0.7
**When** routing decision is made
**Then** events are routed to the single most likely analyzer
**And** the routing path is recorded in the workflow state

**Given** the Triage Agent classifies with confidence < 0.7
**When** routing decision is made
**Then** events are routed to multiple analyzers in parallel
**And** results are merged after all analyzers complete
**And** the parallel execution is logged

**Given** the Triage Agent cannot classify (unknown)
**When** confidence is below 0.3
**Then** the event is flagged for human review
**And** a "diagnosis.needs_review" event is published
**And** partial analysis is still attempted with all analyzers

**Given** the Triage Agent runs
**When** processing completes
**Then** LLM usage (tokens, model, latency) is logged
**And** triage accuracy metrics are collected for feedback loop

**Technical Notes:**
- LLM: Claude Haiku (fast, cheap)
- Prompt: few-shot examples from validated diagnoses
- Parallel routing: LangGraph conditional edges
- Max latency target: 2 seconds

---

### Story 5.4: Disease Detection Agent

As a **Knowledge Model system**,
I want a Disease Detection Agent to identify plant diseases from images,
So that disease-related quality issues are accurately diagnosed.

**Acceptance Criteria:**

**Given** quality events are routed to Disease Detection
**When** events include image references
**Then** images are fetched from Azure Blob Storage
**And** images are analyzed using vision-capable LLM
**And** visual symptoms are described in natural language

**Given** images are analyzed
**When** disease symptoms are detected
**Then** the diagnosis includes: disease_name, confidence, affected_area, severity
**And** RAG is queried for disease identification and treatment guidance
**And** the diagnosis references the expert knowledge source

**Given** RAG provides disease knowledge
**When** the diagnosis is generated
**Then** the response includes: identified_condition, confidence, severity, details
**And** details explain what symptoms were observed
**And** NO treatment recommendations are provided (that's Action Plan's job)

**Given** no disease is detected
**When** the analysis completes
**Then** the diagnosis indicates: condition="none_detected", confidence=high
**And** the agent suggests alternative causes (weather, technique)

**Given** image quality is poor (blurry, too dark)
**When** analysis is attempted
**Then** the diagnosis indicates: image_quality="insufficient"
**And** confidence is lowered appropriately
**And** a note is added requesting better images in future

**Technical Notes:**
- LLM: Claude Sonnet (vision capability)
- Image preprocessing: resize to max 1024px
- RAG domain: plant_diseases
- Max images per analysis: 10

---

### Story 5.5: Weather Impact Analyzer

As a **Knowledge Model system**,
I want a Weather Impact Analyzer to correlate weather with quality issues,
So that weather-related causes are identified with appropriate lag.

**Acceptance Criteria:**

**Given** quality events are routed to Weather Impact Analyzer
**When** processing begins
**Then** weather data for the farmer's region is fetched (past 14 days)
**And** the 3-7 day lag window is applied per weather event type

**Given** weather data shows heavy rain (>50mm/day) 3-5 days before delivery
**When** correlation is analyzed
**Then** the diagnosis includes: condition="moisture_excess", weather_event="heavy_rain", lag_days=X
**And** confidence is weighted by rainfall amount and timing

**Given** weather data shows frost (<2C) 3-5 days before delivery
**When** correlation is analyzed
**Then** the diagnosis includes: condition="frost_damage", weather_event="frost", lag_days=X
**And** RAG is queried for frost impact on tea quality

**Given** weather data shows drought (>5 days no rain) 4-7 days before
**When** correlation is analyzed
**Then** the diagnosis includes: condition="moisture_deficit", weather_event="drought", lag_days=X

**Given** weather data shows high humidity (>90%) 2-4 days before
**When** correlation is analyzed
**Then** the diagnosis includes: condition="fungal_risk", weather_event="high_humidity"
**And** Disease Detection is triggered as secondary analyzer

**Given** no weather correlation is found
**When** analysis completes
**Then** the diagnosis indicates: weather_impact="none_detected"
**And** the agent suggests alternative causes

**Technical Notes:**
- Weather data: from Collection Model (pull mode)
- Lag weights: configurable per event type
- Seasonal adjustments: dry season vs rainy season
- LLM: Claude Haiku (text analysis)

---

### Story 5.6: Technique Assessment Agent

As a **Knowledge Model system**,
I want a Technique Assessment Agent to identify harvesting/handling problems,
So that technique-related quality issues are diagnosed.

**Acceptance Criteria:**

**Given** quality events are routed to Technique Assessment
**When** processing begins
**Then** leaf_type_distribution is analyzed for technique indicators
**And** historical patterns for this farmer are fetched

**Given** leaf assessments show high coarse_leaf percentage (>30%)
**When** analysis is performed
**Then** the diagnosis includes: condition="over_plucking", indicator="high_coarse_leaf"
**And** RAG is queried for proper plucking technique guidance

**Given** leaf assessments show high banji percentage (>20%)
**When** analysis is performed
**Then** the diagnosis includes: condition="poor_timing", indicator="high_banji"
**And** banji_hardness distribution is analyzed (soft vs hard)

**Given** leaf assessments show high damaged leaves
**When** damage_percentage > 15%
**Then** the diagnosis includes: condition="handling_damage", indicator="damaged_leaves"
**And** RAG suggests handling improvements

**Given** farmer's technique has been consistent but quality dropped
**When** historical comparison shows sudden change
**Then** the diagnosis notes: "technique_consistent, other_factors_likely"
**And** confidence in technique as cause is lowered

**Given** multiple technique issues are detected
**When** generating diagnosis
**Then** issues are prioritized by severity
**And** the primary issue is highlighted with supporting details

**Technical Notes:**
- LLM: Claude Haiku
- RAG domain: harvesting_techniques
- Historical window: 30 days
- Thresholds configurable per region

---

### Story 5.7: Trend Analysis Agent

As a **Knowledge Model system**,
I want a Trend Analysis Agent to detect patterns over time,
So that recurring or seasonal issues are identified proactively.

**Acceptance Criteria:**

**Given** the weekly trend analysis job runs (Sunday midnight)
**When** farmers with >=5 deliveries in past 30 days are identified
**Then** trend analysis is triggered for each qualifying farmer

**Given** a farmer's quality is analyzed for trends
**When** the analysis runs
**Then** primary_percentage trend is calculated (improving, stable, declining)
**And** seasonal patterns are identified (wet season vs dry season)
**And** comparison to regional average is computed

**Given** a declining trend is detected (>10% drop over 4 weeks)
**When** the diagnosis is generated
**Then** the diagnosis includes: condition="quality_decline", trend_direction="declining", decline_rate="X%/week"
**And** a "diagnosis.trend_alert" event is published

**Given** a farmer is performing below regional average
**When** the percentile is calculated
**Then** yield_percentile is stored (e.g., "25th percentile")
**And** the diagnosis notes performance relative to peers

**Given** a seasonal pattern is detected
**When** current period matches historical low
**Then** the diagnosis includes: condition="seasonal_pattern", historical_context="dry_season_typical"
**And** this context is passed to Action Plan Model

**Given** no significant trends are detected
**When** the farmer has stable quality
**Then** a positive trend record is created: condition="stable_performance"
**And** no alert is published

**Technical Notes:**
- Schedule: Dapr Jobs (Sunday 00:00)
- Statistical analysis: Python pandas
- No LLM required for basic trend calculation
- LLM used for pattern interpretation and context

---

### Story 5.8: RAG Knowledge Base

As a **platform operator**,
I want a curated knowledge base for RAG enrichment,
So that diagnoses are informed by expert agricultural knowledge.

**Acceptance Criteria:**

**Given** the Pinecone vector database is configured
**When** the knowledge base is initialized
**Then** the following domains are indexed: plant_diseases, tea_cultivation, weather_patterns, harvesting_techniques

**Given** an agronomist uploads new knowledge content
**When** content is processed
**Then** text is chunked (500 tokens with 100 token overlap)
**And** embeddings are generated (OpenAI ada-002)
**And** chunks are stored in Pinecone with metadata: domain, source, version, date

**Given** an agent queries the knowledge base
**When** a RAG search is performed
**Then** top 5 most relevant chunks are returned
**And** relevance scores are included
**And** source citations are preserved for attribution

**Given** knowledge content is versioned
**When** a new version is uploaded
**Then** the old version is retained (soft delete)
**And** agents use the latest version by default
**And** A/B testing can compare versions

**Given** a query returns low-relevance results (score < 0.7)
**When** the agent processes results
**Then** the agent is notified of low confidence
**And** the agent can proceed without RAG or flag for review

**Given** Pinecone is unavailable
**When** a RAG query is attempted
**Then** the query fails gracefully
**And** the agent proceeds without RAG enrichment (degraded mode)
**And** an alert is logged

**Technical Notes:**
- Pinecone: farmer-power-knowledge index
- Embedding model: text-embedding-ada-002
- Namespace per domain for isolated queries
- Knowledge curated by agronomists (not auto-generated)

---

### Story 5.9: Knowledge Model MCP Server

As an **AI agent (Action Plan Model)**,
I want to access diagnoses via MCP tools,
So that action plans can be generated based on analysis results.

**Acceptance Criteria:**

**Given** the Knowledge MCP Server is deployed
**When** an AI agent calls `get_farmer_analyses(farmer_id, date_range, type?)`
**Then** all matching diagnoses are returned
**And** each diagnosis includes: type, condition, confidence, severity, details, source_documents

**Given** an analysis_id exists
**When** an AI agent calls `get_analysis_by_id(analysis_id)`
**Then** the full diagnosis is returned including RAG context used

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

**Technical Notes:**
- MCP Server deployed as separate Kubernetes deployment
- HPA enabled: min 2, max 10 replicas
- Read-only access to Analysis DB (MongoDB)
- gRPC interface following MCP protocol
