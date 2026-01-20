# Farmer Power Platform - Epics & Stories

## Overview

This document provides the complete epic and story breakdown for farmer-power-platform, decomposing the requirements from the Product Briefs, UX Design, and Architecture requirements into implementable stories.

**Note:** This index provides an overview. Each epic has its own detailed file with full story definitions.

## Epic Files (Priority Order)

**Note:** Epics are ordered by implementation priority based on dependency analysis (updated 2026-01-01).

| Priority | Epic | File | Status | Stories | Dependencies |
|----------|------|------|--------|---------|--------------|
| P0 | Epic 0 | [epic-0-infrastructure.md](epic-0-infrastructure.md) | Done | 0.1-0.3 | None |
| P0 | Epic 1 | [epic-1-plantation-model.md](epic-1-plantation-model.md) | Done | 1.1-1.9 | Epic 0 |
| P0 | Epic 2 | [epic-2-collection-model.md](epic-2-collection-model.md) | Done | 2.1-2.11 | Epic 0, 1 |
| P0 | **Epic 0.4** | [epic-0-4-e2e-tests.md](epic-0-4-e2e-tests.md) | **In Progress** | **0.4.1-0.4.9** | **Epic 0, 1, 2** |
| P0 | **Epic 0.6** | [epic-0-6-infrastructure-hardening.md](epic-0-6-infrastructure-hardening.md) | **Backlog** | **0.6.1-0.6.10** | **Epic 0.4** |
| P1 | Epic 0.5 | [epic-0-5-frontend.md](epic-0-5-frontend.md) | Backlog | 0.5.1-0.5.6 | Epic 0 |
| P1 | **Epic 0.75** | [epic-0-75-ai-model.md](epic-0-75-ai-model.md) | **Backlog** | **0.75.1-0.75.7** | **Epic 0** |
| P1 | **Epic 0.8** | [epic-0-8-demo-developer-tooling.md](epic-0-8-demo-developer-tooling.md) | **Backlog** | **0.8.1-0.8.5** | **Epic 0.4, 1, 2** |
| P1 | **Epic 13** | [epic-13-platform-cost.md](epic-13-platform-cost.md) | **Backlog** | **13.1-13.7** | **Epic 0.75** |
| P2 | **Epic 11** | [epic-11-registration-kiosk.md](epic-11-registration-kiosk.md) | Backlog | 11.1-11.4 | Epic 0.5, 1 |
| P2 | **Epic 9** | [epic-9-admin-portal.md](epic-9-admin-portal.md) | Backlog | 9.1-9.4 | Epic 0.5, 1 |
| P3 | Epic 5 | [epic-5-diagnosis-ai.md](epic-5-diagnosis-ai.md) | Backlog | 5.1-5.9 | **Epic 0.75**, 1, 2 |
| P3 | **Epic 10** | [epic-10-regulator.md](epic-10-regulator.md) | Backlog | 10.1-10.4 | Epic 0.5, 2 |
| P4 | Epic 6 | [epic-6-action-plans.md](epic-6-action-plans.md) | Backlog | 6.1-6.6 | **Epic 0.75**, 5 |
| P4 | Epic 4 | [epic-4-sms-feedback.md](epic-4-sms-feedback.md) | Backlog | 4.1-4.7 | Epic 1, 2 |
| P5 | Epic 7 | [epic-7-voice-ivr.md](epic-7-voice-ivr.md) | Backlog | 7.1-7.5 | Epic 4, 6 |
| P5 | Epic 8 | [epic-8-voice-advisor.md](epic-8-voice-advisor.md) | Backlog | 8.1-8.7 | **Epic 0.75**, 5, 6 |
| P5 | **Epic 12** | [epic-12-engagement-model.md](epic-12-engagement-model.md) | **Backlog** | **12.1-12.8** | **Epic 0.75**, 1 |
| P6 | **Epic 3** | [epic-3-dashboard.md](epic-3-dashboard.md) | Backlog | 3.1-3.11 | Epic 0.5, 1, 2, 4, 5, 6 |

