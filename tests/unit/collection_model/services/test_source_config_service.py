"""Unit tests for SourceConfigService (Story 0.6.9, ADR-007).

Tests cover:
- Startup cache warming (AC1)
- Change stream invalidation (AC2)
- Cache hit/miss tracking (AC3)
- Resilient reconnection (AC4)
- OpenTelemetry metrics instrumentation
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCacheWarming:
    """Tests for startup cache warming (AC1)."""

    @pytest.mark.asyncio
    async def test_cache_warmed_on_startup(self, mock_mongodb_client: Any) -> None:
        """Cache is populated with all configs on startup."""
        # Import here to avoid issues with module-level metrics initialization
        from collection_model.services.source_config_service import SourceConfigService

        # Arrange
        db = mock_mongodb_client["collection_model"]
        configs_collection = db["source_configs"]

        # Pre-populate source configs
        await configs_collection.insert_one(
            {
                "source_id": "qc-analyzer",
                "display_name": "QC Analyzer",
                "description": "Test config",
                "enabled": True,
                "ingestion": {
                    "mode": "blob_trigger",
                    "landing_container": "qc-results",
                },
                "transformation": {
                    "extract_fields": ["farmer_id"],
                    "link_field": "farmer_id",
                },
                "storage": {
                    "raw_container": "raw",
                    "index_collection": "documents_index",
                },
            }
        )
        await configs_collection.insert_one(
            {
                "source_id": "weather-api",
                "display_name": "Weather API",
                "description": "Weather data",
                "enabled": True,
                "ingestion": {
                    "mode": "scheduled_pull",
                },
                "transformation": {
                    "extract_fields": ["region_id"],
                    "link_field": "region_id",
                },
                "storage": {
                    "raw_container": "raw",
                    "index_collection": "weather_data",
                },
            }
        )

        service = SourceConfigService(db)

        # Act
        config_count = await service.warm_cache()

        # Assert
        assert config_count == 2
        assert service._cache is not None
        assert len(service._cache) == 2
        assert service._cache_loaded_at is not None

    @pytest.mark.asyncio
    async def test_cache_size_metric_set_on_warm(self, mock_mongodb_client: Any) -> None:
        """Cache size metric is set after warming."""
        from collection_model.services.source_config_service import (
            SourceConfigService,
            cache_size_gauge,
        )

        db = mock_mongodb_client["collection_model"]

        # Add one config
        await db["source_configs"].insert_one(
            {
                "source_id": "test",
                "display_name": "Test",
                "description": "Test",
                "enabled": True,
                "ingestion": {"mode": "blob_trigger"},
                "transformation": {"extract_fields": [], "link_field": "id"},
                "storage": {"raw_container": "raw", "index_collection": "docs"},
            }
        )

        service = SourceConfigService(db)

        with patch.object(cache_size_gauge, "set") as mock_set:
            await service.warm_cache()
            mock_set.assert_called_with(1)


class TestChangeStreamInvalidation:
    """Tests for change stream cache invalidation (AC2)."""

    @pytest.mark.asyncio
    async def test_invalidate_cache_clears_cache(self, mock_mongodb_client: Any) -> None:
        """Cache is cleared when invalidated."""
        from collection_model.services.source_config_service import SourceConfigService

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)

        # Manually set cache
        service._cache = [MagicMock()]
        service._cache_loaded_at = datetime.now(UTC)
        service._cache_expires = datetime.now(UTC) + timedelta(minutes=5)

        # Act
        service._invalidate_cache(reason="change_stream:insert")

        # Assert
        assert service._cache is None
        assert service._cache_loaded_at is None
        assert service._cache_expires is None

    @pytest.mark.asyncio
    async def test_invalidation_metric_incremented(self, mock_mongodb_client: Any) -> None:
        """Invalidation metric is incremented on cache clear."""
        from collection_model.services.source_config_service import (
            SourceConfigService,
            cache_invalidations_counter,
        )

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)

        with patch.object(cache_invalidations_counter, "add") as mock_add:
            service._invalidate_cache(reason="change_stream:update")
            mock_add.assert_called_once_with(1, {"reason": "change_stream:update"})

    @pytest.mark.asyncio
    async def test_manual_invalidation(self, mock_mongodb_client: Any) -> None:
        """Manual invalidation uses 'manual' reason."""
        from collection_model.services.source_config_service import (
            SourceConfigService,
            cache_invalidations_counter,
        )

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)

        with patch.object(cache_invalidations_counter, "add") as mock_add:
            service.invalidate_cache()
            mock_add.assert_called_once_with(1, {"reason": "manual"})


class TestCacheHitMiss:
    """Tests for cache hit/miss tracking (AC3)."""

    @pytest.mark.asyncio
    async def test_cache_hit_increments_metric(self, mock_mongodb_client: Any) -> None:
        """Cache hit increments hit counter."""
        from collection_model.services.source_config_service import (
            SourceConfigService,
            cache_hits_counter,
        )

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)

        # Pre-warm the cache
        await db["source_configs"].insert_one(
            {
                "source_id": "test",
                "display_name": "Test",
                "description": "Test",
                "enabled": True,
                "ingestion": {"mode": "blob_trigger"},
                "transformation": {"extract_fields": [], "link_field": "id"},
                "storage": {"raw_container": "raw", "index_collection": "docs"},
            }
        )
        await service.warm_cache()

        # Act - second call should be cache hit
        with patch.object(cache_hits_counter, "add") as mock_add:
            await service.get_all_configs()
            mock_add.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_cache_miss_increments_metric(self, mock_mongodb_client: Any) -> None:
        """Cache miss increments miss counter."""
        from collection_model.services.source_config_service import (
            SourceConfigService,
            cache_misses_counter,
        )

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)

        # Ensure cache is empty
        assert service._cache is None

        # Act - first call should be cache miss
        with patch.object(cache_misses_counter, "add") as mock_add:
            await service.get_all_configs()
            mock_add.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_config_returns_correct_config(self, mock_mongodb_client: Any) -> None:
        """get_config returns the correct config by source_id."""
        from collection_model.services.source_config_service import SourceConfigService

        db = mock_mongodb_client["collection_model"]

        await db["source_configs"].insert_one(
            {
                "source_id": "qc-analyzer",
                "display_name": "QC Analyzer",
                "description": "Test",
                "enabled": True,
                "ingestion": {"mode": "blob_trigger", "landing_container": "qc"},
                "transformation": {"extract_fields": [], "link_field": "id"},
                "storage": {"raw_container": "raw", "index_collection": "docs"},
            }
        )

        service = SourceConfigService(db)
        await service.warm_cache()

        # Act
        config = await service.get_config("qc-analyzer")

        # Assert
        assert config is not None
        assert config.source_id == "qc-analyzer"

    @pytest.mark.asyncio
    async def test_get_config_returns_none_for_unknown(self, mock_mongodb_client: Any) -> None:
        """get_config returns None for unknown source_id."""
        from collection_model.services.source_config_service import SourceConfigService

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)
        await service.warm_cache()

        # Act
        config = await service.get_config("non-existent")

        # Assert
        assert config is None


class TestChangeStreamLifecycle:
    """Tests for change stream start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_change_stream_creates_task(self, mock_mongodb_client: Any) -> None:
        """start_change_stream creates a background task."""
        from collection_model.services.source_config_service import SourceConfigService

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)

        # Mock the _collection with a watch method
        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock()
        mock_stream.__aiter__ = lambda self: self
        mock_stream.__anext__ = AsyncMock(side_effect=asyncio.CancelledError)

        mock_collection = MagicMock()
        mock_collection.watch = MagicMock(return_value=mock_stream)
        service._collection = mock_collection

        await service.start_change_stream()

        # Assert
        assert service._change_stream_task is not None
        assert service._change_stream_active is True

        # Cleanup
        await service.stop_change_stream()

    @pytest.mark.asyncio
    async def test_stop_change_stream_cancels_task(self, mock_mongodb_client: Any) -> None:
        """stop_change_stream cancels the background task."""
        from collection_model.services.source_config_service import SourceConfigService

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)

        # Create a mock task
        service._change_stream_task = asyncio.create_task(asyncio.sleep(100))
        service._change_stream_active = True

        # Act
        await service.stop_change_stream()

        # Assert
        assert service._change_stream_active is False
        assert service._change_stream_task is None


