"""Ingestion job model for queued blob processing.

This module defines the IngestionJob model which represents a blob that
has been received via Event Grid and queued for processing.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class IngestionJob(BaseModel):
    """Represents a queued ingestion job.

    Created when an Event Grid blob-created event is received and the blob
    matches an enabled source configuration. The job is stored in MongoDB
    and later processed by the ingestion pipeline.

    Attributes:
        ingestion_id: Unique ID for this ingestion run (UUID).
        trace_id: Distributed tracing ID from request headers.
        blob_path: Full blob path within the container.
        blob_etag: Blob ETag for Event Grid retry idempotency.
        container: Azure Blob Storage container name.
        source_id: ID of the matched source configuration.
        content_length: Blob size in bytes.
        status: Current processing status.
        created_at: When the job was queued.
        metadata: Fields extracted from blob path using path_pattern.
        error_message: Error details if processing failed.
        processed_at: When processing completed (success or failure).

    """

    # Observability fields (per Architect review)
    ingestion_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique ID for this ingestion run",
    )
    trace_id: str | None = Field(
        default=None,
        description="Distributed tracing ID from request headers",
    )

    # Blob identification
    blob_path: str = Field(..., description="Full blob path within container")
    blob_etag: str = Field(..., description="Blob ETag for Event Grid retry idempotency")
    container: str = Field(..., description="Storage container name")
    source_id: str = Field(..., description="Matched source config ID")
    content_length: int = Field(..., description="Blob size in bytes")

    # Processing status
    status: Literal["queued", "processing", "completed", "failed"] = Field(
        default="queued",
        description="Current processing status",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the job was queued",
    )

    # Extracted metadata from path pattern
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Fields extracted from blob path using path_pattern config",
    )

    # Processing results
    error_message: str | None = Field(
        default=None,
        description="Error details if processing failed",
    )
    processed_at: datetime | None = Field(
        default=None,
        description="When processing completed (success or failure)",
    )
