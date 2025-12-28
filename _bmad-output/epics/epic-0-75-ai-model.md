# Epic 0.75: AI Model Foundation

Cross-cutting AI infrastructure that enables all AI-powered domain models. These stories establish the LLM gateway, agent framework, RAG engine, and prompt management patterns used across Knowledge Model, Action Plan Model, and Conversational AI.

**Dependencies:** Epic 0 (Infrastructure)

**Blocks:** Epic 5 (Knowledge Model), Epic 6 (Action Plans), Epic 8 (Voice Advisor), Epic 12 (Engagement Model)

**FRs covered:** FR45, FR46, FR47, FR48, FR49

**Scope:**
- LLM Gateway (OpenRouter integration, model routing, cost tracking)
- Agent framework (Extractor, Explorer, Generator types) with LangGraph
- Prompt management (MongoDB storage, versioning, A/B testing)
- RAG infrastructure (Pinecone, knowledge domains, embedding pipeline)
- MCP client integration for data access
- AI security patterns (prompt injection prevention, PII handling)
- Domain-specific agent configurations (Knowledge Model, Action Plan, etc.)

---

## Stories

### Story 0.75.1: AI Model Service Setup

**Story File:** Not yet created | Status: Backlog

As a **platform operator**,
I want the AI Model service deployed with Dapr sidecar and OpenRouter integration,
So that AI workflows can be executed by other domain models.

**Acceptance Criteria:**

**Given** the Kubernetes cluster is running with Dapr installed
**When** the AI Model service is deployed
**Then** the service starts successfully with health check endpoint returning 200
**And** the Dapr sidecar is injected and connected
**And** OpenRouter API connection is verified
**And** gRPC server is listening on port 50051
**And** OpenTelemetry traces are emitted for all operations

**Given** an agent workflow is triggered via DAPR pub/sub
**When** the AI Model processes the event
**Then** the workflow executes with proper trace context propagation
**And** results are published back via DAPR pub/sub

**Given** a domain model invokes an agent via Dapr service invocation
**When** the request includes `agent_id` and `input_data`
**Then** the AI Model loads the agent configuration
**And** executes the workflow with the provided input
**And** returns results via the same invocation

**Technical Notes:**
- Python FastAPI + grpcio
- OpenRouter API key via Kubernetes secret
- Health endpoint: `/health` and `/ready`
- Environment: farmer-power-{env} namespace
- DAPR service invocation for MCP calls

---

### Story 0.75.2: LLM Gateway & Model Routing

**Story File:** Not yet created | Status: Backlog

As a **developer implementing AI agents**,
I want a unified LLM gateway with intelligent model routing,
So that I can select the appropriate model for each task type without changing code.

**Acceptance Criteria:**

**Given** an agent specifies `task_type: triage`
**When** the LLM gateway routes the request
**Then** the request is sent to `anthropic/claude-3-haiku` (fast, cheap)
**And** token usage and cost are logged with trace context

**Given** an agent specifies `task_type: diagnosis`
**When** the LLM gateway routes the request
**Then** the request is sent to `anthropic/claude-3-5-sonnet` (accurate)
**And** fallback to `openai/gpt-4o` if Anthropic is unavailable

**Given** an agent specifies `task_type: vision`
**When** the LLM gateway routes the request
**Then** the request is sent to `anthropic/claude-3-5-sonnet` (vision capable)
**And** images are preprocessed (resized to max 1024px)

**Given** an LLM call fails with a transient error
**When** the retry policy is applied
**Then** the request is retried with exponential backoff (100ms, 500ms, 2000ms)
**And** after 3 failures, the fallback chain is used

**Given** all providers in the fallback chain fail
**When** the workflow handles the error
**Then** an error event is published to the dead letter topic
**And** the failure is logged with full context

**Given** an LLM call is made
**When** the response is received
**Then** the following are logged to OpenTelemetry spans:
  - `input_tokens`, `output_tokens`, `total_cost_usd`
  - `model_id`, `task_type`, `agent_id`
  - `farmer_id`, `factory_id` (if available in context)
**And** metrics are exported for cost attribution dashboards

**Given** I need to monitor LLM costs
**When** I view the Grafana dashboard
**Then** I can see cost breakdown by: model, agent_type, factory, date
**And** alerts fire if daily spend exceeds configured threshold

**Model Routing Configuration:**

