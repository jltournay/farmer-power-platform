# Farmer Power Platform - Documentation Index

_Single entry point for all platform documentation. This index ensures coherence across all project artifacts._

---

## Source of Truth Declaration

| Aspect | Canonical Source | Purpose |
|--------|------------------|---------|
| **Technical Architecture** | `architecture/index.md` | All domain models, infrastructure decisions, patterns |
| **AI Agent Rules** | `project-context.md` | Critical rules for AI agents during implementation |
| **Decision Traceability** | `architecture-decision-index.md` | Maps decisions to documentation coverage |
| **AI Implementation** | `ai-model-developer-guide/index.md` | Detailed AI/LLM development patterns |
| **User Experience** | `ux-design-specification/index.md` | UI/UX patterns and user journeys |
| **Epics & Stories** | `epics/index.md` | Implementation backlog and user stories (sharded by epic) |
| **Test Strategy** | `test-design-system-level.md` | System-level test design and validation approach |
| **Product Vision** | `analysis/product-brief-*.md` | Point-in-time product requirements |
| **Domain Specification** | `analysis/tbk-kenya-tea-grading-model-specification.md` | TBK Kenya tea grading domain knowledge |

**Rule:** When documents conflict, `architecture/index.md` is the authoritative source for technical decisions.

---

## Platform Domain Models (9 Total)

| # | Model | Responsibility | Added |
|---|-------|----------------|-------|
| 1 | **Collection Model** | Data ingestion, document storage, quality event intake | v1.0 |
| 2 | **Knowledge Model** | Diagnoses, pattern detection, root cause analysis | v1.0 |
| 3 | **Plantation Model** | Farmer/factory/region master data, digital twin | v1.0 |
| 4 | **Action Plan Model** | Weekly action plan generation, recommendations | v1.0 |
| 5 | **Market Analysis Model** | Buyer profiles, lot matching, market intelligence | v1.0 |
| 6 | **AI Model** | Centralized LLM orchestration, RAG, agent execution | v1.0 |
| 7 | **Notification Model** | Message delivery: SMS, WhatsApp, Voice IVR (one-way) | v1.0 |
| 8 | **Conversational AI Model** | Two-way dialogue: voice chatbot, text chat (multi-channel) | v1.1 |
| 9 | **Engagement Model** | Farmer progress tracking, streaks, milestones, motivation (Duolingo-style) | v1.2 |

**Note:** Product briefs created before v1.1 reference 6 models. The Notification Model was implicit in v1.0, Conversational AI Model added in v1.1 (2025-12-20), and Engagement Model added in v1.2 (2025-12-28).

---

## Document Inventory

### Core Architecture Documents (Sharded for AI Agent Efficiency)

| Document | Description | Last Updated |
|----------|-------------|--------------|
| [`architecture/index.md`](./architecture/index.md) | Complete platform architecture with all 9 domain models | 2025-12-28 |
| [`project-context.md`](./project-context.md) | Lean AI agent rules (136 rules) - ALWAYS LOAD FIRST | 2025-12-20 |
| [`architecture-decision-index.md`](./architecture-decision-index.md) | Decision traceability matrix | 2025-12-20 |
| [`ai-model-developer-guide/index.md`](./ai-model-developer-guide/index.md) | AI/LLM development patterns (12 sections) | 2025-12-23 |
| [`ux-design-specification/index.md`](./ux-design-specification/index.md) | User experience design (15 sections) | 2025-12-23 |
| [`epics/index.md`](./epics/index.md) | Epics and user stories (14 epics, sharded) | 2025-12-28 |
| [`test-design-system-level.md`](./test-design-system-level.md) | System-level test strategy and design | 2025-12-23 |

### Epics & Stories (Sharded by Epic - Priority Order)

**Note:** Epics reordered by priority on 2025-12-28. See `epics/index.md` for full dependency analysis.

