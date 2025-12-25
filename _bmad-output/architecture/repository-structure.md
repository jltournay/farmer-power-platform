# Repository Structure

## Overview

This document defines the physical organization of the Farmer Power Platform codebase. It establishes conventions for folder layout, service organization, shared code, and deployment artifacts.

## Monorepo Decision

**Decision:** Single monorepo containing all platform services.

| Aspect | Monorepo | Polyrepo |
|--------|----------|----------|
| Code sharing | Easy (shared libs) | Requires publishing packages |
| Atomic changes | Single PR across services | Multiple PRs, coordination needed |
| CI/CD | Single pipeline, selective builds | Separate pipelines per repo |
| Onboarding | Clone once, see everything | Multiple repos to understand |
| Service boundaries | Enforced by convention | Enforced by repo boundaries |

**Rationale:** For a platform with 8 tightly integrated domain models, monorepo enables:
- Atomic refactoring across service boundaries
- Shared proto definitions without versioning complexity
- Unified CI/CD with selective builds
- Single source of truth for deployment manifests

## Top-Level Directory Structure

```
farmer-power-platform/
├── services/                    # All microservices
│   ├── collection-model/
│   ├── plantation-model/
│   ├── knowledge-model/
│   ├── action-plan-model/
│   ├── notification-model/
│   ├── market-analysis-model/
│   ├── ai-model/
│   ├── conversational-ai/
│   ├── bff/                     # Backend-for-Frontend
│   └── inbound-webhook/         # External webhook receiver
│
├── mcp-servers/                 # MCP Server implementations
│   ├── collection-mcp/
│   ├── plantation-mcp/
│   ├── knowledge-mcp/
│   └── action-plan-mcp/
│
├── proto/                       # Shared Protocol Buffer definitions
│   ├── collection/
│   │   └── v1/
│   │       ├── collection.proto
│   │       └── events.proto
│   ├── plantation/
│   │   └── v1/
│   │       └── plantation.proto
│   ├── knowledge/
│   │   └── v1/
│   │       └── knowledge.proto
│   ├── action_plan/
│   │   └── v1/
│   │       └── action_plan.proto
│   ├── notification/
│   │   └── v1/
│   │       └── notification.proto
│   ├── mcp/
│   │   └── v1/
│   │       └── mcp_tool.proto  # gRPC MCP service (not JSON-RPC)
│   └── common/
│       └── v1/
│           ├── pagination.proto
│           ├── errors.proto
│           └── health.proto
│
├── libs/                        # Shared Python libraries
│   ├── fp-common/               # Common utilities
│   │   ├── pyproject.toml
│   │   └── fp_common/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       ├── errors.py
│   │       ├── tracing.py
│   │       └── dapr_client.py
│   ├── fp-proto/                # Generated proto stubs
│   │   ├── pyproject.toml
│   │   └── fp_proto/
│   │       ├── __init__.py
│   │       ├── collection/
│   │       ├── plantation/
│   │       └── ...
│   └── fp-testing/              # Test utilities
│       ├── pyproject.toml
│       └── fp_testing/
│           ├── __init__.py
│           ├── fixtures.py
│           └── mocks.py
│
├── deploy/                      # Deployment configurations
│   ├── kubernetes/
│   │   ├── base/                # Base manifests (Kustomize)
│   │   │   ├── kustomization.yaml
│   │   │   ├── namespace.yaml
│   │   │   └── services/
│   │   │       ├── collection-model.yaml
│   │   │       ├── plantation-model.yaml
│   │   │       └── ...
│   │   ├── overlays/
│   │   │   ├── qa/
│   │   │   │   ├── kustomization.yaml
│   │   │   │   └── config-patch.yaml
│   │   │   ├── preprod/
│   │   │   │   ├── kustomization.yaml
│   │   │   │   └── config-patch.yaml
│   │   │   └── prod/
│   │   │       ├── kustomization.yaml
│   │   │       ├── config-patch.yaml
│   │   │       └── hpa-patch.yaml
│   │   └── components/
│   │       ├── dapr/
│   │       │   ├── statestore.yaml
│   │       │   ├── pubsub.yaml
│   │       │   ├── resiliency.yaml
│   │       │   └── jobs.yaml
│   │       └── secrets/
│   │           └── external-secrets.yaml
│   │
│   ├── docker/
│   │   ├── Dockerfile.python     # Base Python service image
│   │   ├── Dockerfile.node       # Base Node.js image (if needed)
│   │   └── docker-compose.yml    # Local development stack
│   │
│   └── helm/                     # Optional Helm charts
│       └── farmer-power/
│           ├── Chart.yaml
│           ├── values.yaml
│           └── templates/
│
├── scripts/                     # Development & CI scripts
│   ├── proto-gen.sh             # Generate proto stubs
│   ├── local-dev.sh             # Start local environment
│   ├── run-tests.sh             # Run all tests
│   └── deploy.sh                # Deployment script
│
├── tests/                       # Cross-service tests (see test-design-system-level.md)
│   ├── conftest.py              # Global fixtures (mock_dapr_client, mock_openrouter, mongodb_test_client)
│   ├── unit/                    # Per-domain-model unit tests
│   │   ├── collection/
│   │   │   ├── test_ingestion_pipeline.py
│   │   │   ├── test_schema_validation.py
│   │   │   └── test_mcp_tools.py
│   │   ├── plantation/
│   │   │   └── test_farmer_crud.py
│   │   ├── knowledge/
│   │   │   ├── test_triage_agent.py
│   │   │   └── test_analyzer_logic.py
│   │   ├── action_plan/
│   │   │   └── test_selector_logic.py
│   │   ├── notification/
│   │   │   └── test_delivery_logic.py
│   │   └── ai_model/
│   │       ├── test_extractor_workflow.py
│   │       ├── test_explorer_workflow.py
│   │       └── test_generator_workflow.py
│   ├── integration/
│   │   ├── test_dapr_events.py
│   │   ├── test_mcp_integration.py
│   │   └── test_mongodb_operations.py
│   ├── golden/                  # Golden sample testing (CRITICAL for AI accuracy)
│   │   ├── framework.py         # Golden sample validation framework
│   │   ├── qc-event-extractor/
│   │   │   └── samples.json     # 100+ expert-validated samples
│   │   ├── quality-triage/
│   │   │   └── samples.json     # 100+ expert-validated samples
│   │   ├── disease-diagnosis/
│   │   │   └── samples.json     # 50+ agronomist-validated samples
│   │   ├── weather-impact-analyzer/
│   │   │   └── samples.json     # 30+ validated samples
│   │   ├── technique-assessment/
│   │   │   └── samples.json     # 30+ validated samples
│   │   └── action-plan-generator/
│   │       └── samples.json     # 20+ validated samples
│   ├── contracts/               # Contract tests for inter-service communication
│   │   ├── test_event_schemas.py      # DAPR event contract tests
│   │   └── test_mcp_contracts.py      # MCP tool contract tests
│   └── fixtures/
│       ├── llm_responses/       # Recorded LLM responses for replay
│       ├── mongodb_data/        # Test data fixtures
│       └── external_api_mocks/  # Starfish, Weather, Africa's Talking mocks
│
├── docs/                        # Documentation
│   └── architecture/            # Symlink or copy of _bmad-output/architecture
│
├── .github/                     # GitHub Actions CI/CD
│   └── workflows/
│       ├── ci.yaml              # Build, test, lint
│       ├── deploy-qa.yaml
│       ├── deploy-preprod.yaml
│       └── deploy-prod.yaml
│
├── pyproject.toml               # Root project config (workspace)
├── poetry.lock                  # Locked dependencies
├── .pre-commit-config.yaml      # Pre-commit hooks
├── Makefile                     # Common commands
└── README.md
```

