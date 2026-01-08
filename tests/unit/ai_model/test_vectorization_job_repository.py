"""Unit tests for VectorizationJobRepository.

Tests cover:
- VectorizationJobDocument model conversion (to/from VectorizationResult)
- Repository CRUD operations (create, get, update)
- Repository list operations (by document, by status)
- Pipeline integration with repository injection
- Pipeline fallback to in-memory when repository is None

Story 0.75.13d: Vectorization Job Persistence
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ai_model.config import Settings
from ai_model.domain.vectorization import (
    FailedChunk,
    VectorizationJobStatus,
    VectorizationProgress,
    VectorizationResult,
)
from ai_model.domain.vectorization_job_document import VectorizationJobDocument
from ai_model.infrastructure.repositories.vectorization_job_repository import (
    MongoDBVectorizationJobRepository,
    VectorizationJobRepository,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_result() -> VectorizationResult:
    """Create sample VectorizationResult for testing."""
    return VectorizationResult(
        job_id="test-job-123",
        status=VectorizationJobStatus.COMPLETED,
        document_id="disease-guide",
        document_version=1,
        namespace="knowledge-v1-staged",
        progress=VectorizationProgress(
            chunks_total=10,
            chunks_embedded=10,
            chunks_stored=10,
            failed_count=0,
        ),
        content_hash="sha256:abc123",
        pinecone_ids=["disease-guide-0", "disease-guide-1"],
        started_at=datetime(2026, 1, 8, 10, 0, 0, tzinfo=UTC),
        completed_at=datetime(2026, 1, 8, 10, 0, 30, tzinfo=UTC),
    )


@pytest.fixture
def sample_pending_result() -> VectorizationResult:
    """Create sample pending VectorizationResult for testing."""
    return VectorizationResult(
        job_id="pending-job-456",
        status=VectorizationJobStatus.PENDING,
        document_id="weather-guide",
        document_version=2,
        namespace="",
        chunks_total=0,
        chunks_stored=0,
    )


@pytest.fixture
def sample_failed_result() -> VectorizationResult:
    """Create sample failed VectorizationResult for testing."""
    return VectorizationResult(
        job_id="failed-job-789",
        status=VectorizationJobStatus.FAILED,
        document_id="disease-guide",
        document_version=1,
        namespace="knowledge-v1-staged",
        progress=VectorizationProgress(
            chunks_total=5,
            chunks_embedded=0,
            chunks_stored=0,
            failed_count=5,
        ),
        failed_chunks=[
            FailedChunk(chunk_id="chunk-0", chunk_index=0, error_message="API error"),
        ],
        error_message="Embedding service unavailable",
        started_at=datetime(2026, 1, 8, 11, 0, 0, tzinfo=UTC),
        completed_at=datetime(2026, 1, 8, 11, 0, 10, tzinfo=UTC),
    )


@pytest.fixture
def mock_mongodb_collection() -> AsyncMock:
    """Create mock MongoDB collection."""
    collection = AsyncMock()
    collection.create_index = AsyncMock(return_value="idx_name")
    return collection


@pytest.fixture
def mock_database(mock_mongodb_collection) -> MagicMock:
    """Create mock MongoDB database."""
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=mock_mongodb_collection)
    return db


@pytest.fixture
def repository(mock_database) -> MongoDBVectorizationJobRepository:
    """Create repository with mock database."""
    return MongoDBVectorizationJobRepository(db=mock_database, ttl_hours=24)


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVectorizationJobDocument:
    """Tests for VectorizationJobDocument Pydantic model."""

    def test_from_result_completed(self, sample_result):
        """Test conversion from completed VectorizationResult to document."""
        doc = VectorizationJobDocument.from_result(sample_result)

        assert doc.job_id == "test-job-123"
        assert doc.status == VectorizationJobStatus.COMPLETED
        assert doc.document_id == "disease-guide"
        assert doc.document_version == 1
        assert doc.namespace == "knowledge-v1-staged"
        assert doc.chunks_total == 10
        assert doc.chunks_embedded == 10
        assert doc.chunks_stored == 10
        assert doc.failed_count == 0
        assert doc.content_hash == "sha256:abc123"
        assert len(doc.pinecone_ids) == 2
        assert doc.started_at is not None
        assert doc.completed_at is not None
        assert doc.created_at is not None
        assert doc.updated_at is not None

    def test_from_result_pending(self, sample_pending_result):
        """Test conversion from pending VectorizationResult to document."""
        doc = VectorizationJobDocument.from_result(sample_pending_result)

        assert doc.job_id == "pending-job-456"
        assert doc.status == VectorizationJobStatus.PENDING
        assert doc.namespace == ""
        assert doc.chunks_total == 0
        assert doc.completed_at is None

    def test_from_result_with_failed_chunks(self, sample_failed_result):
        """Test conversion preserves failed chunks."""
        doc = VectorizationJobDocument.from_result(sample_failed_result)

        assert doc.status == VectorizationJobStatus.FAILED
        assert doc.failed_count == 5
        assert len(doc.failed_chunks) == 1
        assert doc.failed_chunks[0].chunk_id == "chunk-0"
        assert doc.error_message == "Embedding service unavailable"

    def test_to_result_roundtrip(self, sample_result):
        """Test document -> result conversion preserves data."""
        doc = VectorizationJobDocument.from_result(sample_result)
        result = doc.to_result()

        assert result.job_id == sample_result.job_id
        assert result.status == sample_result.status
        assert result.document_id == sample_result.document_id
        assert result.document_version == sample_result.document_version
        assert result.namespace == sample_result.namespace
        assert result.progress.chunks_total == sample_result.progress.chunks_total
        assert result.progress.chunks_stored == sample_result.progress.chunks_stored
        assert result.content_hash == sample_result.content_hash
        assert result.pinecone_ids == sample_result.pinecone_ids

    def test_to_result_empty_namespace_becomes_none(self, sample_pending_result):
        """Test empty namespace becomes None in result."""
        doc = VectorizationJobDocument.from_result(sample_pending_result)
        result = doc.to_result()

        # Empty namespace should become None in result
        assert result.namespace is None


# ═══════════════════════════════════════════════════════════════════════════════
# REPOSITORY CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRepositoryCRUD:
    """Tests for repository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_stores_job(self, repository, mock_mongodb_collection, sample_result):
        """Test create() stores job in MongoDB."""
        mock_mongodb_collection.insert_one = AsyncMock(return_value=MagicMock())

        job_id = await repository.create(sample_result)

        assert job_id == "test-job-123"
        mock_mongodb_collection.insert_one.assert_called_once()

        # Verify the document has _id set to job_id
        call_args = mock_mongodb_collection.insert_one.call_args[0][0]
        assert call_args["_id"] == "test-job-123"
        assert call_args["job_id"] == "test-job-123"

    @pytest.mark.asyncio
    async def test_get_returns_result(self, repository, mock_mongodb_collection, sample_result):
        """Test get() retrieves and converts job from MongoDB."""
        doc = VectorizationJobDocument.from_result(sample_result)
        mongo_doc = doc.model_dump()
        mongo_doc["_id"] = doc.job_id
        mock_mongodb_collection.find_one = AsyncMock(return_value=mongo_doc)

        result = await repository.get("test-job-123")

        assert result is not None
        assert result.job_id == "test-job-123"
        assert result.status == VectorizationJobStatus.COMPLETED
        mock_mongodb_collection.find_one.assert_called_once_with({"_id": "test-job-123"})

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self, repository, mock_mongodb_collection):
        """Test get() returns None for missing job."""
        mock_mongodb_collection.find_one = AsyncMock(return_value=None)

        result = await repository.get("nonexistent-job")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_replaces_document(self, repository, mock_mongodb_collection, sample_result):
        """Test update() replaces document in MongoDB."""
        # Mock find_one for created_at preservation check
        mock_mongodb_collection.find_one = AsyncMock(return_value=None)
        mock_mongodb_collection.replace_one = AsyncMock(return_value=MagicMock())

        await repository.update(sample_result)

        mock_mongodb_collection.replace_one.assert_called_once()
        call_args = mock_mongodb_collection.replace_one.call_args
        assert call_args[0][0] == {"_id": "test-job-123"}
        assert call_args[1]["upsert"] is True

    @pytest.mark.asyncio
    async def test_update_preserves_created_at(self, repository, mock_mongodb_collection, sample_result):
        """Test update() preserves original created_at timestamp."""
        original_created_at = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

        # Mock find_one to return existing document with original created_at
        mock_mongodb_collection.find_one = AsyncMock(
            return_value={"created_at": original_created_at}
        )
        mock_mongodb_collection.replace_one = AsyncMock(return_value=MagicMock())

        await repository.update(sample_result)

        # Verify the replaced document has original created_at preserved
        call_args = mock_mongodb_collection.replace_one.call_args[0][1]
        assert call_args["created_at"] == original_created_at

    @pytest.mark.asyncio
    async def test_update_uses_new_created_at_for_new_documents(
        self, repository, mock_mongodb_collection, sample_result
    ):
        """Test update() uses new created_at when document doesn't exist."""
        # Mock find_one to return None (document doesn't exist)
        mock_mongodb_collection.find_one = AsyncMock(return_value=None)
        mock_mongodb_collection.replace_one = AsyncMock(return_value=MagicMock())

        await repository.update(sample_result)

        # Verify created_at is set (should be close to now)
        call_args = mock_mongodb_collection.replace_one.call_args[0][1]
        assert "created_at" in call_args
        assert isinstance(call_args["created_at"], datetime)


