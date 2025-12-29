# Story 0.4.2: Plantation MCP Tool Contract Tests

**Status:** in-progress
**GitHub Issue:** #27

## Story

As a **developer integrating with Plantation Model**,
I want all 9 Plantation MCP tools validated with contract tests,
So that AI agents can reliably query plantation data.

## Acceptance Criteria

1. **AC1: get_factory** - Given seed data (regions, grading models) is loaded, When `get_factory` is called with a valid factory_id, Then it returns factory with name, code, region, quality thresholds, payment policy

2. **AC2: get_farmer** - Given a farmer exists in the database, When `get_farmer` is called with the farmer_id, Then it returns farmer with name, phone, farm size, region, collection point, preferences

3. **AC3: get_farmer_summary** - Given a farmer has quality history, When `get_farmer_summary` is called, Then it returns performance metrics structure with trends and yield data

4. **AC4: get_collection_points** - Given a factory has collection points, When `get_collection_points` is called with factory_id, Then it returns all CPs with their details

5. **AC5: get_farmers_by_collection_point** - Given farmers are registered at a collection point, When `get_farmers_by_collection_point` is called, Then it returns the list of farmers at that CP

6. **AC6: get_region** - Given regions are seeded, When `get_region` is called with region_id, Then it returns full region with geography, flush calendar, agronomic factors

7. **AC7: list_regions** - Given multiple regions exist, When `list_regions` is called with county or altitude_band filter, Then it returns filtered active regions

8. **AC8: get_current_flush** - Given a region has flush calendar configured, When `get_current_flush` is called, Then it returns correct flush period with days remaining based on current date

9. **AC9: get_region_weather** - Given a region has weather data, When `get_region_weather` is called with days parameter, Then it returns weather observations array with temp, precip, humidity

## Tasks / Subtasks

- [x] **Task 1: Create test file scaffold** (AC: All)
  - [x] Create `tests/e2e/scenarios/test_01_plantation_mcp_contracts.py`
  - [x] Import fixtures: `plantation_mcp`, `mongodb_direct`, `seed_data`
  - [x] Add `@pytest.mark.e2e` class marker
  - [x] Add file docstring with prerequisites

- [x] **Task 2: Implement factory/farmer test helpers** (AC: 1, 2)
  - [x] ~~Add helper method to create test factory via direct MongoDB insert~~ Using seed_data fixture
  - [x] ~~Add helper method to create test farmer via direct MongoDB insert~~ Using seed_data fixture
  - [x] ~~Add helper method to create test collection point via direct MongoDB insert~~ Using seed_data fixture
  - [x] ~~Use `E2ETestDataFactory` pattern~~ Using seed_data fixture with pre-seeded data

- [x] **Task 3: Implement get_factory test** (AC: 1)
  - [x] ~~Create factory with known ID via mongodb_direct~~ Using seeded FAC-E2E-001
  - [x] Call `plantation_mcp.call_tool("get_factory", {"factory_id": ...})`
  - [x] Assert response contains factory data
  - [x] Assert error for non-existent factory_id

- [x] **Task 4: Implement get_farmer test** (AC: 2)
  - [x] ~~Create farmer with known ID~~ Using seeded FRM-E2E-001
  - [x] Call `plantation_mcp.call_tool("get_farmer", {"farmer_id": ...})`
  - [x] Assert response contains farmer data
  - [x] Assert error for non-existent farmer_id

- [x] **Task 5: Implement get_farmer_summary test** (AC: 3)
  - [x] ~~Create farmer with performance data~~ Using seeded farmer_performance.json
  - [x] Call `plantation_mcp.call_tool("get_farmer_performance", {"farmer_id": ...})`
  - [x] Assert response contains performance metrics structure

- [x] **Task 6: Implement get_collection_points test** (AC: 4)
  - [x] ~~Create factory with 2+ collection points~~ Using seeded FAC-E2E-001 with 2 CPs
  - [x] Call `plantation_mcp.call_tool("get_collection_points", {"factory_id": ...})`
  - [x] Assert CPs returned with correct details

- [x] **Task 7: Implement get_farmers_by_collection_point test** (AC: 5)
  - [x] ~~Create collection point with 3+ farmers~~ Using seeded CP-E2E-001 with 2 farmers
  - [x] Call MCP tool to get farmers by CP
  - [x] Assert farmers returned

- [x] **Task 8: Implement region tests** (AC: 6, 7)
  - [x] Test get_region with seed region_id (e.g., "kericho-high")
  - [x] Assert returns region data
  - [x] Test list_regions with county="Kericho" filter
  - [x] Test list_regions with altitude_band="high" filter
  - [x] Assert correct regions returned

- [x] **Task 9: Implement get_current_flush test** (AC: 8)
  - [x] Call with region_id that has flush calendar
  - [x] Assert returns flush period info

