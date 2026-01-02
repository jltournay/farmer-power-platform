# ADR-002: Frontend Architecture

**Status:** Accepted
**Date:** 2025-12-26
**Deciders:** Winston (Architect), Jeanlouistournay
**Related Stories:** Epic 3 (Factory Manager Dashboard), Story 3.1-3.7

## Context

The Farmer Power Platform requires multiple web-based user interfaces serving distinct user roles:

| UI | User | Screens | Purpose |
|----|------|---------|---------|
| Factory Manager Dashboard | Quality Manager (Joseph) | 4 | Daily operations, farmer intervention |
| Factory Owner Dashboard | Factory Owner | 3 | ROI validation, subscription value |
| Factory Admin | Factory Administrator | 4 | Payment policies, SMS templates |
| Platform Admin | Farmer Power team | 4 | Factory onboarding, user management |
| Regulator Dashboard | Tea Board of Kenya | 4 | National quality intelligence |
| Farmer Registration | Registration Clerk | 4 | Farmer enrollment at collection points |

**Total: 6 distinct UIs, 23 web screens**

### Key Considerations

1. **Security isolation**: Regulator (government) requires complete separation
2. **Deployment model**: Registration runs on dedicated devices at collection points
3. **Code sharing**: All UIs share design system (Material UI v6, custom components)
4. **Team structure**: Single team initially, potential for parallel development later
5. **Network conditions**: Registration kiosks operate in rural Kenya with unreliable connectivity

## Decision

**Hybrid architecture with 4 frontend applications** grouped by security boundary and deployment context.

```
web/
├── factory-portal/          # Factory Manager + Owner + Admin
├── platform-admin/          # Internal Farmer Power team
├── regulator/               # Tea Board of Kenya (isolated)
└── registration-kiosk/      # Collection point devices (PWA)

libs/
└── ui-components/           # Shared component library
```

## Alternatives Considered

### Option A: Single React App with Role-Based Permissions

```
web/
└── dashboard/    # One app, all roles
```

| Pros | Cons |
|------|------|
| Single deployment | All code ships to all users |
| Easy code sharing | Admin code exists in browser (hidden) |
| Simple dev experience | Regulator cannot be isolated |
| | One bad deploy affects everyone |

**Rejected:** Security isolation requirements for Regulator (TBK) make this unacceptable.

### Option B: Separate App Per Role (6 Apps)

```
web/
├── factory-manager/
├── factory-owner/
├── factory-admin/
├── platform-admin/
├── regulator/
└── registration/
```

| Pros | Cons |
|------|------|
| Maximum isolation | 6 build pipelines |
| Independent deployments | Significant duplication |
| | Over-engineered for factory users |

**Rejected:** Factory Manager, Owner, and Admin share the same organizational context and authentication. Separating them adds complexity without benefit.

### Option C: Hybrid by Security Boundary (Selected)

Groups applications by:
- **Security boundary**: Regulator must be isolated
- **Deployment context**: Registration kiosk has unique requirements
- **User context**: Factory users share organizational data

## Application Structure

### 1. Factory Portal (`web/factory-portal/`)

**Users:** Factory Manager, Factory Owner, Factory Admin
**Screens:** 11 total (4 + 3 + 4)
**Type:** Standard React SPA

```
web/factory-portal/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── routes.tsx
│   │   └── providers/
│   │       ├── AuthProvider.tsx
│   │       └── ThemeProvider.tsx
│   │
│   ├── pages/
│   │   ├── manager/              # Joseph's screens
│   │   │   ├── CommandCenter/
│   │   │   ├── FarmerDetail/
│   │   │   ├── TemporalPatterns/
│   │   │   └── SMSPreview/
│   │   ├── owner/                # Factory Owner screens
│   │   │   ├── ROISummary/
│   │   │   ├── ROIDrillDown/
│   │   │   └── RegionalBenchmark/
│   │   └── admin/                # Factory Admin screens
│   │       ├── PaymentPolicy/
│   │       ├── GradeMultipliers/
│   │       ├── SMSTemplates/
│   │       └── ImpactCalculator/
│   │
│   ├── components/
│   │   └── [re-exports from @fp/ui-components]
│   │
│   ├── hooks/
│   │   ├── useFarmers.ts
│   │   ├── useQualityMetrics.ts
│   │   └── useReports.ts
│   │
│   ├── services/
│   │   ├── api.ts
│   │   ├── farmers.ts
│   │   └── reports.ts
│   │
│   ├── stores/
│   │   ├── authStore.ts
│   │   └── filtersStore.ts
│   │
│   └── types/
│
├── package.json
├── vite.config.ts
├── tsconfig.json
└── Dockerfile
```

**Role-based routing:**
```typescript
// routes.tsx
const routes = [
  // Manager routes (role: factory_manager, factory_owner, factory_admin)
  { path: '/command-center', element: <CommandCenter />, roles: ['factory_manager'] },
  { path: '/farmers/:id', element: <FarmerDetail />, roles: ['factory_manager', 'factory_owner'] },

  // Owner routes (role: factory_owner)
  { path: '/roi', element: <ROISummary />, roles: ['factory_owner'] },

  // Admin routes (role: factory_admin)
  { path: '/settings/payment', element: <PaymentPolicy />, roles: ['factory_admin'] },
];
```

### 2. Platform Admin (`web/platform-admin/`)

**Users:** Farmer Power internal team
**Screens:** 4
**Type:** Standard React SPA
**Access:** Internal network only / VPN required

```
web/platform-admin/
├── src/
│   ├── pages/
│   │   ├── Dashboard/
│   │   ├── FactoryOnboarding/
│   │   ├── UserManagement/
│   │   └── FactoryList/
│   └── ...
└── ...
```

### 3. Regulator Dashboard (`web/regulator/`)

