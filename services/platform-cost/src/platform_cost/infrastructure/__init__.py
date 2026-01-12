"""Infrastructure layer for platform cost service.

Provides:
- MongoDB connection management
- OpenTelemetry tracing setup
- Repositories for cost data persistence
"""

from platform_cost.infrastructure.mongodb import (
    check_mongodb_connection,
    close_mongodb_connection,
    get_database,
    get_mongodb_client,
)
from platform_cost.infrastructure.tracing import (
    get_tracer,
    instrument_fastapi,
    setup_tracing,
    shutdown_tracing,
)

__all__ = [
    "check_mongodb_connection",
    "close_mongodb_connection",
    "get_database",
    "get_mongodb_client",
    "get_tracer",
    "instrument_fastapi",
    "setup_tracing",
    "shutdown_tracing",
]
