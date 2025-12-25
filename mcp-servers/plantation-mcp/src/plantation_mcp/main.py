"""Plantation MCP Server - gRPC server entrypoint."""

import asyncio
import signal
from concurrent import futures

import grpc
import structlog
from fp_proto.mcp.v1 import mcp_tool_pb2, mcp_tool_pb2_grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorServer
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from plantation_mcp.api.mcp_service import McpToolServiceServicer
from plantation_mcp.config import settings
from plantation_mcp.infrastructure.plantation_client import PlantationClient

logger = structlog.get_logger(__name__)


def setup_telemetry() -> None:
    """Configure OpenTelemetry tracing."""
    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Instrument gRPC server
    GrpcAioInstrumentorServer().instrument()


async def serve() -> None:
    """Start the gRPC server."""
    logger.info(
        "Starting Plantation MCP Server",
        port=settings.grpc_port,
        max_workers=settings.grpc_max_workers,
    )

    # Setup telemetry
    setup_telemetry()

    # Create gRPC server
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=settings.grpc_max_workers),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )

    # Create plantation client
    plantation_client = PlantationClient()

    # Add MCP Tool Service
    mcp_servicer = McpToolServiceServicer(plantation_client=plantation_client)
    mcp_tool_pb2_grpc.add_McpToolServiceServicer_to_server(mcp_servicer, server)

    # Add health checking
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("McpToolService", health_pb2.HealthCheckResponse.SERVING)

    # Add reflection for debugging
    service_names = (
        mcp_tool_pb2.DESCRIPTOR.services_by_name["McpToolService"].full_name,
        health_pb2.DESCRIPTOR.services_by_name["Health"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    # Start server
    listen_addr = f"[::]:{settings.grpc_port}"
    server.add_insecure_port(listen_addr)
    await server.start()

    logger.info("Plantation MCP Server started", address=listen_addr)

    # Handle shutdown
    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        logger.info("Received shutdown signal")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    await shutdown_event.wait()

    logger.info("Shutting down server...")
    await server.stop(grace=5)
    logger.info("Server stopped")


def main() -> None:
    """Main entry point."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    asyncio.run(serve())


if __name__ == "__main__":
    main()