**Users:** Tea Board of Kenya officials
**Screens:** 4
**Type:** Standard React SPA
**Access:** Completely isolated, separate authentication

```
web/regulator/
├── src/
│   ├── pages/
│   │   ├── NationalOverview/
│   │   ├── RegionalComparison/
│   │   ├── LeafTypeDistribution/
│   │   └── ExportReadiness/
│   └── ...
└── ...
```

**Isolation requirements:**
- Separate subdomain: `regulator.farmerpower.co.ke`
- Separate authentication (government SSO if required)
- No shared runtime state with other apps
- Read-only aggregated data (no individual farmer PII)

### 4. Registration Kiosk (`web/registration-kiosk/`)

**Users:** Registration Clerks at collection points
**Screens:** 4
**Type:** Progressive Web App (PWA)
**Deployment:** Dedicated tablets at collection points

```
web/registration-kiosk/
├── src/
│   ├── pages/
│   │   ├── PhoneVerification/
│   │   ├── FarmerDetails/
│   │   ├── CollectionPointAssignment/
│   │   └── IDCardPrint/
│   │
│   ├── services/
│   │   ├── offlineQueue.ts      # IndexedDB queue
│   │   ├── syncService.ts       # Background sync
│   │   └── printService.ts      # ID card printing
│   │
│   └── sw.ts                    # Service worker
│
├── vite.config.ts               # PWA plugin config
└── ...
```

**PWA requirements:**

| Requirement | Implementation |
|-------------|----------------|
| Offline-first | Service worker caches app shell |
| Offline data entry | IndexedDB stores registration queue |
| Background sync | Submits when connection restored |
| Installable | Web app manifest, install prompt |
| Printer support | Web Print API for ID cards |
| Long sessions | Refresh tokens, auto-renewal |

## Shared Component Library

```
libs/
└── ui-components/
    ├── src/
    │   ├── components/
    │   │   ├── StatusBadge/
    │   │   │   ├── StatusBadge.tsx
    │   │   │   ├── StatusBadge.test.tsx
    │   │   │   └── index.ts
    │   │   ├── TrendIndicator/
    │   │   ├── FarmerCard/
    │   │   ├── LeafTypeTag/
    │   │   ├── SMSPreview/
    │   │   ├── ROIMetricCard/
    │   │   └── ActionStrip/
    │   │
    │   ├── theme/
    │   │   ├── index.ts
    │   │   ├── palette.ts        # TBK color system
    │   │   ├── typography.ts
    │   │   └── components.ts     # MUI overrides
    │   │
    │   └── index.ts              # Public exports
    │
    ├── package.json              # @fp/ui-components
    └── tsconfig.json
```

**Usage in apps:**
```typescript
import { FarmerCard, StatusBadge, theme } from '@fp/ui-components';
```

## Technology Choices

| Category | Choice | Rationale |
|----------|--------|-----------|
| **Framework** | React 18 | Team familiarity, ecosystem, MUI compatibility |
| **Build tool** | Vite | Fast builds, native ESM, simple config |
| **Language** | TypeScript | Type safety, better DX, catches errors early |
| **Styling** | Material UI v6 + Emotion | Per UX spec, accessible, theme system |
| **State (local)** | Zustand | Simple, no boilerplate, TypeScript-first |
| **State (server)** | TanStack Query | Caching, background refresh, loading states |
| **Routing** | React Router v6 | Standard, well-documented |
| **Forms** | React Hook Form + Zod | Performant, validation, type inference |
| **Testing** | Vitest + Testing Library | Fast, Vite-compatible, user-centric |
| **PWA** | Vite PWA Plugin + Workbox | Service worker generation, caching strategies |

## Consequences

### Positive

- **Security**: Regulator dashboard completely isolated from factory data
- **Deployment flexibility**: Apps deploy independently
- **Optimized bundles**: Users only download code for their app
- **Offline capability**: Registration kiosk works in rural areas
- **Shared design system**: Consistent UX across all apps
- **Parallel development**: Teams can work on different apps simultaneously

### Negative

- **4 build pipelines**: More CI/CD configuration
- **Component library maintenance**: Need to publish/version shared components
- **SSO complexity**: Multiple apps need coordinated authentication
- **Initial setup overhead**: More boilerplate than single app

### Mitigations

| Risk | Mitigation |
|------|------------|
| Build complexity | Turborepo or Nx for monorepo orchestration |
| Component versioning | Keep in monorepo, no publishing needed |
| SSO | Shared auth library, same identity provider |
| Duplication | Strict component library discipline |

## Repository Structure Update

Add to `repository-structure.md`:

```
farmer-power-platform/
├── services/                    # Backend (existing)
│
├── web/                         # Frontend applications
│   ├── factory-portal/          # Manager + Owner + Admin
│   ├── platform-admin/          # Internal admin
│   ├── regulator/               # TBK dashboard
│   └── registration-kiosk/      # Collection point PWA
│
├── libs/                        # Shared libraries
│   ├── fp-common/               # Python (existing)
│   ├── fp-proto/                # Python (existing)
│   ├── fp-testing/              # Python (existing)
│   └── ui-components/           # React component library (NEW)
│
└── ...
```

## Build & Deployment

### Monorepo Tooling

```json
// package.json (root)
{
  "workspaces": [
    "web/*",
    "libs/*"
  ],
  "scripts": {
    "dev:factory": "npm -w web/factory-portal run dev",
    "dev:admin": "npm -w web/platform-admin run dev",
    "dev:regulator": "npm -w web/regulator run dev",
    "dev:kiosk": "npm -w web/registration-kiosk run dev",
    "build:all": "npm -ws run build",
    "test:all": "npm -ws run test"
  }
}
```

### Deployment Targets

