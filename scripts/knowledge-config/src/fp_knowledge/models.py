"""CLI-specific models for RAG document management.

These models are used for YAML input validation and CLI display.
They map to/from gRPC messages in the client module.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeDomain(str, Enum):
    """Valid knowledge domains for RAG documents."""

    PLANT_DISEASES = "plant_diseases"
    TEA_CULTIVATION = "tea_cultivation"
    WEATHER_PATTERNS = "weather_patterns"
    QUALITY_STANDARDS = "quality_standards"
    REGIONAL_CONTEXT = "regional_context"


class DocumentStatus(str, Enum):
    """Document lifecycle status.

    Status transitions:
    - draft: Initial creation, content being developed
    - staged: Ready for review, awaiting activation
    - active: Currently in use (only one per document_id)
    - archived: Historical version, kept for audit/rollback
    """

    DRAFT = "draft"
    STAGED = "staged"
    ACTIVE = "active"
    ARCHIVED = "archived"


class DocumentMetadata(BaseModel):
    """Metadata for a RAG document."""

    author: str = Field(description="Agronomist who created/updated the document")
    source: str | None = Field(
        default=None,
        description="Original source (book, research paper, etc.)",
    )
    region: str | None = Field(
        default=None,
        description="Geographic relevance (e.g., 'Kenya', 'Rwanda')",
    )
    season: str | None = Field(
        default=None,
        description="Seasonal relevance (e.g., 'dry_season', 'monsoon')",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Searchable tags for filtering",
    )


class SourceFileInfo(BaseModel):
    """Information about an uploaded source file (PDF, MD, etc.)."""

    filename: str = Field(description="Original filename")
    file_type: str = Field(description="File type: pdf, docx, md, txt")
    blob_path: str | None = Field(
        default=None,
        description="Azure Blob path to original file",
    )
    file_size_bytes: int | None = Field(
        default=None,
        description="File size in bytes",
    )
    extraction_method: str | None = Field(
        default=None,
        description="Extraction method used (text_extraction, azure_doc_intel, etc.)",
    )
    extraction_confidence: float | None = Field(
        default=None,
        description="Extraction quality score (0-1)",
    )
    page_count: int | None = Field(
        default=None,
        description="Number of pages in document",
    )


class RagDocumentInput(BaseModel):
    """Input model for YAML document files.

    This model validates YAML input for the deploy/stage commands.
    """

    document_id: str = Field(
        description="Stable document ID (e.g., 'blister-blight-guide')"
    )
    title: str = Field(description="Document title for display")
    domain: KnowledgeDomain = Field(description="Knowledge domain")
    content: str | None = Field(
        default=None,
        description="Document content (markdown text) - mutually exclusive with file",
    )
    file: str | None = Field(
        default=None,
        description="Path to source file (PDF, MD) - mutually exclusive with content",
    )
    metadata: DocumentMetadata = Field(
        default_factory=lambda: DocumentMetadata(author="unknown"),
        description="Document metadata",
    )

    def has_content_or_file(self) -> bool:
        """Check if either content or file is provided."""
        return bool(self.content) or bool(self.file)


class RagDocument(BaseModel):
    """RAG document model for display and operations.

    Maps from gRPC RAGDocument message.
    """

    id: str = Field(description="Unique document ID (format: {document_id}:v{version})")
    document_id: str = Field(description="Stable ID across versions")
    version: int = Field(description="Incrementing version number")
    title: str = Field(description="Document title for display")
    domain: str = Field(description="Knowledge domain")
    content: str = Field(description="Extracted/authored markdown text content")
    status: DocumentStatus = Field(description="Document lifecycle status")
    metadata: DocumentMetadata = Field(description="Document metadata")
    source_file: SourceFileInfo | None = Field(
        default=None,
        description="Original file reference if uploaded",
    )
    change_summary: str | None = Field(
        default=None,
        description="What changed from previous version",
    )
    created_at: datetime | None = Field(
        default=None,
        description="Creation timestamp",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp",
    )
    content_hash: str | None = Field(
        default=None,
        description="SHA256 hash for change detection",
    )

    model_config = {"extra": "ignore"}


class JobStatus(str, Enum):
    """Extraction/chunking job status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class VectorizationJobStatus(str, Enum):
    """Vectorization job status (Story 0.75.13c)."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some chunks succeeded, some failed


class ExtractionJobResult(BaseModel):
    """Result of an extraction job query."""

    job_id: str = Field(description="Unique job identifier")
    document_id: str = Field(description="RAG document being extracted")
    status: JobStatus = Field(description="Job status")
    progress_percent: int = Field(default=0, description="Extraction progress (0-100)")
    pages_processed: int = Field(default=0, description="Pages extracted so far")
    total_pages: int = Field(default=0, description="Total pages in document")
    error_message: str | None = Field(
        default=None,
        description="Error details if status is failed",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Job start timestamp",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Job completion timestamp",
    )


class ChunkResult(BaseModel):
    """Result of chunking operation."""

    chunks_created: int = Field(description="Number of chunks created")
    total_char_count: int = Field(description="Total character count")
    total_word_count: int = Field(description="Total word count")


class RagChunk(BaseModel):
    """Individual chunk of a RAG document."""

    chunk_id: str = Field(description="Unique chunk identifier")
    document_id: str = Field(description="Parent document ID")
    document_version: int = Field(description="Parent document version")
    chunk_index: int = Field(description="Position in document (0-indexed)")
    content: str = Field(description="Chunk text content")
    section_title: str | None = Field(
        default=None,
        description="Heading this chunk belongs to",
    )
    word_count: int = Field(description="Word count for statistics")
    char_count: int = Field(description="Character count for statistics")
    created_at: datetime | None = Field(
        default=None,
        description="Creation timestamp",
    )
    pinecone_id: str | None = Field(
        default=None,
        description="Vector ID in Pinecone after vectorization",
    )


class OperationResult(BaseModel):
    """Generic result for CLI operations."""

    success: bool = Field(description="Whether the operation succeeded")
    message: str | None = Field(default=None, description="Success/info message")
    error: str | None = Field(default=None, description="Error message if failed")
    data: dict[str, Any] | None = Field(default=None, description="Additional data")


class VectorizationResult(BaseModel):
    """Result of vectorization operation (Story 0.75.13c)."""

    job_id: str = Field(description="Unique job identifier")
    status: VectorizationJobStatus = Field(description="Job status")
    namespace: str | None = Field(default=None, description="Pinecone namespace")
    chunks_total: int = Field(default=0, description="Total chunks to process")
    chunks_embedded: int = Field(
        default=0, description="Chunks with embeddings generated"
    )
    chunks_stored: int = Field(default=0, description="Chunks stored in Pinecone")
    failed_count: int = Field(default=0, description="Number of failed chunks")
    content_hash: str | None = Field(
        default=None, description="Content hash for change detection"
    )
    error_message: str | None = Field(
        default=None, description="Error details if failed"
    )


class VectorizationJobResult(BaseModel):
    """Full result of a vectorization job query (Story 0.75.13c)."""

    job_id: str = Field(description="Unique job identifier")
    status: VectorizationJobStatus = Field(description="Job status")
    document_id: str = Field(description="RAG document being vectorized")
    document_version: int = Field(description="Document version")
    namespace: str | None = Field(default=None, description="Pinecone namespace")
    chunks_total: int = Field(default=0, description="Total chunks to process")
    chunks_embedded: int = Field(
        default=0, description="Chunks with embeddings generated"
    )
    chunks_stored: int = Field(default=0, description="Chunks stored in Pinecone")
    failed_count: int = Field(default=0, description="Number of failed chunks")
    content_hash: str | None = Field(
        default=None, description="Content hash for change detection"
    )
    error_message: str | None = Field(
        default=None, description="Error details if failed"
    )
    started_at: datetime | None = Field(default=None, description="Job start time")
    completed_at: datetime | None = Field(default=None, description="Job end time")
