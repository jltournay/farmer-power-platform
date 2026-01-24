"""Base gRPC client for DAPR service invocation.

This module provides the base client infrastructure for calling backend gRPC services
via DAPR sidecar. All BFF clients should inherit from BaseGrpcClient.

Pattern follows ADR-002 §"Service Invocation Pattern" and ADR-005 for retry logic.

CRITICAL: Uses native gRPC with `dapr-app-id` metadata header, NOT DaprClient().invoke_method()
which is HTTP-based and returns HTTP 501 when calling gRPC services.
"""

from typing import Any

import grpc
import grpc.aio
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


class ServiceUnavailableError(Exception):
    """Raised when a backend service is unavailable after retries."""


class NotFoundError(Exception):
    """Raised when a requested resource is not found."""


# Decorator for gRPC retry logic per ADR-005
grpc_retry = retry(
    retry=retry_if_exception_type(grpc.aio.AioRpcError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)


class BaseGrpcClient:
    """Base gRPC client with DAPR service invocation support.

    Uses singleton channel pattern with lazy initialization and proper reset on error.
    Supports both DAPR-routed connections (via dapr-app-id metadata) and direct
    connections for testing.

    Attributes:
        dapr_grpc_port: Port for DAPR sidecar gRPC endpoint (default: 50001).
        target_app_id: DAPR app-id of the target service.
        direct_host: Optional direct host for testing (bypasses DAPR).

    Example:
        >>> class MyClient(BaseGrpcClient):
        ...     def __init__(self):
        ...         super().__init__(target_app_id="my-service")
        ...
        ...     async def get_item(self, item_id: str) -> Item:
        ...         stub = await self._get_stub(MyServiceStub)
        ...         request = GetItemRequest(id=item_id)
        ...         try:
        ...             response = await self._call(stub.GetItem, request)
        ...             return Item.model_validate(...)
        ...         except grpc.aio.AioRpcError as e:
        ...             self._handle_grpc_error(e, f"Item {item_id}")
    """

    def __init__(
        self,
        target_app_id: str,
        dapr_grpc_port: int = 50001,
        direct_host: str | None = None,
        channel: grpc.aio.Channel | None = None,
    ) -> None:
        """Initialize the base gRPC client.

        Args:
            target_app_id: DAPR app-id of the target service (e.g., "plantation-model").
            dapr_grpc_port: Port for DAPR sidecar gRPC endpoint (default: 50001).
            direct_host: Optional direct host for testing (e.g., "localhost:50051").
                        If provided, DAPR routing is bypassed.
            channel: Optional pre-configured channel for testing.
        """
        self._target_app_id = target_app_id
        self._dapr_grpc_port = dapr_grpc_port
        self._direct_host = direct_host
        self._channel = channel
        self._stubs: dict[type, Any] = {}

    async def _get_channel(self) -> grpc.aio.Channel:
        """Get or create the gRPC channel with lazy initialization.

        Returns:
            The gRPC async channel.
        """
        if self._channel is None:
            if self._direct_host:
                # Direct connection (for testing without DAPR)
                target = self._direct_host
                logger.info(
                    "Creating direct gRPC channel",
                    target=target,
                    app_id=self._target_app_id,
                )
            else:
                # Connect via DAPR sidecar
                target = f"localhost:{self._dapr_grpc_port}"
                logger.info(
                    "Creating DAPR gRPC channel",
                    target=target,
                    app_id=self._target_app_id,
                )

            # Create channel with keepalive and message size options
            options = [
                ("grpc.max_send_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.keepalive_time_ms", 30000),  # 30s keepalive interval
                ("grpc.keepalive_timeout_ms", 10000),  # 10s timeout
                ("grpc.keepalive_permit_without_calls", True),
            ]
            self._channel = grpc.aio.insecure_channel(target, options=options)

        return self._channel

    async def _get_stub(self, stub_class: type) -> Any:
        """Get or create a gRPC stub.

        Uses singleton pattern to reuse stubs for the same stub class.

        Args:
            stub_class: The gRPC stub class (e.g., PlantationServiceStub).

        Returns:
            The stub instance.
        """
        if stub_class not in self._stubs:
            channel = await self._get_channel()
            self._stubs[stub_class] = stub_class(channel)
        return self._stubs[stub_class]

    def _get_metadata(self) -> list[tuple[str, str]]:
        """Get gRPC call metadata for DAPR service invocation.

        Returns:
            List of metadata tuples. Empty if using direct connection.
        """
        if self._direct_host:
            # Direct connection - no DAPR metadata needed
            return []
        # DAPR service invocation - add app-id metadata
        return [("dapr-app-id", self._target_app_id)]

    def _handle_grpc_error(self, error: grpc.aio.AioRpcError, resource_desc: str) -> None:
        """Handle gRPC errors and convert to domain exceptions.

        Args:
            error: The gRPC error.
            resource_desc: Description of the resource being accessed (for error messages).

        Raises:
            NotFoundError: If the resource was not found.
            ServiceUnavailableError: If the service is unavailable.
            grpc.aio.AioRpcError: For other gRPC errors (re-raised).
        """
        if error.code() == grpc.StatusCode.NOT_FOUND:
            raise NotFoundError(f"{resource_desc} not found") from error
        if error.code() == grpc.StatusCode.UNAVAILABLE:
            # Reset channel on connection error to force reconnection
            self._reset_channel()
            raise ServiceUnavailableError(f"Service unavailable for {resource_desc}: {error.details()}") from error
        raise error

    def _reset_channel(self) -> None:
        """Reset channel and stubs to force reconnection on next call.

        Called automatically on UNAVAILABLE errors per ADR-005.
        """
        logger.warning(
            "Resetting gRPC channel due to connection error",
            app_id=self._target_app_id,
        )
        self._channel = None
        self._stubs.clear()

    async def close(self) -> None:
        """Close the gRPC channel gracefully."""
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._stubs.clear()
