"""AI Model gRPC client for BFF.

Story 0.75.23: RAG Query Service with BFF Integration

This client provides typed access to the AI Model service via DAPR gRPC
service invocation. All methods return fp-common Pydantic domain models (NOT dicts).

Pattern follows:
- ADR-002 §"Service Invocation Pattern" (native gRPC with dapr-app-id metadata)
- ADR-005 for retry logic (3 attempts, exponential backoff 1-10s)

CRITICAL: Uses fp-common domain models for type safety. Never returns dict[str, Any].
"""

import grpc
import grpc.aio
import structlog
from bff.infrastructure.clients.base import (
    BaseGrpcClient,
    grpc_retry,
)
from fp_common.converters import (
    retrieval_query_to_proto,
    retrieval_result_from_proto,
)
from fp_common.models import (
    RetrievalQuery,
    RetrievalResult,
)
from fp_proto.ai_model.v1 import ai_model_pb2_grpc

logger = structlog.get_logger(__name__)


class AiModelClient(BaseGrpcClient):
    """Client for AI Model gRPC service via DAPR.

    Provides access to RAG query operations:

    Query Operations:
    - query_knowledge: Query knowledge base with natural language

    All methods return typed Pydantic models from fp-common.

    Example:
        >>> client = AiModelClient()
        >>> result = await client.query_knowledge(
        ...     query="What causes blister blight in tea?",
        ...     domains=["plant_diseases"],
        ...     top_k=5
        ... )
        >>> for match in result.matches:
        ...     print(f"{match.title}: {match.score:.2f}")
        Blister Blight Treatment Guide: 0.92
    """

    def __init__(
        self,
        dapr_grpc_port: int = 50001,
        direct_host: str | None = None,
        channel: grpc.aio.Channel | None = None,
    ) -> None:
        """Initialize the AI Model client.

        Args:
            dapr_grpc_port: Port for DAPR sidecar gRPC endpoint (default: 50001).
            direct_host: Optional direct host for testing (bypasses DAPR).
            channel: Optional pre-configured channel for testing.
        """
        super().__init__(
            target_app_id="ai-model",
            dapr_grpc_port=dapr_grpc_port,
            direct_host=direct_host,
            channel=channel,
        )

    async def _get_rag_stub(self) -> ai_model_pb2_grpc.RAGDocumentServiceStub:
        """Get the RAG Document service stub."""
        return await self._get_stub(ai_model_pb2_grpc.RAGDocumentServiceStub)

    # =========================================================================
    # Query Operations (Story 0.75.23)
    # =========================================================================

    @grpc_retry
    async def query_knowledge(
        self,
        query: str,
        domains: list[str] | None = None,
        top_k: int = 5,
        confidence_threshold: float = 0.0,
        namespace: str | None = None,
    ) -> RetrievalResult:
        """Query the RAG knowledge base with natural language.

        Performs semantic search against vectorized document chunks
        using Pinecone similarity search and returns ranked results.

        Args:
            query: Natural language query text.
            domains: Optional list of knowledge domains to filter.
                     Valid domains: plant_diseases, tea_cultivation,
                     weather_patterns, quality_standards, regional_context.
            top_k: Maximum number of results to return (default: 5, max: 100).
            confidence_threshold: Minimum similarity score (0-1) to include.
            namespace: Optional Pinecone namespace for version isolation.

        Returns:
            RetrievalResult with matches and metadata.

        Raises:
            ServiceUnavailableError: If service is unavailable.
            ValueError: If query is empty.

        Example:
            >>> result = await client.query_knowledge(
            ...     query="How to treat blister blight?",
            ...     domains=["plant_diseases"],
            ...     top_k=5,
            ...     confidence_threshold=0.7
            ... )
            >>> print(f"Found {result.count} matches")
            Found 3 matches
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        try:
            stub = await self._get_rag_stub()

            # Build request using converter
            retrieval_query = RetrievalQuery(
                query=query,
                domains=domains or [],
                top_k=top_k,
                confidence_threshold=confidence_threshold,
                namespace=namespace,
            )
            request = retrieval_query_to_proto(retrieval_query)

            logger.debug(
                "Querying knowledge base",
                query_length=len(query),
                domains=domains,
                top_k=top_k,
                confidence_threshold=confidence_threshold,
                namespace=namespace,
            )

            response = await stub.QueryKnowledge(request, metadata=self._get_metadata())

            result = retrieval_result_from_proto(response)

            logger.debug(
                "Knowledge query completed",
                query_length=len(query),
                total_matches=result.total_matches,
                returned_matches=len(result.matches),
            )

            return result

        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Knowledge query")
            raise

    @grpc_retry
    async def query_knowledge_from_query(
        self,
        retrieval_query: RetrievalQuery,
    ) -> RetrievalResult:
        """Query knowledge base using a RetrievalQuery object.

        Convenience method that accepts a RetrievalQuery Pydantic model directly.

        Args:
            retrieval_query: RetrievalQuery with query parameters.

        Returns:
            RetrievalResult with matches and metadata.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        return await self.query_knowledge(
            query=retrieval_query.query,
            domains=retrieval_query.domains,
            top_k=retrieval_query.top_k,
            confidence_threshold=retrieval_query.confidence_threshold,
            namespace=retrieval_query.namespace,
        )
