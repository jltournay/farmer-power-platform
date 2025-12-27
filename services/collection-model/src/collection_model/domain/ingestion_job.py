"""Ingestion job model for queued blob/pull processing.

This module defines the IngestionJob model which represents content that
has been received (via Event Grid blob event or scheduled pull) and queued
for processing.

Story 2.7: Extended to support pull mode with inline content and linkage.
"""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class IngestionJob(BaseModel):
    """Represents a queued ingestion job.

    Created when:
    - An Event Grid blob-created event is received (blob_trigger mode)
    - A scheduled pull job fetches data from an external API (scheduled_pull mode)

    For blob_trigger mode: blob_path, blob_etag, container are required.
    For scheduled_pull mode: content is required (inline JSON bytes).

    Attributes:
        ingestion_id: Unique ID for this ingestion run (UUID).
        trace_id: Distributed tracing ID from request headers.
        source_id: ID of the matched source configuration.
        status: Current processing status.
        created_at: When the job was queued.
        metadata: Fields extracted from blob path using path_pattern.
        error_message: Error details if processing failed.
        processed_at: When processing completed (success or failure).

        # Blob mode fields (optional for pull mode)
        blob_path: Full blob path within the container.
        blob_etag: Blob ETag for Event Grid retry idempotency.
        container: Azure Blob Storage container name.
        content_length: Blob size in bytes.

        # Pull mode fields (Story 2.7)
        content: Inline content from HTTP fetch (bytes).
        linkage: Fields injected from iteration item for linkage.
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

    # Common fields
    source_id: str = Field(..., description="Matched source config ID")

    # Blob identification (optional for pull mode)
    blob_path: str | None = Field(default=None, description="Full blob path within container (blob mode)")
    blob_etag: str | None = Field(default=None, description="Blob ETag for Event Grid retry idempotency (blob mode)")
    container: str | None = Field(default=None, description="Storage container name (blob mode)")
    content_length: int | None = Field(default=None, description="Blob size in bytes (blob mode)")

    # Pull mode fields (Story 2.7)
    content: bytes | None = Field(default=None, description="Inline content from HTTP fetch (pull mode)")
    linkage: dict[str, Any] | None = Field(default=None, description="Fields injected from iteration item (pull mode)")

    # Processing status
    status: Literal["queued", "processing", "extracting", "completed", "failed"] = Field(
        default="queued",
        description="Current processing status",
    )
    retry_count: int = Field(
        default=0,
        description="Number of retry attempts",
    )
    error_type: Literal["extraction", "storage", "validation", "config"] | None = Field(
        default=None,
        description="Type of error if failed",
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

    @model_validator(mode="after")
    def validate_content_source(self) -> "IngestionJob":
        """Validate that either blob_path or content is set.

        For blob_trigger mode: blob_path, blob_etag, container required.
        For scheduled_pull mode: content required.
        """
        has_blob = self.blob_path is not None
        has_content = self.content is not None

        if not has_blob and not has_content:
            raise ValueError("Either blob_path (blob mode) or content (pull mode) must be set")

        return self

    @property
    def is_pull_mode(self) -> bool:
        """Check if this job is from pull mode (has inline content)."""
        return self.content is not None

    @property
    def is_blob_mode(self) -> bool:
        """Check if this job is from blob mode (has blob path)."""
        return self.blob_path is not None
