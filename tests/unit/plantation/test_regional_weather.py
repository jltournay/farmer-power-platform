"""Unit tests for RegionalWeather domain model (Story 1.8)."""

from datetime import date

import pytest
from plantation_model.domain.models.regional_weather import RegionalWeather, WeatherObservation
from pydantic import ValidationError


class TestWeatherObservation:
    """Tests for WeatherObservation value object."""

    def test_weather_observation_valid(self) -> None:
        """Test creating a valid weather observation."""
        obs = WeatherObservation(
            temp_min=12.5,
            temp_max=24.8,
            precipitation_mm=2.3,
            humidity_avg=78.5,
        )
        assert obs.temp_min == 12.5
        assert obs.temp_max == 24.8
        assert obs.precipitation_mm == 2.3
        assert obs.humidity_avg == 78.5

    def test_weather_observation_negative_precipitation_fails(self) -> None:
        """Test precipitation must be non-negative."""
        with pytest.raises(ValidationError):
            WeatherObservation(
                temp_min=12.5,
                temp_max=24.8,
                precipitation_mm=-1.0,  # Invalid
                humidity_avg=78.5,
            )

    def test_weather_observation_humidity_range(self) -> None:
        """Test humidity must be 0-100%."""
        # Valid edge cases
        obs = WeatherObservation(temp_min=10, temp_max=20, precipitation_mm=0, humidity_avg=0)
        assert obs.humidity_avg == 0

        obs = WeatherObservation(temp_min=10, temp_max=20, precipitation_mm=0, humidity_avg=100)
        assert obs.humidity_avg == 100

        # Invalid: > 100
        with pytest.raises(ValidationError):
            WeatherObservation(temp_min=10, temp_max=20, precipitation_mm=0, humidity_avg=101)

        # Invalid: < 0
        with pytest.raises(ValidationError):
            WeatherObservation(temp_min=10, temp_max=20, precipitation_mm=0, humidity_avg=-1)


class TestRegionalWeather:
    """Tests for RegionalWeather entity."""

    def test_regional_weather_valid(self) -> None:
        """Test creating a valid regional weather record."""
        weather = RegionalWeather(
            region_id="nyeri-highland",
            date=date(2025, 12, 28),
            temp_min=12.5,
            temp_max=24.8,
            precipitation_mm=2.3,
            humidity_avg=78.5,
        )

        assert weather.region_id == "nyeri-highland"
        assert weather.date == date(2025, 12, 28)
        assert weather.temp_min == 12.5
        assert weather.temp_max == 24.8
        assert weather.precipitation_mm == 2.3
        assert weather.humidity_avg == 78.5
        assert weather.source == "open-meteo"  # Default
        assert weather.created_at is not None

    def test_regional_weather_custom_source(self) -> None:
        """Test regional weather with custom source."""
        weather = RegionalWeather(
            region_id="nyeri-highland",
            date=date(2025, 12, 28),
            temp_min=12.5,
            temp_max=24.8,
            precipitation_mm=2.3,
            humidity_avg=78.5,
            source="weather-api-v2",
        )

        assert weather.source == "weather-api-v2"

    def test_regional_weather_from_observation(self) -> None:
        """Test creating regional weather from observation."""
        obs = WeatherObservation(
            temp_min=10.0,
            temp_max=22.0,
            precipitation_mm=5.0,
            humidity_avg=65.0,
        )

        weather = RegionalWeather.from_observation(
            region_id="kericho-midland",
            observation_date=date(2025, 12, 27),
            observation=obs,
        )

        assert weather.region_id == "kericho-midland"
        assert weather.date == date(2025, 12, 27)
        assert weather.temp_min == 10.0
        assert weather.temp_max == 22.0
        assert weather.precipitation_mm == 5.0
        assert weather.humidity_avg == 65.0
        assert weather.source == "open-meteo"

    def test_regional_weather_to_observation(self) -> None:
        """Test converting regional weather to observation."""
        weather = RegionalWeather(
            region_id="nyeri-highland",
            date=date(2025, 12, 28),
            temp_min=12.5,
            temp_max=24.8,
            precipitation_mm=2.3,
            humidity_avg=78.5,
        )

        obs = weather.to_observation()

        assert isinstance(obs, WeatherObservation)
        assert obs.temp_min == 12.5
        assert obs.temp_max == 24.8
        assert obs.precipitation_mm == 2.3
        assert obs.humidity_avg == 78.5

    def test_regional_weather_model_dump(self) -> None:
        """Test serialization with model_dump (Pydantic 2.0)."""
        weather = RegionalWeather(
            region_id="nyeri-highland",
            date=date(2025, 12, 28),
            temp_min=12.5,
            temp_max=24.8,
            precipitation_mm=2.3,
            humidity_avg=78.5,
        )

        data = weather.model_dump()

        assert data["region_id"] == "nyeri-highland"
        assert data["date"] == date(2025, 12, 28)
        assert data["temp_min"] == 12.5
        assert data["source"] == "open-meteo"
