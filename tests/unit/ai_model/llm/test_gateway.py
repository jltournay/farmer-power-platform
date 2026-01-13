"""Unit tests for LLMGateway.

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
Story 13.7: Updated to reflect DAPR-based cost publishing (ADR-016)
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai_model.llm.exceptions import (
    AllModelsUnavailableError,
    LLMError,
    RateLimitExceededError,
)
from ai_model.llm.gateway import DEFAULT_RETRY_MAX_ATTEMPTS, GenerationStats, LLMGateway
from ai_model.llm.rate_limiter import RateLimiter
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, LLMResult


class TestGenerationStats:
    """Tests for GenerationStats class."""

    def test_create_generation_stats(self) -> None:
        """Test creating generation stats."""
        stats = GenerationStats(
            generation_id="gen-123",
            native_tokens_prompt=100,
            native_tokens_completion=50,
            total_cost=Decimal("0.00175"),
            model="anthropic/claude-3-5-sonnet",
        )

        assert stats.generation_id == "gen-123"
        assert stats.native_tokens_prompt == 100
        assert stats.native_tokens_completion == 50
        assert stats.total_cost == Decimal("0.00175")
        assert stats.model == "anthropic/claude-3-5-sonnet"

    def test_total_tokens_property(self) -> None:
        """Test total_tokens property calculation."""
        stats = GenerationStats(
            generation_id="gen-123",
            native_tokens_prompt=100,
            native_tokens_completion=50,
            total_cost=Decimal("0.00175"),
            model="test-model",
        )

        assert stats.total_tokens == 150


class TestLLMGatewayInitialization:
    """Tests for LLMGateway initialization."""

    def test_initialization_with_defaults(self) -> None:
        """Test gateway initializes with default values."""
        gateway = LLMGateway(api_key="test-key")

        assert gateway._fallback_models == []
        assert gateway._rate_limiter is None
        assert gateway._retry_max_attempts == DEFAULT_RETRY_MAX_ATTEMPTS
        # Story 13.7: No dapr_client means cost publishing is disabled
        assert gateway._dapr_client is None

    def test_initialization_with_fallback_models(self) -> None:
        """Test gateway initializes with fallback models."""
        gateway = LLMGateway(
            api_key="test-key",
            fallback_models=["openai/gpt-4o", "google/gemini-pro"],
        )

        assert gateway._fallback_models == ["openai/gpt-4o", "google/gemini-pro"]

    def test_initialization_with_rate_limiter(self) -> None:
        """Test gateway initializes with rate limiter."""
        rate_limiter = RateLimiter(rpm=60, tpm=100000)
        gateway = LLMGateway(
            api_key="test-key",
            rate_limiter=rate_limiter,
        )

        assert gateway._rate_limiter is rate_limiter

    def test_initialization_with_custom_retry(self) -> None:
        """Test gateway initializes with custom retry settings."""
        gateway = LLMGateway(
            api_key="test-key",
            retry_max_attempts=5,
            retry_backoff_ms=[50, 100, 500],
        )

        assert gateway._retry_max_attempts == 5
        assert gateway._retry_backoff_ms == [50, 100, 500]

    def test_initialization_with_dapr_client(self) -> None:
        """Test gateway initializes with DAPR client for cost publishing (Story 13.7)."""
        mock_dapr_client = MagicMock()
        gateway = LLMGateway(
            api_key="test-key",
            dapr_client=mock_dapr_client,
            pubsub_name="my-pubsub",
            cost_topic="cost.recorded",
        )

        assert gateway._dapr_client is mock_dapr_client
        assert gateway._pubsub_name == "my-pubsub"
        assert gateway._cost_topic == "cost.recorded"


class TestLLMGatewayValidateModels:
    """Tests for validate_models method."""

    @pytest.fixture
    def gateway(self) -> LLMGateway:
        """Create a gateway for testing."""
        return LLMGateway(api_key="test-key")

    @pytest.mark.asyncio
    async def test_validate_models_success(self, gateway: LLMGateway) -> None:
        """Test successful model validation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "anthropic/claude-3-5-sonnet"},
                {"id": "openai/gpt-4o"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(gateway, "_get_http_client", return_value=mock_client):
            models = await gateway.validate_models()

        assert len(models) == 2
        assert "anthropic/claude-3-5-sonnet" in models
        assert gateway._available_models == {"anthropic/claude-3-5-sonnet", "openai/gpt-4o"}

    @pytest.mark.asyncio
    async def test_validate_models_http_error(self, gateway: LLMGateway) -> None:
        """Test model validation with HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with (
            patch.object(gateway, "_get_http_client", return_value=mock_client),
            pytest.raises(LLMError) as exc_info,
        ):
            await gateway.validate_models()

        assert "Failed to fetch OpenRouter models" in str(exc_info.value)


class TestLLMGatewayComplete:
    """Tests for complete method."""

    @pytest.fixture
    def gateway(self) -> LLMGateway:
        """Create a gateway for testing (no DAPR client = no cost publishing)."""
        return LLMGateway(
            api_key="test-key",
            fallback_models=["openai/gpt-4o"],
        )

    @pytest.fixture
    def sample_messages(self) -> list[HumanMessage]:
        """Create sample messages."""
        return [HumanMessage(content="Hello, how are you?")]

    @pytest.fixture
    def mock_llm_result(self) -> LLMResult:
        """Create a mock LLM result (agenerate returns LLMResult)."""
        generation = ChatGeneration(
            message=AIMessage(content="I'm doing well, thank you!"),
            text="I'm doing well, thank you!",
            generation_info={
                "id": "gen-123",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 8,
                },
            },
        )
        # agenerate returns LLMResult with generations as list of lists
        return LLMResult(generations=[[generation]])

    @pytest.mark.asyncio
    async def test_complete_success(
        self,
        gateway: LLMGateway,
        sample_messages: list[HumanMessage],
        mock_llm_result: LLMResult,
    ) -> None:
        """Test successful completion."""
        mock_chat_client = AsyncMock()
        mock_chat_client.agenerate = AsyncMock(return_value=mock_llm_result)

        with patch.object(gateway, "_create_chat_client", return_value=mock_chat_client):
            result = await gateway.complete(
                messages=sample_messages,
                model="anthropic/claude-3-5-sonnet",
                agent_id="test-agent",
                agent_type="extractor",
            )

        assert result["content"] == "I'm doing well, thank you!"
        assert result["generation_id"] == "gen-123"
        assert result["success"] is True
        assert result["retry_count"] == 0

    @pytest.mark.asyncio
    async def test_complete_with_rate_limiter(
        self,
        sample_messages: list[HumanMessage],
        mock_llm_result: LLMResult,
    ) -> None:
        """Test completion respects rate limiter."""
        mock_rate_limiter = AsyncMock(spec=RateLimiter)
        mock_rate_limiter.acquire_request = AsyncMock(return_value=True)
        mock_rate_limiter.acquire_tokens = AsyncMock(return_value=True)

        gateway = LLMGateway(
            api_key="test-key",
            rate_limiter=mock_rate_limiter,
        )

        mock_chat_client = AsyncMock()
        mock_chat_client.agenerate = AsyncMock(return_value=mock_llm_result)

        with patch.object(gateway, "_create_chat_client", return_value=mock_chat_client):
            await gateway.complete(messages=sample_messages, model="test-model")

        mock_rate_limiter.acquire_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_rate_limit_exceeded(
        self,
        sample_messages: list[HumanMessage],
    ) -> None:
        """Test completion fails when rate limit exceeded."""
        mock_rate_limiter = AsyncMock(spec=RateLimiter)
        mock_rate_limiter.acquire_request = AsyncMock(
            side_effect=RateLimitExceededError(
                "Rate limit exceeded",
                limit_type="rpm",
                limit_value=60,
            )
        )

        gateway = LLMGateway(
            api_key="test-key",
            rate_limiter=mock_rate_limiter,
        )

        with pytest.raises(RateLimitExceededError):
            await gateway.complete(messages=sample_messages, model="test-model")

    @pytest.mark.asyncio
    async def test_complete_fallback_on_model_unavailable(
        self,
        gateway: LLMGateway,
        sample_messages: list[HumanMessage],
        mock_llm_result: LLMResult,
    ) -> None:
        """Test fallback is used when primary model unavailable."""
        # First call fails with ModelUnavailableError, second succeeds
        mock_chat_client = AsyncMock()
        mock_chat_client.agenerate = AsyncMock(
            side_effect=[
                Exception("model not found"),  # Primary fails
                mock_llm_result,  # Fallback succeeds
            ]
        )

        with patch.object(gateway, "_create_chat_client", return_value=mock_chat_client):
            result = await gateway.complete(
                messages=sample_messages,
                model="anthropic/claude-3-5-sonnet",
            )

        # Should succeed with fallback
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_complete_all_models_fail(
        self,
        gateway: LLMGateway,
        sample_messages: list[HumanMessage],
    ) -> None:
        """Test AllModelsUnavailableError when all models fail."""
        mock_chat_client = AsyncMock()
        mock_chat_client.agenerate = AsyncMock(side_effect=Exception("model unavailable"))

        with (
            patch.object(gateway, "_create_chat_client", return_value=mock_chat_client),
            pytest.raises(AllModelsUnavailableError) as exc_info,
        ):
            await gateway.complete(
                messages=sample_messages,
                model="anthropic/claude-3-5-sonnet",
            )

        # Should have tried primary + fallback
        assert len(exc_info.value.attempted_models) == 2
        assert "anthropic/claude-3-5-sonnet" in exc_info.value.attempted_models
        assert "openai/gpt-4o" in exc_info.value.attempted_models


class TestLLMGatewayRetry:
    """Tests for retry behavior."""

    @pytest.fixture
    def gateway(self) -> LLMGateway:
        """Create a gateway with retry settings."""
        return LLMGateway(
            api_key="test-key",
            retry_max_attempts=3,
            retry_backoff_ms=[10, 20, 50],  # Fast for tests
        )

    @pytest.fixture
    def sample_messages(self) -> list[HumanMessage]:
        """Create sample messages."""
        return [HumanMessage(content="Test")]

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(
        self,
        gateway: LLMGateway,
        sample_messages: list[HumanMessage],
    ) -> None:
        """Test retry on transient 503 error."""
        success_generation = ChatGeneration(
            message=AIMessage(content="Success"),
            text="Success",
            generation_info={"id": "gen-123", "usage": {}},
        )
        success_result = LLMResult(generations=[[success_generation]])

        mock_chat_client = AsyncMock()
        mock_chat_client.agenerate = AsyncMock(
            side_effect=[
                Exception("503 Service Unavailable"),  # First attempt fails
                success_result,  # Second attempt succeeds
            ]
        )

        with patch.object(gateway, "_create_chat_client", return_value=mock_chat_client):
            result = await gateway.complete(
                messages=sample_messages,
                model="test-model",
            )

        assert result["success"] is True
        assert result["retry_count"] == 1


class TestLLMGatewayGenerationStats:
    """Tests for generation stats fetching."""

    @pytest.fixture
    def gateway(self) -> LLMGateway:
        """Create a gateway with DAPR client for cost publishing (Story 13.7)."""
        mock_dapr_client = MagicMock()
        return LLMGateway(
            api_key="test-key",
            dapr_client=mock_dapr_client,
        )

    @pytest.mark.asyncio
    async def test_get_generation_stats_success(self, gateway: LLMGateway) -> None:
        """Test successful generation stats fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "native_tokens_prompt": 100,
            "native_tokens_completion": 50,
            "total_cost": 0.00175,
            "model": "anthropic/claude-3-5-sonnet",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(gateway, "_get_http_client", return_value=mock_client):
            stats = await gateway._get_generation_stats("gen-123")

        assert stats is not None
        assert stats.native_tokens_prompt == 100
        assert stats.native_tokens_completion == 50
        assert stats.total_cost == Decimal("0.00175")

    @pytest.mark.asyncio
    async def test_get_generation_stats_not_available(self, gateway: LLMGateway) -> None:
        """Test generation stats returns None when not available."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(gateway, "_get_http_client", return_value=mock_client):
            stats = await gateway._get_generation_stats("gen-123")

        assert stats is None

    @pytest.mark.asyncio
    async def test_get_generation_stats_no_dapr_client(self) -> None:
        """Test generation stats returns None when no DAPR client (Story 13.7)."""
        gateway = LLMGateway(api_key="test-key")  # No dapr_client

        stats = await gateway._get_generation_stats("gen-123")

        assert stats is None


class TestLLMGatewayContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Test context manager closes HTTP client on exit."""
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        async with LLMGateway(api_key="test-key") as gateway:
            # Set the mock client
            gateway._http_client = mock_client

        # Client's aclose should have been called
        mock_client.aclose.assert_called_once()
        # Client reference is cleared after close
        assert gateway._http_client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self) -> None:
        """Test close is safe when no client exists."""
        gateway = LLMGateway(api_key="test-key")

        # Should not raise
        await gateway.close()

        assert gateway._http_client is None
