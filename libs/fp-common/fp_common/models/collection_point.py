"""Collection Point domain model."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from fp_common.models.value_objects import (
    CollectionPointCapacity,
    GeoLocation,
    OperatingHours,
)


class CollectionPoint(BaseModel):
    """Collection Point entity - where farmers deliver tea.

    Collection Point IDs follow the format: {region_id}-cp-XXX
    (e.g., nyeri-highland-cp-001) where XXX is a zero-padded sequence number.

    Story 9.5a: farmer_ids added for N:M Farmer-CP relationship
    """

    id: str = Field(description="Unique CP ID (format: {region}-cp-XXX)")
    name: str = Field(min_length=1, max_length=100, description="Collection point name")
    factory_id: str = Field(description="Parent factory ID")
    location: GeoLocation = Field(description="Geographic location with altitude")
    region_id: str = Field(description="Region ID for this collection point")
    clerk_id: str | None = Field(default=None, description="Assigned clerk ID")
    clerk_phone: str | None = Field(default=None, description="Clerk phone number")
    operating_hours: OperatingHours = Field(default_factory=OperatingHours, description="Operating hours")
    collection_days: list[str] = Field(
        default_factory=lambda: ["mon", "wed", "fri", "sat"],
        description="Days when collection happens",
    )
    capacity: CollectionPointCapacity = Field(
        default_factory=CollectionPointCapacity,
        description="Capacity and equipment info",
    )
    status: str = Field(
        default="active",
        description="Status: active, inactive, seasonal",
    )
    farmer_ids: list[str] = Field(
        default_factory=list,
        description="Farmers assigned to this CP (Story 9.5a)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "nyeri-highland-cp-001",
                "name": "Kamakwa Collection Point",
                "factory_id": "KEN-FAC-001",
                "location": {
                    "latitude": -0.4150,
                    "longitude": 36.9500,
                    "altitude_meters": 1850.0,
                },
                "region_id": "nyeri-highland",
                "clerk_id": "CLK-001",
                "clerk_phone": "+254712345679",
                "operating_hours": {
                    "weekdays": "06:00-10:00",
                    "weekends": "07:00-09:00",
                },
                "collection_days": ["mon", "wed", "fri", "sat"],
                "capacity": {
                    "max_daily_kg": 5000,
                    "storage_type": "covered_shed",
                    "has_weighing_scale": True,
                    "has_qc_device": False,
                },
                "status": "active",
                "farmer_ids": ["WM-0001", "WM-0002"],
            }
        }
    }


class CollectionPointCreate(BaseModel):
    """Data required to create a new collection point."""

    name: str = Field(min_length=1, max_length=100)
    factory_id: str
    location: GeoLocation
    region_id: str
    clerk_id: str | None = None
    clerk_phone: str | None = None
    operating_hours: OperatingHours | None = None
    collection_days: list[str] | None = None
    capacity: CollectionPointCapacity | None = None
    status: str = Field(default="active")


class CollectionPointUpdate(BaseModel):
    """Data for updating an existing collection point."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    clerk_id: str | None = None
    clerk_phone: str | None = None
    operating_hours: OperatingHours | None = None
    collection_days: list[str] | None = None
    capacity: CollectionPointCapacity | None = None
    status: str | None = None
