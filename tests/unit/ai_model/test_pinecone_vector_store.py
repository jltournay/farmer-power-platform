"""Unit tests for Pinecone Vector Store.

Tests cover:
- Domain models (VectorMetadata, VectorUpsertRequest, QueryResult, etc.)
- Upsert operations (single, batch, chunking)
- Query operations (top_k, filters, namespaces)
- Delete operations (by IDs, delete all)
- Stats operations
- Error handling (not configured, index not found, retries)
- Batching logic

Story 0.75.13: RAG Vector Storage (Pinecone Repository)
"""

from unittest.mock import MagicMock, patch

import pytest
from ai_model.config import Settings
from ai_model.domain.vector_store import (
    VECTOR_DIMENSIONS,
    IndexStats,
    NamespaceStats,
    QueryMatch,
    QueryResult,
    UpsertResult,
    VectorMetadata,
    VectorUpsertRequest,
)
from ai_model.infrastructure.pinecone_vector_store import (
    DELETE_BATCH_SIZE,
    UPSERT_BATCH_SIZE,
    PineconeIndexNotFoundError,
    PineconeNotConfiguredError,
    PineconeVectorStore,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_pinecone_settings(monkeypatch) -> Settings:
    """Create settings with Pinecone configured."""
    monkeypatch.setenv("PINECONE_API_KEY", "test-pinecone-api-key")
    monkeypatch.setenv("PINECONE_ENVIRONMENT", "us-east-1")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "test-index")
    monkeypatch.setenv("PINECONE_EMBEDDING_MODEL", "multilingual-e5-large")

    settings = Settings(
        _env_file=None,
    )
    return settings


@pytest.fixture
def mock_pinecone_settings_disabled(monkeypatch) -> Settings:
    """Create settings without Pinecone configured."""
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODEL_PINECONE_API_KEY", raising=False)

    settings = Settings(
        _env_file=None,
        pinecone_api_key=None,
        pinecone_environment="us-east-1",
        pinecone_index_name="test-index",
    )
    return settings


@pytest.fixture
def mock_pinecone_index():
    """Create mock Pinecone index."""
    index = MagicMock()

    # Default upsert response
    upsert_response = MagicMock()
    upsert_response.upserted_count = 1
    index.upsert.return_value = upsert_response

    # Default query response
    query_response = MagicMock()
    query_response.matches = []
    index.query.return_value = query_response

    # Default stats response
    stats_response = MagicMock()
    stats_response.total_vector_count = 0
    stats_response.namespaces = {}
    stats_response.dimension = 1024
    index.describe_index_stats.return_value = stats_response

    return index


@pytest.fixture
def mock_pinecone_client(mock_pinecone_index):
    """Create mock Pinecone client."""
    client = MagicMock()
    client.Index.return_value = mock_pinecone_index

    # Mock list_indexes for validation
    mock_index_info = MagicMock()
    mock_index_info.name = "test-index"
    client.list_indexes.return_value = [mock_index_info]

    return client


@pytest.fixture
def sample_vector_metadata() -> VectorMetadata:
    """Create sample vector metadata."""
    return VectorMetadata(
        document_id="disease-guide",
        chunk_id="disease-guide-chunk-0",
        chunk_index=0,
        domain="plant_diseases",
        title="Blister Blight Guide",
        region="Kenya",
        season="dry_season",
        tags=["blister-blight", "fungal"],
    )


