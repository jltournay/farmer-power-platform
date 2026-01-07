"""Unit tests for Embedding Service.

Tests cover:
- Single text embedding
- Batch embedding within limit
- Batch embedding exceeding limit (auto-chunking)
- Passage vs query input types
- Retry on transient errors
- Cost event emission
- Configuration validation

Story 0.75.12: RAG Embedding Configuration (Pinecone Inference)
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from ai_model.config import Settings
from ai_model.domain.embedding import (
    EmbeddingCostEvent,
    EmbeddingInputType,
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingUsage,
)
from ai_model.infrastructure.repositories.embedding_cost_repository import (
    EmbeddingCostEventRepository,
)
from ai_model.services.embedding_service import (
    EmbeddingBatchError,
    EmbeddingService,
    PineconeNotConfiguredError,
)
from pydantic import SecretStr

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_pinecone_settings() -> Settings:
    """Create settings with Pinecone configured."""
    settings = Settings(
        pinecone_api_key=SecretStr("test-pinecone-api-key"),
        pinecone_environment="us-east-1",
        pinecone_index_name="test-index",
        pinecone_embedding_model="multilingual-e5-large",
        embedding_batch_size=96,
        embedding_retry_max_attempts=3,
        embedding_retry_backoff_ms=[100, 200, 400],
    )
    return settings


@pytest.fixture
def mock_pinecone_settings_disabled(monkeypatch) -> Settings:
    """Create settings without Pinecone configured.

    Uses monkeypatch to unset PINECONE_API_KEY from environment
    and _env_file=None to disable .env file reading since
    validation_alias would otherwise read from .env file.
    """
    # Unset the environment variable to ensure Settings doesn't read from env
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODEL_PINECONE_API_KEY", raising=False)

    # Disable .env file reading by passing _env_file=None
    settings = Settings(
        _env_file=None,  # Disable .env file reading for this test
        pinecone_api_key=None,  # Not configured
        pinecone_environment="us-east-1",
        pinecone_index_name="test-index",
    )
    return settings


@pytest.fixture
def mock_cost_repository(mock_mongodb_client) -> EmbeddingCostEventRepository:
    """Create mock cost repository."""
    db = mock_mongodb_client["ai_model"]
    return EmbeddingCostEventRepository(db)


@pytest.fixture
def mock_pinecone_embed_response():
    """Create mock Pinecone embed response."""
    response = MagicMock()
    response.data = [
        {"values": [0.1] * 1024},
        {"values": [0.2] * 1024},
    ]
    response.usage = MagicMock()
    response.usage.total_tokens = 150
    return response


@pytest.fixture
def mock_pinecone_client(mock_pinecone_embed_response):
    """Create mock Pinecone client."""
    client = MagicMock()
    client.inference.embed.return_value = mock_pinecone_embed_response
    return client


# ═══════════════════════════════════════════════════════════════════════════════
# EMBEDDING DOMAIN MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestEmbeddingInputType:
    """Tests for EmbeddingInputType enum."""

    def test_passage_value(self):
        """Test passage input type has correct value."""
        assert EmbeddingInputType.PASSAGE.value == "passage"

    def test_query_value(self):
        """Test query input type has correct value."""
        assert EmbeddingInputType.QUERY.value == "query"


class TestEmbeddingRequest:
    """Tests for EmbeddingRequest model."""

    def test_create_with_defaults(self):
        """Test creating request with default values."""
        request = EmbeddingRequest(texts=["Hello world"])
        assert request.texts == ["Hello world"]
        assert request.input_type == EmbeddingInputType.PASSAGE
        assert request.truncate == "END"
        assert request.request_id is None
        assert request.knowledge_domain is None

    def test_create_with_query_input_type(self):
        """Test creating request with query input type."""
        request = EmbeddingRequest(
            texts=["What is the weather?"],
            input_type=EmbeddingInputType.QUERY,
        )
        assert request.input_type == EmbeddingInputType.QUERY

    def test_create_with_all_fields(self):
        """Test creating request with all fields specified."""
        request = EmbeddingRequest(
            texts=["Text 1", "Text 2"],
            input_type=EmbeddingInputType.PASSAGE,
            truncate="NONE",
            request_id="req-123",
            knowledge_domain="agriculture",
        )
        assert request.texts == ["Text 1", "Text 2"]
        assert request.truncate == "NONE"
        assert request.request_id == "req-123"
        assert request.knowledge_domain == "agriculture"

    def test_texts_validation_empty_list(self):
        """Test that empty texts list raises validation error."""
        with pytest.raises(ValueError):
            EmbeddingRequest(texts=[])


class TestEmbeddingResult:
    """Tests for EmbeddingResult model."""

    def test_create_result(self):
        """Test creating embedding result."""
        result = EmbeddingResult(
            embeddings=[[0.1] * 1024, [0.2] * 1024],
            model="multilingual-e5-large",
            dimensions=1024,
            usage=EmbeddingUsage(total_tokens=100),
        )
        assert len(result.embeddings) == 2
        assert result.model == "multilingual-e5-large"
        assert result.dimensions == 1024
        assert result.usage.total_tokens == 100

    def test_count_property(self):
        """Test count property returns number of embeddings."""
        result = EmbeddingResult(
            embeddings=[[0.1] * 1024, [0.2] * 1024, [0.3] * 1024],
            model="multilingual-e5-large",
            dimensions=1024,
        )
        assert result.count == 3


class TestEmbeddingCostEvent:
    """Tests for EmbeddingCostEvent model."""

    def test_create_cost_event(self):
        """Test creating embedding cost event."""
        event = EmbeddingCostEvent(
            id=str(uuid.uuid4()),
            request_id="req-123",
            model="multilingual-e5-large",
            texts_count=10,
            tokens_total=500,
            knowledge_domain="agriculture",
            success=True,
            batch_count=1,
            retry_count=0,
        )
        assert event.texts_count == 10
        assert event.tokens_total == 500
        assert event.success is True

    def test_cost_event_model_dump_for_mongo(self):
        """Test MongoDB serialization."""
        event = EmbeddingCostEvent(
            id="event-123",
            request_id="req-123",
            model="multilingual-e5-large",
            texts_count=5,
            tokens_total=250,
        )
        data = event.model_dump_for_mongo()
        assert data["id"] == "event-123"
        assert data["texts_count"] == 5

    def test_cost_event_from_mongo(self):
        """Test creating event from MongoDB document."""
        doc = {
            "_id": "event-123",
            "id": "event-123",
            "request_id": "req-123",
            "model": "multilingual-e5-large",
            "texts_count": 5,
            "tokens_total": 250,
            "success": True,
            "batch_count": 1,
            "retry_count": 0,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        event = EmbeddingCostEvent.from_mongo(doc)
        assert event.id == "event-123"
        assert event.texts_count == 5


# ═══════════════════════════════════════════════════════════════════════════════
# EMBEDDING SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestEmbeddingServiceInitialization:
    """Tests for EmbeddingService initialization."""

    def test_service_creation(self, mock_pinecone_settings, mock_cost_repository):
        """Test creating embedding service."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=mock_cost_repository,
        )
        assert service._settings == mock_pinecone_settings
        assert service._cost_repository == mock_cost_repository

    def test_service_without_cost_repository(self, mock_pinecone_settings):
        """Test creating service without cost repository."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=None,
        )
        assert service._cost_repository is None


class TestEmbeddingServiceConfiguration:
    """Tests for configuration validation."""

    def test_pinecone_not_configured_raises_error(self, mock_pinecone_settings_disabled):
        """Test that missing API key raises PineconeNotConfiguredError."""
        service = EmbeddingService(
            settings=mock_pinecone_settings_disabled,
            cost_repository=None,
        )
        with pytest.raises(PineconeNotConfiguredError):
            service._get_client()

    def test_pinecone_enabled_property(self, mock_pinecone_settings):
        """Test pinecone_enabled property."""
        assert mock_pinecone_settings.pinecone_enabled is True

    def test_pinecone_disabled_property(self, mock_pinecone_settings_disabled):
        """Test pinecone_enabled property when disabled."""
        assert mock_pinecone_settings_disabled.pinecone_enabled is False


class TestEmbeddingServiceSingleText:
    """Tests for single text embedding."""

    @pytest.mark.asyncio
    async def test_embed_single_query(self, mock_pinecone_settings, mock_cost_repository, mock_pinecone_client):
        """Test embedding a single query text."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=mock_cost_repository,
        )

        # Mock single embedding response
        mock_response = MagicMock()
        mock_response.data = [{"values": [0.1] * 1024}]
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50
        mock_pinecone_client.inference.embed.return_value = mock_response

        with patch.object(service, "_get_client", return_value=mock_pinecone_client):
            result = await service.embed_query("What is the weather?", request_id="req-001")

        assert len(result) == 1024
        assert result[0] == 0.1

    @pytest.mark.asyncio
    async def test_embed_single_passage(self, mock_pinecone_settings, mock_cost_repository, mock_pinecone_client):
        """Test embedding a single passage."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=mock_cost_repository,
        )

        mock_response = MagicMock()
        mock_response.data = [{"values": [0.2] * 1024}]
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 75
        mock_pinecone_client.inference.embed.return_value = mock_response

        with patch.object(service, "_get_client", return_value=mock_pinecone_client):
            results = await service.embed_passages(["This is a document passage."])

        assert len(results) == 1
        assert len(results[0]) == 1024


class TestEmbeddingServiceBatchWithinLimit:
    """Tests for batch embedding within the 96-text limit."""

    @pytest.mark.asyncio
    async def test_embed_batch_within_limit(self, mock_pinecone_settings, mock_cost_repository, mock_pinecone_client):
        """Test embedding a batch within the limit."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=mock_cost_repository,
        )

        texts = ["Text 1", "Text 2", "Text 3"]
        mock_response = MagicMock()
        mock_response.data = [{"values": [0.1] * 1024} for _ in texts]
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 150
        mock_pinecone_client.inference.embed.return_value = mock_response

        with patch.object(service, "_get_client", return_value=mock_pinecone_client):
            result = await service.embed_texts(texts)

        assert result.count == 3
        assert result.dimensions == 1024
        assert result.model == "multilingual-e5-large"

    @pytest.mark.asyncio
    async def test_embed_batch_preserves_order(
        self, mock_pinecone_settings, mock_cost_repository, mock_pinecone_client
    ):
        """Test that batch embedding preserves text order."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=mock_cost_repository,
        )

        texts = ["A", "B", "C"]
        mock_response = MagicMock()
        mock_response.data = [
            {"values": [1.0] * 1024},
            {"values": [2.0] * 1024},
            {"values": [3.0] * 1024},
        ]
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100
        mock_pinecone_client.inference.embed.return_value = mock_response

        with patch.object(service, "_get_client", return_value=mock_pinecone_client):
            result = await service.embed_texts(texts)

        assert result.embeddings[0][0] == 1.0
        assert result.embeddings[1][0] == 2.0
        assert result.embeddings[2][0] == 3.0

    @pytest.mark.asyncio
    async def test_embed_empty_list_returns_empty_result(self, mock_pinecone_settings, mock_cost_repository):
        """Test that empty input returns empty result without API call."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=mock_cost_repository,
        )

        result = await service.embed_texts([])

        assert result.count == 0
        assert result.embeddings == []
        assert result.usage.total_tokens == 0


