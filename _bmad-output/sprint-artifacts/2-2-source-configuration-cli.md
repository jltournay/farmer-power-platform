# Story 2.2: Source Configuration CLI

**Status:** in-review
**GitHub Issue:** #17

---

## Story

As a **platform operator**,
I want a CLI tool to manage data source configurations,
So that new data sources can be onboarded without code changes and configurations are version-controlled in Git.

---

## Acceptance Criteria

1. **Given** the `fp-source-config` CLI is installed
   **When** I run `fp-source-config validate`
   **Then** all YAML files in `config/source-configs/` are validated against the SourceConfig schema
   **And** validation errors are printed with file names and details
   **And** exit code is 0 for valid, 1 for invalid

2. **Given** a specific source configuration file
   **When** I run `fp-source-config validate --file config/source-configs/qc-analyzer-result.yaml`
   **Then** only that file is validated
   **And** validation errors are printed with line context

3. **Given** valid source configurations exist
   **When** I run `fp-source-config deploy --env dev`
   **Then** configurations are upserted to MongoDB for the dev environment
   **And** version numbers are incremented for updated configs
   **And** a summary is printed: created, updated, unchanged counts

4. **Given** I want to preview changes before deploying
   **When** I run `fp-source-config deploy --env dev --dry-run`
   **Then** changes are shown without actually deploying
   **And** no MongoDB writes occur

5. **Given** source configurations exist in MongoDB
   **When** I run `fp-source-config list --env dev`
   **Then** all configured sources are listed with: source_id, display_name, version, deployed_at, enabled

6. **Given** local and deployed configs may differ
   **When** I run `fp-source-config diff --env dev`
   **Then** differences between local YAML and deployed MongoDB are shown
   **And** changes are highlighted per field

7. **Given** a source has multiple deployed versions
   **When** I run `fp-source-config history --env dev --source qc-analyzer-result`
   **Then** deployment history is shown: version, deployed_at, deployed_by, git_sha

8. **Given** a bad deployment needs reverting
   **When** I run `fp-source-config rollback --env prod --source qc-analyzer-result --version 2`
   **Then** confirmation is required for prod environment
   **And** the source is rolled back to the specified version

---

## Tasks / Subtasks

### Task 1: Create config directory structure with schemas and source configs (AC: #1-4)
- [x] 1.1 Create `config/schemas/` directory
- [x] 1.2 Create `config/schemas/data/` directory for data payload schemas
- [x] 1.3 Create `config/schemas/data/qc-bag-result.json` schema
- [x] 1.4 Create `config/schemas/data/qc-exceptions-manifest.json` schema
- [x] 1.5 Create `config/schemas/data/farmer-registration.json` schema
- [x] 1.6 Create `config/source-configs/` directory
- [x] 1.7 Create `qc-analyzer-result.yaml` per architecture spec
- [x] 1.8 Create `qc-analyzer-exceptions.yaml` per architecture spec
- [x] 1.9 Create `weather-api.yaml` per architecture spec
- [x] 1.10 Create `market-prices.yaml` per architecture spec

### Task 2: Define SourceConfig Pydantic models in fp-common (AC: #1, #2)
- [x] 2.1 Create `libs/fp-common/fp_common/models/source_config.py`
- [x] 2.2 Define `IngestionConfig` model with fields:
  - `mode: Literal["blob_trigger", "scheduled_pull"]`
  - `landing_container: str | None`
  - `path_pattern: PathPatternConfig | None`
  - `file_pattern: str | None`
  - `file_format: Literal["json", "zip"]`
  - `trigger_mechanism: Literal["event_grid"] | None`
  - `processed_file_config: ProcessedFileConfig | None`
  - `provider: str | None` (for scheduled_pull)
  - `schedule: str | None` (cron expression)
  - `request: RequestConfig | None`
  - `iteration: IterationConfig | None`
  - `retry: RetryConfig | None`
- [x] 2.3 Define `ValidationConfig` model: `schema_name`, `strict`
- [x] 2.4 Define `TransformationConfig` model: `agent`, `extract_fields`, `link_field`, `field_mappings`
- [x] 2.5 Define `StorageConfig` model: `raw_container`, `index_collection`, `ttl_days`
- [x] 2.6 Define root `SourceConfig` model combining all blocks
- [x] 2.7 Export from `libs/fp-common/fp_common/__init__.py`
- [x] 2.8 Add `generate_json_schema()` utility function to export JSON Schema
- [x] 2.9 Generate `config/schemas/source-config.schema.json` from Pydantic model

