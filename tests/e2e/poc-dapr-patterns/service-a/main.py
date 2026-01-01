"""
Service A - PoC for DAPR Patterns (ADR-010, ADR-011)

This service demonstrates:
1. gRPC server (EchoService) - called by Service B via DAPR
2. Streaming pub/sub subscription - receives events from Service B
3. Calls Service B's CalculatorService via DAPR gRPC proxy
4. FastAPI for health checks only

Architecture per ADR-011:
- Port 8000: FastAPI health endpoints (direct, no DAPR)
- Port 50051: gRPC server (via DAPR sidecar)
- Pub/sub: Outbound streaming subscription (no extra port)
"""

import json
import logging
import os
import threading
import time
from concurrent import futures

import grpc
import uvicorn
from dapr.clients import DaprClient
from dapr.clients.grpc._response import TopicEventResponse
from fastapi import FastAPI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# Will be generated from proto
import poc_pb2
import poc_pb2_grpc

# Configuration
GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))
HTTP_PORT = int(os.getenv("HTTP_PORT", "8000"))
SERVICE_NAME = "service-a"
DAPR_GRPC_PORT = int(os.getenv("DAPR_GRPC_PORT", "50001"))

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(SERVICE_NAME)

# Track received messages for testing
received_messages: list[dict] = []
subscription_ready = threading.Event()


# =============================================================================
# FastAPI Health Endpoints (Port 8000)
# =============================================================================

app = FastAPI(title=f"{SERVICE_NAME} Health")


@app.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "healthy", "service": SERVICE_NAME}


@app.get("/ready")
async def ready():
    """Readiness probe."""
    return {
        "status": "ready",
        "service": SERVICE_NAME,
        "subscription_ready": subscription_ready.is_set(),
    }


@app.get("/received-messages")
async def get_received_messages():
    """Get messages received via pub/sub (for testing)."""
    return {"messages": received_messages, "count": len(received_messages)}


@app.post("/clear-messages")
async def clear_messages():
    """Clear received messages (for testing)."""
    received_messages.clear()
    return {"status": "cleared"}


@app.get("/call-service-b")
async def call_service_b(a: int = 5, b: int = 3):
    """Trigger a gRPC call to Service B's Calculator (for testing ADR-005).

    This uses the singleton client with Tenacity retry.
    """
    try:
        result = service_b_client.add(a, b)
        stats = service_b_client.get_stats()
        return {
            "status": "success",
            "result": result,
            "a": a,
            "b": b,
            "client_stats": stats,
        }
    except Exception as e:
        stats = service_b_client.get_stats()
        return {
            "status": "error",
            "error": str(e),
            "client_stats": stats,
        }


@app.get("/client-stats")
async def get_client_stats():
    """Get gRPC client statistics (for testing ADR-005)."""
    return service_b_client.get_stats()


# =============================================================================
# gRPC Server - EchoService (Port 50051)
# =============================================================================


class EchoServicer(poc_pb2_grpc.EchoServiceServicer):
    """EchoService implementation - called by Service B via DAPR."""

    def Echo(self, request, context):
        logger.info(f"Echo called with message: {request.message}")
        return poc_pb2.EchoResponse(
            message=request.message,
            service=SERVICE_NAME,
        )


