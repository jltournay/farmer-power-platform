"""Unit tests for the CLI module."""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

# Add source-config src to path
sys.path.insert(0, str(Path(__file__).parents[3] / "scripts" / "source-config" / "src"))
# Add fp-common to path
sys.path.insert(0, str(Path(__file__).parents[3] / "libs" / "fp-common"))

from fp_source_config.cli import app

runner = CliRunner()


@pytest.mark.unit
class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_valid_config(self, create_config_file, sample_valid_config: dict[str, Any]) -> None:
        """Test validating a valid configuration."""
        file_path = create_config_file("valid.yaml", sample_valid_config)

        with patch("fp_source_config.cli.get_settings") as mock_settings:
            mock_settings.return_value.config_dir = str(file_path.parent)

            result = runner.invoke(app, ["validate", "-f", str(file_path)])

        assert result.exit_code == 0
        assert "Valid" in result.stdout or "valid" in result.stdout.lower()

    def test_validate_invalid_config(self, create_config_file, sample_invalid_config: dict[str, Any]) -> None:
        """Test validating an invalid configuration."""
        file_path = create_config_file("invalid.yaml", sample_invalid_config)

        result = runner.invoke(app, ["validate", "-f", str(file_path)])

        assert result.exit_code == 1

    def test_validate_file_not_found(self, temp_config_dir: Path) -> None:
        """Test validating a nonexistent file."""
        nonexistent = temp_config_dir / "nonexistent.yaml"

        result = runner.invoke(app, ["validate", "-f", str(nonexistent)])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_validate_all_configs(self, create_config_file, sample_valid_config: dict[str, Any]) -> None:
        """Test validating all configs in directory."""
        file1 = create_config_file("config1.yaml", sample_valid_config)
        config2 = sample_valid_config.copy()
        config2["source_id"] = "test-source-2"
        create_config_file("config2.yaml", config2)

        with patch("fp_source_config.cli.get_settings") as mock_settings:
            mock_settings.return_value.config_dir = str(file1.parent)

            result = runner.invoke(app, ["validate"])

        assert result.exit_code == 0


@pytest.mark.unit
class TestDeployCommand:
    """Tests for the deploy command."""

    def test_deploy_invalid_environment(self, create_config_file, sample_valid_config: dict[str, Any]) -> None:
        """Test deploy with invalid environment."""
        file_path = create_config_file("valid.yaml", sample_valid_config)

        with patch("fp_source_config.cli.get_settings") as mock_settings:
            mock_settings.return_value.config_dir = str(file_path.parent)

            result = runner.invoke(app, ["deploy", "--env", "invalid", "-f", str(file_path)])

        assert result.exit_code != 0

    def test_deploy_dry_run(
        self,
        create_config_file,
        sample_valid_config: dict[str, Any],
        mock_mongodb_client,
    ) -> None:
        """Test deploy with dry run."""
        file_path = create_config_file("valid.yaml", sample_valid_config)

        with (
            patch("fp_source_config.cli.get_settings") as mock_settings,
            patch("fp_source_config.cli.SourceConfigDeployer") as mock_deployer_class,
            patch("fp_source_config.cli.load_schemas_for_configs") as mock_load_schemas,
        ):
            mock_settings.return_value.config_dir = str(file_path.parent)
            mock_settings.return_value.schemas_dir = str(file_path.parent)
            mock_load_schemas.return_value = []  # No schemas to deploy

            mock_deployer = AsyncMock()
            mock_deployer.connect = AsyncMock()
            mock_deployer.disconnect = AsyncMock()
            mock_deployer.validate_schema_references = AsyncMock(return_value=[])
            mock_deployer.deploy = AsyncMock(
                return_value=[MagicMock(source_id="test-source", action="created", version=1)]
            )
            mock_deployer_class.return_value = mock_deployer

            result = runner.invoke(
                app,
                ["deploy", "--env", "dev", "-f", str(file_path), "--dry-run"],
            )

        assert result.exit_code == 0
        mock_deployer.deploy.assert_called_once()

    def test_deploy_file_not_found(self, temp_config_dir: Path) -> None:
        """Test deploy with nonexistent file."""
        nonexistent = temp_config_dir / "nonexistent.yaml"

        result = runner.invoke(app, ["deploy", "--env", "dev", "-f", str(nonexistent)])

        assert result.exit_code == 1


