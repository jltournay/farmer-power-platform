# PoC: DAPR Patterns Validation (ADR-010, ADR-011)

This proof-of-concept validates the DAPR patterns documented in:
- **ADR-010**: DAPR Patterns and Configuration Standards
- **ADR-011**: Service Architecture - gRPC APIs and DAPR SDK Pub/Sub

## What This PoC Validates

| # | Pattern | Test |
|---|---------|------|
| 1 | gRPC via DAPR proxy | Service A ↔ Service B gRPC calls |
| 2 | Streaming pub/sub | `subscribe_with_handler()` message flow |
| 3 | Retry behavior | Transient failures retry then succeed |
| 4 | Dead Letter Queue | Permanent failures go to DLQ |
| 5 | Two-port architecture | Health (8000) + gRPC (50051) only |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  ┌────────────────────────┐         ┌────────────────────────┐          │
│  │  Service A             │         │  Service B             │          │
│  │                        │         │                        │          │
│  │  ├─ gRPC: EchoService  │◄───────►│  ├─ gRPC: Calculator   │          │
│  │  ├─ Pub/Sub subscriber │         │  ├─ Pub/Sub subscriber │          │
│  │  └─ Health: /health    │         │  ├─ DLQ monitor        │          │
│  │                        │         │  └─ Health: /health    │          │
│  └───────────┬────────────┘         └───────────┬────────────┘          │
│              │                                  │                        │
│              ▼                                  ▼                        │
│  ┌────────────────────────┐         ┌────────────────────────┐          │
│  │  DAPR Sidecar A        │         │  DAPR Sidecar B        │          │
│  │  app-protocol: grpc    │         │  app-protocol: grpc    │          │
│  └───────────┬────────────┘         └───────────┬────────────┘          │
│              │                                  │                        │
│              └──────────────► Redis ◄───────────┘                       │
│                              (pubsub)                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Navigate to PoC directory
cd tests/e2e/poc-dapr-patterns

# 2. Build and start services
docker compose up --build -d

# 3. Wait for services to be healthy (check logs)
docker compose logs -f

# 4. Run tests (in another terminal)
pip install requests grpcio grpcio-tools
python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/poc.proto
python run_tests.py

# 5. Cleanup
docker compose down -v
```

## Test Scenarios

### 1. gRPC Service Invocation

Tests direct gRPC calls to validate services are running:

```bash
# Service A - Echo
grpcurl -plaintext localhost:50061 poc.v1.EchoService/Echo

# Service B - Calculator
grpcurl -plaintext localhost:50062 poc.v1.CalculatorService/Add
```

### 2. Pub/Sub Success Flow

```bash
# Trigger from Service B → Service A
curl -X POST "http://localhost:8002/publish-to-a?event_type=success&event_id=test-1"

# Check Service A received it
curl http://localhost:8001/received-messages
```

### 3. Pub/Sub Retry

```bash
# Send message that fails once then succeeds
curl -X POST "http://localhost:8002/publish-to-a?event_type=retry_once&event_id=test-2"

# Wait 5 seconds, then check
curl http://localhost:8001/received-messages
```

### 4. Dead Letter Queue

```bash
# Send message that always fails
curl -X POST "http://localhost:8002/publish-to-a?event_type=always_fail&event_id=test-3"

# Wait 15 seconds for retries to exhaust, then check DLQ
curl http://localhost:8002/dlq-messages
```

## Key Patterns Demonstrated

### Streaming Subscription (ADR-010)

```python
from dapr.clients import DaprClient

client = DaprClient()

close_fn = client.subscribe_with_handler(
    pubsub_name="pubsub",
    topic="poc.events.to-a",
    handler_fn=handle_event,
    dead_letter_topic="poc.dlq.service-a",  # DLQ in code!
)
```

### gRPC via DAPR Proxy (ADR-011)

```python
import grpc

# Connect to DAPR's gRPC proxy (not the service directly)
channel = grpc.insecure_channel(f"localhost:{DAPR_GRPC_PORT}")

# Route to target service via metadata
metadata = [("dapr-app-id", "poc-service-b")]
stub = CalculatorServiceStub(channel)
response = stub.Add(request, metadata=metadata)
```

### Two-Port Architecture (ADR-011)

```yaml
# Only two ports needed:
ports:
  - "8000:8000"   # FastAPI health (direct, no DAPR)
  - "50051:50051" # gRPC service (via DAPR sidecar)
# NO extra port for pub/sub - streaming is outbound!
```

## Expected Test Output

```
============================================================
  PoC: DAPR Patterns Validation (ADR-010, ADR-011)
============================================================

🔄 Waiting for services to be healthy...
✅ All services healthy and subscriptions ready

------------------------------------------------------------
  Running Tests
------------------------------------------------------------

📡 gRPC Service Invocation Tests:
✅ PASS: gRPC: Service A Echo (direct)
✅ PASS: gRPC: Service B Calculator.Add (direct)

📨 Pub/Sub Streaming Tests:
✅ PASS: Pub/Sub: Success message (B → A)
✅ PASS: Pub/Sub: Retry behavior
✅ PASS: Pub/Sub: DLQ receives failed messages

============================================================
  Test Summary
============================================================
  ✅ gRPC: Service A Echo (direct)
  ✅ gRPC: Service B Calculator.Add (direct)
  ✅ Pub/Sub: Success message (B → A)
  ✅ Pub/Sub: Retry behavior
  ✅ Pub/Sub: DLQ receives failed messages

  Total: 5 | Passed: 5 | Failed: 0
============================================================

✅ All tests passed!
```

## Troubleshooting

### Services not starting

```bash
# Check logs
docker compose logs poc-service-a
docker compose logs poc-service-a-dapr

# Verify Redis is healthy
docker compose exec redis redis-cli ping
```

### Subscription not ready

The streaming subscription needs ~5 seconds to establish after DAPR sidecar is ready. Check:

```bash
curl http://localhost:8001/ready
# Should show: {"subscription_ready": true}
```

### DLQ not receiving messages

Check resiliency policy is loaded:

```bash
docker compose logs poc-service-a-dapr | grep -i resiliency
```

## Files

```
poc-dapr-patterns/
├── docker-compose.yaml      # Infrastructure + services
├── Dockerfile.service-a     # Service A container
├── Dockerfile.service-b     # Service B container
├── dapr-components/
│   ├── pubsub.yaml          # Redis pubsub component
│   └── resiliency.yaml      # Retry policy (3 retries)
├── proto/
│   └── poc.proto            # Echo + Calculator services
├── service-a/
│   ├── requirements.txt
│   └── main.py              # EchoService + subscriber
├── service-b/
│   ├── requirements.txt
│   └── main.py              # Calculator + subscriber + DLQ monitor
├── run_tests.py             # Test runner
└── README.md                # This file
```

## Next Steps After Validation

Once this PoC passes:

1. **Migrate plantation-model** to use streaming subscriptions
2. **Remove FastAPI event handlers** (`/api/v1/events/*`)
3. **Update docker-compose** to remove pub/sub port references
4. **Update E2E tests** to verify new pattern works
