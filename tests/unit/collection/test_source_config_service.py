"""Unit tests for SourceConfigService."""

from datetime import UTC, datetime, timedelta

import pytest
from collection_model.services.source_config_service import SourceConfigService


class TestSourceConfigServiceCaching:
    """Tests for SourceConfigService caching behavior."""

    @pytest.mark.asyncio
    async def test_get_all_configs_caches_results(self, mock_mongodb_client) -> None:
        """Test that configs are cached after first call."""
        db = mock_mongodb_client["collection_model"]

        # Insert test config
        await db["source_configs"].insert_one(
            {
                "source_id": "qc-analyzer",
                "enabled": True,
                "ingestion": {"mode": "blob_trigger"},
            }
        )

        service = SourceConfigService(db)

        # First call should fetch from DB
        configs1 = await service.get_all_configs()
        assert len(configs1) == 1

        # Insert another config
        await db["source_configs"].insert_one(
            {
                "source_id": "qc-analyzer-2",
                "enabled": True,
                "ingestion": {"mode": "blob_trigger"},
            }
        )

        # Second call should return cached results
        configs2 = await service.get_all_configs()
        assert len(configs2) == 1  # Still 1 because of cache

    @pytest.mark.asyncio
    async def test_invalidate_cache_forces_refresh(self, mock_mongodb_client) -> None:
        """Test that invalidate_cache forces refresh on next call."""
        db = mock_mongodb_client["collection_model"]

        await db["source_configs"].insert_one(
            {
                "source_id": "qc-analyzer",
                "enabled": True,
                "ingestion": {"mode": "blob_trigger"},
            }
        )

        service = SourceConfigService(db)

        # First call
        configs1 = await service.get_all_configs()
        assert len(configs1) == 1

        # Insert another config
        await db["source_configs"].insert_one(
            {
                "source_id": "qc-analyzer-2",
                "enabled": True,
                "ingestion": {"mode": "blob_trigger"},
            }
        )

        # Invalidate cache
        service.invalidate_cache()

        # Next call should fetch fresh data
        configs2 = await service.get_all_configs()
        assert len(configs2) == 2

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self, mock_mongodb_client) -> None:
        """Test that cache expires after TTL."""
        db = mock_mongodb_client["collection_model"]

        await db["source_configs"].insert_one(
            {
                "source_id": "qc-analyzer",
                "enabled": True,
                "ingestion": {"mode": "blob_trigger"},
            }
        )

        service = SourceConfigService(db)

        # First call
        await service.get_all_configs()

        # Manually expire the cache
        service._cache_expires = datetime.now(UTC) - timedelta(minutes=1)

        # Insert another config
        await db["source_configs"].insert_one(
            {
                "source_id": "qc-analyzer-2",
                "enabled": True,
                "ingestion": {"mode": "blob_trigger"},
            }
        )

        # Next call should fetch fresh data due to expired cache
        configs = await service.get_all_configs()
        assert len(configs) == 2

    @pytest.mark.asyncio
    async def test_only_enabled_configs_returned(self, mock_mongodb_client) -> None:
        """Test that only enabled configs are returned."""
        db = mock_mongodb_client["collection_model"]

        await db["source_configs"].insert_one({"source_id": "enabled-source", "enabled": True})
        await db["source_configs"].insert_one({"source_id": "disabled-source", "enabled": False})

        service = SourceConfigService(db)
        configs = await service.get_all_configs()

        assert len(configs) == 1
        assert configs[0]["source_id"] == "enabled-source"