class TestCacheHealthStatus:
    """Tests for cache health status (Task 5)."""

    @pytest.mark.asyncio
    async def test_get_cache_age_returns_negative_when_empty(self, mock_mongodb_client: Any) -> None:
        """get_cache_age returns -1 when cache is not loaded."""
        from collection_model.services.source_config_service import SourceConfigService

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)

        # Assert
        assert service.get_cache_age() == -1.0

    @pytest.mark.asyncio
    async def test_get_cache_age_returns_positive_after_warm(self, mock_mongodb_client: Any) -> None:
        """get_cache_age returns positive value after warming."""
        from collection_model.services.source_config_service import SourceConfigService

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)

        await service.warm_cache()

        # Assert
        age = service.get_cache_age()
        assert age >= 0

    @pytest.mark.asyncio
    async def test_get_cache_status_structure(self, mock_mongodb_client: Any) -> None:
        """get_cache_status returns correct structure."""
        from collection_model.services.source_config_service import SourceConfigService

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)

        await service.warm_cache()

        # Act
        status = service.get_cache_status()

        # Assert
        assert "cache_size" in status
        assert "cache_age_seconds" in status
        assert "change_stream_active" in status
        assert isinstance(status["cache_size"], int)
        assert isinstance(status["cache_age_seconds"], float)
        assert isinstance(status["change_stream_active"], bool)


