"""Unit tests for AdminKnowledgeService (Story 9.9a - Task 7.1)."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from bff.api.schemas.admin.knowledge_schemas import (
    ChunkListResponse,
    DeleteDocumentResponse,
    DocumentDetail,
    DocumentListResponse,
    DocumentSummary,
    ExtractionJobStatus,
    QueryResponse,
    VectorizationJobStatus,
)
from bff.services.admin.knowledge_service import AdminKnowledgeService
from fastapi import HTTPException, UploadFile
from google.protobuf.timestamp_pb2 import Timestamp


def _make_timestamp(seconds: int = 1700000000) -> Timestamp:
    ts = Timestamp()
    ts.seconds = seconds
    return ts


def _make_mock_doc(document_id="test-doc", version=1, status="draft"):
    doc = MagicMock()
    doc.id = f"{document_id}:v{version}"
    doc.document_id = document_id
    doc.version = version
    doc.title = "Test Document"
    doc.domain = "plant_diseases"
    doc.content = "Content here"
    doc.status = status
    doc.change_summary = ""
    doc.pinecone_namespace = ""
    doc.content_hash = ""
    doc.created_at = _make_timestamp()
    doc.updated_at = _make_timestamp()
    doc.HasField = lambda f: f == "metadata"
    doc.metadata.author = "Author"
    doc.metadata.source = ""
    doc.metadata.region = ""
    doc.metadata.season = ""
    doc.metadata.tags = []
    return doc


@pytest.fixture
def mock_client():
    return AsyncMock()


@pytest.fixture
def service(mock_client):
    return AdminKnowledgeService(ai_model_client=mock_client)


class TestListDocuments:
    @pytest.mark.asyncio
    async def test_list_documents(self, service, mock_client):
        response = MagicMock()
        response.documents = [_make_mock_doc(), _make_mock_doc(document_id="doc-2")]
        response.total_count = 2
        response.page = 1
        response.page_size = 20
        mock_client.list_documents.return_value = response

        result = await service.list_documents(domain="plant_diseases", page=1, page_size=20)

        assert isinstance(result, DocumentListResponse)
        assert len(result.data) == 2
        assert result.pagination.total_count == 2
        mock_client.list_documents.assert_called_once_with(
            domain="plant_diseases", status=None, author=None, page=1, page_size=20
        )


class TestSearchDocuments:
    @pytest.mark.asyncio
    async def test_search_documents(self, service, mock_client):
        response = MagicMock()
        response.documents = [_make_mock_doc()]
        mock_client.search_documents.return_value = response

        result = await service.search_documents(query="blister blight")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], DocumentSummary)


class TestGetDocument:
    @pytest.mark.asyncio
    async def test_get_document(self, service, mock_client):
        mock_client.get_document.return_value = _make_mock_doc()

        result = await service.get_document(document_id="test-doc")

        assert isinstance(result, DocumentDetail)
        assert result.document_id == "test-doc"

    @pytest.mark.asyncio
    async def test_get_document_with_version(self, service, mock_client):
        mock_client.get_document.return_value = _make_mock_doc(version=3)

        result = await service.get_document(document_id="test-doc", version=3)

        assert result.version == 3
        mock_client.get_document.assert_called_once_with(document_id="test-doc", version=3)


class TestCreateDocument:
    @pytest.mark.asyncio
    async def test_create_document(self, service, mock_client):
        create_response = MagicMock()
        create_response.document = _make_mock_doc()
        mock_client.create_document.return_value = create_response

        result = await service.create_document(
            title="New Doc",
            domain="tea_cultivation",
            content="Content",
            author="Author",
        )

        assert isinstance(result, DocumentDetail)
        mock_client.create_document.assert_called_once()


class TestUpdateDocument:
    @pytest.mark.asyncio
    async def test_update_document(self, service, mock_client):
        mock_client.update_document.return_value = _make_mock_doc(version=2)

        result = await service.update_document(
            document_id="test-doc",
            title="Updated Title",
            change_summary="Changed title",
        )

        assert isinstance(result, DocumentDetail)
        assert result.version == 2


class TestDeleteDocument:
    @pytest.mark.asyncio
    async def test_delete_document(self, service, mock_client):
        delete_response = MagicMock()
        delete_response.versions_archived = 3
        mock_client.delete_document.return_value = delete_response

        result = await service.delete_document(document_id="test-doc")

        assert isinstance(result, DeleteDocumentResponse)
        assert result.versions_archived == 3


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_stage_document(self, service, mock_client):
        mock_client.stage_document.return_value = _make_mock_doc(status="staged")
        result = await service.stage_document(document_id="test-doc")
        assert isinstance(result, DocumentDetail)

    @pytest.mark.asyncio
    async def test_activate_document(self, service, mock_client):
        mock_client.activate_document.return_value = _make_mock_doc(status="active")
        result = await service.activate_document(document_id="test-doc")
        assert isinstance(result, DocumentDetail)

    @pytest.mark.asyncio
    async def test_archive_document(self, service, mock_client):
        mock_client.archive_document.return_value = _make_mock_doc(status="archived")
        result = await service.archive_document(document_id="test-doc")
        assert isinstance(result, DocumentDetail)

    @pytest.mark.asyncio
    async def test_rollback_document(self, service, mock_client):
        mock_client.rollback_document.return_value = _make_mock_doc(status="draft", version=4)
        result = await service.rollback_document(document_id="test-doc", target_version=2)
        assert isinstance(result, DocumentDetail)
        assert result.version == 4


class TestUploadDocument:
    @pytest.mark.asyncio
    async def test_upload_valid_file(self, service, mock_client):
        # Mock file
        file_content = b"# Test Document\n\nSome content here."
        upload_file = UploadFile(filename="test.md", file=BytesIO(file_content))

        # Mock create response
        create_response = MagicMock()
        create_response.document = _make_mock_doc()
        mock_client.create_document.return_value = create_response

        # Mock extract response
        extract_response = MagicMock()
        extract_response.job_id = "job-123"
        mock_client.extract_document.return_value = extract_response

        # Mock get extraction job
        job_response = MagicMock()
        job_response.job_id = "job-123"
        job_response.document_id = "test-doc"
        job_response.status = "pending"
        job_response.progress_percent = 0
        job_response.pages_processed = 0
        job_response.total_pages = 0
        job_response.error_message = ""
        job_response.started_at = _make_timestamp()
        job_response.completed_at = Timestamp()
        mock_client.get_extraction_job.return_value = job_response

        result = await service.upload_document(
            file=upload_file,
            title="Test Doc",
            domain="plant_diseases",
        )

        assert isinstance(result, ExtractionJobStatus)
        assert result.job_id == "job-123"

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, service, mock_client):
        upload_file = UploadFile(filename="test.exe", file=BytesIO(b"binary"))

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_document(file=upload_file, title="Bad", domain="plant_diseases")

        assert exc_info.value.status_code == 400
        assert "Unsupported file type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, service, mock_client):
        # Create a file larger than 50MB
        large_content = b"x" * (52_428_801)
        upload_file = UploadFile(filename="large.txt", file=BytesIO(large_content))

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_document(file=upload_file, title="Large", domain="plant_diseases")

        assert exc_info.value.status_code == 400
        assert "exceeds max" in str(exc_info.value.detail)


class TestExtractionJob:
    @pytest.mark.asyncio
    async def test_get_extraction_job(self, service, mock_client):
        job = MagicMock()
        job.job_id = "job-123"
        job.document_id = "doc-1"
        job.status = "completed"
        job.progress_percent = 100
        job.pages_processed = 10
        job.total_pages = 10
        job.error_message = ""
        job.started_at = _make_timestamp()
        job.completed_at = _make_timestamp(1700001000)
        mock_client.get_extraction_job.return_value = job

        result = await service.get_extraction_job(job_id="job-123")

        assert isinstance(result, ExtractionJobStatus)
        assert result.status == "completed"
        assert result.progress_percent == 100


class TestStreamExtractionProgress:
    @pytest.mark.asyncio
    async def test_stream_returns_async_iterator(self, service, mock_client):
        mock_stream = AsyncMock()
        mock_client.stream_extraction_progress.return_value = mock_stream

        result = await service.stream_extraction_progress(document_id="doc-1", job_id="job-1")

        assert result == mock_stream
        mock_client.stream_extraction_progress.assert_called_once_with(job_id="job-1")


class TestListChunks:
    @pytest.mark.asyncio
    async def test_list_chunks(self, service, mock_client):
        chunk = MagicMock()
        chunk.chunk_id = "chunk-1"
        chunk.document_id = "doc-1"
        chunk.document_version = 1
        chunk.chunk_index = 0
        chunk.content = "Chunk content"
        chunk.section_title = "Intro"
        chunk.word_count = 2
        chunk.char_count = 13
        chunk.pinecone_id = ""
        chunk.created_at = _make_timestamp()

        response = MagicMock()
        response.chunks = [chunk]
        response.total_count = 1
        response.page = 1
        response.page_size = 50
        mock_client.list_chunks.return_value = response

        result = await service.list_chunks(document_id="doc-1")

        assert isinstance(result, ChunkListResponse)
        assert len(result.data) == 1
        assert result.data[0].chunk_id == "chunk-1"


class TestVectorization:
    @pytest.mark.asyncio
    async def test_vectorize_document(self, service, mock_client):
        response = MagicMock()
        response.job_id = "vec-job-1"
        response.status = "pending"
        response.namespace = "knowledge-v1"
        response.chunks_total = 0
        response.chunks_embedded = 0
        response.chunks_stored = 0
        response.failed_count = 0
        response.content_hash = ""
        response.error_message = ""
        mock_client.vectorize_document.return_value = response

        result = await service.vectorize_document(document_id="doc-1")

        assert isinstance(result, VectorizationJobStatus)
        assert result.job_id == "vec-job-1"

    @pytest.mark.asyncio
    async def test_get_vectorization_job(self, service, mock_client):
        job = MagicMock()
        job.job_id = "vec-job-1"
        job.status = "completed"
        job.document_id = "doc-1"
        job.document_version = 1
        job.namespace = "knowledge-v1"
        job.chunks_total = 15
        job.chunks_embedded = 15
        job.chunks_stored = 15
        job.failed_count = 0
        job.content_hash = "abc"
        job.error_message = ""
        job.started_at = _make_timestamp()
        job.completed_at = _make_timestamp(1700001000)
        mock_client.get_vectorization_job.return_value = job

        result = await service.get_vectorization_job(job_id="vec-job-1")

        assert isinstance(result, VectorizationJobStatus)
        assert result.chunks_total == 15


class TestQueryKnowledge:
    @pytest.mark.asyncio
    async def test_query_knowledge(self, service, mock_client):
        match = MagicMock()
        match.chunk_id = "chunk-1"
        match.content = "Blister blight..."
        match.score = 0.92
        match.document_id = "disease-guide"
        match.title = "Disease Guide"
        match.domain = "plant_diseases"

        retrieval_result = MagicMock()
        retrieval_result.matches = [match]
        retrieval_result.query = "blister blight treatment"
        retrieval_result.total_matches = 1
        mock_client.query_knowledge.return_value = retrieval_result

        result = await service.query_knowledge(query="blister blight treatment")

        assert isinstance(result, QueryResponse)
        assert len(result.matches) == 1
        assert result.matches[0].score == 0.92
        assert result.query == "blister blight treatment"