- [x] **Task 10: Implement get_region_weather test** (AC: 9)
  - [x] ~~Seed weather data for region~~ Using seeded weather_observations.json
  - [x] Call `get_region_weather` with days=7
  - [x] Assert returns weather observations

- [ ] **Task 11: Test cleanup and validation** (AC: All)
  - [x] Verify no lint errors with `ruff check tests/e2e/`
  - [ ] Run all tests locally (requires Docker infrastructure)
  - [ ] Push and verify CI passes

## E2E Story Checklist (MANDATORY before marking Done)

**Read First:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Pre-Implementation
- [x] Read and understood `E2E-TESTING-MENTAL-MODEL.md`
- [x] Understand: Proto = source of truth, tests verify (not define) behavior

### Before Starting Docker
- [x] Validate seed data: `PYTHONPATH="${PYTHONPATH}:services/plantation-model/src" python tests/e2e/infrastructure/validate_seed_data.py`
- [x] All seed files pass validation

### During Implementation
- [x] If tests fail, investigate using the debugging checklist (not blindly modify code)
- [x] If seed data needs changes, fix seed data (not production code)
- [x] If production code has bugs, document each fix (see below)

### Production Code Changes (if any)
If you modified ANY production code, document each change here:

| File:Lines | What Changed | Why (with evidence) | Type |
|------------|--------------|---------------------|------|
| plantation_client.py:301-312 | HistoricalMetrics: `avg_grade`, `total_kg`, `delivery_count` → `primary_percentage_30d/90d/year`, `total_kg_30d/90d/year` | Proto:667-675 defines these field names; old fields don't exist | Bug fix |
| plantation_client.py:316-318 | TodayMetrics: `avg_grade`, `delivery_count` → `deliveries` | Proto:688 defines `deliveries` field; old fields don't exist | Bug fix |
| plantation_client.py:326-335 | CollectionPoint: removed `code`, `is_active`; added `status` | Proto:361-375 has `status` (line 372), no `code` or `is_active` fields | Bug fix |
| plantation_client.py:443-457 | GetCurrentFlush: direct field access → nested `response.current_flush.*` with HasField check | Proto:273-276 shows response has nested `current_flush` message | Bug fix |

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

### Architecture Patterns

- **MCP Tools are gRPC-based**: Use `PlantationMCPClient` from `tests/e2e/helpers/mcp_clients.py`
- **Tool Invocation Pattern**: `await plantation_mcp.call_tool("tool_name", {args})`
- **Response Format**: Returns dict from protobuf MessageToDict
- **Error Handling**: gRPC exceptions for failures

### Critical Implementation Details

1. **DO NOT use HTTP API for data operations** - Plantation Model HTTP only exposes `/health` and `/ready`
2. **All data queries via MCP gRPC client** - `plantation_mcp` fixture provides `PlantationMCPClient`
3. **Test data setup via mongodb_direct** - Bypass API for test data creation
4. **Seed data already loaded** - `seed_data` fixture loads regions, grading_models from JSON files

### Existing Tool Names (from mcp_clients.py)

```python
# Already implemented convenience methods:
get_farmer(farmer_id)       # via call_tool("get_farmer", ...)
get_factory(factory_id)     # via call_tool("get_factory", ...)
search_farmers(...)         # via call_tool("search_farmers", ...)
get_farmer_performance(...) # via call_tool("get_farmer_performance", ...)

# Need to verify actual tool names via list_tools()
```

### Test File Location

`tests/e2e/scenarios/test_01_plantation_mcp_contracts.py`

### Fixtures Available

| Fixture | Description |
|---------|-------------|
| `plantation_mcp` | gRPC MCP client for Plantation Model |
| `mongodb_direct` | Direct MongoDB access for data setup/verification |
| `seed_data` | Pre-loaded test data (grading_models, regions) |
| `wait_for_services` | Auto-invoked, ensures services healthy |

### Project Structure Notes

- Test file: `tests/e2e/scenarios/test_01_plantation_mcp_contracts.py`
- Fixtures in: `tests/e2e/conftest.py`
- MCP clients in: `tests/e2e/helpers/mcp_clients.py`
- Seed data in: `tests/e2e/infrastructure/seed/`

### Test Naming Convention

```python
class TestPlantationMCPContracts:
    async def test_get_factory_returns_valid_structure(self, ...):
    async def test_get_factory_returns_error_for_invalid_id(self, ...):
    async def test_get_farmer_returns_valid_structure(self, ...):
    # ... etc
```

### Seed Data Reference

All seed data files are located in `tests/e2e/infrastructure/seed/`:

