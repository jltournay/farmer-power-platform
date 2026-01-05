# Epic 2: Quality Data Ingestion

## Overview

This epic focuses on building the Collection Model service - the central data ingestion layer for the Farmer Power Platform. It enables automatic ingestion of quality grading data from multiple sources (QC Analyzer results, exception images, weather APIs, market prices) through a generic, configuration-driven framework.

The Collection Model supports both push (Event Grid blob triggers) and pull (scheduled API polling) modes, with LLM-powered data extraction, deduplication, and domain event emission for downstream services.

---

### Story 2.1: Collection Model Service Setup

**[📄 Story File](../sprint-artifacts/2-1-collection-model-service-setup.md)** | Status: Done

As a **platform operator**,
I want the Collection Model service deployed with DAPR sidecar, MongoDB, and Redis pub/sub,
So that quality grading data can be ingested, stored, and domain events emitted to downstream services.

**Acceptance Criteria:**

**Given** the Kubernetes cluster is running with DAPR installed
**When** the Collection Model service is deployed
**Then** the service starts successfully with health check endpoint returning 200
**And** the DAPR sidecar is injected and connected
**And** MongoDB connection is established (verified via connection test)
**And** Redis pub/sub component is configured and connected
**And** OpenTelemetry traces are emitted for all operations

**Given** the service is running
**When** the DAPR pub/sub is tested
**Then** messages can be published to topics: `collection.document.stored`, `collection.poor_quality_detected`
**And** topic subscriptions are registered with DAPR

**Given** Azure Event Grid subscription is configured
**When** a blob is created in `qc-analyzer-results` or `qc-analyzer-exceptions` containers
**Then** Event Grid sends HTTP POST to the service's `/api/events/blob-created` endpoint
**And** the webhook validates Event Grid subscription handshake

**Technical Notes:**
- Python FastAPI with async handlers
- DAPR pub/sub component: Redis (internal domain events)
- External events: Azure Event Grid webhook (blob triggers)
- Health endpoints: `/health` and `/ready`
- Environment: farmer-power-{env} namespace
- Proto: `farmer_power.collection.v1`

**Infrastructure (Epic 0 prerequisite):**
- Azure Event Grid System Topic for storage account (Epic 0)
- Event subscriptions filtering on `Microsoft.Storage.BlobCreated` (Epic 0)
- Webhook endpoint configured after service deployment

---

### Story 2.2: Source Configuration CLI

**[📄 Story File](../sprint-artifacts/2-2-source-configuration-cli.md)** | Status: Done

As a **platform operator**,
I want a CLI tool to manage data source configurations,
So that new data sources can be onboarded without code changes.

**Acceptance Criteria:**

**Given** the `fp-source-config` CLI is installed
**When** I run `fp-source-config deploy sources.yaml`
**Then** the YAML file is validated against the SourceConfig schema
**And** configurations are upserted to MongoDB collection `source_configs`
**And** a summary is printed: sources added, updated, unchanged

**Given** a source configuration YAML file
**When** I run `fp-source-config validate sources.yaml`
**Then** the file is validated without deploying
**And** validation errors are printed with line numbers
**And** exit code is 0 for valid, 1 for invalid

**Given** source configurations exist in MongoDB
**When** I run `fp-source-config list`
**Then** all configured sources are listed with: source_id, source_type, trigger_mode, status

**Given** a source_id exists
**When** I run `fp-source-config get <source_id>`
**Then** the full configuration is printed as YAML

**Given** a source_id exists
**When** I run `fp-source-config disable <source_id>`
**Then** the source is marked inactive (enabled: false)
**And** no new ingestion jobs will be triggered for this source

**Technical Notes:**
- CLI framework: Typer
- Config schema defined in `fp-common` as Pydantic models
- MongoDB collection: `source_configs`
- SourceConfig fields: source_id, source_type, trigger_mode, container_pattern, llm_extraction_prompt_id, enabled

---

### Story 2.3: Event Grid Trigger Handler

