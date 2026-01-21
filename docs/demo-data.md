# Demo Data Tooling Guide

This guide documents the demo data tooling for the Farmer Power Platform. These tools enable developers to quickly set up demo environments, generate test data, and validate custom seed files.

**ADR Reference:** [ADR-020: Demo Data Strategy](../_bmad-output/architecture/adr/ADR-020-demo-data-loader-pydantic-validation.md)

---

## Overview

The demo data tooling consists of two main scripts:

1. **Seed Data Loader** (`scripts/demo/load_demo_data.py`) - Validates and loads seed data to MongoDB
2. **Data Generator** (`scripts/demo/generate_demo_data.py`) - Generates demo data based on profile configurations

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DEMO DATA TOOLING                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐        ┌─────────────────┐                        │
│  │  E2E Seed Data  │        │  Profile YAML   │                        │
│  │  (JSON files)   │        │  (minimal.yaml  │                        │
│  │                 │        │   demo.yaml)    │                        │
│  └────────┬────────┘        └────────┬────────┘                        │
│           │                          │                                  │
│           ▼                          ▼                                  │
│  ┌─────────────────┐        ┌─────────────────┐                        │
│  │   Loader CLI    │        │  Generator CLI  │                        │
│  │ load_demo_data  │        │generate_demo_data│                       │
│  └────────┬────────┘        └────────┬────────┘                        │
│           │                          │                                  │
│           ▼                          ▼                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    VALIDATION LAYER                              │   │
│  │  ┌─────────────────┐    ┌─────────────────┐                     │   │
│  │  │ Pydantic Models │    │   FK Registry   │                     │   │
│  │  │ (extra=forbid)  │    │ (ID tracking)   │                     │   │
│  │  └─────────────────┘    └─────────────────┘                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                       MONGODB                                    │   │
│  │  ┌────────────────┐ ┌─────────────┐ ┌────────────────┐          │   │
│  │  │ plantation_e2e │ │collection_e2e│ │  ai_model_e2e  │          │   │
│  │  └────────────────┘ └─────────────┘ └────────────────┘          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Starting the Infrastructure

The demo data tools require MongoDB to be running. Use the E2E infrastructure scripts:

```bash
# Start the full stack (MongoDB + all services)
bash scripts/e2e-up.sh

# Or start with fresh image rebuild
bash scripts/e2e-up.sh --build

# When done, stop the infrastructure
bash scripts/e2e-up.sh --down
```

### Verify Infrastructure is Running

```bash
# Check all containers are running
docker ps

# Or run the preflight check
bash scripts/e2e-preflight.sh
```

---

## Quick Start

### Complete Setup (End-to-End)

```bash
# 1. Start the infrastructure (MongoDB + services)
bash scripts/e2e-up.sh

# 2. Load seed data into MongoDB (--clear wipes existing data first)
python scripts/demo/load_demo_data.py --source e2e --clear

# 3. (Optional) Generate additional demo data
python scripts/demo/generate_demo_data.py --profile demo --seed 12345 --load

# 4. Your demo environment is ready!
# Access services at their usual ports (check docker ps)

# 5. When done, stop everything
bash scripts/e2e-up.sh --down
```

> **Note:** Use `--clear` to ensure a clean database state. Without it, the loader uses upsert which keeps existing records.

### Common Commands

```bash
# Load E2E seed data (requires MongoDB running)
python scripts/demo/load_demo_data.py --source e2e

# Generate demo data (50 farmers with quality history)
python scripts/demo/generate_demo_data.py --profile demo --seed 12345 --load

# Validate data without loading (no MongoDB needed)
python scripts/demo/load_demo_data.py --source e2e --dry-run
```

### Environment Setup

Before running the scripts, ensure PYTHONPATH includes the required paths:

```bash
export PYTHONPATH="${PYTHONPATH}:.:libs/fp-common:libs/fp-proto/src"
```

For MongoDB loading, set the connection string:

```bash
export MONGODB_CONNECTION_STRING="mongodb://localhost:27017"
# OR use individual variables:
export MONGODB_HOST="localhost"
export MONGODB_PORT="27017"
```

---

## Tool 1: Seed Data Loader

