"""gRPC to SSE stream adapter.

Transforms async gRPC streaming responses to SSE-compatible events.
"""

from collections.abc import AsyncIterator, Callable
from typing import TypeVar

import structlog

# TypeVar for generic protobuf message type
T = TypeVar("T")

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
