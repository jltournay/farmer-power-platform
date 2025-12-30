"""Unit tests for PullJobHandler (Story 2.7).

Tests cover pull job execution:
- Loading source config
- Single fetch (no iteration)
- Multi-fetch with iteration and concurrency limits
- Error handling and metrics
- Linkage injection from iteration items
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from collection_model.services.pull_job_handler import PullJobHandler
from fp_common.models.source_config import SourceConfig


class TestPullJobHandler:
    """Tests for PullJobHandler."""

    @pytest.fixture
    def mock_source_config_service(self) -> MagicMock:
        """Create mock SourceConfigService."""
        service = MagicMock()
        service.get_config = AsyncMock(return_value=None)
        return service

    @pytest.fixture
    def mock_pull_data_fetcher(self) -> MagicMock:
        """Create mock PullDataFetcher."""
        fetcher = MagicMock()
        fetcher.fetch = AsyncMock(return_value=b'{"temperature": 22.5}')
        return fetcher

    @pytest.fixture
    def mock_iteration_resolver(self) -> MagicMock:
        """Create mock IterationResolver."""
        resolver = MagicMock()
        resolver.resolve = AsyncMock(return_value=[])
        resolver.extract_linkage = MagicMock(return_value={})
        return resolver

    @pytest.fixture
    def mock_processor(self) -> MagicMock:
        """Create mock processor."""
        processor = MagicMock()
        processor.process = AsyncMock(return_value=MagicMock(success=True, is_duplicate=False))
        return processor

    @pytest.fixture
    def mock_ingestion_queue(self) -> MagicMock:
        """Create mock IngestionQueue."""
        queue = MagicMock()
        queue.update_status = AsyncMock()
        return queue

    @pytest.fixture
    def pull_job_handler(
        self,
        mock_source_config_service: MagicMock,
        mock_pull_data_fetcher: MagicMock,
        mock_iteration_resolver: MagicMock,
        mock_processor: MagicMock,
        mock_ingestion_queue: MagicMock,
    ) -> PullJobHandler:
        """Create PullJobHandler with mocked dependencies."""
        return PullJobHandler(
            source_config_service=mock_source_config_service,
            pull_data_fetcher=mock_pull_data_fetcher,
            iteration_resolver=mock_iteration_resolver,
            processor=mock_processor,
            ingestion_queue=mock_ingestion_queue,
        )

    @pytest.fixture
    def sample_source_config_no_iteration(self) -> SourceConfig:
        """Sample source config without iteration."""
        return SourceConfig.model_validate(
            {
                "source_id": "weather-api",
                "display_name": "Weather API",
                "description": "Weather data from Open-Meteo",
                "enabled": True,
                "ingestion": {
                    "mode": "scheduled_pull",
                    "schedule": "0 6 * * *",
                    "provider": "open-meteo",
                    "request": {
                        "base_url": "https://api.open-meteo.com/v1/forecast",
                        "auth_type": "none",
                        "parameters": {
                            "latitude": "52.52",
                            "longitude": "13.41",
                        },
                    },
                },
                "transformation": {
                    "ai_agent_id": "weather-extractor",
                    "extract_fields": ["temperature", "humidity"],
                    "link_field": "location_id",
                },
                "storage": {
                    "raw_container": "weather-raw",
                    "index_collection": "weather_data",
                },
            }
        )

    @pytest.fixture
    def sample_source_config_with_iteration(self) -> SourceConfig:
        """Sample source config with iteration."""
        return SourceConfig.model_validate(
            {
                "source_id": "weather-api-regions",
                "display_name": "Weather API Regions",
                "description": "Weather data for all regions",
                "enabled": True,
                "ingestion": {
                    "mode": "scheduled_pull",
                    "schedule": "0 6 * * *",
                    "provider": "open-meteo",
                    "request": {
                        "base_url": "https://api.open-meteo.com/v1/forecast",
                        "auth_type": "none",
                        "parameters": {
                            "latitude": "{item.latitude}",
                            "longitude": "{item.longitude}",
                        },
                    },
                    "iteration": {
                        "foreach": "region",
                        "source_mcp": "plantation-mcp",
                        "source_tool": "list_active_regions",
                        "concurrency": 2,
                    },
                },
                "transformation": {
                    "ai_agent_id": "weather-extractor",
                    "extract_fields": ["temperature", "humidity"],
                    "link_field": "region_id",
                },
                "storage": {
                    "raw_container": "weather-raw",
                    "index_collection": "weather_data",
                },
            }
        )

    @pytest.fixture
    def sample_regions(self) -> list[dict[str, Any]]:
        """Sample regions from MCP tool."""
        return [
            {"region_id": "nyeri", "latitude": -0.4167, "longitude": 36.95, "name": "Nyeri"},
            {"region_id": "kericho", "latitude": -0.3689, "longitude": 35.2863, "name": "Kericho"},
            {"region_id": "nandi", "latitude": 0.1833, "longitude": 35.1, "name": "Nandi"},
        ]

    @pytest.mark.asyncio
    async def test_handle_job_trigger_loads_config(
        self,
        pull_job_handler: PullJobHandler,
        mock_source_config_service: MagicMock,
        sample_source_config_no_iteration: SourceConfig,
    ) -> None:
        """Test handle_job_trigger loads source config."""
        mock_source_config_service.get_config = AsyncMock(return_value=sample_source_config_no_iteration)

        await pull_job_handler.handle_job_trigger(source_id="weather-api")

        mock_source_config_service.get_config.assert_called_once_with("weather-api")

    @pytest.mark.asyncio
    async def test_handle_job_trigger_returns_error_for_missing_config(
        self,
        pull_job_handler: PullJobHandler,
        mock_source_config_service: MagicMock,
    ) -> None:
        """Test handle_job_trigger returns error for missing config."""
        mock_source_config_service.get_config = AsyncMock(return_value=None)

        result = await pull_job_handler.handle_job_trigger(source_id="unknown-source")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_handle_single_fetch_no_iteration(
        self,
        pull_job_handler: PullJobHandler,
        mock_source_config_service: MagicMock,
        mock_pull_data_fetcher: MagicMock,
        mock_processor: MagicMock,
        sample_source_config_no_iteration: SourceConfig,
    ) -> None:
        """Test single fetch when no iteration block."""
        mock_source_config_service.get_config = AsyncMock(return_value=sample_source_config_no_iteration)

        result = await pull_job_handler.handle_job_trigger(source_id="weather-api")

        # Should make one fetch
        mock_pull_data_fetcher.fetch.assert_called_once()
        # Should process one job
        mock_processor.process.assert_called_once()
        # Should report success
        assert result["success"] is True
        assert result["fetched"] == 1

    @pytest.mark.asyncio
    async def test_handle_multi_fetch_with_iteration(
        self,
        pull_job_handler: PullJobHandler,
        mock_source_config_service: MagicMock,
        mock_pull_data_fetcher: MagicMock,
        mock_iteration_resolver: MagicMock,
        mock_processor: MagicMock,
        sample_source_config_with_iteration: SourceConfig,
        sample_regions: list[dict[str, Any]],
    ) -> None:
        """Test multi-fetch with iteration block."""
        mock_source_config_service.get_config = AsyncMock(return_value=sample_source_config_with_iteration)
        mock_iteration_resolver.resolve = AsyncMock(return_value=sample_regions)

        result = await pull_job_handler.handle_job_trigger(source_id="weather-api-regions")

        # Should call iteration resolver
        mock_iteration_resolver.resolve.assert_called_once()
        # Should make 3 fetches (one per region)
        assert mock_pull_data_fetcher.fetch.call_count == 3
        # Should process 3 jobs
        assert mock_processor.process.call_count == 3
        # Should report success
        assert result["success"] is True
        assert result["fetched"] == 3

    @pytest.mark.asyncio
    async def test_fetch_uses_correct_pull_config(
        self,
        pull_job_handler: PullJobHandler,
        mock_source_config_service: MagicMock,
        mock_pull_data_fetcher: MagicMock,
        sample_source_config_no_iteration: SourceConfig,
    ) -> None:
        """Test fetch passes correct pull config to fetcher."""
        mock_source_config_service.get_config = AsyncMock(return_value=sample_source_config_no_iteration)

        await pull_job_handler.handle_job_trigger(source_id="weather-api")

        call_kwargs = mock_pull_data_fetcher.fetch.call_args[1]
        pull_config = call_kwargs["pull_config"]
        assert pull_config["base_url"] == "https://api.open-meteo.com/v1/forecast"
        assert pull_config["auth_type"] == "none"

    @pytest.mark.asyncio
    async def test_fetch_passes_iteration_item(
        self,
        pull_job_handler: PullJobHandler,
        mock_source_config_service: MagicMock,
        mock_pull_data_fetcher: MagicMock,
        mock_iteration_resolver: MagicMock,
        sample_source_config_with_iteration: SourceConfig,
        sample_regions: list[dict[str, Any]],
    ) -> None:
        """Test fetch passes iteration item for URL substitution."""
        mock_source_config_service.get_config = AsyncMock(return_value=sample_source_config_with_iteration)
        mock_iteration_resolver.resolve = AsyncMock(return_value=sample_regions)

        await pull_job_handler.handle_job_trigger(source_id="weather-api-regions")

        # Check that each fetch call included iteration_item
        for i, call in enumerate(mock_pull_data_fetcher.fetch.call_args_list):
            call_kwargs = call[1]
            assert call_kwargs["iteration_item"] == sample_regions[i]

    @pytest.mark.asyncio
    async def test_processor_receives_inline_content(
        self,
        pull_job_handler: PullJobHandler,
        mock_source_config_service: MagicMock,
        mock_pull_data_fetcher: MagicMock,
        mock_processor: MagicMock,
        sample_source_config_no_iteration: SourceConfig,
    ) -> None:
        """Test processor receives job with inline content."""
        mock_source_config_service.get_config = AsyncMock(return_value=sample_source_config_no_iteration)
        mock_pull_data_fetcher.fetch = AsyncMock(return_value=b'{"temperature": 25}')

        await pull_job_handler.handle_job_trigger(source_id="weather-api")

        # Check processor received job with content
        call_args = mock_processor.process.call_args
        job = call_args[0][0]  # First positional arg is job
        assert hasattr(job, "content")
        assert job.content == b'{"temperature": 25}'

    @pytest.mark.asyncio
    async def test_processor_receives_linkage_from_iteration(
        self,
        pull_job_handler: PullJobHandler,
        mock_source_config_service: MagicMock,
        mock_pull_data_fetcher: MagicMock,
        mock_iteration_resolver: MagicMock,
        mock_processor: MagicMock,
        sample_source_config_with_iteration: SourceConfig,
    ) -> None:
        """Test processor receives linkage extracted from iteration item."""
        mock_source_config_service.get_config = AsyncMock(return_value=sample_source_config_with_iteration)
        regions = [{"region_id": "nyeri", "latitude": -0.4167, "name": "Nyeri"}]
        mock_iteration_resolver.resolve = AsyncMock(return_value=regions)
        mock_iteration_resolver.extract_linkage = MagicMock(return_value={"region_id": "nyeri", "name": "Nyeri"})

        await pull_job_handler.handle_job_trigger(source_id="weather-api-regions")

        # Check processor received job with linkage
        call_args = mock_processor.process.call_args
        job = call_args[0][0]
        assert hasattr(job, "linkage")
        assert job.linkage == {"region_id": "nyeri", "name": "Nyeri"}

    @pytest.mark.asyncio
    async def test_handles_partial_fetch_failures(
        self,
        pull_job_handler: PullJobHandler,
        mock_source_config_service: MagicMock,
        mock_pull_data_fetcher: MagicMock,
        mock_iteration_resolver: MagicMock,
        mock_processor: MagicMock,
        sample_source_config_with_iteration: SourceConfig,
        sample_regions: list[dict[str, Any]],
    ) -> None:
        """Test handler continues on partial fetch failures."""
        mock_source_config_service.get_config = AsyncMock(return_value=sample_source_config_with_iteration)
        mock_iteration_resolver.resolve = AsyncMock(return_value=sample_regions)

        # Second fetch fails
        call_count = 0

        async def mock_fetch(*args: Any, **kwargs: Any) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Network error")
            return b'{"temperature": 22}'

        mock_pull_data_fetcher.fetch = mock_fetch

        result = await pull_job_handler.handle_job_trigger(source_id="weather-api-regions")

        # Should still succeed overall
        assert result["success"] is True
        # Should report 2 successful, 1 failed
        assert result["fetched"] == 2
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_respects_concurrency_limit(
        self,
        mock_source_config_service: MagicMock,
        mock_pull_data_fetcher: MagicMock,
        mock_iteration_resolver: MagicMock,
        mock_processor: MagicMock,
        mock_ingestion_queue: MagicMock,
        sample_source_config_with_iteration: SourceConfig,
        sample_regions: list[dict[str, Any]],
    ) -> None:
        """Test handler respects concurrency limit from config."""
        # Create handler with real semaphore tracking
        handler = PullJobHandler(
            source_config_service=mock_source_config_service,
            pull_data_fetcher=mock_pull_data_fetcher,
            iteration_resolver=mock_iteration_resolver,
            processor=mock_processor,
            ingestion_queue=mock_ingestion_queue,
        )

        mock_source_config_service.get_config = AsyncMock(return_value=sample_source_config_with_iteration)
        mock_iteration_resolver.resolve = AsyncMock(return_value=sample_regions)

        # Track concurrent executions
        max_concurrent = 0
        current_concurrent = 0

        original_fetch = mock_pull_data_fetcher.fetch

        async def tracked_fetch(*args: Any, **kwargs: Any) -> bytes:
            nonlocal max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            import asyncio

            await asyncio.sleep(0.01)  # Simulate work
            result = await original_fetch(*args, **kwargs)
            current_concurrent -= 1
            return result

        mock_pull_data_fetcher.fetch = tracked_fetch

        await handler.handle_job_trigger(source_id="weather-api-regions")

        # Concurrency should be limited to 2 (from config)
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_returns_job_summary(
        self,
        pull_job_handler: PullJobHandler,
        mock_source_config_service: MagicMock,
        mock_iteration_resolver: MagicMock,
        sample_source_config_with_iteration: SourceConfig,
        sample_regions: list[dict[str, Any]],
    ) -> None:
        """Test handler returns complete job summary."""
        mock_source_config_service.get_config = AsyncMock(return_value=sample_source_config_with_iteration)
        mock_iteration_resolver.resolve = AsyncMock(return_value=sample_regions)

        result = await pull_job_handler.handle_job_trigger(source_id="weather-api-regions")

        assert "source_id" in result
        assert result["source_id"] == "weather-api-regions"
        assert "fetched" in result
        assert "failed" in result
        assert "duplicates" in result
        assert "success" in result
