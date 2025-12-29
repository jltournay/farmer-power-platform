# Story 0.4.3: Collection MCP Tool Contract Tests

**Status:** in-progress
**GitHub Issue:** [#28](https://github.com/jltournay/farmer-power-platform/issues/28)
**Epic:** [Epic 0.4: E2E Test Scenarios](../epics/epic-0-4-e2e-tests.md)

## Story

As a **developer integrating with Collection Model**,
I want all 5 Collection MCP tools validated with contract tests,
So that AI agents can reliably query collected documents.

## Acceptance Criteria

1. **AC1: get_documents** - Given documents exist in the collection database, When `get_documents` is called with source_id, farmer_id, or attribute filters, Then it returns matching documents sorted by ingested_at descending

2. **AC2: get_document_by_id** - Given a document exists with a known document_id, When `get_document_by_id` is called with include_files=true, Then it returns full document with SAS URLs for blob access

3. **AC3: get_farmer_documents** - Given a farmer has documents across multiple sources, When `get_farmer_documents` is called with farmer_id, Then it returns aggregated documents from all sources

4. **AC4: search_documents** - Given documents contain searchable content, When `search_documents` is called with a query string, Then it returns relevance-scored results

5. **AC5: list_sources** - Given source configs are seeded, When `list_sources` is called with enabled_only=true, Then it returns enabled source configurations

## Tasks / Subtasks

- [ ] **Task 1: Create test file scaffold** (AC: All)
  - [ ] Create `tests/e2e/scenarios/test_02_collection_mcp_contracts.py`
  - [ ] Import fixtures: `collection_mcp`, `mongodb_direct`, `seed_data`
  - [ ] Add `@pytest.mark.e2e` class marker
  - [ ] Add file docstring with prerequisites

- [ ] **Task 2: Create document seed data** (AC: 1, 2, 3, 4)
  - [ ] Create `tests/e2e/infrastructure/seed/documents.json` with test documents
  - [ ] Documents linked to existing farmers (FRM-E2E-001 to FRM-E2E-004)
  - [ ] Documents from multiple sources (e2e-qc-analyzer-json, e2e-manual-upload)
  - [ ] Update conftest.py to seed documents
  - [ ] Update mongodb_direct.py with seed_documents method

- [ ] **Task 3: Implement get_documents test** (AC: 1)
  - [ ] Test filtering by source_id
  - [ ] Test filtering by farmer_id
  - [ ] Test filtering by attributes
  - [ ] Verify results sorted by ingested_at descending

- [ ] **Task 4: Implement get_document_by_id test** (AC: 2)
  - [ ] Test retrieval with known document_id
  - [ ] Test with include_files=true for SAS URLs
  - [ ] Test error for non-existent document_id

- [ ] **Task 5: Implement get_farmer_documents test** (AC: 3)
  - [ ] Test with farmer having multiple documents
  - [ ] Test filtering by source_ids
  - [ ] Verify aggregation across sources

- [ ] **Task 6: Implement search_documents test** (AC: 4)
  - [ ] Test full-text search with query string
  - [ ] Verify relevance scoring in results

- [ ] **Task 7: Implement list_sources test** (AC: 5)
  - [ ] Test with enabled_only=true
  - [ ] Test with enabled_only=false
  - [ ] Verify source configs returned

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
| - | - | - | - |

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

- **MCP Tools are gRPC-based**: Use `CollectionMCPClient` from `tests/e2e/helpers/mcp_clients.py`
- **Tool Invocation Pattern**: `await collection_mcp.call_tool("tool_name", {args})`
- **Response Format**: Returns dict from protobuf MessageToDict
- **Error Handling**: gRPC exceptions for failures

### Critical Implementation Details

1. **DO NOT use HTTP API for data operations** - Collection Model HTTP only exposes `/health` and `/ready`
2. **All data queries via MCP gRPC client** - `collection_mcp` fixture provides `CollectionMCPClient`
3. **Test data setup via mongodb_direct** - Bypass API for test data creation
4. **Seed data already loaded** - `seed_data` fixture loads source_configs from JSON files

### Collection MCP Tools (from definitions.py)

```python
# Available tools:
get_documents        # Query with source_id, farmer_id, linkage, attributes, date_range filters
get_document_by_id   # Get single document, optional include_files for SAS URLs
get_farmer_documents # Get all documents for a farmer
search_documents     # Full-text search with query string
list_sources         # List source configurations
```

### Test File Location

`tests/e2e/scenarios/test_02_collection_mcp_contracts.py`

### Fixtures Available

| Fixture | Description |
|---------|-------------|
| `collection_mcp` | gRPC MCP client for Collection Model |
| `mongodb_direct` | Direct MongoDB access for data setup/verification |
| `seed_data` | Pre-loaded test data (source_configs, documents) |
| `wait_for_services` | Auto-invoked, ensures services healthy |

### Project Structure Notes

- Test file: `tests/e2e/scenarios/test_02_collection_mcp_contracts.py`
- Fixtures in: `tests/e2e/conftest.py`
- MCP clients in: `tests/e2e/helpers/mcp_clients.py`
- Seed data in: `tests/e2e/infrastructure/seed/`

### Seed Data Reference

All seed data files are located in `tests/e2e/infrastructure/seed/`:

| File | Contents | Key IDs |
|------|----------|---------|
| `source_configs.json` | 2 sources | `e2e-qc-analyzer-json`, `e2e-manual-upload` |
| `documents.json` | 6 documents | `DOC-E2E-001` to `DOC-E2E-006` |
| `farmers.json` | 4 farmers | `FRM-E2E-001` to `FRM-E2E-004` |

**Test Data Relationships:**
```
e2e-qc-analyzer-json (source)
├── DOC-E2E-001 (FRM-E2E-001, quality result)
├── DOC-E2E-002 (FRM-E2E-001, quality result)
└── DOC-E2E-003 (FRM-E2E-002, quality result)

e2e-manual-upload (source)
├── DOC-E2E-004 (FRM-E2E-001, manual upload)
├── DOC-E2E-005 (FRM-E2E-003, manual upload)
└── DOC-E2E-006 (FRM-E2E-004, manual upload)
```

### References

- [Source: `_bmad-output/epics/epic-0-4-e2e-tests.md` - Story 0.4.3 acceptance criteria]
- [Source: `tests/e2e/README.md` - E2E infrastructure documentation]
- [Source: `tests/e2e/helpers/mcp_clients.py` - MCP client implementation]
- [Source: `tests/e2e/conftest.py` - Fixture definitions]
- [Source: `mcp-servers/collection-mcp/src/collection_mcp/tools/definitions.py` - Tool definitions]

### Previous Story Learnings (0.4.2)

Story 0.4.2 Plantation MCP Contracts (13 tests) established:
- MCP tool contract test pattern
- Seed data fixture usage
- String-based defensive assertions
- Pattern: class-based test organization with `@pytest.mark.e2e`

### CI Validation Requirements

Before marking story done:
1. Run locally: `PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_02_collection_mcp_contracts.py -v`
2. Run lint: `ruff check tests/e2e/scenarios/test_02_collection_mcp_contracts.py`
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
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_02_collection_mcp_contracts.py -v

# Cleanup
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

**Created:**

**Modified:**

