# Story 0.4.2: Plantation MCP Tool Contract Tests

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

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

- [ ] **Task 1: Create test file scaffold** (AC: All)
  - [ ] Create `tests/e2e/scenarios/test_01_plantation_mcp_contracts.py`
  - [ ] Import fixtures: `plantation_mcp`, `mongodb_direct`, `seed_data`
  - [ ] Add `@pytest.mark.e2e` class marker
  - [ ] Add file docstring with prerequisites

- [ ] **Task 2: Implement factory/farmer test helpers** (AC: 1, 2)
  - [ ] Add helper method to create test factory via direct MongoDB insert
  - [ ] Add helper method to create test farmer via direct MongoDB insert
  - [ ] Add helper method to create test collection point via direct MongoDB insert
  - [ ] Use `E2ETestDataFactory` pattern from existing tests

- [ ] **Task 3: Implement get_factory test** (AC: 1)
  - [ ] Create factory with known ID via mongodb_direct
  - [ ] Call `plantation_mcp.call_tool("get_factory", {"factory_id": ...})`
  - [ ] Assert response contains: name, code, region, grading_model_id
  - [ ] Assert error for non-existent factory_id

- [ ] **Task 4: Implement get_farmer test** (AC: 2)
  - [ ] Create farmer with known ID
  - [ ] Call `plantation_mcp.call_tool("get_farmer", {"farmer_id": ...})`
  - [ ] Assert response contains: first_name, last_name, phone, region, collection_point_id
  - [ ] Assert error for non-existent farmer_id

- [ ] **Task 5: Implement get_farmer_summary test** (AC: 3)
  - [ ] Create farmer with performance data in mongodb
  - [ ] Call `plantation_mcp.call_tool("get_farmer_performance", {"farmer_id": ...})`
  - [ ] Assert response contains performance metrics structure
  - [ ] Note: Uses `get_farmer_performance` tool name per mcp_clients.py

- [ ] **Task 6: Implement get_collection_points test** (AC: 4)
  - [ ] Create factory with 2+ collection points
  - [ ] Call `plantation_mcp.call_tool("get_collection_points", {"factory_id": ...})`
  - [ ] Assert all CPs returned with correct details

- [ ] **Task 7: Implement get_farmers_by_collection_point test** (AC: 5)
  - [ ] Create collection point with 3+ farmers
  - [ ] Call MCP tool to get farmers by CP
  - [ ] Assert all farmers returned

- [ ] **Task 8: Implement region tests** (AC: 6, 7)
  - [ ] Test get_region with seed region_id (e.g., "kericho-high")
  - [ ] Assert returns full region with geography, flush_calendar
  - [ ] Test list_regions with county="Kericho" filter
  - [ ] Test list_regions with altitude_band="high" filter
  - [ ] Assert correct regions returned

- [ ] **Task 9: Implement get_current_flush test** (AC: 8)
  - [ ] Call with region_id that has flush calendar
  - [ ] Assert returns current flush period based on today's date
  - [ ] Verify days_remaining calculation is reasonable

- [ ] **Task 10: Implement get_region_weather test** (AC: 9)
  - [ ] Seed weather data for region (or verify weather ingestion)
  - [ ] Call `get_region_weather` with days=7
  - [ ] Assert returns weather observations array
  - [ ] Note: May require weather data to be seeded first (dependency)

- [ ] **Task 11: Test cleanup and validation** (AC: All)
  - [ ] Run all 9 tests locally
  - [ ] Verify tests pass with `pytest tests/e2e/scenarios/test_01_plantation_mcp_contracts.py -v`
  - [ ] Verify no lint errors with `ruff check tests/e2e/`
  - [ ] Push and verify CI passes

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

### File List
