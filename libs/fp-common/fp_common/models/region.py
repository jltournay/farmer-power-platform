"""Region domain model for geographic and agronomic tea growing zones."""

import re
from datetime import UTC, datetime
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

from fp_common.models.value_objects import (
    Agronomic,
    AltitudeBandLabel,
    FlushCalendar,
    Geography,
    WeatherConfig,
)


class Region(BaseModel):
    """Region entity - geographic zone for tea growing with weather configuration.

    Region IDs follow the format: {county}-{altitude_band} (e.g., nyeri-highland)
    where county is lowercase and altitude_band is one of: highland, midland, lowland.
    """

    # Regex pattern for region_id validation: lowercase letters/numbers with hyphen, ending with altitude band
    REGION_ID_PATTERN: ClassVar[re.Pattern] = re.compile(r"^[a-z0-9]+-(highland|midland|lowland)$")

    region_id: str = Field(description="Unique region ID (format: {county}-{altitude_band})")
    name: str = Field(min_length=1, max_length=100, description="Human-readable region name")
    county: str = Field(min_length=1, max_length=50, description="County/administrative area name")
    country: str = Field(default="Kenya", max_length=50, description="Country code or name")

    geography: Geography = Field(description="Geographic definition of the region")
    flush_calendar: FlushCalendar = Field(description="Tea flush (season) calendar")
    agronomic: Agronomic = Field(description="Agronomic factors for the region")
    weather_config: WeatherConfig = Field(description="Weather API configuration")

    is_active: bool = Field(default=True, description="Whether region is active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )

    @field_validator("region_id")
    @classmethod
    def validate_region_id_format(cls, v: str) -> str:
        """Validate region_id follows {county}-{altitude_band} format."""
        if not cls.REGION_ID_PATTERN.match(v):
            raise ValueError(
                f"Invalid region_id format '{v}'. "
                "Expected format: {{county}}-{{altitude_band}} "
                "(e.g., 'nyeri-highland'). County must be lowercase alphanumeric, "
                "altitude_band must be one of: highland, midland, lowland."
            )
        return v

    @field_validator("county")
    @classmethod
    def validate_county_lowercase(cls, v: str) -> str:
        """Ensure county is stored in title case but validated as lowercase in ID."""
        return v.strip()

    def get_altitude_band_label(self) -> AltitudeBandLabel:
        """Get the altitude band label from geography."""
        return self.geography.altitude_band.label

    model_config = {
        "json_schema_extra": {
            "example": {
                "region_id": "nyeri-highland",
                "name": "Nyeri Highland",
                "county": "Nyeri",
                "country": "Kenya",
                "geography": {
                    "center_gps": {"lat": -0.4197, "lng": 36.9553},
                    "radius_km": 25,
                    "altitude_band": {
                        "min_meters": 1800,
                        "max_meters": 2200,
                        "label": "highland",
                    },
                },
                "flush_calendar": {
                    "first_flush": {
                        "start": "03-15",
                        "end": "05-15",
                        "characteristics": "Highest quality, delicate flavor",
                    },
                    "monsoon_flush": {
                        "start": "06-15",
                        "end": "09-30",
                        "characteristics": "High volume, robust flavor",
                    },
                    "autumn_flush": {
                        "start": "10-15",
                        "end": "12-15",
                        "characteristics": "Balanced quality",
                    },
                    "dormant": {
                        "start": "12-16",
                        "end": "03-14",
                        "characteristics": "Minimal growth",
                    },
                },
                "agronomic": {
                    "soil_type": "volcanic_red",
                    "typical_diseases": ["blister_blight", "grey_blight", "red_rust"],
                    "harvest_peak_hours": "06:00-10:00",
                    "frost_risk": True,
                },
                "weather_config": {
                    "api_location": {"lat": -0.4197, "lng": 36.9553},
                    "altitude_for_api": 1950,
                    "collection_time": "06:00",
                },
                "is_active": True,
            },
        },
    }


class RegionCreate(BaseModel):
    """Data required to create a new region."""

    name: str = Field(min_length=1, max_length=100)
    county: str = Field(min_length=1, max_length=50)
    country: str = Field(default="Kenya", max_length=50)
    geography: Geography
    flush_calendar: FlushCalendar
    agronomic: Agronomic
    weather_config: WeatherConfig

    def generate_region_id(self) -> str:
        """Generate region_id from county and altitude band."""
        county_slug = self.county.lower().replace(" ", "")
        altitude_band = self.geography.altitude_band.label.value
        return f"{county_slug}-{altitude_band}"


class RegionUpdate(BaseModel):
    """Data for updating an existing region."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    geography: Geography | None = None
    flush_calendar: FlushCalendar | None = None
    agronomic: Agronomic | None = None
    weather_config: WeatherConfig | None = None
    is_active: bool | None = None
