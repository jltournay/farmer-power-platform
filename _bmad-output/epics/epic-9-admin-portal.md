# Epic 9: Platform Admin Portal

**Priority:** P2 (2nd frontend to build - Simple CRUD)

**Dependencies:** Epic 0.5 (Frontend Infrastructure), Epic 1 (Plantation Model)

Internal Farmer Power team can onboard new factories, manage users across all factories, and monitor platform health. This is the internal operations portal.

**Note:** This is the 2nd frontend application to build. It establishes BFF patterns with simple CRUD operations for factory onboarding and user management. Build after Epic 11 (Kiosk) to apply learned patterns.

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
- Story 0.5.6: BFF Service Setup (for health endpoints)

**Story Points:** 5

---

## Story 9.5: Knowledge Management Interface

As a **Platform Administrator or Agronomist**,
I want to upload and manage expert knowledge documents through a web interface,
So that AI recommendations are powered by verified expert content.

**Acceptance Criteria:**

**Given** I navigate to Knowledge Management
**When** the page loads
**Then** I see a library of all knowledge documents
**And** I can filter by domain (Plant Diseases, Tea Cultivation, Weather, etc.)
**And** I can filter by status (Draft, Staged, Active, Archived)
**And** Search is available across document titles and content

**Given** I want to upload a new document
**When** I click "Upload Document"
**Then** I can drag & drop or browse for PDF, DOCX, MD, or TXT files
**And** I enter metadata: title, domain, author, source, region
**And** System auto-detects extraction method (text vs OCR vs Vision)
**And** I see extraction progress with confidence score
**And** I can preview and edit extracted content before saving

**Given** extraction confidence is low (<80%)
**When** the extraction completes
**Then** System shows quality warning with specific issues
**And** Offers options: try Vision AI, edit manually, upload clearer scan
**And** I can continue anyway if content is acceptable

**Given** I want to review a staged document
**When** I open the document review screen
**Then** I can preview the full content
**And** I can test with AI (ask questions, verify retrieval)
**And** I must check approval boxes before activating
**And** Activation moves document to production namespace

**Given** I need to update an active document
**When** I edit and save
**Then** New version is created (old version archived)
**And** Change summary is required
**And** Version history shows all versions with rollback option

**Technical Notes:**
- Location: `web/platform-admin/src/pages/knowledge/`
- API: gRPC RAGDocumentService via BFF
- PDF extraction: PyMuPDF (digital), Azure Document Intelligence (scanned), Vision LLM (diagrams)
- Vector storage: Pinecone with namespace versioning (test vs production)
- Document storage: MongoDB + Azure Blob Storage for original files

**Dependencies:**
- Story 9.1: Platform Admin Application Scaffold
- AI Model RAG Document API (from architecture)

**Story Points:** 8

---

## Story 9.6: LLM Cost Dashboard

As a **Platform Administrator**,
I want a cost dashboard to monitor LLM spending,
So that I can track AI costs, identify cost drivers, and configure budget alerts.

**Acceptance Criteria:**

**Given** I'm on the Platform Dashboard
**When** I view the System Health section
**Then** I see a cost summary widget showing:
- Today's spend (real-time)
- 7-day trend sparkline
- "View Details" link to full cost dashboard

**Given** I navigate to the Cost Dashboard
**When** the page loads
**Then** I see:
- Daily cost trend chart (last 30 days)
- Cost by agent type breakdown (pie chart)
- Cost by model breakdown (pie chart)
- Top 5 most expensive agents (table)

**Given** I want to drill down
**When** I select a date range
**Then** All charts and tables update to the selected range
**And** Export to CSV is available

**Given** I want to configure alerts
**When** I set daily/monthly thresholds
**Then** Alerts are triggered when thresholds are exceeded
**And** Notifications are sent to configured channels (email/Slack)

**Given** the CostService gRPC API is unavailable
**When** the dashboard loads
**Then** Cached data is shown with "Last updated: X" timestamp
**And** A warning banner indicates the data may be stale

**UI Wireframe:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LLM COST DASHBOARD                                   [Export CSV] [⚙ Alerts]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  DATE RANGE: [Last 7 days ▼]  [Custom: _____ to _____]                      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  DAILY COST TREND                                                     │   │
│  │  $50 ─┬─────────────────────────────────────────────────────────────  │   │
│  │       │     ╭──╮                                                      │   │
│  │  $25 ─┼────╱    ╲────────╱╲──────────────────────────────────────────  │   │
│  │       │   ╱      ╲──────╱  ╲                                          │   │
│  │   $0 ─┴──────────────────────────────────────────────────────────────  │   │
│  │       Mon  Tue  Wed  Thu  Fri  Sat  Sun                               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌────────────────────────────┐  ┌────────────────────────────────────┐    │
│  │  COST BY AGENT TYPE        │  │  COST BY MODEL                      │    │
│  │  ┌────────────────────┐    │  │  ┌────────────────────────────┐    │    │
│  │  │    [PIE CHART]     │    │  │  │      [PIE CHART]           │    │    │
│  │  │  Explorer: 45%     │    │  │  │  claude-sonnet: 60%        │    │    │
│  │  │  Generator: 30%    │    │  │  │  gpt-4o-mini: 25%          │    │    │
│  │  │  Vision: 15%       │    │  │  │  gpt-4o: 15%               │    │    │
│  │  │  Other: 10%        │    │  │  │                            │    │    │
│  │  └────────────────────┘    │  │  └────────────────────────────┘    │    │
│  └────────────────────────────┘  └────────────────────────────────────┘    │
│                                                                              │
│  TOP COST DRIVERS                                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Agent ID              │ Type       │ Requests │ Cost (7d) │ Trend   │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │  disease-diagnosis     │ Explorer   │ 1,234    │ $45.20    │ ↑ 12%   │   │
│  │  weekly-action-plan    │ Generator  │ 892      │ $32.10    │ ↓ 5%    │   │
│  │  leaf-image-analyzer   │ Vision     │ 567      │ $18.50    │ → 0%    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Technical Notes:**
- Location: `web/platform-admin/src/pages/costs/`
- Consumes gRPC `UnifiedCostService` API from **platform-cost** service (Epic 13)
- BFF endpoints: `GET /api/admin/costs/summary`, `GET /api/admin/costs/by-agent`, etc.
- Charts: Use existing charting library from @fp/ui-components
- Caching: BFF caches responses for 5 minutes to reduce load
- Reference: ADR-016 (Unified Cost Model and Platform Cost Service)

**Dependencies:**
- Story 9.1: Platform Admin Application Scaffold
- **Epic 13: Unified Platform Cost Service** (provides gRPC UnifiedCostService API)

**Story Points:** 5
