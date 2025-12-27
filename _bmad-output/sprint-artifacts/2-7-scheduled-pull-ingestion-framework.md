# Story 2.7: Scheduled Pull Ingestion Framework

**Status:** ready-for-dev
**Epic:** 2 - Quality Data Ingestion
**GitHub Issue:** #22
**Created:** 2025-12-27

---

## Story

As a **platform operator**,
I want a generic scheduled pull framework for external API data,
So that any HTTP/REST data source can be ingested via configuration without code changes.

---

## Context

This story implements the **SCHEDULED_PULL** ingestion mode for the Collection Model. Unlike blob-trigger mode which reacts to file uploads, pull mode proactively fetches data from external APIs on a schedule.

**Design Principle:** Pull mode is a thin data fetcher that collects JSON and feeds it into the existing ingestion pipeline. The `JsonExtractionProcessor` handles all downstream processing (deduplication, AI extraction, storage, events). New data sources require only configuration - no code changes.

**Already Implemented (reuse from Stories 2-4, 2-5, 2-6):**
- `JsonExtractionProcessor` - fully generic JSON processing pipeline
- `RawDocumentStore` - content hash deduplication (`services/collection-model/src/collection_model/infrastructure/raw_document_store.py`)
- `StorageMetrics` - OpenTelemetry counters (`services/collection-model/src/collection_model/infrastructure/storage_metrics.py`)
- `DaprEventPublisher` - config-driven domain event emission (`services/collection-model/src/collection_model/infrastructure/dapr_event_publisher.py`)
- `DocumentRepository` - index storage (`services/collection-model/src/collection_model/infrastructure/document_repository.py`)
- `SourceConfigService` - source config loading with caching (`services/collection-model/src/collection_model/services/source_config_service.py`)

---

## Acceptance Criteria

### AC1: DAPR Job Lifecycle Management

1. **Given** a source is configured with `ingestion.mode: scheduled_pull`
   **When** the Collection Model service starts
   **Then** `JobRegistrationService.sync_all_jobs()` registers DAPR Jobs for all pull sources
   **And** each job is registered with the configured schedule (cron expression)

2. **Given** a new pull source configuration is created via CLI
   **When** the configuration is saved to MongoDB
   **Then** a DAPR Job is automatically registered for the new source
   **And** the job uses the schedule from `ingestion.schedule`

3. **Given** a pull source configuration is updated (schedule or endpoint changes)
   **When** the update is detected
   **Then** the existing DAPR Job is deleted and re-registered with new settings

### AC2: Pull Job Execution

4. **Given** a DAPR Job triggers at scheduled time
   **When** `PullJobHandler` receives the job event
   **Then** the source configuration is loaded from MongoDB
   **And** the iteration block is evaluated for dynamic multi-fetch

5. **Given** the source has NO iteration block
   **When** the job executes
   **Then** a single HTTP request is made to the configured endpoint
   **And** the JSON response is passed to `JsonExtractionProcessor` pipeline

6. **Given** the source has an iteration block
   **When** the job executes
   **Then** the MCP tool specified in `source_mcp`:`source_tool` is called
   **And** for each item returned, a parallel fetch is executed (limited by `concurrency`)
   **And** each fetched JSON is passed to `JsonExtractionProcessor` with injected linkage

### AC3: HTTP Fetch with DAPR Secrets

7. **Given** a pull source requires authentication (`auth_type: api_key`)
   **When** fetching data from the endpoint
   **Then** the API key is retrieved from DAPR Secret Store using `secret_store` and `secret_key`
   **And** the key is added to the request header specified in `auth_header`

8. **Given** a pull source has `auth_type: none`
   **When** fetching data
   **Then** no authentication headers are added

9. **Given** the HTTP request fails
   **When** error is detected
   **Then** retry with exponential backoff (max attempts from `retry.max_attempts`)
   **And** if iteration mode, skip failed item and continue others
   **And** metrics track success/failure per source

### AC4: Pipeline Reuse

10. **Given** JSON content is fetched from an external API
    **When** passed to the ingestion pipeline
    **Then** `RawDocumentStore` computes content hash for deduplication
    **And** duplicate content returns `is_duplicate=True` without LLM costs
    **And** new content proceeds through `JsonExtractionProcessor`
    **And** `StorageMetrics` records stored/duplicate counts
    **And** domain event is emitted via `DaprEventPublisher`

