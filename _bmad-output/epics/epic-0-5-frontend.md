## Epic 0.5: Frontend & BFF Infrastructure

**Priority:** P1

**Dependencies:** Epic 0 (Infrastructure), Epic 0.4 (Collection Model)

Cross-cutting frontend and BFF infrastructure that enables all web applications. These stories establish the BFF service, shared component library, authentication flow, and foundational frontend patterns.

**Related ADRs:**
- ADR-002 (Frontend Architecture) - BFF structure, component library, test policy
- ADR-003 (Identity & Access Management) - Mock-first authentication strategy

**Scope:**
- Collection Model gRPC service layer (prerequisite for BFF)
- BFF DAPR clients for Plantation and Collection models
- BFF Service with FastAPI REST endpoints
- BFF Authentication middleware (mock + B2C modes)
- Shared React component library (@fp/ui-components)
- Shared authentication library (@fp/auth)
- Factory Portal application scaffold

---

## Development Strategy

### Backend-First Approach

**Decision:** Implement BFF backend before React frontend components.

**Benefits:**
- E2E testable after BFF completion (curl/Postman against real APIs)
- Contract-first development (frontend knows exact API shape)
- Parallel work possible (backend team finishes, frontend team starts)
- No mocking BFF in frontend tests (real APIs available)

### Mock-First Authentication

**Decision:** Implement mock authentication for local development, with Azure AD B2C deferred until production deployment.

**Benefits:**
- Build and test without Azure configuration
- Quick persona switching for role-based testing
- Offline development capability
- Same interface - swap to B2C via config change

**Reference:** ADR-003 "Development Authentication Strategy (Mock-First)"

---

## Story Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: gRPC Foundation                                       │
│  └── Story 0.5.1: Collection gRPC + BFF Clients                 │
│           │                                                     │
│           ▼                                                     │
│  PHASE 2: BFF Service (Backend Complete → E2E Testable)         │
│  └── Story 0.5.2: BFF Service Setup                             │
│           │                                                     │
│           ▼                                                     │
│  └── Story 0.5.3: BFF Auth Middleware                           │
│           │                                                     │
│           ▼                                                     │
│  └── Story 0.5.4: BFF API Routes                                │
│           │                                                     │
│           ▼                                                     │
│  PHASE 3: Frontend Foundation                                   │
│  ├── Story 0.5.5: Shared Component Library ──┐                  │
│  │                                           │                  │
│  ├── Story 0.5.6: Shared Auth Library ───────┼──► Story 0.5.7   │
│  │                                           │    Factory       │
│  └───────────────────────────────────────────┘    Portal        │
│                                                                 │
│  DEFERRED: Story 0.5.8: Azure AD B2C (production prep)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Story Sequence

| Story | Name | Blocks | Points |
|-------|------|--------|--------|
| 0.5.1 | Collection gRPC + BFF Clients | 0.5.2 | 5 |
| 0.5.2 | BFF Service Setup | 0.5.3 | 3 |
| 0.5.3 | BFF Auth Middleware | 0.5.4 | 3 |
| 0.5.4 | BFF API Routes | 0.5.5, 0.5.6, 0.5.7 | 5 |
| 0.5.5 | Shared Component Library | 0.5.7 | 3 |
| 0.5.6 | Shared Auth Library | 0.5.7 | 3 |
| 0.5.7 | Factory Portal Scaffold | - | 3 |
| 0.5.8 | Azure AD B2C Configuration | DEFERRED | 5 |

**Total Points:** 30 (25 active + 5 deferred)

---

### Story 0.5.1: Collection Model gRPC Layer & BFF Clients (BLOCKING)

As a **BFF developer**,
I want Collection Model to expose gRPC services and BFF to have DAPR clients for all domain models,
So that the BFF can aggregate data from Plantation and Collection models.

**Acceptance Criteria:**

