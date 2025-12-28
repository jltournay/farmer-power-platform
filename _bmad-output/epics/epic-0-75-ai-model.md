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

**Given** an agent specifies `task_type: extraction`
**When** the LLM gateway routes the request
**Then** the request is sent to `anthropic/claude-3-haiku` (fast, cheap)
**And** token usage and cost are logged with trace context

**Given** an agent specifies `task_type: diagnosis`
**When** the LLM gateway routes the request
**Then** the request is sent to `anthropic/claude-3-5-sonnet` (accurate)
**And** fallback to `openai/gpt-4o` if Anthropic is unavailable

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

| Task Type | Primary Model | Fallback |
|-----------|---------------|----------|
| extraction | claude-3-haiku | gpt-4o-mini |
| diagnosis | claude-3-5-sonnet | gpt-4o |
| generation | claude-3-5-sonnet | gpt-4o |
| rag_query | claude-3-haiku | - |

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
- `agent.id`, `agent.type`, `agent.version`
- `input.event`, `input.schema`
- `output.event`, `output.schema`
- `mcp_sources[]` - servers and tools to use
- `llm.*` - model routing overrides
- `prompt.*` - template references
- `rag.*` - RAG configuration
- `error_handling.*` - retry and dead letter config

**Technical Notes:**
- LangChain for simple linear workflows (Extractor)
- LangGraph for complex workflows (Explorer, Generator) with conditional branching
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

**Given** a prompt is defined in Git (`prompts/{type}/{agent}/`)
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
**Then** documents are chunked by section (not arbitrary length)
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

**Knowledge Domains:**

| Domain | Content | Used By |
|--------|---------|---------|
| plant_diseases | Symptoms, identification, treatments | diagnosis agents |
| tea_cultivation | Best practices, seasonal guidance | action plan, weather |
| weather_patterns | Regional climate, crop impact | weather analyzer |
| quality_standards | Grading criteria, buyer expectations | extraction, market |
| regional_context | Local practices, cultural factors | action plan |

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
- `knowledge-mcp`: get_diagnosis (future - Epic 5)
- `engagement-mcp`: get_farmer_progress (future - Epic 12)

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

## Retrospective

**Story File:** Not yet created | Status: Backlog

---

_Last Updated: 2025-12-28_
