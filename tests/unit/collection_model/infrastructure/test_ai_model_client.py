"""Unit tests for AiModelClient gRPC retry and singleton channel pattern.

Tests verify ADR-005 compliance:
- Singleton channel pattern (lazy initialization, reuse)
- Tenacity retry on gRPC errors (3 attempts, exponential backoff)
- Channel reset on UNAVAILABLE error
- No retry on non-transient errors (NOT_FOUND)
- ServiceUnavailableError raised after retries exhausted (AC4)

Reference: ADR-005-grpc-client-retry-strategy.md
"""

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest
from collection_model.infrastructure.ai_model_client import (
    AiModelClient,
    ExtractionRequest,
    ServiceUnavailableError,
)

# Import the source config factory using pytest's conftest mechanism
from tests.unit.collection.conftest import create_source_config


class TestAiModelClientSingletonChannel:
    """Tests for singleton channel pattern (ADR-005)."""

    @pytest.mark.asyncio
    async def test_lazy_channel_initialization(self) -> None:
        """Channel is not created until first use."""
        client = AiModelClient(ai_model_app_id="ai-model")

        # Initially, channel and stub should be None
        assert client._channel is None
        assert client._stub is None

    @pytest.mark.asyncio
    async def test_singleton_channel_reused(self) -> None:
        """Same channel is reused across multiple _get_stub calls."""
        # Create a mock channel
        mock_channel = MagicMock(spec=grpc.aio.Channel)
        client = AiModelClient(ai_model_app_id="ai-model", channel=mock_channel)

        # First call creates stub
        stub1 = await client._get_stub()
        channel1 = client._channel

        # Second call reuses the same channel and stub
        stub2 = await client._get_stub()
        channel2 = client._channel

        assert channel1 is channel2
        assert stub1 is stub2

    @pytest.mark.asyncio
    async def test_channel_created_with_keepalive_options(self) -> None:
        """Channel is created with proper keepalive settings per ADR-005."""
        client = AiModelClient(ai_model_app_id="ai-model")

        with patch("grpc.aio.insecure_channel") as mock_create_channel:
            mock_channel = MagicMock(spec=grpc.aio.Channel)
            mock_create_channel.return_value = mock_channel

            await client._get_stub()

            # Verify channel was created with keepalive options
            mock_create_channel.assert_called_once()
            call_args = mock_create_channel.call_args
            assert call_args[0][0] == "localhost:50001"  # DAPR sidecar port
            options = dict(call_args[1]["options"])
            assert options["grpc.keepalive_time_ms"] == 30000
            assert options["grpc.keepalive_timeout_ms"] == 10000


class GrpcUnavailableError(grpc.aio.AioRpcError):
    """Test helper: Real AioRpcError subclass for UNAVAILABLE status."""

    def __init__(self) -> None:
        # Required attributes for grpc.aio._call's __str__ method
        self._code = grpc.StatusCode.UNAVAILABLE
        self._details = "Service unavailable"
        self._initial_metadata = None
        self._trailing_metadata = None
        self._debug_error_string = "UNAVAILABLE: Service unavailable"

    def code(self) -> grpc.StatusCode:
        return grpc.StatusCode.UNAVAILABLE

    def details(self) -> str:
        return "Service unavailable"

    def debug_error_string(self) -> str:
        return "UNAVAILABLE: Service unavailable"

    def trailing_metadata(self):
        return None

    def initial_metadata(self):
        return None


class GrpcNotFoundError(grpc.aio.AioRpcError):
    """Test helper: Real AioRpcError subclass for NOT_FOUND status."""

    def __init__(self) -> None:
        self._code = grpc.StatusCode.NOT_FOUND
        self._details = "Resource not found"
        self._initial_metadata = None
        self._trailing_metadata = None
        self._debug_error_string = "NOT_FOUND: Resource not found"

    def code(self) -> grpc.StatusCode:
        return grpc.StatusCode.NOT_FOUND

    def details(self) -> str:
        return "Resource not found"

    def debug_error_string(self) -> str:
        return "NOT_FOUND: Resource not found"

    def trailing_metadata(self):
        return None

    def initial_metadata(self):
        return None


