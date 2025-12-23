"""Value objects for the Plantation Model service."""

from pydantic import BaseModel, Field


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
    """Operating hours for a collection point."""

    weekdays: str = Field(default="06:00-10:00", description="Weekday operating hours")
    weekends: str = Field(default="07:00-09:00", description="Weekend operating hours")


class CollectionPointCapacity(BaseModel):
    """Capacity and equipment information for a collection point."""

    max_daily_kg: int = Field(default=0, ge=0, description="Maximum daily capacity in kg")
    storage_type: str = Field(
        default="covered_shed",
        description="Storage type: covered_shed, open_air, refrigerated",
    )
    has_weighing_scale: bool = Field(default=False, description="Has weighing scale")
    has_qc_device: bool = Field(default=False, description="Has quality control device")
