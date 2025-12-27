"""Raw document model for storing blob references with content hashes.

This module defines the RawDocument model used to track raw documents
stored in Azure Blob Storage with deduplication via content hash.
"""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class RawDocument(BaseModel):
    """Reference to a raw document stored in blob storage.

    Stores metadata about the original blob including content hash
    for deduplication purposes.

    Attributes:
        document_id: Unique identifier for this raw document.
        source_id: ID of the source configuration.
        ingestion_id: ID of the ingestion job that created this document.
        blob_container: Azure Blob Storage container name.
        blob_path: Path to the blob within the container.
        content_hash: SHA-256 hash of the content for deduplication.
        content_type: MIME type of the content.
        size_bytes: Size of the content in bytes.
        stored_at: When the document was stored.
        metadata: Additional metadata from path extraction.
    """

    document_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this raw document",
    )
    source_id: str = Field(..., description="ID of the source configuration")
    ingestion_id: str = Field(..., description="ID of the ingestion job")
    blob_container: str = Field(..., description="Azure Blob Storage container name")
    blob_path: str = Field(..., description="Path to the blob within container")
    content_hash: str = Field(..., description="SHA-256 hash for deduplication")
    content_type: str = Field(
        default="application/octet-stream",
        description="MIME type of the content",
    )
    size_bytes: int = Field(default=0, description="Size of the content in bytes")
    stored_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the document was stored",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata from path extraction",
    )
