# Story 0.6.11: Proto-to-Pydantic Converters in fp-common

**Status:** in-progress
**GitHub Issue:** #109
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADR:** [ADR-004: Type Safety - Shared Pydantic Models](../architecture/adr/ADR-004-type-safety-shared-pydantic-models.md)
**Story Points:** 3
**Wave:** 4 (Type Safety & Service Boundaries)
**Prerequisites:**
- Story 0.6.1 (Shared Pydantic Models) - DONE - Models exist in fp-common
- Story 0.6.10 (Linkage Field Validation) - DONE

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - Centralize Proto-to-Pydantic conversion logic!**

### 1. Problem Statement

Currently, `plantation_client.py` contains ~150 lines of manual `_*_to_dict()` conversion methods:
- `_farmer_to_dict()` (lines 284-299)
- `_farmer_summary_to_dict()` (lines 301-342)
- `_factory_to_dict()` (lines 251-282)
- `_collection_point_to_dict()` (lines 344-356)
- `_region_to_dict()` (lines 537-595)

These conversion methods:
1. **Map Proto field names to dict keys** (e.g., `farmer.id` → `"farmer_id"`)
2. **Handle nested messages** (e.g., `factory.location.latitude`)
3. **Convert enums** (e.g., `FarmScale.Name(farmer.farm_scale)`)
4. **Handle optional fields** (e.g., `farmer.contact.phone if farmer.contact else ""`)

### 2. Goal

Create **reusable converter functions** in `fp_common.converters` that:
1. Take a Proto message as input
2. Return a **Pydantic model** (not dict)
3. Can be imported by any service or MCP server

### 3. Key Insight - Pydantic Models Already Exist!

Story 0.6.1 already moved models to fp-common:
- `Farmer`, `Factory`, `Region`, `CollectionPoint` in `fp_common.models`
- These match the Proto definitions closely

The converters bridge: **Proto message → Pydantic model**

### 4. Definition of Done Checklist

- [x] **Converters directory created** - `libs/fp-common/fp_common/converters/`
- [x] **Plantation converters created** - `plantation_converters.py`
- [x] **All 5+ converter functions implemented** - farmer, factory, region, collection_point, farmer_summary
- [x] **Round-trip tests pass** - proto → pydantic → model_dump() produces expected dict
- [x] **Unit tests pass** - Each converter tested with edge cases (31 tests)
- [x] **Lint passes** - ruff check and format

---

## Story

As a **developer maintaining MCP servers**,
I want Proto-to-Pydantic conversion functions centralized in fp-common,
So that field mappings are defined once and reused by both services and MCP clients.

## Acceptance Criteria

1. **AC1: Converters Directory Exists** - Given Plantation proto messages exist, When I check `libs/fp-common/fp_common/converters/`, Then I find `plantation_converters.py` with converter functions.

2. **AC2: Farmer Converter** - Given a `plantation_pb2.Farmer` proto message, When I call `farmer_from_proto(proto)`, Then I get a `Farmer` Pydantic model with all fields correctly mapped.

3. **AC3: Factory Converter** - Given a `plantation_pb2.Factory` proto message, When I call `factory_from_proto(proto)`, Then I get a `Factory` Pydantic model with `quality_thresholds` correctly populated.

4. **AC4: Region Converter** - Given a `plantation_pb2.Region` proto message, When I call `region_from_proto(proto)`, Then I get a `Region` Pydantic model with nested `geography`, `flush_calendar`, `agronomic`, and `weather_config`.

5. **AC5: CollectionPoint Converter** - Given a `plantation_pb2.CollectionPoint` proto message, When I call `collection_point_from_proto(proto)`, Then I get a `CollectionPoint` Pydantic model.

6. **AC6: FarmerSummary Converter** - Given a `plantation_pb2.FarmerSummary` proto message, When I call `farmer_summary_from_proto(proto)`, Then I get a dict (or model) with `historical` and `today` metrics correctly populated.

7. **AC7: Importable from fp_common** - Given converters are in fp-common, When MCP client imports them, Then `from fp_common.converters import farmer_from_proto` works.

## Tasks / Subtasks

- [x] **Task 1: Create Converters Directory** (AC: 1)
  - [x] Create `libs/fp-common/fp_common/converters/` directory
  - [x] Create `__init__.py` with exports
  - [x] Create `plantation_converters.py`