class TestEmbeddingServiceBatchExceedingLimit:
    """Tests for batch embedding exceeding 96-text limit (auto-chunking)."""

    @pytest.mark.asyncio
    async def test_embed_batch_auto_chunking(self, mock_pinecone_settings, mock_cost_repository, mock_pinecone_client):
        """Test that batches exceeding limit are automatically chunked."""
        # Use small batch size for testing
        mock_pinecone_settings.embedding_batch_size = 10

        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=mock_cost_repository,
        )

        # Create 25 texts (should create 3 batches: 10, 10, 5)
        texts = [f"Text {i}" for i in range(25)]

        def mock_embed_side_effect(*args, **kwargs):
            inputs = kwargs.get("inputs", args[0] if args else [])
            response = MagicMock()
            response.data = [{"values": [0.1] * 1024} for _ in inputs]
            response.usage = MagicMock()
            response.usage.total_tokens = len(inputs) * 10
            return response

        mock_pinecone_client.inference.embed.side_effect = mock_embed_side_effect

        with patch.object(service, "_get_client", return_value=mock_pinecone_client):
            result = await service.embed_texts(texts)

        assert result.count == 25
        # Pinecone embed should be called 3 times (batches of 10, 10, 5)
        assert mock_pinecone_client.inference.embed.call_count == 3

    @pytest.mark.asyncio
    async def test_embed_batch_accumulates_tokens(
        self, mock_pinecone_settings, mock_cost_repository, mock_pinecone_client
    ):
        """Test that token counts are accumulated across batches."""
        mock_pinecone_settings.embedding_batch_size = 5

        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=mock_cost_repository,
        )

        texts = [f"Text {i}" for i in range(12)]  # 3 batches: 5, 5, 2

        call_count = [0]

        def mock_embed_side_effect(*args, **kwargs):
            call_count[0] += 1
            inputs = kwargs.get("inputs", args[0] if args else [])
            response = MagicMock()
            response.data = [{"values": [0.1] * 1024} for _ in inputs]
            response.usage = MagicMock()
            response.usage.total_tokens = 100  # 100 tokens per batch
            return response

        mock_pinecone_client.inference.embed.side_effect = mock_embed_side_effect

        with patch.object(service, "_get_client", return_value=mock_pinecone_client):
            result = await service.embed_texts(texts)

        assert result.count == 12
        # 3 batches * 100 tokens = 300 total tokens
        assert result.usage.total_tokens == 300