| App | URL | Hosting |
|-----|-----|---------|
| factory-portal | `app.farmerpower.co.ke` | Azure Static Web Apps |
| platform-admin | `admin.farmerpower.co.ke` | Azure Static Web Apps (internal) |
| regulator | `regulator.farmerpower.co.ke` | Azure Static Web Apps (isolated) |
| registration-kiosk | `register.farmerpower.co.ke` | Azure Static Web Apps + PWA |

## BFF Service Architecture (Addendum - 2026-01)

### Overview

The BFF (Backend for Frontend) service acts as the API gateway between web frontends and domain model services. This section documents the connectivity patterns, DAPR integration, and infrastructure configuration.

### Connectivity Pattern

```
┌─────────────┐     HTTP/REST      ┌─────────────┐      DAPR gRPC      ┌──────────────────┐
│   Browser   │ ─────────────────► │     BFF     │ ──────────────────► │  Domain Models   │
│  (React)    │                    │  (FastAPI)  │                     │                  │
└─────────────┘                    └──────┬──────┘                     │  - Plantation    │
                                          │                            │  - Collection    │
                                          ▼                            │  - Engagement    │
                                   ┌──────────────┐                    │  - AI Model      │
                                   │ DAPR Sidecar │◄───────────────────┘
                                   │  (daprd)     │
                                   └──────────────┘
```

**Layer Responsibilities:**

| Layer | Protocol | Responsibility |
|-------|----------|----------------|
| Browser → BFF | HTTP/REST (JSON) | User-facing API, aggregation, auth |
| BFF → DAPR Sidecar | gRPC (localhost) | Service invocation request |
| DAPR → Domain Model | gRPC (via service mesh) | Cross-service communication |

### DAPR Sidecar Configuration

**BFF Service DAPR Configuration:**

```yaml
# services/bff/dapr/config.yaml
apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: bff-config
spec:
  tracing:
    samplingRate: "1"
    otel:
      endpointAddress: "otel-collector:4317"
      isSecure: false
      protocol: grpc
  metric:
    enabled: true
```

**Component Registration:**

| Component | Purpose | Configuration |
|-----------|---------|---------------|
| Service Discovery | Find backend services by app-id | Kubernetes DNS |
| Observability | Distributed tracing | OpenTelemetry collector |
| Resiliency | Circuit breaker, retry | Per-service policies |

**DAPR Sidecar Ports:**

| Port | Protocol | Purpose |
|------|----------|---------|
| 3500 | HTTP | DAPR HTTP API (health checks, metadata) |
| 50001 | gRPC | DAPR gRPC API (service invocation) |
| 8080 | HTTP | BFF FastAPI application port |

### Service Invocation Pattern

**Python Code Pattern (BFF calling Domain Models):**

```python
# services/bff/src/bff/infrastructure/dapr_client.py
from dapr.clients import DaprClient
from dapr.clients.grpc._response import InvokeMethodResponse

from fp_proto.plantation.v1 import plantation_pb2

class PlantationClient:
    """DAPR-based client for Plantation Model."""

    def __init__(self, dapr_grpc_port: int = 50001):
        self.dapr_grpc_port = dapr_grpc_port

    async def get_farmer(self, farmer_id: str) -> plantation_pb2.Farmer:
        """Get farmer by ID via DAPR service invocation."""
        async with DaprClient(f"localhost:{self.dapr_grpc_port}") as client:
            request = plantation_pb2.GetFarmerRequest(id=farmer_id)

            response: InvokeMethodResponse = await client.invoke_method(
                app_id="plantation-model",
                method_name="plantation.v1.PlantationService/GetFarmer",
                data=request.SerializeToString(),
                content_type="application/grpc",
            )

            farmer = plantation_pb2.Farmer()
            farmer.ParseFromString(response.data)
            return farmer

    async def list_farmers(
        self,
        factory_id: str,
        page_size: int = 50,
        page_token: str = ""
    ) -> plantation_pb2.ListFarmersResponse:
        """List farmers with pagination."""
        async with DaprClient(f"localhost:{self.dapr_grpc_port}") as client:
            request = plantation_pb2.ListFarmersRequest(
                factory_id=factory_id,
                page_size=page_size,
                page_token=page_token,
            )

            response = await client.invoke_method(
                app_id="plantation-model",
                method_name="plantation.v1.PlantationService/ListFarmers",
                data=request.SerializeToString(),
                content_type="application/grpc",
            )

            result = plantation_pb2.ListFarmersResponse()
            result.ParseFromString(response.data)
            return result
```

### Proto Dependencies

**BFF requires these proto packages from `libs/fp-proto`:**

| Proto Package | Purpose | Key Messages |
|---------------|---------|--------------|
| `farmer_power.plantation.v1` | Master data | Farmer, Factory, Region |
| `farmer_power.collection.v1` | Quality events | QualityEvent, Delivery |
| `farmer_power.engagement.v1` | Interventions | Intervention, SMSMessage |

### Backend Service gRPC Requirements

**CRITICAL DEPENDENCY:** All domain models consumed by BFF must expose gRPC services.

| Service | gRPC Service | Status | Action Required |
|---------|--------------|--------|-----------------|
| Plantation Model | `PlantationService` | ✅ Implemented | None |
| Collection Model | `CollectionService` | ❌ **MISSING** | **Must implement before BFF** |
| Engagement Model | `EngagementService` | ⏳ Planned | Implement with Epic 4 |
| AI Model | `AIModelService` | ⏳ Planned | Implement with Epic 4 |

#### Collection Model gRPC Gap

**Problem:** Collection Model currently exposes only:
- HTTP/REST endpoints (FastAPI)
- MCP server interface (for AI agents)
- DAPR pub/sub events

**Why MCP is NOT suitable for BFF:**