| Task Type | Primary Model | Fallback | Use Case |
|-----------|---------------|----------|----------|
| triage | claude-3-haiku | gpt-4o-mini | Fast classification/routing |
| extraction | claude-3-haiku | gpt-4o-mini | Structured data extraction |
| diagnosis | claude-3-5-sonnet | gpt-4o | Complex analysis |
| vision | claude-3-5-sonnet | gpt-4o | Image analysis |
| generation | claude-3-5-sonnet | gpt-4o | Content generation |
| rag_query | claude-3-haiku | - | RAG-augmented queries |
| conversational | claude-3-5-sonnet | gpt-4o | Multi-turn voice conversations |

**Technical Notes:**
- OpenRouter provides cost per request in response headers
- Cost attribution uses farmer_id → factory_id mapping from Plantation Model
- Prometheus metrics: `llm_request_cost_usd`, `llm_tokens_total`

---

### Story 0.75.3: Agent Framework (Extractor, Explorer, Generator)

**Story File:** Not yet created | Status: Backlog

As a **developer implementing AI agents**,
I want reusable agent type implementations with standard workflows,
So that I can create new agents by configuration rather than code.

**Acceptance Criteria:**

**Given** an agent is configured with `type: extractor`
**When** the agent runs
**Then** it follows the workflow: fetch -> extract -> validate -> normalize -> output
**And** temperature defaults to 0.1 (deterministic)
**And** output is always JSON

**Given** an agent is configured with `type: explorer`
**When** the agent runs
**Then** it follows the workflow: fetch -> context -> rag -> analyze -> output
**And** temperature defaults to 0.3
**And** RAG is enabled by default

**Given** an agent is configured with `type: generator`
**When** the agent runs
**Then** it follows the workflow: fetch -> context -> prioritize -> generate -> format -> output
**And** temperature defaults to 0.5 (creative)
**And** RAG is enabled for best practices

**Given** an agent is configured with `type: router`
**When** the agent runs
**Then** it follows the workflow: fetch -> classify -> route -> output
**And** temperature defaults to 0.1 (deterministic)
**And** output includes routing decision and confidence

**Given** an agent is configured with `type: conversational`
**When** the agent runs
**Then** it follows the workflow: listen -> transcribe -> classify -> contextualize -> respond -> speak -> [loop]
**And** temperature defaults to 0.4 (natural conversation)
**And** conversation state is maintained across turns
**And** streaming is enabled for low-latency responses
**And** STT/TTS providers are configured per agent

**Given** agent instances are defined in YAML
**When** the AI Model service starts
**Then** all agent instances are loaded and validated
**And** invalid configurations are logged with specific errors

**Given** a workflow is interrupted mid-execution (crash/restart)
**When** the AI Model service restarts
**Then** the workflow resumes from the last MongoDB checkpoint
**And** partial results from completed steps are preserved
**And** the workflow does NOT restart from the beginning
**And** the thread_id enables deterministic resumption

**Given** a new agent type is implemented
**When** the agent is tested
**Then** golden sample test infrastructure exists at `tests/golden/{agent_id}/`
**And** input/expected JSON files follow naming convention (input_001.json, expected_001.json)
**And** pytest fixtures load golden samples for comparison
**And** CI runs golden sample tests on every PR

**Agent Instance Schema:**

```yaml
agent:
  id: "disease-detection-v1"
  type: "explorer"          # extractor | explorer | generator | router | conversational
  version: "1.0.0"
  domain: "knowledge_model" # knowledge_model | action_plan | engagement | voice

input:
  event: "knowledge.analyze.disease"
  schema: "schemas/disease_detection_input.json"

output:
  event: "knowledge.diagnosis.created"
  schema: "schemas/disease_detection_output.json"

mcp_sources:
  - server: "collection-mcp"
    tools: ["get_document", "get_farmer_documents"]
  - server: "plantation-mcp"
    tools: ["get_farmer", "get_farmer_summary"]

llm:
  task_type: "vision"       # overrides default for agent type
  max_tokens: 2000
  temperature: 0.2          # overrides default

prompt:
  id: "disease-detection-prompt"
  version: "latest"         # or specific version

rag:
  enabled: true
  domains: ["plant_diseases"]
  top_k: 5
  threshold: 0.7

error_handling:
  retry_count: 3
  dead_letter_topic: "ai.errors.disease-detection"
```

**Technical Notes:**
- LangChain for simple linear workflows (Extractor)
- LangGraph for complex workflows (Explorer, Generator, Router) with conditional branching
- MongoDB checkpointing via `langgraph.checkpoint.mongodb.MongoDBSaver`
- Checkpoint collection: `ai_model.workflow_checkpoints`
- Golden samples required for all agents before production deployment

---

### Story 0.75.4: Prompt Management (MongoDB Storage)

