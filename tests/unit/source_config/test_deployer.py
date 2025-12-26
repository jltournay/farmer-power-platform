"""Unit tests for the deployer module."""

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Add source-config src to path
sys.path.insert(0, str(Path(__file__).parents[3] / "scripts" / "source-config" / "src"))
# Add fp-common to path
sys.path.insert(0, str(Path(__file__).parents[3] / "libs" / "fp-common"))

from fp_common.models.source_config import SourceConfig
from fp_source_config.deployer import (
    ConfigHistory,
    DeployedConfig,
    DeploymentAction,
    SourceConfigDeployer,
    get_current_user,
    get_git_sha,
    load_source_configs,
)


@pytest.mark.unit
class TestGetGitSha:
    """Tests for the get_git_sha function."""

    def test_get_git_sha_success(self) -> None:
        """Test getting git SHA successfully."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="abc123def456789\n", returncode=0)
            sha = get_git_sha()
            assert sha == "abc123def456"  # First 12 characters

    def test_get_git_sha_not_git_repo(self) -> None:
        """Test getting git SHA when not in a git repo."""
        with patch("subprocess.run") as mock_run:
            from subprocess import CalledProcessError

            mock_run.side_effect = CalledProcessError(128, "git")
            sha = get_git_sha()
            assert sha is None


@pytest.mark.unit
class TestGetCurrentUser:
    """Tests for the get_current_user function."""

    def test_get_current_user(self) -> None:
        """Test getting current user."""
        with patch("getpass.getuser") as mock_getuser:
            mock_getuser.return_value = "testuser"
            user = get_current_user()
            assert user == "testuser"

    def test_get_current_user_failure(self) -> None:
        """Test fallback when getuser fails."""
        with patch("getpass.getuser") as mock_getuser:
            mock_getuser.side_effect = Exception("No user")
            user = get_current_user()
            assert user == "unknown"


@pytest.mark.unit
class TestLoadSourceConfigs:
    """Tests for the load_source_configs function."""

    def test_load_configs(self, create_config_file, sample_valid_config: dict[str, Any]) -> None:
        """Test loading source configurations from files."""
        file_path = create_config_file("config.yaml", sample_valid_config)

        configs = load_source_configs([file_path])

        assert len(configs) == 1
        assert configs[0].source_id == "test-source"

    def test_load_multiple_configs(
        self,
        create_config_file,
        sample_valid_config: dict[str, Any],
        sample_scheduled_config: dict[str, Any],
    ) -> None:
        """Test loading multiple configuration files."""
        file1 = create_config_file("config1.yaml", sample_valid_config)
        file2 = create_config_file("config2.yaml", sample_scheduled_config)

        configs = load_source_configs([file1, file2])

        assert len(configs) == 2
        source_ids = [c.source_id for c in configs]
        assert "test-source" in source_ids
        assert "scheduled-source" in source_ids


@pytest.mark.unit
class TestDeploymentAction:
    """Tests for the DeploymentAction named tuple."""

    def test_deployment_action_created(self) -> None:
        """Test creating a deployment action."""
        action = DeploymentAction(
            source_id="test-source",
            action="created",
            version=1,
        )
        assert action.source_id == "test-source"
        assert action.action == "created"
        assert action.version == 1
        assert action.message is None

    def test_deployment_action_with_message(self) -> None:
        """Test deployment action with message."""
        action = DeploymentAction(
            source_id="test-source",
            action="updated",
            version=2,
            message="Rolled back to version 1",
        )
        assert action.message == "Rolled back to version 1"


@pytest.mark.unit
class TestDeployedConfig:
    """Tests for the DeployedConfig model."""

    def test_deployed_config(self) -> None:
        """Test creating a deployed config."""
        config = DeployedConfig(
            source_id="test-source",
            display_name="Test Source",
            description="A test source",
            enabled=True,
            config={"ingestion": {}},
            version=1,
            deployed_at=datetime.now(UTC),
            deployed_by="testuser",
            git_sha="abc123",
        )
        assert config.source_id == "test-source"
        assert config.version == 1


@pytest.mark.unit
class TestConfigHistory:
    """Tests for the ConfigHistory model."""

    def test_config_history(self) -> None:
        """Test creating a config history entry."""
        history = ConfigHistory(
            source_id="test-source",
            version=1,
            config={"ingestion": {}},
            deployed_at=datetime.now(UTC),
            deployed_by="testuser",
            git_sha="abc123",
        )
        assert history.source_id == "test-source"
        assert history.version == 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestSourceConfigDeployer:
    """Tests for the SourceConfigDeployer class."""

    async def test_deploy_new_config(
        self,
        mock_mongodb_client,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """Test deploying a new configuration."""
        deployer = SourceConfigDeployer("dev")
        deployer._db = mock_mongodb_client["collection_model"]

        config = SourceConfig.model_validate(sample_valid_config)
        actions = await deployer.deploy([config])

        assert len(actions) == 1
        assert actions[0].action == "created"
        assert actions[0].version == 1

    async def test_deploy_unchanged_config(
        self,
        mock_mongodb_client,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """Test deploying an unchanged configuration."""
        deployer = SourceConfigDeployer("dev")
        deployer._db = mock_mongodb_client["collection_model"]

        config = SourceConfig.model_validate(sample_valid_config)

        # First deploy
        await deployer.deploy([config])
        # Second deploy should be unchanged
        actions = await deployer.deploy([config])

        assert len(actions) == 1
        assert actions[0].action == "unchanged"

    async def test_deploy_dry_run(
        self,
        mock_mongodb_client,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """Test dry run deployment."""
        deployer = SourceConfigDeployer("dev")
        deployer._db = mock_mongodb_client["collection_model"]

        config = SourceConfig.model_validate(sample_valid_config)
        actions = await deployer.deploy([config], dry_run=True)

        assert len(actions) == 1
        assert actions[0].action == "created"

        # Verify nothing was actually written
        collection = deployer._db["source_configs"]
        count = await collection.count_documents({})
        assert count == 0

    async def test_list_configs_empty(
        self,
        mock_mongodb_client,
    ) -> None:
        """Test listing configs when empty."""
        deployer = SourceConfigDeployer("dev")
        deployer._db = mock_mongodb_client["collection_model"]

        configs = await deployer.list_configs()

        assert len(configs) == 0

    async def test_list_configs_after_deploy(
        self,
        mock_mongodb_client,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """Test listing configs after deployment."""
        deployer = SourceConfigDeployer("dev")
        deployer._db = mock_mongodb_client["collection_model"]

        config = SourceConfig.model_validate(sample_valid_config)
        await deployer.deploy([config])
        configs = await deployer.list_configs()

        assert len(configs) == 1
        assert configs[0].source_id == "test-source"

    async def test_get_config(
        self,
        mock_mongodb_client,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """Test getting a specific config."""
        deployer = SourceConfigDeployer("dev")
        deployer._db = mock_mongodb_client["collection_model"]

        config = SourceConfig.model_validate(sample_valid_config)
        await deployer.deploy([config])
        retrieved = await deployer.get_config("test-source")

        assert retrieved is not None
        assert retrieved.source_id == "test-source"

    async def test_get_config_not_found(
        self,
        mock_mongodb_client,
    ) -> None:
        """Test getting a nonexistent config."""
        deployer = SourceConfigDeployer("dev")
        deployer._db = mock_mongodb_client["collection_model"]

        retrieved = await deployer.get_config("nonexistent")

        assert retrieved is None

    async def test_get_history(
        self,
        mock_mongodb_client,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """Test getting deployment history."""
        deployer = SourceConfigDeployer("dev")
        deployer._db = mock_mongodb_client["collection_model"]

        config = SourceConfig.model_validate(sample_valid_config)
        # Deploy config
        await deployer.deploy([config])
        # Get history
        history = await deployer.get_history("test-source")

        assert len(history) == 1
        assert history[0].version == 1

    async def test_rollback(
        self,
        mock_mongodb_client,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """Test rolling back to a previous version."""
        import copy

        deployer = SourceConfigDeployer("dev")
        deployer._db = mock_mongodb_client["collection_model"]

        config = SourceConfig.model_validate(sample_valid_config)
        # Deploy initial version
        await deployer.deploy([config])

        # Modify a config field that's actually compared (not just description)
        config_v2 = copy.deepcopy(sample_valid_config)
        config_v2["storage"]["ttl_days"] = 730  # Change from 365 to 730
        config2 = SourceConfig.model_validate(config_v2)
        await deployer.deploy([config2])

        # Rollback to version 1
        action = await deployer.rollback("test-source", 1)

        assert action is not None
        assert action.action == "updated"
        assert action.version == 3  # New version after rollback
        assert action.message == "Rolled back to version 1"

    async def test_rollback_version_not_found(
        self,
        mock_mongodb_client,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """Test rollback to nonexistent version."""
        deployer = SourceConfigDeployer("dev")
        deployer._db = mock_mongodb_client["collection_model"]

        config = SourceConfig.model_validate(sample_valid_config)
        await deployer.deploy([config])
        action = await deployer.rollback("test-source", 999)

        assert action is None
