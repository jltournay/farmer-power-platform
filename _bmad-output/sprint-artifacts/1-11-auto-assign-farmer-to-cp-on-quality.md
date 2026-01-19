# Story 1.11: Auto-Assignment of Farmer to Collection Point on Quality Result

**Status:** in-progress
**GitHub Issue:** #203
**Story Points:** 2
**Epic:** Epic 1 - Farmer Registration & Data Foundation

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform operator**,
I want farmers to be automatically assigned to a collection point when their first quality result is received there,
So that the farmer-CP relationship is established without manual intervention.

## Business Context

After Story 9.5a refactored the data model to N:M (farmer_ids on CollectionPoint), we need a mechanism to populate this relationship. While manual assignment is supported via admin UI (Story 9.5), most assignments should happen automatically when a farmer delivers tea to a collection point.

**Value Proposition:**
- Reduces manual data entry burden on admin users
- Ensures data consistency between quality events and farmer-CP relationships
- Supports farmers delivering to multiple collection points (cross-factory scenario)

## Acceptance Criteria

### AC 1.11.1: Auto-Assignment on Quality Result

**Given** a `collection.quality_result.received` event is received
**And** the event contains `farmer_id` and `collection_point_id`
**When** the quality event processor validates the farmer
**Then** if the farmer is NOT already in the CP's `farmer_ids` list
**And** the system calls the CP repository's `add_farmer(cp_id, farmer_id)` method
**And** the farmer is added to the CP's `farmer_ids` list

### AC 1.11.2: Idempotent Assignment

**Given** a farmer is already assigned to a collection point
**When** another quality result arrives for the same farmer at the same CP
**Then** no duplicate assignment occurs (idempotent via `$addToSet`)
**And** no error is raised
**And** quality processing continues normally

### AC 1.11.3: Cross-Factory Assignment

**Given** a farmer is assigned to CP-A (Factory 1)
**When** a quality result arrives for the same farmer at CP-B (Factory 2)
**Then** the farmer is ALSO assigned to CP-B
**And** the farmer now appears in both CP-A and CP-B's `farmer_ids` lists

### AC 1.11.4: Logging and Metrics

**Given** auto-assignment occurs
**When** the assignment completes or fails
**Then** structured logs capture: farmer_id, cp_id, success/failure, duration
**And** metrics are emitted for monitoring auto-assignment rate

---

## Tasks / Subtasks

### Task 1: Add Auto-Assignment Logic to QualityEventProcessor (AC: 1, 2, 3, 4)

- [x] 1.1 Add `_cp_repo: CollectionPointRepository` to `__init__` parameters
- [x] 1.2 Create `_ensure_farmer_assigned_to_cp()` method:
  ```python
  async def _ensure_farmer_assigned_to_cp(self, farmer_id: str, cp_id: str) -> bool:
      """Auto-assign farmer to CP if not already assigned (idempotent).

      Returns True if farmer was newly assigned, False if already assigned or CP not found.
      """
  ```
- [x] 1.3 Wire into `process()` method after farmer validation (around line 191):
  - Get `collection_point_id` from document's `extracted_fields` or `linkage_fields`
  - Call `_ensure_farmer_assigned_to_cp()` with farmer_id, cp_id
- [x] 1.4 Add `_get_collection_point_id()` helper method to extract CP ID from document
- [x] 1.5 Add OpenTelemetry span for auto-assignment: `"ensure_farmer_assigned_to_cp"`
- [x] 1.6 Add metric counter: `farmer_auto_assignments_total` with labels `{status: "success"|"already_assigned"|"cp_not_found"|"skipped_no_repo"|"error"}`

### Task 2: Update QualityEventProcessor Instantiation (AC: 1)

- [x] 2.1 Update `main.py` (where processor is created):
  - Import `CollectionPointRepository`
  - Pass `cp_repo` to `QualityEventProcessor.__init__()`
- [x] 2.2 Update any tests that instantiate `QualityEventProcessor` to include `cp_repo`

### Task 3: Unit Tests (AC: 1, 2, 3, 4)

- [x] 3.1 Create `tests/unit/plantation_model/domain/services/test_quality_event_processor_auto_assignment.py`:
  - [x] 3.1.1 `test_auto_assigns_farmer_to_cp_when_not_already_assigned` - AC 1.11.1
  - [x] 3.1.2 `test_no_duplicate_assignment_when_already_assigned` - AC 1.11.2
  - [x] 3.1.3 `test_assigns_farmer_to_second_cp_at_different_factory` - AC 1.11.3
  - [x] 3.1.4 Logging tested via structured log assertions (implicit)
  - [x] 3.1.5 Metrics tested via counter assertions (implicit)
  - [x] 3.1.6 `test_processing_succeeds_when_cp_not_found` (graceful degradation)
  - [x] 3.1.7 `test_no_auto_assignment_when_document_lacks_cp_id`
  - [x] 3.1.8 `test_no_auto_assignment_when_cp_repo_not_configured`
  - [x] 3.1.9 `test_processing_succeeds_when_cp_repo_raises_error`

### Task 4: Integration Tests (AC: 1, 2, 3)