**Story File:** Not yet created | Status: Backlog

As a **platform operator**,
I want prompts stored in MongoDB with versioning and hot-reload,
So that prompts can be updated without service redeployment.

**Acceptance Criteria:**

**Given** a prompt is defined in Git (`prompts/{domain}/{agent}/`)
**When** CI/CD runs `farmer-cli prompt publish`
**Then** the prompt is stored in MongoDB with status `staged`
**And** version is auto-incremented based on semver

**Given** a staged prompt exists
**When** an operator runs `farmer-cli prompt promote`
**Then** the prompt status changes to `active`
**And** the previous active version changes to `archived`
**And** the cache TTL expires and new prompt is loaded

**Given** an active prompt causes issues
**When** an operator runs `farmer-cli prompt rollback --to-version X.Y.Z`
**Then** the specified version becomes active
**And** the current active version becomes archived
**And** the change is logged with operator ID

**Given** the AI Model service loads prompts at runtime
**When** the cache TTL expires (5 minutes default)
**Then** prompts are reloaded from MongoDB
**And** stale prompts are evicted from cache

**Prompt Document Schema:**
- `prompt_id`, `agent_id`, `version`, `status`
- `content.system_prompt`, `content.template`, `content.output_schema`
- `metadata.author`, `metadata.changelog`, `metadata.git_commit`
- `ab_test.*` - A/B testing configuration (future)

---

### Story 0.75.5: RAG Infrastructure (Pinecone Integration)

**Story File:** Not yet created | Status: Backlog

As an **AI agent**,
I want to retrieve relevant knowledge from a vector database,
So that my responses are informed by domain expertise.

**Acceptance Criteria:**

**Given** an explorer agent has `rag.enabled: true`
**When** the agent builds context
**Then** the RAG engine queries Pinecone with the configured query template
**And** top-k results (default 5) are retrieved
**And** results with similarity below threshold (default 0.7) are filtered out

**Given** knowledge documents are uploaded via Admin UI
**When** the embedding pipeline runs
**Then** documents are chunked by section (500 tokens with 100 token overlap)
**And** `text-embedding-3-small` (OpenAI) is used for embeddings
**And** vectors are stored in Pinecone with metadata (domain, version, doc_id)
**And** the document status in MongoDB changes to `staged`

**Given** a knowledge document is ready for staging
**When** I run `farmer-cli knowledge stage --doc <path>`
**Then** the document is validated for structure and content
**And** embeddings are generated and uploaded to staged namespace
**And** validation errors are reported before upload

**Given** I need to manage knowledge versions
**When** I run farmer-cli knowledge commands
**Then** the following commands are available:
  - `farmer-cli knowledge validate --doc <path>` - validate document structure
  - `farmer-cli knowledge stage --doc <path>` - embed and upload to staged
  - `farmer-cli knowledge promote --doc <path>` - promote staged to active
  - `farmer-cli knowledge rollback --to-version <X.Y.Z>` - rollback to previous
  - `farmer-cli knowledge versions --doc <path>` - list all versions
**And** progress and status are logged to console

**Given** a staged namespace is ready for promotion
**When** an operator promotes the namespace
**Then** the active namespace pointer is updated
**And** queries route to the new namespace
**And** the previous namespace is archived (kept for rollback)

**Given** the AI Model needs RAG during an LLM call
**When** the query is executed
**Then** retrieved context is injected into the prompt template
**And** retrieval latency is logged as a span
**And** relevance scores are included in traces

**Given** a query returns low-relevance results (score < 0.7)
**When** the agent processes results
**Then** the agent is notified of low confidence
**And** the agent can proceed without RAG or flag for review

**Given** Pinecone is unavailable
**When** a RAG query is attempted
**Then** the query fails gracefully
**And** the agent proceeds without RAG enrichment (degraded mode)
**And** an alert is logged

**Knowledge Domains:**

| Domain | Content | Used By | Curator |
|--------|---------|---------|---------|
| plant_diseases | Symptoms, identification guides, disease lifecycle | Disease Detection Agent | Agronomists |
| tea_cultivation | Best practices, seasonal guidance, soil management | Action Plan, Weather Analyzer | Agronomists |
| weather_patterns | Regional climate impacts, crop sensitivity by season | Weather Impact Analyzer | Agronomists |
| harvesting_techniques | Proper plucking methods, handling best practices | Technique Assessment Agent | Agronomists |
| quality_standards | Grading criteria, buyer expectations, market requirements | Extraction agents | Quality team |
| regional_context | Local practices, cultural factors, cooperative norms | Action Plan Generator | Field team |

