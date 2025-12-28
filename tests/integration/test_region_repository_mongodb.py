"""Integration tests for Region repositories with real MongoDB (Story 1.8).

These tests validate that Region and RegionalWeather CRUD operations work correctly
with a real MongoDB instance.

Prerequisites:
    docker-compose -f tests/docker-compose.test.yaml up -d

Usage:
    PYTHONPATH="${PYTHONPATH}:libs/fp-common:libs/fp-proto/src:libs/fp-testing:services/plantation-model/src" \
        pytest tests/integration/test_region_repository_mongodb.py -v
"""

from datetime import date, timedelta

import pytest
from plantation_model.domain.models.region import Region
from plantation_model.domain.models.regional_weather import WeatherObservation
from plantation_model.domain.models.value_objects import (
    GPS,
    Agronomic,
    AltitudeBand,
    AltitudeBandLabel,
    FlushCalendar,
    FlushPeriod,
    Geography,
    WeatherConfig,
)
from plantation_model.infrastructure.repositories.region_repository import RegionRepository
from plantation_model.infrastructure.repositories.regional_weather_repository import (
    RegionalWeatherRepository,
)


def create_test_region(
    region_id: str = "nyeri-highland",
    name: str = "Nyeri Highland",
    county: str = "Nyeri",
    altitude_label: AltitudeBandLabel = AltitudeBandLabel.HIGHLAND,
    is_active: bool = True,
) -> Region:
    """Create a test Region entity."""
    return Region(
        region_id=region_id,
        name=name,
        county=county,
        country="Kenya",
        geography=Geography(
            center_gps=GPS(lat=-0.4197, lng=36.9553),
            radius_km=25,
            altitude_band=AltitudeBand(
                min_meters=1800,
                max_meters=2200,
                label=altitude_label,
            ),
        ),
        flush_calendar=FlushCalendar(
            first_flush=FlushPeriod(start="03-15", end="05-15", characteristics="Spring"),
            monsoon_flush=FlushPeriod(start="06-15", end="09-30", characteristics="Monsoon"),
            autumn_flush=FlushPeriod(start="10-15", end="12-15", characteristics="Autumn"),
            dormant=FlushPeriod(start="12-16", end="03-14", characteristics="Dormant"),
        ),
        agronomic=Agronomic(soil_type="volcanic_red"),
        weather_config=WeatherConfig(
            api_location=GPS(lat=-0.4197, lng=36.9553),
            altitude_for_api=1950,
        ),
        is_active=is_active,
    )


