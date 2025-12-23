# Source of Truth Declaration

**This document is the canonical source of truth for all technical architecture decisions.**

| Aspect | Status |
|--------|--------|
| Domain Models | **8 models** (see Model Overview below) |
| Infrastructure Decisions | Authoritative |
| Integration Patterns | Authoritative |
| AI/LLM Architecture | Authoritative |

**When conflicts arise:** This document takes precedence over product briefs, which are point-in-time snapshots.

**Related Documents:**
- `index.md` - Navigation and coherence tracking
- `project-context.md` - Lean AI agent rules (derived from this document)
- `architecture-decision-index.md` - Decision traceability matrix

## Platform Model Overview (8 Models)

| # | Model | Responsibility | Section |
|---|-------|----------------|---------|
| 1 | Collection Model | Data ingestion, document storage | [Link](#collection-model-architecture) |
| 2 | Knowledge Model | Diagnoses, pattern detection | [Link](#knowledge-model-architecture) |
| 3 | Plantation Model | Farmer/factory master data | [Link](#plantation-model-architecture) |
| 4 | Action Plan Model | Recommendation generation | [Link](#action-plan-model-architecture) |
| 5 | Market Analysis Model | Buyer matching, market intel | [Link](#market-analysis-model-architecture) |
| 6 | AI Model | LLM orchestration, RAG | [Link](#ai-model-architecture) |
| 7 | Notification Model | SMS, WhatsApp, Voice IVR (one-way) | [Link](#notification-model-architecture) |
| 8 | Conversational AI Model | Two-way dialogue across channels | [Link](#conversational-ai-model-architecture) |

---
