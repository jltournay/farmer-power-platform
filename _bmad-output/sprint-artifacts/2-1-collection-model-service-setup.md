# Story 2.1: Collection Model Service Setup

**Status:** ready-for-dev

---

## Story

As a **platform operator**,
I want the Collection Model service deployed with Dapr sidecar and MongoDB connection,
So that quality grading data can be ingested, stored, and events emitted to downstream services.

---

## Acceptance Criteria

1. **Given** the Kubernetes cluster is running with Dapr installed
   **When** the Collection Model service is deployed
   **Then** the service starts successfully with health check endpoint returning 200

2. **Given** the service is deployed
   **When** the Dapr sidecar injection is checked
   **Then** the Dapr sidecar is injected and connected

3. **Given** the service is running
   **When** a MongoDB connection test is executed
   **Then** MongoDB connection is established (verified via connection test)

4. **Given** the service is running
   **When** a gRPC client connects
   **Then** gRPC server is listening on port 50052

5. **Given** any operation is executed
   **When** the operation completes
   **Then** OpenTelemetry traces are emitted for all operations

6. **Given** the service is running with Dapr sidecar
   **When** the pub/sub configuration is checked
   **Then** Dapr pub/sub is configured for Redis

7. **Given** the service is running
   **When** a quality event occurs
   **Then** messages can be published to topics: `collection.end_bag`, `collection.poor_quality_detected`

---

## Tasks / Subtasks