### Key Changes (2026-01-20)

1. **Epic 0.8 (Demo & Developer Tooling)** - NEW: Unified demo data strategy (ADR-020), 5 stories, 22 story points
2. **Epic 0.8 provides** - Pydantic-validated seed loader + Polyfactory-based data generator

### Key Changes (2026-01-12)

1. **Epic 13 (Platform Cost)** - NEW: Unified cost aggregation service (ADR-016), 7 stories, 28 story points
2. **Epic 13 blocks Story 9.6** - LLM Cost Dashboard now consumes platform-cost gRPC instead of ai-model

### Key Changes (2026-01-01)

1. **Epic 0.4 (E2E Tests)** - NEW: 9 test scenarios validating full stack integration
2. **Epic 0.6 (Infrastructure Hardening)** - NEW: Implements ADRs 004-011 (35 story points, 10 stories)
3. **Epic 1 & 2 marked Done** - Plantation Model and Collection Model complete
4. **Story 0.4.9 blocked** - Blocked by Epic 0.6 (needs DAPR streaming patterns)

### Key Changes (2025-12-28)

1. **Epic 0.75 (AI Model Foundation)** - NEW: Enables Epic 5, 6, 8, 12
2. **Epic 12 (Engagement Model)** - NEW: Farmer motivation engine (9th domain model)
3. **Epic 3 (Dashboard) moved to P6** - Requires most other epics; was incorrectly prioritized early
4. **Epic 11 (Kiosk) moved to P2** - Simplest UI, ideal for validating React patterns first
5. **Epic 9 (Admin Portal) moved to P2** - Simple CRUD, good second React app
6. **Epic 10 (Regulator) moved to P3** - Read-only analytics, simpler than Dashboard
7. **Story 3.1 (BFF Setup) moved to Epic 0.5.6** - BFF is shared infrastructure for all frontends

### Frontend Implementation Order

For React/frontend development, the recommended progression is:

| Order | Epic | Rationale |
|-------|------|-----------|
| 1st | Epic 11 (Kiosk) | Simplest PWA, 1 domain model, validates React patterns |
| 2nd | Epic 9 (Admin Portal) | CRUD operations, establishes BFF patterns |
| 3rd | Epic 10 (Regulator) | Read-only analytics, tests aggregation patterns |
| 4th | Epic 3 (Dashboard) | Most complex, applies all learned patterns |

## Requirements Inventory

### Functional Requirements

**Farmer Communication (SMS/Voice IVR)**
- FR1: Farmer receives SMS within 3 hours of delivery
- FR2: SMS in local language (Swahili, Kikuyu, Luo), under 160 characters
- FR3: SMS shows Grade (stars), score, and ONE specific actionable tip
- FR4: Price impact shown in KES
- FR5: Farmer can call Voice IVR shortcode for detailed explanation
- FR6: Voice IVR plays action plan via TTS in selected language (2-3 min max)
- FR7: Voice IVR supports language selection (Swahili, Kikuyu, Luo)
- FR8: SMS includes personalization (farmer name, improvement trajectory)

**Factory Dashboard**
- FR9: Factory Manager can view farmer quality dashboard
- FR10: Dashboard filters by grade, collection point, trend
- FR11: One-click contact for problem farmers (SMS/WhatsApp)
- FR12: Daily reports auto-generated by 6 AM
- FR13: Dashboard shows "action needed" / "watch" / "wins" categorization
- FR14: Dashboard loads in < 3 seconds

**Data Ingestion API**
- FR15: API accepts END_BAG events from QC Analyzer
- FR16: API accepts POOR_QUALITY_DETECTED events to trigger AI analysis
- FR17: Batch upload supported for intermittent connectivity (queue-based retry)
- FR18: API validates incoming data schema (reject malformed)
- FR19: API returns confirmation with event ID and processing status

