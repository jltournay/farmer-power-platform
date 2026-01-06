"""Proto-to-Pydantic and dict-to-Pydantic converters for Collection domain.

Provides converters for both:
- Proto -> Pydantic (for gRPC clients like CollectionGrpcClient)
- MongoDB dict -> Pydantic (for direct MongoDB access)

Usage:
    from fp_common.converters import document_from_proto, document_from_dict

    # Convert gRPC response to Pydantic model (Story 0.6.13)
    doc = document_from_proto(grpc_response)

    # Convert MongoDB document to Pydantic model
    doc = document_from_dict(mongo_doc)

Reference:
- Pydantic models: fp_common/models/document.py
- Proto definition: proto/collection/v1/collection.proto
- MongoDB schema: collection_model.domain.document_index
"""

from datetime import UTC, datetime
from typing import Any

from fp_proto.collection.v1 import collection_pb2
from google.protobuf.timestamp_pb2 import Timestamp

from fp_common.models import (
    Document,
    ExtractionMetadata,
    IngestionMetadata,
    RawDocumentRef,
    SearchResult,
)


def _proto_timestamp_to_datetime(ts: Timestamp) -> datetime:
    """Convert protobuf Timestamp to Python datetime.

    Args:
        ts: Protobuf Timestamp message.

    Returns:
        Timezone-aware datetime (UTC).

    Note:
        Returns current UTC time if timestamp is empty (seconds=0, nanos=0).
    """
    if ts.seconds == 0 and ts.nanos == 0:
        return datetime.now(UTC)
    return ts.ToDatetime(tzinfo=UTC)


def document_from_proto(proto: collection_pb2.Document) -> Document:
    """Convert proto Document to Pydantic Document model.

    Story 0.6.13: Used by CollectionGrpcClient for typed responses.

    Args:
        proto: Proto Document message from Collection Model gRPC.

    Returns:
        Document Pydantic model.

    Note:
        Proto map<string, string> fields are converted to Python dict.
        Proto Timestamps are converted to timezone-aware datetime (UTC).
    """
    return Document(
        document_id=proto.document_id,
        raw_document=RawDocumentRef(
            blob_container=proto.raw_document.blob_container,
            blob_path=proto.raw_document.blob_path,
            content_hash=proto.raw_document.content_hash,
            size_bytes=proto.raw_document.size_bytes,
            stored_at=_proto_timestamp_to_datetime(proto.raw_document.stored_at),
        ),
        extraction=ExtractionMetadata(
            ai_agent_id=proto.extraction.ai_agent_id,
            extraction_timestamp=_proto_timestamp_to_datetime(proto.extraction.extraction_timestamp),
            confidence=proto.extraction.confidence,
            validation_passed=proto.extraction.validation_passed,
            validation_warnings=list(proto.extraction.validation_warnings),
        ),
        ingestion=IngestionMetadata(
            ingestion_id=proto.ingestion.ingestion_id,
            source_id=proto.ingestion.source_id,
            received_at=_proto_timestamp_to_datetime(proto.ingestion.received_at),
            processed_at=_proto_timestamp_to_datetime(proto.ingestion.processed_at),
        ),
        extracted_fields=dict(proto.extracted_fields),
        linkage_fields=dict(proto.linkage_fields),
        created_at=_proto_timestamp_to_datetime(proto.created_at),
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
