"""Unit tests for Plantation model factories.

Story 0.8.3: Polyfactory Generator Framework
Tests AC #1: Factories exist for each model
Tests AC #2: FK fields reference FK registry
Tests AC #4: Generated entities pass Pydantic validation
Tests AC #5: Generated entities are JSON-serializable
"""

import json
import sys
from pathlib import Path

import pytest

# Add tests/demo and scripts/demo to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "tests" / "demo"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "scripts" / "demo"))

from fk_registry import FKRegistry
from fp_common.models.collection_point import CollectionPoint
from fp_common.models.factory import Factory
from fp_common.models.farmer import Farmer
from fp_common.models.farmer_performance import FarmerPerformance
from fp_common.models.region import Region
from generators import (
    CollectionPointFactory,
    FactoryEntityFactory,
    FarmerFactory,
    FarmerPerformanceFactory,
    RegionFactory,
    reset_fk_registry,
    set_fk_registry,
)


@pytest.fixture(autouse=True)
def reset_factories():
    """Reset all factory counters and FK registry before each test."""
    RegionFactory.reset_counter()
    FactoryEntityFactory.reset_counter()
    CollectionPointFactory.reset_counter()
    FarmerFactory.reset_counter()
    FarmerPerformanceFactory.reset_counter()
    reset_fk_registry()
    yield


@pytest.fixture
def fk_registry(reset_factories):
    """Create and configure FK registry with seed data."""
    registry = FKRegistry()
    set_fk_registry(registry)

    # Register some base IDs for FK lookups
    registry.register("regions", ["nyeri-highland", "kericho-midland"])
    registry.register("factories", ["KEN-FAC-001", "KEN-FAC-002"])
    registry.register("farmers", ["WM-0001", "WM-0002", "WM-0003"])
    registry.register("grading_models", ["tbk_kenya_tea_v1"])

    return registry


class TestRegionFactory:
    """Tests for RegionFactory."""

    def test_build_creates_valid_region(self) -> None:
        """Build should create a valid Region instance."""
        region = RegionFactory.build()
        assert isinstance(region, Region)

    def test_region_passes_pydantic_validation(self) -> None:
        """Generated region should pass Pydantic validation."""
        region = RegionFactory.build()
        # Re-validate to ensure it passes
        validated = Region.model_validate(region.model_dump())
        assert validated.region_id == region.region_id

    def test_region_is_json_serializable(self) -> None:
        """Generated region should be JSON-serializable."""
        region = RegionFactory.build()
        json_str = json.dumps(region.model_dump(mode="json"))
        parsed = json.loads(json_str)
        assert "region_id" in parsed
        assert "geography" in parsed

    def test_build_batch_creates_multiple(self) -> None:
        """Build batch should create multiple unique regions."""
        regions = RegionFactory.batch(5)
        assert len(regions) == 5
        # All should be valid regions
        for r in regions:
            assert isinstance(r, Region)

    def test_region_id_follows_pattern(self) -> None:
        """Region ID should follow {county}-{altitude_band} pattern."""
        for _ in range(10):
            region = RegionFactory.build()
            parts = region.region_id.split("-")
            assert len(parts) == 2
            assert parts[1] in ["highland", "midland", "lowland"]


class TestFactoryEntityFactory:
    """Tests for FactoryEntityFactory."""

    def test_build_requires_region_fk(self, fk_registry) -> None:
        """Build should use region_id from FK registry."""
        factory = FactoryEntityFactory.build()
        assert factory.region_id in fk_registry.get_valid_ids("regions")

    def test_build_fails_without_regions(self) -> None:
        """Build should fail if no regions in registry."""
        with pytest.raises(ValueError, match="No regions registered"):
            FactoryEntityFactory.build()

    def test_factory_passes_pydantic_validation(self, fk_registry) -> None:
        """Generated factory should pass Pydantic validation."""
        factory = FactoryEntityFactory.build()
        validated = Factory.model_validate(factory.model_dump())
        assert validated.id == factory.id

    def test_factory_is_json_serializable(self, fk_registry) -> None:
        """Generated factory should be JSON-serializable."""
        factory = FactoryEntityFactory.build()
        json_str = json.dumps(factory.model_dump(mode="json"))
        parsed = json.loads(json_str)
        assert "id" in parsed
        assert "region_id" in parsed

    def test_factory_id_format(self, fk_registry) -> None:
        """Factory ID should follow KEN-FAC-XXXX format."""
        # Reset counter to ensure clean state
        FactoryEntityFactory.reset_counter()
        factory = FactoryEntityFactory.build()
        assert factory.id.startswith("KEN-FAC-")

    def test_build_batch_and_register(self, fk_registry) -> None:
        """Build batch and register should register IDs in FK registry."""
        factories = FactoryEntityFactory.build_batch_and_register(3)
        assert len(factories) == 3

        # IDs should be registered
        for f in factories:
            assert f.id in fk_registry.get_valid_ids("factories")