**Given** Collection Model exists with REST/MCP only
**When** I add gRPC service layer
**Then** `CollectionService` is defined in `proto/collection/v1/collection.proto`
**And** Service implements: `GetQualityEvent`, `ListQualityEvents`, `GetDelivery`, `ListDeliveries`
**And** Aggregation methods: `GetFarmerQualitySummary`, `GetFactoryDailySummary`
**And** gRPC server runs on port 50051 alongside existing FastAPI health endpoints
**And** Unit tests cover all gRPC handlers

**Given** BFF needs to call Plantation Model
**When** I implement `PlantationClient`
**Then** Client calls `plantation-model` via DAPR service invocation
**And** Methods include: `get_farmer`, `list_farmers`, `get_factory`
**And** Pattern follows ADR-002 §"Service Invocation Pattern" (lines 449-502)

**Given** BFF needs to call Collection Model
**When** I implement `CollectionClient`
**Then** Client calls `collection-model` via DAPR service invocation
**And** Methods include: `get_quality_event`, `list_quality_events`, `get_farmer_quality_summary`
**And** Pattern matches `PlantationClient` implementation

**Given** the gRPC clients are implemented
**When** I run the E2E test suite
**Then** BFF clients successfully call Plantation and Collection via DAPR sidecar
**And** Proto messages are correctly serialized/deserialized

**Technical Notes:**
- Proto location: `proto/collection/v1/collection.proto`
- Collection gRPC server: `services/collection-model/src/collection_model/api/grpc_service.py`
- BFF clients: `services/bff/src/bff/infrastructure/clients/`
- Base client: `services/bff/src/bff/infrastructure/clients/base.py`
- Reference: ADR-002 §"Backend Service gRPC Requirements"
- Reference: ADR-005 (gRPC client retry strategy)

**Proto Definition (CollectionService):**
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

**Dependencies:**
- Epic 0.4 Collection Model (server-side gRPC target)
- Plantation Model gRPC service (already implemented)

**Blocks:**
- Story 0.5.2: BFF Service Setup

**Story Points:** 5

---

### Story 0.5.2: BFF Service Setup

As a **platform operator**,
I want a BFF (Backend for Frontend) service deployed with DAPR sidecar,
So that frontend applications have an optimized API layer.

**Acceptance Criteria:**

**Given** the services folder structure exists
**When** I create `services/bff/`
**Then** FastAPI application is scaffolded following project conventions
**And** Directory structure matches ADR-002 §"BFF Internal Code Structure" (lines 780-933)
**And** `pyproject.toml` includes dependencies: fastapi, uvicorn, dapr, fp-proto, fp-common

**Given** the BFF service is created
**When** I start the service
**Then** FastAPI serves on port 8080
**And** Health endpoint `/health` returns 200
**And** Readiness endpoint `/ready` returns 200
**And** OpenTelemetry tracing is configured via fp-common

**Given** E2E infrastructure needs updating
**When** I update `docker-compose.e2e.yaml`
**Then** BFF service is added with DAPR sidecar
**And** BFF can invoke `plantation-model` and `collection-model` via DAPR
**And** Configuration matches ADR-002 §"Docker Compose Configuration" (lines 654-729)

**Given** DAPR configuration is needed
**When** I create `services/bff/dapr/`
**Then** `config.yaml` configures tracing to OTel collector
**And** `resiliency.yaml` defines circuit breaker and retry policies
**And** Configuration matches ADR-002 §"Resiliency Configuration" (lines 735-776)

**Technical Notes:**
- Location: `services/bff/`
- Port: 8080 (FastAPI REST)
- DAPR ports: 3500 (HTTP), 50001 (gRPC)
- Reference: ADR-002 §"BFF Internal Code Structure"

**Directory Structure:**
```
services/bff/
├── src/bff/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── routes/
│   │   │   └── health.py
│   │   ├── middleware/
│   │   └── schemas/
│   ├── infrastructure/
│   │   ├── clients/
│   │   │   ├── base.py
│   │   │   ├── plantation_client.py
│   │   │   └── collection_client.py
│   │   └── tracing.py
│   ├── services/
│   └── transformers/
├── dapr/
│   ├── config.yaml
│   └── resiliency.yaml
├── Dockerfile
└── pyproject.toml
```

**Dependencies:**
- Story 0.5.1: Collection gRPC + BFF Clients

