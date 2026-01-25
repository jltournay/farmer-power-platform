"""E2E Tests for SourceConfigService gRPC (Story 9.11a).

Tests the read-only gRPC service for source config queries.
Uses seed data from tests/e2e/infrastructure/seed/source_configs.json.

Seed data contains 5 configs:
- e2e-qc-direct-json (blob_trigger, enabled)
- e2e-qc-analyzer-json (blob_trigger, enabled)
- e2e-manual-upload (blob_trigger, enabled)
- e2e-weather-api (scheduled_pull, enabled)
- e2e-exception-images-zip (blob_trigger, enabled)
"""

import json

import grpc
import pytest

from tests.e2e.helpers.mcp_clients import CollectionServiceError


@pytest.mark.e2e
class TestListSourceConfigs:
    """Tests for ListSourceConfigs RPC."""

    @pytest.mark.asyncio
    async def test_list_source_configs_returns_all(self, collection_service, seed_data):
        """Test ListSourceConfigs returns all configs from seed data."""
        # Act
        result = await collection_service.list_source_configs()

        # Assert
        assert "configs" in result
        assert "total_count" in result
        assert result["total_count"] >= 5  # At least 5 from seed data

        # Verify we got configs with expected fields
        configs = result["configs"]
        assert len(configs) >= 5
        for config in configs:
            assert "source_id" in config
            assert "display_name" in config
            assert "enabled" in config
            assert "ingestion_mode" in config

    @pytest.mark.asyncio
    async def test_list_source_configs_with_enabled_filter(self, collection_service, seed_data):
        """Test ListSourceConfigs with enabled_only=true filter."""
        # Act
        result = await collection_service.list_source_configs(enabled_only=True)

        # Assert
        configs = result.get("configs", [])
        assert len(configs) >= 5  # All seed configs are enabled

        # All returned configs should be enabled
        for config in configs:
            assert config.get("enabled") is True

    @pytest.mark.asyncio
    async def test_list_source_configs_with_blob_trigger_filter(self, collection_service, seed_data):
        """Test ListSourceConfigs with ingestion_mode='blob_trigger' filter."""
        # Act
        result = await collection_service.list_source_configs(ingestion_mode="blob_trigger")

        # Assert
        configs = result.get("configs", [])
        assert len(configs) >= 4  # 4 blob_trigger configs in seed data

        # All returned configs should be blob_trigger mode
        for config in configs:
            assert config.get("ingestion_mode") == "blob_trigger"

    @pytest.mark.asyncio
    async def test_list_source_configs_with_scheduled_pull_filter(self, collection_service, seed_data):
        """Test ListSourceConfigs with ingestion_mode='scheduled_pull' filter."""
        # Act
        result = await collection_service.list_source_configs(ingestion_mode="scheduled_pull")

        # Assert
        configs = result.get("configs", [])
        assert len(configs) >= 1  # 1 scheduled_pull config in seed data (e2e-weather-api)

        # All returned configs should be scheduled_pull mode
        for config in configs:
            assert config.get("ingestion_mode") == "scheduled_pull"

    @pytest.mark.asyncio
    async def test_list_source_configs_pagination(self, collection_service, seed_data):
        """Test ListSourceConfigs pagination works correctly."""
        # Act - First page with small page_size
        first_page = await collection_service.list_source_configs(page_size=2)

        # Assert first page
        assert len(first_page.get("configs", [])) == 2
        assert first_page["total_count"] >= 5

        # If there are more results, next_page_token should be set
        if first_page["total_count"] > 2:
            assert first_page.get("next_page_token")

            # Act - Second page
            second_page = await collection_service.list_source_configs(
                page_size=2,
                page_token=first_page["next_page_token"],
            )

            # Assert second page has different configs
            first_ids = {c["source_id"] for c in first_page["configs"]}
            second_ids = {c["source_id"] for c in second_page["configs"]}
            assert first_ids.isdisjoint(second_ids), "Pages should not overlap"

    @pytest.mark.asyncio
    async def test_list_source_configs_combined_filters(self, collection_service, seed_data):
        """Test ListSourceConfigs with multiple filters."""
        # Act - enabled + blob_trigger
        result = await collection_service.list_source_configs(
            enabled_only=True,
            ingestion_mode="blob_trigger",
        )

        # Assert
        configs = result.get("configs", [])
        for config in configs:
            assert config.get("enabled") is True
            assert config.get("ingestion_mode") == "blob_trigger"


@pytest.mark.e2e
class TestGetSourceConfig:
    """Tests for GetSourceConfig RPC."""

    @pytest.mark.asyncio
    async def test_get_source_config_returns_full_json(self, collection_service, seed_data):
        """Test GetSourceConfig returns full config with JSON."""
        # Act
        result = await collection_service.get_source_config("e2e-qc-direct-json")

        # Assert
        assert result["source_id"] == "e2e-qc-direct-json"
        assert result["display_name"] == "E2E QC Direct JSON"
        assert result["enabled"] is True
        assert "config_json" in result

        # Verify config_json is valid JSON with full config
        config_json = json.loads(result["config_json"])
        assert config_json["source_id"] == "e2e-qc-direct-json"
        assert "ingestion" in config_json
        assert "transformation" in config_json
        assert "storage" in config_json

    @pytest.mark.asyncio
    async def test_get_source_config_scheduled_pull(self, collection_service, seed_data):
        """Test GetSourceConfig for scheduled_pull config."""
        # Act
        result = await collection_service.get_source_config("e2e-weather-api")

        # Assert
        assert result["source_id"] == "e2e-weather-api"
        assert "config_json" in result

        # Verify scheduled_pull specific fields in JSON
        config_json = json.loads(result["config_json"])
        assert config_json["ingestion"]["mode"] == "scheduled_pull"
        assert "iteration" in config_json["ingestion"]

    @pytest.mark.asyncio
    async def test_get_source_config_not_found(self, collection_service, seed_data):
        """Test GetSourceConfig returns NOT_FOUND for invalid source_id."""
        # Act & Assert
        with pytest.raises(CollectionServiceError) as exc_info:
            await collection_service.get_source_config("nonexistent-source-id")

        assert exc_info.value.code == grpc.StatusCode.NOT_FOUND
        assert "not found" in exc_info.value.details.lower()

    @pytest.mark.asyncio
    async def test_get_source_config_empty_source_id(self, collection_service, seed_data):
        """Test GetSourceConfig returns INVALID_ARGUMENT for empty source_id."""
        # Act & Assert
        with pytest.raises(CollectionServiceError) as exc_info:
            await collection_service.get_source_config("")

        assert exc_info.value.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.e2e
class TestSourceConfigServiceConnectivity:
    """Verify SourceConfigService is accessible."""

    @pytest.mark.asyncio
    async def test_source_config_service_connectivity(self, collection_service):
        """Verify SourceConfigService is reachable via gRPC."""
        # Act - try to list configs (uses SourceConfigService)
        result = await collection_service.list_source_configs(page_size=1)

        # Assert - should return a valid response
        assert "configs" in result or "total_count" in result
        print("SourceConfigService gRPC: OK")
