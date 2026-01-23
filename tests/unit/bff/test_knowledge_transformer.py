"""Unit tests for KnowledgeTransformer (Story 9.9a - Task 7.2)."""

from unittest.mock import MagicMock

import pytest
from bff.transformers.admin.knowledge_transformer import KnowledgeTransformer
from google.protobuf.timestamp_pb2 import Timestamp


@pytest.fixture
def transformer():
    return KnowledgeTransformer()


def _make_timestamp(seconds: int = 1700000000) -> Timestamp:
    ts = Timestamp()
    ts.seconds = seconds
    return ts


def _make_mock_document(
    document_id="test-doc-1",
    version=1,
    title="Test Document",
    domain="plant_diseases",
    content="Some content",
    status="draft",
    has_metadata=True,
    has_source_file=False,
):
    doc = MagicMock()
    doc.id = f"{document_id}:v{version}"
    doc.document_id = document_id
    doc.version = version
    doc.title = title
    doc.domain = domain
    doc.content = content
    doc.status = status
    doc.change_summary = "Initial version"
    doc.pinecone_namespace = ""
    doc.content_hash = "abc123"
    doc.created_at = _make_timestamp()
    doc.updated_at = _make_timestamp(1700001000)

    if has_metadata:
        doc.HasField = lambda f: f in ("metadata",) or (f == "source_file" and has_source_file)
        doc.metadata.author = "Dr. Tea Expert"
        doc.metadata.source = "Research Paper"
        doc.metadata.region = "Kenya"
        doc.metadata.season = "dry_season"
        doc.metadata.tags = ["tea", "disease"]
    else:
        doc.HasField = lambda f: f == "source_file" and has_source_file

    if has_source_file:
        doc.HasField = lambda f: f in ("metadata", "source_file") if has_metadata else f == "source_file"
        doc.source_file.filename = "guide.pdf"
        doc.source_file.file_type = "pdf"
        doc.source_file.file_size_bytes = 1024000
        doc.source_file.extraction_method = "azure_doc_intel"
        doc.source_file.extraction_confidence = 0.95
        doc.source_file.page_count = 12
    else:
        if not has_metadata:
            doc.HasField = lambda f: False

    return doc


class TestToSummary:
    def test_basic_summary(self, transformer):
        doc = _make_mock_document()
        result = transformer.to_summary(doc)

        assert result.document_id == "test-doc-1"
        assert result.version == 1
        assert result.title == "Test Document"
        assert result.domain == "plant_diseases"
        assert result.status == "draft"
        assert result.author == "Dr. Tea Expert"
        assert result.created_at is not None
        assert result.updated_at is not None

    def test_summary_without_metadata(self, transformer):
        doc = _make_mock_document(has_metadata=False)
        result = transformer.to_summary(doc)
        assert result.author == ""


class TestToDetail:
    def test_full_detail(self, transformer):
        doc = _make_mock_document(has_source_file=True)
        result = transformer.to_detail(doc)

        assert result.id == "test-doc-1:v1"
        assert result.document_id == "test-doc-1"
        assert result.version == 1
        assert result.title == "Test Document"
        assert result.content == "Some content"
        assert result.status == "draft"
        assert result.metadata.author == "Dr. Tea Expert"
        assert result.metadata.region == "Kenya"
        assert result.metadata.tags == ["tea", "disease"]
        assert result.source_file is not None
        assert result.source_file.filename == "guide.pdf"
        assert result.source_file.file_type == "pdf"
        assert result.source_file.page_count == 12

    def test_detail_without_source_file(self, transformer):
        doc = _make_mock_document(has_source_file=False)
        result = transformer.to_detail(doc)
        assert result.source_file is None

    def test_detail_without_metadata(self, transformer):
        doc = _make_mock_document(has_metadata=False, has_source_file=False)
        result = transformer.to_detail(doc)
        assert result.metadata.author == ""
        assert result.metadata.tags == []


class TestToExtractionStatus:
    def test_extraction_status(self, transformer):
        job = MagicMock()
        job.job_id = "job-123"
        job.document_id = "doc-1"
        job.status = "in_progress"
        job.progress_percent = 45
        job.pages_processed = 5
        job.total_pages = 12
        job.error_message = ""
        job.started_at = _make_timestamp()
        job.completed_at = Timestamp()  # zero = not completed

        result = transformer.to_extraction_status(job)

        assert result.job_id == "job-123"
        assert result.document_id == "doc-1"
        assert result.status == "in_progress"
        assert result.progress_percent == 45
        assert result.pages_processed == 5
        assert result.total_pages == 12
        assert result.started_at is not None
        assert result.completed_at is None  # zero timestamp


class TestToVectorizationStatus:
    def test_vectorization_status(self, transformer):
        job = MagicMock()
        job.job_id = "vec-456"
        job.status = "completed"
        job.document_id = "doc-2"
        job.document_version = 3
        job.namespace = "knowledge-v3"
        job.chunks_total = 20
        job.chunks_embedded = 20
        job.chunks_stored = 20
        job.failed_count = 0
        job.content_hash = "hash123"
        job.error_message = ""
        job.started_at = _make_timestamp()
        job.completed_at = _make_timestamp(1700002000)

        result = transformer.to_vectorization_status(job)

        assert result.job_id == "vec-456"
        assert result.status == "completed"
        assert result.chunks_total == 20
        assert result.chunks_stored == 20
        assert result.failed_count == 0


class TestToChunkSummary:
    def test_chunk_summary(self, transformer):
        chunk = MagicMock()
        chunk.chunk_id = "doc-1-v1-chunk-0"
        chunk.document_id = "doc-1"
        chunk.document_version = 1
        chunk.chunk_index = 0
        chunk.content = "This is chunk content"
        chunk.section_title = "Introduction"
        chunk.word_count = 4
        chunk.char_count = 21
        chunk.pinecone_id = "vec-001"
        chunk.created_at = _make_timestamp()

        result = transformer.to_chunk_summary(chunk)

        assert result.chunk_id == "doc-1-v1-chunk-0"
        assert result.chunk_index == 0
        assert result.section_title == "Introduction"
        assert result.word_count == 4


class TestToQueryResult:
    def test_query_result(self, transformer):
        match = MagicMock()
        match.chunk_id = "chunk-abc"
        match.content = "Blister blight treatment..."
        match.score = 0.92
        match.document_id = "disease-guide"
        match.title = "Blister Blight Guide"
        match.domain = "plant_diseases"

        result = transformer.to_query_result(match)

        assert result.chunk_id == "chunk-abc"
        assert result.score == 0.92
        assert result.title == "Blister Blight Guide"
        assert result.domain == "plant_diseases"
