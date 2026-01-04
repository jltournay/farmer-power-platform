"""Prompt repository for MongoDB persistence.

This module provides the PromptRepository class for managing prompts
in the ai_model.prompts MongoDB collection.

Indexes:
- (prompt_id, status): Fast lookup of active/staged prompts
- (prompt_id, version): Unique constraint for version uniqueness
- (agent_id): Fast lookup by agent
"""

import logging

from ai_model.domain.prompt import Prompt, PromptStatus
from ai_model.infrastructure.repositories.base import BaseRepository
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING

logger = logging.getLogger(__name__)


class PromptRepository(BaseRepository[Prompt]):
    """Repository for Prompt entities.

    Provides CRUD operations plus specialized queries:
    - get_active: Get currently active prompt for a prompt_id
    - get_by_version: Get specific version of a prompt
    - list_versions: List all versions of a prompt
    - list_by_agent: List prompts for an agent
    """

    COLLECTION_NAME = "prompts"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the prompt repository.

        Args:
            db: MongoDB database instance (should be ai_model database).
        """
        super().__init__(db, self.COLLECTION_NAME, Prompt)

    async def get_active(self, prompt_id: str) -> Prompt | None:
        """Get the currently active prompt for a prompt_id.

        Only one prompt per prompt_id should have status=active.

        Args:
            prompt_id: The logical prompt identifier (e.g., "disease-diagnosis").

        Returns:
            The active prompt if found, None otherwise.
        """
        doc = await self._collection.find_one(
            {
                "prompt_id": prompt_id,
                "status": PromptStatus.ACTIVE.value,
            }
        )
        if doc is None:
            return None
        doc.pop("_id", None)
        return Prompt.model_validate(doc)

    async def get_by_version(
        self,
        prompt_id: str,
        version: str,
    ) -> Prompt | None:
        """Get a specific version of a prompt.

        Args:
            prompt_id: The logical prompt identifier.
            version: The semantic version string (e.g., "2.1.0").

        Returns:
            The prompt if found, None otherwise.
        """
        doc = await self._collection.find_one(
            {
                "prompt_id": prompt_id,
                "version": version,
            }
        )
        if doc is None:
            return None
        doc.pop("_id", None)
        return Prompt.model_validate(doc)

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
        query: dict = {"prompt_id": prompt_id}
        if not include_archived:
            query["status"] = {"$ne": PromptStatus.ARCHIVED.value}

        cursor = self._collection.find(query).sort("version", -1)
        docs = await cursor.to_list(length=None)

        prompts = []
        for doc in docs:
            doc.pop("_id", None)
            prompts.append(Prompt.model_validate(doc))

        return prompts

    async def list_by_agent(
        self,
        agent_id: str,
        status: PromptStatus | None = None,
    ) -> list[Prompt]:
        """List prompts for a specific agent.

        Args:
            agent_id: The agent identifier.
            status: Optional status filter.

        Returns:
            List of prompts for the agent.
        """
        query: dict = {"agent_id": agent_id}
        if status is not None:
            query["status"] = status.value

        cursor = self._collection.find(query).sort(
            [
                ("prompt_id", ASCENDING),
                ("version", -1),
            ]
        )
        docs = await cursor.to_list(length=None)

        prompts = []
        for doc in docs:
            doc.pop("_id", None)
            prompts.append(Prompt.model_validate(doc))

        return prompts

    async def ensure_indexes(self) -> None:
        """Create indexes for the prompts collection.

        Indexes:
        - (prompt_id, status): Fast lookup of active/staged prompts
        - (prompt_id, version): Unique constraint, fast version lookup
        - (agent_id): Fast lookup by agent
        """
        # Compound index for prompt_id + status (get_active query)
        await self._collection.create_index(
            [("prompt_id", ASCENDING), ("status", ASCENDING)],
            name="idx_prompt_id_status",
        )

        # Compound unique index for prompt_id + version
        await self._collection.create_index(
            [("prompt_id", ASCENDING), ("version", ASCENDING)],
            unique=True,
            name="idx_prompt_id_version_unique",
        )

        # Index for agent_id (list_by_agent query)
        await self._collection.create_index(
            "agent_id",
            name="idx_agent_id",
        )

        logger.info("Prompt indexes created")