**Blocks:**
- Story 0.5.3: BFF Auth Middleware

**Story Points:** 3

---

### Story 0.5.3: BFF Authentication Middleware (Dual-Mode)

As a **backend developer**,
I want the BFF service to validate JWT tokens in both mock and B2C modes,
So that API endpoints are protected locally and in production.

**Acceptance Criteria:**

**Given** `AUTH_PROVIDER=mock` is configured
**When** the middleware validates a token
**Then** JWT is validated using local HS256 secret (`MOCK_JWT_SECRET`)
**And** Token claims are extracted and available in request context
**And** Invalid tokens return 401 Unauthorized

**Given** `AUTH_PROVIDER=azure-b2c` is configured
**When** the middleware validates a token
**Then** JWT is validated against B2C JWKS endpoint
**And** JWKS is cached for 24 hours
**And** Token claims are extracted identically to mock mode

**Given** the JWT is validated (either mode)
**When** the middleware extracts claims
**Then** `TokenClaims` Pydantic model contains all user attributes
**And** Claims include: `sub`, `email`, `name`, `role`, `factory_id`, `factory_ids`, `collection_point_id`, `region_ids`, `permissions`
**And** Claims are added to OpenTelemetry trace context
**And** PII (email, name) is NOT logged

**Given** role-based authorization is needed
**When** I use the `@require_permission` decorator
**Then** Endpoints check specific permission (e.g., `farmers:read`)
**And** Platform admins bypass permission checks
**And** Unauthorized access returns 403 Forbidden

**Given** factory-level authorization is needed
**When** I use the `@require_factory_access` decorator
**Then** Users can only access their assigned factory's data
**And** Multi-factory users (owners) can access all their factories
**And** Regulators are blocked from factory-level data
**And** Platform admins bypass factory restriction

**Given** a token is expired
**When** the client sends a request
**Then** 401 is returned with `token_expired` error code
**And** Client can refresh and retry

**Given** mock mode is used in production build
**When** the app starts with `AUTH_PROVIDER=mock` and `APP_ENV=production`
**Then** Startup fails with configuration error (security guardrail)

**Technical Notes:**
- Location: `services/bff/src/bff/api/middleware/auth.py`
- JWT library: python-jose
- Config: `AUTH_PROVIDER=mock | azure-b2c`
- Mock: HS256 validation with `MOCK_JWT_SECRET`
- B2C: RS256 validation with JWKS caching
- Reference: ADR-003 §"BFF Authorization Middleware" (lines 321-392)
- Reference: ADR-003 §"BFF Mock Token Validation" (lines 721-751)

**TokenClaims Model (from ADR-003):**
```python
class TokenClaims(BaseModel):
    sub: str                              # User ID (Azure AD object ID)
    email: str
    name: str
    role: str                             # Primary role
    factory_id: Optional[str] = None      # Single factory assignment
    factory_ids: List[str] = []           # Multi-factory (owners)
    collection_point_id: Optional[str] = None  # For clerks
    region_ids: List[str] = []            # For regulators
    permissions: List[str] = []           # Computed permissions
```

**Authorization Decorators:**
| Decorator | Purpose | Example |
|-----------|---------|---------|
| `@require_permission("farmers:read")` | Check specific permission | Farmer list endpoint |
| `@require_factory_access` | Enforce factory isolation | All factory-scoped endpoints |

**Dependencies:**
- Story 0.5.2: BFF Service Setup

**Blocks:**
- Story 0.5.4: BFF API Routes

**Story Points:** 3

---

### Story 0.5.4: BFF API Routes

As a **frontend developer**,
I want REST API endpoints for farmers, quality data, and dashboard aggregations,
So that the Factory Portal can display farmer information and quality metrics.

**Acceptance Criteria:**

**Given** authenticated users need farmer data
**When** I call `GET /api/farmers?factory_id={id}&page_size={n}`
**Then** Paginated farmer list is returned with quality summaries
**And** Response includes: `farmers[]`, `next_page_token`, `total_count`
**And** Only farmers from user's factory are returned (factory authorization)

