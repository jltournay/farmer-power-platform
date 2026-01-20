"""Unit tests for Weather model factory.

Story 0.8.3: Polyfactory Generator Framework
Tests AC #1: Factory exists for RegionalWeather
Tests AC #2: FK fields reference FK registry
"""

import datetime as dt
import json
import sys
from pathlib import Path

import pytest

# Add tests/demo and scripts/demo to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "tests" / "demo"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "scripts" / "demo"))

from fk_registry import FKRegistry
from fp_common.models.regional_weather import RegionalWeather
from generators import RegionalWeatherFactory, reset_fk_registry, set_fk_registry


@pytest.fixture(autouse=True)
def reset_factories():
    """Reset FK registry before each test."""
    reset_fk_registry()
    yield


@pytest.fixture
def fk_registry():
    """Create and configure FK registry with seed data."""
    registry = FKRegistry()
    set_fk_registry(registry)

    # Register regions for FK lookups
    registry.register("regions", ["nyeri-highland", "kericho-midland"])

    return registry


class TestRegionalWeatherFactory:
    """Tests for RegionalWeatherFactory."""

    def test_build_creates_valid_weather(self, fk_registry) -> None:
        """Build should create a valid RegionalWeather instance."""
        weather = RegionalWeatherFactory.build()
        assert isinstance(weather, RegionalWeather)

    def test_weather_requires_region_fk(self, fk_registry) -> None:
        """Build should use region_id from FK registry."""
        weather = RegionalWeatherFactory.build()
        assert weather.region_id in fk_registry.get_valid_ids("regions")

    def test_build_fails_without_regions(self) -> None:
        """Build should fail if no regions in registry."""
        with pytest.raises(ValueError, match="No regions registered"):
            RegionalWeatherFactory.build()

    def test_weather_passes_pydantic_validation(self, fk_registry) -> None:
        """Generated weather should pass Pydantic validation."""
        # Use specific region from fixture
        weather = RegionalWeatherFactory.build(region_id="nyeri-highland")
        validated = RegionalWeather.model_validate(weather.model_dump())
        assert validated.region_id == weather.region_id

    def test_weather_is_json_serializable(self, fk_registry) -> None:
        """Generated weather should be JSON-serializable."""
        weather = RegionalWeatherFactory.build(region_id="nyeri-highland")
        json_str = json.dumps(weather.model_dump(mode="json"))
        parsed = json.loads(json_str)
        assert "region_id" in parsed
        assert "temp_min" in parsed
        assert "temp_max" in parsed

    def test_weather_temperature_range(self, fk_registry) -> None:
        """Weather temperatures should be realistic for Kenya highlands."""
        for _ in range(20):
            weather = RegionalWeatherFactory.build(region_id="nyeri-highland")
            # Min temp should be reasonable
            assert 5 <= weather.temp_min <= 25
            # Max temp should be reasonable
            assert 15 <= weather.temp_max <= 35

    def test_weather_precipitation_non_negative(self, fk_registry) -> None:
        """Precipitation should be non-negative."""
        for _ in range(20):
            weather = RegionalWeatherFactory.build(region_id="nyeri-highland")
            assert weather.precipitation_mm >= 0

    def test_weather_humidity_in_range(self, fk_registry) -> None:
        """Humidity should be between 0 and 100."""
        for _ in range(20):
            weather = RegionalWeatherFactory.build(region_id="nyeri-highland")
            assert 0 <= weather.humidity_avg <= 100

    def test_weather_date_recent(self, fk_registry) -> None:
        """Weather date should be within last 30 days."""
        weather = RegionalWeatherFactory.build(region_id="nyeri-highland")
        today = dt.date.today()
        days_diff = (today - weather.date).days
        assert 0 <= days_diff <= 30

    def test_weather_source_default(self, fk_registry) -> None:
        """Weather source should default to open-meteo."""
        weather = RegionalWeatherFactory.build(region_id="nyeri-highland")
        assert weather.source == "open-meteo"


class TestRegionalWeatherFactoryBatch:
    """Tests for batch weather generation."""

    def test_build_for_region_and_dates(self, fk_registry) -> None:
        """Build for region and dates should create consecutive observations."""
        start_date = dt.date.today() - dt.timedelta(days=7)
        observations = RegionalWeatherFactory.build_for_region_and_dates(
            region_id="nyeri-highland",
            start_date=start_date,
            num_days=7,
        )

        assert len(observations) == 7

        # Verify dates are consecutive
        for i, obs in enumerate(observations):
            expected_date = start_date + dt.timedelta(days=i)
            assert obs.date == expected_date
            assert obs.region_id == "nyeri-highland"

    def test_build_for_region_temperature_consistency(self, fk_registry) -> None:
        """Built observations should have temp_min < temp_max."""
        observations = RegionalWeatherFactory.build_for_region_and_dates(
            region_id="nyeri-highland",
            start_date=dt.date.today(),
            num_days=10,
        )

        for obs in observations:
            assert obs.temp_min < obs.temp_max, f"temp_min ({obs.temp_min}) should be < temp_max ({obs.temp_max})"