## Service Folder Template

Each service in `services/` follows this standard structure:

```
services/{service-name}/
├── src/
│   └── {service_name}/          # Python package (snake_case)
│       ├── __init__.py
│       ├── main.py              # FastAPI/gRPC entrypoint
│       ├── config.py            # Service configuration
│       │
│       ├── api/                 # API layer
│       │   ├── __init__.py
│       │   ├── grpc_server.py   # gRPC service implementation
│       │   └── rest_routes.py   # REST endpoints (if any)
│       │
│       ├── domain/              # Business logic
│       │   ├── __init__.py
│       │   ├── models.py        # Domain models (Pydantic)
│       │   ├── services.py      # Business logic services
│       │   └── events.py        # Domain events
│       │
│       ├── infrastructure/      # External integrations
│       │   ├── __init__.py
│       │   ├── mongodb.py       # MongoDB repository
│       │   ├── dapr_client.py   # Dapr integration
│       │   └── external_api.py  # External API clients
│       │
│       └── utils/               # Service-specific utilities
│           └── __init__.py
│
├── tests/
│   ├── unit/
│   │   ├── test_domain.py
│   │   └── test_services.py
│   ├── integration/
│   │   └── test_mongodb.py
│   └── conftest.py              # Pytest fixtures
│
├── config/
│   ├── settings.yaml            # Default settings
│   └── logging.yaml             # Logging configuration
│
├── Dockerfile                   # Service-specific Dockerfile
├── pyproject.toml               # Service dependencies
└── README.md                    # Service documentation
```

