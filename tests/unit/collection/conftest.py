"""Test configuration for Collection Model unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_motor_client() -> MagicMock:
    """Mock Motor MongoDB client (for infrastructure tests)."""
    client = MagicMock()
    client.admin.command = AsyncMock(return_value={"ok": 1})
    return client


@pytest.fixture
def mock_database() -> MagicMock:
    """Mock MongoDB database."""
    db = MagicMock()
    db.create_index = AsyncMock()
    return db


# Note: mock_mongodb_client is inherited from tests/conftest.py
# and provides MockMongoClient with proper async collection methods