| Aspect | gRPC | MCP |
|--------|------|-----|
| Pagination | Native support | Not supported |
| Binary efficiency | Protobuf (compact) | JSON-RPC (verbose) |
| Streaming | Bidirectional streams | Not designed for it |
| Use case | Service-to-service | AI agent tool calls |

**Required: Story 0.5.0 - Collection Model gRPC Service Layer**

Add to `proto/collection/v1/collection.proto`:

```protobuf
service CollectionService {
  // Quality event queries
  rpc GetQualityEvent(GetQualityEventRequest) returns (QualityEvent);
  rpc ListQualityEvents(ListQualityEventsRequest) returns (ListQualityEventsResponse);

  // Delivery queries
  rpc GetDelivery(GetDeliveryRequest) returns (Delivery);
  rpc ListDeliveries(ListDeliveriesRequest) returns (ListDeliveriesResponse);

  // Aggregations for dashboard
  rpc GetFarmerQualitySummary(GetFarmerQualitySummaryRequest) returns (FarmerQualitySummary);
  rpc GetFactoryDailySummary(GetFactoryDailySummaryRequest) returns (FactoryDailySummary);
}
```

### Real-Time Updates (WebSocket Decision)

**Decision: WebSocket NOT REQUIRED - SSE Sufficient for MVP**

#### UX Analysis Summary

A comprehensive review of all 24 web screens across 6 UI modules found **zero use cases requiring WebSocket**:

| UI Module | Screens | WebSocket Need | Pattern |
|-----------|---------|----------------|---------|
| Factory Manager Dashboard | 4 | ❌ No | "Opens dashboard each morning" - batch view |
| Factory Owner Dashboard | 3 | ❌ No | "Monthly email report" - periodic review |
| Regulator Dashboard | 4 | ❌ No | Quarterly aggregates |
| Factory Admin | 5 | ❌ No | Config with "7-day notification period" |
| Platform Admin | 4 | ❌ No | Onboarding wizard - form-based |
| Farmer Registration | 4 | ❌ No | "Works offline with sync when connected" |

#### Why WebSocket is Not Needed

**1. Batch Processing Design:**
The platform processes quality events in batches, not real-time:
```
Farmer delivers (11 AM) → Factory grades (2 PM) → SMS sent (3 PM) → Farmer reads (evening)
```
A 3-4 hour delay is built into the core feedback loop by design.

**2. Periodic Review Patterns:**
- Joseph (Quality Manager): Daily dashboard review
- Factory Owner: Monthly/Quarterly ROI reports
- Regulator: Quarterly national aggregates

**3. Offline-First Design:**
Registration kiosk explicitly designed to "work offline with sync when connected" - queue-based, not WebSocket.

**4. No Collaborative Features:**
No use cases found for:
- Real-time collaboration (multiple users editing)
- Presence indicators ("X is viewing...")
- Live chat or messaging
- Typing indicators or live cursors

#### WebSocket Indicators NOT Found in UX Specification

| Indicator | Present? | Evidence |
|-----------|----------|----------|
| "live" or "real-time" keywords | ❌ No | Searched all UX docs |
| Collaborative editing | ❌ No | All admin interfaces are single-user |
| Presence indicators | ❌ No | Joseph works alone on dashboard |
| Chat/messaging features | ❌ No | Communication via SMS/Voice IVR (async) |
| Sub-second update requirements | ❌ No | Batch processing with hours delay |

#### Recommended Approach

| Requirement | Solution | Rationale |
|-------------|----------|-----------|
| Dashboard data refresh | Manual refresh or polling (60s) | User-initiated per UX spec |
| New ACTION NEEDED notification | SSE (optional) | One-way push sufficient |
| Report ready notification | SSE (optional) | Badge notification pattern |
| SMS send confirmation | REST response | Immediate feedback after POST |

#### SSE Implementation (If Needed)

Server-Sent Events can be added for optional push notifications:

```python
# services/bff/src/bff/api/routes/events.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.get("/events/factory/{factory_id}")
async def factory_events(factory_id: str):
    """SSE stream for factory dashboard updates (optional)."""
    async def event_generator():
        # Subscribe to DAPR pub/sub topic
        async for event in subscribe_to_factory_events(factory_id):
            yield f"data: {event.json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

#### Future Considerations

If bi-directional communication is required in future epics (not currently planned):
1. Document the specific use case and UX requirement
2. Add `stream` RPC methods to domain model protos
3. BFF translates gRPC streams to WebSocket
4. Update this ADR with the new decision

### Docker Compose Configuration (E2E Testing)

**BFF + DAPR Sidecar in E2E Infrastructure:**

```yaml
# tests/e2e/infrastructure/docker-compose.e2e.yaml

services:
  # BFF Service
  bff:
    build:
      context: ../../..
      dockerfile: services/bff/Dockerfile
    ports:
      - "8080:8080"
    environment:
      - APP_ENV=test
      - AUTH_PROVIDER=mock
      - MOCK_JWT_SECRET=test-secret-for-e2e
      - DAPR_HTTP_PORT=3500
      - DAPR_GRPC_PORT=50001
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    depends_on:
      - placement
      - redis
    networks:
      - farmer-power-e2e

  # BFF DAPR Sidecar
  bff-dapr:
    image: daprio/daprd:1.12
    command:
      - "./daprd"
      - "--app-id=bff"
      - "--app-port=8080"
      - "--dapr-http-port=3500"
      - "--dapr-grpc-port=50001"
      - "--placement-host-address=placement:50006"
      - "--resources-path=/components"
      - "--config=/config/config.yaml"
    volumes:
      - ./dapr-components:/components
      - ./dapr-config:/config
    network_mode: "service:bff"
    depends_on:
      - bff

  # DAPR Placement Service (for actor support)
  placement:
    image: daprio/dapr:1.12
    command: ["./placement", "--port", "50006"]
    ports:
      - "50006:50006"
    networks:
      - farmer-power-e2e

