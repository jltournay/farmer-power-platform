"""Test configuration for Collection Model unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_mongodb_client() -> MagicMock:
    """Mock MongoDB client."""
    client = MagicMock()
    client.admin.command = AsyncMock(return_value={"ok": 1})
    return client


@pytest.fixture
def mock_database() -> MagicMock:
    """Mock MongoDB database."""
    db = MagicMock()
    db.create_index = AsyncMock()
    return db
