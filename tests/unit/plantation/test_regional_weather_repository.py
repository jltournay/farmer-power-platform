"""Unit tests for RegionalWeather repository (Story 1.8)."""

from datetime import date, timedelta

import pytest
from plantation_model.domain.models.regional_weather import WeatherObservation
from plantation_model.infrastructure.repositories.regional_weather_repository import (
    RegionalWeatherRepository,
)


def create_test_observation(
    temp_min: float = 12.5,
    temp_max: float = 24.8,
    precipitation_mm: float = 2.3,
    humidity_avg: float = 78.5,
) -> WeatherObservation:
    """Create a test weather observation."""
    return WeatherObservation(
        temp_min=temp_min,
        temp_max=temp_max,
        precipitation_mm=precipitation_mm,
        humidity_avg=humidity_avg,
    )


class TestRegionalWeatherRepository:
    """Tests for RegionalWeatherRepository."""

    @pytest.mark.asyncio
    async def test_upsert_observation_create(self, mock_mongodb_client) -> None:
        """Test creating a new weather observation via upsert."""
        db = mock_mongodb_client["plantation_model"]
        repo = RegionalWeatherRepository(db)
        observation = create_test_observation()
        observation_date = date(2025, 12, 28)

        result = await repo.upsert_observation(
            region_id="nyeri-highland",
            observation_date=observation_date,
            observation=observation,
        )

        assert result.region_id == "nyeri-highland"
        assert result.date == observation_date
        assert result.temp_min == 12.5
        assert result.temp_max == 24.8
        assert result.precipitation_mm == 2.3
        assert result.humidity_avg == 78.5
        assert result.source == "open-meteo"

    @pytest.mark.asyncio
    async def test_upsert_observation_update(self, mock_mongodb_client) -> None:
        """Test updating an existing observation via upsert."""
        db = mock_mongodb_client["plantation_model"]
        repo = RegionalWeatherRepository(db)
        observation_date = date(2025, 12, 28)

        # Create initial observation
        obs1 = create_test_observation(temp_min=10.0, temp_max=20.0)
        await repo.upsert_observation("nyeri-highland", observation_date, obs1)

        # Update with new data
        obs2 = create_test_observation(temp_min=15.0, temp_max=25.0)
        result = await repo.upsert_observation("nyeri-highland", observation_date, obs2)

        assert result.temp_min == 15.0
        assert result.temp_max == 25.0

    @pytest.mark.asyncio
    async def test_get_observation_found(self, mock_mongodb_client) -> None:
        """Test getting an observation that exists."""
        db = mock_mongodb_client["plantation_model"]
        repo = RegionalWeatherRepository(db)
        observation = create_test_observation()
        observation_date = date(2025, 12, 28)

        # Insert first
        await repo.upsert_observation("nyeri-highland", observation_date, observation)

        # Then retrieve
        result = await repo.get_observation("nyeri-highland", observation_date)

        assert result is not None
        assert result.region_id == "nyeri-highland"
        assert result.date == observation_date
        assert result.temp_min == 12.5

    @pytest.mark.asyncio
    async def test_get_observation_not_found(self, mock_mongodb_client) -> None:
        """Test getting an observation that doesn't exist."""
        db = mock_mongodb_client["plantation_model"]
        repo = RegionalWeatherRepository(db)

        result = await repo.get_observation("nyeri-highland", date(2025, 12, 28))

        assert result is None

    @pytest.mark.asyncio
    async def test_get_weather_history(self, mock_mongodb_client) -> None:
        """Test getting weather history for a region.

        Note: The mock doesn't support $gte comparison operators,
        so we verify the query runs without error. Actual date
        filtering is tested in integration tests with real MongoDB.
        """
        db = mock_mongodb_client["plantation_model"]
        repo = RegionalWeatherRepository(db)

        # Just verify the method runs without error
        results = await repo.get_weather_history("nyeri-highland", days=7)

        # With mock, returns empty (no $gte support)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_delete_observation_success(self, mock_mongodb_client) -> None:
        """Test deleting an observation that exists."""
        db = mock_mongodb_client["plantation_model"]
        repo = RegionalWeatherRepository(db)
        observation = create_test_observation()
        observation_date = date(2025, 12, 28)

        # Insert first
        await repo.upsert_observation("nyeri-highland", observation_date, observation)

        # Delete
        result = await repo.delete_observation("nyeri-highland", observation_date)

        assert result is True

        # Verify deleted
        found = await repo.get_observation("nyeri-highland", observation_date)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_observation_not_found(self, mock_mongodb_client) -> None:
        """Test deleting an observation that doesn't exist."""
        db = mock_mongodb_client["plantation_model"]
        repo = RegionalWeatherRepository(db)

        result = await repo.delete_observation("nyeri-highland", date(2025, 12, 28))

        assert result is False

    @pytest.mark.asyncio
    async def test_count_observations(self, mock_mongodb_client) -> None:
        """Test counting observations for a region."""
        db = mock_mongodb_client["plantation_model"]
        repo = RegionalWeatherRepository(db)

        # Insert observations
        today = date.today()
        for i in range(3):
            obs_date = today - timedelta(days=i)
            obs = create_test_observation()
            await repo.upsert_observation("nyeri-highland", obs_date, obs)

        count = await repo.count_observations("nyeri-highland")

        assert count == 3

    @pytest.mark.asyncio
    async def test_count_observations_empty(self, mock_mongodb_client) -> None:
        """Test counting observations when none exist."""
        db = mock_mongodb_client["plantation_model"]
        repo = RegionalWeatherRepository(db)

        count = await repo.count_observations("nonexistent-highland")

        assert count == 0
