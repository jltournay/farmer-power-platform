"""LLM-specific exceptions for the AI Model service.

This module defines the exception hierarchy for LLM operations:
- LLMError: Base exception for all LLM-related errors
- TransientError: Retryable errors (429, 5xx status codes)
- ModelUnavailableError: Model-specific failures (triggers fallback)
- AllModelsUnavailableError: Entire fallback chain exhausted
- RateLimitExceededError: Rate limit breaches

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""


class LLMError(Exception):
    """Base exception for all LLM-related errors.

    All LLM errors inherit from this class to allow for broad exception
    handling when needed.
    """

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            cause: Optional underlying exception that caused this error.
        """
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class TransientError(LLMError):
    """Retryable transient errors from OpenRouter.

    These errors should trigger automatic retry with backoff:
    - 429: Rate limited by the provider
    - 500: Internal server error
    - 502: Bad gateway
    - 503: Service unavailable
    - 504: Gateway timeout

    The retry decorator should handle these automatically.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code that triggered this error.
            cause: Optional underlying exception.
        """
        super().__init__(message, cause=cause)
        self.status_code = status_code


class ModelUnavailableError(LLMError):
    """Error when a specific model is unavailable or failed.

    This error triggers the fallback chain to try the next model.
    Examples:
    - Model not found in OpenRouter
    - Model temporarily unavailable
    - Context window exceeded for this model
    - Model-specific rate limits hit
    """

    def __init__(
        self,
        message: str,
        *,
        model: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            model: The model identifier that failed.
            cause: Optional underlying exception.
        """
        super().__init__(message, cause=cause)
        self.model = model


class AllModelsUnavailableError(LLMError):
    """Error when the entire fallback chain has been exhausted.

    This is a terminal error that cannot be recovered from through
    retry or fallback. The caller must handle this gracefully.
    """

    def __init__(
        self,
        message: str,
        *,
        attempted_models: list[str],
        cause: Exception | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            attempted_models: List of all models that were tried.
            cause: Optional underlying exception from the last attempt.
        """
        super().__init__(message, cause=cause)
        self.attempted_models = attempted_models


class RateLimitExceededError(LLMError):
    """Error when local rate limits are exceeded.

    This error is raised by the local rate limiter, not OpenRouter.
    It indicates that the caller should wait before making more requests.
    """

    def __init__(
        self,
        message: str,
        *,
        limit_type: str,
        limit_value: int,
        retry_after_seconds: float | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            limit_type: Type of limit exceeded ("rpm" or "tpm").
            limit_value: The configured limit value.
            retry_after_seconds: Suggested wait time before retrying.
        """
        super().__init__(message)
        self.limit_type = limit_type
        self.limit_value = limit_value
        self.retry_after_seconds = retry_after_seconds