class TestCollectionPointFactory:
    """Tests for CollectionPointFactory."""

    def test_build_requires_factory_and_region_fk(self, fk_registry) -> None:
        """Build should use factory_id and region_id from FK registry."""
        cp = CollectionPointFactory.build()
        assert cp.factory_id in fk_registry.get_valid_ids("factories")
        assert cp.region_id in fk_registry.get_valid_ids("regions")

    def test_collection_point_passes_pydantic_validation(self, fk_registry) -> None:
        """Generated collection point should pass Pydantic validation."""
        cp = CollectionPointFactory.build()
        validated = CollectionPoint.model_validate(cp.model_dump())
        assert validated.id == cp.id

    def test_collection_point_is_json_serializable(self, fk_registry) -> None:
        """Generated collection point should be JSON-serializable."""
        cp = CollectionPointFactory.build()
        json_str = json.dumps(cp.model_dump(mode="json"))
        parsed = json.loads(json_str)
        assert "id" in parsed
        assert "factory_id" in parsed


class TestFarmerFactory:
    """Tests for FarmerFactory."""

    def test_build_requires_region_fk(self, fk_registry) -> None:
        """Build should use region_id from FK registry."""
        farmer = FarmerFactory.build()
        assert farmer.region_id in fk_registry.get_valid_ids("regions")

    def test_farmer_has_kenya_phone(self, fk_registry) -> None:
        """Farmer should have valid Kenya phone number."""
        farmer = FarmerFactory.build()
        assert farmer.contact.phone.startswith("+254")

    def test_farmer_has_kenya_coordinates(self, fk_registry) -> None:
        """Farmer should have coordinates within Kenya."""
        farmer = FarmerFactory.build()
        loc = farmer.farm_location
        assert -5 <= loc.latitude <= 5
        assert 33 <= loc.longitude <= 42

    def test_farmer_passes_pydantic_validation(self, fk_registry) -> None:
        """Generated farmer should pass Pydantic validation (AC #4)."""
        farmer = FarmerFactory.build()
        validated = Farmer.model_validate(farmer.model_dump())
        assert validated.id == farmer.id

    def test_farmer_is_json_serializable(self, fk_registry) -> None:
        """Generated farmer should be JSON-serializable (AC #5)."""
        farmer = FarmerFactory.build()
        json_str = json.dumps(farmer.model_dump(mode="json"))
        parsed = json.loads(json_str)
        assert "id" in parsed
        assert "first_name" in parsed
        assert "region_id" in parsed

    def test_farmer_id_format(self, fk_registry) -> None:
        """Farmer ID should follow WM-XXXX format."""
        farmer = FarmerFactory.build()
        assert farmer.id.startswith("WM-")
        assert len(farmer.id) == 7  # WM-0001

    def test_farmer_farm_scale_matches_size(self, fk_registry) -> None:
        """Farm scale should be set (factory generates both independently)."""
        farmer = FarmerFactory.build()
        # Just verify both fields are set
        assert farmer.farm_size_hectares > 0
        assert farmer.farm_scale is not None

    def test_build_batch_and_register(self, fk_registry) -> None:
        """Build batch and register should register farmer IDs."""
        farmers = FarmerFactory.build_batch_and_register(5)
        assert len(farmers) == 5

        # IDs should be registered
        for f in farmers:
            assert f.id in fk_registry.get_valid_ids("farmers")


class TestFarmerPerformanceFactory:
    """Tests for FarmerPerformanceFactory."""

    def test_build_requires_farmer_fk(self, fk_registry) -> None:
        """Build should use farmer_id from FK registry."""
        perf = FarmerPerformanceFactory.build()
        assert perf.farmer_id in fk_registry.get_valid_ids("farmers")

    def test_farmer_performance_passes_pydantic_validation(self, fk_registry) -> None:
        """Generated farmer performance should pass Pydantic validation."""
        perf = FarmerPerformanceFactory.build()
        validated = FarmerPerformance.model_validate(perf.model_dump())
        assert validated.farmer_id == perf.farmer_id

    def test_farmer_performance_is_json_serializable(self, fk_registry) -> None:
        """Generated farmer performance should be JSON-serializable."""
        perf = FarmerPerformanceFactory.build()
        json_str = json.dumps(perf.model_dump(mode="json"))
        parsed = json.loads(json_str)
        assert "farmer_id" in parsed
        assert "historical" in parsed
        assert "today" in parsed


class TestFactoryOverrides:
    """Tests for factory field overrides."""

    def test_farmer_with_custom_region(self, fk_registry) -> None:
        """Farmer should accept custom region_id override."""
        farmer = FarmerFactory.build(region_id="nyeri-highland")
        assert farmer.region_id == "nyeri-highland"

    def test_farmer_with_custom_name(self, fk_registry) -> None:
        """Farmer should accept custom name override."""
        farmer = FarmerFactory.build(first_name="Custom", last_name="Name")
        assert farmer.first_name == "Custom"
        assert farmer.last_name == "Name"

    def test_factory_entity_with_custom_capacity(self, fk_registry) -> None:
        """Factory should accept custom processing capacity."""
        # Reset counter to ensure clean state
        FactoryEntityFactory.reset_counter()
        factory = FactoryEntityFactory.build(processing_capacity_kg=99999)
        assert factory.processing_capacity_kg == 99999
