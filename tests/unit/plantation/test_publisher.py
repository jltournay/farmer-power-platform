"""Unit tests for DAPR publisher (events/publisher.py).

Story 0.6.14: Tests for SDK-based publish_event() per ADR-010.
"""

from unittest.mock import MagicMock, patch

import pytest
from dapr.clients.exceptions import DaprInternalError
from grpc import RpcError
from plantation_model.domain.events.farmer_events import FarmerRegisteredEvent
from plantation_model.events.publisher import publish_event


class TestPublishEvent:
    """Tests for publish_event function using DAPR SDK."""

    @pytest.mark.asyncio
    async def test_publish_event_success(self) -> None:
        """Test successful event publishing via SDK."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        with patch("plantation_model.events.publisher.DaprClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=None)

            result = await publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event,
            )

            assert result is True
            mock_client.publish_event.assert_called_once()
            call_kwargs = mock_client.publish_event.call_args.kwargs
            assert call_kwargs["pubsub_name"] == "pubsub"
            assert call_kwargs["topic_name"] == "farmer-events"
            assert call_kwargs["data_content_type"] == "application/json"
            # Data should be JSON string
            assert '"farmer_id": "WM-0001"' in call_kwargs["data"]

    @pytest.mark.asyncio
    async def test_publish_event_with_dict_data(self) -> None:
        """Test publishing event with dict data instead of Pydantic model."""
        event_dict = {
            "event_type": "plantation.farmer.registered",
            "farmer_id": "WM-0001",
            "phone": "+254712345678",
        }

        with patch("plantation_model.events.publisher.DaprClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=None)

            result = await publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event_dict,
            )

            assert result is True
            call_kwargs = mock_client.publish_event.call_args.kwargs
            assert '"event_type": "plantation.farmer.registered"' in call_kwargs["data"]

    @pytest.mark.asyncio
    async def test_publish_event_dapr_internal_error(self) -> None:
        """Test event publishing when DAPR returns internal error."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        with patch("plantation_model.events.publisher.DaprClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.publish_event.side_effect = DaprInternalError("Sidecar unavailable")
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=None)

            result = await publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event,
            )

            # Should return False but not raise exception
            assert result is False

    @pytest.mark.asyncio
    async def test_publish_event_grpc_error(self) -> None:
        """Test event publishing when gRPC returns error."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        with patch("plantation_model.events.publisher.DaprClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.publish_event.side_effect = RpcError()
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=None)

            result = await publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event,
            )

            # Should return False but not raise exception
            assert result is False

    @pytest.mark.asyncio
    async def test_publish_event_unexpected_error(self) -> None:
        """Test event publishing with unexpected error."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        with patch("plantation_model.events.publisher.DaprClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.publish_event.side_effect = Exception("Unexpected error")
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=None)

            result = await publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event,
            )

            # Should return False but not raise exception
            assert result is False

    @pytest.mark.asyncio
    async def test_publish_event_json_serialization(self) -> None:
        """Test that data is properly JSON serialized per ADR-010."""
        event = FarmerRegisteredEvent(
            farmer_id="WM-0001",
            phone="+254712345678",
            collection_point_id="nyeri-highland-cp-001",
            factory_id="KEN-FAC-001",
            region_id="nyeri-highland",
            farm_scale="medium",
        )

        with patch("plantation_model.events.publisher.DaprClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_class.return_value.__exit__ = MagicMock(return_value=None)

            await publish_event(
                pubsub_name="pubsub",
                topic="farmer-events",
                data=event,
            )

            # Verify SDK parameters match ADR-010 spec
            call_kwargs = mock_client.publish_event.call_args.kwargs
            assert call_kwargs["data_content_type"] == "application/json"
            # Data must be JSON string, not dict
            assert isinstance(call_kwargs["data"], str)
