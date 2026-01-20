"""Base factory classes and FK registry integration for Polyfactory generators.

This module provides:
- FKRegistryMixin for sharing FK registry across factories
- BaseModelFactory as a base class for all domain model factories

Story 0.8.3: Polyfactory Generator Framework
AC #2: Factories accept FK values as parameters and default values reference FK registry
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar, TypeVar

from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel

# Add scripts/demo and libs/fp-common to path for imports
_project_root = Path(__file__).parent.parent.parent.parent
_demo_scripts_path = _project_root / "scripts" / "demo"
if str(_demo_scripts_path) not in sys.path:
    sys.path.insert(0, str(_demo_scripts_path))
_fp_common_path = _project_root / "libs" / "fp-common"  # fp_common is directly under fp-common/
if str(_fp_common_path) not in sys.path:
    sys.path.insert(0, str(_fp_common_path))

from fk_registry import FKRegistry  # noqa: E402

T = TypeVar("T", bound=BaseModel)


class FKRegistryMixin:
    """Mixin that provides FK registry access to factories.

    This mixin is shared across all factories to maintain a single FK registry
    instance. Generated entity IDs are registered in the FK registry to enable
    FK validation for dependent entities.

    Usage:
        class FarmerFactory(FKRegistryMixin, ModelFactory):
            __model__ = Farmer

            @classmethod
            def region_id(cls) -> str:
                return cls.get_random_fk("regions")
    """

    # Shared FK registry instance across all factories
    _fk_registry: ClassVar[FKRegistry | None] = None

    @classmethod
    def set_fk_registry(cls, registry: FKRegistry) -> None:
        """Set the shared FK registry for all factories.

        Args:
            registry: FKRegistry instance to use for ID lookups and registration.
        """
        # Always set on FKRegistryMixin to ensure all subclasses share the same registry
        FKRegistryMixin._fk_registry = registry

    @classmethod
    def get_fk_registry(cls) -> FKRegistry:
        """Get the shared FK registry, creating one if needed.

        Returns:
            The shared FKRegistry instance.
        """
        # Always access from FKRegistryMixin to ensure all subclasses share the same registry
        if FKRegistryMixin._fk_registry is None:
            FKRegistryMixin._fk_registry = FKRegistry()
        return FKRegistryMixin._fk_registry

    @classmethod
    def reset_fk_registry(cls) -> None:
        """Reset the FK registry (for testing)."""
        # Always reset on FKRegistryMixin to ensure all subclasses are affected
        FKRegistryMixin._fk_registry = None

    @classmethod
    def get_random_fk(cls, entity_type: str) -> str:
        """Get a random valid FK from the registry.

        Args:
            entity_type: Entity type to get FK from (e.g., "regions", "factories").

        Returns:
            A random valid ID from the registry.

        Raises:
            ValueError: If no IDs registered for entity_type.
        """
        import random

        valid_ids = cls.get_fk_registry().get_valid_ids(entity_type)
        if not valid_ids:
            raise ValueError(
                f"No {entity_type} registered in FK registry. "
                f"Generate {entity_type} first before generating dependent entities."
            )
        return random.choice(list(valid_ids))

    @classmethod
    def register_generated(cls, entity_type: str, ids: list[str]) -> None:
        """Register generated IDs in the FK registry.

        Args:
            entity_type: Entity type for the IDs (e.g., "regions", "farmers").
            ids: List of generated IDs to register.
        """
        cls.get_fk_registry().register(entity_type, ids)


class BaseModelFactory(FKRegistryMixin, ModelFactory[T]):
    """Base factory for all domain model factories.

    Provides:
    - FK registry integration via FKRegistryMixin
    - ID generation with prefixes
    - Auto-registration of generated IDs

    Subclasses should define:
    - __model__: The Pydantic model class
    - _id_prefix: Prefix for generated IDs (e.g., "WM-" for farmers)
    - _id_counter: Counter for sequential IDs (reset per batch)
    - _entity_type: Entity type name for FK registry (e.g., "farmers")
    """

    # Mark as abstract - subclasses must define __model__
    __is_base_factory__ = True

    # Class-level configuration (override in subclasses)
    _id_prefix: ClassVar[str] = "GEN-"
    _id_counter: ClassVar[int] = 0
    _entity_type: ClassVar[str] = "unknown"

    # Allow extra fields to be passed (useful for FK overrides)
    __allow_none_optionals__ = True

    @classmethod
    def _next_id(cls) -> str:
        """Generate the next sequential ID.

        Returns:
            ID string with prefix and zero-padded counter.
        """
        cls._id_counter += 1
        return f"{cls._id_prefix}{cls._id_counter:04d}"

    @classmethod
    def reset_counter(cls) -> None:
        """Reset the ID counter (for testing)."""
        cls._id_counter = 0

    @classmethod
    def build_batch_and_register(cls, size: int, **kwargs) -> list[T]:
        """Build a batch of instances and register their IDs in FK registry.

        Args:
            size: Number of instances to generate.
            **kwargs: Factory field overrides.

        Returns:
            List of generated Pydantic model instances.
        """
        instances = cls.batch(size, **kwargs)

        # Extract IDs and register them
        ids = []
        for instance in instances:
            # Try common ID field names
            if hasattr(instance, "id"):
                ids.append(instance.id)
            elif hasattr(instance, "region_id"):
                ids.append(instance.region_id)
            elif hasattr(instance, "farmer_id"):
                ids.append(instance.farmer_id)

        if ids and cls._entity_type != "unknown":
            cls.register_generated(cls._entity_type, ids)

        return instances
