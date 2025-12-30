"""Generic document index models for storing extracted data.

This module defines the DocumentIndex model which is a generic model
for storing extracted data from ANY source type. The collection name
is determined by source_config.storage.index_collection.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from fp_common.models.source_config import SourceConfig


class RawDocumentRef(BaseModel):
    """Reference to raw document in blob storage.

    Attributes:
        blob_container: Azure Blob Storage container name.
        blob_path: Path to the blob within container.
        content_hash: SHA-256 hash of the content.
        size_bytes: Size of the content in bytes.
        stored_at: When the raw document was stored.
    """

    blob_container: str
    blob_path: str
    content_hash: str
    size_bytes: int
    stored_at: datetime


class ExtractionMetadata(BaseModel):
    """Metadata about the AI Model extraction.

    Attributes:
        ai_agent_id: AI Model agent ID used for extraction.
        extraction_timestamp: When extraction was performed.
        confidence: Confidence score of the extraction.
        validation_passed: Whether extraction passed validation.
        validation_warnings: List of validation warnings.
    """

    ai_agent_id: str
    extraction_timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    validation_passed: bool = True
    validation_warnings: list[str] = Field(default_factory=list)


class IngestionMetadata(BaseModel):
    """Metadata about the ingestion process.

    Attributes:
        ingestion_id: ID of the ingestion job.
        source_id: ID of the source configuration.
        received_at: When the blob was received via Event Grid.
        processed_at: When processing completed.
    """

    ingestion_id: str
    source_id: str
    received_at: datetime
    processed_at: datetime


class DocumentIndex(BaseModel):
    """Generic document index for ANY source type.

    Stores extracted fields as-is from AI Model.
    NO business logic - Collection Model only collects and extracts.
    Stored in collection specified by source_config.storage.index_collection.

    Attributes:
        document_id: Unique identifier for this document.
        raw_document: Reference to the raw document in blob storage.
        extraction: Metadata about the AI extraction.
        ingestion: Metadata about the ingestion process.
        extracted_fields: Extracted fields from AI Model (stored as-is).
        linkage_fields: Dynamic fields for indexing (from transformation.extract_fields).
        created_at: When the document was created.
    """

    document_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this document",
    )
    raw_document: RawDocumentRef
    extraction: ExtractionMetadata
    ingestion: IngestionMetadata
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

    @classmethod
    def from_extraction(
        cls,
        raw_document: RawDocumentRef,
        extraction: ExtractionMetadata,
        ingestion: IngestionMetadata,
        extracted_fields: dict[str, Any],
        source_config: "SourceConfig",
    ) -> "DocumentIndex":
        """Create a DocumentIndex from extraction results.

        Automatically populates linkage_fields from extracted_fields
        based on transformation.extract_fields in source config.

        Args:
            raw_document: Reference to the raw document.
            extraction: Extraction metadata.
            ingestion: Ingestion metadata.
            extracted_fields: Fields extracted by AI Model.
            source_config: Typed SourceConfig for field mapping.

        Returns:
            New DocumentIndex instance.
        """
        # Use typed attribute access from SourceConfig Pydantic model
        transformation = source_config.transformation
        extract_field_names = transformation.extract_fields or []
        field_mappings = transformation.field_mappings or {}

        # Build linkage_fields by copying specified fields
        linkage = {}
        for field_name in extract_field_names:
            if field_name in extracted_fields:
                # Apply field mapping if exists
                mapped_name = field_mappings.get(field_name, field_name)
                linkage[mapped_name] = extracted_fields[field_name]

        return cls(
            raw_document=raw_document,
            extraction=extraction,
            ingestion=ingestion,
            extracted_fields=extracted_fields,
            linkage_fields=linkage,
        )