### Task 3: Create CLI package structure (AC: #1-8)
- [x] 3.1 Create `scripts/source-config/` directory
- [x] 3.2 Create `pyproject.toml` with hatchling build backend
- [x] 3.3 Create `src/fp_source_config/` package directory
- [x] 3.4 Create `src/fp_source_config/__init__.py`
- [x] 3.5 Create `src/fp_source_config/cli.py` with Typer app
- [x] 3.6 Create `src/fp_source_config/settings.py` for environment config
- [x] 3.7 Add `[project.scripts]` entry: `fp-source-config = "fp_source_config.cli:app"`

### Task 4: Implement validate command (AC: #1, #2)
- [x] 4.1 Create `src/fp_source_config/validator.py`
- [x] 4.2 Implement `validate_source_configs(files: list[Path])` function
- [x] 4.3 Parse YAML files using PyYAML
- [x] 4.4 Validate each entry against SourceConfig schema using Pydantic
- [x] 4.5 Return list of validation errors with file context
- [x] 4.6 Implement `validate` CLI command with `--file` option
- [x] 4.7 Print errors using Rich formatting

### Task 5: Implement deployer module (AC: #3, #4)
- [x] 5.1 Create `src/fp_source_config/deployer.py`
- [x] 5.2 Implement `SourceConfigDeployer` class with environment parameter
- [x] 5.3 Implement MongoDB connection per environment
- [x] 5.4 Implement `deploy(files, dry_run)` method with version increment
- [x] 5.5 Track deployment metadata: `deployed_at`, `deployed_by`, `git_sha`
- [x] 5.6 Return deployment results with action (create/update/unchanged)

### Task 6: Implement deploy command (AC: #3, #4)
- [x] 6.1 Add `deploy` CLI command with `--env` and `--file` options
- [x] 6.2 Add `--dry-run` flag
- [x] 6.3 Validate configs before deploying
- [x] 6.4 Call deployer and display results with Rich

### Task 7: Implement list command (AC: #5)
- [x] 7.1 Implement `list_configs()` method in deployer
- [x] 7.2 Add `list` CLI command with `--env` option
- [x] 7.3 Display as Rich table with columns: source_id, display_name, version, deployed_at, enabled

### Task 8: Implement diff command (AC: #6)
- [x] 8.1 Implement `diff(source_id?)` method in deployer
- [x] 8.2 Compare local YAML with deployed MongoDB document
- [x] 8.3 Add `diff` CLI command with `--env` and `--source` options
- [x] 8.4 Display differences with Rich formatting

### Task 9: Implement history command (AC: #7)
- [x] 9.1 Create `source_config_history` collection schema for version tracking
- [x] 9.2 Implement `get_history(source_id, limit)` method in deployer
- [x] 9.3 Add `history` CLI command with `--env`, `--source`, `--limit` options
- [x] 9.4 Display history as Rich table

### Task 10: Implement rollback command (AC: #8)
- [x] 10.1 Implement `rollback(source_id, version)` method in deployer
- [x] 10.2 Add `rollback` CLI command with `--env`, `--source`, `--version` options
- [x] 10.3 Require confirmation for prod environment
- [x] 10.4 Restore config from history and increment version

### Task 11: Write unit tests (AC: #1-8)
- [x] 11.1 Create `tests/unit/source_config/` directory with test structure
- [x] 11.2 Test validator with valid/invalid YAML files
- [x] 11.3 Test deployer with mocked MongoDB
- [x] 11.4 Test list, diff, history, rollback commands
- [x] 11.5 Test environment isolation

---

## Dev Notes

### CLI Location (per Architecture)

```
scripts/source-config/
├── pyproject.toml
├── src/
│   └── fp_source_config/
│       ├── __init__.py
│       ├── cli.py              # Typer CLI entry point
│       ├── deployer.py         # Deployment logic
│       ├── validator.py        # Pydantic validation
│       ├── models.py           # Re-export from fp-common (optional)
│       └── settings.py         # Environment settings
└── tests/
    └── test_validator.py
```

### Config Directory Structure (per Architecture)

