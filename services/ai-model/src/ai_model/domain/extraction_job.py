"""Extraction job domain models for async document extraction tracking.

This module defines the Pydantic models for tracking extraction job progress.
Jobs are stored in the ai_model.extraction_jobs MongoDB collection.

Story 0.75.10b: Basic PDF/Markdown Extraction
Story 0.75.10c: Azure Document Intelligence Integration
"""

from datetime import UTC, datetime
from enum import Enum

from ai_model.domain.rag_document import ExtractionMethod
from pydantic import BaseModel, Field


class ExtractionJobStatus(str, Enum):
    """Extraction job lifecycle status.

    Status transitions:
    - pending: Job created, waiting to start
    - in_progress: Extraction actively running
    - completed: Extraction finished successfully
    - failed: Extraction failed with error
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ExtractionJob(BaseModel):
    """Tracks async extraction job progress.

    Stored in ai_model.extraction_jobs collection.
    Jobs are created when ExtractDocument RPC is called and track
    the progress of PDF/Markdown content extraction.
    """

    id: str = Field(description="MongoDB _id (same as job_id for consistency)")
    job_id: str = Field(description="Unique job identifier (UUID4)")
    document_id: str = Field(description="RAG document ID being extracted")
    status: ExtractionJobStatus = Field(
        default=ExtractionJobStatus.PENDING,
        description="Current job status",
    )
    progress_percent: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Extraction progress (0-100)",
    )
    pages_processed: int = Field(
        default=0,
        ge=0,
        description="Number of pages extracted so far",
    )
    total_pages: int = Field(
        default=0,
        ge=0,
        description="Total pages in document (0 if unknown)",
    )
    error_message: str | None = Field(
        default=None,
        description="Error details if status is failed",
    )
    extraction_method: ExtractionMethod | None = Field(
        default=None,
        description="Method used for extraction (text_extraction, azure_doc_intel, etc.)",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Job creation timestamp",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Job completion timestamp (success or failure)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_id": "disease-diagnosis-guide",
                "status": "in_progress",
                "progress_percent": 45,
                "pages_processed": 9,
                "total_pages": 20,
                "error_message": None,
                "extraction_method": "azure_doc_intel",
                "started_at": "2026-01-07T10:00:00Z",
                "completed_at": None,
            }
        }
    }