@pytest.mark.mongodb
@pytest.mark.asyncio
class TestRegionRepository:
    """Integration tests for RegionRepository."""

    async def test_create_region(self, test_db) -> None:
        """Test region creation persists to MongoDB correctly."""
        repo = RegionRepository(test_db)

        region = create_test_region()
        created = await repo.create(region)

        assert created.region_id == "nyeri-highland"
        assert created.name == "Nyeri Highland"
        assert created.county == "Nyeri"

    async def test_get_by_id(self, test_db) -> None:
        """Test region retrieval by ID."""
        repo = RegionRepository(test_db)

        # Create and retrieve
        region = create_test_region()
        await repo.create(region)

        retrieved = await repo.get_by_id("nyeri-highland")

        assert retrieved is not None
        assert retrieved.region_id == "nyeri-highland"
        assert retrieved.name == "Nyeri Highland"
        assert retrieved.county == "Nyeri"
        assert retrieved.geography.altitude_band.label == AltitudeBandLabel.HIGHLAND
        assert retrieved.flush_calendar.first_flush.start == "03-15"

    async def test_get_by_id_returns_none_for_missing(self, test_db) -> None:
        """Test retrieval returns None for non-existent region."""
        repo = RegionRepository(test_db)

        result = await repo.get_by_id("nonexistent-region")

        assert result is None

    async def test_update_region(self, test_db) -> None:
        """Test updating region fields."""
        repo = RegionRepository(test_db)

        # Create region
        region = create_test_region()
        await repo.create(region)

        # Update
        updated = await repo.update("nyeri-highland", {"name": "Updated Name"})

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.county == "Nyeri"  # Unchanged

    async def test_delete_region(self, test_db) -> None:
        """Test deleting a region."""
        repo = RegionRepository(test_db)

        # Create region
        region = create_test_region()
        await repo.create(region)

        # Delete
        deleted = await repo.delete("nyeri-highland")
        assert deleted is True

        # Verify deleted
        after_delete = await repo.get_by_id("nyeri-highland")
        assert after_delete is None

    async def test_delete_nonexistent_region(self, test_db) -> None:
        """Test deleting a region that doesn't exist."""
        repo = RegionRepository(test_db)

        result = await repo.delete("nonexistent-region")
        assert result is False

    async def test_list_regions(self, test_db) -> None:
        """Test listing all regions."""
        repo = RegionRepository(test_db)

        # Create multiple regions
        region1 = create_test_region("nyeri-highland", "Nyeri Highland", "Nyeri")
        region2 = create_test_region("kericho-midland", "Kericho Midland", "Kericho", AltitudeBandLabel.MIDLAND)
        await repo.create(region1)
        await repo.create(region2)

        regions, next_token, total = await repo.list()

        assert total == 2
        assert len(regions) == 2

    async def test_list_regions_by_county(self, test_db) -> None:
        """Test listing regions filtered by county."""
        repo = RegionRepository(test_db)

        # Create regions in different counties
        region1 = create_test_region("nyeri-highland", "Nyeri Highland", "Nyeri")
        region2 = create_test_region("nyeri-midland", "Nyeri Midland", "Nyeri", AltitudeBandLabel.MIDLAND)
        region3 = create_test_region("kericho-midland", "Kericho Midland", "Kericho", AltitudeBandLabel.MIDLAND)
        await repo.create(region1)
        await repo.create(region2)
        await repo.create(region3)

        # Filter by county
        regions, _, total = await repo.list(county="Nyeri")

        assert total == 2
        assert all(r.county == "Nyeri" for r in regions)

    async def test_list_active_regions_only(self, test_db) -> None:
        """Test listing only active regions."""
        repo = RegionRepository(test_db)

        # Create active and inactive regions
        active = create_test_region("nyeri-highland", is_active=True)
        inactive = create_test_region(
            "kericho-midland", "Kericho", "Kericho", AltitudeBandLabel.MIDLAND, is_active=False
        )
        await repo.create(active)
        await repo.create(inactive)

        # List only active (default)
        regions, _, total = await repo.list_active()

        assert total == 1
        assert regions[0].region_id == "nyeri-highland"

    async def test_ensure_indexes(self, test_db) -> None:
        """Test index creation happens correctly."""
        repo = RegionRepository(test_db)

        # Create indexes
        await repo.ensure_indexes()

        # Verify indexes exist
        indexes = await test_db["regions"].index_information()

        assert "idx_region_id" in indexes
        assert "idx_region_county" in indexes
        assert "idx_region_active" in indexes