The loader script (`scripts/demo/load_demo_data.py`) validates and loads JSON seed data into MongoDB.

### Basic Usage

```bash
# Load E2E seed data (default source)
python scripts/demo/load_demo_data.py --source e2e

# Load from custom directory
python scripts/demo/load_demo_data.py --source custom --path ./my-data/

# Dry-run (validation only, no database writes)
python scripts/demo/load_demo_data.py --source e2e --dry-run

# Clear databases before loading
python scripts/demo/load_demo_data.py --source e2e --clear

# Custom MongoDB URI
python scripts/demo/load_demo_data.py --source e2e --mongodb-uri mongodb://user:pass@host:27017
```

### Command Line Options

| Flag | Description | Default |
|------|-------------|---------|
| `--source` | Data source: `e2e` or `custom` | `e2e` |
| `--path` | Path to custom seed directory (required if `--source custom`) | - |
| `--dry-run` | Validate without loading to database | `false` |
| `--clear` | Clear databases before loading | `false` |
| `--mongodb-uri` | MongoDB connection string | `mongodb://localhost:27017` |

### How It Works

The loader runs four phases in sequence:

#### Phase 1: Pydantic Schema Validation

Each JSON record is validated against its corresponding Pydantic model:

- Models are imported from `fp_common.models` and service packages
- Unknown fields are **rejected** (models use `extra="forbid"`)
- Type mismatches, missing required fields, and constraint violations are caught
- All errors collected before proceeding (not fail-fast)

#### Phase 2: Foreign Key Validation

After schema validation, FK relationships are verified:

- A registry tracks valid IDs for each entity type
- FKs are validated against registered IDs
- Missing or invalid FK references produce errors
- Validation follows dependency order (regions before factories, etc.)

#### Phase 3: MongoDB Upsert

If validation passes, data is loaded in dependency order:

- Uses upsert pattern (safe for re-runs)
- Level 0 entities first (no dependencies)
- Then Level 1, Level 2, etc.
- Each file loaded to its designated collection/database

#### Phase 4: Verification

Post-load verification confirms record counts match expected:

- Queries each collection for actual count
- Compares to expected count from validation phase
- Reports mismatches if any

### Seed File Structure

Seed files are JSON arrays with one file per entity type:

```
tests/e2e/infrastructure/seed/
├── regions.json
├── factories.json
├── collection_points.json
├── farmers.json
├── farmer_performance.json
├── weather_observations.json
├── grading_models.json
├── source_configs.json
├── agent_configs.json
├── prompts.json
└── documents.json
```

#### File Naming Convention

- **Format:** `{entity_type}.json` (plural, snake_case)
- **Examples:** `farmers.json`, `collection_points.json`, `weather_observations.json`

#### JSON Structure

Each file contains an array of records:

```json
[
  {
    "id": "FRM-001",
    "name": "John Kamau",
    "region_id": "REG-001",
    ...
  },
  {
    "id": "FRM-002",
    "name": "Jane Wanjiku",
    "region_id": "REG-002",
    ...
  }
]
```

### Pydantic Model Locations

Models are imported from these packages:

| Entity | Package | Model Class |
|--------|---------|-------------|
| `farmers.json` | `fp_common.models.farmer` | `Farmer` |
| `regions.json` | `fp_common.models.region` | `Region` |
| `factories.json` | `fp_common.models.factory` | `Factory` |
| `collection_points.json` | `fp_common.models.collection_point` | `CollectionPoint` |
| `grading_models.json` | `fp_common.models.grading_model` | `GradingModel` |
| `farmer_performance.json` | `fp_common.models.farmer_performance` | `FarmerPerformance` |
| `weather_observations.json` | `fp_common.models.regional_weather` | `RegionalWeather` |
| `source_configs.json` | `fp_common.models.source_config` | `SourceConfig` |
| `documents.json` | `fp_common.models.document` | `Document` |
| `prompts.json` | `ai_model.domain.prompt` | `Prompt` |
| `agent_configs.json` | `ai_model.domain.agent_config` | `AgentConfig` |

### FK Dependency Order

Data must be loaded in order respecting foreign key relationships:

