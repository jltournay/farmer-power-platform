# Story 0.6.4: gRPC Client Retry - IterationResolver

**Status:** Review
**GitHub Issue:** [#47](https://github.com/jltournay/farmer-power-platform/issues/47)
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADR:** [ADR-005: gRPC Client Retry and Reconnection Strategy](../architecture/adr/ADR-005-grpc-client-retry-strategy.md)
**Story Points:** 2

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - Story is NOT done until ALL these steps are completed!**

### 1. Same Pattern as Story 0.6.3

This story applies the EXACT same pattern as Story 0.6.3 (AiModelClient) to IterationResolver.

**Reference implementation:**
- Story 0.6.3: AiModelClient (do this first)
- PlantationClient: `mcp-servers/plantation-mcp/src/plantation_mcp/plantation_client.py`

### 2. CI Verification

```bash
git push origin story/0-6-4-grpc-retry-iteration-resolver
gh run list --branch story/0-6-4-grpc-retry-iteration-resolver --limit 3
```

### 3. Definition of Done Checklist

- [x] **Singleton channel** - IterationResolver uses lazy singleton pattern
- [x] **Retry decorator** - ALL RPC methods have `@retry` decorator
- [x] **Unit tests pass** - 24 passed, 1 skipped in tests/unit/collection/test_iteration_resolver.py
- [x] **E2E tests pass** - 71 passed, 3 xfailed (no regressions)
- [x] **Lint passes** - `ruff check . && ruff format --check .`

---

## Story

As a **platform engineer**,
I want IterationResolver to auto-recover from gRPC connection failures,
So that transient network issues don't require pod restarts.

## Acceptance Criteria

1. **AC1: Current State (Anti-pattern)** - Given IterationResolver has no retry logic, When I review `services/collection-model/src/collection_model/infrastructure/iteration_resolver.py`, Then it uses per-request channel creation (anti-pattern)

2. **AC2: Singleton Channel Pattern** - Given IterationResolver is refactored, When I check the updated implementation, Then it uses singleton channel pattern with lazy initialization And all RPC methods have `@retry` decorator from Tenacity And retry config matches AiModelClient (3 attempts, exponential 1-10s)

3. **AC3: Auto-recovery Works** - Given the gRPC connection is lost, When the next RPC method is called, Then the retry decorator catches the error And reconnection is attempted automatically

## Tasks / Subtasks

- [ ] **Task 1: Analyze Current Implementation** (AC: 1)
  - [ ] Read `services/collection-model/src/collection_model/infrastructure/iteration_resolver.py`
  - [ ] Document current anti-patterns
  - [ ] Identify all RPC methods that need retry decorator

- [ ] **Task 2: Implement Singleton Channel** (AC: 2)
  - [ ] Add `_channel: grpc.aio.Channel | None = None` attribute
  - [ ] Add `_stub: IterationServiceStub | None = None` attribute
  - [ ] Create `async def _get_stub(self)` method
  - [ ] Configure keepalive options (same as AiModelClient)

- [ ] **Task 3: Add Tenacity Retry to All Methods** (AC: 2, 3)
  - [ ] Apply same retry decorator pattern as Story 0.6.3
  - [ ] Add channel reset on UNAVAILABLE error

- [ ] **Task 4: Create Unit Tests** (AC: All)
  - [ ] Create `tests/unit/collection_model/infrastructure/test_iteration_resolver.py`
  - [ ] Test singleton channel reuse
  - [ ] Test retry on UNAVAILABLE
  - [ ] Test retry exhaustion

- [ ] **Task 5: Verify Integration** (AC: 3)
  - [ ] Run unit tests
  - [ ] Run E2E suite

## Git Workflow (MANDATORY)

### Story Start
- [ ] GitHub Issue created
- [ ] Feature branch created:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-6-4-grpc-retry-iteration-resolver
  ```

**Branch name:** `story/0-6-4-grpc-retry-iteration-resolver`

---

## Unit Tests Required

### New Tests to Create

```python
# tests/unit/collection_model/infrastructure/test_iteration_resolver.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import grpc.aio

from collection_model.infrastructure.iteration_resolver import IterationResolver


class TestIterationResolverSingletonChannel:
    """Tests for singleton channel pattern."""

    @pytest.mark.asyncio
    async def test_singleton_channel_reused(self):
        """Same channel is reused across multiple calls."""
        resolver = IterationResolver()

        # First call creates channel
        stub1 = await resolver._get_stub()
        channel1 = resolver._channel

        # Second call reuses channel
        stub2 = await resolver._get_stub()
        channel2 = resolver._channel

        assert channel1 is channel2
        assert stub1 is stub2

    @pytest.mark.asyncio
    async def test_lazy_channel_initialization(self):
        """Channel is not created until first use."""
        resolver = IterationResolver()
        assert resolver._channel is None
        assert resolver._stub is None


class TestIterationResolverRetry:
    """Tests for retry behavior."""

    @pytest.mark.asyncio
    async def test_retry_on_unavailable(self):
        """Retry triggers on UNAVAILABLE status code."""
        resolver = IterationResolver()

        mock_stub = AsyncMock()
        call_count = 0

        async def failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise grpc.aio.AioRpcError(
                    grpc.StatusCode.UNAVAILABLE,
                    "Connection refused"
                )
            return MagicMock()

        mock_stub.ResolveIteration = failing_then_succeeding

        with patch.object(resolver, '_get_stub', return_value=mock_stub):
            await resolver.resolve_iteration(...)

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self):
        """Error raised after max retries exhausted."""
        resolver = IterationResolver()

        mock_stub = AsyncMock()
        mock_stub.ResolveIteration.side_effect = grpc.aio.AioRpcError(
            grpc.StatusCode.UNAVAILABLE,
            "Connection refused"
        )

        with patch.object(resolver, '_get_stub', return_value=mock_stub):
            with pytest.raises(grpc.aio.AioRpcError):
                await resolver.resolve_iteration(...)

        assert mock_stub.ResolveIteration.call_count == 3