**Technical Notes:**
- Pinecone index: `farmer-power-knowledge`
- Embedding model: `text-embedding-3-small` (OpenAI)
- Namespace per domain for isolated queries
- Knowledge curated by agronomists (not auto-generated)
- A/B testing supported via namespace versioning

---

### Story 0.75.6: AI Model MCP Clients

**Story File:** Not yet created | Status: Backlog

As an **AI agent**,
I want to fetch data from other domain models via MCP,
So that I can access farmer context, quality documents, and analyses.

**Acceptance Criteria:**

**Given** an agent needs farmer context
**When** it calls `plantation-mcp.get_farmer(farmer_id)`
**Then** the request is routed via DAPR service invocation
**And** the response is deserialized and available in the workflow
**And** the call is traced with MCP tool name

**Given** an agent needs quality document data
**When** it calls `collection-mcp.get_document(doc_id)`
**Then** the full document with images and metadata is returned
**And** large images are fetched as blob URLs (not inline)

**Given** an MCP call fails
**When** the error is caught
**Then** the workflow can decide to retry, skip, or fail
**And** the error is logged with trace context and MCP server/tool info

**MCP Clients Required:**
- `collection-mcp`: get_document, get_farmer_documents
- `plantation-mcp`: get_farmer, get_farmer_summary, get_factory
- `knowledge-mcp`: get_diagnosis, get_farmer_analyses (Epic 5)
- `engagement-mcp`: get_farmer_progress (Epic 12)

**Technical Notes:**
- Uses `GrpcMcpClient` from `fp-common` (Story 0.1)
- DAPR service invocation for all MCP calls
- Timeout: 30 seconds per call
- Retry: 3 attempts with backoff

---

### Story 0.75.7: AI Security Patterns

**Story File:** Not yet created | Status: Backlog

As a **security engineer**,
I want AI workflows to prevent prompt injection and protect PII,
So that the system is secure by design.

**Acceptance Criteria:**

**Given** user-controlled input is included in prompts
**When** the prompt is constructed
**Then** input is sanitized and delimited with clear boundaries
**And** XML/markdown escaping is applied to prevent injection
**And** input length is validated against maximum limits

**Given** farmer PII (name, phone, GPS coordinates) is available
**When** prompts are constructed
**Then** PII is NOT included in prompts (use farmer_id reference only)
**And** MCP calls retrieve PII only when needed for output formatting
**And** prompts use pseudonymized identifiers

**Given** an LLM generates output
**When** the output is processed
**Then** output is validated against expected schema
**And** output is sanitized before storage or display
**And** no sensitive patterns (API keys, tokens, internal URLs) are leaked

**Given** a prompt injection attempt is detected
**When** the input validation runs
**Then** the request is rejected with a safe error message
**And** the attempt is logged with trace context for security review
**And** no internal system details are revealed in the error

**Given** PII must appear in farmer-facing output (e.g., SMS message)
**When** the generator formats the message
**Then** PII is retrieved via MCP at the last possible moment
**And** PII is never logged or traced
**And** PII is never sent to the LLM

**Security Controls:**

| Control | Implementation |
|---------|----------------|
| Input sanitization | Escape XML/markdown, length limits, character validation |
| PII protection | farmer_id only in prompts, MCP for PII retrieval |
| Output validation | JSON schema validation, pattern matching for secrets |
| Injection detection | Boundary markers, instruction detection heuristics |
| Audit logging | Security events to separate audit log, no PII |

**Technical Notes:**
- Input sanitization utilities in `fp-common/security/prompt_sanitizer.py`
- PII patterns defined in security configuration (phone, email, GPS regex)
- OWASP LLM Top 10 compliance checklist for each agent
- Security review required for agents handling sensitive data

---

### Story 0.75.8: Knowledge Model Agent Configurations

**Story File:** Not yet created | Status: Backlog

As a **Knowledge Model service**,
I want pre-configured agents for quality diagnosis,
So that I can invoke diagnosis workflows without implementing AI infrastructure.

**Acceptance Criteria:**

**Given** the AI Model service starts
**When** Knowledge Model agents are loaded
**Then** the following agents are available:
  - `triage-agent-v1` (router type)
  - `disease-detection-v1` (explorer type with vision)
  - `weather-impact-v1` (explorer type)
  - `technique-assessment-v1` (explorer type)
  - `trend-analysis-v1` (extractor type)

