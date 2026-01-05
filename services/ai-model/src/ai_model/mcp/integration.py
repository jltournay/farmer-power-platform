"""MCP integration for AI Model service.

Manages MCP server registration and tool discovery for AI agents.
Uses fp_common.mcp infrastructure - this is an integration layer,
NOT a reimplementation.

Story 0.75.8b: MCP Client Integration for Agent Workflows
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from fp_common.mcp import GrpcMcpTool, McpToolRegistry

if TYPE_CHECKING:
    from ai_model.domain.agent_config import AgentConfig

logger = logging.getLogger(__name__)


# Server name to DAPR app-id mapping
# Agent configs use short names, DAPR requires full app-id
SERVER_APP_ID_MAP: dict[str, str] = {
    "collection": "collection-mcp",
    "plantation": "plantation-mcp",
    # Add more as MCP servers are created
}


class ServerStatus(str, Enum):
    """Status of MCP server discovery."""

    REGISTERED = "registered"
    DISCOVERY_PENDING = "discovery_pending"
    READY = "ready"
    UNAVAILABLE = "unavailable"


class McpIntegration:
    """Manages MCP server registration and tool discovery for AI Model.

    Uses fp_common.mcp infrastructure - this is an integration layer,
    NOT a reimplementation.

    Attributes:
        _registry: McpToolRegistry instance for tool management
        _registered_servers: Set of registered server app-ids
        _server_status: Status tracking for each server
        _last_discovery: Timestamp of last tool discovery
        _cache_ttl_seconds: TTL for tool cache in seconds
    """

    def __init__(
        self,
        registry: McpToolRegistry | None = None,
        cache_ttl_seconds: int = 300,
    ) -> None:
        """Initialize MCP integration.

        Args:
            registry: Optional McpToolRegistry instance (creates new if None)
            cache_ttl_seconds: TTL for discovered tools cache (default 5 minutes)
        """
        self._registry = registry or McpToolRegistry()
        self._registered_servers: set[str] = set()
        self._server_status: dict[str, ServerStatus] = {}
        self._last_discovery: datetime | None = None
        self._cache_ttl_seconds = cache_ttl_seconds

    def register_from_agent_configs(
        self,
        agent_configs: list[AgentConfig],
    ) -> set[str]:
        """Extract unique MCP servers from all agent configs and register them.

        Parses mcp_sources from each agent config and registers the servers
        with the McpToolRegistry. Duplicate servers are automatically deduplicated.

        Args:
            agent_configs: List of agent configurations

        Returns:
            Set of registered server app-ids
        """
        servers_to_register: set[str] = set()

        for config in agent_configs:
            for source in config.mcp_sources:
                # Map server name to DAPR app-id
                server_name = source.server
                app_id = SERVER_APP_ID_MAP.get(server_name, f"{server_name}-mcp")
                servers_to_register.add(app_id)

        # Register each unique server
        for app_id in servers_to_register:
            if app_id not in self._registered_servers:
                self._registry.register_server(app_id)
                self._registered_servers.add(app_id)
                self._server_status[app_id] = ServerStatus.REGISTERED
                logger.debug("Registered MCP server: %s", app_id)

        logger.info(
            "Registered %d MCP servers from agent configs: %s",
            len(servers_to_register),
            list(servers_to_register),
        )

        return servers_to_register

    async def discover_all_tools(
        self,
        refresh: bool = False,
    ) -> dict[str, list[dict[str, Any]]]:
        """Discover tools from all registered servers.

        Uses caching with configurable TTL. Handles server unavailability
        gracefully by marking servers as pending and logging warnings.

        Args:
            refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dict mapping app-id to list of tool definitions
        """
        # Check if cache is valid
        if not refresh and self._last_discovery is not None:
            elapsed = (datetime.now(UTC) - self._last_discovery).total_seconds()
            if elapsed < self._cache_ttl_seconds:
                logger.debug("Using cached tool discovery (age: %.1fs)", elapsed)
                # Return empty dict if no servers registered
                if not self._registered_servers:
                    return {}
                # Cache is in registry, just indicate we're using it
                try:
                    return await self._registry.discover_all_tools(refresh=False)
                except Exception:
                    # If cache access fails, proceed with fresh discovery
                    pass

        # Perform fresh discovery
        try:
            all_tools = await self._registry.discover_all_tools(refresh=refresh)
            self._last_discovery = datetime.now(UTC)

            # Update server statuses
            for app_id in all_tools:
                self._server_status[app_id] = ServerStatus.READY

            logger.info(
                "Discovered tools from %d MCP servers: %s",
                len(all_tools),
                {k: len(v) for k, v in all_tools.items()},
            )

            return all_tools

        except Exception as e:
            logger.warning(
                "MCP tool discovery failed: %s (servers: %s)",
                str(e),
                list(self._registered_servers),
            )
            # Mark servers as pending (will retry on first access)
            for app_id in self._registered_servers:
                if self._server_status.get(app_id) != ServerStatus.READY:
                    self._server_status[app_id] = ServerStatus.DISCOVERY_PENDING
            return {}

    def get_tool(self, server: str, tool_name: str) -> GrpcMcpTool:
        """Get a specific tool from a registered server.

        Args:
            server: Server name (short form, e.g., 'collection')
            tool_name: Name of the tool to retrieve

        Returns:
            GrpcMcpTool instance ready for LangGraph

        Raises:
            ValueError: If server is not registered or tool not found
        """
        # Map server name to app-id
        app_id = SERVER_APP_ID_MAP.get(server, f"{server}-mcp")

        if app_id not in self._registered_servers:
            raise ValueError(f"MCP server '{server}' (app-id: {app_id}) is not registered")

        return self._registry.get_tool(app_id, tool_name)

    @property
    def registered_servers(self) -> set[str]:
        """Get set of registered server app-ids."""
        return self._registered_servers.copy()

    @property
    def server_status(self) -> dict[str, ServerStatus]:
        """Get status of all registered servers."""
        return self._server_status.copy()
