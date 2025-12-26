"""Dapr pub/sub client for event publishing."""

from typing import Any

import httpx
import structlog
from collection_model.config import settings
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


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
        self._pubsub_name = settings.dapr_pubsub_name

    async def check_health(self) -> bool:
        """Check if Dapr sidecar is available.

        Returns:
            True if Dapr is reachable, False otherwise.

        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/v1.0/healthz",
                    timeout=2.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def publish_event(
        self,
        topic: str,
        data: BaseModel | dict[str, Any],
        metadata: dict[str, str] | None = None,
    ) -> bool:
        """Publish an event to Dapr pub/sub.

        Args:
            topic: Topic name to publish to.
            data: Event data as Pydantic model or dict.
            metadata: Optional metadata for the message.

        Returns:
            True if event was published successfully, False otherwise.

        """
        url = f"{self._base_url}/v1.0/publish/{self._pubsub_name}/{topic}"

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
                "Published event to Dapr pub/sub",
                pubsub=self._pubsub_name,
                topic=topic,
                event_type=payload.get("event_type", "unknown"),
            )
            return True

        except httpx.ConnectError:
            # Dapr sidecar not available - log and continue
            logger.warning(
                "Dapr sidecar not available, event not published",
                pubsub=self._pubsub_name,
                topic=topic,
                event_type=payload.get("event_type", "unknown"),
            )
            return False

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to publish event to Dapr pub/sub",
                pubsub=self._pubsub_name,
                topic=topic,
                status_code=e.response.status_code,
                error=str(e),
            )
            return False

        except Exception as e:
            logger.error(
                "Unexpected error publishing event to Dapr pub/sub",
                pubsub=self._pubsub_name,
                topic=topic,
                error=str(e),
            )
            return False

    async def publish_document_stored(self, event: BaseModel | dict[str, Any]) -> bool:
        """Publish a document.stored event.

        Published when a raw document is stored successfully after blob ingestion.

        Args:
            event: The document stored event data.

        Returns:
            True if published successfully, False otherwise.

        """
        return await self.publish_event(settings.dapr_document_stored_topic, event)

    async def publish_poor_quality_detected(self, event: BaseModel | dict[str, Any]) -> bool:
        """Publish a poor_quality_detected event.

        Published when quality drops below 70% threshold.

        Args:
            event: The poor quality event data.

        Returns:
            True if published successfully, False otherwise.

        """
        return await self.publish_event(settings.dapr_poor_quality_topic, event)

    async def publish_weather_updated(self, event: BaseModel | dict[str, Any]) -> bool:
        """Publish a weather.updated event.

        Published when weather data is pulled for a region.

        Args:
            event: The weather updated event data.

        Returns:
            True if published successfully, False otherwise.

        """
        return await self.publish_event(settings.dapr_weather_updated_topic, event)

    async def publish_market_prices_updated(self, event: BaseModel | dict[str, Any]) -> bool:
        """Publish a market_prices.updated event.

        Published when market prices are updated.

        Args:
            event: The market prices event data.

        Returns:
            True if published successfully, False otherwise.

        """
        return await self.publish_event(settings.dapr_market_prices_topic, event)


# Global pub/sub client instance
_pubsub_client: DaprPubSubClient | None = None


def get_pubsub_client() -> DaprPubSubClient:
    """Get or create the pub/sub client singleton.

    Returns:
        DaprPubSubClient: The pub/sub client instance.

    """
    global _pubsub_client

    if _pubsub_client is None:
        _pubsub_client = DaprPubSubClient()

    return _pubsub_client


async def check_pubsub_health() -> bool:
    """Check if Dapr pub/sub is available.

    Returns:
        True if Dapr is reachable, False otherwise.

    """
    client = get_pubsub_client()
    return await client.check_health()