**Given** the Knowledge Model invokes `triage-agent-v1`
**When** the agent processes aggregated quality events
**Then** it classifies the probable cause: disease, weather, technique, trend, unknown
**And** assigns confidence score (0.0-1.0)
**And** routes to appropriate analyzer(s) based on confidence threshold

**Given** the Knowledge Model invokes `disease-detection-v1`
**When** the agent processes events with image references
**Then** images are fetched and analyzed using vision LLM
**And** RAG queries `plant_diseases` domain for identification
**And** output matches the disease detection schema from Epic 5.3

**Given** the Knowledge Model invokes `weather-impact-v1`
**When** the agent processes quality events
**Then** weather data is fetched via MCP (past 14 days)
**And** lag correlation (3-7 days) is applied per weather event type
**And** RAG queries `weather_patterns` domain
**And** output matches the weather impact schema from Epic 5.4

**Given** the Knowledge Model invokes `technique-assessment-v1`
**When** the agent processes quality events
**Then** historical patterns are fetched via MCP
**And** leaf_type_distribution is analyzed against thresholds
**And** RAG queries `harvesting_techniques` domain
**And** output matches the technique assessment schema from Epic 5.5

**Given** the Knowledge Model invokes `trend-analysis-v1`
**When** the agent processes farmer history
**Then** statistical analysis is performed (pandas)
**And** LLM interprets patterns and adds context
**And** output matches the trend analysis schema from Epic 5.6

---

#### Agent Configuration: Triage Agent

```yaml
agent:
  id: "triage-agent-v1"
  type: "router"
  version: "1.0.0"
  domain: "knowledge_model"
  description: "Classifies quality issues and routes to specialist analyzers"

input:
  event: "knowledge.triage.requested"
  schema:
    type: object
    properties:
      farmer_id: { type: string }
      events: { type: array, items: { $ref: "#/definitions/QualityEvent" } }
      aggregation_id: { type: string }

output:
  event: "knowledge.triage.completed"
  schema:
    type: object
    properties:
      classification: { enum: [disease, weather, technique, trend, unknown] }
      confidence: { type: number, minimum: 0, maximum: 1 }
      route_to: { type: array, items: { type: string } }
      parallel: { type: boolean }

routing_rules:
  - condition: "confidence >= 0.7"
    action: "route_single"
    description: "High confidence - route to single analyzer"
  - condition: "confidence < 0.7 AND confidence >= 0.3"
    action: "route_parallel"
    description: "Medium confidence - route to multiple analyzers"
  - condition: "confidence < 0.3"
    action: "flag_review"
    publish_event: "knowledge.needs_review"
    description: "Low confidence - flag for human review, still analyze"

llm:
  task_type: "triage"
  max_tokens: 500
  temperature: 0.1

prompt:
  id: "triage-prompt"
  few_shot_examples: true
  example_source: "validated_diagnoses"

rag:
  enabled: false  # Triage doesn't need RAG

error_handling:
  retry_count: 2
  dead_letter_topic: "ai.errors.triage"

performance:
  max_latency_ms: 2000
```

---

#### Agent Configuration: Disease Detection Agent

```yaml
agent:
  id: "disease-detection-v1"
  type: "explorer"
  version: "1.0.0"
  domain: "knowledge_model"
  description: "Identifies plant diseases from visual symptoms"

input:
  event: "knowledge.analyze.disease"
  schema:
    type: object
    properties:
      farmer_id: { type: string }
      document_ids: { type: array, items: { type: string } }
      image_refs: { type: array, items: { type: string } }

output:
  event: "knowledge.diagnosis.disease"
  schema:
    $ref: "schemas/disease_detection_output.json"

mcp_sources:
  - server: "collection-mcp"
    tools: ["get_document"]

llm:
  task_type: "vision"
  max_tokens: 2000
  temperature: 0.2

prompt:
  id: "disease-detection-prompt"

rag:
  enabled: true
  domains: ["plant_diseases"]
  top_k: 5
  threshold: 0.7

vision:
  max_images: 10
  resize_max_px: 1024
  supported_formats: ["jpg", "png", "webp"]

error_handling:
  retry_count: 3
  dead_letter_topic: "ai.errors.disease-detection"
```

---

#### Agent Configuration: Weather Impact Analyzer

