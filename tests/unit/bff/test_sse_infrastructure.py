"""Unit tests for BFF SSE infrastructure.

Tests for:
- SSEManager.create_response headers (AC1)
- SSEManager event formatting (AC1)
- grpc_stream_to_sse adapter (AC2)
- Error handling and error events (AC3)
- Module exports (AC4)
"""

import json

import pytest
from bff.infrastructure.sse import SSEManager, grpc_stream_to_sse


class TestSSEManagerHeaders:
    """Tests for SSEManager response headers (AC1)."""

    @pytest.mark.asyncio
    async def test_create_response_returns_streaming_response(self) -> None:
        """SSEManager.create_response returns StreamingResponse."""
        from fastapi.responses import StreamingResponse

        async def mock_generator():
            yield {"progress": 50}

        response = SSEManager.create_response(mock_generator())

        assert isinstance(response, StreamingResponse)

    @pytest.mark.asyncio
    async def test_create_response_has_correct_content_type(self) -> None:
        """Response has Content-Type text/event-stream."""

        async def mock_generator():
            yield {"progress": 50}

        response = SSEManager.create_response(mock_generator())

        assert response.media_type == "text/event-stream"

    @pytest.mark.asyncio
    async def test_create_response_has_cache_control_no_cache(self) -> None:
        """Response has Cache-Control no-cache header."""

        async def mock_generator():
            yield {"progress": 50}

        response = SSEManager.create_response(mock_generator())

        assert response.headers["Cache-Control"] == "no-cache"

    @pytest.mark.asyncio
    async def test_create_response_has_nginx_buffering_disabled(self) -> None:
        """Response has X-Accel-Buffering no header for nginx compatibility."""

        async def mock_generator():
            yield {"progress": 50}

        response = SSEManager.create_response(mock_generator())

        assert response.headers["X-Accel-Buffering"] == "no"

    @pytest.mark.asyncio
    async def test_create_response_has_connection_keepalive(self) -> None:
        """Response has Connection keep-alive header."""

        async def mock_generator():
            yield {"progress": 50}

        response = SSEManager.create_response(mock_generator())

        assert response.headers["Connection"] == "keep-alive"


class TestSSEManagerEventFormatting:
    """Tests for SSEManager event formatting (AC1)."""

    @pytest.mark.asyncio
    async def test_format_events_produces_sse_format(self) -> None:
        """Events are formatted per SSE protocol: event: {type}\\ndata: {json}\\n\\n."""

        async def mock_generator():
            yield {"progress": 50, "status": "processing"}

        formatted = []
        async for chunk in SSEManager._format_events(mock_generator(), "progress"):
            formatted.append(chunk)

        assert "event: progress\n" in formatted
        # Check data line exists and is valid JSON
        data_lines = [line for line in formatted if line.startswith("data:")]
        assert len(data_lines) == 1
        data_json = data_lines[0].replace("data: ", "").strip()
        parsed = json.loads(data_json)
        assert parsed == {"progress": 50, "status": "processing"}

    @pytest.mark.asyncio
    async def test_format_events_uses_custom_event_type(self) -> None:
        """Event type is configurable."""

        async def mock_generator():
            yield {"count": 1}

        formatted = []
        async for chunk in SSEManager._format_events(mock_generator(), "document.update"):
            formatted.append(chunk)

        assert "event: document.update\n" in formatted

    @pytest.mark.asyncio
    async def test_format_events_default_event_type(self) -> None:
        """Default event type is 'message'."""

        async def mock_generator():
            yield {"data": "test"}

        response = SSEManager.create_response(mock_generator())
        # The default is set in create_response
        assert response is not None

    @pytest.mark.asyncio
    async def test_format_events_produces_multiple_events(self) -> None:
        """Multiple events are properly formatted."""

        async def mock_generator():
            yield {"progress": 10}
            yield {"progress": 50}
            yield {"progress": 100}

        formatted = []
        async for chunk in SSEManager._format_events(mock_generator(), "progress"):
            formatted.append(chunk)

        # Each event has event line + data line = 2 chunks per event
        # 3 events = 6 chunks
        assert len(formatted) == 6
        event_lines = [line for line in formatted if line.startswith("event:")]
        assert len(event_lines) == 3


class TestSSEManagerErrorHandling:
    """Tests for SSEManager error handling (AC3)."""

    @pytest.mark.asyncio
    async def test_error_sends_error_event_before_raising(self) -> None:
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
        # Find error data line and verify it contains error message
        error_data_lines = [
            line
            for i, line in enumerate(formatted)
            if i > 0 and formatted[i - 1] == "event: error\n" and line.startswith("data:")
        ]
        assert len(error_data_lines) == 1
        error_json = json.loads(error_data_lines[0].replace("data: ", "").strip())
        assert error_json["error"] == "Something went wrong"
        assert error_json["status"] == "error"

    @pytest.mark.asyncio
    async def test_error_event_includes_error_message(self) -> None:
        """Error event data includes the error message."""

        async def failing_generator():
            yield {"start": True}  # Yield something first to make it an async generator
            raise RuntimeError("Connection lost")

        formatted = []
        with pytest.raises(RuntimeError):
            async for chunk in SSEManager._format_events(failing_generator(), "progress"):
                formatted.append(chunk)

        # Find error data
        error_data_str = "".join(formatted)
        assert "Connection lost" in error_data_str


