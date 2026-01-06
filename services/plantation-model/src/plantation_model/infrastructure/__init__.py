"""Infrastructure layer - MongoDB, DAPR, OpenTelemetry, external APIs."""

from plantation_model.infrastructure.collection_grpc_client import (
    CollectionClientError,
    CollectionGrpcClient,
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
    "CollectionClientError",
    "CollectionGrpcClient",
    "DocumentNotFoundError",
    "check_mongodb_connection",
    "close_mongodb_connection",
    "get_database",
    "get_mongodb_client",
    "get_tracer",
    "instrument_fastapi",
    "setup_tracing",
    "shutdown_tracing",
]