class TestEmbeddingServiceInputTypes:
    """Tests for passage vs query input type handling."""

    @pytest.mark.asyncio
    async def test_passage_input_type_parameter(
        self, mock_pinecone_settings, mock_cost_repository, mock_pinecone_client
    ):
        """Test that passage input type is passed correctly to Pinecone."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=mock_cost_repository,
        )

        mock_response = MagicMock()
        mock_response.data = [{"values": [0.1] * 1024}]
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50
        mock_pinecone_client.inference.embed.return_value = mock_response

        with patch.object(service, "_get_client", return_value=mock_pinecone_client):
            await service.embed_texts(
                texts=["Document content"],
                input_type=EmbeddingInputType.PASSAGE,
            )

        # Check that embed was called with passage input_type
        call_kwargs = mock_pinecone_client.inference.embed.call_args
        assert call_kwargs.kwargs["parameters"]["input_type"] == "passage"

    @pytest.mark.asyncio
    async def test_query_input_type_parameter(self, mock_pinecone_settings, mock_cost_repository, mock_pinecone_client):
        """Test that query input type is passed correctly to Pinecone."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=mock_cost_repository,
        )

        mock_response = MagicMock()
        mock_response.data = [{"values": [0.1] * 1024}]
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50
        mock_pinecone_client.inference.embed.return_value = mock_response

        with patch.object(service, "_get_client", return_value=mock_pinecone_client):
            await service.embed_texts(
                texts=["Search query"],
                input_type=EmbeddingInputType.QUERY,
            )

        call_kwargs = mock_pinecone_client.inference.embed.call_args
        assert call_kwargs.kwargs["parameters"]["input_type"] == "query"

    @pytest.mark.asyncio
    async def test_embed_query_convenience_uses_query_type(
        self, mock_pinecone_settings, mock_cost_repository, mock_pinecone_client
    ):
        """Test that embed_query convenience method uses query input type."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=mock_cost_repository,
        )

        mock_response = MagicMock()
        mock_response.data = [{"values": [0.1] * 1024}]
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50
        mock_pinecone_client.inference.embed.return_value = mock_response

        with patch.object(service, "_get_client", return_value=mock_pinecone_client):
            await service.embed_query("What is tea?")

        call_kwargs = mock_pinecone_client.inference.embed.call_args
        assert call_kwargs.kwargs["parameters"]["input_type"] == "query"


class TestEmbeddingServiceCostTracking:
    """Tests for cost event emission."""

    @pytest.mark.asyncio
    async def test_cost_event_recorded_on_success(
        self, mock_pinecone_settings, mock_mongodb_client, mock_pinecone_client
    ):
        """Test that cost event is recorded on successful embedding."""
        db = mock_mongodb_client["ai_model"]
        cost_repository = EmbeddingCostEventRepository(db)

        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=cost_repository,
        )

        mock_response = MagicMock()
        mock_response.data = [{"values": [0.1] * 1024}]
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100
        mock_pinecone_client.inference.embed.return_value = mock_response

        with patch.object(service, "_get_client", return_value=mock_pinecone_client):
            await service.embed_texts(
                texts=["Test text"],
                request_id="req-001",
                knowledge_domain="agriculture",
            )

        # Check cost event was recorded
        events = await cost_repository.get_by_request_id("req-001")
        assert len(events) == 1
        assert events[0].success is True
        assert events[0].texts_count == 1
        assert events[0].knowledge_domain == "agriculture"

    @pytest.mark.asyncio
    async def test_cost_event_recorded_on_failure(
        self, mock_pinecone_settings, mock_mongodb_client, mock_pinecone_client
    ):
        """Test that cost event is recorded on failed embedding."""
        db = mock_mongodb_client["ai_model"]
        cost_repository = EmbeddingCostEventRepository(db)

        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=cost_repository,
        )

        mock_pinecone_client.inference.embed.side_effect = ConnectionError("Network error")

        with (
            patch.object(service, "_get_client", return_value=mock_pinecone_client),
            pytest.raises(EmbeddingBatchError),
        ):
            await service.embed_texts(
                texts=["Test text"],
                request_id="req-fail",
            )

        # Check failure event was recorded
        events = await cost_repository.get_by_request_id("req-fail")
        assert len(events) == 1
        assert events[0].success is False

    @pytest.mark.asyncio
    async def test_no_cost_event_without_repository(self, mock_pinecone_settings, mock_pinecone_client):
        """Test that no error occurs when cost repository is not configured."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=None,  # No repository
        )

        mock_response = MagicMock()
        mock_response.data = [{"values": [0.1] * 1024}]
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50
        mock_pinecone_client.inference.embed.return_value = mock_response

        with patch.object(service, "_get_client", return_value=mock_pinecone_client):
            result = await service.embed_texts(["Test text"])

        # Should succeed without error
        assert result.count == 1


