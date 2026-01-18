"""Farmer API schemas for the BFF layer.

These schemas are separate from domain models (fp_common) per ADR-012.
They define the API contract and include presentation-layer concerns
like tier computation and trend mapping.
"""

from datetime import datetime
from enum import Enum

from bff.api.schemas.responses import PaginationMeta, ResponseMeta
from pydantic import BaseModel, Field


class TierLevel(str, Enum):
    """Quality tier levels using Plantation vocabulary.

    Tiers are computed from primary_percentage_30d using
    factory-configurable thresholds (from Factory.quality_thresholds).
    """

    TIER_1 = "tier_1"  # Best quality (>= tier_1 threshold, default 85%)
    TIER_2 = "tier_2"  # Good quality (>= tier_2 threshold, default 70%)
    TIER_3 = "tier_3"  # Acceptable (>= tier_3 threshold, default 50%)
    BELOW_TIER_3 = "below_tier_3"  # Needs improvement (< tier_3 threshold)


class TrendIndicator(str, Enum):
    """Quality trend indicator for UI display.

    Maps from fp_common.models.farmer_performance.TrendDirection.
    """

    UP = "up"  # Improving quality
    DOWN = "down"  # Declining quality
    STABLE = "stable"  # Unchanged


class FarmerSummary(BaseModel):
    """Summary view of a farmer for list endpoints.

    Includes essential info for displaying in farmer lists:
    - Identity (id, name)
    - Quality metrics (primary_percentage_30d, tier)
    - Trend indicator

    This is a presentation model, not a domain model.
    """

    id: str = Field(description="Unique farmer ID (e.g., 'WM-0001')")
    name: str = Field(description="Full name (first + last)")
    primary_percentage_30d: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage of primary grade deliveries in last 30 days",
    )
    tier: TierLevel = Field(description="Quality tier based on factory thresholds")
    trend: TrendIndicator = Field(description="Quality trend direction")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "WM-0001",
                "name": "Wanjiku Muthoni",
                "primary_percentage_30d": 82.5,
                "tier": "tier_2",
                "trend": "up",
            }
        }
    }


class FarmerPerformanceAPI(BaseModel):
    """Performance metrics for API responses.

    Simplified view of FarmerPerformance from fp_common for API consumers.
    Excludes internal fields like grading_model_version.
    """

    primary_percentage_30d: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage of primary grade in last 30 days",
    )
    primary_percentage_90d: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage of primary grade in last 90 days",
    )
    total_kg_30d: float = Field(
        ge=0.0,
        description="Total kg delivered in last 30 days",
    )
    total_kg_90d: float = Field(
        ge=0.0,
        description="Total kg delivered in last 90 days",
    )
    trend: TrendIndicator = Field(description="Quality trend direction")
    deliveries_today: int = Field(
        ge=0,
        description="Number of deliveries today",
    )
    kg_today: float = Field(
        ge=0.0,
        description="Total kg delivered today",
    )


class CollectionPointRef(BaseModel):
    """Reference to a collection point for farmer profile (Story 9.5a)."""

    id: str = Field(description="Collection point ID")
    name: str = Field(description="Collection point name")


class FarmerProfile(BaseModel):
    """Farmer profile information for detail endpoint.

    Includes identity, contact, and farm information.
    Story 9.5a: collection_point_id replaced with collection_points list for N:M.
    """

    id: str = Field(description="Unique farmer ID")
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    phone: str = Field(description="Contact phone number")
    region_id: str = Field(description="Region ID")
    collection_points: list[CollectionPointRef] = Field(
        default_factory=list,
        description="Collection points where farmer delivers (Story 9.5a)",
    )
    farm_size_hectares: float = Field(description="Farm size in hectares")
    registration_date: datetime = Field(description="Registration date")
    is_active: bool = Field(description="Whether farmer is active")


class FarmerDetailResponse(BaseModel):
    """Complete farmer detail for GET /api/farmers/{id}.

    Combines profile, performance, and computed tier in a single response.
    """

    profile: FarmerProfile = Field(description="Farmer profile information")
    performance: FarmerPerformanceAPI = Field(description="Performance metrics")
    tier: TierLevel = Field(description="Quality tier based on factory thresholds")
    meta: ResponseMeta = Field(default_factory=ResponseMeta)

    model_config = {
        "json_schema_extra": {
            "example": {
                "profile": {
                    "id": "WM-0001",
                    "first_name": "Wanjiku",
                    "last_name": "Muthoni",
                    "phone": "+254712345678",
                    "region_id": "nyeri-highland",
                    "collection_points": [
                        {"id": "nyeri-highland-cp-001", "name": "Nyeri Central CP"},
                    ],
                    "farm_size_hectares": 1.5,
                    "registration_date": "2024-06-15T10:30:00Z",
                    "is_active": True,
                },
                "performance": {
                    "primary_percentage_30d": 82.5,
                    "primary_percentage_90d": 78.0,
                    "total_kg_30d": 450.0,
                    "total_kg_90d": 1200.0,
                    "trend": "up",
                    "deliveries_today": 2,
                    "kg_today": 35.5,
                },
                "tier": "tier_2",
                "meta": {
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2024-01-03T10:00:00Z",
                    "version": "1.0",
                },
            }
        }
    }


class FarmerListResponse(BaseModel):
    """Paginated farmer list for GET /api/farmers.

    Returns farmer summaries with pagination metadata.
    """

    data: list[FarmerSummary] = Field(description="List of farmer summaries")
    pagination: PaginationMeta = Field(description="Pagination metadata")
    meta: ResponseMeta = Field(default_factory=ResponseMeta)

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    {
                        "id": "WM-0001",
                        "name": "Wanjiku Muthoni",
                        "primary_percentage_30d": 82.5,
                        "tier": "tier_2",
                        "trend": "up",
                    },
                    {
                        "id": "WM-0002",
                        "name": "John Kamau",
                        "primary_percentage_30d": 91.0,
                        "tier": "tier_1",
                        "trend": "stable",
                    },
                ],
                "pagination": {
                    "page": 1,
                    "page_size": 50,
                    "total_count": 150,
                    "total_pages": 3,
                    "has_next": True,
                    "has_prev": False,
                    "next_page_token": "cursor-abc",
                },
                "meta": {
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2024-01-03T10:00:00Z",
                    "version": "1.0",
                },
            }
        }
    }
