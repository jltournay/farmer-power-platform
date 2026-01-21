"""Polyfactory generators for the Farmer Power Platform.

This module provides Polyfactory-based generators for creating valid domain
model instances with Kenya-specific data. All factories integrate with the
FKRegistry from Story 0.8.1 for FK validation.

Story 0.8.3: Polyfactory Generator Framework
Story 0.8.4: Profile-Based Data Generation (scenarios, quality docs, profiles)

Usage:
    from tests.demo.generators import (
        FarmerFactory,
        RegionFactory,
        FactoryEntityFactory,
        CollectionPointFactory,
        RegionalWeatherFactory,
        FarmerPerformanceFactory,
        DocumentFactory,
        set_fk_registry,
        set_global_seed,
    )
    from scripts.demo.fk_registry import FKRegistry

    # Set global seed for deterministic generation
    set_global_seed(12345)

    # Initialize FK registry
    registry = FKRegistry()
    set_fk_registry(registry)

    # Generate entities in dependency order
    regions = RegionFactory.build_batch_and_register(5)
    factories = FactoryEntityFactory.build_batch_and_register(3)
    collection_points = CollectionPointFactory.build_batch_and_register(10)
    farmers = FarmerFactory.build_batch_and_register(100)

    # All entities are JSON-serializable
    farmer_dicts = [f.model_dump(mode="json") for f in farmers]
"""

import sys
from pathlib import Path

# Add required paths before importing modules that need them
# Path: tests/demo/generators/__init__.py -> parent.parent.parent = tests -> parent.parent.parent.parent = project root
_project_root = Path(__file__).parent.parent.parent.parent
_fp_common_path = _project_root / "libs" / "fp-common"  # fp_common is directly under fp-common/
if str(_fp_common_path) not in sys.path:
    sys.path.insert(0, str(_fp_common_path))

_scripts_demo_path = _project_root / "scripts" / "demo"
if str(_scripts_demo_path) not in sys.path:
    sys.path.insert(0, str(_scripts_demo_path))

from .base import BaseModelFactory, FKRegistryMixin, set_factory_seed  # noqa: E402
from .kenya_providers import KenyaProvider  # noqa: E402
from .plantation import (  # noqa: E402
    CollectionPointFactory,
    FactoryEntityFactory,
    FarmerFactory,
    FarmerPerformanceFactory,
    RegionFactory,
)
from .profile_loader import Profile, ProfileLoader, parse_range  # noqa: E402
from .quality import DocumentFactory  # noqa: E402
from .random_utils import (  # noqa: E402
    SeededRandom,
    get_global_seed,
    get_seeded_random,
    seeded_choice,
    seeded_choices,
    seeded_randint,
    seeded_sample,
    seeded_uniform,
    set_global_seed,
)
from .scenarios import (  # noqa: E402
    SCENARIOS,
    FarmerScenario,
    QualityTier,
    ScenarioAssigner,
    get_scenario,
    list_scenarios,
)
from .weather import RegionalWeatherFactory  # noqa: E402

__all__ = [  # noqa: RUF022
    # Base classes
    "BaseModelFactory",
    "FKRegistryMixin",
    # Data providers
    "KenyaProvider",
    # Plantation factories
    "RegionFactory",
    "FactoryEntityFactory",
    "CollectionPointFactory",
    "FarmerFactory",
    "FarmerPerformanceFactory",
    # Weather factories
    "RegionalWeatherFactory",
    # Document factory (Story 0.8.4)
    "DocumentFactory",
    # Scenarios (Story 0.8.4)
    "SCENARIOS",
    "FarmerScenario",
    "QualityTier",
    "ScenarioAssigner",
    "get_scenario",
    "list_scenarios",
    # Profile loading (Story 0.8.4)
    "Profile",
    "ProfileLoader",
    "parse_range",
    # Seeded random (Story 0.8.4)
    "SeededRandom",
    "set_global_seed",
    "get_global_seed",
    "get_seeded_random",
    "seeded_randint",
    "seeded_uniform",
    "seeded_choice",
    "seeded_choices",
    "seeded_sample",
    # FK registry utility functions
    "set_fk_registry",
    "reset_fk_registry",
    "get_fk_registry",
    # Factory seed (Story 0.8.4)
    "set_factory_seed",
]


def set_fk_registry(registry) -> None:
    """Set the FK registry for all factories.

    Args:
        registry: FKRegistry instance from scripts.demo.fk_registry.
    """
    FKRegistryMixin.set_fk_registry(registry)


def reset_fk_registry() -> None:
    """Reset the FK registry (for testing)."""
    FKRegistryMixin.reset_fk_registry()


def get_fk_registry():
    """Get the current FK registry."""
    return FKRegistryMixin.get_fk_registry()