**[📄 Story File](../sprint-artifacts/2-3-event-grid-trigger-handler.md)** | Status: Done

As a **Collection Model service**,
I want to receive Azure Event Grid blob-created events,
So that new QC Analyzer uploads trigger automatic ingestion.

**Acceptance Criteria:**

**Given** the Collection Model service is running
**When** Event Grid sends a subscription validation request
**Then** the service responds with the validationResponse
**And** the subscription is confirmed

**Given** a blob is created in `qc-analyzer-results` container
**When** Event Grid sends blob-created event
**Then** the event is parsed: container, blob_path, content_length, timestamp
**And** source_config is looked up by container pattern match
**And** if source is enabled, ingestion job is queued

**Given** the blob matches source_config with trigger_mode=BLOB_TRIGGER
**When** the event is processed
**Then** blob metadata is extracted: source_type, device_id (from path)
**And** processing_status is set to "queued" in MongoDB
**And** the blob is queued for content processing

**Given** no source_config matches the blob container
**When** the event is processed
**Then** the event is logged with warning "No matching source config"
**And** no further processing occurs
**And** metrics track unmatched events

**Given** the same blob event is received twice (Event Grid retry)
**When** processing is attempted
**Then** idempotency check detects duplicate (by blob_path + etag)
**And** duplicate is skipped with log "Already processed"

**Technical Notes:**
- Endpoint: POST `/api/events/blob-created`
- Event Grid schema: EventGridEvent or CloudEvents v1.0
- Idempotency: MongoDB unique index on (blob_path, blob_etag)
- Async processing: queue to internal task queue after validation

---

### Story 2.4: Generic Content Processing Framework + JSON Processor

**[📄 Story File](../sprint-artifacts/2-4-generic-content-processing-framework.md)** | Status: Done

As a **platform operator**,
I want a generic, configuration-driven content processing framework,
So that new data sources can be processed without code changes to the core pipeline.

As a **platform data analyst**,
I want QC Analyzer JSON results automatically ingested,
So that bag summaries and grading data are stored for analysis.

**Acceptance Criteria:**

**Framework (Generic):**

**Given** an ingestion job is dequeued for processing
**When** the processor is selected
**Then** the `transformation.agent` field from SourceConfig determines which ContentProcessor is used
**And** no hardcoded source_type checks exist in the pipeline
**And** the ProcessorRegistry returns the appropriate processor class

**Given** a new source type needs to be added
**When** a developer implements ContentProcessor
**Then** they only need to:
  1. Create a new processor class implementing `ContentProcessor` ABC
  2. Register it in `ProcessorRegistry` with the `transformation.agent` key
  3. Add source configuration YAML with matching `transformation.agent`
**And** no changes to the core pipeline code are required

**Given** an unknown `transformation.agent` value is encountered
**When** the processor lookup fails
**Then** processing_status is set to "failed"
**And** error details include: "No processor registered for agent: {agent_name}"
**And** the job is not retried (configuration error, not transient)

**JSON Processor (QC Analyzer Results):**

**Given** a JSON blob is queued for processing
**When** the `JsonExtractionProcessor` is invoked
**Then** the blob is downloaded from Azure Blob Storage (async streaming)
**And** the raw JSON is stored in `raw_documents` collection
**And** processing_status is updated to "extracting"

**Given** the raw JSON is stored
**When** LLM extraction runs with the configured prompt (from `transformation.llm_prompt_id`)
**Then** structured data is extracted: bag_id, farmer_id, collection_point_id, timestamp, overall_classification, leaf_assessments[]
**And** bag_summary is calculated: primary_percentage, leaf_type_distribution, overall_grade
**And** extracted data is stored in `quality_events` collection

**Given** leaf_type_distribution is calculated
**When** the TBK grade is determined
**Then** the grade follows the TBK specification:
  - Grade 1 (Premium): ≥85% primary AND fine_leaf ≥60%
  - Grade 2 (Standard): ≥70% primary OR fine_leaf ≥40%
  - Grade 3 (Below Standard): <70% primary AND fine_leaf <40%