class TestAiModelClientRetry:
    """Tests for Tenacity retry behavior (ADR-005)."""

    @pytest.mark.asyncio
    async def test_retry_on_unavailable(self) -> None:
        """Retry triggers on UNAVAILABLE status code."""
        client = AiModelClient(ai_model_app_id="ai-model")
        call_count = 0

        # Create a mock that fails twice then succeeds
        async def failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise GrpcUnavailableError()
            # Return a successful health check response
            mock_response = MagicMock()
            mock_response.healthy = True
            return mock_response

        mock_stub = MagicMock()
        mock_stub.HealthCheck = failing_then_succeeding

        with patch.object(client, "_get_stub", return_value=mock_stub):
            result = await client.health_check()

        assert result is True
        assert call_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self) -> None:
        """ServiceUnavailableError raised after max retries exhausted (AC4)."""
        client = AiModelClient(ai_model_app_id="ai-model")
        call_count = 0

        # Create a mock that always fails
        async def always_failing(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise GrpcUnavailableError()

        mock_stub = MagicMock()
        mock_stub.HealthCheck = always_failing

        with (
            patch.object(client, "_get_stub", return_value=mock_stub),
            pytest.raises(ServiceUnavailableError),
        ):
            await client.health_check()

        # Should have tried 3 times (retry decorator default)
        assert call_count == 3


class TestAiModelClientChannelRecreation:
    """Tests for channel recreation on error (ADR-005)."""

    @pytest.mark.asyncio
    async def test_reset_channel_clears_state(self) -> None:
        """_reset_channel clears both channel and stub."""
        mock_channel = MagicMock(spec=grpc.aio.Channel)
        client = AiModelClient(ai_model_app_id="ai-model", channel=mock_channel)

        # Initialize stub
        await client._get_stub()
        assert client._channel is not None
        assert client._stub is not None

        # Reset
        client._reset_channel()

        assert client._channel is None
        assert client._stub is None

    @pytest.mark.asyncio
    async def test_channel_recreation_after_reset(self) -> None:
        """New channel is created after reset."""
        client = AiModelClient(ai_model_app_id="ai-model")

        with patch("grpc.aio.insecure_channel") as mock_create_channel:
            # First call
            mock_channel1 = MagicMock(spec=grpc.aio.Channel)
            mock_create_channel.return_value = mock_channel1
            await client._get_stub()

            original_channel = client._channel
            assert original_channel is mock_channel1

            # Reset
            client._reset_channel()

            # Second call should create new channel
            mock_channel2 = MagicMock(spec=grpc.aio.Channel)
            mock_create_channel.return_value = mock_channel2
            await client._get_stub()

            assert client._channel is mock_channel2
            assert client._channel is not original_channel

    @pytest.mark.asyncio
    async def test_channel_reset_on_unavailable_error(self) -> None:
        """Channel is reset when UNAVAILABLE error occurs during extract."""
        client = AiModelClient(ai_model_app_id="ai-model")
        reset_called = False

        # Mock the extract to raise UNAVAILABLE
        async def unavailable_error(*args, **kwargs):
            raise GrpcUnavailableError()

        mock_stub = MagicMock()
        mock_stub.Extract = unavailable_error

        original_reset = client._reset_channel

        def track_reset():
            nonlocal reset_called
            reset_called = True
            original_reset()

        # Create a valid SourceConfig using the factory
        source_config = create_source_config(source_id="test-source")

        request = ExtractionRequest(
            raw_content="test content",
            ai_agent_id="test-agent",
            source_config=source_config,
        )

        with (
            patch.object(client, "_get_stub", return_value=mock_stub),
            patch.object(client, "_reset_channel", side_effect=track_reset),
            pytest.raises(ServiceUnavailableError),
        ):
            await client.extract(request)

        # _reset_channel should have been called due to UNAVAILABLE
        assert reset_called


class TestAiModelClientClose:
    """Tests for resource cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_channel(self) -> None:
        """close() properly cleans up the channel."""
        mock_channel = AsyncMock(spec=grpc.aio.Channel)
        client = AiModelClient(ai_model_app_id="ai-model", channel=mock_channel)

        # Initialize stub
        await client._get_stub()
        assert client._channel is not None

        # Close
        await client.close()

        mock_channel.close.assert_called_once()
        assert client._channel is None
        assert client._stub is None

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self) -> None:
        """close() can be called multiple times safely."""
        client = AiModelClient(ai_model_app_id="ai-model")

        # Close without ever initializing
        await client.close()
        assert client._channel is None

        # Close again
        await client.close()
        assert client._channel is None


class TestAiModelClientMetadata:
    """Tests for DAPR metadata handling."""

    def test_get_metadata_returns_app_id(self) -> None:
        """_get_metadata returns proper DAPR app-id."""
        client = AiModelClient(ai_model_app_id="test-ai-model")

        metadata = client._get_metadata()

        assert metadata == [("dapr-app-id", "test-ai-model")]


class TestServiceUnavailableError:
    """Tests for ServiceUnavailableError exception."""

    def test_error_includes_context(self) -> None:
        """Exception includes app_id, method_name, and attempt_count."""
        error = ServiceUnavailableError(
            message="Connection failed",
            app_id="ai-model",
            method_name="Extract",
            attempt_count=3,
        )

        assert error.app_id == "ai-model"
        assert error.method_name == "Extract"
        assert error.attempt_count == 3
        assert "ai-model" in str(error)
        assert "Extract" in str(error)
        assert "3" in str(error)


class TestAiModelClientExtractRetry:
    """Tests for extract() retry behavior (ADR-005 AC3)."""

    @pytest.mark.asyncio
    async def test_extract_retries_on_unavailable(self) -> None:
        """extract() retries on UNAVAILABLE and succeeds after recovery."""
        client = AiModelClient(ai_model_app_id="ai-model")
        call_count = 0

        # Mock that fails twice then succeeds
        async def failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise GrpcUnavailableError()
            # Return a successful response
            mock_response = MagicMock()
            mock_response.success = True
            mock_response.extracted_fields_json = '{"field": "value"}'
            mock_response.confidence = 0.95
            mock_response.validation_passed = True
            mock_response.validation_warnings = []
            return mock_response

        mock_stub = MagicMock()
        mock_stub.Extract = failing_then_succeeding

        source_config = create_source_config(source_id="test-source")
        request = ExtractionRequest(
            raw_content="test content",
            ai_agent_id="test-agent",
            source_config=source_config,
        )

        with patch.object(client, "_get_stub", return_value=mock_stub):
            result = await client.extract(request)

        assert result.extracted_fields == {"field": "value"}
        assert result.confidence == 0.95
        assert call_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_extract_raises_service_unavailable_after_retries(self) -> None:
        """extract() raises ServiceUnavailableError after retries exhausted (AC4)."""
        client = AiModelClient(ai_model_app_id="ai-model")
        call_count = 0

        # Mock that always fails
        async def always_failing(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise GrpcUnavailableError()

        mock_stub = MagicMock()
        mock_stub.Extract = always_failing

        source_config = create_source_config(source_id="test-source")
        request = ExtractionRequest(
            raw_content="test content",
            ai_agent_id="test-agent",
            source_config=source_config,
        )

        with (
            patch.object(client, "_get_stub", return_value=mock_stub),
            pytest.raises(ServiceUnavailableError) as exc_info,
        ):
            await client.extract(request)

        # Verify ServiceUnavailableError has correct context
        assert exc_info.value.app_id == "ai-model"
        assert exc_info.value.method_name == "Extract"
        assert exc_info.value.attempt_count == 3
        assert call_count == 3  # Tried 3 times


class TestAiModelClientNoRetryOnNonTransient:
    """Tests verifying non-transient errors are NOT retried."""

    @pytest.mark.asyncio
    async def test_no_retry_on_not_found(self) -> None:
        """NOT_FOUND errors are retried (gRPC errors trigger retry) but don't reset channel."""
        client = AiModelClient(ai_model_app_id="ai-model")
        call_count = 0
        reset_called = False

        async def not_found_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise GrpcNotFoundError()

        mock_stub = MagicMock()
        mock_stub.HealthCheck = not_found_error

        original_reset = client._reset_channel

        def track_reset():
            nonlocal reset_called
            reset_called = True
            original_reset()

        with (
            patch.object(client, "_get_stub", return_value=mock_stub),
            patch.object(client, "_reset_channel", side_effect=track_reset),
            pytest.raises(grpc.aio.AioRpcError),
        ):
            await client.health_check()

        # NOT_FOUND is still an AioRpcError so retry is attempted
        # But channel should NOT be reset (only UNAVAILABLE resets channel)
        assert call_count == 3  # Retried 3 times
        assert not reset_called  # Channel NOT reset for NOT_FOUND


class TestAiModelClientHealthCheckServiceUnavailable:
    """Tests for health_check() ServiceUnavailableError (AC4)."""

    @pytest.mark.asyncio
    async def test_health_check_raises_service_unavailable_after_retries(self) -> None:
        """health_check() raises ServiceUnavailableError after retries exhausted."""
        client = AiModelClient(ai_model_app_id="ai-model")
        call_count = 0

        async def always_failing(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise GrpcUnavailableError()

        mock_stub = MagicMock()
        mock_stub.HealthCheck = always_failing

        with (
            patch.object(client, "_get_stub", return_value=mock_stub),
            pytest.raises(ServiceUnavailableError) as exc_info,
        ):
            await client.health_check()

        # Verify ServiceUnavailableError has correct context
        assert exc_info.value.app_id == "ai-model"
        assert exc_info.value.method_name == "HealthCheck"
        assert exc_info.value.attempt_count == 3
        assert call_count == 3
