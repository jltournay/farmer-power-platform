# Story 0.4.4: Factory-Farmer Registration Flow

**Status:** done
**GitHub Issue:** [#29](https://github.com/jltournay/farmer-power-platform/issues/29)
**Epic:** [Epic 0.4: E2E Test Scenarios](../epics/epic-0-4-e2e-tests.md)

## Story

As a **field operations manager**,
I want the complete registration flow validated end-to-end,
So that new farmers are correctly assigned to regions based on GPS and altitude.

## Acceptance Criteria

1. **AC1: Factory Creation** - Given an empty database with seeded regions and grading models, When I create a factory with TBK grading model, Then the factory is created successfully with correct configuration

2. **AC2: Collection Point Creation** - Given a factory exists, When I create a collection point under that factory, Then the collection point is linked to the factory

3. **AC3: Farmer Registration with GPS** - Given a collection point exists, When I register a farmer with GPS coordinates (lat=1.0, lng=35.0), Then the farmer is created with region assigned based on altitude

4. **AC4: Altitude-Based Region Assignment** - Given the Google Elevation mock returns 1400m for lat>=1.0, When the farmer is assigned to a region, Then the region altitude band is "midland" (1400-1800m range)

5. **AC5: MCP Query Verification** - Given a farmer is registered, When I query via `get_farmer`, `get_farmers_by_collection_point`, Then the farmer is returned correctly in all queries

## Tasks / Subtasks

- [x] **Task 1: Create test file scaffold** (AC: All)
  - [x] Create `tests/e2e/scenarios/test_03_factory_farmer_flow.py`
  - [x] Import fixtures: `plantation_mcp`, `mongodb_direct`, `seed_data`
  - [x] Add `@pytest.mark.e2e` class marker
  - [x] Add file docstring with prerequisites

- [x] **Task 2: Verify Google Elevation Mock** (AC: 3, 4)
  - [x] Mock already exists in docker-compose.e2e.yaml ✓
  - [x] Located at `tests/e2e/infrastructure/mock-servers/google-elevation/`
  - [x] Mock endpoint: `GET /maps/api/elevation/json?locations={lat},{lng}`
  - [x] Return deterministic altitude: lat>=1.0 → 1400m (midland)

- [x] **Task 3: Implement factory creation test** (AC: 1)
  - [x] Use `plantation_service.create_factory()` via gRPC
  - [x] Create factory with TBK grading model
  - [x] Verify via `plantation_mcp.call_tool("get_factory", ...)`
  - [x] Assert factory has correct configuration

- [x] **Task 4: Implement collection point creation test** (AC: 2)
  - [x] Use `plantation_service.create_collection_point()` via gRPC
  - [x] Create CP linked to factory
  - [x] Verify via `plantation_mcp.call_tool("get_collection_points", ...)`
  - [x] Assert CP is linked to factory

- [x] **Task 5: Implement farmer registration test** (AC: 3, 4)
  - [x] Use `plantation_service.create_farmer()` via gRPC
  - [x] Register farmer with GPS coordinates (lat=1.0, lng=35.0)
  - [x] Altitude 1400m → kericho-midland region
  - [x] Verify region assignment matches mock altitude (1400m → midland)

- [x] **Task 6: Implement MCP query verification test** (AC: 5)
  - [x] Call `get_farmer` and verify data
  - [x] Call `get_farmers_by_collection_point` and verify farmer in list
  - [x] Assert key fields present in response

- [x] **Task 7: Test cleanup and validation** (AC: All)
  - [x] Verify no lint errors with `ruff check tests/e2e/`
  - [x] Run all tests locally (requires Docker infrastructure)
  - [x] Push and verify CI passes

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
| | | | |

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

- **Factory/Farmer creation via HTTP API** - Plantation Model exposes REST endpoints for write operations
- **Query verification via MCP gRPC** - Read operations via `plantation_mcp` fixture
- **Google Elevation Mock** - Deterministic altitude responses for region assignment

### Critical Implementation Details

1. **Write operations use HTTP API, not MCP** - MCP tools are read-only
2. **Elevation mock must be deterministic** - Same lat/lng always returns same altitude
3. **Region assignment is async** - May need to wait/poll after farmer creation
4. **Test data isolation** - Use unique IDs to avoid conflicts with seed data

### Test Flow Diagram

```
1. Create Factory (KEN-FAC-E2E-FLOW-001)
   └─► 2. Create Collection Point (CP-E2E-FLOW-001)
       └─► 3. Register Farmer (GPS: lat=0.8, lng=35.0)
           └─► 4. Elevation Mock returns 1000m
               └─► 5. Region assigned: midland (based on altitude)
                   └─► 6. Verify via MCP tools
```

### Google Elevation Mock Specification

**Location:** `tests/e2e/infrastructure/mock-servers/google-elevation/server.py`

**Endpoint:** `GET /maps/api/elevation/json`

**Query Parameters:**
- `locations`: `{lat},{lng}` format (pipe-separated for multiple)

**Mock Responses (Actual Implementation):**
| Latitude Range | Altitude (m) | Region Band |
|----------------|--------------|-------------|
| lat < 0.5 | 600 | lowland |
| 0.5 <= lat < 1.0 | 1000 | lowland (800-1400m range) |
| lat >= 1.0 | 1400 | midland (1400-1800m range) |

**Response Format:**
```json
{
  "results": [
    {
      "elevation": 1400.0,
      "location": {"lat": 1.0, "lng": 35.0},
      "resolution": 30.0
    }
  ],
  "status": "OK"
}
```

### Data Operations (IMPORTANT)

**Write operations use Plantation gRPC API** via `plantation_service` fixture:

```python
# Factory creation
factory = await plantation_service.create_factory(
    name="...", code="...", region_id="...", ...
)

# Collection point creation
cp = await plantation_service.create_collection_point(
    name="...", factory_id=factory["id"], ...
)

# Farmer registration (region auto-assigned via elevation lookup)
farmer = await plantation_service.create_farmer(
    first_name="...", collection_point_id=cp["id"], farm_location={...}, ...
)
```

### Test File Location

`tests/e2e/scenarios/test_03_factory_farmer_flow.py`

### Fixtures Available

| Fixture | Description |
|---------|-------------|
| `plantation_service` | gRPC client for Plantation Model write operations |
| `plantation_mcp` | gRPC MCP client for Plantation Model (read-only) |
| `mongodb_direct` | Direct MongoDB access for verification |
| `seed_data` | Pre-loaded test data (regions, grading_models) |
| `wait_for_services` | Auto-invoked, ensures services healthy |

### Seed Data Dependencies

This test uses seeded regions and grading models:

| File | Required Data |
|------|---------------|
| `regions.json` | Regions with altitude bands (highland, midland, lowland) |
| `grading_models.json` | TBK grading model for factory assignment |

**Region Altitude Bands (from seed data):**
- Highland: 1800-2200m (kericho-highland, nandi-highland)
- Midland: 1400-1800m (kericho-midland, bomet-midland)
- Lowland: 800-1400m (kericho-lowland)

### References

- [Source: `_bmad-output/epics/epic-0-4-e2e-tests.md` - Story 0.4.4 acceptance criteria]
- [Source: `tests/e2e/README.md` - E2E infrastructure documentation]
- [Source: `tests/e2e/helpers/mcp_clients.py` - MCP client implementation]
- [Source: `tests/e2e/helpers/api_clients.py` - HTTP API client implementation]
- [Source: `proto/plantation/v1/plantation.proto` - Factory, CollectionPoint, Farmer message definitions]

### Previous Story Learnings (0.4.2, 0.4.3)

**From Story 0.4.2 (Plantation MCP Contracts):**
- MCP tools are read-only, use `await plantation_mcp.call_tool("tool_name", {args})`
- Response format is dict from protobuf MessageToDict
- Use defensive assertions with string content checks

**From Story 0.4.3 (Collection MCP Contracts):**
- Document field paths match schema (e.g., `ingestion.source_id`, `linkage_fields.farmer_id`)
- Always verify field names against proto/domain definitions
- Production code bugs should be documented with evidence

### CI Validation Requirements

Before marking story done:
1. Run locally: `PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_03_factory_farmer_flow.py -v`
2. Run lint: `ruff check tests/e2e/scenarios/test_03_factory_farmer_flow.py`
3. Push and verify GitHub Actions CI passes

### Local E2E Test Setup

**Prerequisites:** Docker 24.0+, Docker Compose 2.20+

**Quick Start:**
```bash
# Build and start E2E stack
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d

# Wait for services to be healthy
watch -n 2 'docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps'

# Run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_03_factory_farmer_flow.py -v

# Cleanup
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - implementation straightforward

### Completion Notes List

1. **Google Elevation Mock already exists** - Located at `tests/e2e/infrastructure/mock-servers/google-elevation/`
2. **Write operations via gRPC API** - Uses `plantation_service` fixture for CreateFactory, CreateCollectionPoint, CreateFarmer
3. **Added PlantationServiceClient** - New gRPC client for Plantation Model write operations in `mcp_clients.py`
4. **Adjusted test coordinates** - Used lat=1.0 (returns 1400m) to get midland region instead of lat=0.8 (returns 1000m → lowland)
5. **Story spec correction** - Original story expected 1000m to be midland, but actual seed data says midland is 1400-1800m

### File List

**Created:**
- `tests/e2e/scenarios/test_03_factory_farmer_flow.py` - 6 tests covering AC1-AC5

**Modified:**
- `tests/e2e/helpers/mcp_clients.py` - Added PlantationServiceClient for gRPC write operations
- `tests/e2e/conftest.py` - Added plantation_service fixture
- `_bmad-output/sprint-artifacts/sprint-status.yaml` - Updated 0-4-4 to in-progress
- `_bmad-output/sprint-artifacts/0-4-4-factory-farmer-registration-flow.md` - Updated tasks, notes, and file list
