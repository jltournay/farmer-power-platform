"""Embedding domain models for Pinecone Inference API.

This module defines Pydantic models for embedding operations:
- EmbeddingInputType: Enum for passage vs query input types
- EmbeddingRequest: Request model for batch embedding
- EmbeddingResult: Response model with embeddings and usage stats

Story 0.75.12: RAG Embedding Configuration (Pinecone Inference)
Story 13.7: Removed EmbeddingCostEvent - cost tracking now via DAPR to platform-cost (ADR-016)
"""

from enum import Enum

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
