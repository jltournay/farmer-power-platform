# Lessons Learned: Story 1.2 Code Review Findings

**Story:** 1.2 - Factory and Collection Point Management
**Date:** 2025-12-23
**Severity Legend:** HIGH = blocks release, MEDIUM = should fix before merge

---

## Summary

During code review of Story 1.2, several issues were identified that should be avoided in future implementations. This document serves as a reference for agents working on similar gRPC services with entity relationships.

---

## Issue #1: Missing gRPC Service Tests (HIGH)

### Problem
Task 5.4 "Test gRPC service methods with mock repositories" was marked complete, but NO actual test files existed for the gRPC service layer.

### Root Cause
Tests were written for domain models and repositories, but the gRPC servicer methods (`GetFactory`, `CreateFactory`, etc.) had zero test coverage.

### Fix Applied
Created comprehensive test files:
- `tests/unit/plantation/test_grpc_factory.py` (12 tests)
- `tests/unit/plantation/test_grpc_collection_point.py` (19 tests)

### Prevention
- **Always create tests for EACH layer**: domain models, repositories, AND service/API layer
- **Verify test files exist** before marking testing tasks complete
- **Use test naming convention**: `test_grpc_{entity}.py` for gRPC service tests

---

## Issue #2: Test Count Mismatch in Documentation (HIGH)

### Problem
Documentation claimed "88 tests" but actual count was different (and kept changing as tests were added).

### Root Cause
Test count was manually written and never verified against actual `pytest` output.

### Fix Applied
Updated documentation with actual verified count: 140 tests (122 unit + 18 integration)

### Prevention
- **Run `pytest --collect-only -q | tail -1`** to get accurate test count before documenting
- **Don't hardcode test counts** - or add a note that count is approximate
- **Verify counts** during code review by running the test suite

---

## Issue #3: Incomplete File List in Story Documentation (MEDIUM)

### Problem
Several files created during implementation were not listed in the story's "File List" section.

### Root Cause
Files were added incrementally during development but documentation wasn't updated.

### Fix Applied
Added all missing files to the File List section.

### Prevention
- **Update File List immediately** when creating new files
- **Use `git status`** at end of story to verify all changed files are documented
- **Include test files** in the File List, not just source files

---

## Issue #4: Missing Delete RPCs (MEDIUM)

### Problem
CRUD operations were incomplete - Create, Read, Update existed but Delete was missing for both Factory and CollectionPoint.

### Root Cause
Proto definitions included Delete RPCs, but implementation was skipped/forgotten.

### Fix Applied
- Added `DeleteFactory` and `DeleteCollectionPoint` to proto
- Implemented both methods in `PlantationServiceServicer`
- Added tests for success and NOT_FOUND cases

### Prevention
- **CRUD = Create, Read, Update, DELETE** - always implement all four
- **Cross-reference proto definitions** with implementation to ensure completeness
- **Add Delete to acceptance criteria** explicitly

---

## Issue #5: Missing Input Validation for Enum-like Fields (MEDIUM)

### Problem
Fields like `status`, `storage_type`, and `collection_days` accepted any string value, including invalid ones. No validation was performed at the gRPC layer.

### Root Cause
Pydantic models had no validators for these fields, and gRPC layer didn't validate before processing.

### Fix Applied
Added validation in `CreateCollectionPoint` and `UpdateCollectionPoint`:
```python
VALID_CP_STATUSES = {"active", "inactive", "seasonal"}
VALID_STORAGE_TYPES = {"covered_shed", "open_air", "refrigerated"}
VALID_COLLECTION_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}

if request.status not in VALID_CP_STATUSES:
    await context.abort(
        grpc.StatusCode.INVALID_ARGUMENT,
        f"Invalid status '{request.status}'. Must be one of: ..."
    )
```

