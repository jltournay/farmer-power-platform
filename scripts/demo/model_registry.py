"""Model Registry mapping file patterns to Pydantic models.

This module provides a registry that maps seed data filenames to their
corresponding Pydantic models, enabling automatic model selection during
validation.

Story 0.8.1: Pydantic Validation Infrastructure
AC #5: Models imported directly from service packages (no duplication)
AC #2: Unknown fields rejected - strict models inherit with extra="forbid"
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelRegistry:
    """Registry mapping file patterns to Pydantic models.

    This registry allows looking up the correct Pydantic model for
    validating a given seed data file.

    Example:
        registry = ModelRegistry()
        registry.register("farmers.json", StrictFarmer)
        model = registry.get_model("farmers.json")
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._registry: dict[str, type[BaseModel]] = {}

    def register(self, pattern: str, model: type[BaseModel]) -> None:
        """Register a model for a file pattern.

        Args:
            pattern: Filename pattern (e.g., "farmers.json").
            model: Pydantic model class to use for validation.
        """
        self._registry[pattern] = model

    def get_model(self, pattern: str) -> type[BaseModel] | None:
        """Get the model for a file pattern.

        Args:
            pattern: Filename pattern to look up.

        Returns:
            Pydantic model class, or None if not found.
        """
        return self._registry.get(pattern)

    def get_all_patterns(self) -> list[str]:
        """Get all registered file patterns."""
        return list(self._registry.keys())


# ============================================================================
# Strict Model Definitions
# These inherit from the actual service models but add extra="forbid"
# AC #2: Unknown fields rejected (not silently ignored)
# AC #5: Models imported directly from service packages (no duplication)
# ============================================================================


# Lazy-loaded strict model cache
_strict_models: dict[str, type[BaseModel]] = {}


def _get_strict_farmer() -> type[BaseModel]:
    """Get strict Farmer model (lazy loaded)."""
    if "Farmer" not in _strict_models:
        from fp_common.models.farmer import Farmer

        class StrictFarmer(Farmer):
            """Strict Farmer model that rejects extra fields."""

            model_config = ConfigDict(extra="forbid")

        _strict_models["Farmer"] = StrictFarmer
    return _strict_models["Farmer"]


def _get_strict_region() -> type[BaseModel]:
    """Get strict Region model (lazy loaded)."""
    if "Region" not in _strict_models:
        from fp_common.models.region import Region

        class StrictRegion(Region):
            """Strict Region model that rejects extra fields."""

            model_config = ConfigDict(extra="forbid")

        _strict_models["Region"] = StrictRegion
    return _strict_models["Region"]


def _get_strict_factory() -> type[BaseModel]:
    """Get strict Factory model (lazy loaded)."""
    if "Factory" not in _strict_models:
        from fp_common.models.factory import Factory

        class StrictFactory(Factory):
            """Strict Factory model that rejects extra fields."""

            model_config = ConfigDict(extra="forbid")

        _strict_models["Factory"] = StrictFactory
    return _strict_models["Factory"]


def _get_strict_collection_point() -> type[BaseModel]:
    """Get strict CollectionPoint model (lazy loaded)."""
    if "CollectionPoint" not in _strict_models:
        from fp_common.models.collection_point import CollectionPoint

        class StrictCollectionPoint(CollectionPoint):
            """Strict CollectionPoint model that rejects extra fields."""

            model_config = ConfigDict(extra="forbid")

        _strict_models["CollectionPoint"] = StrictCollectionPoint
    return _strict_models["CollectionPoint"]


def _get_strict_grading_model() -> type[BaseModel]:
    """Get strict GradingModel model (lazy loaded)."""
    if "GradingModel" not in _strict_models:
        from fp_common.models.grading_model import GradingModel

        class StrictGradingModel(GradingModel):
            """Strict GradingModel model that rejects extra fields."""

            model_config = ConfigDict(extra="forbid")

        _strict_models["GradingModel"] = StrictGradingModel
    return _strict_models["GradingModel"]


def _get_strict_farmer_performance() -> type[BaseModel]:
    """Get strict FarmerPerformance model (lazy loaded)."""
    if "FarmerPerformance" not in _strict_models:
        from fp_common.models.farmer_performance import FarmerPerformance

        class StrictFarmerPerformance(FarmerPerformance):
            """Strict FarmerPerformance model that rejects extra fields."""

            model_config = ConfigDict(extra="forbid")

        _strict_models["FarmerPerformance"] = StrictFarmerPerformance
    return _strict_models["FarmerPerformance"]


