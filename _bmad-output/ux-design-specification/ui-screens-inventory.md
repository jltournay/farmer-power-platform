# UI & Screens Inventory

Complete inventory of all user interfaces and their screens for the Farmer Power Platform.

---

## Frontend Application Mapping

| Frontend Application | Epic | UI Sections Included |
|---------------------|------|----------------------|
| **Factory Portal** | Epic 3 | Factory Manager Dashboard, Factory Owner Dashboard, Factory Admin UI |
| **Platform Admin Portal** | Epic 9 | Platform Admin UI, Knowledge Management UI (RAG) |
| **Regulator Dashboard** | Epic 10 | Regulator Dashboard |
| **Registration Kiosk PWA** | Epic 11 | Farmer Registration UI |
| **Non-Web Channels** | Epic 4, 7 | SMS, Voice IVR |

---

## 1. Factory Manager Dashboard (Joseph)

**Frontend Application:** Factory Portal (Epic 3)
**User:** Quality Manager (Joseph)
**Purpose:** Daily operations, farmer intervention, pattern analysis

| # | Screen | Purpose |
|---|--------|---------|
| 1 | **Daily Command Center (Homepage)** | Answer "What should I do today?" - Action Strip with ACTION NEEDED / WATCH / WINS |
| 2 | **Farmer Detail View** | Full farmer profile with leaf type breakdown, history, AI recommendations |
| 3 | **Temporal Patterns View** | Day/time heatmaps to identify systemic quality issues |
| 4 | **SMS Preview Panel** | Preview what farmers receive, toggle message variants |

