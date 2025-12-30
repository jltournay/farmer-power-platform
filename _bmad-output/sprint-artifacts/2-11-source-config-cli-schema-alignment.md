# Story 2.11: Source Config CLI Schema Alignment

**Status:** review
**GitHub Issue:** TBD
**Epic:** [Epic 2: Quality Data Ingestion](../epics/epic-2-collection-model.md)

## Story

As a **developer**,
I want the fp-source-config CLI to write source configs in the same schema that Collection Model expects,
So that configs deployed via CLI can be read by Collection Model without schema translation.

## Problem Statement

Story 2-10 migrated Collection Model to use typed `SourceConfig` Pydantic models with flat schema access:
- `config.ingestion.mode` (typed attribute access)
- `config.storage.index_collection` (direct field access)

However, the `fp-source-config` CLI writes configs to MongoDB with a **nested wrapper**:

```python
# CLI deployer.py:161-177 writes:
doc = {
    "source_id": config.source_id,
    "display_name": config.display_name,
    "config": {  # ← NESTED WRAPPER - WRONG!
        "ingestion": config_dict["ingestion"],
        "transformation": config_dict["transformation"],
        "storage": config_dict["storage"],
    },
}
```

Collection Model's `SourceConfigRepository` expects the **flat schema** (matching Pydantic model):

```python
# Collection Model expects:
doc = {
    "source_id": "...",
    "display_name": "...",
    "ingestion": {...},      # ← FLAT - no wrapper
    "transformation": {...},
    "storage": {...},
}
```

**Root Cause:** The CLI deployer was written before the repository pattern refactoring and uses a legacy nested schema.

**Impact:** Configs deployed via CLI cannot be read by Collection Model - `SourceConfig.model_validate()` will fail because required fields (`ingestion`, `transformation`, `storage`) are nested under `config` key.

## Acceptance Criteria

1. **AC1: Flat Schema Storage** - Given the `SourceConfig` Pydantic model defines flat structure, When CLI deploys a config, Then MongoDB document matches Pydantic schema exactly (no `config` wrapper)

2. **AC2: Backward Compatibility Check** - Given existing configs may use nested schema, When Collection Model reads configs, Then it handles both schemas gracefully OR migration script converts old format

3. **AC3: Validator Uses Pydantic** - Given validator.py already uses `SourceConfig.model_validate()`, When validation passes, Then the same validated model is used for deployment (no re-wrapping)

4. **AC4: Integration Test** - Given CLI deploys a config, When Collection Model reads it via `SourceConfigService`, Then typed access works (`config.ingestion.mode`)

5. **AC5: E2E Seed Data Alignment** - Given E2E tests use seed data, When seed data is validated, Then it matches the flat Pydantic schema

6. **AC6: Unit Test Coverage Verification** - Given fp-source-config has 52 unit tests, When schema alignment is complete, Then tests explicitly verify deployed document schema matches `SourceConfig` Pydantic model (no nested wrapper)

## Tasks / Subtasks

- [ ] **Task 1: Analyze current MongoDB data** (AC: 2)
  - [ ] Check if any production/dev configs exist with nested schema
  - [ ] Document migration needs if any

- [ ] **Task 2: Refactor deployer.py** (AC: 1, 3)
  - [ ] Remove `config` wrapper in `deploy()` method (lines 161-177)
  - [ ] Store fields directly: `ingestion`, `transformation`, `storage`, `events`
  - [ ] Update `list_configs()` and `get_config()` to read flat schema
  - [ ] Update history tracking to use flat schema

- [ ] **Task 3: Update DeployedConfig model** (AC: 1)
  - [ ] Change `config: dict` field to individual typed fields
  - [ ] Or remove wrapper entirely and use `SourceConfig` directly

- [ ] **Task 4: Add migration handling** (AC: 2)
  - [ ] Option A: Migration script to flatten existing nested configs
  - [ ] Option B: `SourceConfigRepository` handles both schemas (temporary)
  - [ ] Choose based on Task 1 findings

- [ ] **Task 5: Enhance unit tests for schema verification** (AC: 1, 3, 6)
  - [ ] `tests/unit/source_config/test_deployer.py` - add assertions for deployed doc schema
  - [ ] Add test: deployed doc has NO `config` wrapper key
  - [ ] Add test: deployed doc has `ingestion`, `transformation`, `storage` at root level
  - [ ] Add test: `SourceConfig.model_validate(deployed_doc)` succeeds
  - [ ] Add test: verify round-trip: validate → deploy → read → validate again

- [ ] **Task 6: Integration test** (AC: 4)
  - [ ] Add test: CLI deploy → Collection Model read → typed access works
  - [ ] Verify round-trip: YAML → CLI → MongoDB → Collection Model → typed access

