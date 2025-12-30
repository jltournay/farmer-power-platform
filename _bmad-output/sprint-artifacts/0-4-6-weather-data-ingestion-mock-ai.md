# Story 0.4.6: Weather Data Ingestion with Mock AI

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->
**Epic:** [Epic 0.4: E2E Test Scenarios](../epics/epic-0-4-e2e-tests.md)

## Story

As a **data engineer**,
I want weather data ingestion validated with mocked AI extraction,
So that real weather API data flows through the pipeline with deterministic extraction.

## Acceptance Criteria

1. **AC1: Mock AI Extractor Deployment** - Given Mock AI Extractor server is deployed at :8090, When I send an extraction request for weather data, Then the mock returns deterministic weather document structure

2. **AC2: Weather Pull Job Trigger** - Given source config `e2e-weather-api` exists with weather API endpoint, When the weather pull job is triggered, Then real weather data is fetched from Open-Meteo API

3. **AC3: Weather Document Creation** - Given weather data is fetched, When the AI extraction mock processes it, Then a weather document is created with region linkage

4. **AC4: Plantation MCP Query** - Given weather documents exist for a region, When I call `get_region_weather` via Plantation MCP, Then weather observations are returned correctly

5. **AC5: Collection MCP Query** - Given the weather document is stored, When I query via Collection MCP `get_documents(source_id="e2e-weather-api")`, Then the document is returned with weather attributes

## Tasks / Subtasks

- [ ] **Task 1: Create Mock AI Extractor Server** (AC: 1)
  - [ ] Create `tests/e2e/infrastructure/mock-servers/ai-extractor/` directory
  - [ ] Create `server.py` FastAPI server returning deterministic weather extraction
  - [ ] Create `Dockerfile` for containerization
  - [ ] Add `/health` endpoint for healthcheck
  - [ ] Add `/extract` endpoint matching AI Model extraction contract

- [ ] **Task 2: Add Mock AI Extractor to Docker Compose** (AC: 1)
  - [ ] Add `mock-ai-extractor` service to `docker-compose.e2e.yaml`
  - [ ] Configure port mapping (8090:8080)
  - [ ] Add healthcheck
  - [ ] Add to e2e-network

- [ ] **Task 3: Create Weather Source Config** (AC: 2)
  - [ ] Add `e2e-weather-api` to `seed/source_configs.json`
  - [ ] Configure `mode: scheduled_pull` for weather API
  - [ ] Configure `ai_agent_id: mock-weather-extractor`
  - [ ] Set `link_field: region_id` for region linkage

- [ ] **Task 4: Create E2E Test File** (AC: All)
  - [ ] Create `tests/e2e/scenarios/test_05_weather_ingestion.py`
  - [ ] Import fixtures: `collection_mcp`, `plantation_mcp`, `collection_api`, `seed_data`
  - [ ] Add `@pytest.mark.e2e` class marker
  - [ ] Add file docstring with prerequisites

- [ ] **Task 5: Implement Mock AI Test** (AC: 1)
  - [ ] Test mock server is accessible at :8090
  - [ ] Test extraction endpoint returns deterministic weather structure
  - [ ] Verify response schema matches expected format

- [ ] **Task 6: Implement Weather Pull Test** (AC: 2)
  - [ ] Call Collection Model API to trigger weather pull
  - [ ] Verify Open-Meteo API is called (real data)
  - [ ] Verify weather data is received successfully

- [ ] **Task 7: Implement Document Creation Test** (AC: 3)
  - [ ] Wait for async processing after pull trigger
  - [ ] Query MongoDB for weather documents
  - [ ] Verify document has region_id linkage
  - [ ] Verify extracted weather attributes

- [ ] **Task 8: Implement MCP Query Tests** (AC: 4, 5)
  - [ ] Test `get_region_weather` via Plantation MCP
  - [ ] Verify weather observations returned
  - [ ] Test `get_documents(source_id="e2e-weather-api")` via Collection MCP
  - [ ] Verify document attributes

- [ ] **Task 9: Test Validation** (AC: All)
  - [ ] Run `ruff check tests/e2e/scenarios/test_05_weather_ingestion.py`
  - [ ] Run all tests locally with Docker infrastructure
  - [ ] Verify CI pipeline passes

## E2E Story Checklist (MANDATORY before marking Done)

