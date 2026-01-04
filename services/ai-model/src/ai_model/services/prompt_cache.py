"""Prompt cache with MongoDB Change Streams.

Story 0.75.4: Implements in-memory caching for prompts
with automatic invalidation via Change Streams (ADR-013).

Supports A/B testing by allowing lookup of staged prompts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from ai_model.domain.prompt import Prompt
from fp_common.cache import MongoChangeStreamCache

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = structlog.get_logger(__name__)


class PromptCache(MongoChangeStreamCache[Prompt]):
    """Prompt cache with Change Stream invalidation.

    Caches prompts from the `prompts` collection.
    Supports A/B testing via staged prompt lookups.

    Features (inherited from MongoChangeStreamCache):
    - Startup cache warming before accepting requests
    - Change Stream watcher for real-time invalidation
    - Resume token persistence for resilient reconnection
    - OpenTelemetry metrics: prompt_cache_hits_total, etc.

    Domain-specific features:
    - get_prompt(): Lookup active prompt by agent_id
    - get_prompt_for_ab_test(): Support A/B test variant selection
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the prompt cache.

        Args:
            db: MongoDB database instance.
        """
        super().__init__(
            db=db,
            collection_name="prompts",
            cache_name="prompt",
        )

    # -------------------------------------------------------------------------
    # Abstract Method Implementations (required by MongoChangeStreamCache)
    # -------------------------------------------------------------------------

    def _get_cache_key(self, item: Prompt) -> str:
        """Extract cache key from Prompt.

        Uses agent_id as the key since there's typically one active
        prompt per agent.

        Args:
            item: Prompt instance.

        Returns:
            The agent_id as cache key.
        """
        return item.agent_id

    def _parse_document(self, doc: dict) -> Prompt:
        """Parse MongoDB document to Prompt model.

        Args:
            doc: MongoDB document dict.

        Returns:
            Parsed Prompt instance.
        """
        # Remove MongoDB _id if present
        doc.pop("_id", None)
        return Prompt.model_validate(doc)

    def _get_filter(self) -> dict:
        """Get MongoDB filter for loading active prompts only.

        Returns:
            Filter for active prompts.
        """
        return {"status": "active"}

    # -------------------------------------------------------------------------
    # Domain-Specific Methods
    # -------------------------------------------------------------------------

    async def get_prompt(self, agent_id: str) -> Prompt | None:
        """Get active prompt for an agent.

        Args:
            agent_id: Agent identifier (e.g., "disease-diagnosis").

        Returns:
            Prompt instance or None if not found.
        """
        return await self.get(agent_id)

    async def get_prompt_for_ab_test(
        self,
        agent_id: str,
        use_staged: bool = False,
    ) -> Prompt | None:
        """Get prompt with A/B test variant support.

        When use_staged is True, fetches the staged prompt for the agent
        (if one exists) instead of the active prompt. Staged prompts are
        fetched directly from MongoDB (not cached) since A/B tests are
        temporary.

        Args:
            agent_id: Agent identifier.
            use_staged: If True, return staged prompt; otherwise active.

        Returns:
            Prompt instance or None if not found.
        """
        if not use_staged:
            return await self.get(agent_id)

        # Staged prompts are queried fresh (not cached)
        # A/B tests are temporary, so caching staged prompts adds complexity
        doc = await self._collection.find_one(
            {
                "agent_id": agent_id,
                "status": "staged",
            }
        )
        if doc:
            doc.pop("_id", None)
            return Prompt.model_validate(doc)
        return None