**Given** extraction succeeds
**When** the quality_event is stored
**Then** a `collection.document.stored` domain event is emitted via Redis pub/sub
**And** processing_status is updated to "completed"
**And** the event payload includes: document_id, source_id, farmer_id

**Given** LLM extraction fails
**When** error is detected
**Then** processing_status is set to "failed"
**And** error details are stored: error_type, error_message, retry_count
**And** document is queued for retry (max 3 attempts)

**Technical Notes:**

**Framework Architecture:**
```
processors/
├── __init__.py
├── base.py              # ContentProcessor ABC, ProcessorResult
├── registry.py          # ProcessorRegistry (agent → processor mapping)
├── json_extraction.py   # JsonExtractionProcessor
└── zip_extraction.py    # ZipExtractionProcessor (Story 2.5)
```

**ContentProcessor ABC:**
```python
from abc import ABC, abstractmethod
from collection_model.domain.ingestion_job import IngestionJob

class ContentProcessor(ABC):
    """Base class for all content processors."""

    @abstractmethod
    async def process(
        self,
        job: IngestionJob,
        source_config: dict
    ) -> ProcessorResult:
        """Process the ingestion job according to source config."""
        pass

    @abstractmethod
    def supports_content_type(self, content_type: str) -> bool:
        """Check if processor supports the given content type."""
        pass
```

**ProcessorRegistry:**
```python
class ProcessorRegistry:
    """Maps transformation.agent values to processor classes."""

    _processors: dict[str, type[ContentProcessor]] = {}

    @classmethod
    def register(cls, agent_name: str, processor_class: type[ContentProcessor]):
        cls._processors[agent_name] = processor_class

    @classmethod
    def get_processor(cls, agent_name: str) -> ContentProcessor:
        if agent_name not in cls._processors:
            raise ProcessorNotFoundError(f"No processor for agent: {agent_name}")
        return cls._processors[agent_name]()

# Registration (in __init__.py or startup)
ProcessorRegistry.register("collection-json-extraction", JsonExtractionProcessor)
ProcessorRegistry.register("collection-zip-extraction", ZipExtractionProcessor)
```

**Pipeline Integration:**
```python
# In content_processor_worker.py - NO hardcoded source checks
async def process_job(job: IngestionJob, source_config: dict):
    agent = source_config["transformation"]["agent"]
    processor = ProcessorRegistry.get_processor(agent)  # Pure config-driven
    result = await processor.process(job, source_config)
    return result
```

- Azure Blob SDK: async download with streaming
- LLM extraction via OpenRouter (prompt from MongoDB `prompts` collection)
- MongoDB collections: raw_documents, quality_events
- Deduplication handled in Story 2.6

---

### Story 2.5: ZIP Content Processor for Exception Images

**[📄 Story File](../sprint-artifacts/2-5-qc-analyzer-exception-images-ingestion.md)** | Status: Done

As a **Knowledge Model AI agent**,
I want secondary leaf exception images automatically extracted and stored,
So that I can analyze poor quality samples with visual evidence.

**Acceptance Criteria:**

**Given** the Generic Content Processing Framework exists (Story 2.4)
**When** a ZIP blob is queued for processing with `processor_type: zip-extraction`
**Then** the `ZipExtractionProcessor` is selected via source config
**And** no changes to the core pipeline are required

**Given** the `ZipExtractionProcessor` is invoked
**When** the blob is downloaded
**Then** the ZIP is extracted in memory (streaming, no disk write)
**And** `manifest.json` is validated against `generic-zip-manifest.schema.json`
**And** `payload` is validated against source-specific schema (`qc-exceptions-manifest.json`)

**Given** the manifest contains documents with file roles
**When** files are processed per `manifest.documents[]`
**Then** files with `role: image` are extracted to `exception-images` container
**And** blob path follows: `exception-images/{plantation_id}/{batch_id}/{document_id}.jpg`
**And** files with `role: metadata` are parsed and merged into document attributes

