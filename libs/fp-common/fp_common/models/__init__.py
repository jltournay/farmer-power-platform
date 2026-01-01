"""Pydantic models for Farmer Power Platform.

This module exports all shared domain models used across services.
"""

# Collection Point models
from fp_common.models.collection_point import (
    CollectionPoint,
    CollectionPointCreate,
    CollectionPointUpdate,
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
    FlushCalendar,
    FlushPeriod,
    Geography,
    GeoLocation,
    OperatingHours,
    PaymentPolicy,
    PaymentPolicyType,
    QualityThresholds,
    WeatherConfig,
)

__all__ = [
    # Value Objects
    "GPS",
    "Agronomic",
    "AltitudeBand",
    "AltitudeBandLabel",
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
    # Document
    "Document",
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
    "NotificationChannel",
    "OperatingHours",
    "PathPatternConfig",
    "PaymentPolicy",
    "PaymentPolicyType",
    "PlantationEventTopic",
    "PreferredChannel",
    "PreferredLanguage",
    "ProcessedFileConfig",
    "QualityThresholds",
    "RawDocumentRef",
    # Region
    "Region",
    "RegionCreate",
    "RegionUpdate",
    # Weather
    "RegionalWeather",
    "RequestConfig",
    "RetryConfig",
    "SchemaDocument",
    "SearchResult",
    "SourceConfig",
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