class TestEmbeddingServiceErrorHandling:
    """Tests for error handling and retry logic."""

    @pytest.mark.asyncio
    async def test_batch_error_includes_batch_index(
        self, mock_pinecone_settings, mock_cost_repository, mock_pinecone_client
    ):
        """Test that batch errors include the batch index and original error."""
        mock_pinecone_settings.embedding_batch_size = 5
        mock_pinecone_settings.embedding_retry_max_attempts = 1  # No retries

        service = EmbeddingService(
            settings=mock_pinecone_settings,
            cost_repository=mock_cost_repository,
        )

        # Track batch inputs to fail on specific batch
        def mock_fail_on_second_batch(*args, **kwargs):
            inputs = kwargs.get("inputs", [])
            # Fail if processing batch that starts with "Text 5" (second batch)
            if inputs and inputs[0] == "Text 5":
                raise ValueError("Simulated batch failure")
            response = MagicMock()
            response.data = [{"values": [0.1] * 1024} for _ in inputs]
            response.usage = MagicMock()
            response.usage.total_tokens = 50
            return response

        mock_pinecone_client.inference.embed.side_effect = mock_fail_on_second_batch

        texts = [f"Text {i}" for i in range(12)]  # Will need 3 batches (5, 5, 2)

        with (
            patch.object(service, "_get_client", return_value=mock_pinecone_client),
            pytest.raises(EmbeddingBatchError) as exc_info,
        ):
            await service.embed_texts(texts)

        assert exc_info.value.batch_index == 1  # Second batch (0-indexed)
        assert "Simulated batch failure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pinecone_not_configured_error(self, mock_pinecone_settings_disabled, mock_cost_repository):
        """Test error when Pinecone is not configured."""
        service = EmbeddingService(
            settings=mock_pinecone_settings_disabled,
            cost_repository=mock_cost_repository,
        )

        # PineconeNotConfiguredError is wrapped in EmbeddingBatchError
        with pytest.raises(EmbeddingBatchError) as exc_info:
            await service.embed_texts(["Test text"])

        # Original error should be PineconeNotConfiguredError
        assert isinstance(exc_info.value.original_error, PineconeNotConfiguredError)


