"""Unit tests for FK Registry module.

Tests for:
- AC #4: FK validation checks against FK registry with detailed error reporting
"""

from scripts.demo.fk_registry import FKRegistry, FKValidationError, validate_foreign_keys


class TestFKRegistry:
    """Tests for FKRegistry class."""

    def test_register_and_get_valid_ids(self) -> None:
        """Registry stores and retrieves valid IDs for entity types."""
        registry = FKRegistry()

        # Register some IDs
        registry.register("regions", ["reg-001", "reg-002", "reg-003"])
        registry.register("factories", ["fac-001", "fac-002"])

        # Retrieve
        region_ids = registry.get_valid_ids("regions")
        assert region_ids == {"reg-001", "reg-002", "reg-003"}

        factory_ids = registry.get_valid_ids("factories")
        assert factory_ids == {"fac-001", "fac-002"}

    def test_get_valid_ids_unknown_entity_returns_empty(self) -> None:
        """Getting IDs for unknown entity returns empty set."""
        registry = FKRegistry()
        registry.register("regions", ["reg-001"])

        unknown = registry.get_valid_ids("unknown_entity")
        assert unknown == set()

    def test_validate_fk_success(self) -> None:
        """AC #4: FK lookup succeeds for valid FK."""
        registry = FKRegistry()
        registry.register("regions", ["reg-001", "reg-002"])

        is_valid = registry.validate_fk(
            entity_type="regions",
            fk_value="reg-001",
        )
        assert is_valid is True

    def test_validate_fk_failure(self) -> None:
        """AC #4: FK lookup fails for invalid FK."""
        registry = FKRegistry()
        registry.register("regions", ["reg-001", "reg-002"])

        is_valid = registry.validate_fk(
            entity_type="regions",
            fk_value="reg-999",
        )
        assert is_valid is False

    def test_validate_fk_unknown_entity(self) -> None:
        """FK validation for unknown entity returns False."""
        registry = FKRegistry()
        registry.register("regions", ["reg-001"])

        is_valid = registry.validate_fk(
            entity_type="factories",
            fk_value="fac-001",
        )
        assert is_valid is False

    def test_register_extends_existing(self) -> None:
        """Registering more IDs for same entity extends the set."""
        registry = FKRegistry()
        registry.register("regions", ["reg-001"])
        registry.register("regions", ["reg-002", "reg-003"])

        ids = registry.get_valid_ids("regions")
        assert ids == {"reg-001", "reg-002", "reg-003"}


class TestFKValidationError:
    """Tests for FKValidationError dataclass."""

    def test_error_contains_context(self) -> None:
        """AC #4: FK error includes source entity, field name, invalid value."""
        error = FKValidationError(
            source_entity="farmers",
            field_name="region_id",
            invalid_value="invalid-region",
            target_entity="regions",
            record_index=5,
        )

        assert error.source_entity == "farmers"
        assert error.field_name == "region_id"
        assert error.invalid_value == "invalid-region"
        assert error.target_entity == "regions"
        assert error.record_index == 5

    def test_error_str_representation(self) -> None:
        """Error has useful string representation."""
        error = FKValidationError(
            source_entity="farmers",
            field_name="region_id",
            invalid_value="invalid-region",
            target_entity="regions",
            record_index=5,
        )

        error_str = str(error)
        assert "farmers" in error_str
        assert "region_id" in error_str
        assert "invalid-region" in error_str
        assert "regions" in error_str


