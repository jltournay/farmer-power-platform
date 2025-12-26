"""MongoDB async client with connection pooling and retry logic."""

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from collection_model.config import settings

logger = structlog.get_logger(__name__)

# Global MongoDB client instance
_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None

# Collection names owned by Collection Model
SOURCE_CONFIGS_COLLECTION = "source_configs"
RAW_DOCUMENTS_COLLECTION = "raw_documents"
QUALITY_EVENTS_COLLECTION = "quality_events"
WEATHER_DATA_COLLECTION = "weather_data"
MARKET_PRICES_COLLECTION = "market_prices"


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
    stop=stop_after_attempt(settings.mongodb_retry_attempts),
    wait=wait_exponential(
        multiplier=1,
        min=settings.mongodb_retry_min_wait,
        max=settings.mongodb_retry_max_wait,
    ),
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


async def ensure_indexes() -> None:
    """Create indexes for all collections owned by Collection Model.

    Collections:
    - source_configs: Data source configurations (from fp-source-config CLI)
    - raw_documents: Raw blob content before LLM extraction
    - quality_events: Extracted grading events with bag summaries
    - weather_data: Weather API pull results
    - market_prices: Market price API pull results
    """
    db = await get_database()

    # source_configs indexes
    source_configs = db[SOURCE_CONFIGS_COLLECTION]
    await source_configs.create_index("source_id", unique=True)
    await source_configs.create_index("source_type")
    await source_configs.create_index("enabled")
    logger.debug("source_configs indexes created")

    # raw_documents indexes (includes deduplication)
    raw_documents = db[RAW_DOCUMENTS_COLLECTION]
    await raw_documents.create_index("content_hash", unique=True)  # Deduplication
    await raw_documents.create_index(
        [("blob_path", 1), ("blob_etag", 1)], unique=True
    )  # Idempotency for Event Grid
    await raw_documents.create_index("source_id")
    await raw_documents.create_index("processing_status")
    await raw_documents.create_index("created_at")
    logger.debug("raw_documents indexes created")

    # quality_events indexes
    quality_events = db[QUALITY_EVENTS_COLLECTION]
    await quality_events.create_index("farmer_id")
    await quality_events.create_index("bag_id")
    await quality_events.create_index("created_at")
    await quality_events.create_index("primary_percentage")
    await quality_events.create_index([("farmer_id", 1), ("created_at", -1)])
    await quality_events.create_index(
        [("primary_percentage", 1), ("analyzed", 1)]
    )  # For poor quality queries
    logger.debug("quality_events indexes created")

    # weather_data indexes
    weather_data = db[WEATHER_DATA_COLLECTION]
    await weather_data.create_index("region_id")
    await weather_data.create_index("date")
    await weather_data.create_index([("region_id", 1), ("date", -1)])
    logger.debug("weather_data indexes created")

    # market_prices indexes
    market_prices = db[MARKET_PRICES_COLLECTION]
    await market_prices.create_index("commodity")
    await market_prices.create_index("region")
    await market_prices.create_index("date")
    await market_prices.create_index([("commodity", 1), ("region", 1), ("date", -1)])
    logger.debug("market_prices indexes created")

    logger.info("MongoDB indexes ensured for all collections")


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
