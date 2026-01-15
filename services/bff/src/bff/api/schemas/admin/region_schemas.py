"""Region admin API schemas.

Provides request/response schemas for region management (AC1):
- RegionSummary: List view with counts
- RegionDetail: Full detail with weather config and boundaries
- RegionCreateRequest/RegionUpdateRequest: CRUD payloads
- RegionListResponse: Paginated list response
"""

from datetime import datetime

from bff.api.schemas.responses import PaginationMeta
from fp_common.models.value_objects import (
    Agronomic,
    FlushCalendar,
    Geography,
    WeatherConfig,
)
from pydantic import BaseModel, Field


class RegionSummary(BaseModel):
    """Region summary for list views.

    Provides compact representation with aggregate counts for admin list.
    """

    id: str = Field(description="Region ID (format: {county}-{altitude_band})")
    name: str = Field(description="Human-readable region name")
    county: str = Field(description="County/administrative area")
    country: str = Field(description="Country name")
    altitude_band: str = Field(description="Altitude classification: highland/midland/lowland")
    factory_count: int = Field(default=0, ge=0, description="Number of factories in region")
    farmer_count: int = Field(default=0, ge=0, description="Number of farmers in region")
    is_active: bool = Field(description="Whether region is active")


class RegionDetail(BaseModel):
    """Full region detail for single-entity views.

    Includes weather configuration and polygon boundaries per ADR-017.
    """

    id: str = Field(description="Region ID")
    name: str = Field(description="Human-readable region name")
    county: str = Field(description="County/administrative area")
    country: str = Field(description="Country name")
    geography: Geography = Field(description="Geographic definition including polygon boundary")
    flush_calendar: FlushCalendar = Field(description="Tea flush season calendar")
    agronomic: Agronomic = Field(description="Agronomic factors")
    weather_config: WeatherConfig = Field(description="Weather API configuration")
    factory_count: int = Field(default=0, ge=0, description="Number of factories in region")
    farmer_count: int = Field(default=0, ge=0, description="Number of farmers in region")
    is_active: bool = Field(description="Whether region is active")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class RegionCreateRequest(BaseModel):
    """Request payload for creating a new region.

    Region ID is auto-generated from county + altitude band.
    """

    name: str = Field(min_length=1, max_length=100, description="Human-readable region name")
    county: str = Field(min_length=1, max_length=50, description="County/administrative area")
    country: str = Field(default="Kenya", max_length=50, description="Country name")
    geography: Geography = Field(description="Geographic definition")
    flush_calendar: FlushCalendar = Field(description="Tea flush season calendar")
    agronomic: Agronomic = Field(description="Agronomic factors")
    weather_config: WeatherConfig = Field(description="Weather API configuration")


class RegionUpdateRequest(BaseModel):
    """Request payload for updating an existing region.

    All fields are optional - only provided fields are updated.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    geography: Geography | None = Field(default=None)
    flush_calendar: FlushCalendar | None = Field(default=None)
    agronomic: Agronomic | None = Field(default=None)
    weather_config: WeatherConfig | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class RegionListResponse(BaseModel):
    """Paginated response for region list endpoint."""

    data: list[RegionSummary] = Field(description="List of region summaries")
    pagination: PaginationMeta = Field(description="Pagination metadata")

    @classmethod
    def from_summaries(
        cls,
        summaries: list[RegionSummary],
        total_count: int,
        page_size: int,
        page: int = 1,
        next_page_token: str | None = None,
    ) -> "RegionListResponse":
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
