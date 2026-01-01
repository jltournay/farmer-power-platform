"""Unit tests for fp_common.logging.configure_logging."""

import io
import json
import logging
import sys
from unittest.mock import patch

import pytest
import structlog
from fp_common.logging import configure_logging, reset_logging


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def setup_method(self) -> None:
        """Reset logging configuration before each test."""
        reset_logging()
        # Clear all loggers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

    def teardown_method(self) -> None:
        """Reset logging configuration after each test."""
        reset_logging()

    def test_configure_logging_sets_json_renderer(self) -> None:
        """configure_logging uses JSON renderer by default."""
        configure_logging("test-service")
        logger = structlog.get_logger("test")

        # Capture stdout
        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            logger.info("test message")

        output = captured.getvalue()
        # Verify output is valid JSON
        log_entry = json.loads(output)
        assert "event" in log_entry
        assert log_entry["event"] == "test message"

    def test_configure_logging_adds_service_name(self) -> None:
        """Logs include service name in context."""
        configure_logging("plantation-model")
        logger = structlog.get_logger("test")

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            logger.info("test message")

        output = captured.getvalue()
        log_entry = json.loads(output)
        assert "service" in log_entry
        assert log_entry["service"] == "plantation-model"

    def test_configure_logging_uses_iso_timestamp(self) -> None:
        """Timestamps are in ISO format."""
        configure_logging("test-service")
        logger = structlog.get_logger("test")

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            logger.info("test message")

        output = captured.getvalue()
        log_entry = json.loads(output)
        assert "timestamp" in log_entry
        # ISO format check: should contain date separator and time separator
        timestamp = log_entry["timestamp"]
        assert "T" in timestamp or "-" in timestamp

    def test_configure_logging_adds_log_level(self) -> None:
        """Logs include log level."""
        configure_logging("test-service")
        logger = structlog.get_logger("test")

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            logger.info("test message")

        output = captured.getvalue()
        log_entry = json.loads(output)
        assert "level" in log_entry
        assert log_entry["level"] == "info"

    def test_configure_logging_console_format(self) -> None:
        """configure_logging with console format uses console renderer."""
        configure_logging("test-service", log_format="console")
        logger = structlog.get_logger("test")

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            logger.info("test message")

        output = captured.getvalue()
        # Console format should NOT be valid JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(output)

    def test_configure_logging_respects_env_format(self) -> None:
        """configure_logging respects LOG_FORMAT environment variable."""
        with patch.dict("os.environ", {"LOG_FORMAT": "console"}):
            configure_logging("test-service")
            logger = structlog.get_logger("test")

            captured = io.StringIO()
            with patch.object(sys, "stdout", captured):
                logger.info("test message")

            output = captured.getvalue()
            # Console format should NOT be valid JSON
            with pytest.raises(json.JSONDecodeError):
                json.loads(output)

    def test_configure_logging_respects_env_level(self) -> None:
        """configure_logging respects LOG_LEVEL environment variable."""
        with patch.dict("os.environ", {"LOG_LEVEL": "WARNING"}):
            configure_logging("test-service")
            logger = structlog.get_logger("test")

            captured = io.StringIO()
            with patch.object(sys, "stdout", captured):
                logger.info("should not appear")
                logger.warning("should appear")

            output = captured.getvalue()
            # Only warning should appear
            assert "should not appear" not in output
            assert "should appear" in output

    def test_configure_logging_parameter_overrides_env(self) -> None:
        """configure_logging parameters override environment variables."""
        with patch.dict("os.environ", {"LOG_FORMAT": "console"}):
            configure_logging("test-service", log_format="json")
            logger = structlog.get_logger("test")

            captured = io.StringIO()
            with patch.object(sys, "stdout", captured):
                logger.info("test message")

            output = captured.getvalue()
            # Should be valid JSON despite env var
            log_entry = json.loads(output)
            assert log_entry["event"] == "test message"
