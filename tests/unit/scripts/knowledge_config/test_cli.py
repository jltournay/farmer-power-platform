"""Tests for fp_knowledge.cli module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fp_knowledge.cli import (
    _status_style,
    _validate_environment,
    app,
)
from fp_knowledge.models import (
    ChunkResult,
    DocumentStatus,
    RagDocument,
)
from typer.testing import CliRunner

runner = CliRunner()


class TestValidateEnvironment:
    """Tests for _validate_environment helper."""

    def test_valid_dev(self) -> None:
        """Test valid dev environment."""
        assert _validate_environment("dev") == "dev"

    def test_valid_staging(self) -> None:
        """Test valid staging environment."""
        assert _validate_environment("staging") == "staging"

    def test_valid_prod(self) -> None:
        """Test valid prod environment."""
        assert _validate_environment("prod") == "prod"

    def test_invalid_environment(self) -> None:
        """Test invalid environment raises error."""
        from typer import BadParameter

        with pytest.raises(BadParameter):
            _validate_environment("invalid")


class TestStatusStyle:
    """Tests for _status_style helper."""

    def test_active_status(self) -> None:
        """Test active status style."""
        result = _status_style(DocumentStatus.ACTIVE)
        assert "green" in result
        assert "active" in result

    def test_staged_status(self) -> None:
        """Test staged status style."""
        result = _status_style(DocumentStatus.STAGED)
        assert "yellow" in result
        assert "staged" in result

    def test_draft_status(self) -> None:
        """Test draft status style."""
        result = _status_style(DocumentStatus.DRAFT)
        assert "dim" in result
        assert "draft" in result

    def test_archived_status(self) -> None:
        """Test archived status style."""
        result = _status_style(DocumentStatus.ARCHIVED)
        assert "dim" in result
        assert "archived" in result

    def test_string_status(self) -> None:
        """Test with string status value."""
        result = _status_style("active")
        assert "green" in result


class TestValidateCommand:
    """Tests for the validate CLI command."""

    def test_validate_valid_file(self, sample_yaml_file: Path) -> None:
        """Test validating a valid YAML file."""
        result = runner.invoke(app, ["validate", "-f", str(sample_yaml_file)])

        assert result.exit_code == 0
        assert "Valid" in result.output

    def test_validate_file_not_found(self) -> None:
        """Test validating a non-existent file."""
        result = runner.invoke(app, ["validate", "-f", "/nonexistent/file.yaml"])

        assert result.exit_code == 1
        assert "Error" in result.output or "not found" in result.output.lower()

    def test_validate_invalid_file(self, invalid_yaml_file: Path) -> None:
        """Test validating an invalid YAML file."""
        result = runner.invoke(app, ["validate", "-f", str(invalid_yaml_file)])

        assert result.exit_code == 1

    def test_validate_verbose(self, sample_yaml_file: Path) -> None:
        """Test validate with verbose flag."""
        result = runner.invoke(app, ["validate", "-f", str(sample_yaml_file), "--verbose"])

        assert result.exit_code == 0
        assert "document_id" in result.output

    def test_validate_quiet(self, sample_yaml_file: Path) -> None:
        """Test validate with quiet flag."""
        result = runner.invoke(app, ["validate", "-f", str(sample_yaml_file), "--quiet"])

        assert result.exit_code == 0


class TestDeployCommand:
    """Tests for the deploy CLI command."""

    def test_deploy_file_not_found(self) -> None:
        """Test deploying a non-existent file."""
        result = runner.invoke(
            app,
            ["deploy", "-f", "/nonexistent/file.yaml", "--env", "dev"],
        )

        assert result.exit_code == 1

    def test_deploy_dry_run(self, sample_yaml_file: Path) -> None:
        """Test deploy with dry-run flag."""
        result = runner.invoke(
            app,
            ["deploy", "-f", str(sample_yaml_file), "--env", "dev", "--dry-run"],
        )

        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "Would deploy" in result.output

    def test_deploy_invalid_environment(self, sample_yaml_file: Path) -> None:
        """Test deploy with invalid environment."""
        result = runner.invoke(
            app,
            ["deploy", "-f", str(sample_yaml_file), "--env", "invalid"],
        )

        assert result.exit_code != 0


class TestListCommand:
    """Tests for the list CLI command."""

    @patch("fp_knowledge.cli.get_settings")
    @patch("fp_knowledge.cli.KnowledgeClient")
    def test_list_empty(
        self,
        mock_client_class: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test list when no documents found."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_documents = AsyncMock(return_value=([], 0))
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["list", "--env", "dev"])

        assert result.exit_code == 0
        assert "No documents" in result.output

    @patch("fp_knowledge.cli.get_settings")
    @patch("fp_knowledge.cli.KnowledgeClient")
    def test_list_with_documents(
        self,
        mock_client_class: MagicMock,
        mock_settings: MagicMock,
        sample_document: RagDocument,
    ) -> None:
        """Test list with documents returned."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_documents = AsyncMock(return_value=([sample_document], 1))
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["list", "--env", "dev"])

        assert result.exit_code == 0
        # Document ID may be truncated in table display
        assert "blister-blight" in result.output

    def test_list_invalid_domain(self) -> None:
        """Test list with invalid domain filter."""
        result = runner.invoke(
            app,
            ["list", "--env", "dev", "--domain", "invalid_domain"],
        )

        assert result.exit_code == 1
        assert "Invalid domain" in result.output

    def test_list_invalid_status(self) -> None:
        """Test list with invalid status filter."""
        result = runner.invoke(
            app,
            ["list", "--env", "dev", "--status", "invalid_status"],
        )

        assert result.exit_code == 1
        assert "Invalid status" in result.output