**Given** I need a specific farmer's details
**When** I call `GET /api/farmers/{farmer_id}`
**Then** Farmer profile with quality history is returned
**And** Response includes: profile, quality_summary, recent_deliveries, trend
**And** Factory authorization is enforced

**Given** I need quality events for a farmer
**When** I call `GET /api/farmers/{farmer_id}/quality-events`
**Then** Quality events are returned with pagination
**And** Response includes: events[], next_page_token
**And** Events are sorted by date descending

**Given** I need dashboard summary data
**When** I call `GET /api/dashboard/summary?factory_id={id}`
**Then** Aggregated dashboard data is returned
**And** Response includes: action_needed_count, watch_count, win_count
**And** Response includes: today_deliveries, quality_trend

**Given** I need farmers grouped by status
**When** I call `GET /api/dashboard/farmers-by-status?factory_id={id}`
**Then** Farmers are returned grouped by WIN/WATCH/ACTION_NEEDED
**And** Each group includes farmer cards with summary data

**Given** any API error occurs
**When** the error is returned to the client
**Then** Error response follows RFC 7807 Problem Details format
**And** Internal details are NOT exposed to client

**Technical Notes:**
- Location: `services/bff/src/bff/api/routes/`
- Routes: `farmers.py`, `dashboard.py`, `quality.py`
- Schemas: `services/bff/src/bff/api/schemas/`
- Services: `services/bff/src/bff/services/`
- Transformers: `services/bff/src/bff/transformers/`
- Reference: ADR-002 §"Data Flow" (lines 870-900)

