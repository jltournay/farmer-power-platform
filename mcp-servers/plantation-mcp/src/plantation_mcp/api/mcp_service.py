"""MCP Tool Service implementation."""

import json
from typing import Any

import grpc
import structlog
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate
from opentelemetry import trace

from fp_proto.mcp.v1 import mcp_tool_pb2, mcp_tool_pb2_grpc

from plantation_mcp.infrastructure.plantation_client import (
    NotFoundError,
    PlantationClient,
    ServiceUnavailableError,
)
from plantation_mcp.tools.definitions import TOOL_REGISTRY, list_tools

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


class McpToolServiceServicer(mcp_tool_pb2_grpc.McpToolServiceServicer):
    """MCP Tool Service implementation for Plantation data.

    Provides AI agents access to farmer and collection point data.
    """

    def __init__(self, plantation_client: PlantationClient) -> None:
        """Initialize the servicer.

        Args:
            plantation_client: Client for Plantation Model service.
        """
        self._plantation_client = plantation_client
        self._tool_handlers: dict[str, Any] = {
            "get_farmer": self._handle_get_farmer,
            "get_farmer_summary": self._handle_get_farmer_summary,
            "get_collection_points": self._handle_get_collection_points,
            "get_farmers_by_collection_point": self._handle_get_farmers_by_collection_point,
        }

    async def ListTools(
        self,
        request: mcp_tool_pb2.ListToolsRequest,
        context: grpc.aio.ServicerContext,
    ) -> mcp_tool_pb2.ListToolsResponse:
        """List all available tools with their schemas.

        Args:
            request: ListToolsRequest with optional category filter.
            context: gRPC context.

        Returns:
            ListToolsResponse with tool definitions.
        """
        with tracer.start_as_current_span("mcp.list_tools") as span:
            category = request.category if request.category else None
            span.set_attribute("mcp.category_filter", category or "none")

            tools = list_tools(category=category)

            tool_defs = [
                mcp_tool_pb2.ToolDefinition(
                    name=tool.name,
                    description=tool.description,
                    input_schema_json=json.dumps(tool.input_schema),
                    category=tool.category,
                )
                for tool in tools
            ]

            span.set_attribute("mcp.tools_count", len(tool_defs))
            logger.info("Listed tools", count=len(tool_defs), category=category)

            return mcp_tool_pb2.ListToolsResponse(tools=tool_defs)

    async def CallTool(
        self,
        request: mcp_tool_pb2.ToolCallRequest,
        context: grpc.aio.ServicerContext,
    ) -> mcp_tool_pb2.ToolCallResponse:
        """Invoke a tool.

        Args:
            request: ToolCallRequest with tool name and arguments.
            context: gRPC context.

        Returns:
            ToolCallResponse with result or error.
        """
        with tracer.start_as_current_span(f"mcp.call_tool.{request.tool_name}") as span:
            span.set_attribute("mcp.tool_name", request.tool_name)
            span.set_attribute("mcp.caller_agent_id", request.caller_agent_id or "unknown")

            logger.info(
                "Tool call received",
                tool_name=request.tool_name,
                caller_agent_id=request.caller_agent_id,
            )

            # Check if tool exists
            handler = self._tool_handlers.get(request.tool_name)
            if not handler:
                logger.warning("Tool not found", tool_name=request.tool_name)
                span.set_attribute("mcp.error", "tool_not_found")
                return mcp_tool_pb2.ToolCallResponse(
                    success=False,
                    error_code=mcp_tool_pb2.ERROR_CODE_TOOL_NOT_FOUND,
                    error_message=f"Unknown tool: {request.tool_name}",
                )

            # Parse and validate arguments
            try:
                arguments = json.loads(request.arguments_json) if request.arguments_json else {}
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON arguments", error=str(e))
                span.set_attribute("mcp.error", "invalid_json")
                return mcp_tool_pb2.ToolCallResponse(
                    success=False,
                    error_code=mcp_tool_pb2.ERROR_CODE_INVALID_ARGUMENTS,
                    error_message=f"Invalid JSON arguments: {e}",
                )

            # Validate against schema
            tool_def = TOOL_REGISTRY.get(request.tool_name)
            if tool_def:
                try:
                    validate(instance=arguments, schema=tool_def.input_schema)
                except JsonSchemaValidationError as e:
                    logger.warning(
                        "Schema validation failed",
                        tool_name=request.tool_name,
                        error=e.message,
                    )
                    span.set_attribute("mcp.error", "schema_validation_failed")
                    return mcp_tool_pb2.ToolCallResponse(
                        success=False,
                        error_code=mcp_tool_pb2.ERROR_CODE_INVALID_ARGUMENTS,
                        error_message=f"Validation error: {e.message}",
                    )

            # Execute handler
            try:
                result = await handler(arguments)
                span.set_attribute("mcp.success", True)
                logger.info("Tool call succeeded", tool_name=request.tool_name)

                return mcp_tool_pb2.ToolCallResponse(
                    success=True,
                    result_json=json.dumps(result),
                )

            except NotFoundError as e:
                logger.warning(
                    "Resource not found",
                    tool_name=request.tool_name,
                    error=str(e),
                )
                span.set_attribute("mcp.error", "not_found")
                return mcp_tool_pb2.ToolCallResponse(
                    success=False,
                    error_code=mcp_tool_pb2.ERROR_CODE_INVALID_ARGUMENTS,
                    error_message=str(e),
                )

            except ServiceUnavailableError as e:
                logger.error(
                    "Service unavailable",
                    tool_name=request.tool_name,
                    error=str(e),
                )
                span.set_attribute("mcp.error", "service_unavailable")
                return mcp_tool_pb2.ToolCallResponse(
                    success=False,
                    error_code=mcp_tool_pb2.ERROR_CODE_SERVICE_UNAVAILABLE,
                    error_message=str(e),
                )

            except Exception as e:
                logger.exception(
                    "Internal error during tool execution",
                    tool_name=request.tool_name,
                    error=str(e),
                )
                span.set_attribute("mcp.error", "internal_error")
                span.record_exception(e)
                return mcp_tool_pb2.ToolCallResponse(
                    success=False,
                    error_code=mcp_tool_pb2.ERROR_CODE_INTERNAL_ERROR,
                    error_message=f"Internal error: {type(e).__name__}",
                )

    # =========================================================================
    # Tool Handlers
    # =========================================================================

    async def _handle_get_farmer(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get_farmer tool call.

        Args:
            arguments: Tool arguments with farmer_id.

        Returns:
            Farmer details dict.
        """
        farmer_id = arguments["farmer_id"]
        return await self._plantation_client.get_farmer(farmer_id)

    async def _handle_get_farmer_summary(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle get_farmer_summary tool call.

        Args:
            arguments: Tool arguments with farmer_id.

        Returns:
            Farmer summary dict with performance metrics.
        """
        farmer_id = arguments["farmer_id"]
        return await self._plantation_client.get_farmer_summary(farmer_id)

    async def _handle_get_collection_points(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle get_collection_points tool call.

        Args:
            arguments: Tool arguments with factory_id.

        Returns:
            Dict with list of collection points.
        """
        factory_id = arguments["factory_id"]
        collection_points = await self._plantation_client.get_collection_points(
            factory_id
        )
        return {"collection_points": collection_points}

    async def _handle_get_farmers_by_collection_point(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle get_farmers_by_collection_point tool call.

        Args:
            arguments: Tool arguments with collection_point_id.

        Returns:
            Dict with list of farmers.
        """
        collection_point_id = arguments["collection_point_id"]
        farmers = await self._plantation_client.get_farmers_by_collection_point(
            collection_point_id
        )
        return {"farmers": farmers}
