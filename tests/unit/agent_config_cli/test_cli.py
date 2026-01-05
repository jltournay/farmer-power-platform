"""Unit tests for agent config CLI commands."""

import re
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fp_agent_config.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text for assertion comparisons."""
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_pattern.sub("", text)


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_valid_extractor(self, fixtures_dir: Path):
        """Test validate command with valid extractor config."""
        file_path = fixtures_dir / "extractor_valid.yaml"
        result = runner.invoke(app, ["validate", "-f", str(file_path)])

        assert result.exit_code == 0
        assert "Valid" in result.stdout

    def test_validate_valid_explorer(self, fixtures_dir: Path):
        """Test validate command with valid explorer config."""
        file_path = fixtures_dir / "explorer_valid.yaml"
        result = runner.invoke(app, ["validate", "-f", str(file_path)])

        assert result.exit_code == 0
        assert "Valid" in result.stdout

    def test_validate_valid_generator(self, fixtures_dir: Path):
        """Test validate command with valid generator config."""
        file_path = fixtures_dir / "generator_valid.yaml"
        result = runner.invoke(app, ["validate", "-f", str(file_path)])

        assert result.exit_code == 0
        assert "Valid" in result.stdout

    def test_validate_valid_conversational(self, fixtures_dir: Path):
        """Test validate command with valid conversational config."""
        file_path = fixtures_dir / "conversational_valid.yaml"
        result = runner.invoke(app, ["validate", "-f", str(file_path)])

        assert result.exit_code == 0
        assert "Valid" in result.stdout

    def test_validate_valid_tiered_vision(self, fixtures_dir: Path):
        """Test validate command with valid tiered-vision config."""
        file_path = fixtures_dir / "tiered_vision_valid.yaml"
        result = runner.invoke(app, ["validate", "-f", str(file_path)])

        assert result.exit_code == 0
        assert "Valid" in result.stdout

    def test_validate_verbose_output(self, fixtures_dir: Path):
        """Test validate command verbose output."""
        file_path = fixtures_dir / "extractor_valid.yaml"
        result = runner.invoke(app, ["validate", "-f", str(file_path), "--verbose"])

        assert result.exit_code == 0
        assert "Valid" in result.stdout
        assert "agent_id" in result.stdout
        assert "type" in result.stdout

    def test_validate_quiet_output(self, fixtures_dir: Path):
        """Test validate command quiet output."""
        file_path = fixtures_dir / "extractor_valid.yaml"
        result = runner.invoke(app, ["validate", "-f", str(file_path), "--quiet"])

        assert result.exit_code == 0
        # Quiet mode should produce minimal output
        assert result.stdout.strip() == ""

    def test_validate_invalid_file(self, fixtures_dir: Path):
        """Test validate command with invalid config."""
        file_path = fixtures_dir / "invalid_missing_type.yaml"
        result = runner.invoke(app, ["validate", "-f", str(file_path)])

        assert result.exit_code == 1
        assert "Error" in result.stdout or "Error" in result.stderr

    def test_validate_file_not_found(self):
        """Test validate command with non-existent file."""
        result = runner.invoke(app, ["validate", "-f", "/nonexistent/file.yaml"])

        assert result.exit_code == 1


class TestDeployCommand:
    """Tests for the deploy command."""

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_deploy_dry_run(self, mock_client_class, fixtures_dir: Path):
        """Test deploy command in dry-run mode."""
        file_path = fixtures_dir / "extractor_valid.yaml"
        result = runner.invoke(app, ["deploy", "-f", str(file_path), "--env", "dev", "--dry-run"])

        assert result.exit_code == 0
        assert "Dry run" in result.stdout
        assert "qc-event-extractor" in result.stdout
        # Client should not be called in dry-run mode
        mock_client_class.assert_not_called()

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_deploy_success(self, mock_client_class, fixtures_dir: Path):
        """Test deploy command success."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.get_by_version = AsyncMock(return_value=None)
        mock_client.create = AsyncMock()
        mock_client_class.return_value = mock_client

        file_path = fixtures_dir / "extractor_valid.yaml"
        result = runner.invoke(app, ["deploy", "-f", str(file_path), "--env", "dev"])

        assert result.exit_code == 0
        assert "Deployed" in result.stdout

    def test_deploy_invalid_environment(self, fixtures_dir: Path):
        """Test deploy command with invalid environment."""
        file_path = fixtures_dir / "extractor_valid.yaml"
        result = runner.invoke(app, ["deploy", "-f", str(file_path), "--env", "invalid"])

        assert result.exit_code != 0

    def test_deploy_file_not_found(self):
        """Test deploy command with non-existent file."""
        result = runner.invoke(app, ["deploy", "-f", "/nonexistent/file.yaml", "--env", "dev"])

        assert result.exit_code == 1


