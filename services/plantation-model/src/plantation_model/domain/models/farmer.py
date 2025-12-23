"""Farmer domain model."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from plantation_model.domain.models.value_objects import ContactInfo, GeoLocation


class FarmScale(str, Enum):
    """Farm scale classification based on hectares.

    Classification:
    - SMALLHOLDER: < 1 hectare (family-operated, manual harvesting)
    - MEDIUM: 1-5 hectares (may employ seasonal labor)
    - ESTATE: > 5 hectares (commercial operation)
    """

    SMALLHOLDER = "smallholder"
    MEDIUM = "medium"
    ESTATE = "estate"

    @classmethod
    def from_hectares(cls, hectares: float) -> "FarmScale":
        """Calculate farm scale from hectares.

        Args:
            hectares: Farm size in hectares.

        Returns:
            FarmScale enum value based on size thresholds.
        """
        if hectares < 1.0:
            return cls.SMALLHOLDER
        elif hectares <= 5.0:
            return cls.MEDIUM
        else:
            return cls.ESTATE


class Farmer(BaseModel):
    """Farmer entity - tea producer registered at a collection point.

    Farmer IDs follow the format: WM-XXXX (e.g., WM-0001)
    where WM is the prefix and XXXX is a zero-padded sequence number.

    Key relationships:
    - Farmers are registered at a primary collection_point_id
    - Region is auto-assigned based on GPS coordinates and altitude band
    - Farm scale is auto-calculated from farm_size_hectares
    """

    id: str = Field(description="Unique farmer ID (format: WM-XXXX)")
    grower_number: Optional[str] = Field(
        default=None, description="External/legacy grower number"
    )
    first_name: str = Field(min_length=1, max_length=100, description="First name")
    last_name: str = Field(min_length=1, max_length=100, description="Last name")
    region_id: str = Field(description="Auto-assigned region based on GPS + altitude")
    collection_point_id: str = Field(
        description="Primary registration collection point"
    )
    farm_location: GeoLocation = Field(description="Farm GPS coordinates with altitude")
    contact: ContactInfo = Field(
        default_factory=ContactInfo, description="Contact information (phone required)"
    )
    farm_size_hectares: float = Field(
        ge=0.01, le=1000.0, description="Farm size in hectares"
    )
    farm_scale: FarmScale = Field(
        description="Auto-calculated from farm_size_hectares"
    )
    national_id: str = Field(
        min_length=1, max_length=20, description="Government-issued national ID"
    )
    registration_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Registration timestamp",
    )
    is_active: bool = Field(default=True, description="Whether farmer is active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "WM-0001",
                "grower_number": "GN-12345",
                "first_name": "Wanjiku",
                "last_name": "Kamau",
                "region_id": "nyeri-highland",
                "collection_point_id": "nyeri-highland-cp-001",
                "farm_location": {
                    "latitude": -0.4197,
                    "longitude": 36.9553,
                    "altitude_meters": 1950.0,
                },
                "contact": {
                    "phone": "+254712345678",
                    "email": "",
                    "address": "",
                },
                "farm_size_hectares": 1.5,
                "farm_scale": "medium",
                "national_id": "12345678",
                "is_active": True,
            }
        }
    }


class FarmerCreate(BaseModel):
    """Data required to create a new farmer.

    Note: region_id, farm_scale, and altitude are auto-calculated by the service:
    - altitude: Fetched from Google Elevation API based on GPS
    - region_id: Determined by county + altitude band
    - farm_scale: Calculated from farm_size_hectares
    """

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=10, max_length=15, description="Phone number")
    national_id: str = Field(min_length=1, max_length=20, description="Government ID")
    farm_size_hectares: float = Field(ge=0.01, le=1000.0)
    latitude: float = Field(ge=-90, le=90, description="Farm latitude")
    longitude: float = Field(ge=-180, le=180, description="Farm longitude")
    collection_point_id: str = Field(description="Primary collection point")
    grower_number: Optional[str] = Field(
        default=None, description="External/legacy grower number"
    )


class FarmerUpdate(BaseModel):
    """Data for updating an existing farmer.

    Note: If farm_size_hectares is updated, farm_scale will be recalculated.
    region_id cannot be changed after registration.
    """

    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, min_length=10, max_length=15)
    farm_size_hectares: Optional[float] = Field(default=None, ge=0.01, le=1000.0)
    is_active: Optional[bool] = None
