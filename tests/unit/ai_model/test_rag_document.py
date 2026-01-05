"""Unit tests for RAG Document domain models.

Tests cover:
- RagDocumentStatus enum values
- KnowledgeDomain enum values
- ExtractionMethod enum values
- SourceFile model validation
- RAGDocumentMetadata model validation
- RagChunk model validation
- RagDocument model validation (complete model)
- RagDocument model serialization (model_dump)
- RagDocument model deserialization (model_validate)
- Invalid field rejection tests
"""

from datetime import UTC, datetime

import pytest
from ai_model.domain.rag_document import (
    ExtractionMethod,
    KnowledgeDomain,
    RagChunk,
    RagDocument,
    RAGDocumentMetadata,
    RagDocumentStatus,
    SourceFile,
)
from pydantic import ValidationError


class TestRagDocumentStatus:
    """Tests for RagDocumentStatus enum."""

    def test_status_has_draft_value(self) -> None:
        """Draft status exists and has correct value."""
        assert RagDocumentStatus.DRAFT.value == "draft"

    def test_status_has_staged_value(self) -> None:
        """Staged status exists and has correct value."""
        assert RagDocumentStatus.STAGED.value == "staged"

    def test_status_has_active_value(self) -> None:
        """Active status exists and has correct value."""
        assert RagDocumentStatus.ACTIVE.value == "active"

    def test_status_has_archived_value(self) -> None:
        """Archived status exists and has correct value."""
        assert RagDocumentStatus.ARCHIVED.value == "archived"

    def test_status_is_string_enum(self) -> None:
        """Status values are strings for MongoDB compatibility."""
        for status in RagDocumentStatus:
            assert isinstance(status.value, str)


class TestKnowledgeDomain:
    """Tests for KnowledgeDomain enum."""

    def test_domain_has_all_expected_values(self) -> None:
        """All expected knowledge domains are defined."""
        expected_domains = [
            "plant_diseases",
            "tea_cultivation",
            "weather_patterns",
            "quality_standards",
            "regional_context",
        ]
        actual_domains = [d.value for d in KnowledgeDomain]
        assert set(actual_domains) == set(expected_domains)

    def test_domain_is_string_enum(self) -> None:
        """Domain values are strings for MongoDB compatibility."""
        for domain in KnowledgeDomain:
            assert isinstance(domain.value, str)


class TestExtractionMethod:
    """Tests for ExtractionMethod enum."""

    def test_extraction_method_has_all_values(self) -> None:
        """All expected extraction methods are defined."""
        expected_methods = ["manual", "text_extraction", "azure_doc_intel", "vision_llm"]
        actual_methods = [m.value for m in ExtractionMethod]
        assert set(actual_methods) == set(expected_methods)


class TestSourceFile:
    """Tests for SourceFile model."""

    def test_source_file_with_required_fields(self) -> None:
        """SourceFile can be created with required fields only."""
        source = SourceFile(
            filename="guide.pdf",
            file_type="pdf",
            blob_path="rag-documents/guide.pdf",
            file_size_bytes=1024,
        )
        assert source.filename == "guide.pdf"
        assert source.file_type == "pdf"
        assert source.blob_path == "rag-documents/guide.pdf"
        assert source.file_size_bytes == 1024
        assert source.extraction_method is None
        assert source.extraction_confidence is None
        assert source.page_count is None

    def test_source_file_with_all_fields(self) -> None:
        """SourceFile can be created with all fields."""
        source = SourceFile(
            filename="guide.pdf",
            file_type="pdf",
            blob_path="rag-documents/guide.pdf",
            file_size_bytes=245760,
            extraction_method=ExtractionMethod.AZURE_DOC_INTEL,
            extraction_confidence=0.96,
            page_count=15,
        )
        assert source.extraction_method == ExtractionMethod.AZURE_DOC_INTEL
        assert source.extraction_confidence == 0.96
        assert source.page_count == 15

    def test_source_file_rejects_negative_file_size(self) -> None:
        """SourceFile rejects negative file size."""
        with pytest.raises(ValidationError) as exc_info:
            SourceFile(
                filename="test.pdf",
                file_type="pdf",
                blob_path="path/test.pdf",
                file_size_bytes=-100,
            )
        assert "file_size_bytes" in str(exc_info.value)

    def test_source_file_rejects_invalid_confidence(self) -> None:
        """SourceFile rejects confidence outside 0-1 range."""
        with pytest.raises(ValidationError) as exc_info:
            SourceFile(
                filename="test.pdf",
                file_type="pdf",
                blob_path="path/test.pdf",
                file_size_bytes=1024,
                extraction_confidence=1.5,
            )
        assert "extraction_confidence" in str(exc_info.value)


