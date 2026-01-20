"""Foreign Key Registry for referential integrity validation.

This module provides a registry that tracks valid IDs for each entity type,
enabling FK validation to catch broken references before database writes.

Story 0.8.1: Pydantic Validation Infrastructure
AC #4: FK validation checks each foreign key against FK registry
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FKValidationError:
    """Detailed FK validation error with context.

    Attributes:
        source_entity: Entity type containing the FK (e.g., "farmers").
        field_name: Name of the FK field (e.g., "region_id").
        invalid_value: The invalid FK value that failed lookup.
        target_entity: Entity type the FK should reference (e.g., "regions").
        record_index: 0-based index of the record in the array.
    """

    source_entity: str
    field_name: str
    invalid_value: str | None
    target_entity: str
    record_index: int

    def __str__(self) -> str:
        """Return formatted error string with all context."""
        if self.invalid_value is None:
            return (
                f"{self.source_entity}[{self.record_index}].{self.field_name}: "
                f"Required FK is missing (should reference {self.target_entity})"
            )
        return (
            f"{self.source_entity}[{self.record_index}].{self.field_name}: "
            f"Invalid FK '{self.invalid_value}' - not found in {self.target_entity}"
        )


class FKRegistry:
    """Registry of valid IDs for each entity type.

    This registry is populated in dependency order (regions before farmers,
    factories before collection_points, etc.) and then used to validate
    FK fields in dependent entities.

    Example usage:
        registry = FKRegistry()
        registry.register("regions", ["reg-001", "reg-002"])
        registry.register("factories", ["fac-001"])

        # Later, when validating farmers:
        is_valid = registry.validate_fk("regions", farmer["region_id"])
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._registry: dict[str, set[str]] = {}

    def register(self, entity_type: str, ids: list[str]) -> None:
        """Register valid IDs for an entity type.

        If the entity type already has registered IDs, the new IDs are added
        to the existing set (extends, not replaces).

        Args:
            entity_type: Name of the entity (e.g., "regions", "farmers").
            ids: List of valid IDs for this entity type.
        """
        if entity_type not in self._registry:
            self._registry[entity_type] = set()
        self._registry[entity_type].update(ids)

    def get_valid_ids(self, entity_type: str) -> set[str]:
        """Get all valid IDs for an entity type.

        Args:
            entity_type: Name of the entity.

        Returns:
            Set of valid IDs, or empty set if entity not registered.
        """
        return self._registry.get(entity_type, set())

    def validate_fk(self, entity_type: str, fk_value: str) -> bool:
        """Check if a FK value is valid for the given entity type.

        Args:
            entity_type: Target entity type the FK should reference.
            fk_value: The FK value to validate.

        Returns:
            True if fk_value exists in the registered IDs for entity_type.
        """
        return fk_value in self._registry.get(entity_type, set())


def validate_foreign_keys(
    records: list[dict[str, Any]],
    source_entity: str,
    fk_mappings: dict[str, str],
    registry: FKRegistry,
    optional_fields: set[str] | None = None,
    list_fields: set[str] | None = None,
) -> list[FKValidationError]:
    """Validate FK fields in a list of records against the registry.

    Args:
        records: List of record dictionaries to validate.
        source_entity: Name of the source entity (for error context).
        fk_mappings: Dict mapping FK field names to target entity types.
            Example: {"region_id": "regions", "factory_id": "factories"}
        registry: FKRegistry containing valid IDs.
        optional_fields: Set of FK field names that are optional (None is valid).
        list_fields: Set of FK field names that contain lists of FKs
            (e.g., "farmer_ids" containing ["FRM-001", "FRM-002"]).

    Returns:
        List of FKValidationError for any invalid FK values found.
    """
    optional_fields = optional_fields or set()
    list_fields = list_fields or set()
    errors: list[FKValidationError] = []

    for index, record in enumerate(records):
        for field_name, target_entity in fk_mappings.items():
            fk_value = record.get(field_name)

            # Handle missing field
            if fk_value is None or field_name not in record:
                if field_name not in optional_fields:
                    errors.append(
                        FKValidationError(
                            source_entity=source_entity,
                            field_name=field_name,
                            invalid_value=None,
                            target_entity=target_entity,
                            record_index=index,
                        )
                    )
                continue

            # Handle list fields (e.g., farmer_ids)
            if field_name in list_fields:
                if not isinstance(fk_value, list):
                    fk_value = [fk_value]

                for single_value in fk_value:
                    if not registry.validate_fk(target_entity, single_value):
                        errors.append(
                            FKValidationError(
                                source_entity=source_entity,
                                field_name=field_name,
                                invalid_value=single_value,
                                target_entity=target_entity,
                                record_index=index,
                            )
                        )
            else:
                # Single FK value
                if not registry.validate_fk(target_entity, fk_value):
                    errors.append(
                        FKValidationError(
                            source_entity=source_entity,
                            field_name=field_name,
                            invalid_value=fk_value,
                            target_entity=target_entity,
                            record_index=index,
                        )
                    )

    return errors