```yaml
agent:
  id: "weather-impact-v1"
  type: "explorer"
  version: "1.0.0"
  domain: "knowledge_model"
  description: "Correlates weather events with quality issues"

input:
  event: "knowledge.analyze.weather"
  schema:
    type: object
    properties:
      farmer_id: { type: string }
      document_ids: { type: array, items: { type: string } }
      delivery_date: { type: string, format: date }

output:
  event: "knowledge.diagnosis.weather"
  schema:
    $ref: "schemas/weather_impact_output.json"

mcp_sources:
  - server: "collection-mcp"
    tools: ["get_document", "get_weather_data"]
  - server: "plantation-mcp"
    tools: ["get_farmer"]

llm:
  task_type: "diagnosis"
  max_tokens: 1500
  temperature: 0.2

prompt:
  id: "weather-impact-prompt"

rag:
  enabled: true
  domains: ["weather_patterns", "tea_cultivation"]
  top_k: 5
  threshold: 0.7

weather_correlation:
  lookback_days: 14
  lag_weights:
    heavy_rain:
      threshold: 50  # mm/day
      lag_days: [3, 4, 5]
      weights: [0.3, 0.5, 0.2]
    frost:
      threshold: 2  # °C (below)
      lag_days: [3, 4, 5]
      weights: [0.3, 0.5, 0.2]
    drought:
      threshold: 5  # consecutive days no rain
      lag_days: [4, 5, 6, 7]
      weights: [0.2, 0.3, 0.3, 0.2]
    high_humidity:
      threshold: 90  # percentage
      lag_days: [2, 3, 4]
      weights: [0.3, 0.4, 0.3]

error_handling:
  retry_count: 3
  dead_letter_topic: "ai.errors.weather-impact"
```

---

#### Agent Configuration: Technique Assessment Agent

```yaml
agent:
  id: "technique-assessment-v1"
  type: "explorer"
  version: "1.0.0"
  domain: "knowledge_model"
  description: "Identifies harvesting and handling problems"

input:
  event: "knowledge.analyze.technique"
  schema:
    type: object
    properties:
      farmer_id: { type: string }
      document_ids: { type: array, items: { type: string } }
      leaf_type_distribution: { type: object }

output:
  event: "knowledge.diagnosis.technique"
  schema:
    $ref: "schemas/technique_assessment_output.json"

mcp_sources:
  - server: "collection-mcp"
    tools: ["get_document", "get_farmer_documents"]
  - server: "plantation-mcp"
    tools: ["get_farmer"]

llm:
  task_type: "diagnosis"
  max_tokens: 1500
  temperature: 0.2

prompt:
  id: "technique-assessment-prompt"

rag:
  enabled: true
  domains: ["harvesting_techniques"]
  top_k: 5
  threshold: 0.7

technique_thresholds:
  coarse_leaf:
    threshold: 30  # percentage
    condition: "over_plucking"
  banji:
    threshold: 20  # percentage
    condition: "poor_timing"
  damaged_leaves:
    threshold: 15  # percentage
    condition: "handling_damage"

historical_comparison:
  lookback_days: 30
  min_deliveries: 3

error_handling:
  retry_count: 3
  dead_letter_topic: "ai.errors.technique-assessment"
```

---

#### Agent Configuration: Trend Analysis Agent

```yaml
agent:
  id: "trend-analysis-v1"
  type: "extractor"
  version: "1.0.0"
  domain: "knowledge_model"
  description: "Detects patterns in farmer quality history"

input:
  event: "knowledge.analyze.trend"
  schema:
    type: object
    properties:
      farmer_id: { type: string }
      analysis_period_days: { type: integer, default: 30 }

output:
  event: "knowledge.diagnosis.trend"
  schema:
    $ref: "schemas/trend_analysis_output.json"

mcp_sources:
  - server: "collection-mcp"
    tools: ["get_farmer_documents"]
  - server: "plantation-mcp"
    tools: ["get_farmer", "get_regional_stats"]

llm:
  task_type: "extraction"
  max_tokens: 1000
  temperature: 0.1

prompt:
  id: "trend-interpretation-prompt"
  description: "Used only for pattern interpretation, not calculation"

rag:
  enabled: false  # Statistical analysis, not knowledge-based

trend_calculation:
  min_deliveries: 5
  decline_threshold: 10  # percentage drop over period
  comparison_window_weeks: 4
  seasonal_adjustment: true

alert_conditions:
  - condition: "trend_direction == 'declining' AND decline_rate > 10"
    severity: "moderate"
    publish_event: "knowledge.trend_alert"
  - condition: "yield_percentile < 25"
    severity: "low"
    include_in_diagnosis: true

schedule:
  cron: "0 0 * * 0"  # Sunday midnight
  description: "Weekly trend analysis for active farmers"

error_handling:
  retry_count: 2
  dead_letter_topic: "ai.errors.trend-analysis"
```

---

### Story 0.75.9: Triage Feedback Loop

**Story File:** Not yet created | Status: Backlog

