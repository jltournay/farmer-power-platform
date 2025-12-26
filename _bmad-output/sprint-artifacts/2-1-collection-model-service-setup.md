# Story 2.1: Collection Model Service Setup

**Status:** in-progress
**GitHub Issue:** #16

---

## Story

As a **platform operator**,
I want the Collection Model service deployed with DAPR sidecar, MongoDB, and Redis pub/sub,
So that quality grading data can be ingested, stored, and domain events emitted to downstream services.

---

## Acceptance Criteria

1. **Given** the Kubernetes cluster is running with DAPR installed
   **When** the Collection Model service is deployed
   **Then** the service starts successfully with health check endpoint returning 200
   **And** the DAPR sidecar is injected and connected
   **And** MongoDB connection is established (verified via connection test)
   **And** Redis pub/sub component is configured and connected
   **And** OpenTelemetry traces are emitted for all operations

2. **Given** the service is running
   **When** the DAPR pub/sub is tested
   **Then** messages can be published to topics: `collection.document.stored`, `collection.poor_quality_detected`
   **And** topic subscriptions are registered with DAPR

3. **Given** Azure Event Grid subscription is configured (Epic 0 prerequisite)
   **When** a blob is created in `qc-analyzer-results` or `qc-analyzer-exceptions` containers
   **Then** Event Grid sends HTTP POST to the service's `/api/events/blob-created` endpoint
   **And** the webhook validates Event Grid subscription handshake

---

## Tasks / Subtasks

### Task 1: Create service folder structure (AC: #1)
- [x] 1.1 Create `services/collection-model/` directory
- [x] 1.2 Create `src/collection_model/` Python package
- [x] 1.3 Create `pyproject.toml` with dependencies
- [x] 1.4 Create `Dockerfile` based on `deploy/docker/Dockerfile.python`

### Task 2: Implement FastAPI application with health endpoints (AC: #1)
- [x] 2.1 Create `main.py` entrypoint with FastAPI app
- [x] 2.2 Implement `/health` endpoint (liveness probe)
- [x] 2.3 Implement `/ready` endpoint (readiness probe with MongoDB check)
- [x] 2.4 Create `config.py` for service configuration using Pydantic Settings

### Task 3: Configure Kubernetes deployment with DAPR (AC: #1)
- [x] 3.1 Create `deploy/kubernetes/base/services/collection-model.yaml` with DAPR annotations
- [ ] 3.2 Configure DAPR app-id: `collection-model`
- [ ] 3.3 Configure DAPR app-port: `8000` (HTTP)
- [ ] 3.4 Verify DAPR sidecar injection works in deployment

### Task 4: Implement MongoDB connection (AC: #1)
- [x] 4.1 Create `infrastructure/mongodb.py` with async Motor client
- [x] 4.2 Implement connection pooling and retry logic
- [x] 4.3 Create connection test utility for readiness probe
- [ ] 4.4 Configure collections: `source_configs`, `raw_documents`, `quality_events`

### Task 5: Configure OpenTelemetry tracing (AC: #1)
- [ ] 5.1 Add OpenTelemetry SDK and OTLP exporter to dependencies
- [ ] 5.2 Auto-instrument FastAPI and PyMongo
- [ ] 5.3 Configure via settings (`OTEL_ENABLED`, `OTEL_EXPORTER_ENDPOINT`)

### Task 6: Configure DAPR pub/sub for Redis (AC: #2)
- [x] 6.1 Verify DAPR pub/sub component exists (created in Epic 1)
- [x] 6.2 Implement `infrastructure/pubsub.py` with DAPR HTTP client
- [x] 6.3 Create publish method for `collection.document.stored` topic
- [x] 6.4 Create publish method for `collection.poor_quality_detected` topic
- [x] 6.5 Add pub/sub health check to readiness probe

### Task 7: Implement Event Grid webhook handler (AC: #3)
- [x] 7.1 Create `api/events.py` with FastAPI router
- [x] 7.2 Implement `POST /api/events/blob-created` endpoint
- [x] 7.3 Handle Event Grid subscription validation (return `validationResponse`)
- [x] 7.4 Parse `Microsoft.Storage.BlobCreated` events
- [x] 7.5 Log received events (processing deferred to Story 2.3)

### Task 8: Write unit tests
- [x] 8.1 Create test directory `tests/unit/collection/` with `__init__.py` and `conftest.py`
- [x] 8.2 Test health endpoint responses
- [x] 8.3 Test MongoDB connection with mocks
- [x] 8.4 Test configuration loading
- [x] 8.5 Test pub/sub publishing with mocked DAPR client
- [x] 8.6 Test Event Grid webhook handler (validation + event parsing)

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
│   │   └── events.py            # Event Grid webhook handler
│   ├── domain/
│   │   ├── __init__.py
│   │   └── models.py            # Pydantic domain models
│   └── infrastructure/
│       ├── __init__.py
│       ├── mongodb.py           # MongoDB async client
│       ├── pubsub.py            # DAPR pub/sub client
│       └── tracing.py           # OpenTelemetry configuration
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
| Service Mesh | DAPR | Latest |
| Pub/Sub | Redis (via DAPR) | Latest |
| Tracing | OpenTelemetry | Auto |

### Critical Implementation Rules

**From project-context.md:**

1. **ALL I/O operations MUST be async** - Use `async def` for all database and network operations
2. **Use Pydantic 2.0 syntax** - `model_dump()` not `dict()`, `model_validate()` not `parse_obj()`
3. **ALL inter-service communication via DAPR** - No direct HTTP between services
4. **Type hints required** - ALL function signatures MUST have type hints
5. **Absolute imports only** - No relative imports
6. **Environment prefix** - Use `COLLECTION_` prefix for all config env vars