```
config/
├── schemas/
│   ├── source-config.schema.json      # Auto-generated from Pydantic (IDE support)
│   └── data/                          # Data payload validation schemas
│       ├── qc-bag-result.json         # QC Analyzer result payload schema
│       ├── qc-exceptions-manifest.json # QC exceptions manifest schema
│       └── farmer-registration.json   # Mobile app registration schema
└── source-configs/
    ├── qc-analyzer-result.yaml
    ├── qc-analyzer-exceptions.yaml
    ├── mobile-app.yaml
    ├── weather-api.yaml
    └── market-prices.yaml
```

**Schema Types:**

| Schema | Purpose | Generated |
|--------|---------|-----------|
| `source-config.schema.json` | Validates source config YAML files (IDE autocomplete) | Auto from Pydantic |
| `data/*.json` | Validates ingested data payloads at runtime | Manual |

### SourceConfig Schema Location

The SourceConfig Pydantic models MUST be defined in `fp-common` so they can be shared:

```
libs/fp-common/fp_common/
├── __init__.py                  # Export SourceConfig
└── models/
    ├── __init__.py
    └── source_config.py         # Full hierarchical schema
```

### Technology Stack

| Component | Choice | Version |
|-----------|--------|---------|
| CLI Framework | Typer | Latest |
| YAML Parser | PyYAML | Latest |
| MongoDB Driver | Motor (async) | Latest |
| Output Formatting | Rich | Latest |
| Validation | Pydantic | 2.0+ |
| Build Backend | Hatchling | Latest |
| Language | Python | 3.12 |

### Critical Implementation Rules

**From project-context.md:**

1. **Use Pydantic 2.0 syntax** - `model_dump()` not `dict()`, `model_validate()` not `parse_obj()`
2. **Type hints required** - ALL function signatures MUST have type hints
3. **Absolute imports only** - No relative imports
4. **Use Typer for CLI** - Per architecture specification
5. **Async MongoDB operations** - Use Motor for async, wrap in `asyncio.run()` for CLI

### pyproject.toml (per Architecture)

```toml
[project]
name = "fp-source-config"
version = "0.1.0"
description = "Farmer Power Source Configuration CLI"
requires-python = ">=3.12"
dependencies = [
    "typer[all]>=0.9.0",
    "rich>=13.0.0",
    "pyyaml>=6.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "motor>=3.3.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.23.0"]

[project.scripts]
fp-source-config = "fp_source_config.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Full SourceConfig Model (per Architecture)

```python
# libs/fp-common/fp_common/models/source_config.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PathPatternConfig(BaseModel):
    """Path pattern extraction configuration."""
    pattern: str
    extract_fields: list[str]


class ProcessedFileConfig(BaseModel):
    """What to do with files after processing."""
    action: Literal["archive", "move", "delete"]
    archive_container: str | None = None
    archive_ttl_days: int | None = None
    processed_folder: str | None = None


class RequestConfig(BaseModel):
    """HTTP request configuration for scheduled pulls."""
    base_url: str
    auth_type: Literal["none", "api_key", "oauth2"]
    auth_secret_key: str | None = None
    parameters: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = 30


class IterationConfig(BaseModel):
    """Iteration configuration for scheduled pulls."""
    foreach: str
    source_mcp: str
    source_tool: str
    concurrency: int = 5


class RetryConfig(BaseModel):
    """Retry configuration."""
    max_attempts: int = 3
    backoff: Literal["exponential", "linear"] = "exponential"


class ZipConfig(BaseModel):
    """ZIP file handling configuration."""
    manifest_file: str
    images_folder: str
    extract_images: bool = True
    image_storage_container: str


class IngestionConfig(BaseModel):
    """Ingestion configuration block."""
    mode: Literal["blob_trigger", "scheduled_pull"]

    # blob_trigger fields
    landing_container: str | None = None
    path_pattern: PathPatternConfig | None = None
    file_pattern: str | None = None
    file_format: Literal["json", "zip"] | None = None
    trigger_mechanism: Literal["event_grid"] | None = None
    processed_file_config: ProcessedFileConfig | None = None
    zip_config: ZipConfig | None = None

    # scheduled_pull fields
    provider: str | None = None
    schedule: str | None = None
    request: RequestConfig | None = None
    iteration: IterationConfig | None = None
    retry: RetryConfig | None = None


class ValidationConfig(BaseModel):
    """Validation configuration block."""
    schema_name: str
    strict: bool = True


