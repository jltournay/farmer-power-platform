"""Direct MongoDB client for E2E test verification."""

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

    async def list_databases(self) -> list[str]:
        """List all databases."""
        return await self.client.list_database_names()

    # Seed data helpers
    async def seed_grading_models(self, grading_models: list[dict[str, Any]]) -> None:
        """Seed grading models into plantation database."""
        if grading_models:
            await self.plantation_db.grading_models.insert_many(grading_models)

    async def seed_regions(self, regions: list[dict[str, Any]]) -> None:
        """Seed regions into plantation database."""
        if regions:
            await self.plantation_db.regions.insert_many(regions)

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
