"""Structured logging configuration for Farmer Power Platform services.

Provides consistent JSON-formatted logging with OpenTelemetry trace context injection.
See ADR-009 for logging standards and runtime configuration patterns.

Usage:
    from fp_common.logging import configure_logging
    import structlog

    configure_logging("plantation-model")
    logger = structlog.get_logger("plantation_model.domain.services")
    logger.info("Processing quality event", event_id="qe-123")
"""

import logging
import os
from typing import Any

import structlog
from opentelemetry import trace


def add_service_context(service_name: str) -> structlog.types.Processor:
    """Create processor that adds service name to all logs.

    Args:
        service_name: Name of the service for log context

    Returns:
        Structlog processor function
    """

    def processor(
        logger: logging.Logger,
        method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        event_dict["service"] = service_name
        return event_dict

    return processor


def add_trace_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add OpenTelemetry trace context to logs.

    Injects trace_id and span_id from the current span if one is active.
    When no span is active, logs are emitted without trace context.

    Args:
        logger: The wrapped logger object
        method_name: The name of the logging method called
        event_dict: The event dictionary with log context

    Returns:
        The event dictionary with trace context added
    """
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def configure_logging(
    service_name: str,
    log_format: str | None = None,
    log_level: str | None = None,
) -> None:
    """Configure structured logging for a service.

    Sets up structlog with JSON output (default) or console output for development.
    Includes service name, ISO timestamps, log levels, and OpenTelemetry trace context.

    Environment Variables:
        LOG_FORMAT: Output format - "json" (default) or "console"
        LOG_LEVEL: Default log level - "INFO" (default), "DEBUG", "WARNING", "ERROR"

    Args:
        service_name: Name of the service for log context (e.g., "plantation-model")
        log_format: Output format - "json" or "console". Defaults to LOG_FORMAT env var or "json"
        log_level: Log level string. Defaults to LOG_LEVEL env var or "INFO"

    Example:
        configure_logging("plantation-model")
        logger = structlog.get_logger("plantation_model.domain.services")
        logger.info("Event processed", event_id="qe-123")

        # Output (JSON):
        # {"event": "Event processed", "event_id": "qe-123", "service": "plantation-model",
        #  "timestamp": "2026-01-01T12:00:00.000000Z", "level": "info",
        #  "trace_id": "abc123...", "span_id": "def456..."}
    """
    # Resolve configuration from environment or parameters
    resolved_format = log_format or os.environ.get("LOG_FORMAT", "json")
    resolved_level = log_level or os.environ.get("LOG_LEVEL", "INFO")

    # Convert level string to logging constant
    numeric_level = getattr(logging, resolved_level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
    )

    # Build processor chain
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_service_context(service_name),
        add_trace_context,
    ]

    # Add renderer based on format
    if resolved_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def reset_logging() -> None:
    """Reset structlog configuration.

    Useful in tests to ensure clean state between test cases.
    """
    structlog.reset_defaults()
