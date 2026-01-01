"""Unit tests for IterationResolver (Story 2.7, updated Story 0.4.6).

Tests cover MCP tool invocation for dynamic iteration:
- Calling MCP tools via DAPR gRPC proxying
- Parsing tool results as iteration items
- Error handling for failed tool calls
- Linkage field extraction

Note: Tests mock the gRPC channel and stub to simulate DAPR gRPC proxying.
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest
from collection_model.infrastructure.iteration_resolver import (
    IterationResolver,
    IterationResolverError,
    ServiceUnavailableError,
)
from fp_common.models.source_config import IterationConfig


def _create_mock_response(
    success: bool = True,
    result_json: str = "[]",
    error_message: str = "",
) -> MagicMock:
    """Create a mock gRPC response that mimics ToolCallResponse protobuf."""
    mock = MagicMock()
    mock.success = success
    mock.result_json = result_json
    mock.error_message = error_message
    return mock


class TestIterationResolver:
    """Tests for IterationResolver."""

    @pytest.fixture
    def iteration_resolver(self) -> IterationResolver:
        """Create IterationResolver."""
        return IterationResolver()

    @pytest.fixture
    def sample_iteration_config(self) -> IterationConfig:
        """Sample iteration config for weather data."""
        return IterationConfig.model_validate(
            {
                "foreach": "region",
                "source_mcp": "plantation-mcp",
                "source_tool": "list_active_regions",
                "concurrency": 5,
            }
        )

    @pytest.fixture
    def sample_mcp_response(self) -> list[dict[str, Any]]:
        """Sample MCP tool response - list of regions."""
        return [
            {
                "region_id": "nyeri",
                "latitude": -0.4167,
                "longitude": 36.9500,
                "name": "Nyeri",
            },
            {
                "region_id": "kericho",
                "latitude": -0.3689,
                "longitude": 35.2863,
                "name": "Kericho",
            },
            {
                "region_id": "nandi",
                "latitude": 0.1833,
                "longitude": 35.1000,
                "name": "Nandi",
            },
        ]

    @pytest.mark.asyncio
    async def test_resolve_returns_items_from_mcp_tool(
        self,
        iteration_resolver: IterationResolver,
        sample_iteration_config: IterationConfig,
        sample_mcp_response: list[dict[str, Any]],
    ) -> None:
        """Test resolve returns items from MCP tool call."""
        mock_response = _create_mock_response(
            success=True,
            result_json=json.dumps(sample_mcp_response),
        )

        # Mock the gRPC channel and stub for DAPR gRPC proxying
        mock_stub = MagicMock()
        mock_stub.CallTool = AsyncMock(return_value=mock_response)

        with patch("grpc.aio.insecure_channel") as mock_channel:
            mock_channel.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_channel.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch(
                "collection_model.infrastructure.iteration_resolver.mcp_tool_pb2_grpc.McpToolServiceStub",
                return_value=mock_stub,
            ):
                items = await iteration_resolver.resolve(sample_iteration_config)

        assert len(items) == 3
        assert items[0]["region_id"] == "nyeri"
        assert items[1]["region_id"] == "kericho"
        assert items[2]["region_id"] == "nandi"

    @pytest.mark.asyncio
    async def test_resolve_calls_correct_mcp_tool(
        self,
        iteration_resolver: IterationResolver,
        sample_iteration_config: IterationConfig,
    ) -> None:
        """Test resolve calls the correct MCP server and tool via DAPR metadata."""
        mock_response = _create_mock_response(success=True, result_json="[]")

        mock_stub = MagicMock()
        mock_stub.CallTool = AsyncMock(return_value=mock_response)

        with patch("grpc.aio.insecure_channel") as mock_channel:
            mock_channel.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_channel.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch(
                "collection_model.infrastructure.iteration_resolver.mcp_tool_pb2_grpc.McpToolServiceStub",
                return_value=mock_stub,
            ):
                await iteration_resolver.resolve(sample_iteration_config)

        # Verify gRPC call with DAPR metadata
        mock_stub.CallTool.assert_called_once()
        call_args = mock_stub.CallTool.call_args
        # Check metadata contains dapr-app-id
        metadata = call_args.kwargs.get("metadata", [])
        assert ("dapr-app-id", "plantation-mcp") in metadata

    @pytest.mark.asyncio
    async def test_resolve_passes_tool_arguments(
        self,
        iteration_resolver: IterationResolver,
    ) -> None:
        """Test resolve calls correct tool name and uses default arguments."""
        # Create IterationConfig for testing
        config = IterationConfig.model_validate(
            {
                "foreach": "farmers",
                "source_mcp": "plantation-mcp",
                "source_tool": "get_farmers_by_region",
                "concurrency": 5,
            }
        )

        mock_response = _create_mock_response(success=True, result_json="[]")

        mock_stub = MagicMock()
        mock_stub.CallTool = AsyncMock(return_value=mock_response)

        with patch("grpc.aio.insecure_channel") as mock_channel:
            mock_channel.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_channel.return_value.__aexit__ = AsyncMock(return_value=None)
            with (
                patch(
                    "collection_model.infrastructure.iteration_resolver.mcp_tool_pb2_grpc.McpToolServiceStub",
                    return_value=mock_stub,
                ) as mock_stub_class,
                patch(
                    "collection_model.infrastructure.iteration_resolver.mcp_tool_pb2.ToolCallRequest"
                ) as mock_request_class,
            ):
                mock_request = MagicMock()
                mock_request_class.return_value = mock_request
                await iteration_resolver.resolve(config)

        # Verify request was created with correct tool_name
        mock_request_class.assert_called_once()
        call_kwargs = mock_request_class.call_args.kwargs
        assert call_kwargs["tool_name"] == "get_farmers_by_region"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="result_path not in IterationConfig model - requires model extension")
    async def test_resolve_handles_nested_result(
        self,
        iteration_resolver: IterationResolver,
    ) -> None:
        """Test resolve handles results nested in a 'regions' key.

        Note: This test is skipped because IterationConfig doesn't have a
        result_path field. If this feature is needed, add result_path to
        the IterationConfig model in fp_common/models/source_config.py.
        """
        # Create IterationConfig for testing
        config = IterationConfig.model_validate(
            {
                "foreach": "regions",
                "source_mcp": "plantation-mcp",
                "source_tool": "list_regions",
                "concurrency": 5,
            }
        )

        mock_response = _create_mock_response(
            success=True,
            result_json=json.dumps({"regions": [{"id": 1}, {"id": 2}]}),
        )

        mock_stub = MagicMock()
        mock_stub.CallTool = AsyncMock(return_value=mock_response)

        with patch("grpc.aio.insecure_channel") as mock_channel:
            mock_channel.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_channel.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch(
                "collection_model.infrastructure.iteration_resolver.mcp_tool_pb2_grpc.McpToolServiceStub",
                return_value=mock_stub,
            ):
                items = await iteration_resolver.resolve(config)

        assert len(items) == 2
        assert items[0]["id"] == 1
        assert items[1]["id"] == 2

    @pytest.mark.asyncio
    async def test_resolve_raises_on_tool_not_found(
        self,
        iteration_resolver: IterationResolver,
        sample_iteration_config: IterationConfig,
    ) -> None:
        """Test resolve raises error when MCP tool not found."""
        mock_response = _create_mock_response(
            success=False,
            error_message="Unknown tool: list_active_regions",
        )

        mock_stub = MagicMock()
        mock_stub.CallTool = AsyncMock(return_value=mock_response)

        with patch("grpc.aio.insecure_channel") as mock_channel:
            mock_channel.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_channel.return_value.__aexit__ = AsyncMock(return_value=None)
            with (
                patch(
                    "collection_model.infrastructure.iteration_resolver.mcp_tool_pb2_grpc.McpToolServiceStub",
                    return_value=mock_stub,
                ),
                pytest.raises(IterationResolverError) as exc_info,
            ):
                await iteration_resolver.resolve(sample_iteration_config)

        assert "tool not found" in str(exc_info.value).lower() or "Unknown tool" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_raises_on_mcp_failure(
        self,
        iteration_resolver: IterationResolver,
        sample_iteration_config: IterationConfig,
    ) -> None:
        """Test resolve raises error on MCP service failure."""
        mock_response = _create_mock_response(
            success=False,
            error_message="Service unavailable",
        )

        mock_stub = MagicMock()
        mock_stub.CallTool = AsyncMock(return_value=mock_response)

        with patch("grpc.aio.insecure_channel") as mock_channel:
            mock_channel.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_channel.return_value.__aexit__ = AsyncMock(return_value=None)
            with (
                patch(
                    "collection_model.infrastructure.iteration_resolver.mcp_tool_pb2_grpc.McpToolServiceStub",
                    return_value=mock_stub,
                ),
                pytest.raises(IterationResolverError) as exc_info,
            ):
                await iteration_resolver.resolve(sample_iteration_config)

        assert "Service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_raises_on_connection_error(
        self,
        iteration_resolver: IterationResolver,
        sample_iteration_config: IterationConfig,
    ) -> None:
        """Test resolve raises error on gRPC connection failure."""

        # Simulate connection error when getting stub
        async def raise_connection_error():
            raise Exception("Connection refused")

        with (
            patch.object(iteration_resolver, "_get_stub", side_effect=raise_connection_error),
            pytest.raises(IterationResolverError) as exc_info,
        ):
            await iteration_resolver.resolve(sample_iteration_config)

        assert "Connection refused" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_returns_empty_list_for_no_results(
        self,
        iteration_resolver: IterationResolver,
        sample_iteration_config: IterationConfig,
    ) -> None:
        """Test resolve returns empty list when MCP returns no items."""
        mock_response = _create_mock_response(success=True, result_json="[]")

        mock_stub = MagicMock()
        mock_stub.CallTool = AsyncMock(return_value=mock_response)

        with patch("grpc.aio.insecure_channel") as mock_channel:
            mock_channel.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_channel.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch(
                "collection_model.infrastructure.iteration_resolver.mcp_tool_pb2_grpc.McpToolServiceStub",
                return_value=mock_stub,
            ):
                items = await iteration_resolver.resolve(sample_iteration_config)

        assert items == []


class TestIterationResolverLinkageExtraction:
    """Tests for linkage field extraction from iteration items."""

    @pytest.fixture
    def iteration_resolver(self) -> IterationResolver:
        """Create IterationResolver."""
        return IterationResolver()

    def test_extract_linkage_fields(
        self,
        iteration_resolver: IterationResolver,
    ) -> None:
        """Test extracting specified linkage fields from item."""
        item = {
            "region_id": "nyeri",
            "latitude": -0.4167,
            "longitude": 36.9500,
            "name": "Nyeri",
            "internal_code": "KE-NYR",
        }
        inject_fields = ["region_id", "name"]

        linkage = iteration_resolver.extract_linkage(item, inject_fields)

        assert linkage == {"region_id": "nyeri", "name": "Nyeri"}
        assert "latitude" not in linkage
        assert "internal_code" not in linkage

    def test_extract_linkage_handles_missing_fields(
        self,
        iteration_resolver: IterationResolver,
    ) -> None:
        """Test extracting linkage ignores missing fields."""
        item = {"region_id": "nyeri", "name": "Nyeri"}
        inject_fields = ["region_id", "name", "missing_field"]

        linkage = iteration_resolver.extract_linkage(item, inject_fields)

        assert linkage == {"region_id": "nyeri", "name": "Nyeri"}

    def test_extract_linkage_empty_fields(
        self,
        iteration_resolver: IterationResolver,
    ) -> None:
        """Test extracting linkage with empty field list."""
        item = {"region_id": "nyeri", "name": "Nyeri"}
        inject_fields: list[str] = []

        linkage = iteration_resolver.extract_linkage(item, inject_fields)

        assert linkage == {}

    def test_extract_linkage_none_fields(
        self,
        iteration_resolver: IterationResolver,
    ) -> None:
        """Test extracting linkage with None field list."""
        item = {"region_id": "nyeri", "name": "Nyeri"}

        linkage = iteration_resolver.extract_linkage(item, None)

        assert linkage == {}


# =============================================================================
# ADR-005: gRPC Client Retry and Singleton Channel Tests
# =============================================================================


class GrpcUnavailableError(grpc.aio.AioRpcError):
    """Test helper: Real AioRpcError subclass for UNAVAILABLE status."""

    def __init__(self) -> None:
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


class TestIterationResolverSingletonChannel:
    """Tests for singleton channel pattern (ADR-005)."""

    @pytest.mark.asyncio
    async def test_lazy_channel_initialization(self) -> None:
        """Channel is not created until first use."""
        resolver = IterationResolver()

        # Initially, channel and stub should be None
        assert resolver._channel is None
        assert resolver._stub is None

    @pytest.mark.asyncio
    async def test_singleton_channel_reused(self) -> None:
        """Same channel is reused across multiple _get_stub calls."""
        # Create a mock channel
        mock_channel = MagicMock(spec=grpc.aio.Channel)
        resolver = IterationResolver(channel=mock_channel)

        # First call creates stub
        stub1 = await resolver._get_stub()
        channel1 = resolver._channel

        # Second call reuses the same channel and stub
        stub2 = await resolver._get_stub()
        channel2 = resolver._channel

        assert channel1 is channel2
        assert stub1 is stub2

    @pytest.mark.asyncio
    async def test_channel_created_with_keepalive_options(self) -> None:
        """Channel is created with proper keepalive settings per ADR-005."""
        resolver = IterationResolver()

        with patch("grpc.aio.insecure_channel") as mock_create_channel:
            mock_channel = MagicMock(spec=grpc.aio.Channel)
            mock_create_channel.return_value = mock_channel

            await resolver._get_stub()

            # Verify channel was created with keepalive options
            mock_create_channel.assert_called_once()
            call_args = mock_create_channel.call_args
            assert call_args[0][0] == "localhost:50001"  # DAPR sidecar port
            options = dict(call_args[1]["options"])
            assert options["grpc.keepalive_time_ms"] == 30000
            assert options["grpc.keepalive_timeout_ms"] == 10000


class TestIterationResolverRetry:
    """Tests for Tenacity retry behavior (ADR-005)."""

    @pytest.fixture
    def sample_iteration_config(self) -> IterationConfig:
        """Sample iteration config for testing."""
        return IterationConfig.model_validate(
            {
                "foreach": "region",
                "source_mcp": "plantation-mcp",
                "source_tool": "list_active_regions",
                "concurrency": 5,
            }
        )

    @pytest.mark.asyncio
    async def test_retry_on_unavailable(
        self,
        sample_iteration_config: IterationConfig,
    ) -> None:
        """Retry triggers on UNAVAILABLE status code."""
        resolver = IterationResolver()
        call_count = 0

        # Create a mock that fails twice then succeeds
        async def failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise GrpcUnavailableError()
            # Return a successful response
            mock_response = MagicMock()
            mock_response.success = True
            mock_response.result_json = "[]"
            mock_response.error_message = ""
            return mock_response

        mock_stub = MagicMock()
        mock_stub.CallTool = failing_then_succeeding

        with patch.object(resolver, "_get_stub", return_value=mock_stub):
            result = await resolver.resolve(sample_iteration_config)

        assert result == []
        assert call_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_service_unavailable(
        self,
        sample_iteration_config: IterationConfig,
    ) -> None:
        """ServiceUnavailableError raised after max retries exhausted (AC4)."""
        resolver = IterationResolver()
        call_count = 0

        # Create a mock that always fails
        async def always_failing(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise GrpcUnavailableError()

        mock_stub = MagicMock()
        mock_stub.CallTool = always_failing

        with (
            patch.object(resolver, "_get_stub", return_value=mock_stub),
            pytest.raises(ServiceUnavailableError) as exc_info,
        ):
            await resolver.resolve(sample_iteration_config)

        # Verify ServiceUnavailableError has correct context
        assert exc_info.value.app_id == "plantation-mcp"
        assert exc_info.value.method_name == "CallTool"
        assert exc_info.value.attempt_count == 3
        assert call_count == 3  # Tried 3 times


class TestIterationResolverChannelRecreation:
    """Tests for channel recreation on error (ADR-005)."""

    @pytest.mark.asyncio
    async def test_reset_channel_clears_state(self) -> None:
        """_reset_channel clears both channel and stub."""
        mock_channel = MagicMock(spec=grpc.aio.Channel)
        resolver = IterationResolver(channel=mock_channel)

        # Initialize stub
        await resolver._get_stub()
        assert resolver._channel is not None
        assert resolver._stub is not None

        # Reset
        resolver._reset_channel()

        assert resolver._channel is None
        assert resolver._stub is None

    @pytest.mark.asyncio
    async def test_channel_recreation_after_reset(self) -> None:
        """New channel is created after reset."""
        resolver = IterationResolver()

        with patch("grpc.aio.insecure_channel") as mock_create_channel:
            # First call
            mock_channel1 = MagicMock(spec=grpc.aio.Channel)
            mock_create_channel.return_value = mock_channel1
            await resolver._get_stub()

            original_channel = resolver._channel
            assert original_channel is mock_channel1

            # Reset
            resolver._reset_channel()

            # Second call should create new channel
            mock_channel2 = MagicMock(spec=grpc.aio.Channel)
            mock_create_channel.return_value = mock_channel2
            await resolver._get_stub()

            assert resolver._channel is mock_channel2
            assert resolver._channel is not original_channel

    @pytest.mark.asyncio
    async def test_channel_reset_on_unavailable_error(self) -> None:
        """Channel is reset when UNAVAILABLE error occurs."""
        resolver = IterationResolver()
        reset_called = False

        config = IterationConfig.model_validate(
            {
                "foreach": "region",
                "source_mcp": "plantation-mcp",
                "source_tool": "list_active_regions",
                "concurrency": 5,
            }
        )

        # Mock the CallTool to raise UNAVAILABLE
        async def unavailable_error(*args, **kwargs):
            raise GrpcUnavailableError()

        mock_stub = MagicMock()
        mock_stub.CallTool = unavailable_error

        original_reset = resolver._reset_channel

        def track_reset():
            nonlocal reset_called
            reset_called = True
            original_reset()

        with (
            patch.object(resolver, "_get_stub", return_value=mock_stub),
            patch.object(resolver, "_reset_channel", side_effect=track_reset),
            pytest.raises(ServiceUnavailableError),
        ):
            await resolver.resolve(config)

        # _reset_channel should have been called due to UNAVAILABLE
        assert reset_called


class TestIterationResolverNoRetryOnNonTransient:
    """Tests verifying non-transient errors don't reset channel."""

    @pytest.mark.asyncio
    async def test_no_channel_reset_on_not_found(self) -> None:
        """NOT_FOUND errors don't reset channel."""
        resolver = IterationResolver()
        call_count = 0
        reset_called = False

        config = IterationConfig.model_validate(
            {
                "foreach": "region",
                "source_mcp": "plantation-mcp",
                "source_tool": "list_active_regions",
                "concurrency": 5,
            }
        )

        async def not_found_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise GrpcNotFoundError()

        mock_stub = MagicMock()
        mock_stub.CallTool = not_found_error

        original_reset = resolver._reset_channel

        def track_reset():
            nonlocal reset_called
            reset_called = True
            original_reset()

        with (
            patch.object(resolver, "_get_stub", return_value=mock_stub),
            patch.object(resolver, "_reset_channel", side_effect=track_reset),
            pytest.raises(grpc.aio.AioRpcError),
        ):
            await resolver.resolve(config)

        # NOT_FOUND still retries (any AioRpcError), but channel should NOT be reset
        assert call_count == 3  # Retried 3 times
        assert not reset_called  # Channel NOT reset for NOT_FOUND


