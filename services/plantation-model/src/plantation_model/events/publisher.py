"""DAPR pub/sub publisher for event publishing.

Story 0.6.14: Uses official DAPR Python SDK per ADR-010.
Replaces custom httpx-based implementation with SDK's publish_event().
"""

import json
import logging
from typing import Any

from dapr.clients import DaprClient
from dapr.clients.exceptions import DaprInternalError
from grpc import RpcError
from pydantic import BaseModel

logger = logging.getLogger(__name__)


async def publish_event(
    pubsub_name: str,
    topic: str,
    data: BaseModel | dict[str, Any],
) -> bool:
    """Publish an event to DAPR pub/sub using the official SDK.

    Story 0.6.14: Implements ADR-010 standard pattern for publishing.

    Args:
        pubsub_name: Name of the DAPR pub/sub component (e.g., "pubsub").
        topic: Topic name to publish to (e.g., "plantation.quality.graded").
        data: Event data as Pydantic model or dict.

    Returns:
        True if event was published successfully, False otherwise.

    Note:
        Per ADR-010, the SDK handles transport details (HTTP/gRPC) automatically.
        Data is serialized to JSON string with data_content_type="application/json".
    """
    # Convert Pydantic model to dict if needed
    payload = data.model_dump(mode="json") if isinstance(data, BaseModel) else data
    event_type = payload.get("event_type", "unknown")

    try:
        with DaprClient() as client:
            client.publish_event(
                pubsub_name=pubsub_name,
                topic_name=topic,
                data=json.dumps(payload),
                data_content_type="application/json",
            )

        logger.info(
            "Published event to DAPR pub/sub: pubsub=%s topic=%s event_type=%s",
            pubsub_name,
            topic,
            event_type,
        )
        return True

    except (DaprInternalError, RpcError) as e:
        # DAPR sidecar not available or RPC error
        logger.warning(
            "DAPR sidecar unavailable, event not published: pubsub=%s topic=%s event_type=%s error=%s",
            pubsub_name,
            topic,
            event_type,
            str(e),
        )
        return False

    except Exception as e:
        logger.error(
            "Unexpected error publishing event to DAPR pub/sub: pubsub=%s topic=%s event_type=%s error=%s",
            pubsub_name,
            topic,
            event_type,
            str(e),
        )
        return False