---

## Tasks / Subtasks

### Task 1: Create DAPR Jobs Infrastructure (AC: 1, 2, 3)

- [ ] Create `services/collection-model/src/collection_model/infrastructure/dapr_jobs_client.py`
  - [ ] `DaprJobsClient` class with async methods
  - [ ] `register_job(source_id, schedule, target_path)` - creates DAPR Job
  - [ ] `delete_job(source_id)` - removes DAPR Job
  - [ ] `list_jobs()` - returns registered jobs (optional, for debugging)
  - [ ] Uses DAPR HTTP API for job management (see DAPR Jobs documentation)

### Task 2: Create Job Registration Service (AC: 1, 2, 3)

- [ ] Create `services/collection-model/src/collection_model/services/job_registration_service.py`
  - [ ] `JobRegistrationService` class
  - [ ] `sync_all_jobs()` - called on startup, registers jobs for all `scheduled_pull` sources
  - [ ] `register_job_for_source(source_config)` - register single job
  - [ ] `unregister_job_for_source(source_id)` - remove job
  - [ ] Inject `DaprJobsClient` and `SourceConfigService`

### Task 3: Integrate Job Registration into Startup (AC: 1)

- [ ] Modify `services/collection-model/src/collection_model/main.py`
  - [ ] Initialize `DaprJobsClient` in lifespan
  - [ ] Initialize `JobRegistrationService` in lifespan
  - [ ] Call `job_registration_service.sync_all_jobs()` after MongoDB init
  - [ ] Store in `app.state.job_registration_service`

### Task 4: Create HTTP Pull Data Fetcher (AC: 5, 7, 8, 9)

- [ ] Create `services/collection-model/src/collection_model/infrastructure/pull_data_fetcher.py`
  - [ ] `PullDataFetcher` class with async methods
  - [ ] `fetch(pull_config, iteration_item=None)` - returns JSON bytes
  - [ ] `_get_auth_header(pull_config)` - retrieves secret via DAPR Secret Store
  - [ ] `_build_url(base_url, parameters, iteration_item)` - URL template substitution
  - [ ] Uses `httpx` for async HTTP requests (already in dependencies)
  - [ ] Retry logic with `tenacity` (exponential backoff)

### Task 5: Create Iteration Resolver (AC: 6)

- [ ] Create `services/collection-model/src/collection_model/infrastructure/iteration_resolver.py`
  - [ ] `IterationResolver` class
  - [ ] `resolve(iteration_config)` - calls MCP tool, returns list of items
  - [ ] Uses DAPR Service Invocation to call `plantation-mcp` (or configured MCP server)
  - [ ] Returns list of dicts with fields to inject into URL and linkage

### Task 6: Create Pull Job Handler (AC: 4, 5, 6, 10)

- [ ] Create `services/collection-model/src/collection_model/services/pull_job_handler.py`
  - [ ] `PullJobHandler` class
  - [ ] `handle_job_trigger(source_id)` - main entry point from DAPR Job callback
  - [ ] Loads source config via `SourceConfigService`
  - [ ] If iteration: calls `IterationResolver`, fans out parallel fetches
  - [ ] Each fetch: calls `PullDataFetcher`, creates `IngestionJob`, invokes `JsonExtractionProcessor`
  - [ ] Uses `asyncio.gather` with `return_exceptions=True` for parallel execution
  - [ ] Respects `concurrency` limit from config

### Task 7: Add Job Trigger API Endpoint (AC: 4)

- [ ] Modify `services/collection-model/src/collection_model/api/events.py`
  - [ ] Add `POST /api/v1/triggers/job/{source_id}` endpoint
  - [ ] Receives DAPR Job callback
  - [ ] Delegates to `PullJobHandler.handle_job_trigger()`
  - [ ] Returns 200 on success, 500 on failure

### Task 8: Extend IngestionJob for Inline Content (AC: 5, 6)

- [ ] Modify `services/collection-model/src/collection_model/domain/ingestion_job.py`
  - [ ] Add `content: bytes | None = None` field (inline content from pull, vs blob_path)
  - [ ] Add `linkage: dict[str, Any] | None = None` field (injected from iteration)
  - [ ] Add validation: either `blob_path` or `content` must be set

### Task 9: Update JsonExtractionProcessor for Inline Content (AC: 10)

