"""Admin API schemas for platform admin portal.

Provides request/response schemas for admin CRUD operations on:
- Regions (AC1)
- Factories (AC2)
- Collection Points (AC3)
- Farmers (AC4)

All schemas follow ADR-012 BFF patterns with separate API schemas
from domain models.
"""

from bff.api.schemas.admin.collection_point_schemas import (
    CollectionPointCreateRequest,
    CollectionPointDetail,
    CollectionPointListResponse,
    CollectionPointSummary,
    CollectionPointUpdateRequest,
)
from bff.api.schemas.admin.factory_schemas import (
    FactoryCreateRequest,
    FactoryDetail,
    FactoryListResponse,
    FactorySummary,
    FactoryUpdateRequest,
    QualityThresholdsAPI,
)
from bff.api.schemas.admin.farmer_schemas import (
    AdminFarmerCreateRequest,
    AdminFarmerDetail,
    AdminFarmerListResponse,
    AdminFarmerSummary,
    AdminFarmerUpdateRequest,
    FarmerImportRequest,
    FarmerImportResponse,
    ImportErrorRow,
)
from bff.api.schemas.admin.grading_model_schemas import (
    AssignGradingModelRequest,
    GradingModelDetail,
    GradingModelListResponse,
    GradingModelSummary,
)
from bff.api.schemas.admin.region_schemas import (
    RegionCreateRequest,
    RegionDetail,
    RegionListResponse,
    RegionSummary,
    RegionUpdateRequest,
)

__all__ = [
    "AdminFarmerCreateRequest",
    "AdminFarmerDetail",
    "AdminFarmerListResponse",
    "AdminFarmerSummary",
    "AdminFarmerUpdateRequest",
    "AssignGradingModelRequest",
    "CollectionPointCreateRequest",
    "CollectionPointDetail",
    "CollectionPointListResponse",
    "CollectionPointSummary",
    "CollectionPointUpdateRequest",
    "FactoryCreateRequest",
    "FactoryDetail",
    "FactoryListResponse",
    "FactorySummary",
    "FactoryUpdateRequest",
    "FarmerImportRequest",
    "FarmerImportResponse",
    "GradingModelDetail",
    "GradingModelListResponse",
    "GradingModelSummary",
    "ImportErrorRow",
    "QualityThresholdsAPI",
    "RegionCreateRequest",
    "RegionDetail",
    "RegionListResponse",
    "RegionSummary",
    "RegionUpdateRequest",
]