**Read First:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Pre-Implementation
- [ ] Read and understood `E2E-TESTING-MENTAL-MODEL.md`
- [ ] Understand: Proto = source of truth, tests verify (not define) behavior

### Before Starting Docker
- [ ] Validate seed data: `PYTHONPATH="${PYTHONPATH}:services/plantation-model/src:services/collection-model/src" python tests/e2e/infrastructure/validate_seed_data.py`
- [ ] All seed files pass validation

### During Implementation
- [ ] If tests fail, investigate using the debugging checklist (not blindly modify code)
- [ ] If seed data needs changes, fix seed data (not production code)
- [ ] If production code has bugs, document each fix (see below)

### Production Code Changes (if any)
If you modified ANY production code, document each change here:

| File:Lines | What Changed | Why (with evidence) | Type |
|------------|--------------|---------------------|------|
| (none expected) | | | |

**Rules:**
- "To pass tests" is NOT a valid reason
- Must reference proto line, API spec, or other evidence
- If you can't fill this out, you may not understand what you're changing

### Before Marking Done
- [ ] All tests pass locally with Docker infrastructure
- [ ] `ruff check` and `ruff format --check` pass
- [ ] CI pipeline is green
- [ ] If production code changed: Change log above is complete
- [ ] Story file updated with completion notes

---

## Dev Notes

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     WEATHER INGESTION FLOW (Story 0.4.6)                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Trigger: Scheduled Pull Job OR Manual API Call                      │
│         │                                                               │
│         ▼                                                               │
│  2. Collection Model fetches from Open-Meteo API (REAL)                 │
│         │                                                               │
│         ▼                                                               │
│  3. Raw weather JSON sent to Mock AI Extractor (MOCK)                   │
│     └─► http://mock-ai-extractor:8080/extract                           │
│         │                                                               │
│         ▼                                                               │
│  4. Mock returns deterministic extraction (temp, precip, humidity)      │
│         │                                                               │
│         ▼                                                               │
│  5. Weather document stored in MongoDB (collection_e2e.weather_docs)    │
│         │                                                               │
│         ▼                                                               │
│  6. Query via:                                                          │
│     - Collection MCP: get_documents(source_id="e2e-weather-api")        │
│     - Plantation MCP: get_region_weather(region_id, days)               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Mock Strategy (from Epic)

| Component | Approach | Rationale |
|-----------|----------|-----------|
| Open-Meteo API | **REAL** | Free, stable, validates real API integration |
| AI Extraction | **MOCK** | Deterministic responses for E2E |
| MongoDB | **REAL** | Full database behavior |

### Mock AI Extractor Specification

The mock server should:
1. Listen on port 8080 (mapped to host 8090)
2. Accept POST requests to `/extract` with weather JSON
3. Return deterministic weather attributes:
   - `temperature_c`: Based on input timestamp
   - `precipitation_mm`: Based on input data
   - `humidity_percent`: Deterministic value
   - `region_id`: From input or default

**Mock Extraction Response Schema:**
```json
{
  "extracted_fields": {
    "region_id": "REG-E2E-001",
    "observation_date": "2025-01-15",
    "temperature_c": 22.5,
    "temperature_min_c": 18.0,
    "temperature_max_c": 27.0,
    "precipitation_mm": 5.2,
    "humidity_percent": 75.0,
    "source": "open-meteo"
  },
  "confidence": 0.95,
  "validation_passed": true,
  "validation_warnings": []
}
```

### Source Config Schema

**`e2e-weather-api` config structure:**
```json
{
  "source_id": "e2e-weather-api",
  "enabled": true,
  "description": "E2E Test - Weather data from Open-Meteo with mock AI extraction",
  "config": {
    "ingestion": {
      "mode": "scheduled_pull",
      "processor_type": "json-extraction",
      "api_endpoint": "https://api.open-meteo.com/v1/forecast",
      "schedule": "0 */6 * * *"
    },
    "transformation": {
      "ai_agent_id": "mock-weather-extractor",
      "link_field": "region_id",
      "extract_fields": [
        "region_id",
        "observation_date",
        "temperature_c",
        "precipitation_mm",
        "humidity_percent"
      ]
    },
    "storage": {
      "index_collection": "weather_documents",
      "raw_container": "raw-documents-e2e"
    },
    "events": {
      "on_success": {
        "topic": "collection.weather_observation.received"
      }
    }
  }
}
```

