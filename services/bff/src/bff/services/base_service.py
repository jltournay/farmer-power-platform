"""Base service class for BFF services.

Provides common patterns for service composition per ADR-012:
- Bounded parallel execution with semaphore
- Structured logging with service context
- Error handling patterns
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import structlog

T = TypeVar("T")
R = TypeVar("R")


class BaseService:
    """Base class for BFF services.

    Provides:
    - _parallel_map(): Bounded parallel execution using Semaphore(5)
    - _logger: Structured logger with service context

    Usage:
        class FarmerService(BaseService):
            async def enrich_farmers(self, farmers: list[Farmer]) -> list[FarmerSummary]:
                return await self._parallel_map(farmers, self._enrich_single)
    """

    def __init__(self) -> None:
        """Initialize the base service with structured logging."""
        self._logger = structlog.get_logger(self.__class__.__name__)

    async def _parallel_map(
        self,
        items: list[T],
        func: Callable[[T], Awaitable[R]],
        max_concurrent: int = 5,
    ) -> list[R]:
        """Execute async function on each item with bounded concurrency.

        Uses asyncio.Semaphore to limit parallel calls and prevent
        overwhelming downstream services.

        Args:
            items: List of items to process.
            func: Async function to apply to each item.
            max_concurrent: Maximum concurrent calls (default: 5 per ADR-012).

        Returns:
            List of results in the same order as input items.

        Example:
            >>> async def fetch_performance(farmer_id: str) -> FarmerPerformance:
            ...     return await client.get_farmer_summary(farmer_id)
            >>> performances = await self._parallel_map(farmer_ids, fetch_performance)
        """
        if not items:
            return []

        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_call(item: T) -> R:
            async with semaphore:
                return await func(item)

        return await asyncio.gather(*[bounded_call(item) for item in items])
