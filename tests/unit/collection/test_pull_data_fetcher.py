"""Unit tests for PullDataFetcher (Story 2.7).

Tests cover HTTP data fetching for scheduled pull sources:
- URL building with parameter substitution
- Authentication header generation (API key, bearer token, none)
- HTTP fetch with retry logic
- Iteration item value substitution in URLs
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from collection_model.infrastructure.pull_data_fetcher import PullDataFetcher


class TestPullDataFetcher:
    """Tests for PullDataFetcher."""

    @pytest.fixture
    def mock_dapr_secret_client(self) -> MagicMock:
        """Create mock DAPR secret client."""
        client = MagicMock()
        client.get_secret = AsyncMock(return_value={"api_key": "test-secret-key"})
        return client

    @pytest.fixture
    def pull_data_fetcher(self, mock_dapr_secret_client: MagicMock) -> PullDataFetcher:
        """Create PullDataFetcher with mocked dependencies."""
        return PullDataFetcher(dapr_secret_client=mock_dapr_secret_client)

    @pytest.fixture
    def sample_pull_config_no_auth(self) -> dict[str, Any]:
        """Sample pull config with no authentication."""
        return {
            "base_url": "https://api.open-meteo.com/v1/forecast",
            "auth_type": "none",
            "parameters": {
                "latitude": "52.52",
                "longitude": "13.41",
                "current": "temperature_2m",
            },
        }

    @pytest.fixture
    def sample_pull_config_api_key(self) -> dict[str, Any]:
        """Sample pull config with API key authentication."""
        return {
            "base_url": "https://api.weather.example.com/v1/data",
            "auth_type": "api_key",
            "auth_config": {
                "secret_name": "weather-api-key",
                "secret_store": "azure-keyvault",
                "header_name": "X-API-Key",
            },
            "parameters": {
                "format": "json",
            },
        }

    @pytest.fixture
    def sample_pull_config_bearer(self) -> dict[str, Any]:
        """Sample pull config with bearer token authentication."""
        return {
            "base_url": "https://api.secure.example.com/v1/data",
            "auth_type": "bearer",
            "auth_config": {
                "secret_name": "secure-api-token",
                "secret_store": "kubernetes-secrets",
            },
        }

    @pytest.fixture
    def sample_pull_config_with_iteration(self) -> dict[str, Any]:
        """Sample pull config using iteration item values."""
        return {
            "base_url": "https://api.open-meteo.com/v1/forecast",
            "auth_type": "none",
            "parameters": {
                "latitude": "{item.latitude}",
                "longitude": "{item.longitude}",
                "current": "temperature_2m",
            },
        }

    # URL Building Tests

    def test_build_url_simple_parameters(
        self,
        pull_data_fetcher: PullDataFetcher,
        sample_pull_config_no_auth: dict[str, Any],
    ) -> None:
        """Test URL building with simple static parameters."""
        url = pull_data_fetcher._build_url(
            base_url=sample_pull_config_no_auth["base_url"],
            parameters=sample_pull_config_no_auth.get("parameters", {}),
            iteration_item=None,
        )

        assert "https://api.open-meteo.com/v1/forecast" in url
        assert "latitude=52.52" in url
        assert "longitude=13.41" in url
        assert "current=temperature_2m" in url

    def test_build_url_with_iteration_item_substitution(
        self,
        pull_data_fetcher: PullDataFetcher,
        sample_pull_config_with_iteration: dict[str, Any],
    ) -> None:
        """Test URL building with iteration item value substitution."""
        iteration_item = {
            "region_id": "nairobi",
            "latitude": "-1.2921",
            "longitude": "36.8219",
        }

        url = pull_data_fetcher._build_url(
            base_url=sample_pull_config_with_iteration["base_url"],
            parameters=sample_pull_config_with_iteration.get("parameters", {}),
            iteration_item=iteration_item,
        )

        assert "latitude=-1.2921" in url
        assert "longitude=36.8219" in url
        assert "current=temperature_2m" in url
        # Template should be replaced, not present
        assert "{item." not in url

    def test_build_url_no_parameters(
        self,
        pull_data_fetcher: PullDataFetcher,
    ) -> None:
        """Test URL building with no parameters."""
        url = pull_data_fetcher._build_url(
            base_url="https://api.example.com/data",
            parameters={},
            iteration_item=None,
        )

        assert url == "https://api.example.com/data"

    def test_build_url_nested_iteration_item(
        self,
        pull_data_fetcher: PullDataFetcher,
    ) -> None:
        """Test URL building with nested iteration item access."""
        config = {
            "base_url": "https://api.example.com/data",
            "parameters": {
                "lat": "{item.location.latitude}",
                "lon": "{item.location.longitude}",
            },
        }
        iteration_item = {
            "region_id": "mombasa",
            "location": {
                "latitude": "-4.0435",
                "longitude": "39.6682",
            },
        }

        url = pull_data_fetcher._build_url(
            base_url=config["base_url"],
            parameters=config["parameters"],
            iteration_item=iteration_item,
        )

        assert "lat=-4.0435" in url
        assert "lon=39.6682" in url

    # Authentication Tests

    @pytest.mark.asyncio
    async def test_get_auth_header_none(
        self,
        pull_data_fetcher: PullDataFetcher,
        sample_pull_config_no_auth: dict[str, Any],
    ) -> None:
        """Test auth header generation for no auth."""
        headers = await pull_data_fetcher._get_auth_header(sample_pull_config_no_auth)

        assert headers == {}

    @pytest.mark.asyncio
    async def test_get_auth_header_api_key(
        self,
        pull_data_fetcher: PullDataFetcher,
        mock_dapr_secret_client: MagicMock,
        sample_pull_config_api_key: dict[str, Any],
    ) -> None:
        """Test auth header generation for API key."""
        mock_dapr_secret_client.get_secret = AsyncMock(
            return_value={"api_key": "secret-api-key-123"}
        )

        headers = await pull_data_fetcher._get_auth_header(sample_pull_config_api_key)

        assert headers == {"X-API-Key": "secret-api-key-123"}
        mock_dapr_secret_client.get_secret.assert_called_once_with(
            store_name="azure-keyvault",
            key="weather-api-key",
        )

    @pytest.mark.asyncio
    async def test_get_auth_header_bearer(
        self,
        pull_data_fetcher: PullDataFetcher,
        mock_dapr_secret_client: MagicMock,
        sample_pull_config_bearer: dict[str, Any],
    ) -> None:
        """Test auth header generation for bearer token."""
        mock_dapr_secret_client.get_secret = AsyncMock(
            return_value={"token": "bearer-token-xyz"}
        )

        headers = await pull_data_fetcher._get_auth_header(sample_pull_config_bearer)

        assert headers == {"Authorization": "Bearer bearer-token-xyz"}
        mock_dapr_secret_client.get_secret.assert_called_once_with(
            store_name="kubernetes-secrets",
            key="secure-api-token",
        )

    # Fetch Tests

    @pytest.mark.asyncio
    async def test_fetch_success(
        self,
        pull_data_fetcher: PullDataFetcher,
        sample_pull_config_no_auth: dict[str, Any],
    ) -> None:
        """Test successful HTTP fetch."""
        mock_response = MagicMock()
        mock_response.content = b'{"temperature": 22.5}'
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_response

            result = await pull_data_fetcher.fetch(
                pull_config=sample_pull_config_no_auth,
                iteration_item=None,
            )

        assert result == b'{"temperature": 22.5}'

    @pytest.mark.asyncio
    async def test_fetch_with_iteration_item(
        self,
        pull_data_fetcher: PullDataFetcher,
        sample_pull_config_with_iteration: dict[str, Any],
    ) -> None:
        """Test fetch with iteration item parameter substitution."""
        mock_response = MagicMock()
        mock_response.content = b'{"temperature": 28.0, "region": "nairobi"}'
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        iteration_item = {
            "region_id": "nairobi",
            "latitude": "-1.2921",
            "longitude": "36.8219",
        }

        with patch.object(
            httpx.AsyncClient, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_response

            result = await pull_data_fetcher.fetch(
                pull_config=sample_pull_config_with_iteration,
                iteration_item=iteration_item,
            )

        assert result == b'{"temperature": 28.0, "region": "nairobi"}'
        # Verify URL was built with substituted values
        call_args = mock_get.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        assert "-1.2921" in url
        assert "36.8219" in url

    @pytest.mark.asyncio
    async def test_fetch_with_auth_headers(
        self,
        pull_data_fetcher: PullDataFetcher,
        mock_dapr_secret_client: MagicMock,
        sample_pull_config_api_key: dict[str, Any],
    ) -> None:
        """Test fetch includes authentication headers."""
        mock_dapr_secret_client.get_secret = AsyncMock(
            return_value={"api_key": "my-api-key"}
        )
        mock_response = MagicMock()
        mock_response.content = b'{"data": "secure"}'
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_response

            await pull_data_fetcher.fetch(
                pull_config=sample_pull_config_api_key,
                iteration_item=None,
            )

        # Verify headers were passed
        call_kwargs = mock_get.call_args[1]
        assert "headers" in call_kwargs
        assert call_kwargs["headers"].get("X-API-Key") == "my-api-key"

    @pytest.mark.asyncio
    async def test_fetch_http_error_raises(
        self,
        pull_data_fetcher: PullDataFetcher,
        sample_pull_config_no_auth: dict[str, Any],
    ) -> None:
        """Test fetch raises on HTTP error after retries exhausted."""
        with patch.object(
            httpx.AsyncClient, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )

            with pytest.raises(httpx.HTTPStatusError):
                await pull_data_fetcher.fetch(
                    pull_config=sample_pull_config_no_auth,
                    iteration_item=None,
                )

    @pytest.mark.asyncio
    async def test_fetch_timeout_handling(
        self,
        pull_data_fetcher: PullDataFetcher,
        sample_pull_config_no_auth: dict[str, Any],
    ) -> None:
        """Test fetch handles timeout errors."""
        with patch.object(
            httpx.AsyncClient, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Connection timed out")

            with pytest.raises(httpx.TimeoutException):
                await pull_data_fetcher.fetch(
                    pull_config=sample_pull_config_no_auth,
                    iteration_item=None,
                )


class TestPullDataFetcherRetry:
    """Tests for retry behavior of PullDataFetcher."""

    @pytest.fixture
    def mock_dapr_secret_client(self) -> MagicMock:
        """Create mock DAPR secret client."""
        client = MagicMock()
        client.get_secret = AsyncMock(return_value={})
        return client

    @pytest.fixture
    def pull_data_fetcher(self, mock_dapr_secret_client: MagicMock) -> PullDataFetcher:
        """Create PullDataFetcher with reduced retry for testing."""
        return PullDataFetcher(
            dapr_secret_client=mock_dapr_secret_client,
            max_retries=2,
            retry_wait_seconds=0.01,  # Fast retries for tests
        )

    @pytest.mark.asyncio
    async def test_fetch_retries_on_transient_error(
        self,
        pull_data_fetcher: PullDataFetcher,
    ) -> None:
        """Test fetch retries on transient errors then succeeds."""
        mock_response = MagicMock()
        mock_response.content = b'{"success": true}'
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        call_count = 0

        async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection refused")
            return mock_response

        with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
            result = await pull_data_fetcher.fetch(
                pull_config={
                    "base_url": "https://api.example.com/data",
                    "auth_type": "none",
                },
                iteration_item=None,
            )

        assert result == b'{"success": true}'
        assert call_count == 2  # First failed, second succeeded

    @pytest.mark.asyncio
    async def test_fetch_exhausts_retries(
        self,
        pull_data_fetcher: PullDataFetcher,
    ) -> None:
        """Test fetch exhausts all retries on persistent errors."""
        call_count = 0

        async def mock_get(*args: Any, **kwargs: Any) -> None:
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection refused")

        with patch.object(httpx.AsyncClient, "get", side_effect=mock_get), pytest.raises(httpx.ConnectError):
            await pull_data_fetcher.fetch(
                pull_config={
                    "base_url": "https://api.example.com/data",
                    "auth_type": "none",
                },
                iteration_item=None,
            )

        # Should have tried max_retries + 1 times (initial + retries)
        assert call_count == 3  # 1 initial + 2 retries
