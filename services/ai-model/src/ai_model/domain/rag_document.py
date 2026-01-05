"""RAG Document domain models for AI Model service.

This module defines the Pydantic models for RAG document storage with versioning.
RAG documents are stored in the ai_model.rag_documents MongoDB collection.

Key design decisions (see architecture/ai-model-architecture/rag-document-api.md):
- Documents are versioned via document_id + version combination
- Status lifecycle: draft → staged → active → archived
- SourceFile tracks PDF extraction metadata
- RagChunk stores individual chunks for vectorization (separate collection)
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class RagDocumentStatus(str, Enum):
    """RAG document lifecycle status.

    Status transitions:
    - draft: Initial state, content being prepared
    - staged: Ready for review/A/B testing
    - active: Currently in use for RAG queries
    - archived: Historical version, kept for audit

    Transition flow: draft → staged → active → archived
    """

    DRAFT = "draft"
    STAGED = "staged"
    ACTIVE = "active"
    ARCHIVED = "archived"


class KnowledgeDomain(str, Enum):
    """Knowledge domains for RAG documents.

    Documents are categorized by domain to enable filtered retrieval
    and domain-specific relevance scoring.
    """

    PLANT_DISEASES = "plant_diseases"
    TEA_CULTIVATION = "tea_cultivation"
    WEATHER_PATTERNS = "weather_patterns"
    QUALITY_STANDARDS = "quality_standards"
    REGIONAL_CONTEXT = "regional_context"


class ExtractionMethod(str, Enum):
    """PDF extraction method used to extract content.

    Determines how the document content was extracted from source file:
    - manual: User typed content directly
    - text_extraction: PyMuPDF for digital PDFs (fast, free)
    - azure_doc_intel: Azure Document Intelligence for scanned/complex PDFs
    - vision_llm: Vision LLM for diagrams/tables (highest cost)
    """

    MANUAL = "manual"
    TEXT_EXTRACTION = "text_extraction"
    AZURE_DOC_INTEL = "azure_doc_intel"
    VISION_LLM = "vision_llm"


class FileType(str, Enum):
    """Supported file types for RAG document sources."""

    PDF = "pdf"
    DOCX = "docx"
    MD = "md"
    TXT = "txt"


class SourceFile(BaseModel):
    """Original uploaded file reference (for PDF/DOCX uploads).

    Tracks the original file and extraction metadata for auditing
    and potential re-extraction.
    """

    filename: str = Field(description="Original filename (e.g., 'blister-blight-guide.pdf')")
    file_type: Literal["pdf", "docx", "md", "txt"] = Field(description="File type indicator")
    blob_path: str = Field(description="Azure Blob path to original file")
    file_size_bytes: int = Field(ge=0, description="File size in bytes")
    extraction_method: ExtractionMethod | None = Field(
        default=None,
        description="Method used to extract content from file",
    )
    extraction_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Extraction quality score (0-1)",
    )
    page_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of pages in document",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "filename": "blister-blight-guide.pdf",
                "file_type": "pdf",
                "blob_path": "rag-documents/disease-guide/v1/blister-blight-guide.pdf",
                "file_size_bytes": 245760,
                "extraction_method": "azure_doc_intel",
                "extraction_confidence": 0.96,
                "page_count": 15,
            }
        }
    }


class RAGDocumentMetadata(BaseModel):
    """Metadata for RAG document.

    Stores authorship, source information, and searchable tags
    for filtering and relevance scoring.
    """

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

    model_config = {
        "json_schema_extra": {
            "example": {
                "author": "Dr. Wanjiku",
                "source": "Kenya Tea Research Foundation",
                "region": "Kenya",
                "season": None,
                "tags": ["blister-blight", "fungal", "treatment"],
            }
        }
    }


class RagChunk(BaseModel):
    """Individual chunk of a RAG document for vectorization.

    RagChunks are stored in a separate collection (ai_model.rag_chunks)
    and reference their parent document. This model is defined here
    but the repository will be implemented in Story 0.75.10d.
    """

    chunk_id: str = Field(description="Unique chunk identifier")
    document_id: str = Field(description="Parent document ID reference")
    document_version: int = Field(ge=1, description="Parent document version")
    chunk_index: int = Field(ge=0, description="Position in document (0-indexed)")
    content: str = Field(description="Chunk text content")
    section_title: str | None = Field(
        default=None,
        description="Heading this chunk belongs to",
    )
    word_count: int = Field(ge=0, description="Word count for statistics")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    pinecone_id: str | None = Field(
        default=None,
        description="Vector ID after vectorization",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "chunk_id": "disease-guide-v1-chunk-0",
                "document_id": "disease-diagnosis-guide",
                "document_version": 1,
                "chunk_index": 0,
                "content": "# Blister Blight\n\nBlister blight is caused by...",
                "section_title": "Blister Blight",
                "word_count": 150,
                "created_at": "2026-01-05T10:00:00Z",
                "pinecone_id": "disease-diagnosis-guide-0",
            }
        }
    }


class RagDocument(BaseModel):
    """RAG knowledge document for expert knowledge storage.

    Documents are stored in the ai_model.rag_documents collection.
    Each document has a unique combination of (document_id, version).

    Key relationships:
    - document_id: Stable ID across versions (e.g., "disease-diagnosis-guide")
    - version: Incrementing version number for tracking changes
    """

    id: str = Field(description="Unique document ID (format: {document_id}:v{version})")
    document_id: str = Field(description="Stable ID across versions (e.g., 'disease-diagnosis-guide')")
    version: int = Field(
        default=1,
        ge=1,
        description="Incrementing version number",
    )
    title: str = Field(description="Document title for display")
    domain: KnowledgeDomain = Field(
        description="Knowledge domain for categorization",
    )
    content: str = Field(description="Extracted/authored markdown text content")
    source_file: SourceFile | None = Field(
        default=None,
        description="Original file reference if uploaded as PDF/DOCX",
    )
    status: RagDocumentStatus = Field(
        default=RagDocumentStatus.DRAFT,
        description="Document lifecycle status",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )
    metadata: RAGDocumentMetadata = Field(
        description="Document metadata for filtering and attribution",
    )
    change_summary: str | None = Field(
        default=None,
        description="What changed from previous version",
    )
    pinecone_namespace: str | None = Field(
        default=None,
        description="Pinecone namespace (e.g., 'knowledge-v12')",
    )
    pinecone_ids: list[str] = Field(
        default_factory=list,
        description="Vector IDs in Pinecone after vectorization",
    )
    content_hash: str | None = Field(
        default=None,
        description="SHA256 hash for change detection",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "disease-diagnosis-guide:v3",
                "document_id": "disease-diagnosis-guide",
                "version": 3,
                "title": "Blister Blight Treatment Guide",
                "domain": "plant_diseases",
                "content": "# Blister Blight\n\nBlister blight is caused by...",
                "status": "active",
                "source_file": {
                    "filename": "blister-blight-guide.pdf",
                    "file_type": "pdf",
                    "blob_path": "rag-documents/disease-guide/v3/blister-blight.pdf",
                    "file_size_bytes": 245760,
                    "extraction_method": "azure_doc_intel",
                    "extraction_confidence": 0.96,
                    "page_count": 15,
                },
                "metadata": {
                    "author": "Dr. Wanjiku",
                    "source": "Kenya Tea Research Foundation",
                    "region": "Kenya",
                    "season": None,
                    "tags": ["blister-blight", "fungal", "treatment"],
                },
                "change_summary": "Added new treatment protocol for resistant strains",
                "created_at": "2026-01-05T10:00:00Z",
                "updated_at": "2026-01-05T10:00:00Z",
                "pinecone_namespace": "knowledge-v3",
                "pinecone_ids": ["disease-diagnosis-guide-0", "disease-diagnosis-guide-1"],
                "content_hash": "sha256:abc123...",
            }
        }
    }
