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

import pytest
from collection_model.infrastructure.iteration_resolver import (
    IterationResolver,
    IterationResolverError,
)


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
    def sample_iteration_config(self) -> dict[str, Any]:
        """Sample iteration config for weather data."""
        return {
            "foreach": "region",
            "source_mcp": "plantation-mcp",
            "source_tool": "list_active_regions",
            "tool_arguments": {},
            "inject_linkage": ["region_id", "name"],
            "concurrency": 5,
        }

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
        sample_iteration_config: dict[str, Any],
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
        sample_iteration_config: dict[str, Any],
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
        """Test resolve passes tool arguments to MCP."""
        config = {
            "source_mcp": "plantation-mcp",
            "source_tool": "get_farmers_by_region",
            "tool_arguments": {"region_id": "nyeri"},
        }

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

        # Verify request was created with correct tool_name and arguments
        mock_request_class.assert_called_once()
        call_kwargs = mock_request_class.call_args.kwargs
        assert call_kwargs["tool_name"] == "get_farmers_by_region"
        assert "nyeri" in call_kwargs["arguments_json"]

    @pytest.mark.asyncio
    async def test_resolve_handles_nested_result(
        self,
        iteration_resolver: IterationResolver,
    ) -> None:
        """Test resolve handles results nested in a 'regions' key."""
        config = {
            "source_mcp": "plantation-mcp",
            "source_tool": "list_regions",
            "result_path": "regions",  # Path to extract from result
        }

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
        sample_iteration_config: dict[str, Any],
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
        sample_iteration_config: dict[str, Any],
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
        sample_iteration_config: dict[str, Any],
    ) -> None:
        """Test resolve raises error on gRPC connection failure."""
        with patch("grpc.aio.insecure_channel") as mock_channel:
            # Simulate connection error when entering async context
            mock_channel.return_value.__aenter__ = AsyncMock(side_effect=Exception("Connection refused"))
            mock_channel.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(IterationResolverError) as exc_info:
                await iteration_resolver.resolve(sample_iteration_config)

        assert "Connection refused" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_returns_empty_list_for_no_results(
        self,
        iteration_resolver: IterationResolver,
        sample_iteration_config: dict[str, Any],
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