- [x] 4.1 Create `tests/integration/test_farmer_auto_assignment.py`:
  - [x] 4.1.1 `test_auto_assign_farmer_on_quality_event_e2e` - Full flow with MongoDB
  - [x] 4.1.2 `test_cross_factory_assignment_integration` - Farmer in multiple CPs

### Task 5: E2E Tests (AC: 1, 2)

**PREREQUISITE:** Update seed data to have documents with `collection_point_id`.

- [x] 5.1 Update `tests/e2e/infrastructure/seed/documents.json`:
  - Added DOC-E2E-007 and DOC-E2E-008 with `collection_point_id` for auto-assignment testing
- [x] 5.2 Create `tests/e2e/scenarios/test_36_farmer_auto_assignment_on_quality.py`:
  - [x] 5.2.1 `test_farmer_auto_assigned_on_quality_event` - Assign farmer to CP, verify in queries
  - [x] 5.2.2 `test_farmer_auto_assignment_idempotent` - Assign twice, verify no duplicate

---

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: `gh issue create --title "Story 1.11: Auto-Assign Farmer to CP on Quality Result"` → **#203**
- [x] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/1-11-auto-assign-farmer-to-cp
  ```

**Branch name:** `story/1-11-auto-assign-farmer-to-cp`

### During Development
- [x] All commits reference GitHub issue: `Relates to #203`
- [x] Commits are atomic by type (production, test, seed - not mixed)
- [x] Push to feature branch: `git push -u origin story/1-11-auto-assign-farmer-to-cp`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 1.11: Auto-Assign Farmer to CP" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/1-11-auto-assign-farmer-to-cp`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/plantation/ tests/unit/plantation_model/ -v
```
**Output:**
```
532 passed, 18 warnings in 373.67s (0:06:13)
```

**Story-specific tests (12 new):**
```bash
pytest tests/unit/plantation_model/domain/services/test_quality_event_processor_auto_assignment.py -v
```
```
12 passed, 2 warnings in 1.55s
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

**Local E2E Status:** ✅ PASSED

```bash
bash scripts/e2e-test.sh --keep-up
```
```
220 passed, 1 skipped in 180.58s (0:03:00)
```

**Story-specific E2E tests (6 new):**
```bash
pytest tests/e2e/scenarios/test_36_farmer_auto_assignment_on_quality.py -v
```
```
tests/e2e/scenarios/test_36_farmer_auto_assignment_on_quality.py::TestFarmerAutoAssignmentIdempotent::test_farmer_auto_assigned_on_quality_event PASSED
tests/e2e/scenarios/test_36_farmer_auto_assignment_on_quality.py::TestFarmerAutoAssignmentIdempotent::test_farmer_auto_assignment_idempotent PASSED
tests/e2e/scenarios/test_36_farmer_auto_assignment_on_quality.py::TestCrossFactoryAutoAssignment::test_farmer_assigned_to_multiple_cps_different_factories PASSED
tests/e2e/scenarios/test_36_farmer_auto_assignment_on_quality.py::TestCrossFactoryAutoAssignment::test_cross_factory_assignment_does_not_affect_other_cp PASSED
tests/e2e/scenarios/test_36_farmer_auto_assignment_on_quality.py::TestAutoAssignmentBFFIntegration::test_bff_assign_farmer_idempotent PASSED
tests/e2e/scenarios/test_36_farmer_auto_assignment_on_quality.py::TestAutoAssignmentBFFIntegration::test_bff_get_collection_point_shows_assigned_farmers PASSED
6 passed in 1.52s
```

**E2E passed:** [x] Yes / [ ] Pending CI

### 3. Lint Check
```bash
ruff check services/plantation-model/src/plantation_model/ && ruff format --check services/plantation-model/src/plantation_model/
```
**Output:**
```
All checks passed!
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/1-11-auto-assign-farmer-to-cp

# Wait ~30s, then check CI status
gh run list --branch story/1-11-auto-assign-farmer-to-cp --limit 3
```
**CI Run ID:** 21148933795
**CI Status:** ✅ Passed
**E2E CI Run ID:** 21149156476
**E2E CI Status:** ✅ Passed (220 passed, 1 skipped)
**Verification Date:** 2026-01-19

---

## Dev Notes

### Architecture Context

This story wires auto-assignment into the existing `QualityEventProcessor` which is already called when `collection.quality_result.received` events arrive.

**Event Flow:**
```
Collection Model publishes event
    ↓
plantation-model subscription receives event
    ↓
QualityEventProcessor.process() called
    ↓
[NEW] _ensure_farmer_assigned_to_cp() called
    ↓
CollectionPointRepository.add_farmer() (idempotent $addToSet)
    ↓
Continue with performance update...
```

### Key Files to Modify

