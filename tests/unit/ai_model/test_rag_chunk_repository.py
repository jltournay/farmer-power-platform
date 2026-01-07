"""Unit tests for RagChunkRepository.

Story 0.75.10d: Semantic Chunking
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.rag_document import RagChunk
from ai_model.infrastructure.repositories.rag_chunk_repository import RagChunkRepository


@pytest.fixture
def mock_db():
    """Create a mock MongoDB database."""
    db = MagicMock()
    collection = MagicMock()

    # Setup async methods on collection
    collection.find = MagicMock()
    collection.find_one = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.insert_many = AsyncMock()
    collection.delete_many = AsyncMock()
    collection.count_documents = AsyncMock()
    collection.find_one_and_update = AsyncMock()
    collection.create_index = AsyncMock()

    db.__getitem__ = MagicMock(return_value=collection)
    return db


@pytest.fixture
def repository(mock_db):
    """Create a RagChunkRepository with mock database."""
    return RagChunkRepository(mock_db)


@pytest.fixture
def sample_chunk():
    """Create a sample RagChunk for testing."""
    return RagChunk(
        chunk_id="test-doc-v1-chunk-0",
        document_id="test-doc",
        document_version=1,
        chunk_index=0,
        content="Test chunk content.",
        section_title="Test Section",
        word_count=3,
        char_count=19,
        created_at=datetime.now(UTC),
        pinecone_id=None,
    )


@pytest.fixture
def sample_chunks():
    """Create multiple sample RagChunks for testing."""
    now = datetime.now(UTC)
    return [
        RagChunk(
            chunk_id="test-doc-v1-chunk-0",
            document_id="test-doc",
            document_version=1,
            chunk_index=0,
            content="First chunk content.",
            section_title="Section One",
            word_count=3,
            char_count=20,
            created_at=now,
            pinecone_id=None,
        ),
        RagChunk(
            chunk_id="test-doc-v1-chunk-1",
            document_id="test-doc",
            document_version=1,
            chunk_index=1,
            content="Second chunk content.",
            section_title="Section Two",
            word_count=3,
            char_count=21,
            created_at=now,
            pinecone_id=None,
        ),
        RagChunk(
            chunk_id="test-doc-v1-chunk-2",
            document_id="test-doc",
            document_version=1,
            chunk_index=2,
            content="Third chunk content.",
            section_title="Section Two",
            word_count=3,
            char_count=20,
            created_at=now,
            pinecone_id="pinecone-id-2",
        ),
    ]


class TestRagChunkRepositoryInit:
    """Tests for RagChunkRepository initialization."""

    def test_repository_uses_correct_collection(self, mock_db):
        """Test repository uses rag_chunks collection."""
        repo = RagChunkRepository(mock_db)
        mock_db.__getitem__.assert_called_with("rag_chunks")

    def test_repository_collection_name_constant(self):
        """Test COLLECTION_NAME is rag_chunks."""
        assert RagChunkRepository.COLLECTION_NAME == "rag_chunks"


class TestRagChunkRepositoryGetByDocument:
    """Tests for get_by_document method."""

    @pytest.mark.asyncio
    async def test_get_by_document_returns_chunks_ordered(self, repository, mock_db, sample_chunks):
        """Test get_by_document returns chunks ordered by chunk_index."""
        # Setup mock cursor
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[{"_id": c.chunk_id, **c.model_dump()} for c in sample_chunks])
        mock_db["rag_chunks"].find.return_value = mock_cursor

        chunks = await repository.get_by_document("test-doc", 1)

        assert len(chunks) == 3
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[2].chunk_index == 2
        mock_cursor.sort.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_document_filters_correctly(self, repository, mock_db):
        """Test get_by_document uses correct filter."""
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db["rag_chunks"].find.return_value = mock_cursor

        await repository.get_by_document("my-doc", 5)

        mock_db["rag_chunks"].find.assert_called_once_with({"document_id": "my-doc", "document_version": 5})

    @pytest.mark.asyncio
    async def test_get_by_document_empty_result(self, repository, mock_db):
        """Test get_by_document returns empty list when no chunks."""
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db["rag_chunks"].find.return_value = mock_cursor

        chunks = await repository.get_by_document("nonexistent", 1)

        assert chunks == []


class TestRagChunkRepositoryDeleteByDocument:
    """Tests for delete_by_document method."""

    @pytest.mark.asyncio
    async def test_delete_by_document_returns_count(self, repository, mock_db):
        """Test delete_by_document returns deleted count."""
        mock_result = MagicMock()
        mock_result.deleted_count = 5
        mock_db["rag_chunks"].delete_many = AsyncMock(return_value=mock_result)

        deleted = await repository.delete_by_document("test-doc", 1)

        assert deleted == 5

    @pytest.mark.asyncio
    async def test_delete_by_document_filters_correctly(self, repository, mock_db):
        """Test delete_by_document uses correct filter."""
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_db["rag_chunks"].delete_many = AsyncMock(return_value=mock_result)

        await repository.delete_by_document("my-doc", 3)

        mock_db["rag_chunks"].delete_many.assert_called_once_with({"document_id": "my-doc", "document_version": 3})


class TestRagChunkRepositoryCountByDocument:
    """Tests for count_by_document method."""

    @pytest.mark.asyncio
    async def test_count_by_document_returns_count(self, repository, mock_db):
        """Test count_by_document returns correct count."""
        mock_db["rag_chunks"].count_documents = AsyncMock(return_value=10)

        count = await repository.count_by_document("test-doc", 1)

        assert count == 10

    @pytest.mark.asyncio
    async def test_count_by_document_filters_correctly(self, repository, mock_db):
        """Test count_by_document uses correct filter."""
        mock_db["rag_chunks"].count_documents = AsyncMock(return_value=0)

        await repository.count_by_document("my-doc", 2)

        mock_db["rag_chunks"].count_documents.assert_called_once_with({"document_id": "my-doc", "document_version": 2})


class TestRagChunkRepositoryBulkCreate:
    """Tests for bulk_create method."""

    @pytest.mark.asyncio
    async def test_bulk_create_returns_chunks(self, repository, mock_db, sample_chunks):
        """Test bulk_create returns created chunks."""
        result = await repository.bulk_create(sample_chunks)

        assert result == sample_chunks
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_bulk_create_calls_insert_many(self, repository, mock_db, sample_chunks):
        """Test bulk_create uses insertMany."""
        await repository.bulk_create(sample_chunks)

        mock_db["rag_chunks"].insert_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_empty_list_returns_empty(self, repository, mock_db):
        """Test bulk_create with empty list returns empty."""
        result = await repository.bulk_create([])

        assert result == []
        mock_db["rag_chunks"].insert_many.assert_not_called()


class TestRagChunkRepositoryUpdatePineconeId:
    """Tests for update_pinecone_id method."""

    @pytest.mark.asyncio
    async def test_update_pinecone_id_success(self, repository, mock_db, sample_chunk):
        """Test update_pinecone_id returns updated chunk."""
        updated_doc = sample_chunk.model_dump()
        updated_doc["_id"] = sample_chunk.chunk_id
        updated_doc["pinecone_id"] = "new-vector-id"
        mock_db["rag_chunks"].find_one_and_update = AsyncMock(return_value=updated_doc)

        result = await repository.update_pinecone_id(sample_chunk.chunk_id, "new-vector-id")

        assert result is not None
        assert result.pinecone_id == "new-vector-id"

    @pytest.mark.asyncio
    async def test_update_pinecone_id_not_found(self, repository, mock_db):
        """Test update_pinecone_id returns None when not found."""
        mock_db["rag_chunks"].find_one_and_update = AsyncMock(return_value=None)

        result = await repository.update_pinecone_id("nonexistent", "vector-id")

        assert result is None


class TestRagChunkRepositoryGetChunksWithoutVectors:
    """Tests for get_chunks_without_vectors method."""

    @pytest.mark.asyncio
    async def test_get_chunks_without_vectors_filters_null_pinecone_id(self, repository, mock_db, sample_chunks):
        """Test get_chunks_without_vectors returns only unvectorized chunks."""
        # Only return chunks with pinecone_id=None
        unvectorized = [c for c in sample_chunks if c.pinecone_id is None]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[{"_id": c.chunk_id, **c.model_dump()} for c in unvectorized])
        mock_db["rag_chunks"].find.return_value = mock_cursor

        chunks = await repository.get_chunks_without_vectors("test-doc", 1)

        # Should only get 2 chunks (index 0 and 1, not 2 which has pinecone_id)
        assert len(chunks) == 2
        assert all(c.pinecone_id is None for c in chunks)


class TestRagChunkRepositoryEnsureIndexes:
    """Tests for ensure_indexes method."""

    @pytest.mark.asyncio
    async def test_ensure_indexes_creates_all_indexes(self, repository, mock_db):
        """Test ensure_indexes creates required indexes."""
        await repository.ensure_indexes()

        # Should create 4 indexes
        assert mock_db["rag_chunks"].create_index.call_count == 4
