"""gRPC server implementation for AI Model service.

Story 0.75.5: Added CostService registration.
Story 0.75.10: Added RAGDocumentService registration.
"""

import grpc
import structlog
from ai_model.api.cost_service import CostServiceServicer
from ai_model.api.rag_document_service import RAGDocumentServiceServicer
from ai_model.config import settings
from ai_model.infrastructure.mongodb import get_database
from ai_model.infrastructure.repositories import LlmCostEventRepository, RagDocumentRepository
from ai_model.llm.budget_monitor import BudgetMonitor
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
        self._budget_monitor: BudgetMonitor | None = None

    async def start(self) -> None:
        """Start the gRPC server.

        Configures:
        - AiModelService (Extract, HealthCheck)
        - CostService (Story 0.75.5)
        - Health checking service (grpc.health.v1.Health)
        - Server reflection for debugging
        - Concurrent request handling
        """
        self._server = grpc.aio.server(
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.keepalive_time_ms", 30000),
                ("grpc.keepalive_timeout_ms", 10000),
            ],
        )

        # Story 0.75.5: Initialize dependencies (following plantation-model pattern)
        db = await get_database()
        cost_repository = LlmCostEventRepository(db)
        budget_monitor = BudgetMonitor(
            daily_threshold_usd=settings.llm_cost_alert_daily_usd,
            monthly_threshold_usd=settings.llm_cost_alert_monthly_usd,
        )

        # Ensure indexes
        await cost_repository.ensure_indexes()

        # Store budget_monitor for access by other components
        self._budget_monitor = budget_monitor

        # Add AiModelService
        ai_model_servicer = AiModelServiceServicer()
        ai_model_pb2_grpc.add_AiModelServiceServicer_to_server(ai_model_servicer, self._server)

        # Story 0.75.5: Add CostService
        cost_servicer = CostServiceServicer(cost_repository, budget_monitor)
        ai_model_pb2_grpc.add_CostServiceServicer_to_server(cost_servicer, self._server)
        logger.info("CostService registered")

        # Story 0.75.10: Add RAGDocumentService
        rag_doc_repository = RagDocumentRepository(db)
        await rag_doc_repository.ensure_indexes()
        rag_doc_servicer = RAGDocumentServiceServicer(rag_doc_repository)
        ai_model_pb2_grpc.add_RAGDocumentServiceServicer_to_server(rag_doc_servicer, self._server)
        logger.info("RAGDocumentService registered")

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
        service_names = (
            ai_model_pb2.DESCRIPTOR.services_by_name["AiModelService"].full_name,
            ai_model_pb2.DESCRIPTOR.services_by_name["CostService"].full_name,
            ai_model_pb2.DESCRIPTOR.services_by_name["RAGDocumentService"].full_name,
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
