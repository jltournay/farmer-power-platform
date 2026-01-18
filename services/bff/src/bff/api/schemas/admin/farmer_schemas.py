"""Farmer admin API schemas.

Provides request/response schemas for farmer management (AC4):
- AdminFarmerSummary: List view with admin fields
- AdminFarmerDetail: Full detail with profile, performance, prefs
- AdminFarmerCreateRequest/AdminFarmerUpdateRequest: CRUD payloads
- FarmerImportRequest/FarmerImportResponse: CSV import schemas
- AdminFarmerListResponse: Paginated list response
"""

from datetime import datetime

from bff.api.schemas.farmer_schemas import TierLevel, TrendIndicator
from bff.api.schemas.responses import PaginationMeta
from fp_common.models.farmer import (
    FarmScale,
    InteractionPreference,
    NotificationChannel,
    PreferredLanguage,
)
from fp_common.models.value_objects import GeoLocation
from pydantic import BaseModel, Field, field_validator


class AdminFarmerSummary(BaseModel):
    """Farmer summary for admin list views.

    Includes admin-relevant fields like phone and CP count.
    Story 9.5a: collection_point_id replaced with cp_count for N:M relationship.
    """

    id: str = Field(description="Farmer ID (format: WM-XXXX)")
    name: str = Field(description="Full name (first + last)")
    phone: str = Field(description="Phone number (E.164 format)")
    cp_count: int = Field(default=0, description="Number of collection points assigned")
    region_id: str = Field(description="Region ID")
    farm_scale: FarmScale = Field(description="Farm scale classification")
    tier: TierLevel = Field(description="Current quality tier")
    trend: TrendIndicator = Field(description="Performance trend")
    is_active: bool = Field(description="Whether farmer is active")


class CommunicationPreferencesAPI(BaseModel):
    """Communication preferences for API layer."""

    notification_channel: NotificationChannel = Field(description="Push notification channel")
    interaction_pref: InteractionPreference = Field(description="Information consumption mode")
    pref_lang: PreferredLanguage = Field(description="Preferred language")


class FarmerPerformanceMetrics(BaseModel):
    """Performance metrics for farmer detail view."""

    primary_percentage_30d: float = Field(description="30-day primary grade percentage")
    primary_percentage_90d: float = Field(description="90-day primary grade percentage")
    total_kg_30d: float = Field(description="Total kg delivered in 30 days")
    total_kg_90d: float = Field(description="Total kg delivered in 90 days")
    tier: TierLevel = Field(description="Current quality tier")
    trend: TrendIndicator = Field(description="Performance trend indicator")
    deliveries_today: int = Field(description="Number of deliveries today")
    kg_today: float = Field(description="Kg delivered today")


class CollectionPointSummaryForFarmer(BaseModel):
    """Summary of a collection point for farmer detail view (Story 9.5a)."""

    id: str = Field(description="Collection point ID")
    name: str = Field(description="Collection point name")
    factory_id: str = Field(description="Parent factory ID")


