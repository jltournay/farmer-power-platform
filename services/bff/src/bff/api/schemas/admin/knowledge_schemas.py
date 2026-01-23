"""Knowledge Management admin API schemas (Story 9.9a).

Provides request/response schemas for knowledge document management:
- DocumentSummary: List view with basic info
- DocumentDetail: Full detail with metadata and source file info
- DocumentListResponse: Paginated list response
- ExtractionJobStatus: Extraction job polling response
- VectorizationJobStatus: Vectorization job polling response
- ChunkSummary/ChunkListResponse: Chunk listing
- QueryResult/QueryResponse: Knowledge query results
"""

from datetime import datetime
from enum import Enum

from bff.api.schemas.responses import PaginationMeta
from pydantic import BaseModel, Field


class KnowledgeDomain(str, Enum):
    """Knowledge domain categories."""

    plant_diseases = "plant_diseases"
    tea_cultivation = "tea_cultivation"
    weather_patterns = "weather_patterns"
    quality_standards = "quality_standards"
    regional_context = "regional_context"


class DocumentStatus(str, Enum):
    """Document lifecycle status."""

    draft = "draft"
    staged = "staged"
    active = "active"
    archived = "archived"


ALLOWED_FILE_TYPES = {"pdf", "docx", "md", "txt"}
MAX_FILE_SIZE_BYTES = 52_428_800  # 50MB


# =========================================================================
# Request Schemas
# =========================================================================


class CreateDocumentRequest(BaseModel):
    """Request to create a new knowledge document."""

    title: str = Field(description="Document title", min_length=1, max_length=500)
    domain: KnowledgeDomain = Field(description="Knowledge domain")
    content: str = Field(default="", description="Document content (markdown)")
    author: str = Field(default="", description="Document author")
    source: str = Field(default="", description="Original source reference")
    region: str = Field(default="", description="Geographic relevance")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")


class UpdateDocumentRequest(BaseModel):
    """Request to update an existing knowledge document (creates new version)."""

    title: str = Field(default="", description="Updated title (empty = no change)")
    content: str = Field(default="", description="Updated content (empty = no change)")
    author: str = Field(default="", description="Updated author")
    source: str = Field(default="", description="Updated source reference")
    region: str = Field(default="", description="Updated region")
    tags: list[str] = Field(default_factory=list, description="Updated tags")
    change_summary: str = Field(default="", description="Summary of what changed")


class VectorizeDocumentRequest(BaseModel):
    """Request to trigger document vectorization."""

    version: int = Field(default=0, ge=0, description="Version to vectorize (0 = latest)")


class QueryKnowledgeRequest(BaseModel):
    """Request to query the knowledge base."""

    query: str = Field(description="Natural language query text", min_length=1)
    domains: list[KnowledgeDomain] = Field(default_factory=list, description="Domains to search (empty = all)")
    top_k: int = Field(default=5, ge=1, le=100, description="Max results to return")
    confidence_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Min similarity score")


class RollbackDocumentRequest(BaseModel):
    """Request to rollback a document to a previous version."""

    target_version: int = Field(ge=1, description="Version to rollback to")


# =========================================================================
# Response Schemas
# =========================================================================


class SourceFileResponse(BaseModel):
    """Source file information for uploaded documents."""

    filename: str = Field(description="Original filename")
    file_type: str = Field(description="File type (pdf, docx, md, txt)")
    file_size_bytes: int = Field(description="File size in bytes")
    extraction_method: str = Field(default="", description="How content was extracted")
    extraction_confidence: float = Field(default=0.0, description="Extraction quality score (0-1)")
    page_count: int = Field(default=0, description="Number of pages")


class DocumentMetadataResponse(BaseModel):
    """Document metadata in responses."""

    author: str = Field(default="", description="Document author")
    source: str = Field(default="", description="Original source")
    region: str = Field(default="", description="Geographic relevance")
    season: str = Field(default="", description="Seasonal relevance")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")


