"""Factory domain model."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from fp_common.models.value_objects import (
    ContactInfo,
    GeoLocation,
    PaymentPolicy,
    QualityThresholds,
)


class Factory(BaseModel):
    """Factory entity - tea processing facility.

    Factory IDs follow the format: KEN-FAC-XXX (e.g., KEN-FAC-001)
    where KEN is the country prefix and XXX is a zero-padded sequence number.
    """

    id: str = Field(description="Unique factory ID (format: KEN-FAC-XXX)")
    name: str = Field(min_length=1, max_length=100, description="Factory name")
    code: str = Field(min_length=1, max_length=20, description="Unique factory code")
    region_id: str = Field(description="Region where factory is located")
    location: GeoLocation = Field(description="Geographic location with altitude")
    contact: ContactInfo = Field(default_factory=ContactInfo, description="Contact information")
    processing_capacity_kg: int = Field(default=0, ge=0, description="Daily processing capacity in kg")
    quality_thresholds: QualityThresholds = Field(
        default_factory=QualityThresholds,
        description="Quality tier thresholds for farmer categorization",
    )
    payment_policy: PaymentPolicy = Field(
        default_factory=PaymentPolicy,
        description="Payment incentive policy configuration",
    )
    is_active: bool = Field(default=True, description="Whether factory is active")
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
                "id": "KEN-FAC-001",
                "name": "Nyeri Tea Factory",
                "code": "NTF",
                "region_id": "nyeri-highland",
                "location": {
                    "latitude": -0.4232,
                    "longitude": 36.9587,
                    "altitude_meters": 1950.0,
                },
                "contact": {
                    "phone": "+254712345678",
                    "email": "factory@ntf.co.ke",
                    "address": "P.O. Box 123, Nyeri",
                },
                "processing_capacity_kg": 50000,
                "quality_thresholds": {
                    "tier_1": 85.0,
                    "tier_2": 70.0,
                    "tier_3": 50.0,
                },
                "payment_policy": {
                    "policy_type": "feedback_only",
                    "tier_1_adjustment": 0.0,
                    "tier_2_adjustment": 0.0,
                    "tier_3_adjustment": 0.0,
                    "below_tier_3_adjustment": 0.0,
                },
                "is_active": True,
            },
        },
    }


class FactoryCreate(BaseModel):
    """Data required to create a new factory."""

    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=20)
    region_id: str
    location: GeoLocation
    contact: ContactInfo | None = None
    processing_capacity_kg: int = Field(default=0, ge=0)
    quality_thresholds: QualityThresholds | None = None
    payment_policy: PaymentPolicy | None = None


class FactoryUpdate(BaseModel):
    """Data for updating an existing factory."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=20)
    location: GeoLocation | None = None
    contact: ContactInfo | None = None
    processing_capacity_kg: int | None = Field(default=None, ge=0)
    quality_thresholds: QualityThresholds | None = None
    payment_policy: PaymentPolicy | None = None
    is_active: bool | None = None