| File | Contents | Key IDs |
|------|----------|---------|
| `regions.json` | 5 regions | `kericho-low`, `kericho-medium`, `kericho-high`, `nandi-high`, `bomet-medium` |
| `grading_models.json` | 2 models | `tbk_kenya_tea_v1` (binary), `ktda_ternary_v1` (ternary) |
| `factories.json` | 2 factories | `FAC-E2E-001` (TBK, kericho-high), `FAC-E2E-002` (KTDA, nandi-high) |
| `collection_points.json` | 3 CPs | `CP-E2E-001`, `CP-E2E-002` (FAC-E2E-001), `CP-E2E-003` (FAC-E2E-002) |
| `farmers.json` | 4 farmers | `FRM-E2E-001` to `FRM-E2E-004` |
| `farmer_performance.json` | 4 records | Performance summaries with metrics, trends, status |
| `weather_observations.json` | 2 regions | 7 days each for `kericho-high`, `nandi-high` |

**Test Data Relationships:**
```
FAC-E2E-001 (Kericho, TBK)
├── CP-E2E-001 (Ainamoi)
│   ├── FRM-E2E-001 (James Kiprop)
│   └── FRM-E2E-002 (Grace Cheruiyot, lead farmer)
└── CP-E2E-002 (Kapsoit)
    └── FRM-E2E-003 (Daniel Bett)

FAC-E2E-002 (Nandi, KTDA)
└── CP-E2E-003 (Nandi Hills Central)
    └── FRM-E2E-004 (Sarah Kosgei)
```

**Accessing Seed Data in Tests:**
```python
async def test_example(self, seed_data):
    # Access seeded data directly
    factories = seed_data["factories"]
    farmers = seed_data["farmers"]

    # Use known IDs for assertions
    factory_id = "FAC-E2E-001"
    farmer_id = "FRM-E2E-001"
```

### References

- [Source: `_bmad-output/epics/epic-0-4-e2e-tests.md` - Story 0.4.2 acceptance criteria]
- [Source: `tests/e2e/README.md` - E2E infrastructure documentation]
- [Source: `tests/e2e/helpers/mcp_clients.py` - MCP client implementation]
- [Source: `tests/e2e/conftest.py` - Fixture definitions]
- [Source: `_bmad-output/test-design-system-level.md` - E2E test infrastructure section]
- [Source: `_bmad-output/project-context.md` - MCP Server Rules section]

### Previous Story Learnings (0.4.1)

Story 0.4.1 Infrastructure Verification (19 tests) established:
- All services healthy before functional tests
- MCP tools accessible via gRPC
- `list_tools()` returns tool metadata
- Seed data loaded correctly to MongoDB
- Pattern: class-based test organization with `@pytest.mark.e2e`

### CI Validation Requirements

Before marking story done:
1. Run locally: `PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_01_plantation_mcp_contracts.py -v`
2. Run lint: `ruff check tests/e2e/scenarios/test_01_plantation_mcp_contracts.py`
3. Push and verify GitHub Actions CI passes

### Local E2E Test Setup

**Prerequisites:** Docker 24.0+, Docker Compose 2.20+

**Step 1: Build service images**
```bash
# From repository root - build all 4 services
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml build
```

**Step 2: Start the E2E stack**
```bash
# Start all containers in detached mode
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
```

**Step 3: Wait for all services to be healthy**
```bash
# Check container status - all should show "healthy"
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps

# Or watch until ready
watch -n 2 'docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps'
```

**Step 4: Run the tests**
```bash
# Run this specific test file
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_01_plantation_mcp_contracts.py -v

# Or run all E2E tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
```

**Step 5: Cleanup (when done)**
```bash
# Stop and remove containers
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down

# Remove volumes too (clears all data)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

**Troubleshooting:**
```bash
# View logs if services fail to start
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml logs plantation-model
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml logs plantation-mcp

# Rebuild without cache if images are stale
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml build --no-cache
```

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Created `test_01_plantation_mcp_contracts.py` with 14 test methods across 9 test classes
- Tests cover all 9 Plantation MCP tools as specified in acceptance criteria
- Used seed data from fixtures instead of creating data dynamically (cleaner approach)
- Test assertions are defensive - check for content presence with multiple possible field names
- All tests use `@pytest.mark.e2e` and `@pytest.mark.asyncio` markers
- Lint check passed with no errors

### File List

**Created:**
- `tests/e2e/scenarios/test_01_plantation_mcp_contracts.py` - Main test file with 9 tool contract tests

**Modified (earlier in session - seed data):**
- `tests/e2e/infrastructure/seed/factories.json` - 2 test factories
- `tests/e2e/infrastructure/seed/collection_points.json` - 3 test CPs
- `tests/e2e/infrastructure/seed/farmers.json` - 4 test farmers
- `tests/e2e/infrastructure/seed/farmer_performance.json` - 4 performance records
- `tests/e2e/infrastructure/seed/weather_observations.json` - 7 days for 2 regions
- `tests/e2e/conftest.py` - Added seeding for new data files
- `tests/e2e/helpers/mongodb_direct.py` - Added seed methods for new collections