**Related Docs:**
- [Dashboard MVP - Priority Deliverable](./dashboard-mvp-priority-deliverable.md)
- [User Journey: Joseph's Daily Operations](./5-user-journey-flows.md#52-josephs-daily-operations)

---

## 2. Factory Owner Dashboard

**Frontend Application:** Factory Portal (Epic 3)
**User:** Factory Owner
**Purpose:** ROI validation, subscription value proof

| # | Screen | Purpose |
|---|--------|---------|
| 1 | **ROI Summary (Homepage)** | Hero metric: Premium %, waste reduction savings |
| 2 | **ROI Drill-Down** | Attribution breakdown - which farmers/collection points improved |
| 3 | **Regional Benchmark** | Factory ranking vs regional average |

**Related Docs:**
- [User Journey: Factory Owner ROI Review](./5-user-journey-flows.md#53-factory-owner-roi-review)
- [Core User Experience: Factory Owner](./2-core-user-experience.md#factory-owner-the-roi-proof-experience)

---

## 3. Regulator Dashboard (Tea Board of Kenya)

**Frontend Application:** Regulator Dashboard (Epic 10)
**User:** Tea Board of Kenya regulators
**Purpose:** National quality intelligence, policy decisions, export strategy

| # | Screen | Purpose |
|---|--------|---------|
| 1 | **National Overview** | National Primary %, factories reporting, farmers covered |
| 2 | **Regional Comparison** | Primary % by region with trends |
| 3 | **Leaf Type Distribution** | National breakdown of Primary vs Secondary leaf types |
| 4 | **Export Readiness** | % meeting Premium (≥85%) and Standard (≥70%) thresholds |

**Related Docs:**
- [Dashboard MVP: Regulator Dashboard](./dashboard-mvp-priority-deliverable.md#screen-5-regulator-dashboard-tea-board-of-kenya---tbk-format)

---

## 4. Factory Admin UI

**Frontend Application:** Factory Portal (Epic 3)
**User:** Factory Administrator
**Purpose:** Configure payment policies, quality thresholds, and customize farmer communications

| # | Screen | Purpose |
|---|--------|---------|
| 1 | **Payment Policy Configuration** | Select/change payment policy type |
| 2 | **Quality Tiers & Pricing** | Configure Primary % thresholds (Premium/Standard/Acceptable/Below Standard) and price adjustments |
| 3 | **SMS Template Editor** | Customize tier-based messages (Premium/Standard/Acceptable/Below Standard) |
| 4 | **Impact Calculator** | Preview projected monthly cost changes |
| 5 | **Threshold Preview** | See farmer distribution changes before applying new thresholds |

**Related Docs:**
- [Admin Interface: Factory Admin UI](./admin-interface-core-experience.md#factory-admin-ui)
- [Quality Tiers & Pricing Configuration](./admin-interface-core-experience.md#quality-tiers--pricing-configuration)

---

## 5. Platform Admin UI

**Frontend Application:** Platform Admin Portal (Epic 9)
**User:** Farmer Power platform administrators, Agronomists, TBK specialists
**Purpose:** Factory onboarding, user management, system monitoring, AI knowledge management

### Core Admin Screens

| # | Screen | Purpose |
|---|--------|---------|
| 1 | **Platform Dashboard** | Factory status overview, system health, cost summary widget |
| 2 | **Factory Onboarding Wizard** | 4-step flow: Details → Admin User → QC Integration → Go Live |
| 3 | **User Management** | Add/edit users, role assignment |
| 4 | **Factory List** | All factories with status (Active/Onboarding/Issues) |
| 5 | **LLM Cost Dashboard** | Monitor AI spending, cost trends, breakdown by agent/model, configure alerts |

### RAG Document Ingestion Screens

| # | Screen | Purpose |
|---|--------|---------|
| 6 | **Knowledge Document Library** | Browse, search, filter documents by domain/status |
| 7 | **Document Upload (Step 1)** | Drag & drop file, enter title/domain/author metadata |
| 8 | **Document Processing (Step 2)** | Automatic extraction progress, confidence score display |
| 9 | **Content Preview (Step 2b)** | Review extracted content, edit if needed |
| 10 | **Extraction Quality Warning** | Low confidence handling, re-extraction options |
| 11 | **Save Document (Step 3)** | Summary, save as Draft/Staged/Active |
| 12 | **Document Review & Activation** | Preview, test with AI, approve for production |
| 13 | **Version History** | View all versions, compare, rollback |

**Related Docs:**
- [Admin Interface: Platform Admin UI](./admin-interface-core-experience.md#platform-admin-ui)
- [RAG Document Ingestion UX Specification](./rag-document-ingestion-ux.md)
- [Epic 9 Story 9.5: Knowledge Management Interface](../epics/epic-9-admin-portal.md#story-95-knowledge-management-interface)
- [Epic 9 Story 9.6: LLM Cost Dashboard](../epics/epic-9-admin-portal.md#story-96-llm-cost-dashboard)

---

## 6. Farmer Registration UI (Collection Point)

**Frontend Application:** Registration Kiosk PWA (Epic 11)
**User:** Registration Clerk (at collection point or factory)
**Purpose:** Rapid farmer enrollment with immediate ID issuance

| # | Screen | Purpose |
|---|--------|---------|
| 1 | **Phone Verification** | Enter phone, instant duplicate check |
| 2 | **Farmer Details Form** | Name, National ID, preferred name, language |
| 3 | **Collection Point Assignment** | Select collection point |
| 4 | **ID Card Print** | Generate & print farmer ID card with QR |

**Related Docs:**
- [Admin Interface: Farmer Registration UI](./admin-interface-core-experience.md#farmer-registration-ui)
- [User Journey: Farmer Registration](./5-user-journey-flows.md#54-farmer-registration)

---

## 7. Farmer Touchpoints (Non-Web)

**Channels:** SMS (Epic 4), Voice IVR (Epic 7)
**User:** Farmer (Wanjiku)
**Purpose:** Quality feedback delivery, actionable coaching

| # | Channel | Screens/Flows |
|---|---------|---------------|
| 1 | **SMS** | Single message with Primary %, top issue, actionable tip (160 chars) |
| 2 | **Voice IVR (*384#)** | 8-step flow: Greeting → Language Selection → Personalized Greeting → Quality Summary → Action Plan → Closing → Options Menu |

**Related Docs:**
- [Voice IVR Experience Design](./voice-ivr-experience-design.md)
- [Dashboard MVP: SMS Preview Panel](./dashboard-mvp-priority-deliverable.md#screen-4-sms-preview-panel-tbk-format)
- [User Journey: Wanjiku's Quality Feedback Loop](./5-user-journey-flows.md#51-wanjikus-quality-feedback-loop)

---

## Summary

### Total Screens by UI

| UI | Frontend Application | Epic | Screen Count |
|----|---------------------|------|--------------|
| Factory Manager Dashboard | Factory Portal | 3 | 4 |
| Factory Owner Dashboard | Factory Portal | 3 | 3 |
| Factory Admin | Factory Portal | 3 | 5 |
| Regulator Dashboard | Regulator Dashboard | 10 | 4 |
| Platform Admin (Core + RAG) | Platform Admin Portal | 9 | 13 |
| Farmer Registration | Registration Kiosk PWA | 11 | 4 |
| **Total Web Screens** | | | **33** |

### Non-Web Channels

| Channel | Description |
|---------|-------------|
| SMS | Single message per delivery |
| Voice IVR | 8-step spoken flow (2-3 minutes) |

---

## Screen Priority Matrix

| Priority | Screens | Rationale |
|----------|---------|-----------|
| **P1 - MVP** | Joseph's Command Center, Farmer Detail, SMS Preview | Core demo capability, investor validation |
| **P1 - MVP** | Regulator Dashboard | Regulatory endorsement accelerator |
| **P2 - Launch** | Factory Owner ROI, Temporal Patterns | Subscription value proof |
| **P2 - Launch** | Farmer Registration, Voice IVR | Full feedback loop |
| **P2 - Launch** | Knowledge Management (Upload, Review) | AI quality depends on expert knowledge |
| **P3 - Scale** | Factory Admin, Platform Admin | Self-service operations |
| **P3 - Scale** | Knowledge Management (Version History) | Advanced document management |

---