**Collection Model**
- FR20: Store quality grading results linked to farmer_id and bag_id
- FR21: Store images and evidence in Azure Blob Storage
- FR22: Support push mode (webhook from QC Analyzer) and pull mode (Weather API)
- FR23: Emit events to Dapr pub/sub for downstream processing

**Knowledge Model**
- FR24: Diagnose quality issues from collected data (disease, weather, technique)
- FR25: Weather Impact Analyzer correlates weather with quality (3-7 day lag)
- FR26: Disease Detection from image analysis
- FR27: Store diagnoses in Analysis DB with confidence and severity
- FR28: Aggregate events within 24-hour window per farmer before analysis

**Action Plan Model**
- FR29: Generate personalized weekly action plans for farmers
- FR30: Dual-format output: detailed report + SMS summary
- FR31: Farm-scale-aware recommendations (smallholder/medium/estate)
- FR32: Translation to farmer's preferred language
- FR33: Schedule: Monday 6 AM weekly generation

**Plantation Model**
- FR34: Store farmer master data (name, phone, national_id, farm_size, location)
- FR35: Store factory and collection point data
- FR36: Farmer registration generates unique Farmer ID (e.g., WM-4521)
- FR37: Track farmer performance history and yield metrics
- FR38: Store farmer communication preferences (pref_channel, pref_lang)

**Notification Model**
- FR39: Unified channel abstraction (SMS, Voice IVR, WhatsApp)
- FR40: SMS cost optimization with tiered strategy (GSM-7, 160/320 chars)
- FR41: Delivery assurance with retry logic (standard: 3x, critical: 6x)
- FR42: Lead farmer escalation for unreachable farmers
- FR43: Group messaging and regional broadcasts
- FR44: Inbound keyword handling (HELP, DONE, STOP, STATUS)

**AI Model**
- FR45: LangGraph orchestration of multi-agent workflows
- FR46: RAG enrichment from Pinecone knowledge base
- FR47: Triage Agent routes quality issues to specialized analyzers
- FR48: Disease Analyzer, Weather Analyzer, Technique Analyzer
- FR49: MCP Servers expose data to AI agents (Collection, Analysis, Plantation, Action Plan)

**Conversational AI Model (Voice Quality Advisor)**
- FR50: Farmer calls Voice Advisor number from any basic phone
- FR51: Identify farmer by caller ID or spoken farmer ID
- FR52: Swahili speech-to-text transcription
- FR53: Intent classification for quality-related questions
- FR54: Personalized response generation with farmer's history context
- FR55: Guided dialogue (3-5 turns max, 3 min max session)
- FR56: SMS fallback if AI cannot understand
- FR57: Streaming response for natural conversation feel (<2s perceived latency)

**TBK Grading Integration**
- FR58: Support TBK binary classification (Primary/Secondary)
- FR59: Multi-head model output: leaf_type, coarse_subtype, banji_hardness
- FR60: Bag summary with primary_percentage, leaf_type_distribution
- FR61: Grade calculation logic per TBK specification

### NonFunctional Requirements

**Performance & Scale**
- NFR1: Support 100 factories, 800,000 farms at Kenya scale
- NFR2: Process 10,000 quality events/hour (peak: 20,000)
- NFR3: Handle 100 API requests/second (peak: 200)
- NFR4: Support 500 concurrent dashboard users (peak: 1,000)
- NFR5: Process 200 LLM calls/minute (peak: 400)
- NFR6: Dashboard loads in < 3 seconds
- NFR7: Quality Event → Action Plan < 60 seconds (p95)
- NFR8: Quality Event → Farmer SMS < 5 minutes

**Reliability & Availability**
- NFR9: System availability > 99.5%
- NFR10: SMS delivery rate > 98%
- NFR11: Dashboard staleness < 30 seconds
- NFR12: Graceful degradation during cloud outages (batch sync)

**AI Accuracy**
- NFR13: AI grading accuracy ≥ 97% agreement with expert human graders
- NFR14: Within-1-grade accuracy ≥ 99%
- NFR15: Critical misgrade (Premium↔Reject confusion) < 0.1%
- NFR16: Voice STT accuracy (Swahili) > 85%
- NFR17: Intent recognition accuracy > 90%