# ═══════════════════════════════════════════════════════════════════════════════
# REPOSITORY LIST TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRepositoryList:
    """Tests for repository list operations."""

    @pytest.mark.asyncio
    async def test_list_by_document(self, repository, mock_mongodb_collection, sample_result):
        """Test list_by_document() returns jobs for document."""
        doc = VectorizationJobDocument.from_result(sample_result)
        mongo_doc = doc.model_dump()
        mongo_doc["_id"] = doc.job_id

        # Create a mock cursor
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[mongo_doc])
        mock_mongodb_collection.find = MagicMock(return_value=mock_cursor)

        results = await repository.list_by_document("disease-guide")

        assert len(results) == 1
        assert results[0].document_id == "disease-guide"
        mock_mongodb_collection.find.assert_called_once_with({"document_id": "disease-guide"})

    @pytest.mark.asyncio
    async def test_list_by_status(self, repository, mock_mongodb_collection, sample_result):
        """Test list_by_status() returns jobs with matching status."""
        doc = VectorizationJobDocument.from_result(sample_result)
        mongo_doc = doc.model_dump()
        mongo_doc["_id"] = doc.job_id

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[mongo_doc])
        mock_mongodb_collection.find = MagicMock(return_value=mock_cursor)

        results = await repository.list_by_status(VectorizationJobStatus.COMPLETED)

        assert len(results) == 1
        assert results[0].status == VectorizationJobStatus.COMPLETED
        mock_mongodb_collection.find.assert_called_once_with({"status": "completed"})

    @pytest.mark.asyncio
    async def test_list_by_status_empty(self, repository, mock_mongodb_collection):
        """Test list_by_status() returns empty list when no matches."""
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_mongodb_collection.find = MagicMock(return_value=mock_cursor)

        results = await repository.list_by_status(VectorizationJobStatus.IN_PROGRESS)

        assert len(results) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# INDEX TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRepositoryIndexes:
    """Tests for repository index creation."""

    @pytest.mark.asyncio
    async def test_ensure_indexes_creates_indexes(self, repository, mock_mongodb_collection):
        """Test ensure_indexes() creates required indexes."""
        mock_mongodb_collection.create_index = AsyncMock(return_value="idx_name")

        await repository.ensure_indexes()

        # Should create multiple indexes
        assert mock_mongodb_collection.create_index.call_count >= 4

        # Verify unique index on job_id
        calls = mock_mongodb_collection.create_index.call_args_list
        job_id_call = next(c for c in calls if c[0][0] == "job_id")
        assert job_id_call[1]["unique"] is True

    @pytest.mark.asyncio
    async def test_ensure_indexes_idempotent(self, repository, mock_mongodb_collection):
        """Test ensure_indexes() is idempotent (only runs once)."""
        mock_mongodb_collection.create_index = AsyncMock(return_value="idx_name")

        await repository.ensure_indexes()
        first_count = mock_mongodb_collection.create_index.call_count

        await repository.ensure_indexes()
        second_count = mock_mongodb_collection.create_index.call_count

        # Should not create indexes twice
        assert first_count == second_count

    @pytest.mark.asyncio
    async def test_ttl_index_not_created_when_disabled(self, mock_database, mock_mongodb_collection):
        """Test TTL index is not created when ttl_hours=0."""
        mock_mongodb_collection.create_index = AsyncMock(return_value="idx_name")
        repo = MongoDBVectorizationJobRepository(db=mock_database, ttl_hours=0)

        await repo.ensure_indexes()

        # Verify no TTL index (no expireAfterSeconds in any call)
        calls = mock_mongodb_collection.create_index.call_args_list
        ttl_calls = [c for c in calls if "expireAfterSeconds" in c[1]]
        assert len(ttl_calls) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPipelineIntegration:
    """Tests for VectorizationPipeline integration with repository."""

    @pytest.fixture
    def mock_settings(self, monkeypatch) -> Settings:
        """Create settings for pipeline tests."""
        monkeypatch.setenv("PINECONE_API_KEY", "test-pinecone-api-key")
        monkeypatch.setenv("PINECONE_INDEX_NAME", "test-index")
        return Settings(_env_file=None, vectorization_batch_size=10)

    @pytest.fixture
    def mock_job_repository(self) -> AsyncMock:
        """Create mock VectorizationJobRepository."""
        repo = AsyncMock(spec=VectorizationJobRepository)
        repo.create = AsyncMock(return_value="job-123")
        repo.get = AsyncMock(return_value=None)
        repo.update = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_pipeline_uses_repository_for_create_job(
        self,
        mock_settings,
        mock_job_repository,
    ):
        """Test pipeline persists job via repository in create_job()."""
        from ai_model.services.vectorization_pipeline import VectorizationPipeline

        # Create pipeline with repository
        pipeline = VectorizationPipeline(
            chunk_repository=AsyncMock(),
            document_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            vector_store=AsyncMock(),
            settings=mock_settings,
            job_repository=mock_job_repository,
        )

        job = await pipeline.create_job("test-doc", 1)

        # Verify repository was called
        mock_job_repository.create.assert_called_once()
        assert job.document_id == "test-doc"

    @pytest.mark.asyncio
    async def test_pipeline_uses_repository_for_get_job_status(
        self,
        mock_settings,
        mock_job_repository,
        sample_result,
    ):
        """Test pipeline queries repository in get_job_status()."""
        from ai_model.services.vectorization_pipeline import VectorizationPipeline

        mock_job_repository.get = AsyncMock(return_value=sample_result)

        pipeline = VectorizationPipeline(
            chunk_repository=AsyncMock(),
            document_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            vector_store=AsyncMock(),
            settings=mock_settings,
            job_repository=mock_job_repository,
        )

        # Query for job not in local cache
        result = await pipeline.get_job_status("test-job-123")

        # Should query repository
        mock_job_repository.get.assert_called_once_with("test-job-123")
        assert result is not None
        assert result.job_id == "test-job-123"

    @pytest.mark.asyncio
    async def test_pipeline_fallback_without_repository(self, mock_settings):
        """Test pipeline falls back to in-memory when repository is None."""
        from ai_model.services.vectorization_pipeline import VectorizationPipeline

        # Create pipeline WITHOUT repository
        with patch("ai_model.services.vectorization_pipeline.logger") as mock_logger:
            pipeline = VectorizationPipeline(
                chunk_repository=AsyncMock(),
                document_repository=AsyncMock(),
                embedding_service=AsyncMock(),
                vector_store=AsyncMock(),
                settings=mock_settings,
                job_repository=None,
            )

            # Should log warning about in-memory mode
            mock_logger.warning.assert_called_once()
            assert "in-memory" in str(mock_logger.warning.call_args)

        # Create job should still work (in-memory)
        job = await pipeline.create_job("test-doc", 1)
        assert job is not None

        # Get job status should find it in-memory
        result = await pipeline.get_job_status(job.job_id)
        assert result is not None

    @pytest.mark.asyncio
    async def test_pipeline_caches_repository_result(
        self,
        mock_settings,
        mock_job_repository,
        sample_result,
    ):
        """Test pipeline caches result from repository for subsequent lookups."""
        from ai_model.services.vectorization_pipeline import VectorizationPipeline

        mock_job_repository.get = AsyncMock(return_value=sample_result)

        pipeline = VectorizationPipeline(
            chunk_repository=AsyncMock(),
            document_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            vector_store=AsyncMock(),
            settings=mock_settings,
            job_repository=mock_job_repository,
        )

        # First call should query repository
        result1 = await pipeline.get_job_status("test-job-123")
        assert result1 is not None

        # Second call should use cache (no additional repository call)
        result2 = await pipeline.get_job_status("test-job-123")
        assert result2 is not None

        # Repository should only be called once
        assert mock_job_repository.get.call_count == 1


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestConfiguration:
    """Tests for configuration handling."""

    def test_default_ttl_is_24_hours(self, monkeypatch):
        """Test default TTL configuration."""
        monkeypatch.setenv("PINECONE_API_KEY", "test-key")
        settings = Settings(_env_file=None)
        assert settings.vectorization_job_ttl_hours == 24

    def test_ttl_is_configurable(self, monkeypatch):
        """Test TTL can be configured via environment."""
        monkeypatch.setenv("PINECONE_API_KEY", "test-key")
        monkeypatch.setenv("AI_MODEL_VECTORIZATION_JOB_TTL_HOURS", "48")
        settings = Settings(_env_file=None)
        assert settings.vectorization_job_ttl_hours == 48

    def test_list_limit_is_configurable(self, mock_database):
        """Test list_limit can be configured in repository constructor."""
        repo = MongoDBVectorizationJobRepository(
            db=mock_database,
            ttl_hours=24,
            list_limit=50,
        )
        assert repo._list_limit == 50

    def test_default_list_limit_is_100(self, mock_database):
        """Test default list_limit is 100."""
        repo = MongoDBVectorizationJobRepository(db=mock_database)
        assert repo._list_limit == 100


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE ERROR HANDLING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPipelineErrorHandling:
    """Tests for pipeline error handling when repository operations fail."""

    @pytest.fixture
    def mock_settings(self, monkeypatch) -> Settings:
        """Create settings for pipeline tests."""
        monkeypatch.setenv("PINECONE_API_KEY", "test-pinecone-api-key")
        monkeypatch.setenv("PINECONE_INDEX_NAME", "test-index")
        return Settings(_env_file=None, vectorization_batch_size=10)

    @pytest.fixture
    def failing_job_repository(self) -> AsyncMock:
        """Create mock repository that fails on persist operations."""
        repo = AsyncMock(spec=VectorizationJobRepository)
        repo.create = AsyncMock(side_effect=Exception("MongoDB connection failed"))
        repo.update = AsyncMock(side_effect=Exception("MongoDB connection failed"))
        repo.get = AsyncMock(return_value=None)
        return repo

    @pytest.mark.asyncio
    async def test_create_job_continues_on_repository_failure(
        self,
        mock_settings,
        failing_job_repository,
    ):
        """Test create_job() continues when repository.create() fails."""
        from ai_model.services.vectorization_pipeline import VectorizationPipeline

        with patch("ai_model.services.vectorization_pipeline.logger") as mock_logger:
            pipeline = VectorizationPipeline(
                chunk_repository=AsyncMock(),
                document_repository=AsyncMock(),
                embedding_service=AsyncMock(),
                vector_store=AsyncMock(),
                settings=mock_settings,
                job_repository=failing_job_repository,
            )

            # Should not raise, should return job
            job = await pipeline.create_job("test-doc", 1)

            assert job is not None
            assert job.document_id == "test-doc"

            # Should have logged warning about persistence failure
            mock_logger.warning.assert_called()
            warning_call = str(mock_logger.warning.call_args)
            assert "persist" in warning_call.lower() or "repository" in warning_call.lower()

    @pytest.mark.asyncio
    async def test_get_job_status_continues_on_repository_failure(
        self,
        mock_settings,
        failing_job_repository,
    ):
        """Test get_job_status() returns None when repository.get() fails."""
        from ai_model.services.vectorization_pipeline import VectorizationPipeline

        failing_job_repository.get = AsyncMock(
            side_effect=Exception("MongoDB connection failed")
        )

        with patch("ai_model.services.vectorization_pipeline.logger") as mock_logger:
            pipeline = VectorizationPipeline(
                chunk_repository=AsyncMock(),
                document_repository=AsyncMock(),
                embedding_service=AsyncMock(),
                vector_store=AsyncMock(),
                settings=mock_settings,
                job_repository=failing_job_repository,
            )

            # Should not raise, should return None (not in cache, repo failed)
            result = await pipeline.get_job_status("unknown-job")

            assert result is None

            # Should have logged error about repository failure
            mock_logger.error.assert_called()
            error_call = str(mock_logger.error.call_args)
            assert "repository" in error_call.lower() or "job" in error_call.lower()
