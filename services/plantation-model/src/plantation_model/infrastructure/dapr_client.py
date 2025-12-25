"""Dapr pub/sub client for event publishing."""

import logging
from typing import Any

import httpx
from plantation_model.config import settings
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DaprPubSubClient:
    """Client for publishing events to Dapr pub/sub.

    Dapr provides a pub/sub abstraction that works with various message brokers
    (Redis, RabbitMQ, Kafka, etc.). Events are published via Dapr's HTTP API.

    The Dapr sidecar must be running alongside the service for this to work.
    In development/testing without Dapr, events will be logged but not sent.
    """

    def __init__(
        self,
        dapr_host: str | None = None,
        dapr_http_port: int | None = None,
    ) -> None:
        """Initialize the Dapr pub/sub client.

        Args:
            dapr_host: Dapr sidecar host (defaults to settings.dapr_host).
            dapr_http_port: Dapr HTTP port (defaults to settings.dapr_http_port).
        """
        self._dapr_host = dapr_host or settings.dapr_host
        self._dapr_http_port = dapr_http_port or settings.dapr_http_port
        self._base_url = f"http://{self._dapr_host}:{self._dapr_http_port}"

    async def publish_event(
        self,
        pubsub_name: str,
        topic: str,
        data: BaseModel | dict[str, Any],
        metadata: dict[str, str] | None = None,
    ) -> bool:
        """Publish an event to Dapr pub/sub.

        Args:
            pubsub_name: Name of the Dapr pub/sub component (e.g., "pubsub").
            topic: Topic name to publish to (e.g., "farmer-events").
            data: Event data as Pydantic model or dict.
            metadata: Optional metadata for the message.

        Returns:
            True if event was published successfully, False otherwise.
        """
        url = f"{self._base_url}/v1.0/publish/{pubsub_name}/{topic}"

        # Convert Pydantic model to dict if needed
        payload = data.model_dump(mode="json") if isinstance(data, BaseModel) else data

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        **(metadata or {}),
                    },
                    timeout=10.0,
                )
                response.raise_for_status()

            logger.info(
                "Published event to Dapr pub/sub: pubsub=%s topic=%s event_type=%s",
                pubsub_name,
                topic,
                payload.get("event_type", "unknown"),
            )
            return True

        except httpx.ConnectError:
            # Dapr sidecar not available - log and continue
            # This allows the service to work without Dapr in development
            logger.warning(
                "Dapr sidecar not available, event not published: pubsub=%s topic=%s event_type=%s",
                pubsub_name,
                topic,
                payload.get("event_type", "unknown"),
            )
            return False

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to publish event to Dapr pub/sub: pubsub=%s topic=%s status_code=%s error=%s",
                pubsub_name,
                topic,
                e.response.status_code,
                str(e),
            )
            return False

        except Exception as e:
            logger.error(
                "Unexpected error publishing event to Dapr pub/sub: pubsub=%s topic=%s error=%s",
                pubsub_name,
                topic,
                str(e),
            )
            return False