@pytest.fixture
def sample_upsert_request(sample_vector_metadata) -> VectorUpsertRequest:
    """Create sample upsert request."""
    return VectorUpsertRequest(
        id="disease-guide-0",
        values=[0.1] * VECTOR_DIMENSIONS,
        metadata=sample_vector_metadata,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DOMAIN MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVectorDimensions:
    """Tests for VECTOR_DIMENSIONS constant."""

    def test_vector_dimensions_value(self):
        """Test that vector dimensions is 1024 for E5-large."""
        assert VECTOR_DIMENSIONS == 1024


class TestVectorMetadata:
    """Tests for VectorMetadata model."""

    def test_create_with_required_fields(self):
        """Test creating metadata with required fields."""
        metadata = VectorMetadata(
            document_id="doc-1",
            chunk_id="chunk-1",
            chunk_index=0,
            domain="plant_diseases",
            title="Test Document",
        )
        assert metadata.document_id == "doc-1"
        assert metadata.chunk_id == "chunk-1"
        assert metadata.chunk_index == 0
        assert metadata.domain == "plant_diseases"
        assert metadata.title == "Test Document"
        assert metadata.region is None
        assert metadata.season is None
        assert metadata.tags == []

    def test_create_with_all_fields(self):
        """Test creating metadata with all fields."""
        metadata = VectorMetadata(
            document_id="doc-1",
            chunk_id="chunk-1",
            chunk_index=5,
            domain="tea_cultivation",
            title="Tea Growing Guide",
            region="Rwanda",
            season="monsoon",
            tags=["cultivation", "best-practices"],
        )
        assert metadata.region == "Rwanda"
        assert metadata.season == "monsoon"
        assert metadata.tags == ["cultivation", "best-practices"]

    def test_chunk_index_validation(self):
        """Test chunk_index must be non-negative."""
        with pytest.raises(ValueError):
            VectorMetadata(
                document_id="doc-1",
                chunk_id="chunk-1",
                chunk_index=-1,
                domain="plant_diseases",
                title="Test",
            )

    def test_model_dump(self):
        """Test model_dump for Pinecone metadata."""
        metadata = VectorMetadata(
            document_id="doc-1",
            chunk_id="chunk-1",
            chunk_index=0,
            domain="plant_diseases",
            title="Test Document",
            tags=["tag1", "tag2"],
        )
        data = metadata.model_dump()
        assert data["document_id"] == "doc-1"
        assert data["tags"] == ["tag1", "tag2"]


class TestVectorUpsertRequest:
    """Tests for VectorUpsertRequest model."""

    def test_create_upsert_request(self):
        """Test creating upsert request."""
        request = VectorUpsertRequest(
            id="vec-1",
            values=[0.1] * 1024,
            metadata=None,
        )
        assert request.id == "vec-1"
        assert len(request.values) == 1024
        assert request.metadata is None

    def test_create_with_metadata(self, sample_vector_metadata):
        """Test creating upsert request with metadata."""
        request = VectorUpsertRequest(
            id="vec-1",
            values=[0.2] * 1024,
            metadata=sample_vector_metadata,
        )
        assert request.metadata is not None
        assert request.metadata.document_id == "disease-guide"


class TestUpsertResult:
    """Tests for UpsertResult model."""

    def test_create_upsert_result(self):
        """Test creating upsert result."""
        result = UpsertResult(upserted_count=10)
        assert result.upserted_count == 10

    def test_upserted_count_validation(self):
        """Test upserted_count must be non-negative."""
        with pytest.raises(ValueError):
            UpsertResult(upserted_count=-1)


class TestQueryMatch:
    """Tests for QueryMatch model."""

    def test_create_query_match(self):
        """Test creating query match."""
        match = QueryMatch(
            id="vec-1",
            score=0.95,
            metadata=None,
        )
        assert match.id == "vec-1"
        assert match.score == 0.95
        assert match.metadata is None

    def test_create_with_metadata(self, sample_vector_metadata):
        """Test creating query match with metadata."""
        match = QueryMatch(
            id="vec-1",
            score=0.87,
            metadata=sample_vector_metadata,
        )
        assert match.metadata is not None
        assert match.metadata.domain == "plant_diseases"

    def test_score_validation(self):
        """Test score must be between 0 and 1."""
        with pytest.raises(ValueError):
            QueryMatch(id="vec-1", score=1.5, metadata=None)
        with pytest.raises(ValueError):
            QueryMatch(id="vec-1", score=-0.1, metadata=None)


class TestQueryResult:
    """Tests for QueryResult model."""

    def test_create_empty_result(self):
        """Test creating empty query result."""
        result = QueryResult()
        assert result.matches == []
        assert result.namespace is None
        assert result.count == 0

    def test_create_with_matches(self, sample_vector_metadata):
        """Test creating result with matches."""
        matches = [
            QueryMatch(id="vec-1", score=0.95, metadata=sample_vector_metadata),
            QueryMatch(id="vec-2", score=0.87, metadata=None),
        ]
        result = QueryResult(matches=matches, namespace="knowledge-v1")
        assert result.count == 2
        assert result.namespace == "knowledge-v1"

    def test_count_property(self):
        """Test count property."""
        result = QueryResult(matches=[QueryMatch(id=f"vec-{i}", score=0.9 - i * 0.1, metadata=None) for i in range(5)])
        assert result.count == 5


class TestNamespaceStats:
    """Tests for NamespaceStats model."""

    def test_create_namespace_stats(self):
        """Test creating namespace stats."""
        stats = NamespaceStats(vector_count=1000)
        assert stats.vector_count == 1000

    def test_default_vector_count(self):
        """Test default vector count is 0."""
        stats = NamespaceStats()
        assert stats.vector_count == 0


class TestIndexStats:
    """Tests for IndexStats model."""

    def test_create_index_stats(self):
        """Test creating index stats."""
        stats = IndexStats(
            total_vector_count=5000,
            namespaces={"ns1": NamespaceStats(vector_count=3000), "ns2": NamespaceStats(vector_count=2000)},
            dimension=1024,
        )
        assert stats.total_vector_count == 5000
        assert len(stats.namespaces) == 2
        assert stats.dimension == 1024

    def test_default_values(self):
        """Test default values."""
        stats = IndexStats()
        assert stats.total_vector_count == 0
        assert stats.namespaces == {}
        assert stats.dimension == VECTOR_DIMENSIONS


# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR STORE INITIALIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVectorStoreInitialization:
    """Tests for PineconeVectorStore initialization."""

    def test_store_creation(self, mock_pinecone_settings):
        """Test creating vector store."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        assert store._settings == mock_pinecone_settings
        assert store._client is None
        assert store._index is None
        assert store._index_validated is False

    def test_pinecone_not_configured_raises_error(self, mock_pinecone_settings_disabled):
        """Test that missing API key raises PineconeNotConfiguredError."""
        store = PineconeVectorStore(settings=mock_pinecone_settings_disabled)
        with pytest.raises(PineconeNotConfiguredError):
            store._get_client()


class TestVectorStoreIndexValidation:
    """Tests for index validation."""

    @pytest.mark.asyncio
    async def test_index_validation_success(self, mock_pinecone_settings, mock_pinecone_client):
        """Test successful index validation."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)

        with patch.object(store, "_get_client", return_value=mock_pinecone_client):
            await store._validate_index_exists()

        assert store._index_validated is True

    @pytest.mark.asyncio
    async def test_index_not_found_raises_error(self, mock_pinecone_settings, mock_pinecone_client):
        """Test that missing index raises PineconeIndexNotFoundError."""
        mock_pinecone_client.list_indexes.return_value = []

        store = PineconeVectorStore(settings=mock_pinecone_settings)

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            pytest.raises(PineconeIndexNotFoundError),
        ):
            await store._validate_index_exists()

    @pytest.mark.asyncio
    async def test_index_validation_skips_if_already_validated(self, mock_pinecone_settings, mock_pinecone_client):
        """Test that validation is skipped if already done."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        await store._validate_index_exists()
        mock_pinecone_client.list_indexes.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# UPSERT OPERATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVectorStoreUpsert:
    """Tests for upsert operations."""

    @pytest.mark.asyncio
    async def test_upsert_empty_list(self, mock_pinecone_settings):
        """Test upserting empty list returns zero count."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)

        result = await store.upsert([])

        assert result.upserted_count == 0

    @pytest.mark.asyncio
    async def test_upsert_single_vector(
        self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index, sample_upsert_request
    ):
        """Test upserting a single vector."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            result = await store.upsert([sample_upsert_request], namespace="test-ns")

        assert result.upserted_count == 1
        mock_pinecone_index.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_formats_vectors_correctly(
        self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index, sample_upsert_request
    ):
        """Test that vectors are formatted correctly for Pinecone."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            await store.upsert([sample_upsert_request], namespace="test-ns")

        call_kwargs = mock_pinecone_index.upsert.call_args.kwargs
        vectors = call_kwargs["vectors"]
        assert len(vectors) == 1
        assert vectors[0]["id"] == "disease-guide-0"
        assert len(vectors[0]["values"]) == VECTOR_DIMENSIONS
        assert "metadata" in vectors[0]
        assert vectors[0]["metadata"]["document_id"] == "disease-guide"

    @pytest.mark.asyncio
    async def test_upsert_batch_within_limit(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test upserting batch within 100 vector limit."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        vectors = [
            VectorUpsertRequest(
                id=f"vec-{i}",
                values=[0.1] * VECTOR_DIMENSIONS,
                metadata=None,
            )
            for i in range(50)
        ]

        upsert_response = MagicMock()
        upsert_response.upserted_count = 50
        mock_pinecone_index.upsert.return_value = upsert_response

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            result = await store.upsert(vectors)

        assert result.upserted_count == 50
        assert mock_pinecone_index.upsert.call_count == 1

    @pytest.mark.asyncio
    async def test_upsert_auto_batching(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test that large upserts are automatically batched."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        vectors = [
            VectorUpsertRequest(
                id=f"vec-{i}",
                values=[0.1] * VECTOR_DIMENSIONS,
                metadata=None,
            )
            for i in range(250)
        ]

        def mock_upsert(**kwargs):
            response = MagicMock()
            response.upserted_count = len(kwargs["vectors"])
            return response

        mock_pinecone_index.upsert.side_effect = mock_upsert

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            result = await store.upsert(vectors)

        assert result.upserted_count == 250
        assert mock_pinecone_index.upsert.call_count == 3

    @pytest.mark.asyncio
    async def test_upsert_with_namespace(
        self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index, sample_upsert_request
    ):
        """Test upserting with namespace."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            await store.upsert([sample_upsert_request], namespace="knowledge-v12")

        call_kwargs = mock_pinecone_index.upsert.call_args.kwargs
        assert call_kwargs["namespace"] == "knowledge-v12"


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY OPERATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVectorStoreQuery:
    """Tests for query operations."""

    @pytest.mark.asyncio
    async def test_query_basic(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test basic query operation."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        match1 = MagicMock()
        match1.id = "vec-1"
        match1.score = 0.95
        match1.metadata = {
            "document_id": "doc-1",
            "chunk_id": "chunk-1",
            "chunk_index": 0,
            "domain": "plant_diseases",
            "title": "Test Doc",
        }

        query_response = MagicMock()
        query_response.matches = [match1]
        mock_pinecone_index.query.return_value = query_response

        embedding = [0.1] * VECTOR_DIMENSIONS

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            result = await store.query(embedding, top_k=5)

        assert result.count == 1
        assert result.matches[0].id == "vec-1"
        assert result.matches[0].score == 0.95
        assert result.matches[0].metadata is not None
        assert result.matches[0].metadata.document_id == "doc-1"

    @pytest.mark.asyncio
    async def test_query_with_top_k(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test query with custom top_k."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        embedding = [0.1] * VECTOR_DIMENSIONS

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            await store.query(embedding, top_k=10)

        call_kwargs = mock_pinecone_index.query.call_args.kwargs
        assert call_kwargs["top_k"] == 10

    @pytest.mark.asyncio
    async def test_query_with_filters(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test query with metadata filters."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        embedding = [0.1] * VECTOR_DIMENSIONS
        filters = {"domain": {"$in": ["plant_diseases", "tea_cultivation"]}}

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            await store.query(embedding, top_k=5, filters=filters)

        call_kwargs = mock_pinecone_index.query.call_args.kwargs
        assert call_kwargs["filter"] == filters

    @pytest.mark.asyncio
    async def test_query_with_namespace(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test query with namespace."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        embedding = [0.1] * VECTOR_DIMENSIONS

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            result = await store.query(embedding, namespace="knowledge-v12")

        call_kwargs = mock_pinecone_index.query.call_args.kwargs
        assert call_kwargs["namespace"] == "knowledge-v12"
        assert result.namespace == "knowledge-v12"

    @pytest.mark.asyncio
    async def test_query_includes_metadata(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test that query includes metadata in results."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        embedding = [0.1] * VECTOR_DIMENSIONS

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            await store.query(embedding)

        call_kwargs = mock_pinecone_index.query.call_args.kwargs
        assert call_kwargs["include_metadata"] is True

    @pytest.mark.asyncio
    async def test_query_handles_invalid_metadata(
        self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index
    ):
        """Test query handles invalid metadata gracefully."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        match1 = MagicMock()
        match1.id = "vec-1"
        match1.score = 0.95
        match1.metadata = {"invalid": "metadata"}

        query_response = MagicMock()
        query_response.matches = [match1]
        mock_pinecone_index.query.return_value = query_response

        embedding = [0.1] * VECTOR_DIMENSIONS

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            result = await store.query(embedding)

        assert result.count == 1
        assert result.matches[0].id == "vec-1"
        assert result.matches[0].metadata is None


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE OPERATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVectorStoreDelete:
    """Tests for delete operations."""

    @pytest.mark.asyncio
    async def test_delete_empty_list(self, mock_pinecone_settings):
        """Test deleting empty list returns zero."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)

        result = await store.delete([])

        assert result == 0

    @pytest.mark.asyncio
    async def test_delete_single_id(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test deleting a single vector ID."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            result = await store.delete(["vec-1"])

        assert result == 1
        mock_pinecone_index.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_multiple_ids(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test deleting multiple vector IDs."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        ids = ["vec-1", "vec-2", "vec-3"]

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            result = await store.delete(ids)

        assert result == 3
        call_kwargs = mock_pinecone_index.delete.call_args.kwargs
        assert call_kwargs["ids"] == ids

    @pytest.mark.asyncio
    async def test_delete_with_namespace(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test deleting with namespace."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            await store.delete(["vec-1"], namespace="knowledge-v12")

        call_kwargs = mock_pinecone_index.delete.call_args.kwargs
        assert call_kwargs["namespace"] == "knowledge-v12"

    @pytest.mark.asyncio
    async def test_delete_auto_batching(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test that large deletes are automatically batched."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        ids = [f"vec-{i}" for i in range(2500)]

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            result = await store.delete(ids)

        assert result == 2500
        assert mock_pinecone_index.delete.call_count == 3


class TestVectorStoreDeleteAll:
    """Tests for delete_all operation."""

    @pytest.mark.asyncio
    async def test_delete_all_requires_namespace(self, mock_pinecone_settings):
        """Test that delete_all requires namespace."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)

        with pytest.raises(ValueError, match="Namespace is required"):
            await store.delete_all("")

    @pytest.mark.asyncio
    async def test_delete_all_with_namespace(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test delete_all with valid namespace."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            await store.delete_all("knowledge-v12-staged")

        call_kwargs = mock_pinecone_index.delete.call_args.kwargs
        assert call_kwargs["delete_all"] is True
        assert call_kwargs["namespace"] == "knowledge-v12-staged"


# ═══════════════════════════════════════════════════════════════════════════════
# STATS OPERATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVectorStoreStats:
    """Tests for get_stats operation."""

    @pytest.mark.asyncio
    async def test_get_stats_empty_index(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test getting stats from empty index."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            result = await store.get_stats()

        assert result.total_vector_count == 0
        assert result.namespaces == {}

    @pytest.mark.asyncio
    async def test_get_stats_with_vectors(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test getting stats from index with vectors."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)
        store._index_validated = True

        ns1_stats = MagicMock()
        ns1_stats.vector_count = 1000
        ns2_stats = MagicMock()
        ns2_stats.vector_count = 500

        stats_response = MagicMock()
        stats_response.total_vector_count = 1500
        stats_response.namespaces = {"ns1": ns1_stats, "ns2": ns2_stats}
        stats_response.dimension = 1024
        mock_pinecone_index.describe_index_stats.return_value = stats_response

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            result = await store.get_stats()

        assert result.total_vector_count == 1500
        assert len(result.namespaces) == 2
        assert result.namespaces["ns1"].vector_count == 1000
        assert result.namespaces["ns2"].vector_count == 500
        assert result.dimension == 1024


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR HANDLING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVectorStoreErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_upsert_validates_index(
        self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index, sample_upsert_request
    ):
        """Test that upsert validates index before operation."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            await store.upsert([sample_upsert_request])

        mock_pinecone_client.list_indexes.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_validates_index(self, mock_pinecone_settings, mock_pinecone_client, mock_pinecone_index):
        """Test that query validates index before operation."""
        store = PineconeVectorStore(settings=mock_pinecone_settings)

        embedding = [0.1] * VECTOR_DIMENSIONS

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            patch.object(store, "_get_index", return_value=mock_pinecone_index),
        ):
            await store.query(embedding)

        mock_pinecone_client.list_indexes.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_configured_error_on_upsert(self, mock_pinecone_settings_disabled, sample_upsert_request):
        """Test that upsert raises error when not configured."""
        store = PineconeVectorStore(settings=mock_pinecone_settings_disabled)

        with pytest.raises(PineconeNotConfiguredError):
            await store.upsert([sample_upsert_request])

    @pytest.mark.asyncio
    async def test_not_configured_error_on_query(self, mock_pinecone_settings_disabled):
        """Test that query raises error when not configured."""
        store = PineconeVectorStore(settings=mock_pinecone_settings_disabled)

        embedding = [0.1] * VECTOR_DIMENSIONS

        with pytest.raises(PineconeNotConfiguredError):
            await store.query(embedding)

    @pytest.mark.asyncio
    async def test_index_not_found_error(self, mock_pinecone_settings, mock_pinecone_client):
        """Test that missing index raises PineconeIndexNotFoundError."""
        mock_pinecone_client.list_indexes.return_value = []

        store = PineconeVectorStore(settings=mock_pinecone_settings)

        embedding = [0.1] * VECTOR_DIMENSIONS

        with (
            patch.object(store, "_get_client", return_value=mock_pinecone_client),
            pytest.raises(PineconeIndexNotFoundError),
        ):
            await store.query(embedding)


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH SIZE CONSTANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatchSizeConstants:
    """Tests for batch size constants."""

    def test_upsert_batch_size(self):
        """Test upsert batch size is 100."""
        assert UPSERT_BATCH_SIZE == 100

    def test_delete_batch_size(self):
        """Test delete batch size is 1000."""
        assert DELETE_BATCH_SIZE == 1000
