"""Unit tests for Embedding Service.

Tests cover:
- Single text embedding
- Batch embedding within limit
- Batch embedding exceeding limit (auto-chunking)
- Passage vs query input types
- Retry on transient errors
- Configuration validation

Story 0.75.12: RAG Embedding Configuration (Pinecone Inference)
Story 13.7: Removed cost repository tests - costs now published via DAPR (ADR-016)
"""

from unittest.mock import MagicMock, patch

import pytest
from ai_model.config import Settings
from ai_model.domain.embedding import (
    EmbeddingInputType,
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingUsage,
)
from ai_model.services.embedding_service import (
    EmbeddingBatchError,
    EmbeddingService,
    PineconeNotConfiguredError,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_pinecone_settings(monkeypatch) -> Settings:
    """Create settings with Pinecone configured.

    Uses monkeypatch to set environment variables because pydantic-settings
    with validation_alias reads from environment first, overriding explicit
    constructor values.
    """
    # Set environment variables that validation_alias will read
    monkeypatch.setenv("PINECONE_API_KEY", "test-pinecone-api-key")
    monkeypatch.setenv("PINECONE_ENVIRONMENT", "us-east-1")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "test-index")
    monkeypatch.setenv("PINECONE_EMBEDDING_MODEL", "multilingual-e5-large")

    settings = Settings(
        _env_file=None,  # Disable .env file reading for test isolation
        embedding_batch_size=96,
        embedding_retry_max_attempts=3,
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


# ═══════════════════════════════════════════════════════════════════════════════
# EMBEDDING SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestEmbeddingServiceInitialization:
    """Tests for EmbeddingService initialization."""

    def test_service_creation(self, mock_pinecone_settings):
        """Test creating embedding service."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
        )
        assert service._settings == mock_pinecone_settings

    def test_service_without_dapr_client(self, mock_pinecone_settings):
        """Test creating service without DAPR client."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
            dapr_client=None,
        )
        assert service._dapr_client is None


class TestEmbeddingServiceConfiguration:
    """Tests for configuration validation."""

    def test_pinecone_not_configured_raises_error(self, mock_pinecone_settings_disabled):
        """Test that missing API key raises PineconeNotConfiguredError."""
        service = EmbeddingService(
            settings=mock_pinecone_settings_disabled,
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
    async def test_embed_single_query(self, mock_pinecone_settings, mock_pinecone_client):
        """Test embedding a single query text."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
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
    async def test_embed_single_passage(self, mock_pinecone_settings, mock_pinecone_client):
        """Test embedding a single passage."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
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
    async def test_embed_batch_within_limit(self, mock_pinecone_settings, mock_pinecone_client):
        """Test embedding a batch within the limit."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
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
    async def test_embed_batch_preserves_order(self, mock_pinecone_settings, mock_pinecone_client):
        """Test that batch embedding preserves text order."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
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
    async def test_embed_empty_list_returns_empty_result(self, mock_pinecone_settings):
        """Test that empty input returns empty result without API call."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
        )

        result = await service.embed_texts([])

        assert result.count == 0
        assert result.embeddings == []
        assert result.usage.total_tokens == 0


class TestEmbeddingServiceBatchExceedingLimit:
    """Tests for batch embedding exceeding 96-text limit (auto-chunking)."""

    @pytest.mark.asyncio
    async def test_embed_batch_auto_chunking(self, mock_pinecone_settings, mock_pinecone_client):
        """Test that batches exceeding limit are automatically chunked."""
        # Use small batch size for testing
        mock_pinecone_settings.embedding_batch_size = 10

        service = EmbeddingService(
            settings=mock_pinecone_settings,
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
    async def test_embed_batch_accumulates_tokens(self, mock_pinecone_settings, mock_pinecone_client):
        """Test that token counts are accumulated across batches."""
        mock_pinecone_settings.embedding_batch_size = 5

        service = EmbeddingService(
            settings=mock_pinecone_settings,
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
    async def test_passage_input_type_parameter(self, mock_pinecone_settings, mock_pinecone_client):
        """Test that passage input type is passed correctly to Pinecone."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
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
    async def test_query_input_type_parameter(self, mock_pinecone_settings, mock_pinecone_client):
        """Test that query input type is passed correctly to Pinecone."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
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
    async def test_embed_query_convenience_uses_query_type(self, mock_pinecone_settings, mock_pinecone_client):
        """Test that embed_query convenience method uses query input type."""
        service = EmbeddingService(
            settings=mock_pinecone_settings,
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


class TestEmbeddingServiceErrorHandling:
    """Tests for error handling and retry logic."""

    @pytest.mark.asyncio
    async def test_batch_error_includes_batch_index(self, mock_pinecone_settings, mock_pinecone_client):
        """Test that batch errors include the batch index and original error."""
        mock_pinecone_settings.embedding_batch_size = 5
        mock_pinecone_settings.embedding_retry_max_attempts = 1  # No retries

        service = EmbeddingService(
            settings=mock_pinecone_settings,
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
    async def test_pinecone_not_configured_error(self, mock_pinecone_settings_disabled):
        """Test error when Pinecone is not configured."""
        service = EmbeddingService(
            settings=mock_pinecone_settings_disabled,
        )

        # PineconeNotConfiguredError is wrapped in EmbeddingBatchError
        with pytest.raises(EmbeddingBatchError) as exc_info:
            await service.embed_texts(["Test text"])

        # Original error should be PineconeNotConfiguredError
        assert isinstance(exc_info.value.original_error, PineconeNotConfiguredError)