class TransformationConfig(BaseModel):
    """Transformation configuration block."""
    agent: str
    extract_fields: list[str]
    link_field: str
    field_mappings: dict[str, str] = Field(default_factory=dict)


class StorageConfig(BaseModel):
    """Storage configuration block."""
    raw_container: str
    index_collection: str
    ttl_days: int | None = None


class SourceConfig(BaseModel):
    """Complete source configuration."""

    model_config = ConfigDict(populate_by_name=True)

    source_id: str = Field(..., description="Unique identifier")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Source description")
    enabled: bool = Field(True, description="Whether source is active")

    ingestion: IngestionConfig
    validation: ValidationConfig | None = None
    transformation: TransformationConfig
    storage: StorageConfig
```

### Example: qc-analyzer-result.yaml (per Architecture)

```yaml
source_id: qc-analyzer-result
display_name: QC Analyzer - Bag Result
description: Aggregated quality grading results from Starfish QC machines

ingestion:
  mode: blob_trigger
  landing_container: qc-analyzer-landing
  path_pattern:
    pattern: "results/{plantation_id}/{crop}/{market}/{batch_id}.json"
    extract_fields: [plantation_id, crop, market, batch_id]
  file_pattern: "*.json"
  file_format: json
  trigger_mechanism: event_grid
  processed_file_config:
    action: archive
    archive_container: qc-archive
    archive_ttl_days: 365

validation:
  schema_name: data/qc-bag-result.json
  strict: true

transformation:
  agent: qc-result-extraction-agent
  extract_fields:
    - plantation_id
    - factory_id
    - collection_point_id
    - grading_model_id
    - grading_model_version
    - batch_timestamp
    - bag_summary
  link_field: plantation_id
  field_mappings:
    plantation_id: farmer_id

storage:
  raw_container: quality-results-raw
  index_collection: quality_results_index
  ttl_days: 730
```

### Data Payload Schemas

These JSON schemas validate the actual data being ingested (not the source config YAML).

**config/schemas/data/qc-bag-result.json:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://farmerpower.io/schemas/data/qc-bag-result.json",
  "title": "QC Analyzer Bag Result",
  "description": "Schema for QC Analyzer bag grading results",
  "type": "object",
  "required": ["plantation_id", "factory_id", "batch_id", "batch_timestamp", "bag_summary"],
  "properties": {
    "plantation_id": {
      "type": "string",
      "description": "Farmer/plantation identifier (maps to farmer_id)"
    },
    "factory_id": {
      "type": "string",
      "description": "Factory where grading occurred"
    },
    "collection_point_id": {
      "type": "string",
      "description": "Collection point identifier"
    },
    "grading_model_id": {
      "type": "string",
      "description": "ML model used for grading"
    },
    "grading_model_version": {
      "type": "string",
      "description": "Version of the grading model"
    },
    "batch_id": {
      "type": "string",
      "description": "Unique batch identifier"
    },
    "batch_timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "When the batch was graded"
    },
    "bag_summary": {
      "type": "object",
      "required": ["total_weight_kg", "primary_percentage", "overall_grade"],
      "properties": {
        "total_weight_kg": { "type": "number" },
        "primary_percentage": { "type": "number", "minimum": 0, "maximum": 100 },
        "secondary_percentage": { "type": "number", "minimum": 0, "maximum": 100 },
        "overall_grade": { "type": "string", "enum": ["A", "B", "C", "D", "REJECT"] },
        "leaf_type_distribution": {
          "type": "object",
          "additionalProperties": { "type": "number" }
        }
      }
    }
  }
}
```

**config/schemas/data/qc-exceptions-manifest.json:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://farmerpower.io/schemas/data/qc-exceptions-manifest.json",
  "title": "QC Analyzer Exceptions Manifest",
  "description": "Schema for ZIP manifest containing secondary leaf images",
  "type": "object",
  "required": ["plantation_id", "batch_id", "batch_result_ref", "exception_images"],
  "properties": {
    "plantation_id": { "type": "string" },
    "source_id": { "type": "string" },
    "batch_id": { "type": "string" },
    "batch_result_ref": { "type": "string" },
    "factory_id": { "type": "string" },
    "grading_model_id": { "type": "string" },
    "grading_model_version": { "type": "string" },
    "batch_timestamp": { "type": "string", "format": "date-time" },
    "exception_count": { "type": "integer", "minimum": 0 },
    "exception_images": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["file_uri", "classification"],
        "properties": {
          "file_uri": { "type": "string" },
          "mime_type": { "type": "string" },
          "classification": {
            "type": "object",
            "properties": {
              "quality_grade": { "type": "string" },
              "confidence": { "type": "number" },
              "leaf_type": { "type": "string" },
              "coarse_subtype": { "type": ["string", "null"] },
              "banji_hardness": { "type": ["number", "null"] }
            }
          }
        }
      }
    }
  }
}
```

### Generating SourceConfig JSON Schema from Pydantic

Add this utility to auto-generate the schema for IDE support:

```python
# libs/fp-common/fp_common/models/source_config.py

