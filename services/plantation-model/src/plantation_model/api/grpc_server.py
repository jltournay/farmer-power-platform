"""gRPC server implementation for Plantation Model service."""

import grpc
import structlog
from fp_proto.plantation.v1 import plantation_pb2, plantation_pb2_grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection

from plantation_model.api.plantation_service import PlantationServiceServicer
from plantation_model.config import settings
from plantation_model.domain.models.id_generator import IDGenerator
from plantation_model.infrastructure.google_elevation import GoogleElevationClient
from plantation_model.infrastructure.mongodb import get_database
from plantation_model.infrastructure.repositories.collection_point_repository import (
    CollectionPointRepository,
)
from plantation_model.infrastructure.repositories.factory_repository import (
    FactoryRepository,
)
from plantation_model.infrastructure.repositories.farmer_repository import (
    FarmerRepository,
)

logger = structlog.get_logger(__name__)

# Service name for health checks
SERVICE_NAME = "farmer_power.plantation.v1.PlantationService"


class GrpcServer:
    """Async gRPC server wrapper with health checking and reflection."""

    def __init__(self) -> None:
        """Initialize gRPC server configuration."""
        self._server: grpc.aio.Server | None = None
        self._health_servicer: health.HealthServicer | None = None

    async def start(self) -> None:
        """Start the gRPC server.

        Configures:
        - PlantationService (Factory/CollectionPoint CRUD)
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

        # Initialize dependencies
        db = await get_database()
        factory_repo = FactoryRepository(db)
        cp_repo = CollectionPointRepository(db)
        farmer_repo = FarmerRepository(db)
        id_generator = IDGenerator(db)
        elevation_client = GoogleElevationClient(settings.google_elevation_api_key)

        # Ensure indexes are created
        await factory_repo.ensure_indexes()
        await cp_repo.ensure_indexes()
        await farmer_repo.ensure_indexes()

        # Add PlantationService
        plantation_servicer = PlantationServiceServicer(
            factory_repo=factory_repo,
            collection_point_repo=cp_repo,
            farmer_repo=farmer_repo,
            id_generator=id_generator,
            elevation_client=elevation_client,
        )
        plantation_pb2_grpc.add_PlantationServiceServicer_to_server(
            plantation_servicer, self._server
        )

        # Add health checking service
        self._health_servicer = health.HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(
            self._health_servicer, self._server
        )

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
            plantation_pb2.DESCRIPTOR.services_by_name["PlantationService"].full_name,
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
            status = (
                health_pb2.HealthCheckResponse.SERVING
                if serving
                else health_pb2.HealthCheckResponse.NOT_SERVING
            )
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
