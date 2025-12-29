### Epic 0.4: E2E Test Scenarios for Plantation & Collection Models

**Priority:** P0

**Dependencies:** Epic 0.3 (E2E Infrastructure) - Complete

End-to-end tests validating the full stack deployment of Plantation Model, Collection Model, and their MCP servers. These tests catch integration regressions before production and validate TBK/KTDA grading accuracy critical to farmer payments.

**Related Documents:**
- `_bmad-output/test-design-system-level.md` - System-level test strategy
- `tests/e2e/README.md` - E2E infrastructure documentation

**Scope:**
- MCP tool contract validation (14 tools total)
- Factory-Farmer registration flow with region assignment
- Quality event blob ingestion (JSON direct, no AI)
- Weather data ingestion with mocked AI extraction
- ZIP processor bulk ingestion
- Cross-model DAPR event flow (Collection → Plantation)
- TBK/KTDA grading model validation

---

## Architecture Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        E2E TEST SCOPE - EPIC 0.4                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐               │
│  │  Plantation │     │  Collection │     │   Azurite   │               │
│  │    Model    │◄────│    Model    │◄────│   (Blob)    │               │
│  │   :8001     │DAPR │   :8002     │     │  :10000     │               │
│  └──────┬──────┘     └──────┬──────┘     └─────────────┘               │
│         │                   │                                           │
│  ┌──────▼──────┐     ┌──────▼──────┐     ┌─────────────┐               │
│  │  Plantation │     │  Collection │     │  Mock AI    │ ◄── NEW       │
│  │     MCP     │     │     MCP     │     │  Extractor  │               │
│  │   :50052    │     │   :50053    │     │   :8090     │               │
│  └─────────────┘     └─────────────┘     └─────────────┘               │
│                                                                         │
│  REAL: MongoDB, Redis, Weather API (Open-Meteo)                        │
│  MOCK: Google Elevation, AI Extractor, Azurite                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Mock Strategy

| Component | Approach | Rationale |
|-----------|----------|-----------|
| Google Elevation API | **MOCK** (deterministic) | Predictable altitude → region assignment |
| Weather API (Open-Meteo) | **REAL** | Free, stable, validates real integration |
| AI Extraction (Weather) | **MOCK** | Deterministic responses for E2E |
| AI Extraction (QC Events) | **BYPASS** | Direct JSON extraction, no AI needed |
| MongoDB | **REAL** (containerized) | Full database behavior |
| Azure Blob Storage | **MOCK** (Azurite) | Local emulator |

---

#### Story 0.4.1: Infrastructure Verification

**Status:** ✅ Done (19 tests in `test_00_infrastructure_verification.py`)

As a **platform engineer**,
I want E2E infrastructure verification tests,
So that I can validate all services are healthy before running functional tests.

**Test Count:** 19 tests

---

#### Story 0.4.2: Plantation MCP Tool Contract Tests

As a **developer integrating with Plantation Model**,
I want all 9 Plantation MCP tools validated with contract tests,
So that AI agents can reliably query plantation data.

**Acceptance Criteria:**

**Given** seed data (regions, grading models) is loaded
**When** `get_factory` is called with a valid factory_id
**Then** it returns factory with name, code, region, quality thresholds, payment policy

**Given** a farmer exists in the database
**When** `get_farmer` is called with the farmer_id
**Then** it returns farmer with name, phone, farm size, region, collection point, preferences

**Given** a farmer has quality history
**When** `get_farmer_summary` is called
**Then** it returns performance metrics structure with trends and yield data

**Given** a factory has collection points
**When** `get_collection_points` is called with factory_id
**Then** it returns all CPs with their details

**Given** farmers are registered at a collection point
**When** `get_farmers_by_collection_point` is called
**Then** it returns the list of farmers at that CP

**Given** regions are seeded
**When** `get_region` is called with region_id
**Then** it returns full region with geography, flush calendar, agronomic factors

**Given** multiple regions exist
**When** `list_regions` is called with county or altitude_band filter
**Then** it returns filtered active regions

**Given** a region has flush calendar configured
**When** `get_current_flush` is called
**Then** it returns correct flush period with days remaining based on current date

**Given** a region has weather data
**When** `get_region_weather` is called with days parameter
**Then** it returns weather observations array with temp, precip, humidity

**Technical Notes:**
- Test File: `tests/e2e/scenarios/test_01_plantation_mcp_contracts.py`
- Uses `plantation_mcp` gRPC fixture
- Validates against seed data in `infrastructure/seed/`

**Test Count:** 9 tests

**Story Points:** 2

