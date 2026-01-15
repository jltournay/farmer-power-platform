"""Factory admin API schemas.

Provides request/response schemas for factory management (AC2):
- FactorySummary: List view with counts
- FactoryDetail: Full detail with thresholds and grading model
- FactoryCreateRequest/FactoryUpdateRequest: CRUD payloads
- FactoryListResponse: Paginated list response
"""

from datetime import datetime

from bff.api.schemas.responses import PaginationMeta
from fp_common.models.value_objects import (
    ContactInfo,
    GeoLocation,
    PaymentPolicy,
)
from pydantic import BaseModel, Field, field_validator


class QualityThresholdsAPI(BaseModel):
    """Quality tier thresholds for API layer.

    Thresholds define minimum Primary % for each tier:
    - tier_1 > tier_2 > tier_3 (validated)
    """

    tier_1: float = Field(
        default=85.0,
        ge=0,
        le=100,
        description="Premium tier threshold (>= X% Primary)",
    )
    tier_2: float = Field(
        default=70.0,
        ge=0,
        le=100,
        description="Standard tier threshold (>= X% Primary)",
    )
    tier_3: float = Field(
        default=50.0,
        ge=0,
        le=100,
        description="Acceptable tier threshold (>= X% Primary)",
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


class FactorySummary(BaseModel):
    """Factory summary for list views.

    Provides compact representation with aggregate counts.
    """

    id: str = Field(description="Factory ID (format: KEN-FAC-XXX)")
    name: str = Field(description="Factory name")
    code: str = Field(description="Unique factory code")
    region_id: str = Field(description="Region ID where factory is located")
    collection_point_count: int = Field(default=0, ge=0, description="Number of collection points")
    farmer_count: int = Field(default=0, ge=0, description="Number of farmers")
    is_active: bool = Field(description="Whether factory is active")


class GradingModelSummary(BaseModel):
    """Summary of grading model assigned to factory."""

    id: str = Field(description="Grading model ID")
    name: str = Field(description="Grading model name")
    version: str = Field(description="Model version")
    grade_count: int = Field(description="Number of grades in model")


class FactoryDetail(BaseModel):
    """Full factory detail for single-entity views.

    Includes quality thresholds and grading model information.
    """

    id: str = Field(description="Factory ID")
    name: str = Field(description="Factory name")
    code: str = Field(description="Unique factory code")
    region_id: str = Field(description="Region ID")
    location: GeoLocation = Field(description="Geographic location")
    contact: ContactInfo = Field(description="Contact information")
    processing_capacity_kg: int = Field(description="Daily processing capacity in kg")
    quality_thresholds: QualityThresholdsAPI = Field(description="Quality tier thresholds")
    payment_policy: PaymentPolicy = Field(description="Payment incentive policy")
    grading_model: GradingModelSummary | None = Field(
        default=None,
        description="Assigned grading model (if any)",
    )
    collection_point_count: int = Field(default=0, ge=0, description="Number of collection points")
    farmer_count: int = Field(default=0, ge=0, description="Number of farmers")
    is_active: bool = Field(description="Whether factory is active")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class FactoryCreateRequest(BaseModel):
    """Request payload for creating a new factory.

    Factory ID is auto-generated based on country prefix.
    """

    name: str = Field(min_length=1, max_length=100, description="Factory name")
    code: str = Field(min_length=1, max_length=20, description="Unique factory code")
    region_id: str = Field(description="Region ID (must exist)")
    location: GeoLocation = Field(description="Geographic location")
    contact: ContactInfo | None = Field(default=None, description="Contact information")
    processing_capacity_kg: int = Field(default=0, ge=0, description="Daily capacity in kg")
    quality_thresholds: QualityThresholdsAPI | None = Field(
        default=None,
        description="Quality tier thresholds (defaults applied if not provided)",
    )
    payment_policy: PaymentPolicy | None = Field(
        default=None,
        description="Payment incentive policy (defaults applied if not provided)",
    )


class FactoryUpdateRequest(BaseModel):
    """Request payload for updating an existing factory.

    All fields are optional - only provided fields are updated.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=20)
    location: GeoLocation | None = Field(default=None)
    contact: ContactInfo | None = Field(default=None)
    processing_capacity_kg: int | None = Field(default=None, ge=0)
    quality_thresholds: QualityThresholdsAPI | None = Field(default=None)
    payment_policy: PaymentPolicy | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class FactoryListResponse(BaseModel):
    """Paginated response for factory list endpoint."""

    data: list[FactorySummary] = Field(description="List of factory summaries")
    pagination: PaginationMeta = Field(description="Pagination metadata")

    @classmethod
    def from_summaries(
        cls,
        summaries: list[FactorySummary],
        total_count: int,
        page_size: int,
        page: int = 1,
        next_page_token: str | None = None,
    ) -> "FactoryListResponse":
        """Create response from list of summaries with pagination."""
        return cls(
            data=summaries,
            pagination=PaginationMeta.from_client_response(
                total_count=total_count,
                page_size=page_size,
                page=page,
                next_page_token=next_page_token,
            ),
        )
