# ADR-018: Real-Time Communication Patterns (SSE vs WebSocket)

**Status:** Accepted
**Date:** 2026-01-14
**Deciders:** Winston (Architect), Amelia (Dev), John (PM), Jeanlouistournay
**Related Stories:** Story 0.5.x (SSE Infrastructure), Story 9.9 (Knowledge Management Interface)

## Context

During Story 9.9 planning (Knowledge Management Interface), we identified a gap in real-time communication:

1. **Backend capability exists**: The RAG Model service exposes gRPC streaming for document processing progress (`ProcessDocument` stream)
2. **Frontend needs progress updates**: The Knowledge Management UI includes a progress bar for document processing
3. **BFF gap**: No mechanism to translate gRPC streams to browser-consumable real-time updates

This decision impacts multiple future features:
- Document processing progress (Epic 9 - Admin Portal)
- Weather alert push notifications (Epic 7)
- Bulk operation feedback (Epic 9)
- Multi-user sync status (future)

---

## Decision 1: Server-Sent Events (SSE) over WebSockets

### Problem

Two main options exist for server-to-client real-time communication:

| Option | Description |
|--------|-------------|
| **WebSockets** | Full-duplex, persistent TCP connection |
| **Server-Sent Events (SSE)** | HTTP-based, unidirectional server-to-client stream |

### Decision

**Use Server-Sent Events (SSE) for all BFF real-time communication.**

### Rationale

| Factor | SSE | WebSocket | Winner |
|--------|-----|-----------|--------|
| **Complexity** | HTTP/2 native, no special infrastructure | Requires upgrade handshake, connection management | SSE |
| **Proxy compatibility** | Works through most proxies, load balancers | May require special configuration | SSE |
| **Browser support** | Native `EventSource` API | Native `WebSocket` API | Tie |
| **Reconnection** | Automatic with `Last-Event-ID` | Manual implementation required | SSE |
| **Directionality** | Server → Client only | Bidirectional | WebSocket |
| **Our use case** | Progress updates, notifications (unidirectional) | N/A | SSE |

**Key insight**: Our use cases (progress bars, notifications, status updates) are **unidirectional**. WebSockets provide bidirectional communication we don't need, at the cost of additional infrastructure complexity.

### When to Reconsider WebSockets

WebSockets would be appropriate if we add:
- Real-time collaborative editing (multiple users editing same entity)
- Chat/messaging features
- High-frequency bidirectional data (gaming, trading)

For now, these are not on the roadmap.

---

## Decision 2: BFF-Internal SSE Infrastructure

### Problem

Where should SSE infrastructure live?

