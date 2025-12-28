"""Infrastructure layer - MongoDB, DAPR, OpenTelemetry, external APIs."""

from plantation_model.infrastructure.collection_client import (
    CollectionClient,
    CollectionClientError,
    DocumentNotFoundError,
)
from plantation_model.infrastructure.mongodb import (
    check_mongodb_connection,
    close_mongodb_connection,
    get_database,
    get_mongodb_client,
)
from plantation_model.infrastructure.tracing import (
    get_tracer,
    instrument_fastapi,
    setup_tracing,
    shutdown_tracing,
)

__all__ = [
    # Collection client (Story 1.7)
    "CollectionClient",
    "CollectionClientError",
    "DocumentNotFoundError",
    # MongoDB
    "check_mongodb_connection",
    "close_mongodb_connection",
    "get_database",
    "get_mongodb_client",
    # Tracing
    "get_tracer",
    "instrument_fastapi",
    "setup_tracing",
    "shutdown_tracing",
]