class AdminFarmerDetail(BaseModel):
    """Full farmer detail for admin single-entity views.

    Includes profile, performance metrics, and communication preferences.
    Story 9.5a: collection_point_id replaced with collection_points list.
    """

    id: str = Field(description="Farmer ID")
    grower_number: str | None = Field(default=None, description="External/legacy grower number")
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    phone: str = Field(description="Phone number")
    national_id: str = Field(description="Government-issued national ID")
    region_id: str = Field(description="Region ID")
    collection_points: list[CollectionPointSummaryForFarmer] = Field(
        default_factory=list,
        description="Collection points where farmer is assigned (Story 9.5a)",
    )
    farm_location: GeoLocation = Field(description="Farm GPS location")
    farm_size_hectares: float = Field(description="Farm size in hectares")
    farm_scale: FarmScale = Field(description="Farm scale classification")
    performance: FarmerPerformanceMetrics = Field(description="Performance metrics")
    communication_prefs: CommunicationPreferencesAPI = Field(description="Communication preferences")
    is_active: bool = Field(description="Whether farmer is active")
    registration_date: datetime = Field(description="Registration date")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class AdminFarmerCreateRequest(BaseModel):
    """Request payload for creating a new farmer.

    Farmer ID is auto-generated. Region and farm_scale are auto-calculated.
    Story 9.5a: collection_point_id removed - use separate assignment API.
    """

    first_name: str = Field(min_length=1, max_length=100, description="First name")
    last_name: str = Field(min_length=1, max_length=100, description="Last name")
    phone: str = Field(min_length=10, max_length=15, description="Phone number (E.164)")
    national_id: str = Field(min_length=1, max_length=20, description="National ID")
    # Story 9.5a: collection_point_id removed - use separate assignment API
    farm_size_hectares: float = Field(ge=0.01, le=1000.0, description="Farm size in hectares")
    latitude: float = Field(ge=-90, le=90, description="Farm latitude")
    longitude: float = Field(ge=-180, le=180, description="Farm longitude")
    grower_number: str | None = Field(default=None, description="External/legacy grower number")
    notification_channel: NotificationChannel = Field(
        default=NotificationChannel.SMS,
        description="Push notification channel",
    )
    interaction_pref: InteractionPreference = Field(
        default=InteractionPreference.TEXT,
        description="Information consumption mode",
    )
    pref_lang: PreferredLanguage = Field(
        default=PreferredLanguage.SWAHILI,
        description="Preferred language",
    )

    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """Validate phone number format (E.164)."""
        if not v.startswith("+"):
            raise ValueError("Phone number must be in E.164 format (e.g., +254712345678)")
        return v


class AdminFarmerUpdateRequest(BaseModel):
    """Request payload for updating an existing farmer.

    All fields are optional - only provided fields are updated.
    Note: region_id cannot be changed after registration.
    """

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=10, max_length=15)
    farm_size_hectares: float | None = Field(default=None, ge=0.01, le=1000.0)
    notification_channel: NotificationChannel | None = Field(default=None)
    interaction_pref: InteractionPreference | None = Field(default=None)
    pref_lang: PreferredLanguage | None = Field(default=None)
    is_active: bool | None = Field(default=None)

    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: str | None) -> str | None:
        """Validate phone number format if provided."""
        if v is not None and not v.startswith("+"):
            raise ValueError("Phone number must be in E.164 format (e.g., +254712345678)")
        return v


class ImportErrorRow(BaseModel):
    """Error information for a failed import row."""

    row: int = Field(description="Row number (1-indexed)")
    error: str = Field(description="Error description")
    data: dict | None = Field(default=None, description="Row data that failed")


class FarmerImportRequest(BaseModel):
    """Request payload for bulk farmer import.

    CSV file is uploaded as multipart/form-data, not in this schema.

    Expected CSV columns:
    - first_name, last_name, phone, national_id
    - farm_size_hectares, latitude, longitude, grower_number (optional)

    Story 9.5a: collection_point_id removed - use separate assignment API after import.
    """

    skip_header: bool = Field(
        default=True,
        description="Whether to skip the first row (header)",
    )


class FarmerImportResponse(BaseModel):
    """Response from bulk farmer import operation."""

    created_count: int = Field(ge=0, description="Number of farmers successfully created")
    error_count: int = Field(ge=0, description="Number of rows that failed")
    error_rows: list[ImportErrorRow] = Field(
        default_factory=list,
        description="Details of failed rows",
    )
    total_rows: int = Field(ge=0, description="Total rows processed")


class AdminFarmerListResponse(BaseModel):
    """Paginated response for farmer list endpoint."""

    data: list[AdminFarmerSummary] = Field(description="List of farmer summaries")
    pagination: PaginationMeta = Field(description="Pagination metadata")

    @classmethod
    def from_summaries(
        cls,
        summaries: list[AdminFarmerSummary],
        total_count: int,
        page_size: int,
        page: int = 1,
        next_page_token: str | None = None,
    ) -> "AdminFarmerListResponse":
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
