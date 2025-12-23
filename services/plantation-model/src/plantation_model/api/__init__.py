"""API layer for Plantation Model service.

Includes both REST (FastAPI) and gRPC interfaces.
"""

from plantation_model.api.health import router as health_router
from plantation_model.api.grpc_server import (
    GrpcServer,
    get_grpc_server,
    start_grpc_server,
    stop_grpc_server,
)

__all__ = [
    "health_router",
    "GrpcServer",
    "get_grpc_server",
    "start_grpc_server",
    "stop_grpc_server",
]
