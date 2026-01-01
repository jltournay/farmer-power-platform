# Story 0.6.3: gRPC Client Retry - AiModelClient

**Status:** review
**GitHub Issue:** #45
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADR:** [ADR-005: gRPC Client Retry and Reconnection Strategy](../architecture/adr/ADR-005-grpc-client-retry-strategy.md)
**Story Points:** 2

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - Story is NOT done until ALL these steps are completed!**

### 1. Pattern Already Validated

This pattern is validated by the PoC at `tests/e2e/poc-dapr-patterns/`. The resilience test proves:
- gRPC connections auto-recover after server restart
- Tenacity retry decorator works correctly

**Reference implementation:** `mcp-servers/plantation-mcp/src/plantation_mcp/plantation_client.py`

### 2. CI and PoC Verification

```bash
# Run PoC resilience test first
cd tests/e2e/poc-dapr-patterns
docker compose up --build -d
python run_tests.py --test resilience
docker compose down -v

# Then CI on branch
git push origin story/0-6-3-grpc-retry-ai-model-client
gh run list --branch story/0-6-3-grpc-retry-ai-model-client --limit 3
```

### 3. Definition of Done Checklist

- [x] **Singleton channel** - AiModelClient uses lazy singleton pattern
- [x] **Retry decorator** - ALL RPC methods have `@retry` decorator
- [x] **Unit tests pass** - New tests in tests/unit/collection_model/infrastructure/
- [x] **PoC test passes** - Resilience test still green
- [x] **E2E tests pass** - No regressions
- [x] **Lint passes** - `ruff check . && ruff format --check .`

---

## Story

As a **platform engineer**,
I want AiModelClient to auto-recover from gRPC connection failures,
So that transient network issues don't require pod restarts.

## Acceptance Criteria

1. **AC1: Current State (Anti-pattern)** - Given AiModelClient has no retry logic, When I review `services/collection-model/src/collection_model/infrastructure/ai_model_client.py`, Then it uses per-request channel creation (anti-pattern)

2. **AC2: Singleton Channel Pattern** - Given AiModelClient is refactored, When I check the updated implementation, Then it uses singleton channel pattern with lazy initialization And all RPC methods have `@retry` decorator from Tenacity And retry config is: 3 attempts, exponential backoff (1-10s)

3. **AC3: Auto-recovery Works** - Given the gRPC connection is lost, When the next RPC method is called, Then the retry decorator catches the error And reconnection is attempted automatically And the call succeeds after reconnection

4. **AC4: Clear Error on Exhaustion** - Given all retries are exhausted, When the connection still fails, Then a clear error is raised with context (app_id, method, attempt count)

## Tasks / Subtasks

- [x] **Task 1: Analyze Current Implementation** (AC: 1) ✅
  - [x] Read `services/collection-model/src/collection_model/infrastructure/ai_model_client.py`
  - [x] Document current anti-patterns (per-request channel, no retry)
  - [x] Identify all RPC methods that need retry decorator: `extract()`, `health_check()`

- [x] **Task 2: Implement Singleton Channel** (AC: 2) ✅
  - [x] Add `_channel: grpc.aio.Channel | None = None` attribute
  - [x] Add `_stub: AiModelServiceStub | None = None` attribute
  - [x] Create `async def _get_stub(self) -> AiModelServiceStub` method
  - [x] Configure keepalive options:
    - `grpc.keepalive_time_ms`: 30000
    - `grpc.keepalive_timeout_ms`: 10000

- [x] **Task 3: Add Tenacity Retry to All Methods** (AC: 2, 3) ✅
  - [x] Tenacity dependency already present in `pyproject.toml`
  - [x] Create retry decorator (3 attempts, exponential backoff 1-10s)
  - [x] Applied to ALL RPC methods: `extract()`, `health_check()`
  - [x] Add channel reset on UNAVAILABLE error via `_reset_channel()`

- [x] **Task 4: Add Error Context** (AC: 4) ✅
  - [x] Created `ServiceUnavailableError` exception with context
  - [x] Include: app_id, method_name, attempt_count
  - [x] Log error with full context before raising

- [x] **Task 5: Create Unit Tests** (AC: All) ✅
  - [x] Created `tests/unit/collection_model/infrastructure/test_ai_model_client.py`
  - [x] 12 tests covering all acceptance criteria
  - [x] All 12 tests pass
  - [x] Full unit test suite (997 tests) passes