@pytest.mark.mongodb
@pytest.mark.asyncio
class TestRegionalWeatherRepository:
    """Integration tests for RegionalWeatherRepository."""

    async def test_upsert_observation(self, test_db) -> None:
        """Test weather observation upsert."""
        repo = RegionalWeatherRepository(test_db)

        observation = WeatherObservation(
            temp_min=12.5,
            temp_max=24.8,
            precipitation_mm=2.3,
            humidity_avg=78.5,
        )
        today = date.today()

        result = await repo.upsert_observation(
            region_id="nyeri-highland",
            observation_date=today,
            observation=observation,
            source="open-meteo",
        )

        assert result.region_id == "nyeri-highland"
        assert result.date == today
        assert result.temp_min == 12.5
        assert result.temp_max == 24.8
        assert result.source == "open-meteo"

    async def test_upsert_observation_updates_existing(self, test_db) -> None:
        """Test that upsert updates existing observation."""
        repo = RegionalWeatherRepository(test_db)
        today = date.today()

        # Insert initial observation
        obs1 = WeatherObservation(temp_min=10.0, temp_max=20.0, precipitation_mm=0.0, humidity_avg=50.0)
        await repo.upsert_observation("nyeri-highland", today, obs1)

        # Upsert updated observation
        obs2 = WeatherObservation(temp_min=12.0, temp_max=25.0, precipitation_mm=5.0, humidity_avg=80.0)
        result = await repo.upsert_observation("nyeri-highland", today, obs2)

        assert result.temp_min == 12.0
        assert result.temp_max == 25.0
        assert result.precipitation_mm == 5.0

        # Verify only one document exists
        count = await repo.count_observations("nyeri-highland")
        assert count == 1

    async def test_get_observation(self, test_db) -> None:
        """Test retrieving a specific observation."""
        repo = RegionalWeatherRepository(test_db)
        today = date.today()

        # Insert observation
        obs = WeatherObservation(temp_min=15.0, temp_max=28.0, precipitation_mm=1.5, humidity_avg=65.0)
        await repo.upsert_observation("nyeri-highland", today, obs)

        # Retrieve
        result = await repo.get_observation("nyeri-highland", today)

        assert result is not None
        assert result.temp_min == 15.0
        assert result.temp_max == 28.0

    async def test_get_observation_returns_none_for_missing(self, test_db) -> None:
        """Test retrieval returns None for missing observation."""
        repo = RegionalWeatherRepository(test_db)

        result = await repo.get_observation("nyeri-highland", date.today())

        assert result is None

    async def test_get_weather_history(self, test_db) -> None:
        """Test retrieving weather history for a region."""
        repo = RegionalWeatherRepository(test_db)
        today = date.today()

        # Insert observations for multiple days
        for i in range(5):
            obs = WeatherObservation(
                temp_min=10.0 + i,
                temp_max=20.0 + i,
                precipitation_mm=float(i),
                humidity_avg=50.0 + i * 5,
            )
            await repo.upsert_observation("nyeri-highland", today - timedelta(days=i), obs)

        # Get history
        history = await repo.get_weather_history("nyeri-highland", days=7)

        assert len(history) == 5
        # Should be ordered by date descending
        assert history[0].date == today

    async def test_delete_observation(self, test_db) -> None:
        """Test deleting a weather observation."""
        repo = RegionalWeatherRepository(test_db)
        today = date.today()

        # Insert observation
        obs = WeatherObservation(temp_min=15.0, temp_max=25.0, precipitation_mm=0.0, humidity_avg=60.0)
        await repo.upsert_observation("nyeri-highland", today, obs)

        # Delete
        deleted = await repo.delete_observation("nyeri-highland", today)
        assert deleted is True

        # Verify deleted
        result = await repo.get_observation("nyeri-highland", today)
        assert result is None

    async def test_delete_observation_returns_false_for_missing(self, test_db) -> None:
        """Test deleting non-existent observation returns False."""
        repo = RegionalWeatherRepository(test_db)

        result = await repo.delete_observation("nyeri-highland", date.today())

        assert result is False

    async def test_count_observations(self, test_db) -> None:
        """Test counting observations for a region."""
        repo = RegionalWeatherRepository(test_db)
        today = date.today()

        # Insert multiple observations
        for i in range(3):
            obs = WeatherObservation(temp_min=10.0, temp_max=20.0, precipitation_mm=0.0, humidity_avg=50.0)
            await repo.upsert_observation("nyeri-highland", today - timedelta(days=i), obs)

        count = await repo.count_observations("nyeri-highland")

        assert count == 3

    async def test_ensure_indexes(self, test_db) -> None:
        """Test index creation happens correctly."""
        repo = RegionalWeatherRepository(test_db)

        # Create indexes
        await repo.ensure_indexes()

        # Verify indexes exist
        indexes = await test_db["regional_weather"].index_information()

        assert "idx_region_date" in indexes
        assert "idx_ttl" in indexes
