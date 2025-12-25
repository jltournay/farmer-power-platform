"""MCP infrastructure for AI agent tool invocation via DAPR.

Provides:
- GrpcMcpClient: Raw gRPC calls to MCP servers via DAPR service invocation
- GrpcMcpTool: LangChain BaseTool wrapper for MCP tools
- McpToolRegistry: Tool discovery and registration
- McpToolError: Exception class for tool execution failures
- ErrorCode: Error code enum matching proto definition
"""

from fp_common.mcp.client import GrpcMcpClient
from fp_common.mcp.errors import ErrorCode, McpToolError
from fp_common.mcp.registry import McpToolRegistry
from fp_common.mcp.tool import GrpcMcpTool

__all__ = [
    "ErrorCode",
    "GrpcMcpClient",
    "GrpcMcpTool",
    "McpToolRegistry",
    "McpToolError",
]
