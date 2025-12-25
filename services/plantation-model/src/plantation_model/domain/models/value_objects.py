"""Value objects for the Plantation Model service."""

import re
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator


class GeoLocation(BaseModel):
    """Geographic location with auto-populated altitude.

    The altitude_meters field is automatically fetched from Google Elevation API
    based on GPS coordinates - it should NOT be provided by user input.
    """

    latitude: float = Field(ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(ge=-180, le=180, description="Longitude in decimal degrees")
    altitude_meters: float = Field(
        default=0.0,
        description="Altitude in meters - auto-populated from Google Elevation API",
    )


class ContactInfo(BaseModel):
    """Contact information for an entity."""

    phone: str = Field(default="", description="Phone number")
    email: str = Field(default="", description="Email address")
    address: str = Field(default="", description="Physical address")


class OperatingHours(BaseModel):
    """Operating hours for a collection point.

    Hours must be in format "HH:MM-HH:MM" (e.g., "06:00-10:00").
    """

    # Regex pattern for validating time range format (HH:MM-HH:MM)
    TIME_RANGE_PATTERN: ClassVar[re.Pattern] = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$")

    weekdays: str = Field(default="06:00-10:00", description="Weekday operating hours (HH:MM-HH:MM)")
    weekends: str = Field(default="07:00-09:00", description="Weekend operating hours (HH:MM-HH:MM)")

    @field_validator("weekdays", "weekends")
    @classmethod
    def validate_time_range_format(cls, v: str) -> str:
        """Validate that the time range is in correct format."""
        if not cls.TIME_RANGE_PATTERN.match(v):
            raise ValueError(f"Invalid time range format '{v}'. Expected format: HH:MM-HH:MM (e.g., '06:00-10:00')")
        return v


class CollectionPointCapacity(BaseModel):
    """Capacity and equipment information for a collection point."""

    max_daily_kg: int = Field(default=0, ge=0, description="Maximum daily capacity in kg")
    storage_type: str = Field(
        default="covered_shed",
        description="Storage type: covered_shed, open_air, refrigerated",
    )
    has_weighing_scale: bool = Field(default=False, description="Has weighing scale")
    has_qc_device: bool = Field(default=False, description="Has quality control device")
