# E2E Testing Mental Model

**Required reading for all developers working on E2E tests.**

This document explains the conceptual framework for understanding E2E contract tests, the hierarchy of truth, and how to debug failures correctly.

---

## Feature Branch Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Workflow Overview

```
STORY LIFECYCLE
══════════════════════════════════════════════════════════════════════════════

1. STORY START                 2. DEVELOPMENT                   3. STORY DONE
   ─────────────                  ───────────                      ──────────

   Create/Update GitHub Issue     Create Feature Branch            Create Pull Request
   ┌─────────────────────────┐    ┌─────────────────────────┐      ┌─────────────────────────┐
   │ gh issue create         │    │ git checkout main       │      │ gh pr create            │
   │   --title "Story X.Y.Z" │    │ git pull                │      │   --title "Story X.Y.Z" │
   │   --body "..."          │    │ git checkout -b         │      │   --base main           │
   │                         │    │   story/X-Y-Z-name      │      │                         │
   │ Or use existing issue   │    │                         │      │ Fill PR template        │
   └─────────────────────────┘    └─────────────────────────┘      └─────────────────────────┘
                                           │                                │
                                           ▼                                ▼
                                  Implement + Test Locally          Code Review Gate
                                  ┌─────────────────────────┐      ┌─────────────────────────┐
                                  │ - Write code            │      │ - CI must pass          │
                                  │ - Run local E2E tests   │      │ - Run /code-review      │
                                  │ - Document changes      │      │ - Address feedback      │
                                  │ - Atomic commits        │      │ - Get approval          │
                                  └─────────────────────────┘      └─────────────────────────┘
                                           │                                │
                                           ▼                                ▼
                                  Push to Feature Branch            Merge to Main
                                  ┌─────────────────────────┐      ┌─────────────────────────┐
                                  │ git push -u origin      │      │ gh pr merge             │
                                  │   story/X-Y-Z-name      │      │   --squash              │
                                  │                         │      │                         │
                                  │ (triggers CI)           │      │ Update issue status     │
                                  └─────────────────────────┘      └─────────────────────────┘

══════════════════════════════════════════════════════════════════════════════
```

### Branch Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Story | `story/{epic}-{story}-{short-name}` | `story/0-4-7-cross-model-dapr` |
| Hotfix | `fix/{issue}-{short-name}` | `fix/32-blob-upload-error` |
| Docs | `docs/{short-description}` | `docs/update-mental-model` |

### Step-by-Step Commands

**1. Story Start (create or update GitHub issue):**
```bash
# Create new issue
gh issue create \
  --title "Story 0.4.7: Cross-Model DAPR Event Flow" \
  --body "## Story
As a **platform operator**...

## Acceptance Criteria
1. AC1: ...
"

# Or update existing issue
gh issue edit 32 --add-label "in-progress"
```

**2. Create Feature Branch:**
```bash
git checkout main
git pull origin main
git checkout -b story/0-4-7-cross-model-dapr
```

**3. Development (atomic commits):**
```bash
# Production code change
git add services/collection-model/src/...
git commit -m "fix(collection): description

Relates to #32
"

# Test infrastructure change (separate commit)
git add tests/e2e/infrastructure/...
git commit -m "feat(e2e): description

Relates to #32
"

# Push to feature branch
git push -u origin story/0-4-7-cross-model-dapr
```

**4. Create Pull Request:**
```bash
gh pr create \
  --title "Story 0.4.7: Cross-Model DAPR Event Flow" \
  --base main \
  --body "## Summary
- Implemented cross-model DAPR event publishing
- Added E2E tests for event flow verification

## Changes
- [x] Production code changes documented
- [x] Local E2E tests pass
- [x] CI passing

## Test Evidence
\`\`\`
pytest tests/e2e/scenarios/test_06_*.py -v
6 passed in 12.34s
\`\`\`

Closes #32
"
```

**5. Code Review + Merge:**
```bash
# Run code review workflow
/code-review

# After approval, merge (squash recommended)
gh pr merge --squash

# Clean up local branch
git checkout main
git pull
git branch -d story/0-4-7-cross-model-dapr
```

### Protection Rules (Enforced by GitHub)