**Given** images and metadata are extracted
**When** documents are stored
**Then** a `DocumentIndex` is created in the `documents` collection for each manifest document
**And** `linkage_fields` contains: `plantation_id`, `batch_id`, `factory_id`, `batch_result_ref`
**And** `extracted_fields` contains image attributes: `quality_grade`, `confidence`, `leaf_type`, `coarse_subtype`
**And** `raw_document` references the original ZIP blob

**Given** all documents are stored
**When** processing completes
**Then** a `collection.quality-exceptions.ingested` domain event is emitted
**And** processing_status is updated to "completed"
**And** the event payload includes: `document_id`, `source_id`, `plantation_id`, `batch_id`, document count

**Given** the ZIP is corrupted or invalid
**When** extraction fails
**Then** processing_status is set to "failed"
**And** error details logged: "Invalid ZIP format" or "Missing manifest.json" or schema validation errors
**And** original blob is retained for manual review

**Technical Notes:**
- Implements `ContentProcessor` ABC from Story 2.4
- Registered as: `ProcessorRegistry.register("zip-extraction", ZipExtractionProcessor)`
- ZIP processing: zipfile module with streaming (no temp files)
- Max ZIP size: 50MB
- Max images per ZIP: 100
- Image formats: JPEG, PNG only
- Uses generic ZIP manifest format (see `collection-model-architecture.md`)
- All documents stored in single `documents` collection, differentiated by `source_id`
- Linking via `linkage_fields.batch_id` and `linkage_fields.plantation_id`
- No changes to core pipeline - pure configuration-driven polymorphism

---

### Story 2.6: Document Storage & Deduplication

**[📄 Story File](../sprint-artifacts/2-6-document-storage-deduplication.md)** | Status: Done

As a **platform operator**,
I want duplicate documents detected and rejected,
So that storage is efficient and downstream analysis is not skewed.

**Acceptance Criteria:**

**Given** a document is about to be stored
**When** content hash (SHA-256) is calculated
**Then** the hash is checked against existing documents in MongoDB
**And** if duplicate found, storage is skipped with status "duplicate"

**Given** a duplicate document is detected
**When** the ingestion completes
**Then** no domain event is emitted
**And** response indicates: duplicate=true, original_document_id
**And** metrics track duplicate rate per source

**Given** a unique document is stored
**When** content hash is saved
**Then** MongoDB unique index on content_hash prevents race conditions
**And** document includes: content_hash, source_id, blob_path, stored_at

**Given** documents are stored over time
**When** storage metrics are queried
**Then** metrics include: total_documents, duplicates_rejected, storage_bytes, by_source breakdown

**Technical Notes:**
- Hash algorithm: SHA-256 on raw blob content
- MongoDB unique index: { content_hash: 1 }
- Duplicate detection before LLM extraction (save costs)
- Collection: raw_documents with content_hash field

---

### Story 2.7: Scheduled Pull Ingestion Framework

**[📄 Story File](../sprint-artifacts/2-7-scheduled-pull-ingestion-framework.md)** | Status: Done

As a **platform operator**,
I want a generic scheduled pull framework for external API data,
So that any HTTP/REST data source can be ingested via configuration without code changes.

**Design Principle:** Pull mode is a data fetcher that feeds JSON into the existing ingestion pipeline. The `JsonExtractionProcessor` handles all downstream processing (deduplication, AI extraction, storage, events). New data sources require only configuration - no code changes.

**Acceptance Criteria:**

**DAPR Job Lifecycle Management:**

**Given** a source is configured with `ingestion.mode: scheduled_pull`
**When** the Collection Model service starts
**Then** `JobRegistrationService.sync_all_jobs()` registers DAPR Jobs for all pull sources
**And** each job is registered with the configured schedule (cron or period)