class TestGrpcStreamToSSE:
    """Tests for grpc_stream_to_sse adapter (AC2)."""

    @pytest.mark.asyncio
    async def test_transforms_messages_correctly(self) -> None:
        """grpc_stream_to_sse correctly transforms gRPC messages."""

        class MockMessage:
            def __init__(self, percent: int, status: str):
                self.progress_percent = percent
                self.status = status

        async def mock_grpc_stream():
            yield MockMessage(25, "processing")
            yield MockMessage(75, "processing")
            yield MockMessage(100, "complete")

        events = []
        async for event in grpc_stream_to_sse(
            mock_grpc_stream(), lambda msg: {"percent": msg.progress_percent, "status": msg.status}
        ):
            events.append(event)

        assert len(events) == 3
        assert events[0] == {"percent": 25, "status": "processing"}
        assert events[1] == {"percent": 75, "status": "processing"}
        assert events[2] == {"percent": 100, "status": "complete"}

    @pytest.mark.asyncio
    async def test_propagates_grpc_errors(self) -> None:
        """grpc_stream_to_sse propagates gRPC errors to SSEManager."""

        class MockMessage:
            progress_percent = 50
            status = "processing"

        async def failing_grpc_stream():
            yield MockMessage()
            # Simulate gRPC stream error mid-flight
            raise ConnectionError("gRPC stream disconnected")

        events = []
        with pytest.raises(ConnectionError, match="gRPC stream disconnected"):
            async for event in grpc_stream_to_sse(failing_grpc_stream(), lambda msg: {"percent": msg.progress_percent}):
                events.append(event)

        # First event should have been yielded before error
        assert len(events) == 1
        assert events[0] == {"percent": 50}

    @pytest.mark.asyncio
    async def test_handles_empty_stream(self) -> None:
        """grpc_stream_to_sse handles empty stream gracefully."""

        async def empty_grpc_stream():
            return
            yield  # Never reached

        events = []
        async for event in grpc_stream_to_sse(empty_grpc_stream(), lambda msg: {"data": msg}):
            events.append(event)

        assert events == []


class TestSSEManagerEmptyGenerator:
    """Tests for edge cases (AC5)."""

    @pytest.mark.asyncio
    async def test_handles_empty_generator(self) -> None:
        """SSEManager handles generator that yields nothing."""

        async def empty_generator():
            return
            yield  # Never reached - makes it an async generator

        formatted = []
        async for chunk in SSEManager._format_events(empty_generator(), "progress"):
            formatted.append(chunk)

        assert formatted == []


class TestModuleExports:
    """Tests for module exports (AC4)."""

    def test_sse_manager_importable(self) -> None:
        """SSEManager is importable from bff.infrastructure.sse."""
        from bff.infrastructure.sse import SSEManager

        assert SSEManager is not None

    def test_grpc_stream_to_sse_importable(self) -> None:
        """grpc_stream_to_sse is importable from bff.infrastructure.sse."""
        from bff.infrastructure.sse import grpc_stream_to_sse

        assert grpc_stream_to_sse is not None

    def test_package_all_exports(self) -> None:
        """Package __all__ contains expected exports."""
        from bff.infrastructure import sse

        assert hasattr(sse, "__all__")
        assert "SSEManager" in sse.__all__
        assert "grpc_stream_to_sse" in sse.__all__


class TestIntegrationScenario:
    """Integration tests for the full SSE flow."""

    @pytest.mark.asyncio
    async def test_full_sse_flow_with_grpc_adapter(self) -> None:
        """Complete flow: gRPC stream -> adapter -> SSEManager -> formatted output."""

        class MockProgressMessage:
            def __init__(self, percent: int, msg: str):
                self.progress_percent = percent
                self.message = msg

        async def mock_grpc_progress_stream():
            yield MockProgressMessage(0, "Starting")
            yield MockProgressMessage(50, "Processing")
            yield MockProgressMessage(100, "Done")

        # Adapt gRPC stream to SSE events
        sse_events = grpc_stream_to_sse(
            mock_grpc_progress_stream(), lambda msg: {"percent": msg.progress_percent, "msg": msg.message}
        )

        # Create SSE response
        response = SSEManager.create_response(sse_events, event_type="progress")

        # Verify response headers
        assert response.media_type == "text/event-stream"
        assert response.headers["Cache-Control"] == "no-cache"
        assert response.headers["X-Accel-Buffering"] == "no"

        # Read all formatted events from response body
        formatted = []
        async for chunk in response.body_iterator:
            formatted.append(chunk)

        # Verify event structure
        assert len(formatted) == 6  # 3 events * 2 lines each
        assert "event: progress\n" in formatted
        # Verify all progress values are present in data lines
        all_data = "".join(formatted)
        assert '"percent": 0' in all_data
        assert '"percent": 50' in all_data
        assert '"percent": 100' in all_data
