"""Content processors package.

This package contains the content processing framework including:
- ContentProcessor ABC and ProcessorResult model
- ProcessorRegistry for dynamic processor lookup
- Concrete processor implementations

Processors are registered on module import for automatic discovery.
"""

from collection_model.processors.base import (
    ContentProcessor,
    ProcessorNotFoundError,
    ProcessorResult,
)
from collection_model.processors.json_extraction import JsonExtractionProcessor
from collection_model.processors.registry import ProcessorRegistry

# Register processors
ProcessorRegistry.register("json-extraction", JsonExtractionProcessor)

__all__ = [
    "ContentProcessor",
    "JsonExtractionProcessor",
    "ProcessorNotFoundError",
    "ProcessorRegistry",
    "ProcessorResult",
]
