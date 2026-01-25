"""Unit tests for SourceConfigServiceServicer (Story 9.11a).

Tests the gRPC service implementation for source config queries.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest
from collection_model.api.source_config_service import SourceConfigServiceServicer
from fp_proto.collection.v1 import collection_pb2

from tests.unit.collection.conftest import create_source_config


@pytest.fixture
def mock_repository():
    """Create a mock SourceConfigRepository."""
    return AsyncMock()


@pytest.fixture
def mock_db():
    """Create a mock MongoDB database."""
    return MagicMock()


@pytest.fixture
def mock_context():
    """Create a mock gRPC context."""
    context = AsyncMock(spec=grpc.aio.ServicerContext)
    context.abort = AsyncMock()
    return context


@pytest.fixture
def servicer(mock_db, mock_repository):
    """Create a SourceConfigServiceServicer with mocked repository."""
    with patch(
        "collection_model.api.source_config_service.SourceConfigRepository",
        return_value=mock_repository,
    ):
        return SourceConfigServiceServicer(mock_db)


class TestListSourceConfigs:
    """Tests for ListSourceConfigs RPC."""

    @pytest.mark.asyncio
    async def test_list_source_configs_no_filters(self, servicer, mock_context, mock_repository):
        """Test ListSourceConfigs with no filters returns all configs."""
        # Arrange
        configs = [
            create_source_config(source_id="config-1", enabled=True, mode="blob_trigger"),
            create_source_config(source_id="config-2", enabled=False, mode="scheduled_pull"),
        ]
        mock_repository.list_all.return_value = configs
        mock_repository.count.return_value = 2

        request = collection_pb2.ListSourceConfigsRequest()

        # Act
        response = await servicer.ListSourceConfigs(request, mock_context)

        # Assert
        assert len(response.configs) == 2
        assert response.total_count == 2
        assert response.next_page_token == ""
        mock_repository.list_all.assert_awaited_once_with(
            page_size=21,  # page_size + 1 for has_more check
            skip=0,
            enabled_only=False,
            ingestion_mode=None,
        )
        mock_repository.count.assert_awaited_once_with(enabled_only=False, ingestion_mode=None)

    @pytest.mark.asyncio
    async def test_list_source_configs_enabled_only(self, servicer, mock_context, mock_repository):
        """Test ListSourceConfigs with enabled_only=true filter."""
        # Arrange
        configs = [
            create_source_config(source_id="config-1", enabled=True),
        ]
        mock_repository.list_all.return_value = configs
        mock_repository.count.return_value = 1

        request = collection_pb2.ListSourceConfigsRequest(enabled_only=True)

        # Act
        response = await servicer.ListSourceConfigs(request, mock_context)

        # Assert
        assert len(response.configs) == 1
        assert response.configs[0].enabled is True
        mock_repository.list_all.assert_awaited_once_with(
            page_size=21,
            skip=0,
            enabled_only=True,
            ingestion_mode=None,
        )

    @pytest.mark.asyncio
    async def test_list_source_configs_ingestion_mode_blob_trigger(self, servicer, mock_context, mock_repository):
        """Test ListSourceConfigs with ingestion_mode='blob_trigger' filter."""
        # Arrange
        configs = [
            create_source_config(source_id="config-1", mode="blob_trigger"),
        ]
        mock_repository.list_all.return_value = configs
        mock_repository.count.return_value = 1

        request = collection_pb2.ListSourceConfigsRequest(ingestion_mode="blob_trigger")

        # Act
        response = await servicer.ListSourceConfigs(request, mock_context)

        # Assert
        assert len(response.configs) == 1
        assert response.configs[0].ingestion_mode == "blob_trigger"
        mock_repository.list_all.assert_awaited_once_with(
            page_size=21,
            skip=0,
            enabled_only=False,
            ingestion_mode="blob_trigger",
        )

    @pytest.mark.asyncio
    async def test_list_source_configs_ingestion_mode_scheduled_pull(self, servicer, mock_context, mock_repository):
        """Test ListSourceConfigs with ingestion_mode='scheduled_pull' filter."""
        # Arrange
        configs = [
            create_source_config(source_id="config-1", mode="scheduled_pull", schedule="0 * * * *", provider="test"),
        ]
        mock_repository.list_all.return_value = configs
        mock_repository.count.return_value = 1

        request = collection_pb2.ListSourceConfigsRequest(ingestion_mode="scheduled_pull")

        # Act
        response = await servicer.ListSourceConfigs(request, mock_context)

        # Assert
        assert len(response.configs) == 1
        assert response.configs[0].ingestion_mode == "scheduled_pull"
        mock_repository.list_all.assert_awaited_once_with(
            page_size=21,
            skip=0,
            enabled_only=False,
            ingestion_mode="scheduled_pull",
        )

    @pytest.mark.asyncio
    async def test_list_source_configs_pagination(self, servicer, mock_context, mock_repository):
        """Test ListSourceConfigs with page_size and page_token."""
        # Arrange
        # Return page_size + 1 to indicate there are more results
        configs = [create_source_config(source_id=f"config-{i}") for i in range(6)]
        mock_repository.list_all.return_value = configs
        mock_repository.count.return_value = 10

        request = collection_pb2.ListSourceConfigsRequest(page_size=5, page_token="")

        # Act
        response = await servicer.ListSourceConfigs(request, mock_context)

        # Assert
        assert len(response.configs) == 5
        assert response.total_count == 10
        assert response.next_page_token == "5"
        mock_repository.list_all.assert_awaited_once_with(
            page_size=6,  # page_size + 1
            skip=0,
            enabled_only=False,
            ingestion_mode=None,
        )

    @pytest.mark.asyncio
    async def test_list_source_configs_second_page(self, servicer, mock_context, mock_repository):
        """Test ListSourceConfigs second page using page_token."""
        # Arrange
        configs = [create_source_config(source_id=f"config-{i}") for i in range(3)]
        mock_repository.list_all.return_value = configs
        mock_repository.count.return_value = 8

        request = collection_pb2.ListSourceConfigsRequest(page_size=5, page_token="5")

        # Act
        response = await servicer.ListSourceConfigs(request, mock_context)

        # Assert
        assert len(response.configs) == 3
        assert response.next_page_token == ""  # No more pages
        mock_repository.list_all.assert_awaited_once_with(
            page_size=6,
            skip=5,
            enabled_only=False,
            ingestion_mode=None,
        )

    @pytest.mark.asyncio
    async def test_list_source_configs_empty_result(self, servicer, mock_context, mock_repository):
        """Test ListSourceConfigs with empty result set."""
        # Arrange
        mock_repository.list_all.return_value = []
        mock_repository.count.return_value = 0

        request = collection_pb2.ListSourceConfigsRequest()

        # Act
        response = await servicer.ListSourceConfigs(request, mock_context)

        # Assert
        assert len(response.configs) == 0
        assert response.total_count == 0
        assert response.next_page_token == ""

    @pytest.mark.asyncio
    async def test_list_source_configs_invalid_page_token(self, servicer, mock_context, mock_repository):
        """Test ListSourceConfigs with invalid page_token resets to 0."""
        # Arrange
        configs = [create_source_config(source_id="config-1")]
        mock_repository.list_all.return_value = configs
        mock_repository.count.return_value = 1

        request = collection_pb2.ListSourceConfigsRequest(page_token="invalid")

        # Act
        response = await servicer.ListSourceConfigs(request, mock_context)

        # Assert
        assert len(response.configs) == 1
        mock_repository.list_all.assert_awaited_once_with(
            page_size=21,
            skip=0,  # Reset to 0 for invalid token
            enabled_only=False,
            ingestion_mode=None,
        )

    @pytest.mark.asyncio
    async def test_list_source_configs_negative_page_token(self, servicer, mock_context, mock_repository):
        """Test ListSourceConfigs with negative page_token resets to 0."""
        # Arrange
        configs = [create_source_config(source_id="config-1")]
        mock_repository.list_all.return_value = configs
        mock_repository.count.return_value = 1

        request = collection_pb2.ListSourceConfigsRequest(page_token="-5")

        # Act
        response = await servicer.ListSourceConfigs(request, mock_context)

        # Assert
        assert len(response.configs) == 1
        mock_repository.list_all.assert_awaited_once_with(
            page_size=21,
            skip=0,  # Reset to 0 for negative token
            enabled_only=False,
            ingestion_mode=None,
        )

    @pytest.mark.asyncio
    async def test_list_source_configs_max_page_size(self, servicer, mock_context, mock_repository):
        """Test ListSourceConfigs caps page_size at 100."""
        # Arrange
        mock_repository.list_all.return_value = []
        mock_repository.count.return_value = 0

        request = collection_pb2.ListSourceConfigsRequest(page_size=500)

        # Act
        await servicer.ListSourceConfigs(request, mock_context)

        # Assert
        mock_repository.list_all.assert_awaited_once_with(
            page_size=101,  # Capped at 100, then +1 for has_more check
            skip=0,
            enabled_only=False,
            ingestion_mode=None,
        )


class TestGetSourceConfig:
    """Tests for GetSourceConfig RPC."""

    @pytest.mark.asyncio
    async def test_get_source_config_success(self, servicer, mock_context, mock_repository):
        """Test GetSourceConfig returns full config with JSON."""
        # Arrange
        config = create_source_config(
            source_id="test-config",
            display_name="Test Config",
            mode="blob_trigger",
            ai_agent_id="qc-extractor-agent",
        )
        mock_repository.get_by_source_id.return_value = config

        request = collection_pb2.GetSourceConfigRequest(source_id="test-config")

        # Act
        response = await servicer.GetSourceConfig(request, mock_context)

        # Assert
        assert response.source_id == "test-config"
        assert response.display_name == "Test Config"
        assert response.enabled is True
        assert "test-config" in response.config_json
        mock_repository.get_by_source_id.assert_awaited_once_with("test-config")
        mock_context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_source_config_not_found(self, servicer, mock_context, mock_repository):
        """Test GetSourceConfig returns NOT_FOUND for invalid source_id."""
        # Arrange
        mock_repository.get_by_source_id.return_value = None

        request = collection_pb2.GetSourceConfigRequest(source_id="nonexistent")

        # Act
        await servicer.GetSourceConfig(request, mock_context)

        # Assert
        mock_context.abort.assert_awaited_once_with(
            grpc.StatusCode.NOT_FOUND,
            "Source config not found: nonexistent",
        )

    @pytest.mark.asyncio
    async def test_get_source_config_empty_source_id(self, servicer, mock_context, mock_repository):
        """Test GetSourceConfig returns INVALID_ARGUMENT for empty source_id."""
        # Arrange
        request = collection_pb2.GetSourceConfigRequest(source_id="")

        # Act
        await servicer.GetSourceConfig(request, mock_context)

        # Assert
        mock_context.abort.assert_awaited_once_with(
            grpc.StatusCode.INVALID_ARGUMENT,
            "source_id is required",
        )
        mock_repository.get_by_source_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_source_config_json_contains_full_config(self, servicer, mock_context, mock_repository):
        """Test GetSourceConfig config_json includes all nested config."""
        # Arrange
        config = create_source_config(
            source_id="full-config",
            mode="scheduled_pull",
            schedule="0 * * * *",
            provider="test-provider",
            iteration={
                "foreach": "regions",
                "source_mcp": "plantation-mcp",
                "source_tool": "get_all_regions",
                "concurrency": 5,
            },
        )
        mock_repository.get_by_source_id.return_value = config

        request = collection_pb2.GetSourceConfigRequest(source_id="full-config")

        # Act
        response = await servicer.GetSourceConfig(request, mock_context)

        # Assert
        assert "scheduled_pull" in response.config_json
        assert "0 * * * *" in response.config_json
        assert "test-provider" in response.config_json
        assert "regions" in response.config_json
