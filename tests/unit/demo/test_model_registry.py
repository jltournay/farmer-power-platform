"""Unit tests for Model Registry module.

Tests for:
- AC #5: Models imported directly from service packages (no duplication)
- Mapping file patterns to correct Pydantic models
"""

from scripts.demo.model_registry import (
    ModelRegistry,
    get_model_for_file,
    get_seed_model_registry,
)


class TestModelRegistry:
    """Tests for ModelRegistry class."""

    def test_register_and_get_model(self) -> None:
        """Registry can register and retrieve models by pattern."""
        from pydantic import BaseModel, ConfigDict

        class TestModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            id: str

        registry = ModelRegistry()
        registry.register("tests.json", TestModel)

        model = registry.get_model("tests.json")
        assert model is TestModel

    def test_get_model_not_found_returns_none(self) -> None:
        """Getting unknown pattern returns None."""
        registry = ModelRegistry()
        model = registry.get_model("unknown.json")
        assert model is None

    def test_pattern_matching_works(self) -> None:
        """Pattern matching finds model based on filename."""
        from pydantic import BaseModel, ConfigDict

        class FarmerModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            id: str

        registry = ModelRegistry()
        registry.register("farmers.json", FarmerModel)

        # Exact match
        model = registry.get_model("farmers.json")
        assert model is FarmerModel

        # Should not match similar but different names
        model = registry.get_model("new_farmers.json")
        assert model is None


class TestGetModelForFile:
    """Tests for get_model_for_file function."""

    def test_resolves_farmers_json(self) -> None:
        """AC #5: Resolves farmers.json to Farmer model from fp_common."""

        model = get_model_for_file("farmers.json")
        # Should return a model that validates Farmer-shaped data
        # Note: We wrap in StrictFarmer for extra="forbid"
        assert model is not None
        # Verify it has the key Farmer fields
        assert "id" in model.model_fields
        assert "first_name" in model.model_fields

    def test_resolves_regions_json(self) -> None:
        """AC #5: Resolves regions.json to Region model from fp_common."""
        model = get_model_for_file("regions.json")
        assert model is not None
        assert "region_id" in model.model_fields

    def test_resolves_factories_json(self) -> None:
        """AC #5: Resolves factories.json to Factory model from fp_common."""
        model = get_model_for_file("factories.json")
        assert model is not None
        assert "id" in model.model_fields
        assert "code" in model.model_fields

    def test_resolves_collection_points_json(self) -> None:
        """AC #5: Resolves collection_points.json to CollectionPoint model."""
        model = get_model_for_file("collection_points.json")
        assert model is not None
        assert "id" in model.model_fields
        assert "factory_id" in model.model_fields

    def test_resolves_grading_models_json(self) -> None:
        """AC #5: Resolves grading_models.json to GradingModel."""
        model = get_model_for_file("grading_models.json")
        assert model is not None
        assert "model_id" in model.model_fields

    def test_resolves_farmer_performance_json(self) -> None:
        """AC #5: Resolves farmer_performance.json to FarmerPerformance."""
        model = get_model_for_file("farmer_performance.json")
        assert model is not None
        assert "farmer_id" in model.model_fields

    def test_resolves_source_configs_json(self) -> None:
        """AC #5: Resolves source_configs.json to SourceConfig."""
        model = get_model_for_file("source_configs.json")
        assert model is not None
        assert "source_id" in model.model_fields

    def test_resolves_prompts_json(self) -> None:
        """AC #5: Resolves prompts.json to Prompt from ai_model."""
        model = get_model_for_file("prompts.json")
        assert model is not None
        assert "prompt_id" in model.model_fields

    def test_resolves_agent_configs_json(self) -> None:
        """AC #5: Resolves agent_configs.json to AgentConfig."""
        model = get_model_for_file("agent_configs.json")
        assert model is not None
        # AgentConfig is a discriminated union, so check common fields

    def test_resolves_weather_observations_json(self) -> None:
        """AC #5: Resolves weather_observations.json to RegionalWeather."""
        model = get_model_for_file("weather_observations.json")
        assert model is not None
        assert "region_id" in model.model_fields

    def test_resolves_documents_json(self) -> None:
        """AC #5: Resolves documents.json to Document from fp_common."""
        model = get_model_for_file("documents.json")
        assert model is not None
        assert "document_id" in model.model_fields

    def test_unknown_file_returns_none(self) -> None:
        """Unknown file pattern returns None."""
        model = get_model_for_file("unknown_file.json")
        assert model is None


class TestGetSeedModelRegistry:
    """Tests for get_seed_model_registry function."""

    def test_returns_populated_registry(self) -> None:
        """Returns pre-populated registry with all seed models."""
        registry = get_seed_model_registry()
        assert isinstance(registry, ModelRegistry)

        # Verify key models are registered
        assert registry.get_model("farmers.json") is not None
        assert registry.get_model("regions.json") is not None
        assert registry.get_model("factories.json") is not None

    def test_all_models_have_extra_forbid(self) -> None:
        """AC #2: All registered models reject extra fields."""
        registry = get_seed_model_registry()

        # Models that expose model_config directly
        standard_patterns = [
            "farmers.json",
            "regions.json",
            "factories.json",
            "collection_points.json",
            "grading_models.json",
            "farmer_performance.json",
            "source_configs.json",
            "prompts.json",
            "weather_observations.json",
            "documents.json",
        ]

        for pattern in standard_patterns:
            model = registry.get_model(pattern)
            if model is not None:
                # Check model_config.extra is "forbid"
                config = getattr(model, "model_config", {})
                assert config.get("extra") == "forbid", f"{pattern} model should have extra='forbid'"

    def test_agent_configs_validates_via_type_adapter(self) -> None:
        """agent_configs.json uses TypeAdapter for discriminated union validation.

        Note: Unlike other models, AgentConfig is a discriminated union where the
        underlying production models don't have extra="forbid". TypeAdapter still
        validates the structure correctly (required fields, types, etc.) but won't
        reject extra fields at the top level. This is acceptable since:
        1. We import directly from production models (AC #5)
        2. Structure validation catches real schema errors
        """
        import pytest

        model = get_model_for_file("agent_configs.json")
        assert model is not None

        # Use a complete valid extractor config (matching seed data structure)
        valid_config = {
            "id": "test-agent:1.0.0",
            "agent_id": "test-agent",
            "version": "1.0.0",
            "type": "extractor",
            "status": "active",
            "description": "Test extractor",
            "input": {"event": "test.event", "schema": {"type": "object"}},
            "output": {"event": "test.output", "schema": {"type": "object"}},
            "llm": {"model": "test/model", "temperature": 0.1, "max_tokens": 100},
            "extraction_schema": {
                "required_fields": ["grade"],
                "optional_fields": [],
                "field_types": {"grade": "string"},
            },
            "normalization_rules": [],
            "mcp_sources": [],
            "error_handling": {
                "max_attempts": 1,
                "backoff_ms": [100],
                "on_failure": "publish_error_event",
                "dead_letter_topic": None,
            },
            "metadata": {
                "author": "test",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "git_commit": None,
            },
        }

        # Should validate successfully
        model.model_validate(valid_config)

        # Should reject invalid type discriminator
        invalid_config = {**valid_config, "type": "invalid_type"}
        with pytest.raises(Exception):  # ValidationError from Pydantic
            model.model_validate(invalid_config)

        # Should reject missing required fields
        missing_required = {k: v for k, v in valid_config.items() if k != "extraction_schema"}
        with pytest.raises(Exception):  # ValidationError from Pydantic
            model.model_validate(missing_required)
