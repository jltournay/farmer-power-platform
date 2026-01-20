# ADR-020: Demo Data Strategy with Pydantic Validation

**Status:** Accepted
**Date:** 2026-01-20
**Deciders:** Winston (Architect), Murat (Test Architect), Jeanlouistournay
**Related Stories:** N/A (Infrastructure improvement)
**Problem Observed:** AI agents create invalid seed data with schema violations, FK errors, and missing fields

## Context

When attempting to populate MongoDB with demonstration data for UI testing, previous AI-generated scripts introduced multiple data integrity issues:

| Issue | Impact |
|-------|--------|
| Duplicate index keys | Service failed to start |
| Invalid foreign keys | Orphan records, broken relationships |
| Fields not in Pydantic model | Runtime crashes or silent data corruption |
| Missing mandatory Pydantic fields | ValidationError at service layer |
| Wrong enum values | Silent bad data or runtime errors |
| Wrong field types | Type coercion issues or crashes |

### Current State

The E2E test infrastructure has **validated seed data** that works correctly:

```
tests/e2e/infrastructure/seed/
├── grading_models.json      # 2 grading models
├── regions.json             # 5 regions
├── factories.json           # 2 factories
├── collection_points.json   # 3 collection points
├── farmers.json             # 4 farmers
├── farmer_performance.json  # Performance records
├── weather_observations.json
├── source_configs.json      # 5 source configs
├── documents.json           # Quality documents
├── agent_configs.json       # 2 AI agent configs
└── prompts.json             # LLM prompts
```

However, this data is loaded **only during pytest runs** via fixtures in `tests/e2e/conftest.py`. For UI development and demos, developers need persistent data in MongoDB that survives beyond test sessions.

### The Gap

```
E2E Tests:    seed JSON → pytest fixtures → MongoDB (ephemeral)
Demo/UI Dev:  ??? → ??? → MongoDB (persistent)
```

Source configs are pre-seeded via `mongo-init.js` in an init container, but all other entities have no persistent loading mechanism.

### The Coupling Problem

Simply reusing E2E seed files for demos creates a dangerous coupling:

| Concern | E2E Tests | Demo/UI |
|---------|-----------|---------|
| Data volume | Minimal (4 farmers) | Need 50+ farmers for realistic UI |
| Data stability | Must NOT change (tests assert on specific values) | May need frequent changes |
| Scenarios | Controlled, specific test cases | Need variety (poor quality, improving, top performer) |
| Edge cases | Only what tests need | Need realistic distribution |

**If we change E2E seed data for demo purposes, tests break.**
**If we limit demo to E2E data, UI testing is unrealistic.**

### The Solution: Two Complementary Tools

We need both:
1. **Seed Loader** - Load minimal E2E seed data (stable, validated)
2. **Data Generator** - Generate rich demo data using Pydantic factories (flexible, scenario-based)

Both tools share the same validation infrastructure (Pydantic models, FK checks).

## Decision

**Implement a unified demo data strategy with two complementary tools sharing the same Pydantic validation infrastructure.**

### Design Principles

1. **Pydantic models are the single source of truth** - Both tools use the same models
2. **Shared validation infrastructure** - Same FK validation logic for loader and generator
3. **E2E seed files remain stable** - Never modified for demo purposes
4. **Generator uses Pydantic factories** - `polyfactory` ensures schema compliance
5. **Profile-based configuration** - YAML profiles define scenarios and volumes
6. **FK validation in-memory** - Cross-reference entities before any database writes
7. **Fail-fast, fail-complete** - Collect ALL errors, then abort (no partial loads)
8. **Idempotent** - Safe to run multiple times via upsert pattern

### Two Tools, One Strategy

| Tool | Purpose | Data Source | When to Use |
|------|---------|-------------|-------------|
| `load-demo-data.py` | Load minimal E2E seed | `tests/e2e/infrastructure/seed/*.json` | Quick setup, E2E-compatible |
| `generate-demo-data.py` | Generate rich demo data | Pydantic factories + profile YAML | UI demos, realistic scenarios |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SHARED VALIDATION INFRASTRUCTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Pydantic Models (fp_common, ai_model)                                      │
│       ↓                                                                     │
│  FK Validation (validate_foreign_keys)                                      │
│       ↓                                                                     │
│  MongoDB Loading (MongoDBDirectClient.seed_*)                               │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TOOL 1: load-demo-data.py          TOOL 2: generate-demo-data.py           │
│  ┌─────────────────────────┐        ┌─────────────────────────┐             │
│  │ Load JSON seed files    │        │ Load profile YAML       │             │
│  │ Validate via Pydantic   │        │ Generate via polyfactory│             │
│  │ FK check                │        │ FK check (built-in)     │             │
│  │ Insert to MongoDB       │        │ Insert to MongoDB       │             │
│  └─────────────────────────┘        └─────────────────────────┘             │
│                                                                             │
│  Output: 4 farmers, 2 factories     Output: 50+ farmers, scenarios          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Architecture

