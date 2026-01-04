# 9. Observability

## Logging Standards

Use structured logging with consistent fields:

```python
import structlog

logger = structlog.get_logger()

# Standard fields for all agent logs
def log_agent_event(event_type: str, **kwargs):
    logger.info(
        event_type,
        agent_id=current_agent_id(),
        trace_id=current_trace_id(),
        **kwargs
    )

# Usage
log_agent_event(
    "agent_started",
    input_event="collection.document.received",
    doc_id="doc-123"
)

log_agent_event(
    "llm_called",
    model="anthropic/claude-3-5-sonnet",
    input_tokens=1250,
    output_tokens=450,
    latency_ms=1200
)

log_agent_event(
    "agent_completed",
    output_event="ai.extraction.complete",
    success=True,
    duration_ms=2500
)
```

## Tracing Requirements

Ensure trace context propagates through the entire flow:

```python
from opentelemetry import trace
from opentelemetry.trace import SpanKind

tracer = trace.get_tracer(__name__)

async def run_agent(event: dict):
    # DAPR provides trace context in event headers
    context = extract_trace_context(event.headers)

    with tracer.start_as_current_span(
        "agent.run",
        context=context,
        kind=SpanKind.CONSUMER,
        attributes={
            "agent.id": agent_id,
            "agent.type": agent_type,
            "input.event": event.topic
        }
    ) as span:

        # Child span for MCP calls
        with tracer.start_as_current_span("mcp.fetch_document"):
            document = await mcp_client.get_document(doc_id)

        # Child span for LLM
        with tracer.start_as_current_span(
            "llm.complete",
            attributes={"llm.model": model, "agent.id": agent_id}
        ):
            result = await llm_gateway.complete(prompt)

        span.set_attribute("output.success", True)
        return result
```

## Metrics to Capture

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `agent_invocations_total` | Counter | agent_id, status | Track usage |
| `agent_duration_seconds` | Histogram | agent_id | Performance |
| `llm_tokens_total` | Counter | model, direction | Cost tracking |
| `llm_latency_seconds` | Histogram | model, agent_id | LLM performance |
| `rag_queries_total` | Counter | domain, cache_hit | RAG usage |
| `agent_errors_total` | Counter | agent_id, error_type | Error tracking |

```python
from prometheus_client import Counter, Histogram

agent_invocations = Counter(
    'agent_invocations_total',
    'Total agent invocations',
    ['agent_id', 'status']
)

agent_duration = Histogram(
    'agent_duration_seconds',
    'Agent execution duration',
    ['agent_id'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
)

llm_tokens = Counter(
    'llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'direction']  # direction: input/output
)
```

## Alerting Thresholds

Configure alerts for:

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Error rate | >5% in 5min | Page on-call |
| Latency p95 | >10s | Investigate |
| Token cost | >$X/day | Review optimization |
| Dead letter queue | >10 items | Investigate failures |

---
