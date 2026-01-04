# Observability

**DAPR provides OpenTelemetry instrumentation out of the box.**

> **Implementation details:** See `ai-model-developer-guide/9-observability.md` for logging conventions, custom metrics, and trace correlation.

| Aspect | Approach |
|--------|----------|
| **Tracing** | DAPR automatic trace context propagation |
| **Backend** | Grafana Cloud (OpenTelemetry compatible, swappable) |
| **Cost Tracking** | Per-call logging (tokens, cost, model, farmer_id) |
| **Metrics** | Latency, error rates, token usage per agent/model |

**Trace propagation across events:**

```
Collection ──▶ DAPR ──▶ AI Model ──▶ MCP calls ──▶ DAPR ──▶ Collection
    │            │          │            │           │          │
 span-1      span-2      span-3      span-4       span-5     span-6
    └──────────────────────┴────────────────────────┴──────────┘
                          same trace_id
```

**Infrastructure Agnosticism:**

| Infrastructure | Abstraction | Current Choice | Can Switch To |
|----------------|-------------|----------------|---------------|
| Message Broker | DAPR Pub/Sub | TBD | Azure SB, Kafka, Redis, RabbitMQ |
| Observability | OpenTelemetry | Grafana Cloud | Azure Monitor, Datadog, Jaeger |
| LLM Provider | OpenRouter | Multi-provider | Any supported model |
| Scheduler | DAPR Jobs | TBD | Any DAPR-supported backend |