### Service Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Service folder | kebab-case | `collection-model/` |
| Python package | snake_case | `collection_model/` |
| gRPC service | PascalCase | `CollectionService` |
| Proto package | snake_case | `farmer_power.collection.v1` |
| Docker image | kebab-case | `farmer-power/collection-model` |
| K8s deployment | kebab-case | `collection-model` |

## Proto Organization

### Directory Structure

```
proto/
├── buf.yaml                     # Buf configuration
├── buf.gen.yaml                 # Code generation config
│
├── collection/
│   └── v1/
│       ├── collection.proto     # Service definitions
│       ├── events.proto         # Event payloads
│       └── models.proto         # Shared message types
│
├── plantation/
│   └── v1/
│       ├── plantation.proto
│       └── models.proto
│
├── knowledge/
│   └── v1/
│       ├── knowledge.proto
│       └── diagnosis.proto
│
├── action_plan/
│   └── v1/
│       └── action_plan.proto
│
├── notification/
│   └── v1/
│       ├── notification.proto
│       └── channels.proto
│
├── mcp/
│   └── v1/
│       └── mcp_tool.proto       # gRPC MCP service (see infrastructure-decisions.md)
│
└── common/
    └── v1/
        ├── pagination.proto     # Pagination messages
        ├── errors.proto         # Error codes and messages
        ├── health.proto         # Health check service
        └── timestamps.proto     # Common timestamp types
```

### Proto File Example

```protobuf
// proto/collection/v1/collection.proto

syntax = "proto3";

package farmer_power.collection.v1;

import "common/v1/pagination.proto";
import "common/v1/errors.proto";

option go_package = "github.com/farmerpower/proto/collection/v1";

// CollectionService handles quality data ingestion
service CollectionService {
  // Submit a single END_BAG event
  rpc SubmitEndBag(SubmitEndBagRequest) returns (SubmitEndBagResponse);

  // Batch submit multiple events
  rpc BatchSubmitEndBag(BatchSubmitEndBagRequest) returns (BatchSubmitEndBagResponse);

  // Get quality event by ID
  rpc GetQualityEvent(GetQualityEventRequest) returns (QualityEvent);

  // List quality events with filters
  rpc ListQualityEvents(ListQualityEventsRequest) returns (ListQualityEventsResponse);
}

message SubmitEndBagRequest {
  string bag_id = 1;
  string farmer_id = 2;
  string collection_point_id = 3;
  string factory_id = 4;
  google.protobuf.Timestamp timestamp = 5;
  repeated LeafAssessment leaf_assessments = 6;
}

// ... more message definitions
```

### Proto Generation

```bash
# scripts/proto-gen.sh
#!/bin/bash

# Generate Python stubs
buf generate --template buf.gen.yaml

# Copy to libs/fp-proto
cp -r gen/python/* libs/fp-proto/fp_proto/
```

```yaml
# buf.gen.yaml
version: v1
plugins:
  - plugin: buf.build/protocolbuffers/python
    out: gen/python
  - plugin: buf.build/grpc/python
    out: gen/python
  - plugin: buf.build/community/nipunn1313-mypy
    out: gen/python
```

