"""MongoDB document model for vectorization job persistence.

This module defines the Pydantic model for storing vectorization jobs in MongoDB.
It maps to/from the VectorizationResult domain model.

Story 0.75.13d: Vectorization Job Persistence
"""

from datetime import UTC, datetime

from ai_model.domain.vectorization import (
    FailedChunk,
    VectorizationJobStatus,
    VectorizationProgress,
    VectorizationResult,
)
from pydantic import BaseModel, ConfigDict, Field


class VectorizationJobDocument(BaseModel):
    """MongoDB document model for vectorization job persistence.

    This model represents a vectorization job as stored in MongoDB.
    It includes MongoDB-specific fields (_id) and timestamps for TTL management.

    The job_id is used as the MongoDB _id for direct lookups.
    A TTL index on completed_at enables automatic cleanup of completed jobs.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    # Primary identifier (also used as MongoDB _id)
    job_id: str = Field(
        ...,
        description="Unique identifier for this vectorization job",
    )

    # Job status and document reference
    status: VectorizationJobStatus = Field(
        ...,
        description="Current job status",
    )
    document_id: str = Field(
        ...,
        description="Document being vectorized",
    )
    document_version: int = Field(
        ...,
        ge=1,
        description="Version of the document being vectorized",
    )
    namespace: str = Field(
        default="",
        description="Pinecone namespace where vectors were stored",
    )

    # Progress metrics
    chunks_total: int = Field(
        default=0,
        ge=0,
        description="Total number of chunks to vectorize",
    )
    chunks_embedded: int = Field(
        default=0,
        ge=0,
        description="Number of chunks with embeddings generated",
    )
    chunks_stored: int = Field(
        default=0,
        ge=0,
        description="Number of chunks successfully stored in Pinecone",
    )
    failed_count: int = Field(
        default=0,
        ge=0,
        description="Number of chunks that failed processing",
    )

    # Results
    content_hash: str | None = Field(
        default=None,
        description="SHA256 hash of vectorized content",
    )
    pinecone_ids: list[str] = Field(
        default_factory=list,
        description="List of vector IDs stored in Pinecone",
    )
    failed_chunks: list[FailedChunk] = Field(
        default_factory=list,
        description="Details of failed chunks",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if job failed",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the job was created",
    )
    started_at: datetime | None = Field(
        default=None,
        description="When processing started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When processing completed (TTL index target)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )

    @classmethod
    def from_result(cls, result: VectorizationResult) -> "VectorizationJobDocument":
        """Create a document from a VectorizationResult.

        Args:
            result: The domain model result to convert.

        Returns:
            MongoDB document ready for persistence.
        """
        return cls(
            job_id=result.job_id,
            status=result.status,
            document_id=result.document_id,
            document_version=result.document_version,
            namespace=result.namespace or "",
            chunks_total=result.progress.chunks_total,
            chunks_embedded=result.progress.chunks_embedded,
            chunks_stored=result.progress.chunks_stored,
            failed_count=result.progress.failed_count,
            content_hash=result.content_hash,
            pinecone_ids=result.pinecone_ids,
            failed_chunks=result.failed_chunks,
            error_message=result.error_message,
            started_at=result.started_at,
            completed_at=result.completed_at,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def to_result(self) -> VectorizationResult:
        """Convert this document to a VectorizationResult.

        Returns:
            Domain model suitable for API responses.
        """
        return VectorizationResult(
            job_id=self.job_id,
            status=self.status,
            document_id=self.document_id,
            document_version=self.document_version,
            namespace=self.namespace or None,
            progress=VectorizationProgress(
                chunks_total=self.chunks_total,
                chunks_embedded=self.chunks_embedded,
                chunks_stored=self.chunks_stored,
                failed_count=self.failed_count,
            ),
            content_hash=self.content_hash,
            pinecone_ids=self.pinecone_ids,
            failed_chunks=self.failed_chunks,
            error_message=self.error_message,
            started_at=self.started_at,
            completed_at=self.completed_at,
        )