- [x] **Task 6: Verify Integration** (AC: 3) ✅
  - [x] Unit tests pass (997 tests)
  - [x] E2E tests pass (71 passed, 3 xfailed)
  - [x] Lint passes

## Git Workflow (MANDATORY)

### Story Start
- [ ] GitHub Issue created
- [ ] Feature branch created:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-6-3-grpc-retry-ai-model-client
  ```

**Branch name:** `story/0-6-3-grpc-retry-ai-model-client`

---

## Unit Tests Required

### New Tests to Create

```python
# tests/unit/collection_model/infrastructure/test_ai_model_client.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import grpc.aio

from collection_model.infrastructure.ai_model_client import AiModelClient


class TestAiModelClientSingletonChannel:
    """Tests for singleton channel pattern."""

    @pytest.mark.asyncio
    async def test_singleton_channel_reused(self):
        """Same channel is reused across multiple calls."""
        client = AiModelClient()

        # First call creates channel
        stub1 = await client._get_stub()
        channel1 = client._channel

        # Second call reuses channel
        stub2 = await client._get_stub()
        channel2 = client._channel

        assert channel1 is channel2
        assert stub1 is stub2

    @pytest.mark.asyncio
    async def test_lazy_channel_initialization(self):
        """Channel is not created until first use."""
        client = AiModelClient()
        assert client._channel is None
        assert client._stub is None

        await client._get_stub()

        assert client._channel is not None
        assert client._stub is not None


class TestAiModelClientRetry:
    """Tests for retry behavior."""

    @pytest.mark.asyncio
    async def test_retry_on_unavailable(self):
        """Retry triggers on UNAVAILABLE status code."""
        client = AiModelClient()

        # Mock stub to fail twice then succeed
        mock_stub = AsyncMock()
        call_count = 0

        async def failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                error = grpc.aio.AioRpcError(
                    grpc.StatusCode.UNAVAILABLE,
                    "Connection refused"
                )
                raise error
            return MagicMock()  # Success response

        mock_stub.SomeRpcMethod = failing_then_succeeding

        with patch.object(client, '_get_stub', return_value=mock_stub):
            # Should succeed after retries
            await client.some_rpc_method(...)

        assert call_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self):
        """Error raised after max retries exhausted."""
        client = AiModelClient()

        mock_stub = AsyncMock()
        mock_stub.SomeRpcMethod.side_effect = grpc.aio.AioRpcError(
            grpc.StatusCode.UNAVAILABLE,
            "Connection refused"
        )

        with patch.object(client, '_get_stub', return_value=mock_stub):
            with pytest.raises(grpc.aio.AioRpcError):
                await client.some_rpc_method(...)

        # Should have tried 3 times
        assert mock_stub.SomeRpcMethod.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_not_found(self):
        """NOT_FOUND errors are not retried."""
        client = AiModelClient()

        mock_stub = AsyncMock()
        mock_stub.SomeRpcMethod.side_effect = grpc.aio.AioRpcError(
            grpc.StatusCode.NOT_FOUND,
            "Resource not found"
        )

        with patch.object(client, '_get_stub', return_value=mock_stub):
            with pytest.raises(grpc.aio.AioRpcError):
                await client.some_rpc_method(...)

        # Should only try once (no retry for NOT_FOUND)
        assert mock_stub.SomeRpcMethod.call_count == 1


class TestAiModelClientChannelRecreation:
    """Tests for channel recreation on error."""

    @pytest.mark.asyncio
    async def test_channel_recreation_on_connection_error(self):
        """Channel is reset after connection error for next attempt."""
        client = AiModelClient()

        # Create initial channel
        await client._get_stub()
        original_channel = client._channel

        # Simulate connection error and reset
        client._reset_channel()

        assert client._channel is None
        assert client._stub is None

        # Next call creates new channel
        await client._get_stub()

        assert client._channel is not original_channel
```

---

## E2E Test Impact

### PoC Validation
The PoC at `tests/e2e/poc-dapr-patterns/` validates this exact pattern:

```bash
cd tests/e2e/poc-dapr-patterns
docker compose up --build -d
sleep 20
python run_tests.py --test resilience
docker compose down -v
```

### Expected Behavior
- **No breaking changes** - AiModelClient API unchanged
- **Improved resilience** - Transient failures auto-recovered

### Verification
After implementation, existing E2E tests should pass. The AiModelClient is used in:
- Weather data ingestion (Story 0.4.6)
- AI extraction pipelines

---

## Implementation Reference

### Required Pattern (from ADR-005)

```python
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
import grpc.aio

