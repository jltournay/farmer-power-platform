"""Unit tests for fp_common.logging trace context injection."""

import io
import json
import logging
import sys
from unittest.mock import patch

import structlog
from fp_common.logging import configure_logging, reset_logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider


class TestTraceContext:
    """Tests for OpenTelemetry trace context injection."""

    def setup_method(self) -> None:
        """Reset logging configuration before each test."""
        reset_logging()
        # Clear all loggers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # Set up OpenTelemetry tracer provider
        trace.set_tracer_provider(TracerProvider())

    def teardown_method(self) -> None:
        """Reset logging configuration after each test."""
        reset_logging()

    def test_trace_context_adds_trace_id_when_span_active(self) -> None:
        """trace_id injected when OpenTelemetry span active."""
        configure_logging("test-service")
        logger = structlog.get_logger("test")

        tracer = trace.get_tracer("test-tracer")

        with tracer.start_as_current_span("test-span"):
            captured = io.StringIO()
            with patch.object(sys, "stdout", captured):
                logger.info("test message")

            output = captured.getvalue()
            log_entry = json.loads(output)

            # Verify trace_id and span_id are present
            assert "trace_id" in log_entry
            assert "span_id" in log_entry
            # Verify they are hex strings (32 chars for trace_id, 16 for span_id)
            assert len(log_entry["trace_id"]) == 32
            assert len(log_entry["span_id"]) == 16

    def test_trace_context_handles_no_active_span(self) -> None:
        """No error when no span active."""
        configure_logging("test-service")
        logger = structlog.get_logger("test")

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured):
            # No span active - should still log without error
            logger.info("test message")

        output = captured.getvalue()
        log_entry = json.loads(output)

        # Message should be logged
        assert log_entry["event"] == "test message"
        # trace_id and span_id should NOT be present (no active span)
        assert "trace_id" not in log_entry
        assert "span_id" not in log_entry

    def test_trace_context_nested_spans(self) -> None:
        """Trace context reflects innermost span."""
        configure_logging("test-service")
        logger = structlog.get_logger("test")

        tracer = trace.get_tracer("test-tracer")

        with tracer.start_as_current_span("outer-span") as outer_span:
            outer_ctx = outer_span.get_span_context()

            with tracer.start_as_current_span("inner-span") as inner_span:
                inner_ctx = inner_span.get_span_context()

                captured = io.StringIO()
                with patch.object(sys, "stdout", captured):
                    logger.info("test message")

                output = captured.getvalue()
                log_entry = json.loads(output)

                # Should have inner span's span_id
                assert log_entry["span_id"] == format(inner_ctx.span_id, "016x")
                # But same trace_id (spans share trace)
                assert log_entry["trace_id"] == format(inner_ctx.trace_id, "032x")
                assert log_entry["trace_id"] == format(outer_ctx.trace_id, "032x")
