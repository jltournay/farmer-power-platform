"""Farmer Power Platform common utilities.

Provides shared infrastructure components for all services.
"""

from fp_common.admin import create_admin_router
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
    "IngestionConfig",
    "IterationConfig",
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
    "reset_logging",
]
