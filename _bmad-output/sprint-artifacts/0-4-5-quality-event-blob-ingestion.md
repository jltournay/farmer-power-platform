# Story 0.4.5: Quality Event Blob Ingestion (No AI)

**Status:** ready-for-dev
**GitHub Issue:** [#30](https://github.com/jltournay/farmer-power-platform/issues/30)
**Epic:** [Epic 0.4: E2E Test Scenarios](../epics/epic-0-4-e2e-tests.md)

## Story

As a **data engineer**,
I want quality event ingestion via blob trigger validated,
So that QC analyzer results are stored without AI extraction overhead.

## Acceptance Criteria

1. **AC1: Blob Upload** - Given source config `e2e-qc-direct-json` exists with `ai_agent_id: null`, When I upload a JSON blob to `quality-events-e2e` container, Then the blob is stored in Azurite successfully

2. **AC2: Blob Event Trigger** - Given a blob exists in the landing container, When I trigger the blob event via `POST /events/blob`, Then the Collection Model accepts the event and queues processing

3. **AC3: Document Creation** - Given the blob event is processed, When I wait for async processing (3s), Then a document is created in MongoDB with correct `farmer_id` linkage

4. **AC4: MCP Query Verification** - Given the document is created, When I query via `get_documents(farmer_id="WM-E2E-001")`, Then the document is returned with extracted attributes

5. **AC5: DAPR Event Published** - Given the document is processed successfully, When I check DAPR pubsub, Then event `collection.quality_result.received` is published

6. **AC6: Duplicate Detection** - Given a duplicate blob is uploaded (same content hash), When the blob event is triggered, Then the duplicate is detected and skipped (no new document)

## Tasks / Subtasks

- [ ] **Task 1: Verify/Create source config** (AC: 1)
  - [ ] Check `seed/source_configs.json` for `e2e-qc-direct-json`
  - [ ] Verify `processor_type: json-extraction` and `ai_agent_id: null`
  - [ ] Add source config if missing

- [ ] **Task 2: Create test file scaffold** (AC: All)
  - [ ] Create `tests/e2e/scenarios/test_04_quality_blob_ingestion.py`
  - [ ] Import fixtures: `collection_mcp`, `azurite_client`, `collection_api`, `seed_data`
  - [ ] Add `@pytest.mark.e2e` class marker
  - [ ] Add file docstring with prerequisites

- [ ] **Task 3: Implement blob upload test** (AC: 1)
  - [ ] Use `azurite_client.upload_json()` to upload QC event JSON
  - [ ] Verify blob exists in `quality-events-e2e` container
  - [ ] Test blob content is retrievable

- [ ] **Task 4: Implement blob event trigger test** (AC: 2)
  - [ ] Call Collection Model API `POST /events/blob` with event payload
  - [ ] Verify 202 Accepted response
  - [ ] Event payload should match Azure Blob Storage event schema

- [ ] **Task 5: Implement document creation test** (AC: 3, 4)
  - [ ] Wait for async processing (3s delay or polling)
  - [ ] Query via `collection_mcp.call_tool("get_documents", {"farmer_id": "..."})`
  - [ ] Verify document has correct `farmer_id` linkage
  - [ ] Verify extracted attributes from JSON

- [ ] **Task 6: Implement DAPR event verification test** (AC: 5)
  - [ ] Query MongoDB `dapr_events` collection or use DAPR pubsub verification
  - [ ] Verify `collection.quality_result.received` event was published
  - [ ] Verify event payload contains document_id

- [ ] **Task 7: Implement duplicate detection test** (AC: 6)
  - [ ] Upload same blob again (same content hash)
  - [ ] Trigger blob event
  - [ ] Verify no new document created (count unchanged)
  - [ ] Verify appropriate skip response

- [ ] **Task 8: Test cleanup and validation** (AC: All)
  - [ ] Verify no lint errors with `ruff check tests/e2e/`
  - [ ] Run all tests locally (requires Docker infrastructure)
  - [ ] Push and verify CI passes

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

- **Blob ingestion via Event Grid trigger** - Collection Model exposes `POST /events/blob` endpoint
- **JSON extraction without AI** - `processor_type: json-extraction` bypasses AI agent
- **Query verification via MCP gRPC** - Read operations via `collection_mcp` fixture
- **Duplicate detection via content hash** - SHA-256 hash of blob content

### Critical Implementation Details

1. **Use Azurite for blob storage** - Local emulator, not real Azure
2. **Source config must exist** - `e2e-qc-direct-json` in seed/source_configs.json
3. **Async processing** - Need to wait/poll after blob event trigger
4. **Farmer must exist** - Quality events reference existing farmer IDs

### Test Flow Diagram

```
1. Upload JSON blob to Azurite (quality-events-e2e container)
   └─► 2. Trigger blob event via POST /events/blob
       └─► 3. Collection Model processes (json-extraction)
           └─► 4. Document created in MongoDB
               └─► 5. DAPR publishes quality_result.received
                   └─► 6. Verify via Collection MCP tools
```

### Sample Quality Event JSON

```json
{
  "event_id": "QC-E2E-001",
  "farmer_id": "WM-E2E-001",
  "collection_point_id": "CP-E2E-001",
  "timestamp": "2025-01-15T08:30:00Z",
  "leaf_analysis": {
    "leaf_type": "two_leaves_bud",
    "color_score": 85,
    "freshness_score": 90
  },
  "weight_kg": 12.5,
  "grade": "Primary"
}
```

### Blob Event Payload Format

```json
{
  "specversion": "1.0",
  "type": "Microsoft.Storage.BlobCreated",
  "source": "/subscriptions/.../resourceGroups/.../storageAccounts/...",
  "subject": "/blobServices/default/containers/quality-events-e2e/blobs/QC-E2E-001.json",
  "id": "unique-event-id",
  "time": "2025-01-15T08:30:00Z",
  "data": {
    "api": "PutBlob",
    "contentType": "application/json",
    "contentLength": 256,
    "url": "http://azurite:10000/devstoreaccount1/quality-events-e2e/QC-E2E-001.json"
  }
}
```

### Fixtures Available

| Fixture | Description |
|---------|-------------|
| `collection_api` | HTTP client for Collection Model endpoints |
| `collection_mcp` | gRPC MCP client for Collection Model (read-only) |
| `azurite_client` | Azurite blob storage client |
| `mongodb_direct` | Direct MongoDB access for verification |
| `seed_data` | Pre-loaded test data (source_configs, farmers) |
| `wait_for_services` | Auto-invoked, ensures services healthy |

### Seed Data Dependencies

This test requires seeded data:

| File | Required Data |
|------|---------------|
| `source_configs.json` | `e2e-qc-direct-json` source config |
| `farmers.json` | Farmer `WM-E2E-001` for linkage |
| `collection_points.json` | CP `CP-E2E-001` for reference |

### Test File Location

`tests/e2e/scenarios/test_04_quality_blob_ingestion.py`

### References

- [Source: `_bmad-output/epics/epic-0-4-e2e-tests.md` - Story 0.4.5 acceptance criteria]
- [Source: `tests/e2e/README.md` - E2E infrastructure documentation]
- [Source: `tests/e2e/helpers/azure_blob.py` - Azurite client implementation]
- [Source: `proto/collection/v1/collection.proto` - Document message definitions]

### CI Validation Requirements

Before marking story done:
1. Run locally: `PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_04_quality_blob_ingestion.py -v`
2. Run lint: `ruff check tests/e2e/scenarios/test_04_quality_blob_ingestion.py`
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
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_04_quality_blob_ingestion.py -v

# Cleanup
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

---

## Dev Agent Record

### Agent Model Used

TBD

### Debug Log References

TBD

### Completion Notes List

TBD

### File List

**Created:**
- TBD

**Modified:**
- TBD