---

#### Story 0.4.3: Collection MCP Tool Contract Tests

As a **developer integrating with Collection Model**,
I want all 5 Collection MCP tools validated with contract tests,
So that AI agents can reliably query collected documents.

**Acceptance Criteria:**

**Given** documents exist in the collection database
**When** `get_documents` is called with source_id, farmer_id, or attribute filters
**Then** it returns matching documents sorted by ingested_at descending

**Given** a document exists with a known document_id
**When** `get_document_by_id` is called with include_files=true
**Then** it returns full document with SAS URLs for blob access

**Given** a farmer has documents across multiple sources
**When** `get_farmer_documents` is called with farmer_id
**Then** it returns aggregated documents from all sources

**Given** documents contain searchable content
**When** `search_documents` is called with a query string
**Then** it returns relevance-scored results

**Given** source configs are seeded
**When** `list_sources` is called with enabled_only=true
**Then** it returns enabled source configurations

**Technical Notes:**
- Test File: `tests/e2e/scenarios/test_02_collection_mcp_contracts.py`
- Uses `collection_mcp` gRPC fixture
- Requires documents to be ingested first (dependency on Story 0.4.5)

**Test Count:** 5 tests

**Story Points:** 2

---

#### Story 0.4.4: Factory-Farmer Registration Flow

As a **field operations manager**,
I want the complete registration flow validated end-to-end,
So that new farmers are correctly assigned to regions based on GPS and altitude.

**Acceptance Criteria:**

**Given** an empty database with seeded regions and grading models
**When** I create a factory with TBK grading model
**Then** the factory is created successfully with correct configuration

**Given** a factory exists
**When** I create a collection point under that factory
**Then** the collection point is linked to the factory

**Given** a collection point exists
**When** I register a farmer with GPS coordinates (lat=0.8, lng=35.0)
**Then** the farmer is created with auto-assigned region based on GPS + altitude

**Given** the Google Elevation mock returns 1000m for lat=0.8
**When** the farmer is assigned to a region
**Then** the region altitude band is "midland" (matches mock response)

**Given** a farmer is registered
**When** I query via `get_farmer`, `get_farmers_by_collection_point`
**Then** the farmer is returned correctly in all queries

**Test Flow:**
```
1. Create Factory (KEN-FAC-E2E-001)
   └─► 2. Create Collection Point (CP-E2E-001)
       └─► 3. Register Farmer (GPS: lat=0.8, lng=35.0)
           └─► 4. Verify: Region = midland (altitude 1000m from mock)
               └─► 5. Query via MCP tools
```

**Technical Notes:**
- Test File: `tests/e2e/scenarios/test_03_factory_farmer_flow.py`
- Depends on Google Elevation Mock (deterministic lat → altitude)
- Tests factory → CP → farmer hierarchy

**Test Count:** 5 tests

**Story Points:** 3

---

#### Story 0.4.5: Quality Event Blob Ingestion (No AI)

As a **data engineer**,
I want quality event ingestion via blob trigger validated,
So that QC analyzer results are stored without AI extraction overhead.

**Acceptance Criteria:**

**Given** source config `e2e-qc-direct-json` exists with `ai_agent_id: null`
**When** I upload a JSON blob to `quality-events-e2e` container
**Then** the blob is stored in Azurite successfully

**Given** a blob exists in the landing container
**When** I trigger the blob event via `POST /events/blob`
**Then** the Collection Model accepts the event and queues processing

**Given** the blob event is processed
**When** I wait for async processing (3s)
**Then** a document is created in MongoDB with correct `farmer_id` linkage

**Given** the document is created
**When** I query via `get_documents(farmer_id="WM-E2E-001")`
**Then** the document is returned with extracted attributes

**Given** the document is processed successfully
**When** I check DAPR pubsub
**Then** event `collection.quality_result.received` is published

**Given** a duplicate blob is uploaded (same content hash)
**When** the blob event is triggered
**Then** the duplicate is detected and skipped (no new document)

**Technical Notes:**
- Test File: `tests/e2e/scenarios/test_04_quality_blob_ingestion.py`
- Uses `json-extraction` processor (no AI)
- Source config: `e2e-qc-direct-json` in `seed/source_configs.json`

**Test Count:** 6 tests

**Story Points:** 3

---

#### Story 0.4.6: Weather Data Ingestion with Mock AI

As a **data engineer**,
I want weather data ingestion validated with mocked AI extraction,
So that real weather API data flows through the pipeline with deterministic extraction.

**Acceptance Criteria:**

