# Story 0.5.9: BFF SSE Infrastructure

**Status:** review
**GitHub Issue:** #183

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **frontend developer**,
I want **Server-Sent Events (SSE) infrastructure in the BFF**,
So that **real-time progress updates from backend gRPC streams can be pushed to browser clients**.

## Acceptance Criteria

1. **SSEManager Class (AC1)**:
   - `SSEManager.create_response(event_generator, event_type)` returns FastAPI `StreamingResponse`
   - Response has Content-Type `text/event-stream`
   - Response has Cache-Control `no-cache`
   - Response has X-Accel-Buffering `no` (nginx compatibility)
   - Events are formatted per SSE protocol: `event: {type}\ndata: {json}\n\n`

2. **gRPC Stream Adapter (AC2)**:
   - `grpc_stream_to_sse(grpc_stream, transform_fn)` async iterator is available
   - Transforms each gRPC protobuf message to dict via transform_fn
   - Yields SSE-compatible events from async gRPC stream
   - gRPC errors during iteration propagate to SSEManager for error event emission

3. **Error Handling (AC3)**:
   - Errors during stream processing send error event before closing
   - Error event has type `error` and includes error message
   - Stream closes gracefully after error

4. **Module Exports (AC4)**:
   - `bff.infrastructure.sse` package is importable
   - Exports: `SSEManager`, `grpc_stream_to_sse`
   - Package is properly initialized with `__init__.py`

5. **Unit Tests (AC5)**:
   - SSEManager.create_response returns StreamingResponse with correct headers
   - grpc_stream_to_sse correctly adapts mock gRPC stream
   - Error handling sends error event before closing
   - Tests in `tests/unit/bff/test_sse_infrastructure.py`

## Tasks / Subtasks