| Priority | Epic | File | Status | Stories |
|----------|------|------|--------|---------|
| P0 | Epic 0 | [`epics/epic-0-infrastructure.md`](./epics/epic-0-infrastructure.md) | Done | 0.1-0.3 |
| P0 | Epic 1 | [`epics/epic-1-plantation-model.md`](./epics/epic-1-plantation-model.md) | In Progress | 1.1-1.8 |
| P0 | Epic 2 | [`epics/epic-2-collection-model.md`](./epics/epic-2-collection-model.md) | Done | 2.1-2.9 |
| P1 | Epic 0.5 | [`epics/epic-0-5-frontend.md`](./epics/epic-0-5-frontend.md) | Backlog | 0.5.1-0.5.6 |
| P1 | **Epic 0.75** | [`epics/epic-0-75-ai-model.md`](./epics/epic-0-75-ai-model.md) | **Backlog** | **0.75.1-0.75.7** |
| P2 | Epic 11 | [`epics/epic-11-registration-kiosk.md`](./epics/epic-11-registration-kiosk.md) | Backlog | 11.1-11.4 |
| P2 | Epic 9 | [`epics/epic-9-admin-portal.md`](./epics/epic-9-admin-portal.md) | Backlog | 9.1-9.4 |
| P3 | Epic 5 | [`epics/epic-5-diagnosis-ai.md`](./epics/epic-5-diagnosis-ai.md) | Backlog | 5.1-5.9 |
| P3 | Epic 10 | [`epics/epic-10-regulator.md`](./epics/epic-10-regulator.md) | Backlog | 10.1-10.4 |
| P4 | Epic 6 | [`epics/epic-6-action-plans.md`](./epics/epic-6-action-plans.md) | Backlog | 6.1-6.6 |
| P4 | Epic 4 | [`epics/epic-4-sms-feedback.md`](./epics/epic-4-sms-feedback.md) | Backlog | 4.1-4.7 |
| P5 | Epic 7 | [`epics/epic-7-voice-ivr.md`](./epics/epic-7-voice-ivr.md) | Backlog | 7.1-7.5 |
| P5 | Epic 8 | [`epics/epic-8-voice-advisor.md`](./epics/epic-8-voice-advisor.md) | Backlog | 8.1-8.7 |
| P5 | **Epic 12** | [`epics/epic-12-engagement-model.md`](./epics/epic-12-engagement-model.md) | **Backlog** | **12.1-12.8** |
| P6 | Epic 3 | [`epics/epic-3-dashboard.md`](./epics/epic-3-dashboard.md) | Backlog | 3.1-3.12 |

**Sprint Status:** [`sprint-artifacts/sprint-status.yaml`](./sprint-artifacts/sprint-status.yaml)

**AI Agent Loading Strategy:**
1. **Always load first:** `project-context.md` (17 KB - critical rules)
2. **Load by task:** Navigate via index files to load only relevant sections
3. **Never load:** Full sharded folders at once

### Product Briefs & Domain Specifications (Point-in-Time Snapshots)

| Document | Scope | Date | Models Referenced |
|----------|-------|------|-------------------|
| [`analysis/product-brief-farmer-power-platform-2025-12-16.md`](./analysis/product-brief-farmer-power-platform-2025-12-16.md) | Full platform | 2025-12-16 | 6 (pre-Notification/Conversational) |
| [`analysis/product-brief-voice-quality-advisor-2025-12-20.md`](./analysis/product-brief-voice-quality-advisor-2025-12-20.md) | Voice Quality Advisor feature | 2025-12-20 | 8 (includes Conversational AI) |
| [`analysis/tbk-kenya-tea-grading-model-specification.md`](./analysis/tbk-kenya-tea-grading-model-specification.md) | TBK Kenya Tea Grading Model | 2025-12-20 | Domain specification for Knowledge Model |

### Analysis & Research

| Document | Description | Date |
|----------|-------------|------|
| [`analysis/brainstorming-business-model-2025-12-17.md`](./analysis/brainstorming-business-model-2025-12-17.md) | Business model exploration | 2025-12-17 |

### Sprint Artifacts

| Document | Description | Date |
|----------|-------------|------|
| [`sprint-change-proposal-2025-12-20.md`](./sprint-change-proposal-2025-12-20.md) | Change proposal for current sprint | 2025-12-20 |

---

## Document Relationships

