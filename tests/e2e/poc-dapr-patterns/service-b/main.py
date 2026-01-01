"""
Service B - PoC for DAPR Patterns (ADR-010, ADR-011)

This service demonstrates:
1. gRPC server (CalculatorService) - called by Service A via DAPR
2. Streaming pub/sub subscription - receives events from Service A
3. DLQ monitor - subscribes to dead letter topics
4. Calls Service A's EchoService via DAPR gRPC proxy
5. FastAPI for health checks only

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

# Will be generated from proto
import poc_pb2
import poc_pb2_grpc

# Configuration
GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))
HTTP_PORT = int(os.getenv("HTTP_PORT", "8000"))
SERVICE_NAME = "service-b"
DAPR_GRPC_PORT = int(os.getenv("DAPR_GRPC_PORT", "50001"))

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(SERVICE_NAME)

# Track received messages and DLQ messages for testing
received_messages: list[dict] = []
dlq_messages: list[dict] = []
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


@app.get("/dlq-messages")
async def get_dlq_messages():
    """Get messages received in DLQ (for testing)."""
    return {"messages": dlq_messages, "count": len(dlq_messages)}


@app.post("/clear-messages")
async def clear_messages():
    """Clear all received messages (for testing)."""
    received_messages.clear()
    dlq_messages.clear()
    return {"status": "cleared"}


@app.post("/publish-to-a")
async def publish_to_a(event_type: str = "success", event_id: str = None):
    """Publish a test event to Service A (for testing)."""
    if event_id is None:
        event_id = f"evt-{int(time.time() * 1000)}"

    event_data = {"type": event_type, "id": event_id, "from": SERVICE_NAME}
    publish_event_to_a(event_data)
    return {"status": "published", "event": event_data}


# =============================================================================
# gRPC Server - CalculatorService (Port 50051)
# =============================================================================


class CalculatorServicer(poc_pb2_grpc.CalculatorServiceServicer):
    """CalculatorService implementation - called by Service A via DAPR."""

    def Add(self, request, context):
        result = request.a + request.b
        logger.info(f"Add called: {request.a} + {request.b} = {result}")
        return poc_pb2.AddResponse(
            result=result,
            service=SERVICE_NAME,
        )


def start_grpc_server():
    """Start the gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    poc_pb2_grpc.add_CalculatorServiceServicer_to_server(CalculatorServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    logger.info(f"gRPC server started on port {GRPC_PORT}")
    return server


# =============================================================================
# Pub/Sub Streaming Subscription
# =============================================================================


def handle_event_from_a(message) -> TopicEventResponse:
    """Handle events published by Service A.

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


def handle_dlq_message(message) -> TopicEventResponse:
    """Handle messages that ended up in DLQ after retries exhausted."""
    # message.data() returns dict directly, not JSON string
    raw_data = message.data()
    data = raw_data if isinstance(raw_data, dict) else json.loads(raw_data)
    msg_id = data.get("id", "unknown")

    logger.warning(f"DLQ received message: {msg_id}")
    dlq_messages.append({
        "id": msg_id,
        "data": data,
        "received_at": time.time(),
    })
    return TopicEventResponse("success")


def start_subscriptions():
    """Start streaming subscriptions."""
    logger.info("Starting pub/sub subscriptions...")

    # Wait for DAPR sidecar to be ready
    time.sleep(5)

    try:
        client = DaprClient()

        # Main event subscription
        close_fn_main = client.subscribe_with_handler(
            pubsub_name="pubsub",
            topic="poc.events.to-b",
            handler_fn=handle_event_from_a,
            dead_letter_topic="poc.dlq.service-b",
        )
        logger.info("Subscription established for topic: poc.events.to-b")

        # DLQ subscription - monitor dead letters from Service A
        close_fn_dlq_a = client.subscribe_with_handler(
            pubsub_name="pubsub",
            topic="poc.dlq.service-a",
            handler_fn=handle_dlq_message,
        )
        logger.info("DLQ subscription established for topic: poc.dlq.service-a")

        # DLQ subscription - monitor our own dead letters
        close_fn_dlq_b = client.subscribe_with_handler(
            pubsub_name="pubsub",
            topic="poc.dlq.service-b",
            handler_fn=handle_dlq_message,
        )
        logger.info("DLQ subscription established for topic: poc.dlq.service-b")

        subscription_ready.set()

        # Keep subscriptions alive
        while True:
            time.sleep(1)

    except Exception as e:
        logger.exception(f"Subscription failed: {e}")


# =============================================================================
# DAPR Client - Call Service A
# =============================================================================


def call_service_a_echo(message: str) -> str:
    """Call Service A's Echo via DAPR gRPC proxy."""
    logger.info(f"Calling Service A Echo({message})")

    # Connect to DAPR's gRPC proxy
    channel = grpc.insecure_channel(f"localhost:{DAPR_GRPC_PORT}")

    # Add DAPR metadata to route to service-a
    metadata = [("dapr-app-id", "poc-service-a")]

    stub = poc_pb2_grpc.EchoServiceStub(channel)
    request = poc_pb2.EchoRequest(message=message)

    response = stub.Echo(request, metadata=metadata)
    logger.info(f"Service A returned: {response.message}")

    return response.message


def publish_event_to_a(event_data: dict) -> None:
    """Publish an event to Service A."""
    logger.info(f"Publishing event to Service A: {event_data}")

    with DaprClient() as client:
        client.publish_event(
            pubsub_name="pubsub",
            topic_name="poc.events.to-a",
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

    # Start pub/sub subscriptions in background thread
    subscription_thread = threading.Thread(target=start_subscriptions, daemon=True)
    subscription_thread.start()

    # Start FastAPI for health endpoints
    logger.info(f"Starting FastAPI on port {HTTP_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT, log_level="info")


if __name__ == "__main__":
    main()
