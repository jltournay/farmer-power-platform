"""Unit tests for agent config MongoDB client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fp_agent_config.client import AgentConfigClient, PromoteResult, RollbackResult
from fp_agent_config.models import agent_config_adapter


class TestAgentConfigClient:
    """Tests for AgentConfigClient class."""

    @pytest.fixture
    def client(self, mock_settings):
        """Create a client instance with mock settings."""
        return AgentConfigClient(mock_settings, "dev")

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self, client):
        """Test client connect and disconnect."""
        with patch("fp_agent_config.client.AsyncIOMotorClient") as mock_motor:
            mock_instance = MagicMock()
            mock_motor.return_value = mock_instance

            await client.connect()

            mock_motor.assert_called_once()
            assert client._client is not None

            await client.disconnect()
            mock_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_config(self, client, sample_extractor_config):
        """Test creating a new agent config."""
        with patch("fp_agent_config.client.AsyncIOMotorClient") as mock_motor:
            mock_instance = MagicMock()
            mock_db = MagicMock()
            mock_collection = AsyncMock()

            mock_motor.return_value = mock_instance
            mock_instance.__getitem__ = MagicMock(return_value=mock_db)
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)

            mock_collection.insert_one = AsyncMock()

            await client.connect()

            config = agent_config_adapter.validate_python(sample_extractor_config)
            result = await client.create(config)

            mock_collection.insert_one.assert_called_once()
            assert result.agent_id == config.agent_id

    @pytest.mark.asyncio
    async def test_get_active(self, client, sample_extractor_config):
        """Test getting active config."""
        with patch("fp_agent_config.client.AsyncIOMotorClient") as mock_motor:
            mock_instance = MagicMock()
            mock_db = MagicMock()
            mock_collection = AsyncMock()

            mock_motor.return_value = mock_instance
            mock_instance.__getitem__ = MagicMock(return_value=mock_db)
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)

            mock_collection.find_one = AsyncMock(return_value=sample_extractor_config)

            await client.connect()

            result = await client.get_active("qc-event-extractor")

            assert result is not None
            assert result.agent_id == "qc-event-extractor"
            mock_collection.find_one.assert_called_once_with(
                {
                    "agent_id": "qc-event-extractor",
                    "status": "active",
                }
            )

    @pytest.mark.asyncio
    async def test_get_active_not_found(self, client):
        """Test getting active config when not found."""
        with patch("fp_agent_config.client.AsyncIOMotorClient") as mock_motor:
            mock_instance = MagicMock()
            mock_db = MagicMock()
            mock_collection = AsyncMock()

            mock_motor.return_value = mock_instance
            mock_instance.__getitem__ = MagicMock(return_value=mock_db)
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)

            mock_collection.find_one = AsyncMock(return_value=None)

            await client.connect()

            result = await client.get_active("nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_by_version(self, client, sample_explorer_config):
        """Test getting config by version."""
        with patch("fp_agent_config.client.AsyncIOMotorClient") as mock_motor:
            mock_instance = MagicMock()
            mock_db = MagicMock()
            mock_collection = AsyncMock()

            mock_motor.return_value = mock_instance
            mock_instance.__getitem__ = MagicMock(return_value=mock_db)
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)

            mock_collection.find_one = AsyncMock(return_value=sample_explorer_config)

            await client.connect()

            result = await client.get_by_version("disease-diagnosis", "1.0.0")

            assert result is not None
            assert result.agent_id == "disease-diagnosis"
            assert result.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_list_configs(self, client):
        """Test listing configs with filters."""
        with patch("fp_agent_config.client.AsyncIOMotorClient") as mock_motor:
            mock_instance = MagicMock()
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_cursor = AsyncMock()

            mock_motor.return_value = mock_instance
            mock_instance.__getitem__ = MagicMock(return_value=mock_db)
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)

            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_sorted = MagicMock(return_value=mock_cursor)
            mock_collection.find = MagicMock(return_value=MagicMock(sort=mock_sorted))

            await client.connect()

            result = await client.list_configs(status="active", agent_type="explorer")

            assert result == []
            mock_collection.find.assert_called_once_with(
                {
                    "status": "active",
                    "type": "explorer",
                }
            )

    @pytest.mark.asyncio
    async def test_enable(self, client, sample_extractor_config):
        """Test enabling an agent."""
        with patch("fp_agent_config.client.AsyncIOMotorClient") as mock_motor:
            mock_instance = MagicMock()
            mock_db = MagicMock()
            mock_collection = AsyncMock()

            mock_motor.return_value = mock_instance
            mock_instance.__getitem__ = MagicMock(return_value=mock_db)
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)

            mock_collection.find_one = AsyncMock(return_value=sample_extractor_config)
            mock_collection.update_one = AsyncMock()

            await client.connect()

            success, error = await client.enable("qc-event-extractor")

            assert success is True
            assert error is None
            mock_collection.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_enable_not_found(self, client):
        """Test enabling non-existent agent."""
        with patch("fp_agent_config.client.AsyncIOMotorClient") as mock_motor:
            mock_instance = MagicMock()
            mock_db = MagicMock()
            mock_collection = AsyncMock()

            mock_motor.return_value = mock_instance
            mock_instance.__getitem__ = MagicMock(return_value=mock_db)
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)

            mock_collection.find_one = AsyncMock(return_value=None)

            await client.connect()

            success, error = await client.enable("nonexistent")

            assert success is False
            assert "no active config" in error.lower()

    @pytest.mark.asyncio
    async def test_disable(self, client, sample_extractor_config):
        """Test disabling an agent."""
        with patch("fp_agent_config.client.AsyncIOMotorClient") as mock_motor:
            mock_instance = MagicMock()
            mock_db = MagicMock()
            mock_collection = AsyncMock()

            mock_motor.return_value = mock_instance
            mock_instance.__getitem__ = MagicMock(return_value=mock_db)
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)

            mock_collection.find_one = AsyncMock(return_value=sample_extractor_config)
            mock_collection.update_one = AsyncMock()

            await client.connect()

            success, error = await client.disable("qc-event-extractor")

            assert success is True
            assert error is None


class TestVersionIncrement:
    """Tests for version increment logic."""

    @pytest.fixture
    def client(self, mock_settings):
        """Create a client instance."""
        return AgentConfigClient(mock_settings, "dev")

    def test_increment_version_standard(self, client):
        """Test standard version increment."""
        assert client._increment_version("1.0.0") == "1.0.1"
        assert client._increment_version("1.2.3") == "1.2.4"
        assert client._increment_version("0.0.9") == "0.0.10"
        assert client._increment_version("10.20.30") == "10.20.31"

    def test_increment_version_non_standard(self, client):
        """Test non-standard version format."""
        assert client._increment_version("1.0") == "1.0.1"
        assert client._increment_version("1") == "1.1"

    def test_increment_version_invalid(self, client):
        """Test invalid version format."""
        result = client._increment_version("abc")
        assert result == "abc.1"


class TestPromoteResult:
    """Tests for PromoteResult dataclass."""

    def test_success_result(self):
        """Test successful promote result."""
        result = PromoteResult(
            success=True,
            promoted_version="2.0.0",
            archived_version="1.0.0",
        )
        assert result.success is True
        assert result.promoted_version == "2.0.0"
        assert result.archived_version == "1.0.0"
        assert result.error is None

    def test_failure_result(self):
        """Test failed promote result."""
        result = PromoteResult(
            success=False,
            error="No staged config found",
        )
        assert result.success is False
        assert result.error == "No staged config found"


class TestRollbackResult:
    """Tests for RollbackResult dataclass."""

    def test_success_result(self):
        """Test successful rollback result."""
        result = RollbackResult(
            success=True,
            new_version="1.0.1",
            archived_version="2.0.0",
        )
        assert result.success is True
        assert result.new_version == "1.0.1"
        assert result.archived_version == "2.0.0"
        assert result.error is None

    def test_failure_result(self):
        """Test failed rollback result."""
        result = RollbackResult(
            success=False,
            error="Version not found",
        )
        assert result.success is False
        assert result.error == "Version not found"