### Open-Meteo API Reference

**Endpoint:** `https://api.open-meteo.com/v1/forecast`

**Sample Request:**
```
GET /v1/forecast?latitude=-1.286&longitude=36.817&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Africa/Nairobi
```

**Sample Response:**
```json
{
  "daily": {
    "time": ["2025-01-15"],
    "temperature_2m_max": [27.1],
    "temperature_2m_min": [18.3],
    "precipitation_sum": [5.2]
  }
}
```

### Existing Infrastructure Patterns

**From Story 0.4.5 learnings:**
1. Use `azurite_client` fixture for blob operations
2. Use `collection_api.trigger_*` methods for API calls
3. Use `asyncio.sleep(3)` for async processing wait
4. Use `mongodb_direct` for verification queries
5. Path patterns extract fields from blob path

**From google-elevation mock server:**
- FastAPI server structure
- Deterministic responses based on input
- `/health` endpoint for healthcheck
- Dockerfile with uvicorn

### Test File Location

`tests/e2e/scenarios/test_05_weather_ingestion.py`

### Fixtures Available

| Fixture | Description |
|---------|-------------|
| `collection_api` | HTTP client for Collection Model endpoints |
| `collection_mcp` | gRPC MCP client for Collection Model |
| `plantation_mcp` | gRPC MCP client for Plantation Model |
| `mongodb_direct` | Direct MongoDB access for verification |
| `seed_data` | Pre-loaded test data (source_configs, regions) |
| `wait_for_services` | Auto-invoked, ensures services healthy |

### Seed Data Dependencies

| File | Required Data |
|------|---------------|
| `source_configs.json` | `e2e-weather-api` source config |
| `regions.json` | Region `REG-E2E-001` for weather linkage |

### File Structure to Create

```
tests/e2e/
├── infrastructure/
│   ├── mock-servers/
│   │   ├── google-elevation/  (existing)
│   │   └── ai-extractor/      (NEW)
│   │       ├── Dockerfile
│   │       └── server.py
│   └── docker-compose.e2e.yaml  (UPDATE)
├── infrastructure/seed/
│   └── source_configs.json      (UPDATE)
└── scenarios/
    └── test_05_weather_ingestion.py  (NEW)
```

### CI Validation Requirements

Before marking story done:
1. Run locally: `PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_05_weather_ingestion.py -v`
2. Run lint: `ruff check tests/e2e/scenarios/test_05_weather_ingestion.py`
3. Push and verify GitHub Actions CI passes

### Local E2E Test Setup

**Prerequisites:** Docker 24.0+, Docker Compose 2.20+

**Quick Start:**
```bash
# Rebuild to include new mock server
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml build

# Start E2E stack
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d

# Wait for services to be healthy
watch -n 2 'docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps'

# Run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_05_weather_ingestion.py -v

# Cleanup
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

### References

- [Source: `_bmad-output/epics/epic-0-4-e2e-tests.md` - Story 0.4.6 acceptance criteria]
- [Source: `tests/e2e/README.md` - E2E infrastructure documentation]
- [Source: `tests/e2e/infrastructure/mock-servers/google-elevation/server.py` - Mock server pattern]
- [Source: `tests/e2e/scenarios/test_04_quality_blob_ingestion.py` - Test file pattern]
- [Source: `_bmad-output/project-context.md` - Architecture rules]
- [Source: `services/collection-model/` - Collection Model implementation]

### Critical Implementation Notes

1. **Mock AI uses port 8080 internally, mapped to 8090 externally** - Matches epic spec
2. **Collection Model must support AI extraction path** - Verify `ai_agent_id` config routes to mock
3. **Weather documents link via region_id** - Different from quality events which link via farmer_id
4. **Open-Meteo is free, no API key needed** - Real API call in tests
5. **Deterministic mock is critical** - Same input = same output for reproducible tests

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - story creation phase

### Completion Notes List

(To be filled during implementation)

### File List

**To Create:**
- `tests/e2e/infrastructure/mock-servers/ai-extractor/server.py`
- `tests/e2e/infrastructure/mock-servers/ai-extractor/Dockerfile`
- `tests/e2e/scenarios/test_05_weather_ingestion.py`

**To Modify:**
- `tests/e2e/infrastructure/docker-compose.e2e.yaml`
- `tests/e2e/infrastructure/seed/source_configs.json`
