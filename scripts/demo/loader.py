"""Database loading module for seed data.

This module provides async database loading logic that:
- Loads seed data in dependency order
- Uses upsert pattern to prevent duplicates on re-runs
- Reuses MongoDBDirectClient from E2E helpers
- Supports verification of loaded record counts

Story 0.8.2: Seed Data Loader Script
AC #1: Data loaded to MongoDB in dependency order
AC #4: Upsert pattern used (no duplicates on re-runs)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic import BaseModel

# Add tests/e2e to path for MongoDBDirectClient import
_e2e_path = Path(__file__).parent.parent.parent / "tests" / "e2e"
if str(_e2e_path) not in sys.path:
    sys.path.insert(0, str(_e2e_path))


@dataclass
class LoadResult:
    """Result of loading a single seed file.

    Attributes:
        filename: Name of the seed file loaded.
        collection: MongoDB collection name.
        records_loaded: Number of records loaded/upserted.
        database: MongoDB database name.
    """

    filename: str
    collection: str
    records_loaded: int
    database: str


@dataclass
class VerificationResult:
    """Result of verifying record counts in MongoDB.

    Attributes:
        collection: MongoDB collection name.
        expected: Expected record count.
        actual: Actual record count in database.
        database: MongoDB database name.
    """

    collection: str
    expected: int
    actual: int
    database: str

    @property
    def is_valid(self) -> bool:
        """Return True if actual count matches expected."""
        return self.expected == self.actual


# Seed file order respecting FK dependencies (from ADR-020)
# Level 0 - Independent entities (no FK dependencies)
# Level 1 - Depends on Level 0
# Level 2 - Depends on Level 1 + Level 0
# etc.
SEED_ORDER: list[tuple[str, str, str, str]] = [
    # Format: filename, seed_method, primary_key_field, database
    # Level 0 - Independent entities
    ("grading_models.json", "seed_grading_models", "model_id", "plantation_e2e"),
    ("regions.json", "seed_regions", "region_id", "plantation_e2e"),
    ("agent_configs.json", "seed_agent_configs", "id", "ai_model_e2e"),
    ("prompts.json", "seed_prompts", "id", "ai_model_e2e"),
    # Level 1 - Depends on Level 0
    ("source_configs.json", "seed_source_configs", "source_id", "collection_e2e"),
    ("factories.json", "seed_factories", "id", "plantation_e2e"),
    # Level 2 - Depends on Level 1 + Level 0
    ("collection_points.json", "seed_collection_points", "id", "plantation_e2e"),
    # Level 3 - Depends on Level 0 (regions)
    ("farmers.json", "seed_farmers", "id", "plantation_e2e"),
    # Level 4 - Depends on Level 3
    ("farmer_performance.json", "seed_farmer_performance", "farmer_id", "plantation_e2e"),
    ("weather_observations.json", "seed_weather_observations", "region_id", "plantation_e2e"),
    # Level 5 - Depends on Levels 1 and 3
    ("documents.json", "seed_documents", "document_id", "collection_e2e"),
]


# Collection name mapping (for verification phase)
COLLECTION_MAPPING: dict[str, tuple[str, str]] = {
    # filename -> (database, collection)
    "grading_models.json": ("plantation_e2e", "grading_models"),
    "regions.json": ("plantation_e2e", "regions"),
    "agent_configs.json": ("ai_model_e2e", "agent_configs"),
    "prompts.json": ("ai_model_e2e", "prompts"),
    "source_configs.json": ("collection_e2e", "source_configs"),
    "factories.json": ("plantation_e2e", "factories"),
    "collection_points.json": ("plantation_e2e", "collection_points"),
    "farmers.json": ("plantation_e2e", "farmers"),
    "farmer_performance.json": ("plantation_e2e", "farmer_performances"),
    "weather_observations.json": ("plantation_e2e", "weather_observations"),
    "documents.json": ("collection_e2e", "quality_documents"),
}


class SeedDataLoader:
    """Loads seed data into MongoDB in dependency order.

    Uses MongoDBDirectClient from E2E helpers for database operations.
    Supports upsert pattern to enable safe re-runs.

    Example:
        async with SeedDataLoader(mongodb_uri) as loader:
            results = await loader.load_all(validated_data)
            verification = await loader.verify_counts(expected_counts)
    """

    def __init__(self, mongodb_uri: str = "mongodb://localhost:27017") -> None:
        """Initialize loader with MongoDB connection string.

        Args:
            mongodb_uri: MongoDB connection URI.
        """
        self._uri = mongodb_uri
        self._client: Any = None

    async def __aenter__(self) -> SeedDataLoader:
        """Initialize MongoDB client."""
        # Import here to avoid import cycles
        from helpers.mongodb_direct import MongoDBDirectClient

        self._client = MongoDBDirectClient(self._uri)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Close MongoDB client."""
        if self._client:
            await self._client.__aexit__(*args)

    @property
    def client(self) -> Any:
        """Get the MongoDB client instance."""
        if self._client is None:
            raise RuntimeError("Loader not initialized. Use async context manager.")
        return self._client

    async def load_file(
        self,
        filename: str,
        records: list[dict[str, Any]],
    ) -> LoadResult:
        """Load records from a single file into MongoDB.

        Uses the appropriate seed method from MongoDBDirectClient based on
        the filename. All seed methods use upsert pattern.

        Args:
            filename: Name of the seed file.
            records: List of validated record dictionaries.

        Returns:
            LoadResult with details of what was loaded.

        Raises:
            ValueError: If filename is not a recognized seed file.
        """
        # Find the seed configuration for this file
        seed_config = None
        for fname, method, pk_field, database in SEED_ORDER:
            if fname == filename:
                seed_config = (fname, method, pk_field, database)
                break

        if seed_config is None:
            raise ValueError(f"Unknown seed file: {filename}")

        _, method_name, _, database = seed_config

        # Call the appropriate seed method on MongoDBDirectClient
        seed_method = getattr(self._client, method_name, None)
        if seed_method is None:
            raise ValueError(f"Seed method not found: {method_name}")

        await seed_method(records)

        # Get collection name for result
        db_name, collection = COLLECTION_MAPPING.get(filename, (database, filename.replace(".json", "")))

        return LoadResult(
            filename=filename,
            collection=collection,
            records_loaded=len(records),
            database=db_name,
        )

    async def load_all(
        self,
        validated_data: dict[str, list[dict[str, Any]]],
    ) -> list[LoadResult]:
        """Load all validated data in dependency order.

        Args:
            validated_data: Dict mapping filename to list of validated records.
                Keys should match filenames in SEED_ORDER.

        Returns:
            List of LoadResult for each file loaded.
        """
        results: list[LoadResult] = []

        for filename, _, _, _ in SEED_ORDER:
            records = validated_data.get(filename)
            if records:
                result = await self.load_file(filename, records)
                results.append(result)

        return results

    async def verify_counts(
        self,
        expected_counts: dict[str, int],
    ) -> list[VerificationResult]:
        """Verify record counts in MongoDB match expected values.

        Args:
            expected_counts: Dict mapping filename to expected record count.

        Returns:
            List of VerificationResult for each file checked.
        """
        results: list[VerificationResult] = []

        for filename, expected in expected_counts.items():
            db_name, collection = COLLECTION_MAPPING.get(filename, ("unknown", filename.replace(".json", "")))

            # Get actual count from database
            db = self._client.get_database(db_name)
            actual = await db[collection].count_documents({})

            results.append(
                VerificationResult(
                    collection=collection,
                    expected=expected,
                    actual=actual,
                    database=db_name,
                )
            )

        return results

    async def clear_all_databases(self) -> None:
        """Clear all E2E databases before loading.

        This is useful for starting fresh without leftover data.
        """
        await self._client.drop_all_e2e_databases()


def convert_pydantic_to_dicts(
    validated_records: list[BaseModel],
) -> list[dict[str, Any]]:
    """Convert validated Pydantic models to dictionaries for loading.

    Uses model_dump() to convert Pydantic models to dicts suitable for
    MongoDB insertion.

    Args:
        validated_records: List of validated Pydantic model instances.

    Returns:
        List of dictionaries ready for database insertion.
    """
    return [record.model_dump(mode="json") for record in validated_records]