| Rule | Setting | Why |
|------|---------|-----|
| Require PR | ✅ Enabled | No direct pushes to main |
| Require CI pass | ✅ Enabled | Broken code can't merge |
| Require approval | ✅ 1 reviewer | Code review gate |
| Dismiss stale reviews | ✅ Enabled | New commits need re-review |
| Require branch up-to-date | ✅ Enabled | Must rebase before merge |

### Why Feature Branches?

1. **Code review gate** - Changes reviewed before reaching main
2. **CI validation** - Tests must pass before merge
3. **Clear history** - Each story is one squashed commit
4. **Easy revert** - Can revert entire story if needed
5. **Parallel work** - Multiple stories can develop simultaneously
6. **Trust but verify** - Developer work is validated before integration

---

## The Truth Hierarchy

In E2E testing, there is a strict hierarchy of what defines "correct":

```
TRUTH HIERARCHY (Top = Most Authoritative)
══════════════════════════════════════════════════════════════

1. PROTO DEFINITIONS          ← The Contract (NEVER changes for tests)
   proto/plantation/v1/*.proto
   proto/collection/v1/*.proto

2. PRODUCTION CODE            ← Implements the Contract
   services/*/src/
   mcp-servers/*/src/

3. SEED DATA                  ← Test Input (must conform to production)
   tests/e2e/infrastructure/seed/

4. TEST ASSERTIONS            ← Verify behavior
   tests/e2e/scenarios/

══════════════════════════════════════════════════════════════
```

**Key principle:** Truth flows DOWN, not up. Lower layers adapt to higher layers, never the reverse.

---

## E2E Tests vs Unit Tests

Understanding the difference is critical:

| Aspect | Unit Tests | E2E Contract Tests |
|--------|------------|-------------------|
| **What you control** | Everything (mocks, inputs, outputs) | Only inputs (seed data, API calls) |
| **System under test** | Isolated function/class | Running deployed services |
| **When test fails** | Your code is wrong | Something doesn't match the contract |
| **What to fix** | The code you wrote | Investigate first, then fix the right layer |

### The MCP Fixture Reality

In our E2E tests, `plantation_mcp` and `collection_mcp` fixtures are **real gRPC clients** connecting to **real running services**:

```python
# This is NOT a mock - it's calling the actual MCP server!
result = await plantation_mcp.call_tool("get_factory", {"factory_id": "FAC-E2E-001"})
```

When this test fails, the MCP server returned something unexpected. The question is: **why?**

---

## Direction of Truth Flow

```
CORRECT MENTAL MODEL:
══════════════════════════════════════════════════════════════

Proto Schema ────defines────► Production Code ────► Tests VERIFY
     │                              │
     │                              │
     └──────► Seed Data ───exercises─┘
              (must match proto)

══════════════════════════════════════════════════════════════

WRONG MENTAL MODEL (Anti-Pattern):
══════════════════════════════════════════════════════════════

Tests ────"require"────► Production Code (modified to pass)
                              ▲
Seed Data ────"require"───────┘ (modified to accept)

══════════════════════════════════════════════════════════════
```

**Never modify production code to make tests pass.**
**Never modify production code to accept incorrect seed data.**

---

## When a Test Fails: The Debugging Checklist

When you see a RED test, follow this checklist **IN ORDER**:

### Step 1: Check Seed Data Against Proto

```bash
# Look at what the proto expects
cat proto/plantation/v1/plantation.proto | grep -A 20 "message Factory"

# Compare with seed data
cat tests/e2e/infrastructure/seed/factories.json
```

**Ask:** Does my seed data have the correct field names and structure per the proto?

**If seed is wrong:** Fix the seed file, not production code.

### Step 2: Check Production Code Against Proto

```bash
# Look at the _to_dict method in the client
cat mcp-servers/plantation-mcp/src/plantation_mcp/infrastructure/plantation_client.py
```

**Ask:** Does the client code reference fields that actually exist in the proto?

**If client is wrong:** This is a real bug in production code. Fix it, but document WHY.

### Step 3: Check Test Assertions

```python
# Is the test checking for the right field names?
assert "factory_id" in result  # Correct per proto?
```

**Ask:** Is my assertion matching what the proto and production actually return?

**If assertion is wrong:** Fix the test assertion.

### Step 4: Check Service State

```bash
# Is the service actually running and healthy?
curl http://localhost:8001/health

# Is seed data loaded?
docker exec e2e-mongodb mongosh --eval "db.factories.find()"
```

**Ask:** Is the infrastructure in the expected state?