**Given** a new pull source configuration is created via CLI
**When** the configuration is saved to MongoDB
**Then** a DAPR Job is automatically registered for the new source
**And** the job uses the schedule from `ingestion.schedule`

**Given** a pull source configuration is updated
**When** the schedule or endpoint changes
**Then** the existing DAPR Job is deleted and re-registered with new settings

**Pull Job Execution:**

**Given** a DAPR Job triggers at scheduled time
**When** `PullJobHandler` receives the job event
**Then** the source configuration is loaded from MongoDB
**And** the iteration block is checked for dynamic multi-fetch

**Given** the source has NO iteration block
**When** the job executes
**Then** a single HTTP request is made to the configured endpoint
**And** the JSON response is passed to `JsonExtractionProcessor` pipeline

**Given** the source has an iteration block
**When** the job executes
**Then** the MCP tool specified in `source_mcp`:`source_tool` is called
**And** for each item returned, a parallel fetch is executed (limited by `concurrency`)
**And** each fetched JSON is passed to `JsonExtractionProcessor` with injected linkage

**HTTP Fetch with Secrets:**

**Given** a pull source requires authentication
**When** fetching data from the endpoint
**Then** the API key is retrieved from DAPR Secret Store using `secret_store` and `secret_key`
**And** the key is added to the request header specified in `auth_header`

**Given** the HTTP request fails
**When** error is detected
**Then** retry with exponential backoff (max attempts from `retry.max_attempts`)
**And** if iteration mode, skip failed item and continue others
**And** metrics track success/failure per source

**Pipeline Reuse:**

**Given** JSON content is fetched from an external API
**When** passed to the ingestion pipeline
**Then** `RawDocumentStore` computes content hash for deduplication (Story 2-6)
**And** duplicate content returns `is_duplicate=True` without LLM costs
**And** new content proceeds through `JsonExtractionProcessor`
**And** `StorageMetrics` records stored/duplicate counts
**And** domain event is emitted via `DaprEventPublisher`

**Technical Implementation:**

| Component | Type | Description |
|-----------|------|-------------|
| `JobRegistrationService` | NEW | Register/update/delete DAPR Jobs on startup + config changes |
| `PullJobHandler` | NEW | Handle DAPR Job triggers with iteration support |
| `PullDataFetcher` | NEW | HTTP client with DAPR Secrets, URL templating |
| `IterationResolver` | NEW | Call MCP tools to get iteration items |
| `SourceConfigService` | MODIFIED | Hook job registration into config CRUD |
| `IngestionJob.content` | MODIFIED | Optional field for inline content (vs blob_path) |
| `IngestionJob.linkage` | MODIFIED | Optional injected linkage from iteration context |

**Source Configuration Schema:**

```yaml
source_id: weather-api
ingestion:
  mode: scheduled_pull
  schedule: "0 6 * * *"  # Cron or "@every 6h"
  request:
    base_url: https://api.open-meteo.com/v1/forecast
    auth_type: none | api_key | oauth
    secret_store: azure-keyvault  # DAPR secret store name
    secret_key: weather-api-key   # Key in secret store
    auth_header: X-API-Key        # Header to add
    parameters:
      hourly: temperature_2m,precipitation
      timezone: Africa/Nairobi
    timeout_seconds: 30
  iteration:  # Optional - enables multi-fetch
    foreach: region
    source_mcp: plantation-mcp
    source_tool: list_active_regions
    concurrency: 5
  retry:
    max_attempts: 3
    backoff: exponential
transformation:
  ai_agent_id: weather-data-extraction-agent
  link_field: region_id
  # ... same as blob trigger sources
storage:
  # ... same as blob trigger sources
events:
  # ... same as blob trigger sources
```

**Reused Components (no changes):**
- `JsonExtractionProcessor` - processes fetched JSON
- `RawDocumentStore` - deduplication via content hash
- `StorageMetrics` - OTel counters (Story 2-6)
- `DaprEventPublisher` - domain event emission
- `DocumentRepository` - index storage

**DAPR Secret Store Configuration:**

