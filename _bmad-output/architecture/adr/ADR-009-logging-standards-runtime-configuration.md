# ADR-009: Logging Standards and Runtime Configuration

**Status:** Accepted
**Date:** 2025-12-31
**Deciders:** Winston (Architect), Murat (TEA), Amelia (Dev), Jeanlouistournay
**Related Stories:** Epic 0-4 (Grading Validation)

## Context

During E2E testing and debugging, we encountered:
1. Inconsistent log levels across services
2. No way to enable DEBUG for specific packages
3. No way to change log levels without restarting pods
4. Missing context in log messages

## Decision

**Implement hierarchical logger naming, clear log level rules, and runtime log level configuration via HTTP endpoint.**

## Logger Naming Pattern

All loggers MUST follow hierarchical naming based on Python package structure:

```
{service_name}.{layer}.{module}
```

**Examples:**
```python
# Service: collection-model
logger = structlog.get_logger("collection_model.api.events")
logger = structlog.get_logger("collection_model.services.source_config_service")
logger = structlog.get_logger("collection_model.infrastructure.dapr_event_publisher")

# Service: plantation-model
logger = structlog.get_logger("plantation_model.domain.services.quality_event_processor")
logger = structlog.get_logger("plantation_model.infrastructure.collection_client")
```

**Layer prefixes:**
| Layer | Purpose | Example |
|-------|---------|---------|
| `api` | HTTP handlers, gRPC services | `api.events`, `api.grpc_server` |
| `domain` | Business logic | `domain.services.quality_processor` |
| `infrastructure` | External integrations | `infrastructure.mongodb` |
| `services` | Application services | `services.source_config_service` |

## Log Level Rules

### ERROR - Something broke, needs attention
- Unhandled exception caught at boundary
- External service failed after all retries
- Event sent to dead letter queue
- Data corruption detected

### WARNING - Something unexpected, but handled
- Retry triggered (will attempt again)
- Fallback used (degraded but functional)
- Validation failed on external input

### INFO - Significant business events
- Request/event received (entry point)
- Request/event completed (exit point)
- State change occurred
- Service startup/shutdown

### DEBUG - Detailed troubleshooting info
- Intermediate processing steps
- Cache hits
- Query parameters
- **NEVER in production by default**

## Runtime Log Level Configuration

### HTTP Endpoint

```python
# {service}/api/admin.py

@router.post("/admin/logging/{logger_name}")
async def set_log_level(logger_name: str, level: str):
    """Set log level for a specific logger at runtime."""
    logging.getLogger(logger_name).setLevel(level.upper())
    return {"logger": logger_name, "level": level, "status": "updated"}

@router.delete("/admin/logging/{logger_name}")
async def reset_log_level(logger_name: str):
    """Reset logger to default level."""
    logging.getLogger(logger_name).setLevel(logging.NOTSET)
    return {"logger": logger_name, "status": "reset"}
```

### Usage Examples

```bash
# Enable DEBUG for quality event processor
curl -X POST "http://localhost:8080/admin/logging/plantation_model.domain.services?level=DEBUG"

# Enable DEBUG for all infrastructure
curl -X POST "http://localhost:8080/admin/logging/plantation_model.infrastructure?level=DEBUG"

# Reset to default
curl -X DELETE "http://localhost:8080/admin/logging/plantation_model.infrastructure"
```

## Structlog Configuration

Create shared config in `libs/fp-common/fp_common/logging.py`:

```python
import structlog
from opentelemetry import trace

def configure_logging(service_name: str) -> None:
    """Configure structured logging with OpenTelemetry integration."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_service_context(service_name),
        add_trace_context,  # Inject trace_id/span_id
        structlog.processors.JSONRenderer(),
    ]
    structlog.configure(processors=processors, ...)

def add_trace_context(logger, method_name, event_dict):
    """Add OpenTelemetry trace context to logs."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Default log level for service |
| `LOG_FORMAT` | `json` | Output format: `json` or `console` |

## Implementation Gap (Current State)

The codebase **DOES NOT** currently implement these standards:

| Gap | Current | Required |
|-----|---------|----------|
| Logger naming | Uses `__name__` | Explicit hierarchical naming |
| Mixed libraries | Some use `logging.getLogger()` | ALL use `structlog.get_logger()` |
| Duplicated config | Each service duplicates structlog.configure() | Move to `fp_common/logging.py` |
| No runtime endpoint | None | Add `/admin/logging` to all services |
| No trace context | Not injected | Add OpenTelemetry processor |

**Files using wrong `logging.getLogger()` (must migrate):**
- All repository files in plantation-model
- `dapr_client.py`, `plantation_service.py`

## Consequences

### Positive

- **Runtime debugging** without pod restart
- **Hierarchical control** - enable DEBUG for specific packages
- **Observable** - trace_id/span_id in all logs
- **Consistent format** across all services

### Negative

- **Migration effort** - Update all logger calls
- **Shared dependency** - Services depend on fp_common/logging.py

## Revisit Triggers

Re-evaluate this decision if:

1. **Log volume too high** - May need sampling
2. **Performance impact** - May need async logging
3. **Security concerns** - May need audit for /admin endpoint

## References

- [Structlog Documentation](https://www.structlog.org/)
- [OpenTelemetry Python Logging](https://opentelemetry.io/docs/instrumentation/python/)
- Epic 0-4: Grading Validation
- Related: All other ADRs (logging supports debugging)
