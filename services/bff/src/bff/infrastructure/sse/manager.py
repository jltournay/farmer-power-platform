"""SSE Manager for creating FastAPI streaming responses.

Implements Server-Sent Events (SSE) protocol per ADR-018.
"""

import json
from collections.abc import AsyncIterator

import structlog
from fastapi.responses import StreamingResponse

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
            yield "event: error\n"
            yield f"data: {json.dumps(error_data)}\n\n"
            raise