def generate_json_schema(output_path: str | None = None) -> dict:
    """Generate JSON Schema from SourceConfig Pydantic model.

    Args:
        output_path: If provided, write schema to this file path.

    Returns:
        The generated JSON Schema as a dict.
    """
    import json

    schema = SourceConfig.model_json_schema()
    schema["$id"] = "https://farmerpower.io/schemas/source-config.schema.json"
    schema["title"] = "Farmer Power Source Configuration"

    if output_path:
        with open(output_path, "w") as f:
            json.dump(schema, f, indent=2)

    return schema


if __name__ == "__main__":
    # CLI usage: python -m fp_common.models.source_config
    generate_json_schema("config/schemas/source-config.schema.json")
    print("Generated config/schemas/source-config.schema.json")
```

### MongoDB Document Schema (per Architecture)

```javascript
// Stored in source_configs collection
{
    "_id": "qc-analyzer-result",
    "source_id": "qc-analyzer-result",
    "display_name": "QC Analyzer - Bag Result",
    "enabled": true,
    "config": {
        "ingestion": { ... },
        "validation": { ... },
        "transformation": { ... },
        "storage": { ... }
    },
    "version": 3,
    "deployed_at": "2025-12-26T10:00:00Z",
    "deployed_by": "github-actions",
    "git_sha": "abc123"
}

// Version history in source_config_history collection
{
    "_id": ObjectId("..."),
    "source_id": "qc-analyzer-result",
    "version": 2,
    "config": { ... },
    "deployed_at": "2025-12-25T10:00:00Z",
    "deployed_by": "jeanlouistournay",
    "git_sha": "def456"
}
```

**MongoDB Indexes:**
```javascript
// source_configs
db.source_configs.createIndex({ "source_id": 1 }, { unique: true })

// source_config_history
db.source_config_history.createIndex({ "source_id": 1, "version": -1 })
```

### CLI Commands Summary (per Architecture)

```bash
# Validate all configs
fp-source-config validate

# Validate specific config
fp-source-config validate --file config/source-configs/qc-analyzer-result.yaml

# Deploy to environment
fp-source-config deploy --env dev
fp-source-config deploy --env staging
fp-source-config deploy --env prod

# Deploy specific config only
fp-source-config deploy --env dev --file qc-analyzer-result.yaml

# Dry-run deployment
fp-source-config deploy --env dev --dry-run

# List deployed configs
fp-source-config list --env dev

# Compare local vs deployed
fp-source-config diff --env dev
fp-source-config diff --env dev --source qc-analyzer-result

# View deployment history
fp-source-config history --env dev --source qc-analyzer-result --limit 10

