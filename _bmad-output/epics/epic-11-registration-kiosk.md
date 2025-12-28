# Epic 11: Registration Kiosk PWA

**Priority:** P2 (1st frontend to build - SIMPLEST)

**Dependencies:** Epic 0.5 (Frontend Infrastructure), Epic 1 (Plantation Model)

Registration clerks at collection points can enroll new farmers using dedicated tablets. The application works offline for rural areas with poor connectivity.

**Note:** This is the SIMPLEST frontend application and should be built FIRST to validate React patterns and PWA architecture. It only depends on Plantation Model for farmer registration.

**Related ADRs:** ADR-002 (Frontend Architecture), ADR-003 (Identity & Access Management)

**Scope:**
- Progressive Web App (PWA) for offline-first operation
- Farmer registration workflow
- Collection point assignment
- ID card printing support
- Background sync when connectivity restored

---

## Story 11.1: Registration Kiosk Application Scaffold

As a **platform developer**,
I want the Registration Kiosk PWA scaffolded with offline support,
So that registration works in rural areas with poor connectivity.

**Acceptance Criteria:**

**Given** the web folder structure exists
**When** I create `web/registration-kiosk/`
**Then** Vite + React + TypeScript project is initialized with PWA plugin
**And** Service worker is configured for offline-first
**And** App manifest enables "Add to Home Screen"

**Given** the PWA is installed on a tablet
**When** network is unavailable
**Then** App shell loads from cache
**And** "Offline mode" indicator is shown
**And** All registration functionality works

**Given** authentication is needed
**When** clerk logs in on kiosk device
**Then** Device Code Flow is used (no redirect)
**And** Session persists for 8 hours
**And** Auto-refresh keeps session alive

**Technical Notes:**
- Location: `web/registration-kiosk/`
- PWA: Workbox for service worker
- Offline storage: IndexedDB
- Auth: Device Code Flow (ADR-003)
- Reference: ADR-002 for PWA requirements

**Dependencies:**
- Story 0.5.1: Shared Component Library
- Story 0.5.3: Shared Auth Library

**Story Points:** 5

---

## Story 11.2: Farmer Registration Workflow

As a **Registration Clerk**,
I want to register new farmers with their details,
So that they can be tracked in the quality system.

**Acceptance Criteria:**

**Given** I open the registration form
**When** I enter farmer details
**Then** Form collects: name, phone, national_id, farm_size, location
**And** GPS coordinates can be captured from device
**And** Phone number is validated (Kenya format)

**Given** I submit the registration
**When** online
**Then** Farmer is created immediately via API
**And** Farmer ID is generated (e.g., WM-4521)
**And** Confirmation screen shows farmer ID

**Given** I submit the registration
**When** offline
**Then** Registration is queued in IndexedDB
**And** Temporary ID is shown: "Pending sync"
**And** Queue count badge shows on home screen

**Given** I have queued registrations
**When** network is restored
**Then** Background sync uploads pending registrations
**And** Temporary IDs are replaced with real IDs
**And** Notification confirms sync complete

**Technical Notes:**
- Form: React Hook Form + Zod validation
- Offline queue: IndexedDB with queue status
- Sync: Background Sync API / periodic check
- API: POST /api/farmers

**Dependencies:**
- Story 11.1: Registration Kiosk Application Scaffold
- Story 1.3: Farmer Registration (API)

**Story Points:** 5

---

## Story 11.3: Collection Point Assignment

As a **Registration Clerk**,
I want to assign farmers to their collection point,
So that deliveries are tracked correctly.

**Acceptance Criteria:**

**Given** I am registering a farmer
**When** I reach collection point step
**Then** Dropdown shows collection points for this factory
**And** Collection points are cached offline
**And** Default is clerk's assigned collection point

**Given** the farmer needs a different collection point
**When** I select from the list
**Then** Map shows collection point location
**And** Distance from farmer's GPS is calculated
**And** Warning if distance > 10km (unusual)

**Given** collection point data is stale
**When** app syncs
**Then** Collection point list is refreshed
**And** Changes are merged (new points added, closed points flagged)
**And** Last sync time is shown in UI

**Technical Notes:**
- Collection points cached in IndexedDB
- Sync on login and every 24 hours
- Distance: Haversine formula (client-side)

**Dependencies:**
- Story 11.1: Registration Kiosk Application Scaffold
- Story 1.2: Factory and Collection Point Management

**Story Points:** 3

---

## Story 11.4: Farmer ID Card Printing

As a **Registration Clerk**,
I want to print a farmer ID card after registration,
So that farmers have proof of registration.

**Acceptance Criteria:**

**Given** registration is complete
**When** I click "Print ID Card"
**Then** ID card preview shows: farmer name, ID, collection point, QR code
**And** QR code contains farmer_id for quick lookup
**And** Print dialog opens with correct page size (ID card format)

**Given** printer is connected
**When** I confirm print
**Then** ID card prints on configured printer
**And** Print success is logged
**And** Reprint option is available from farmer list

**Given** printer is not connected
**When** I try to print
**Then** Error message shows with troubleshooting steps
**And** Option to queue for later printing
**And** "View digital ID" alternative is offered

**Given** registration was completed offline
**When** sync completes and real ID is assigned
**Then** Print option becomes available
**And** ID card shows final farmer_id

**Technical Notes:**
- Web Print API (window.print)
- ID card template: CSS @media print
- QR code: qrcode.react library
- Thermal printer support: ESC/POS if needed

**Dependencies:**
- Story 11.2: Farmer Registration Workflow

**Story Points:** 3
