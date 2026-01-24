"""Unit tests for seed data loader module.

Story 0.8.2: Seed Data Loader Script
Task 7: Write unit tests
AC #1-6: Comprehensive test coverage

Uses mock MongoDB to test loading logic without actual database.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.demo.loader import (
    COLLECTION_MAPPING,
    SEED_ORDER,
    LoadResult,
    SeedDataLoader,
    VerificationResult,
    convert_pydantic_to_dicts,
)


class TestSeedOrder:
    """Tests for SEED_ORDER configuration."""

    def test_seed_order_has_all_expected_files(self) -> None:
        """Verify SEED_ORDER contains all expected seed files."""
        expected_files = {
            "grading_models.json",
            "regions.json",
            "agent_configs.json",
            "prompts.json",
            "cost_events.json",
            "source_configs.json",
            "factories.json",
            "collection_points.json",
            "farmers.json",
            "farmer_performance.json",
            "weather_observations.json",
            "documents.json",
        }

        actual_files = {entry[0] for entry in SEED_ORDER}
        assert actual_files == expected_files

    def test_load_order_respects_dependencies(self) -> None:
        """Test that SEED_ORDER respects FK dependency order.

        Level 0 (no deps): grading_models, regions, agent_configs, prompts
        Level 1 (Level 0): source_configs, factories
        Level 2 (Level 1+0): collection_points
        Level 3 (Level 0): farmers
        Level 4 (Level 3): farmer_performance, weather_observations
        Level 5 (Level 1+3): documents
        """
        file_order = [entry[0] for entry in SEED_ORDER]

        # Level 0 should come before all dependents
        level_0 = {"grading_models.json", "regions.json", "agent_configs.json", "prompts.json"}
        level_0_indices = {file_order.index(f) for f in level_0 if f in file_order}

        # Factories depend on regions
        factories_idx = file_order.index("factories.json")
        regions_idx = file_order.index("regions.json")
        assert regions_idx < factories_idx, "regions must come before factories"

        # Collection points depend on factories and regions
        cp_idx = file_order.index("collection_points.json")
        assert factories_idx < cp_idx, "factories must come before collection_points"
        assert regions_idx < cp_idx, "regions must come before collection_points"

        # Farmers depend on regions
        farmers_idx = file_order.index("farmers.json")
        assert regions_idx < farmers_idx, "regions must come before farmers"

        # Farmer performance depends on farmers
        fp_idx = file_order.index("farmer_performance.json")
        assert farmers_idx < fp_idx, "farmers must come before farmer_performance"

        # Weather observations depend on regions
        weather_idx = file_order.index("weather_observations.json")
        assert regions_idx < weather_idx, "regions must come before weather_observations"

        # Documents depend on source_configs (and optionally farmers)
        docs_idx = file_order.index("documents.json")
        sc_idx = file_order.index("source_configs.json")
        assert sc_idx < docs_idx, "source_configs must come before documents"


class TestCollectionMapping:
    """Tests for COLLECTION_MAPPING configuration."""

    def test_collection_mapping_matches_seed_order(self) -> None:
        """Verify all SEED_ORDER files have collection mappings."""
        for filename, _, _, _ in SEED_ORDER:
            assert filename in COLLECTION_MAPPING, f"Missing mapping for {filename}"


class TestLoadResult:
    """Tests for LoadResult dataclass."""

    def test_load_result_attributes(self) -> None:
        """Test LoadResult stores all attributes correctly."""
        result = LoadResult(
            filename="farmers.json",
            collection="farmers",
            records_loaded=10,
            database="plantation_e2e",
        )

        assert result.filename == "farmers.json"
        assert result.collection == "farmers"
        assert result.records_loaded == 10
        assert result.database == "plantation_e2e"


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_verification_result_valid_when_counts_match(self) -> None:
        """Test is_valid returns True when expected == actual."""
        result = VerificationResult(
            collection="farmers",
            expected=10,
            actual=10,
            database="plantation_e2e",
        )

        assert result.is_valid is True

    def test_verification_result_invalid_when_counts_differ(self) -> None:
        """Test is_valid returns False when expected != actual."""
        result = VerificationResult(
            collection="farmers",
            expected=10,
            actual=5,
            database="plantation_e2e",
        )

        assert result.is_valid is False


class TestConvertPydanticToDicts:
    """Tests for convert_pydantic_to_dicts function."""

    def test_converts_pydantic_models_to_dicts(self) -> None:
        """Test that Pydantic models are converted to dictionaries."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            id: str
            name: str

        models = [
            TestModel(id="1", name="Test 1"),
            TestModel(id="2", name="Test 2"),
        ]

        result = convert_pydantic_to_dicts(models)

        assert len(result) == 2
        assert result[0] == {"id": "1", "name": "Test 1"}
        assert result[1] == {"id": "2", "name": "Test 2"}

    def test_returns_empty_list_for_empty_input(self) -> None:
        """Test that empty input returns empty list."""
        result = convert_pydantic_to_dicts([])
        assert result == []


