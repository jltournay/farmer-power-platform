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

gRPC Client Retry Pattern (ADR-005):
------------------------------------
All gRPC clients MUST implement retry logic with singleton channel pattern.
This ensures auto-recovery from transient failures without pod restart.

- Singleton channel: created once, reused across calls
- Tenacity retry: 3 attempts with exponential backoff (1-10s)
- Channel reset on UNAVAILABLE error forces reconnection
"""

import json
from typing import Any

import grpc
import structlog
from fp_common.models.source_config import IterationConfig
from fp_proto.mcp.v1 import mcp_tool_pb2, mcp_tool_pb2_grpc
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

# DAPR sidecar gRPC port (used for gRPC proxying to other services)
DAPR_GRPC_PORT = 50001


class IterationResolverError(Exception):
    """Error during iteration resolution via MCP tool call."""


class ServiceUnavailableError(Exception):
    """Raised when the MCP service is unavailable after retries.

    Attributes:
        app_id: The DAPR app ID of the service.
        method_name: The gRPC method that failed.
        attempt_count: Number of retry attempts made.
    """

    def __init__(
        self,
        message: str,
        app_id: str,
        method_name: str,
        attempt_count: int = 3,
    ) -> None:
        self.app_id = app_id
        self.method_name = method_name
        self.attempt_count = attempt_count
        super().__init__(f"{message} (app_id={app_id}, method={method_name}, attempts={attempt_count})")


class IterationResolver:
    """Resolves iteration items by calling MCP tools via DAPR.

    When a source config has an iteration block, this resolver calls
    the specified MCP server and tool to get a list of items. Each
    item is used for parallel fetch with parameter substitution.

    Retry Pattern (ADR-005):
    - Singleton channel pattern: channel created once and reused
    - Tenacity retry on all RPC methods: 3 attempts, exponential backoff 1-10s
    - Channel reset on UNAVAILABLE error forces reconnection on next attempt

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

    def __init__(self, channel: grpc.aio.Channel | None = None) -> None:
        """Initialize the IterationResolver.

        Args:
            channel: Optional pre-configured gRPC channel (for testing).
        """
        self._channel: grpc.aio.Channel | None = channel
        self._stub: mcp_tool_pb2_grpc.McpToolServiceStub | None = None

    async def _get_stub(self) -> mcp_tool_pb2_grpc.McpToolServiceStub:
        """Get or create the gRPC stub (singleton pattern).

        Creates the channel lazily on first use and reuses it for subsequent calls.
        This is the recommended pattern per ADR-005.

        Returns:
            The gRPC stub for MCP tool service.
        """
        if self._stub is None:
            if self._channel is None:
                target = f"localhost:{DAPR_GRPC_PORT}"
                logger.debug(
                    "Creating gRPC channel to DAPR sidecar",
                    target=target,
                )
                self._channel = grpc.aio.insecure_channel(
                    target,
                    options=[
                        ("grpc.keepalive_time_ms", 30000),
                        ("grpc.keepalive_timeout_ms", 10000),
                    ],
                )
            self._stub = mcp_tool_pb2_grpc.McpToolServiceStub(self._channel)
        return self._stub

    def _get_metadata(self, source_mcp: str) -> list[tuple[str, str]]:
        """Get gRPC call metadata for DAPR service invocation.

        Args:
            source_mcp: The target MCP service app ID.

        Returns:
            List of metadata tuples including dapr-app-id.
        """
        return [("dapr-app-id", source_mcp)]

    def _reset_channel(self) -> None:
        """Reset channel and stub on connection error.

        Forces reconnection on the next call. This is called when an
        UNAVAILABLE error is encountered to ensure fresh connection.
        """
        logger.warning("Resetting gRPC channel after connection error")
        self._channel = None
        self._stub = None

    async def resolve(
        self,
        iteration_config: IterationConfig,
    ) -> list[dict[str, Any]]:
        """Resolve iteration items by calling MCP tool.

        Invokes the MCP tool specified in the config via DAPR Service
        Invocation and returns the list of items for iteration.
        Includes retry logic per ADR-005: 3 attempts with exponential backoff.

        Args:
            iteration_config: Typed IterationConfig with source_mcp,
                            source_tool, and optional tool_arguments.

        Returns:
            List of iteration items (dicts with fields for substitution).

        Raises:
            IterationResolverError: On MCP call failure or invalid response.
            ServiceUnavailableError: If service is unavailable after all retries.
        """
        source_mcp = iteration_config.source_mcp
        if not source_mcp:
            raise IterationResolverError("Missing source_mcp in iteration config")

        try:
            return await self._resolve_with_retry(iteration_config)
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                logger.error(
                    "MCP service unavailable after all retries",
                    app_id=source_mcp,
                    method="CallTool",
                    attempts=3,
                )
                raise ServiceUnavailableError(
                    message="MCP service unavailable after retries",
                    app_id=source_mcp,
                    method_name="CallTool",
                    attempt_count=3,
                ) from e
            raise

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _resolve_with_retry(
        self,
        iteration_config: IterationConfig,
    ) -> list[dict[str, Any]]:
        """Internal resolution with retry logic (ADR-005).

        This method is wrapped by resolve() which transforms the final error
        to ServiceUnavailableError with context per AC4.
        """
        # Use typed attribute access from Pydantic model
        source_mcp = iteration_config.source_mcp
        source_tool = iteration_config.source_tool
        tool_arguments = iteration_config.tool_arguments or {}
        result_path = iteration_config.result_path

        if not source_mcp or not source_tool:
            raise IterationResolverError("Missing source_mcp or source_tool in iteration config")

        logger.debug(
            "Resolving iteration via MCP tool",
            source_mcp=source_mcp,
            source_tool=source_tool,
            has_arguments=bool(tool_arguments),
        )

        # Build MCP ToolCallRequest protobuf message
        request = mcp_tool_pb2.ToolCallRequest(
            tool_name=source_tool,
            arguments_json=json.dumps(tool_arguments),
        )

        try:
            stub = await self._get_stub()
            metadata = self._get_metadata(source_mcp)
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

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                # Reset channel to force reconnection on next attempt
                self._reset_channel()
                logger.warning(
                    "MCP service unavailable, will retry",
                    app_id=source_mcp,
                    error=str(e),
                )
            raise

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

    async def close(self) -> None:
        """Clean up resources by closing the gRPC channel."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
