"""Token bucket rate limiter for LLM requests.

This module implements a token bucket algorithm for rate limiting:
- RPM (Requests Per Minute): Limits the number of requests
- TPM (Tokens Per Minute): Limits the total tokens processed

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

import asyncio
import time
from typing import Final

import structlog
from ai_model.llm.exceptions import RateLimitExceededError
from opentelemetry import metrics

logger = structlog.get_logger(__name__)

# OpenTelemetry metrics
meter = metrics.get_meter(__name__)
rate_limit_exceeded_counter = meter.create_counter(
    name="llm_rate_limit_exceeded_total",
    description="Total number of rate limit exceeded events",
    unit="1",
)


class TokenBucket:
    """Token bucket implementation for rate limiting.

    Tokens are added to the bucket at a fixed rate and consumed when
    requests are made. If the bucket is empty, requests must wait.
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        name: str = "bucket",
    ) -> None:
        """Initialize the token bucket.

        Args:
            capacity: Maximum number of tokens the bucket can hold.
            refill_rate: Tokens added per second.
            name: Name for logging purposes.
        """
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._name = name
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    @property
    def capacity(self) -> int:
        """Return the bucket capacity."""
        return self._capacity

    @property
    def available_tokens(self) -> float:
        """Return the current number of available tokens (without refilling)."""
        return self._tokens

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    async def acquire(
        self,
        tokens: int = 1,
        *,
        wait: bool = True,
        timeout_seconds: float | None = None,
    ) -> bool:
        """Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire.
            wait: If True, wait for tokens to become available.
                  If False, return immediately if not available.
            timeout_seconds: Maximum time to wait for tokens.

        Returns:
            True if tokens were acquired, False if not available and wait=False.

        Raises:
            RateLimitExceededError: If wait=False and tokens not available,
                or if timeout exceeded.
        """
        async with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True

            if not wait:
                # Calculate when tokens will be available
                needed = tokens - self._tokens
                retry_after = needed / self._refill_rate if self._refill_rate > 0 else None
                raise RateLimitExceededError(
                    f"Rate limit exceeded: {self._name} bucket has {self._tokens:.1f} tokens, need {tokens}",
                    limit_type=self._name,
                    limit_value=self._capacity,
                    retry_after_seconds=retry_after,
                )

        # Wait for tokens
        start_time = time.monotonic()
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

            # Check timeout
            if timeout_seconds is not None:
                elapsed = time.monotonic() - start_time
                if elapsed >= timeout_seconds:
                    raise RateLimitExceededError(
                        f"Rate limit timeout: waited {elapsed:.1f}s for {self._name} tokens",
                        limit_type=self._name,
                        limit_value=self._capacity,
                        retry_after_seconds=None,
                    )

            # Wait a short time before retrying
            await asyncio.sleep(0.05)  # 50ms polling interval


# Constants for rate limiter configuration
DEFAULT_RPM: Final[int] = 60
DEFAULT_TPM: Final[int] = 100000
SECONDS_PER_MINUTE: Final[float] = 60.0


class RateLimiter:
    """Combined RPM and TPM rate limiter for LLM requests.

    This class manages two independent token buckets:
    - RPM bucket: One token consumed per request
    - TPM bucket: Tokens consumed = input_tokens + output_tokens

    Both limits must be satisfied for a request to proceed.
    """

    def __init__(
        self,
        rpm: int = DEFAULT_RPM,
        tpm: int = DEFAULT_TPM,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            rpm: Requests per minute limit.
            tpm: Tokens per minute limit.
        """
        self._rpm_bucket = TokenBucket(
            capacity=rpm,
            refill_rate=rpm / SECONDS_PER_MINUTE,
            name="rpm",
        )
        self._tpm_bucket = TokenBucket(
            capacity=tpm,
            refill_rate=tpm / SECONDS_PER_MINUTE,
            name="tpm",
        )
        logger.info(
            "Rate limiter initialized",
            rpm=rpm,
            tpm=tpm,
        )

    @property
    def rpm_limit(self) -> int:
        """Return the RPM limit."""
        return self._rpm_bucket.capacity

    @property
    def tpm_limit(self) -> int:
        """Return the TPM limit."""
        return self._tpm_bucket.capacity

    async def acquire_request(
        self,
        *,
        wait: bool = True,
        timeout_seconds: float | None = None,
    ) -> bool:
        """Acquire permission to make a request (1 RPM token).

        This should be called before making an LLM request.
        Token consumption for the response should be tracked separately
        via consume_tokens().

        Args:
            wait: If True, wait for tokens. If False, fail immediately.
            timeout_seconds: Maximum wait time.

        Returns:
            True if request is allowed.

        Raises:
            RateLimitExceededError: If rate limit exceeded.
        """
        try:
            return await self._rpm_bucket.acquire(
                tokens=1,
                wait=wait,
                timeout_seconds=timeout_seconds,
            )
        except RateLimitExceededError:
            rate_limit_exceeded_counter.add(1, {"limit_type": "rpm"})
            raise

    async def acquire_tokens(
        self,
        tokens: int,
        *,
        wait: bool = True,
        timeout_seconds: float | None = None,
    ) -> bool:
        """Acquire token budget (TPM tokens).

        This can be called:
        - Before a request with estimated tokens
        - After a request with actual tokens used

        Args:
            tokens: Number of tokens to acquire.
            wait: If True, wait for tokens. If False, fail immediately.
            timeout_seconds: Maximum wait time.

        Returns:
            True if tokens acquired.

        Raises:
            RateLimitExceededError: If rate limit exceeded.
        """
        try:
            return await self._tpm_bucket.acquire(
                tokens=tokens,
                wait=wait,
                timeout_seconds=timeout_seconds,
            )
        except RateLimitExceededError:
            rate_limit_exceeded_counter.add(1, {"limit_type": "tpm"})
            raise

    async def acquire(
        self,
        estimated_tokens: int = 0,
        *,
        wait: bool = True,
        timeout_seconds: float | None = None,
    ) -> bool:
        """Acquire both RPM and TPM tokens for a request.

        Args:
            estimated_tokens: Estimated tokens for the request.
                              If 0, only RPM is checked upfront.
            wait: If True, wait for tokens. If False, fail immediately.
            timeout_seconds: Maximum wait time.

        Returns:
            True if all limits satisfied.

        Raises:
            RateLimitExceededError: If any rate limit exceeded.
        """
        await self.acquire_request(wait=wait, timeout_seconds=timeout_seconds)

        if estimated_tokens > 0:
            await self.acquire_tokens(
                estimated_tokens,
                wait=wait,
                timeout_seconds=timeout_seconds,
            )

        return True

    def get_status(self) -> dict[str, float]:
        """Get current rate limiter status.

        Returns:
            Dictionary with available tokens for each bucket.
        """
        return {
            "rpm_available": self._rpm_bucket.available_tokens,
            "rpm_limit": self._rpm_bucket.capacity,
            "tpm_available": self._tpm_bucket.available_tokens,
            "tpm_limit": self._tpm_bucket.capacity,
        }
