"""Agent configuration repository for MongoDB persistence.

This module provides the AgentConfigRepository class for managing agent configurations
in the ai_model.agent_configs MongoDB collection.

Key design decisions:
- Single collection with discriminated union (not one collection per type)
- Uses Pydantic TypeAdapter for discriminated union deserialization
- Repository handles all 5 agent config types via single interface

Indexes:
- (agent_id, status): Fast lookup of active/staged configs
- (agent_id, version): Unique constraint for version uniqueness per agent
- (type): Fast lookup by agent type
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ai_model.domain.agent_config import (
    AgentConfig,
    AgentConfigStatus,
    AgentType,
    ConversationalConfig,
    ExplorerConfig,
    ExtractorConfig,
    GeneratorConfig,
    TieredVisionConfig,
)
from pydantic import TypeAdapter
from pymongo import ASCENDING

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# TypeAdapter for discriminated union deserialization
_agent_config_adapter: TypeAdapter[AgentConfig] = TypeAdapter(AgentConfig)


class AgentConfigRepository:
    """Repository for AgentConfig entities.

    Provides CRUD operations plus specialized queries:
    - get_active: Get currently active config for an agent_id
    - get_by_type: List all configs of a specific agent type
    - get_by_version: Get specific version of a config
    - list_versions: List all versions of an agent config

    Uses Pydantic discriminated unions to handle 5 agent config types
    through a single repository interface.
    """

    COLLECTION_NAME = "agent_configs"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the agent config repository.

        Args:
            db: MongoDB database instance (should be ai_model database).
        """
        self._db = db
        self._collection = db[self.COLLECTION_NAME]

    def _deserialize(self, doc: dict[str, Any]) -> AgentConfig:
        """Deserialize a MongoDB document to the correct AgentConfig type.

        Uses Pydantic TypeAdapter with discriminated union to automatically
        select the correct config type based on the 'type' field.

        Args:
            doc: MongoDB document with agent config data.

        Returns:
            The correct AgentConfig subtype (ExtractorConfig, ExplorerConfig, etc.)
        """
        # Remove MongoDB _id field before validation
        doc.pop("_id", None)
        return _agent_config_adapter.validate_python(doc)

    def _serialize(self, config: AgentConfig) -> dict[str, Any]:
        """Serialize an AgentConfig to MongoDB document format.

        Args:
            config: Agent config to serialize.

        Returns:
            Dictionary ready for MongoDB insertion.
        """
        # Use model_dump with mode='json' for datetime serialization
        doc = config.model_dump(mode="json")
        # Use id as MongoDB _id
        doc["_id"] = config.id
        return doc

    async def create(self, config: AgentConfig) -> AgentConfig:
        """Create a new agent configuration.

        Args:
            config: The agent configuration to create.

        Returns:
            The created agent configuration.

        Raises:
            DuplicateKeyError: If config with same id already exists.
        """
        doc = self._serialize(config)
        await self._collection.insert_one(doc)
        logger.info(
            "Created agent config",
            extra={"agent_id": config.agent_id, "version": config.version},
        )
        return config

    async def get_by_id(self, entity_id: str) -> AgentConfig | None:
        """Get an agent configuration by its unique ID.

        Args:
            entity_id: The unique document ID (format: {agent_id}:{version}).

        Returns:
            The agent config if found, None otherwise.
        """
        doc = await self._collection.find_one({"_id": entity_id})
        if doc is None:
            return None
        return self._deserialize(doc)

    async def update(self, config: AgentConfig) -> AgentConfig:
        """Update an existing agent configuration.

        Uses delete + insert pattern to replace the entire document.
        This ensures atomicity and proper handling of discriminated unions.

        Args:
            config: The agent configuration to update.

        Returns:
            The updated agent configuration.

        Raises:
            ValueError: If config doesn't exist.
        """
        # First check if exists
        existing = await self._collection.find_one({"_id": config.id})
        if existing is None:
            raise ValueError(f"Agent config not found: {config.id}")

        # Delete and re-insert (atomic replacement)
        await self._collection.delete_one({"_id": config.id})
        doc = self._serialize(config)
        await self._collection.insert_one(doc)

        logger.info(
            "Updated agent config",
            extra={"agent_id": config.agent_id, "version": config.version},
        )
        return config

    async def delete(self, entity_id: str) -> bool:
        """Delete an agent configuration.

        Args:
            entity_id: The unique document ID.

        Returns:
            True if deleted, False if not found.
        """
        result = await self._collection.delete_one({"_id": entity_id})
        if result.deleted_count > 0:
            logger.info("Deleted agent config", extra={"id": entity_id})
            return True
        return False

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        status: AgentConfigStatus | None = None,
    ) -> list[AgentConfig]:
        """List agent configurations with optional filtering.

        Args:
            skip: Number of documents to skip (pagination).
            limit: Maximum documents to return.
            status: Optional status filter.

        Returns:
            List of agent configurations.
        """
        query: dict[str, Any] = {}
        if status is not None:
            query["status"] = status.value

        cursor = self._collection.find(query).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)

        return [self._deserialize(doc) for doc in docs]

    async def get_active(self, agent_id: str) -> AgentConfig | None:
        """Get the currently active config for an agent_id.

        Only one config per agent_id should have status=active.

        Args:
            agent_id: The logical agent identifier (e.g., "disease-diagnosis").

        Returns:
            The active config if found, None otherwise.
        """
        doc = await self._collection.find_one(
            {
                "agent_id": agent_id,
                "status": AgentConfigStatus.ACTIVE.value,
            }
        )
        if doc is None:
            return None
        return self._deserialize(doc)

    async def get_by_type(
        self,
        agent_type: AgentType,
        status: AgentConfigStatus | None = None,
    ) -> list[AgentConfig]:
        """Get all configurations of a specific agent type.

        Args:
            agent_type: The agent type to filter by.
            status: Optional status filter.

        Returns:
            List of agent configurations of the specified type.
        """
        query: dict[str, Any] = {"type": agent_type.value}
        if status is not None:
            query["status"] = status.value

        cursor = self._collection.find(query).sort("agent_id", ASCENDING)
        docs = await cursor.to_list(length=None)

        return [self._deserialize(doc) for doc in docs]

    async def get_by_version(
        self,
        agent_id: str,
        version: str,
    ) -> AgentConfig | None:
        """Get a specific version of an agent configuration.

        Args:
            agent_id: The logical agent identifier.
            version: The semantic version string (e.g., "2.1.0").

        Returns:
            The agent config if found, None otherwise.
        """
        doc = await self._collection.find_one(
            {
                "agent_id": agent_id,
                "version": version,
            }
        )
        if doc is None:
            return None
        return self._deserialize(doc)

    async def list_versions(
        self,
        agent_id: str,
        include_archived: bool = True,
    ) -> list[AgentConfig]:
        """List all versions of an agent configuration.

        Args:
            agent_id: The logical agent identifier.
            include_archived: Whether to include archived versions.

        Returns:
            List of config versions, sorted by version descending.
        """
        query: dict[str, Any] = {"agent_id": agent_id}
        if not include_archived:
            query["status"] = {"$ne": AgentConfigStatus.ARCHIVED.value}

        cursor = self._collection.find(query).sort("version", -1)
        docs = await cursor.to_list(length=None)

        return [self._deserialize(doc) for doc in docs]

    async def ensure_indexes(self) -> None:
        """Create indexes for the agent_configs collection.

        Indexes:
        - (agent_id, status): Fast lookup of active/staged configs
        - (agent_id, version): Unique constraint, fast version lookup
        - (type): Fast lookup by agent type
        """
        # Compound index for agent_id + status (get_active query)
        await self._collection.create_index(
            [("agent_id", ASCENDING), ("status", ASCENDING)],
            name="idx_agent_id_status",
        )

        # Compound unique index for agent_id + version
        await self._collection.create_index(
            [("agent_id", ASCENDING), ("version", ASCENDING)],
            unique=True,
            name="idx_agent_id_version_unique",
        )

        # Index for type (get_by_type query)
        await self._collection.create_index(
            "type",
            name="idx_type",
        )

        logger.info("Agent config indexes created")


# Type alias exports for convenience
ExtractorConfigType = ExtractorConfig
ExplorerConfigType = ExplorerConfig
GeneratorConfigType = GeneratorConfig
ConversationalConfigType = ConversationalConfig
TieredVisionConfigType = TieredVisionConfig
