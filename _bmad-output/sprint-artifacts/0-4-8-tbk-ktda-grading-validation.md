# Story 0.4.8: TBK/KTDA Grading Model Validation

**Status:** ready-for-dev
**GitHub Issue:** #39
**Epic:** [Epic 0.4: E2E Test Scenarios](../epics/epic-0-4-e2e-tests.md)
**Story Points:** 2

## Story

As a **quality assurance manager**,
I want grading model calculations validated,
So that farmer payments are based on accurate grade distributions.

## Acceptance Criteria

1. **AC1: TBK Primary Grade (two_leaves_bud)** - Given TBK grading model is seeded (binary: Primary/Secondary), When a quality event with `leaf_type: two_leaves_bud` is processed, Then the grade is calculated as "Primary"

2. **AC2: TBK Secondary Grade (coarse_leaf)** - Given TBK reject conditions are configured, When a quality event with `leaf_type: coarse_leaf` is processed, Then the grade is calculated as "Secondary"

3. **AC3: TBK Conditional Reject (hard banji)** - Given TBK conditional reject is configured, When a quality event with `leaf_type: banji, banji_hardness: hard` is processed, Then the grade is calculated as "Secondary"

4. **AC4: TBK Soft Banji Acceptable** - Given TBK soft banji is acceptable, When a quality event with `leaf_type: banji, banji_hardness: soft` is processed, Then the grade is calculated as "Primary"

5. **AC5: KTDA Grade A (fine/optimal)** - Given KTDA grading model is seeded (ternary: Grade A/B/Rejected), When a quality event with `leaf_type: fine, moisture_level: optimal` is processed, Then the grade is calculated as "Grade A" (premium)

6. **AC6: KTDA Rejected (stalks)** - Given KTDA reject conditions are configured, When a quality event with `leaf_type: stalks` is processed, Then the grade is calculated as "Rejected"

## Tasks / Subtasks

- [ ] **Task 1: Create Test File Scaffold** (AC: All)
  - [ ] Create `tests/e2e/scenarios/test_07_grading_validation.py`
  - [ ] Import fixtures: `plantation_mcp`, `collection_mcp`, `collection_api`, `azurite_client`, `mongodb_direct`
  - [ ] Add `@pytest.mark.e2e` class marker
  - [ ] Add file docstring documenting test scope and grading model requirements

- [ ] **Task 2: Implement TBK Primary Grade Test** (AC: 1)
  - [ ] Create quality event with `leaf_type: two_leaves_bud` for farmer with TBK grading model
  - [ ] Ingest via blob trigger (reuse pattern from Story 0.4.5)
  - [ ] Wait for DAPR event processing (5s)
  - [ ] Query `get_farmer_summary` via Plantation MCP
  - [ ] Verify `grade_distribution_30d` contains "Primary" with count > 0

- [ ] **Task 3: Implement TBK Secondary Grade Tests** (AC: 2, 3)
  - [ ] Test AC2: Event with `leaf_type: coarse_leaf` → "Secondary"
  - [ ] Test AC3: Event with `leaf_type: banji, banji_hardness: hard` → "Secondary"
  - [ ] Verify conditional_reject logic applies to hard banji

- [ ] **Task 4: Implement TBK Soft Banji Test** (AC: 4)
  - [ ] Create event with `leaf_type: banji, banji_hardness: soft`
  - [ ] Verify soft banji bypasses conditional_reject
  - [ ] Verify grade is "Primary" (not "Secondary")

- [ ] **Task 5: Implement KTDA Ternary Grading Tests** (AC: 5, 6)
  - [ ] Test AC5: Event with `leaf_type: fine, moisture_level: optimal` → "Grade A"
  - [ ] Test AC6: Event with `leaf_type: stalks` → "Rejected"
  - [ ] Verify KTDA uses ternary grading (3 levels vs TBK binary)

- [ ] **Task 6: Test Validation** (AC: All)
  - [ ] Run `ruff check tests/e2e/scenarios/test_07_grading_validation.py`
  - [ ] Run `ruff format` on new files
  - [ ] Run all tests locally with Docker infrastructure
  - [ ] Verify CI pipeline passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: `gh issue create --title "Story 0.4.8: TBK/KTDA Grading Model Validation"` → #39
