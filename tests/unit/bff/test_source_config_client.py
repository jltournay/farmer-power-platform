"""Unit tests for SourceConfigClient.

Story 9.11b: Tests for source config gRPC client methods,
DAPR service invocation, error handling, and proto conversion.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from bff.infrastructure.clients.base import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.source_config_client import SourceConfigClient
from fp_common.models import SourceConfigDetail, SourceConfigSummary
from fp_proto.collection.v1 import collection_pb2, collection_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp


def _datetime_to_timestamp(dt: datetime) -> Timestamp:
    """Convert datetime to proto Timestamp."""
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


def create_source_config_summary_proto(
    source_id: str = "qc-analyzer-result",
    display_name: str = "QC Analyzer Results",
    description: str = "Quality control analyzer results from factory devices",
    enabled: bool = True,
    ingestion_mode: str = "blob_trigger",
    ai_agent_id: str = "qc-extractor-v1",
    updated_at: datetime | None = None,
) -> collection_pb2.SourceConfigSummary:
    """Create a SourceConfigSummary proto message for testing."""
    if updated_at is None:
        updated_at = datetime.now(UTC)

    return collection_pb2.SourceConfigSummary(
        source_id=source_id,
        display_name=display_name,
        description=description,
        enabled=enabled,
        ingestion_mode=ingestion_mode,
        ai_agent_id=ai_agent_id,
        updated_at=_datetime_to_timestamp(updated_at),
    )


def create_source_config_response_proto(
    source_id: str = "qc-analyzer-result",
    display_name: str = "QC Analyzer Results",
    description: str = "Quality control analyzer results from factory devices",
    enabled: bool = True,
    config_json: str = '{"source_id": "qc-analyzer-result"}',
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> collection_pb2.SourceConfigResponse:
    """Create a SourceConfigResponse proto message for testing."""
    now = datetime.now(UTC)
    if created_at is None:
        created_at = now
    if updated_at is None:
        updated_at = now

    return collection_pb2.SourceConfigResponse(
        source_id=source_id,
        display_name=display_name,
        description=description,
        enabled=enabled,
        config_json=config_json,
        created_at=_datetime_to_timestamp(created_at),
        updated_at=_datetime_to_timestamp(updated_at),
    )


@pytest.fixture
def mock_source_config_stub() -> MagicMock:
    """Create a mock SourceConfigService stub."""
    stub = MagicMock()
    stub.ListSourceConfigs = AsyncMock()
    stub.GetSourceConfig = AsyncMock()
    return stub


@pytest.fixture
def source_config_client_with_mock_stub(
    mock_source_config_stub: MagicMock,
) -> tuple[SourceConfigClient, MagicMock]:
    """Create a SourceConfigClient with a mocked stub."""
    client = SourceConfigClient(direct_host="localhost:50051")
    # Inject the mock stub
    client._stubs[collection_pb2_grpc.SourceConfigServiceStub] = mock_source_config_stub
    return client, mock_source_config_stub


class TestSourceConfigClientInit:
    """Tests for SourceConfigClient initialization."""

    def test_default_init(self) -> None:
        """Test default initialization with DAPR settings."""
        client = SourceConfigClient()
        assert client._target_app_id == "collection-model"
        assert client._dapr_grpc_port == 50001
        assert client._direct_host is None
        assert client._channel is None

    def test_direct_host_init(self) -> None:
        """Test initialization with direct host."""
        client = SourceConfigClient(direct_host="localhost:50051")
        assert client._direct_host == "localhost:50051"

    def test_custom_dapr_port(self) -> None:
        """Test initialization with custom DAPR port."""
        client = SourceConfigClient(dapr_grpc_port=50099)
        assert client._dapr_grpc_port == 50099


class TestSourceConfigClientMetadata:
    """Tests for gRPC metadata handling."""

    def test_metadata_with_dapr(self) -> None:
        """Test metadata generation with DAPR routing."""
        client = SourceConfigClient()
        metadata = client._get_metadata()
        assert ("dapr-app-id", "collection-model") in metadata

    def test_metadata_direct_connection(self) -> None:
        """Test metadata is empty for direct connection."""
        client = SourceConfigClient(direct_host="localhost:50051")
        metadata = client._get_metadata()
        assert metadata == []


class TestListSourceConfigs:
    """Tests for list_source_configs method."""

    @pytest.mark.asyncio
    async def test_list_source_configs_success(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test successful source config listing returns PaginatedResponse."""
        client, stub = source_config_client_with_mock_stub
        response = collection_pb2.ListSourceConfigsResponse(
            configs=[
                create_source_config_summary_proto(source_id="source-001"),
                create_source_config_summary_proto(source_id="source-002"),
            ],
            next_page_token="token123",
            total_count=100,
        )
        stub.ListSourceConfigs.return_value = response

        result = await client.list_source_configs()

        assert len(result.data) == 2
        assert all(isinstance(cfg, SourceConfigSummary) for cfg in result.data)
        assert result.data[0].source_id == "source-001"
        assert result.data[1].source_id == "source-002"
        assert result.pagination.next_page_token == "token123"
        assert result.pagination.total_count == 100
        assert result.pagination.has_next is True

    @pytest.mark.asyncio
    async def test_list_source_configs_with_pagination(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test source config listing with pagination parameters."""
        client, stub = source_config_client_with_mock_stub
        response = collection_pb2.ListSourceConfigsResponse(
            configs=[create_source_config_summary_proto()],
            next_page_token="",
            total_count=1,
        )
        stub.ListSourceConfigs.return_value = response

        result = await client.list_source_configs(
            page_size=10,
            page_token="prev_token",
        )

        call_args = stub.ListSourceConfigs.call_args
        request = call_args[0][0]
        assert request.page_size == 10
        assert request.page_token == "prev_token"
        assert result.pagination.next_page_token is None
        assert result.pagination.has_next is False

    @pytest.mark.asyncio
    async def test_list_source_configs_with_enabled_only_filter(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test source config listing with enabled_only filter."""
        client, stub = source_config_client_with_mock_stub
        response = collection_pb2.ListSourceConfigsResponse(
            configs=[create_source_config_summary_proto(enabled=True)],
            next_page_token="",
            total_count=1,
        )
        stub.ListSourceConfigs.return_value = response

        await client.list_source_configs(enabled_only=True)

        call_args = stub.ListSourceConfigs.call_args
        request = call_args[0][0]
        assert request.enabled_only is True

    @pytest.mark.asyncio
    async def test_list_source_configs_with_ingestion_mode_filter(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test source config listing with ingestion_mode filter."""
        client, stub = source_config_client_with_mock_stub
        response = collection_pb2.ListSourceConfigsResponse(
            configs=[create_source_config_summary_proto(ingestion_mode="blob_trigger")],
            next_page_token="",
            total_count=1,
        )
        stub.ListSourceConfigs.return_value = response

        await client.list_source_configs(ingestion_mode="blob_trigger")

        call_args = stub.ListSourceConfigs.call_args
        request = call_args[0][0]
        assert request.ingestion_mode == "blob_trigger"

    @pytest.mark.asyncio
    async def test_list_source_configs_page_size_capped(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test page_size is capped at 100 in request and response."""
        client, stub = source_config_client_with_mock_stub
        response = collection_pb2.ListSourceConfigsResponse(
            configs=[],
            next_page_token="",
            total_count=0,
        )
        stub.ListSourceConfigs.return_value = response

        result = await client.list_source_configs(page_size=200)

        call_args = stub.ListSourceConfigs.call_args
        request = call_args[0][0]
        assert request.page_size == 100
        assert result.pagination.page_size == 100

    @pytest.mark.asyncio
    async def test_list_source_configs_empty_result(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test source config listing with no results."""
        client, stub = source_config_client_with_mock_stub
        response = collection_pb2.ListSourceConfigsResponse(
            configs=[],
            next_page_token="",
            total_count=0,
        )
        stub.ListSourceConfigs.return_value = response

        result = await client.list_source_configs()

        assert len(result.data) == 0
        assert result.pagination.total_count == 0


class TestGetSourceConfig:
    """Tests for get_source_config method."""

    @pytest.mark.asyncio
    async def test_get_source_config_success(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test successful source config retrieval."""
        client, stub = source_config_client_with_mock_stub
        stub.GetSourceConfig.return_value = create_source_config_response_proto(
            source_id="qc-analyzer-result",
            display_name="QC Analyzer Results",
            config_json='{"source_id": "qc-analyzer-result", "enabled": true}',
        )

        result = await client.get_source_config("qc-analyzer-result")

        assert isinstance(result, SourceConfigDetail)
        assert result.source_id == "qc-analyzer-result"
        assert result.display_name == "QC Analyzer Results"
        assert result.config_json == '{"source_id": "qc-analyzer-result", "enabled": true}'
        assert result.created_at is not None
        assert result.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_source_config_not_found(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test source config not found error."""
        client, stub = source_config_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.NOT_FOUND,
            initial_metadata=None,
            trailing_metadata=None,
            details="Source config not found",
            debug_error_string="",
        )
        stub.GetSourceConfig.side_effect = error

        with pytest.raises(NotFoundError, match="Source config nonexistent not found"):
            await client.get_source_config("nonexistent")

    @pytest.mark.asyncio
    async def test_get_source_config_request_params(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test get_source_config sends correct request parameters."""
        client, stub = source_config_client_with_mock_stub
        stub.GetSourceConfig.return_value = create_source_config_response_proto()

        await client.get_source_config("my-source")

        call_args = stub.GetSourceConfig.call_args
        request = call_args[0][0]
        assert request.source_id == "my-source"


class TestErrorHandling:
    """Tests for error handling and retry logic."""

    @pytest.mark.asyncio
    async def test_service_unavailable_error_on_list(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test service unavailable error handling on list."""
        client, stub = source_config_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.UNAVAILABLE,
            initial_metadata=None,
            trailing_metadata=None,
            details="Connection refused",
            debug_error_string="",
        )
        stub.ListSourceConfigs.side_effect = error

        with pytest.raises(ServiceUnavailableError, match="Service unavailable"):
            await client.list_source_configs()

    @pytest.mark.asyncio
    async def test_service_unavailable_error_on_get(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test service unavailable error handling on get."""
        client, stub = source_config_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.UNAVAILABLE,
            initial_metadata=None,
            trailing_metadata=None,
            details="Connection refused",
            debug_error_string="",
        )
        stub.GetSourceConfig.side_effect = error

        with pytest.raises(ServiceUnavailableError, match="Service unavailable"):
            await client.get_source_config("source-123")

    @pytest.mark.asyncio
    async def test_unknown_grpc_error_propagated(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test unknown gRPC errors are propagated."""
        client, stub = source_config_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.INTERNAL,
            initial_metadata=None,
            trailing_metadata=None,
            details="Internal server error",
            debug_error_string="",
        )
        stub.GetSourceConfig.side_effect = error

        with pytest.raises(grpc.aio.AioRpcError):
            await client.get_source_config("source-123")


class TestProtoConversion:
    """Tests for proto-to-domain model conversion."""

    @pytest.mark.asyncio
    async def test_summary_fields_converted(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test all summary fields are correctly converted."""
        client, stub = source_config_client_with_mock_stub
        proto = create_source_config_summary_proto(
            source_id="custom-source",
            display_name="Custom Source",
            description="A custom source config",
            enabled=False,
            ingestion_mode="scheduled_pull",
            ai_agent_id="custom-agent-v2",
        )
        response = collection_pb2.ListSourceConfigsResponse(
            configs=[proto],
            next_page_token="",
            total_count=1,
        )
        stub.ListSourceConfigs.return_value = response

        result = await client.list_source_configs()

        config = result.data[0]
        assert config.source_id == "custom-source"
        assert config.display_name == "Custom Source"
        assert config.description == "A custom source config"
        assert config.enabled is False
        assert config.ingestion_mode == "scheduled_pull"
        assert config.ai_agent_id == "custom-agent-v2"
        assert config.updated_at is not None

    @pytest.mark.asyncio
    async def test_detail_fields_converted(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test all detail fields are correctly converted."""
        client, stub = source_config_client_with_mock_stub
        config_json = '{"source_id": "test", "ingestion": {"mode": "blob_trigger"}}'
        stub.GetSourceConfig.return_value = create_source_config_response_proto(
            source_id="test-source",
            display_name="Test Source",
            description="Test description",
            enabled=True,
            config_json=config_json,
        )

        result = await client.get_source_config("test-source")

        assert result.source_id == "test-source"
        assert result.display_name == "Test Source"
        assert result.description == "Test description"
        assert result.enabled is True
        assert result.config_json == config_json
        assert result.created_at is not None
        assert result.updated_at is not None

    @pytest.mark.asyncio
    async def test_nullable_ai_agent_id(
        self,
        source_config_client_with_mock_stub: tuple[SourceConfigClient, MagicMock],
    ) -> None:
        """Test empty ai_agent_id is converted to None."""
        client, stub = source_config_client_with_mock_stub
        proto = create_source_config_summary_proto(ai_agent_id="")
        response = collection_pb2.ListSourceConfigsResponse(
            configs=[proto],
            next_page_token="",
            total_count=1,
        )
        stub.ListSourceConfigs.return_value = response

        result = await client.list_source_configs()

        assert result.data[0].ai_agent_id is None


class TestClientClose:
    """Tests for client cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_channel(self) -> None:
        """Test close properly cleans up channel."""
        client = SourceConfigClient(direct_host="localhost:50051")
        mock_channel = AsyncMock()
        client._channel = mock_channel
        client._stubs["test"] = "value"

        await client.close()

        mock_channel.close.assert_called_once()
        assert client._channel is None
        assert client._stubs == {}