**Cost Efficiency**
- NFR18: Monthly platform cost target: $20,000-25,000 (Kenya Phase 1)
- NFR19: Per factory cost: < $250/month
- NFR20: Per farmer cost: < $0.50/year
- NFR21: Voice Advisor cost per call: < $0.30

**Security & Compliance**
- NFR22: Data residency: Azure South Africa North region
- NFR23: Kenya Data Protection Act 2019 compliance
- NFR24: Encryption at rest (AES-256) and in transit (TLS 1.3)
- NFR25: Field-level encryption for PII (farmer name, phone, GPS)
- NFR26: OAuth2/OpenID Connect authentication
- NFR27: RBAC roles: Admin, FactoryManager, FactoryViewer, Regulator

**Observability**
- NFR28: Full observability via OpenTelemetry (logging, metrics, tracing)
- NFR29: LangChain/LangGraph traces for AI debugging
- NFR30: Cost attribution per farmer_id, factory_id, agent type

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1-FR4, FR8 | Epic 4 | Farmer SMS Feedback |
| FR5-FR7 | Epic 7 | Voice IVR Experience |
| FR9-FR14 | Epic 3 | Factory Manager Dashboard |
| FR15-FR19 | Epic 2 | Data Ingestion API |
| FR20-FR23 | Epic 2 | Collection Model |
| FR24-FR28 | Epic 5 | Knowledge Model / Diagnosis |
| FR29-FR33 | Epic 6 | Action Plan Model |
| FR34-FR38 | Epic 1 | Plantation Model / Registration |
| FR39-FR44 | Epic 4 | Notification Model |
| FR45-FR49 | **Epic 0.75** | **AI Model Foundation** |
| FR50-FR57 | Epic 8 | Conversational AI / Voice Advisor |
| FR58-FR61 | Epic 2 | TBK Grading Integration |
| Engagement | **Epic 12** | **Farmer Engagement & Motivation** |

## Epic Summaries

### Epic 0: Platform Infrastructure Foundation
Cross-cutting infrastructure that enables domain model services. These stories establish shared libraries, proto definitions, and foundational patterns used across all epics.
**Dependencies:** None (foundational)

### Epic 0.4: E2E Test Scenarios
End-to-end integration tests validating the full stack: Plantation Model, Collection Model, MCP Servers, and DAPR events. Ensures all domain models work together correctly.
**Dependencies:** Epic 0, 1, 2
**Stories:** 9 test scenarios covering infrastructure, MCP contracts, registration flows, blob ingestion, cross-model events

### Epic 0.6: Infrastructure Hardening (ADR Implementation)
Cross-cutting infrastructure improvements implementing 8 accepted Architecture Decision Records (ADRs). Establishes shared patterns, type safety, resilience mechanisms, and DAPR SDK streaming subscriptions.
**Dependencies:** Epic 0.4
**ADRs Implemented:** ADR-004 (Type Safety), ADR-005 (gRPC Retry), ADR-006 (DLQ), ADR-007 (Cache), ADR-008 (Linkage), ADR-009 (Logging), ADR-010 (DAPR Patterns), ADR-011 (Service Architecture)
**Validated By:** PoC at `tests/e2e/poc-dapr-patterns/` (5/5 tests passing)
**Story Points:** 35 total (10 stories)

### Epic 0.5: Frontend & Identity Infrastructure
Cross-cutting frontend and authentication infrastructure that enables all web applications. These stories establish the shared component library, authentication flow, and foundational frontend patterns.
**Dependencies:** Epic 0

### Epic 0.75: AI Model Foundation (NEW)
Cross-cutting AI infrastructure that enables all AI-powered domain models. These stories establish the LLM gateway, agent framework, RAG engine, and prompt management patterns.
**Dependencies:** Epic 0
**Blocks:** Epic 5, 6, 8, 12
**FRs covered:** FR45, FR46, FR47, FR48, FR49

