"""Agent tool provider for resolving MCP tools from agent config.

Bridges agent configuration to actual tool instances that can be
used in LangGraph workflows.

Story 0.75.8b: MCP Client Integration for Agent Workflows
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_model.domain.agent_config import AgentConfig
    from ai_model.mcp.integration import McpIntegration
    from fp_common.mcp import GrpcMcpTool

logger = logging.getLogger(__name__)


class AgentToolProvider:
    """Resolves agent config's mcp_sources to LangChain tools.

    This class bridges agent configuration to actual tool instances
    that can be used in LangGraph workflows.

    Attributes:
        _integration: McpIntegration instance for tool resolution
    """

    def __init__(self, integration: McpIntegration) -> None:
        """Initialize provider with MCP integration.

        Args:
            integration: McpIntegration instance for tool resolution
        """
        self._integration = integration

    def get_tools_for_agent(
        self,
        agent_config: AgentConfig,
    ) -> list[GrpcMcpTool]:
        """Get all MCP tools configured for an agent.

        Iterates through the agent's mcp_sources configuration and
        resolves each tool reference to a GrpcMcpTool instance.

        Args:
            agent_config: Agent configuration with mcp_sources

        Returns:
            List of GrpcMcpTool instances ready for LangGraph

        Raises:
            ValueError: If a server is not registered
            RuntimeError: If tool resolution fails
        """
        tools: list[GrpcMcpTool] = []

        for source in agent_config.mcp_sources:
            server_name = source.server
            for tool_name in source.tools:
                tool = self._integration.get_tool(server_name, tool_name)
                tools.append(tool)
                logger.debug(
                    "Resolved tool %s from %s for agent %s",
                    tool_name,
                    server_name,
                    agent_config.agent_id,
                )

        logger.info(
            "Resolved %d MCP tools for agent %s",
            len(tools),
            agent_config.agent_id,
        )

        return tools
