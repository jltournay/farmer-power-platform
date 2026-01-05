"""Unit tests for fp-prompt-config CLI commands."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fp_prompt_config.cli import app
from fp_prompt_config.client import PromoteResult, RollbackResult
from fp_prompt_config.models import PromptStatus
from typer.testing import CliRunner

from .conftest import make_prompt

runner = CliRunner()


def get_all_output(result) -> str:
    """Get combined stdout and stderr from result.

    CliRunner mixes stderr into stdout by default.
    The 'output' attribute contains the combined output.
    """
    return result.output or ""


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_valid_file(self, valid_prompt_yaml: Path) -> None:
        """Test validate command with a valid YAML file."""
        result = runner.invoke(app, ["validate", "-f", str(valid_prompt_yaml)])

        assert result.exit_code == 0
        assert "Valid" in result.stdout

    def test_validate_missing_file(self) -> None:
        """Test validate command with a non-existent file."""
        result = runner.invoke(app, ["validate", "-f", "/nonexistent/file.yaml"])

        assert result.exit_code == 1
        assert "Error:" in get_all_output(result)

    def test_validate_invalid_file(self, invalid_prompt_missing_fields_yaml: Path) -> None:
        """Test validate command with an invalid YAML file."""
        result = runner.invoke(app, ["validate", "-f", str(invalid_prompt_missing_fields_yaml)])

        assert result.exit_code == 1
        assert "Error:" in get_all_output(result)

    def test_validate_verbose_output(self, valid_prompt_yaml: Path) -> None:
        """Test validate command with verbose flag."""
        result = runner.invoke(app, ["validate", "-f", str(valid_prompt_yaml), "--verbose"])

        assert result.exit_code == 0
        assert "prompt_id:" in result.stdout
        assert "disease-diagnosis" in result.stdout


class TestDeployCommand:
    """Tests for the deploy command."""

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_deploy_valid_file(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
        sample_prompt_yaml: Path,
    ) -> None:
        """Test deploy command with a valid YAML file."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.validate_agent_reference = AsyncMock(return_value=None)
        mock_client.get_by_version = AsyncMock(return_value=None)
        mock_client.create = AsyncMock()
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["deploy", "-f", str(sample_prompt_yaml), "--env", "dev"])

        assert result.exit_code == 0
        assert "Deployed" in result.stdout

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_deploy_dry_run(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
        sample_prompt_yaml: Path,
    ) -> None:
        """Test deploy command with dry-run flag."""
        result = runner.invoke(app, ["deploy", "-f", str(sample_prompt_yaml), "--env", "dev", "--dry-run"])

        assert result.exit_code == 0
        assert "Dry run" in result.stdout
        assert "Would deploy" in result.stdout

    def test_deploy_invalid_env(self, sample_prompt_yaml: Path) -> None:
        """Test deploy command with invalid environment."""
        result = runner.invoke(app, ["deploy", "-f", str(sample_prompt_yaml), "--env", "invalid"])

        assert result.exit_code != 0

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_deploy_agent_validation_fails(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
        sample_staged_prompt_yaml: Path,
    ) -> None:
        """Test deploy command when agent validation fails."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.validate_agent_reference = AsyncMock(return_value="agent_id 'test-agent' does not exist")
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["deploy", "-f", str(sample_staged_prompt_yaml), "--env", "dev"])

        assert result.exit_code == 1
        assert "Error:" in get_all_output(result)

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_deploy_version_exists(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
        sample_prompt_yaml: Path,
    ) -> None:
        """Test deploy command when version already exists."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.validate_agent_reference = AsyncMock(return_value=None)
        mock_client.get_by_version = AsyncMock(return_value=make_prompt())
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["deploy", "-f", str(sample_prompt_yaml), "--env", "dev"])

        assert result.exit_code == 1
        assert "already exists" in get_all_output(result)