# ═══════════════════════════════════════════════════════════════════════════════
# EMBEDDING COST REPOSITORY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestEmbeddingCostEventRepository:
    """Tests for EmbeddingCostEventRepository."""

    @pytest.mark.asyncio
    async def test_insert_and_get_by_id(self, mock_mongodb_client):
        """Test inserting and retrieving a cost event."""
        db = mock_mongodb_client["ai_model"]
        repo = EmbeddingCostEventRepository(db)

        event = EmbeddingCostEvent(
            id="event-123",
            request_id="req-123",
            model="multilingual-e5-large",
            texts_count=10,
            tokens_total=500,
            success=True,
        )

        await repo.insert(event)
        retrieved = await repo.get_by_id("event-123")

        assert retrieved is not None
        assert retrieved.id == "event-123"
        assert retrieved.texts_count == 10

    @pytest.mark.asyncio
    async def test_get_by_request_id(self, mock_mongodb_client):
        """Test retrieving events by request ID."""
        db = mock_mongodb_client["ai_model"]
        repo = EmbeddingCostEventRepository(db)

        # Insert multiple events with same request ID
        for i in range(3):
            event = EmbeddingCostEvent(
                id=f"event-{i}",
                request_id="req-multi",
                model="multilingual-e5-large",
                texts_count=i + 1,
                tokens_total=(i + 1) * 50,
            )
            await repo.insert(event)

        events = await repo.get_by_request_id("req-multi")
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_ensure_indexes(self, mock_mongodb_client):
        """Test that ensure_indexes runs without error."""
        db = mock_mongodb_client["ai_model"]
        repo = EmbeddingCostEventRepository(db)

        # Should not raise
        await repo.ensure_indexes()
