"""Performance summary model for entity metrics aggregation.

This model provides a typed response for performance summary metrics,
replacing the dict[str, Any] anti-pattern with proper Pydantic validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PerformanceSummary(BaseModel):
    """Aggregated performance metrics for an entity.

    Returned by get_performance_summary(). Contains aggregated metrics
    for a farmer, factory, or region over a specified time period.

    Attributes:
        id: Unique identifier for this summary record.
        entity_type: Type of entity ("farmer", "factory", "region").
        entity_id: ID of the entity being summarized.
        period: Period type ("daily", "weekly", "monthly", "yearly").
        period_start: Start of the aggregation period.
        period_end: End of the aggregation period.
        total_green_leaf_kg: Total green leaf collected in kg.
        total_made_tea_kg: Total processed tea in kg.
        collection_count: Number of collections in the period.
        average_quality_score: Average quality score across collections.
        created_at: When this summary was created.
        updated_at: When this summary was last updated.
    """

    id: str = Field(description="Unique identifier for this summary record")
    entity_type: str = Field(description='Type of entity: "farmer", "factory", or "region"')
    entity_id: str = Field(description="ID of the entity being summarized")
    period: str = Field(description='Period type: "daily", "weekly", "monthly", "yearly"')
    period_start: datetime | None = Field(default=None, description="Start of the aggregation period")
    period_end: datetime | None = Field(default=None, description="End of the aggregation period")
    total_green_leaf_kg: float = Field(default=0.0, description="Total green leaf collected in kg")
    total_made_tea_kg: float = Field(default=0.0, description="Total processed tea in kg")
    collection_count: int = Field(default=0, description="Number of collections in the period")
    average_quality_score: float = Field(default=0.0, description="Average quality score across collections")
    created_at: datetime | None = Field(default=None, description="When this summary was created")
    updated_at: datetime | None = Field(default=None, description="When this summary was last updated")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "perf-001",
                "entity_type": "farmer",
                "entity_id": "WM-0001",
                "period": "monthly",
                "period_start": "2025-12-01T00:00:00Z",
                "period_end": "2025-12-31T23:59:59Z",
                "total_green_leaf_kg": 1500.0,
                "total_made_tea_kg": 300.0,
                "collection_count": 45,
                "average_quality_score": 82.5,
                "created_at": "2025-12-28T10:00:00Z",
                "updated_at": "2025-12-28T10:00:00Z",
            },
        },
    }
