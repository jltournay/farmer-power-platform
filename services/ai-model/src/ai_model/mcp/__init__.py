"""MCP integration for AI Model agent workflows.

This package provides the integration layer between AI Model agents
and the MCP client infrastructure in fp_common.mcp.

Components:
- McpIntegration: Server registration and tool discovery
- AgentToolProvider: Resolves agent config mcp_sources to tools
- ServerStatus: Enum for server discovery status

Story 0.75.8b: MCP Client Integration for Agent Workflows
"""

from ai_model.mcp.integration import McpIntegration, ServerStatus
from ai_model.mcp.provider import AgentToolProvider

__all__ = [
    "AgentToolProvider",
    "McpIntegration",
    "ServerStatus",
]
