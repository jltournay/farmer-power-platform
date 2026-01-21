"""Unit tests for profile loader.

Story 0.8.4: Profile-Based Data Generation
AC #1: Profiles defined in YAML (minimal, demo, demo-large)
"""

# Add required paths
import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).parent.parent.parent.parent
_tests_demo_path = _project_root / "tests" / "demo"
if str(_tests_demo_path) not in sys.path:
    sys.path.insert(0, str(_tests_demo_path))

from generators.profile_loader import ProfileLoader, parse_range  # noqa: E402


class TestProfileLoader:
    """Test profile loading functionality."""

    def test_list_profiles_returns_available_profiles(self) -> None:
        """Test that list_profiles returns expected profile names."""
        loader = ProfileLoader()
        profiles = loader.list_profiles()

        assert "minimal" in profiles
        assert "demo" in profiles
        assert "demo-large" in profiles

    def test_load_minimal_profile(self) -> None:
        """Test loading minimal profile."""
        loader = ProfileLoader()
        profile = loader.load("minimal")

        assert profile.name == "minimal"
        assert profile.get_farmer_count() == 3
        assert profile.get_factory_count() == 1

    def test_load_demo_profile(self) -> None:
        """Test loading demo profile."""
        loader = ProfileLoader()
        profile = loader.load("demo")

        assert profile.name == "demo"
        assert profile.get_farmer_count() == 50
        assert profile.get_factory_count() == 3
        assert profile.get_document_count() == 500

    def test_load_demo_large_profile(self) -> None:
        """Test loading demo-large profile."""
        loader = ProfileLoader()
        profile = loader.load("demo-large")

        assert profile.name == "demo-large"
        assert profile.get_farmer_count() == 250
        assert profile.get_factory_count() == 10

    def test_load_nonexistent_profile_raises_error(self) -> None:
        """Test that loading unknown profile raises FileNotFoundError."""
        loader = ProfileLoader()

        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "Available profiles" in str(exc_info.value)

    def test_get_scenario_counts(self) -> None:
        """Test getting scenario counts from profile."""
        loader = ProfileLoader()
        profile = loader.load("demo")

        scenarios = profile.get_scenario_counts()

        # Demo profile should have scenarios defined
        assert "top_performer" in scenarios
        assert "improving_trend" in scenarios
        assert "consistently_poor" in scenarios

    def test_get_farmer_id_prefix(self) -> None:
        """Test getting farmer ID prefix from profile."""
        loader = ProfileLoader()

        minimal = loader.load("minimal")
        assert minimal.get_farmer_id_prefix() == "FRM-MIN-"

        demo = loader.load("demo")
        assert demo.get_farmer_id_prefix() == "FRM-DEMO-"


class TestParseRange:
    """Test parse_range utility function."""

    def test_parse_single_int(self) -> None:
        """Test parsing single integer."""
        assert parse_range(5) == (5, 5)

    def test_parse_int_string(self) -> None:
        """Test parsing integer as string."""
        assert parse_range("5") == (5, 5)

    def test_parse_range_string(self) -> None:
        """Test parsing range string."""
        assert parse_range("5-15") == (5, 15)

    def test_parse_range_with_spaces(self) -> None:
        """Test parsing range handles numeric conversion."""
        assert parse_range("10-20") == (10, 20)