- [x] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-4-8-tbk-ktda-grading-validation
  ```

**Branch name:** `story/0-4-8-tbk-ktda-grading-validation`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-4-8-tbk-ktda-grading-validation`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.4.8: TBK/KTDA Grading Model Validation" --base main`
- [ ] CI passes on PR
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-4-8-tbk-ktda-grading-validation`

**PR URL:** (to be created)

---

## E2E Story Checklist (MANDATORY for E2E stories)

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
If you modified ANY production code (`services/`, `mcp-servers/`, `libs/`), document each change here:

| File:Lines | What Changed | Why (with evidence) | Type |
|------------|--------------|---------------------|------|
| (none) | | | |

**Rules:**
- "To pass tests" is NOT a valid reason
- Must reference proto line, API spec, or other evidence
- If you can't fill this out, you may not understand what you're changing

### Infrastructure/Integration Changes (if any)
If you modified mock servers, docker-compose, env vars, or seed data that affects service behavior:

| File | What Changed | Why | Impact |
|------|--------------|-----|--------|
| (none) | | | |

### Unit Test Changes (if any)
If you modified ANY unit test behavior, document here:

| Test File | Test Name Before | Test Name After | Behavior Change | Justification |
|-----------|------------------|-----------------|-----------------|---------------|
| (none) | | | | |

### Local Test Run Evidence (MANDATORY before any push)

**First run timestamp:** (to be filled)

**Docker stack status:**
```
(to be filled after docker-compose up)
```

**Test run output:**
```
(to be filled after pytest run)
```

**If tests failed before passing, explain what you fixed:**

| Attempt | Failure | Root Cause | Fix Applied | Layer Fixed |
|---------|---------|------------|-------------|-------------|
| | | | | |

### Before Marking Done
- [ ] All tests pass locally with Docker infrastructure
- [ ] `ruff check` and `ruff format --check` pass
- [ ] CI pipeline is green
- [ ] If production code changed: Change log above is complete
- [ ] If unit tests changed: Change log above is complete
- [ ] Story file updated with completion notes

---

## Dev Notes

### Grading Model Architecture

This story validates the **GradingModel domain model** which determines how quality events are graded for payment calculations.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 GRADING MODEL VALIDATION (Story 0.4.8)                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Grading Types:                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │ BINARY (TBK)    │  │ TERNARY (KTDA)  │  │ MULTI_LEVEL     │         │
│  │ Primary/Second. │  │ Grade A/B/Rej.  │  │ (Future)        │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│                                                                         │
│  Grade Calculation Flow:                                                │
│  1. Quality Event received with attributes (leaf_type, moisture, etc.) │
│  2. GradingModel loaded for farmer's factory                           │
│  3. Check reject_conditions → if match → lowest grade                  │
│  4. Check conditional_reject → if match AND condition → lower grade    │
│  5. Otherwise → calculate grade from grade_rules                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### TBK Grading Model (Binary)

**Seed Data:** `tests/e2e/infrastructure/seed/grading_models.json` - `tbk_kenya_tea_v1`

| Component | Configuration | Behavior |
|-----------|---------------|----------|
| `grading_type` | `BINARY` | Two grades only |
| `grade_labels` | `["Primary", "Secondary"]` | Index 0 = best, 1 = worst |
| `reject_conditions` | `["coarse_leaf"]` | Always Secondary |
| `conditional_reject` | `{"field": "banji_hardness", "value": "hard", "applies_to": ["banji"]}` | Hard banji → Secondary |

**Test Matrix:**

| Input | Expected Grade | Reason |
|-------|----------------|--------|
| `leaf_type: two_leaves_bud` | Primary | Default best grade |
| `leaf_type: coarse_leaf` | Secondary | In `reject_conditions` |
| `leaf_type: banji, banji_hardness: hard` | Secondary | `conditional_reject` applies |
| `leaf_type: banji, banji_hardness: soft` | Primary | Soft banji bypasses conditional reject |

### KTDA Grading Model (Ternary)

**Seed Data:** `tests/e2e/infrastructure/seed/grading_models.json` - `ktda_ternary_v1`

| Component | Configuration | Behavior |
|-----------|---------------|----------|
| `grading_type` | `TERNARY` | Three grades |
| `grade_labels` | `["Grade A", "Grade B", "Rejected"]` | Premium/Standard/Rejected |
| `reject_conditions` | `["stalks"]` | Always Rejected |
| `grade_rules` | `{"fine": 0, "medium": 1, ...}` | Quality → grade index |

**Test Matrix:**

| Input | Expected Grade | Reason |
|-------|----------------|--------|
| `leaf_type: fine, moisture_level: optimal` | Grade A | Best quality combination |
| `leaf_type: medium, moisture_level: wet` | Grade B | Medium quality |
| `leaf_type: stalks` | Rejected | In `reject_conditions` |

### GradingModel Domain Model

**Location:** `services/plantation-model/src/plantation_model/domain/models/grading_model.py`

```python
class GradingType(str, Enum):
    BINARY = "binary"      # TBK: Primary/Secondary
    TERNARY = "ternary"    # KTDA: Grade A/B/Rejected
    MULTI_LEVEL = "multi_level"  # Future extensibility

class GradeRules(BaseModel):
    reject_conditions: list[str]  # Leaf types that always reject
    conditional_reject: Optional[ConditionalReject]  # Conditional downgrade