### Prevention
- **Define valid values as constants** at module level
- **Validate at API boundary** (gRPC service layer) before processing
- **Return `INVALID_ARGUMENT`** with clear error message listing valid options
- **Add validation tests** for each enum-like field

---

## Issue #6: Referential Integrity Not Enforced (CRITICAL)

### Problem
`DeleteFactory` allowed deleting a factory even when it had associated collection points, leaving orphaned records in the database.

### Root Cause
Delete operation only checked if the factory existed, not if it had child entities.

### Fix Applied
Added pre-deletion check:
```python
async def DeleteFactory(self, request, context):
    # Check if factory has any collection points
    cps, _, count = await self._cp_repo.list(
        filters={"factory_id": request.id},
        page_size=1,
    )
    if count > 0:
        await context.abort(
            grpc.StatusCode.FAILED_PRECONDITION,
            f"Cannot delete factory {request.id}: {count} collection point(s) still exist.",
        )
    # ... proceed with deletion
```

### Prevention
- **Always check for child entities** before deleting parent entities
- **Use `FAILED_PRECONDITION`** status code for referential integrity violations
- **Document entity relationships** and their cascade/restrict behavior
- **Add referential integrity tests** as part of Delete operation tests

---

## Issue #7: gRPC Mock Context Not Simulating Real Behavior (MEDIUM)

### Problem
Initial tests for error cases (NOT_FOUND, ALREADY_EXISTS) were passing incorrectly because `context.abort()` wasn't raising an exception like the real gRPC context does.

### Root Cause
Mock was created as `context.abort = AsyncMock()` which just records the call but doesn't stop execution.

### Fix Applied
```python
@pytest.fixture
def mock_context(self) -> MagicMock:
    context = MagicMock(spec=grpc.aio.ServicerContext)
    # Make abort raise an exception to stop execution (like real gRPC behavior)
    context.abort = AsyncMock(side_effect=grpc.RpcError())
    return context
```

And wrap abort-expecting calls:
```python
with pytest.raises(grpc.RpcError):
    await servicer.GetFactory(request, mock_context)
```

### Prevention
- **Always use `side_effect=grpc.RpcError()`** for mock abort
- **Wrap expected-failure calls** in `pytest.raises(grpc.RpcError)`
- **Test that execution stops** after abort by verifying no further calls were made

---

## Checklist for Future gRPC Service Implementations

### Before Implementation
- [ ] All CRUD operations defined in proto (Create, Read, Update, Delete, List)
- [ ] Entity relationships documented (parent-child, cascade behavior)
- [ ] Valid values for enum-like fields defined

### During Implementation
- [ ] Validate enum-like fields at API boundary with `INVALID_ARGUMENT`
- [ ] Check parent entity exists before creating child (NOT_FOUND)
- [ ] Check for child entities before deleting parent (FAILED_PRECONDITION)
- [ ] Check for duplicates on unique fields (ALREADY_EXISTS)

### Testing
- [ ] Tests exist for EACH layer: models, repositories, gRPC service
- [ ] Success cases tested
- [ ] Error cases tested (NOT_FOUND, ALREADY_EXISTS, INVALID_ARGUMENT, FAILED_PRECONDITION)
- [ ] Mock context uses `side_effect=grpc.RpcError()` for abort
- [ ] Referential integrity tested (create child for missing parent, delete parent with children)

### Documentation
- [ ] File List includes ALL created/modified files
- [ ] Test count verified by running pytest
- [ ] Entity relationships documented

---

## gRPC Status Code Quick Reference

| Scenario | Status Code |
|----------|-------------|
| Entity not found | `NOT_FOUND` |
| Duplicate unique field | `ALREADY_EXISTS` |
| Invalid field value | `INVALID_ARGUMENT` |
| Referential integrity violation | `FAILED_PRECONDITION` |
| Missing required field | `INVALID_ARGUMENT` |
| Unauthorized | `PERMISSION_DENIED` |
| Server error | `INTERNAL` |
