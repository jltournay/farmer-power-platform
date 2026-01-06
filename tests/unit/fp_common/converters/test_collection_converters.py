"""Unit tests for collection_converters module.

Tests verify conversion correctness including:
- Proto -> Pydantic (document_from_proto) for gRPC clients (Story 0.6.13)
- MongoDB dict -> Pydantic (document_from_dict) for direct access
- Nested structure handling
- Datetime/Timestamp parsing
- Optional field defaults
- Round-trip validation
"""

from datetime import UTC, datetime

from fp_common.converters import document_from_dict, document_from_proto, search_result_from_dict
from fp_common.models import Document, SearchResult
from fp_proto.collection.v1 import collection_pb2
from google.protobuf.timestamp_pb2 import Timestamp


def _datetime_to_timestamp(dt: datetime) -> Timestamp:
    """Helper to convert datetime to protobuf Timestamp."""
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


class TestDocumentFromProto:
    """Tests for document_from_proto converter.

    Story 0.6.13: Proto -> Pydantic conversion for gRPC clients.
    """

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped from proto."""
        now = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)

        proto = collection_pb2.Document(
            document_id="doc-proto-001",
            raw_document=collection_pb2.RawDocumentRef(
                blob_container="quality-data",
                blob_path="factory-001/2026-01-06/batch-001.json",
                content_hash="sha256:proto123",
                size_bytes=2048,
                stored_at=_datetime_to_timestamp(now),
            ),
            extraction=collection_pb2.ExtractionMetadata(
                ai_agent_id="qc-extractor-v2",
                extraction_timestamp=_datetime_to_timestamp(now),
                confidence=0.97,
                validation_passed=True,
                validation_warnings=["minor"],
            ),
            ingestion=collection_pb2.IngestionMetadata(
                ingestion_id="ing-proto-001",
                source_id="qc-analyzer-result",
                received_at=_datetime_to_timestamp(now),
                processed_at=_datetime_to_timestamp(now),
            ),
            extracted_fields={"farmer_id": "WM-0001", "grade": "Primary"},
            linkage_fields={"farmer_id": "WM-0001"},
            created_at=_datetime_to_timestamp(now),
        )

        doc = document_from_proto(proto)

        assert isinstance(doc, Document)
        assert doc.document_id == "doc-proto-001"
        assert doc.raw_document.blob_container == "quality-data"
        assert doc.raw_document.blob_path == "factory-001/2026-01-06/batch-001.json"
        assert doc.raw_document.content_hash == "sha256:proto123"
        assert doc.raw_document.size_bytes == 2048
        assert doc.extraction.ai_agent_id == "qc-extractor-v2"
        assert doc.extraction.confidence == 0.97
        assert doc.extraction.validation_passed is True
        assert doc.extraction.validation_warnings == ["minor"]
        assert doc.ingestion.source_id == "qc-analyzer-result"
        assert doc.extracted_fields["farmer_id"] == "WM-0001"
        assert doc.linkage_fields["farmer_id"] == "WM-0001"

    def test_timestamp_conversion(self):
        """Proto timestamps are correctly converted to datetime."""
        specific_time = datetime(2026, 1, 6, 14, 30, 45, tzinfo=UTC)

        proto = collection_pb2.Document(
            document_id="doc-timestamp-test",
            raw_document=collection_pb2.RawDocumentRef(
                blob_container="c",
                blob_path="p",
                content_hash="h",
                size_bytes=100,
                stored_at=_datetime_to_timestamp(specific_time),
            ),
            extraction=collection_pb2.ExtractionMetadata(
                ai_agent_id="agent",
                extraction_timestamp=_datetime_to_timestamp(specific_time),
                confidence=0.9,
                validation_passed=True,
            ),
            ingestion=collection_pb2.IngestionMetadata(
                ingestion_id="i",
                source_id="s",
                received_at=_datetime_to_timestamp(specific_time),
                processed_at=_datetime_to_timestamp(specific_time),
            ),
            created_at=_datetime_to_timestamp(specific_time),
        )

        doc = document_from_proto(proto)

        assert doc.raw_document.stored_at == specific_time
        assert doc.extraction.extraction_timestamp == specific_time
        assert doc.ingestion.received_at == specific_time
        assert doc.ingestion.processed_at == specific_time
        assert doc.created_at == specific_time

    def test_empty_timestamps_default_to_now(self):
        """Empty proto timestamps default to current time."""
        proto = collection_pb2.Document(
            document_id="doc-empty-ts",
            raw_document=collection_pb2.RawDocumentRef(
                blob_container="c",
                blob_path="p",
                content_hash="h",
                size_bytes=100,
                # stored_at not set -> defaults to empty Timestamp
            ),
            extraction=collection_pb2.ExtractionMetadata(
                ai_agent_id="agent",
                # extraction_timestamp not set
                confidence=0.9,
                validation_passed=True,
            ),
            ingestion=collection_pb2.IngestionMetadata(
                ingestion_id="i",
                source_id="s",
                # received_at and processed_at not set
            ),
            # created_at not set
        )

        doc = document_from_proto(proto)

        # All timestamps should be datetime objects (defaulting to now)
        assert isinstance(doc.raw_document.stored_at, datetime)
        assert isinstance(doc.extraction.extraction_timestamp, datetime)
        assert isinstance(doc.ingestion.received_at, datetime)
        assert isinstance(doc.ingestion.processed_at, datetime)
        assert isinstance(doc.created_at, datetime)

    def test_map_fields_converted_to_dict(self):
        """Proto map<string, string> fields are converted to dict."""
        now = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)

        proto = collection_pb2.Document(
            document_id="doc-maps",
            raw_document=collection_pb2.RawDocumentRef(
                blob_container="c",
                blob_path="p",
                content_hash="h",
                size_bytes=100,
                stored_at=_datetime_to_timestamp(now),
            ),
            extraction=collection_pb2.ExtractionMetadata(
                ai_agent_id="a",
                extraction_timestamp=_datetime_to_timestamp(now),
                confidence=0.9,
                validation_passed=True,
            ),
            ingestion=collection_pb2.IngestionMetadata(
                ingestion_id="i",
                source_id="s",
                received_at=_datetime_to_timestamp(now),
                processed_at=_datetime_to_timestamp(now),
            ),
            extracted_fields={
                "farmer_id": "WM-0001",
                "factory_id": "KEN-FAC-001",
                "grading_model_id": "tbk-kenya-v1",
            },
            linkage_fields={
                "farmer_id": "WM-0001",
                "region_id": "nyeri-highland",
            },
            created_at=_datetime_to_timestamp(now),
        )

        doc = document_from_proto(proto)

        assert isinstance(doc.extracted_fields, dict)
        assert isinstance(doc.linkage_fields, dict)
        assert doc.extracted_fields["farmer_id"] == "WM-0001"
        assert doc.extracted_fields["factory_id"] == "KEN-FAC-001"
        assert doc.extracted_fields["grading_model_id"] == "tbk-kenya-v1"
        assert doc.linkage_fields["farmer_id"] == "WM-0001"
        assert doc.linkage_fields["region_id"] == "nyeri-highland"

    def test_validation_warnings_list(self):
        """Proto repeated string field is converted to list."""
        now = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)

        proto = collection_pb2.Document(
            document_id="doc-warnings",
            raw_document=collection_pb2.RawDocumentRef(
                blob_container="c",
                blob_path="p",
                content_hash="h",
                size_bytes=100,
                stored_at=_datetime_to_timestamp(now),
            ),
            extraction=collection_pb2.ExtractionMetadata(
                ai_agent_id="agent",
                extraction_timestamp=_datetime_to_timestamp(now),
                confidence=0.75,
                validation_passed=False,
                validation_warnings=["warning1", "warning2", "warning3"],
            ),
            ingestion=collection_pb2.IngestionMetadata(
                ingestion_id="i",
                source_id="s",
                received_at=_datetime_to_timestamp(now),
                processed_at=_datetime_to_timestamp(now),
            ),
            created_at=_datetime_to_timestamp(now),
        )

        doc = document_from_proto(proto)

        assert isinstance(doc.extraction.validation_warnings, list)
        assert doc.extraction.validation_warnings == ["warning1", "warning2", "warning3"]
        assert doc.extraction.validation_passed is False


class TestDocumentFromDict:
    """Tests for document_from_dict converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        mongo_doc = {
            "document_id": "doc-12345",
            "raw_document": {
                "blob_container": "quality-data",
                "blob_path": "factory-001/2025-12-28/batch-001.json",
                "content_hash": "sha256:abc123",
                "size_bytes": 1024,
                "stored_at": datetime(2025, 12, 28, 10, 0, 0, tzinfo=UTC),
            },
            "extraction": {
                "ai_agent_id": "qc-extractor-v1",
                "extraction_timestamp": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
                "confidence": 0.95,
                "validation_passed": True,
                "validation_warnings": [],
            },
            "ingestion": {
                "ingestion_id": "ing-001",
                "source_id": "qc-analyzer-result",
                "received_at": datetime(2025, 12, 28, 10, 0, 0, tzinfo=UTC),
                "processed_at": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
            },
            "extracted_fields": {
                "farmer_id": "WM-0001",
                "grade": "Primary",
                "weight_kg": 25.5,
            },
            "linkage_fields": {
                "farmer_id": "WM-0001",
            },
            "created_at": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
        }

        doc = document_from_dict(mongo_doc)

        assert isinstance(doc, Document)
        assert doc.document_id == "doc-12345"
        assert doc.raw_document.blob_container == "quality-data"
        assert doc.raw_document.blob_path == "factory-001/2025-12-28/batch-001.json"
        assert doc.extraction.ai_agent_id == "qc-extractor-v1"
        assert doc.extraction.confidence == 0.95
        assert doc.ingestion.source_id == "qc-analyzer-result"
        assert doc.extracted_fields["farmer_id"] == "WM-0001"
        assert doc.extracted_fields["grade"] == "Primary"
        assert doc.linkage_fields["farmer_id"] == "WM-0001"

    def test_nested_raw_document(self):
        """Nested raw_document structure is correctly extracted."""
        mongo_doc = {
            "document_id": "doc-001",
            "raw_document": {
                "blob_container": "test-container",
                "blob_path": "test/path.json",
                "content_hash": "sha256:xyz789",
                "size_bytes": 2048,
                "stored_at": datetime(2025, 12, 28, 12, 0, 0, tzinfo=UTC),
            },
            "extraction": {
                "ai_agent_id": "test-agent",
                "extraction_timestamp": datetime(2025, 12, 28, 12, 0, 5, tzinfo=UTC),
                "confidence": 0.85,
                "validation_passed": True,
                "validation_warnings": ["minor warning"],
            },
            "ingestion": {
                "ingestion_id": "ing-test",
                "source_id": "test-source",
                "received_at": datetime(2025, 12, 28, 12, 0, 0, tzinfo=UTC),
                "processed_at": datetime(2025, 12, 28, 12, 0, 5, tzinfo=UTC),
            },
            "extracted_fields": {},
            "linkage_fields": {},
            "created_at": datetime(2025, 12, 28, 12, 0, 5, tzinfo=UTC),
        }

        doc = document_from_dict(mongo_doc)

        assert doc.raw_document.blob_container == "test-container"
        assert doc.raw_document.blob_path == "test/path.json"
        assert doc.raw_document.content_hash == "sha256:xyz789"
        assert doc.raw_document.size_bytes == 2048
        assert doc.raw_document.stored_at == datetime(2025, 12, 28, 12, 0, 0, tzinfo=UTC)

    def test_nested_extraction_metadata(self):
        """Nested extraction metadata is correctly extracted."""
        mongo_doc = {
            "document_id": "doc-002",
            "raw_document": {
                "blob_container": "c",
                "blob_path": "p",
                "content_hash": "h",
                "size_bytes": 100,
                "stored_at": datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            },
            "extraction": {
                "ai_agent_id": "my-agent-v2",
                "extraction_timestamp": datetime(2025, 12, 28, 14, 30, 0, tzinfo=UTC),
                "confidence": 0.78,
                "validation_passed": False,
                "validation_warnings": ["field missing", "confidence low"],
            },
            "ingestion": {
                "ingestion_id": "i",
                "source_id": "s",
                "received_at": datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                "processed_at": datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            },
            "extracted_fields": {},
            "linkage_fields": {},
            "created_at": datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        }

        doc = document_from_dict(mongo_doc)

        assert doc.extraction.ai_agent_id == "my-agent-v2"
        assert doc.extraction.extraction_timestamp == datetime(2025, 12, 28, 14, 30, 0, tzinfo=UTC)
        assert doc.extraction.confidence == 0.78
        assert doc.extraction.validation_passed is False
        assert doc.extraction.validation_warnings == ["field missing", "confidence low"]

    def test_datetime_parsing_from_string(self):
        """Datetime strings are correctly parsed."""
        mongo_doc = {
            "document_id": "doc-003",
            "raw_document": {
                "blob_container": "c",
                "blob_path": "p",
                "content_hash": "h",
                "size_bytes": 100,
                "stored_at": "2025-12-28T10:00:00+00:00",  # ISO string
            },
            "extraction": {
                "ai_agent_id": "agent",
                "extraction_timestamp": "2025-12-28T10:00:05Z",  # ISO string with Z
                "confidence": 0.9,
                "validation_passed": True,
                "validation_warnings": [],
            },
            "ingestion": {
                "ingestion_id": "i",
                "source_id": "s",
                "received_at": "2025-12-28T10:00:00Z",
                "processed_at": "2025-12-28T10:00:05Z",
            },
            "extracted_fields": {},
            "linkage_fields": {},
            "created_at": "2025-12-28T10:00:05+00:00",
        }

        doc = document_from_dict(mongo_doc)

        # Verify datetimes were parsed correctly
        assert isinstance(doc.raw_document.stored_at, datetime)
        assert isinstance(doc.extraction.extraction_timestamp, datetime)
        assert isinstance(doc.ingestion.received_at, datetime)
        assert isinstance(doc.created_at, datetime)

    def test_missing_optional_fields_use_defaults(self):
        """Missing optional fields use appropriate defaults."""
        # Minimal document with empty nested structures
        mongo_doc = {
            "document_id": "doc-minimal",
            "raw_document": {},
            "extraction": {},
            "ingestion": {},
            "extracted_fields": {},
            "linkage_fields": {},
        }

        doc = document_from_dict(mongo_doc)

        assert doc.document_id == "doc-minimal"
        # Raw document defaults
        assert doc.raw_document.blob_container == ""
        assert doc.raw_document.blob_path == ""
        assert doc.raw_document.size_bytes == 0
        # Extraction defaults
        assert doc.extraction.ai_agent_id == ""
        assert doc.extraction.confidence == 0.0
        assert doc.extraction.validation_passed is True
        assert doc.extraction.validation_warnings == []
        # Ingestion defaults
        assert doc.ingestion.ingestion_id == ""
        assert doc.ingestion.source_id == ""

    def test_extracted_fields_preserved(self):
        """Extracted fields dict is preserved as-is."""
        mongo_doc = {
            "document_id": "doc-fields",
            "raw_document": {"blob_container": "", "blob_path": "", "content_hash": "", "size_bytes": 0},
            "extraction": {"ai_agent_id": "", "confidence": 0.0, "validation_passed": True, "validation_warnings": []},
            "ingestion": {"ingestion_id": "", "source_id": ""},
            "extracted_fields": {
                "farmer_id": "WM-1234",
                "grade": "Secondary",
                "weight_kg": 15.5,
                "nested": {"key": "value"},
                "list_field": [1, 2, 3],
            },
            "linkage_fields": {"farmer_id": "WM-1234", "batch_id": "BATCH-001"},
            "created_at": datetime.now(UTC),
        }

        doc = document_from_dict(mongo_doc)

        assert doc.extracted_fields["farmer_id"] == "WM-1234"
        assert doc.extracted_fields["grade"] == "Secondary"
        assert doc.extracted_fields["weight_kg"] == 15.5
        assert doc.extracted_fields["nested"]["key"] == "value"
        assert doc.extracted_fields["list_field"] == [1, 2, 3]
        assert doc.linkage_fields["farmer_id"] == "WM-1234"
        assert doc.linkage_fields["batch_id"] == "BATCH-001"


