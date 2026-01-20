"""Polyfactory generators for the Farmer Power Platform.

This module provides Polyfactory-based generators for creating valid domain
model instances with Kenya-specific data. All factories integrate with the
FKRegistry from Story 0.8.1 for FK validation.

Story 0.8.3: Polyfactory Generator Framework

Usage:
    from tests.demo.generators import (
        FarmerFactory,
        RegionFactory,
        FactoryEntityFactory,
        CollectionPointFactory,
        RegionalWeatherFactory,
        FarmerPerformanceFactory,
        set_fk_registry,
    )
    from scripts.demo.fk_registry import FKRegistry

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

from .base import BaseModelFactory, FKRegistryMixin  # noqa: E402
from .kenya_providers import KenyaProvider  # noqa: E402
from .plantation import (  # noqa: E402
    CollectionPointFactory,
    FactoryEntityFactory,
    FarmerFactory,
    FarmerPerformanceFactory,
    RegionFactory,
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
    # Utility functions
    "set_fk_registry",
    "reset_fk_registry",
    "get_fk_registry",
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
