"""LLM Gateway for unified LLM access with retry, fallback, and cost tracking.

This module provides the LLMGateway class that wraps ChatOpenRouter to add:
- Tenacity retry with exponential backoff for transient errors
- Fallback chain to try multiple models
- Cost tracking via OpenRouter Generation Stats API
- Rate limiting integration
- OpenTelemetry metrics

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

import uuid
from decimal import Decimal
from typing import Any

import httpx
import structlog
from ai_model.llm.chat_openrouter import (
    DEFAULT_MODEL,
    DEFAULT_SITE_NAME,
    DEFAULT_SITE_URL,
    OPENROUTER_BASE_URL,
    ChatOpenRouter,
)
from ai_model.llm.exceptions import (
    AllModelsUnavailableError,
    LLMError,
    ModelUnavailableError,
    TransientError,
)
from ai_model.llm.rate_limiter import RateLimiter
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from opentelemetry import metrics
from pydantic import SecretStr
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

# OpenTelemetry metrics
meter = metrics.get_meter(__name__)
llm_request_cost_histogram = meter.create_histogram(
    name="llm_request_cost_usd",
    description="Cost per LLM request in USD",
    unit="usd",
)
llm_tokens_counter = meter.create_counter(
    name="llm_tokens_total",
    description="Total tokens processed",
    unit="tokens",
)
llm_retry_counter = meter.create_counter(
    name="llm_retry_total",
    description="Total LLM retries",
    unit="1",
)
llm_fallback_counter = meter.create_counter(
    name="llm_fallback_total",
    description="Total fallback model activations",
    unit="1",
)

# Retry configuration defaults
DEFAULT_RETRY_MAX_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF_MS = [100, 500, 2000]

# Transient error status codes
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class GenerationStats:
    """Statistics from OpenRouter's Generation Stats API."""

    def __init__(
        self,
        generation_id: str,
        native_tokens_prompt: int,
        native_tokens_completion: int,
        total_cost: Decimal,
        model: str,
    ) -> None:
        """Initialize generation stats.

        Args:
            generation_id: Unique generation identifier.
            native_tokens_prompt: Native token count for prompt (billing tokens).
            native_tokens_completion: Native token count for completion.
            total_cost: Total cost in USD (from OpenRouter billing).
            model: Model that processed the request.
        """
        self.generation_id = generation_id
        self.native_tokens_prompt = native_tokens_prompt
        self.native_tokens_completion = native_tokens_completion
        self.total_cost = total_cost
        self.model = model

    @property
    def total_tokens(self) -> int:
        """Return total tokens (prompt + completion)."""
        return self.native_tokens_prompt + self.native_tokens_completion