class TestSourceConfigServiceContainerLookup:
    """Tests for container-based config lookup."""

    @pytest.mark.asyncio
    async def test_get_config_by_container_finds_match(self, mock_mongodb_client) -> None:
        """Test finding config by container name."""
        db = mock_mongodb_client["collection_model"]

        await db["source_configs"].insert_one(
            {
                "source_id": "qc-analyzer",
                "enabled": True,
                "ingestion": {
                    "mode": "blob_trigger",
                    "landing_container": "qc-analyzer-landing",
                },
            }
        )

        service = SourceConfigService(db)
        config = await service.get_config_by_container("qc-analyzer-landing")

        assert config is not None
        assert config["source_id"] == "qc-analyzer"

    @pytest.mark.asyncio
    async def test_get_config_by_container_returns_none_for_no_match(self, mock_mongodb_client) -> None:
        """Test returns None when no config matches container."""
        db = mock_mongodb_client["collection_model"]

        await db["source_configs"].insert_one(
            {
                "source_id": "qc-analyzer",
                "enabled": True,
                "ingestion": {
                    "mode": "blob_trigger",
                    "landing_container": "qc-analyzer-landing",
                },
            }
        )

        service = SourceConfigService(db)
        config = await service.get_config_by_container("unknown-container")

        assert config is None

    @pytest.mark.asyncio
    async def test_get_config_by_container_ignores_non_blob_trigger(self, mock_mongodb_client) -> None:
        """Test that non-blob_trigger configs are ignored."""
        db = mock_mongodb_client["collection_model"]

        await db["source_configs"].insert_one(
            {
                "source_id": "weather-api",
                "enabled": True,
                "ingestion": {
                    "mode": "api_pull",  # Not blob_trigger
                    "landing_container": "weather-data",
                },
            }
        )

        service = SourceConfigService(db)
        config = await service.get_config_by_container("weather-data")

        assert config is None


class TestPathMetadataExtraction:
    """Tests for path pattern metadata extraction."""

    def test_extract_path_metadata_basic_pattern(self) -> None:
        """Test basic path pattern extraction."""
        config = {
            "ingestion": {
                "path_pattern": {
                    "pattern": "results/{plantation_id}/{crop}/{batch_id}.json",
                    "extract_fields": ["plantation_id", "crop", "batch_id"],
                }
            }
        }

        metadata = SourceConfigService.extract_path_metadata("results/WM-4521/tea/batch-001.json", config)

        assert metadata == {
            "plantation_id": "WM-4521",
            "crop": "tea",
            "batch_id": "batch-001",
        }

    def test_extract_path_metadata_partial_fields(self) -> None:
        """Test extracting only specified fields."""
        config = {
            "ingestion": {
                "path_pattern": {
                    "pattern": "results/{plantation_id}/{crop}/{batch_id}.json",
                    "extract_fields": ["plantation_id"],  # Only extract one field
                }
            }
        }

        metadata = SourceConfigService.extract_path_metadata("results/WM-4521/tea/batch-001.json", config)

        assert metadata == {"plantation_id": "WM-4521"}

    def test_extract_path_metadata_no_match(self) -> None:
        """Test returns empty dict when path doesn't match pattern."""
        config = {
            "ingestion": {
                "path_pattern": {
                    "pattern": "results/{plantation_id}/{batch_id}.json",
                    "extract_fields": ["plantation_id"],
                }
            }
        }

        metadata = SourceConfigService.extract_path_metadata("other/path/to/file.json", config)

        assert metadata == {}

    def test_extract_path_metadata_no_pattern(self) -> None:
        """Test returns empty dict when no path_pattern in config."""
        config = {"ingestion": {}}

        metadata = SourceConfigService.extract_path_metadata("results/WM-4521/tea/batch-001.json", config)

        assert metadata == {}

    def test_extract_path_metadata_with_dots_in_filename(self) -> None:
        """Test extraction works with dots in filename pattern."""
        config = {
            "ingestion": {
                "path_pattern": {
                    "pattern": "data/{device_id}/{date}.data.json",
                    "extract_fields": ["device_id", "date"],
                }
            }
        }

        metadata = SourceConfigService.extract_path_metadata("data/device-001/2025-12-26.data.json", config)

        assert metadata == {"device_id": "device-001", "date": "2025-12-26"}

    def test_extract_path_metadata_deeply_nested(self) -> None:
        """Test extraction with deeply nested paths."""
        config = {
            "ingestion": {
                "path_pattern": {
                    "pattern": "{year}/{month}/{day}/{factory}/{device}/{file}.json",
                    "extract_fields": ["year", "month", "day", "factory", "device"],
                }
            }
        }

        metadata = SourceConfigService.extract_path_metadata("2025/12/26/FAC-001/device-001/result.json", config)

        assert metadata == {
            "year": "2025",
            "month": "12",
            "day": "26",
            "factory": "FAC-001",
            "device": "device-001",
        }
