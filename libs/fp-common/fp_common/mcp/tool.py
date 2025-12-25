"""LangChain tool wrapper for gRPC MCP tools.

Provides GrpcMcpTool for integrating MCP tools with LangChain agents.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from fp_common.mcp.client import GrpcMcpClient  # noqa: TC001
from fp_common.mcp.errors import McpToolError


class GrpcMcpTool(BaseTool):
    """LangChain tool wrapper for gRPC MCP tools.

    Wraps a GrpcMcpClient to provide a standard LangChain tool interface
    for AI agents to invoke MCP server tools.

    Attributes:
        name: Tool name (passed to MCP server)
        description: Tool description for LLM
        mcp_client: GrpcMcpClient instance for invoking tools
        args_schema: Optional Pydantic model for argument validation
        raise_on_error: If True, raise McpToolError instead of returning error JSON
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description for LLM")
    mcp_client: GrpcMcpClient = Field(exclude=True)
    args_schema: type[BaseModel] | None = None
    raise_on_error: bool = Field(
        default=False,
        description="If True, raise McpToolError instead of returning error JSON",
    )

    async def _arun(self, **kwargs: Any) -> str:
        """Execute the tool asynchronously.

        Args:
            **kwargs: Tool arguments passed to MCP server

        Returns:
            JSON string of the tool result for LLM consumption

        Raises:
            McpToolError: If raise_on_error is True and tool execution fails
        """
        try:
            result = await self.mcp_client.call_tool(
                tool_name=self.name,
                arguments=kwargs,
            )
            return json.dumps(result, indent=2)
        except McpToolError as e:
            if self.raise_on_error:
                raise
            return json.dumps(
                {
                    "error": True,
                    "error_code": e.error_code.name,
                    "message": e.message,
                }
            )

    def _run(self, **kwargs: Any) -> str:
        """Sync execution not supported.

        Raises:
            NotImplementedError: Always, as sync execution is not supported
        """
        raise NotImplementedError("Use async execution with _arun()")