class TestSearchResultFromDict:
    """Tests for search_result_from_dict converter."""

    def test_basic_fields_with_relevance(self):
        """Basic fields and relevance score are correctly mapped."""
        mongo_doc = {
            "document_id": "search-result-001",
            "raw_document": {
                "blob_container": "search-data",
                "blob_path": "result.json",
                "content_hash": "sha256:search123",
                "size_bytes": 512,
                "stored_at": datetime(2025, 12, 28, 10, 0, 0, tzinfo=UTC),
            },
            "extraction": {
                "ai_agent_id": "search-agent",
                "extraction_timestamp": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
                "confidence": 0.92,
                "validation_passed": True,
                "validation_warnings": [],
            },
            "ingestion": {
                "ingestion_id": "search-ing-001",
                "source_id": "search-source",
                "received_at": datetime(2025, 12, 28, 10, 0, 0, tzinfo=UTC),
                "processed_at": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
            },
            "extracted_fields": {"query_match": "tea quality"},
            "linkage_fields": {},
            "created_at": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
            "relevance_score": 0.85,  # Search-specific field
        }

        result = search_result_from_dict(mongo_doc)

        assert isinstance(result, SearchResult)
        assert result.document_id == "search-result-001"
        assert result.relevance_score == 0.85
        assert result.raw_document.blob_container == "search-data"
        assert result.extraction.ai_agent_id == "search-agent"

    def test_default_relevance_score(self):
        """Default relevance score is 1.0 when not provided."""
        mongo_doc = {
            "document_id": "no-score-doc",
            "raw_document": {"blob_container": "", "blob_path": "", "content_hash": "", "size_bytes": 0},
            "extraction": {"ai_agent_id": "", "confidence": 0.0, "validation_passed": True, "validation_warnings": []},
            "ingestion": {"ingestion_id": "", "source_id": ""},
            "extracted_fields": {},
            "linkage_fields": {},
            "created_at": datetime.now(UTC),
            # No relevance_score field
        }

        result = search_result_from_dict(mongo_doc)

        assert result.relevance_score == 1.0  # Default

    def test_inherits_document_fields(self):
        """SearchResult has all Document fields."""
        mongo_doc = {
            "document_id": "full-search-doc",
            "raw_document": {
                "blob_container": "test",
                "blob_path": "test/path.json",
                "content_hash": "hash123",
                "size_bytes": 999,
                "stored_at": datetime(2025, 12, 28, 10, 0, 0, tzinfo=UTC),
            },
            "extraction": {
                "ai_agent_id": "agent123",
                "extraction_timestamp": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
                "confidence": 0.99,
                "validation_passed": True,
                "validation_warnings": ["warning1"],
            },
            "ingestion": {
                "ingestion_id": "ing123",
                "source_id": "src123",
                "received_at": datetime(2025, 12, 28, 10, 0, 0, tzinfo=UTC),
                "processed_at": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
            },
            "extracted_fields": {"key": "value"},
            "linkage_fields": {"link_key": "link_value"},
            "created_at": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
            "relevance_score": 0.75,
        }

        result = search_result_from_dict(mongo_doc)

        # All Document fields should be present
        assert result.document_id == "full-search-doc"
        assert result.raw_document.blob_container == "test"
        assert result.raw_document.size_bytes == 999
        assert result.extraction.confidence == 0.99
        assert result.extraction.validation_warnings == ["warning1"]
        assert result.ingestion.source_id == "src123"
        assert result.extracted_fields["key"] == "value"
        assert result.linkage_fields["link_key"] == "link_value"
        # Plus the relevance_score
        assert result.relevance_score == 0.75