### Epic 0.8: Demo & Developer Tooling (NEW)
Cross-cutting developer tooling that enables demo environments and developer productivity. Implements unified demo data strategy with Pydantic-validated seed loader and Polyfactory-based data generator.
**Dependencies:** Epic 0.4, 1, 2
**ADR:** ADR-020 (Demo Data Strategy with Pydantic Validation)
**Tools provided:** `load-demo-data.py`, `generate-demo-data.py`

### Epic 1: Farmer Registration & Data Foundation
Factory staff can register farmers into the system. Farmers receive their unique ID and are ready to be tracked.
**Dependencies:** Epic 0
**FRs covered:** FR34, FR35, FR36, FR37, FR38

### Epic 2: Quality Data Ingestion
QC Analyzer can submit quality grading results to the platform. Data is validated, stored, and events are emitted for downstream processing.
**Dependencies:** Epic 0, 1
**FRs covered:** FR15-FR23, FR58-FR61

### Epic 3: Factory Manager Dashboard
Factory Quality Managers can view farmer quality data, identify problem farmers, and take action. Daily reports are auto-generated.
**Dependencies:** Epic 0.5, 1, 2, 4, 5, 6 (LAST frontend epic - requires most other epics)
**FRs covered:** FR9, FR10, FR11, FR12, FR13, FR14

### Epic 4: Farmer SMS Feedback
Farmers receive personalized SMS feedback within 3 hours of delivery, with actionable tips in their local language.
**Dependencies:** Epic 1, 2
**FRs covered:** FR1-FR4, FR8, FR39-FR44

### Epic 5: Quality Diagnosis AI
Platform automatically diagnoses quality issues (disease, weather, technique) and stores analysis results for action plan generation.
**Dependencies:** Epic 0.75, 1, 2
**FRs covered:** FR24-FR28

### Epic 6: Weekly Action Plans
Farmers receive weekly personalized action plans with specific recommendations tailored to their farm size and recent quality issues.
**Dependencies:** Epic 0.75, 5
**FRs covered:** FR29, FR30, FR31, FR32, FR33

### Epic 7: Voice IVR Experience
Farmers can call a shortcode to hear their detailed action plan via TTS in their preferred language.
**Dependencies:** Epic 4, 6
**FRs covered:** FR5, FR6, FR7

### Epic 8: Voice Quality Advisor (Conversational AI)
Farmers can call and have a two-way conversation about quality improvement, asking questions in Swahili.
**Dependencies:** Epic 0.75, 5, 6
**FRs covered:** FR50-FR57

### Epic 9: Platform Admin Portal
Platform administrators can onboard factories, manage users, and monitor platform health.
**Dependencies:** Epic 0.5, 1 (Simple CRUD - 2nd frontend to build)

### Epic 10: Regulator Dashboard
Regulators can view national and regional quality metrics and trends.
**Dependencies:** Epic 0.5, 2 (Read-only analytics - 3rd frontend to build)

### Epic 11: Registration Kiosk PWA
Field staff can register farmers using a mobile PWA with offline support.
**Dependencies:** Epic 0.5, 1 (Simplest UI - 1st frontend to build)

### Epic 12: Farmer Engagement & Motivation (NEW)
Track farmer progress with streaks, milestones, and levels. Enable Duolingo-style encouragement patterns that motivate farmers to consistently improve quality.
**Dependencies:** Epic 0.75, 1
**Domain Model:** Engagement Model (9th domain model)

### Epic 13: Unified Platform Cost Service (NEW)
Centralized cost aggregation service collecting costs from all billable services (LLM, Document Intelligence, Embeddings, SMS) via DAPR pub/sub. Exposes unified gRPC API for Platform Admin Cost Dashboard.
**Dependencies:** Epic 0.75
**ADR:** ADR-016 (Unified Cost Model and Platform Cost Service)
**NFRs covered:** NFR18, NFR19, NFR20, NFR30 (cost attribution)
**Blocks:** Story 9.6 (LLM Cost Dashboard)