networks:
  farmer-power-e2e:
    driver: bridge
```

**DAPR Components for E2E:**

```yaml
# tests/e2e/infrastructure/dapr-components/pubsub.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
spec:
  type: pubsub.redis
  version: v1
  metadata:
    - name: redisHost
      value: "redis:6379"
```

### Resiliency Configuration

**Circuit Breaker and Retry Policies:**

```yaml
# services/bff/dapr/resiliency.yaml
apiVersion: dapr.io/v1alpha1
kind: Resiliency
metadata:
  name: bff-resiliency
spec:
  policies:
    timeouts:
      general: 5s
      slow-service: 10s

    retries:
      retryForever:
        policy: constant
        maxInterval: 5s
        maxRetries: -1

      standard:
        policy: exponential
        maxInterval: 10s
        maxRetries: 3

    circuitBreakers:
      simpleCB:
        maxRequests: 1
        interval: 30s
        timeout: 60s
        trip: consecutiveFailures >= 5

  targets:
    apps:
      plantation-model:
        timeout: general
        retry: standard
        circuitBreaker: simpleCB

      collection-model:
        timeout: general
        retry: standard
        circuitBreaker: simpleCB
```

### BFF Internal Code Structure

The BFF (Backend for Frontend) service follows the project's layered architecture pattern but adapts it for its specific role as an API gateway.

#### BFF vs Backend Services

| Aspect | Backend Service (e.g., plantation-model) | BFF Service |
|--------|------------------------------------------|-------------|
| Exposes | gRPC server | HTTP REST only |
| Database | Owns MongoDB collections | No database (stateless) |
| Events | Publishes DAPR events | Consumes events (optional SSE) |
| Models | Owns domain models | Transforms/aggregates data |
| Called by | BFF, MCP servers | Browser (React frontend) |

#### Directory Structure

```
services/bff/
├── src/
│   └── bff/
│       ├── __init__.py
│       ├── main.py                      # FastAPI app entrypoint
│       ├── config.py                    # Environment configuration
│       │
│       ├── api/                         # HTTP REST API layer
│       │   ├── __init__.py
│       │   ├── routes/                  # Route handlers by domain
│       │   │   ├── __init__.py
│       │   │   ├── farmers.py           # /api/farmers/*
│       │   │   ├── factories.py         # /api/factories/*
│       │   │   ├── quality.py           # /api/quality/*
│       │   │   ├── dashboard.py         # /api/dashboard/*
│       │   │   └── health.py            # /health, /ready
│       │   ├── middleware/              # Request processing
│       │   │   ├── __init__.py
│       │   │   ├── auth.py              # JWT validation
│       │   │   ├── error_handler.py     # Global error handling
│       │   │   └── request_id.py        # Request tracing
│       │   └── schemas/                 # Pydantic request/response models
│       │       ├── __init__.py
│       │       ├── farmer_schemas.py
│       │       ├── quality_schemas.py
│       │       └── dashboard_schemas.py
│       │
│       ├── infrastructure/              # External service clients
│       │   ├── __init__.py
│       │   ├── clients/                 # DAPR service invocation clients
│       │   │   ├── __init__.py
│       │   │   ├── base.py              # Base DAPR client
│       │   │   ├── plantation_client.py # Calls plantation-model
│       │   │   └── collection_client.py # Calls collection-model
│       │   ├── auth/                    # Authentication providers
│       │   │   ├── __init__.py
│       │   │   ├── jwt_validator.py     # JWT token validation
│       │   │   └── mock_auth.py         # Mock auth for E2E tests
│       │   └── tracing.py               # OpenTelemetry setup
│       │
│       ├── services/                    # Business logic / orchestration
│       │   ├── __init__.py
│       │   ├── farmer_service.py        # Farmer data aggregation
│       │   ├── dashboard_service.py     # Dashboard data composition
│       │   └── quality_service.py       # Quality data transformation
│       │
│       └── transformers/                # Proto ↔ JSON transformers
│           ├── __init__.py
│           ├── farmer_transformer.py    # Farmer proto → JSON
│           ├── quality_transformer.py   # QualityEvent proto → JSON
│           └── pagination.py            # Page token handling
│
├── dapr/                                # DAPR configuration
│   ├── config.yaml                      # DAPR app config
│   └── resiliency.yaml                  # Circuit breaker, retry
│
├── Dockerfile
├── pyproject.toml
└── README.md
```

#### Layer Responsibilities

| Layer | Location | Responsibility |
|-------|----------|----------------|
| **Routes** | `api/routes/` | HTTP request handling, parameter validation, call services |
| **Middleware** | `api/middleware/` | Cross-cutting: authentication, error handling, tracing |
| **Schemas** | `api/schemas/` | Pydantic models defining JSON request/response contracts |
| **Clients** | `infrastructure/clients/` | DAPR gRPC calls to backend services |
| **Auth** | `infrastructure/auth/` | JWT validation, mock auth for testing |
| **Services** | `services/` | Business orchestration, aggregate data from multiple backends |
| **Transformers** | `transformers/` | Convert proto messages ↔ JSON responses |

#### Data Flow

```
Browser Request (JSON)
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│  api/middleware/auth.py              Validate JWT token         │
│      │                                                          │
│      ▼                                                          │
│  api/routes/farmers.py               Parse request, validate    │
│      │                                                          │
│      ▼                                                          │
│  services/farmer_service.py          Orchestrate backend calls  │
│      │                                                          │
│      ├──► infrastructure/clients/plantation_client.py           │
│      │         │                                                │
│      │         └──► DAPR gRPC ──► plantation-model              │
│      │                                                          │
│      └──► infrastructure/clients/collection_client.py           │
│                │                                                │
│                └──► DAPR gRPC ──► collection-model              │
│      │                                                          │
│      ▼                                                          │
│  transformers/farmer_transformer.py  Proto → JSON               │
│      │                                                          │
│      ▼                                                          │
│  api/schemas/farmer_schemas.py       Validate response model    │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
JSON Response to Browser
```

#### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No `domain/` layer** | BFF doesn't own domain models - it transforms data from backend services |
| **`transformers/` instead of `domain/`** | Clear single purpose: convert proto messages to browser-friendly JSON |
| **`services/` for orchestration** | Aggregates and combines data from multiple backend services |
| **`api/schemas/` for contracts** | Defines the JSON API contract for the React frontend |
| **Separate `clients/` per backend** | One client class per backend service for clear dependencies |
| **`dapr/` at service root** | DAPR configuration lives with the service, outside `src/` |
| **Stateless design** | No database, no in-memory state - enables horizontal scaling |

#### File Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Route modules | `{domain}.py` | `farmers.py`, `quality.py` |
| Client classes | `{service}_client.py` | `plantation_client.py` |
| Service classes | `{domain}_service.py` | `farmer_service.py` |
| Transformer classes | `{domain}_transformer.py` | `farmer_transformer.py` |
| Schema modules | `{domain}_schemas.py` | `farmer_schemas.py` |

#### Test Mapping

| BFF Module | Test Location |
|------------|---------------|
| `api/routes/` | `tests/unit/bff/test_*_route.py` |
| `api/middleware/` | `tests/unit/bff/test_middleware.py` |
| `infrastructure/clients/` | `tests/unit/bff/test_*_client.py` |
| `services/` | `tests/unit/bff/test_*_service.py` |
| `transformers/` | `tests/unit/bff/test_*_transformer.py` |
| BFF ↔ Backend integration | `tests/integration/test_bff_*.py` |

### Frontend Test Policy

#### Test Pyramid

```
                    ┌─────────────────────┐
                    │   E2E (Browser)     │  5%
                    │   Playwright        │
                    ├─────────────────────┤
                    │  Visual Regression  │  10%
                    │  Storybook+Snapshot │
                    ├─────────────────────┤
                    │   Integration       │  25%
                    │   BFF+DAPR Mocks    │
                    ├─────────────────────┤
                    │      Unit Tests     │  60%
                    │  Components + Hooks │
                    └─────────────────────┘
