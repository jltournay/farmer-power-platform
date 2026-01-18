# Story 9.5a: Farmer-CollectionPoint Data Model Refactor

## Context

**Issue:** [GitHub Issue #200](https://github.com/jltournay/farmer-power-platform/issues/200)

This is a **technical prerequisite story** that must be completed before Story 9.5 (Farmer Management) can proceed. The current data model incorrectly has `collection_point_id` as a single FK on the Farmer entity, implying a farmer belongs to ONE collection point.

**Domain Reality:**
- A Factory assigns farmers to its CollectionPoints
- Different factories can assign the same farmer to their CPs
- The relationship ownership is on CollectionPoint side (CP has farmers)
- Collection point assignment is a separate action from farmer creation
- Assignment can be manual (admin UI) or automatic (on quality result received)

## Story

As a **platform developer**,
I want to refactor the Farmer-CollectionPoint relationship from N:1 to N:M,
So that a farmer can be correctly associated with multiple collection points across different factories.

## Acceptance Criteria

### AC 9.5a.1: Remove collection_point_id from Farmer

**Given** the current Farmer model has `collection_point_id: str`
**When** this story is complete
**Then**:
- Farmer entity no longer has `collection_point_id` field
- Farmer creation does NOT require a collection point
- Farmer proto message updated to remove the field
- All references to `farmer.collection_point_id` are removed or migrated

### AC 9.5a.2: Add farmer_ids to CollectionPoint

**Given** a CollectionPoint entity
**When** this story is complete
**Then**:
- CollectionPoint has `farmer_ids: list[str] = []` field
- Proto `CollectionPoint` message includes `repeated string farmer_ids`
- Existing CPs initialize with empty farmer_ids list

### AC 9.5a.3: Farmer-CP Assignment Endpoints

**Given** the new N:M relationship
**When** admin needs to assign/unassign farmers
**Then** the following endpoints exist:
- `POST /api/admin/collection-points/{cp_id}/farmers/{farmer_id}` - Assign farmer to CP
- `DELETE /api/admin/collection-points/{cp_id}/farmers/{farmer_id}` - Unassign farmer from CP
- Assignment is idempotent (assigning twice = no-op)
- Unassignment is idempotent (unassigning non-member = no-op)

### AC 9.5a.4: Plantation Model gRPC Methods

**Given** the service layer changes
**When** inter-service communication is needed
**Then**:
- `rpc AssignFarmerToCollectionPoint(AssignFarmerRequest) returns (CollectionPoint)`
- `rpc UnassignFarmerFromCollectionPoint(UnassignFarmerRequest) returns (CollectionPoint)`
- Methods validate farmer_id and cp_id exist before assignment

### AC 9.5a.5: Farmer List Shows Factory Count

**Given** the farmer list API
**When** listing farmers
**Then**:
- Response includes `factory_count: int` instead of `collection_point_id`
- Factory count = distinct factories whose CPs contain this farmer
- List can be filtered by `collection_point_id` (farmers assigned to that CP)

### AC 9.5a.6: Farmer Detail Shows Collection Points

**Given** a farmer detail view
**When** viewing farmer details
**Then**:
- Response includes `collection_points: list[CollectionPointSummary]`
- Each CP summary includes: id, name, factory_id, factory_name
- Empty list if farmer not assigned to any CPs

### AC 9.5a.7: E2E Tests Updated

**Given** the data model changes
**When** E2E tests run
**Then**:
- Seed data updated to use farmer_ids on CPs
- Existing E2E tests updated to work with new model
- New tests for assignment/unassignment endpoints

---

## Technical Notes

### Data Model Change Summary

**Before (N:1 - WRONG):**
```python
class Farmer(BaseModel):
    id: str
    collection_point_id: str  # Single FK - implies farmer belongs to ONE CP
    ...

class CollectionPoint(BaseModel):
    id: str
    factory_id: str
    ...
```

**After (N:M - CORRECT):**
```python
class Farmer(BaseModel):
    id: str
    # NO collection_point_id - farmer is independent
    ...

class CollectionPoint(BaseModel):
    id: str
    factory_id: str
    farmer_ids: list[str] = []  # Farmers assigned to this CP
    ...
```

### Query Patterns

| Query | Implementation |
|-------|----------------|
| Farmers at CP X | `cp.farmer_ids` (direct) |
| CPs for Farmer Y | Find all CPs where `farmer_id in farmer_ids` |
| Factory count for Farmer | Count distinct `factory_id` from CPs containing farmer |
| Farmers in Factory Z | Find all CPs for factory, union all farmer_ids |

### Files to Modify

| Layer | Files |
|-------|-------|
| **fp-common models** | `libs/fp-common/fp_common/models/farmer.py`, `collection_point.py` |
| **Proto definitions** | `proto/plantation/v1/farmer.proto`, `collection_point.proto`, `plantation_service.proto` |
| **Plantation Model** | `services/plantation-model/src/plantation_model/grpc/handlers/`, repositories |
| **BFF Admin** | `services/bff/src/bff/api/routes/admin/`, schemas |
| **Seed Data** | `tests/e2e/infrastructure/seed/` |

### Future: Auto-Assignment

When a quality result is received (via Collection Model), the system should auto-assign the farmer to the CP if not already assigned. This auto-assignment logic will be implemented in a future story (likely Epic 2 or a new Epic 1 story), not in this story.

This story only implements the **manual assignment** via admin UI endpoints.

---

## Dependencies

- **Blocks:** Story 9.5 (Farmer Management)
- **Related:** GitHub Issue #200

## Story Points: 5