class TestResumeToken:
    """Tests for resume token handling (AC4)."""

    @pytest.mark.asyncio
    async def test_resume_token_initialized_none(self, mock_mongodb_client: Any) -> None:
        """Resume token is None on initialization."""
        from collection_model.services.source_config_service import SourceConfigService

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)

        # Assert
        assert service._resume_token is None

    @pytest.mark.asyncio
    async def test_resume_token_passed_to_watch_on_reconnect(self, mock_mongodb_client: Any) -> None:
        """Resume token is passed to watch() for resilient reconnection (AC4).

        Verifies that when the service has a stored resume token from a previous
        connection, it passes that token to watch() to resume from where it left off.
        """
        from collection_model.services.source_config_service import SourceConfigService

        db = mock_mongodb_client["collection_model"]
        service = SourceConfigService(db)

        # Simulate a stored resume token from a previous connection
        fake_resume_token = {"_data": "test_resume_token_12345"}
        service._resume_token = fake_resume_token

        # Create a mock async context manager for the change stream
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        # Make the stream immediately raise CancelledError on iteration
        async def raise_cancelled():
            raise asyncio.CancelledError

        mock_stream.__aiter__ = MagicMock(return_value=mock_stream)
        mock_stream.__anext__ = raise_cancelled

        # Mock the collection watch method
        mock_collection = MagicMock()
        mock_collection.watch = MagicMock(return_value=mock_stream)
        service._collection = mock_collection

        # Start change stream - this creates the background task
        await service.start_change_stream()

        # Give the task a moment to start and call watch()
        await asyncio.sleep(0.05)

        # Stop change stream
        await service.stop_change_stream()

        # Verify watch was called with the resume token
        mock_collection.watch.assert_called_once()
        call_kwargs = mock_collection.watch.call_args[1]
        assert call_kwargs.get("resume_after") == fake_resume_token