def start_grpc_server():
    """Start the gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    poc_pb2_grpc.add_EchoServiceServicer_to_server(EchoServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    logger.info(f"gRPC server started on port {GRPC_PORT}")
    return server


# =============================================================================
# Pub/Sub Streaming Subscription
# =============================================================================


def handle_event_from_b(message) -> TopicEventResponse:
    """Handle events published by Service B.

    Message types:
    - {"type": "success", "id": "..."} - Process normally
    - {"type": "retry_once", "id": "..."} - Fail once, then succeed
    - {"type": "always_fail", "id": "..."} - Always fail (goes to DLQ)

    Returns:
    - TopicEventResponse("success") - Message processed successfully
    - TopicEventResponse("retry") - Retry the message
    - TopicEventResponse("drop") - Discard the message (goes to DLQ if configured)
    """
    # message.data() returns dict directly, not JSON string
    raw_data = message.data()
    data = raw_data if isinstance(raw_data, dict) else json.loads(raw_data)
    msg_type = data.get("type", "unknown")
    msg_id = data.get("id", "unknown")

    logger.info(f"Received event: type={msg_type}, id={msg_id}")

    if msg_type == "success":
        logger.info(f"SUCCESS: Processing message {msg_id}")
        received_messages.append({"id": msg_id, "type": msg_type, "status": "success"})
        return TopicEventResponse("success")

    elif msg_type == "retry_once":
        # Check if we've already retried this message
        retry_key = f"retry_{msg_id}"
        already_retried = any(m.get("retry_key") == retry_key for m in received_messages)

        if not already_retried:
            logger.warning(f"RETRY: First attempt for {msg_id} - failing")
            received_messages.append({"id": msg_id, "type": msg_type, "status": "retrying", "retry_key": retry_key})
            return TopicEventResponse("retry")

        logger.info(f"SUCCESS after retry: {msg_id}")
        received_messages.append({"id": msg_id, "type": msg_type, "status": "success_after_retry"})
        return TopicEventResponse("success")

    elif msg_type == "always_fail":
        logger.error(f"FAILING: {msg_id} - will go to DLQ after retries")
        received_messages.append({"id": msg_id, "type": msg_type, "status": "failing"})
        return TopicEventResponse("drop")  # This will go to DLQ

    else:
        logger.warning(f"Unknown message type: {msg_type}")
        received_messages.append({"id": msg_id, "type": msg_type, "status": "unknown"})
        return TopicEventResponse("success")


def start_subscription():
    """Start streaming subscription to receive events from Service B."""
    logger.info("Starting pub/sub subscription...")

    # Wait for DAPR sidecar to be ready
    time.sleep(5)

    try:
        client = DaprClient()

        close_fn = client.subscribe_with_handler(
            pubsub_name="pubsub",
            topic="poc.events.to-a",
            handler_fn=handle_event_from_b,
            dead_letter_topic="poc.dlq.service-a",
        )

        subscription_ready.set()
        logger.info("Subscription established for topic: poc.events.to-a")

        # Keep subscription alive
        while True:
            time.sleep(1)

    except Exception as e:
        logger.exception(f"Subscription failed: {e}")


# =============================================================================
# gRPC Client - Call Service B (ADR-005 Pattern)
# =============================================================================


class ServiceBClient:
    """gRPC client for Service B following ADR-005 pattern.

    Key features:
    - Singleton channel (created once, reused)
    - Tenacity retry on transient failures
    - Keepalive to detect dead connections
    """

    def __init__(self) -> None:
        self._channel: grpc.Channel | None = None
        self._stub: poc_pb2_grpc.CalculatorServiceStub | None = None
        self._call_count = 0
        self._retry_count = 0

    def _get_stub(self) -> poc_pb2_grpc.CalculatorServiceStub:
        """Lazy singleton channel - created once, reused."""
        if self._stub is None:
            logger.info("Creating new gRPC channel to DAPR proxy (singleton)")
            self._channel = grpc.insecure_channel(
                f"localhost:{DAPR_GRPC_PORT}",
                options=[
                    ("grpc.keepalive_time_ms", 10000),      # Send keepalive every 10s
                    ("grpc.keepalive_timeout_ms", 5000),    # Wait 5s for response
                    ("grpc.keepalive_permit_without_calls", True),  # Keepalive even when idle
                    ("grpc.http2.min_time_between_pings_ms", 10000),
                ],
            )
            self._stub = poc_pb2_grpc.CalculatorServiceStub(self._channel)
        return self._stub

    @retry(
        retry=retry_if_exception_type(grpc.RpcError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Retry attempt {retry_state.attempt_number} after error: {retry_state.outcome.exception()}"
        ),
    )
    def add(self, a: int, b: int) -> int:
        """Call Calculator.Add with retry logic."""
        self._call_count += 1
        logger.info(f"Calculator.Add({a}, {b}) - call #{self._call_count}")

        stub = self._get_stub()
        metadata = [("dapr-app-id", "poc-service-b")]
        request = poc_pb2.AddRequest(a=a, b=b)

        try:
            response = stub.Add(request, metadata=metadata, timeout=5)
            logger.info(f"Service B returned: {response.result}")
            return response.result
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e.code()} - {e.details()}")
            # Reset stub to force reconnection on next attempt
            self._stub = None
            self._channel = None
            self._retry_count += 1
            raise

    def get_stats(self) -> dict:
        """Get client statistics for testing."""
        return {
            "call_count": self._call_count,
            "retry_count": self._retry_count,
            "channel_active": self._channel is not None,
        }

    def close(self) -> None:
        """Clean up resources."""
        if self._channel:
            self._channel.close()
            self._channel = None
            self._stub = None


# Global singleton client
service_b_client = ServiceBClient()


def publish_event_to_b(event_data: dict) -> None:
    """Publish an event to Service B."""
    logger.info(f"Publishing event to Service B: {event_data}")

    with DaprClient() as client:
        client.publish_event(
            pubsub_name="pubsub",
            topic_name="poc.events.to-b",
            data=json.dumps(event_data),
            data_content_type="application/json",
        )


# =============================================================================
# Main
# =============================================================================


def main():
    logger.info(f"Starting {SERVICE_NAME}...")

    # Start gRPC server
    grpc_server = start_grpc_server()

    # Start pub/sub subscription in background thread
    subscription_thread = threading.Thread(target=start_subscription, daemon=True)
    subscription_thread.start()

    # Start FastAPI for health endpoints
    logger.info(f"Starting FastAPI on port {HTTP_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT, log_level="info")


if __name__ == "__main__":
    main()
