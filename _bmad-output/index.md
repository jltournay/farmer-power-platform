# Farmer Power Platform - Documentation Index

_Single entry point for all platform documentation. This index ensures coherence across all project artifacts._

---

## Source of Truth Declaration

| Aspect | Canonical Source | Purpose |
|--------|------------------|---------|
| **Technical Architecture** | `architecture.md` | All domain models, infrastructure decisions, patterns |
| **AI Agent Rules** | `project-context.md` | Critical rules for AI agents during implementation |
| **Decision Traceability** | `architecture-decision-index.md` | Maps decisions to documentation coverage |
| **AI Implementation** | `ai-model-developer-guide.md` | Detailed AI/LLM development patterns |
| **User Experience** | `ux-design-specification.md` | UI/UX patterns and user journeys |

**Rule:** When documents conflict, `architecture.md` is the authoritative source for technical decisions.

---

## Platform Domain Models (8 Total)

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

**Note:** Product briefs created before v1.1 reference 6 models. The Notification Model was implicit in v1.0 and the Conversational AI Model was added in v1.1 (2025-12-20).

---

## Document Inventory

### Core Architecture Documents

| Document | Description | Last Updated |
|----------|-------------|--------------|
| [`architecture.md`](./architecture.md) | Complete platform architecture with all 8 domain models | 2025-12-20 |
| [`project-context.md`](./project-context.md) | Lean AI agent rules (136 rules) | 2025-12-20 |
| [`architecture-decision-index.md`](./architecture-decision-index.md) | Decision traceability matrix | 2025-12-20 |
| [`ai-model-developer-guide.md`](./ai-model-developer-guide.md) | AI/LLM development patterns | 2025-12-17 |
| [`ux-design-specification.md`](./ux-design-specification.md) | User experience design | 2025-12-17 |

### Product Briefs (Point-in-Time Snapshots)

| Document | Scope | Date | Models Referenced |
|----------|-------|------|-------------------|
| [`analysis/product-brief-farmer-power-platform-2025-12-16.md`](./analysis/product-brief-farmer-power-platform-2025-12-16.md) | Full platform | 2025-12-16 | 6 (pre-Notification/Conversational) |
| [`analysis/product-brief-voice-quality-advisor-2025-12-20.md`](./analysis/product-brief-voice-quality-advisor-2025-12-20.md) | Voice Quality Advisor feature | 2025-12-20 | 8 (includes Conversational AI) |

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
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────┐
│ architecture.md │    │ project-context.md  │    │ Product Briefs  │
│ (Source of Truth)│    │ (AI Agent Rules)   │    │ (Point-in-Time) │
└────────┬────────┘    └──────────┬──────────┘    └─────────────────┘
         │                        │
         │ Traces to              │ Derived from
         ▼                        ▼
┌─────────────────────┐    ┌─────────────────────┐
│ architecture-       │    │ ai-model-developer- │
│ decision-index.md   │    │ guide.md            │
│ (Decision Matrix)   │    │ (Implementation)    │
└─────────────────────┘    └─────────────────────┘
```

---

## Update Guidelines

### When to Update Each Document

| Trigger | Update |
|---------|--------|
| New domain model added | `architecture.md` (add model section) → `index.md` (update count) → `project-context.md` (add boundaries) |
| New architectural decision | `architecture.md` → `architecture-decision-index.md` (add entry) |
| New AI agent pattern | `architecture.md` → `ai-model-developer-guide.md` (add pattern) → `project-context.md` (add rules) |
| New feature requiring PRD | Create new product brief in `analysis/` → Reference in `index.md` |
| Technology version change | `project-context.md` (update versions) → `architecture.md` if major |

### Coherence Checklist

When making significant changes, verify:

- [ ] Model count matches across `index.md`, `architecture.md`, `project-context.md`
- [ ] All models have entries in Domain Model Boundaries table (`project-context.md`)
- [ ] New decisions are indexed in `architecture-decision-index.md`
- [ ] AI agent types include all current types in `ai-model-developer-guide.md`
- [ ] Product briefs are marked with their model count context

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

### MCP Server Lookup

| MCP Server | Owned By | Data Exposed |
|------------|----------|--------------|
| MCP-CollectedDocuments | Collection Model | Quality events, images, weather |
| MCP-Analysis | Knowledge Model | Diagnoses, disease detection |
| MCP-ActionPlan | Action Plan Model | Generated action plans |
| MCP-PlantationModel | Plantation Model | Farms, factories, grading models |

**Note:** AI Model and Notification Model do NOT expose MCP servers (they orchestrate/deliver, not own data). Conversational AI Model uses existing MCPs via AI Model.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-16 | Initial platform with 6 core models |
| 1.1 | 2025-12-20 | Added Notification Model (explicit), Conversational AI Model (8th model) |

---

_Last Updated: 2025-12-20_
_Maintainer: Platform Architecture Team_