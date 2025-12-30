"""Unit tests for JobRegistrationService (Story 2.7).

Tests cover job lifecycle management:
- sync_all_jobs: Register jobs for all scheduled_pull sources on startup
- register_job_for_source: Register single job from source config
- unregister_job_for_source: Remove job for a source
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from collection_model.infrastructure.dapr_jobs_client import DaprJobsClient
from collection_model.services.job_registration_service import JobRegistrationService
from collection_model.services.source_config_service import SourceConfigService


class TestJobRegistrationService:
    """Tests for JobRegistrationService."""

    @pytest.fixture
    def mock_dapr_jobs_client(self) -> MagicMock:
        """Create mock DaprJobsClient."""
        client = MagicMock(spec=DaprJobsClient)
        client.register_job = AsyncMock(return_value=True)
        client.delete_job = AsyncMock(return_value=True)
        client.list_jobs = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def mock_source_config_service(self) -> MagicMock:
        """Create mock SourceConfigService."""
        service = MagicMock(spec=SourceConfigService)
        service.get_all_configs = AsyncMock(return_value=[])
        service.get_config = AsyncMock(return_value=None)
        return service

    @pytest.fixture
    def sample_pull_source_config(self) -> dict[str, Any]:
        """Create sample scheduled_pull source config."""
        return {
            "source_id": "weather-api",
            "ingestion": {
                "mode": "scheduled_pull",
                "schedule": "0 6 * * *",
                "request": {
                    "base_url": "https://api.open-meteo.com/v1/forecast",
                    "auth_type": "none",
                },
            },
        }

    @pytest.fixture
    def sample_blob_trigger_source_config(self) -> dict[str, Any]:
        """Create sample blob_trigger source config (should be skipped)."""
        return {
            "source_id": "qc-analyzer",
            "ingestion": {
                "mode": "blob_trigger",
                "container": "qc-landing",
            },
        }

    @pytest.fixture
    def job_registration_service(
        self,
        mock_dapr_jobs_client: MagicMock,
        mock_source_config_service: MagicMock,
    ) -> JobRegistrationService:
        """Create JobRegistrationService with mocks."""
        return JobRegistrationService(
            dapr_jobs_client=mock_dapr_jobs_client,
            source_config_service=mock_source_config_service,
        )

    @pytest.mark.asyncio
    async def test_sync_all_jobs_registers_scheduled_pull_sources(
        self,
        job_registration_service: JobRegistrationService,
        mock_dapr_jobs_client: MagicMock,
        mock_source_config_service: MagicMock,
        sample_pull_source_config: dict[str, Any],
    ) -> None:
        """Test sync_all_jobs registers jobs for scheduled_pull sources."""
        mock_source_config_service.get_all_configs = AsyncMock(return_value=[sample_pull_source_config])

        result = await job_registration_service.sync_all_jobs()

        assert result["registered"] == 1
        assert result["skipped"] == 0
        assert result["failed"] == 0
        mock_dapr_jobs_client.register_job.assert_called_once_with(
            source_id="weather-api",
            schedule="0 6 * * *",
        )

    @pytest.mark.asyncio
    async def test_sync_all_jobs_skips_blob_trigger_sources(
        self,
        job_registration_service: JobRegistrationService,
        mock_dapr_jobs_client: MagicMock,
        mock_source_config_service: MagicMock,
        sample_blob_trigger_source_config: dict[str, Any],
    ) -> None:
        """Test sync_all_jobs skips non-scheduled_pull sources."""
        mock_source_config_service.get_all_configs = AsyncMock(return_value=[sample_blob_trigger_source_config])

        result = await job_registration_service.sync_all_jobs()

        assert result["registered"] == 0
        assert result["skipped"] == 1
        assert result["failed"] == 0
        mock_dapr_jobs_client.register_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_all_jobs_handles_multiple_sources(
        self,
        job_registration_service: JobRegistrationService,
        mock_dapr_jobs_client: MagicMock,
        mock_source_config_service: MagicMock,
        sample_pull_source_config: dict[str, Any],
        sample_blob_trigger_source_config: dict[str, Any],
    ) -> None:
        """Test sync_all_jobs handles mix of source types."""
        market_prices_config = {
            "source_id": "market-prices",
            "ingestion": {
                "mode": "scheduled_pull",
                "schedule": "0 */4 * * *",
                "request": {
                    "base_url": "https://api.prices.example.com/v1/prices",
                    "auth_type": "api_key",
                },
            },
        }
        mock_source_config_service.get_all_configs = AsyncMock(
            return_value=[
                sample_pull_source_config,
                sample_blob_trigger_source_config,
                market_prices_config,
            ]
        )

        result = await job_registration_service.sync_all_jobs()

        assert result["registered"] == 2
        assert result["skipped"] == 1
        assert result["failed"] == 0
        assert mock_dapr_jobs_client.register_job.call_count == 2

    @pytest.mark.asyncio
    async def test_sync_all_jobs_tracks_failures(
        self,
        job_registration_service: JobRegistrationService,
        mock_dapr_jobs_client: MagicMock,
        mock_source_config_service: MagicMock,
        sample_pull_source_config: dict[str, Any],
    ) -> None:
        """Test sync_all_jobs tracks registration failures."""
        mock_source_config_service.get_all_configs = AsyncMock(return_value=[sample_pull_source_config])
        mock_dapr_jobs_client.register_job = AsyncMock(return_value=False)

        result = await job_registration_service.sync_all_jobs()

        assert result["registered"] == 0
        assert result["skipped"] == 0
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_register_job_for_source_success(
        self,
        job_registration_service: JobRegistrationService,
        mock_dapr_jobs_client: MagicMock,
        sample_pull_source_config: dict[str, Any],
    ) -> None:
        """Test registering a single job from source config."""
        result = await job_registration_service.register_job_for_source(sample_pull_source_config)

        assert result is True
        mock_dapr_jobs_client.register_job.assert_called_once_with(
            source_id="weather-api",
            schedule="0 6 * * *",
        )

    @pytest.mark.asyncio
    async def test_register_job_for_source_skips_non_pull_mode(
        self,
        job_registration_service: JobRegistrationService,
        mock_dapr_jobs_client: MagicMock,
        sample_blob_trigger_source_config: dict[str, Any],
    ) -> None:
        """Test register_job_for_source skips non-pull sources."""
        result = await job_registration_service.register_job_for_source(sample_blob_trigger_source_config)

        assert result is False
        mock_dapr_jobs_client.register_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_unregister_job_for_source_success(
        self,
        job_registration_service: JobRegistrationService,
        mock_dapr_jobs_client: MagicMock,
    ) -> None:
        """Test unregistering a job for a source."""
        result = await job_registration_service.unregister_job_for_source(source_id="weather-api")

        assert result is True
        mock_dapr_jobs_client.delete_job.assert_called_once_with(source_id="weather-api")

    @pytest.mark.asyncio
    async def test_unregister_job_for_source_handles_failure(
        self,
        job_registration_service: JobRegistrationService,
        mock_dapr_jobs_client: MagicMock,
    ) -> None:
        """Test unregister_job_for_source handles failures gracefully."""
        mock_dapr_jobs_client.delete_job = AsyncMock(return_value=False)

        result = await job_registration_service.unregister_job_for_source(source_id="weather-api")

        assert result is False

    @pytest.mark.asyncio
    async def test_sync_all_jobs_with_no_sources(
        self,
        job_registration_service: JobRegistrationService,
        mock_dapr_jobs_client: MagicMock,
        mock_source_config_service: MagicMock,
    ) -> None:
        """Test sync_all_jobs when no sources are configured."""
        mock_source_config_service.get_all_configs = AsyncMock(return_value=[])

        result = await job_registration_service.sync_all_jobs()

        assert result["registered"] == 0
        assert result["skipped"] == 0
        assert result["failed"] == 0
        mock_dapr_jobs_client.register_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_job_extracts_schedule_correctly(
        self,
        job_registration_service: JobRegistrationService,
        mock_dapr_jobs_client: MagicMock,
    ) -> None:
        """Test that schedule is extracted from nested config correctly."""
        config = {
            "source_id": "test-source",
            "ingestion": {
                "mode": "scheduled_pull",
                "schedule": "@every 30m",  # DAPR-style schedule
                "request": {
                    "base_url": "https://example.com",
                },
            },
        }

        await job_registration_service.register_job_for_source(config)

        mock_dapr_jobs_client.register_job.assert_called_once_with(
            source_id="test-source",
            schedule="@every 30m",
        )
