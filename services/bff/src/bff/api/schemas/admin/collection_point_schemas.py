"""Collection Point admin API schemas.

Provides request/response schemas for collection point management (AC3):
- CollectionPointSummary: List view with counts
- CollectionPointDetail: Full detail with location and lead farmer
- CollectionPointCreateRequest/CollectionPointUpdateRequest: CRUD payloads
- CollectionPointListResponse: Paginated list response
"""

from datetime import datetime

from bff.api.schemas.responses import PaginationMeta
from fp_common.models.value_objects import (
    CollectionPointCapacity,
    GeoLocation,
    OperatingHours,
)
from pydantic import BaseModel, Field


class CollectionPointSummary(BaseModel):
    """Collection point summary for list views.

    Provides compact representation with aggregate counts.
    """

    id: str = Field(description="Collection point ID (format: {region}-cp-XXX)")
    name: str = Field(description="Collection point name")
    factory_id: str = Field(description="Parent factory ID")
    region_id: str = Field(description="Region ID")
    farmer_count: int = Field(default=0, ge=0, description="Number of farmers assigned")
    status: str = Field(description="Status: active, inactive, seasonal")


class LeadFarmerSummary(BaseModel):
    """Summary of lead farmer assigned to collection point."""

    id: str = Field(description="Farmer ID")
    name: str = Field(description="Farmer full name")
    phone: str = Field(description="Farmer phone number")


class CollectionPointDetail(BaseModel):
    """Full collection point detail for single-entity views.

    Includes location, operating hours, and lead farmer if assigned.
    """

    id: str = Field(description="Collection point ID")
    name: str = Field(description="Collection point name")
    factory_id: str = Field(description="Parent factory ID")
    region_id: str = Field(description="Region ID")
    location: GeoLocation = Field(description="Geographic location")
    clerk_id: str | None = Field(default=None, description="Assigned clerk ID")
    clerk_phone: str | None = Field(default=None, description="Clerk phone number")
    operating_hours: OperatingHours = Field(description="Operating hours")
    collection_days: list[str] = Field(description="Days when collection happens")
    capacity: CollectionPointCapacity = Field(description="Capacity and equipment info")
    lead_farmer: LeadFarmerSummary | None = Field(
        default=None,
        description="Lead farmer for this collection point",
    )
    farmer_count: int = Field(default=0, ge=0, description="Number of farmers assigned")
    status: str = Field(description="Status: active, inactive, seasonal")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class CollectionPointCreateRequest(BaseModel):
    """Request payload for creating a new collection point.

    Collection points are created nested under a factory via
    POST /api/admin/factories/{factory_id}/collection-points
    """

    name: str = Field(min_length=1, max_length=100, description="Collection point name")
    location: GeoLocation = Field(description="Geographic location")
    region_id: str = Field(description="Region ID (must exist)")
    clerk_id: str | None = Field(default=None, description="Assigned clerk ID")
    clerk_phone: str | None = Field(default=None, description="Clerk phone number")
    operating_hours: OperatingHours | None = Field(default=None, description="Operating hours")
    collection_days: list[str] | None = Field(
        default=None,
        description="Collection days (e.g., ['mon', 'wed', 'fri'])",
    )
    capacity: CollectionPointCapacity | None = Field(default=None, description="Capacity info")
    status: str = Field(default="active", description="Status: active, inactive, seasonal")


class CollectionPointUpdateRequest(BaseModel):
    """Request payload for updating an existing collection point.

    All fields are optional - only provided fields are updated.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    clerk_id: str | None = Field(default=None)
    clerk_phone: str | None = Field(default=None)
    operating_hours: OperatingHours | None = Field(default=None)
    collection_days: list[str] | None = Field(default=None)
    capacity: CollectionPointCapacity | None = Field(default=None)
    status: str | None = Field(default=None)


class FarmerAssignmentResponse(BaseModel):
    """Response for farmer assignment/unassignment operations (Story 9.5a).

    Returns the updated collection point with its farmer_ids list.
    """

    id: str = Field(description="Collection point ID")
    name: str = Field(description="Collection point name")
    factory_id: str = Field(description="Parent factory ID")
    farmer_ids: list[str] = Field(description="List of assigned farmer IDs")
    farmer_count: int = Field(description="Number of farmers assigned")


class CollectionPointListResponse(BaseModel):
    """Paginated response for collection point list endpoint."""

    data: list[CollectionPointSummary] = Field(description="List of collection point summaries")
    pagination: PaginationMeta = Field(description="Pagination metadata")

    @classmethod
    def from_summaries(
        cls,
        summaries: list[CollectionPointSummary],
        total_count: int,
        page_size: int,
        page: int = 1,
        next_page_token: str | None = None,
    ) -> "CollectionPointListResponse":
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
