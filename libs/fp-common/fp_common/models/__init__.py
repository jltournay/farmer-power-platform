"""Pydantic models for Farmer Power Platform.

This module exports all shared domain models used across services.
"""

# Collection Point models
# Agent Config Summary models (Story 9.12b)
from fp_common.models.agent_config_summary import (
    AgentConfigDetail,
    AgentConfigSummary,
    PromptSummary,
)
from fp_common.models.collection_point import (
    CollectionPoint,
    CollectionPointCreate,
    CollectionPointUpdate,
)

# Cost models (Story 13.6)
from fp_common.models.cost import (
    AgentTypeCost,
    BudgetStatus,
    BudgetThresholdConfig,
    CostSummary,
    CostTypeSummary,
    CurrentDayCost,
    DailyCostEntry,
    DailyCostTrend,
    DecimalStr,
    DocumentCostSummary,
    DomainCost,
    EmbeddingCostByDomain,
    LlmCostByAgentType,
    LlmCostByModel,
    ModelCost,
)

# Document models
from fp_common.models.document import (
    Document,
    ExtractionMetadata,
    IngestionMetadata,
    RawDocumentRef,
    SearchResult,
)

# Domain events
from fp_common.models.domain_events import (
    CollectionEventTopic,
    PlantationEventTopic,
    get_all_valid_topics,
    is_valid_topic,
)

# Factory models
from fp_common.models.factory import Factory, FactoryCreate, FactoryUpdate

# Farmer models
from fp_common.models.farmer import (
    Farmer,
    FarmerCreate,
    FarmerUpdate,
    FarmScale,
    InteractionPreference,
    NotificationChannel,
    PreferredChannel,
    PreferredLanguage,
)

# Farmer performance models
from fp_common.models.farmer_performance import (
    FarmerPerformance,
    HistoricalMetrics,
    TodayMetrics,
    TrendDirection,
)

# Flush model
from fp_common.models.flush import Flush

# Grading models
from fp_common.models.grading_model import (
    ConditionalReject,
    GradeRules,
    GradingAttribute,
    GradingModel,
    GradingType,
)

# Performance summary model
from fp_common.models.performance_summary import PerformanceSummary

# RAG retrieval models (Story 0.75.23)
from fp_common.models.rag import RetrievalMatch, RetrievalQuery, RetrievalResult

# Region models
from fp_common.models.region import Region, RegionCreate, RegionUpdate

# Weather models
from fp_common.models.regional_weather import RegionalWeather, WeatherObservation

# Source configuration models
from fp_common.models.source_config import (
    EventConfig,
    EventsConfig,
    IngestionConfig,
    IterationConfig,
    PathPatternConfig,
    ProcessedFileConfig,
    RequestConfig,
    RetryConfig,
    SchemaDocument,
    SourceConfig,
    StorageConfig,
    TransformationConfig,
    ValidationConfig,
    ZipConfig,
    generate_json_schema,
)

# Source Config Summary models (Story 9.11b)
from fp_common.models.source_config_summary import (
    SourceConfigDetail,
    SourceConfigSummary,
)

# Source Summary model
from fp_common.models.source_summary import SourceSummary

# Value objects
from fp_common.models.value_objects import (
    GPS,
    Agronomic,
    AltitudeBand,
    AltitudeBandLabel,
    CollectionPointCapacity,
    ContactInfo,
    Coordinate,
    FlushCalendar,
    FlushPeriod,
    Geography,
    GeoLocation,
    OperatingHours,
    PaymentPolicy,
    PaymentPolicyType,
    PolygonRing,
    QualityThresholds,
    RegionBoundary,
    WeatherConfig,
)

__all__ = [
    # Value Objects
    "GPS",
    # Agent Config Summary models (Story 9.12b)
    "AgentConfigDetail",
    "AgentConfigSummary",
    # Cost models (Story 13.6)
    "AgentTypeCost",
    "Agronomic",
    "AltitudeBand",
    "AltitudeBandLabel",
    "BudgetStatus",
    "BudgetThresholdConfig",
    # Domain Events
    "CollectionEventTopic",
    # Collection Point
    "CollectionPoint",
    "CollectionPointCapacity",
    "CollectionPointCreate",
    "CollectionPointUpdate",
    # Grading
    "ConditionalReject",
    "ContactInfo",
    # Story 1.10: Polygon boundary types
    "Coordinate",
    "CostSummary",
    "CostTypeSummary",
    "CurrentDayCost",
    "DailyCostEntry",
    "DailyCostTrend",
    "DecimalStr",
    # Document
    "Document",
    "DocumentCostSummary",
    "DomainCost",
    "EmbeddingCostByDomain",
    # Source Config
    "EventConfig",
    "EventsConfig",
    "ExtractionMetadata",
    # Factory
    "Factory",
    "FactoryCreate",
    "FactoryUpdate",
    "FarmScale",
    # Farmer
    "Farmer",
    "FarmerCreate",
    # Farmer Performance
    "FarmerPerformance",
    "FarmerUpdate",
    # Flush
    "Flush",
    "FlushCalendar",
    "FlushPeriod",
    "GeoLocation",
    "Geography",
    "GradeRules",
    "GradingAttribute",
    "GradingModel",
    "GradingType",
    "HistoricalMetrics",
    "IngestionConfig",
    "IngestionMetadata",
    "InteractionPreference",
    "IterationConfig",
    "LlmCostByAgentType",
    "LlmCostByModel",
    "ModelCost",
    "NotificationChannel",
    "OperatingHours",
    "PathPatternConfig",
    "PaymentPolicy",
    "PaymentPolicyType",
    # Performance Summary
    "PerformanceSummary",
    "PlantationEventTopic",
    "PolygonRing",
    "PreferredChannel",
    "PreferredLanguage",
    "ProcessedFileConfig",
    # Agent Prompts (Story 9.12b)
    "PromptSummary",
    "QualityThresholds",
    "RawDocumentRef",
    # Region
    "Region",
    "RegionBoundary",
    "RegionCreate",
    "RegionUpdate",
    # Weather
    "RegionalWeather",
    "RequestConfig",
    # RAG retrieval models (Story 0.75.23)
    "RetrievalMatch",
    "RetrievalQuery",
    "RetrievalResult",
    "RetryConfig",
    "SchemaDocument",
    "SearchResult",
    "SourceConfig",
    # Source Config Summary (Story 9.11b)
    "SourceConfigDetail",
    "SourceConfigSummary",
    # Source Summary
    "SourceSummary",
    "StorageConfig",
    "TodayMetrics",
    "TransformationConfig",
    "TrendDirection",
    "ValidationConfig",
    "WeatherConfig",
    "WeatherObservation",
    "ZipConfig",
    "generate_json_schema",
    "get_all_valid_topics",
    "is_valid_topic",
]