class TestListCommand:
    """Tests for the list command."""

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_list_empty(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        """Test list command with no prompts."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["list", "--env", "dev"])

        assert result.exit_code == 0
        assert "No prompts found" in result.stdout

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_list_with_prompts(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        """Test list command with prompts."""
        prompts = [
            make_prompt(status=PromptStatus.ACTIVE),
            make_prompt(prompt_id="other-prompt", version="2.0.0"),
        ]
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_prompts = AsyncMock(return_value=prompts)
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["list", "--env", "dev"])

        assert result.exit_code == 0
        assert "test-prompt" in result.stdout
        assert "other-prompt" in result.stdout

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_list_with_status_filter(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        """Test list command with status filter."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_prompts = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["list", "--env", "dev", "--status", "active"])

        assert result.exit_code == 0
        mock_client.list_prompts.assert_called_once_with(status="active", agent_id=None)


class TestGetCommand:
    """Tests for the get command."""

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_get_active_prompt(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        """Test get command returns active prompt."""
        prompt = make_prompt(status=PromptStatus.ACTIVE)
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.get_active = AsyncMock(return_value=prompt)
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["get", "--prompt-id", "test-prompt", "--env", "dev"])

        assert result.exit_code == 0
        assert "test-prompt" in result.stdout

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_get_specific_version(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        """Test get command with specific version."""
        prompt = make_prompt(version="2.0.0")
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.get_by_version = AsyncMock(return_value=prompt)
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            ["get", "--prompt-id", "test-prompt", "--env", "dev", "--version", "2.0.0"],
        )

        assert result.exit_code == 0
        mock_client.get_by_version.assert_called_once_with("test-prompt", "2.0.0")

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_get_not_found(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        """Test get command when prompt not found."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.get_active = AsyncMock(return_value=None)
        mock_client.get_latest_staged = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["get", "--prompt-id", "nonexistent", "--env", "dev"])

        assert result.exit_code == 1
        assert "Error:" in get_all_output(result)

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_get_with_output_file(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test get command with --output flag writes to file."""
        prompt = make_prompt(status=PromptStatus.ACTIVE)
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.get_active = AsyncMock(return_value=prompt)
        mock_client_class.return_value = mock_client

        output_file = tmp_path / "output.yaml"
        result = runner.invoke(
            app,
            ["get", "--prompt-id", "test-prompt", "--env", "dev", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        assert "Saved to" in result.stdout
        assert output_file.exists()
        content = output_file.read_text()
        assert "test-prompt" in content


class TestStageCommand:
    """Tests for the stage command."""

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_stage_valid_file(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
        sample_prompt_yaml: Path,
    ) -> None:
        """Test stage command with a valid YAML file."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.validate_agent_reference = AsyncMock(return_value=None)
        mock_client.get_by_version = AsyncMock(return_value=None)
        mock_client.create = AsyncMock()
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["stage", "-f", str(sample_prompt_yaml), "--env", "dev"])

        assert result.exit_code == 0
        assert "Staged" in result.stdout


class TestPromoteCommand:
    """Tests for the promote command."""

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_promote_success(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        """Test promote command succeeds."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.promote = AsyncMock(
            return_value=PromoteResult(success=True, promoted_version="2.0.0", archived_version="1.0.0")
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["promote", "--prompt-id", "test-prompt", "--env", "dev"])

        assert result.exit_code == 0
        assert "Promoted" in result.stdout

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_promote_no_staged(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        """Test promote command when no staged prompt exists."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.promote = AsyncMock(
            return_value=PromoteResult(success=False, error="No staged prompt found for 'test-prompt'")
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["promote", "--prompt-id", "test-prompt", "--env", "dev"])

        assert result.exit_code == 1
        assert "Error:" in get_all_output(result)


class TestRollbackCommand:
    """Tests for the rollback command."""

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_rollback_success(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        """Test rollback command succeeds."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.rollback = AsyncMock(
            return_value=RollbackResult(success=True, new_version="1.0.1", archived_version="2.0.0")
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "rollback",
                "--prompt-id",
                "test-prompt",
                "--to-version",
                "1.0.0",
                "--env",
                "dev",
            ],
        )

        assert result.exit_code == 0
        assert "Rolled back" in result.stdout

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_rollback_version_not_found(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        """Test rollback command when target version not found."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.rollback = AsyncMock(
            return_value=RollbackResult(success=False, error="Version 9.9.9 not found for 'test-prompt'")
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "rollback",
                "--prompt-id",
                "test-prompt",
                "--to-version",
                "9.9.9",
                "--env",
                "dev",
            ],
        )

        assert result.exit_code == 1
        assert "Error:" in get_all_output(result)


class TestVersionsCommand:
    """Tests for the versions command."""

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_versions_list(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        """Test versions command lists all versions."""
        prompts = [
            make_prompt(version="2.0.0", status=PromptStatus.ACTIVE),
            make_prompt(version="1.0.0", status=PromptStatus.ARCHIVED),
        ]
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_versions = AsyncMock(return_value=prompts)
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["versions", "--prompt-id", "test-prompt", "--env", "dev"])

        assert result.exit_code == 0
        assert "2.0.0" in result.stdout
        assert "1.0.0" in result.stdout

    @patch("fp_prompt_config.cli.PromptClient")
    @patch("fp_prompt_config.cli.get_settings")
    def test_versions_empty(
        self,
        mock_get_settings: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        """Test versions command with no versions."""
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_versions = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["versions", "--prompt-id", "nonexistent", "--env", "dev"])

        assert result.exit_code == 0
        assert "No versions found" in result.stdout
