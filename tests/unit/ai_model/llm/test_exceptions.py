"""Unit tests for LLM exceptions.

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

from ai_model.llm.exceptions import (
    AllModelsUnavailableError,
    LLMError,
    ModelUnavailableError,
    RateLimitExceededError,
    TransientError,
)


class TestLLMError:
    """Tests for base LLMError exception."""

    def test_llm_error_message(self) -> None:
        """Test LLMError stores message correctly."""
        error = LLMError("Test error message")
        assert error.message == "Test error message"
        assert str(error) == "Test error message"

    def test_llm_error_with_cause(self) -> None:
        """Test LLMError stores cause correctly."""
        cause = ValueError("Original error")
        error = LLMError("Wrapped error", cause=cause)
        assert error.cause is cause
        assert "caused by" in str(error)

    def test_llm_error_without_cause(self) -> None:
        """Test LLMError without cause."""
        error = LLMError("No cause")
        assert error.cause is None
        assert "caused by" not in str(error)


class TestTransientError:
    """Tests for TransientError exception."""

    def test_transient_error_status_code(self) -> None:
        """Test TransientError stores status code."""
        error = TransientError("Rate limited", status_code=429)
        assert error.status_code == 429
        assert error.message == "Rate limited"

    def test_transient_error_with_cause(self) -> None:
        """Test TransientError with cause."""
        cause = ConnectionError("Connection reset")
        error = TransientError("Server error", status_code=503, cause=cause)
        assert error.status_code == 503
        assert error.cause is cause

    def test_transient_error_inheritance(self) -> None:
        """Test TransientError inherits from LLMError."""
        error = TransientError("Test", status_code=500)
        assert isinstance(error, LLMError)


class TestModelUnavailableError:
    """Tests for ModelUnavailableError exception."""

    def test_model_unavailable_error_model(self) -> None:
        """Test ModelUnavailableError stores model."""
        error = ModelUnavailableError(
            "Model not found",
            model="anthropic/claude-3-5-sonnet",
        )
        assert error.model == "anthropic/claude-3-5-sonnet"
        assert error.message == "Model not found"

    def test_model_unavailable_error_inheritance(self) -> None:
        """Test ModelUnavailableError inherits from LLMError."""
        error = ModelUnavailableError("Test", model="test-model")
        assert isinstance(error, LLMError)


class TestAllModelsUnavailableError:
    """Tests for AllModelsUnavailableError exception."""

    def test_all_models_unavailable_error_models(self) -> None:
        """Test AllModelsUnavailableError stores attempted models."""
        models = ["model-1", "model-2", "model-3"]
        error = AllModelsUnavailableError(
            "All models failed",
            attempted_models=models,
        )
        assert error.attempted_models == models
        assert error.message == "All models failed"

    def test_all_models_unavailable_error_inheritance(self) -> None:
        """Test AllModelsUnavailableError inherits from LLMError."""
        error = AllModelsUnavailableError("Test", attempted_models=[])
        assert isinstance(error, LLMError)


class TestRateLimitExceededError:
    """Tests for RateLimitExceededError exception."""

    def test_rate_limit_exceeded_error_properties(self) -> None:
        """Test RateLimitExceededError stores properties."""
        error = RateLimitExceededError(
            "RPM limit exceeded",
            limit_type="rpm",
            limit_value=60,
            retry_after_seconds=5.0,
        )
        assert error.limit_type == "rpm"
        assert error.limit_value == 60
        assert error.retry_after_seconds == 5.0

    def test_rate_limit_exceeded_error_no_retry_after(self) -> None:
        """Test RateLimitExceededError without retry_after."""
        error = RateLimitExceededError(
            "TPM limit exceeded",
            limit_type="tpm",
            limit_value=100000,
        )
        assert error.retry_after_seconds is None

    def test_rate_limit_exceeded_error_inheritance(self) -> None:
        """Test RateLimitExceededError inherits from LLMError."""
        error = RateLimitExceededError("Test", limit_type="rpm", limit_value=60)
        assert isinstance(error, LLMError)
