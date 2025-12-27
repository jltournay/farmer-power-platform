"""Unit tests for IterationResolver (Story 2.7).

Tests cover MCP tool invocation for dynamic iteration:
- Calling MCP tools via DAPR Service Invocation
- Parsing tool results as iteration items
- Error handling for failed tool calls
- Linkage field extraction
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from collection_model.infrastructure.iteration_resolver import (
    IterationResolver,
    IterationResolverError,
)


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
        # Mock DAPR client
        mock_response = MagicMock()
        mock_response.data = b'{"success": true, "result_json": "[{\\"region_id\\": \\"nyeri\\", \\"latitude\\": -0.4167, \\"longitude\\": 36.95, \\"name\\": \\"Nyeri\\"}, {\\"region_id\\": \\"kericho\\", \\"latitude\\": -0.3689, \\"longitude\\": 35.2863, \\"name\\": \\"Kericho\\"}, {\\"region_id\\": \\"nandi\\", \\"latitude\\": 0.1833, \\"longitude\\": 35.1, \\"name\\": \\"Nandi\\"}]"}'

        with patch("collection_model.infrastructure.iteration_resolver.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_client.invoke_method.return_value = mock_response
            mock_dapr.return_value.__enter__.return_value = mock_client

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
        """Test resolve calls the correct MCP server and tool."""
        mock_response = MagicMock()
        mock_response.data = b'{"success": true, "result_json": "[]"}'

        with patch("collection_model.infrastructure.iteration_resolver.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_client.invoke_method.return_value = mock_response
            mock_dapr.return_value.__enter__.return_value = mock_client

            await iteration_resolver.resolve(sample_iteration_config)

        # Verify DAPR invocation
        mock_client.invoke_method.assert_called_once()
        call_kwargs = mock_client.invoke_method.call_args[1]
        assert call_kwargs["app_id"] == "plantation-mcp"
        assert call_kwargs["method_name"] == "CallTool"
        assert call_kwargs["content_type"] == "application/json"

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

        mock_response = MagicMock()
        mock_response.data = b'{"success": true, "result_json": "[]"}'

        with patch("collection_model.infrastructure.iteration_resolver.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_client.invoke_method.return_value = mock_response
            mock_dapr.return_value.__enter__.return_value = mock_client

            await iteration_resolver.resolve(config)

        # Verify arguments were passed
        call_kwargs = mock_client.invoke_method.call_args[1]
        request_data = call_kwargs["data"]
        assert '"tool_name": "get_farmers_by_region"' in request_data
        # Arguments are JSON-encoded, so they appear escaped in the string
        assert "region_id" in request_data
        assert "nyeri" in request_data

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

        mock_response = MagicMock()
        mock_response.data = b'{"success": true, "result_json": "{\\"regions\\": [{\\"id\\": 1}, {\\"id\\": 2}]}"}'

        with patch("collection_model.infrastructure.iteration_resolver.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_client.invoke_method.return_value = mock_response
            mock_dapr.return_value.__enter__.return_value = mock_client

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
        mock_response = MagicMock()
        mock_response.data = (
            b'{"success": false, "error_code": 3, "error_message": "Unknown tool: list_active_regions"}'
        )

        with patch("collection_model.infrastructure.iteration_resolver.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_client.invoke_method.return_value = mock_response
            mock_dapr.return_value.__enter__.return_value = mock_client

            with pytest.raises(IterationResolverError) as exc_info:
                await iteration_resolver.resolve(sample_iteration_config)

        assert "tool not found" in str(exc_info.value).lower() or "Unknown tool" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_raises_on_mcp_failure(
        self,
        iteration_resolver: IterationResolver,
        sample_iteration_config: dict[str, Any],
    ) -> None:
        """Test resolve raises error on MCP service failure."""
        mock_response = MagicMock()
        mock_response.data = b'{"success": false, "error_code": 2, "error_message": "Service unavailable"}'

        with patch("collection_model.infrastructure.iteration_resolver.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_client.invoke_method.return_value = mock_response
            mock_dapr.return_value.__enter__.return_value = mock_client

            with pytest.raises(IterationResolverError) as exc_info:
                await iteration_resolver.resolve(sample_iteration_config)

        assert "Service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_raises_on_connection_error(
        self,
        iteration_resolver: IterationResolver,
        sample_iteration_config: dict[str, Any],
    ) -> None:
        """Test resolve raises error on DAPR connection failure."""
        with patch("collection_model.infrastructure.iteration_resolver.DaprClient") as mock_dapr:
            mock_dapr.return_value.__enter__.side_effect = Exception("Connection refused")

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
        mock_response = MagicMock()
        mock_response.data = b'{"success": true, "result_json": "[]"}'

        with patch("collection_model.infrastructure.iteration_resolver.DaprClient") as mock_dapr:
            mock_client = MagicMock()
            mock_client.invoke_method.return_value = mock_response
            mock_dapr.return_value.__enter__.return_value = mock_client

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
