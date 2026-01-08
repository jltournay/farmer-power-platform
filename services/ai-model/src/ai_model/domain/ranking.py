"""Ranking domain models for RAG result re-ranking and scoring.

This module defines Pydantic models for the RAG ranking service:
- RankingConfig: Configuration for ranking operations
- RankedMatch: Single ranked result extending RetrievalMatch
- RankingResult: Container for all ranked matches with metadata

Story 0.75.15: RAG Ranking Logic
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RankingConfig(BaseModel):
    """Configuration for ranking operations.

    Controls all aspects of the ranking pipeline including re-ranking,
    domain boosting, recency weighting, and deduplication.

    Attributes:
        domain_boosts: Boost factors per domain (e.g., {"plant_diseases": 1.2}).
        recency_weight: Weight for recency scoring (0.0 = disabled, 0.1-0.3 typical).
        dedup_threshold: Similarity threshold for deduplication (0.9 = 90% similar).
        top_n: Maximum results to return after ranking.
        rerank_model: Pinecone reranker model to use.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    domain_boosts: dict[str, float] = Field(
        default_factory=dict,
        description="Boost factors per domain (e.g., {'plant_diseases': 1.2})",
    )
    recency_weight: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Weight for recency scoring (0.0 = disabled)",
    )
    dedup_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for deduplication (0.9 = 90% similar)",
    )
    top_n: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum results to return after ranking",
    )
    rerank_model: str = Field(
        default="pinecone-rerank-v0",
        description="Pinecone reranker model to use",
    )


class RankedMatch(BaseModel):
    """Single ranked result from the ranking pipeline.

    Extends RetrievalMatch with additional ranking-specific fields
    for rerank score, boost factor, and recency factor.

    Attributes:
        chunk_id: Unique chunk identifier (MongoDB _id).
        content: Full chunk text content.
        score: Original retrieval similarity score (0-1).
        rerank_score: Score from reranker (higher is more relevant, may exceed 1.0 after boosting).
        document_id: Parent document ID for attribution.
        title: Document title for display.
        domain: Knowledge domain of the chunk.
        metadata: Additional metadata (region, season, tags).
        boost_applied: Domain boost factor that was applied (default 1.0).
        recency_factor: Recency factor applied (0.0-1.0, 1.0 = today).
        updated_at: Document last updated timestamp (for recency calculation).
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
        description="Original retrieval similarity score (0-1)",
    )
    rerank_score: float = Field(
        ...,
        ge=0.0,
        description="Score from reranker (higher is more relevant, may exceed 1.0 after boosting)",
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
    boost_applied: float = Field(
        default=1.0,
        ge=0.0,
        description="Domain boost factor that was applied",
    )
    recency_factor: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Recency factor applied (0.0-1.0, 1.0 = today)",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Document last updated timestamp",
    )


class RankingResult(BaseModel):
    """Result of a ranking operation.

    Contains all ranked matches plus metadata about the ranking process.

    Attributes:
        matches: List of ranked matches ordered by final score.
        query: The original search query.
        ranking_config: Configuration used for ranking.
        duplicates_removed: Number of duplicates removed during deduplication.
        reranker_used: Whether the reranker was successfully used.
        namespace: Pinecone namespace that was queried.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    matches: list[RankedMatch] = Field(
        default_factory=list,
        description="List of ranked matches ordered by final score",
    )
    query: str = Field(
        ...,
        description="The original search query",
    )
    ranking_config: RankingConfig = Field(
        default_factory=RankingConfig,
        description="Configuration used for ranking",
    )
    duplicates_removed: int = Field(
        default=0,
        ge=0,
        description="Number of duplicates removed during deduplication",
    )
    reranker_used: bool = Field(
        default=True,
        description="Whether the reranker was successfully used",
    )
    namespace: str | None = Field(
        default=None,
        description="Pinecone namespace that was queried",
    )

    @property
    def count(self) -> int:
        """Return number of matches after ranking."""
        return len(self.matches)
