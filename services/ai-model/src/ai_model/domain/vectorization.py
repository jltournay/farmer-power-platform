"""Vectorization pipeline domain models.

This module defines Pydantic models for the vectorization pipeline:
- VectorizationJobStatus: Lifecycle status for vectorization jobs
- VectorizationJob: Represents a vectorization operation
- VectorizationProgress: Progress metrics for tracking
- VectorizationResult: Result of a vectorization operation

Story 0.75.13b: RAG Vectorization Pipeline (Orchestration)
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class VectorizationJobStatus(str, Enum):
    """Vectorization job lifecycle status.

    Status transitions:
    - pending: Job created, waiting to start
    - in_progress: Currently processing chunks
    - completed: All chunks vectorized successfully
    - failed: Job failed completely
    - partial: Some chunks failed, others succeeded
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class VectorizationProgress(BaseModel):
    """Progress metrics for a vectorization job.

    Tracks the progress of chunk processing through the pipeline:
    embedding generation and vector storage.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

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
    eta_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Estimated time remaining in seconds",
    )

    @property
    def progress_percent(self) -> float:
        """Calculate progress as percentage (0-100)."""
        if self.chunks_total == 0:
            return 100.0
        return (self.chunks_stored / self.chunks_total) * 100.0


class VectorizationJob(BaseModel):
    """Represents a vectorization job for tracking purposes.

    Jobs can be tracked asynchronously via job_id for long-running
    operations or monitored in real-time for synchronous mode.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    job_id: str = Field(
        ...,
        description="Unique identifier for this vectorization job",
    )
    status: VectorizationJobStatus = Field(
        default=VectorizationJobStatus.PENDING,
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
    namespace: str | None = Field(
        default=None,
        description="Target Pinecone namespace (e.g., 'knowledge-v12')",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Job creation timestamp",
    )


class FailedChunk(BaseModel):
    """Details of a chunk that failed vectorization.

    Used for debugging and retry logic.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    chunk_id: str = Field(
        ...,
        description="ID of the failed chunk",
    )
    chunk_index: int = Field(
        ...,
        ge=0,
        description="Index of the failed chunk in document",
    )
    error_message: str = Field(
        ...,
        description="Error message describing the failure",
    )


class VectorizationResult(BaseModel):
    """Result of a vectorization operation.

    Contains the final status, progress metrics, and any error information.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    job_id: str = Field(
        ...,
        description="Unique identifier for this job",
    )
    status: VectorizationJobStatus = Field(
        ...,
        description="Final job status",
    )
    document_id: str = Field(
        ...,
        description="Document that was vectorized",
    )
    document_version: int = Field(
        ...,
        ge=1,
        description="Version of the document",
    )
    namespace: str | None = Field(
        default=None,
        description="Pinecone namespace where vectors were stored",
    )
    progress: VectorizationProgress = Field(
        default_factory=VectorizationProgress,
        description="Progress metrics at completion",
    )
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
        description="Details of failed chunks (for partial/failed status)",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if job failed",
    )
    started_at: datetime | None = Field(
        default=None,
        description="When processing started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When processing completed",
    )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate duration in seconds if both timestamps are set."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
