"""Unit tests for weather updated event handler (Story 1.8)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from plantation_model.api.event_handlers.weather_updated_handler import (
    get_weather_subscriptions,
    router,
)
from plantation_model.infrastructure.repositories.regional_weather_repository import (
    RegionalWeatherRepository,
)


def create_test_app(regional_weather_repo: RegionalWeatherRepository | None = None) -> FastAPI:
    """Create a test FastAPI app with the handler router."""
    app = FastAPI()
    app.include_router(router)
    if regional_weather_repo is not None:
        app.state.regional_weather_repo = regional_weather_repo
    return app


def create_cloud_event(
    region_id: str = "nyeri-highland",
    observation_date: str = "2025-12-28",
    temp_min: float = 12.5,
    temp_max: float = 24.8,
    precipitation_mm: float = 2.3,
    humidity_avg: float = 78.5,
    source: str = "open-meteo",
) -> dict:
    """Create a test CloudEvent with weather data."""
    return {
        "id": "evt-12345",
        "source": "collection-model",
        "type": "collection.weather.updated",
        "specversion": "1.0",
        "datacontenttype": "application/json",
        "data": {
            "region_id": region_id,
            "date": observation_date,
            "observations": {
                "temp_min": temp_min,
                "temp_max": temp_max,
                "precipitation_mm": precipitation_mm,
                "humidity_avg": humidity_avg,
            },
            "source": source,
        },
    }


class TestWeatherSubscriptions:
    """Tests for subscription configuration."""

    def test_get_weather_subscriptions_returns_subscription(self) -> None:
        """Test that subscriptions are returned correctly."""
        subscriptions = get_weather_subscriptions()

        assert len(subscriptions) == 1
        sub = subscriptions[0]
        assert sub["pubsubname"] == "pubsub"
        assert sub["topic"] == "collection.weather.updated"
        assert sub["route"] == "/api/v1/events/weather-updated"


class TestWeatherUpdatedHandler:
    """Tests for weather updated event handler."""

    def test_handle_valid_event_success(self) -> None:
        """Test handling a valid weather event."""
        mock_repo = MagicMock(spec=RegionalWeatherRepository)
        mock_repo.upsert_observation = AsyncMock()

        app = create_test_app(mock_repo)
        client = TestClient(app)

        event = create_cloud_event()
        response = client.post("/api/v1/events/weather-updated", json=event)

        assert response.status_code == 200
        assert response.json()["status"] == "SUCCESS"
        mock_repo.upsert_observation.assert_called_once()

    def test_handle_event_repository_not_initialized(self) -> None:
        """Test handling event when repository is not initialized."""
        app = create_test_app(None)  # No repository
        client = TestClient(app)

        event = create_cloud_event()
        response = client.post("/api/v1/events/weather-updated", json=event)

        # Should still return success to avoid infinite retries
        assert response.status_code == 200
        assert "Repository not initialized" in response.json().get("message", "")

    def test_handle_invalid_cloud_event(self) -> None:
        """Test handling invalid CloudEvent format."""
        mock_repo = MagicMock(spec=RegionalWeatherRepository)
        app = create_test_app(mock_repo)
        client = TestClient(app)

        # Missing required CloudEvent fields
        invalid_event = {"not_a_cloud_event": True}
        response = client.post("/api/v1/events/weather-updated", json=invalid_event)

        assert response.status_code == 400
        assert response.json()["status"] == "DROP"

    def test_handle_invalid_event_payload(self) -> None:
        """Test handling CloudEvent with invalid payload."""
        mock_repo = MagicMock(spec=RegionalWeatherRepository)
        app = create_test_app(mock_repo)
        client = TestClient(app)

        event = {
            "id": "evt-12345",
            "source": "collection-model",
            "type": "collection.weather.updated",
            "data": {
                # Missing required fields
                "region_id": "nyeri-highland",
            },
        }
        response = client.post("/api/v1/events/weather-updated", json=event)

        assert response.status_code == 400
        assert response.json()["status"] == "DROP"

    def test_handle_invalid_date_format(self) -> None:
        """Test handling event with invalid date format."""
        mock_repo = MagicMock(spec=RegionalWeatherRepository)
        app = create_test_app(mock_repo)
        client = TestClient(app)

        event = create_cloud_event(observation_date="not-a-date")
        response = client.post("/api/v1/events/weather-updated", json=event)

        assert response.status_code == 400
        assert response.json()["status"] == "DROP"

    def test_handle_repository_error_returns_retry(self) -> None:
        """Test that repository errors trigger retry response."""
        mock_repo = MagicMock(spec=RegionalWeatherRepository)
        mock_repo.upsert_observation = AsyncMock(side_effect=Exception("DB error"))

        app = create_test_app(mock_repo)
        client = TestClient(app)

        event = create_cloud_event()
        response = client.post("/api/v1/events/weather-updated", json=event)

        assert response.status_code == 500
        assert response.json()["status"] == "RETRY"

    def test_handle_event_with_nested_payload(self) -> None:
        """Test handling event with payload nested under 'payload' key."""
        mock_repo = MagicMock(spec=RegionalWeatherRepository)
        mock_repo.upsert_observation = AsyncMock()

        app = create_test_app(mock_repo)
        client = TestClient(app)

        event = {
            "id": "evt-12345",
            "source": "collection-model",
            "type": "collection.weather.updated",
            "data": {
                "payload": {
                    "region_id": "nyeri-highland",
                    "date": "2025-12-28",
                    "observations": {
                        "temp_min": 10.0,
                        "temp_max": 20.0,
                        "precipitation_mm": 0.0,
                        "humidity_avg": 50.0,
                    },
                    "source": "open-meteo",
                }
            },
        }
        response = client.post("/api/v1/events/weather-updated", json=event)

        assert response.status_code == 200
        assert response.json()["status"] == "SUCCESS"
        mock_repo.upsert_observation.assert_called_once()

    def test_handle_event_passes_correct_values_to_repo(self) -> None:
        """Test that correct values are passed to repository."""
        mock_repo = MagicMock(spec=RegionalWeatherRepository)
        mock_repo.upsert_observation = AsyncMock()

        app = create_test_app(mock_repo)
        client = TestClient(app)

        event = create_cloud_event(
            region_id="kericho-midland",
            observation_date="2025-06-15",
            temp_min=15.0,
            temp_max=25.0,
            precipitation_mm=10.5,
            humidity_avg=85.0,
            source="test-source",
        )
        response = client.post("/api/v1/events/weather-updated", json=event)

        assert response.status_code == 200

        # Verify repository was called with correct arguments
        call_args = mock_repo.upsert_observation.call_args
        assert call_args.kwargs["region_id"] == "kericho-midland"
        assert call_args.kwargs["observation_date"] == date(2025, 6, 15)
        assert call_args.kwargs["source"] == "test-source"
        assert call_args.kwargs["observation"].temp_min == 15.0
        assert call_args.kwargs["observation"].temp_max == 25.0
        assert call_args.kwargs["observation"].precipitation_mm == 10.5
        assert call_args.kwargs["observation"].humidity_avg == 85.0
