"""gRPC server implementation for Platform Cost service.

Story 13.4: gRPC UnifiedCostService (ADR-016)

This module provides the gRPC server wrapper with:
- UnifiedCostService (cost queries and budget management)
- Health checking service (grpc.health.v1.Health)
- Server reflection for debugging
"""

import grpc
import structlog
from fp_proto.platform_cost.v1 import platform_cost_pb2, platform_cost_pb2_grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection

from platform_cost.api.unified_cost_service import UnifiedCostServiceServicer
from platform_cost.config import settings
from platform_cost.infrastructure.repositories.cost_repository import (
    UnifiedCostRepository,
)
from platform_cost.infrastructure.repositories.threshold_repository import (
    ThresholdRepository,
)
from platform_cost.services.budget_monitor import BudgetMonitor

logger = structlog.get_logger(__name__)

# Service name for health checks
SERVICE_NAME = "farmer_power.platform_cost.v1.UnifiedCostService"


class GrpcServer:
    """Async gRPC server wrapper with health checking and reflection."""

    def __init__(
        self,
        cost_repository: UnifiedCostRepository,
        budget_monitor: BudgetMonitor,
        threshold_repository: ThresholdRepository,
    ) -> None:
        """Initialize gRPC server configuration.

        Args:
            cost_repository: Repository for cost event queries.
            budget_monitor: In-memory budget tracking.
            threshold_repository: Persistent threshold storage.
        """
        self._server: grpc.aio.Server | None = None
        self._health_servicer: health.HealthServicer | None = None
        self._cost_repository = cost_repository
        self._budget_monitor = budget_monitor
        self._threshold_repository = threshold_repository

    async def start(self) -> None:
        """Start the gRPC server.

        Configures:
        - UnifiedCostService (cost queries and budget management)
        - Health checking service (grpc.health.v1.Health)
        - Server reflection for debugging
        """
        self._server = grpc.aio.server(
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.keepalive_time_ms", 30000),
                ("grpc.keepalive_timeout_ms", 10000),
            ],
        )

        # Add UnifiedCostService
        cost_servicer = UnifiedCostServiceServicer(
            cost_repository=self._cost_repository,
            budget_monitor=self._budget_monitor,
            threshold_repository=self._threshold_repository,
        )
        platform_cost_pb2_grpc.add_UnifiedCostServiceServicer_to_server(cost_servicer, self._server)

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
            platform_cost_pb2.DESCRIPTOR.services_by_name["UnifiedCostService"].full_name,
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
