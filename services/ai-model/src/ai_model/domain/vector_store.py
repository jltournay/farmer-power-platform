"""Vector store domain models for Pinecone operations.

This module defines Pydantic models for vector storage operations:
- VectorMetadata: Metadata stored with each vector for filtering
- VectorUpsertRequest: Request model for upserting vectors
- UpsertResult: Result of an upsert operation
- QueryMatch: Single match from a query
- QueryResult: Result of a similarity query
- IndexStats: Statistics about the Pinecone index

Story 0.75.13: RAG Vector Storage (Pinecone Repository)
"""

from pydantic import BaseModel, ConfigDict, Field

# Constants
VECTOR_DIMENSIONS = 1024  # E5-large dimensionality


class VectorMetadata(BaseModel):
    """Metadata stored with each vector in Pinecone.

    This schema enables filtering and attribution in queries.
    Pinecone metadata limit: 40KB per vector.

    Note: Chunk text is NOT stored here (40KB limit would bloat storage).
    After query() returns matches, retrieve chunk content from MongoDB
    using chunk_id.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    document_id: str = Field(
        ...,
        description="Stable ID from RAGDocument (e.g., 'disease-diagnosis-guide')",
    )
    chunk_id: str = Field(
        ...,
        description="Unique chunk identifier for MongoDB lookup",
    )
    chunk_index: int = Field(
        ...,
        ge=0,
        description="Position within document (0-indexed)",
    )
    domain: str = Field(
        ...,
        description="Knowledge domain (e.g., 'plant_diseases', 'tea_cultivation')",
    )
    title: str = Field(
        ...,
        description="Document title for display in results",
    )
    region: str | None = Field(
        default=None,
        description="Geographic filter (e.g., 'Kenya', 'Rwanda')",
    )
    season: str | None = Field(
        default=None,
        description="Seasonal filter (e.g., 'dry_season', 'monsoon')",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Searchable tags for filtering",
    )


class VectorUpsertRequest(BaseModel):
    """Request model for upserting a single vector.

    Attributes:
        id: Unique vector ID (format: {document_id}-{chunk_index})
        values: Embedding vector (1024 dimensions for E5-large)
        metadata: Filtering and attribution metadata
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    id: str = Field(
        ...,
        description="Unique vector ID (format: {document_id}-{chunk_index})",
    )
    values: list[float] = Field(
        ...,
        description="Embedding vector (1024 dimensions for E5-large)",
    )
    metadata: VectorMetadata | None = Field(
        default=None,
        description="Filtering and attribution metadata",
    )


class UpsertResult(BaseModel):
    """Result of an upsert operation.

    Attributes:
        upserted_count: Number of vectors successfully upserted
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    upserted_count: int = Field(
        ...,
        ge=0,
        description="Number of vectors successfully upserted",
    )


class QueryMatch(BaseModel):
    """Single match from a similarity query.

    Attributes:
        id: Vector ID that matched
        score: Similarity score (0-1, higher is more similar)
        metadata: Stored metadata for filtering and attribution
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    id: str = Field(
        ...,
        description="Vector ID that matched",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score (0-1, higher is more similar)",
    )
    metadata: VectorMetadata | None = Field(
        default=None,
        description="Stored metadata for filtering and attribution",
    )


class QueryResult(BaseModel):
    """Result of a similarity query.

    Attributes:
        matches: List of matching vectors ordered by similarity
        namespace: Namespace that was queried
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    matches: list[QueryMatch] = Field(
        default_factory=list,
        description="List of matching vectors ordered by similarity",
    )
    namespace: str | None = Field(
        default=None,
        description="Namespace that was queried",
    )

    @property
    def count(self) -> int:
        """Return number of matches."""
        return len(self.matches)


class NamespaceStats(BaseModel):
    """Statistics for a single namespace.

    Attributes:
        vector_count: Number of vectors in the namespace
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    vector_count: int = Field(
        default=0,
        ge=0,
        description="Number of vectors in the namespace",
    )


class IndexStats(BaseModel):
    """Statistics about the Pinecone index.

    Attributes:
        total_vector_count: Total vectors across all namespaces
        namespaces: Per-namespace statistics
        dimension: Vector dimensionality
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    total_vector_count: int = Field(
        default=0,
        ge=0,
        description="Total vectors across all namespaces",
    )
    namespaces: dict[str, NamespaceStats] = Field(
        default_factory=dict,
        description="Per-namespace vector counts",
    )
    dimension: int = Field(
        default=VECTOR_DIMENSIONS,
        ge=1,
        description="Vector dimensionality",
    )