- [x] **Task 2: Implement farmer_from_proto** (AC: 2)
  - [x] Handle basic fields: id, first_name, last_name, phone
  - [x] Handle nested contact info
  - [x] Convert FarmScale enum to Pydantic enum
  - [x] Convert NotificationChannel, InteractionPreference, PreferredLanguage enums
  - [x] Handle region_id, collection_point_id
  - [x] Handle is_active boolean

- [x] **Task 3: Implement factory_from_proto** (AC: 3)
  - [x] Handle basic fields: id, name, code, region_id
  - [x] Handle nested location (GeoLocation)
  - [x] Handle quality_thresholds with defaults
  - [x] Handle processing_capacity_kg, is_active
  - [x] Handle payment_policy

- [x] **Task 4: Implement region_from_proto** (AC: 4)
  - [x] Handle basic fields: region_id, name, county, country
  - [x] Handle nested geography (center_gps, radius_km, altitude_band)
  - [x] Handle flush_calendar (first_flush, monsoon_flush, autumn_flush, dormant)
  - [x] Handle agronomic (soil_type, typical_diseases, harvest_peak_hours, frost_risk)
  - [x] Handle weather_config (api_location, altitude_for_api, collection_time)

- [x] **Task 5: Implement collection_point_from_proto** (AC: 5)
  - [x] Handle basic fields: id, name, factory_id, region_id
  - [x] Handle nested location
  - [x] Handle status field
  - [x] Handle operating_hours, capacity, collection_days

- [x] **Task 6: Implement farmer_summary_from_proto** (AC: 6)
  - [x] Handle basic farmer fields
  - [x] Handle optional historical metrics (HistoricalMetrics model)
  - [x] Handle optional today metrics (TodayMetrics model)
  - [x] Handle grade_counts dict conversion
  - [x] Handle attribute_counts nested dict conversion

- [x] **Task 7: Export from fp_common.converters** (AC: 7)
  - [x] Update `converters/__init__.py` with all exports
  - [x] Verify import works from external package

- [x] **Task 8: Create Unit Tests** (AC: All)
  - [x] Test each converter with sample proto data (31 tests)
  - [x] Test edge cases: empty optional fields, missing nested messages
  - [x] Test enum conversion
  - [x] Test round-trip: proto → pydantic → model_dump() matches expected dict

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.6.11: Proto-to-Pydantic Converters in fp-common"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-6-11-proto-pydantic-converters
  ```

**Branch name:** `story/0-6-11-proto-pydantic-converters`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-6-11-proto-pydantic-converters`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.6.11: Proto-to-Pydantic Converters" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-6-11-proto-pydantic-converters`

**PR URL:** _______________ (fill in when created)

---

## Implementation Reference

### File Structure

```
libs/fp-common/fp_common/converters/
├── __init__.py                    # Exports all converters
└── plantation_converters.py       # Proto → Pydantic for Plantation domain
```

### Converter Pattern

