"""Source Config gRPC client for BFF.

Story 9.11b: Source Config gRPC Client + REST API in BFF

Provides typed access to Collection Model's SourceConfigService via DAPR
service invocation. Implements list and get operations for source configurations.

Per ADR-002 §"Service Invocation Pattern", ADR-005 for retry logic,
and ADR-012 for response wrappers (list methods return PaginatedResponse).
"""

import grpc
import grpc.aio
from bff.api.schemas import PaginatedResponse
from bff.infrastructure.clients.base import (
    BaseGrpcClient,
    grpc_retry,
)
from fp_common.converters import (
    source_config_detail_from_proto,
    source_config_summary_from_proto,
)
from fp_common.models import SourceConfigDetail, SourceConfigSummary
from fp_proto.collection.v1 import collection_pb2, collection_pb2_grpc


class SourceConfigClient(BaseGrpcClient):
    """gRPC client for Collection Model's SourceConfigService.

    Provides typed access to source configuration operations via DAPR service invocation.
    All methods return Pydantic domain models (NOT dict[str, Any]).

    Example:
        >>> client = SourceConfigClient()
        >>> configs = await client.list_source_configs(page_size=10)
        >>> assert isinstance(configs, PaginatedResponse)
        >>> assert isinstance(configs.items[0], SourceConfigSummary)

        >>> # With direct connection for testing
        >>> client = SourceConfigClient(direct_host="localhost:50051")
        >>> detail = await client.get_source_config("qc-analyzer-result")
        >>> assert isinstance(detail, SourceConfigDetail)
    """

    def __init__(
        self,
        dapr_grpc_port: int = 50001,
        direct_host: str | None = None,
        channel: grpc.aio.Channel | None = None,
    ) -> None:
        """Initialize the SourceConfigClient.

        Args:
            dapr_grpc_port: Port for DAPR sidecar gRPC endpoint (default: 50001).
            direct_host: Optional direct host for testing (e.g., "localhost:50051").
                        If provided, DAPR routing is bypassed.
            channel: Optional pre-configured channel for testing.
        """
        super().__init__(
            target_app_id="collection-model",
            dapr_grpc_port=dapr_grpc_port,
            direct_host=direct_host,
            channel=channel,
        )

    # =========================================================================
    # Source Config Query Methods
    # =========================================================================

    @grpc_retry
    async def list_source_configs(
        self,
        page_size: int = 20,
        page_token: str | None = None,
        enabled_only: bool = False,
        ingestion_mode: str | None = None,
    ) -> PaginatedResponse[SourceConfigSummary]:
        """List source configurations with pagination and optional filters.

        Args:
            page_size: Maximum number of configs to return (max 100, default 20).
            page_token: Pagination cursor from previous response.
            enabled_only: If True, only return enabled source configs.
            ingestion_mode: Filter by ingestion mode ("blob_trigger" or "scheduled_pull").

        Returns:
            PaginatedResponse containing SourceConfigSummary items with pagination metadata.

        Raises:
            ServiceUnavailableError: If the Collection Model service is unavailable.
        """
        stub = await self._get_stub(collection_pb2_grpc.SourceConfigServiceStub)
        effective_page_size = min(page_size, 100)

        request = collection_pb2.ListSourceConfigsRequest(
            page_size=effective_page_size,
            page_token=page_token or "",
            enabled_only=enabled_only,
            ingestion_mode=ingestion_mode or "",
        )

        try:
            response = await stub.ListSourceConfigs(request, metadata=self._get_metadata())
            configs = [source_config_summary_from_proto(cfg) for cfg in response.configs]
            next_token = response.next_page_token if response.next_page_token else None

            return PaginatedResponse.from_client_response(
                items=configs,
                total_count=response.total_count,
                page_size=effective_page_size,
                next_page_token=next_token,
            )
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "List source configs")
            raise  # For type checker, _handle_grpc_error always raises

    @grpc_retry
    async def get_source_config(self, source_id: str) -> SourceConfigDetail:
        """Get source configuration detail by ID.

        Args:
            source_id: The source configuration ID (e.g., "qc-analyzer-result").

        Returns:
            SourceConfigDetail with full configuration including config_json.

        Raises:
            NotFoundError: If the source configuration is not found.
            ServiceUnavailableError: If the Collection Model service is unavailable.
        """
        stub = await self._get_stub(collection_pb2_grpc.SourceConfigServiceStub)

        request = collection_pb2.GetSourceConfigRequest(source_id=source_id)

        try:
            response = await stub.GetSourceConfig(request, metadata=self._get_metadata())
            return source_config_detail_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Source config {source_id}")
            raise  # For type checker, _handle_grpc_error always raises