---

## Common Anti-Patterns (DO NOT DO)

### Anti-Pattern 1: Modifying Production to Match Tests

```python
# Test expects "deliveries" field
assert "deliveries" in result["today"]

# WRONG: Developer changes production code
# plantation_client.py:
result["today"]["deliveries"] = today.delivery_count  # Renamed to pass test!
```

**Why it's wrong:** If the proto has `delivery_count`, changing client to return `deliveries` breaks the contract.

**Correct approach:** Check if proto has `deliveries` or `delivery_count`, then fix the appropriate layer.

### Anti-Pattern 2: Modifying Production to Accept Bad Seed

```json
// Seed file has typo
{ "factory_idd": "FAC-001" }
```

```python
# WRONG: Developer changes production to accept typo
def parse_factory(data):
    factory_id = data.get("factory_idd") or data.get("factory_id")  # Accommodating typo!
```

**Why it's wrong:** Production code should not accommodate test data errors.

**Correct approach:** Fix the seed file: `"factory_id": "FAC-001"`

### Anti-Pattern 3: Declaring "Done" Without Running Tests

```bash
# Developer workflow
git add .
git commit -m "Implement story 0.4.2"
# Never ran: pytest tests/e2e/scenarios/test_01_plantation_mcp_contracts.py
```

**Why it's wrong:** E2E tests ARE the acceptance criteria. If you haven't run them, you haven't verified the story.

**Correct approach:** Always run tests before marking done:
```bash
PYTHONPATH="${PYTHONPATH}:." pytest tests/e2e/scenarios/test_01_plantation_mcp_contracts.py -v
```

---

## Decision Tree: What to Fix

```
Test Failed
    │
    ▼
Does seed data match proto schema?
    │
    ├── NO ──► Fix seed data
    │
    └── YES
          │
          ▼
     Does production code match proto?
          │
          ├── NO ──► Fix production code (this is a real bug!)
          │          Document: "Fixed bug: client referenced non-existent field"
          │
          └── YES
                │
                ▼
           Is test assertion correct?
                │
                ├── NO ──► Fix test assertion
                │
                └── YES ──► Investigate service state/infrastructure
```

---

## Examples

### Example 1: Seed Data Error

**Symptom:** `test_get_factory` fails with "factory not found"

**Investigation:**
```json
// seed/factories.json
{ "id": "FAC-E2E-001", "name": "Test Factory" }
```

```protobuf
// Proto expects
message Factory {
  string factory_id = 1;  // Not "id"!
}
```

**Diagnosis:** Seed uses `id`, proto uses `factory_id`

**Fix:** Update seed file:
```json
{ "factory_id": "FAC-E2E-001", "name": "Test Factory" }
```

### Example 2: Production Bug (Real Bug Found by Test)

**Symptom:** `test_get_farmer_summary` returns wrong field names

**Investigation:**
```python
# plantation_client.py (old)
result["historical"] = {
    "avg_grade": hist.avg_grade,  # This field doesn't exist in proto!
}
```

```protobuf
// Proto has
message HistoricalMetrics {
  double primary_percentage_30d = 7;
  // No "avg_grade" field!
}
```

**Diagnosis:** Production code references `avg_grade` which doesn't exist in proto. This is a pre-existing bug.

**Fix:** Update production code to match proto:
```python
result["historical"] = {
    "primary_percentage_30d": hist.primary_percentage_30d,
}
```

**Note:** This is a legitimate production fix, not "changing code to pass tests."

### Example 3: Test Assertion Error

**Symptom:** Test fails checking for wrong field

**Investigation:**
```python
# Test checks for "delivery_count"
assert "delivery_count" in result["today"]
```

```protobuf
// Proto has
message TodayMetrics {
  int32 deliveries = 1;  // Called "deliveries", not "delivery_count"
}
```

**Diagnosis:** Test assertion uses wrong field name

**Fix:** Update test:
```python
assert "deliveries" in result["today"]
```

---

## Production Code Change Log (MANDATORY)

If you modify ANY production code while working on E2E tests, you MUST document it using this format. Add this to your PR description or commit message:

### What Counts as "Production Code"?

