"""Tests for McpToolRegistry.

Tests cover:
- AC #3: Tool discovery and registration
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fp_common.mcp.registry import McpToolRegistry


class TestMcpToolRegistryInit:
    """Tests for McpToolRegistry initialization."""

    def test_registry_initializes_empty(self) -> None:
        """Registry initializes with no registered servers."""
        registry = McpToolRegistry()
        assert len(registry._servers) == 0

    def test_registry_register_server(self) -> None:
        """Registry can register an MCP server by app_id."""
        registry = McpToolRegistry()
        registry.register_server("plantation-mcp")

        assert "plantation-mcp" in registry._servers


class TestMcpToolRegistryDiscovery:
    """Tests for McpToolRegistry tool discovery."""

    @pytest.mark.asyncio
    async def test_discover_tools_from_server(self) -> None:
        """AC #3: Registry discovers tools from registered MCP server."""
        mock_tools = [
            {
                "name": "get_farmer_by_id",
                "description": "Get farmer by ID",
                "input_schema": {"type": "object"},
                "category": "query",
            },
        ]

        with patch("fp_common.mcp.registry.GrpcMcpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=mock_tools)
            mock_client_class.return_value = mock_client

            registry = McpToolRegistry()
            registry.register_server("plantation-mcp")

            tools = await registry.discover_tools("plantation-mcp")

            assert len(tools) == 1
            assert tools[0]["name"] == "get_farmer_by_id"

    @pytest.mark.asyncio
    async def test_discover_all_tools(self) -> None:
        """Registry discovers tools from all registered servers."""
        plantation_tools = [
            {"name": "get_farmer", "description": "Get farmer", "input_schema": {}, "category": "query"},
        ]
        collection_tools = [
            {"name": "get_document", "description": "Get document", "input_schema": {}, "category": "query"},
        ]

        with patch("fp_common.mcp.registry.GrpcMcpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.list_tools = AsyncMock(side_effect=[plantation_tools, collection_tools])
            mock_client_class.return_value = mock_client

            registry = McpToolRegistry()
            registry.register_server("plantation-mcp")
            registry.register_server("collection-mcp")

            all_tools = await registry.discover_all_tools()

            assert len(all_tools) == 2
            assert "plantation-mcp" in all_tools
            assert "collection-mcp" in all_tools


class TestMcpToolRegistryCaching:
    """Tests for McpToolRegistry caching."""

    @pytest.mark.asyncio
    async def test_tools_are_cached(self) -> None:
        """AC #6.4: Tool definitions are cached after discovery."""
        mock_tools = [
            {"name": "get_farmer", "description": "Get farmer", "input_schema": {}, "category": "query"},
        ]

        with patch("fp_common.mcp.registry.GrpcMcpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=mock_tools)
            mock_client_class.return_value = mock_client

            registry = McpToolRegistry()
            registry.register_server("plantation-mcp")

            # First call - should hit MCP server
            await registry.discover_tools("plantation-mcp")
            assert mock_client.list_tools.call_count == 1

            # Second call - should use cache
            await registry.discover_tools("plantation-mcp")
            assert mock_client.list_tools.call_count == 1  # Still 1

    @pytest.mark.asyncio
    async def test_cache_can_be_bypassed(self) -> None:
        """Cache can be bypassed with refresh=True."""
        mock_tools = [
            {"name": "get_farmer", "description": "Get farmer", "input_schema": {}, "category": "query"},
        ]

        with patch("fp_common.mcp.registry.GrpcMcpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.list_tools = AsyncMock(return_value=mock_tools)
            mock_client_class.return_value = mock_client

            registry = McpToolRegistry()
            registry.register_server("plantation-mcp")

            # First call
            await registry.discover_tools("plantation-mcp")
            # Force refresh
            await registry.discover_tools("plantation-mcp", refresh=True)

            assert mock_client.list_tools.call_count == 2


class TestMcpToolRegistryGetTool:
    """Tests for McpToolRegistry.get_tool method."""

    @pytest.mark.asyncio
    async def test_get_tool_returns_grpc_mcp_tool(self) -> None:
        """get_tool returns a GrpcMcpTool instance."""
        from fp_common.mcp.client import GrpcMcpClient
        from fp_common.mcp.tool import GrpcMcpTool

        mock_tools = [
            {
                "name": "get_farmer",
                "description": "Get farmer by ID",
                "input_schema": {"type": "object"},
                "category": "query",
            },
        ]

        with patch("fp_common.mcp.registry.GrpcMcpClient") as mock_client_class:
            # Create a mock that passes Pydantic validation
            mock_client = MagicMock(spec=GrpcMcpClient)
            mock_client.app_id = "plantation-mcp"
            mock_client.list_tools = AsyncMock(return_value=mock_tools)
            mock_client_class.return_value = mock_client

            registry = McpToolRegistry()
            registry.register_server("plantation-mcp")

            await registry.discover_tools("plantation-mcp")
            tool = registry.get_tool("plantation-mcp", "get_farmer")

            assert isinstance(tool, GrpcMcpTool)
            assert tool.name == "get_farmer"
            assert tool.description == "Get farmer by ID"