```
Level 0: grading_models, regions, agent_configs, prompts, source_configs
         (No FK dependencies - independent entities)

Level 1: factories
         FK: region_id → regions

Level 2: collection_points
         FK: factory_id → factories
         FK: region_id → regions

Level 3: farmers
         FK: region_id → regions

Level 4: farmer_performance, weather_observations
         FK: farmer_id → farmers (for performance)
         FK: region_id → regions (for weather)

Level 5: documents
         FK: ingestion.source_id → source_configs
```

---

## Tool 2: Data Generator

The generator script (`scripts/demo/generate_demo_data.py`) creates demo data based on profile configurations.

### Basic Usage

```bash
# Generate with demo profile
python scripts/demo/generate_demo_data.py --profile demo

# Deterministic generation (same seed = same data)
python scripts/demo/generate_demo_data.py --profile demo --seed 12345

# Generate and load to MongoDB in one step
python scripts/demo/generate_demo_data.py --profile demo --seed 12345 --load

# List available profiles
python scripts/demo/generate_demo_data.py --list-profiles

# Custom output directory
python scripts/demo/generate_demo_data.py --profile demo --output ./my-data

# Dry-run (show what would be generated)
python scripts/demo/generate_demo_data.py --profile demo --dry-run
```

### Command Line Options

| Flag | Description | Default |
|------|-------------|---------|
| `--profile` | Profile name: `minimal`, `demo`, `demo-large` | `demo` |
| `--seed` | Random seed for deterministic generation | None (random) |
| `--output` | Output directory for generated files | `tests/demo/generated/{profile}` |
| `--load` | Load generated data to MongoDB after generation | `false` |
| `--mongodb-uri` | MongoDB URI (for `--load`) | `mongodb://localhost:27017` |
| `--list-profiles` | List available profiles and exit | - |
| `--dry-run` | Show what would be generated without writing | `false` |
| `-v, --verbose` | Verbose output | `false` |

### Available Profiles

| Profile | Farmers | Factories | CPs | Documents | Use Case |
|---------|---------|-----------|-----|-----------|----------|
| `minimal` | 3 | 1 | 2 | 15 | Quick testing |
| `demo` | 50 | 3 | 10 | 500 | UI development, demos |
| `demo-large` | 250 | 10 | 40 | 3000 | Performance testing |

### Profile YAML Structure

Profiles are defined in `tests/demo/profiles/`:

```yaml
# Profile metadata
profile: demo
description: Standard demo dataset for UI testing

# Reference data (loaded from E2E seed, not generated)
reference_data:
  source: e2e_seed
  entities:
    - grading_models
    - regions
    - agent_configs
    - prompts
    - source_configs

# Generated data configuration
generated_data:
  factories:
    count: 3
    distribution:
      by_region: proportional

  collection_points:
    count: 10
    per_factory: ~3

  farmers:
    count: 50
    id_prefix: "FRM-DEMO-"
    distribution:
      by_region: proportional
      farm_scale:
        smallholder: 60
        medium: 35
        estate: 5
      notification_channel:
        sms: 70
        whatsapp: 30
      pref_lang:
        sw: 50
        en: 30
        ki: 15
        luo: 5

    # Scenario assignments
    scenarios:
      consistently_poor: 3
      improving_trend: 5
      top_performer: 5
      declining_trend: 3
      inactive: 2

  farmer_performance:
    generate_for: all_farmers
    historical_days: 90

  weather_observations:
    generate_for: all_regions
    date_range: last_90_days

  quality_documents:
    count: 500
    distribution:
      per_farmer: 5-15
      date_range: last_90_days
```

### Scenario Definitions

Scenarios create recognizable quality patterns for UI demonstrations:

| Scenario | Description | Quality Pattern | UI Badge |
|----------|-------------|-----------------|----------|
| `top_performer` | Model farmers with excellent quality | Tier 1 consistently | WIN |
| `improving_trend` | Success stories showing improvement | Tier 3 → Tier 1 over time | Improving ↑ |
| `declining_trend` | At-risk farmers needing attention | Tier 1 → Tier 3 decline | WATCH |
| `consistently_poor` | Farmers needing intervention | Tier 3/reject pattern | ACTION |
| `inactive` | No recent deliveries | No data | Inactive |

