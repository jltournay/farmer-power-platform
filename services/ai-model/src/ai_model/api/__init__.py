"""API layer for AI Model service.

Story 13.7: Removed CostServiceServicer - cost tracking now via DAPR to platform-cost (ADR-016)
"""

from ai_model.api.grpc_server import (
    GrpcServer,
    get_grpc_server,
    start_grpc_server,
    stop_grpc_server,
)
from ai_model.api.rag_document_service import RAGDocumentServiceServicer

__all__ = [
    "GrpcServer",
    "RAGDocumentServiceServicer",
    "get_grpc_server",
    "start_grpc_server",
    "stop_grpc_server",
]