class TestRoundTrip:
    """Tests for round-trip conversion."""

    def test_document_round_trip(self):
        """Dict -> Pydantic -> dict produces expected structure."""
        mongo_doc = {
            "document_id": "round-trip-001",
            "raw_document": {
                "blob_container": "quality-data",
                "blob_path": "factory-001/batch.json",
                "content_hash": "sha256:abc",
                "size_bytes": 1024,
                "stored_at": datetime(2025, 12, 28, 10, 0, 0, tzinfo=UTC),
            },
            "extraction": {
                "ai_agent_id": "extractor",
                "extraction_timestamp": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
                "confidence": 0.95,
                "validation_passed": True,
                "validation_warnings": [],
            },
            "ingestion": {
                "ingestion_id": "ing-001",
                "source_id": "qc-result",
                "received_at": datetime(2025, 12, 28, 10, 0, 0, tzinfo=UTC),
                "processed_at": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
            },
            "extracted_fields": {"grade": "Primary", "weight_kg": 25.0},
            "linkage_fields": {"farmer_id": "WM-0001"},
            "created_at": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
        }

        doc = document_from_dict(mongo_doc)
        data = doc.model_dump()

        # Verify key fields in dict
        assert data["document_id"] == "round-trip-001"
        assert data["raw_document"]["blob_container"] == "quality-data"
        assert data["extraction"]["confidence"] == 0.95
        assert data["ingestion"]["source_id"] == "qc-result"
        assert data["extracted_fields"]["grade"] == "Primary"
        assert data["linkage_fields"]["farmer_id"] == "WM-0001"

    def test_search_result_round_trip(self):
        """Dict -> Pydantic -> dict preserves relevance_score."""
        mongo_doc = {
            "document_id": "search-round-trip",
            "raw_document": {
                "blob_container": "data",
                "blob_path": "path.json",
                "content_hash": "hash",
                "size_bytes": 100,
                "stored_at": datetime(2025, 12, 28, 10, 0, 0, tzinfo=UTC),
            },
            "extraction": {
                "ai_agent_id": "agent",
                "extraction_timestamp": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
                "confidence": 0.9,
                "validation_passed": True,
                "validation_warnings": [],
            },
            "ingestion": {
                "ingestion_id": "i",
                "source_id": "s",
                "received_at": datetime(2025, 12, 28, 10, 0, 0, tzinfo=UTC),
                "processed_at": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
            },
            "extracted_fields": {},
            "linkage_fields": {},
            "created_at": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
            "relevance_score": 0.87,
        }

        result = search_result_from_dict(mongo_doc)
        data = result.model_dump()

        assert data["document_id"] == "search-round-trip"
        assert data["relevance_score"] == 0.87