**Given** Mock AI Extractor server is deployed at :8090
**When** I send an extraction request for weather data
**Then** the mock returns deterministic weather document structure

**Given** source config `e2e-weather-api` exists with weather API endpoint
**When** the weather pull job is triggered
**Then** real weather data is fetched from Open-Meteo API

**Given** weather data is fetched
**When** the AI extraction mock processes it
**Then** a weather document is created with region linkage

**Given** weather documents exist for a region
**When** I call `get_region_weather` via Plantation MCP
**Then** weather observations are returned correctly

**Given** the weather document is stored
**When** I query via Collection MCP `get_documents(source_id="e2e-weather-api")`
**Then** the document is returned with weather attributes

**Infrastructure Addition:**
```yaml
# docker-compose.e2e.yaml
mock-ai-extractor:
  build: ./infrastructure/mock-servers/ai-extractor
  ports:
    - "8090:8080"
  environment:
    - DETERMINISTIC_MODE=true
```

**Technical Notes:**
- Test File: `tests/e2e/scenarios/test_05_weather_ingestion.py`
- New infrastructure: `mock-servers/ai-extractor/`
- Uses real Open-Meteo API, mock AI extraction

**Test Count:** 5 tests

**Story Points:** 5

---

#### Story 0.4.7: Cross-Model DAPR Event Flow

**Risk Level:** CRITICAL (TBK Score: 9)

As a **platform architect**,
I want the cross-model event flow validated,
So that Collection Model events correctly update Plantation Model farmer performance.

**Acceptance Criteria:**

**Given** a farmer WM-E2E-001 exists in Plantation Model with initial performance
**When** I query `get_farmer_summary` before any quality events
**Then** the performance summary shows initial/empty metrics

**Given** the farmer exists
**When** a quality document for WM-E2E-001 is ingested in Collection Model
**Then** DAPR publishes `collection.quality_result.received` event

**Given** the event is published
**When** Plantation Model receives the event (wait 5s for processing)
**Then** the farmer's performance summary is updated with new quality data

**Given** the performance is updated
**When** I call `get_farmer_summary` via Plantation MCP
**Then** it reflects the updated metrics from the quality event

**Test Flow:**
```
1. Setup: Create farmer WM-E2E-001 in Plantation
   └─► 2. Ingest: Quality event for WM-E2E-001 in Collection
       └─► 3. Event: DAPR publishes quality_result.received
           └─► 4. Wait: 5s for event processing
               └─► 5. Verify: get_farmer_summary shows updated data
```

**Technical Notes:**
- Test File: `tests/e2e/scenarios/test_06_cross_model_events.py`
- Critical integration point between services
- Tests DAPR pubsub reliability

**Test Count:** 4 tests

**Story Points:** 3

---

#### Story 0.4.8: TBK/KTDA Grading Model Validation

As a **quality assurance manager**,
I want grading model calculations validated,
So that farmer payments are based on accurate grade distributions.

**Acceptance Criteria:**

**Given** TBK grading model is seeded (binary: Primary/Secondary)
**When** a quality event with `leaf_type: two_leaves_bud` is processed
**Then** the grade is calculated as "Primary"

**Given** TBK reject conditions are configured
**When** a quality event with `leaf_type: coarse_leaf` is processed
**Then** the grade is calculated as "Secondary"

**Given** TBK conditional reject is configured
**When** a quality event with `leaf_type: banji, banji_hardness: hard` is processed
**Then** the grade is calculated as "Secondary"

**Given** TBK soft banji is acceptable
**When** a quality event with `leaf_type: banji, banji_hardness: soft` is processed
**Then** the grade is calculated as "Primary"

**Given** KTDA grading model is seeded (ternary: Grade A/B/Rejected)
**When** a quality event with `leaf_type: fine, moisture_level: optimal` is processed
**Then** the grade is calculated as "Grade A" (premium)

**Given** KTDA reject conditions are configured
**When** a quality event with `leaf_type: stalks` is processed
**Then** the grade is calculated as "Rejected"

**Test Data:**
```json
// TBK Test Cases
{ "leaf_type": "two_leaves_bud" } → "Primary"
{ "leaf_type": "coarse_leaf" } → "Secondary"
{ "leaf_type": "banji", "banji_hardness": "hard" } → "Secondary"
{ "leaf_type": "banji", "banji_hardness": "soft" } → "Primary"

// KTDA Test Cases
{ "leaf_type": "fine", "moisture_level": "optimal" } → "Grade A"
{ "leaf_type": "medium", "moisture_level": "wet" } → "Grade B"
{ "leaf_type": "stalks" } → "Rejected"
```

