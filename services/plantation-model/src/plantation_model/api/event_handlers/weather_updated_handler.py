"""DAPR subscription handler for Collection Model weather updated events.

This module handles `collection.weather.updated` events emitted by
the Collection Model when weather data is fetched via scheduled pull ingestion.

Event Flow:
1. Collection Model fetches weather from Open-Meteo API
2. Collection Model emits `collection.weather.updated` event
3. DAPR routes to this handler via Pub/Sub subscription
4. Handler parses weather observations
5. Handler upserts RegionalWeather records
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, Request, Response
from opentelemetry import trace
from plantation_model.domain.models.regional_weather import WeatherObservation
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from plantation_model.infrastructure.repositories.regional_weather_repository import (
        RegionalWeatherRepository,
    )

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])


class WeatherObservationData(BaseModel):
    """Weather observation data from Collection Model."""

    temp_min: float = Field(description="Minimum temperature in Celsius")
    temp_max: float = Field(description="Maximum temperature in Celsius")
    precipitation_mm: float = Field(ge=0, description="Total precipitation in mm")
    humidity_avg: float = Field(ge=0, le=100, description="Average humidity %")


class WeatherUpdatedEvent(BaseModel):
    """Event payload for collection.weather.updated.

    Matches the payload defined in Collection Model weather ingestion.
    """

    region_id: str = Field(description="Region ID (e.g., nyeri-highland)")
    date: str = Field(description="Observation date in YYYY-MM-DD format")
    observations: WeatherObservationData = Field(description="Weather observations")
    source: str = Field(default="open-meteo", description="Weather data source")
    collected_at: datetime | None = Field(default=None, description="When data was collected")


class CloudEventWrapper(BaseModel):
    """DAPR CloudEvents 1.0 wrapper.

    DAPR delivers Pub/Sub messages as CloudEvents.
    """

    id: str = Field(description="Event ID")
    source: str = Field(description="Event source")
    type: str = Field(description="Event type")
    specversion: str = Field(default="1.0", description="CloudEvents version")
    datacontenttype: str = Field(default="application/json", description="Content type")
    data: dict[str, Any] = Field(description="Event payload")
    time: datetime | None = Field(default=None, description="Event timestamp")
    traceparent: str | None = Field(default=None, description="W3C trace context")


def get_weather_subscriptions() -> list[dict[str, Any]]:
    """Return DAPR Pub/Sub subscriptions for weather events.

    Returns:
        List of subscription configurations.
    """
    return [
        {
            "pubsubname": "pubsub",
            "topic": "collection.weather.updated",
            "route": "/api/v1/events/weather-updated",
            "metadata": {
                "rawPayload": "true",  # Receive CloudEvents format
            },
        }
    ]


@router.post("/weather-updated")
async def handle_weather_updated(request: Request) -> Response:
    """Handle weather updated events from Collection Model.

    This endpoint is called by DAPR when a `collection.weather.updated`
    event is published. The handler:

    1. Parses the CloudEvent payload
    2. Validates weather observation data
    3. Upserts RegionalWeather record

    Args:
        request: FastAPI request with CloudEvent payload.

    Returns:
        Response with DAPR acknowledgment status:
        - 200 SUCCESS: Event processed successfully
        - 400 DROP: Invalid event, don't retry
        - 500 RETRY: Temporary failure, retry later
    """
    with tracer.start_as_current_span("handle_weather_updated") as span:
        try:
            body = await request.json()
        except Exception as e:
            logger.error("Failed to parse event body", error=str(e))
            span.set_attribute("error", "parse_failed")
            return Response(status_code=400, content='{"status": "DROP"}')

        # Parse CloudEvent wrapper
        try:
            cloud_event = CloudEventWrapper.model_validate(body)
            event_id = cloud_event.id
            trace_parent = cloud_event.traceparent

            span.set_attribute("event.id", event_id)
            span.set_attribute("event.type", cloud_event.type)
            if trace_parent:
                span.set_attribute("event.traceparent", trace_parent)

        except Exception as e:
            logger.error("Invalid CloudEvent format", error=str(e), body=body)
            span.set_attribute("error", "invalid_cloud_event")
            return Response(status_code=400, content='{"status": "DROP"}')

        # Parse event data
        try:
            # Event data may be nested under 'payload' or at root
            event_payload = cloud_event.data.get("payload", cloud_event.data)
            event_data = WeatherUpdatedEvent.model_validate(event_payload)

            span.set_attribute("event.region_id", event_data.region_id)
            span.set_attribute("event.date", event_data.date)
            span.set_attribute("event.source", event_data.source)

            logger.info(
                "Processing weather updated event",
                event_id=event_id,
                region_id=event_data.region_id,
                date=event_data.date,
                source=event_data.source,
            )

        except Exception as e:
            logger.error(
                "Invalid event payload",
                error=str(e),
                data=cloud_event.data,
            )
            span.set_attribute("error", "invalid_payload")
            return Response(status_code=400, content='{"status": "DROP"}')

        # Parse observation date
        try:
            observation_date = date.fromisoformat(event_data.date)
        except ValueError as e:
            logger.error(
                "Invalid date format",
                error=str(e),
                date=event_data.date,
            )
            span.set_attribute("error", "invalid_date")
            return Response(status_code=400, content='{"status": "DROP"}')

        # Get repository from app state
        regional_weather_repo: RegionalWeatherRepository | None = getattr(
            request.app.state, "regional_weather_repo", None
        )

        if regional_weather_repo is None:
            logger.warning(
                "Regional weather repository not initialized - event will be skipped",
                event_id=event_id,
                region_id=event_data.region_id,
            )
            # Return success to avoid infinite retries in development
            return Response(
                status_code=200,
                content='{"status": "SUCCESS", "message": "Repository not initialized"}',
            )

        # Upsert the weather observation
        try:
            observation = WeatherObservation(
                temp_min=event_data.observations.temp_min,
                temp_max=event_data.observations.temp_max,
                precipitation_mm=event_data.observations.precipitation_mm,
                humidity_avg=event_data.observations.humidity_avg,
            )

            await regional_weather_repo.upsert_observation(
                region_id=event_data.region_id,
                observation_date=observation_date,
                observation=observation,
                source=event_data.source,
            )

            logger.info(
                "Weather observation upserted successfully",
                event_id=event_id,
                region_id=event_data.region_id,
                date=event_data.date,
            )
            span.set_attribute("processing.success", True)

            return Response(status_code=200, content='{"status": "SUCCESS"}')

        except Exception as e:
            logger.exception(
                "Failed to upsert weather observation",
                event_id=event_id,
                region_id=event_data.region_id,
                error=str(e),
            )
            span.set_attribute("error", str(e))
            span.record_exception(e)

            # Return RETRY to let DAPR retry later
            return Response(status_code=500, content='{"status": "RETRY"}')