```
                              ┌─────────────────────────────────────┐
                              │           index.md                  │
                              │    (Navigation & Coherence)         │
                              └──────────────┬──────────────────────┘
                                             │
       ┌──────────────┬──────────────┬───────┼───────┬──────────────┬──────────────┐
       │              │              │               │              │              │
       ▼              ▼              ▼               ▼              ▼              ▼
┌─────────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐ ┌───────────┐ ┌───────────┐
│architecture/│ │ project-  │ │ Product   │ │   epics/    │ │test-design│ │   ux-     │
│(12 sharded) │ │context.md │ │ Briefs    │ │(12 sharded) │ │system-    │ │design-    │
│Source Truth │ │AI Rules   │ │+ TBK Spec │ │ Stories     │ │level.md   │ │spec/      │
└──────┬──────┘ └─────┬─────┘ └───────────┘ └─────────────┘ └───────────┘ └───────────┘
       │              │
       │ Traces to    │ Derived from
       ▼              ▼
┌─────────────────────┐  ┌─────────────────────────────┐
│ architecture-       │  │ ai-model-developer-guide/   │
│ decision-index.md   │  │ (12 sharded files)          │
│ (Decision Matrix)   │  │                             │
└─────────────────────┘  └─────────────────────────────┘
```

### Traceability Flow

```
Product Brief → Architecture → Epics → Stories → Test Design → Implementation
     ↓              ↓           ↓        ↓            ↓
  Vision      Decisions    Features  Tasks      Validation
```

---

## Update Guidelines

### When to Update Each Document

| Trigger | Update |
|---------|--------|
| New domain model added | `architecture/` (add model file) → `index.md` (update count) → `project-context.md` (add boundaries) |
| New architectural decision | `architecture/` (relevant section) → `architecture-decision-index.md` (add entry) |
| New AI agent pattern | `architecture/ai-model-architecture.md` → `ai-model-developer-guide/` (add pattern) → `project-context.md` (add rules) |
| New feature requiring PRD | Create new product brief in `analysis/` → Reference in `index.md` |
| Technology version change | `project-context.md` (update versions) → `architecture/infrastructure-decisions.md` if major |

### Coherence Checklist

When making significant changes, verify:

- [ ] Model count matches across `index.md`, `architecture/index.md`, `project-context.md`
- [ ] All models have entries in Domain Model Boundaries table (`project-context.md`)
- [ ] New decisions are indexed in `architecture-decision-index.md`
- [ ] AI agent types include all current types in `ai-model-developer-guide/3-agent-development.md`
- [ ] Product briefs are marked with their model count context
- [ ] Sharded folder index files are updated when sections change

---

## Quick Reference

### Model Lookup by Responsibility

| Need | Model |
|------|-------|
| Ingest quality data | Collection Model |
| Diagnose quality issues | Knowledge Model |
| Get farmer/factory data | Plantation Model |
| Generate action plans | Action Plan Model |
| Match lots to buyers | Market Analysis Model |
| Execute LLM/AI tasks | AI Model |
| Send SMS/WhatsApp/Voice | Notification Model |
| Interactive voice/text chat | Conversational AI Model |
| Track farmer progress/streaks | Engagement Model |

### MCP Server Lookup

| MCP Server | Owned By | Data Exposed |
|------------|----------|--------------|
| MCP-CollectedDocuments | Collection Model | Quality events, images, weather |
| MCP-Analysis | Knowledge Model | Diagnoses, disease detection |
| MCP-ActionPlan | Action Plan Model | Generated action plans |
| MCP-PlantationModel | Plantation Model | Farms, factories, grading models |
| MCP-Engagement | Engagement Model | Streaks, milestones, motivation state |

**Note:** AI Model and Notification Model do NOT expose MCP servers (they orchestrate/deliver, not own data). Conversational AI Model uses existing MCPs via AI Model.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-16 | Initial platform with 6 core models |
| 1.1 | 2025-12-20 | Added Notification Model (explicit), Conversational AI Model (8th model) |
| 1.2 | 2025-12-23 | Sharded large documents for AI agent efficiency (architecture, ai-model-developer-guide, ux-design-specification) |
| 1.3 | 2025-12-23 | Complete traceability: Added epics.md, test-design-system-level.md, TBK specification to index |
| 1.4 | 2025-12-28 | Added Engagement Model (9th model) - Duolingo-style farmer motivation engine |
| 1.5 | 2025-12-28 | Sharded epics.md (4,500+ lines) into 12 separate epic files for maintainability |
| 1.6 | 2025-12-28 | **Epic restructure:** Added Epic 0.75 (AI Model Foundation), Epic 12 (Engagement Model). Reordered epics by priority - Epic 3 (Dashboard) moved to P6 (last), Epic 11 (Kiosk) moved to P2 (first UI). Total: 14 epics. |

---

_Last Updated: 2025-12-28_
_Maintainer: Platform Architecture Team_