def _get_strict_source_config() -> type[BaseModel]:
    """Get strict SourceConfig model (lazy loaded)."""
    if "SourceConfig" not in _strict_models:
        from fp_common.models.source_config import SourceConfig

        class StrictSourceConfig(SourceConfig):
            """Strict SourceConfig model that rejects extra fields."""

            model_config = ConfigDict(extra="forbid")

        _strict_models["SourceConfig"] = StrictSourceConfig
    return _strict_models["SourceConfig"]


def _get_strict_prompt() -> type[BaseModel]:
    """Get strict Prompt model (lazy loaded)."""
    if "Prompt" not in _strict_models:
        from ai_model.domain.prompt import Prompt

        class StrictPrompt(Prompt):
            """Strict Prompt model that rejects extra fields."""

            model_config = ConfigDict(extra="forbid")

        _strict_models["Prompt"] = StrictPrompt
    return _strict_models["Prompt"]


def _get_strict_regional_weather() -> type[BaseModel]:
    """Get strict RegionalWeather model (lazy loaded)."""
    if "RegionalWeather" not in _strict_models:
        from fp_common.models.regional_weather import RegionalWeather

        class StrictRegionalWeather(RegionalWeather):
            """Strict RegionalWeather model that rejects extra fields."""

            model_config = ConfigDict(extra="forbid")

        _strict_models["RegionalWeather"] = StrictRegionalWeather
    return _strict_models["RegionalWeather"]


def _get_strict_document() -> type[BaseModel]:
    """Get strict Document model (lazy loaded)."""
    if "Document" not in _strict_models:
        from fp_common.models.document import Document

        class StrictDocument(Document):
            """Strict Document model that rejects extra fields."""

            model_config = ConfigDict(extra="forbid")

        _strict_models["Document"] = StrictDocument
    return _strict_models["Document"]


def _get_agent_config_model() -> type[BaseModel]:
    """Get AgentConfig model (lazy loaded).

    AgentConfig is a discriminated union. We use AgentConfigBase with strict
    config for basic field validation. The actual validation uses TypeAdapter
    for the discriminated union in the validation code.
    """
    if "AgentConfig" not in _strict_models:
        from ai_model.domain.agent_config import AgentConfigBase

        class StrictAgentConfigBase(AgentConfigBase):
            """Strict AgentConfigBase model that rejects extra fields."""

            model_config = ConfigDict(extra="forbid")

        _strict_models["AgentConfig"] = StrictAgentConfigBase
    return _strict_models["AgentConfig"]


def get_model_for_file(filename: str) -> type[BaseModel] | None:
    """Get the Pydantic model for a seed data file.

    This function maps filenames to their corresponding Pydantic models,
    importing models directly from service packages (AC #5).

    Args:
        filename: Name of the seed data file (e.g., "farmers.json").

    Returns:
        Pydantic model class with extra="forbid", or None if unknown file.
    """
    registry = get_seed_model_registry()
    return registry.get_model(filename)


# Singleton registry instance
_seed_registry: ModelRegistry | None = None


def get_seed_model_registry() -> ModelRegistry:
    """Get the pre-populated seed model registry.

    Returns a singleton registry with all seed data models registered.
    Models are imported from service packages (AC #5) and wrapped to
    enforce extra="forbid" (AC #2).

    Returns:
        ModelRegistry with all seed data models.
    """
    global _seed_registry

    if _seed_registry is None:
        _seed_registry = ModelRegistry()

        # Register all seed data models with their file patterns
        # AC #5: Models imported directly from service packages
        _seed_registry.register("farmers.json", _get_strict_farmer())
        _seed_registry.register("regions.json", _get_strict_region())
        _seed_registry.register("factories.json", _get_strict_factory())
        _seed_registry.register("collection_points.json", _get_strict_collection_point())
        _seed_registry.register("grading_models.json", _get_strict_grading_model())
        _seed_registry.register("farmer_performance.json", _get_strict_farmer_performance())
        _seed_registry.register("source_configs.json", _get_strict_source_config())
        _seed_registry.register("prompts.json", _get_strict_prompt())
        _seed_registry.register("agent_configs.json", _get_agent_config_model())
        _seed_registry.register("weather_observations.json", _get_strict_regional_weather())
        _seed_registry.register("documents.json", _get_strict_document())

    return _seed_registry


def reset_registry() -> None:
    """Reset the singleton registry (for testing)."""
    global _seed_registry
    _seed_registry = None
    _strict_models.clear()
