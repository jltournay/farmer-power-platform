# Epic 9: Platform Admin Portal

Internal Farmer Power team can onboard new factories, manage users across all factories, and monitor platform health. This is the internal operations portal.

**Related ADRs:** ADR-002 (Frontend Architecture), ADR-003 (Identity & Access Management)

**Scope:**
- Platform admin web application (separate from factory-portal)
- Factory onboarding workflow
- Cross-factory user management
- Platform health dashboard
- Access restricted to internal team (VPN/internal network)

---

## Story 9.1: Platform Admin Application Scaffold

As a **platform developer**,
I want the Platform Admin React application scaffolded with routing and layout,
So that internal team screens can be built.

**Acceptance Criteria:**

**Given** the web folder structure exists
**When** I create `web/platform-admin/`
**Then** Vite + React + TypeScript project is initialized
**And** `@fp/ui-components` and `@fp/auth` are configured as dependencies
**And** ESLint and Prettier are configured

**Given** the project is scaffolded
**When** I configure routing
**Then** React Router v6 is configured with:
  - `/dashboard` (Platform Overview)
  - `/factories` (Factory List)
  - `/factories/new` (Factory Onboarding)
  - `/users` (User Management)
**And** Routes require `platform_admin` role

**Given** the app is built
**When** I access the application
**Then** It's only accessible from internal network/VPN
**And** Separate B2C application registration is used
**And** No factory-specific branding (Farmer Power internal theme)

**Technical Notes:**
- Location: `web/platform-admin/`
- Deployment: `admin.farmerpower.co.ke` (internal access only)
- Reference: ADR-002 for folder structure

**Dependencies:**
- Story 0.5.1: Shared Component Library
- Story 0.5.3: Shared Auth Library

**Story Points:** 3

---

## Story 9.2: Factory Onboarding Wizard

As a **Platform Administrator**,
I want a wizard to onboard new factories to the platform,
So that factory setup is consistent and complete.

**Acceptance Criteria:**

**Given** I navigate to Factory Onboarding
**When** I start the wizard
**Then** Step 1 collects: factory name, location, contact person, email
**And** Step 2 collects: collection points (name, GPS coordinates)
**And** Step 3 configures: default payment policy, SMS templates
**And** Step 4 creates: initial admin user for factory

**Given** I complete the wizard
**When** I click "Create Factory"
**Then** Factory record is created in Plantation Model
**And** Factory admin user is created in Azure AD B2C
**And** Welcome email is sent with login credentials
**And** Confirmation page shows summary and next steps

**Given** I need to resume onboarding
**When** I save draft partway through
**Then** Draft is saved and can be resumed later
**And** Draft list shows incomplete onboardings

**Technical Notes:**
- Multi-step form with validation per step
- API: POST /api/admin/factories (creates factory + user)
- User creation via Microsoft Graph API
- Email via Notification Model

**Dependencies:**
- Story 9.1: Platform Admin Application Scaffold
- Story 1.2: Factory and Collection Point Management

**Story Points:** 5

---

## Story 9.3: User Management Dashboard

As a **Platform Administrator**,
I want to view and manage users across all factories,
So that I can support user administration tasks.

**Acceptance Criteria:**

**Given** I navigate to User Management
**When** the page loads
**Then** I see a table of all platform users
**And** Columns show: name, email, factory, role, last login, status
**And** Search and filter by factory, role, status are available

**Given** I need to create a new user
**When** I click "Add User"
**Then** Form collects: name, email, factory (dropdown), role (dropdown)
**And** User is created in Azure AD B2C
**And** Welcome email is sent automatically

**Given** I need to modify a user
**When** I click on a user row
**Then** I can edit: role, factory assignment
**And** I can reset password (sends reset email)
**And** I can disable/enable account

**Given** a user is locked out
**When** I reset their password
**Then** Temporary password is generated
**And** Email is sent with reset instructions
**And** Audit log captures who performed the reset

**Technical Notes:**
- Users stored in Azure AD B2C (not local DB)
- Microsoft Graph API for user operations
- Audit log to MongoDB for compliance

**Dependencies:**
- Story 9.1: Platform Admin Application Scaffold
- Story 0.5.2: Azure AD B2C Configuration

**Story Points:** 5

---

## Story 9.4: Platform Health Dashboard

As a **Platform Administrator**,
I want to see platform-wide health metrics and factory statistics,
So that I can monitor operations and identify issues.

**Acceptance Criteria:**

**Given** I navigate to the Platform Dashboard
**When** the page loads
**Then** I see: total factories, total farmers, active users (24h)
**And** System health indicators: API latency, error rate, queue depth
**And** Map shows factory locations with status indicators

**Given** I want to see factory details
**When** I click on a factory card/pin
**Then** I see: farmer count, daily delivery volume, quality trend
**And** Link to impersonate factory admin (for support)
**And** Recent activity log for that factory

**Given** there are system issues
**When** error rate exceeds threshold
**Then** Alert banner shows on dashboard
**And** Affected services are highlighted
**And** Recent error samples are shown

**Technical Notes:**
- Aggregated metrics from OpenTelemetry
- Health checks from each service
- Map: Leaflet with Kenya regions

**Dependencies:**
- Story 9.1: Platform Admin Application Scaffold
- Story 3.1: Dashboard BFF Setup (for health endpoints)

**Story Points:** 5