class AiModelClient:
    """AI Model gRPC client with retry and singleton channel."""

    def __init__(self, target: str | None = None) -> None:
        self._target = target or os.getenv("AI_MODEL_GRPC_ADDRESS", "localhost:50051")
        self._channel: grpc.aio.Channel | None = None
        self._stub: AiModelServiceStub | None = None

    async def _get_stub(self) -> AiModelServiceStub:
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
            self._stub = AiModelServiceStub(self._channel)
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
    async def extract_content(self, content: bytes, content_type: str) -> ExtractionResult:
        """Extract content with retry on transient errors."""
        stub = await self._get_stub()
        try:
            request = ExtractionRequest(content=content, content_type=content_type)
            response = await stub.Extract(request, metadata=self._get_metadata())
            return response
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                self._reset_channel()  # Force reconnection on next attempt
            raise

    async def close(self) -> None:
        """Clean up resources."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
```

### Anti-Pattern to Replace

```python
# ❌ FORBIDDEN: Per-request channel creation (current implementation)
async def extract_content(self, content: bytes) -> ExtractionResult:
    async with grpc.aio.insecure_channel(self._target) as channel:
        stub = AiModelServiceStub(channel)
        response = await stub.Extract(request)  # No retry!
        return response
```

---

## Local Test Run Evidence (MANDATORY)

**1. Unit Tests (12 specific to this story):**
```bash
pytest tests/unit/collection_model/infrastructure/test_ai_model_client.py -v
```
**Output:**
```
======================== 12 passed in 9.47s =========================

Tests:
- test_lazy_channel_initialization PASSED
- test_singleton_channel_reused PASSED
- test_channel_created_with_keepalive_options PASSED
- test_retry_on_unavailable PASSED
- test_retry_exhausted_raises PASSED
- test_reset_channel_clears_state PASSED
- test_channel_recreation_after_reset PASSED
- test_channel_reset_on_unavailable_error PASSED
- test_close_cleans_up_channel PASSED
- test_close_is_idempotent PASSED
- test_get_metadata_returns_app_id PASSED
- test_error_includes_context PASSED
```

**2. Full Unit Test Suite:**
```bash
pytest tests/unit/ -v
```
**Output:**
```
================= 997 passed, 2 skipped, 39 warnings in 50.01s =================
```

**3. E2E Tests Pass:**
```bash
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
PYTHONPATH=".:libs/fp-proto/src:libs/fp-common" pytest tests/e2e/scenarios/ -v
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
================== 71 passed, 3 xfailed in 105.49s (0:01:45) ===================
```

**4. Lint Check:**
```bash
ruff check . && ruff format --check .
```
**Output:**
```
All checks passed!
293 files already formatted
```
**Lint passed:** [x] Yes / [ ] No

---

## E2E Test Strategy (Mental Model Alignment)

> **Reference:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Direction of Change

This story **improves resilience** of existing gRPC client. The API surface is **unchanged**.

| Aspect | Impact |
|--------|--------|
| Proto definitions | **UNCHANGED** |
| Client API | **UNCHANGED** - Same method signatures |
| Production behavior | **IMPROVED** - Transient failures auto-recover |
| E2E tests | **MUST PASS WITHOUT MODIFICATION** |

### Existing E2E Tests

**ALL existing E2E tests MUST pass unchanged.** The AiModelClient's external behavior is identical; only internal retry logic is added.

If tests fail after this change:
1. Check if retry logic is interfering with error propagation
2. Check if timeouts are being exceeded due to retries
3. This would be a production bug - fix the production code

### New E2E Tests Needed

**None for E2E.** Retry behavior is validated by:
- Unit tests (mocked gRPC errors)
- PoC resilience test (`tests/e2e/poc-dapr-patterns/`)

The PoC test already validates the singleton + retry pattern works.

### If Existing Tests Fail

```
Test Failed
    │
    ▼
Is failure related to retry behavior?
    │
    ├── YES (timeout, error propagation) ──► Fix retry configuration
    │                                        Check exponential backoff limits
    │
    └── NO (unrelated failure) ──► Investigate per Mental Model
```

---

## References

- [ADR-005: gRPC Client Retry Strategy](../architecture/adr/ADR-005-grpc-client-retry-strategy.md)
- [Reference: PlantationClient](../../../mcp-servers/plantation-mcp/src/plantation_mcp/plantation_client.py)
- [PoC: Resilience Test](../../../tests/e2e/poc-dapr-patterns/)
- [Tenacity Documentation](https://tenacity.readthedocs.io/)