```

| Layer | Coverage Target | Tools | Focus |
|-------|-----------------|-------|-------|
| **Unit (React)** | 60% | Vitest + React Testing Library | Components, hooks, utilities |
| **Unit (BFF)** | 60% | pytest + httpx | Route handlers, transformers |
| **Integration** | 25% | pytest + DAPR mocks | BFF ↔ Backend communication |
| **Visual Regression** | All shared components | Storybook + snapshots | Component appearance |
| **E2E (Browser)** | Key user journeys | Playwright | Full user flows |
| **Accessibility** | All pages | axe-playwright | WCAG 2.1 AA |

#### Test Directory Structure (Centralized)

Following the project's centralized test pattern:

```
tests/
├── unit/
│   ├── bff/                          # BFF unit tests
│   │   ├── __init__.py
│   │   ├── test_farmers_route.py
│   │   ├── test_dapr_client.py
│   │   └── test_transformers.py
│   └── web/                          # React component tests (Vitest)
│       ├── test_farmer_card.test.ts
│       ├── test_action_strip.test.ts
│       └── test_hooks.test.ts
├── integration/
│   ├── test_bff_plantation.py        # BFF ↔ Plantation integration
│   └── test_bff_collection.py        # BFF ↔ Collection integration
├── e2e/
│   ├── scenarios/                    # Backend E2E (existing)
│   └── browser/                      # Frontend browser E2E
│       ├── test_dashboard.spec.ts    # Playwright tests
│       └── test_farmer_detail.spec.ts
├── visual/                           # Visual regression snapshots
│   └── snapshots/
└── fixtures/
    └── web/                          # Frontend test fixtures
        ├── mock_farmers.json
        └── mock_quality_events.json
```

#### Storybook Configuration

**What is Storybook?**

Storybook is a visual catalog for UI components - a "museum gallery" where each component is displayed in all its possible states. It enables:
- Developing components in isolation
- Visual documentation for designers and PMs
- Visual regression testing (screenshot comparison)

**Storybook stories live with components (exception to centralized tests):**

```
web/libs/ui-components/src/
├── FarmerCard/
│   ├── FarmerCard.tsx
│   ├── FarmerCard.stories.tsx        # Storybook stories (visual docs)
│   └── index.ts
```

**Story file example:**

```typescript
// FarmerCard.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { FarmerCard } from './FarmerCard';

const meta: Meta<typeof FarmerCard> = {
  component: FarmerCard,
  title: 'Components/FarmerCard',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof FarmerCard>;

export const ActionNeeded: Story = {
  args: {
    farmer: {
      id: 'WM-4521',
      name: 'Mama Wanjiku',
      primaryPercent: 58,
      category: 'ACTION_NEEDED',
    },
  },
};

export const Watch: Story = {
  args: {
    farmer: {
      id: 'WM-4521',
      name: 'Mama Wanjiku',
      primaryPercent: 74,
      category: 'WATCH',
    },
  },
};

export const Win: Story = {
  args: {
    farmer: {
      id: 'WM-4521',
      name: 'Mama Wanjiku',
      primaryPercent: 88,
      category: 'WIN',
    },
  },
};
```

**Required stories for each shared component:**

| Component | Required Stories |
|-----------|------------------|
| FarmerCard | ACTION_NEEDED, WATCH, WIN, Loading, Error |
| StatusBadge | All TBK categories |
| ActionStrip | Empty, Few items, Many items |
| QualityChart | With data, Empty state, Loading |

#### React Component Testing

**Unit test pattern (in `tests/unit/web/`):**

```typescript
// tests/unit/web/test_farmer_card.test.ts
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FarmerCard } from '@fp/ui-components';

