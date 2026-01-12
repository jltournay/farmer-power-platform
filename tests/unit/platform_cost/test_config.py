"""Unit tests for platform-cost configuration.

Story 13.2: Platform Cost Service scaffold.
"""

import os
from unittest import mock

import pytest


class TestSettings:
    """Test cases for Settings class."""

    def test_default_settings(self):
        """Test default configuration values."""
        # Import Settings class (not the global instance)
        from platform_cost.config import Settings

        # Create fresh instance with cleared environment
        with mock.patch.dict(os.environ, {}, clear=True):
            settings = Settings()

            assert settings.service_name == "platform-cost"
            assert settings.service_version == "0.1.0"
            assert settings.environment == "development"
            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
            assert settings.grpc_port == 50054
            assert settings.mongodb_uri == "mongodb://localhost:27017"
            assert settings.mongodb_database == "platform_cost"
            assert settings.dapr_pubsub_name == "pubsub"
            assert settings.cost_event_topic == "platform.cost.recorded"
            assert settings.budget_daily_threshold_usd == 10.0
            assert settings.budget_monthly_threshold_usd == 100.0
            assert settings.cost_event_retention_days == 90
            assert settings.otel_enabled is True

    def test_environment_variable_override(self):
        """Test configuration from environment variables."""
        from platform_cost.config import Settings

        env_vars = {
            "PLATFORM_COST_SERVICE_NAME": "test-platform-cost",
            "PLATFORM_COST_PORT": "9000",
            "PLATFORM_COST_GRPC_PORT": "50099",
            "PLATFORM_COST_MONGODB_URI": "mongodb://testhost:27017",
            "PLATFORM_COST_MONGODB_DATABASE": "test_costs",
            "PLATFORM_COST_BUDGET_DAILY_THRESHOLD_USD": "50.0",
            "PLATFORM_COST_BUDGET_MONTHLY_THRESHOLD_USD": "500.0",
            "PLATFORM_COST_COST_EVENT_RETENTION_DAYS": "30",
            "PLATFORM_COST_OTEL_ENABLED": "false",
        }

        with mock.patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            assert settings.service_name == "test-platform-cost"
            assert settings.port == 9000
            assert settings.grpc_port == 50099
            assert settings.mongodb_uri == "mongodb://testhost:27017"
            assert settings.mongodb_database == "test_costs"
            assert settings.budget_daily_threshold_usd == 50.0
            assert settings.budget_monthly_threshold_usd == 500.0
            assert settings.cost_event_retention_days == 30
            assert settings.otel_enabled is False

    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case-insensitive."""
        from platform_cost.config import Settings

        env_vars = {
            "platform_cost_port": "8888",  # lowercase
        }

        with mock.patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            assert settings.port == 8888

    def test_dapr_settings(self):
        """Test DAPR-related configuration."""
        from platform_cost.config import Settings

        env_vars = {
            "PLATFORM_COST_DAPR_HOST": "dapr-sidecar",
            "PLATFORM_COST_DAPR_HTTP_PORT": "3600",
            "PLATFORM_COST_DAPR_GRPC_PORT": "50002",
            "PLATFORM_COST_DAPR_PUBSUB_NAME": "custom-pubsub",
            "PLATFORM_COST_COST_EVENT_TOPIC": "custom.cost.topic",
        }

        with mock.patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            assert settings.dapr_host == "dapr-sidecar"
            assert settings.dapr_http_port == 3600
            assert settings.dapr_grpc_port == 50002
            assert settings.dapr_pubsub_name == "custom-pubsub"
            assert settings.cost_event_topic == "custom.cost.topic"

    def test_mongodb_pool_settings(self):
        """Test MongoDB connection pool settings."""
        from platform_cost.config import Settings

        env_vars = {
            "PLATFORM_COST_MONGODB_MIN_POOL_SIZE": "10",
            "PLATFORM_COST_MONGODB_MAX_POOL_SIZE": "100",
        }

        with mock.patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            assert settings.mongodb_min_pool_size == 10
            assert settings.mongodb_max_pool_size == 100