Secrets (API keys, OAuth credentials) are accessed via DAPR Secret Store component. This provides:
- Abstraction over secret backends (Azure Key Vault, Kubernetes Secrets, HashiCorp Vault)
- No secrets in source configuration or environment variables
- Automatic secret rotation support (backend-dependent)

**DAPR Component Definition** (`deploy/dapr/components/secretstore.yaml`):

```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: azure-keyvault
  namespace: farmer-power
spec:
  type: secretstores.azure.keyvault
  version: v1
  metadata:
    - name: vaultName
      value: "farmer-power-secrets"
    - name: azureClientId
      value: ""  # Uses Managed Identity in AKS
    - name: azureTenantId
      value: ""  # From Azure AD
```

**Alternative: Kubernetes Secrets** (for local/dev):

```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: kubernetes-secrets
  namespace: farmer-power
spec:
  type: secretstores.kubernetes
  version: v1
  metadata: []
```

**Usage in Source Config:**

```yaml
ingestion:
  request:
    auth_type: api_key
    secret_store: azure-keyvault    # DAPR component name
    secret_key: starfish-api-key    # Key name in secret store
    auth_header: Authorization      # HTTP header to populate
```

**Code Implementation:**

```python
# PullDataFetcher retrieves secret via DAPR client
async def _get_auth_header(self, pull_config: dict) -> dict[str, str]:
    if pull_config.get("auth_type") == "none":
        return {}

    secret_store = pull_config["secret_store"]
    secret_key = pull_config["secret_key"]
    auth_header = pull_config["auth_header"]

    # DAPR Secret Store API
    secret = await self._dapr.get_secret(
        store_name=secret_store,
        key=secret_key,
    )

    return {auth_header: secret[secret_key]}
```

**Test Validation:**
- Weather API source config (Open-Meteo, no auth, with iteration)
- Mock MCP tool returns region list
- Verify parallel fetch with concurrency limit
- Verify deduplication prevents duplicate processing
- Verify DAPR Job registration on startup and config change

---

### Story 2.8: Market Prices Pull Mode

**Story File:** Covered by Story 2.7 | Status: Configuration-only

**Status:** COVERED BY STORY 2.7

This story is now a **configuration-only task** - no code changes required.

The generic Scheduled Pull Ingestion Framework (Story 2.7) supports any HTTP/REST data source via configuration. Market prices ingestion requires only:

1. Create source configuration YAML with `mode: scheduled_pull`
2. Configure Starfish API endpoint and authentication
3. Create AI extraction agent for market price fields
4. Register configuration via CLI

**Example Configuration:**

```yaml
source_id: market-prices-starfish
display_name: Starfish Kenya Tea Auction Prices
ingestion:
  mode: scheduled_pull
  schedule: "0 7 * * *"  # Daily 7 AM EAT
  request:
    base_url: https://api.starfish.co.ke/v1/tea-auction/prices
    auth_type: api_key
    secret_store: azure-keyvault
    secret_key: starfish-api-key
    auth_header: Authorization
    parameters:
      market: mombasa
      date: today
    timeout_seconds: 30
  retry:
    max_attempts: 3
    backoff: exponential
transformation:
  ai_agent_id: market-prices-extraction-agent
  extract_fields:
    - commodity
    - region
    - price
    - currency
    - unit
    - auction_date
  link_field: region
storage:
  raw_container: market-data-raw
  index_collection: documents
events:
  on_success:
    topic: collection.market_prices.updated
    payload_fields: [commodity, region, price, auction_date]
```

**Note:** This story remains in `unscoped-phase2` in sprint-status.yaml as it depends on Starfish API access being available. When ready, implementation is configuration-only.

---

### Story 2.9: Collection Model MCP Server

**[📄 Story File](../sprint-artifacts/2-9-collection-model-mcp-server.md)** | Status: Done

As an **AI agent**,
I want to query collected documents via generic MCP tools,
So that I can access any source's data using consistent, config-driven queries.

