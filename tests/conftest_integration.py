"""
Integration test configuration with real MongoDB.

This module provides fixtures for integration tests that connect to
a real MongoDB instance running in Docker.

Usage:
    1. Start MongoDB: docker-compose -f tests/docker-compose.test.yaml up -d
    2. Run tests: pytest tests/integration/ -m mongodb -v
    3. Cleanup: docker-compose -f tests/docker-compose.test.yaml down

Fixtures:
    - mongodb_client: Session-scoped Motor client
    - test_db: Function-scoped database with automatic cleanup
    - wait_for_mongodb: Helper to wait for MongoDB readiness
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# MongoDB connection settings from environment or defaults
MONGODB_TEST_HOST = os.environ.get("MONGODB_TEST_HOST", "localhost")
MONGODB_TEST_PORT = int(os.environ.get("MONGODB_TEST_PORT", "27018"))
MONGODB_TEST_URI = os.environ.get(
    "MONGODB_TEST_URI", f"mongodb://{MONGODB_TEST_HOST}:{MONGODB_TEST_PORT}"
)


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom pytest markers for MongoDB integration tests."""
    config.addinivalue_line(
        "markers",
        "mongodb: mark test as requiring real MongoDB connection",
    )


async def wait_for_mongodb(
    uri: str = MONGODB_TEST_URI,
    max_attempts: int = 30,
    delay: float = 1.0,
) -> AsyncIOMotorClient:
    """Wait for MongoDB to be ready and return a connected client.

    Args:
        uri: MongoDB connection URI.
        max_attempts: Maximum number of connection attempts.
        delay: Delay between attempts in seconds.

    Returns:
        Connected AsyncIOMotorClient.

    Raises:
        RuntimeError: If MongoDB is not available after max_attempts.
    """
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)

    for attempt in range(max_attempts):
        try:
            # Ping the server to verify connection
            await client.admin.command("ping")
            logger.info("MongoDB is ready at %s", uri)
            return client
        except Exception as e:
            if attempt < max_attempts - 1:
                logger.debug(
                    "MongoDB not ready (attempt %d/%d): %s",
                    attempt + 1,
                    max_attempts,
                    e,
                )
                await asyncio.sleep(delay)
            else:
                raise RuntimeError(
                    f"MongoDB not available after {max_attempts} attempts. "
                    f"Make sure MongoDB is running: "
                    f"docker-compose -f tests/docker-compose.test.yaml up -d"
                ) from e

    # This should never be reached, but satisfies type checker
    raise RuntimeError("MongoDB connection failed")


@pytest_asyncio.fixture(scope="function")
async def mongodb_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Function-scoped MongoDB client.

    Connects to the test MongoDB instance and verifies it's ready.

    Yields:
        Connected AsyncIOMotorClient.
    """
    client = await wait_for_mongodb()
    logger.debug("MongoDB client connected")

    yield client

    # Cleanup: close client
    client.close()
    logger.debug("MongoDB client closed")


@pytest_asyncio.fixture(scope="function")
async def test_db(
    mongodb_client: AsyncIOMotorClient,
) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Function-scoped test database with automatic cleanup.

    Creates a unique database for each test to ensure isolation.
    The database is dropped after the test completes.

    Args:
        mongodb_client: MongoDB client.

    Yields:
        Unique test database.
    """
    # Create unique database name for this test
    db_name = f"test_{uuid.uuid4().hex[:8]}"
    db = mongodb_client[db_name]

    logger.debug("Created test database: %s", db_name)

    yield db

    # Cleanup: drop the test database
    await mongodb_client.drop_database(db_name)
    logger.debug("Dropped test database: %s", db_name)


@pytest_asyncio.fixture(scope="function")
async def plantation_test_db(
    mongodb_client: AsyncIOMotorClient,
) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Function-scoped plantation model test database.

    Similar to test_db but with a more descriptive name prefix.
    Useful when you need multiple databases in one test.

    Args:
        mongodb_client: MongoDB client.

    Yields:
        Unique test database for plantation model.
    """
    db_name = f"plantation_test_{uuid.uuid4().hex[:8]}"
    db = mongodb_client[db_name]

    logger.debug("Created plantation test database: %s", db_name)

    yield db

    await mongodb_client.drop_database(db_name)
    logger.debug("Dropped plantation test database: %s", db_name)


# Re-export wait_for_mongodb for use in tests
__all__ = [
    "mongodb_client",
    "test_db",
    "plantation_test_db",
    "wait_for_mongodb",
    "MONGODB_TEST_URI",
]