### Creating Custom Profiles

1. Copy an existing profile YAML:
   ```bash
   cp tests/demo/profiles/demo.yaml tests/demo/profiles/custom.yaml
   ```

2. Modify the configuration:
   - Adjust `count` values for each entity
   - Change `distribution` percentages
   - Add/modify scenarios
   - Change `id_prefix` for unique farmer IDs

3. Use your custom profile:
   ```bash
   python scripts/demo/generate_demo_data.py --profile custom
   ```

### Extending Polyfactory Factories

The generator uses [Polyfactory](https://polyfactory.litestar.dev/) for data generation. Factory classes are in `tests/demo/generators/`:

```
tests/demo/generators/
├── __init__.py
├── base.py              # FKRegistryMixin, BaseModelFactory
├── kenya_providers.py   # Kenya-specific data (names, phones)
├── orchestrator.py      # Main orchestrator
├── plantation.py        # Factory, CollectionPoint, Farmer factories
├── profile_loader.py    # Profile YAML loading
├── quality.py           # Document, FarmerPerformance factories
├── random_utils.py      # Seeded random utilities
├── scenarios.py         # QualityTier, FarmerScenario definitions
└── weather.py           # Weather observation factories
```

To add a new factory:

1. Create a factory class inheriting from `BaseModelFactory`:
   ```python
   from generators.base import BaseModelFactory, FKRegistryMixin
   from fp_common.models.your_model import YourModel

   class YourModelFactory(FKRegistryMixin, BaseModelFactory[YourModel]):
       __model__ = YourModel

       @classmethod
       def build(cls, **kwargs) -> YourModel:
           # Custom generation logic
           return super().build(**kwargs)
   ```

2. Register the factory in `__init__.py`

3. Add orchestration logic in `orchestrator.py`

---

## Troubleshooting

### Pydantic Validation Errors

Error messages include filename, record index, and field path:

```
farmers.json[2].contact.phone: Field required
farmers.json[5].region_id: Invalid FK 'REG-999' - not found in regions
```

**Common issues:**

| Error | Cause | Solution |
|-------|-------|----------|
| `Field required` | Missing required field | Add the field to JSON |
| `Extra field not permitted` | Unknown field in JSON | Remove field or update model |
| `Value must be an integer` | Type mismatch | Fix value type in JSON |
| `Invalid FK 'X' - not found in Y` | FK references non-existent ID | Add referenced entity first |

### FK Validation Errors

FK errors occur when referenced entities don't exist:

```
factories[0].region_id: Invalid FK 'REG-999' - not found in regions
```

**Solutions:**

1. Ensure reference data exists (regions, grading_models, etc.)
2. Check spelling/case of FK values
3. Verify load order respects dependencies
4. For generated data, use `--load` to include E2E reference data

### MongoDB Connection Issues

If loading fails:

1. Check MongoDB is running: `mongosh --eval "db.runCommand({ping:1})"`
2. Verify connection string format: `mongodb://[user:pass@]host:port`
3. Check network access if using remote MongoDB

### Dependencies Not Installed

```
ModuleNotFoundError: No module named 'polyfactory'
```

Install required packages:

```bash
pip install polyfactory faker
```

---

## Reference Links

- [ADR-020: Demo Data Strategy](../_bmad-output/architecture/adr/ADR-020-demo-data-loader-pydantic-validation.md)
- [Story 0.8.1: Pydantic Validation Infrastructure](../_bmad-output/sprint-artifacts/0-8-1-pydantic-validation-infrastructure.md)
- [Story 0.8.2: Seed Data Loader Script](../_bmad-output/sprint-artifacts/0-8-2-seed-data-loader-script.md)
- [Story 0.8.3: Polyfactory Generator Framework](../_bmad-output/sprint-artifacts/0-8-3-polyfactory-generator-framework.md)
- [Story 0.8.4: Profile-Based Data Generation](../_bmad-output/sprint-artifacts/0-8-4-profile-based-data-generation.md)
- [Project Context](../_bmad-output/project-context.md) - Pydantic patterns