```

---

## E2E Test Impact

### Expected Behavior
- **No breaking changes** - IterationResolver API unchanged
- **Improved resilience** - Transient failures auto-recovered

### Verification
After implementation, existing E2E tests should pass. The IterationResolver is used in document processing pipelines.

---

## Implementation Reference

### Required Pattern (same as Story 0.6.3)

```python
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
import grpc.aio

class IterationResolver:
    """Iteration resolver gRPC client with retry and singleton channel."""

    def __init__(self, target: str | None = None) -> None:
        self._target = target or os.getenv("ITERATION_GRPC_ADDRESS", "localhost:50051")
        self._channel: grpc.aio.Channel | None = None
        self._stub: IterationServiceStub | None = None

    async def _get_stub(self) -> IterationServiceStub:
        """Lazy singleton channel - created once, reused."""
        if self._stub is None:
            if self._channel is None:
                self._channel = grpc.aio.insecure_channel(
                    self._target,
                    options=[
                        ("grpc.keepalive_time_ms", 30000),
                        ("grpc.keepalive_timeout_ms", 10000),
                    ]
                )
            self._stub = IterationServiceStub(self._channel)
        return self._stub

    def _reset_channel(self) -> None:
        """Reset channel on connection error."""
        self._channel = None
        self._stub = None

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def resolve_iteration(self, document_id: str) -> IterationResult:
        """Resolve iteration with retry on transient errors."""
        stub = await self._get_stub()
        try:
            request = ResolveRequest(document_id=document_id)
            response = await stub.ResolveIteration(request)
            return response
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                self._reset_channel()
            raise

    async def close(self) -> None:
        """Clean up resources."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
```

---

## Local Test Run Evidence (MANDATORY)

**1. Unit Tests:**
```bash
pytest tests/unit/collection/test_iteration_resolver.py -v
```
**Output:**
```
tests/unit/collection/test_iteration_resolver.py::TestIterationResolver::test_resolve_returns_items_from_mcp_tool PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolver::test_resolve_calls_correct_mcp_tool PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolver::test_resolve_passes_tool_arguments PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolver::test_resolve_handles_nested_result SKIPPED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolver::test_resolve_raises_on_tool_not_found PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolver::test_resolve_raises_on_mcp_failure PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolver::test_resolve_raises_on_connection_error PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolver::test_resolve_returns_empty_list_for_no_results PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverLinkageExtraction::test_extract_linkage_fields PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverLinkageExtraction::test_extract_linkage_handles_missing_fields PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverLinkageExtraction::test_extract_linkage_empty_fields PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverLinkageExtraction::test_extract_linkage_none_fields PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverSingletonChannel::test_lazy_channel_initialization PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverSingletonChannel::test_singleton_channel_reused PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverSingletonChannel::test_channel_created_with_keepalive_options PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverRetry::test_retry_on_unavailable PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverRetry::test_retry_exhausted_raises_service_unavailable PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverChannelRecreation::test_reset_channel_clears_state PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverChannelRecreation::test_channel_recreation_after_reset PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverChannelRecreation::test_channel_reset_on_unavailable_error PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverNoRetryOnNonTransient::test_no_channel_reset_on_not_found PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverClose::test_close_cleans_up_channel PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverClose::test_close_is_idempotent PASSED
tests/unit/collection/test_iteration_resolver.py::TestIterationResolverMetadata::test_get_metadata_returns_app_id PASSED
tests/unit/collection/test_iteration_resolver.py::TestServiceUnavailableError::test_error_includes_context PASSED

================== 24 passed, 1 skipped in 12.57s ==================
```

**2. E2E Tests Pass:**
```bash
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
```
**Output:**
```
tests/e2e/scenarios/test_00_infrastructure_verification.py: 19 passed
tests/e2e/scenarios/test_01_plantation_mcp_contracts.py: 12 passed
tests/e2e/scenarios/test_02_collection_mcp_contracts.py: 12 passed
tests/e2e/scenarios/test_03_factory_farmer_flow.py: 5 passed
tests/e2e/scenarios/test_04_quality_blob_ingestion.py: 6 passed
tests/e2e/scenarios/test_05_weather_ingestion.py: 7 passed
tests/e2e/scenarios/test_06_cross_model_events.py: 5 passed
tests/e2e/scenarios/test_07_grading_validation.py: 3 passed, 3 xfailed

=================== 71 passed, 3 xfailed in 98.18s (0:01:38) ===================
```

**3. Lint Check:**
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [x] Yes / [ ] No

**4. E2E CI Verification:**
```bash
gh workflow run "E2E Tests" --ref story/0-6-4-grpc-retry-iteration-resolver
gh run list --workflow="E2E Tests" --branch story/0-6-4-grpc-retry-iteration-resolver --limit 1
```
**Output:**
```
completed  success  E2E Tests  E2E Tests  story/0-6-4-grpc-retry-iteration-resolver  workflow_dispatch  20642591862  4m2s  2026-01-01T17:24:13Z
```
**E2E CI passed:** [x] Yes / [ ] No

**5. Regular CI Verification:**
```bash
gh run list --branch story/0-6-4-grpc-retry-iteration-resolver --limit 1
```
**Output:**
```
completed  success  Story 0.6.4: gRPC Client Retry - IterationResolver  CI  story/0-6-4-grpc-retry-iteration-resolver  pull_request  20642590824  2m1s
```
**Regular CI passed:** [x] Yes / [ ] No

---

## Implementation Notes

### gRPC Call Timeout (Fix for E2E CI)

Initial E2E CI runs failed with `httpx.ReadTimeout` on `test_get_documents_returns_weather_document`. Root cause: the gRPC call in `_resolve_with_retry` had no timeout, causing it to hang indefinitely in Docker/CI environment when connection issues occurred.

**Fix applied:** Added `timeout=15.0` to the gRPC call:
```python
response = await stub.CallTool(request, metadata=metadata, timeout=15.0)
```

This ensures the retry mechanism can kick in instead of blocking until the HTTP timeout (30s) is reached.

### Docker Image Rebuild Verification

**IMPORTANT:** When testing E2E locally, always use `--no-cache` to ensure Docker images contain latest code:

```bash
# Force rebuild (not cached)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml build --no-cache collection-model

# Verify fix is in image
docker run --rm infrastructure-collection-model grep -n "timeout=15" /app/src/collection_model/infrastructure/iteration_resolver.py
# Output: 243:            response = await stub.CallTool(request, metadata=metadata, timeout=15.0)
```

**Verified:** [x] Docker image contains timeout fix at line 243

---

## E2E Test Strategy (Mental Model Alignment)

> **Reference:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Direction of Change

This story **improves resilience** of existing gRPC client. Same pattern as Story 0.6.3.

| Aspect | Impact |
|--------|--------|
| Proto definitions | **UNCHANGED** |
| Client API | **UNCHANGED** - Same method signatures |
| Production behavior | **IMPROVED** - Transient failures auto-recover |
| E2E tests | **MUST PASS WITHOUT MODIFICATION** |

### Existing E2E Tests

**ALL existing E2E tests MUST pass unchanged.** The IterationResolver's external behavior is identical.

### New E2E Tests Needed

**None.** Same reasoning as Story 0.6.3 - validated by unit tests and PoC.

### If Existing Tests Fail

Same debugging approach as Story 0.6.3. Check retry configuration if timeouts occur.

---

## References

- [ADR-005: gRPC Client Retry Strategy](../architecture/adr/ADR-005-grpc-client-retry-strategy.md)
- [Story 0.6.3: AiModelClient Retry](./0-6-3-grpc-retry-ai-model-client.md)
- [Reference: PlantationClient](../../../mcp-servers/plantation-mcp/src/plantation_mcp/plantation_client.py)