- [ ] **Task 1: Create service folder structure** (AC: #1)
  - [ ] 1.1 Create `services/collection-model/` directory
  - [ ] 1.2 Create `src/collection_model/` Python package
  - [ ] 1.3 Create `pyproject.toml` with dependencies
  - [ ] 1.4 Create `Dockerfile` based on `deploy/docker/Dockerfile.python`

- [ ] **Task 2: Implement FastAPI application with health endpoints** (AC: #1)
  - [ ] 2.1 Create `main.py` entrypoint with FastAPI app
  - [ ] 2.2 Implement `/health` endpoint (liveness probe)
  - [ ] 2.3 Implement `/ready` endpoint (readiness probe with MongoDB check)
  - [ ] 2.4 Create `config.py` for service configuration

- [ ] **Task 3: Configure Dapr sidecar** (AC: #2)
  - [ ] 3.1 Create Kubernetes deployment manifest with Dapr annotations
  - [ ] 3.2 Verify Dapr state store component exists at `deploy/kubernetes/components/dapr/statestore.yaml` (created in Story 1.1)
  - [ ] 3.3 Verify Dapr sidecar injection in deployment

- [ ] **Task 4: Implement MongoDB connection** (AC: #3)
  - [ ] 4.1 Create `infrastructure/mongodb.py` with async Motor client
  - [ ] 4.2 Implement connection pooling and retry logic
  - [ ] 4.3 Create connection test utility for readiness probe
  - [ ] 4.4 Configure collections: `quality_events`, `weather_data`, `documents_index`

- [ ] **Task 5: Implement gRPC server** (AC: #4)
  - [ ] 5.1 Create `proto/collection/v1/collection.proto` definitions
  - [ ] 5.2 Create `api/grpc_server.py` with health checking
  - [ ] 5.3 Enable server reflection for debugging
  - [ ] 5.4 Configure gRPC to listen on port 50052

- [ ] **Task 6: Configure OpenTelemetry tracing** (AC: #5)
  - [ ] 6.1 Add OpenTelemetry SDK and OTLP exporter
  - [ ] 6.2 Auto-instrument FastAPI, gRPC, and PyMongo
  - [ ] 6.3 Configure via settings (OTEL_ENABLED, OTEL_EXPORTER_ENDPOINT)

- [ ] **Task 7: Configure Dapr pub/sub for Redis** (AC: #6, #7)
  - [ ] 7.1 Verify Dapr pub/sub component exists at `deploy/kubernetes/components/dapr/pubsub.yaml` (created in Story 1.1)
  - [ ] 7.2 Implement `infrastructure/pubsub.py` with Dapr HTTP client
  - [ ] 7.3 Create publish methods for `collection.end_bag` topic
  - [ ] 7.4 Create publish methods for `collection.poor_quality_detected` topic
  - [ ] 7.5 Add pub/sub health check to readiness probe

- [ ] **Task 8: Write unit and integration tests**
  - [ ] 8.1 Create test directory `tests/unit/collection/` with `__init__.py` and `conftest.py`
  - [ ] 8.2 Test health endpoint responses
  - [ ] 8.3 Test MongoDB connection with mocks
  - [ ] 8.4 Test configuration loading
  - [ ] 8.5 Test pub/sub publishing with mocked Dapr client
  - [ ] 8.6 Integration tests for full app in `tests/integration/`

---

## Dev Notes

### Service Location

```
services/collection-model/
├── src/collection_model/
│   ├── __init__.py
│   ├── main.py                  # FastAPI entrypoint
│   ├── config.py                # Pydantic Settings
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py            # Health check endpoints
│   │   └── grpc_server.py       # gRPC service implementation
│   ├── domain/
│   │   ├── __init__.py
│   │   └── models.py            # Pydantic domain models (placeholder)
│   └── infrastructure/
│       ├── __init__.py
│       ├── mongodb.py           # MongoDB async client
│       ├── pubsub.py            # Dapr pub/sub client
│       └── tracing.py           # OpenTelemetry configuration
├── tests/
│   └── test_health.py
├── Dockerfile
└── pyproject.toml
```

### Technology Stack

| Component | Choice | Version |
|-----------|--------|---------|
| Language | Python | 3.12 |
| Web Framework | FastAPI | Latest |
| Validation | Pydantic | 2.0+ |
| MongoDB Driver | Motor (async) | Latest |
| gRPC | grpcio + grpcio-reflection | Latest |
| Service Mesh | Dapr | Latest |
| Pub/Sub | Redis (via Dapr) | Latest |
| Tracing | OpenTelemetry | Auto |

### Critical Implementation Rules

**From project-context.md:**

1. **ALL I/O operations MUST be async** - Use `async def` for all database and network operations
2. **Use Pydantic 2.0 syntax** - `model_dump()` not `dict()`, `model_validate()` not `parse_obj()`
3. **ALL inter-service communication via Dapr** - No direct HTTP between services
4. **Type hints required** - ALL function signatures MUST have type hints
5. **Absolute imports only** - No relative imports
6. **Environment prefix** - Use `COLLECTION_` prefix for all config env vars (e.g., `COLLECTION_MONGODB_URI`)

### MongoDB Collections Owned by Collection Model

| Collection | Purpose |
|------------|---------|
| `quality_events` | All grading events (end_bag, tbk_result, poor_quality_detected) |
| `weather_data` | Cached weather data from API pulls |
| `documents_index` | Index of uploaded documents with embeddings reference |

### Dapr Pub/Sub Topics

| Topic | Event Type | Published When |
|-------|-----------|----------------|
| `collection.end_bag` | EndBagEvent | QC Analyzer completes bag grading |
| `collection.poor_quality_detected` | PoorQualityEvent | Quality drops below threshold |

### pyproject.toml Dependencies

```toml
[tool.poetry]
name = "collection-model"
version = "0.1.0"
description = "Collection Model Service - Quality data ingestion gateway"

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
motor = "^3.3.0"
grpcio = "^1.60.0"
grpcio-reflection = "^1.60.0"
grpcio-health-checking = "^1.60.0"
structlog = "^24.1.0"
httpx = "^0.26.0"  # For Dapr HTTP client
dapr = "^1.13.0"
dapr-ext-grpc = "^1.13.0"  # For Dapr gRPC integration
fp-common = { path = "../../libs/fp-common" }
fp-proto = { path = "../../libs/fp-proto" }

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
httpx = "^0.26.0"
fp-testing = { path = "../../libs/fp-testing" }
```

### Dapr Pub/Sub Component (Redis)

```yaml
# deploy/kubernetes/components/dapr/pubsub.yaml (reuse from Story 1.1)
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
  namespace: farmer-power
spec:
  type: pubsub.redis
  version: v1
  metadata:
    - name: redisHost
      value: "redis:6379"
    - name: redisPassword
      secretKeyRef:
        name: redis-secrets
        key: password
```

### Kubernetes Deployment with Dapr

```yaml
# deploy/kubernetes/base/services/collection-model.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collection-model
  labels:
    app: collection-model
spec:
  replicas: 2
  selector:
    matchLabels:
      app: collection-model
  template:
    metadata:
      labels:
        app: collection-model
      annotations:
        dapr.io/enabled: "true"
        dapr.io/app-id: "collection-model"
        dapr.io/app-port: "8000"
        dapr.io/app-protocol: "http"
        dapr.io/enable-api-logging: "true"
    spec:
      containers:
        - name: collection-model
          image: farmer-power/collection-model:latest
          ports:
            - containerPort: 8000  # FastAPI HTTP
            - containerPort: 50052 # gRPC
          env:
            - name: MONGODB_URI
              valueFrom:
                secretKeyRef:
                  name: mongodb-secrets
                  key: uri
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 15
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
```

### Pub/Sub Publishing Implementation

```python
# infrastructure/pubsub.py
from typing import Any
import httpx
from pydantic import BaseModel
from collection_model.config import settings

DAPR_HTTP_PORT = 3500

class DaprPubSubClient:
    """Dapr pub/sub client for publishing events."""

    def __init__(self) -> None:
        self.base_url = f"http://localhost:{DAPR_HTTP_PORT}"
        self.pubsub_name = "pubsub"

    async def publish(self, topic: str, data: dict[str, Any]) -> None:
        """Publish event to Dapr pub/sub topic."""
        url = f"{self.base_url}/v1.0/publish/{self.pubsub_name}/{topic}"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            response.raise_for_status()

    async def publish_end_bag_event(self, event: BaseModel) -> None:
        """Publish end_bag event."""
        await self.publish("collection.end_bag", event.model_dump())

    async def publish_poor_quality_event(self, event: BaseModel) -> None:
        """Publish poor_quality_detected event."""
        await self.publish("collection.poor_quality_detected", event.model_dump())
```

### Project Structure Notes

- Service follows `services/{service-name}/` convention (kebab-case folder)
- Python package uses `{service_name}/` convention (snake_case)
- Proto definitions go in `proto/collection/v1/collection.proto`
- Shared libraries imported from `libs/fp-common/` and `libs/fp-proto/`
- Unit tests in `tests/unit/collection/` (global tests folder)
- Service-specific tests in `services/collection-model/tests/`
- gRPC port 50052 (Plantation uses 50051)

### References

- [Source: _bmad-output/architecture/collection-model-architecture.md] - Full architecture design
- [Source: _bmad-output/architecture/repository-structure.md] - Service folder template
- [Source: _bmad-output/architecture/infrastructure-decisions.md] - Dapr configuration
- [Source: _bmad-output/project-context.md#technology-stack] - Version requirements
- [Source: _bmad-output/project-context.md#python-specific-rules] - Async/Pydantic rules
- [Source: Story 1.1] - Plantation Model service setup (reference implementation)

---

## Out of Scope

- Implementing actual gRPC methods beyond health checking (Story 2-2+)
- Webhook endpoints for QC Analyzer (Story 2-2)
- TBK grading result storage (Story 2-3)
- Batch upload for offline mode (Story 2-4)
- Event subscription handling (Story 2-5+)

---

## GitHub Issue

To be created when story is picked up for development.
