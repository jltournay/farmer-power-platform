"""Test configuration for AI Model unit tests.

Note: mock_mongodb_client is inherited from tests/conftest.py
and provides MockMongoClient with proper async collection methods.
DO NOT override mock_mongodb_client here - use a different fixture name
if you need a custom MongoDB mock.
"""

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


@pytest.fixture
def mock_settings() -> MagicMock:
    """Mock AI Model settings."""
    settings = MagicMock()
    settings.service_name = "ai-model"
    settings.service_version = "0.1.0"
    settings.environment = "test"
    settings.host = "0.0.0.0"
    settings.port = 8000
    settings.grpc_port = 50051
    settings.mongodb_uri = "mongodb://localhost:27017"
    settings.mongodb_database = "ai_model"
    settings.mongodb_min_pool_size = 5
    settings.mongodb_max_pool_size = 50
    settings.otel_enabled = False
    settings.otel_exporter_endpoint = "http://localhost:4317"
    return settings