**Acceptance Criteria:**

**AC1: get_documents - Query with Filters**
**Given** the Collection MCP Server is deployed
**When** an AI agent calls `get_documents(source_id="qc-analyzer-result", farmer_id="WM-4521", date_range={start, end}, limit=50)`
**Then** matching documents are returned from the generic `documents` collection
**And** each document includes: document_id, source_id, farmer_id, linkage, attributes, files, ingested_at
**And** results are sorted by ingested_at descending

**AC2: get_documents - Attribute Filtering**
**Given** quality documents exist with varying primary_percentage
**When** an AI agent calls `get_documents(source_id="qc-analyzer-result", attributes={"bag_summary.primary_percentage": {"$lt": 70}})`
**Then** only documents matching the attribute filter are returned
**And** this enables queries like "poor quality events" without hardcoded tools

**AC3: get_documents - Linkage Filtering**
**Given** documents exist with linkage fields (batch_id, plantation_id, factory_id)
**When** an AI agent calls `get_documents(linkage={"batch_id": "batch-2025-12-26-001"})`
**Then** all documents linked to that batch are returned across any source_id

**AC4: get_document_by_id - Single Document with Files**
**Given** a document_id exists
**When** an AI agent calls `get_document_by_id(document_id="qc-analyzer-exceptions/batch-001/leaf_001", include_files=true)`
**Then** the full document is returned with all attributes and payload
**And** files[] array includes blob_uri with fresh SAS tokens (1 hour validity)
**And** file roles are preserved (image, metadata, primary, thumbnail)

**AC5: get_farmer_documents - Cross-Source Farmer Query**
**Given** a farmer has documents from multiple sources
**When** an AI agent calls `get_farmer_documents(farmer_id="WM-4521", source_ids=["qc-analyzer-result", "qc-analyzer-exceptions"], date_range={last_30_days})`
**Then** all matching documents across specified sources are returned
**And** this replaces the need for source-specific farmer tools

**AC6: search_documents - Full-Text Search**
**Given** documents have searchable content in attributes
**When** an AI agent calls `search_documents(query="coarse leaf", source_ids=["qc-analyzer-exceptions"], limit=20)`
**Then** documents matching the search query are returned
**And** results include relevance scoring

**AC7: list_sources - Source Registry**
**Given** source configurations are deployed
**When** an AI agent calls `list_sources(enabled_only=true)`
**Then** all enabled source configurations are returned
**And** each includes: source_id, display_name, ingestion.mode, description

**AC8: Weather and Market Data via Generic Tools**
**Given** weather-api and market-prices sources are configured
**When** an AI agent calls `get_documents(source_id="weather-api", linkage={"region_id": "nyeri"}, date_range={last_7_days})`
**Then** weather documents for that region are returned
**And** the same pattern works for `get_documents(source_id="market-prices", ...)`
**And** no source-specific tools are needed

**AC9: Error Handling**
**Given** an invalid source_id is provided
**When** an AI agent calls `get_documents(source_id="nonexistent")`
**Then** an empty result set is returned (not an error)
**And** the response includes metadata indicating 0 matches

**Given** an invalid document_id is provided
**When** an AI agent calls `get_document_by_id(document_id="nonexistent")`
**Then** a NOT_FOUND error is returned with appropriate error code

**Technical Notes:**
- MCP Server: stateless, deployed as separate Kubernetes deployment
- HPA enabled: min 2, max 10 replicas
- Read-only access to MongoDB (read replicas preferred)
- All tools query the generic `documents` collection with source_id filtering
- No source-specific tools - config-driven architecture
- File URLs: Azure Blob Storage SDK generates SAS tokens on-demand
- Proto: `farmer_power.collection_mcp.v1`
- Implements MCP ToolCallRequest/ToolCallResponse pattern via DAPR Service Invocation

---

---

### Story 2.10: Collection Model Repository Pattern Refactoring (Tech Debt)