| Category | Examples | Must Document? |
|----------|----------|----------------|
| Service code | `services/*/src/*.py` | YES |
| MCP server code | `mcp-servers/*/src/*.py` | YES |
| Shared libraries | `libs/*/src/*.py` | YES |
| Proto definitions | `proto/*/*.proto` | YES |
| **Infrastructure** | Mock servers, docker-compose changes, env vars | YES |
| Seed data | `tests/e2e/infrastructure/seed/*.json` | YES (separate section) |
| Test scenarios | `tests/e2e/scenarios/*.py` | NO (unless behavior change) |

**Key insight:** If a change affects how production services BEHAVE (even via configuration), document it.

```markdown
## Production Code Changes

### Change 1: [filename] - [brief description]
- **File:** [full path with line numbers]
- **What changed:** [describe the specific change]
- **Why:** [explain why original code was wrong]
- **Evidence:** [proto line, API response, or other proof]
- **Type:** [Bug fix | Schema alignment | New feature]
```

### Example:

```markdown
## Production Code Changes

### Change 1: plantation_client.py - FarmerSummary field names
- **File:** mcp-servers/plantation-mcp/src/plantation_mcp/infrastructure/plantation_client.py:301-321
- **What changed:** Renamed `avg_grade` → `primary_percentage_30d`, `delivery_count` → `deliveries`
- **Why:** Proto defines these fields with different names; old code referenced non-existent fields
- **Evidence:** proto/plantation/v1/plantation.proto:667-688 shows correct field names
- **Type:** Bug fix (proto-client misalignment)
```

### Rules:

1. **No documentation = No merge** - PR cannot be approved without this log
2. **"To pass tests" is NOT a valid reason** - You must explain the root cause
3. **Reference the source of truth** - Proto line numbers, API specs, etc.
4. **If you can't fill this out, STOP** - You may not understand what you're changing

---

## Unit Test Change Log (MANDATORY)

If you modify ANY unit test behavior (not just E2E tests), you MUST document it:

```markdown
## Unit Test Changes

| Test File | Test Name Before | Test Name After | Behavior Change | Justification |
|-----------|------------------|-----------------|-----------------|---------------|
| test_json_extraction.py | test_process_missing_ai_agent_id | test_process_direct_extraction_without_ai_agent | Expected FAILURE → Expected SUCCESS | AC1 specifies ai_agent_id:null is valid (Story 0.4.5 line 15) |
```

### Rules:

1. **Changing "expect failure" to "expect success" REQUIRES justification**
2. **Reference the AC, proto, or requirement** that proves the new behavior is correct
3. **If you can't justify, the original test was probably right** - investigate more
4. **Renaming tests is fine** - but behavior changes need explanation

### Red Flags (Stop and Think):

- You're changing `assert result.success is False` to `assert result.success is True`
- You're removing error assertions
- You're changing expected exceptions
- You're lowering test coverage

These changes might be legitimate, but they REQUIRE documentation explaining WHY.

---

## Commit Discipline (MANDATORY)

Commits must be **atomic by type**. Never mix these in one commit:

| Commit Type | Prefix | Contains |
|-------------|--------|----------|
| Production fix | `fix(service):` | Only production code (`services/*/src/`) |
| Test infrastructure | `feat(e2e):` | Only test infra/seed (`tests/e2e/infrastructure/`) |
| Test scenarios | `test(e2e):` | Only test scenarios (`tests/e2e/scenarios/`) |
| Unit test change | `test(unit):` | Only unit test files (`tests/unit/`) |
| Documentation | `docs:` | Only docs/story files |

### Anti-Pattern (DO NOT DO):

```bash
# WRONG - mixes production + test + seed in one commit
git commit -m "fix(collection): support direct JSON extraction"
# Files: json_extraction.py, test_json_extraction.py, source_configs.json
```

### Correct Pattern:

```bash
# Commit 1: Production code only
git commit -m "fix(collection): support ai_agent_id null in json_extraction.py

Relates to #30

When ai_agent_id is null, extract fields directly from JSON without AI.
Per TransformationConfig model, ai_agent_id is Optional[str].
"

# Commit 2: Unit test update (with justification)
git commit -m "test(unit): update test to expect success for direct extraction

Relates to #30

Renamed: test_process_missing_ai_agent_id → test_process_direct_extraction_without_ai_agent
Behavior: Expected FAILURE → Expected SUCCESS
Justification: Story 0.4.5 AC1 specifies ai_agent_id:null for direct extraction
"

# Commit 3: Seed data
git commit -m "chore(seed): add e2e-qc-direct-json source config

Relates to #30
"
```

