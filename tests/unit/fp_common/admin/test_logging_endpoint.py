"""Unit tests for fp_common.admin logging endpoints."""

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fp_common.admin import create_admin_router


class TestLoggingEndpoint:
    """Tests for /admin/logging endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client with admin router."""
        app = FastAPI()
        app.include_router(create_admin_router())
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def reset_loggers(self) -> None:
        """Reset logger levels after each test."""
        yield
        # Reset any loggers that were modified
        for name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(name)
            if isinstance(logger, logging.Logger):
                logger.setLevel(logging.NOTSET)

    def test_set_log_level_updates_logger(self, client: TestClient) -> None:
        """POST /admin/logging/{name}?level=DEBUG sets level."""
        response = client.post("/admin/logging/test_logger?level=DEBUG")

        assert response.status_code == 200
        data = response.json()
        assert data["logger"] == "test_logger"
        assert data["level"] == "DEBUG"
        assert data["status"] == "updated"

        # Verify logger was actually updated
        assert logging.getLogger("test_logger").level == logging.DEBUG

    def test_set_log_level_case_insensitive(self, client: TestClient) -> None:
        """POST /admin/logging accepts lowercase level."""
        response = client.post("/admin/logging/test_logger?level=debug")

        assert response.status_code == 200
        data = response.json()
        assert data["level"] == "DEBUG"  # Normalized to uppercase
        assert logging.getLogger("test_logger").level == logging.DEBUG

    def test_set_log_level_warning(self, client: TestClient) -> None:
        """POST /admin/logging/{name}?level=WARNING sets WARNING level."""
        response = client.post("/admin/logging/test_logger?level=WARNING")

        assert response.status_code == 200
        assert logging.getLogger("test_logger").level == logging.WARNING

    def test_set_log_level_error(self, client: TestClient) -> None:
        """POST /admin/logging/{name}?level=ERROR sets ERROR level."""
        response = client.post("/admin/logging/test_logger?level=ERROR")

        assert response.status_code == 200
        assert logging.getLogger("test_logger").level == logging.ERROR

    def test_set_log_level_invalid_returns_error(self, client: TestClient) -> None:
        """POST /admin/logging with invalid level returns error status."""
        response = client.post("/admin/logging/test_logger?level=INVALID")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data["status"]
        assert "INVALID" in data["status"]

    def test_reset_log_level_restores_default(self, client: TestClient) -> None:
        """DELETE /admin/logging/{name} resets level to NOTSET."""
        # First set a level
        logging.getLogger("test_logger").setLevel(logging.DEBUG)
        assert logging.getLogger("test_logger").level == logging.DEBUG

        # Now reset
        response = client.delete("/admin/logging/test_logger")

        assert response.status_code == 200
        data = response.json()
        assert data["logger"] == "test_logger"
        assert data["status"] == "reset"

        # Verify logger was reset
        assert logging.getLogger("test_logger").level == logging.NOTSET

    def test_get_log_levels_lists_configured(self, client: TestClient) -> None:
        """GET /admin/logging lists non-default levels."""
        # Set up some loggers with non-default levels
        logging.getLogger("configured_logger_1").setLevel(logging.DEBUG)
        logging.getLogger("configured_logger_2").setLevel(logging.WARNING)

        response = client.get("/admin/logging")

        assert response.status_code == 200
        data = response.json()
        assert "loggers" in data

        loggers = data["loggers"]
        assert "configured_logger_1" in loggers
        assert "configured_logger_2" in loggers
        assert loggers["configured_logger_1"] == "DEBUG"
        assert loggers["configured_logger_2"] == "WARNING"

    def test_get_log_levels_excludes_default(self, client: TestClient) -> None:
        """GET /admin/logging excludes loggers with default (NOTSET) level."""
        # Create a logger but don't set its level
        logging.getLogger("default_level_logger")

        response = client.get("/admin/logging")

        assert response.status_code == 200
        data = response.json()
        # Should not include the default level logger
        assert "default_level_logger" not in data.get("loggers", {})

    def test_set_log_level_dotted_name(self, client: TestClient) -> None:
        """POST /admin/logging handles dotted logger names."""
        response = client.post("/admin/logging/plantation_model.domain.services?level=DEBUG")

        assert response.status_code == 200
        data = response.json()
        assert data["logger"] == "plantation_model.domain.services"
        assert logging.getLogger("plantation_model.domain.services").level == (logging.DEBUG)

    def test_custom_prefix(self) -> None:
        """create_admin_router accepts custom prefix."""
        app = FastAPI()
        app.include_router(create_admin_router(prefix="/api/admin"))
        client = TestClient(app)

        # Default prefix should not work
        response = client.get("/admin/logging")
        assert response.status_code == 404

        # Custom prefix should work
        response = client.get("/api/admin/logging")
        assert response.status_code == 200
