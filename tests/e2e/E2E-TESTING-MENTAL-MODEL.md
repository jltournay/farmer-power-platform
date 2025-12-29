# E2E Testing Mental Model

**Required reading for all developers working on E2E tests.**

This document explains the conceptual framework for understanding E2E contract tests, the hierarchy of truth, and how to debug failures correctly.

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

## Before You Start: Validate Seed Data

**Always validate seed data before starting Docker:**

```bash
PYTHONPATH="${PYTHONPATH}:services/plantation-model/src" python tests/e2e/infrastructure/validate_seed_data.py
```

This catches schema errors in seconds instead of minutes (after Docker startup). If validation fails, fix the seed data before proceeding.

---

## Before You Push: Checklist

- [ ] I validated seed data with `validate_seed_data.py`
- [ ] I ran the E2E tests locally and they pass
- [ ] If I modified production code:
  - [ ] I documented each change in the Production Code Change Log format
  - [ ] I can explain WHY the original code was wrong (with evidence)
  - [ ] The change fixes a real bug, not just "makes tests pass"
- [ ] If I modified seed data, it now matches the expected schema
- [ ] I understand WHY my tests pass, not just THAT they pass
- [ ] CI is green (check with `gh run list --limit 1`)

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
