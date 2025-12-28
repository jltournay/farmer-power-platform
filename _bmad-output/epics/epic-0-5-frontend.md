### Epic 0.5: Frontend & Identity Infrastructure

**Priority:** P1

**Dependencies:** Epic 0 (Infrastructure)

Cross-cutting frontend and authentication infrastructure that enables all web applications. These stories establish the shared component library, authentication flow, BFF service, and foundational frontend patterns.

**Related ADRs:** ADR-002 (Frontend Architecture), ADR-003 (Identity & Access Management)

**Scope:**
- Shared React component library (@fp/ui-components)
- Azure AD B2C configuration and auth library (@fp/auth)
- Factory Portal application scaffold
- **BFF Service Setup** (shared by all frontends)
- Authentication middleware (BFF pattern)
- Theme system and design tokens

---

#### Story 0.5.1: Shared Component Library Setup

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
**Then** Material UI v6 theme is configured with TBK color palette
**And** Custom palette includes: primary (tea green), secondary (earth brown), status colors
**And** Typography scale matches UX specification (Roboto, 14px base)
**And** Spacing follows 8px grid system

**Given** the theme is configured
**When** I create the base components
**Then** `StatusBadge` component is available with variants: critical, warning, improving, excellent
**And** `TrendIndicator` shows up/down/stable with color coding
**And** `LeafTypeTag` displays leaf type with TBK color coding
**And** All components have unit tests and TypeScript types

**Given** I import from `@fp/ui-components`
**When** I use components in a frontend app
**Then** tree-shaking works correctly (only imported components bundled)
**And** Theme is accessible via `ThemeProvider` wrapper

**Technical Notes:**
- Location: `libs/ui-components/`
- Build: Vite library mode with rollup
- Exports: ESM only, TypeScript declarations
- Testing: Vitest + React Testing Library
- Reference: `_bmad-output/ux-design-specification/design-system-foundation.md`

**Dependencies:**
- None (foundational)

**Story Points:** 3

---

#### Story 0.5.2: Azure AD B2C Configuration

As a **platform administrator**,
I want Azure AD B2C configured for the Farmer Power Platform,
So that users can authenticate securely with role-based access control.

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

**Technical Notes:**
- B2C tier: Free (50K MAUs included)
- Token lifetime: 1 hour access, 14 days refresh
- Reference: `_bmad-output/architecture/adr/ADR-003-identity-access-management.md`
- User provisioning: Microsoft Graph API (not self-service)

**Dependencies:**
- Azure subscription

**Story Points:** 5

---

#### Story 0.5.3: Shared Auth Library

As a **frontend developer**,
I want a shared authentication library for React applications,
So that all frontend apps implement consistent authentication and authorization.

**Acceptance Criteria:**

**Given** the auth library needs to be created
**When** I create `libs/auth/`
**Then** it exports as `@fp/auth` via npm workspaces
**And** MSAL React is configured as the authentication provider
**And** TypeScript types are exported for auth context

**Given** the auth library is created
**When** I implement the `AuthProvider` component
**Then** it wraps MSAL provider with B2C configuration
**And** Silent token refresh is handled automatically
**And** Login redirect flow is implemented (PKCE)

**Given** the auth context is available
**When** I use the `useAuth` hook
**Then** `isAuthenticated` boolean is available
**And** `user` object includes: name, email, roles[], factoryId
**And** `login()` and `logout()` functions are available
**And** `getAccessToken()` returns token for API calls

**Given** role-based access is needed
**When** I use the `RequireRole` component
**Then** it renders children only if user has required role
**And** Unauthorized users are redirected to access denied page
**And** Loading state is handled during auth check

**Given** the auth flow completes
**When** tokens are received
**Then** Access token is stored securely (memory, not localStorage)
**And** Refresh token handles silent renewal
**And** OpenTelemetry traces include user context (not PII)

**Technical Notes:**
- Location: `libs/auth/`
- MSAL version: @azure/msal-react ^2.0
- Token storage: In-memory with silent refresh
- Reference: ADR-003 for B2C configuration

**Dependencies:**
- Story 0.5.2: Azure AD B2C Configuration

**Story Points:** 3

---

