"""
MongoDB test utilities for integration testing.

Provides reusable utilities for testing with real MongoDB:
- MongoTestClient: Async context manager for test connections
- create_test_database: Create isolated test databases
- cleanup_test_database: Clean up test databases

Usage:
    async with MongoTestClient() as client:
        db = await client.create_test_database("my_test")
        # ... run tests ...
        await client.cleanup_test_database(db.name)
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

# Default MongoDB connection settings
DEFAULT_MONGODB_HOST = "localhost"
DEFAULT_MONGODB_PORT = 27018  # Test port (not production 27017)
DEFAULT_MONGODB_URI = f"mongodb://{DEFAULT_MONGODB_HOST}:{DEFAULT_MONGODB_PORT}"


class MongoTestClient:
    """Async context manager for MongoDB test connections.

    Provides utilities for creating and managing test databases
    with automatic cleanup support.

    Usage:
        async with MongoTestClient() as client:
            db = await client.create_test_database()
            # ... use db ...
            # db is automatically tracked for cleanup

        # Or with explicit URI:
        async with MongoTestClient(uri="mongodb://custom:27017") as client:
            ...
    """

    def __init__(
        self,
        uri: str | None = None,
        max_connect_attempts: int = 30,
        connect_retry_delay: float = 1.0,
    ) -> None:
        """Initialize the MongoDB test client.

        Args:
            uri: MongoDB connection URI. Defaults to localhost:27018.
            max_connect_attempts: Max attempts to connect to MongoDB.
            connect_retry_delay: Delay between connection attempts.
        """
        self.uri = uri or os.environ.get("MONGODB_TEST_URI", DEFAULT_MONGODB_URI)
        self.max_connect_attempts = max_connect_attempts
        self.connect_retry_delay = connect_retry_delay
        self._client: AsyncIOMotorClient | None = None
        self._created_databases: list[str] = []

    async def __aenter__(self) -> MongoTestClient:
        """Connect to MongoDB when entering context."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Cleanup databases and close connection when exiting context."""
        await self.cleanup_all()
        await self.close()

    async def connect(self) -> None:
        """Connect to MongoDB with retry logic.

        Raises:
            RuntimeError: If MongoDB is not available after max attempts.
        """
        self._client = AsyncIOMotorClient(
            self.uri,
            serverSelectionTimeoutMS=5000,
        )

        for attempt in range(self.max_connect_attempts):
            try:
                await self._client.admin.command("ping")
                logger.info("Connected to MongoDB at %s", self.uri)
                return
            except Exception as e:
                if attempt < self.max_connect_attempts - 1:
                    logger.debug(
                        "MongoDB connection attempt %d/%d failed: %s",
                        attempt + 1,
                        self.max_connect_attempts,
                        e,
                    )
                    await asyncio.sleep(self.connect_retry_delay)
                else:
                    raise RuntimeError(
                        f"Could not connect to MongoDB at {self.uri} "
                        f"after {self.max_connect_attempts} attempts. "
                        f"Ensure MongoDB is running: "
                        f"docker-compose -f tests/docker-compose.test.yaml up -d"
                    ) from e

    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("MongoDB connection closed")

    @property
    def client(self) -> AsyncIOMotorClient:
        """Get the Motor client.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        return self._client

    async def create_test_database(
        self,
        prefix: str = "test",
    ) -> AsyncIOMotorDatabase:
        """Create a unique test database.

        The database name is generated using the prefix and a UUID
        to ensure isolation between tests.

        Args:
            prefix: Prefix for the database name.

        Returns:
            Unique test database.
        """
        db_name = f"{prefix}_{uuid.uuid4().hex[:8]}"
        db = self.client[db_name]
        self._created_databases.append(db_name)
        logger.debug("Created test database: %s", db_name)
        return db

    async def cleanup_test_database(self, db_name: str) -> None:
        """Drop a test database.

        Args:
            db_name: Name of the database to drop.
        """
        await self.client.drop_database(db_name)
        if db_name in self._created_databases:
            self._created_databases.remove(db_name)
        logger.debug("Dropped test database: %s", db_name)

    async def cleanup_all(self) -> None:
        """Drop all test databases created by this client."""
        for db_name in list(self._created_databases):
            try:
                await self.client.drop_database(db_name)
                logger.debug("Dropped test database: %s", db_name)
            except Exception as e:
                logger.warning("Failed to drop database %s: %s", db_name, e)
        self._created_databases.clear()


@asynccontextmanager
async def create_test_database(
    uri: str | None = None,
    prefix: str = "test",
) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Context manager to create and cleanup a test database.

    Convenience function that creates a MongoTestClient, creates
    a database, yields it, then cleans up.

    Args:
        uri: MongoDB connection URI.
        prefix: Prefix for the database name.

    Yields:
        Test database.

    Usage:
        async with create_test_database() as db:
            collection = db["my_collection"]
            await collection.insert_one({"test": "data"})
    """
    async with MongoTestClient(uri=uri) as client:
        db = await client.create_test_database(prefix)
        yield db
        # Cleanup happens in MongoTestClient.__aexit__


async def wait_for_mongodb(
    uri: str | None = None,
    max_attempts: int = 30,
    delay: float = 1.0,
) -> bool:
    """Wait for MongoDB to be ready.

    Useful for CI/CD pipelines where MongoDB may take time to start.

    Args:
        uri: MongoDB connection URI.
        max_attempts: Maximum connection attempts.
        delay: Delay between attempts in seconds.

    Returns:
        True if MongoDB is ready, False otherwise.
    """
    uri = uri or os.environ.get("MONGODB_TEST_URI", DEFAULT_MONGODB_URI)
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)

    try:
        for attempt in range(max_attempts):
            try:
                await client.admin.command("ping")
                logger.info("MongoDB is ready at %s", uri)
                return True
            except Exception as e:
                if attempt < max_attempts - 1:
                    logger.debug(
                        "Waiting for MongoDB (%d/%d): %s",
                        attempt + 1,
                        max_attempts,
                        e,
                    )
                    await asyncio.sleep(delay)
        return False
    finally:
        client.close()


# Re-export key utilities
__all__ = [
    "DEFAULT_MONGODB_URI",
    "MongoTestClient",
    "create_test_database",
    "wait_for_mongodb",
]
