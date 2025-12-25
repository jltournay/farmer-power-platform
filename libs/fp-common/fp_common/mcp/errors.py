"""MCP error handling module.

Provides error codes and exception class for MCP tool execution failures.
Matches proto enum definitions in proto/mcp/v1/mcp_tool.proto.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Optional


class ErrorCode(IntEnum):
    """Error codes for MCP tool execution failures.

    Values match proto/mcp/v1/mcp_tool.proto ErrorCode enum.
    """

    UNSPECIFIED = 0
    INVALID_ARGUMENTS = 1
    SERVICE_UNAVAILABLE = 2
    TOOL_NOT_FOUND = 3
    INTERNAL_ERROR = 4


class McpToolError(Exception):
    """Exception raised when MCP tool execution fails.

    Attributes:
        error_code: Error code indicating failure type
        message: Human-readable error description
        trace_id: OpenTelemetry trace ID for correlation
        app_id: DAPR app ID of the MCP server
        tool_name: Name of the tool that failed
    """

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        trace_id: str,
        app_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> None:
        """Initialize McpToolError.

        Args:
            error_code: Error code indicating failure type
            message: Human-readable error description
            trace_id: OpenTelemetry trace ID for correlation
            app_id: DAPR app ID of the MCP server (optional)
            tool_name: Name of the tool that failed (optional)
        """
        self.error_code = error_code
        self.message = message
        self.trace_id = trace_id
        self.app_id = app_id
        self.tool_name = tool_name
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with full context for logging."""
        parts = [
            f"[{self.error_code.name}]",
            self.message,
        ]
        if self.app_id:
            parts.append(f"app_id={self.app_id}")
        if self.tool_name:
            parts.append(f"tool={self.tool_name}")
        parts.append(f"trace_id={self.trace_id}")
        return " | ".join(parts)