- [ ] Modify `services/collection-model/src/collection_model/processors/json_extraction.py`
  - [ ] In `process()`, check if `job.content` is set
  - [ ] If set, skip blob download and use inline content directly
  - [ ] Merge `job.linkage` into document linkage if present

### Task 10: Hook Job Registration into Config Changes (AC: 2, 3)

- [ ] Modify `services/collection-model/src/collection_model/services/source_config_service.py`
  - [ ] Add optional `job_registration_service` dependency
  - [ ] On config create: if `mode=scheduled_pull`, call `register_job_for_source()`
  - [ ] On config update: call `unregister_job_for_source()` then `register_job_for_source()`
  - [ ] On config delete: call `unregister_job_for_source()`

### Task 11: Create DAPR Secret Store Component (Infrastructure)

- [ ] Create `deploy/dapr/components/secretstore.yaml`
  - [ ] Azure Key Vault component for production
  - [ ] Kubernetes Secrets component for local/dev
  - [ ] Document in story that this needs AKS Managed Identity setup

---

## Dev Notes

### Architecture Pattern

```
┌────────────────────────────────────────────────────────────────────────┐
│                    SCHEDULED PULL FLOW                                  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DAPR Job Scheduler                                                     │
│  ┌─────────────────┐                                                   │
│  │ weather-api     │──── triggers ────┐                                │
│  │ schedule: 0 6 * │                  │                                │
│  └─────────────────┘                  ▼                                │
│                             ┌──────────────────┐                       │
│                             │ PullJobHandler   │                       │
│                             │                  │                       │
│                             │ 1. Load config   │                       │
│                             │ 2. Check iteration│                      │
│                             └────────┬─────────┘                       │
│                                      │                                  │
│           ┌──────────────────────────┴─────────────────────┐           │
│           ▼                                                ▼           │
│  ┌─────────────────┐                        ┌─────────────────────┐   │
│  │ NO ITERATION    │                        │ WITH ITERATION      │   │
│  │ Single fetch    │                        │                     │   │
│  └────────┬────────┘                        │ 1. IterationResolver│   │
│           │                                 │    → call MCP tool  │   │
│           │                                 │    → get region list│   │
│           │                                 │                     │   │
│           │                                 │ 2. Parallel fetches │   │
│           │                                 │    (concurrency: 5) │   │
│           │                                 └──────────┬──────────┘   │
│           │                                            │               │
│           └──────────────┬─────────────────────────────┘               │
│                          ▼                                              │
│                 ┌─────────────────┐                                    │
│                 │ PullDataFetcher │                                    │
│                 │                 │                                    │
│                 │ • Build URL     │                                    │
│                 │ • Get secret    │◀──── DAPR Secret Store            │
│                 │ • HTTP request  │                                    │
│                 │ • Retry logic   │                                    │
│                 └────────┬────────┘                                    │
│                          │                                              │
│                          ▼                                              │
│           ┌──────────────────────────────┐                             │
│           │    EXISTING PIPELINE         │                             │
│           │    (from Story 2-4, 2-5, 2-6)│                             │
│           ├──────────────────────────────┤                             │
│           │ • RawDocumentStore (dedup)   │                             │
│           │ • JsonExtractionProcessor    │                             │
│           │ • StorageMetrics (OTel)      │                             │
│           │ • DaprEventPublisher         │                             │
│           └──────────────────────────────┘                             │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### DAPR Jobs API

Per DAPR documentation (v1.15+), jobs are managed via HTTP API:

```python
# Register job
POST http://localhost:3500/v1.0/jobs/{job_name}
{
    "schedule": "@every 6h",  # or cron: "0 6 * * *"
    "data": {"source_id": "weather-api"},
    "dueTime": "0s",  # start immediately or delay
    "repeats": 0  # 0 = indefinite
}

# Delete job
DELETE http://localhost:3500/v1.0/jobs/{job_name}

# Job callback to app
POST http://localhost:8080/api/v1/triggers/job/{source_id}
```

### DAPR Secret Store Usage

```python
# PullDataFetcher._get_auth_header()
async def _get_auth_header(self, pull_config: dict) -> dict[str, str]:
    if pull_config.get("auth_type") == "none":
        return {}

    secret_store = pull_config["secret_store"]
    secret_key = pull_config["secret_key"]
    auth_header = pull_config["auth_header"]

    # DAPR Secret Store API via sidecar
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:3500/v1.0/secrets/{secret_store}/{secret_key}"
        )
        response.raise_for_status()
        secret = response.json()[secret_key]

    return {auth_header: secret}