As a **platform operator**,
I want triage accuracy to improve over time,
So that routing decisions become more accurate based on agronomist feedback.

**Acceptance Criteria:**

**Given** an agronomist reviews a diagnosis
**When** they confirm or correct the triage classification
**Then** the feedback is stored with: original_classification, corrected_classification, confidence, notes

**Given** feedback is accumulated over time
**When** the weekly aggregation job runs
**Then** patterns are identified (≥5 similar corrections, >80% agreement)
**And** candidate few-shot examples are generated

**Given** new few-shot examples are generated
**When** an operator reviews them
**Then** examples can be approved, rejected, or modified
**And** approved examples are staged for A/B testing

**Given** a new prompt version with updated examples exists
**When** A/B testing is enabled
**Then** 10% of traffic uses the new version
**And** accuracy metrics are compared after 1 week
**And** better-performing version is promoted

**Feedback Schema:**

```json
{
  "diagnosis_id": "uuid",
  "original_classification": "disease",
  "corrected_classification": "weather",
  "agronomist_id": "user-123",
  "notes": "Symptoms looked like disease but timing matches heavy rain 4 days prior",
  "created_at": "2025-12-28T10:00:00Z"
}
```

**Metrics Tracked:**

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| Correction Rate | % of diagnoses corrected | >20% triggers review |
| Pattern Detection | New correction patterns identified | Weekly report |
| Prompt Version Accuracy | Precision/recall per category per version | Degradation >5% |

---

### Story 0.75.10: Action Plan Agent Configuration

**Story File:** Not yet created | Status: Backlog

As an **Action Plan Model service**,
I want a pre-configured agent for generating personalized action plans,
So that I can invoke plan generation without implementing AI infrastructure.

**Acceptance Criteria:**

**Given** the AI Model service starts
**When** Action Plan agents are loaded
**Then** the following agent is available:
  - `action-plan-generator-v1` (generator type)

**Given** the Action Plan Model invokes `action-plan-generator-v1`
**When** the agent processes a farmer's diagnoses and context
**Then** it generates personalized recommendations
**And** output includes detailed report, SMS summary, and TTS script
**And** content is in the farmer's preferred language

---

#### Agent Configuration: Action Plan Generator

```yaml
agent:
  id: "action-plan-generator-v1"
  type: "generator"
  version: "1.0.0"
  domain: "action_plan"
  description: "Generates personalized weekly improvement recommendations"

input:
  event: "action_plan.generation.requested"
  schema:
    type: object
    properties:
      farmer_id: { type: string }
      diagnoses: { type: array, items: { $ref: "#/definitions/Diagnosis" } }
      week_number: { type: integer }

output:
  event: "action_plan.generated"
  schema:
    type: object
    properties:
      farmer_id: { type: string }
      recommendations: { type: array, maxItems: 3 }
      detailed_report: { type: string }
      sms_summary: { type: string, maxLength: 160 }
      tts_script: { type: string }
      language: { type: string }

mcp_sources:
  - server: "knowledge-mcp"
    tools: ["get_farmer_analyses"]
  - server: "plantation-mcp"
    tools: ["get_farmer_summary"]
  - server: "collection-mcp"
    tools: ["get_recent_quality_events"]

llm:
  task_type: "generation"
  max_tokens: 2000
  temperature: 0.5

prompt:
  id: "action-plan-generator-prompt"

rag:
  enabled: true
  domains: ["tea_cultivation", "regional_context"]
  top_k: 5
  threshold: 0.7

farm_scale_adaptation:
  smallholder:
    focus: ["manual_techniques", "low_cost"]
    language_level: "simple"
  medium:
    focus: ["basic_tools", "labor_coordination"]
    language_level: "standard"
  estate:
    focus: ["workforce", "equipment", "roi"]
    language_level: "technical"

output_formats:
  detailed_report:
    min_words: 300
    max_words: 500
  sms_summary:
    max_chars: 160
    required_elements: ["grade", "one_action", "encouragement"]
  tts_script:
    max_duration_seconds: 180
    ssml_enabled: true

multilingual:
  supported: ["en", "sw", "ki", "luo"]
  fallback: "en"
  quality_check: true

error_handling:
  retry_count: 3
  dead_letter_topic: "ai.errors.action-plan"
```

---

### Story 0.75.11: Voice Advisor Agent Configuration

**Story File:** Not yet created | Status: Backlog

As a **Voice Advisor service**,
I want a pre-configured conversational agent for voice interactions,
So that farmers can have natural voice conversations about quality improvement.

**Acceptance Criteria:**