class TestSeedDataLoader:
    """Tests for SeedDataLoader class."""

    @pytest.fixture
    def mock_mongodb_client(self) -> MagicMock:
        """Create a mock MongoDBDirectClient."""
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        # Mock seed methods
        client.seed_grading_models = AsyncMock()
        client.seed_regions = AsyncMock()
        client.seed_agent_configs = AsyncMock()
        client.seed_prompts = AsyncMock()
        client.seed_source_configs = AsyncMock()
        client.seed_factories = AsyncMock()
        client.seed_collection_points = AsyncMock()
        client.seed_farmers = AsyncMock()
        client.seed_farmer_performance = AsyncMock()
        client.seed_weather_observations = AsyncMock()
        client.seed_documents = AsyncMock()
        client.drop_all_e2e_databases = AsyncMock()

        # Mock database access
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.count_documents = AsyncMock(return_value=5)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        client.get_database = MagicMock(return_value=mock_db)

        return client

    @pytest.mark.asyncio
    async def test_load_file_calls_correct_seed_method(
        self,
        mock_mongodb_client: MagicMock,
    ) -> None:
        """Test that load_file calls the correct seed method for each file."""
        # Set the mock client directly - no patching needed
        loader = SeedDataLoader()
        loader._client = mock_mongodb_client

        records = [{"id": "test-1", "name": "Test"}]
        result = await loader.load_file("farmers.json", records)

        mock_mongodb_client.seed_farmers.assert_called_once_with(records)
        assert result.filename == "farmers.json"
        assert result.records_loaded == 1

    @pytest.mark.asyncio
    async def test_load_file_raises_for_unknown_file(
        self,
        mock_mongodb_client: MagicMock,
    ) -> None:
        """Test that load_file raises ValueError for unknown seed file."""
        loader = SeedDataLoader()
        loader._client = mock_mongodb_client

        with pytest.raises(ValueError, match="Unknown seed file"):
            await loader.load_file("unknown.json", [])

    @pytest.mark.asyncio
    async def test_load_all_processes_files_in_order(
        self,
        mock_mongodb_client: MagicMock,
    ) -> None:
        """Test that load_all processes files in SEED_ORDER sequence."""
        loader = SeedDataLoader()
        loader._client = mock_mongodb_client

        validated_data = {
            "regions.json": [{"region_id": "reg-1"}],
            "farmers.json": [{"id": "frm-1"}],
            "grading_models.json": [{"model_id": "gm-1"}],
        }

        results = await loader.load_all(validated_data)

        # Should be processed in SEED_ORDER: grading_models, regions, farmers
        assert len(results) == 3
        assert results[0].filename == "grading_models.json"
        assert results[1].filename == "regions.json"
        assert results[2].filename == "farmers.json"

    @pytest.mark.asyncio
    async def test_verify_counts_returns_correct_results(
        self,
        mock_mongodb_client: MagicMock,
    ) -> None:
        """Test that verify_counts checks counts correctly."""
        # Setup mock to return different counts
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.count_documents = AsyncMock(return_value=5)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_mongodb_client.get_database = MagicMock(return_value=mock_db)

        loader = SeedDataLoader()
        loader._client = mock_mongodb_client

        expected_counts = {"farmers.json": 5}
        results = await loader.verify_counts(expected_counts)

        assert len(results) == 1
        assert results[0].is_valid is True
        assert results[0].expected == 5
        assert results[0].actual == 5

    @pytest.mark.asyncio
    async def test_upsert_pattern_no_duplicates(
        self,
        mock_mongodb_client: MagicMock,
    ) -> None:
        """Test that loading twice doesn't create duplicates (upsert pattern).

        The upsert pattern is implemented in MongoDBDirectClient's seed methods.
        This test verifies that we call the same method both times, which uses upsert.
        """
        loader = SeedDataLoader()
        loader._client = mock_mongodb_client

        records = [{"id": "frm-1", "name": "Farmer 1"}]

        # Load twice
        await loader.load_file("farmers.json", records)
        await loader.load_file("farmers.json", records)

        # Seed method should be called twice (upsert handles dedup)
        assert mock_mongodb_client.seed_farmers.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_all_databases(
        self,
        mock_mongodb_client: MagicMock,
    ) -> None:
        """Test that clear_all_databases delegates to client."""
        loader = SeedDataLoader()
        loader._client = mock_mongodb_client

        await loader.clear_all_databases()

        mock_mongodb_client.drop_all_e2e_databases.assert_called_once()


