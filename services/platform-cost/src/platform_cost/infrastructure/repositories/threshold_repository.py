"""Threshold Repository for budget threshold configuration persistence.

Story 13.3: Cost Repository and Budget Monitor

This module provides storage for budget threshold configuration (daily/monthly limits).
Thresholds are persisted in MongoDB so they survive service restarts and can be
updated at runtime via gRPC (Story 13.4).

The repository stores a single document with the current threshold configuration.
Updates use upsert to ensure the configuration always exists.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# Collection name for threshold configuration
COLLECTION_NAME = "budget_thresholds"

# Document ID for the singleton threshold config
THRESHOLD_CONFIG_ID = "budget_threshold_config"


class ThresholdConfig(BaseModel):
    """Budget threshold configuration.

    Stores daily and monthly cost thresholds used by BudgetMonitor
    for alerting when costs exceed configured limits.

    Attributes:
        daily_threshold_usd: Daily cost limit in USD. 0 = disabled.
        monthly_threshold_usd: Monthly cost limit in USD. 0 = disabled.
        updated_at: When the configuration was last updated.
        updated_by: Who updated the configuration (service or user).
    """

    daily_threshold_usd: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Daily cost threshold in USD. 0 = disabled.",
    )
    monthly_threshold_usd: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Monthly cost threshold in USD. 0 = disabled.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the configuration was last updated.",
    )
    updated_by: str = Field(
        default="system",
        description="Who updated the configuration (service or user).",
    )


class ThresholdRepository:
    """Repository for budget threshold configuration.

    Stores and retrieves the budget threshold configuration from MongoDB.
    Uses a singleton document pattern - there's only one threshold config.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the repository.

        Args:
            db: MongoDB database instance.
        """
        self._db = db
        self._collection = db[COLLECTION_NAME]

    async def get_thresholds(self) -> ThresholdConfig | None:
        """Get the current threshold configuration.

        Returns:
            ThresholdConfig if exists, None if no configuration is stored.
        """
        doc = await self._collection.find_one({"_id": THRESHOLD_CONFIG_ID})
        if doc is None:
            logger.debug("No threshold configuration found")
            return None

        return ThresholdConfig(
            daily_threshold_usd=Decimal(str(doc.get("daily_threshold_usd", "0"))),
            monthly_threshold_usd=Decimal(str(doc.get("monthly_threshold_usd", "0"))),
            updated_at=doc.get("updated_at", datetime.now(UTC)),
            updated_by=doc.get("updated_by", "system"),
        )

    async def set_thresholds(
        self,
        daily_threshold_usd: Decimal | None = None,
        monthly_threshold_usd: Decimal | None = None,
        updated_by: str = "system",
    ) -> ThresholdConfig:
        """Set threshold configuration.

        Supports partial updates - only specified thresholds are updated.
        Uses upsert to create the configuration if it doesn't exist.

        Args:
            daily_threshold_usd: New daily threshold (None = keep current).
            monthly_threshold_usd: New monthly threshold (None = keep current).
            updated_by: Who is updating the configuration.

        Returns:
            The updated ThresholdConfig.
        """
        now = datetime.now(UTC)

        # Get current config for partial update
        current = await self.get_thresholds()
        if current is None:
            current = ThresholdConfig()

        # Apply updates
        if daily_threshold_usd is not None:
            current.daily_threshold_usd = daily_threshold_usd
        if monthly_threshold_usd is not None:
            current.monthly_threshold_usd = monthly_threshold_usd

        current.updated_at = now
        current.updated_by = updated_by

        # Build update document
        update_doc: dict[str, Any] = {
            "$set": {
                "daily_threshold_usd": str(current.daily_threshold_usd),
                "monthly_threshold_usd": str(current.monthly_threshold_usd),
                "updated_at": current.updated_at,
                "updated_by": current.updated_by,
            }
        }

        # Upsert the configuration
        await self._collection.update_one(
            {"_id": THRESHOLD_CONFIG_ID},
            update_doc,
            upsert=True,
        )

        logger.info(
            "Threshold configuration updated",
            daily_threshold_usd=str(current.daily_threshold_usd),
            monthly_threshold_usd=str(current.monthly_threshold_usd),
            updated_by=updated_by,
        )

        return current
