"""Flush period model for MCP servers.

This model provides a typed response for flush period queries,
replacing the dataclass-based FlushResult with a proper Pydantic model
for MCP consumption and validation at service boundaries.
"""

from pydantic import BaseModel, Field

from fp_common.models.value_objects import FlushPeriod


class Flush(BaseModel):
    """Current or upcoming flush period information.

    Returned by get_current_flush() MCP tool. Provides information
    about the current tea growing season (flush period) for a region.

    Flush periods are:
    - first_flush: Early spring harvest (highest quality)
    - monsoon_flush: Monsoon season harvest (high volume)
    - autumn_flush: Fall harvest (balanced quality)
    - dormant: Winter dormancy period (minimal growth)

    Attributes:
        name: Name of the flush period (e.g., 'first_flush', 'monsoon_flush').
        period: The FlushPeriod definition with start/end dates.
        days_remaining: Days remaining until the flush period ends.
        characteristics: Description of flush characteristics.
    """

    name: str = Field(description="Name of the flush period (first_flush, monsoon_flush, autumn_flush, dormant)")
    period: FlushPeriod = Field(description="The flush period definition with start/end dates")
    days_remaining: int = Field(ge=0, description="Days remaining until the flush period ends")
    characteristics: str = Field(
        default="",
        description="Description of flush characteristics (copied from period for convenience)",
    )

    @classmethod
    def from_period(cls, name: str, period: FlushPeriod, days_remaining: int) -> "Flush":
        """Create a Flush from a FlushPeriod.

        Args:
            name: The flush period name.
            period: The FlushPeriod definition.
            days_remaining: Days until the period ends.

        Returns:
            A new Flush instance.
        """
        return cls(
            name=name,
            period=period,
            days_remaining=days_remaining,
            characteristics=period.characteristics,
        )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "first_flush",
                "period": {
                    "start": "03-15",
                    "end": "05-15",
                    "characteristics": "Highest quality, delicate flavor",
                },
                "days_remaining": 45,
                "characteristics": "Highest quality, delicate flavor",
            },
        },
    }