class LLMGateway:
    """Unified LLM Gateway with retry, fallback, and cost tracking.

    This class wraps ChatOpenRouter to provide enterprise-grade features:
    - Automatic retry with exponential backoff for transient errors
    - Fallback chain to try multiple models when primary fails
    - Cost tracking via OpenRouter Generation Stats API
    - Rate limiting for RPM and TPM
    - OpenTelemetry metrics for observability

    Example:
        ```python
        gateway = LLMGateway(
            api_key=settings.openrouter_api_key,
            fallback_models=["openai/gpt-4o", "google/gemini-pro"],
            rate_limiter=rate_limiter,
        )

        # Complete with automatic retry and fallback
        result = await gateway.complete(
            messages=messages,
            model="anthropic/claude-3-5-sonnet",
            agent_id="disease-diagnosis",
            agent_type="explorer",
        )
        ```
    """

    def __init__(
        self,
        api_key: str | SecretStr,
        fallback_models: list[str] | None = None,
        rate_limiter: RateLimiter | None = None,
        retry_max_attempts: int = DEFAULT_RETRY_MAX_ATTEMPTS,
        retry_backoff_ms: list[int] | None = None,
        site_url: str = DEFAULT_SITE_URL,
        site_name: str = DEFAULT_SITE_NAME,
        cost_tracking_enabled: bool = True,
    ) -> None:
        """Initialize the LLM Gateway.

        Args:
            api_key: OpenRouter API key.
            fallback_models: List of fallback models to try if primary fails.
            rate_limiter: Rate limiter instance for RPM/TPM limiting.
            retry_max_attempts: Maximum retry attempts for transient errors.
            retry_backoff_ms: Backoff delays in milliseconds [100, 500, 2000].
            site_url: Site URL for OpenRouter identification.
            site_name: Site name for OpenRouter identification.
            cost_tracking_enabled: Whether to track costs via Generation Stats API.
        """
        self._api_key = api_key if isinstance(api_key, SecretStr) else SecretStr(api_key)
        self._fallback_models = fallback_models or []
        self._rate_limiter = rate_limiter
        self._retry_max_attempts = retry_max_attempts
        self._retry_backoff_ms = retry_backoff_ms or DEFAULT_RETRY_BACKOFF_MS
        self._site_url = site_url
        self._site_name = site_name
        self._cost_tracking_enabled = cost_tracking_enabled
        self._http_client: httpx.AsyncClient | None = None
        self._available_models: set[str] = set()

        logger.info(
            "LLM Gateway initialized",
            fallback_models=self._fallback_models,
            retry_max_attempts=self._retry_max_attempts,
            cost_tracking_enabled=self._cost_tracking_enabled,
        )

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client for API calls."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=OPENROUTER_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key.get_secret_value()}",
                    "HTTP-Referer": self._site_url,
                    "X-Title": self._site_name,
                },
                timeout=30.0,
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def validate_models(self) -> list[str]:
        """Validate model availability via OpenRouter /models API.

        Fetches the list of available models from OpenRouter and stores
        them for validation during requests.

        Returns:
            List of available model IDs.

        Raises:
            LLMError: If the models API call fails.
        """
        client = await self._get_http_client()
        try:
            response = await client.get("/models")
            response.raise_for_status()
            data = response.json()

            models = [m["id"] for m in data.get("data", [])]
            self._available_models = set(models)

            logger.info(
                "Validated OpenRouter models",
                model_count=len(models),
            )
            return models

        except httpx.HTTPStatusError as e:
            raise LLMError(
                f"Failed to fetch OpenRouter models: {e.response.status_code}",
                cause=e,
            ) from e
        except Exception as e:
            raise LLMError(f"Failed to validate models: {e}", cause=e) from e

    def _create_chat_client(self, model: str, **kwargs: Any) -> ChatOpenRouter:
        """Create a ChatOpenRouter client for the specified model."""
        return ChatOpenRouter(
            model=model,
            openai_api_key=self._api_key.get_secret_value(),
            site_url=self._site_url,
            site_name=self._site_name,
            **kwargs,
        )

    async def _get_generation_stats(self, generation_id: str) -> GenerationStats | None:
        """Fetch generation stats from OpenRouter for accurate cost.

        The generation stats endpoint returns native token counts and
        actual billing cost, which differ from the normalized counts
        in the chat completion response.

        Args:
            generation_id: The generation ID from the chat completion response.

        Returns:
            GenerationStats if successful, None if not available.
        """
        if not self._cost_tracking_enabled:
            return None

        client = await self._get_http_client()

        # Retry with backoff - generation ID may not be immediately available
        retry_delays = [0.1, 0.2, 0.5]  # 100ms, 200ms, 500ms

        for attempt, delay in enumerate(retry_delays):
            if attempt > 0:
                import asyncio

                await asyncio.sleep(delay)

            try:
                response = await client.get(f"/generation?id={generation_id}")

                if response.status_code == 404:
                    logger.debug(
                        "Generation not yet available, retrying",
                        generation_id=generation_id,
                        attempt=attempt + 1,
                    )
                    continue

                response.raise_for_status()
                data = response.json()

                return GenerationStats(
                    generation_id=generation_id,
                    native_tokens_prompt=data.get("native_tokens_prompt", 0),
                    native_tokens_completion=data.get("native_tokens_completion", 0),
                    total_cost=Decimal(str(data.get("total_cost", 0))),
                    model=data.get("model", ""),
                )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    continue
                logger.warning(
                    "Failed to fetch generation stats",
                    generation_id=generation_id,
                    status_code=e.response.status_code,
                )
                return None
            except Exception as e:
                logger.warning(
                    "Error fetching generation stats",
                    generation_id=generation_id,
                    error=str(e),
                )
                return None

        logger.warning(
            "Generation stats not available after retries",
            generation_id=generation_id,
        )
        return None

    async def _complete_with_retry(
        self,
        model: str,
        messages: list[BaseMessage],
        **kwargs: Any,
    ) -> tuple[ChatResult, int]:
        """Complete with Tenacity retry for transient errors.

        Args:
            model: Model identifier to use.
            messages: List of messages for the chat completion.
            **kwargs: Additional arguments for ChatOpenRouter.

        Returns:
            Tuple of (ChatResult, retry_count).

        Raises:
            TransientError: If all retries exhausted for transient errors.
            ModelUnavailableError: If model is unavailable or context exceeded.
        """
        client = self._create_chat_client(model, **kwargs)
        retry_count = 0

        # Calculate backoff parameters from milliseconds
        min_wait = self._retry_backoff_ms[0] / 1000 if self._retry_backoff_ms else 0.1
        max_wait = self._retry_backoff_ms[-1] / 1000 if self._retry_backoff_ms else 2.0

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._retry_max_attempts),
                wait=wait_exponential(multiplier=0.1, min=min_wait, max=max_wait),
                retry=retry_if_exception_type((TransientError,)),
                reraise=True,
            ):
                with attempt:
                    try:
                        result = await client.agenerate([messages])
                        return result, retry_count
                    except Exception as e:
                        error_msg = str(e).lower()

                        # Check for transient errors
                        if any(code in error_msg for code in ["429", "500", "502", "503", "504"]):
                            retry_count += 1
                            llm_retry_counter.add(1, {"model": model})
                            logger.warning(
                                "Transient error, retrying",
                                model=model,
                                attempt=retry_count,
                                error=str(e),
                            )
                            # Extract status code if possible
                            status_code = 500
                            for code in TRANSIENT_STATUS_CODES:
                                if str(code) in error_msg:
                                    status_code = code
                                    break
                            raise TransientError(
                                f"Transient error from OpenRouter: {e}",
                                status_code=status_code,
                                cause=e,
                            ) from e

                        # Check for model-specific errors
                        if any(
                            term in error_msg
                            for term in [
                                "model not found",
                                "context length",
                                "context_length_exceeded",
                                "model unavailable",
                            ]
                        ):
                            raise ModelUnavailableError(
                                f"Model {model} unavailable: {e}",
                                model=model,
                                cause=e,
                            ) from e

                        # Re-raise other errors
                        raise

        except RetryError as e:
            # All retries exhausted
            raise TransientError(
                f"All {self._retry_max_attempts} retries exhausted for model {model}",
                status_code=500,
                cause=e.last_attempt.exception() if e.last_attempt else None,
            ) from e

        # This should not be reached
        raise LLMError(f"Unexpected error in retry loop for model {model}")

    async def complete(
        self,
        messages: list[BaseMessage],
        model: str = DEFAULT_MODEL,
        agent_id: str = "",
        agent_type: str = "",
        request_id: str | None = None,
        factory_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Complete a chat request with retry and fallback.

        This is the main entry point for LLM requests. It handles:
        1. Rate limiting (if configured)
        2. Retry with exponential backoff for transient errors
        3. Fallback to alternative models if primary fails
        4. Cost tracking via Generation Stats API
        5. OpenTelemetry metrics

        Args:
            messages: List of messages for the chat completion.
            model: Primary model to use.
            agent_id: ID of the agent making the request.
            agent_type: Type of agent (extractor, explorer, generator, etc.).
            request_id: Correlation ID for tracing (generated if not provided).
            factory_id: Optional factory ID for cost attribution.
            **kwargs: Additional arguments for ChatOpenRouter.

        Returns:
            Dictionary with:
            - content: The generated text content.
            - generation_id: OpenRouter generation ID.
            - model: Actual model used (may differ if fallback triggered).
            - tokens_in: Native input token count.
            - tokens_out: Native output token count.
            - cost_usd: Total cost in USD (Decimal).
            - retry_count: Number of retries before success.

        Raises:
            AllModelsUnavailableError: If all models (primary + fallbacks) fail.
            RateLimitExceededError: If rate limits exceeded.
            LLMError: For other unrecoverable errors.
        """
        request_id = request_id or str(uuid.uuid4())

        # Rate limiting
        if self._rate_limiter:
            await self._rate_limiter.acquire_request()

        # Build model list: primary + fallbacks
        models_to_try = [model, *self._fallback_models]
        attempted_models: list[str] = []
        last_error: Exception | None = None

        for idx, current_model in enumerate(models_to_try):
            attempted_models.append(current_model)

            if idx > 0:
                llm_fallback_counter.add(1, {"from_model": model, "to_model": current_model})
                logger.info(
                    "Falling back to alternative model",
                    from_model=model,
                    to_model=current_model,
                    attempt=idx + 1,
                )

            try:
                result, retry_count = await self._complete_with_retry(
                    model=current_model,
                    messages=messages,
                    **kwargs,
                )

                # Extract response content
                generation = result.generations[0][0]
                if not isinstance(generation, ChatGeneration):
                    raise LLMError("Unexpected response type from LLM")

                content = generation.text
                response_metadata = generation.generation_info or {}

                # Get generation ID for cost tracking
                generation_id = response_metadata.get("id", "")

                # Fetch accurate cost from Generation Stats API
                stats = await self._get_generation_stats(generation_id) if generation_id else None

                if stats:
                    tokens_in = stats.native_tokens_prompt
                    tokens_out = stats.native_tokens_completion
                    cost_usd = stats.total_cost
                    actual_model = stats.model or current_model
                else:
                    # Fallback to normalized counts from response
                    usage = response_metadata.get("usage", {})
                    tokens_in = usage.get("prompt_tokens", 0)
                    tokens_out = usage.get("completion_tokens", 0)
                    cost_usd = Decimal("0")  # Cannot calculate without generation stats
                    actual_model = current_model

                # Record metrics
                llm_tokens_counter.add(tokens_in, {"model": actual_model, "direction": "in"})
                llm_tokens_counter.add(tokens_out, {"model": actual_model, "direction": "out"})
                if cost_usd > 0:
                    llm_request_cost_histogram.record(
                        float(cost_usd),
                        {"model": actual_model, "agent_type": agent_type},
                    )

                # Consume tokens from rate limiter
                if self._rate_limiter:
                    await self._rate_limiter.acquire_tokens(tokens_in + tokens_out, wait=False)

                logger.info(
                    "LLM request completed",
                    model=actual_model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=str(cost_usd),
                    retry_count=retry_count,
                    request_id=request_id,
                    agent_id=agent_id,
                )

                return {
                    "content": content,
                    "generation_id": generation_id,
                    "model": actual_model,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_usd": cost_usd,
                    "retry_count": retry_count,
                    "request_id": request_id,
                    "success": True,
                }

            except ModelUnavailableError as e:
                last_error = e
                logger.warning(
                    "Model unavailable, trying fallback",
                    model=current_model,
                    error=str(e),
                )
                continue

            except TransientError as e:
                last_error = e
                logger.warning(
                    "Transient error after retries, trying fallback",
                    model=current_model,
                    error=str(e),
                )
                continue

        # All models failed
        raise AllModelsUnavailableError(
            f"All {len(attempted_models)} models failed: {attempted_models}",
            attempted_models=attempted_models,
            cause=last_error,
        )

    async def __aenter__(self) -> "LLMGateway":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