describe('FarmerCard', () => {
  const mockFarmer = {
    id: 'WM-4521',
    name: 'Mama Wanjiku',
    primaryPercent: 58,
    category: 'ACTION_NEEDED',
  };

  it('renders farmer name', () => {
    render(<FarmerCard farmer={mockFarmer} />);
    expect(screen.getByText('Mama Wanjiku')).toBeInTheDocument();
  });

  it('shows ACTION NEEDED badge for <70% primary', () => {
    render(<FarmerCard farmer={mockFarmer} />);
    expect(screen.getByRole('status')).toHaveTextContent('ACTION NEEDED');
  });

  it('calls onAssign when assign button clicked', async () => {
    const onAssign = vi.fn();
    render(<FarmerCard farmer={mockFarmer} onAssign={onAssign} />);

    await userEvent.click(screen.getByRole('button', { name: /assign/i }));

    expect(onAssign).toHaveBeenCalledWith('WM-4521');
  });

  it('is accessible - has proper ARIA attributes', () => {
    render(<FarmerCard farmer={mockFarmer} />);
    expect(screen.getByRole('article')).toHaveAttribute('aria-label');
  });
});
```

#### BFF Service Testing

**Unit test pattern (in `tests/unit/bff/`):**

```python
# tests/unit/bff/test_farmers_route.py
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

from bff.main import app
from fp_proto.plantation.v1 import plantation_pb2


@pytest.fixture
def mock_plantation_client(mocker):
    """Mock the DAPR-based Plantation client."""
    client = AsyncMock()
    mocker.patch('bff.infrastructure.dapr_client.PlantationClient', return_value=client)
    return client


@pytest.mark.asyncio
async def test_list_farmers_returns_paginated_results(
    test_client: AsyncClient,
    mock_plantation_client: AsyncMock,
):
    """GET /api/farmers returns paginated farmer list."""
    # Arrange
    mock_farmer = plantation_pb2.Farmer(
        id="WM-4521",
        first_name="Wanjiku",
        last_name="Muthoni",
    )
    mock_plantation_client.list_farmers.return_value = plantation_pb2.ListFarmersResponse(
        farmers=[mock_farmer],
        next_page_token="token123",
    )

    # Act
    response = await test_client.get("/api/farmers?factory_id=FAC-001&page_size=10")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["farmers"]) == 1
    assert data["farmers"][0]["id"] == "WM-4521"
    assert data["next_page_token"] == "token123"


@pytest.mark.asyncio
async def test_list_farmers_requires_factory_id(test_client: AsyncClient):
    """GET /api/farmers without factory_id returns 422."""
    response = await test_client.get("/api/farmers")
    assert response.status_code == 422
```

#### Browser E2E Testing

**Playwright test pattern (in `tests/e2e/browser/`):**

```typescript
// tests/e2e/browser/test_dashboard.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Factory Manager Dashboard', () => {

  test.beforeEach(async ({ page }) => {
    // Login or set auth token
    await page.goto('/');
  });

  test('shows ACTION NEEDED section with farmer count', async ({ page }) => {
    const actionSection = page.getByTestId('action-needed-section');

    await expect(actionSection).toBeVisible();
    await expect(actionSection.getByRole('heading')).toContainText('ACTION NEEDED');
    await expect(actionSection.getByTestId('farmer-count')).toBeVisible();
  });

  test('clicking farmer card navigates to detail view', async ({ page }) => {
    // Click first farmer card
    await page.getByTestId('farmer-card').first().click();

    // Verify navigation
    await expect(page).toHaveURL(/\/farmers\//);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('dashboard has no accessibility violations', async ({ page }) => {
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });
});
```

**Key user journeys to test:**

| Journey | Priority | Epic |
|---------|----------|------|
| Joseph opens dashboard, sees ACTION NEEDED count | P0 | 0.5 |
| Joseph clicks farmer card, views detail | P0 | 0.5 |
| Joseph assigns extension officer | P1 | 0.5 |
| Factory Owner views ROI summary | P1 | 3 |

#### Visual Regression Process

**How visual regression works:**

1. **Baseline**: Screenshots taken from Storybook stories
2. **On PR**: New screenshots compared to baseline
3. **Diff detected**: Highlighted for human review
4. **Approve/Reject**: Human decides if change is intentional

**Visual validation workflow:**

```
Developer creates component
        ↓
Writes Storybook stories (all states)
        ↓
Runs `npm run storybook` locally
        ↓
Reviews visually + shares with designer
        ↓
Takes baseline snapshots
        ↓
PR triggers snapshot comparison
        ↓
Visual changes require approval
```

**Snapshot storage (in `tests/visual/snapshots/`):**

```
tests/visual/snapshots/
├── farmer-card/
│   ├── action-needed.png
│   ├── watch.png
│   └── win.png
├── status-badge/
│   └── all-states.png
└── action-strip/
    └── default.png
```

#### Accessibility Testing Requirements

**Automated checks (every PR):**

```typescript
// Run axe-core on all pages
const results = await new AxeBuilder({ page })
  .withTags(['wcag2a', 'wcag2aa'])
  .analyze();

expect(results.violations).toEqual([]);
```

**Manual checklist (per component):**

- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] Focus indicators visible (3px Forest Green outline)
- [ ] Screen reader announces correctly
- [ ] Color not sole indicator (icon + text + color)
- [ ] Touch targets ≥44px on mobile

#### CI Pipeline Configuration

```yaml
# .github/workflows/frontend-tests.yaml
name: Frontend Tests

