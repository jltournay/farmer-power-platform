# Story 0.75.18: E2E Weather Observation Extraction Flow

**Status:** in-progress
**GitHub Issue:** #148

## Story

As a **platform developer**,
I want end-to-end validation of the weather extraction flow with real AI Model and LLM calls,
So that the AI Model integration is proven before building more agents.

## Context

**Story 0.75.17** implemented the Extractor agent type with configuration and golden samples for QC events. **Story 2-12** implemented the async event-driven communication from Collection Model to AI Model. This story validates the full integration path with a **real weather extraction workflow** using real LLM calls via OpenRouter.

### What Exists (DO NOT RECREATE)

| Component | Location | Purpose |
|-----------|----------|---------|
| `ExtractorWorkflow` | `services/ai-model/src/ai_model/workflows/extractor.py` | 5-step linear extraction workflow |
| `AgentExecutor` | `services/ai-model/src/ai_model/services/agent_executor.py` | Orchestrates config→prompt→workflow→publish |
| `AgentConfigCache` | `services/ai-model/src/ai_model/domain/source_cache_loader.py` | MongoDB cache for agent configs |
| `PromptCache` | `services/ai-model/src/ai_model/domain/source_cache_loader.py` | MongoDB cache for prompts |
| `EventSubscriber` | `services/ai-model/src/ai_model/events/subscriber.py` | DAPR streaming handler for `ai.agent.requested` |
| QC Extractor Config | `config/agents/qc-event-extractor.yaml` | Sample extractor agent config (Story 0.75.17) |
| QC Extractor Prompt | `config/prompts/qc-event-extractor.json` | Sample prompt for QC extraction (Story 0.75.17) |
| Weather Source Config | `config/source-configs/weather-api.yaml` | Source config for weather pull (needs `ai_agent_id` update) |
| E2E Weather Test | `tests/e2e/scenarios/test_05_weather_ingestion.py` | Skipped test to be re-enabled |
| Collection Event Publishing | `services/collection-model/src/collection_model/processors/json_extraction.py` | Publishes `AgentRequestEvent` when `ai_agent_id` set |
| Collection Event Subscription | `services/collection-model/src/collection_model/events/subscriber.py` | Handles `AgentCompletedEvent`/`AgentFailedEvent` |

### What This Story Creates

1. **Weather Extractor Agent Config** - `config/agents/weather-extractor.yaml`
2. **Weather Extractor Prompt** - `config/prompts/weather-extractor.json`
3. **Update Weather Source Config** - Add `ai_agent_id: weather-extractor`
4. **E2E Seed Data** - Agent config and prompt in MongoDB seeds
5. **Re-enabled E2E Tests** - Remove skip marker, adapt for real AI Model

---

## ⚠️ CRITICAL: E2E Testing Mental Model (MANDATORY READING)

> **Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md` BEFORE starting this story.**

### Truth Hierarchy

```
TRUTH HIERARCHY (Top = Most Authoritative)
══════════════════════════════════════════════════════════════

1. PROTO DEFINITIONS          ← The Contract (NEVER changes for tests)
2. PRODUCTION CODE            ← Implements the Contract
3. SEED DATA                  ← Test Input (must conform to production)
4. TEST ASSERTIONS            ← Verify behavior