```python
# libs/fp-common/fp_common/converters/plantation_converters.py
"""Proto-to-Pydantic converters for Plantation domain.

These converters centralize the mapping from Proto messages to Pydantic models,
eliminating duplicate _to_dict() methods across services and MCP clients.
"""

from fp_proto.plantation.v1 import plantation_pb2

from fp_common.models import (
    CollectionPoint,
    Factory,
    Farmer,
    FarmScale,
    GeoLocation,
    InteractionPreference,
    NotificationChannel,
    PreferredLanguage,
    QualityThresholds,
    Region,
)
from fp_common.models.value_objects import ContactInfo


def farmer_from_proto(proto: plantation_pb2.Farmer) -> Farmer:
    """Convert Farmer proto message to Pydantic model.

    Args:
        proto: The Farmer proto message from gRPC response.

    Returns:
        Farmer Pydantic model with all fields mapped.

    Note:
        Enum values are converted from Proto enum to Pydantic enum.
        The Proto uses uppercase (FARM_SCALE_SMALLHOLDER), Pydantic uses lowercase.
    """
    # Convert Proto enum names to Pydantic enum values
    farm_scale = _proto_enum_to_pydantic(
        plantation_pb2.FarmScale.Name(proto.farm_scale),
        FarmScale,
    )
    notification_channel = _proto_enum_to_pydantic(
        plantation_pb2.NotificationChannel.Name(proto.notification_channel),
        NotificationChannel,
    )
    interaction_pref = _proto_enum_to_pydantic(
        plantation_pb2.InteractionPreference.Name(proto.interaction_pref),
        InteractionPreference,
    )
    pref_lang = _proto_enum_to_pydantic(
        plantation_pb2.PreferredLanguage.Name(proto.pref_lang),
        PreferredLanguage,
    )

    return Farmer(
        id=proto.id,
        first_name=proto.first_name,
        last_name=proto.last_name,
        region_id=proto.region_id,
        collection_point_id=proto.collection_point_id,
        contact=ContactInfo(
            phone=proto.contact.phone if proto.contact else "",
        ),
        farm_location=GeoLocation(
            latitude=proto.farm_location.latitude if proto.farm_location else 0,
            longitude=proto.farm_location.longitude if proto.farm_location else 0,
            altitude_meters=proto.farm_location.altitude_meters if proto.farm_location else 0,
        ),
        farm_size_hectares=proto.farm_size_hectares,
        farm_scale=farm_scale,
        national_id=proto.national_id or "unknown",  # Required field, fallback if empty
        is_active=proto.is_active,
        notification_channel=notification_channel,
        interaction_pref=interaction_pref,
        pref_lang=pref_lang,
    )


def factory_from_proto(proto: plantation_pb2.Factory) -> Factory:
    """Convert Factory proto message to Pydantic model.

    Args:
        proto: The Factory proto message from gRPC response.

    Returns:
        Factory Pydantic model with quality_thresholds.

    Note:
        If quality_thresholds is not set in proto, defaults are used (85/70/50).
    """
    # Handle quality thresholds with defaults
    if proto.HasField("quality_thresholds"):
        qt = QualityThresholds(
            tier_1=proto.quality_thresholds.tier_1,
            tier_2=proto.quality_thresholds.tier_2,
            tier_3=proto.quality_thresholds.tier_3,
        )
    else:
        qt = QualityThresholds()  # Uses defaults from model

    return Factory(
        id=proto.id,
        name=proto.name,
        code=proto.code,
        region_id=proto.region_id,
        location=GeoLocation(
            latitude=proto.location.latitude if proto.location else 0,
            longitude=proto.location.longitude if proto.location else 0,
            altitude_meters=proto.location.altitude_meters if proto.location else 0,
        ),
        processing_capacity_kg=proto.processing_capacity_kg,
        quality_thresholds=qt,
        is_active=proto.is_active,
    )


def collection_point_from_proto(proto: plantation_pb2.CollectionPoint) -> CollectionPoint:
    """Convert CollectionPoint proto message to Pydantic model."""
    return CollectionPoint(
        id=proto.id,
        name=proto.name,
        factory_id=proto.factory_id,
        region_id=proto.region_id,
        location=GeoLocation(
            latitude=proto.location.latitude if proto.location else 0,
            longitude=proto.location.longitude if proto.location else 0,
        ),
        status=proto.status or "active",
    )


def _proto_enum_to_pydantic(proto_name: str, pydantic_enum: type) -> Any:
    """Convert Proto enum name to Pydantic enum value.

    Proto enums use uppercase with prefix (e.g., FARM_SCALE_SMALLHOLDER).
    Pydantic enums use lowercase values (e.g., "smallholder").

    Args:
        proto_name: Proto enum name (e.g., "FARM_SCALE_SMALLHOLDER").
        pydantic_enum: Target Pydantic enum class.

    Returns:
        Matching Pydantic enum member.
    """
    # Strip common prefixes and convert to lowercase
    value = proto_name.lower()
    for prefix in ["farm_scale_", "notification_channel_", "interaction_preference_", "preferred_language_"]:
        if value.startswith(prefix):
            value = value[len(prefix):]
            break

    # Match against Pydantic enum values
    for member in pydantic_enum:
        if member.value == value:
            return member

    # Fallback to first member if no match
    return list(pydantic_enum)[0]
```

### Unit Test Structure

