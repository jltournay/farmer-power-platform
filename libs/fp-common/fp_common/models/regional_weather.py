"""RegionalWeather domain model for storing weather observations per region."""

import datetime as dt
from datetime import UTC

from pydantic import BaseModel, Field


class WeatherObservation(BaseModel):
    """Daily weather observation for a region.

    Contains temperature, precipitation, and humidity data collected from
    weather APIs (e.g., Open-Meteo) for a specific date.
    """

    temp_min: float = Field(description="Minimum temperature in Celsius")
    temp_max: float = Field(description="Maximum temperature in Celsius")
    precipitation_mm: float = Field(ge=0, description="Total precipitation in millimeters")
    humidity_avg: float = Field(ge=0, le=100, description="Average humidity percentage")


class RegionalWeather(BaseModel):
    """Regional weather entity - daily weather observations for a region.

    This entity stores weather data collected via scheduled pull ingestion
    from weather APIs. Data is keyed by (region_id, date) for efficient
    upserts and lookups.

    TTL: 90 days (managed via MongoDB TTL index on created_at field).
    """

    region_id: str = Field(description="Region ID this weather data belongs to")
    date: dt.date = Field(description="Date of the weather observation")

    # Weather observations
    temp_min: float = Field(description="Minimum temperature in Celsius")
    temp_max: float = Field(description="Maximum temperature in Celsius")
    precipitation_mm: float = Field(ge=0, description="Total precipitation in millimeters")
    humidity_avg: float = Field(ge=0, le=100, description="Average humidity percentage")

    # Metadata
    source: str = Field(default="open-meteo", description="Weather data source")
    created_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(UTC),
        description="When this record was created (used for TTL)",
    )

    @classmethod
    def from_observation(
        cls,
        region_id: str,
        observation_date: dt.date,
        observation: WeatherObservation,
        source: str = "open-meteo",
    ) -> "RegionalWeather":
        """Create a RegionalWeather from a WeatherObservation."""
        return cls(
            region_id=region_id,
            date=observation_date,
            temp_min=observation.temp_min,
            temp_max=observation.temp_max,
            precipitation_mm=observation.precipitation_mm,
            humidity_avg=observation.humidity_avg,
            source=source,
        )

    def to_observation(self) -> WeatherObservation:
        """Convert to a WeatherObservation value object."""
        return WeatherObservation(
            temp_min=self.temp_min,
            temp_max=self.temp_max,
            precipitation_mm=self.precipitation_mm,
            humidity_avg=self.humidity_avg,
        )

    model_config = {
        "json_schema_extra": {
            "example": {
                "region_id": "nyeri-highland",
                "date": "2025-12-28",
                "temp_min": 12.5,
                "temp_max": 24.8,
                "precipitation_mm": 2.3,
                "humidity_avg": 78.5,
                "source": "open-meteo",
            },
        },
    }
