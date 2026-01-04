"""Agent configuration cache with MongoDB Change Streams.

Story 0.75.4: Implements in-memory caching for agent configurations
with automatic invalidation via Change Streams (ADR-013).

The AgentConfig is a discriminated union of 5 agent types, requiring
TypeAdapter for proper deserialization from MongoDB documents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from ai_model.domain.agent_config import (
    AgentConfig,
    AgentType,
)
from fp_common.cache import MongoChangeStreamCache
from pydantic import TypeAdapter

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = structlog.get_logger(__name__)

# TypeAdapter for discriminated union deserialization
# This handles the 5 agent types: extractor, explorer, generator, conversational, tiered-vision
_agent_config_adapter = TypeAdapter(AgentConfig)


class AgentConfigCache(MongoChangeStreamCache[AgentConfig]):
    """Agent configuration cache with Change Stream invalidation.

    Caches agent configs from the `agent_configs` collection.
    Uses TypeAdapter for proper discriminated union deserialization.

    Features (inherited from MongoChangeStreamCache):
    - Startup cache warming before accepting requests
    - Change Stream watcher for real-time invalidation
    - Resume token persistence for resilient reconnection
    - OpenTelemetry metrics: agent_config_cache_hits_total, etc.

    Domain-specific features:
    - get_config(): Lookup by agent_id
    - get_configs_by_type(): Filter configs by agent type
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the agent config cache.

        Args:
            db: MongoDB database instance.
        """
        super().__init__(
            db=db,
            collection_name="agent_configs",
            cache_name="agent_config",
        )

    # -------------------------------------------------------------------------
    # Abstract Method Implementations (required by MongoChangeStreamCache)
    # -------------------------------------------------------------------------

    def _get_cache_key(self, item: AgentConfig) -> str:
        """Extract cache key from AgentConfig.

        Args:
            item: AgentConfig instance (any of the 5 types).

        Returns:
            The agent_id as cache key.
        """
        return item.agent_id

    def _parse_document(self, doc: dict) -> AgentConfig:
        """Parse MongoDB document to AgentConfig using discriminated union.

        Uses TypeAdapter to correctly deserialize to the specific agent type
        (ExtractorConfig, ExplorerConfig, GeneratorConfig, etc.) based on
        the "type" discriminator field.

        Args:
            doc: MongoDB document dict.

        Returns:
            Parsed AgentConfig instance (specific type).
        """
        # Remove MongoDB _id if present
        doc.pop("_id", None)
        return _agent_config_adapter.validate_python(doc)

    def _get_filter(self) -> dict:
        """Get MongoDB filter for loading active configs only.

        Returns:
            Filter for active configs.
        """
        return {"status": "active"}

    # -------------------------------------------------------------------------
    # Domain-Specific Methods
    # -------------------------------------------------------------------------

    async def get_config(self, agent_id: str) -> AgentConfig | None:
        """Get agent config by agent_id.

        Args:
            agent_id: Agent identifier (e.g., "disease-diagnosis").

        Returns:
            AgentConfig instance or None if not found.
        """
        return await self.get(agent_id)

    async def get_configs_by_type(self, agent_type: AgentType) -> list[AgentConfig]:
        """Get all configs of a specific agent type.

        Args:
            agent_type: AgentType enum value.

        Returns:
            List of configs matching the type.
        """
        all_configs = await self.get_all()
        return [config for config in all_configs.values() if config.type == agent_type.value]
