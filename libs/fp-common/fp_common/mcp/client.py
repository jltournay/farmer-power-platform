"""gRPC MCP client for invoking tools via DAPR service invocation.

Provides GrpcMcpClient for AI agents to call MCP server tools.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from dapr.clients import DaprClient
from opentelemetry import trace

from fp_proto.mcp.v1 import mcp_tool_pb2
from fp_common.mcp.errors import ErrorCode, McpToolError

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class GrpcMcpClient:
    """Client for invoking MCP tools via DAPR service invocation.

    Attributes:
        app_id: DAPR app ID of the target MCP server
    """

    def __init__(self, app_id: str) -> None:
        """Initialize client for a specific MCP server.

        Args:
            app_id: DAPR app ID of the MCP server (e.g., "plantation-mcp")
        """
        self.app_id = app_id

    def _invoke_method_sync(
        self,
        method_name: str,
        data: bytes,
    ) -> Any:
        """Synchronously invoke a DAPR method.

        Args:
            method_name: gRPC method name
            data: Serialized request data

        Returns:
            Response from DAPR
        """
        with DaprClient() as client:
            return client.invoke_method(
                app_id=self.app_id,
                method_name=method_name,
                data=data,
                content_type="application/grpc",
            )

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        caller_agent_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Invoke an MCP tool and return the result.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments as a dictionary
            caller_agent_id: Optional agent ID for audit logging

        Returns:
            Tool result as a dictionary

        Raises:
            McpToolError: If tool execution fails
        """
        with tracer.start_as_current_span(f"mcp.call_tool.{tool_name}") as span:
            span.set_attribute("mcp.app_id", self.app_id)
            span.set_attribute("mcp.tool_name", tool_name)

            # Get trace ID for correlation (defensive check for None span_context)
            span_context = span.get_span_context()
            trace_id = ""
            if span_context is not None and span_context.is_valid:
                trace_id = format(span_context.trace_id, "032x")

            request = mcp_tool_pb2.ToolCallRequest(
                tool_name=tool_name,
                arguments_json=json.dumps(arguments),
                trace_id=trace_id,
                caller_agent_id=caller_agent_id or "",
            )

            try:
                # Run sync DAPR call in thread pool to not block event loop
                response = await asyncio.to_thread(
                    self._invoke_method_sync,
                    "McpToolService/CallTool",
                    request.SerializeToString(),
                )

                result = mcp_tool_pb2.ToolCallResponse()
                result.ParseFromString(response.data)

                if not result.success:
                    error = McpToolError(
                        error_code=ErrorCode(result.error_code),
                        message=result.error_message,
                        trace_id=trace_id,
                        app_id=self.app_id,
                        tool_name=tool_name,
                    )
                    logger.error(
                        "MCP tool call failed",
                        extra={
                            "app_id": self.app_id,
                            "tool_name": tool_name,
                            "error_code": result.error_code,
                            "error_message": result.error_message,
                            "trace_id": trace_id,
                        },
                    )
                    span.record_exception(error)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(error)))
                    raise error

                result_dict: dict[str, Any] = json.loads(result.result_json)
                return result_dict

            except McpToolError:
                raise
            except Exception as e:
                logger.exception(
                    "MCP tool call exception",
                    extra={
                        "app_id": self.app_id,
                        "tool_name": tool_name,
                        "trace_id": trace_id,
                    },
                )
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise

    async def list_tools(self, category: Optional[str] = None) -> list[dict[str, Any]]:
        """List available tools from the MCP server.

        Args:
            category: Optional category filter

        Returns:
            List of tool definitions
        """
        request = mcp_tool_pb2.ListToolsRequest(category=category or "")

        # Run sync DAPR call in thread pool to not block event loop
        response = await asyncio.to_thread(
            self._invoke_method_sync,
            "McpToolService/ListTools",
            request.SerializeToString(),
        )

        result = mcp_tool_pb2.ListToolsResponse()
        result.ParseFromString(response.data)

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": json.loads(tool.input_schema_json) if tool.input_schema_json else {},
                "category": tool.category,
            }
            for tool in result.tools
        ]
