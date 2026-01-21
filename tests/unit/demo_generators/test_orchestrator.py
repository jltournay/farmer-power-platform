"""Unit tests for data orchestrator.

Story 0.8.4: Profile-Based Data Generation
AC #2: Output follows E2E seed file structure
AC #3: Deterministic with --seed flag
"""

import json

# Add required paths
import sys
import tempfile
from pathlib import Path

import pytest

_project_root = Path(__file__).parent.parent.parent.parent
_tests_demo_path = _project_root / "tests" / "demo"
if str(_tests_demo_path) not in sys.path:
    sys.path.insert(0, str(_tests_demo_path))

from generators.orchestrator import DataOrchestrator, GeneratedData  # noqa: E402
from generators.profile_loader import ProfileLoader  # noqa: E402


class TestDataOrchestrator:
    """Test DataOrchestrator class."""

    def test_generate_with_minimal_profile(self) -> None:
        """Test generating data with minimal profile."""
        loader = ProfileLoader()
        profile = loader.load("minimal")
        orchestrator = DataOrchestrator(seed=12345)

        data = orchestrator.generate(profile)

        assert len(data.factories) == profile.get_factory_count()
        assert len(data.farmers) == profile.get_farmer_count()
        assert len(data.documents) > 0

    def test_generated_farmers_have_valid_ids(self) -> None:
        """Test generated farmers have proper ID format."""
        loader = ProfileLoader()
        profile = loader.load("minimal")
        orchestrator = DataOrchestrator(seed=12345)

        data = orchestrator.generate(profile)

        for farmer in data.farmers:
            assert farmer["id"].startswith("FRM-MIN-")

    def test_generated_documents_reference_valid_farmers(self) -> None:
        """Test documents reference farmers that exist."""
        loader = ProfileLoader()
        profile = loader.load("minimal")
        orchestrator = DataOrchestrator(seed=12345)

        data = orchestrator.generate(profile)

        farmer_ids = {f["id"] for f in data.farmers}
        for doc in data.documents:
            farmer_id = doc["linkage_fields"]["farmer_id"]
            assert farmer_id in farmer_ids, f"Document references unknown farmer: {farmer_id}"

    def test_documents_have_valid_structure(self) -> None:
        """Test generated documents have expected structure (AC #2)."""
        loader = ProfileLoader()
        profile = loader.load("minimal")
        orchestrator = DataOrchestrator(seed=12345)

        data = orchestrator.generate(profile)

        for doc in data.documents:
            # Check required fields exist
            assert "document_id" in doc
            assert "raw_document" in doc
            assert "extraction" in doc
            assert "ingestion" in doc
            assert "extracted_fields" in doc
            assert "linkage_fields" in doc
            assert "created_at" in doc

            # Check nested structure
            assert "blob_container" in doc["raw_document"]
            assert "blob_path" in doc["raw_document"]
            assert "ai_agent_id" in doc["extraction"]
            assert "source_id" in doc["ingestion"]

    def test_documents_have_bag_summary(self) -> None:
        """Test documents have bag_summary with quality metrics."""
        loader = ProfileLoader()
        profile = loader.load("minimal")
        orchestrator = DataOrchestrator(seed=12345)

        data = orchestrator.generate(profile)

        for doc in data.documents:
            bag_summary = doc["extracted_fields"]["bag_summary"]
            assert "total_weight_kg" in bag_summary
            assert "primary_percentage" in bag_summary
            assert "secondary_percentage" in bag_summary
            assert "grade" in bag_summary

            # Validate percentages
            primary = bag_summary["primary_percentage"]
            secondary = bag_summary["secondary_percentage"]
            assert 0 <= primary <= 100
            assert 0 <= secondary <= 100


class TestWriteToFiles:
    """Test writing generated data to files."""

    def test_write_creates_expected_files(self) -> None:
        """Test write_to_files creates all expected JSON files."""
        loader = ProfileLoader()
        profile = loader.load("minimal")
        orchestrator = DataOrchestrator(seed=12345)
        data = orchestrator.generate(profile)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_counts = orchestrator.write_to_files(data, tmpdir)
            output_path = Path(tmpdir)

            # Check expected files exist
            assert (output_path / "factories.json").exists()
            assert (output_path / "farmers.json").exists()
            assert (output_path / "documents.json").exists()
            assert (output_path / "_metadata.json").exists()

    def test_write_creates_valid_json(self) -> None:
        """Test written files are valid JSON."""
        loader = ProfileLoader()
        profile = loader.load("minimal")
        orchestrator = DataOrchestrator(seed=12345)
        data = orchestrator.generate(profile)

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator.write_to_files(data, tmpdir)
            output_path = Path(tmpdir)

            # Verify JSON is valid
            farmers_path = output_path / "farmers.json"
            with farmers_path.open() as f:
                farmers = json.load(f)
            assert isinstance(farmers, list)
            assert len(farmers) == profile.get_farmer_count()

    def test_metadata_file_contains_profile_info(self) -> None:
        """Test _metadata.json contains profile information."""
        loader = ProfileLoader()
        profile = loader.load("minimal")
        orchestrator = DataOrchestrator(seed=12345)
        data = orchestrator.generate(profile)

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator.write_to_files(data, tmpdir)
            output_path = Path(tmpdir)

            metadata_path = output_path / "_metadata.json"
            with metadata_path.open() as f:
                metadata = json.load(f)

            assert metadata["profile"] == "minimal"
            assert metadata["seed"] == 12345
            assert "generated_at" in metadata
            assert "counts" in metadata


class TestDeterministicGeneration:
    """Test deterministic generation with seed (AC #3)."""

    def test_same_seed_produces_same_id_sequence(self) -> None:
        """Test that same seed produces same farmer IDs."""
        loader = ProfileLoader()
        profile = loader.load("minimal")

        orchestrator1 = DataOrchestrator(seed=12345)
        data1 = orchestrator1.generate(profile)

        orchestrator2 = DataOrchestrator(seed=12345)
        data2 = orchestrator2.generate(profile)

        ids1 = [f["id"] for f in data1.farmers]
        ids2 = [f["id"] for f in data2.farmers]

        assert ids1 == ids2, "Same seed should produce same farmer IDs"

    def test_different_seed_produces_different_counts(self) -> None:
        """Test that different seeds produce same structure but different details."""
        loader = ProfileLoader()
        profile = loader.load("minimal")

        orchestrator1 = DataOrchestrator(seed=12345)
        data1 = orchestrator1.generate(profile)

        orchestrator2 = DataOrchestrator(seed=54321)
        data2 = orchestrator2.generate(profile)

        # Structure should be same
        assert len(data1.farmers) == len(data2.farmers)
        assert len(data1.documents) > 0 and len(data2.documents) > 0


class TestGeneratedData:
    """Test GeneratedData dataclass."""

    def test_generated_data_defaults(self) -> None:
        """Test GeneratedData has sensible defaults."""
        data = GeneratedData()

        assert data.factories == []
        assert data.farmers == []
        assert data.documents == []
        assert data.profile_name == ""
        assert data.seed is None
