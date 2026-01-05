"""MongoDB client for prompt operations.

This module provides the PromptClient class for managing prompts
in the ai_model.prompts MongoDB collection.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from fp_prompt_config.models import Prompt, PromptStatus
from fp_prompt_config.settings import Environment, Settings


@dataclass
class PromoteResult:
    """Result of promoting a prompt."""

    success: bool
    promoted_version: str | None = None
    archived_version: str | None = None
    error: str | None = None


@dataclass
class RollbackResult:
    """Result of rolling back a prompt."""

    success: bool
    new_version: str | None = None
    archived_version: str | None = None
    error: str | None = None


class PromptClient:
    """Async MongoDB client for prompt operations.

    Provides CRUD operations plus specialized queries for prompt management:
    - create: Insert new prompt
    - get_active: Get active prompt for a prompt_id
    - get_by_version: Get specific version of a prompt
    - list_prompts: List prompts with optional filters
    - list_versions: List all versions of a prompt
    - promote: Promote staged prompt to active
    - rollback: Rollback to a previous version
    - validate_agent_reference: Validate agent_id exists
    """

    def __init__(self, settings: Settings, env: Environment) -> None:
        """Initialize the prompt client.

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
    def _prompts(self):
        """Get the prompts collection."""
        if self._db is None:
            raise RuntimeError("Client not connected")
        return self._db[self._settings.prompts_collection]

    @property
    def _agent_configs(self):
        """Get the agent_configs collection."""
        if self._db is None:
            raise RuntimeError("Client not connected")
        return self._db[self._settings.agent_configs_collection]

    def _serialize(self, prompt: Prompt) -> dict[str, Any]:
        """Serialize a Prompt to MongoDB document format."""
        doc = prompt.model_dump(mode="json")
        doc["_id"] = prompt.id
        return doc

    def _deserialize(self, doc: dict[str, Any]) -> Prompt:
        """Deserialize a MongoDB document to Prompt."""
        doc.pop("_id", None)
        return Prompt.model_validate(doc)

    async def create(self, prompt: Prompt) -> Prompt:
        """Create a new prompt.

        Args:
            prompt: The prompt to create.

        Returns:
            The created prompt.

        Raises:
            DuplicateKeyError: If prompt with same id already exists.
        """
        doc = self._serialize(prompt)
        await self._prompts.insert_one(doc)
        return prompt

    async def get_active(self, prompt_id: str) -> Prompt | None:
        """Get the currently active prompt for a prompt_id.

        Args:
            prompt_id: The logical prompt identifier.

        Returns:
            The active prompt if found, None otherwise.
        """
        doc = await self._prompts.find_one(
            {
                "prompt_id": prompt_id,
                "status": PromptStatus.ACTIVE.value,
            }
        )
        if doc is None:
            return None
        return self._deserialize(doc)

    async def get_latest_staged(self, prompt_id: str) -> Prompt | None:
        """Get the latest staged prompt for a prompt_id.

        Args:
            prompt_id: The logical prompt identifier.

        Returns:
            The latest staged prompt if found, None otherwise.
        """
        cursor = (
            self._prompts.find(
                {
                    "prompt_id": prompt_id,
                    "status": PromptStatus.STAGED.value,
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
        prompt_id: str,
        version: str,
    ) -> Prompt | None:
        """Get a specific version of a prompt.

        Args:
            prompt_id: The logical prompt identifier.
            version: The semantic version string.

        Returns:
            The prompt if found, None otherwise.
        """
        doc = await self._prompts.find_one(
            {
                "prompt_id": prompt_id,
                "version": version,
            }
        )
        if doc is None:
            return None
        return self._deserialize(doc)

    async def list_prompts(
        self,
        status: str | None = None,
        agent_id: str | None = None,
    ) -> list[Prompt]:
        """List prompts with optional filtering.

        Args:
            status: Optional status filter (draft, staged, active, archived).
            agent_id: Optional agent_id filter.

        Returns:
            List of prompts matching the filters.
        """
        query: dict[str, Any] = {}
        if status:
            query["status"] = status
        if agent_id:
            query["agent_id"] = agent_id

        cursor = self._prompts.find(query).sort([("prompt_id", 1), ("version", -1)])
        docs = await cursor.to_list(length=None)

        return [self._deserialize(doc) for doc in docs]

    async def list_versions(
        self,
        prompt_id: str,
        include_archived: bool = True,
    ) -> list[Prompt]:
        """List all versions of a prompt.

        Args:
            prompt_id: The logical prompt identifier.
            include_archived: Whether to include archived versions.

        Returns:
            List of prompt versions, sorted by version descending.
        """
        query: dict[str, Any] = {"prompt_id": prompt_id}
        if not include_archived:
            query["status"] = {"$ne": PromptStatus.ARCHIVED.value}

        cursor = self._prompts.find(query).sort("version", -1)
        docs = await cursor.to_list(length=None)

        return [self._deserialize(doc) for doc in docs]

    async def validate_agent_reference(self, prompt: Prompt) -> str | None:
        """Validate that the agent_id exists in agent_configs.

        Only validates for staged/active prompts. Draft prompts skip validation.

        IMPORTANT: Uses get_active(agent_id) because prompt.agent_id is a logical
        identifier (e.g., "diagnose-quality-issue"), not a document _id.

        Args:
            prompt: The prompt to validate.

        Returns:
            Error message if validation fails, None if valid.
        """
        # Skip validation for draft prompts
        if prompt.status == PromptStatus.DRAFT:
            return None

        # For staged/active, agent must exist
        doc = await self._agent_configs.find_one(
            {
                "agent_id": prompt.agent_id,
                "status": "active",
            }
        )

        if doc is None:
            return (
                f"Cannot publish prompt '{prompt.prompt_id}' with status "
                f"'{prompt.status.value}': agent_id '{prompt.agent_id}' "
                "does not exist in agent_configs or has no active version"
            )

        return None

    async def promote(self, prompt_id: str) -> PromoteResult:
        """Promote staged prompt to active.

        Uses MongoDB transaction to:
        1. Archive current active version (if exists)
        2. Update staged version status to active

        Args:
            prompt_id: The prompt ID to promote.

        Returns:
            PromoteResult with success status and details.
        """
        if self._client is None or self._db is None:
            return PromoteResult(success=False, error="Client not connected")

        # Find staged version
        staged = await self.get_latest_staged(prompt_id)
        if not staged:
            return PromoteResult(
                success=False,
                error=f"No staged prompt found for '{prompt_id}'",
            )

        # Find current active (may not exist)
        current_active = await self.get_active(prompt_id)
        archived_version = None

        async with await self._client.start_session() as session:
            async with session.start_transaction():
                # 1. Archive current active (if exists)
                if current_active:
                    await self._prompts.update_one(
                        {"_id": current_active.id},
                        {"$set": {"status": PromptStatus.ARCHIVED.value}},
                        session=session,
                    )
                    archived_version = current_active.version

                # 2. Promote staged to active
                await self._prompts.update_one(
                    {"_id": staged.id},
                    {
                        "$set": {
                            "status": PromptStatus.ACTIVE.value,
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
        prompt_id: str,
        to_version: str,
    ) -> RollbackResult:
        """Rollback to a previous version.

        Creates a new version from the rollback target with incremented version.

        Args:
            prompt_id: The prompt ID to rollback.
            to_version: The version to rollback to.

        Returns:
            RollbackResult with success status and details.
        """
        if self._client is None or self._db is None:
            return RollbackResult(success=False, error="Client not connected")

        # Find target version
        target = await self.get_by_version(prompt_id, to_version)
        if not target:
            return RollbackResult(
                success=False,
                error=f"Version {to_version} not found for '{prompt_id}'",
            )

        # Find current active
        current_active = await self.get_active(prompt_id)
        archived_version = None

        # Calculate new version (increment patch)
        new_version = self._increment_version(to_version)

        # Check if new version already exists
        existing = await self.get_by_version(prompt_id, new_version)
        if existing:
            # Keep incrementing until we find an unused version
            for _ in range(100):  # Safety limit
                new_version = self._increment_version(new_version)
                existing = await self.get_by_version(prompt_id, new_version)
                if not existing:
                    break
            else:
                return RollbackResult(
                    success=False,
                    error="Could not find available version number",
                )

        # Create new prompt from target
        now = datetime.now(UTC)
        new_id = f"{prompt_id}:{new_version}"
        rollback_note = f"Rollback from {to_version}"
        if current_active:
            rollback_note = f"Rollback from v{current_active.version} to v{to_version}"

        new_prompt = target.model_copy(
            update={
                "id": new_id,
                "version": new_version,
                "status": PromptStatus.ACTIVE,
                "metadata": target.metadata.model_copy(
                    update={
                        "updated_at": now,
                        "changelog": rollback_note,
                    }
                ),
            }
        )

        async with await self._client.start_session() as session:
            async with session.start_transaction():
                # 1. Archive current active (if exists)
                if current_active:
                    await self._prompts.update_one(
                        {"_id": current_active.id},
                        {"$set": {"status": PromptStatus.ARCHIVED.value}},
                        session=session,
                    )
                    archived_version = current_active.version

                # 2. Insert new version
                doc = self._serialize(new_prompt)
                await self._prompts.insert_one(doc, session=session)

        return RollbackResult(
            success=True,
            new_version=new_version,
            archived_version=archived_version,
        )

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