```python
# tests/unit/fp_common/converters/test_plantation_converters.py
import pytest

from fp_proto.plantation.v1 import plantation_pb2

from fp_common.converters import (
    farmer_from_proto,
    factory_from_proto,
    collection_point_from_proto,
)
from fp_common.models import Farmer, Factory, CollectionPoint, FarmScale


class TestFarmerFromProto:
    """Tests for farmer_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Wanjiku",
            last_name="Kamau",
            region_id="nyeri-highland",
            collection_point_id="cp-001",
            farm_size_hectares=1.5,
            farm_scale=plantation_pb2.FARM_SCALE_MEDIUM,
            is_active=True,
        )

        farmer = farmer_from_proto(proto)

        assert isinstance(farmer, Farmer)
        assert farmer.id == "WM-0001"
        assert farmer.first_name == "Wanjiku"
        assert farmer.last_name == "Kamau"
        assert farmer.region_id == "nyeri-highland"
        assert farmer.farm_scale == FarmScale.MEDIUM

    def test_enum_conversion(self):
        """Proto enums are converted to Pydantic enums."""
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            farm_scale=plantation_pb2.FARM_SCALE_SMALLHOLDER,
            notification_channel=plantation_pb2.NOTIFICATION_CHANNEL_SMS,
            interaction_pref=plantation_pb2.INTERACTION_PREFERENCE_VOICE,
            pref_lang=plantation_pb2.PREFERRED_LANGUAGE_SWAHILI,
        )

        farmer = farmer_from_proto(proto)

        assert farmer.farm_scale == FarmScale.SMALLHOLDER
        assert farmer.notification_channel.value == "sms"
        assert farmer.interaction_pref.value == "voice"
        assert farmer.pref_lang.value == "sw"

    def test_nested_contact_info(self):
        """Nested contact info is extracted."""
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
            contact=plantation_pb2.ContactInfo(phone="+254712345678"),
        )

        farmer = farmer_from_proto(proto)

        assert farmer.contact.phone == "+254712345678"

    def test_missing_optional_fields(self):
        """Missing optional fields use defaults."""
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Test",
            last_name="Farmer",
        )

        farmer = farmer_from_proto(proto)

        assert farmer.contact.phone == ""
        assert farmer.is_active is False  # Proto default


class TestFactoryFromProto:
    """Tests for factory_from_proto converter."""

    def test_quality_thresholds_present(self):
        """Quality thresholds are extracted when present."""
        proto = plantation_pb2.Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            quality_thresholds=plantation_pb2.QualityThresholds(
                tier_1=90.0,
                tier_2=75.0,
                tier_3=60.0,
            ),
        )

        factory = factory_from_proto(proto)

        assert factory.quality_thresholds.tier_1 == 90.0
        assert factory.quality_thresholds.tier_2 == 75.0
        assert factory.quality_thresholds.tier_3 == 60.0

    def test_quality_thresholds_defaults(self):
        """Quality thresholds use defaults when not set."""
        proto = plantation_pb2.Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
        )

        factory = factory_from_proto(proto)

        # Defaults from QualityThresholds model
        assert factory.quality_thresholds.tier_1 == 85.0
        assert factory.quality_thresholds.tier_2 == 70.0
        assert factory.quality_thresholds.tier_3 == 50.0


class TestRoundTrip:
    """Tests for round-trip conversion."""

    def test_farmer_round_trip(self):
        """Proto → Pydantic → dict produces expected structure."""
        proto = plantation_pb2.Farmer(
            id="WM-0001",
            first_name="Wanjiku",
            last_name="Kamau",
            region_id="nyeri-highland",
            collection_point_id="cp-001",
            farm_size_hectares=1.5,
            farm_scale=plantation_pb2.FARM_SCALE_MEDIUM,
            is_active=True,
            notification_channel=plantation_pb2.NOTIFICATION_CHANNEL_SMS,
        )

        farmer = farmer_from_proto(proto)
        data = farmer.model_dump()

        # Verify key fields in dict
        assert data["id"] == "WM-0001"
        assert data["first_name"] == "Wanjiku"
        assert data["farm_scale"] == "medium"  # Enum serialized as value
        assert data["notification_channel"] == "sms"
```

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH=".:libs/fp-common:libs/fp-proto/src" pytest tests/unit/fp_common/converters/ -v
```
**Output:**
```
======================== 31 passed, 1 warning in 0.70s =========================
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure with --build (MANDATORY)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
================== 102 passed, 1 skipped in 124.15s (0:02:04) ==================
```
**E2E passed:** [x] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/0-6-11-proto-pydantic-converters

# Wait ~30s, then check CI status
gh run list --branch feature/0-6-11-proto-pydantic-converters --limit 3
```
**CI Run ID:** 20753588242 (CI), 20753678048 (E2E)
**CI E2E Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-06