class TestListCommand:
    """Tests for the list command."""

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_list_empty(self, mock_client_class):
        """Test list command with no configs."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_configs = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["list", "--env", "dev"])

        assert result.exit_code == 0
        assert "No configs found" in result.stdout

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_list_with_status_filter(self, mock_client_class):
        """Test list command with status filter."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_configs = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["list", "--env", "dev", "--status", "active"])

        assert result.exit_code == 0
        mock_client.list_configs.assert_called_once_with(status="active", agent_type=None)

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_list_with_type_filter(self, mock_client_class):
        """Test list command with type filter."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_configs = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["list", "--env", "dev", "--type", "explorer"])

        assert result.exit_code == 0
        mock_client.list_configs.assert_called_once_with(status=None, agent_type="explorer")


class TestGetCommand:
    """Tests for the get command."""

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_get_not_found(self, mock_client_class):
        """Test get command when config not found."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.get_active = AsyncMock(return_value=None)
        mock_client.get_latest_staged = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["get", "--agent-id", "nonexistent", "--env", "dev"])

        assert result.exit_code == 1
        # Error goes to stderr - check for error message about no config
        output = (result.stdout + (result.stderr or "")).lower()
        assert "no active or staged" in output or "not found" in output


class TestStageCommand:
    """Tests for the stage command."""

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_stage_success(self, mock_client_class, fixtures_dir: Path):
        """Test stage command success."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.get_by_version = AsyncMock(return_value=None)
        mock_client.create = AsyncMock()
        mock_client_class.return_value = mock_client

        file_path = fixtures_dir / "extractor_valid.yaml"
        result = runner.invoke(app, ["stage", "-f", str(file_path), "--env", "dev"])

        assert result.exit_code == 0
        assert "Staged" in result.stdout


class TestPromoteCommand:
    """Tests for the promote command."""

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_promote_not_found(self, mock_client_class):
        """Test promote command when no staged config found."""
        from fp_agent_config.client import PromoteResult

        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.promote = AsyncMock(return_value=PromoteResult(success=False, error="No staged config found"))
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["promote", "--agent-id", "test", "--env", "dev"])

        assert result.exit_code == 1


class TestRollbackCommand:
    """Tests for the rollback command."""

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_rollback_version_not_found(self, mock_client_class):
        """Test rollback command when target version not found."""
        from fp_agent_config.client import RollbackResult

        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.rollback = AsyncMock(return_value=RollbackResult(success=False, error="Version not found"))
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            ["rollback", "--agent-id", "test", "--to-version", "1.0.0", "--env", "dev"],
        )

        assert result.exit_code == 1


class TestVersionsCommand:
    """Tests for the versions command."""

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_versions_empty(self, mock_client_class):
        """Test versions command with no versions."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_versions = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["versions", "--agent-id", "test", "--env", "dev"])

        assert result.exit_code == 0
        assert "No versions found" in result.stdout


class TestEnableCommand:
    """Tests for the enable command."""

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_enable_success(self, mock_client_class):
        """Test enable command success."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.enable = AsyncMock(return_value=(True, None))
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["enable", "--agent-id", "test", "--env", "dev"])

        assert result.exit_code == 0
        assert "Enabled" in result.stdout

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_enable_not_found(self, mock_client_class):
        """Test enable command when no active config found."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.enable = AsyncMock(return_value=(False, "No active config found"))
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["enable", "--agent-id", "test", "--env", "dev"])

        assert result.exit_code == 1


class TestDisableCommand:
    """Tests for the disable command."""

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_disable_success(self, mock_client_class):
        """Test disable command success."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.disable = AsyncMock(return_value=(True, None))
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["disable", "--agent-id", "test", "--env", "dev"])

        assert result.exit_code == 0
        assert "Disabled" in result.stdout

    @patch("fp_agent_config.cli.AgentConfigClient")
    def test_disable_not_found(self, mock_client_class):
        """Test disable command when no active config found."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.disable = AsyncMock(return_value=(False, "No active config found"))
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["disable", "--agent-id", "test", "--env", "dev"])

        assert result.exit_code == 1


class TestHelpText:
    """Tests for CLI help text."""

    def test_main_help(self):
        """Test main CLI help text."""
        result = runner.invoke(app, ["--help"])
        stdout = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "fp-agent-config" in stdout or "Manage agent configurations" in stdout

    def test_validate_help(self):
        """Test validate command help text."""
        result = runner.invoke(app, ["validate", "--help"])
        stdout = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "validate" in stdout.lower()
        assert "--file" in stdout

    def test_deploy_help(self):
        """Test deploy command help text."""
        result = runner.invoke(app, ["deploy", "--help"])
        stdout = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "deploy" in stdout.lower()
        assert "--env" in stdout

    def test_list_help(self):
        """Test list command help text."""
        result = runner.invoke(app, ["list", "--help"])
        stdout = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "--status" in stdout
        assert "--type" in stdout

    def test_enable_help(self):
        """Test enable command help text."""
        result = runner.invoke(app, ["enable", "--help"])
        stdout = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "--agent-id" in stdout

    def test_disable_help(self):
        """Test disable command help text."""
        result = runner.invoke(app, ["disable", "--help"])
        stdout = strip_ansi(result.stdout)

        assert result.exit_code == 0
        assert "--agent-id" in stdout