**[📄 Story File](../sprint-artifacts/2-10-collection-model-repository-refactoring.md)** | Status: Backlog

As a **developer**,
I want Collection Model to use Pydantic models and repository pattern for source configs,
So that type safety catches bugs at development time instead of E2E testing.

**Problem Statement:**

During Story 0.4.6 (Weather Data Ingestion), multiple production code bugs were discovered that should have been caught by type safety:
- DAPR gRPC invocation pattern misunderstood
- Source config accessed as `config.get("config", {}).get(X)` instead of direct fields
- `SourceConfigService` returns `dict[str, Any]` instead of `SourceConfig` Pydantic model

**Root Cause:** Collection Model doesn't follow the repository pattern used by Plantation Model.

**Acceptance Criteria:**

1. **AC1:** `BaseRepository` pattern implemented in Collection Model
2. **AC2:** `SourceConfigRepository` returns `SourceConfig` Pydantic models
3. **AC3:** `SourceConfigService` refactored to use repository
4. **AC4:** All 12+ consumer files migrated to typed attribute access
5. **AC5:** Unit tests updated to use real Pydantic models
6. **AC6:** DAPR gRPC pattern documented in `project-context.md`

**Technical Notes:**
- Reference: Plantation Model's `BaseRepository` pattern
- Target: Zero `dict[str, Any]` for source config access
- Existing model: `fp_common.models.source_config.SourceConfig`

---

### Story 2.12: Collection → AI Model Event-Driven Communication

**[📄 Story File](../sprint-artifacts/2-12-collection-ai-model-event-driven-communication.md)** | Status: Blocked
**Blocked By:** Story 0.75.17 (Extractor Agent Implementation)
**Blocks:** Story 0.75.18 (E2E Weather Observation Extraction Flow)
**GitHub Issue:** #81

As a **platform developer**,
I want Collection Model to communicate with AI Model via async events instead of synchronous gRPC,
So that the system follows the architecture specification and scales properly.

**Scope:**
- Add event publishing after document storage (`collection.document.received`)
- Add event subscription for AI results (`ai.extraction.complete`)
- Remove/deprecate synchronous `AiModelClient.extract()` method
- Follow dead letter queue pattern (ADR-006)

**Acceptance Criteria:**
- Collection Model publishes `collection.document.received` event after document storage
- Collection Model subscribes to `ai.extraction.complete` events
- Document updated with extracted fields via event handler
- No synchronous gRPC calls for extraction workflow
- Unit tests cover event publishing and subscription
- `test_05_weather_ingestion.py` marked as xfail (replaced by Story 0.75.18)

---

### Story 2.13: Thumbnail Generation for AI Tiered Vision Processing

**[📄 Story File](../sprint-artifacts/2-13-thumbnail-generation-tiered-vision.md)** | Status: Blocked
**Blocked By:** Story 0.75.17 (Extractor Agent Implementation)
**Blocks:** Story 0.75.18 (E2E Weather Observation Extraction Flow), Story 0.75.22 (Tiered-Vision Agent)
**GitHub Issue:** #88

As a **platform operator**,
I want Collection Model to generate thumbnails at image ingestion time,
So that AI Model's Tiered Vision processing can reduce LLM costs by 57%.

**Scope:**
- Add Pillow dependency and ThumbnailGenerator service
- Generate 256x256 JPEG thumbnails at image ingestion
- Store thumbnails in blob storage alongside originals
- Update document schema with `thumbnail_url` field
- Add `get_document_thumbnail` MCP tool
- Update event payload with `has_thumbnail` flag

**Acceptance Criteria:**
- Images ingested via ZIP processor have thumbnails generated
- Thumbnails stored in blob storage alongside originals
- Document records include `thumbnail_url` field
- `get_document_thumbnail` MCP tool returns thumbnail bytes
- Unit tests for thumbnail generation

---

## Retrospective

**[📋 Epic 2 Retrospective](../sprint-artifacts/epic-2-retro-2025-12-27.md)** | Completed: 2025-12-27

