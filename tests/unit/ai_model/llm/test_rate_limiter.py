"""Unit tests for token bucket rate limiter.

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

import asyncio
import time

import pytest
from ai_model.llm.exceptions import RateLimitExceededError
from ai_model.llm.rate_limiter import RateLimiter, TokenBucket


class TestTokenBucket:
    """Tests for TokenBucket class."""

    @pytest.fixture
    def bucket(self) -> TokenBucket:
        """Create a token bucket with 10 capacity, 10/sec refill."""
        return TokenBucket(capacity=10, refill_rate=10.0, name="test")

    @pytest.mark.asyncio
    async def test_acquire_succeeds_when_under_limit(self, bucket: TokenBucket) -> None:
        """Test acquire succeeds when tokens are available."""
        result = await bucket.acquire(tokens=5)
        assert result is True
        assert bucket.available_tokens < 10

    @pytest.mark.asyncio
    async def test_acquire_multiple_succeeds(self, bucket: TokenBucket) -> None:
        """Test multiple acquires succeed when under limit."""
        await bucket.acquire(tokens=3)
        await bucket.acquire(tokens=3)
        await bucket.acquire(tokens=3)
        # Should have used 9 tokens, ~1 remaining
        assert bucket.available_tokens < 2

    @pytest.mark.asyncio
    async def test_acquire_raises_when_exceeded_no_wait(self, bucket: TokenBucket) -> None:
        """Test acquire raises when limit exceeded with wait=False."""
        # Drain the bucket
        await bucket.acquire(tokens=10)

        with pytest.raises(RateLimitExceededError) as exc_info:
            await bucket.acquire(tokens=1, wait=False)

        assert exc_info.value.limit_type == "test"
        assert exc_info.value.limit_value == 10

    @pytest.mark.asyncio
    async def test_acquire_waits_when_exceeded_wait_true(self, bucket: TokenBucket) -> None:
        """Test acquire waits for tokens when wait=True."""
        # Use a fast-refill bucket for this test
        fast_bucket = TokenBucket(capacity=2, refill_rate=100.0, name="fast")

        # Drain the bucket
        await fast_bucket.acquire(tokens=2)

        # This should wait and then succeed
        start = time.monotonic()
        result = await fast_bucket.acquire(tokens=1, wait=True)
        elapsed = time.monotonic() - start

        assert result is True
        assert elapsed > 0  # Had to wait

    @pytest.mark.asyncio
    async def test_acquire_timeout_exceeded(self, bucket: TokenBucket) -> None:
        """Test acquire raises when timeout exceeded."""
        # Create slow refill bucket
        slow_bucket = TokenBucket(capacity=10, refill_rate=0.1, name="slow")
        await slow_bucket.acquire(tokens=10)

        with pytest.raises(RateLimitExceededError):
            await slow_bucket.acquire(tokens=5, wait=True, timeout_seconds=0.1)

    @pytest.mark.asyncio
    async def test_token_refill_over_time(self) -> None:
        """Test tokens refill over time."""
        # 10 tokens per second
        bucket = TokenBucket(capacity=10, refill_rate=10.0, name="refill_test")

        # Drain the bucket
        await bucket.acquire(tokens=10)
        assert bucket.available_tokens < 1

        # Wait for refill
        await asyncio.sleep(0.5)  # Should add ~5 tokens

        # Should be able to acquire again
        result = await bucket.acquire(tokens=3, wait=False)
        assert result is True


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.fixture
    def rate_limiter(self) -> RateLimiter:
        """Create a rate limiter with 60 RPM and 1000 TPM."""
        return RateLimiter(rpm=60, tpm=1000)

    @pytest.mark.asyncio
    async def test_acquire_request_succeeds(self, rate_limiter: RateLimiter) -> None:
        """Test acquire_request succeeds."""
        result = await rate_limiter.acquire_request()
        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_tokens_succeeds(self, rate_limiter: RateLimiter) -> None:
        """Test acquire_tokens succeeds."""
        result = await rate_limiter.acquire_tokens(100)
        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_both_succeeds(self, rate_limiter: RateLimiter) -> None:
        """Test acquire (both RPM and TPM) succeeds."""
        result = await rate_limiter.acquire(estimated_tokens=100)
        assert result is True

    @pytest.mark.asyncio
    async def test_rpm_limit_exceeded(self) -> None:
        """Test RPM limit is enforced."""
        # Create limiter with only 2 RPM
        limiter = RateLimiter(rpm=2, tpm=100000)

        # Use up the RPM
        await limiter.acquire_request()
        await limiter.acquire_request()

        # Third request should fail
        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.acquire_request(wait=False)

        assert exc_info.value.limit_type == "rpm"

    @pytest.mark.asyncio
    async def test_tpm_limit_exceeded(self) -> None:
        """Test TPM limit is enforced."""
        # Create limiter with only 100 TPM
        limiter = RateLimiter(rpm=1000, tpm=100)

        # Use up the TPM
        await limiter.acquire_tokens(100)

        # Next token request should fail
        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.acquire_tokens(50, wait=False)

        assert exc_info.value.limit_type == "tpm"

    @pytest.mark.asyncio
    async def test_rpm_and_tpm_independent(self) -> None:
        """Test RPM and TPM are tracked independently."""
        limiter = RateLimiter(rpm=5, tpm=1000)

        # Make 5 requests using 100 tokens each
        for _ in range(5):
            await limiter.acquire(estimated_tokens=100)

        # RPM should be exhausted, but TPM still has capacity
        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.acquire_request(wait=False)

        assert exc_info.value.limit_type == "rpm"

    def test_get_status(self, rate_limiter: RateLimiter) -> None:
        """Test get_status returns current state."""
        status = rate_limiter.get_status()
        assert "rpm_available" in status
        assert "rpm_limit" in status
        assert "tpm_available" in status
        assert "tpm_limit" in status
        assert status["rpm_limit"] == 60
        assert status["tpm_limit"] == 1000

    def test_limits_properties(self, rate_limiter: RateLimiter) -> None:
        """Test rpm_limit and tpm_limit properties."""
        assert rate_limiter.rpm_limit == 60
        assert rate_limiter.tpm_limit == 1000