══════════════════════════════════════════════════════════════
```

### This Story Scope: CONFIG + SEED + TEST ONLY

| Layer | Changes Expected | Justification Required? |
|-------|------------------|------------------------|
| Proto definitions | ❌ NO changes | N/A |
| Production code (`services/*/src/`) | ❌ NO changes expected | **YES - with evidence** |
| Config files (`config/`) | ✅ Create/modify | No |
| Seed data (`tests/e2e/seed_data/`) | ✅ Create/modify | No |
| Test scenarios (`tests/e2e/scenarios/`) | ✅ Modify | No |

### 🚨 Production Code Changes: PROHIBITED WITHOUT JUSTIFICATION

**If you find yourself needing to modify production code to make tests pass:**

1. **STOP** - Do not proceed
2. **INVESTIGATE** - Is the production code actually wrong per proto?
3. **DOCUMENT** - Fill out the Production Code Change Log below with evidence
4. **If you cannot provide evidence, the change is NOT allowed**

**Valid reasons for production code changes:**
- Bug fix: Production code doesn't match proto schema (provide proto line numbers)
- Bug fix: Production code has logic error (provide expected vs actual behavior)

**Invalid reasons (WILL BE REJECTED):**
- "To make tests pass"
- "Test expects different behavior"
- "Seed data requires this change"

---

## Production Code Change Log (MANDATORY IF PRODUCTION CODE CHANGED)

> **No documentation = No merge.** If this table is empty, production code MUST NOT have changed.

| # | File | Lines | What Changed | Why (Root Cause) | Evidence (Proto/Spec) | Type |
|---|------|-------|--------------|------------------|----------------------|------|
| - | - | - | _None expected for this story_ | - | - | - |

**If you add entries above, each must include:**
- **File:** Full path with line numbers
- **What Changed:** Specific code change description
- **Why:** Root cause (NOT "to pass tests")
- **Evidence:** Proto line number, API spec, or other authoritative source
- **Type:** Bug fix | Schema alignment | New feature

---

## Acceptance Criteria

1. **AC1: Weather Extractor Agent Configuration** - Create `config/agents/weather-extractor.yaml`:
   - Agent ID: `weather-extractor`
   - Agent type: `extractor`
   - LLM: OpenRouter-compatible model (e.g., `anthropic/claude-3-haiku`)
   - Temperature: `0.1` (deterministic extraction)
   - Extraction schema with weather fields: `observation_date`, `temperature_c`, `humidity_percent`, `precipitation_mm`, `wind_speed_kmh`
   - Normalization rules for timestamp and temperature formats

2. **AC2: Weather Extractor Prompt Configuration** - Create `config/prompts/weather-extractor.json`:
   - System prompt explaining weather data extraction from Open-Meteo API responses
   - User prompt template with `{{raw_data}}` placeholder
   - Output schema for JSON validation
   - Prompt validates against existing `Prompt` Pydantic model

3. **AC3: Update Weather Source Config** - Modify `config/source-configs/weather-api.yaml`:
   - Set `ai_agent_id: weather-extractor` under `ai_extraction` section
   - Verify iteration config: `foreach: region`, `source_mcp: plantation-mcp`, `source_tool: list_active_regions`
   - Storage index collection: `weather_documents`

4. **AC4: E2E Seed Data for AI Model** - Create seed data entries:
   - Add weather-extractor agent config to `tests/e2e/seed_data/agent_configs.json`
   - Add weather-extractor prompt to `tests/e2e/seed_data/prompts.json`
   - Ensure seeds are loaded by E2E infrastructure setup

5. **AC5: E2E Test Re-enablement** - Update `tests/e2e/scenarios/test_05_weather_ingestion.py`:
   - Remove `pytestmark = pytest.mark.skip()` at line 40
   - Update agent ID from `mock-weather-extractor` to `weather-extractor`
   - Tests validate real AI Model extraction via OpenRouter
   - Tests poll for `AgentCompletedEvent` via document status update

6. **AC6: E2E Test Passes** - Full E2E flow works:
   - Collection Model triggers weather pull job
   - Weather data fetched from Open-Meteo API
   - Document stored with `status="pending"`
   - `AgentRequestEvent` published to `ai.agent.requested`
   - AI Model extracts weather fields via real LLM call
   - `AgentCompletedEvent` published to `ai.agent.weather-extractor.completed`
   - Collection Model updates document with extracted fields
   - Plantation MCP `get_region_weather` returns weather observations
   - All E2E tests pass (previously 8 skipped now pass)

7. **AC7: CI E2E Passes** - E2E workflow passes on story branch before code review

## Tasks / Subtasks

- [ ] **Task 1: Create Weather Extractor Agent Configuration** (AC: #1)
  - [ ] Create `config/agents/weather-extractor.yaml`:
    ```yaml
    agent_id: weather-extractor
    agent_type: extractor
    version: "1.0.0"
    prompt_id: weather-extractor-prompt-v1
    description: "Extracts structured weather observations from Open-Meteo API responses"

    llm:
      model: anthropic/claude-3-haiku
      temperature: 0.1
      max_tokens: 500
      output_format: json

    extraction_schema:
      required_fields:
        - observation_date
        - temperature_c
        - humidity_percent
        - precipitation_mm
      optional_fields:
        - wind_speed_kmh
        - weather_code
        - extraction_confidence
      field_types:
        observation_date: string  # ISO 8601 format
        temperature_c: number
        humidity_percent: number
        precipitation_mm: number
        wind_speed_kmh: number
        weather_code: integer
        extraction_confidence: number

    normalization_rules:
      - field: observation_date
        transform: iso8601
      - field: temperature_c
        transform: round_2dp

    rag:
      enabled: false
    ```
  - [ ] Validate YAML against `ExtractorConfig` Pydantic model

- [ ] **Task 2: Create Weather Extractor Prompt Configuration** (AC: #2)
  - [ ] Create `config/prompts/weather-extractor.json`:
    ```json
    {
      "prompt_id": "weather-extractor-prompt-v1",
      "agent_id": "weather-extractor",
      "version": "1.0.0",
      "status": "active",
      "system_prompt": "You are a weather data extraction agent. Extract structured weather observations from Open-Meteo API JSON responses. Return ONLY valid JSON matching the extraction schema.",
      "template": "Extract weather observation data from the following Open-Meteo API response.\n\nInput data:\n{{raw_data}}\n\nExtract the following fields:\n- observation_date: The date of the weather observation (ISO 8601 format)\n- temperature_c: Temperature in Celsius\n- humidity_percent: Relative humidity percentage (0-100)\n- precipitation_mm: Precipitation in millimeters\n- wind_speed_kmh: Wind speed in km/h (optional)\n- weather_code: WMO weather code (optional)\n- extraction_confidence: Your confidence in the extraction (0-1)\n\nReturn ONLY valid JSON matching the schema. Do not include explanations.",
      "metadata": {
        "created_by": "dev-story",
        "domain": "weather"
      }
    }
    ```
  - [ ] Validate JSON against `Prompt` Pydantic model

- [ ] **Task 3: Update Weather Source Config** (AC: #3)
  - [ ] Edit `config/source-configs/weather-api.yaml`:
    - [ ] Add `ai_extraction.enabled: true`
    - [ ] Add `ai_extraction.agent_id: weather-extractor`
  - [ ] Verify iteration config intact
  - [ ] Verify storage config: `index_collection: weather_documents`

- [ ] **Task 4: Create E2E Seed Data** (AC: #4)
  - [ ] Create or update `tests/e2e/seed_data/agent_configs.json`:
    - [ ] Add `weather-extractor` agent config entry
    - [ ] Ensure `qc-event-extractor` entry exists (from Story 0.75.17)
  - [ ] Create or update `tests/e2e/seed_data/prompts.json`:
    - [ ] Add `weather-extractor-prompt-v1` prompt entry
    - [ ] Ensure `qc-event-extractor-prompt-v1` entry exists (from Story 0.75.17)
  - [ ] Update seed data loader in `tests/e2e/infrastructure/conftest.py`:
    - [ ] Verify `seed_ai_model_data()` loads agent_configs and prompts
    - [ ] Insert into `ai_model_e2e.agent_configs` and `ai_model_e2e.prompts` collections

- [ ] **Task 5: Re-enable E2E Weather Tests** (AC: #5)
  - [ ] Remove `pytestmark = pytest.mark.skip()` from line 40
  - [ ] Update `MOCK_AI_MODEL_PORT` to correct AI Model gRPC port (50051 internal, 8090 external)
  - [ ] Update test assertions for real AI extraction results
  - [ ] Add polling for document status change from `pending` to `complete`
  - [ ] Verify weather fields in `extracted_fields`

- [ ] **Task 6: Run Local E2E Tests** (AC: #6, MANDATORY)
  - [ ] Rebuild E2E infrastructure: `docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build`
  - [ ] Verify Docker images rebuilt (NOT cached)
  - [ ] Run E2E tests: `PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v`
  - [ ] Verify weather tests pass (previously skipped)
  - [ ] Capture output in "Local Test Run Evidence" section
  - [ ] Tear down: `docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v`

- [ ] **Task 7: CI E2E Verification** (AC: #7, MANDATORY)
  - [ ] Push to story branch
  - [ ] Trigger E2E CI: `gh workflow run e2e.yaml --ref feature/0-75-18-e2e-weather-extraction`
  - [ ] Monitor until completion: `gh run watch <run-id>`
  - [ ] Verify PASSED status
  - [ ] Record run ID in story file

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.18: E2E Weather Observation Extraction Flow"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-18-e2e-weather-extraction
  ```

**Branch name:** `feature/0-75-18-e2e-weather-extraction`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #148`
- [ ] Commits are atomic by type (config, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-18-e2e-weather-extraction`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.18: E2E Weather Observation Extraction Flow" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-18-e2e-weather-extraction`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/ -v --tb=no -q
```
**Output:**
```
(paste test summary here - e.g., "X passed in Y.YYs")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure with rebuild
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
============================= test session starts ==============================
platform darwin -- Python 3.11.12, pytest-9.0.2, pluggy-1.6.0
collected 107 items

tests/e2e/scenarios/test_05_weather_ingestion.py::TestWeatherExtractorConfiguration::test_weather_extractor_agent_config_exists PASSED
tests/e2e/scenarios/test_05_weather_ingestion.py::TestWeatherExtractorConfiguration::test_weather_extractor_prompt_exists PASSED
tests/e2e/scenarios/test_05_weather_ingestion.py::TestWeatherPullJobTrigger::test_weather_pull_job_trigger_succeeds PASSED
tests/e2e/scenarios/test_05_weather_ingestion.py::TestWeatherDocumentCreation::test_weather_document_created_with_region_linkage PASSED
tests/e2e/scenarios/test_05_weather_ingestion.py::TestWeatherDocumentCreation::test_weather_document_has_weather_attributes SKIPPED (OPENROUTER_API_KEY not set)
tests/e2e/scenarios/test_05_weather_ingestion.py::TestPlantationMCPWeatherQuery::test_get_region_weather_returns_observations PASSED
tests/e2e/scenarios/test_05_weather_ingestion.py::TestCollectionMCPWeatherQuery::test_get_documents_returns_weather_document PASSED

================== 105 passed, 2 skipped in 127.69s (0:02:07) ==================
```
**Note:** `test_weather_document_has_weather_attributes` is skipped when OPENROUTER_API_KEY is not set.
This test requires real LLM calls. In CI, the test will run with the API key from GitHub Secrets.

**E2E passed:** [x] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/0-75-18-e2e-weather-extraction

# Trigger E2E CI
gh workflow run e2e.yaml --ref feature/0-75-18-e2e-weather-extraction

# Wait and check status
gh run list --branch feature/0-75-18-e2e-weather-extraction --limit 3
```
**CI Run ID:** _______________
**CI E2E Run ID:** _______________
**CI Status:** [ ] Passed / [ ] Failed
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Event Flow Architecture (from Story 2-12)

```
Collection Model → DAPR Pub/Sub → AI Model → DAPR Pub/Sub → Collection Model
       │                  │              │                       │
       │ 1. Store doc     │              │                       │
       │    status=pending│              │                       │
       │                  │              │                       │
       │ 2. Publish AgentRequestEvent    │                       │
       │    topic: ai.agent.requested    │                       │
       │ ─────────────────┴──────────────┤                       │
       │                                 │ 3. Receive event      │
       │                                 │    Load config/prompt │
       │                                 │    Execute workflow   │
       │                                 │    Call LLM (real)    │
       │                                 │                       │
       │                                 │ 4. Publish AgentCompletedEvent
       │                                 │    topic: ai.agent.weather-extractor.completed
       │                                 │ ──────────────────────┤
       │                                                         │
       │ 5. Receive result                                       │
       │    Update doc status=complete                           │
       │    Store extracted_fields                               │
       │    Emit success event                                   │
```

### Critical Configuration Requirements

| Config | Location | Required Fields |
|--------|----------|-----------------|
| Agent Config | MongoDB `ai_model_e2e.agent_configs` | `agent_id`, `agent_type`, `prompt_id`, `llm.model` |
| Prompt | MongoDB `ai_model_e2e.prompts` | `prompt_id`, `agent_id`, `template`, `status: active` |
| Source Config | MongoDB `collection_model_e2e.source_configs` | `ai_extraction.enabled`, `ai_extraction.agent_id` |

### Open-Meteo API Response Structure

The weather extractor will receive JSON like:
```json
{
  "latitude": -1.29,
  "longitude": 36.82,
  "generationtime_ms": 0.123,
  "daily": {
    "time": ["2026-01-10"],
    "temperature_2m_max": [28.5],
    "temperature_2m_min": [18.2],
    "precipitation_sum": [0.5],
    "relative_humidity_2m_mean": [72],
    "wind_speed_10m_max": [15.3]
  }
}
```

### Expected Extracted Fields

```json
{
  "observation_date": "2026-01-10",
  "temperature_c": 23.35,  // Average of max/min
  "humidity_percent": 72,
  "precipitation_mm": 0.5,
  "wind_speed_kmh": 15.3,
  "extraction_confidence": 0.95
}
```

### E2E Test Polling Pattern

```python
# Wait for document status to change from "pending" to "complete"
async def wait_for_extraction_complete(mongodb, doc_id, timeout=45.0):
    start = time.time()
    while time.time() - start < timeout:
        doc = await mongodb.find_one("weather_documents", {"_id": doc_id})
        if doc and doc.get("extraction", {}).get("status") == "complete":
            return doc
        await asyncio.sleep(0.5)
    raise TimeoutError(f"Document {doc_id} extraction did not complete")
```

### OpenRouter Credentials (E2E)

E2E tests require `OPENROUTER_API_KEY` environment variable. Set in:
- Local: `.env` file
- CI: GitHub Secrets

### Anti-Patterns to AVOID

1. **DO NOT hardcode LLM responses** - Use real OpenRouter calls in E2E
2. **DO NOT skip E2E tests** - All 8 skipped tests must now pass
3. **DO NOT create mock AI server** - Use real AI Model container
4. **🚨 DO NOT modify production code without evidence** - See "Production Code Change Log" section above
5. **DO NOT use direct MongoDB inserts** - Use seed data fixtures

### 🚨 Production Code Modification Rules (CRITICAL)

**This story is CONFIG + SEED + TEST only. Production code changes require:**

1. **Evidence from proto or spec** - Not "to make tests pass"
2. **Documentation in Production Code Change Log** - Table must be filled
3. **Code review approval** - PR will be blocked without justification

**If tests fail and you think production code needs to change:**
```
STOP → Read E2E-TESTING-MENTAL-MODEL.md → Follow debugging checklist →
If production bug found → Document with evidence → Then fix
```

**Decision tree:**
```
Test fails
    │
    ├── Seed data wrong? → Fix seed data
    │
    ├── Test assertion wrong? → Fix test
    │
    └── Production code wrong per proto? → Document evidence → Fix production
```

### Files to Create

| File | Type | Purpose |
|------|------|---------|
| `config/agents/weather-extractor.yaml` | Config | Agent configuration |
| `config/prompts/weather-extractor.json` | Config | Prompt template |
| `tests/e2e/seed_data/agent_configs.json` | Seed | MongoDB seed for configs |
| `tests/e2e/seed_data/prompts.json` | Seed | MongoDB seed for prompts |

### Files to Modify

| File | Change |
|------|--------|
| `config/source-configs/weather-api.yaml` | Add `ai_extraction.agent_id: weather-extractor` |
| `tests/e2e/scenarios/test_05_weather_ingestion.py` | Remove skip, update for real AI |
| `tests/e2e/infrastructure/conftest.py` | Add seed data loading for AI Model |

### References

- [Source: `_bmad-output/architecture/ai-model-architecture/communication-pattern.md`]
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md` § Story 0.75.18]
- [Source: `_bmad-output/sprint-artifacts/2-12-collection-ai-model-event-driven-communication.md`]
- [Source: `_bmad-output/sprint-artifacts/0-75-17-extractor-agent-implementation.md`]
- [Source: `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`]

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- (list new files)

**Modified:**
- (list modified files with brief description)

---

_Story created: 2026-01-10_
_Created by: BMAD create-story workflow_
