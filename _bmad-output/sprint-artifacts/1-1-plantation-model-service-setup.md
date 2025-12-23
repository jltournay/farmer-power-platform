# Story 1.1: Plantation Model Service Setup

**Status:** dev-complete

---

## Story

As a **platform operator**,
I want the Plantation Model service deployed with Dapr sidecar and MongoDB connection,
So that farmer and factory data can be stored and accessed by other services.

---

## Acceptance Criteria

1. **Given** the Kubernetes cluster is running with Dapr installed
   **When** the Plantation Model service is deployed
   **Then** the service starts successfully with health check endpoint returning 200

2. **Given** the service is deployed
   **When** the Dapr sidecar injection is checked
   **Then** the Dapr sidecar is injected and connected

3. **Given** the service is running
   **When** a MongoDB connection test is executed
   **Then** MongoDB connection is established (verified via connection test)

4. **Given** the service is running
   **When** a gRPC client connects
   **Then** gRPC server is listening on port 50051

5. **Given** any operation is executed
   **When** the operation completes
   **Then** OpenTelemetry traces are emitted for all operations

---

## Tasks / Subtasks

- [x] **Task 1: Create service folder structure** (AC: #1)
  - [x] 1.1 Create `services/plantation-model/` directory
  - [x] 1.2 Create `src/plantation_model/` Python package
  - [x] 1.3 Create `pyproject.toml` with dependencies
  - [x] 1.4 Create `Dockerfile` based on `deploy/docker/Dockerfile.python`

- [x] **Task 2: Implement FastAPI application with health endpoints** (AC: #1)
  - [x] 2.1 Create `main.py` entrypoint with FastAPI app
  - [x] 2.2 Implement `/health` endpoint (liveness probe)
  - [x] 2.3 Implement `/ready` endpoint (readiness probe with MongoDB check)
  - [x] 2.4 Create `config.py` for service configuration

- [x] **Task 3: Configure DAPR sidecar** (AC: #2)
  - [x] 3.1 Create Kubernetes deployment manifest with DAPR annotations
  - [x] 3.2 Configure DAPR state store component for MongoDB
  - [x] 3.3 Configure DAPR pubsub component for Redis

- [x] **Task 4: Implement MongoDB connection** (AC: #3)
  - [x] 4.1 Create `infrastructure/mongodb.py` with async Motor client
  - [x] 4.2 Implement connection pooling and retry logic
  - [x] 4.3 Create connection test utility for readiness probe
  - [x] 4.4 Configure via environment variables (K8s secrets)

- [x] **Task 5: Implement gRPC server** (AC: #4)
  - [x] 5.1 Create `proto/plantation/v1/plantation.proto` definitions
  - [x] 5.2 Create `api/grpc_server.py` with health checking
  - [x] 5.3 Enable server reflection for debugging
  - [x] 5.4 Configure gRPC to listen on port 50051

- [x] **Task 6: Configure OpenTelemetry tracing** (AC: #5)
  - [x] 6.1 Add OpenTelemetry SDK and OTLP exporter
  - [x] 6.2 Auto-instrument FastAPI, gRPC, and PyMongo
  - [x] 6.3 Configure via settings (OTEL_ENABLED, OTEL_EXPORTER_ENDPOINT)

- [x] **Task 7: Write unit and integration tests**
  - [x] 7.1 Create `tests/unit/` and `tests/integration/` directories
  - [x] 7.2 Test health endpoint responses (test_health.py)
  - [x] 7.3 Test MongoDB connection with mocks (test_mongodb.py)
  - [x] 7.4 Test configuration loading (test_config.py)
  - [x] 7.5 Integration tests for full app (test_app.py)

---

## Dev Notes

### Service Location
```
services/plantation-model/
├── src/plantation_model/
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
│       └── mongodb.py           # MongoDB async client
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
| Service Mesh | DAPR | Latest |
| Tracing | OpenTelemetry (via DAPR) | Auto |

### Critical Implementation Rules

**From project-context.md:**

1. **ALL I/O operations MUST be async** - Use `async def` for all database and network operations
2. **Use Pydantic 2.0 syntax** - `model_dump()` not `dict()`, `model_validate()` not `parse_obj()`
3. **ALL inter-service communication via DAPR** - No direct HTTP between services
4. **Type hints required** - ALL function signatures MUST have type hints
5. **Absolute imports only** - No relative imports

### pyproject.toml Dependencies

```toml
[tool.poetry]
name = "plantation-model"
version = "0.1.0"
description = "Plantation Model Service - Master data registry"

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
motor = "^3.3.0"
grpcio = "^1.60.0"
grpcio-reflection = "^1.60.0"
structlog = "^24.1.0"
fp-common = { path = "../../libs/fp-common" }
fp-proto = { path = "../../libs/fp-proto" }

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.23.0"
httpx = "^0.26.0"
fp-testing = { path = "../../libs/fp-testing" }
```

### Health Endpoint Implementation

```python
# api/health.py
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from plantation_model.infrastructure.mongodb import check_mongodb_connection

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict:
    """Liveness probe - service is running."""
    return {"status": "healthy"}

@router.get("/ready", status_code=status.HTTP_200_OK)
async def ready() -> JSONResponse:
    """Readiness probe - service can accept traffic."""
    mongodb_ok = await check_mongodb_connection()

    if not mongodb_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "mongodb": "disconnected"}
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ready", "mongodb": "connected"}
    )
```

### Kubernetes Deployment with DAPR

```yaml
# deploy/kubernetes/base/services/plantation-model.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: plantation-model
  labels:
    app: plantation-model
spec:
  replicas: 2
  selector:
    matchLabels:
      app: plantation-model
  template:
    metadata:
      labels:
        app: plantation-model
      annotations:
        dapr.io/enabled: "true"
        dapr.io/app-id: "plantation-model"
        dapr.io/app-port: "8000"
        dapr.io/app-protocol: "http"
        dapr.io/enable-api-logging: "true"
    spec:
      containers:
        - name: plantation-model
          image: farmer-power/plantation-model:latest
          ports:
            - containerPort: 8000  # FastAPI HTTP
            - containerPort: 50051 # gRPC
          env:
            - name: MONGODB_URI
              valueFrom:
                secretKeyRef:
                  name: mongodb-secrets
                  key: uri
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

### Project Structure Notes

- Service follows `services/{service-name}/` convention (kebab-case folder)
- Python package uses `{service_name}/` convention (snake_case)
- Proto definitions go in `proto/plantation/v1/plantation.proto`
- Shared libraries imported from `libs/fp-common/` and `libs/fp-proto/`
- Unit tests in `tests/unit/plantation/` (global tests folder)
- Service-specific tests in `services/plantation-model/tests/`

### References

- [Source: _bmad-output/architecture/plantation-model-architecture.md] - Full architecture design
- [Source: _bmad-output/architecture/repository-structure.md] - Service folder template
- [Source: _bmad-output/architecture/infrastructure-decisions.md] - DAPR configuration
- [Source: _bmad-output/project-context.md#technology-stack] - Version requirements
- [Source: _bmad-output/project-context.md#python-specific-rules] - Async/Pydantic rules

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

1. Created complete service structure following project conventions
2. FastAPI app with async lifespan handler for clean startup/shutdown
3. Health endpoints use dependency injection for MongoDB check
4. gRPC server uses grpc-health-checking package with reflection
5. OpenTelemetry auto-instruments FastAPI, gRPC, and PyMongo
6. All configuration via Pydantic Settings with PLANTATION_ env prefix
7. Unit tests use mocking, integration tests use TestClient
8. Kubernetes manifests include DAPR annotations and resource limits

### File List

**Service Files:**
- `services/plantation-model/pyproject.toml` - Dependencies with Poetry
- `services/plantation-model/Dockerfile` - Multi-stage build
- `services/plantation-model/src/plantation_model/__init__.py`
- `services/plantation-model/src/plantation_model/main.py` - FastAPI entrypoint
- `services/plantation-model/src/plantation_model/config.py` - Pydantic Settings
- `services/plantation-model/src/plantation_model/api/__init__.py`
- `services/plantation-model/src/plantation_model/api/health.py` - Health endpoints
- `services/plantation-model/src/plantation_model/api/grpc_server.py` - gRPC server
- `services/plantation-model/src/plantation_model/infrastructure/__init__.py`
- `services/plantation-model/src/plantation_model/infrastructure/mongodb.py` - Async MongoDB
- `services/plantation-model/src/plantation_model/infrastructure/tracing.py` - OpenTelemetry

**Proto Files:**
- `proto/plantation/v1/plantation.proto` - gRPC service definitions

**Kubernetes Files:**
- `deploy/kubernetes/base/services/plantation-model.yaml` - Deployment + Service
- `deploy/kubernetes/components/dapr/statestore.yaml` - MongoDB state store
- `deploy/kubernetes/components/dapr/pubsub.yaml` - Redis pub/sub

**Test Files (global tests folder per test-design-system-level.md):**
- `tests/unit/plantation/test_config.py` - Configuration tests
- `tests/unit/plantation/test_health.py` - Health endpoint tests
- `tests/unit/plantation/test_mongodb.py` - MongoDB connection tests
- `tests/integration/test_plantation_app.py` - Full application integration tests