**Technical Notes:**
- Test File: `tests/e2e/scenarios/test_07_grading_validation.py`
- Uses seeded grading models from `seed/grading_models.json`
- Validates grade_rules logic

**Test Count:** 6 tests

**Story Points:** 2

---

#### Story 0.4.9: ZIP Processor Ingestion

As a **data engineer**,
I want ZIP file ingestion validated with manifest parsing and atomic storage,
So that bulk QC analyzer uploads are processed correctly.

**Acceptance Criteria:**

**Given** source config `e2e-qc-analyzer-zip` exists with `processor_type: zip-extraction`
**When** I upload a valid ZIP with manifest.json and 3 documents
**Then** all 3 documents are created in MongoDB atomically

**Given** a ZIP contains multiple documents
**When** processing completes successfully
**Then** all files are extracted and stored to blob storage with correct paths

**Given** the ZIP is processed
**When** I query via `get_documents(source_id="e2e-qc-analyzer-zip")`
**Then** all documents from the manifest are returned

**Given** a corrupt ZIP file is uploaded
**When** the blob event is triggered
**Then** processing fails gracefully with "Corrupt ZIP file detected" error

**Given** a ZIP without manifest.json is uploaded
**When** the blob event is triggered
**Then** processing fails with "Missing manifest file: manifest.json" error

**Given** an invalid manifest schema is in the ZIP
**When** the blob event is triggered
**Then** processing fails with manifest validation error

**Given** a ZIP with path traversal attempt (`../etc/passwd`) is uploaded
**When** the blob event is triggered
**Then** processing fails with "path traversal rejected" security error

**Given** a ZIP exceeds 500MB size limit
**When** upload is attempted
**Then** processing fails with size limit error

**Given** a duplicate ZIP (same content hash) is uploaded
**When** the blob event is triggered
**Then** the duplicate is detected and skipped

**Test Data:**
```
tests/e2e/fixtures/
├── valid_batch_3_docs.zip      # 3 leaf samples with images
├── corrupt_zip.zip             # Intentionally corrupt
├── missing_manifest.zip        # No manifest.json
└── path_traversal_attempt.zip  # Contains ../etc/passwd path
```

**Technical Notes:**
- Test File: `tests/e2e/scenarios/test_08_zip_ingestion.py`
- Tests ZIP processor security (path traversal)
- Tests atomic batch storage (all-or-nothing)

**Test Count:** 9 tests

**Story Points:** 5

---

## Summary

| Story | Description | Tests | Priority | Status |
|-------|-------------|-------|----------|--------|
| 0.4.1 | Infrastructure Verification | 19 | P0 | ✅ Done |
| 0.4.2 | Plantation MCP Contracts | 9 | P0 | To Do |
| 0.4.3 | Collection MCP Contracts | 5 | P0 | To Do |
| 0.4.4 | Factory-Farmer Flow | 5 | P0 | To Do |
| 0.4.5 | Quality Blob Ingestion | 6 | P0 | To Do |
| 0.4.6 | Weather + Mock AI | 5 | P1 | To Do |
| 0.4.7 | Cross-Model Events | 4 | P0 | To Do |
| 0.4.8 | Grading Validation | 6 | P1 | To Do |
| 0.4.9 | ZIP Processor Ingestion | 9 | P0 | To Do |
| **Total** | | **68** | | |

## Infrastructure Additions Required

1. **Mock AI Extractor Server**
   - Location: `tests/e2e/infrastructure/mock-servers/ai-extractor/`
   - Returns deterministic extractions for weather data
   - Docker container added to `docker-compose.e2e.yaml`

2. **Additional Source Configs** (`seed/source_configs.json`)
   - `e2e-qc-direct-json` - JSON extraction without AI
   - `e2e-qc-analyzer-zip` - ZIP processor config
   - `e2e-weather-api` - Weather API with mock AI

3. **Test Fixtures** (`tests/e2e/fixtures/`)
   - ZIP files for Story 0.4.9 (valid, corrupt, missing manifest, path traversal)

## Definition of Done

- [ ] All 68 tests pass locally with `pytest tests/e2e/scenarios/ -v`
- [ ] All tests pass in GitHub Actions CI (`e2e-tests.yaml` workflow)
- [ ] Mock AI Extractor server added to docker-compose
- [ ] Source configs updated for E2E test scenarios
- [ ] Test fixtures created for ZIP processor tests
- [ ] `tests/e2e/README.md` updated with new test scenarios

---

**Total Story Points:** 25

**Estimated Duration:** 2 sprints
