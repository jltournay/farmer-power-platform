"""Embedding domain models for Pinecone Inference API.

This module defines Pydantic models for embedding operations:
- EmbeddingInputType: Enum for passage vs query input types
- EmbeddingRequest: Request model for batch embedding
- EmbeddingResult: Response model with embeddings and usage stats
- EmbeddingCostEvent: Cost tracking event for embedding operations

Story 0.75.12: RAG Embedding Configuration (Pinecone Inference)
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingInputType(str, Enum):
    """Input type for E5 model embeddings.

    E5 models require specifying input type for optimal embeddings:
    - PASSAGE: For documents/passages being indexed (use when upserting)
    - QUERY: For search queries (use when searching)

    Failure to set this correctly will degrade retrieval accuracy.
    """

    PASSAGE = "passage"
    QUERY = "query"


class EmbeddingRequest(BaseModel):
    """Request model for embedding operations.

    Attributes:
        texts: List of texts to embed.
        input_type: Whether texts are passages (documents) or queries.
        truncate: Truncation strategy for texts exceeding max tokens.
        request_id: Optional correlation ID for tracing.
        knowledge_domain: Optional domain for cost attribution.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    texts: list[str] = Field(
        ...,
        description="List of texts to embed",
        min_length=1,
    )
    input_type: EmbeddingInputType = Field(
        default=EmbeddingInputType.PASSAGE,
        description="Input type for E5 model (passage for documents, query for search)",
    )
    truncate: str = Field(
        default="END",
        description="Truncation strategy: END (truncate at end) or NONE (error on overflow)",
    )
    request_id: str | None = Field(
        default=None,
        description="Correlation ID for distributed tracing",
    )
    knowledge_domain: str | None = Field(
        default=None,
        description="Knowledge domain for cost attribution",
    )


class EmbeddingUsage(BaseModel):
    """Usage statistics from embedding operation.

    Attributes:
        total_tokens: Total tokens processed across all texts.
    """

    total_tokens: int = Field(
        default=0,
        ge=0,
        description="Total tokens processed",
    )


class EmbeddingResult(BaseModel):
    """Result of an embedding operation.

    Attributes:
        embeddings: List of embedding vectors (one per input text).
        model: The embedding model used.
        dimensions: Dimensionality of each embedding vector.
        usage: Token usage statistics.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    embeddings: list[list[float]] = Field(
        ...,
        description="List of embedding vectors (one per input text)",
    )
    model: str = Field(
        ...,
        description="Embedding model used (e.g., multilingual-e5-large)",
    )
    dimensions: int = Field(
        ...,
        ge=1,
        description="Dimensionality of embedding vectors (1024 for E5-large)",
    )
    usage: EmbeddingUsage = Field(
        default_factory=EmbeddingUsage,
        description="Token usage statistics",
    )

    @property
    def count(self) -> int:
        """Return number of embeddings in result."""
        return len(self.embeddings)


class EmbeddingCostEvent(BaseModel):
    """Embedding cost event for tracking and attribution.

    Stored in: ai_model.embedding_cost_events
    Purpose: Visibility and attribution (not billing - Pinecone Inference
             embedding cost is included in index pricing)

    Note: Unlike LlmCostEvent, there is no cost_usd field because
    Pinecone Inference API embedding is included in index pricing.

    Attributes:
        id: Unique event identifier (UUID).
        timestamp: When the embedding completed (UTC).
        request_id: Correlation ID for distributed tracing.
        model: Embedding model used (e.g., multilingual-e5-large).
        texts_count: Number of texts embedded in this request.
        tokens_total: Estimated total tokens (from Pinecone usage).
        knowledge_domain: Optional domain for cost attribution.
        success: Whether the embedding operation succeeded.
        batch_count: Number of batches used (for large requests).
        retry_count: Number of retries before success/failure.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    id: str = Field(
        ...,
        description="Unique event identifier (UUID)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the embedding completed (UTC)",
    )
    request_id: str = Field(
        ...,
        description="Correlation ID for distributed tracing",
    )
    model: str = Field(
        ...,
        description="Embedding model used (e.g., multilingual-e5-large)",
    )
    texts_count: int = Field(
        default=0,
        ge=0,
        description="Number of texts embedded",
    )
    tokens_total: int = Field(
        default=0,
        ge=0,
        description="Total tokens processed (from Pinecone usage)",
    )
    knowledge_domain: str | None = Field(
        default=None,
        description="Knowledge domain for per-domain attribution",
    )
    success: bool = Field(
        default=True,
        description="Whether the embedding operation succeeded",
    )
    batch_count: int = Field(
        default=1,
        ge=1,
        description="Number of batches used for this request",
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retries before success/failure",
    )

    def model_dump_for_mongo(self) -> dict[str, Any]:
        """Dump model for MongoDB storage.

        Handles datetime serialization and sets _id.
        """
        data = self.model_dump()
        return data

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "EmbeddingCostEvent":
        """Create instance from MongoDB document.

        Removes MongoDB _id if present.
        """
        # Remove MongoDB _id if present
        doc.pop("_id", None)
        return cls.model_validate(doc)
