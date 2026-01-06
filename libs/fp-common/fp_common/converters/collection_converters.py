"""MongoDB dict-to-Pydantic converters for Collection domain.

Unlike Plantation converters (Proto -> Pydantic), these convert
MongoDB document dicts to Pydantic models.

Usage:
    from fp_common.converters import document_from_dict, search_result_from_dict

    # Convert MongoDB document to Pydantic model
    doc = document_from_dict(mongo_doc)
    result = search_result_from_dict(search_doc)

Reference:
- Pydantic models: fp_common/models/document.py
- MongoDB schema: collection_model.domain.document_index
"""

from datetime import UTC, datetime
from typing import Any

from fp_common.models import (
    Document,
    ExtractionMetadata,
    IngestionMetadata,
    RawDocumentRef,
    SearchResult,
)


def _parse_datetime(value: Any, default: datetime | None = None) -> datetime:
    """Parse datetime from various formats.

    Args:
        value: Value to parse (datetime, str, or None).
        default: Default datetime if value is None/empty.

    Returns:
        Parsed datetime or default.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        # Handle ISO format strings
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return default or datetime.now(UTC)


def document_from_dict(doc: dict[str, Any]) -> Document:
    """Convert MongoDB document dict to Document Pydantic model.

    Args:
        doc: MongoDB document from quality_documents collection.

    Returns:
        Document Pydantic model.

    Note:
        MongoDB stores documents with nested raw_document, extraction,
        ingestion structures per Document schema in fp_common.models.
    """
    raw = doc.get("raw_document", {})
    ext = doc.get("extraction", {})
    ing = doc.get("ingestion", {})

    return Document(
        document_id=doc.get("document_id", ""),
        raw_document=RawDocumentRef(
            blob_container=raw.get("blob_container", ""),
            blob_path=raw.get("blob_path", ""),
            content_hash=raw.get("content_hash", ""),
            size_bytes=raw.get("size_bytes", 0),
            stored_at=_parse_datetime(raw.get("stored_at")),
        ),
        extraction=ExtractionMetadata(
            ai_agent_id=ext.get("ai_agent_id", ""),
            extraction_timestamp=_parse_datetime(ext.get("extraction_timestamp")),
            confidence=ext.get("confidence", 0.0),
            validation_passed=ext.get("validation_passed", True),
            validation_warnings=ext.get("validation_warnings", []),
        ),
        ingestion=IngestionMetadata(
            ingestion_id=ing.get("ingestion_id", ""),
            source_id=ing.get("source_id", ""),
            received_at=_parse_datetime(ing.get("received_at")),
            processed_at=_parse_datetime(ing.get("processed_at")),
        ),
        extracted_fields=doc.get("extracted_fields", {}),
        linkage_fields=doc.get("linkage_fields", {}),
        created_at=_parse_datetime(doc.get("created_at")),
    )


def search_result_from_dict(doc: dict[str, Any]) -> SearchResult:
    """Convert MongoDB search result to SearchResult Pydantic model.

    Args:
        doc: MongoDB document with optional relevance_score from text search.

    Returns:
        SearchResult with document fields + relevance_score.
    """
    raw = doc.get("raw_document", {})
    ext = doc.get("extraction", {})
    ing = doc.get("ingestion", {})

    return SearchResult(
        document_id=doc.get("document_id", ""),
        raw_document=RawDocumentRef(
            blob_container=raw.get("blob_container", ""),
            blob_path=raw.get("blob_path", ""),
            content_hash=raw.get("content_hash", ""),
            size_bytes=raw.get("size_bytes", 0),
            stored_at=_parse_datetime(raw.get("stored_at")),
        ),
        extraction=ExtractionMetadata(
            ai_agent_id=ext.get("ai_agent_id", ""),
            extraction_timestamp=_parse_datetime(ext.get("extraction_timestamp")),
            confidence=ext.get("confidence", 0.0),
            validation_passed=ext.get("validation_passed", True),
            validation_warnings=ext.get("validation_warnings", []),
        ),
        ingestion=IngestionMetadata(
            ingestion_id=ing.get("ingestion_id", ""),
            source_id=ing.get("source_id", ""),
            received_at=_parse_datetime(ing.get("received_at")),
            processed_at=_parse_datetime(ing.get("processed_at")),
        ),
        extracted_fields=doc.get("extracted_fields", {}),
        linkage_fields=doc.get("linkage_fields", {}),
        created_at=_parse_datetime(doc.get("created_at")),
        relevance_score=doc.get("relevance_score", 1.0),
    )