class TestRAGDocumentMetadata:
    """Tests for RAGDocumentMetadata model."""

    def test_metadata_with_required_fields(self) -> None:
        """Metadata can be created with required fields only."""
        metadata = RAGDocumentMetadata(author="Dr. Wanjiku")
        assert metadata.author == "Dr. Wanjiku"
        assert metadata.source is None
        assert metadata.region is None
        assert metadata.season is None
        assert metadata.tags == []

    def test_metadata_with_all_fields(self) -> None:
        """Metadata can be created with all fields."""
        metadata = RAGDocumentMetadata(
            author="Dr. Wanjiku",
            source="Kenya Tea Research Foundation",
            region="Kenya",
            season="dry_season",
            tags=["blister-blight", "fungal"],
        )
        assert metadata.source == "Kenya Tea Research Foundation"
        assert metadata.region == "Kenya"
        assert metadata.season == "dry_season"
        assert metadata.tags == ["blister-blight", "fungal"]

    def test_metadata_requires_author(self) -> None:
        """Metadata requires author field."""
        with pytest.raises(ValidationError) as exc_info:
            RAGDocumentMetadata()  # type: ignore[call-arg]
        assert "author" in str(exc_info.value)


class TestRagChunk:
    """Tests for RagChunk model."""

    def test_chunk_with_required_fields(self) -> None:
        """RagChunk can be created with required fields."""
        chunk = RagChunk(
            chunk_id="doc-v1-chunk-0",
            document_id="disease-guide",
            document_version=1,
            chunk_index=0,
            content="Blister blight is caused by the fungus...",
            word_count=25,
        )
        assert chunk.chunk_id == "doc-v1-chunk-0"
        assert chunk.document_id == "disease-guide"
        assert chunk.document_version == 1
        assert chunk.chunk_index == 0
        assert chunk.section_title is None
        assert chunk.pinecone_id is None

    def test_chunk_with_all_fields(self) -> None:
        """RagChunk can be created with all fields."""
        now = datetime.now(UTC)
        chunk = RagChunk(
            chunk_id="doc-v1-chunk-0",
            document_id="disease-guide",
            document_version=1,
            chunk_index=0,
            content="Blister blight content...",
            section_title="Blister Blight",
            word_count=50,
            created_at=now,
            pinecone_id="disease-guide-0",
        )
        assert chunk.section_title == "Blister Blight"
        assert chunk.pinecone_id == "disease-guide-0"
        assert chunk.created_at == now

    def test_chunk_rejects_negative_version(self) -> None:
        """RagChunk rejects version less than 1."""
        with pytest.raises(ValidationError) as exc_info:
            RagChunk(
                chunk_id="chunk-0",
                document_id="doc",
                document_version=0,
                chunk_index=0,
                content="Content",
                word_count=1,
            )
        assert "document_version" in str(exc_info.value)

    def test_chunk_rejects_negative_index(self) -> None:
        """RagChunk rejects negative chunk index."""
        with pytest.raises(ValidationError) as exc_info:
            RagChunk(
                chunk_id="chunk-0",
                document_id="doc",
                document_version=1,
                chunk_index=-1,
                content="Content",
                word_count=1,
            )
        assert "chunk_index" in str(exc_info.value)


