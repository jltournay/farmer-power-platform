"""Farmer Power Platform common utilities.

Provides shared infrastructure components for all services.
"""

from fp_common.admin import create_admin_router
from fp_common.cache import MongoChangeStreamCache
from fp_common.events import (
    DLQHandler,
    DLQRecord,
    DLQRepository,
    handle_dead_letter,
    start_dlq_subscription,
)
from fp_common.logging import configure_logging, reset_logging
from fp_common.models.source_config import (
    IngestionConfig,
    IterationConfig,
    PathPatternConfig,
    ProcessedFileConfig,
    RequestConfig,
    RetryConfig,
    SourceConfig,
    StorageConfig,
    TransformationConfig,
    ValidationConfig,
    ZipConfig,
    generate_json_schema,
)

__version__ = "0.1.0"

__all__ = [
    "DLQHandler",
    "DLQRecord",
    "DLQRepository",
    "IngestionConfig",
    "IterationConfig",
    "MongoChangeStreamCache",
    "PathPatternConfig",
    "ProcessedFileConfig",
    "RequestConfig",
    "RetryConfig",
    "SourceConfig",
    "StorageConfig",
    "TransformationConfig",
    "ValidationConfig",
    "ZipConfig",
    "configure_logging",
    "create_admin_router",
    "generate_json_schema",
    "handle_dead_letter",
    "reset_logging",
    "start_dlq_subscription",
]
