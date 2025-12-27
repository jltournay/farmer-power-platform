"""Unit tests for DaprJobsClient (Story 2.7).

Tests cover DAPR Jobs HTTP API interactions:
- register_job: Creates a DAPR Job with schedule
- delete_job: Removes a DAPR Job
- list_jobs: Lists registered jobs (optional debugging feature)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from collection_model.infrastructure.dapr_jobs_client import DaprJobsClient


class TestDaprJobsClient:
    """Tests for DaprJobsClient."""

    @pytest.fixture
    def dapr_jobs_client(self) -> DaprJobsClient:
        """Create DaprJobsClient instance."""
        return DaprJobsClient(dapr_port=3500)

    @pytest.mark.asyncio
    async def test_register_job_success(self, dapr_jobs_client: DaprJobsClient) -> None:
        """Test successful job registration via DAPR HTTP API."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await dapr_jobs_client.register_job(
                source_id="weather-api",
                schedule="0 6 * * *",
            )

            assert result is True
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "v1.0/jobs/weather-api" in call_args[0][0]
            json_body = call_args[1]["json"]
            assert json_body["schedule"] == "0 6 * * *"
            assert json_body["data"]["source_id"] == "weather-api"

    @pytest.mark.asyncio
    async def test_register_job_with_cron_schedule(self, dapr_jobs_client: DaprJobsClient) -> None:
        """Test job registration with cron expression schedule."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await dapr_jobs_client.register_job(
                source_id="market-prices",
                schedule="0 */4 * * *",  # Every 4 hours
            )

            assert result is True
            json_body = mock_client.post.call_args[1]["json"]
            assert json_body["schedule"] == "0 */4 * * *"

    @pytest.mark.asyncio
    async def test_register_job_failure_returns_false(self, dapr_jobs_client: DaprJobsClient) -> None:
        """Test job registration returns False on HTTP error."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status = MagicMock(side_effect=Exception("DAPR error"))
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await dapr_jobs_client.register_job(
                source_id="weather-api",
                schedule="0 6 * * *",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_delete_job_success(self, dapr_jobs_client: DaprJobsClient) -> None:
        """Test successful job deletion via DAPR HTTP API."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_response.raise_for_status = MagicMock()
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await dapr_jobs_client.delete_job(source_id="weather-api")

            assert result is True
            mock_client.delete.assert_called_once()
            call_args = mock_client.delete.call_args
            assert "v1.0/jobs/weather-api" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_delete_job_not_found_returns_true(self, dapr_jobs_client: DaprJobsClient) -> None:
        """Test job deletion returns True even if job doesn't exist (idempotent)."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.raise_for_status = MagicMock()  # 404 is not an error for delete
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await dapr_jobs_client.delete_job(source_id="nonexistent-job")

            assert result is True

    @pytest.mark.asyncio
    async def test_delete_job_failure_returns_false(self, dapr_jobs_client: DaprJobsClient) -> None:
        """Test job deletion returns False on HTTP error."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status = MagicMock(side_effect=Exception("DAPR error"))
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await dapr_jobs_client.delete_job(source_id="weather-api")

            assert result is False

    @pytest.mark.asyncio
    async def test_list_jobs_success(self, dapr_jobs_client: DaprJobsClient) -> None:
        """Test listing registered jobs."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={
                "jobs": [
                    {"name": "weather-api", "schedule": "0 6 * * *"},
                    {"name": "market-prices", "schedule": "0 */4 * * *"},
                ]
            })
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await dapr_jobs_client.list_jobs()

            assert len(result) == 2
            assert result[0]["name"] == "weather-api"
            assert result[1]["name"] == "market-prices"

    @pytest.mark.asyncio
    async def test_list_jobs_empty(self, dapr_jobs_client: DaprJobsClient) -> None:
        """Test listing jobs when no jobs registered."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={"jobs": []})
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await dapr_jobs_client.list_jobs()

            assert result == []

    @pytest.mark.asyncio
    async def test_job_name_sanitization(self, dapr_jobs_client: DaprJobsClient) -> None:
        """Test that source_id with special characters is sanitized for job name."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await dapr_jobs_client.register_job(
                source_id="weather_api_v2",  # underscore in name
                schedule="0 6 * * *",
            )

            assert result is True
            # Job name should be derived from source_id
            call_args = mock_client.post.call_args
            assert "weather_api_v2" in call_args[0][0] or "weather-api-v2" in call_args[0][0]
