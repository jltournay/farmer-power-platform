"""Unit tests for the validator module."""

import sys
from pathlib import Path
from typing import Any

import pytest

# Add source-config src to path
sys.path.insert(0, str(Path(__file__).parents[3] / "scripts" / "source-config" / "src"))
# Add fp-common to path
sys.path.insert(0, str(Path(__file__).parents[3] / "libs" / "fp-common"))

from fp_source_config.validator import (
    get_source_config_files,
    load_yaml_file,
    validate_source_config,
    validate_source_configs,
)


@pytest.mark.unit
class TestLoadYamlFile:
    """Tests for the load_yaml_file function."""

    def test_load_valid_yaml(self, temp_config_dir: Path, sample_valid_config: dict[str, Any]) -> None:
        """Test loading a valid YAML file."""
        import yaml

        file_path = temp_config_dir / "valid.yaml"
        with file_path.open("w") as f:
            yaml.dump(sample_valid_config, f)

        result = load_yaml_file(file_path)
        assert result is not None
        assert result["source_id"] == "test-source"

    def test_load_invalid_yaml(self, temp_config_dir: Path) -> None:
        """Test loading an invalid YAML file returns None."""
        file_path = temp_config_dir / "invalid.yaml"
        with file_path.open("w") as f:
            f.write("invalid: yaml: content: [")

        result = load_yaml_file(file_path)
        assert result is None

    def test_load_nonexistent_file(self, temp_config_dir: Path) -> None:
        """Test loading a nonexistent file raises error."""
        file_path = temp_config_dir / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            load_yaml_file(file_path)


@pytest.mark.unit
class TestValidateSourceConfig:
    """Tests for the validate_source_config function."""

    def test_validate_valid_config(self, create_config_file, sample_valid_config: dict[str, Any]) -> None:
        """Test validating a valid configuration."""
        file_path = create_config_file("valid.yaml", sample_valid_config)

        result = validate_source_config(file_path)

        assert result.is_valid is True
        assert result.source_id == "test-source"
        assert result.errors == []

    def test_validate_scheduled_config(self, create_config_file, sample_scheduled_config: dict[str, Any]) -> None:
        """Test validating a scheduled pull configuration."""
        file_path = create_config_file("scheduled.yaml", sample_scheduled_config)

        result = validate_source_config(file_path)

        assert result.is_valid is True
        assert result.source_id == "scheduled-source"

    def test_validate_invalid_config(self, create_config_file, sample_invalid_config: dict[str, Any]) -> None:
        """Test validating an invalid configuration."""
        file_path = create_config_file("invalid.yaml", sample_invalid_config)

        result = validate_source_config(file_path)

        assert result.is_valid is False
        assert result.source_id == "invalid-source"
        assert len(result.errors) > 0

    def test_validate_missing_source_id(self, create_config_file, sample_valid_config: dict[str, Any]) -> None:
        """Test validation fails when source_id is missing."""
        config = sample_valid_config.copy()
        del config["source_id"]
        file_path = create_config_file("no_source_id.yaml", config)

        result = validate_source_config(file_path)

        assert result.is_valid is False
        assert result.source_id is None

    def test_validate_invalid_yaml(self, temp_config_dir: Path) -> None:
        """Test validation fails for invalid YAML."""
        file_path = temp_config_dir / "broken.yaml"
        with file_path.open("w") as f:
            f.write("broken: yaml: [")

        result = validate_source_config(file_path)

        assert result.is_valid is False
        assert "Failed to parse YAML" in result.errors[0]


@pytest.mark.unit
class TestValidateSourceConfigs:
    """Tests for the validate_source_configs function."""

    def test_validate_multiple_configs(
        self,
        create_config_file,
        sample_valid_config: dict[str, Any],
        sample_scheduled_config: dict[str, Any],
    ) -> None:
        """Test validating multiple configuration files."""
        file1 = create_config_file("config1.yaml", sample_valid_config)
        file2 = create_config_file("config2.yaml", sample_scheduled_config)

        results = validate_source_configs([file1, file2])

        assert len(results) == 2
        assert all(r.is_valid for r in results)

    def test_validate_mixed_valid_invalid(
        self,
        create_config_file,
        sample_valid_config: dict[str, Any],
        sample_invalid_config: dict[str, Any],
    ) -> None:
        """Test validating a mix of valid and invalid configs."""
        file1 = create_config_file("valid.yaml", sample_valid_config)
        file2 = create_config_file("invalid.yaml", sample_invalid_config)

        results = validate_source_configs([file1, file2])

        assert len(results) == 2
        valid_count = sum(1 for r in results if r.is_valid)
        invalid_count = sum(1 for r in results if not r.is_valid)
        assert valid_count == 1
        assert invalid_count == 1


@pytest.mark.unit
class TestGetSourceConfigFiles:
    """Tests for the get_source_config_files function."""

    def test_get_files_from_directory(self, create_config_file, sample_valid_config: dict[str, Any]) -> None:
        """Test getting YAML files from a directory."""
        create_config_file("config1.yaml", sample_valid_config)
        create_config_file("config2.yaml", sample_valid_config)

        # Get the parent directory from the fixture
        from tests.unit.source_config.conftest import SAMPLE_VALID_CONFIG

        files = get_source_config_files(create_config_file("temp.yaml", SAMPLE_VALID_CONFIG).parent)

        assert len(files) == 3  # Including temp.yaml

    def test_get_files_empty_directory(self, temp_config_dir: Path) -> None:
        """Test getting files from an empty directory."""
        files = get_source_config_files(temp_config_dir)
        assert len(files) == 0

    def test_get_files_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test getting files from a nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        files = get_source_config_files(nonexistent)
        assert len(files) == 0

    def test_get_files_ignores_non_yaml(self, temp_config_dir: Path, sample_valid_config: dict[str, Any]) -> None:
        """Test that non-YAML files are ignored."""
        import yaml

        # Create YAML file
        yaml_file = temp_config_dir / "config.yaml"
        with yaml_file.open("w") as f:
            yaml.dump(sample_valid_config, f)

        # Create non-YAML file
        txt_file = temp_config_dir / "readme.txt"
        txt_file.write_text("This is not YAML")

        files = get_source_config_files(temp_config_dir)

        assert len(files) == 1
        assert files[0].suffix == ".yaml"
