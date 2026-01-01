# Story 0.6.7: DAPR Resiliency Configuration

**Status:** To Do
**GitHub Issue:** TBD
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADR:** [ADR-006: Event Delivery and Dead Letter Queue](../architecture/adr/ADR-006-event-delivery-dead-letter-queue.md)
**Story Points:** 2
**Wave:** 2 (DAPR SDK Migration)
**Prerequisite:** None (can be done in parallel with 0.6.5/0.6.6)

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - This is YAML configuration, NOT code!**

### 1. Configuration Only

This story creates DAPR component configuration. No Python code changes.

### 2. Validated by PoC

The resiliency behavior is validated by `tests/e2e/poc-dapr-patterns/`:
- `test_pubsub_retry` - Verifies retry behavior
- `test_pubsub_dlq` - Verifies DLQ after retries exhausted

### 3. Definition of Done Checklist

- [ ] **Resiliency file created** - `deploy/dapr/components/resiliency.yaml`
- [ ] **Retry policy configured** - 3 retries, exponential backoff
- [ ] **Targets pubsub component** - Applied to all pub/sub operations
- [ ] **PoC tests pass** - Retry and DLQ tests green
- [ ] **E2E tests pass** - No regressions

---

## Story

As a **platform engineer**,
I want DAPR resiliency policies configured for pub/sub,
So that events are retried with exponential backoff before dead-lettering.

## Acceptance Criteria

1. **AC1: No Resiliency Exists** - Given no resiliency policy exists, When I check `deploy/dapr/components/`, Then there is no `resiliency.yaml` file

2. **AC2: Resiliency Policy Created** - Given the resiliency policy is created, When I check the configuration, Then `resiliency.yaml` defines maxRetries: 3, policy: exponential, duration: 1s, maxInterval: 30s And it targets the `pubsub` component

3. **AC3: Retry Behavior Works** - Given an event handler returns `TopicEventResponse("retry")`, When DAPR processes the retry, Then it follows the exponential backoff policy And after 3 failures, the event goes to DLQ

## Tasks / Subtasks

- [ ] **Task 1: Create Resiliency Configuration** (AC: 1, 2)
  - [ ] Create `deploy/dapr/components/resiliency.yaml`
  - [ ] Define retry policy with exponential backoff
  - [ ] Target pubsub component for inbound operations

- [ ] **Task 2: Update Docker Compose** (AC: 2)
  - [ ] Ensure DAPR sidecars load resiliency configuration
  - [ ] Update component path if needed

- [ ] **Task 3: Update E2E Infrastructure** (AC: 2)
  - [ ] Copy resiliency.yaml to E2E components directory
  - [ ] Verify E2E docker-compose loads it

- [ ] **Task 4: Verify Behavior** (AC: 3)
  - [ ] Run PoC retry test
  - [ ] Verify retry timing follows policy
  - [ ] Verify DLQ receives after 3 failures

## Git Workflow (MANDATORY)

**Branch name:** `story/0-6-7-dapr-resiliency-config`

---

## Implementation

### Resiliency Configuration

```yaml
# deploy/dapr/components/resiliency.yaml
apiVersion: dapr.io/v1alpha1
kind: Resiliency
metadata:
  name: pubsub-resiliency
spec:
  policies:
    retries:
      eventRetry:
        policy: exponential
        maxRetries: 3
        duration: 1s
        maxInterval: 30s

  targets:
    components:
      pubsub:
        inbound:
          retry: eventRetry
```

### Configuration Explained

| Field | Value | Purpose |
|-------|-------|---------|
| `policy` | `exponential` | Backoff increases exponentially |
| `maxRetries` | `3` | Maximum 3 retry attempts |
| `duration` | `1s` | Initial wait between retries |
| `maxInterval` | `30s` | Maximum wait between retries |

### Retry Timing

| Attempt | Wait Before | Cumulative Time |
|---------|-------------|-----------------|
| 1st retry | 1s | 1s |
| 2nd retry | 2s | 3s |
| 3rd retry | 4s | 7s |
| DLQ | - | After 3rd failure |

---

## Files to Create/Modify

| Action | File | Change |
|--------|------|--------|
| CREATE | `deploy/dapr/components/resiliency.yaml` | Resiliency configuration |
| MODIFY | `tests/e2e/infrastructure/dapr/components/` | Copy resiliency.yaml |

---

## Unit Tests Required

N/A - This is YAML configuration. Validated by E2E/PoC tests.

---

## E2E Test Impact

### PoC Validation

```bash
cd tests/e2e/poc-dapr-patterns
docker compose up --build -d
python run_tests.py --test retry  # Should pass
python run_tests.py --test dlq    # Should pass
docker compose down -v
```

### Expected Behavior

After configuration:
1. Events that fail with `TopicEventResponse("retry")` are retried 3 times
2. Retry timing follows exponential backoff (1s, 2s, 4s)
3. After 3 failures, event goes to DLQ topic
4. `TopicEventResponse("drop")` goes to DLQ immediately (no retry)

---

## Local Test Run Evidence (MANDATORY)

**1. PoC Retry Test:**
```bash
cd tests/e2e/poc-dapr-patterns
python run_tests.py --test retry
```
**Output:** (paste here)

**2. PoC DLQ Test:**
```bash
python run_tests.py --test dlq
```
**Output:** (paste here)

**3. Full E2E Suite:**
```bash
pytest tests/e2e/scenarios/ -v
```
**Output:** (paste here - no regressions)

---

## E2E Test Strategy (Mental Model Alignment)

> **Reference:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Direction of Change

This story is **YAML configuration only** - no production code changes.

| Aspect | Impact |
|--------|--------|
| Proto definitions | **UNCHANGED** |
| Production code | **UNCHANGED** - This is DAPR configuration |
| Event behavior | **IMPROVED** - Retry policy now defined |
| E2E tests | **MUST PASS WITHOUT MODIFICATION** |

### Existing E2E Tests

**ALL existing E2E tests MUST pass unchanged.** The resiliency config improves reliability but doesn't change happy-path behavior.

### New E2E Tests Needed

**None.** Resiliency behavior is validated by PoC tests:
- `test_pubsub_retry` - Verifies retry on transient failure
- `test_pubsub_dlq` - Verifies DLQ after retries exhausted

### If Existing Tests Fail

```
Test Failed
    │
    ▼
Is failure related to resiliency config?
    │
    ├── YES (retry delays, DLQ routing) ──► Check YAML syntax
    │                                        Verify DAPR loaded config
    │
    └── NO (unrelated failure) ──► Investigate per Mental Model
```

---

## References

- [ADR-006: Event Delivery and DLQ](../architecture/adr/ADR-006-event-delivery-dead-letter-queue.md)
- [DAPR Resiliency Policies](https://docs.dapr.io/operations/resiliency/policies/)
- [PoC: DAPR Patterns](../../../tests/e2e/poc-dapr-patterns/)