- [x] **Task 1: Create SSE Package Structure** (AC: #4)
  - [x] 1.1 Create `services/bff/src/bff/infrastructure/sse/` directory
  - [x] 1.2 Create `__init__.py` with exports
  - [x] 1.3 Verify import works: `from bff.infrastructure.sse import SSEManager, grpc_stream_to_sse`

- [x] **Task 2: Implement SSEManager** (AC: #1, #3)
  - [x] 2.1 Create `manager.py` with SSEManager class
  - [x] 2.2 Implement `create_response()` class method
  - [x] 2.3 Implement `_format_events()` async generator
  - [x] 2.4 Add error event handling with try/except
  - [x] 2.5 Add type hints and docstrings

- [x] **Task 3: Implement gRPC Adapter** (AC: #2)
  - [x] 3.1 Create `grpc_adapter.py` with `grpc_stream_to_sse` function
  - [x] 3.2 Implement async iteration over gRPC stream
  - [x] 3.3 Apply transform function to each message
  - [x] 3.4 Add type hints using TypeVar for generic message type

- [x] **Task 4: Write Unit Tests** (AC: #5)
  - [x] 4.1 Create `tests/unit/bff/test_sse_infrastructure.py`
  - [x] 4.2 Test SSEManager.create_response headers
  - [x] 4.3 Test SSEManager event formatting
  - [x] 4.4 Test grpc_stream_to_sse with mock stream
  - [x] 4.5 Test error handling sends error event
  - [x] 4.6 Test gRPC stream error propagation in adapter
  - [x] 4.7 Test empty generator edge case
  - [x] 4.8 Run tests and verify all pass

- [x] **Task 5: Verify Integration** (AC: #4)
  - [x] 5.1 Run ruff check and format
  - [x] 5.2 Run unit tests: `pytest tests/unit/bff/test_sse_infrastructure.py -v`
  - [x] 5.3 Verify no import errors in BFF service

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: #183
- [x] Feature branch created from main: `story/0-5-9-bff-sse-infrastructure`

**Branch name:** `story/0-5-9-bff-sse-infrastructure`

### During Development
- [x] All commits reference GitHub issue: `Relates to #183`
- [x] Commits are atomic by type (production, test, seed - not mixed)
- [x] Push to feature branch: `git push -u origin story/0-5-9-bff-sse-infrastructure`

### Story Done
- [x] Create Pull Request: #184
- [x] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-5-9-bff-sse-infrastructure`

**PR URL:** https://github.com/jltournay/farmer-power-platform/pull/184

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/bff/test_sse_infrastructure.py -v
```
**Output:**
```
======================== 19 passed, 3 warnings in 0.14s ========================
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`
>
> **Note:** This story adds BFF infrastructure code only. E2E validation will confirm:
> - BFF service starts successfully with new SSE module
> - No import errors or startup failures

**CI E2E Workflow (Step 9c):**
```
gh workflow run "E2E Tests" --ref story/0-5-9-bff-sse-infrastructure
```

**E2E CI Run ID:** 21008829794
**E2E CI Status:** ✓ PASSED (8m9s)

**Output:**
```
✓ E2E Tests in 8m9s (ID 60398244845)
  ✓ Set up job
  ✓ Checkout code
  ✓ Build and start E2E stack
  ✓ Wait for services to be ready
  ✓ Run E2E tests
  ✓ Upload test results
  ✓ Cleanup E2E stack
  ✓ Test Summary
  ✓ Complete job
```
**E2E passed:** [x] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Output:** `All checks passed! 607 files already formatted`
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/0-5-9-bff-sse-infrastructure

# Wait ~30s, then check CI status
gh run list --branch story/0-5-9-bff-sse-infrastructure --limit 3
```
**CI Run ID:** 21008573173
**CI Status:** ✓ All Tests Pass
**E2E CI Run ID:** 21008829794
**E2E Status:** ✓ Passed
**Verification Date:** 2026-01-14

---

## E2E Story Checklist (Additional guidance for E2E-focused stories)

**Read First:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Pre-Implementation
- [ ] Read and understood `E2E-TESTING-MENTAL-MODEL.md`
- [ ] Understand: Proto = source of truth, tests verify (not define) behavior

### Before Starting Docker
- [ ] Validate seed data: `python tests/e2e/infrastructure/validate_seed_data.py`
- [ ] All seed files pass validation

### During Implementation
- [ ] If tests fail, investigate using the debugging checklist (not blindly modify code)
- [ ] If seed data needs changes, fix seed data (not production code)
- [ ] If production code has bugs, document each fix (see below)

### Production Code Changes (if any)
If you modified ANY production code (`services/`, `mcp-servers/`, `libs/`), document each change here:

| File:Lines | What Changed | Why (with evidence) | Type |
|------------|--------------|---------------------|------|
| (none expected - this is new code) | | | |

**Rules:**
- "To pass tests" is NOT a valid reason
- Must reference proto line, API spec, or other evidence
- If you can't fill this out, you may not understand what you're changing

### Local Test Run Evidence (MANDATORY before any push)

**First run timestamp:** _______________

**Docker stack status:**
```
# Paste output of: docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps
```

**Test run output:**
```
# Paste output of: pytest tests/e2e/scenarios/ -v
# Must show: X passed, 0 failed
```

### Before Marking Done
- [ ] All tests pass locally with Docker infrastructure
- [ ] `ruff check` and `ruff format --check` pass
- [ ] CI pipeline is green
- [ ] If production code changed: Change log above is complete
- [ ] Story file updated with completion notes

---

## Dev Notes

### CRITICAL: This is BFF-Internal Infrastructure Only

This story creates SSE infrastructure inside the BFF service. Key points:

1. **NOT a shared library** - SSE lives in `services/bff/src/bff/infrastructure/sse/`
2. **BFF is the only HTTP edge** - Backend services use gRPC streaming, BFF translates to SSE
3. **Connection-per-resource pattern** - Simple routing, one SSE endpoint per resource type
4. **No endpoint implementation** - This story creates infrastructure only; Story 9.9 will use it

### Directory Structure (MUST CREATE)

```
services/bff/src/bff/infrastructure/sse/
├── __init__.py          # Exports SSEManager, grpc_stream_to_sse
├── manager.py           # SSEManager class
├── grpc_adapter.py      # grpc_stream_to_sse function
└── py.typed             # PEP 561 marker for type stub support
```

### SSEManager Implementation (from ADR-018)

```python
# services/bff/src/bff/infrastructure/sse/manager.py
from typing import AsyncIterator
from fastapi.responses import StreamingResponse
import json
import structlog

logger = structlog.get_logger(__name__)


class SSEManager:
    """Manages Server-Sent Events responses for FastAPI.

    Usage:
        async def progress_generator():
            yield {"progress": 10, "status": "processing"}
            yield {"progress": 50, "status": "processing"}
            yield {"progress": 100, "status": "complete"}

        return SSEManager.create_response(progress_generator())
    """

    CONTENT_TYPE = "text/event-stream"
    CACHE_CONTROL = "no-cache"

    @classmethod
    def create_response(
        cls,
        event_generator: AsyncIterator[dict],
        event_type: str = "message",
    ) -> StreamingResponse:
        """Create SSE StreamingResponse from async generator.

        Args:
            event_generator: Async iterator yielding event data dicts
            event_type: SSE event type (default: "message")

        Returns:
            FastAPI StreamingResponse configured for SSE
        """
        return StreamingResponse(
            cls._format_events(event_generator, event_type),
            media_type=cls.CONTENT_TYPE,
            headers={
                "Cache-Control": cls.CACHE_CONTROL,
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    @classmethod
    async def _format_events(
        cls,
        event_generator: AsyncIterator[dict],
        event_type: str,
    ) -> AsyncIterator[str]:
        """Format events as SSE protocol.

        SSE format:
            event: {event_type}
            data: {json_data}

            (blank line separates events)
        """
        logger.debug("SSE stream started", event_type=event_type)
        try:
            async for event_data in event_generator:
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(event_data)}\n\n"
            logger.debug("SSE stream completed", event_type=event_type)
        except Exception as e:
            # Send error event before closing
            logger.warning("SSE stream error", event_type=event_type, error=str(e))
            error_data = {"error": str(e), "status": "error"}
            yield f"event: error\n"
            yield f"data: {json.dumps(error_data)}\n\n"
            raise
```

### gRPC Adapter Implementation (from ADR-018)

```python
# services/bff/src/bff/infrastructure/sse/grpc_adapter.py
from typing import AsyncIterator, TypeVar, Callable

# Optional protobuf import for type hints only
try:
    from google.protobuf.message import Message
    T = TypeVar("T", bound=Message)
except ImportError:
    # Fallback for environments without protobuf installed
    from typing import Any
    T = TypeVar("T")

import structlog

logger = structlog.get_logger(__name__)


async def grpc_stream_to_sse(
    grpc_stream: AsyncIterator[T],
    transform: Callable[[T], dict],
) -> AsyncIterator[dict]:
    """Adapt gRPC stream to SSE event stream.

    Args:
        grpc_stream: Async iterator from gRPC streaming call
        transform: Function to convert protobuf message to dict

    Yields:
        Dict events suitable for SSE transmission

    Note:
        gRPC errors during iteration are NOT caught here - they propagate
        to SSEManager._format_events() which emits an error event before
        re-raising. This ensures clients receive error notification.

    Example:
        async def get_progress(doc_id: str):
            stub = await self._get_rag_stub()
            stream = stub.ProcessDocument(request)

            return grpc_stream_to_sse(
                stream,
                lambda msg: {
                    "progress": msg.progress_percent,
                    "status": msg.status,
                    "message": msg.message,
                }
            )
    """
    async for message in grpc_stream:
        yield transform(message)
```

### Usage Example (for Story 9.9 - NOT this story)

```python
# services/bff/src/bff/api/routes/knowledge/documents.py
from fastapi import APIRouter, Depends
from bff.infrastructure.sse import SSEManager, grpc_stream_to_sse
from bff.infrastructure.clients.ai_model_client import AiModelClient
from bff.api.dependencies import get_ai_model_client, get_current_user

router = APIRouter(prefix="/knowledge/documents", tags=["knowledge"])


@router.get("/{document_id}/progress")
async def get_document_processing_progress(
    document_id: str,
    ai_model_client: AiModelClient = Depends(get_ai_model_client),
    user = Depends(get_current_user),
):
    """Stream document processing progress via SSE."""
    grpc_stream = await ai_model_client.stream_document_progress(document_id)

    sse_events = grpc_stream_to_sse(
        grpc_stream,
        lambda msg: {
            "percent": msg.progress_percent,
            "status": msg.status.name.lower(),
            "message": msg.message,
        }
    )

    return SSEManager.create_response(sse_events, event_type="progress")
```

### Test Pattern

```python
# tests/unit/bff/test_sse_infrastructure.py
import pytest
from unittest.mock import AsyncMock
from bff.infrastructure.sse import SSEManager, grpc_stream_to_sse


@pytest.mark.asyncio
async def test_sse_manager_creates_response_with_correct_headers():
    """SSEManager.create_response returns StreamingResponse with SSE headers."""
    async def mock_generator():
        yield {"progress": 50}

    response = SSEManager.create_response(mock_generator())

    assert response.media_type == "text/event-stream"
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["X-Accel-Buffering"] == "no"


@pytest.mark.asyncio
async def test_sse_manager_formats_events_correctly():
    """SSEManager formats events per SSE protocol."""
    async def mock_generator():
        yield {"progress": 50, "status": "processing"}

    formatted = []
    async for chunk in SSEManager._format_events(mock_generator(), "progress"):
        formatted.append(chunk)

    assert "event: progress\n" in formatted
    assert 'data: {"progress": 50, "status": "processing"}\n\n' in formatted


@pytest.mark.asyncio
async def test_grpc_stream_to_sse_transforms_messages():
    """grpc_stream_to_sse correctly transforms gRPC messages."""
    class MockMessage:
        progress_percent = 75
        status = "processing"

    async def mock_grpc_stream():
        yield MockMessage()

    events = []
    async for event in grpc_stream_to_sse(
        mock_grpc_stream(),
        lambda msg: {"percent": msg.progress_percent, "status": msg.status}
    ):
        events.append(event)

    assert len(events) == 1
    assert events[0] == {"percent": 75, "status": "processing"}


@pytest.mark.asyncio
async def test_sse_manager_sends_error_event_on_exception():
    """SSEManager sends error event when generator raises exception."""
    async def failing_generator():
        yield {"progress": 10}
        raise ValueError("Something went wrong")

    formatted = []
    with pytest.raises(ValueError):
        async for chunk in SSEManager._format_events(failing_generator(), "progress"):
            formatted.append(chunk)

    # Should have sent error event before re-raising
    assert "event: error\n" in formatted
    assert "Something went wrong" in "".join(formatted)


@pytest.mark.asyncio
async def test_grpc_stream_to_sse_propagates_errors():
    """grpc_stream_to_sse propagates gRPC errors to SSEManager."""
    import grpc

    async def failing_grpc_stream():
        yield MockMessage()
        # Simulate gRPC stream error mid-flight
        raise grpc.aio.AioRpcError(
            grpc.StatusCode.UNAVAILABLE,
            initial_metadata=None,
            trailing_metadata=None,
            details="Connection lost",
        )

    class MockMessage:
        progress_percent = 50
        status = "processing"

    events = []
    with pytest.raises(grpc.aio.AioRpcError):
        async for event in grpc_stream_to_sse(
            failing_grpc_stream(),
            lambda msg: {"percent": msg.progress_percent}
        ):
            events.append(event)

    # First event should have been yielded before error
    assert len(events) == 1
    assert events[0] == {"percent": 50}


@pytest.mark.asyncio
async def test_sse_manager_handles_empty_generator():
    """SSEManager handles generator that yields nothing."""
    async def empty_generator():
        return
        yield  # Never reached

    formatted = []
    async for chunk in SSEManager._format_events(empty_generator(), "progress"):
        formatted.append(chunk)

    assert formatted == []  # No events emitted
```

### Project Structure Notes

- **Location:** `services/bff/src/bff/infrastructure/sse/`
- **Pattern:** Follows existing BFF infrastructure patterns (see `clients/` folder)
- **Imports:** Uses FastAPI StreamingResponse, json, typing, structlog
- **No external dependencies:** Pure Python implementation

### HTTP Version Compatibility Notes

- **HTTP/1.1:** `Connection: keep-alive` is default; header is informational only
- **HTTP/2:** Connection header is ignored (HTTP/2 is inherently multiplexed)
- **Nginx proxy:** `X-Accel-Buffering: no` is **critical** regardless of HTTP version to prevent buffering
- **Browser limits:** HTTP/1.1 has ~6 connections per domain; HTTP/2 has no such limit

### Heartbeat Support (Optional for Long Streams)

For long-running streams (10+ minutes), proxies may terminate idle connections.
Consider adding periodic keepalive comments if needed in future:

```python
# Optional heartbeat pattern (for Story 9.9 if document processing takes >5 min)
async def _format_events_with_heartbeat(generator, event_type, heartbeat_seconds=30):
    import asyncio
    last_event = asyncio.get_event_loop().time()
    async for event_data in generator:
        yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
        last_event = asyncio.get_event_loop().time()
    # SSE comment format for keepalive: ": heartbeat\n\n"
```

### Previous Story Intelligence

**From Story 0.5.7 (Factory Portal Scaffold):**
- Frontend authentication patterns established
- React EventSource usage pattern documented
- Visual validation and human approval process required

**From Story 0.75.23 (RAG Query Service):**
- AiModelClient exists for AI Model gRPC calls
- BaseGrpcClient pattern with DAPR service invocation
- grpc_retry decorator available for retry logic

**From ADR-018:**
- SSE chosen over WebSocket for unidirectional server-to-client streaming
- Connection-per-resource pattern (simpler than multiplexed)
- BFF-internal only (not shared library)

### Files to Create

| Path | Purpose |
|------|---------|
| `services/bff/src/bff/infrastructure/sse/__init__.py` | Package exports |
| `services/bff/src/bff/infrastructure/sse/manager.py` | SSEManager class |
| `services/bff/src/bff/infrastructure/sse/grpc_adapter.py` | grpc_stream_to_sse function |
| `services/bff/src/bff/infrastructure/sse/py.typed` | PEP 561 type stub marker (empty file) |
| `tests/unit/bff/test_sse_infrastructure.py` | Unit tests (8 test cases) |

### Files to Modify

| Path | Change |
|------|--------|
| `services/bff/src/bff/infrastructure/__init__.py` | Add sse to exports (optional) |

### Anti-Patterns to Avoid

1. **DO NOT** create shared library in libs/ - SSE is BFF-internal only
2. **DO NOT** implement actual endpoints - this story is infrastructure only
3. **DO NOT** add WebSocket support - SSE is the chosen pattern per ADR-018
4. **DO NOT** use blocking I/O - all operations must be async
5. **DO NOT** forget error event on exception - must send before re-raising
6. **DO NOT** use HTTP response buffering - disable with X-Accel-Buffering header

### References

- [Source: _bmad-output/architecture/adr/ADR-018-real-time-communication-patterns.md]
- [Source: _bmad-output/epics/epic-0-5-frontend.md#Story-0.5.9]
- [Source: _bmad-output/project-context.md]
- [Source: services/bff/src/bff/infrastructure/clients/base.py - BaseGrpcClient pattern]
- [Source: services/bff/src/bff/infrastructure/clients/ai_model_client.py - gRPC client example]

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- (list new files)

**Modified:**
- (list modified files with brief description)
