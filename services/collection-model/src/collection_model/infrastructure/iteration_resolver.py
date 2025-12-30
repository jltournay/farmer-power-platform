"""Iteration Resolver for scheduled pull sources with multi-fetch (Story 2.7).

This module provides the IterationResolver class for calling MCP tools
via DAPR Service Invocation to get lists of items for parallel fetching.
Used when source configs have an iteration block to dynamically expand
API calls based on runtime data (e.g., list of regions, farmers).

DAPR gRPC Proxying Pattern (Story 0.4.6 fix):
--------------------------------------------
To invoke gRPC services (like MCP servers) via DAPR, we use native gRPC
with the `dapr-app-id` metadata header. This is the recommended approach
for gRPC-to-gRPC communication in DAPR (see DAPR docs: howto-invoke-services-grpc).

Pattern:
1. Connect to DAPR sidecar's gRPC port (default 50001)
2. Use native proto stubs (McpToolServiceStub)
3. Add metadata: [("dapr-app-id", target_service)]
4. DAPR routes the call to the target service

This replaces the previous DaprClient.invoke_method() approach which uses
HTTP and doesn't support HTTP-to-gRPC transcoding for protobuf messages.
"""

import json
from typing import Any

import grpc
import structlog
from fp_proto.mcp.v1 import mcp_tool_pb2, mcp_tool_pb2_grpc

logger = structlog.get_logger(__name__)

# DAPR sidecar gRPC port (used for gRPC proxying to other services)
DAPR_GRPC_PORT = 50001


class IterationResolverError(Exception):
    """Error during iteration resolution via MCP tool call."""


class IterationResolver:
    """Resolves iteration items by calling MCP tools via DAPR.

    When a source config has an iteration block, this resolver calls
    the specified MCP server and tool to get a list of items. Each
    item is used for parallel fetch with parameter substitution.

    Example iteration config:
    ```yaml
    iteration:
      foreach: region
      source_mcp: plantation-mcp
      source_tool: list_active_regions
      tool_arguments: {}
      result_path: regions  # Optional: extract from nested result
      inject_linkage:
        - region_id
        - name
      concurrency: 5
    ```
    """

    async def resolve(
        self,
        iteration_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Resolve iteration items by calling MCP tool.

        Invokes the MCP tool specified in the config via DAPR Service
        Invocation and returns the list of items for iteration.

        Args:
            iteration_config: Iteration configuration with source_mcp,
                            source_tool, and optional tool_arguments.

        Returns:
            List of iteration items (dicts with fields for substitution).

        Raises:
            IterationResolverError: On MCP call failure or invalid response.
        """
        source_mcp = iteration_config.get("source_mcp", "")
        source_tool = iteration_config.get("source_tool", "")
        tool_arguments = iteration_config.get("tool_arguments", {})
        result_path = iteration_config.get("result_path")

        if not source_mcp or not source_tool:
            raise IterationResolverError("Missing source_mcp or source_tool in iteration config")

        logger.debug(
            "Resolving iteration via MCP tool",
            source_mcp=source_mcp,
            source_tool=source_tool,
            has_arguments=bool(tool_arguments),
        )

        try:
            # Build MCP ToolCallRequest protobuf message
            request = mcp_tool_pb2.ToolCallRequest(
                tool_name=source_tool,
                arguments_json=json.dumps(tool_arguments),
            )

            # Call MCP server via DAPR gRPC proxying
            # Connect to DAPR sidecar's gRPC port and use dapr-app-id metadata
            # to route the request to the target MCP service
            target = f"localhost:{DAPR_GRPC_PORT}"
            async with grpc.aio.insecure_channel(target) as channel:
                stub = mcp_tool_pb2_grpc.McpToolServiceStub(channel)
                # DAPR routes the call to the target app via dapr-app-id metadata
                metadata = [("dapr-app-id", source_mcp)]
                response = await stub.CallTool(request, metadata=metadata)

            if not response.success:
                error_message = response.error_message or "Unknown error"
                raise IterationResolverError(f"MCP tool call failed: {error_message}")

            # Parse result_json from response
            result_json = response.result_json or "[]"
            result = json.loads(result_json)

            # Extract items from result path if specified
            items = self._extract_items(result, result_path)

            logger.info(
                "Iteration resolved successfully",
                source_mcp=source_mcp,
                source_tool=source_tool,
                item_count=len(items),
            )

            return items

        except IterationResolverError:
            raise

        except Exception as e:
            logger.exception(
                "Failed to resolve iteration via MCP",
                source_mcp=source_mcp,
                source_tool=source_tool,
                error=str(e),
            )
            raise IterationResolverError(f"MCP invocation failed: {e}") from e

    def _extract_items(
        self,
        result: Any,
        result_path: str | None,
    ) -> list[dict[str, Any]]:
        """Extract list of items from MCP result.

        Args:
            result: Parsed JSON result from MCP tool.
            result_path: Optional dot-path to extract items from nested result.

        Returns:
            List of iteration items.

        Raises:
            IterationResolverError: If result is not a list after extraction.
        """
        # If result_path specified, navigate to nested value
        if result_path:
            for key in result_path.split("."):
                if isinstance(result, dict) and key in result:
                    result = result[key]
                else:
                    logger.warning(
                        "Result path not found in MCP response",
                        result_path=result_path,
                        key=key,
                    )
                    return []

        # Result should be a list
        if isinstance(result, list):
            return result

        logger.warning(
            "MCP result is not a list",
            result_type=type(result).__name__,
        )
        return []

    def extract_linkage(
        self,
        item: dict[str, Any],
        inject_fields: list[str] | None,
    ) -> dict[str, Any]:
        """Extract linkage fields from an iteration item.

        Used to inject item data into document linkage for downstream
        processing and querying.

        Args:
            item: Iteration item from MCP tool result.
            inject_fields: List of field names to extract.

        Returns:
            Dictionary with extracted field values.
        """
        if not inject_fields:
            return {}

        linkage = {}
        for field in inject_fields:
            if field in item:
                linkage[field] = item[field]

        return linkage
