"""MongoDB checkpointer factory for LangGraph workflows.

This module provides the factory function for creating MongoDB-backed
checkpointers that enable workflow crash recovery and session persistence.

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

import structlog
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

logger = structlog.get_logger(__name__)

# Default TTL for checkpoints in conversational workflows (30 minutes)
DEFAULT_CHECKPOINT_TTL_SECONDS = 1800

# Collection names
CHECKPOINT_COLLECTION = "checkpoints"
CHECKPOINT_WRITES_COLLECTION = "checkpoint_writes"


def create_mongodb_checkpointer(
    client: MongoClient,  # type: ignore[type-arg]
    database: str,
    ttl_seconds: int = DEFAULT_CHECKPOINT_TTL_SECONDS,
) -> BaseCheckpointSaver:
    """Create a MongoDB checkpointer for LangGraph workflows.

    This factory creates a checkpointer that:
    - Persists workflow state to MongoDB collections
    - Enables crash recovery by resuming from last checkpoint
    - Supports conversation session management with TTL

    The checkpointer uses two collections:
    - checkpoints: Stores checkpoint data
    - checkpoint_writes: Stores pending writes

    Collections are created automatically with TTL indexes for
    automatic cleanup of stale sessions.

    Note:
        langgraph-checkpoint-mongodb v0.3.0+ uses synchronous PyMongo client
        but provides async methods (aget_tuple, aput, etc.) that run sync
        operations via run_in_executor. This is the official approach.

    Args:
        client: PyMongo MongoClient (synchronous).
        database: MongoDB database name to use.
        ttl_seconds: TTL for checkpoint expiration (default 30 minutes).
            Set to 0 to disable TTL (checkpoints persist indefinitely).

    Returns:
        MongoDBSaver instance configured for the database.

    Example:
        ```python
        from pymongo import MongoClient

        client = MongoClient("mongodb://localhost:27017")
        checkpointer = create_mongodb_checkpointer(
            client=client,
            database="ai_model",
            ttl_seconds=1800,  # 30 minutes
        )

        # Use with LangGraph
        graph = workflow.compile(checkpointer=checkpointer)
        ```

    Note:
        The TTL index is created by MongoDBSaver automatically.
        MongoDB's TTL thread runs approximately every 60 seconds,
        so actual deletion may be delayed.
    """
    # Create the MongoDB saver with TTL
    # MongoDBSaver v0.3.0+ handles TTL index creation automatically
    checkpointer = MongoDBSaver(
        client=client,
        db_name=database,
        checkpoint_collection_name=CHECKPOINT_COLLECTION,
        writes_collection_name=CHECKPOINT_WRITES_COLLECTION,
        ttl=ttl_seconds if ttl_seconds > 0 else None,
    )

    logger.info(
        "MongoDB checkpointer created",
        database=database,
        checkpoint_collection=CHECKPOINT_COLLECTION,
        writes_collection=CHECKPOINT_WRITES_COLLECTION,
        ttl_enabled=ttl_seconds > 0,
        ttl_seconds=ttl_seconds if ttl_seconds > 0 else None,
    )

    return checkpointer


def cleanup_checkpoints(
    client: MongoClient,  # type: ignore[type-arg]
    database: str,
    thread_id: str | None = None,
) -> int:
    """Manually clean up checkpoints from MongoDB.

    Useful for cleaning up test data or force-expiring sessions.

    Args:
        client: PyMongo MongoClient (synchronous).
        database: MongoDB database name.
        thread_id: Optional thread ID to clean up. If None, cleans all.

    Returns:
        Number of checkpoints deleted.
    """
    db = client[database]
    checkpoints_collection = db[CHECKPOINT_COLLECTION]
    writes_collection = db[CHECKPOINT_WRITES_COLLECTION]

    query = {"thread_id": thread_id} if thread_id else {}

    # Delete from both collections
    checkpoint_result = checkpoints_collection.delete_many(query)
    writes_result = writes_collection.delete_many(query)

    total_deleted = checkpoint_result.deleted_count + writes_result.deleted_count

    logger.info(
        "Checkpoints cleaned up",
        database=database,
        thread_id=thread_id,
        checkpoints_deleted=checkpoint_result.deleted_count,
        writes_deleted=writes_result.deleted_count,
    )

    return total_deleted