class TestGetCommand:
    """Tests for the get CLI command."""

    @patch("fp_knowledge.cli.get_settings")
    @patch("fp_knowledge.cli.KnowledgeClient")
    def test_get_not_found(
        self,
        mock_client_class: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test get when document not found."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.get_by_id = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            ["get", "--document-id", "nonexistent", "--env", "dev"],
        )

        assert result.exit_code == 1
        # Error message says "no active document found"
        assert "no active document found" in result.output.lower()

    @patch("fp_knowledge.cli.get_settings")
    @patch("fp_knowledge.cli.KnowledgeClient")
    def test_get_found(
        self,
        mock_client_class: MagicMock,
        mock_settings: MagicMock,
        sample_document: RagDocument,
    ) -> None:
        """Test get when document is found."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.get_by_id = AsyncMock(return_value=sample_document)
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            ["get", "--document-id", "blister-blight-guide", "--env", "dev"],
        )

        assert result.exit_code == 0


class TestVersionsCommand:
    """Tests for the versions CLI command."""

    @patch("fp_knowledge.cli.get_settings")
    @patch("fp_knowledge.cli.KnowledgeClient")
    def test_versions_empty(
        self,
        mock_client_class: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test versions when no versions found."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_versions = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            ["versions", "--document-id", "nonexistent", "--env", "dev"],
        )

        assert result.exit_code == 0
        assert "No versions" in result.output

    @patch("fp_knowledge.cli.get_settings")
    @patch("fp_knowledge.cli.KnowledgeClient")
    def test_versions_found(
        self,
        mock_client_class: MagicMock,
        mock_settings: MagicMock,
        sample_document: RagDocument,
    ) -> None:
        """Test versions when versions are found."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_versions = AsyncMock(return_value=[sample_document])
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            ["versions", "--document-id", "blister-blight-guide", "--env", "dev"],
        )

        assert result.exit_code == 0
        assert "1" in result.output  # Version 1


class TestPromoteCommand:
    """Tests for the promote CLI command."""

    @patch("fp_knowledge.cli.get_settings")
    @patch("fp_knowledge.cli.KnowledgeClient")
    def test_promote_no_staged(
        self,
        mock_client_class: MagicMock,
        mock_settings: MagicMock,
        sample_document: RagDocument,
    ) -> None:
        """Test promote when no staged version exists."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        # Return only draft version, no staged
        mock_client.list_versions = AsyncMock(return_value=[sample_document])
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            ["promote", "--document-id", "blister-blight-guide", "--env", "dev"],
        )

        assert result.exit_code == 1
        assert "No staged" in result.output

    @patch("fp_knowledge.cli.get_settings")
    @patch("fp_knowledge.cli.KnowledgeClient")
    def test_promote_success(
        self,
        mock_client_class: MagicMock,
        mock_settings: MagicMock,
        sample_staged_document: RagDocument,
        sample_active_document: RagDocument,
    ) -> None:
        """Test successful promotion."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.list_versions = AsyncMock(return_value=[sample_staged_document])
        mock_client.activate = AsyncMock(return_value=sample_active_document)
        mock_client.chunk = AsyncMock(
            return_value=ChunkResult(
                chunks_created=10,
                total_char_count=5000,
                total_word_count=1000,
            )
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            ["promote", "--document-id", "blister-blight-guide", "--env", "dev"],
        )

        assert result.exit_code == 0
        assert "Promoted" in result.output


class TestRollbackCommand:
    """Tests for the rollback CLI command."""

    @patch("fp_knowledge.cli.get_settings")
    @patch("fp_knowledge.cli.KnowledgeClient")
    def test_rollback_success(
        self,
        mock_client_class: MagicMock,
        mock_settings: MagicMock,
        sample_document: RagDocument,
    ) -> None:
        """Test successful rollback."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.rollback = AsyncMock(return_value=sample_document)
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "rollback",
                "--document-id",
                "blister-blight-guide",
                "--to-version",
                "1",
                "--env",
                "dev",
            ],
        )

        assert result.exit_code == 0
        assert "Rolled back" in result.output
