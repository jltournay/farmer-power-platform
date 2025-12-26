"""Domain models for Collection Model service.

These Pydantic models define the structure of domain events published
via DAPR pub/sub to downstream services.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentStoredEvent(BaseModel):
    """Event published when a raw document is stored successfully.

    Published to topic: collection.document.stored
    """

    document_id: str = Field(description="Unique identifier for the stored document")
    source_type: str = Field(description="Type of source: 'qc_analyzer_result', 'qc_analyzer_exception', etc.")
    farmer_id: str | None = Field(default=None, description="Farmer ID if identifiable from document")
    blob_path: str = Field(description="Azure Blob Storage path")
    blob_etag: str = Field(description="Blob ETag for idempotency")
    content_hash: str = Field(description="SHA-256 hash of document content")
    content_type: str = Field(description="MIME type of the document")
    content_length: int = Field(description="Size in bytes")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the document was stored")
    event_type: str = Field(default="document.stored", description="Event type identifier")


class PoorQualityDetectedEvent(BaseModel):
    """Event published when quality drops below threshold.

    Published to topic: collection.poor_quality_detected
    Triggers alerts to field officers for farmer intervention.
    """

    event_id: str = Field(description="Unique event identifier")
    farmer_id: str = Field(description="Farmer with quality issues")
    primary_percentage: float = Field(description="Current primary grade percentage (0-100)")
    threshold: float = Field(default=70.0, description="Threshold that was breached")
    leaf_type_distribution: dict[str, float] = Field(
        default_factory=dict,
        description="Distribution of leaf types causing issues",
    )
    priority: str = Field(
        default="standard",
        description="Alert priority: 'standard' or 'critical'",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When quality issue detected")
    event_type: str = Field(default="poor_quality_detected", description="Event type identifier")


class WeatherUpdatedEvent(BaseModel):
    """Event published when weather data is pulled for a region.

    Published to topic: collection.weather.updated
    """

    region_id: str = Field(description="Region identifier (county + altitude band)")
    weather_date: str = Field(description="Date of weather data (YYYY-MM-DD)")
    temperature_high: float | None = Field(default=None, description="High temperature in Celsius")
    temperature_low: float | None = Field(default=None, description="Low temperature in Celsius")
    rainfall_mm: float | None = Field(default=None, description="Rainfall in mm")
    humidity_percent: float | None = Field(default=None, description="Average humidity percentage")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When weather was updated")
    event_type: str = Field(default="weather.updated", description="Event type identifier")


class MarketPricesUpdatedEvent(BaseModel):
    """Event published when market prices are updated.

    Published to topic: collection.market_prices.updated
    """

    commodity: str = Field(description="Commodity type (e.g., 'tea', 'coffee')")
    region: str = Field(description="Market region")
    price_per_kg: float = Field(description="Current price per kilogram")
    currency: str = Field(default="KES", description="Currency code")
    price_date: str = Field(description="Date of price data (YYYY-MM-DD)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When price was updated")
    event_type: str = Field(default="market_prices.updated", description="Event type identifier")


__all__ = [
    "DocumentStoredEvent",
    "MarketPricesUpdatedEvent",
    "PoorQualityDetectedEvent",
    "WeatherUpdatedEvent",
]