class DocumentSummary(BaseModel):
    """Knowledge document summary for list views."""

    document_id: str = Field(description="Stable document ID")
    version: int = Field(description="Current version number")
    title: str = Field(description="Document title")
    domain: str = Field(description="Knowledge domain")
    status: str = Field(description="Lifecycle status")
    author: str = Field(default="", description="Document author")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class DocumentDetail(BaseModel):
    """Full knowledge document detail."""

    id: str = Field(description="Unique document ID (document_id:v{version})")
    document_id: str = Field(description="Stable document ID across versions")
    version: int = Field(description="Version number")
    title: str = Field(description="Document title")
    domain: str = Field(description="Knowledge domain")
    content: str = Field(default="", description="Markdown content")
    status: str = Field(description="Lifecycle status")
    metadata: DocumentMetadataResponse = Field(default_factory=DocumentMetadataResponse)
    source_file: SourceFileResponse | None = Field(default=None, description="Source file info if uploaded")
    change_summary: str = Field(default="", description="What changed from previous version")
    pinecone_namespace: str = Field(default="", description="Vector namespace")
    content_hash: str = Field(default="", description="Content hash for change detection")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class DocumentListResponse(BaseModel):
    """Paginated knowledge document list response."""

    data: list[DocumentSummary] = Field(description="List of document summaries")
    pagination: PaginationMeta = Field(description="Pagination metadata")


class ExtractionJobStatus(BaseModel):
    """Extraction job status for polling."""

    job_id: str = Field(description="Job identifier")
    document_id: str = Field(description="Document being extracted")
    status: str = Field(description="Job status: pending, in_progress, completed, failed")
    progress_percent: int = Field(default=0, ge=0, le=100, description="Progress (0-100)")
    pages_processed: int = Field(default=0, description="Pages extracted so far")
    total_pages: int = Field(default=0, description="Total pages in document")
    error_message: str = Field(default="", description="Error details if failed")
    started_at: datetime | None = Field(default=None, description="Job start time")
    completed_at: datetime | None = Field(default=None, description="Job completion time")


class VectorizationJobStatus(BaseModel):
    """Vectorization job status for polling."""

    job_id: str = Field(description="Job identifier")
    status: str = Field(description="Job status: pending, in_progress, completed, failed, partial")
    document_id: str = Field(description="Document being vectorized")
    document_version: int = Field(default=0, description="Document version")
    namespace: str = Field(default="", description="Pinecone namespace")
    chunks_total: int = Field(default=0, description="Total chunks to vectorize")
    chunks_embedded: int = Field(default=0, description="Chunks embedded so far")
    chunks_stored: int = Field(default=0, description="Chunks stored in Pinecone")
    failed_count: int = Field(default=0, description="Failed chunks")
    content_hash: str = Field(default="", description="Content hash on completion")
    error_message: str = Field(default="", description="Error details if failed")
    started_at: datetime | None = Field(default=None, description="Job start time")
    completed_at: datetime | None = Field(default=None, description="Job completion time")


class ChunkSummary(BaseModel):
    """Chunk summary for list views."""

    chunk_id: str = Field(description="Unique chunk identifier")
    document_id: str = Field(description="Parent document ID")
    document_version: int = Field(description="Parent document version")
    chunk_index: int = Field(description="Position in document")
    content: str = Field(description="Chunk text content")
    section_title: str = Field(default="", description="Section heading")
    word_count: int = Field(default=0, description="Word count")
    char_count: int = Field(default=0, description="Character count")
    pinecone_id: str = Field(default="", description="Vector ID if vectorized")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")


class ChunkListResponse(BaseModel):
    """Paginated chunk list response."""

    data: list[ChunkSummary] = Field(description="List of chunks")
    pagination: PaginationMeta = Field(description="Pagination metadata")


class QueryResultItem(BaseModel):
    """Single match from a knowledge query."""

    chunk_id: str = Field(description="Chunk identifier")
    content: str = Field(description="Chunk text content")
    score: float = Field(description="Similarity score (0-1)")
    document_id: str = Field(description="Source document ID")
    title: str = Field(description="Source document title")
    domain: str = Field(description="Knowledge domain")


class QueryResponse(BaseModel):
    """Knowledge query response."""

    matches: list[QueryResultItem] = Field(description="Ranked retrieval matches")
    query: str = Field(description="Original query")
    total_matches: int = Field(default=0, description="Total matches before filtering")
