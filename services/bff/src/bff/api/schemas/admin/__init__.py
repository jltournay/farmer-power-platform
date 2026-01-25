"""Admin API schemas for platform admin portal.

Provides request/response schemas for admin CRUD operations on:
- Regions (AC1)
- Factories (AC2)
- Collection Points (AC3)
- Farmers (AC4)
- Platform Cost Monitoring (Story 9.10a)

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
from bff.api.schemas.admin.knowledge_schemas import (
    ChunkListResponse,
    ChunkSummary,
    CreateDocumentRequest,
    DeleteDocumentResponse,
    DocumentDetail,
    DocumentListResponse,
    DocumentMetadataResponse,
    DocumentStatus,
    DocumentSummary,
    ExtractionJobStatus,
    KnowledgeDomain,
    QueryKnowledgeRequest,
    QueryResponse,
    QueryResultItem,
    RollbackDocumentRequest,
    SourceFileResponse,
    UpdateDocumentRequest,
    VectorizationJobStatus,
    VectorizeDocumentRequest,
)
from bff.api.schemas.admin.platform_cost_schemas import (
    AgentTypeCostEntry,
    BudgetConfigRequest,
    BudgetConfigResponse,
    BudgetStatusResponse,
    CostSummaryResponse,
    CostTypeBreakdown,
    CurrentDayCostResponse,
    DailyTrendEntry,
    DailyTrendResponse,
    DocumentCostResponse,
    DomainCostEntry,
    EmbeddingByDomainResponse,
    LlmByAgentTypeResponse,
    LlmByModelResponse,
    ModelCostEntry,
)
from bff.api.schemas.admin.region_schemas import (
    RegionCreateRequest,
    RegionDetail,
    RegionListResponse,
    RegionSummary,
    RegionUpdateRequest,
)
from bff.api.schemas.admin.source_config_schemas import (
    SourceConfigDetailResponse,
    SourceConfigListResponse,
    SourceConfigSummaryResponse,
)

__all__ = [
    "AdminFarmerCreateRequest",
    "AdminFarmerDetail",
    "AdminFarmerListResponse",
    "AdminFarmerSummary",
    "AdminFarmerUpdateRequest",
    "AgentTypeCostEntry",
    "AssignGradingModelRequest",
    "BudgetConfigRequest",
    "BudgetConfigResponse",
    "BudgetStatusResponse",
    "ChunkListResponse",
    "ChunkSummary",
    "CollectionPointCreateRequest",
    "CollectionPointDetail",
    "CollectionPointListResponse",
    "CollectionPointSummary",
    "CollectionPointUpdateRequest",
    "CostSummaryResponse",
    "CostTypeBreakdown",
    "CreateDocumentRequest",
    "CurrentDayCostResponse",
    "DailyTrendEntry",
    "DailyTrendResponse",
    "DeleteDocumentResponse",
    "DocumentCostResponse",
    "DocumentDetail",
    "DocumentListResponse",
    "DocumentMetadataResponse",
    "DocumentStatus",
    "DocumentSummary",
    "DomainCostEntry",
    "EmbeddingByDomainResponse",
    "ExtractionJobStatus",
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
    "KnowledgeDomain",
    "LlmByAgentTypeResponse",
    "LlmByModelResponse",
    "ModelCostEntry",
    "QualityThresholdsAPI",
    "QueryKnowledgeRequest",
    "QueryResponse",
    "QueryResultItem",
    "RegionCreateRequest",
    "RegionDetail",
    "RegionListResponse",
    "RegionSummary",
    "RegionUpdateRequest",
    "RollbackDocumentRequest",
    "SourceConfigDetailResponse",
    "SourceConfigListResponse",
    "SourceConfigSummaryResponse",
    "SourceFileResponse",
    "UpdateDocumentRequest",
    "VectorizationJobStatus",
    "VectorizeDocumentRequest",
]