### Why Atomic Commits Matter:

1. **Easier to review** - Each commit has one purpose
2. **Easier to revert** - Can undo production change without losing tests
3. **Clearer history** - `git log --oneline` tells the story
4. **Audit trail** - Can see exactly what production code changed

---

## Local Test Run Evidence (MANDATORY for E2E Stories)

Before ANY push, you must have evidence of local test runs in your story file:

```markdown
### Local Test Run Evidence

**First run timestamp:** 2025-12-30 10:30:00
**Docker stack status:**
```
# Output of: docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps
NAME                  STATUS
mongodb               running (healthy)
redis                 running (healthy)
plantation-model      running (healthy)
collection-model      running (healthy)
...
```

**Test run output:**
```
# Output of: pytest tests/e2e/scenarios/test_04_*.py -v
========================= test session starts =========================
tests/e2e/scenarios/test_04_quality_blob_ingestion.py::TestQualityBlobIngestion::test_01_blob_upload PASSED
tests/e2e/scenarios/test_04_quality_blob_ingestion.py::TestQualityBlobIngestion::test_02_blob_event_trigger PASSED
...
========================= 6 passed in 12.34s =========================
```

**If tests failed before passing, explain what you fixed:**

| Attempt | Failure | Root Cause | Fix Applied | Layer Fixed |
|---------|---------|------------|-------------|-------------|
| 1 | Source config not found | Missing seed data | Added e2e-qc-direct-json to source_configs.json | Seed Data |
| 2 | ContentSettings error | Azure SDK requires object | Fixed blob_storage.py import | Production (Bug) |
```

### Why This Matters:

1. **Proves you tested locally** - Not just hoping CI will catch issues
2. **Documents debugging journey** - Future devs understand what was tried
3. **Prevents CI spam** - No more 4+ pushes to fix obvious issues
4. **Builds trust** - User can see actual test output, not just claims

---

## Before You Start: Validate Seed Data

**Always validate seed data before starting Docker:**

```bash
PYTHONPATH="${PYTHONPATH}:services/plantation-model/src" python tests/e2e/infrastructure/validate_seed_data.py
```

This catches schema errors in seconds instead of minutes (after Docker startup). If validation fails, fix the seed data before proceeding.

---

## Pre-Push Blocking Checklist

**STOP. Before running `git push`, complete ALL items below.**

### Gate 1: Local Validation (no Docker needed)
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] `python tests/e2e/infrastructure/validate_seed_data.py` passes

### Gate 2: Docker E2E (MANDATORY for any E2E story)
- [ ] Docker stack is running: `docker compose ps` shows all healthy
- [ ] E2E tests pass locally: Paste test output in "Local Test Run Evidence" section of story
- [ ] I understand WHY tests pass, not just THAT they pass

### Gate 3: Change Documentation
- [ ] If production code changed: Filled "Production Code Changes" table with evidence
- [ ] If unit test changed: Filled "Unit Test Changes" table with justification
- [ ] If seed data changed: Verified it matches proto schema

### Gate 4: Commit Hygiene
- [ ] Commits are atomic by type (not mixing production + test + seed)
- [ ] Each commit message references GitHub issue (e.g., "Relates to #30")

**Only after ALL gates pass: `git push`**

---

## Quick Reference: File Locations

| What | Where |
|------|-------|
| Proto definitions | `proto/*/v1/*.proto` |
| Plantation MCP client | `mcp-servers/plantation-mcp/src/plantation_mcp/infrastructure/plantation_client.py` |
| Collection MCP client | `mcp-servers/collection-mcp/src/collection_mcp/infrastructure/collection_client.py` |
| Seed data | `tests/e2e/infrastructure/seed/` |
| E2E test fixtures | `tests/e2e/conftest.py` |
| E2E test scenarios | `tests/e2e/scenarios/` |

---

## Summary

1. **Proto is the contract** - It defines what's correct
2. **Production implements the contract** - Should match proto exactly
3. **Seed data exercises production** - Must conform to proto schema
4. **Tests verify behavior** - Assertions should match proto expectations
5. **When tests fail, investigate** - Use the debugging checklist
6. **Fix the right layer** - Never modify production to accommodate test errors

**Remember:** The test exposed a problem. Your job is to find WHERE the problem is, not to make the test pass by any means necessary.