on:
  pull_request:
    paths:
      - 'web/**'
      - 'services/bff/**'
      - 'tests/unit/web/**'
      - 'tests/unit/bff/**'
      - 'tests/e2e/browser/**'

jobs:
  unit-tests-react:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd web && npm ci
      - run: cd web && npm run test:unit -- --coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  unit-tests-bff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e services/bff[test]
      - run: pytest tests/unit/bff/ -v --cov

  storybook-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: cd web && npm ci
      - run: cd web && npm run build-storybook
      - name: Visual regression (snapshot comparison)
        run: cd web && npm run test:visual

  e2e-browser:
    runs-on: ubuntu-latest
    needs: [unit-tests-react, unit-tests-bff]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npx playwright install --with-deps
      - run: npm run test:e2e:browser
```

#### Quality Gates

| Gate | Unit (React) | Unit (BFF) | Visual | E2E | Accessibility |
|------|--------------|------------|--------|-----|---------------|
| PR to feature | 100% pass | 100% pass | Review | N/A | N/A |
| PR to main | 100% pass | 100% pass | Approved | 100% pass | 0 critical |
| Release | 100% pass | 100% pass | Approved | 100% pass | WCAG 2.1 AA |

### Component Specification Reference

This section provides a single source of truth for locating React component specifications.

#### Authoritative Documents

| Document | Location | Content |
|----------|----------|---------|
| **Component Strategy** | `_bmad-output/ux-design-specification/6-component-strategy.md` | Props interfaces, visual anatomy, variants |
| **UX Consistency Patterns** | `_bmad-output/ux-design-specification/7-ux-consistency-patterns.md` | Interaction patterns, feedback, forms |
| **Design System Foundation** | `_bmad-output/ux-design-specification/design-system-foundation.md` | Color tokens, typography, spacing |

#### Component Catalog

| Component | Priority | Spec Location | Required Stories | Accessibility |
|-----------|----------|---------------|------------------|---------------|
| **StatusBadge** | P0 | 6-component-strategy.md §6.2 | win, watch, action | `role="status"`, `aria-label` |
| **TrendIndicator** | P0 | 6-component-strategy.md §6.2 | up, down, stable | Icon + text (color not sole indicator) |
| **FarmerCard** | P0 | 6-component-strategy.md §6.2 | default, hover, selected, assigned | `role="article"`, keyboard nav |
| **LeafTypeTag** | P0 | 6-component-strategy.md §6.2 | All leaf types | Tooltip on focus (not just hover) |
| **ActionStrip** | P0 | 6-component-strategy.md §6.2 | empty, selected states | Keyboard navigation between sections |
| **SMSPreview** | P1 | 6-component-strategy.md §6.2 | win, watch, action, first_delivery | Screen reader friendly |
| **ROIMetricCard** | P1 | 6-component-strategy.md §6.2 | With/without secondary metric | Chart has text summary |

#### Design Tokens (MUI v6 Theme)

```typescript
// web/libs/ui-components/src/theme/farmerPowerTheme.ts
import { createTheme } from '@mui/material/styles';

export const farmerPowerTheme = createTheme({
  palette: {
    primary: { main: '#1B4332' },      // Forest Green
    secondary: { main: '#5C4033' },    // Earth Brown
    warning: { main: '#D4A03A' },      // Harvest Gold
    error: { main: '#C1292E' },        // Warm Red
    success: { main: '#1B4332' },      // Forest Green (WIN)
    background: {
      default: '#FFFDF9',              // Warm White
      paper: '#FFFFFF'
    },
  },
  typography: {
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  shape: {
    borderRadius: 6,
  },
});

// Status-specific tokens
export const statusColors = {
  win: { bg: '#D8F3DC', text: '#1B4332', icon: '✅' },
  watch: { bg: '#FFF8E7', text: '#D4A03A', icon: '⚠️' },
  action: { bg: '#FFE5E5', text: '#C1292E', icon: '🔴' },
};
```

#### Component Implementation Checklist

Before marking a shared component as "done", verify:

- [ ] **Props interface** matches spec in `6-component-strategy.md`
- [ ] **Visual anatomy** matches ASCII diagram in spec
- [ ] **All variants** have Storybook stories
- [ ] **Accessibility** requirements implemented (ARIA, keyboard nav)
- [ ] **Unit tests** in `tests/unit/web/`
- [ ] **Visual snapshot** baseline captured
- [ ] **Design review** approved by UX (Sally or equivalent)

### Summary: Implementation Prerequisites

Before Epic 0.5 stories can proceed, the following must be completed:

| Prerequisite | Owner | Deliverable |
|--------------|-------|-------------|
| Collection Model gRPC Service | Backend Team | Story 0.5.0 |
| BFF DAPR configuration files | Architect | `services/bff/dapr/` |
| E2E Docker Compose update | DevOps/QA | `docker-compose.e2e.yaml` |
| Proto compilation for BFF | Backend Team | `libs/fp-proto` update |
| Frontend test infrastructure | Frontend Team | Vitest + Storybook + Playwright setup |

## References

- [UI & Screens Inventory](../_bmad-output/ux-design-specification/ui-screens-inventory.md)
- [UX Design Specification](../_bmad-output/ux-design-specification/index.md)
- [Design System Foundation](../_bmad-output/ux-design-specification/design-system-foundation.md)
- [Component Strategy](../_bmad-output/ux-design-specification/6-component-strategy.md)
- [DAPR Service Invocation](https://docs.dapr.io/developing-applications/building-blocks/service-invocation/)
- [DAPR Python SDK](https://docs.dapr.io/developing-applications/sdks/python/)
- [gRPC + DAPR Best Practices](https://docs.dapr.io/operations/configuration/grpc/)
- Epic 3: Factory Manager Dashboard