### Validation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: PYDANTIC VALIDATION (NO DB WRITES)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  For each seed file in dependency order:                                    │
│    1. Load JSON from tests/e2e/infrastructure/seed/                         │
│    2. For each item: model_class.model_validate(item)                       │
│    3. Collect ALL validation errors (don't stop at first)                   │
│    4. KEEP Pydantic model instances (do NOT convert to dict yet)            │
│                                                                             │
│  If ANY Pydantic errors → STOP, print all errors, exit(1)                   │
│  If ALL valid → proceed to Phase 2 with model instances                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: FOREIGN KEY VALIDATION (NO DB WRITES)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Build reference sets from validated Pydantic models (typed attribute       │
│  access provides IDE support and catches typos at development time):        │
│    regions        = {r.region_id for r in regions}                          │
│    factories      = {f.id for f in factories}                               │
│    farmers        = {f.id for f in farmers}                                 │
│    source_configs = {s.source_id for s in source_configs}                   │
│    agent_configs  = {a.agent_id for a in agent_configs}                     │
│                                                                             │
│  Check FK constraints using typed model attributes:                         │
│    ✓ factory.region_id ∈ regions                                            │
│    ✓ farmer.region_id ∈ regions                                             │
│    ✓ cp.factory_id ∈ factories                                              │
│    ✓ cp.region_id ∈ regions                                                 │
│    ✓ cp.farmer_ids ⊆ farmers                                                │
│    ✓ perf.farmer_id ∈ farmers                                               │
│    ✓ weather.region_id ∈ regions                                            │
│    ✓ doc.ingestion.source_id ∈ source_configs                               │
│    ✓ sc.transformation.ai_agent_id ∈ agent_configs (if set)                 │
│                                                                             │
│  If ANY FK errors → STOP, print all errors, exit(1)                         │
│  If ALL valid → proceed to Phase 3                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: DATABASE LOAD                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Optional: Drop databases if --clear flag                                   │
│                                                                             │
│  For each entity type in dependency order:                                  │
│    1. Convert Pydantic models to dicts: model.model_dump(mode="json")       │
│    2. Call existing MongoDBDirectClient.seed_* method (upsert pattern)      │
│    3. Log: "✓ Loaded {entity}: {count} records"                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: POST-LOAD VERIFICATION                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Query MongoDB to verify:                                                   │
│    - Count matches expected for each collection                             │
│    - Sample records retrievable by primary key                              │
│                                                                             │
│  Print summary:                                                             │
│    ✅ plantation_e2e.farmers: 4 records                                     │
│    ✅ plantation_e2e.factories: 2 records                                   │
│    ✅ collection_e2e.source_configs: 5 records                              │
│    ...                                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Seed File → Pydantic Model Mapping

| Seed File | Pydantic Model | Import Path | Primary Key |
|-----------|----------------|-------------|-------------|
| `grading_models.json` | `GradingModel` | `fp_common.models.grading_model` | `model_id` |
| `regions.json` | `Region` | `fp_common.models.region` | `region_id` |
| `factories.json` | `Factory` | `fp_common.models.factory` | `id` |
| `collection_points.json` | `CollectionPoint` | `fp_common.models.collection_point` | `id` |
| `farmers.json` | `Farmer` | `fp_common.models.farmer` | `id` |
| `farmer_performance.json` | `FarmerPerformance` | `fp_common.models.farmer_performance` | `farmer_id` |
| `weather_observations.json` | `RegionalWeather` | `fp_common.models.regional_weather` | `region_id` |
| `source_configs.json` | `SourceConfig` | `fp_common.models.source_config` | `source_id` |
| `documents.json` | `Document` | `fp_common.models.document` | `document_id` |
| `agent_configs.json` | `AgentConfig` | `ai_model.domain.agent_config` | `id` |
| `prompts.json` | `Prompt` | `ai_model.domain.prompt` | `id` |

### Database Schema Mapping

| Database | Collection | Primary Key Field | `_id` Mapping |
|----------|------------|-------------------|---------------|
| `plantation_e2e` | `grading_models` | `model_id` | `_id` = `model_id` |
| `plantation_e2e` | `regions` | `region_id` | `_id` = `region_id` |
| `plantation_e2e` | `factories` | `id` | `_id` = `id` |
| `plantation_e2e` | `collection_points` | `id` | `_id` = `id` |
| `plantation_e2e` | `farmers` | `id` | `_id` = `id` |
| `plantation_e2e` | `farmer_performances` | `farmer_id` | `_id` = `farmer_id` |
| `plantation_e2e` | `weather_observations` | `region_id` | upsert on `region_id` |
| `collection_e2e` | `source_configs` | `source_id` | upsert on `source_id` |
| `collection_e2e` | `quality_documents` | `document_id` | upsert on `document_id` |
| `ai_model_e2e` | `agent_configs` | `id` | `_id` = `id` |
| `ai_model_e2e` | `prompts` | `id` | `_id` = `id` |

### Dependency Order (CRITICAL)

The load order respects foreign key dependencies:

```python
SEED_ORDER = [
    # Level 0 - Independent entities (no FK dependencies)
    ("grading_models.json", GradingModel, "seed_grading_models", "model_id"),
    ("regions.json", Region, "seed_regions", "region_id"),
    ("agent_configs.json", AgentConfig, "seed_agent_configs", "id"),
    ("prompts.json", Prompt, "seed_prompts", "id"),

    # Level 1 - Depends on Level 0
    ("source_configs.json", SourceConfig, "seed_source_configs", "source_id"),
    ("factories.json", Factory, "seed_factories", "id"),

    # Level 2 - Depends on Level 1
    ("collection_points.json", CollectionPoint, "seed_collection_points", "id"),

    # Level 3 - Depends on Level 0 (regions)
    ("farmers.json", Farmer, "seed_farmers", "id"),

    # Level 4 - Depends on Level 3
    ("farmer_performance.json", FarmerPerformance, "seed_farmer_performance", "farmer_id"),
    ("weather_observations.json", RegionalWeather, "seed_weather_observations", "region_id"),

    # Level 5 - Depends on Levels 1 and 3
    ("documents.json", Document, "seed_documents", "document_id"),
]
```

### FK Dependency Graph

```
LEVEL 0 (No dependencies):
├── grading_models
├── regions
├── agent_configs
└── prompts

LEVEL 1 (Depends on Level 0):
├── source_configs
│   └── FK: ai_agent_id → agent_configs.agent_id (optional)
└── factories
    └── FK: region_id → regions.region_id (REQUIRED)

LEVEL 2 (Depends on Level 1):
└── collection_points
    ├── FK: factory_id → factories.id (REQUIRED)
    ├── FK: region_id → regions.region_id (REQUIRED)
    └── farmer_ids[] → farmers.id (validated after farmers load)

LEVEL 3 (Depends on Level 0):
└── farmers
    └── FK: region_id → regions.region_id (REQUIRED)

LEVEL 4 (Depends on Level 3):
├── farmer_performance
│   └── FK: farmer_id → farmers.id (REQUIRED)
└── weather_observations
    └── FK: region_id → regions.region_id (REQUIRED)

LEVEL 5 (Depends on Levels 1, 3):
└── documents
    ├── FK: ingestion.source_id → source_configs.source_id (REQUIRED)
    └── linkage_fields.farmer_id → farmers.id (optional)
```

## Implementation

### Files to Create

**Part 1: Seed Loader**

| File | Purpose |
|------|---------|
| `scripts/load-demo-data.py` | Load E2E seed with Pydantic validation |
| `scripts/demo-up.sh` | Shell wrapper with environment setup |

**Part 2: Data Generator**

| File | Purpose |
|------|---------|
| `scripts/generate-demo-data.py` | Main generator script |
| `tests/demo/generators/__init__.py` | Package init |
| `tests/demo/generators/base.py` | FKRegistry + BaseGenerator |
| `tests/demo/generators/region_generator.py` | Region generation |
| `tests/demo/generators/factory_generator.py` | Factory + CollectionPoint generation |
| `tests/demo/generators/farmer_generator.py` | Farmer generation with scenarios |
| `tests/demo/generators/quality_generator.py` | Quality document generation |
| `tests/demo/generators/scenarios.py` | Pre-defined farmer scenarios |
| `tests/demo/profiles/minimal.yaml` | Minimal profile (4 farmers) |
| `tests/demo/profiles/demo.yaml` | Standard demo profile (50 farmers) |
| `tests/demo/profiles/demo-large.yaml` | Large demo profile (200 farmers) |

### Script Pseudocode

```python
#!/usr/bin/env python3
"""
Demo Data Loader for Farmer Power Platform.

Loads validated seed data into MongoDB for UI development and demonstrations.
Uses same seed files as E2E tests with mandatory Pydantic validation.

Usage:
    python scripts/load-demo-data.py [--clear] [--validate-only] [--mongodb-uri URI]

Options:
    --clear          Drop databases before loading (destructive!)
    --validate-only  Run validation without loading to database
    --mongodb-uri    Override MongoDB connection string
"""

import asyncio
import json
import sys
from pathlib import Path
from pydantic import ValidationError

# MUST import from existing infrastructure - DO NOT recreate
sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.e2e.helpers.mongodb_direct import MongoDBDirectClient

# Pydantic models - fp_common
from fp_common.models.grading_model import GradingModel
from fp_common.models.region import Region
from fp_common.models.factory import Factory
from fp_common.models.collection_point import CollectionPoint
from fp_common.models.farmer import Farmer
from fp_common.models.farmer_performance import FarmerPerformance
from fp_common.models.regional_weather import RegionalWeather
from fp_common.models.source_config import SourceConfig
from fp_common.models.document import Document

# Pydantic models - ai_model (service-specific)
from ai_model.domain.agent_config import AgentConfig
from ai_model.domain.prompt import Prompt


SEED_DIR = Path(__file__).parent.parent / "tests/e2e/infrastructure/seed"

# (filename, pydantic_model, seed_method, primary_key)
SEED_ORDER = [
    ("grading_models.json", GradingModel, "seed_grading_models", "model_id"),
    ("regions.json", Region, "seed_regions", "region_id"),
    ("agent_configs.json", AgentConfig, "seed_agent_configs", "id"),
    ("prompts.json", Prompt, "seed_prompts", "id"),
    ("source_configs.json", SourceConfig, "seed_source_configs", "source_id"),
    ("factories.json", Factory, "seed_factories", "id"),
    ("collection_points.json", CollectionPoint, "seed_collection_points", "id"),
    ("farmers.json", Farmer, "seed_farmers", "id"),
    ("farmer_performance.json", FarmerPerformance, "seed_farmer_performance", "farmer_id"),
    ("weather_observations.json", RegionalWeather, "seed_weather_observations", "region_id"),
    ("documents.json", Document, "seed_documents", "document_id"),
]


from pydantic import BaseModel
from typing import TypeVar

T = TypeVar("T", bound=BaseModel)


def validate_with_pydantic(
    filepath: Path,
    model_class: type[T],
    primary_key: str,
) -> tuple[list[T], list[str]]:
    """
    Load JSON and validate each item through Pydantic model.

    Returns:
        - List of validated Pydantic model instances (NOT dicts)
        - List of error messages (empty if all valid)

    Note: Models are kept as instances for type-safe FK validation in Phase 2.
          Conversion to dict happens only in Phase 3 when inserting to MongoDB.
    """
    with open(filepath) as f:
        raw_data = json.load(f)

    validated: list[T] = []
    errors: list[str] = []

    for idx, item in enumerate(raw_data):
        item_id = item.get(primary_key, f"index-{idx}")
        try:
            model_instance = model_class.model_validate(item)
            validated.append(model_instance)  # Keep model instance, NOT dict
        except ValidationError as e:
            for err in e.errors():
                field_path = " -> ".join(str(loc) for loc in err["loc"])
                errors.append(
                    f"  [{item_id}] {field_path}: {err['msg']} "
                    f"(got: {err.get('input', 'N/A')!r})"
                )

    return validated, errors


def validate_foreign_keys(validated_models: dict[str, list[BaseModel]]) -> list[str]:
    """
    Validate foreign key relationships across all entities.

    Args:
        validated_models: Dict mapping entity name to list of Pydantic model instances
                         (using typed attributes, not dict access)

    Returns:
        List of FK violation error messages
    """
    errors = []

    # Build reference sets using typed attribute access
    regions = {r.region_id for r in validated_models.get("regions", [])}
    factories = {f.id for f in validated_models.get("factories", [])}
    farmers = {f.id for f in validated_models.get("farmers", [])}
    source_configs = {s.source_id for s in validated_models.get("source_configs", [])}
    agent_configs = {a.agent_id for a in validated_models.get("agent_configs", [])}

    # Check factories.region_id (typed attribute access)
    for factory in validated_models.get("factories", []):
        if factory.region_id not in regions:
            errors.append(f"Factory {factory.id}: invalid region_id '{factory.region_id}'")

    # Check farmers.region_id
    for farmer in validated_models.get("farmers", []):
        if farmer.region_id not in regions:
            errors.append(f"Farmer {farmer.id}: invalid region_id '{farmer.region_id}'")

    # Check collection_points FKs
    for cp in validated_models.get("collection_points", []):
        if cp.factory_id not in factories:
            errors.append(f"CollectionPoint {cp.id}: invalid factory_id '{cp.factory_id}'")
        if cp.region_id not in regions:
            errors.append(f"CollectionPoint {cp.id}: invalid region_id '{cp.region_id}'")
        for fid in cp.farmer_ids or []:
            if fid not in farmers:
                errors.append(f"CollectionPoint {cp.id}: invalid farmer_id '{fid}' in farmer_ids")

    # Check farmer_performance.farmer_id
    for perf in validated_models.get("farmer_performance", []):
        if perf.farmer_id not in farmers:
            errors.append(f"FarmerPerformance: invalid farmer_id '{perf.farmer_id}'")

    # Check weather_observations.region_id
    for weather in validated_models.get("weather_observations", []):
        if weather.region_id not in regions:
            errors.append(f"WeatherObservation: invalid region_id '{weather.region_id}'")

    # Check documents.ingestion.source_id
    for doc in validated_models.get("documents", []):
        source_id = doc.ingestion.source_id if doc.ingestion else None
        if source_id and source_id not in source_configs:
            errors.append(f"Document {doc.document_id}: invalid source_id '{source_id}'")

    # Check source_configs.ai_agent_id (optional field)
    for sc in validated_models.get("source_configs", []):
        ai_agent_id = sc.transformation.ai_agent_id if sc.transformation else None
        if ai_agent_id and ai_agent_id not in agent_configs:
            errors.append(f"SourceConfig {sc.source_id}: invalid ai_agent_id '{ai_agent_id}'")

    return errors


async def load_demo_data(
    mongodb_uri: str,
    clear_first: bool = False,
    validate_only: bool = False,
) -> bool:
    """Main entry point for demo data loading."""

    print("=" * 60)
    print("PHASE 1: PYDANTIC VALIDATION")
    print("=" * 60)

    # Store Pydantic model instances (NOT dicts) for type-safe FK validation
    all_validated: dict[str, list[BaseModel]] = {}
    all_pydantic_errors: list[str] = []

    for filename, model_class, seed_method, pk in SEED_ORDER:
        filepath = SEED_DIR / filename
        if not filepath.exists():
            print(f"  SKIP {filename} (not found)")
            continue

        validated, errors = validate_with_pydantic(filepath, model_class, pk)
        entity_name = filename.replace(".json", "")
        all_validated[entity_name] = validated  # Store model instances

        if errors:
            print(f"  FAIL {filename}")
            all_pydantic_errors.extend([f"{filename}:"] + errors)
        else:
            print(f"  OK   {filename} ({len(validated)} records)")

    if all_pydantic_errors:
        print("\n" + "=" * 60)
        print("PYDANTIC VALIDATION FAILED")
        print("=" * 60)
        for err in all_pydantic_errors:
            print(err)
        return False

    print("\n" + "=" * 60)
    print("PHASE 2: FOREIGN KEY VALIDATION")
    print("=" * 60)

    # FK validation uses typed model attributes (IDE support, typo detection)
    fk_errors = validate_foreign_keys(all_validated)

    if fk_errors:
        print("FOREIGN KEY VALIDATION FAILED:")
        for err in fk_errors:
            print(f"  {err}")
        return False

    print("  All foreign key relationships valid")

    if validate_only:
        print("\n--validate-only: Skipping database load")
        return True

    print("\n" + "=" * 60)
    print("PHASE 3: DATABASE LOAD")
    print("=" * 60)

    async with MongoDBDirectClient(mongodb_uri) as client:
        if clear_first:
            print("  Clearing E2E databases...")
            await client.drop_all_e2e_databases()

        for filename, model_class, seed_method, pk in SEED_ORDER:
            entity_name = filename.replace(".json", "")
            models = all_validated.get(entity_name, [])
            if not models:
                continue

            # Convert Pydantic models to dicts ONLY at database load time
            data = [m.model_dump(mode="json") for m in models]

            method = getattr(client, seed_method)
            await method(data)
            print(f"  Loaded {entity_name}: {len(data)} records")

        print("\n" + "=" * 60)
        print("PHASE 4: VERIFICATION")
        print("=" * 60)

        # Verify counts
        checks = [
            ("plantation_e2e", "grading_models", len(all_validated.get("grading_models", []))),
            ("plantation_e2e", "regions", len(all_validated.get("regions", []))),
            ("plantation_e2e", "factories", len(all_validated.get("factories", []))),
            ("plantation_e2e", "collection_points", len(all_validated.get("collection_points", []))),
            ("plantation_e2e", "farmers", len(all_validated.get("farmers", []))),
            ("collection_e2e", "source_configs", len(all_validated.get("source_configs", []))),
            ("ai_model_e2e", "agent_configs", len(all_validated.get("agent_configs", []))),
            ("ai_model_e2e", "prompts", len(all_validated.get("prompts", []))),
        ]

        all_ok = True
        for db_name, coll_name, expected in checks:
            db = client.get_database(db_name)
            actual = await db[coll_name].count_documents({})
            if actual >= expected:
                print(f"  OK   {db_name}.{coll_name}: {actual} records")
            else:
                print(f"  FAIL {db_name}.{coll_name}: expected {expected}, got {actual}")
                all_ok = False

        return all_ok


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load demo data with Pydantic validation")
    parser.add_argument("--clear", action="store_true", help="Drop databases first")
    parser.add_argument("--validate-only", action="store_true", help="Validate without loading")
    parser.add_argument("--mongodb-uri", default="mongodb://localhost:27017", help="MongoDB URI")

    args = parser.parse_args()

    success = asyncio.run(load_demo_data(
        mongodb_uri=args.mongodb_uri,
        clear_first=args.clear,
        validate_only=args.validate_only,
    ))

    sys.exit(0 if success else 1)
```

### Shell Wrapper

```bash
#!/bin/bash
# scripts/demo-up.sh - Load demo data with environment setup

set -e

# Load .env if exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

MONGODB_URI="${MONGODB_URI:-mongodb://localhost:27017}"

echo "Demo Data Loader"
echo "MongoDB: $MONGODB_URI"
echo ""

# Set PYTHONPATH for imports
export PYTHONPATH="${PYTHONPATH}:.:libs/fp-common/src:libs/fp-proto/src:services/ai-model/src"

python scripts/load-demo-data.py --mongodb-uri "$MONGODB_URI" "$@"
```

### Example Error Output

When validation fails, the script produces clear, actionable errors:

```
============================================================
PHASE 1: PYDANTIC VALIDATION
============================================================
  OK   grading_models.json (2 records)
  OK   regions.json (5 records)
  FAIL farmers.json
  OK   factories.json (2 records)

============================================================
PYDANTIC VALIDATION FAILED
============================================================
farmers.json:
  [FRM-E2E-001] farm_location -> altitude_meters: Input should be a valid number (got: 'high')
  [FRM-E2E-002] notification_channel: Input should be 'sms' or 'whatsapp' (got: 'email')
  [FRM-E2E-003] farm_size_hectares: Input should be greater than 0.01 (got: 0)
```

---

## Part 2: Data Generator (`generate-demo-data.py`)

### Purpose

Generate rich, realistic demo data using Pydantic factories with configurable profiles. This tool creates data that:

- Is **always schema-valid** (generated from Pydantic models)
- Has **valid FK relationships** (built-in dependency tracking)
- Supports **configurable scenarios** (poor quality farmers, improving trends, etc.)
- Can generate **any volume** without touching E2E seed files

### File Structure

```
scripts/
├── load-demo-data.py              # Part 1: Load E2E seed
└── generate-demo-data.py          # Part 2: Generate rich data

tests/demo/
├── generators/
│   ├── __init__.py
│   ├── base.py                    # Base generator with FK registry
│   ├── region_generator.py
│   ├── factory_generator.py
│   ├── farmer_generator.py
│   ├── quality_generator.py
│   └── scenarios.py               # Pre-defined farmer scenarios
└── profiles/
    ├── minimal.yaml               # 4 farmers (matches E2E)
    ├── demo.yaml                  # 50 farmers, varied scenarios
    ├── demo-large.yaml            # 200 farmers, full scenarios
    └── load-test.yaml             # 1000+ farmers for stress testing
```

### Profile Configuration

```yaml
# tests/demo/profiles/demo.yaml
profile: demo
description: Standard demo dataset for UI testing and demonstrations

# Reference data - use E2E seed (stable IDs)
reference_data:
  source: e2e_seed
  entities:
    - grading_models    # Reuse TBK, KTDA grading models
    - regions           # Reuse 5 defined regions
    - agent_configs     # Reuse AI agent configs
    - prompts           # Reuse LLM prompts
    - source_configs    # Reuse ingestion configs

# Generated data
generated_data:
  factories:
    count: 5
    include_e2e: true   # Keep FAC-E2E-001, FAC-E2E-002
    generate: 3         # Add 3 more
    distribution:
      by_region: proportional

  collection_points:
    count: 15
    per_factory: 3

  farmers:
    count: 50
    id_prefix: "FRM-DEMO-"
    distribution:
      by_region: proportional
      farm_scale:
        smallholder: 60%
        medium: 35%
        estate: 5%
      notification_channel:
        sms: 70%
        whatsapp: 30%
      pref_lang:
        sw: 50%
        en: 30%
        ki: 15%
        luo: 5%

    # Named scenarios for specific demo needs
    scenarios:
      consistently_poor:
        count: 3
        description: "Farmers with consistently low quality grades"
        quality_pattern: [tier_3, tier_3, reject, tier_3, tier_3]

      improving_trend:
        count: 5
        description: "Farmers showing quality improvement over time"
        quality_pattern: [tier_3, tier_3, tier_2, tier_2, tier_1]

      top_performer:
        count: 5
        description: "Consistently high quality farmers"
        quality_pattern: [tier_1, tier_1, tier_1, tier_1, tier_1]

      declining_trend:
        count: 3
        description: "Farmers with declining quality"
        quality_pattern: [tier_1, tier_2, tier_2, tier_3, tier_3]

      inactive:
        count: 2
        description: "Inactive farmers (no recent deliveries)"
        is_active: false
        quality_pattern: []

  farmer_performance:
    generate_for: all_farmers
    historical_days: 90

  quality_documents:
    count: 500
    distribution:
      per_farmer: 5-15
      date_range: last_90_days

  weather_observations:
    generate_for: all_regions
    date_range: last_90_days
```

### Generator Architecture

```python
# tests/demo/generators/base.py

from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import TypeVar, Generic

T = TypeVar("T", bound=BaseModel)


class FKRegistry:
    """
    Tracks generated entities for FK validation.

    Ensures child entities only reference existing parent entities.
    """

    def __init__(self):
        self._registry: dict[str, set[str]] = {}

    def register(self, entity_type: str, entity_id: str) -> None:
        """Register an entity ID for FK lookups."""
        if entity_type not in self._registry:
            self._registry[entity_type] = set()
        self._registry[entity_type].add(entity_id)

    def get_valid_ids(self, entity_type: str) -> list[str]:
        """Get all valid IDs for an entity type."""
        return list(self._registry.get(entity_type, set()))

    def validate_fk(self, entity_type: str, entity_id: str) -> bool:
        """Check if an ID exists for FK validation."""
        return entity_id in self._registry.get(entity_type, set())


class BaseGenerator(ABC, Generic[T]):
    """Base class for entity generators."""

    def __init__(self, fk_registry: FKRegistry):
        self.fk_registry = fk_registry

    @abstractmethod
    def generate_one(self, **kwargs) -> T:
        """Generate a single entity."""
        pass

    def generate_batch(self, count: int, **kwargs) -> list[T]:
        """Generate multiple entities."""
        entities = []
        for i in range(count):
            entity = self.generate_one(index=i, **kwargs)
            entities.append(entity)
            self._register_entity(entity)
        return entities

    @abstractmethod
    def _register_entity(self, entity: T) -> None:
        """Register entity in FK registry."""
        pass
```

```python
# tests/demo/generators/farmer_generator.py

import random
from polyfactory.factories.pydantic_factory import ModelFactory
from fp_common.models.farmer import Farmer, FarmScale, NotificationChannel, PreferredLanguage
from .base import BaseGenerator, FKRegistry


class FarmerFactory(ModelFactory):
    """Polyfactory for Farmer model with realistic defaults."""
    __model__ = Farmer
    __faker__ = Faker("sw_KE")  # Swahili-Kenya locale for realistic names


class FarmerGenerator(BaseGenerator[Farmer]):
    """Generate farmers with configurable scenarios."""

    KENYAN_FIRST_NAMES = ["James", "Grace", "Daniel", "Sarah", "John", "Mary", ...]
    KENYAN_LAST_NAMES = ["Kiprop", "Cheruiyot", "Bett", "Kosgei", "Langat", ...]

    def __init__(self, fk_registry: FKRegistry, config: dict):
        super().__init__(fk_registry)
        self.config = config
        self.id_prefix = config.get("id_prefix", "FRM-DEMO-")
        self._counter = 0

    def generate_one(
        self,
        index: int = 0,
        scenario: str | None = None,
        **kwargs
    ) -> Farmer:
        self._counter += 1

        # Get valid region from FK registry
        valid_regions = self.fk_registry.get_valid_ids("regions")
        region_id = self._select_region(valid_regions)

        # Generate farmer with realistic distribution
        farmer = Farmer(
            id=f"{self.id_prefix}{self._counter:03d}",
            grower_number=f"GN-DEMO-{self._counter:03d}",
            first_name=random.choice(self.KENYAN_FIRST_NAMES),
            last_name=random.choice(self.KENYAN_LAST_NAMES),
            region_id=region_id,
            farm_location=self._generate_location_for_region(region_id),
            contact=self._generate_contact(),
            farm_size_hectares=self._generate_farm_size(),
            farm_scale=FarmScale.from_hectares(self._last_farm_size),
            national_id=f"{random.randint(10000000, 99999999)}",
            notification_channel=self._select_weighted("notification_channel"),
            pref_lang=self._select_weighted("pref_lang"),
            is_active=kwargs.get("is_active", True),
        )

        return farmer

    def _select_region(self, valid_regions: list[str]) -> str:
        """Select region based on distribution config."""
        # Proportional distribution across regions
        return random.choice(valid_regions)

    def _select_weighted(self, field: str) -> str:
        """Select value based on weighted distribution from config."""
        distribution = self.config.get("distribution", {}).get(field, {})
        if not distribution:
            return self._default_for_field(field)

        choices = list(distribution.keys())
        weights = [float(v.strip('%')) for v in distribution.values()]
        return random.choices(choices, weights=weights)[0]

    def _register_entity(self, entity: Farmer) -> None:
        self.fk_registry.register("farmers", entity.id)
```

```python
# tests/demo/generators/scenarios.py

"""
Pre-defined farmer scenarios for demo data.

Each scenario defines a pattern of quality results and farmer characteristics
that illustrate specific use cases for demos.
"""

from dataclasses import dataclass
from enum import Enum


class QualityTier(Enum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    REJECT = "reject"


@dataclass
class FarmerScenario:
    """Defines a farmer scenario for demo purposes."""
    name: str
    description: str
    quality_pattern: list[QualityTier]  # Recent quality results
    is_active: bool = True
    farm_scale: str | None = None       # Override if needed

    def generate_quality_history(self, days: int = 90) -> list[dict]:
        """Generate quality documents matching this scenario's pattern."""
        # Implementation generates documents following the pattern
        pass


# Pre-defined scenarios
SCENARIOS = {
    "consistently_poor": FarmerScenario(
        name="consistently_poor",
        description="Farmer struggling with quality - needs intervention",
        quality_pattern=[QualityTier.TIER_3, QualityTier.TIER_3, QualityTier.REJECT,
                        QualityTier.TIER_3, QualityTier.TIER_3],
    ),
    "improving_trend": FarmerScenario(
        name="improving_trend",
        description="Farmer showing improvement after receiving advice",
        quality_pattern=[QualityTier.TIER_3, QualityTier.TIER_3, QualityTier.TIER_2,
                        QualityTier.TIER_2, QualityTier.TIER_1],
    ),
    "top_performer": FarmerScenario(
        name="top_performer",
        description="Consistently excellent quality - model farmer",
        quality_pattern=[QualityTier.TIER_1] * 5,
    ),
    "new_farmer": FarmerScenario(
        name="new_farmer",
        description="Recently registered, minimal history",
        quality_pattern=[QualityTier.TIER_2],
    ),
}
```

### Main Generator Script

```python
#!/usr/bin/env python3
# scripts/generate-demo-data.py

"""
Demo Data Generator for Farmer Power Platform.

Generates rich, realistic demo data using Pydantic factories.
Supports configurable profiles for different demo scenarios.

Usage:
    python scripts/generate-demo-data.py --profile demo [--clear] [--include-e2e-seed]

Options:
    --profile        Profile name (minimal, demo, demo-large, load-test)
    --clear          Drop databases before generating
    --include-e2e-seed  Load E2E seed as base before generating
    --validate-only  Validate profile without generating
    --mongodb-uri    Override MongoDB connection string
"""

import asyncio
import yaml
from pathlib import Path

from tests.demo.generators.base import FKRegistry
from tests.demo.generators.region_generator import RegionGenerator
from tests.demo.generators.factory_generator import FactoryGenerator
from tests.demo.generators.farmer_generator import FarmerGenerator
from tests.demo.generators.quality_generator import QualityDocumentGenerator

PROFILES_DIR = Path(__file__).parent.parent / "tests/demo/profiles"


async def generate_demo_data(
    profile_name: str,
    mongodb_uri: str,
    clear_first: bool = False,
    include_e2e_seed: bool = False,
) -> bool:
    """Generate demo data based on profile configuration."""

    # Load profile
    profile_path = PROFILES_DIR / f"{profile_name}.yaml"
    with open(profile_path) as f:
        profile = yaml.safe_load(f)

    print(f"Profile: {profile['profile']}")
    print(f"Description: {profile['description']}")
    print("=" * 60)

    # Initialize FK registry
    fk_registry = FKRegistry()

    async with MongoDBDirectClient(mongodb_uri) as client:
        if clear_first:
            print("Clearing databases...")
            await client.drop_all_e2e_databases()

        # Phase 1: Load reference data (E2E seed or generate)
        print("\nPHASE 1: REFERENCE DATA")
        if include_e2e_seed or profile.get("reference_data", {}).get("source") == "e2e_seed":
            await load_e2e_reference_data(client, fk_registry, profile)

        # Phase 2: Generate entities in dependency order
        print("\nPHASE 2: GENERATE ENTITIES")

        gen_config = profile.get("generated_data", {})

        # Factories (depends on regions)
        if "factories" in gen_config:
            factories = await generate_factories(fk_registry, gen_config["factories"])
            await client.seed_factories([f.model_dump(mode="json") for f in factories])
            print(f"  Generated {len(factories)} factories")

        # Collection points (depends on factories, regions)
        if "collection_points" in gen_config:
            cps = await generate_collection_points(fk_registry, gen_config["collection_points"])
            await client.seed_collection_points([cp.model_dump(mode="json") for cp in cps])
            print(f"  Generated {len(cps)} collection points")

        # Farmers (depends on regions)
        if "farmers" in gen_config:
            farmers = await generate_farmers(fk_registry, gen_config["farmers"])
            await client.seed_farmers([f.model_dump(mode="json") for f in farmers])
            print(f"  Generated {len(farmers)} farmers")

        # Quality documents (depends on farmers, source_configs)
        if "quality_documents" in gen_config:
            docs = await generate_quality_documents(fk_registry, gen_config["quality_documents"])
            await client.seed_documents([d.model_dump(mode="json") for d in docs])
            print(f"  Generated {len(docs)} quality documents")

        # Farmer performance (computed from quality documents)
        if "farmer_performance" in gen_config:
            perf = await generate_farmer_performance(fk_registry, gen_config["farmer_performance"])
            await client.seed_farmer_performance([p.model_dump(mode="json") for p in perf])
            print(f"  Generated {len(perf)} farmer performance records")

        print("\n" + "=" * 60)
        print("GENERATION COMPLETE")
        print("=" * 60)

        return True


async def load_e2e_reference_data(client, fk_registry: FKRegistry, profile: dict) -> None:
    """Load E2E seed data as reference and register in FK registry."""
    from scripts.load_demo_data import SEED_DIR, validate_with_pydantic, SEED_ORDER

    ref_entities = profile.get("reference_data", {}).get("entities", [])

    for filename, model_class, seed_method, pk in SEED_ORDER:
        entity_name = filename.replace(".json", "")
        if entity_name not in ref_entities:
            continue

        filepath = SEED_DIR / filename
        if not filepath.exists():
            continue

        models, errors = validate_with_pydantic(filepath, model_class, pk)
        if errors:
            raise ValueError(f"E2E seed validation failed: {errors}")

        # Register in FK registry
        for model in models:
            pk_value = getattr(model, pk.replace("_id", "_id") if "_id" in pk else pk)
            fk_registry.register(entity_name, pk_value)

        # Load to database
        method = getattr(client, seed_method)
        await method([m.model_dump(mode="json") for m in models])
        print(f"  Loaded E2E seed: {entity_name} ({len(models)} records)")
```

### Usage Examples

```bash
# Minimal setup (same as E2E)
python scripts/load-demo-data.py

# Standard demo (50 farmers with scenarios)
python scripts/generate-demo-data.py --profile demo --include-e2e-seed

# Large demo for presentations
python scripts/generate-demo-data.py --profile demo-large --clear

# Fresh start with demo data
python scripts/generate-demo-data.py --profile demo --clear --include-e2e-seed

# Validate profile without generating
python scripts/generate-demo-data.py --profile demo --validate-only
```

## Consequences

### Positive

| Benefit | Description |
|---------|-------------|
| **Schema enforcement** | Pydantic catches missing fields, wrong types, invalid enums BEFORE insert |
| **Type-safe FK validation** | Model attributes (`factory.region_id`) provide IDE autocomplete, catch typos at dev time |
| **FK integrity** | Cross-entity validation prevents orphan records |
| **Clear error messages** | Field path + expected vs actual makes debugging trivial |
| **Decoupled E2E and demo data** | E2E seed files stay stable, demo data generated separately |
| **Configurable scenarios** | Profile YAML allows custom volumes and farmer scenarios |
| **Realistic demo data** | Generated data follows realistic distributions |
| **Reuses proven code** | Same `MongoDBDirectClient` and Pydantic models |
| **Idempotent** | Safe to run repeatedly via upsert pattern |
| **Late dict conversion** | Models stay as instances until DB insert |

### Negative

| Cost | Mitigation |
|------|------------|
| Additional PYTHONPATH setup | Shell wrapper handles this |
| Two tools to maintain | Shared validation infrastructure minimizes duplication |
| Generator complexity | Polyfactory handles most generation, scenarios are declarative |
| Profile maintenance | YAML profiles are simple and self-documenting |

### Neutral

- Demo data uses same `_e2e` databases as E2E tests
- Scripts live in `scripts/` alongside other utility scripts
- Generators live in `tests/demo/` to be close to profiles

## What The Tools Must NOT Do

### Seed Loader (`load-demo-data.py`)

| Prohibited Action | Correct Approach |
|-------------------|------------------|
| Create new seed JSON files | Use existing `tests/e2e/infrastructure/seed/*.json` |
| Modify E2E seed files for demo needs | Use generator for additional data |
| Recreate MongoDBDirectClient | Import from `tests.e2e.helpers.mongodb_direct` |
| Skip Pydantic validation | Validation is mandatory |
| Load partial data on error | Fail-complete: all or nothing |

### Data Generator (`generate-demo-data.py`)

| Prohibited Action | Correct Approach |
|-------------------|------------------|
| Generate entities without FK registry | Always register parent before child |
| Hardcode entity IDs | Use configurable prefixes from profile |
| Skip profile validation | Validate YAML before generating |
| Generate data that violates Pydantic models | Use polyfactory with model introspection |
| Mix generated IDs with E2E seed IDs | Use separate prefixes (FRM-DEMO- vs FRM-E2E-) |

## Revisit Triggers

Re-evaluate this decision if:

1. **Seed data format changes** - Update SEED_ORDER mapping in loader
2. **New entity types added** - Add to validation, FK checks, and generator
3. **Pydantic models move** - Update import paths in both tools
4. **Need separate demo databases** - Add `--database-suffix` flag
5. **New demo scenarios needed** - Add to `tests/demo/generators/scenarios.py`
6. **Profile format insufficient** - Extend YAML schema
7. **Performance issues with large generation** - Consider batch inserts, parallel generation

## References

- `tests/e2e/infrastructure/seed/` - Source seed data files (E2E, stable)
- `tests/e2e/helpers/mongodb_direct.py` - MongoDBDirectClient with seed methods
- `tests/e2e/conftest.py` - Reference implementation of fixture-based loading
- [polyfactory](https://polyfactory.litestar.dev/) - Pydantic factory library for test data generation
- ADR-004: Type Safety with Shared Pydantic Models
- ADR-015: E2E Autonomous Debugging Infrastructure