## Shared Libraries

### fp-common

Core utilities shared across all services:

```
libs/fp-common/
├── pyproject.toml
└── fp_common/
    ├── __init__.py
    ├── config.py           # Configuration loading (Pydantic Settings)
    ├── errors.py           # Standard error types
    ├── tracing.py          # OpenTelemetry setup
    ├── logging.py          # Structured logging
    ├── dapr/
    │   ├── __init__.py
    │   ├── client.py       # Dapr client wrapper
    │   ├── pubsub.py       # Pub/sub helpers
    │   └── state.py        # State store helpers
    ├── mcp/                 # MCP client utilities (gRPC-based)
    │   ├── __init__.py
    │   ├── client.py       # GrpcMcpClient - DAPR service invocation wrapper
    │   ├── tool.py         # GrpcMcpTool - LangChain BaseTool wrapper
    │   ├── registry.py     # Tool discovery and registration
    │   └── errors.py       # McpToolError, error codes
    └── health/
        ├── __init__.py
        └── checks.py       # Health check utilities
```

### fp-proto

Generated proto stubs (managed, not edited manually):

```
libs/fp-proto/
├── pyproject.toml
└── fp_proto/
    ├── __init__.py
    ├── collection/
    │   └── v1/
    │       ├── __init__.py
    │       ├── collection_pb2.py
    │       ├── collection_pb2_grpc.py
    │       └── collection_pb2.pyi
    ├── mcp/                          # MCP gRPC stubs (shared by all MCP servers)
    │   └── v1/
    │       ├── __init__.py
    │       ├── mcp_tool_pb2.py       # Message types
    │       ├── mcp_tool_pb2_grpc.py  # Service stubs
    │       └── mcp_tool_pb2.pyi      # Type hints
    └── common/
        └── v1/
            └── ...
```

### fp-testing

Test utilities and fixtures (aligned with `test-design-system-level.md`):

```
libs/fp-testing/
├── pyproject.toml
└── fp_testing/
    ├── __init__.py
    ├── fixtures.py              # Pytest fixtures (event_loop, async support)
    ├── factories.py             # Factory Boy factories for domain models
    ├── golden/
    │   ├── __init__.py
    │   ├── framework.py         # Golden sample validation framework
    │   ├── loader.py            # Load samples from tests/golden/
    │   └── validator.py         # Validate with acceptable variance
    ├── mocks/
    │   ├── __init__.py
    │   ├── dapr_mock.py         # Mock Dapr client (service invocation, pubsub)
    │   ├── mongodb_mock.py      # Mock MongoDB (testcontainers integration)
    │   ├── llm_mock.py          # Mock LLM with record/replay
    │   ├── pinecone_mock.py     # In-memory vector DB mock
    │   ├── mcp_mock.py          # Mock MCP servers (gRPC service mock)
    │   └── external_apis.py     # Starfish, Weather, Africa's Talking mocks
    └── assertions.py            # Custom assertions for AI output validation
```

> **Reference:** See `_bmad-output/test-design-system-level.md` for full test strategy, risk assessment, and golden sample requirements.

## Docker Organization

### Base Dockerfile

```dockerfile
# deploy/docker/Dockerfile.python
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.0

# Copy shared libs first (for caching)
COPY libs/ /app/libs/

# ---
FROM base as builder

# Copy service code
ARG SERVICE_NAME
COPY services/${SERVICE_NAME}/pyproject.toml services/${SERVICE_NAME}/poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

COPY services/${SERVICE_NAME}/src/ ./src/

# ---
FROM base as runtime

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/src /app/src

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 50051 8080

ARG SERVICE_NAME
ENV SERVICE_NAME=${SERVICE_NAME}

CMD ["python", "-m", "src.${SERVICE_NAME}.main"]
```

### Service Dockerfile

```dockerfile
# services/collection-model/Dockerfile
FROM farmer-power/python-base:latest as base

# Service-specific build args
ARG SERVICE_NAME=collection_model

# Copy service-specific files
COPY services/collection-model/ /app/

# Install service dependencies
RUN poetry install --no-interaction --no-ansi

CMD ["python", "-m", "collection_model.main"]
```