| Option | Description |
|--------|-------------|
| **libs/fp-common/** | Shared library for all services |
| **services/bff/src/infrastructure/sse/** | BFF-internal only |

### Decision

**SSE infrastructure lives entirely within BFF (`services/bff/src/infrastructure/sse/`).**

### Rationale

1. **Only BFF serves HTTP clients** - Backend services use gRPC exclusively
2. **SSE is an HTTP protocol concern** - Belongs at the HTTP edge (BFF)
3. **Simpler dependency graph** - No cross-service SSE coordination needed
4. **gRPC streams stay internal** - Backend services continue using gRPC streaming

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         REAL-TIME COMMUNICATION FLOW                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    gRPC Stream    ┌─────────────┐    SSE    ┌────────┐ │
│  │  Backend    │ ───────────────── │     BFF     │ ──────── │ Browser │ │
│  │  Service    │                   │  (FastAPI)  │          │         │ │
│  │  (gRPC)     │                   │             │          │         │ │
│  └─────────────┘                   └─────────────┘          └────────┘ │
│                                           │                             │
│                                           │                             │
│                         ┌─────────────────┴─────────────────┐          │
│                         │  services/bff/src/infrastructure/  │          │
│                         │  └── sse/                          │          │
│                         │      ├── __init__.py               │          │
│                         │      ├── manager.py                │          │
│                         │      └── grpc_adapter.py           │          │
│                         └────────────────────────────────────┘          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Decision 3: Connection-Per-Resource Pattern

### Problem

Two connection patterns exist:

| Pattern | Description |
|---------|-------------|
| **Connection-per-resource** | Separate SSE endpoint per resource (e.g., `/documents/{id}/progress`) |
| **Multiplexed connection** | Single `/events` endpoint with topic subscriptions |

### Decision

**Use connection-per-resource pattern for MVP.**

### Rationale

| Factor | Connection-per-resource | Multiplexed |
|--------|------------------------|-------------|
| **Complexity** | Simple routing, one stream per endpoint | Topic routing, subscription management |
| **Auth model** | Standard per-request auth | Shared connection auth complexity |
| **Debugging** | Clear 1:1 mapping | Harder to trace specific streams |
| **Connection limits** | ~6 per domain (HTTP/1.1), unlimited (HTTP/2) | Single connection |
| **Our scale** | Admin portal, low concurrent streams | N/A |

For the Admin Portal use case (low concurrent users, occasional document processing), connection limits are not a concern. We can refactor to multiplexed later if needed.

### Migration Path

If we hit connection limits in the future:
1. Add `/api/events` multiplexed endpoint
2. Implement topic subscription protocol
3. Migrate high-frequency consumers first
4. Keep connection-per-resource for low-frequency use cases

---

## Implementation

### BFF SSE Infrastructure

```python
# services/bff/src/bff/infrastructure/sse/__init__.py
from .manager import SSEManager
from .grpc_adapter import grpc_stream_to_sse

__all__ = ["SSEManager", "grpc_stream_to_sse"]
```

```python
# services/bff/src/bff/infrastructure/sse/manager.py
from typing import AsyncIterator
from fastapi import Response
from fastapi.responses import StreamingResponse
import json


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
        try:
            async for event_data in event_generator:
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(event_data)}\n\n"
        except Exception as e:
            # Send error event before closing
            error_data = {"error": str(e), "status": "error"}
            yield f"event: error\n"
            yield f"data: {json.dumps(error_data)}\n\n"
            raise
```

```python
# services/bff/src/bff/infrastructure/sse/grpc_adapter.py
from typing import AsyncIterator, TypeVar, Callable
from google.protobuf.message import Message

T = TypeVar("T", bound=Message)


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

### Example Endpoint (Story 9.9)

```python
# services/bff/src/bff/api/routes/knowledge/documents.py
from fastapi import APIRouter, Depends
from bff.infrastructure.sse import SSEManager, grpc_stream_to_sse
from bff.infrastructure.clients.rag_client import RAGClient
from bff.api.dependencies import get_rag_client, get_current_user

router = APIRouter(prefix="/knowledge/documents", tags=["knowledge"])


@router.get("/{document_id}/progress")
async def get_document_processing_progress(
    document_id: str,
    rag_client: RAGClient = Depends(get_rag_client),
    user = Depends(get_current_user),
):
    """Stream document processing progress via SSE.

    Returns:
        SSE stream with events:
        - event: progress
          data: {"percent": 0-100, "status": "processing|complete|error", "message": "..."}
    """
    grpc_stream = await rag_client.stream_document_progress(document_id)

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

### Frontend Usage

```typescript
// React component example
function useDocumentProgress(documentId: string) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<'idle' | 'processing' | 'complete' | 'error'>('idle');

  useEffect(() => {
    const eventSource = new EventSource(
      `/api/knowledge/documents/${documentId}/progress`
    );

    eventSource.addEventListener('progress', (event) => {
      const data = JSON.parse(event.data);
      setProgress(data.percent);
      setStatus(data.status);

      if (data.status === 'complete' || data.status === 'error') {
        eventSource.close();
      }
    });

    eventSource.addEventListener('error', () => {
      setStatus('error');
      eventSource.close();
    });

    return () => eventSource.close();
  }, [documentId]);

  return { progress, status };
}
```

---

## Consequences

### Positive

- **Simpler infrastructure** - No WebSocket upgrade handling, connection management
- **Proxy-friendly** - Works through standard HTTP proxies and load balancers
- **Native reconnection** - Browser `EventSource` handles reconnection automatically
- **Clear separation** - gRPC for backend, SSE for frontend, BFF as translator
- **Minimal code** - ~100 lines for complete SSE infrastructure

### Negative

- **Unidirectional only** - Cannot use for features requiring client-to-server streaming
- **Connection overhead** - One connection per resource (mitigated by HTTP/2)
- **No binary data** - SSE is text-only (not a concern for progress/status updates)

### Risks Mitigated

- **Complexity risk** - SSE is significantly simpler than WebSocket infrastructure
- **Compatibility risk** - SSE works in all modern browsers and through proxies
- **Maintenance risk** - Less code means fewer bugs and easier maintenance

---

## Future Considerations

### When to Add WebSockets

If these features are added to the roadmap, reconsider WebSockets:
- Real-time collaborative editing (multiple users, same document)
- Chat/messaging between users
- High-frequency bidirectional data streams

### Multiplexed SSE Migration

If connection limits become an issue:
1. Monitor concurrent SSE connections per user
2. If exceeding 6 concurrent (HTTP/1.1 limit), implement multiplexed endpoint
3. Prioritize HTTP/2 deployment (no per-domain connection limit)

---

## References

- Story 9.9: `_bmad-output/epics/epic-9-admin-portal/story-99-knowledge-management-interface.md`
- ADR-012: BFF Service Composition (establishes BFF patterns)
- ADR-011: gRPC/FastAPI/DAPR Architecture (backend streaming)
- MDN EventSource: https://developer.mozilla.org/en-US/docs/Web/API/EventSource
- SSE Specification: https://html.spec.whatwg.org/multipage/server-sent-events.html
