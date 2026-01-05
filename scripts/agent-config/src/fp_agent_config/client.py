"""MongoDB client for agent configuration operations.

This module provides the AgentConfigClient class for managing agent configurations
in the ai_model.agent_configs MongoDB collection.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from fp_agent_config.models import (
    AgentConfig,
    AgentConfigStatus,
    agent_config_adapter,
)
from fp_agent_config.settings import Environment, Settings


@dataclass
class PromoteResult:
    """Result of promoting an agent config."""

    success: bool
    promoted_version: str | None = None
    archived_version: str | None = None
    error: str | None = None


@dataclass
class RollbackResult:
    """Result of rolling back an agent config."""

    success: bool
    new_version: str | None = None
    archived_version: str | None = None
    error: str | None = None


class AgentConfigClient:
    """Async MongoDB client for agent configuration operations.

    Provides CRUD operations plus specialized queries for agent config management:
    - create: Insert new agent config
    - get_active: Get active config for an agent_id
    - get_by_version: Get specific version of a config
    - list_configs: List configs with optional filters
    - list_versions: List all versions of an agent
    - promote: Promote staged config to active
    - rollback: Rollback to a previous version
    - enable: Enable an agent at runtime
    - disable: Disable an agent at runtime
    """

    def __init__(self, settings: Settings, env: Environment) -> None:
        """Initialize the agent config client.

        Args:
            settings: Application settings.
            env: Target environment (dev, staging, prod).
        """
        self._settings = settings
        self._env = env
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None

    async def connect(self) -> None:
        """Connect to MongoDB."""
        uri = self._settings.get_mongodb_uri(self._env)
        self._client = AsyncIOMotorClient(uri)
        self._db = self._client[self._settings.database_name]

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    @property
    def _configs(self):
        """Get the agent_configs collection."""
        if self._db is None:
            raise RuntimeError("Client not connected")
        return self._db[self._settings.agent_configs_collection]

    def _serialize(self, config: AgentConfig) -> dict[str, Any]:
        """Serialize an AgentConfig to MongoDB document format."""
        doc = config.model_dump(mode="json")
        doc["_id"] = config.id
        return doc

    def _deserialize(self, doc: dict[str, Any]) -> AgentConfig:
        """Deserialize a MongoDB document to AgentConfig."""
        doc.pop("_id", None)
        return agent_config_adapter.validate_python(doc)

    async def create(self, config: AgentConfig) -> AgentConfig:
        """Create a new agent configuration.

        Args:
            config: The agent config to create.

        Returns:
            The created agent config.

        Raises:
            DuplicateKeyError: If config with same id already exists.
        """
        doc = self._serialize(config)
        await self._configs.insert_one(doc)
        return config

    async def get_active(self, agent_id: str) -> AgentConfig | None:
        """Get the currently active config for an agent_id.

        Args:
            agent_id: The logical agent identifier.

        Returns:
            The active config if found, None otherwise.
        """
        doc = await self._configs.find_one(
            {
                "agent_id": agent_id,
                "status": AgentConfigStatus.ACTIVE.value,
            }
        )
        if doc is None:
            return None
        return self._deserialize(doc)

    async def get_latest_staged(self, agent_id: str) -> AgentConfig | None:
        """Get the latest staged config for an agent_id.

        Args:
            agent_id: The logical agent identifier.

        Returns:
            The latest staged config if found, None otherwise.
        """
        cursor = (
            self._configs.find(
                {
                    "agent_id": agent_id,
                    "status": AgentConfigStatus.STAGED.value,
                }
            )
            .sort("version", -1)
            .limit(1)
        )
        docs = await cursor.to_list(length=1)
        if not docs:
            return None
        return self._deserialize(docs[0])

    async def get_by_version(
        self,
        agent_id: str,
        version: str,
    ) -> AgentConfig | None:
        """Get a specific version of an agent config.

        Args:
            agent_id: The logical agent identifier.
            version: The semantic version string.

        Returns:
            The config if found, None otherwise.
        """
        doc = await self._configs.find_one(
            {
                "agent_id": agent_id,
                "version": version,
            }
        )
        if doc is None:
            return None
        return self._deserialize(doc)

    async def list_configs(
        self,
        status: str | None = None,
        agent_type: str | None = None,
    ) -> list[AgentConfig]:
        """List agent configs with optional filtering.

        Args:
            status: Optional status filter (draft, staged, active, archived).
            agent_type: Optional type filter (extractor, explorer, etc.).

        Returns:
            List of configs matching the filters.
        """
        query: dict[str, Any] = {}
        if status:
            query["status"] = status
        if agent_type:
            query["type"] = agent_type

        cursor = self._configs.find(query).sort([("agent_id", 1), ("version", -1)])
        docs = await cursor.to_list(length=None)

        return [self._deserialize(doc) for doc in docs]

    async def list_versions(
        self,
        agent_id: str,
        include_archived: bool = True,
    ) -> list[AgentConfig]:
        """List all versions of an agent config.

        Args:
            agent_id: The logical agent identifier.
            include_archived: Whether to include archived versions.

        Returns:
            List of config versions, sorted by version descending.
        """
        query: dict[str, Any] = {"agent_id": agent_id}
        if not include_archived:
            query["status"] = {"$ne": AgentConfigStatus.ARCHIVED.value}

        cursor = self._configs.find(query).sort("version", -1)
        docs = await cursor.to_list(length=None)

        return [self._deserialize(doc) for doc in docs]

    async def promote(self, agent_id: str) -> PromoteResult:
        """Promote staged config to active.

        Uses MongoDB transaction to:
        1. Archive current active version (if exists)
        2. Update staged version status to active

        Args:
            agent_id: The agent ID to promote.

        Returns:
            PromoteResult with success status and details.
        """
        if self._client is None or self._db is None:
            return PromoteResult(success=False, error="Client not connected")

        # Find staged version
        staged = await self.get_latest_staged(agent_id)
        if not staged:
            return PromoteResult(
                success=False,
                error=f"No staged config found for '{agent_id}'",
            )

        # Find current active (may not exist)
        current_active = await self.get_active(agent_id)
        archived_version = None

        async with await self._client.start_session() as session:
            async with session.start_transaction():
                # 1. Archive current active (if exists)
                if current_active:
                    await self._configs.update_one(
                        {"_id": current_active.id},
                        {"$set": {"status": AgentConfigStatus.ARCHIVED.value}},
                        session=session,
                    )
                    archived_version = current_active.version

                # 2. Promote staged to active
                await self._configs.update_one(
                    {"_id": staged.id},
                    {
                        "$set": {
                            "status": AgentConfigStatus.ACTIVE.value,
                            "metadata.updated_at": datetime.now(UTC).isoformat(),
                        }
                    },
                    session=session,
                )

        return PromoteResult(
            success=True,
            promoted_version=staged.version,
            archived_version=archived_version,
        )

    async def rollback(
        self,
        agent_id: str,
        to_version: str,
    ) -> RollbackResult:
        """Rollback to a previous version.

        Creates a new version from the rollback target with incremented version.

        Args:
            agent_id: The agent ID to rollback.
            to_version: The version to rollback to.

        Returns:
            RollbackResult with success status and details.
        """
        if self._client is None or self._db is None:
            return RollbackResult(success=False, error="Client not connected")

        # Find target version
        target = await self.get_by_version(agent_id, to_version)
        if not target:
            return RollbackResult(
                success=False,
                error=f"Version {to_version} not found for '{agent_id}'",
            )

        # Find current active
        current_active = await self.get_active(agent_id)
        archived_version = None

        # Calculate new version (increment patch)
        new_version = self._increment_version(to_version)

        # Check if new version already exists
        existing = await self.get_by_version(agent_id, new_version)
        if existing:
            # Keep incrementing until we find an unused version
            for _ in range(100):  # Safety limit
                new_version = self._increment_version(new_version)
                existing = await self.get_by_version(agent_id, new_version)
                if not existing:
                    break
            else:
                return RollbackResult(
                    success=False,
                    error="Could not find available version number",
                )

        # Create new config from target
        now = datetime.now(UTC)
        new_id = f"{agent_id}:{new_version}"

        new_config = target.model_copy(
            update={
                "id": new_id,
                "version": new_version,
                "status": AgentConfigStatus.ACTIVE,
                "metadata": target.metadata.model_copy(
                    update={
                        "updated_at": now,
                    }
                ),
            }
        )

        async with await self._client.start_session() as session:
            async with session.start_transaction():
                # 1. Archive current active (if exists)
                if current_active:
                    await self._configs.update_one(
                        {"_id": current_active.id},
                        {"$set": {"status": AgentConfigStatus.ARCHIVED.value}},
                        session=session,
                    )
                    archived_version = current_active.version

                # 2. Insert new version
                doc = self._serialize(new_config)
                await self._configs.insert_one(doc, session=session)

        return RollbackResult(
            success=True,
            new_version=new_version,
            archived_version=archived_version,
        )

    async def enable(self, agent_id: str) -> tuple[bool, str | None]:
        """Enable an agent at runtime.

        Sets enabled=true on the active config for the agent_id.

        Args:
            agent_id: The agent ID to enable.

        Returns:
            Tuple of (success, error_message).
        """
        if self._db is None:
            return False, "Client not connected"

        # Find active config
        active = await self.get_active(agent_id)
        if not active:
            return False, f"No active config found for '{agent_id}'"

        # Update enabled flag
        await self._configs.update_one(
            {"_id": active.id},
            {
                "$set": {
                    "enabled": True,
                    "metadata.updated_at": datetime.now(UTC).isoformat(),
                }
            },
        )

        return True, None

    async def disable(self, agent_id: str) -> tuple[bool, str | None]:
        """Disable an agent at runtime.

        Sets enabled=false on the active config for the agent_id.

        Args:
            agent_id: The agent ID to disable.

        Returns:
            Tuple of (success, error_message).
        """
        if self._db is None:
            return False, "Client not connected"

        # Find active config
        active = await self.get_active(agent_id)
        if not active:
            return False, f"No active config found for '{agent_id}'"

        # Update enabled flag
        await self._configs.update_one(
            {"_id": active.id},
            {
                "$set": {
                    "enabled": False,
                    "metadata.updated_at": datetime.now(UTC).isoformat(),
                }
            },
        )

        return True, None

    def _increment_version(self, version: str) -> str:
        """Increment the patch version.

        Args:
            version: Semantic version string (e.g., "1.2.3").

        Returns:
            Incremented version (e.g., "1.2.4").
        """
        parts = version.split(".")
        if len(parts) != 3:
            return f"{version}.1"

        major, minor, patch = parts
        try:
            new_patch = int(patch) + 1
            return f"{major}.{minor}.{new_patch}"
        except ValueError:
            return f"{version}.1"