### Docker Compose (Local Development)

```yaml
# deploy/docker/docker-compose.yml
version: '3.8'

services:
  # Infrastructure
  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Dapr
  dapr-placement:
    image: daprio/dapr:1.12.0
    command: ["./placement", "-port", "50006"]
    ports:
      - "50006:50006"

  # Services
  collection-model:
    build:
      context: ../..
      dockerfile: services/collection-model/Dockerfile
    ports:
      - "50051:50051"
      - "8081:8080"
    environment:
      - MONGODB_URI=mongodb://admin:password@mongodb:27017
      - DAPR_HTTP_PORT=3500
      - DAPR_GRPC_PORT=50001
    depends_on:
      - mongodb
      - dapr-placement

  collection-model-dapr:
    image: daprio/daprd:1.12.0
    command: [
      "./daprd",
      "-app-id", "collection-model",
      "-app-port", "50051",
      "-app-protocol", "grpc",
      "-placement-host-address", "dapr-placement:50006"
    ]
    network_mode: "service:collection-model"
    depends_on:
      - collection-model

  # Add more services as needed...

volumes:
  mongodb_data:
```

## Kubernetes Manifests (Kustomize)

### Base Deployment

```yaml
# deploy/kubernetes/base/services/collection-model.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collection-model
  labels:
    app: collection-model
    app.kubernetes.io/part-of: farmer-power
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
        dapr.io/app-port: "50051"
        dapr.io/app-protocol: "grpc"
    spec:
      containers:
        - name: collection-model
          image: farmer-power/collection-model:latest
          ports:
            - containerPort: 50051
              name: grpc
            - containerPort: 8080
              name: http
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: app-secrets
          resources:
            requests:
              cpu: "100m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: collection-model
spec:
  selector:
    app: collection-model
  ports:
    - name: grpc
      port: 50051
      targetPort: 50051
    - name: http
      port: 8080
      targetPort: 8080
```

### Environment Overlays

```yaml
# deploy/kubernetes/overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: farmer-power-prod

resources:
  - ../../base

patchesStrategicMerge:
  - config-patch.yaml
  - hpa-patch.yaml

images:
  - name: farmer-power/collection-model
    newTag: v1.2.3
  - name: farmer-power/plantation-model
    newTag: v1.2.3
```