# Rollback to previous version
fp-source-config rollback --env prod --source qc-analyzer-result --version 2
```

### Previous Story (2-1) Learnings

**Critical insights from Story 2.1 implementation:**

1. **Test fixture conflicts:** DO NOT override `mock_mongodb_client` in local `conftest.py`. Use the fixture from root `tests/conftest.py`.

2. **CI PYTHONPATH:** If adding a new service/package, update `.github/workflows/ci.yaml` to include the path in PYTHONPATH for both `unit-tests` and `integration-tests` jobs.

3. **MongoDB client pattern:** Use Motor async client with connection pooling. The CLI will need to wrap async calls with `asyncio.run()`.

### Git Intelligence Summary

Recent commits show:
- CI validation rules and new service checklist added (ee96aff)
- Conftest fixture conflict fixed (37cb939)
- Collection-model added to CI PYTHONPATH (dd3b080)
- Story 2.1 completed with code review (001a918, 326526d)

**Pattern to follow:** When creating this CLI, ensure it's added to CI PYTHONPATH if tests are run in CI.

### Integration with Collection Model Service

The CLI manages configurations that the Collection Model service reads via `SourceConfigService`:

1. **Event Grid trigger handler (Story 2.3)** will use `source_configs` to:
   - Match incoming blob events by `landing_container` and `path_pattern`
   - Check if source is `enabled` before processing
   - Get `transformation.agent` for LLM extraction

2. **Scheduled pull jobs (Stories 2.7, 2.8)** will use `source_configs` to:
   - Get schedule and request configuration
   - Check `enabled` status before running pulls

3. **SourceConfigService in runtime:**
   - 5-minute TTL cache
   - Async operations
   - Type-safe queries

### Testing Strategy

| Test Type | What to Test | Mocking Required |
|-----------|--------------|------------------|
| Unit | Validator with valid/invalid YAML | None (pure function) |
| Unit | Deployer MongoDB operations | mock_mongodb_client |
| Unit | Diff, history, rollback logic | mock_mongodb_client |
| Integration | Full CLI workflow | testcontainers |

**Test File Location:** `scripts/source-config/tests/`

### References

- [Source: _bmad-output/architecture/collection-model-architecture.md] - Full architecture specification
- [Source: _bmad-output/epics.md#story-22] - Epic story definition
- [Source: _bmad-output/project-context.md] - Coding standards and rules
- [Source: Story 2.1] - Collection Model service setup (reference for MongoDB patterns)

---

## Out of Scope

- Event Grid trigger handler implementation (Story 2.3)
- QC Analyzer JSON ingestion (Story 2.4)
- QC Analyzer ZIP ingestion (Story 2.5)
- SourceConfigService runtime implementation (part of Story 2.3)
- GitHub Actions workflow for automated deployment
- Mobile app source configuration (not in MVP)

---

## Definition of Done

- [x] `config/schemas/source-config.schema.json` auto-generated from Pydantic
- [x] `config/schemas/data/` directory with data payload JSON schemas
- [x] `config/source-configs/` directory with YAML files for all sources
- [x] SourceConfig Pydantic models defined in `fp-common` (full hierarchical schema)
- [x] `fp-source-config validate` command works with valid/invalid YAML
- [x] `fp-source-config deploy --env` command deploys to MongoDB with versioning
- [x] `fp-source-config deploy --dry-run` shows changes without deploying
- [x] `fp-source-config list --env` command displays all sources
- [x] `fp-source-config diff --env` command shows local vs deployed differences
- [x] `fp-source-config history --env --source` command shows deployment history
- [x] `fp-source-config rollback --env --source --version` command restores previous version
- [x] Unit tests passing for all commands (51 tests)
- [ ] CI passes (lint, format, tests)
- [ ] Code reviewed and merged

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Code review found 19 test failures due to fixture schema mismatch - fixed
- MockMongoCursor.sort() signature fix for Motor compatibility
- MockMongoCollection.find() changed from async to sync (Motor pattern)

### Completion Notes List

- All 8 ACs implemented and verified
- 51 unit tests passing
- Code review completed with fixes

### File List

**Created:**
- `scripts/source-config/pyproject.toml`
- `scripts/source-config/src/fp_source_config/__init__.py`
- `scripts/source-config/src/fp_source_config/cli.py`
- `scripts/source-config/src/fp_source_config/deployer.py`
- `scripts/source-config/src/fp_source_config/validator.py`
- `scripts/source-config/src/fp_source_config/settings.py`
- `libs/fp-common/fp_common/models/source_config.py`
- `config/schemas/source-config.schema.json`
- `config/schemas/data/qc-bag-result.json`
- `config/schemas/data/qc-exceptions-manifest.json`
- `config/schemas/data/farmer-registration.json`
- `config/source-configs/qc-analyzer-result.yaml`
- `config/source-configs/qc-analyzer-exceptions.yaml`
- `config/source-configs/weather-api.yaml`
- `config/source-configs/market-prices.yaml`
- `tests/unit/source_config/__init__.py`
- `tests/unit/source_config/conftest.py`
- `tests/unit/source_config/test_cli.py`
- `tests/unit/source_config/test_deployer.py`
- `tests/unit/source_config/test_validator.py`

**Modified:**
- `libs/fp-common/fp_common/__init__.py` (export SourceConfig)
- `tests/conftest.py` (fix MockMongoCursor.sort, MockMongoCollection.find)
