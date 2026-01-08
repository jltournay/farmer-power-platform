"""Retrieval domain models for RAG retrieval operations.

This module defines Pydantic models for the RAG retrieval service:
- RetrievalQuery: Input parameters for a retrieval request
- RetrievalMatch: Single match from a retrieval query
- RetrievalResult: Container for all retrieval matches

Story 0.75.14: RAG Retrieval Service
"""

from pydantic import BaseModel, ConfigDict, Field


class RetrievalQuery(BaseModel):
    """Input parameters for a retrieval query.

    Attributes:
        query: The search query text.
        domains: List of knowledge domains to search (empty = all domains).
        top_k: Maximum number of results to return.
        confidence_threshold: Minimum similarity score (0-1) to include in results.
        namespace: Pinecone namespace for version isolation.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    query: str = Field(
        ...,
        min_length=1,
        description="The search query text",
    )
    domains: list[str] = Field(
        default_factory=list,
        description="Knowledge domains to filter by (empty = all domains)",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of results to return",
    )
    confidence_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0-1) to include in results",
    )
    namespace: str | None = Field(
        default=None,
        description="Pinecone namespace for version isolation",
    )


class RetrievalMatch(BaseModel):
    """Single match from a retrieval query.

    Contains the chunk content plus attribution metadata for display.

    Attributes:
        chunk_id: Unique chunk identifier (MongoDB _id).
        content: Full chunk text content.
        score: Similarity score (0-1, higher is more similar).
        document_id: Parent document ID for attribution.
        title: Document title for display.
        domain: Knowledge domain of the chunk.
        metadata: Additional metadata (region, season, tags).
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    chunk_id: str = Field(
        ...,
        description="Unique chunk identifier",
    )
    content: str = Field(
        ...,
        description="Full chunk text content",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score (0-1, higher is more similar)",
    )
    document_id: str = Field(
        ...,
        description="Parent document ID for attribution",
    )
    title: str = Field(
        ...,
        description="Document title for display",
    )
    domain: str = Field(
        ...,
        description="Knowledge domain of the chunk",
    )
    metadata: dict[str, str | list[str] | None] = Field(
        default_factory=dict,
        description="Additional metadata (region, season, tags)",
    )


class RetrievalResult(BaseModel):
    """Result of a retrieval query.

    Attributes:
        matches: List of matching chunks ordered by similarity.
        query: The original search query.
        namespace: Namespace that was queried.
        total_matches: Total matches before confidence filtering.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    matches: list[RetrievalMatch] = Field(
        default_factory=list,
        description="List of matching chunks ordered by similarity",
    )
    query: str = Field(
        ...,
        description="The original search query",
    )
    namespace: str | None = Field(
        default=None,
        description="Namespace that was queried",
    )
    total_matches: int = Field(
        default=0,
        ge=0,
        description="Total matches before confidence filtering",
    )

    @property
    def count(self) -> int:
        """Return number of matches after filtering."""
        return len(self.matches)
