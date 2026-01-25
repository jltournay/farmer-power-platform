"""Direct MongoDB client for E2E test verification."""

from datetime import UTC
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class MongoDBDirectClient:
    """
    Direct MongoDB client for E2E test verification.

    Used to verify data in MongoDB directly, bypassing the API layer.
    This allows tests to confirm that data was correctly persisted.
    """

    def __init__(self, uri: str = "mongodb://localhost:27017"):
        self.uri = uri
        self._client: AsyncIOMotorClient | None = None

    async def __aenter__(self) -> "MongoDBDirectClient":
        self._client = AsyncIOMotorClient(self.uri)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            self._client.close()

    @property
    def client(self) -> AsyncIOMotorClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    def get_database(self, name: str) -> AsyncIOMotorDatabase:
        """Get a database by name."""
        return self.client[name]

    # Plantation Model database helpers
    @property
    def plantation_db(self) -> AsyncIOMotorDatabase:
        """Get the plantation E2E database."""
        return self.get_database("plantation_e2e")

    async def get_farmer_direct(self, farmer_id: str) -> dict[str, Any] | None:
        """Get farmer directly from MongoDB."""
        return await self.plantation_db.farmers.find_one({"farmer_id": farmer_id})

    async def get_factory_direct(self, factory_id: str) -> dict[str, Any] | None:
        """Get factory directly from MongoDB."""
        return await self.plantation_db.factories.find_one({"factory_id": factory_id})

    async def get_region_direct(self, region_id: str) -> dict[str, Any] | None:
        """Get region directly from MongoDB."""
        return await self.plantation_db.regions.find_one({"region_id": region_id})

    async def count_farmers(self, factory_id: str | None = None) -> int:
        """Count farmers, optionally by factory."""
        query = {}
        if factory_id:
            query["factory_id"] = factory_id
        return await self.plantation_db.farmers.count_documents(query)

    # Collection Model database helpers
    @property
    def collection_db(self) -> AsyncIOMotorDatabase:
        """Get the collection E2E database."""
        return self.get_database("collection_e2e")

    async def get_document_direct(self, document_id: str) -> dict[str, Any] | None:
        """Get document directly from MongoDB (quality_documents collection)."""
        return await self.collection_db.quality_documents.find_one({"document_id": document_id})

    async def count_quality_documents(
        self,
        farmer_id: str | None = None,
        source_id: str | None = None,
    ) -> int:
        """Count quality documents, optionally by farmer or source."""
        query: dict[str, Any] = {}
        if farmer_id:
            # Documents store farmer_id in linkage_fields or extracted_fields
            query["$or"] = [
                {"linkage_fields.farmer_id": farmer_id},
                {"extracted_fields.farmer_id": farmer_id},
            ]
        if source_id:
            query["ingestion.source_id"] = source_id
        return await self.collection_db.quality_documents.count_documents(query)

    async def get_latest_quality_documents(
        self,
        farmer_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get latest quality documents for a farmer."""
        query = {
            "$or": [
                {"linkage_fields.farmer_id": farmer_id},
                {"extracted_fields.farmer_id": farmer_id},
            ]
        }
        cursor = self.collection_db.quality_documents.find(query).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_source_config(self, source_id: str) -> dict[str, Any] | None:
        """Get source config by ID."""
        return await self.collection_db.source_configs.find_one({"source_id": source_id})

    async def list_source_configs(self) -> list[dict[str, Any]]:
        """List all source configs."""
        cursor = self.collection_db.source_configs.find({})
        return await cursor.to_list(length=100)

    # Backward compatibility aliases
    async def count_documents(
        self,
        farmer_id: str | None = None,
        source: str | None = None,
    ) -> int:
        """Alias for count_quality_documents for backward compatibility."""
        return await self.count_quality_documents(farmer_id=farmer_id, source_id=source)

    async def get_latest_documents(
        self,
        farmer_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Alias for get_latest_quality_documents for backward compatibility."""
        return await self.get_latest_quality_documents(farmer_id=farmer_id, limit=limit)

    # Database management
    async def drop_database(self, name: str) -> None:
        """Drop a database (for cleanup)."""
        await self.client.drop_database(name)

    async def drop_all_e2e_databases(self) -> None:
        """Drop all E2E databases."""
        await self.drop_database("plantation_e2e")
        await self.drop_database("collection_e2e")
        await self.drop_database("ai_model_e2e")
        await self.drop_database("platform_cost_e2e")  # Story 13.8

    async def list_databases(self) -> list[str]:
        """List all databases."""
        return await self.client.list_database_names()

    # Seed data helpers
    async def seed_grading_models(self, grading_models: list[dict[str, Any]]) -> None:
        """Seed grading models into plantation database."""
        if grading_models:
            for gm in grading_models:
                # Set _id to match model_id for repository lookups
                gm_doc = {**gm, "_id": gm["model_id"]}
                await self.plantation_db.grading_models.update_one(
                    {"_id": gm["model_id"]},
                    {"$set": gm_doc},
                    upsert=True,
                )

    async def seed_regions(self, regions: list[dict[str, Any]]) -> None:
        """Seed regions into plantation database."""
        if regions:
            for region in regions:
                # Set _id to match region_id for repository lookups
                region_doc = {**region, "_id": region["region_id"]}
                await self.plantation_db.regions.update_one(
                    {"_id": region["region_id"]},
                    {"$set": region_doc},
                    upsert=True,
                )

    async def seed_source_configs(self, source_configs: list[dict[str, Any]]) -> None:
        """Seed source configs into collection database."""
        if source_configs:
            # Use upsert to avoid duplicates on re-runs
            for config in source_configs:
                await self.collection_db.source_configs.update_one(
                    {"source_id": config["source_id"]},
                    {"$set": config},
                    upsert=True,
                )

    async def seed_factories(self, factories: list[dict[str, Any]]) -> None:
        """Seed factories into plantation database."""
        if factories:
            for factory in factories:
                # Set _id to match id for repository lookups
                factory_doc = {**factory, "_id": factory["id"]}
                await self.plantation_db.factories.update_one(
                    {"_id": factory["id"]},
                    {"$set": factory_doc},
                    upsert=True,
                )

    async def seed_collection_points(self, collection_points: list[dict[str, Any]]) -> None:
        """Seed collection points into plantation database."""
        if collection_points:
            for cp in collection_points:
                # Set _id to match id for repository lookups
                cp_doc = {**cp, "_id": cp["id"]}
                await self.plantation_db.collection_points.update_one(
                    {"_id": cp["id"]},
                    {"$set": cp_doc},
                    upsert=True,
                )

    async def seed_farmers(self, farmers: list[dict[str, Any]]) -> None:
        """Seed farmers into plantation database."""
        if farmers:
            for farmer in farmers:
                # Set _id to match id for repository lookups
                farmer_doc = {**farmer, "_id": farmer["id"]}
                await self.plantation_db.farmers.update_one(
                    {"_id": farmer["id"]},
                    {"$set": farmer_doc},
                    upsert=True,
                )

    async def seed_farmer_performance(self, performance_data: list[dict[str, Any]]) -> None:
        """Seed farmer performance summaries into plantation database."""
        if performance_data:
            for perf in performance_data:
                # Set _id to match farmer_id for repository lookups
                perf_doc = {**perf, "_id": perf["farmer_id"]}
                await self.plantation_db.farmer_performances.update_one(
                    {"_id": perf["farmer_id"]},
                    {"$set": perf_doc},
                    upsert=True,
                )

    async def seed_weather_observations(self, weather_data: list[dict[str, Any]]) -> None:
        """Seed weather observations into plantation database.

        Uses (region_id, date) as composite key for upsert to allow
        multiple observations per region (one per date).
        """
        if weather_data:
            for obs in weather_data:
                await self.plantation_db.weather_observations.update_one(
                    {"region_id": obs["region_id"], "date": obs["date"]},
                    {"$set": obs},
                    upsert=True,
                )

    async def seed_documents(self, documents: list[dict[str, Any]]) -> None:
        """Seed documents into collection database (quality_documents collection)."""
        if documents:
            for doc in documents:
                await self.collection_db.quality_documents.update_one(
                    {"document_id": doc["document_id"]},
                    {"$set": doc},
                    upsert=True,
                )

    async def find_documents(
        self,
        collection: str,
        query: dict[str, Any],
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Find documents in a collection with a query."""
        db = self.collection_db
        cursor = db[collection].find(query).limit(limit)
        return await cursor.to_list(length=limit)

    async def count_documents_by_source(self, source_id: str) -> int:
        """Count documents by source_id.

        Args:
            source_id: The source configuration ID to filter by.

        Returns:
            Count of documents matching the source_id.
        """
        query = {"ingestion.source_id": source_id}
        return await self.collection_db.quality_documents.count_documents(query)

    # =========================================================================
    # Generic Documents Collection (for ZIP processor, Story 0.4.9)
    # =========================================================================

    async def count_documents_in_collection(
        self,
        collection_name: str,
        source_id: str | None = None,
        link_field: str | None = None,
        link_value: str | None = None,
    ) -> int:
        """Count documents in a specified collection.

        Args:
            collection_name: The MongoDB collection name (e.g., "documents")
            source_id: Optional source_id filter
            link_field: Optional linkage field name to filter by
            link_value: Optional linkage field value to filter by

        Returns:
            Count of documents matching the filters.
        """
        query: dict[str, Any] = {}
        if source_id:
            query["ingestion.source_id"] = source_id
        if link_field and link_value:
            query[f"linkage_fields.{link_field}"] = link_value
        return await self.collection_db[collection_name].count_documents(query)

    async def get_documents_from_collection(
        self,
        collection_name: str,
        source_id: str | None = None,
        link_field: str | None = None,
        link_value: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get documents from a specified collection.

        Args:
            collection_name: The MongoDB collection name (e.g., "documents")
            source_id: Optional source_id filter
            link_field: Optional linkage field name to filter by
            link_value: Optional linkage field value to filter by
            limit: Maximum number of documents to return

        Returns:
            List of documents matching the filters.
        """
        query: dict[str, Any] = {}
        if source_id:
            query["ingestion.source_id"] = source_id
        if link_field and link_value:
            query[f"linkage_fields.{link_field}"] = link_value

        cursor = self.collection_db[collection_name].find(query).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_document_by_id(
        self,
        collection_name: str,
        document_id: str,
    ) -> dict[str, Any] | None:
        """Get a document by its document_id from a specified collection.

        Args:
            collection_name: The MongoDB collection name
            document_id: The document_id to look up

        Returns:
            The document if found, None otherwise.
        """
        return await self.collection_db[collection_name].find_one({"document_id": document_id})

    # =========================================================================
    # AI Model Database Helpers (Story 0.75.18)
    # =========================================================================

    @property
    def ai_model_db(self) -> AsyncIOMotorDatabase:
        """Get the AI Model E2E database."""
        return self.get_database("ai_model_e2e")

    async def seed_agent_configs(self, agent_configs: list[dict[str, Any]]) -> None:
        """Seed agent configs into AI Model database.

        Args:
            agent_configs: List of agent config documents to seed.
        """
        if agent_configs:
            for config in agent_configs:
                # Set _id to match id for repository lookups
                config_doc = {**config, "_id": config["id"]}
                await self.ai_model_db.agent_configs.update_one(
                    {"_id": config["id"]},
                    {"$set": config_doc},
                    upsert=True,
                )

    async def seed_prompts(self, prompts: list[dict[str, Any]]) -> None:
        """Seed prompts into AI Model database.

        Args:
            prompts: List of prompt documents to seed.
        """
        if prompts:
            for prompt in prompts:
                # Set _id to match id for repository lookups
                prompt_doc = {**prompt, "_id": prompt["id"]}
                await self.ai_model_db.prompts.update_one(
                    {"_id": prompt["id"]},
                    {"$set": prompt_doc},
                    upsert=True,
                )

    async def get_agent_config(self, agent_id: str) -> dict[str, Any] | None:
        """Get an agent config by agent_id.

        Args:
            agent_id: The agent_id to look up.

        Returns:
            The agent config if found, None otherwise.
        """
        return await self.ai_model_db.agent_configs.find_one({"agent_id": agent_id})

    async def get_prompt(self, prompt_id: str) -> dict[str, Any] | None:
        """Get a prompt by prompt_id.

        Args:
            prompt_id: The prompt_id to look up.

        Returns:
            The prompt if found, None otherwise.
        """
        return await self.ai_model_db.prompts.find_one({"prompt_id": prompt_id})

    # =========================================================================
    # Platform Cost Database Helpers (Story 13.8)
    # =========================================================================

    @property
    def platform_cost_db(self) -> AsyncIOMotorDatabase:
        """Get the Platform Cost E2E database."""
        return self.get_database("platform_cost_e2e")

    async def count_cost_events(
        self,
        cost_type: str | None = None,
        agent_type: str | None = None,
    ) -> int:
        """Count cost events in platform_cost database.

        Args:
            cost_type: Optional filter by cost type (llm, document, embedding, sms).
            agent_type: Optional filter by agent type.

        Returns:
            Count of cost events matching the filters.
        """
        query: dict[str, Any] = {}
        if cost_type:
            query["cost_type"] = cost_type
        if agent_type:
            query["agent_type"] = agent_type
        return await self.platform_cost_db.cost_events.count_documents(query)

    async def get_latest_cost_events(
        self,
        limit: int = 10,
        cost_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get latest cost events from platform_cost database.

        Args:
            limit: Maximum number of events to return.
            cost_type: Optional filter by cost type.

        Returns:
            List of cost events sorted by timestamp descending.
        """
        query: dict[str, Any] = {}
        if cost_type:
            query["cost_type"] = cost_type
        cursor = self.platform_cost_db.cost_events.find(query).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_cost_event_by_request_id(self, request_id: str) -> dict[str, Any] | None:
        """Get a cost event by request_id.

        Args:
            request_id: The request_id to look up.

        Returns:
            The cost event if found, None otherwise.
        """
        return await self.platform_cost_db.cost_events.find_one({"request_id": request_id})

    async def get_budget_thresholds(self) -> dict[str, Any] | None:
        """Get current budget thresholds from platform_cost database.

        Returns:
            The threshold configuration if found, None otherwise.
        """
        return await self.platform_cost_db.budget_thresholds.find_one({})

    async def seed_cost_events(self, cost_events: list[dict[str, Any]]) -> None:
        """Seed cost events into platform_cost database.

        Args:
            cost_events: List of cost event documents to seed.

        Note:
            Converts timestamp strings to datetime objects for proper MongoDB
            date queries. This is needed because model_dump(mode="json") converts
            datetime to ISO strings, but MongoDB queries require native dates.
        """
        from datetime import datetime

        if cost_events:
            for event in cost_events:
                # Convert timestamp string to datetime for MongoDB date queries
                if "timestamp" in event and isinstance(event["timestamp"], str):
                    ts_str = event["timestamp"]
                    # Handle ISO format with Z suffix or +00:00
                    if ts_str.endswith("Z"):
                        ts_str = ts_str[:-1] + "+00:00"
                    event["timestamp"] = datetime.fromisoformat(ts_str).replace(tzinfo=UTC)

                await self.platform_cost_db.cost_events.update_one(
                    {"request_id": event["request_id"]},
                    {"$set": event},
                    upsert=True,
                )