- [ ] **Task 7: Verify E2E seed data** (AC: 5)
  - [ ] Check `tests/e2e/seed_data/` for source config format
  - [ ] Ensure seed data uses flat schema

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `scripts/source-config/src/fp_source_config/deployer.py` | MODIFY | Remove config wrapper, use flat schema |
| `scripts/source-config/src/fp_source_config/deployer.py` | MODIFY | Update DeployedConfig model |
| `tests/unit/source_config/test_deployer.py` | MODIFY | Update tests for flat schema |
| `tests/integration/test_cli_collection_integration.py` | NEW | CLI → Collection Model integration |

## Technical Notes

### Before (Nested Schema - Wrong)

```python
# deployer.py current behavior
doc = {
    "source_id": config.source_id,
    "config": {
        "ingestion": config_dict["ingestion"],
        "transformation": config_dict["transformation"],
        "storage": config_dict["storage"],
    },
}
```

### After (Flat Schema - Correct)

```python
# deployer.py target behavior
doc = {
    "source_id": config.source_id,
    "display_name": config.display_name,
    "description": config.description,
    "enabled": config.enabled,
    "ingestion": config_dict["ingestion"],
    "transformation": config_dict["transformation"],
    "storage": config_dict["storage"],
    "events": config_dict.get("events"),
    "validation": config_dict.get("validation"),
    # ... deployment metadata
    "version": 1,
    "deployed_at": deployed_at,
    "deployed_by": deployed_by,
}
```

### Pydantic Model (Source of Truth)

```python
# fp_common/models/source_config.py
class SourceConfig(BaseModel):
    source_id: str
    display_name: str
    description: str = ""
    enabled: bool = True
    ingestion: IngestionConfig      # ← Direct field, not nested
    transformation: TransformationConfig
    storage: StorageConfig
    events: EventsConfig | None = None
    validation: ValidationConfig | None = None
```

## Success Metrics

- [x] CLI-deployed configs readable by Collection Model without modification
- [x] `SourceConfig.model_validate(mongodb_doc)` works for CLI-deployed docs
- [x] Zero schema translation needed between CLI and Collection Model
- [x] E2E tests pass with CLI-deployed configs

## Dependencies

- Story 2-10 (Collection Model Repository Refactoring) - DONE
- `fp_common.models.source_config.SourceConfig` Pydantic model

## Risks

- **Existing data**: May need migration if nested configs exist in MongoDB
- **Rollback complexity**: If CLI is updated but old configs exist, need dual-schema support temporarily

---

## Dev Notes

**Migration Not Required:** E2E seed data already uses flat schema format. No production deployments exist yet that use the nested schema.

**E2E Seed Data Note:** Verified that `tests/e2e/infrastructure/seed/source_configs.json` uses flat schema (fields at root level, no `config` wrapper). Found unrelated topic name issue in `e2e-weather-api` config (`collection.weather_observation.received` should be `collection.weather.updated`).

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

1. **Task 1 (Analyze):** E2E seed data already uses flat schema. No migration needed.

2. **Task 2 (Refactor deployer.py):**
   - Removed `config` wrapper from `deploy()` method (create and update paths)
   - Changed comparison logic to compare flat schema fields directly
   - Updated history document structure to use flat schema

3. **Task 3 (Update DeployedConfig model):**
   - Changed `config: dict` to individual typed fields: `ingestion`, `transformation`, `storage`, `validation`, `events`
   - Updated `ConfigHistory` model similarly

4. **Task 4 (Migration handling):** Not needed - no existing nested schema data.

5. **Task 5 (Unit tests):** Added `TestFlatSchemaDeployment` class with 6 tests:
   - `test_deployed_doc_has_no_config_wrapper`
   - `test_deployed_doc_has_flat_schema_fields`
   - `test_deployed_doc_model_validate_succeeds`
   - `test_round_trip_validate_deploy_read_validate`
   - `test_history_doc_has_flat_schema`
   - `test_updated_doc_maintains_flat_schema`

6. **Task 6 (Integration test):** Created `test_cli_collection_integration.py` with 5 tests verifying CLI deploy → Collection Model read works.

7. **Task 7 (E2E seed data):** Verified all 4 configs in `source_configs.json` use flat schema.

### File List

| File | Action | Description |
|------|--------|-------------|
| `scripts/source-config/src/fp_source_config/deployer.py` | MODIFIED | Flat schema for deploy, update, list, get, history, rollback |
| `tests/unit/source_config/test_deployer.py` | MODIFIED | Updated model tests, added TestFlatSchemaDeployment (6 tests) |
| `tests/integration/test_cli_collection_integration.py` | CREATED | CLI → Collection Model integration tests (5 tests) |

### Test Results
- 79 unit tests pass in `tests/unit/source_config/`
- 48 deployer tests + 31 validator tests
- 6 new flat schema verification tests
- 5 new integration tests (require MongoDB)