**API Endpoints:**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/farmers` | List farmers (paginated) |
| GET | `/api/farmers/{id}` | Get farmer detail |
| GET | `/api/farmers/{id}/quality-events` | Get farmer's quality events |
| GET | `/api/dashboard/summary` | Dashboard aggregations |
| GET | `/api/dashboard/farmers-by-status` | Farmers grouped by status |

**Dependencies:**
- Story 0.5.3: BFF Auth Middleware

**Blocks:**
- Story 0.5.5: Shared Component Library
- Story 0.5.6: Shared Auth Library
- Story 0.5.7: Factory Portal Scaffold

**Story Points:** 5

---

### Story 0.5.5: Shared Component Library Setup

As a **frontend developer**,
I want a shared React component library with the design system foundation,
So that all frontend applications have consistent UI components and styling.

**Acceptance Criteria:**

**Given** the monorepo structure is configured
**When** I create the `libs/ui-components/` package
**Then** it exports as `@fp/ui-components` via npm workspaces
**And** TypeScript is configured with strict mode
**And** Vitest is configured for component testing

**Given** the component library is created
**When** I implement the theme foundation
**Then** Material UI v6 theme is configured with Farmer Power color palette
**And** Custom palette includes: primary (Forest Green #1B4332), secondary (Earth Brown #5C4033)
**And** Status colors: win (#D8F3DC), watch (#FFF8E7), action (#FFE5E5)
**And** Typography uses Inter font family
**And** Spacing follows 8px grid system

**Given** the theme is configured
**When** I create the base components
**Then** `StatusBadge` component is available with variants: WIN, WATCH, ACTION_NEEDED
**And** `TrendIndicator` shows up/down/stable with color coding and icons
**And** `LeafTypeTag` displays leaf type with TBK color coding
**And** All components have unit tests in `tests/unit/web/`
**And** All components have TypeScript types exported

**Given** the components are created
**When** I configure Storybook
**Then** Storybook is configured for visual documentation
**And** Each component has a `.stories.tsx` file with all variants
**And** Stories cover: default, hover, focus, disabled, loading states
**And** Storybook builds successfully with `npm run build-storybook`

**Given** visual regression testing is needed
**When** I create visual snapshots
**Then** Baseline snapshots are captured for all component stories
**And** Snapshots are stored in `tests/visual/snapshots/`

**Given** I import from `@fp/ui-components`
**When** I use components in a frontend app
**Then** Tree-shaking works correctly (only imported components bundled)
**And** Theme is accessible via `ThemeProvider` wrapper

**Technical Notes:**
- Location: `libs/ui-components/`
- Build: Vite library mode with rollup
- Exports: ESM only, TypeScript declarations
- Testing: Vitest + React Testing Library
- Visual: Storybook + snapshot testing
- Reference: ADR-002 §"Component Specification Reference" (lines 1355-1424)
- Reference: `_bmad-output/ux-design-specification/6-component-strategy.md`

**Directory Structure:**
```
libs/ui-components/
├── src/
│   ├── components/
│   │   ├── StatusBadge/
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── StatusBadge.stories.tsx
│   │   │   └── index.ts
│   │   ├── TrendIndicator/
│   │   └── LeafTypeTag/
│   ├── theme/
│   │   ├── index.ts
│   │   ├── palette.ts
│   │   └── typography.ts
│   └── index.ts
├── .storybook/
├── package.json
└── tsconfig.json
```

**Required Storybook Stories:**
| Component | Required Stories |
|-----------|------------------|
| StatusBadge | WIN, WATCH, ACTION_NEEDED |
| TrendIndicator | up, down, stable |
| LeafTypeTag | All 7 leaf types |

**Dependencies:**
- Story 0.5.4: BFF API Routes (API contract finalized)

**Blocks:**
- Story 0.5.7: Factory Portal Scaffold

**Story Points:** 3

---

### Story 0.5.6: Shared Auth Library (Mock-First)

As a **frontend developer**,
I want a shared authentication library with swappable providers,
So that all frontend apps work with mock auth locally and Azure B2C in production.

**Acceptance Criteria:**

**Given** the auth library needs to be created
**When** I create `libs/auth/`
**Then** it exports as `@fp/auth` via npm workspaces
**And** TypeScript types are exported for auth context
**And** Two providers are available: `MockAuthProvider` and `AzureB2CAuthProvider`

**Given** `VITE_AUTH_PROVIDER=mock` is set
**When** the `AuthProvider` component initializes
**Then** `MockAuthProvider` is used
**And** `MockLoginSelector` component shows available personas
**And** Tokens are stored in localStorage (dev only)

**Given** mock auth is active
**When** I select a mock user persona
**Then** A locally-signed JWT is generated with same claims structure as B2C
**And** Claims include: `sub`, `name`, `email`, `role`, `factory_id`, `factory_ids`, `collection_point_id`, `region_ids`, `permissions`
**And** JWT is signed with HS256 using `VITE_MOCK_JWT_SECRET`
**And** The user is immediately "logged in"

**Given** the auth context is available
**When** I use the `useAuth` hook
**Then** `isAuthenticated` boolean is available
**And** `user` object matches `TokenClaims` structure from BFF
**And** `login()` and `logout()` functions are available
**And** `getAccessToken()` returns token for API calls

**Given** permission checking is needed
**When** I use the `usePermission` hook
**Then** I can check if user has specific permission
**And** Platform admins always return true
**And** Example: `const canEdit = usePermission('sms_templates:write')`

**Given** route protection is needed
**When** I use the `ProtectedRoute` component
**Then** It checks if user has required role(s)
**And** Unauthorized users are redirected to access denied page
**And** Loading state is handled during auth check

**Given** mock users are needed
**When** I check the mock user personas
**Then** 5 personas are available matching ADR-003 specification
**And** Each has complete permissions and assignments per role

**Technical Notes:**
- Location: `libs/auth/`
- Mock: localStorage JWT with HS256 signing (matches BFF mock validation)
- B2C: MSAL React @azure/msal-react ^2.0 (stub implementation, completed in 0.5.8)
- Config: `VITE_AUTH_PROVIDER=mock | azure-b2c`
- Reference: ADR-003 §"Development Authentication Strategy" (lines 595-804)
- Reference: ADR-003 §"Mock User Personas" (lines 664-719)
- Reference: ADR-003 §"Frontend Auth Library" (lines 472-521)

**Directory Structure:**
```
libs/auth/
├── src/
│   ├── providers/
│   │   ├── AuthProvider.tsx
│   │   ├── MockAuthProvider.tsx
│   │   └── AzureB2CAuthProvider.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   └── usePermission.ts
│   ├── components/
│   │   ├── ProtectedRoute.tsx
│   │   └── MockLoginSelector.tsx
│   ├── mock/
│   │   └── users.ts           # Mock user personas
│   ├── types.ts
│   └── index.ts
├── package.json
└── tsconfig.json
```

**Mock User Personas (from ADR-003):**

| ID | Name | Role | Factory | Permissions |
|----|------|------|---------|-------------|
| mock-manager-001 | Jane Mwangi | factory_manager | KEN-FAC-001 | farmers:read, quality_events:read, diagnoses:read, action_plans:read |
| mock-owner-001 | John Ochieng | factory_owner | KEN-FAC-001, KEN-FAC-002 | + payment_policies:write, factory_settings:write |
| mock-admin-001 | Admin User | platform_admin | (all) | * (wildcard) |
| mock-clerk-001 | Mary Wanjiku | registration_clerk | KEN-FAC-001 + KEN-CP-001 | farmers:create |
| mock-regulator-001 | TBK Inspector | regulator | regions: nandi, kericho | national_stats:read, regional_stats:read |

**MockLoginSelector Component:**
```tsx
// Shows dropdown/buttons to select test user persona
// Displays: role badge, name, factory assignment
// On select: generates JWT, stores in localStorage, triggers auth state update
```

**Dependencies:**
- Story 0.5.4: BFF API Routes (API contract finalized)

**Blocks:**
- Story 0.5.7: Factory Portal Scaffold

**Story Points:** 3

---

### Story 0.5.7: Factory Portal Scaffold

As a **frontend developer**,
I want the Factory Portal React application scaffolded with routing and layout,
So that Factory Manager, Owner, and Admin screens can be built.

**Acceptance Criteria:**

**Given** the web folder structure exists
**When** I create `web/factory-portal/`
**Then** Vite + React + TypeScript project is initialized
**And** `@fp/ui-components` and `@fp/auth` are configured as dependencies
**And** ESLint and Prettier are configured

**Given** the project is scaffolded
**When** I configure routing
**Then** React Router v6 is configured with:
  - `/` redirects to `/command-center`
  - `/command-center` (Factory Manager dashboard)
  - `/farmers/:id` (Farmer Detail)
  - `/roi` (Factory Owner ROI)
  - `/settings/*` (Factory Admin)
**And** Routes are protected by `RequireRole` component
**And** Unknown routes show 404 page

**Given** routing is configured
**When** I implement the layout
**Then** Sidebar navigation shows role-appropriate menu items
**And** Header shows user name and factory name
**And** Logout button is available
**And** Layout is responsive (Material UI breakpoints)

**Given** the layout is implemented
**When** I create placeholder pages
**Then** Each route has a placeholder component
**And** Placeholders show page title and "Coming soon" message
**And** Placeholders demonstrate layout integration

**Given** the app is built
**When** I run `npm run build`
**Then** Production bundle is generated
**And** Bundle size is < 500KB (gzipped, excluding node_modules)
**And** Source maps are generated for debugging

**Given** the development server runs
**When** I run `npm run dev`
**Then** Hot module replacement works
**And** API proxy is configured to BFF service (`/api` -> `http://localhost:8080`)

**Technical Notes:**
- Location: `web/factory-portal/`
- Vite config: React plugin, path aliases
- Proxy: `/api` -> BFF service URL
- Reference: ADR-002 §"Application Structure" (lines 93-164)

**Directory Structure:**
```
web/factory-portal/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── routes.tsx
│   │   └── providers/
│   │       ├── AuthProvider.tsx
│   │       └── ThemeProvider.tsx
│   ├── pages/
│   │   ├── manager/
│   │   │   └── CommandCenter/
│   │   ├── owner/
│   │   │   └── ROISummary/
│   │   └── admin/
│   │       └── Settings/
│   ├── components/
│   │   ├── Layout/
│   │   └── Sidebar/
│   └── main.tsx
├── package.json
├── vite.config.ts
└── Dockerfile
```

**Dependencies:**
- Story 0.5.4: BFF API Routes (real API available)
- Story 0.5.5: Shared Component Library
- Story 0.5.6: Shared Auth Library

**Story Points:** 3

---

### Story 0.5.8: Azure AD B2C Configuration

**Status:** DEFERRED (implement for production deployment)

As a **platform administrator**,
I want Azure AD B2C configured for the Farmer Power Platform,
So that users can authenticate securely with role-based access control.

> **Note:** This story is deferred for local development. Mock authentication (Stories 0.5.3 and 0.5.6) provides the same interface. Implement this story when preparing for Azure AKS deployment.

**Acceptance Criteria:**

**Given** the Azure subscription is available
**When** Azure AD B2C tenant is provisioned
**Then** Tenant is created: `farmerpowerb2c.onmicrosoft.com`
**And** Custom domain configured: `auth.farmerpower.ai`
**And** Branding matches Farmer Power design (logo, colors)

**Given** the B2C tenant is configured
**When** user flows are created
**Then** Sign-in flow is configured (no self-registration)
**And** Password reset flow is available
**And** MFA is optional (configurable per user)

**Given** the tenant is configured
**When** application registrations are created
**Then** `factory-portal-spa` is registered (SPA, PKCE)
**And** `platform-admin-spa` is registered (SPA, PKCE)
**And** `bff-api` is registered (confidential client)
**And** API scopes are defined: `Factory.Read`, `Factory.Write`, `Platform.Admin`

**Given** custom claims are needed
**When** custom user attributes are configured
**Then** `factory_id` attribute is available
**And** `role` attribute is available (from extension attribute)
**And** Claims are included in ID token

**Given** users need to be created
**When** admin creates a user via Microsoft Graph API
**Then** User is created with local account (email + password)
**And** Role is assigned via custom attribute
**And** Welcome email is sent with temporary password

**Given** the B2C provider is configured
**When** I update `@fp/auth` AzureB2CAuthProvider
**Then** MSAL React is configured with B2C endpoints
**And** Token acquisition uses PKCE flow
**And** Logout properly clears B2C session

**Technical Notes:**
- B2C tier: Free (50K MAUs included)
- Token lifetime: 1 hour access, 14 days refresh
- Reference: ADR-003 "Azure AD B2C Configuration"
- User provisioning: Microsoft Graph API (not self-service)

**Cloudflare DNS Configuration:**

| Record | Type | Value | Proxy |
|--------|------|-------|-------|
| `auth` | CNAME | `farmerpowerb2c.b2clogin.com` | **DNS only (grey cloud)** |
| Root | TXT | `MS=<azure-verification-code>` | N/A |

**Critical:** The `auth.farmerpower.ai` subdomain **must** have Cloudflare proxy disabled (grey cloud icon). Azure AD B2C requires direct connection.

**Dependencies:**
- Azure subscription
- Cloudflare DNS access for farmerpower.ai
- Stories 0.5.3 and 0.5.6 complete (interface compatibility)

**Story Points:** 5

---

## Testing Strategy

### Test Pyramid (Epic 0.5)

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
                    │  Components + BFF   │
                    └─────────────────────┘
```

**Reference:** ADR-002 §"Frontend Test Policy" (lines 939-1354)

### E2E Milestone

After **Story 0.5.4** (BFF API Routes), the following E2E test is possible:

```bash
# Start infrastructure
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Test BFF endpoints
curl http://localhost:8080/health
curl -H "Authorization: Bearer <mock-token>" http://localhost:8080/api/farmers?factory_id=FAC-001

# Run E2E tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
```

---

## References

- [ADR-002: Frontend Architecture](./_bmad-output/architecture/adr/ADR-002-frontend-architecture.md)
- [ADR-003: Identity & Access Management](./_bmad-output/architecture/adr/ADR-003-identity-access-management.md)
- [UX Design Specification](./_bmad-output/ux-design-specification/index.md)
- [Component Strategy](./_bmad-output/ux-design-specification/6-component-strategy.md)
- [Design System Foundation](./_bmad-output/ux-design-specification/design-system-foundation.md)
