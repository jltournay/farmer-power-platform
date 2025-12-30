"""DAPR Pub/Sub client for config-driven event emission.

This module provides the DaprEventPublisher class for publishing domain events
via DAPR Pub/Sub. Event topics and payload fields are read from source config -
NO hardcoded topics.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
import structlog
from collection_model.config import settings
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class DocumentProcessedEvent(BaseModel):
    """Generic domain event for document processing.

    Payload fields are dynamically populated from source config.

    Attributes:
        event_id: Unique identifier for this event.
        event_type: Type of the event (e.g., "document.processed").
        source_id: ID of the source configuration.
        timestamp: When the event occurred.
        payload: Dynamic payload fields from config.
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str = "document.processed"
    source_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)


class DaprEventPublisher:
    """DAPR Pub/Sub client for domain event emission.

    All event topics are read from source config - NO hardcoded topics.
    Uses DAPR HTTP API for Pub/Sub operations.
    """

    def __init__(
        self,
        dapr_http_port: int | None = None,
        pubsub_name: str | None = None,
    ) -> None:
        """Initialize the event publisher.

        Args:
            dapr_http_port: DAPR HTTP port (defaults to settings.dapr_http_port).
            pubsub_name: DAPR Pub/Sub component name (defaults to settings.dapr_pubsub_name).
        """
        self._dapr_port = dapr_http_port or settings.dapr_http_port
        self._pubsub_name = pubsub_name or settings.dapr_pubsub_name
        self._base_url = f"http://localhost:{self._dapr_port}"

    async def check_health(self) -> bool:
        """Check if DAPR sidecar is available.

        Returns:
            True if DAPR is reachable, False otherwise.
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

    async def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        source_id: str = "unknown",
    ) -> bool:
        """Publish an event to a DAPR Pub/Sub topic.

        The topic is read from source config (events.on_success.topic or
        events.on_failure.topic) - NOT hardcoded.

        Args:
            topic: The topic to publish to (from source config).
            payload: The event payload (fields from config).
            source_id: ID of the source for logging.

        Returns:
            True if published successfully, False otherwise.
        """
        url = f"{self._base_url}/v1.0/publish/{self._pubsub_name}/{topic}"

        event = DocumentProcessedEvent(
            source_id=source_id,
            payload=payload,
        )

        logger.debug(
            "Publishing event to DAPR",
            topic=topic,
            source_id=source_id,
            event_id=event.event_id,
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=event.model_dump(mode="json"),
                    headers={"Content-Type": "application/json"},
                    timeout=10.0,
                )
                response.raise_for_status()

            logger.info(
                "Event published successfully",
                topic=topic,
                source_id=source_id,
                event_id=event.event_id,
            )
            return True

        except httpx.HTTPStatusError as e:
            logger.error(
                "DAPR publish returned error status",
                topic=topic,
                source_id=source_id,
                status_code=e.response.status_code,
            )
            return False

        except Exception as e:
            logger.exception(
                "Failed to publish event to DAPR",
                topic=topic,
                source_id=source_id,
                error=str(e),
            )
            return False

    async def publish_success(
        self,
        source_config: dict[str, Any],
        document: Any,
    ) -> bool:
        """Publish a success event using config-driven topic and payload.

        Reads topic from source_config.events.on_success.topic and
        payload fields from source_config.events.on_success.payload_fields.

        Args:
            source_config: The source configuration with events section.
            document: The document to extract payload fields from.

        Returns:
            True if published successfully, False if no event configured.
        """
        events_config = source_config.get("events", {})
        on_success = events_config.get("on_success")
        if not on_success:
            logger.debug(
                "No on_success event configured",
                source_id=source_config.get("source_id"),
            )
            return False

        topic = on_success.get("topic")
        payload_fields = on_success.get("payload_fields", [])

        if not topic:
            logger.warning(
                "on_success event has no topic",
                source_id=source_config.get("source_id"),
            )
            return False

        # Build payload from document
        payload = self._extract_payload_fields(document, payload_fields)

        return await self.publish(
            topic=topic,
            payload=payload,
            source_id=source_config.get("source_id", "unknown"),
        )

    async def publish_failure(
        self,
        source_config: dict[str, Any],
        error_type: str,
        error_message: str,
        document_id: str | None = None,
    ) -> bool:
        """Publish a failure event using config-driven topic.

        Reads topic from source_config.events.on_failure.topic.

        Args:
            source_config: The source configuration with events section.
            error_type: The type of error.
            error_message: Error description.
            document_id: Optional document ID if available.

        Returns:
            True if published successfully, False if no event configured.
        """
        events_config = source_config.get("events", {})
        on_failure = events_config.get("on_failure")
        if not on_failure:
            logger.debug(
                "No on_failure event configured",
                source_id=source_config.get("source_id"),
            )
            return False

        topic = on_failure.get("topic")
        if not topic:
            return False

        payload = {
            "error_type": error_type,
            "error_message": error_message,
            "source_id": source_config.get("source_id"),
        }
        if document_id:
            payload["document_id"] = document_id

        return await self.publish(
            topic=topic,
            payload=payload,
            source_id=source_config.get("source_id", "unknown"),
        )

    @staticmethod
    def _extract_payload_fields(
        document: Any,
        field_names: list[str],
    ) -> dict[str, Any]:
        """Extract specified fields from a document for event payload.

        Args:
            document: The document (Pydantic model or dict) to extract from.
            field_names: List of field names to include.

        Returns:
            Dict of field names to values.
        """
        payload = {}

        # Convert to dict if Pydantic model
        if hasattr(document, "model_dump"):
            doc_dict = document.model_dump()
        elif isinstance(document, dict):
            doc_dict = document
        else:
            return payload

        for field_name in field_names:
            # Handle nested fields with dot notation
            if "." in field_name:
                parts = field_name.split(".")
                value = doc_dict
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = None
                        break
                if value is not None:
                    payload[field_name.replace(".", "_")] = value
            elif field_name in doc_dict:
                payload[field_name] = doc_dict[field_name]
            # Also check linkage_fields
            elif "linkage_fields" in doc_dict and field_name in doc_dict["linkage_fields"]:
                payload[field_name] = doc_dict["linkage_fields"][field_name]

        return payload