**Given** the AI Model service starts
**When** Voice Advisor agents are loaded
**Then** the following agent is available:
  - `voice-advisor-v1` (conversational type)

**Given** the Voice Advisor service invokes `voice-advisor-v1`
**When** the agent processes a farmer's voice input
**Then** it transcribes speech to text
**And** classifies intent
**And** gathers context via MCP
**And** generates personalized response
**And** converts response to speech
**And** manages conversation state across turns

---

#### Agent Configuration: Voice Advisor

```yaml
agent:
  id: "voice-advisor-v1"
  type: "conversational"
  version: "1.0.0"
  domain: "voice"
  description: "Interactive voice quality advisor for farmers"

input:
  trigger: "inbound_call"
  audio_format: "pcm_8khz"

output:
  audio_format: "mp3"
  streaming: true

mcp_sources:
  - server: "plantation-mcp"
    tools: ["get_farmer_summary"]
  - server: "collection-mcp"
    tools: ["get_recent_quality_events"]
  - server: "knowledge-mcp"
    tools: ["get_farmer_analyses"]
  - server: "action-plan-mcp"
    tools: ["get_current_action_plan"]

llm:
  task_type: "conversational"
  max_tokens: 150  # Short for spoken delivery
  temperature: 0.4
  streaming: true

prompt:
  id: "voice-advisor-prompt"
  intents:
    - quality_question
    - action_plan_query
    - delivery_status
    - general_help
    - clarification
    - goodbye
    - out_of_scope

stt:
  provider: "google"
  model: "chirp_2"
  language: "sw-KE"
  sample_rate: 8000
  enhanced_model: true
  phrase_hints: ["chai", "majani", "primary", "secondary", "grade", "ubora"]
  confidence_threshold: 0.6

tts:
  provider: "google"
  voice: "sw-KE-Wavenet-A"
  speaking_rate: 1.0
  pitch: 0
  ssml_enabled: true

conversation:
  max_turns: 5
  max_duration_seconds: 180
  greeting_template: "Habari {farmer_name}! Mimi ni mshauri wako wa ubora wa chai. Ninawezaje kukusaidia leo?"
  closing_template: "Asante kwa kupiga simu. Kwa msaada zaidi, piga tena wakati wowote. Kwaheri!"
  barge_in: true
  clarification_limit: 2

latency:
  target_e2e_ms: 2000
  first_chunk_ms: 1000
  filler_phrases:
    - "Ngoja kidogo..."
    - "Acha nifikirie..."

fallback:
  sms_enabled: true
  sms_trigger_after_failed_clarifications: 3
  notification_service: "notification-model"

rag:
  enabled: false  # Context from MCP is sufficient for conversations

error_handling:
  retry_count: 2
  dead_letter_topic: "ai.errors.voice-advisor"
  graceful_degradation:
    stt_unavailable: "sms_fallback"
    llm_unavailable: "prerecorded_message"
    tts_unavailable: "sms_only"
```

---

## Dependencies

| This Epic Depends On | Reason |
|---------------------|--------|
| Epic 0 (Story 0.1) | MCP gRPC Infrastructure |
| Epic 1 | Plantation MCP Server for farmer context |
| Epic 2 | Collection MCP Server for document access |

| Epics That Depend On This | Reason |
|--------------------------|--------|
| Epic 5 (Knowledge Model) | Uses AI Model for diagnosis agents |
| Epic 6 (Action Plans) | Uses AI Model for plan generation |
| Epic 8 (Voice Advisor) | Uses AI Model for conversational AI |
| Epic 12 (Engagement) | Uses AI Model for motivation engine |

---

## Agent Configuration Summary

| Agent ID | Type | Domain | LLM Task | RAG Domains |
|----------|------|--------|----------|-------------|
| triage-agent-v1 | router | knowledge_model | triage | - |
| disease-detection-v1 | explorer | knowledge_model | vision | plant_diseases |
| weather-impact-v1 | explorer | knowledge_model | diagnosis | weather_patterns, tea_cultivation |
| technique-assessment-v1 | explorer | knowledge_model | diagnosis | harvesting_techniques |
| trend-analysis-v1 | extractor | knowledge_model | extraction | - |
| action-plan-generator-v1 | generator | action_plan | generation | tea_cultivation, regional_context |
| voice-advisor-v1 | conversational | voice | conversational | - |

> **Future agents** for Epic 12 (Engagement Model) will be added when that epic is detailed.

---

## Retrospective

**Story File:** Not yet created | Status: Backlog

---

_Last Updated: 2025-12-28_
