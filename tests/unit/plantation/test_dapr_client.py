"""Unit tests for DaprPubSubClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from plantation_model.domain.events.farmer_events import FarmerRegisteredEvent
from plantation_model.infrastructure.dapr_client import DaprPubSubClient


@pytest.fixture
def dapr_client() -> DaprPubSubClient:
    """Create a DaprPubSubClient with test settings."""
    return DaprPubSubClient(dapr_host="localhost", dapr_http_port=3500)


class TestDaprPubSubClientPublish:
    """Tests for DaprPubSubClient.publish_event method."""

    @pytest.mark.asyncio
    async def test_publish_event_success(
        self,
        dapr_client: DaprPubSubClient,
    ) -> None:
        """Test successful event publishing."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("plantation_model.infrastructure.dapr_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await dapr_client.publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event,
            )

            assert result is True
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "http://localhost:3500/v1.0/publish/pubsub/farmer-events" in str(call_args)

    @pytest.mark.asyncio
    async def test_publish_event_with_dict_data(
        self,
        dapr_client: DaprPubSubClient,
    ) -> None:
        """Test publishing event with dict data instead of Pydantic model."""
        event_dict = {
            "event_type": "plantation.farmer.registered",
            "farmer_id": "WM-0001",
            "phone": "+254712345678",
        }

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("plantation_model.infrastructure.dapr_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await dapr_client.publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event_dict,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_publish_event_dapr_not_available(
        self,
        dapr_client: DaprPubSubClient,
    ) -> None:
        """Test event publishing when Dapr sidecar is not available."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        with patch("plantation_model.infrastructure.dapr_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await dapr_client.publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event,
            )

            # Should return False but not raise exception
            assert result is False

    @pytest.mark.asyncio
    async def test_publish_event_http_error(
        self,
        dapr_client: DaprPubSubClient,
    ) -> None:
        """Test event publishing with HTTP error response."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        with patch("plantation_model.infrastructure.dapr_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            # Create mock response that raises on raise_for_status
            mock_response = MagicMock()
            mock_response.status_code = 500

            def raise_for_status():
                raise httpx.HTTPStatusError(
                    "Internal Server Error",
                    request=MagicMock(),
                    response=mock_response,
                )

            mock_response.raise_for_status = raise_for_status
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await dapr_client.publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event,
            )

            # Should return False but not raise exception
            assert result is False

    @pytest.mark.asyncio
    async def test_publish_event_unexpected_error(
        self,
        dapr_client: DaprPubSubClient,
    ) -> None:
        """Test event publishing with unexpected error."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        with patch("plantation_model.infrastructure.dapr_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await dapr_client.publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event,
            )

            # Should return False but not raise exception
            assert result is False

    @pytest.mark.asyncio
    async def test_publish_event_with_metadata(
        self,
        dapr_client: DaprPubSubClient,
    ) -> None:
        """Test publishing event with custom metadata headers."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("plantation_model.infrastructure.dapr_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await dapr_client.publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event,
                metadata={"x-trace-id": "abc123"},
            )

            assert result is True
            # Verify metadata was included in headers
            call_kwargs = mock_client.post.call_args.kwargs
            assert "x-trace-id" in call_kwargs.get("headers", {})


class TestDaprPubSubClientConfiguration:
    """Tests for DaprPubSubClient configuration."""

    def test_client_uses_default_settings(self) -> None:
        """Test client uses settings when not explicitly provided."""
        with patch("plantation_model.infrastructure.dapr_client.settings") as mock_settings:
            mock_settings.dapr_host = "test-host"
            mock_settings.dapr_http_port = 9999

            client = DaprPubSubClient()

            assert client._dapr_host == "test-host"
            assert client._dapr_http_port == 9999

    def test_client_uses_explicit_settings(self) -> None:
        """Test client uses explicitly provided settings."""
        client = DaprPubSubClient(dapr_host="explicit-host", dapr_http_port=1234)

        assert client._dapr_host == "explicit-host"
        assert client._dapr_http_port == 1234
        assert client._base_url == "http://explicit-host:1234"