@pytest.mark.unit
class TestListCommand:
    """Tests for the list command."""

    def test_list_invalid_environment(self) -> None:
        """Test list with invalid environment."""
        result = runner.invoke(app, ["list", "--env", "invalid"])
        assert result.exit_code != 0

    def test_list_empty(self, mock_mongodb_client) -> None:
        """Test listing when no configs deployed."""
        with patch("fp_source_config.cli.SourceConfigDeployer") as mock_deployer_class:
            mock_deployer = AsyncMock()
            mock_deployer.connect = AsyncMock()
            mock_deployer.disconnect = AsyncMock()
            mock_deployer.list_configs = AsyncMock(return_value=[])
            mock_deployer_class.return_value = mock_deployer

            result = runner.invoke(app, ["list", "--env", "dev"])

        assert result.exit_code == 0
        assert "No configurations" in result.stdout


@pytest.mark.unit
class TestDiffCommand:
    """Tests for the diff command."""

    def test_diff_invalid_environment(self, create_config_file, sample_valid_config: dict[str, Any]) -> None:
        """Test diff with invalid environment."""
        file_path = create_config_file("valid.yaml", sample_valid_config)

        with patch("fp_source_config.cli.get_settings") as mock_settings:
            mock_settings.return_value.config_dir = str(file_path.parent)

            result = runner.invoke(app, ["diff", "--env", "invalid"])

        assert result.exit_code != 0

    def test_diff_no_local_configs(self, temp_config_dir: Path) -> None:
        """Test diff with no local configs."""
        with patch("fp_source_config.cli.get_settings") as mock_settings:
            mock_settings.return_value.config_dir = str(temp_config_dir)

            result = runner.invoke(app, ["diff", "--env", "dev"])

        assert result.exit_code == 0
        assert "No YAML files" in result.stdout


@pytest.mark.unit
class TestHistoryCommand:
    """Tests for the history command."""

    def test_history_invalid_environment(self) -> None:
        """Test history with invalid environment."""
        result = runner.invoke(app, ["history", "--env", "invalid", "--source", "test"])
        assert result.exit_code != 0

    def test_history_empty(self, mock_mongodb_client) -> None:
        """Test history when no history exists."""
        with patch("fp_source_config.cli.SourceConfigDeployer") as mock_deployer_class:
            mock_deployer = AsyncMock()
            mock_deployer.connect = AsyncMock()
            mock_deployer.disconnect = AsyncMock()
            mock_deployer.get_history = AsyncMock(return_value=[])
            mock_deployer_class.return_value = mock_deployer

            result = runner.invoke(app, ["history", "--env", "dev", "--source", "test"])

        assert result.exit_code == 0
        assert "No history" in result.stdout


@pytest.mark.unit
class TestRollbackCommand:
    """Tests for the rollback command."""

    def test_rollback_invalid_environment(self) -> None:
        """Test rollback with invalid environment."""
        result = runner.invoke(
            app,
            [
                "rollback",
                "--env",
                "invalid",
                "--source",
                "test",
                "--version",
                "1",
                "--force",
            ],
        )
        assert result.exit_code != 0

    def test_rollback_cancelled(self) -> None:
        """Test rollback cancelled by user."""
        result = runner.invoke(
            app,
            [
                "rollback",
                "--env",
                "dev",
                "--source",
                "test",
                "--version",
                "1",
            ],
            input="n\n",  # User says no to confirmation
        )
        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()

    def test_rollback_with_force(self, mock_mongodb_client) -> None:
        """Test rollback with force flag."""
        with patch("fp_source_config.cli.SourceConfigDeployer") as mock_deployer_class:
            mock_deployer = AsyncMock()
            mock_deployer.connect = AsyncMock()
            mock_deployer.disconnect = AsyncMock()
            mock_deployer.rollback = AsyncMock(
                return_value=MagicMock(
                    source_id="test",
                    action="updated",
                    version=2,
                    message="Rolled back to version 1",
                )
            )
            mock_deployer_class.return_value = mock_deployer

            result = runner.invoke(
                app,
                [
                    "rollback",
                    "--env",
                    "dev",
                    "--source",
                    "test",
                    "--version",
                    "1",
                    "--force",
                ],
            )

        assert result.exit_code == 0
        assert "Successfully" in result.stdout

    def test_rollback_version_not_found(self, mock_mongodb_client) -> None:
        """Test rollback when version not found."""
        with patch("fp_source_config.cli.SourceConfigDeployer") as mock_deployer_class:
            mock_deployer = AsyncMock()
            mock_deployer.connect = AsyncMock()
            mock_deployer.disconnect = AsyncMock()
            mock_deployer.rollback = AsyncMock(return_value=None)
            mock_deployer_class.return_value = mock_deployer

            result = runner.invoke(
                app,
                [
                    "rollback",
                    "--env",
                    "dev",
                    "--source",
                    "test",
                    "--version",
                    "999",
                    "--force",
                ],
            )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
