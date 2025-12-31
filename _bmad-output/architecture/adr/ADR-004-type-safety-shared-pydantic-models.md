# ADR-004: Type Safety Architecture - Shared Pydantic Models in MCP Servers

**Status:** Accepted
**Date:** 2025-12-31
**Deciders:** Winston (Architect), John (PM), Amelia (Dev), Jeanlouistournay
**Related Stories:** Epic 0-4 (Grading Validation)

## Context

During E2E testing of Epic 0-4 (Grading Validation), we discovered extensive use of `dict[str, Any]` in MCP servers instead of typed Pydantic models. Investigation revealed:

- **47 instances** of `dict[str, Any]` in MCP servers
- All public methods in `plantation_client.py` return `dict[str, Any]`
- All public methods in `document_client.py` return `dict[str, Any]`
- `source_config_client.py` returns `dict[str, Any]` despite `SourceConfig` Pydantic model existing in `fp-common`

This creates a **type erasure boundary**:

```
Proto (typed) → PlantationClient._to_dict() → dict[str, Any] → MCP Response
MongoDB → DocumentClient → dict[str, Any] → MCP Response
SourceConfig (Pydantic) → SourceConfigClient → dict[str, Any]  ← TYPE LOST!
```

## Decision

**Share common Pydantic models via `fp-common` and replace ALL `dict[str, Any]` return types in MCP servers with typed Pydantic models.**

## Alternatives Considered

| Option | Description | Verdict |
|--------|-------------|---------|
| Keep `dict[str, Any]` | Continue current pattern | Rejected: Type safety lost |
| Re-export models | Copy models to MCP | Rejected: Duplication |
| **Move to fp-common** | Single source of truth | **Selected** |

## Consequences

### Positive

- **IDE autocomplete** for LLM agents consuming MCP tools
- **Validation at MCP boundaries** catches errors before they propagate
- **Single source of truth** for data schemas across services
- **Reduced runtime bugs** from missing/wrong fields
- **Better documentation** through Pydantic model docstrings

### Negative

- **Additional dependencies** - MCP servers depend on `fp-common` models
- **Migration effort** - Refactor all `_to_dict()` methods and return types
- **Potential circular imports** - Need careful import structure

### Neutral

- `dict[str, Any]` remains acceptable for:
  - MongoDB query building (internal to repository layer)
  - Dynamic extracted fields (LLM output with variable schema)
  - Proto → dict conversion (internal transformation before Pydantic validation)

## Implementation Plan

### Phase 1: Create New Models in fp-common

Create in `libs/fp-common/fp_common/models/`:

| File                | Models                                                                                  |
|---------------------|-----------------------------------------------------------------------------------------|
| `document.py`       | `RawDocumentRef`, `ExtractionMetadata`, `IngestionMetadata`, `Document`, `SearchResult` |
| `source_summary.py` | `SourceSummary`                                                                         |
| `flush.py`          | `Flush`                                                                                 |

### Phase 2: MOVE Plantation Models to fp-common

**IMPORTANT:** Models are MOVED to fp-common, not copied or re-exported.

**From:** `services/plantation-model/src/plantation_model/domain/models/`
**To:** `libs/fp-common/fp_common/models/`

Models to move:
- `farmer.py` → `fp_common/models/farmer.py`
- `factory.py` → `fp_common/models/factory.py`
- `region.py` → `fp_common/models/region.py`
- `collection_point.py` → `fp_common/models/collection_point.py`
- `grading_model.py` → `fp_common/models/grading_model.py`
- `farmer_performance.py` → `fp_common/models/farmer_performance.py`
- `weather.py` → `fp_common/models/weather.py`
- All related enums and value objects

**plantation-model service then imports from fp-common:**
```python
# In plantation_model/domain/models/__init__.py
from fp_common.models import (
    Farmer, Factory, Region, CollectionPoint,
    GradingModel, FarmerPerformance,
    RegionalWeather, WeatherObservation,
    # ... all models now from fp-common
)
```

### Phase 3: Update MCP Servers

**plantation-mcp** - Update 10 methods:
- `get_farmer()` → returns `Farmer`
- `get_farmer_summary()` → returns `FarmerSummary`
- `get_factory()` → returns `Factory`
- `get_collection_points()` → returns `list[CollectionPoint]`
- `get_farmers_by_collection_point()` → returns `list[Farmer]`
- `get_region()` → returns `Region`
- `list_regions()` → returns `list[Region]`
- `get_current_flush()` → returns `Flush`
- `get_region_weather()` → returns `RegionalWeather`

**collection-mcp** - Update 5 methods:
- `get_documents()` → returns `list[Document]`
- `get_document_by_id()` → returns `Document`
- `get_farmer_documents()` → returns `list[Document]`
- `search_documents()` → returns `list[SearchResult]`
- `list_sources()` → returns `list[SourceSummary]`

## Revisit Triggers

Re-evaluate this decision if:

1. **Circular imports become unmanageable** - May need separate model packages
2. **Performance issues** - Pydantic validation overhead too high for specific use cases
3. **Schema divergence needed** - Different services need incompatible schema versions

## References

- Epic 0-4: Grading Validation
- Investigation: Party Mode session 2024-12-31
- Impacts: Epic 0-5+ (all future MCP work builds on this foundation)