| File | Change Type | Purpose |
|------|-------------|---------|
| `services/plantation-model/src/plantation_model/domain/services/quality_event_processor.py` | MODIFY | Add `_ensure_farmer_assigned_to_cp()` method |
| `services/plantation-model/src/plantation_model/subscriptions/quality_subscription.py` | MODIFY | Pass `cp_repo` to processor |
| `tests/unit/plantation/test_quality_event_processor_assignment.py` | NEW | Unit tests for auto-assignment |
| `tests/integration/test_farmer_auto_assignment.py` | NEW | Integration tests |
| `tests/e2e/infrastructure/seed/farmers.json` | MODIFY | Add unassigned test farmer |
| `tests/e2e/scenarios/test_36_farmer_auto_assignment.py` | NEW | E2E tests |

### Code Patterns to Follow

**From Story 9.5a - CollectionPointRepository.add_farmer():**
```python
# Uses $addToSet for idempotency - adding same farmer twice has no effect
async def add_farmer(self, cp_id: str, farmer_id: str) -> CollectionPoint | None:
    result = await self._collection.find_one_and_update(
        {"id": cp_id},
        {"$addToSet": {"farmer_ids": farmer_id}},
        return_document=True,
    )
    # ...
```

### Getting collection_point_id from Document

The document from Collection Model has `collection_point_id` in either `extracted_fields` or `linkage_fields`:

```python
def _get_collection_point_id(self, document: Document) -> str | None:
    """Extract collection point ID from document."""
    if "collection_point_id" in document.extracted_fields:
        return str(document.extracted_fields["collection_point_id"])
    if "collection_point_id" in document.linkage_fields:
        return str(document.linkage_fields["collection_point_id"])
    return None
```

### Previous Story Intelligence (Story 9.5a)

**Completed on 2026-01-18 - Key takeaways:**

1. **N:M Relationship Pattern:** Farmer-CP is now N:M with `farmer_ids: list[str]` on CollectionPoint
2. **Idempotent Assignment:** `$addToSet` ensures no duplicates - safe to call multiple times
3. **Repository Methods Available:**
   - `CollectionPointRepository.add_farmer(cp_id, farmer_id)` - Returns updated CP or None
   - `CollectionPointRepository.list_by_farmer(farmer_id)` - Find all CPs for a farmer
4. **Test Patterns:** E2E tests for assignment are in `test_35_farmer_cp_assignment.py`

### Technology Stack Reference

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12 | Service implementation |
| Pydantic | 2.0 | Data models (`model_dump()`, not `dict()`) |
| Motor | Latest | Async MongoDB client |
| OpenTelemetry | Latest | Tracing and metrics |
| structlog | Latest | Structured logging |

### Testing Requirements

| Test Type | Location | What to Test |
|-----------|----------|--------------|
| Unit | `tests/unit/plantation/` | Assignment logic, idempotency, edge cases |
| Integration | `tests/integration/` | Full flow with MongoDB |
| E2E | `tests/e2e/scenarios/` | Quality event triggers assignment |

### Potential Edge Cases

1. **CP Not Found:** If `collection_point_id` in document references non-existent CP
   - Graceful degradation: log warning, continue processing without assignment
   - Do NOT fail the entire quality event processing

2. **Missing collection_point_id:** If document doesn't have CP reference
   - Log debug message, skip assignment, continue processing

3. **Farmer Already Assigned:** Covered by `$addToSet` idempotency

4. **Concurrent Assignments:** MongoDB `$addToSet` is atomic, race conditions handled

### References

- [Source: _bmad-output/epics/epic-1-plantation-model.md#story-1.11] - Story definition in epics
- [Source: _bmad-output/sprint-artifacts/9-5a-farmer-cp-data-model.md] - Dependency story
- [Source: services/plantation-model/src/plantation_model/domain/services/quality_event_processor.py] - Wiring point
- [Source: services/plantation-model/src/plantation_model/infrastructure/repositories/collection_point_repository.py:112] - `add_farmer()` method
- [Source: _bmad-output/project-context.md] - Project rules and patterns

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None required - implementation was straightforward.

### Completion Notes List

1. Implemented auto-assignment logic in `QualityEventProcessor._ensure_farmer_assigned_to_cp()`
2. Added OpenTelemetry tracing span `ensure_farmer_assigned_to_cp`
3. Added metric counter `farmer_auto_assignments_total` with status labels
4. Auto-assignment is best-effort - failures don't block quality event processing
5. Uses `list_by_farmer()` to check existing assignment before `add_farmer()` for optimization

### File List

**Created:**
- `tests/unit/plantation_model/domain/services/test_quality_event_processor_auto_assignment.py` - 12 unit tests for auto-assignment
- `tests/integration/test_farmer_auto_assignment.py` - Integration tests with real MongoDB
- `tests/e2e/scenarios/test_36_farmer_auto_assignment_on_quality.py` - E2E tests for auto-assignment

**Modified:**
- `services/plantation-model/src/plantation_model/domain/services/quality_event_processor.py` - Added `_cp_repo` param, `_get_collection_point_id()`, `_ensure_farmer_assigned_to_cp()`, and metric counter
- `services/plantation-model/src/plantation_model/main.py` - Added `CollectionPointRepository` instantiation and pass to processor
- `tests/e2e/infrastructure/seed/documents.json` - Added DOC-E2E-007 and DOC-E2E-008 with `collection_point_id`