---

## E2E Story Checklist

**Read First:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Pre-Implementation
- [ ] Read and understood `E2E-TESTING-MENTAL-MODEL.md`
- [ ] Understand: Proto = source of truth, tests verify (not define) behavior

### This Story's E2E Impact

**This story has MINIMAL E2E impact:**
- No API changes (internal refactoring only)
- No behavior changes
- Existing E2E tests should pass unchanged

The converters are a **new internal module** that will be used in Story 0.6.12 to refactor MCP clients.

### Production Code Changes (if any)

| File:Lines | What Changed | Why (with evidence) | Type |
|------------|--------------|---------------------|------|
| (none - new files only) | | | |

---

## Dev Notes

### Architecture Context

**Wave 4 Overview:**
1. **Story 0.6.11 (this)** - Create converters in fp-common
2. **Story 0.6.12** - MCP clients USE converters, return Pydantic models
3. **Story 0.6.13** - Replace CollectionClient direct DB with gRPC
4. **Story 0.6.14** - Replace custom DaprPubSubClient with SDK

This story is **foundational** - it creates the converters that Story 0.6.12 will use.

### Proto Message Structure Reference

**Relevant Proto definitions at `proto/plantation/v1/plantation.proto`:**

```protobuf
message Farmer {
  string id = 1;
  string grower_number = 2;
  string first_name = 3;
  string last_name = 4;
  string region_id = 5;
  string collection_point_id = 6;
  GeoLocation farm_location = 7;
  ContactInfo contact = 8;
  double farm_size_hectares = 9;
  FarmScale farm_scale = 10;
  string national_id = 11;
  bool is_active = 12;
  NotificationChannel notification_channel = 13;
  InteractionPreference interaction_pref = 14;
  PreferredLanguage pref_lang = 15;
}
```

### Existing _to_dict() Methods to Replace

**In `plantation_client.py`:**
- `_farmer_to_dict()` - 16 lines
- `_farmer_summary_to_dict()` - 42 lines
- `_factory_to_dict()` - 32 lines
- `_collection_point_to_dict()` - 13 lines
- `_region_to_dict()` - 59 lines

Total: ~162 lines that will be consolidated into converters.

### Testing Approach

1. **Unit tests** verify converter logic with mock Proto messages
2. **No E2E tests needed** - converters are internal, no API changes
3. **Story 0.6.12** will validate converters work correctly in MCP context

### Learnings from Previous Stories

**From Story 0.6.10:**
- Metrics instrumentation pattern works well
- Unit tests should cover edge cases thoroughly
- E2E tests with valid seed data should pass unchanged

**From Story 0.6.1 (Shared Models):**
- Models in fp-common are well-structured
- Imports work correctly across packages
- Pydantic 2.0 syntax is used throughout

### Project Structure Notes

- **New directory:** `libs/fp-common/fp_common/converters/`
- **Follows existing pattern:** Similar to `libs/fp-common/fp_common/models/`
- **Import path:** `from fp_common.converters import farmer_from_proto`

### References

- [ADR-004: Type Safety Architecture](../architecture/adr/ADR-004-type-safety-shared-pydantic-models.md)
- [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
- [Story 0.6.1: Shared Pydantic Models](./0-6-1-shared-pydantic-models.md) - Already done
- [project-context.md](../project-context.md) - Critical rules reference

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

1. Created 5 converter functions: farmer_from_proto, factory_from_proto, region_from_proto, collection_point_from_proto, farmer_summary_from_proto
2. Used TypeVar for generic enum converter (Python 3.11 compatible - noqa for UP047)
3. All converters handle nested messages, enums, and optional fields
4. 31 comprehensive unit tests covering:
   - Basic field mapping
   - Enum conversion (Proto uppercase -> Pydantic lowercase)
   - Nested message extraction
   - Optional field defaults
   - Round-trip validation

### File List

**Created:**
- libs/fp-common/fp_common/converters/__init__.py
- libs/fp-common/fp_common/converters/plantation_converters.py
- tests/unit/fp_common/converters/__init__.py
- tests/unit/fp_common/converters/test_plantation_converters.py

**Modified:**
- _bmad-output/sprint-artifacts/sprint-status.yaml (status: in-progress)
- _bmad-output/sprint-artifacts/0-6-11-proto-to-pydantic-converters.md (this file)