class TestRagDocument:
    """Tests for RagDocument model."""

    @pytest.fixture
    def valid_document_data(self) -> dict:
        """Provide valid RAG document data for tests."""
        return {
            "id": "disease-guide:v1",
            "document_id": "disease-guide",
            "version": 1,
            "title": "Blister Blight Treatment Guide",
            "domain": KnowledgeDomain.PLANT_DISEASES,
            "content": "# Blister Blight\n\nBlister blight is caused by...",
            "metadata": {
                "author": "Dr. Wanjiku",
                "tags": ["blister-blight", "fungal"],
            },
        }

    def test_document_with_required_fields(self, valid_document_data: dict) -> None:
        """RagDocument can be created with required fields."""
        doc = RagDocument(**valid_document_data)

        assert doc.id == "disease-guide:v1"
        assert doc.document_id == "disease-guide"
        assert doc.version == 1
        assert doc.title == "Blister Blight Treatment Guide"
        assert doc.domain == KnowledgeDomain.PLANT_DISEASES
        assert doc.status == RagDocumentStatus.DRAFT  # Default

    def test_document_defaults_to_draft_status(self, valid_document_data: dict) -> None:
        """RagDocument defaults to draft status."""
        doc = RagDocument(**valid_document_data)
        assert doc.status == RagDocumentStatus.DRAFT

    def test_document_with_source_file(self, valid_document_data: dict) -> None:
        """RagDocument can include source file reference."""
        valid_document_data["source_file"] = {
            "filename": "blister-blight.pdf",
            "file_type": "pdf",
            "blob_path": "rag-documents/blister-blight.pdf",
            "file_size_bytes": 245760,
            "extraction_method": "azure_doc_intel",
            "extraction_confidence": 0.96,
            "page_count": 15,
        }

        doc = RagDocument(**valid_document_data)

        assert doc.source_file is not None
        assert doc.source_file.filename == "blister-blight.pdf"
        assert doc.source_file.extraction_confidence == 0.96

    def test_document_serialization_model_dump(self, valid_document_data: dict) -> None:
        """RagDocument can be serialized with model_dump()."""
        doc = RagDocument(**valid_document_data)
        data = doc.model_dump()

        assert data["id"] == "disease-guide:v1"
        assert data["document_id"] == "disease-guide"
        assert data["domain"] == "plant_diseases"  # Enum serialized to string
        assert data["status"] == "draft"  # Enum serialized to string
        assert isinstance(data["metadata"], dict)

    def test_document_deserialization_model_validate(self) -> None:
        """RagDocument can be deserialized with model_validate()."""
        raw_data = {
            "id": "weather-guide:v2",
            "document_id": "weather-guide",
            "version": 2,
            "title": "Weather Patterns Guide",
            "domain": "weather_patterns",  # String, not enum
            "content": "Weather content...",
            "status": "active",  # String, not enum
            "metadata": {
                "author": "Operations",
            },
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }

        doc = RagDocument.model_validate(raw_data)

        assert doc.document_id == "weather-guide"
        assert doc.domain == KnowledgeDomain.WEATHER_PATTERNS
        assert doc.status == RagDocumentStatus.ACTIVE

    def test_document_rejects_invalid_domain(self, valid_document_data: dict) -> None:
        """RagDocument rejects invalid domain value."""
        valid_document_data["domain"] = "invalid_domain"

        with pytest.raises(ValidationError) as exc_info:
            RagDocument(**valid_document_data)
        assert "domain" in str(exc_info.value)

    def test_document_rejects_invalid_status(self, valid_document_data: dict) -> None:
        """RagDocument rejects invalid status value."""
        valid_document_data["status"] = "invalid_status"

        with pytest.raises(ValidationError) as exc_info:
            RagDocument(**valid_document_data)
        assert "status" in str(exc_info.value)

    def test_document_rejects_version_less_than_one(self, valid_document_data: dict) -> None:
        """RagDocument rejects version less than 1."""
        valid_document_data["version"] = 0

        with pytest.raises(ValidationError) as exc_info:
            RagDocument(**valid_document_data)
        assert "version" in str(exc_info.value)

    def test_document_requires_id(self) -> None:
        """RagDocument requires id field."""
        with pytest.raises(ValidationError) as exc_info:
            RagDocument(
                document_id="test",
                title="Test",
                domain=KnowledgeDomain.PLANT_DISEASES,
                content="Content",
                metadata=RAGDocumentMetadata(author="test"),
            )  # type: ignore[call-arg]
        assert "id" in str(exc_info.value)

    def test_document_requires_document_id(self) -> None:
        """RagDocument requires document_id field."""
        with pytest.raises(ValidationError) as exc_info:
            RagDocument(
                id="test:v1",
                title="Test",
                domain=KnowledgeDomain.PLANT_DISEASES,
                content="Content",
                metadata=RAGDocumentMetadata(author="test"),
            )  # type: ignore[call-arg]
        assert "document_id" in str(exc_info.value)
