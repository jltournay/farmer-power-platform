"""Farmer-related domain events.

Events are published via Dapr pub/sub when significant farmer lifecycle
events occur. Downstream services can subscribe to these events.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class FarmerRegisteredEvent(BaseModel):
    """Event published when a new farmer is successfully registered.

    This event is published to the "farmer-events" topic after a farmer
    is created in the database. Downstream services (e.g., notification
    service, analytics) can subscribe to this event.

    Topic: farmer-events
    Event Type: plantation.farmer.registered
    """

    event_type: str = Field(
        default="plantation.farmer.registered",
        description="Event type identifier",
    )
    farmer_id: str = Field(description="Unique farmer ID (WM-XXXX format)")
    phone: str = Field(description="Farmer's phone number")
    collection_point_id: str = Field(description="Collection point where farmer registered")
    factory_id: str = Field(description="Factory ID (derived from collection point's parent factory)")
    region_id: str = Field(description="Assigned region based on GPS + altitude")
    farm_scale: str = Field(description="Farm scale classification (smallholder/medium/estate)")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Event timestamp",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_type": "plantation.farmer.registered",
                "farmer_id": "WM-0001",
                "phone": "+254712345678",
                "collection_point_id": "nyeri-highland-cp-001",
                "factory_id": "KEN-FAC-001",
                "region_id": "nyeri-highland",
                "farm_scale": "medium",
                "timestamp": "2025-12-23T10:30:00Z",
            }
        }
    }


