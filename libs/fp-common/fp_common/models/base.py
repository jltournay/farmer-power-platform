"""Base models and utilities for Farmer Power Platform.

This module provides common base classes and utilities used across
all domain models in the platform.
"""

from pydantic import BaseModel, ConfigDict


class FPBaseModel(BaseModel):
    """Base model for all Farmer Power Platform domain entities.

    Provides common configuration and utilities used across all models.
    """

    model_config = ConfigDict(
        # Allow population by field name or alias
        populate_by_name=True,
        # Use enum values in serialization
        use_enum_values=False,
    )