### MongoDB Collections Owned by Collection Model

| Collection | Purpose |
|------------|---------|
| `source_configs` | Data source configurations (from `fp-source-config` CLI) |
| `raw_documents` | Raw blob content before LLM extraction |
| `quality_events` | Extracted grading events with bag summaries |
| `weather_data` | Weather API pull results |
| `market_prices` | Market price API pull results |

### DAPR Pub/Sub Topics

| Topic | Event Type | Published When |
|-------|-----------|----------------|
| `collection.document.stored` | DocumentStoredEvent | Raw document stored successfully |
| `collection.poor_quality_detected` | PoorQualityEvent | Quality drops below 70% threshold |
| `collection.weather.updated` | WeatherUpdatedEvent | Weather data pulled for region |
| `collection.market_prices.updated` | MarketPricesUpdatedEvent | Market prices updated |

### Event Grid Webhook Handler

```python
# api/events.py
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
import structlog

router = APIRouter(prefix="/api/events", tags=["events"])
logger = structlog.get_logger()

class EventGridEvent(BaseModel):
    id: str
    eventType: str
    subject: str
    data: dict
    eventTime: str

class SubscriptionValidation(BaseModel):
    validationCode: str
    validationUrl: str | None = None

@router.post("/blob-created")
async def handle_blob_created(request: Request) -> Response:
    """Handle Azure Event Grid blob-created events."""
    body = await request.json()

    # Handle subscription validation handshake
    if isinstance(body, list) and len(body) > 0:
        event = body[0]
        if event.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
            validation_code = event["data"]["validationCode"]
            logger.info("Event Grid subscription validation", code=validation_code)
            return Response(
                content=f'{{"validationResponse": "{validation_code}"}}',
                media_type="application/json"
            )

    # Process blob-created events (actual processing in Story 2.3)
    for event in body:
        if event.get("eventType") == "Microsoft.Storage.BlobCreated":
            logger.info(
                "Blob created event received",
                subject=event.get("subject"),
                blob_url=event["data"].get("url"),
            )
            # TODO: Queue for processing (Story 2.3)

    return Response(status_code=202)
```

### Pub/Sub Publishing Implementation

```python
# infrastructure/pubsub.py
from typing import Any
import httpx
from pydantic import BaseModel

DAPR_HTTP_PORT = 3500

class DaprPubSubClient:
    """DAPR pub/sub client for publishing domain events."""

    def __init__(self) -> None:
        self.base_url = f"http://localhost:{DAPR_HTTP_PORT}"
        self.pubsub_name = "pubsub"

    async def publish(self, topic: str, data: dict[str, Any]) -> None:
        """Publish event to DAPR pub/sub topic."""
        url = f"{self.base_url}/v1.0/publish/{self.pubsub_name}/{topic}"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            response.raise_for_status()

    async def publish_document_stored(self, event: BaseModel) -> None:
        """Publish document.stored event."""
        await self.publish("collection.document.stored", event.model_dump())

    async def publish_poor_quality_detected(self, event: BaseModel) -> None:
        """Publish poor_quality_detected event."""
        await self.publish("collection.poor_quality_detected", event.model_dump())
```

### Kubernetes Deployment with DAPR

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
          env:
            - name: COLLECTION_MONGODB_URI
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
---
apiVersion: v1
kind: Service
metadata:
  name: collection-model
spec:
  selector:
    app: collection-model
  ports:
    - port: 8000
      targetPort: 8000
      name: http
```

### Infrastructure Prerequisites (Epic 0)

The following must be provisioned before Event Grid webhooks work:

1. **Azure Event Grid System Topic** - For the storage account
2. **Event Subscription** - Filtering on `Microsoft.Storage.BlobCreated`
3. **Webhook Endpoint** - Points to `https://{ingress}/api/events/blob-created`

These are deployed via Terraform/Bicep in Epic 0 infrastructure stories.

### Proto Definition

```protobuf
// proto/collection/v1/collection.proto
syntax = "proto3";

package farmer_power.collection.v1;

// Domain events published via DAPR pub/sub
message DocumentStoredEvent {
  string document_id = 1;
  string source_type = 2;
  string farmer_id = 3;
  string blob_path = 4;
  string timestamp = 5;
}

message PoorQualityDetectedEvent {
  string event_id = 1;
  string farmer_id = 2;
  double primary_percentage = 3;
  map<string, double> leaf_type_distribution = 4;
  string priority = 5;  // "standard" or "critical"
}
```

### References

- [Source: _bmad-output/architecture/collection-model-architecture.md] - Full architecture design
- [Source: _bmad-output/epics.md#story-21] - Epic story definition
- [Source: _bmad-output/project-context.md] - Coding standards and rules
- [Source: Story 1.1] - Plantation Model service setup (reference implementation)

---

## Out of Scope

- Source configuration CLI tool (Story 2.2)
  - Event Grid event processing logic (Story 2.3)
- QC Analyzer JSON ingestion (Story 2.4)
- QC Analyzer ZIP ingestion (Story 2.5)
- Deduplication logic (Story 2.6)
- Actual domain event emission after processing (Story 2.10)

---

## Definition of Done

- [ ] Service starts and passes health checks
- [ ] MongoDB connection verified via `/ready` endpoint
- [ ] DAPR sidecar injected and pub/sub configured
- [ ] Event Grid webhook endpoint responds to validation requests
- [ ] Event Grid blob-created events logged (not processed)
- [ ] OpenTelemetry traces visible in collector
- [ ] All unit tests passing
- [ ] Code reviewed and merged