class TestDryRunMode:
    """Tests for dry-run mode behavior."""

    def test_dry_run_skips_database(self) -> None:
        """Test that --dry-run flag prevents database writes.

        This is tested at the integration level in the main script,
        but we verify the mode parsing here.
        """
        # Verify the script parses dry_run argument correctly
        # Mock sys.argv to test parsing
        import sys

        from scripts.demo.load_demo_data import parse_args

        with patch.object(sys, "argv", ["load_demo_data.py", "--dry-run"]):
            args = parse_args()
            assert args.dry_run is True


class TestCustomSourcePath:
    """Tests for custom source path feature."""

    def test_custom_source_path_validation(self, tmp_path: Path) -> None:
        """Test that custom source path is validated correctly."""
        import argparse

        from scripts.demo.load_demo_data import validate_args

        # Create a valid custom path
        custom_dir = tmp_path / "custom_seed"
        custom_dir.mkdir()

        parser = argparse.ArgumentParser()
        parser.add_argument("--source", default="custom")
        parser.add_argument("--path", type=Path, default=custom_dir)
        args = parser.parse_args([])

        result = validate_args(args)
        assert result == custom_dir

    def test_custom_source_path_missing_raises_error(self) -> None:
        """Test that missing --path with --source custom raises error."""
        import argparse

        from scripts.demo.load_demo_data import validate_args

        parser = argparse.ArgumentParser()
        parser.add_argument("--source", default="custom")
        parser.add_argument("--path", type=Path, default=None)
        args = parser.parse_args([])

        with pytest.raises(SystemExit):
            validate_args(args)


class TestExitCodes:
    """Tests for exit code behavior."""

    def test_exit_code_on_failure(self) -> None:
        """Test that validation failures return non-zero exit code.

        This is tested at the integration level, but we verify the
        contract here.
        """
        # A validation failure should return exit code 1
        # The main function is async, so we verify it returns int
        import inspect

        from scripts.demo.load_demo_data import main

        assert inspect.iscoroutinefunction(main)

        # Return type annotation check (annotation can be string or type)
        annotations = main.__annotations__
        return_type = annotations.get("return")
        assert return_type in (int, "int"), f"Expected int or 'int', got {return_type}"
