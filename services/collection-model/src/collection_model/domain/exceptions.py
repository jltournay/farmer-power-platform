"""Custom exceptions for Collection Model service.

This module defines exceptions used throughout the content processing pipeline.
Each exception type maps to an error_type for proper retry behavior.
"""


class CollectionModelError(Exception):
    """Base exception for Collection Model errors."""

    error_type: str = "unknown"


class ExtractionError(CollectionModelError):
    """Raised when AI Model extraction fails.

    This is typically a transient error - the job should be retried.
    Examples:
    - LLM timeout
    - AI Model service unavailable
    - Invalid LLM response
    """

    error_type: str = "extraction"


class StorageError(CollectionModelError):
    """Raised when storage operations fail.

    This is typically a transient error - the job should be retried.
    Examples:
    - MongoDB connection error
    - Blob storage unavailable
    - Write timeout
    """

    error_type: str = "storage"


class ValidationError(CollectionModelError):
    """Raised when content validation fails.

    This may or may not be retryable depending on the cause.
    Examples:
    - Invalid JSON format
    - Schema validation failure
    - Missing required fields
    """

    error_type: str = "validation"


class ConfigurationError(CollectionModelError):
    """Raised when configuration is invalid.

    This is NOT retryable - it's a permanent configuration error.
    Examples:
    - Unknown processor_type
    - Missing source configuration
    - Invalid AI agent ID
    """

    error_type: str = "config"


class BlobNotFoundError(StorageError):
    """Raised when the blob cannot be found in Azure Blob Storage.

    This may indicate the blob was deleted or the path is invalid.
    """

    pass


class DuplicateDocumentError(StorageError):
    """Raised when a document with the same content hash already exists.

    This is actually a success case - we skip processing.
    """

    pass