## CI/CD Pipeline Structure

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      services: ${{ steps.filter.outputs.changes }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v2
        id: filter
        with:
          filters: |
            collection-model:
              - 'services/collection-model/**'
              - 'libs/**'
              - 'proto/collection/**'
            plantation-model:
              - 'services/plantation-model/**'
              - 'libs/**'
              - 'proto/plantation/**'
            # ... more services

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run ruff
        run: ruff check .
      - name: Run mypy
        run: mypy .

  test:
    needs: detect-changes
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: ${{ fromJson(needs.detect-changes.outputs.services) }}
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          cd services/${{ matrix.service }}
          poetry install
          pytest

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: ${{ fromJson(needs.detect-changes.outputs.services) }}
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: |
          docker build -t farmer-power/${{ matrix.service }}:${{ github.sha }} \
            -f services/${{ matrix.service }}/Dockerfile .
      - name: Push to registry
        run: |
          docker push farmer-power/${{ matrix.service }}:${{ github.sha }}
```

## Development Workflow

### Makefile Commands

```makefile
# Makefile

.PHONY: proto install test lint docker-build local-up local-down

# Generate proto stubs
proto:
	./scripts/proto-gen.sh

# Install all dependencies
install:
	poetry install
	cd libs/fp-common && poetry install
	cd libs/fp-proto && poetry install

# Run all tests
test:
	pytest tests/ services/*/tests/

# Run linting
lint:
	ruff check .
	mypy services/ libs/

# Build all Docker images
docker-build:
	docker-compose -f deploy/docker/docker-compose.yml build

# Start local development environment
local-up:
	docker-compose -f deploy/docker/docker-compose.yml up -d

# Stop local development environment
local-down:
	docker-compose -f deploy/docker/docker-compose.yml down

# Deploy to environment
deploy-%:
	kubectl apply -k deploy/kubernetes/overlays/$*
```

### Local Development Steps

1. **Clone and setup:**
   ```bash
   git clone git@github.com:farmerpower/farmer-power-platform.git
   cd farmer-power-platform
   make install
   ```

2. **Generate proto stubs:**
   ```bash
   make proto
   ```

3. **Start local infrastructure:**
   ```bash
   make local-up
   ```

4. **Run a specific service:**
   ```bash
   cd services/collection-model
   poetry run python -m collection_model.main
   ```

5. **Run tests:**
   ```bash
   make test
   # Or for a specific service:
   cd services/collection-model && pytest
   ```

## Testing Strategy

> **Full Details:** See `_bmad-output/test-design-system-level.md` for complete test strategy.

### Test Pyramid by Domain Model

| Component | Unit | Integration | Golden Sample | E2E |
|-----------|------|-------------|---------------|-----|
| Collection Model | 70% | 20% | - | 10% |
| Plantation Model | 60% | 30% | - | 10% |
| Knowledge Model | 50% | 30% | 20% | - |
| AI Model | 40% | 20% | 40% | - |
| Action Plan Model | 50% | 30% | - | 20% |
| Notification Model | 50% | 40% | - | 10% |
| Conversational AI | 40% | 40% | - | 20% |

### Test Framework Stack

| Tool | Purpose |
|------|---------|
| pytest | Test runner |
| pytest-asyncio | Async test support |
| testcontainers | MongoDB integration tests |
| Factory Boy | Test data factories |
| unittest.mock / AsyncMock | Mocking |
| httpx | HTTP mocking for external APIs |

### Golden Sample Testing (Critical for AI)

Golden samples are expert-validated input/output pairs used to test AI agent accuracy:

| Agent | Required Samples | Source |
|-------|------------------|--------|
| qc-event-extractor | 100+ | QC analyzer payloads |
| quality-triage | 100+ | Expert-classified cases |
| disease-diagnosis | 50+ | Agronomist-validated |
| weather-impact-analyzer | 30+ | Regional weather cases |
| technique-assessment | 30+ | Technique issues |
| action-plan-generator | 20+ | Sample outputs |

### Test Boundary Rules

```
ALWAYS MOCK (External):
├── LLM Providers (record/replay + golden samples)
├── Starfish Network API
├── Weather APIs
├── Africa's Talking SMS/Voice
├── Google Elevation API
└── Pinecone Vector DB

REAL FOR INTEGRATION, MOCK FOR UNIT (Internal):
├── MongoDB (testcontainers or in-memory)
├── DAPR Pub/Sub (in-memory component)
├── DAPR Service Invocation
└── MCP Servers

ALWAYS REAL:
├── Business logic functions
├── Pydantic model validation
├── Schema transformations
└── Error handling paths
```

### Quality Gates

| Gate | P0 Pass | P1 Pass | Golden Accuracy |
|------|---------|---------|-----------------|
| PR to feature | 100% | N/A | N/A |
| PR to main | 100% | 95% | 90%+ |
| Release candidate | 100% | 100% | 95%+ |

## Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Repository structure | Monorepo | Atomic changes, shared code, unified CI |
| Proto organization | Versioned directories (`v1/`) | API evolution support |
| Shared code | Internal Python packages in `libs/` | Easy dependency management |
| Build tool | Poetry with workspaces | Modern Python packaging |
| Container strategy | Multi-stage Dockerfile | Smaller images, cached layers |
| K8s deployment | Kustomize overlays | DRY config, environment separation |
| CI/CD | GitHub Actions with selective builds | Only rebuild changed services |
| Test framework | pytest + pytest-asyncio | Modern Python testing |
| AI testing | Golden sample framework | Critical for LLM accuracy validation |
| Mock boundaries | External always mocked | Deterministic, fast tests |
| MCP protocol | gRPC (not JSON-RPC) | Unified protocol, DAPR integration (see infrastructure-decisions.md) |
| MCP client code | Shared in `libs/fp-common/mcp/` | Reusable across AI Model and tests |

---

*This document should be reviewed and updated as the project evolves.*