class TestIterationResolverClose:
    """Tests for resource cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_channel(self) -> None:
        """close() properly cleans up the channel."""
        mock_channel = AsyncMock(spec=grpc.aio.Channel)
        resolver = IterationResolver(channel=mock_channel)

        # Initialize stub
        await resolver._get_stub()
        assert resolver._channel is not None

        # Close
        await resolver.close()

        mock_channel.close.assert_called_once()
        assert resolver._channel is None
        assert resolver._stub is None

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self) -> None:
        """close() can be called multiple times safely."""
        resolver = IterationResolver()

        # Close without ever initializing
        await resolver.close()
        assert resolver._channel is None

        # Close again
        await resolver.close()
        assert resolver._channel is None


class TestIterationResolverMetadata:
    """Tests for DAPR metadata handling."""

    def test_get_metadata_returns_app_id(self) -> None:
        """_get_metadata returns proper DAPR app-id."""
        resolver = IterationResolver()

        metadata = resolver._get_metadata("test-mcp-server")

        assert metadata == [("dapr-app-id", "test-mcp-server")]


class TestServiceUnavailableError:
    """Tests for ServiceUnavailableError exception."""

    def test_error_includes_context(self) -> None:
        """Exception includes app_id, method_name, and attempt_count."""
        error = ServiceUnavailableError(
            message="Connection failed",
            app_id="plantation-mcp",
            method_name="CallTool",
            attempt_count=3,
        )

        assert error.app_id == "plantation-mcp"
        assert error.method_name == "CallTool"
        assert error.attempt_count == 3
        assert "plantation-mcp" in str(error)
        assert "CallTool" in str(error)
        assert "3" in str(error)
