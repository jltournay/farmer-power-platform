"""Server-Sent Events (SSE) infrastructure for BFF.

This module provides SSE capabilities for streaming real-time updates
from backend gRPC streams to browser clients.

Usage:
    from bff.infrastructure.sse import SSEManager, grpc_stream_to_sse

    # In FastAPI route:
    grpc_stream = await ai_model_client.stream_document_progress(doc_id)
    sse_events = grpc_stream_to_sse(
        grpc_stream,
        lambda msg: {"percent": msg.progress_percent, "status": msg.status}
    )
    return SSEManager.create_response(sse_events, event_type="progress")
"""

from bff.infrastructure.sse.grpc_adapter import grpc_stream_to_sse
from bff.infrastructure.sse.manager import SSEManager

__all__ = ["SSEManager", "grpc_stream_to_sse"]