```

### Source Config Reference

Weather API config is already defined (`config/source-configs/weather-api.yaml`):

```yaml
source_id: weather-api
ingestion:
  mode: scheduled_pull
  schedule: "0 6 * * *"
  request:
    base_url: https://api.open-meteo.com/v1/forecast
    auth_type: none
    parameters:
      hourly: temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m
    timeout_seconds: 30
  iteration:
    foreach: region
    source_mcp: plantation-mcp
    source_tool: list_active_regions
    concurrency: 5
  retry:
    max_attempts: 3
    backoff: exponential
```

### Existing Code to Reuse

| Component | File | Method |
|-----------|------|--------|
| JSON processing | `processors/json_extraction.py` | `process()` |
| Deduplication | `infrastructure/raw_document_store.py` | `store_raw_document()` |
| Storage metrics | `infrastructure/storage_metrics.py` | `record_stored()`, `record_duplicate()` |
| Event emission | `infrastructure/dapr_event_publisher.py` | `publish_success()` |
| Source config | `services/source_config_service.py` | `get_config()` |

### Critical: Do NOT Modify

- `processors/json_extraction.py` core logic (only add inline content support)
- `infrastructure/raw_document_store.py` (already handles deduplication)
- `infrastructure/storage_metrics.py` (already has counters)
- `infrastructure/dapr_event_publisher.py` (already config-driven)

### Project Structure Notes

New files follow existing patterns:
- Infrastructure components: `services/collection-model/src/collection_model/infrastructure/`
- Services: `services/collection-model/src/collection_model/services/`
- Unit tests: `tests/unit/collection/`

### Testing Strategy

| Test | Type | Location |
|------|------|----------|
| DaprJobsClient unit tests | Unit | `tests/unit/collection/test_dapr_jobs_client.py` |
| JobRegistrationService unit tests | Unit | `tests/unit/collection/test_job_registration_service.py` |
| PullDataFetcher unit tests | Unit | `tests/unit/collection/test_pull_data_fetcher.py` |
| IterationResolver unit tests | Unit | `tests/unit/collection/test_iteration_resolver.py` |
| PullJobHandler unit tests | Unit | `tests/unit/collection/test_pull_job_handler.py` |
| Job trigger endpoint tests | Unit | `tests/unit/collection/test_events.py` |
| End-to-end pull flow | Integration | `tests/integration/test_pull_ingestion.py` |

---

### References

- [Source: `_bmad-output/architecture/collection-model-architecture.md` - Ingestion Modes, SCHEDULED_PULL section]
- [Source: `_bmad-output/epics.md` - Story 2.7 Acceptance Criteria]
- [Source: `_bmad-output/project-context.md` - DAPR Communication Rules]
- [Source: `config/source-configs/weather-api.yaml` - Existing source config]
- [Source: `services/collection-model/src/collection_model/processors/json_extraction.py` - Reuse pattern]
- [DAPR Jobs Documentation](https://docs.dapr.io/developing-applications/building-blocks/jobs/)
- [DAPR Secrets Documentation](https://docs.dapr.io/developing-applications/building-blocks/secrets/)

---

## Definition of Done

- [ ] `DaprJobsClient` created with register/delete job methods
- [ ] `JobRegistrationService` syncs jobs on startup
- [ ] `PullDataFetcher` fetches data with DAPR secret support
- [ ] `IterationResolver` calls MCP tools for dynamic multi-fetch
- [ ] `PullJobHandler` orchestrates pull flow with parallel execution
- [ ] Job trigger API endpoint added
- [ ] `IngestionJob` extended with `content` and `linkage` fields
- [ ] `JsonExtractionProcessor` supports inline content
- [ ] Job registration hooked into config create/update/delete
- [ ] DAPR Secret Store component definition created
- [ ] Unit tests for all new components
- [ ] Integration test for end-to-end pull flow
- [ ] Weather API source config validates correctly
- [ ] CI passes (ruff check, ruff format, tests)

---

## Dev Agent Record

### Agent Model Used

<!-- Filled by dev-story workflow -->

### Debug Log References

### Completion Notes List

### File List

---

_Created: 2025-12-27_