#### Story 0.5.4: Factory Portal Scaffold

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
  - `/command-center` (Factory Manager)
  - `/farmers/:id` (Farmer Detail)
  - `/roi` (Factory Owner)
  - `/settings/*` (Factory Admin)
**And** Routes are protected by `RequireRole` component

**Given** routing is configured
**When** I implement the layout
**Then** Sidebar navigation shows role-appropriate menu items
**And** Header shows user name and factory name
**And** Logout button is available
**And** Layout is responsive (Material UI breakpoints)

**Given** the app is built
**When** I run `npm run build`
**Then** Production bundle is generated
**And** Bundle size is < 500KB (gzipped, excluding node_modules)
**And** Source maps are generated for debugging

**Given** the development server runs
**When** I run `npm run dev`
**Then** Hot module replacement works
**And** API proxy is configured to BFF service

**Technical Notes:**
- Location: `web/factory-portal/`
- Vite config: React plugin, path aliases
- Proxy: `/api` -> BFF service URL
- Reference: ADR-002 for folder structure

**Dependencies:**
- Story 0.5.1: Shared Component Library
- Story 0.5.3: Shared Auth Library

**Story Points:** 3

---

#### Story 0.5.5: BFF Authentication Middleware

As a **backend developer**,
I want the BFF service to validate JWT tokens from Azure AD B2C,
So that API endpoints are protected with proper authorization.

**Acceptance Criteria:**

**Given** the BFF service exists (from Story 0.5.6)
**When** I add authentication middleware
**Then** JWT tokens are validated against B2C JWKS endpoint
**And** Token claims are extracted and available in request context
**And** Invalid tokens return 401 Unauthorized

**Given** the JWT is validated
**When** the middleware extracts claims
**Then** `user_id`, `email`, `roles[]`, `factory_id` are available
**And** Claims are added to OpenTelemetry trace context
**And** PII (email, name) is NOT logged

**Given** role-based authorization is needed
**When** I use the `@require_role` decorator
**Then** Endpoints are protected by role check
**And** Unauthorized access returns 403 Forbidden
**And** Error message does not reveal internal details

**Given** factory-level authorization is needed
**When** I use the `@require_factory` decorator
**Then** Users can only access their assigned factory's data
**And** Cross-factory access returns 403 Forbidden
**And** Platform admins bypass factory restriction

**Given** a token is expired
**When** the client sends a request
**Then** 401 is returned with `token_expired` error code
**And** Client can refresh and retry

**Technical Notes:**
- FastAPI middleware with python-jose
- JWKS caching: 24 hours
- Decorators: `@require_role`, `@require_factory`
- Reference: ADR-003 for authorization flow

**Dependencies:**
- Story 0.5.2: Azure AD B2C Configuration
- Story 0.5.6: BFF Service Setup

**Story Points:** 3

---

#### Story 0.5.6: BFF Service Setup

As a **platform operator**,
I want a shared BFF (Backend for Frontend) service deployed,
So that all frontend applications have an optimized API layer.

**Acceptance Criteria:**

**Given** the Kubernetes cluster is running
**When** the BFF service is deployed
**Then** the service starts successfully with health check endpoint returning 200
**And** FastAPI is serving REST endpoints on port 8080
**And** OpenTelemetry traces are emitted for all requests
**And** CORS is configured for allowed frontend origins

**Given** the BFF is running
**When** an unauthenticated request is made
**Then** the request is rejected with 401 Unauthorized
**And** the response includes WWW-Authenticate header

**Given** a user is authenticated (OAuth2/OIDC)
**When** they request data
**Then** the BFF queries domain models via gRPC (Plantation, Collection, etc.)
**And** data is aggregated and transformed for frontend consumption
**And** only data for factories the user has access to is returned

**Given** the BFF receives multiple concurrent requests
**When** processing under load
**Then** connection pooling is used for downstream gRPC calls
**And** request timeout is enforced (5 seconds max)
**And** circuit breaker trips after 5 consecutive failures

**Technical Notes:**
- Python FastAPI with async support
- OAuth2 token validation via Azure AD B2C
- gRPC clients with connection pooling
- Location: `services/bff/`
- Environment: farmer-power-{env} namespace
- Shared by all frontends (Kiosk, Admin, Regulator, Dashboard)

**Dependencies:**
- Story 0.5.2: Azure AD B2C Configuration

**Story Points:** 5

---