class GradingModel(BaseModel):
    id: str
    name: str
    grading_type: GradingType
    grade_labels: list[str]  # Index 0 = best
    grade_rules: GradeRules
```

### QualityEventProcessor Integration

**Location:** `services/plantation-model/src/plantation_model/domain/services/quality_event_processor.py`

The `QualityEventProcessor` uses the `GradingModel` to:
1. Fetch quality document from Collection MCP
2. Load grading model for farmer's factory
3. Extract grade from document attributes
4. Update `FarmerPerformance.historical.grade_distribution_30d`

**Key Method:** `_extract_grade_counts(doc, grading_model) -> dict[str, int]`

### Test Implementation Pattern

```python
@pytest.mark.e2e
class TestTBKGradingValidation:
    """TBK binary grading model validation tests."""

    async def test_two_leaves_bud_grades_primary(
        self,
        plantation_mcp,
        collection_api,
        azurite_client,
        mongodb_direct
    ):
        """AC1: two_leaves_bud → Primary grade."""
        # 1. Create quality event with leaf_type: two_leaves_bud
        quality_event = {
            "farmer_id": "FRM-E2E-TBK-001",
            "leaf_type": "two_leaves_bud",
            "weight_kg": 10.0,
            "timestamp": datetime.now(UTC).isoformat()
        }

        # 2. Ingest via blob trigger
        await azurite_client.upload_json(container, blob_path, quality_event)
        await collection_api.trigger_blob_event(container, blob_path)

        # 3. Wait for processing (5s for DAPR)
        await asyncio.sleep(5)

        # 4. Query farmer summary
        response = await plantation_mcp.call_tool("get_farmer_summary", {"farmer_id": "FRM-E2E-TBK-001"})
        summary = json.loads(response["content"][0]["text"])

        # 5. Verify grade distribution
        grade_dist = summary["historical"]["grade_distribution_30d"]
        assert "Primary" in grade_dist
        assert grade_dist["Primary"] > 0
```

### Seed Data Requirements

| File | Required Data |
|------|---------------|
| `grading_models.json` | `tbk_kenya_tea_v1` and `ktda_ternary_v1` grading models |
| `farmers.json` | Farmers linked to factories using each grading model |
| `factories.json` | Factories configured with TBK and KTDA grading models |
| `source_configs.json` | `e2e-qc-direct-json` for blob ingestion |

### Test File Location

`tests/e2e/scenarios/test_07_grading_validation.py`

### CI Validation Requirements

Before marking story done:
1. Run lint: `ruff check . && ruff format --check .`
2. Run E2E tests locally (see Local E2E Test Setup below)
3. Push and verify GitHub Actions CI passes

### Local E2E Test Setup

**Prerequisites:** Docker 24.0+, Docker Compose 2.20+

**Full E2E Test Workflow:**
```bash
# 1. Build Docker images (required after any code changes)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml build

# 2. Start E2E stack
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d

# 3. Wait for services to be healthy (all should show "healthy")
watch -n 2 'docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps'

# 4. Run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_07_grading_validation.py -v

# 5. Cleanup
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

### References

- [Source: `_bmad-output/epics/epic-0-4-e2e-tests.md` - Story 0.4.8 acceptance criteria]
- [Source: `tests/e2e/infrastructure/seed/grading_models.json` - TBK and KTDA grading model seed data]
- [Source: `services/plantation-model/src/plantation_model/domain/models/grading_model.py` - GradingModel domain model]
- [Source: `services/plantation-model/src/plantation_model/domain/services/quality_event_processor.py` - Grade processing logic]
- [Source: `proto/plantation/v1/plantation.proto` - GradingModel proto definition]
- [Source: `tests/e2e/scenarios/test_06_cross_model_events.py` - Event flow pattern to reuse]

### Critical Implementation Notes

1. **Factory-Grading Model linkage** - Farmers inherit grading model from their factory
2. **Grade distribution is cumulative** - Multiple events for same farmer accumulate in `grade_distribution_30d`
3. **Conditional reject logic** - Only applies when BOTH `applies_to` field matches AND condition value matches
4. **Test isolation** - Use unique farmer IDs per grading model type to avoid cross-contamination
5. **DAPR event timing** - Allow 5s after blob ingestion for event propagation

### Potential Issues to Watch

1. **Grading model not found** - Ensure factory has `grading_model_id` field set
2. **Grade labels mismatch** - Verify seed data `grade_labels` match expected assertions
3. **Conditional reject not triggering** - Check both `applies_to` and `value` conditions
4. **KTDA vs TBK farmers** - Don't mix farmers across grading model types in same test

---

## Dev Agent Record

### Agent Model Used

(to be filled)

### Debug Log References

(to be filled)

### Completion Notes List

(to be filled)

### File List

**Created:**
- (to be filled)

**Modified:**
- (to be filled)
