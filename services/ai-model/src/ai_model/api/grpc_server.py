"""gRPC server implementation for AI Model service.

Story 0.75.10: Added RAGDocumentService registration.
Story 0.75.13c: Added VectorizationPipeline wiring for RAGDocumentService.
Story 0.75.13d: Added VectorizationJobRepository for persistent job tracking.
Story 13.7: Removed CostService - costs now published via DAPR to platform-cost (ADR-016)
Story 9.12a: Added AgentConfigService for admin visibility (ADR-019)
"""

import grpc
import structlog
from ai_model.api.agent_config_service import AgentConfigServiceServicer
from ai_model.api.rag_document_service import RAGDocumentServiceServicer
from ai_model.config import settings
from ai_model.infrastructure.mongodb import get_database
from ai_model.infrastructure.repositories import (
    ExtractionJobRepository,
    MongoDBVectorizationJobRepository,
    RagChunkRepository,
    RagDocumentRepository,
)
from ai_model.infrastructure.repositories.agent_config_repository import AgentConfigRepository
from ai_model.infrastructure.repositories.prompt_repository import PromptRepository
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection

logger = structlog.get_logger(__name__)

# Service name for health checks
SERVICE_NAME = "farmer_power.ai_model.v1.AiModelService"


class AiModelServiceServicer(ai_model_pb2_grpc.AiModelServiceServicer):
    """gRPC servicer for AI Model service.

    Implements the AiModelService proto definition.
    """

    async def Extract(
        self,
        request: ai_model_pb2.ExtractionRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.ExtractionResponse:
        """Extract structured data from raw content using LLM.

        This is a stub implementation. Full implementation in Story 0.75.17.

        Args:
            request: The extraction request containing raw content and agent ID.
            context: gRPC context for the request.

        Returns:
            ExtractionResponse with success=False indicating not implemented.
        """
        logger.info(
            "Extract RPC called (stub)",
            ai_agent_id=request.ai_agent_id,
            content_type=request.content_type,
            trace_id=request.trace_id,
        )

        # Return not implemented response
        return ai_model_pb2.ExtractionResponse(
            success=False,
            extracted_fields_json="{}",
            confidence=0.0,
            validation_passed=False,
            error_message="Extract RPC not implemented. See Story 0.75.17.",
        )

    async def HealthCheck(
        self,
        request: ai_model_pb2.HealthCheckRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.HealthCheckResponse:
        """Health check for service readiness.

        Args:
            request: Empty health check request.
            context: gRPC context for the request.

        Returns:
            HealthCheckResponse with health status and version.
        """
        return ai_model_pb2.HealthCheckResponse(
            healthy=True,
            version=settings.service_version,
        )


class GrpcServer:
    """Async gRPC server wrapper with health checking and reflection."""

    def __init__(self) -> None:
        """Initialize gRPC server configuration."""
        self._server: grpc.aio.Server | None = None
        self._health_servicer: health.HealthServicer | None = None

    async def start(self) -> None:
        """Start the gRPC server.

        Configures:
        - AiModelService (Extract, HealthCheck)
        - RAGDocumentService (Story 0.75.10)
        - Health checking service (grpc.health.v1.Health)
        - Server reflection for debugging
        - Concurrent request handling

        Note: CostService was removed in Story 13.7 - costs now published via DAPR.
        """
        self._server = grpc.aio.server(
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.keepalive_time_ms", 30000),
                ("grpc.keepalive_timeout_ms", 10000),
            ],
        )

        # Initialize database
        db = await get_database()

        # Add AiModelService
        ai_model_servicer = AiModelServiceServicer()
        ai_model_pb2_grpc.add_AiModelServiceServicer_to_server(ai_model_servicer, self._server)

        # Story 0.75.10: Add RAGDocumentService
        rag_doc_repository = RagDocumentRepository(db)
        await rag_doc_repository.ensure_indexes()

        # Story 0.75.13c: Create shared dependencies for RAG workflows
        # RagChunkRepository is needed by both ChunkingWorkflow and VectorizationPipeline
        rag_chunk_repository = RagChunkRepository(db)
        await rag_chunk_repository.ensure_indexes()

        # Story 0.75.13c: Create ChunkingWorkflow (INDEPENDENT of Pinecone)
        # Chunking uses MongoDB only, not Pinecone
        # ChunkingWorkflow creates SemanticChunker internally using settings
        from ai_model.services.chunking_workflow import ChunkingWorkflow

        chunking_workflow = ChunkingWorkflow(
            chunk_repository=rag_chunk_repository,
            settings=settings,
        )
        logger.info("ChunkingWorkflow initialized for RAGDocumentService")

        # Story 0.75.13d: Create VectorizationJobRepository for persistent job tracking
        vectorization_job_repository = MongoDBVectorizationJobRepository(
            db=db,
            ttl_hours=settings.vectorization_job_ttl_hours,
        )
        await vectorization_job_repository.ensure_indexes()
        logger.info(
            "VectorizationJobRepository initialized",
            ttl_hours=settings.vectorization_job_ttl_hours,
        )

        # Story 0.75.13c: Create VectorizationPipeline for RAGDocumentService
        # Only create if Pinecone is configured
        vectorization_pipeline = None
        if settings.pinecone_enabled:
            # Import pipeline dependencies
            from ai_model.infrastructure.pinecone_vector_store import PineconeVectorStore
            from ai_model.services.embedding_service import EmbeddingService
            from ai_model.services.vectorization_pipeline import VectorizationPipeline

            embedding_service = EmbeddingService(settings=settings)
            vector_store = PineconeVectorStore(settings=settings)

            # Story 0.75.13d: Add job_repository for persistent job tracking
            vectorization_pipeline = VectorizationPipeline(
                chunk_repository=rag_chunk_repository,
                document_repository=rag_doc_repository,
                embedding_service=embedding_service,
                vector_store=vector_store,
                settings=settings,
                job_repository=vectorization_job_repository,
            )
            logger.info("VectorizationPipeline initialized with persistent job tracking")
        else:
            logger.warning(
                "Pinecone not configured - VectorizationPipeline disabled. "
                "Set PINECONE_API_KEY to enable vectorization."
            )

        # Story 9.9a: Create ExtractionWorkflow for document extraction
        from ai_model.infrastructure.blob_storage import BlobStorageClient
        from ai_model.services.extraction_workflow import ExtractionWorkflow

        extraction_job_repository = ExtractionJobRepository(db)
        await extraction_job_repository.ensure_indexes()
        blob_client = BlobStorageClient()
        extraction_workflow = ExtractionWorkflow(
            document_repository=rag_doc_repository,
            job_repository=extraction_job_repository,
            blob_client=blob_client,
            settings=settings,
        )
        logger.info("ExtractionWorkflow initialized for RAGDocumentService")

        # Story 9.9a: Create RetrievalService for QueryKnowledge (requires Pinecone)
        retrieval_service = None
        if settings.pinecone_enabled:
            from ai_model.services.retrieval_service import RetrievalService

            # Reuse embedding_service and vector_store from VectorizationPipeline
            retrieval_service = RetrievalService(
                embedding_service=embedding_service,
                vector_store=vector_store,
                chunk_repository=rag_chunk_repository,
            )
            logger.info("RetrievalService initialized for RAGDocumentService")
        else:
            logger.warning("Pinecone not configured - RetrievalService disabled. QueryKnowledge will be unavailable.")

        rag_doc_servicer = RAGDocumentServiceServicer(
            rag_doc_repository,
            vectorization_pipeline=vectorization_pipeline,
            blob_client=blob_client,
        )
        # Wire chunking workflow (independent of vectorization)
        rag_doc_servicer.set_chunking_workflow(chunking_workflow)
        # Wire extraction workflow
        rag_doc_servicer.set_extraction_workflow(extraction_workflow)
        # Wire retrieval service (may be None if Pinecone not configured)
        if retrieval_service:
            rag_doc_servicer.set_retrieval_service(retrieval_service)

        ai_model_pb2_grpc.add_RAGDocumentServiceServicer_to_server(rag_doc_servicer, self._server)
        logger.info("RAGDocumentService registered")

        # Story 9.12a: Add AgentConfigService for admin visibility (ADR-019)
        agent_config_repository = AgentConfigRepository(db)
        await agent_config_repository.ensure_indexes()

        prompt_repository = PromptRepository(db)
        await prompt_repository.ensure_indexes()

        agent_config_servicer = AgentConfigServiceServicer(
            db=db,
            agent_config_repository=agent_config_repository,
            prompt_repository=prompt_repository,
        )
        ai_model_pb2_grpc.add_AgentConfigServiceServicer_to_server(agent_config_servicer, self._server)
        logger.info("AgentConfigService registered")

        # Add health checking service
        self._health_servicer = health.HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(self._health_servicer, self._server)

        # Set initial health status
        self._health_servicer.set(
            SERVICE_NAME,
            health_pb2.HealthCheckResponse.SERVING,
        )
        self._health_servicer.set(
            "",  # Overall server health
            health_pb2.HealthCheckResponse.SERVING,
        )

        # Enable server reflection for debugging with grpcurl/grpcui
        # Note: CostService removed in Story 13.7 - costs now published via DAPR
        # Note: AgentConfigService added in Story 9.12a for admin visibility
        service_names = (
            ai_model_pb2.DESCRIPTOR.services_by_name["AiModelService"].full_name,
            ai_model_pb2.DESCRIPTOR.services_by_name["RAGDocumentService"].full_name,
            ai_model_pb2.DESCRIPTOR.services_by_name["AgentConfigService"].full_name,
            health_pb2.DESCRIPTOR.services_by_name["Health"].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(service_names, self._server)

        # Bind to address
        listen_addr = f"[::]:{settings.grpc_port}"
        self._server.add_insecure_port(listen_addr)

        await self._server.start()
        logger.info(
            "gRPC server started",
            address=listen_addr,
            services=list(service_names),
        )

    async def stop(self, grace_period: float = 5.0) -> None:
        """Stop the gRPC server gracefully.

        Args:
            grace_period: Time in seconds to wait for in-flight requests.
        """
        if self._server is None:
            return

        logger.info("Stopping gRPC server", grace_period=grace_period)

        # Mark services as not serving
        if self._health_servicer:
            self._health_servicer.set(
                SERVICE_NAME,
                health_pb2.HealthCheckResponse.NOT_SERVING,
            )
            self._health_servicer.set(
                "",
                health_pb2.HealthCheckResponse.NOT_SERVING,
            )

        await self._server.stop(grace_period)
        self._server = None
        logger.info("gRPC server stopped")

    async def wait_for_termination(self) -> None:
        """Wait for the server to terminate."""
        if self._server:
            await self._server.wait_for_termination()

    def set_serving(self, serving: bool = True) -> None:
        """Set the health status of the service.

        Args:
            serving: True if service is healthy, False otherwise.
        """
        if self._health_servicer:
            status = health_pb2.HealthCheckResponse.SERVING if serving else health_pb2.HealthCheckResponse.NOT_SERVING
            self._health_servicer.set(SERVICE_NAME, status)
            self._health_servicer.set("", status)


# Global server instance
_grpc_server: GrpcServer | None = None


async def get_grpc_server() -> GrpcServer:
    """Get or create the gRPC server singleton.

    Returns:
        GrpcServer: The gRPC server instance.
    """
    global _grpc_server

    if _grpc_server is None:
        _grpc_server = GrpcServer()

    return _grpc_server


async def start_grpc_server() -> GrpcServer:
    """Start the gRPC server.

    Returns:
        GrpcServer: The started gRPC server instance.
    """
    server = await get_grpc_server()
    await server.start()
    return server


async def stop_grpc_server() -> None:
    """Stop the gRPC server if running."""
    global _grpc_server

    if _grpc_server is not None:
        await _grpc_server.stop()
        _grpc_server = None
