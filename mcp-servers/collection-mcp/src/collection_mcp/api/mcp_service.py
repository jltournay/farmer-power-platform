"""MCP Tool Service implementation for Collection Model."""

import json
from typing import Any

import grpc
import structlog
from fp_proto.mcp.v1 import mcp_tool_pb2, mcp_tool_pb2_grpc
from jsonschema import ValidationError as JsonSchemaValidationError, validate
from opentelemetry import trace

from collection_mcp.infrastructure.blob_url_generator import BlobUrlGenerator
from collection_mcp.infrastructure.document_client import (
    DocumentClient,
    DocumentNotFoundError,
)
from collection_mcp.infrastructure.source_config_client import SourceConfigClient
from collection_mcp.tools.definitions import TOOL_REGISTRY, list_tools

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


class McpToolServiceServicer(mcp_tool_pb2_grpc.McpToolServiceServicer):
    """MCP Tool Service implementation for Collection Model data.

    Provides AI agents access to documents from any configured source
    using generic, config-driven tools.
    """

    def __init__(
        self,
        document_client: DocumentClient,
        blob_url_generator: BlobUrlGenerator,
        source_config_client: SourceConfigClient,
    ) -> None:
        """Initialize the servicer.

        Args:
            document_client: Client for MongoDB document operations.
            blob_url_generator: Generator for Azure Blob SAS URLs.
            source_config_client: Client for source configuration queries.
        """
        self._document_client = document_client
        self._blob_url_generator = blob_url_generator
        self._source_config_client = source_config_client

        self._tool_handlers: dict[str, Any] = {
            "get_documents": self._handle_get_documents,
            "get_document_by_id": self._handle_get_document_by_id,
            "get_farmer_documents": self._handle_get_farmer_documents,
            "search_documents": self._handle_search_documents,
            "list_sources": self._handle_list_sources,
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
                    result_json=json.dumps(result, default=str),
                )

            except DocumentNotFoundError as e:
                logger.warning(
                    "Document not found",
                    tool_name=request.tool_name,
                    document_id=e.document_id,
                )
                span.set_attribute("mcp.error", "not_found")
                return mcp_tool_pb2.ToolCallResponse(
                    success=False,
                    error_code=mcp_tool_pb2.ERROR_CODE_INVALID_ARGUMENTS,
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

    async def _handle_get_documents(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get_documents tool call.

        Args:
            arguments: Tool arguments with optional filters.

        Returns:
            Dict with documents list and metadata.
        """
        source_id = arguments.get("source_id")
        collection_name = None

        # Look up source config to get the correct collection name
        # Per Pydantic model (fp_common/models/source_config.py:239), storage is a direct field
        if source_id:
            source_config = await self._source_config_client.get_source(source_id)
            if source_config:
                storage = source_config.get("storage", {})
                collection_name = storage.get("index_collection")
                logger.debug(
                    "Resolved collection from source config",
                    source_id=source_id,
                    collection_name=collection_name,
                )

        documents = await self._document_client.get_documents(
            source_id=source_id,
            farmer_id=arguments.get("farmer_id"),
            linkage=arguments.get("linkage"),
            attributes=arguments.get("attributes"),
            date_range=arguments.get("date_range"),
            limit=arguments.get("limit", 50),
            collection_name=collection_name,
        )

        return {
            "documents": documents,
            "count": len(documents),
            "filters_applied": {k: v for k, v in arguments.items() if v is not None and k != "limit"},
        }

    async def _handle_get_document_by_id(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get_document_by_id tool call.

        Args:
            arguments: Tool arguments with document_id and include_files flag.

        Returns:
            Document dict, optionally with SAS URLs for files.
        """
        document_id = arguments["document_id"]
        include_files = arguments.get("include_files", False)

        document = await self._document_client.get_document_by_id(document_id)

        # Enrich files with SAS URLs if requested
        if include_files and "files" in document and document["files"]:
            document["files"] = self._blob_url_generator.enrich_files_with_sas(document["files"])

        return {"document": document}

    async def _handle_get_farmer_documents(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle get_farmer_documents tool call.

        Args:
            arguments: Tool arguments with farmer_id and optional filters.

        Returns:
            Dict with documents list and metadata.
        """
        farmer_id = arguments["farmer_id"]

        documents = await self._document_client.get_farmer_documents(
            farmer_id=farmer_id,
            source_ids=arguments.get("source_ids"),
            date_range=arguments.get("date_range"),
            limit=arguments.get("limit", 100),
        )

        return {
            "farmer_id": farmer_id,
            "documents": documents,
            "count": len(documents),
            "source_ids_filter": arguments.get("source_ids"),
        }

    async def _handle_search_documents(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle search_documents tool call.

        Args:
            arguments: Tool arguments with query and optional filters.

        Returns:
            Dict with search results and metadata.
        """
        query = arguments["query"]

        documents = await self._document_client.search_documents(
            query_text=query,
            source_ids=arguments.get("source_ids"),
            farmer_id=arguments.get("farmer_id"),
            limit=arguments.get("limit", 20),
        )

        return {
            "query": query,
            "results": documents,
            "count": len(documents),
        }

    async def _handle_list_sources(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle list_sources tool call.

        Args:
            arguments: Tool arguments with enabled_only flag.

        Returns:
            Dict with sources list and metadata.
        """
        enabled_only = arguments.get("enabled_only", True)

        sources = await self._source_config_client.list_sources(
            enabled_only=enabled_only,
        )

        return {
            "sources": sources,
            "count": len(sources),
            "enabled_only": enabled_only,
        }