class TestValidateForeignKeys:
    """Tests for validate_foreign_keys function."""

    def test_validates_single_fk(self) -> None:
        """AC #4: Validates single FK field against registry."""
        registry = FKRegistry()
        registry.register("regions", ["reg-001", "reg-002"])

        records = [
            {"id": "frm-001", "name": "Farmer 1", "region_id": "reg-001"},
            {"id": "frm-002", "name": "Farmer 2", "region_id": "reg-002"},
        ]

        errors = validate_foreign_keys(
            records=records,
            source_entity="farmers",
            fk_mappings={"region_id": "regions"},
            registry=registry,
        )

        assert len(errors) == 0

    def test_reports_invalid_fk(self) -> None:
        """AC #4: Reports invalid FK with context."""
        registry = FKRegistry()
        registry.register("regions", ["reg-001"])

        records = [
            {"id": "frm-001", "name": "Farmer 1", "region_id": "invalid-region"},
        ]

        errors = validate_foreign_keys(
            records=records,
            source_entity="farmers",
            fk_mappings={"region_id": "regions"},
            registry=registry,
        )

        assert len(errors) == 1
        assert errors[0].source_entity == "farmers"
        assert errors[0].field_name == "region_id"
        assert errors[0].invalid_value == "invalid-region"
        assert errors[0].target_entity == "regions"
        assert errors[0].record_index == 0

    def test_validates_multiple_fk_fields(self) -> None:
        """Validates multiple FK fields in one call."""
        registry = FKRegistry()
        registry.register("regions", ["reg-001", "reg-002"])
        registry.register("factories", ["fac-001"])

        records = [
            {
                "id": "cp-001",
                "name": "CP 1",
                "region_id": "reg-001",
                "factory_id": "fac-001",
            },
            {
                "id": "cp-002",
                "name": "CP 2",
                "region_id": "invalid-region",  # invalid
                "factory_id": "invalid-factory",  # invalid
            },
        ]

        errors = validate_foreign_keys(
            records=records,
            source_entity="collection_points",
            fk_mappings={
                "region_id": "regions",
                "factory_id": "factories",
            },
            registry=registry,
        )

        assert len(errors) == 2
        error_fields = {e.field_name for e in errors}
        assert error_fields == {"region_id", "factory_id"}
        assert all(e.record_index == 1 for e in errors)

    def test_handles_optional_fk_none(self) -> None:
        """Handles None values for optional FK fields."""
        registry = FKRegistry()
        registry.register("agent_configs", ["agent-001"])

        records = [
            {"id": "src-001", "name": "Source 1", "ai_agent_id": None},  # Optional FK
        ]

        errors = validate_foreign_keys(
            records=records,
            source_entity="source_configs",
            fk_mappings={"ai_agent_id": "agent_configs"},
            registry=registry,
            optional_fields={"ai_agent_id"},
        )

        assert len(errors) == 0

    def test_handles_missing_fk_field(self) -> None:
        """Handles records missing FK field entirely."""
        registry = FKRegistry()
        registry.register("regions", ["reg-001"])

        records = [
            {"id": "frm-001", "name": "Farmer 1"},  # Missing region_id
        ]

        # Optional field missing is OK
        errors = validate_foreign_keys(
            records=records,
            source_entity="farmers",
            fk_mappings={"region_id": "regions"},
            registry=registry,
            optional_fields={"region_id"},
        )
        assert len(errors) == 0

        # Required field missing should error
        errors = validate_foreign_keys(
            records=records,
            source_entity="farmers",
            fk_mappings={"region_id": "regions"},
            registry=registry,
        )
        # This returns an error for missing required FK
        assert len(errors) == 1
        assert errors[0].invalid_value is None

    def test_validates_list_of_fks(self) -> None:
        """Validates list fields containing multiple FKs (e.g., farmer_ids)."""
        registry = FKRegistry()
        registry.register("farmers", ["frm-001", "frm-002", "frm-003"])

        records = [
            {
                "id": "cp-001",
                "name": "CP 1",
                "farmer_ids": ["frm-001", "frm-002"],  # all valid
            },
            {
                "id": "cp-002",
                "name": "CP 2",
                "farmer_ids": ["frm-001", "invalid-farmer"],  # one invalid
            },
        ]

        errors = validate_foreign_keys(
            records=records,
            source_entity="collection_points",
            fk_mappings={"farmer_ids": "farmers"},
            registry=registry,
            list_fields={"farmer_ids"},
        )

        assert len(errors) == 1
        assert errors[0].record_index == 1
        assert errors[0].field_name == "farmer_ids"
        assert errors[0].invalid_value == "invalid-farmer"
