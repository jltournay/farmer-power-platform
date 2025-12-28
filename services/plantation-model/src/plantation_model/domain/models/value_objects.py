"""Value objects for the Plantation Model service."""

import re
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator


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


# ============================================================================
# Region-related Value Objects (Story 1.8)
# ============================================================================


class AltitudeBandLabel(str, Enum):
    """Valid altitude band labels for tea growing regions."""

    HIGHLAND = "highland"
    MIDLAND = "midland"
    LOWLAND = "lowland"


class GPS(BaseModel):
    """GPS coordinates (lat/lng only, without altitude)."""

    lat: float = Field(ge=-90, le=90, description="Latitude in decimal degrees")
    lng: float = Field(ge=-180, le=180, description="Longitude in decimal degrees")


class AltitudeBand(BaseModel):
    """Altitude band definition for a region.

    Altitude bands define tea growing conditions:
    - highland: 1800m+ (cooler, more rainfall, later flushes, frost risk)
    - midland: 1400m-1800m (moderate conditions)
    - lowland: below 1400m (warmer, earlier flushes)
    """

    min_meters: int = Field(ge=0, description="Minimum altitude in meters")
    max_meters: int = Field(ge=0, description="Maximum altitude in meters")
    label: AltitudeBandLabel = Field(description="Altitude band classification")

    @model_validator(mode="after")
    def validate_altitude_range(self) -> "AltitudeBand":
        """Validate that max_meters >= min_meters."""
        if self.max_meters < self.min_meters:
            raise ValueError(f"max_meters ({self.max_meters}) must be >= min_meters ({self.min_meters})")
        return self


class Geography(BaseModel):
    """Geographic definition of a region."""

    center_gps: GPS = Field(description="Center point of the region")
    radius_km: float = Field(gt=0, le=100, description="Radius of region coverage in km")
    altitude_band: AltitudeBand = Field(description="Altitude band classification")


class FlushPeriod(BaseModel):
    """A flush (tea growing season) period definition.

    Uses MM-DD format for start/end to allow year-spanning periods (e.g., dormant: 12-16 to 03-14).
    """

    # Regex pattern for validating MM-DD format
    MM_DD_PATTERN: ClassVar[re.Pattern] = re.compile(r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")

    start: str = Field(description="Start date in MM-DD format")
    end: str = Field(description="End date in MM-DD format")
    characteristics: str = Field(default="", max_length=200, description="Description of flush characteristics")

    @field_validator("start", "end")
    @classmethod
    def validate_mm_dd_format(cls, v: str) -> str:
        """Validate that date is in MM-DD format."""
        if not cls.MM_DD_PATTERN.match(v):
            raise ValueError(f"Invalid date format '{v}'. Expected format: MM-DD (e.g., '03-15')")
        return v


class FlushCalendar(BaseModel):
    """Tea flush calendar for a region.

    Defines the four main flush periods for tea production:
    - first_flush: Early spring harvest (highest quality)
    - monsoon_flush: Monsoon season harvest (high volume)
    - autumn_flush: Fall harvest (balanced quality)
    - dormant: Winter dormancy period (minimal growth)
    """

    first_flush: FlushPeriod = Field(description="First flush (spring) period")
    monsoon_flush: FlushPeriod = Field(description="Monsoon flush period")
    autumn_flush: FlushPeriod = Field(description="Autumn flush period")
    dormant: FlushPeriod = Field(description="Dormant (winter) period")


class WeatherConfig(BaseModel):
    """Weather API configuration for a region.

    Defines where to fetch weather data for the region.
    Using a single point per region reduces API costs (50 calls vs 800,000 per-farm calls).
    """

    api_location: GPS = Field(description="GPS coordinates for weather API calls")
    altitude_for_api: int = Field(ge=0, description="Altitude in meters for weather API")
    collection_time: str = Field(
        default="06:00",
        description="Daily time to collect weather data (HH:MM)",
    )

    @field_validator("collection_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time format HH:MM."""
        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", v):
            raise ValueError(f"Invalid time format '{v}'. Expected format: HH:MM (e.g., '06:00')")
        return v


class Agronomic(BaseModel):
    """Agronomic factors for a region affecting tea quality."""

    soil_type: str = Field(max_length=50, description="Primary soil type (e.g., volcanic_red)")
    typical_diseases: list[str] = Field(
        default_factory=list,
        description="Common diseases in this region",
    )
    harvest_peak_hours: str = Field(
        default="06:00-10:00",
        description="Peak harvest hours (HH:MM-HH:MM)",
    )
    frost_risk: bool = Field(default=False, description="Whether region has frost risk")

    @field_validator("harvest_peak_hours")
    @classmethod
    def validate_harvest_hours_format(cls, v: str) -> str:
        """Validate harvest hours format."""
        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$", v):
            raise ValueError(f"Invalid time range format '{v}'. Expected format: HH:MM-HH:MM (e.g., '06:00-10:00')")
        return v
