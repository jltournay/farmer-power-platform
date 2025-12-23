"""MongoDB async client with connection pooling and retry logic."""

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from plantation_model.config import settings

logger = structlog.get_logger(__name__)

# Global MongoDB client instance
_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def get_mongodb_client() -> AsyncIOMotorClient:
    """Get or create the MongoDB client singleton.

    Returns:
        AsyncIOMotorClient: The MongoDB async client.

    Raises:
        ConnectionFailure: If unable to connect to MongoDB.
    """
    global _client

    if _client is None:
        logger.info(
            "Creating MongoDB client",
            database=settings.mongodb_database,
            min_pool=settings.mongodb_min_pool_size,
            max_pool=settings.mongodb_max_pool_size,
        )

        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            minPoolSize=settings.mongodb_min_pool_size,
            maxPoolSize=settings.mongodb_max_pool_size,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=30000,
        )

        # Verify connection
        await _client.admin.command("ping")
        logger.info("MongoDB client connected successfully")

    return _client


async def get_database() -> AsyncIOMotorDatabase:
    """Get the application database.

    Returns:
        AsyncIOMotorDatabase: The application database.
    """
    global _database

    if _database is None:
        client = await get_mongodb_client()
        _database = client[settings.mongodb_database]
        logger.info("MongoDB database ready", database=settings.mongodb_database)

    return _database


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionFailure, ServerSelectionTimeoutError)),
    reraise=True,
)
async def check_mongodb_connection() -> bool:
    """Check if MongoDB connection is healthy.

    Uses retry logic with exponential backoff for transient failures.

    Returns:
        bool: True if connection is healthy, False otherwise.
    """
    try:
        client = await get_mongodb_client()
        await client.admin.command("ping")
        return True
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.warning("MongoDB connection check failed", error=str(e))
        raise
    except Exception as e:
        logger.error("Unexpected error checking MongoDB connection", error=str(e))
        return False


async def close_mongodb_connection() -> None:
    """Close the MongoDB connection.

    Should be called during application shutdown.
    """
    global _client, _database

    if _client is not None:
        logger.info("Closing MongoDB connection")
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")
