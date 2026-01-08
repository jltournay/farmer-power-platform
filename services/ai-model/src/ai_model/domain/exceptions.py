"""Domain exceptions for AI Model service.

Story 0.75.13c: Centralized exceptions to avoid circular imports.

These exceptions are domain-level errors that can be safely imported
anywhere without triggering circular import chains.
"""


class AiModelError(Exception):
    """Base exception for AI Model service errors."""

    pass


class DocumentNotFoundError(AiModelError):
    """Raised when a document or document version is not found."""

    pass


class InvalidDocumentStatusError(AiModelError):
    """Raised when document status doesn't allow the requested operation."""

    pass


class VectorizationError(AiModelError):
    """Raised when vectorization fails."""

    pass


class EmbeddingError(AiModelError):
    """Raised when embedding generation fails."""

    pass


class VectorStoreError(AiModelError):
    """Raised when vector store operations fail."""

    pass
