"""MCP tool registry for tool discovery and management.

Provides McpToolRegistry for registering MCP servers and discovering available tools.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from fp_common.mcp.client import GrpcMcpClient
from fp_common.mcp.tool import GrpcMcpTool

logger = logging.getLogger(__name__)


class McpToolRegistry:
    """Registry for MCP servers and their tools.

    Provides tool discovery and caching for registered MCP servers.

    Attributes:
        _servers: Set of registered MCP server app_ids
        _tools_cache: Cached tool definitions by server app_id
        _clients: GrpcMcpClient instances by server app_id
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._servers: set[str] = set()
        self._tools_cache: dict[str, list[dict[str, Any]]] = {}
        self._clients: dict[str, GrpcMcpClient] = {}

    def register_server(self, app_id: str) -> None:
        """Register an MCP server for tool discovery.

        Args:
            app_id: DAPR app ID of the MCP server
        """
        self._servers.add(app_id)
        if app_id not in self._clients:
            self._clients[app_id] = GrpcMcpClient(app_id=app_id)
        logger.debug("Registered MCP server: %s", app_id)

    async def discover_tools(
        self,
        app_id: str,
        category: Optional[str] = None,
        refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """Discover available tools from an MCP server.

        Args:
            app_id: DAPR app ID of the MCP server
            category: Optional category filter
            refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of tool definitions

        Raises:
            ValueError: If app_id is not registered
        """
        if app_id not in self._servers:
            raise ValueError(f"MCP server '{app_id}' is not registered")

        cache_key = f"{app_id}:{category or 'all'}"

        if not refresh and cache_key in self._tools_cache:
            return self._tools_cache[cache_key]

        client = self._clients[app_id]
        tools = await client.list_tools(category=category)

        self._tools_cache[cache_key] = tools
        logger.debug(
            "Discovered %d tools from %s (category=%s)",
            len(tools),
            app_id,
            category or "all",
        )
        return tools

    async def discover_all_tools(
        self,
        refresh: bool = False,
    ) -> dict[str, list[dict[str, Any]]]:
        """Discover tools from all registered MCP servers concurrently.

        Args:
            refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dict mapping app_id to list of tool definitions
        """
        if not self._servers:
            return {}

        # Use asyncio.gather for concurrent discovery (per project-context.md)
        app_ids = list(self._servers)
        results = await asyncio.gather(
            *[self.discover_tools(app_id, refresh=refresh) for app_id in app_ids]
        )

        all_tools = dict(zip(app_ids, results))
        logger.debug("Discovered tools from %d servers", len(all_tools))
        return all_tools

    def get_tool(self, app_id: str, tool_name: str) -> GrpcMcpTool:
        """Get a GrpcMcpTool instance for a specific tool.

        Args:
            app_id: DAPR app ID of the MCP server
            tool_name: Name of the tool

        Returns:
            GrpcMcpTool instance ready for use with LangChain

        Raises:
            ValueError: If app_id is not registered or tool not found in cache
        """
        if app_id not in self._servers:
            raise ValueError(f"MCP server '{app_id}' is not registered")

        # Look for tool in cache
        cache_key = f"{app_id}:all"
        if cache_key not in self._tools_cache:
            raise ValueError(
                f"No tools cached for '{app_id}'. Call discover_tools first."
            )

        tools = self._tools_cache[cache_key]
        tool_def = next((t for t in tools if t["name"] == tool_name), None)

        if tool_def is None:
            raise ValueError(f"Tool '{tool_name}' not found in '{app_id}'")

        return GrpcMcpTool(
            name=tool_def["name"],
            description=tool_def["description"],
            mcp_client=self._clients[app_id],
        )
