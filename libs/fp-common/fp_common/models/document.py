"""Document domain models for MCP servers.

These models are shared across MCP servers for typed document responses.
They mirror the DocumentIndex structure from collection-model but are
optimized for MCP consumption and validation at service boundaries.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RawDocumentRef(BaseModel):
    """Reference to raw document in blob storage.

    Attributes:
        blob_container: Azure Blob Storage container name.
        blob_path: Path to the blob within container.
        content_hash: SHA-256 hash of the content.
        size_bytes: Size of the content in bytes.
        stored_at: When the raw document was stored.
    """

    blob_container: str = Field(description="Azure Blob Storage container name")
    blob_path: str = Field(description="Path to the blob within container")
    content_hash: str = Field(description="SHA-256 hash of the content")
    size_bytes: int = Field(ge=0, description="Size of the content in bytes")
    stored_at: datetime = Field(description="When the raw document was stored")


class ExtractionMetadata(BaseModel):
    """Metadata about the AI Model extraction.

    Attributes:
        ai_agent_id: AI Model agent ID used for extraction.
        extraction_timestamp: When extraction was performed.
        confidence: Confidence score of the extraction.
        validation_passed: Whether extraction passed validation.
        validation_warnings: List of validation warnings.
    """

    ai_agent_id: str = Field(description="AI Model agent ID used for extraction")
    extraction_timestamp: datetime = Field(description="When extraction was performed")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score of the extraction")
    validation_passed: bool = Field(default=True, description="Whether extraction passed validation")
    validation_warnings: list[str] = Field(default_factory=list, description="List of validation warnings")


class IngestionMetadata(BaseModel):
    """Metadata about the ingestion process.

    Attributes:
        ingestion_id: ID of the ingestion job.
        source_id: ID of the source configuration.
        received_at: When the blob was received via Event Grid.
        processed_at: When processing completed.
    """

    ingestion_id: str = Field(description="ID of the ingestion job")
    source_id: str = Field(description="ID of the source configuration")
    received_at: datetime = Field(description="When the blob was received via Event Grid")
    processed_at: datetime = Field(description="When processing completed")


class Document(BaseModel):
    """Document model for MCP server responses.

    This is the typed Pydantic model returned by MCP tools like
    get_documents(), get_document_by_id(), etc. It replaces the
    dict[str, Any] anti-pattern with proper type safety.

    Attributes:
        document_id: Unique identifier for this document.
        raw_document: Reference to the raw document in blob storage.
        extraction: Metadata about the AI extraction.
        ingestion: Metadata about the ingestion process.
        extracted_fields: Extracted fields from AI Model (stored as-is).
        linkage_fields: Dynamic fields for indexing.
        created_at: When the document was created.
    """

    document_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this document",
    )
    raw_document: RawDocumentRef = Field(description="Reference to the raw document in blob storage")
    extraction: ExtractionMetadata = Field(description="Metadata about the AI extraction")
    ingestion: IngestionMetadata = Field(description="Metadata about the ingestion process")
    extracted_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted fields from AI Model (stored as-is)",
    )
    linkage_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Dynamic fields for indexing (from transformation.extract_fields)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the document was created",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "document_id": "doc-12345",
                "raw_document": {
                    "blob_container": "quality-data",
                    "blob_path": "factory-001/2025-12-28/batch-001.json",
                    "content_hash": "sha256:abc123...",
                    "size_bytes": 1024,
                    "stored_at": "2025-12-28T10:00:00Z",
                },
                "extraction": {
                    "ai_agent_id": "qc-extractor-v1",
                    "extraction_timestamp": "2025-12-28T10:00:05Z",
                    "confidence": 0.95,
                    "validation_passed": True,
                    "validation_warnings": [],
                },
                "ingestion": {
                    "ingestion_id": "ing-001",
                    "source_id": "qc-analyzer-result",
                    "received_at": "2025-12-28T10:00:00Z",
                    "processed_at": "2025-12-28T10:00:05Z",
                },
                "extracted_fields": {
                    "farmer_id": "WM-0001",
                    "grade": "Primary",
                    "weight_kg": 25.5,
                },
                "linkage_fields": {
                    "farmer_id": "WM-0001",
                },
                "created_at": "2025-12-28T10:00:05Z",
            },
        },
    }


class SearchResult(BaseModel):
    """Search result with relevance scoring.

    Returned by search_documents() MCP tool. Includes all Document
    fields plus a relevance_score for ranking results.

    Attributes:
        document_id: Unique identifier for this document.
        raw_document: Reference to the raw document in blob storage.
        extraction: Metadata about the AI extraction.
        ingestion: Metadata about the ingestion process.
        extracted_fields: Extracted fields from AI Model.
        linkage_fields: Dynamic fields for indexing.
        created_at: When the document was created.
        relevance_score: Relevance score for search ranking (0.0 to 1.0).
    """

    document_id: str = Field(description="Unique identifier for this document")
    raw_document: RawDocumentRef = Field(description="Reference to the raw document in blob storage")
    extraction: ExtractionMetadata = Field(description="Metadata about the AI extraction")
    ingestion: IngestionMetadata = Field(description="Metadata about the ingestion process")
    extracted_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted fields from AI Model",
    )
    linkage_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Dynamic fields for indexing",
    )
    created_at: datetime = Field(description="When the document was created")
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        default=1.0,
        description="Relevance score for search ranking (0.0 to 1.0)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "document_id": "doc-12345",
                "raw_document": {
                    "blob_container": "quality-data",
                    "blob_path": "factory-001/2025-12-28/batch-001.json",
                    "content_hash": "sha256:abc123...",
                    "size_bytes": 1024,
                    "stored_at": "2025-12-28T10:00:00Z",
                },
                "extraction": {
                    "ai_agent_id": "qc-extractor-v1",
                    "extraction_timestamp": "2025-12-28T10:00:05Z",
                    "confidence": 0.95,
                    "validation_passed": True,
                    "validation_warnings": [],
                },
                "ingestion": {
                    "ingestion_id": "ing-001",
                    "source_id": "qc-analyzer-result",
                    "received_at": "2025-12-28T10:00:00Z",
                    "processed_at": "2025-12-28T10:00:05Z",
                },
                "extracted_fields": {
                    "farmer_id": "WM-0001",
                    "grade": "Primary",
                },
                "linkage_fields": {
                    "farmer_id": "WM-0001",
                },
                "created_at": "2025-12-28T10:00:05Z",
                "relevance_score": 0.85,
            },
        },
    }
