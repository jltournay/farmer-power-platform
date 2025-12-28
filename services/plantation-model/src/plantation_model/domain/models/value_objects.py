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


class QualityThresholds(BaseModel):
    """Factory-configurable quality thresholds for farmer categorization.

    NEUTRAL NAMING: tier_1, tier_2, tier_3 (NOT WIN/WATCH/WORK)
    Engagement Model maps these to engagement categories.
    Factory Admin UI shows as: Premium/Standard/Acceptable/Below Standard.

    Thresholds define minimum Primary % for each tier:
    - tier_1: Premium tier (default ≥85% Primary)
    - tier_2: Standard tier (default ≥70% Primary)
    - tier_3: Acceptable tier (default ≥50% Primary)
    - Below tier_3 = Below Standard (auto-calculated)
    """

    tier_1: float = Field(
        default=85.0,
        ge=0,
        le=100,
        description="Premium tier threshold (≥X% Primary)",
    )
    tier_2: float = Field(
        default=70.0,
        ge=0,
        le=100,
        description="Standard tier threshold (≥X% Primary)",
    )
    tier_3: float = Field(
        default=50.0,
        ge=0,
        le=100,
        description="Acceptable tier threshold (≥X% Primary)",
    )

    @field_validator("tier_2")
    @classmethod
    def tier_2_less_than_tier_1(cls, v: float, info) -> float:
        """Validate tier_2 < tier_1."""
        tier_1 = info.data.get("tier_1", 85.0)
        if v >= tier_1:
            raise ValueError(f"tier_2 ({v}) must be less than tier_1 ({tier_1})")
        return v

    @field_validator("tier_3")
    @classmethod
    def tier_3_less_than_tier_2(cls, v: float, info) -> float:
        """Validate tier_3 < tier_2."""
        tier_2 = info.data.get("tier_2", 70.0)
        if v >= tier_2:
            raise ValueError(f"tier_3 ({v}) must be less than tier_2 ({tier_2})")
        return v
