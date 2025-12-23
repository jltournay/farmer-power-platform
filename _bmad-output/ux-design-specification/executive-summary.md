# Executive Summary

## Project Vision

Farmer Power Platform transforms tea quality data into tangible value for all stakeholders. By connecting real-time AI grading directly to pricing and actionable feedback, the platform creates a virtuous circle: better farming practices → measurably better outcomes → higher prices for farmers and less waste for factories.

The UX challenge is bridging extreme user diversity - from basic feature phones receiving 160-character SMS messages in Swahili to factory managers expecting modern action-oriented dashboards.

## Target Users

**Primary (Cloud Platform):**

| User | Context | Primary Interface |
|------|---------|-------------------|
| **Wanjiku (Farmer)** | 800,000 smallholders, feature phones, 70% income from tea | SMS (160 chars, Swahili/Kikuyu/Luo) |
| **Joseph (Factory Quality Manager)** | Reviews dashboards, identifies problem farmers, manages 2 extension officers | Web Dashboard |
| **Factory Owner** | Makes subscription decisions, reviews ROI, needs competitive intelligence | Web Dashboard (reports) |
| **Regulator (Tea Board of Kenya)** | National quality trends, regional comparisons | Web Dashboard (analytics) |

**Administrative Interfaces (Cloud Platform):**

| User | Context | Primary Interface |
|------|---------|-------------------|
| **Factory Admin** | Configures payment policies, pricing rules, SMS templates for their factory | Web Admin Panel |
| **Platform Admin** | Onboards factories, manages users, RBAC, system configuration | Web Admin Panel |
| **Registration Clerk** | Enrolls new farmers, issues ID cards, assigns collection points | Web/Mobile Registration |

**Out of Scope (QC Analyzer Hardware):**
- Peter (Collection Clerk) - Uses tagging device
- Grace (Factory QC Operator) - Uses QC Analyzer interface

## TBK Grading Model Integration

> **Regulatory Requirement:** Tea Board of Kenya (TBK) mandates binary grading (Primary/Secondary) based on leaf type classification per Tea Act 2020.

### Grading System Overview

| Aspect | TBK Specification |
|--------|-------------------|
| **Grading Type** | Binary: Primary (best) / Secondary (lower) |
| **Classification** | 7 leaf types with conditional logic |
| **Output** | Percentage of Primary leaves per bag |

### Leaf Type to Grade Mapping

| Leaf Type | Grade | UX Coaching Message |
|-----------|-------|---------------------|
| `bud` | Primary ✅ | Perfect plucking! |
| `one_leaf_bud` | Primary ✅ | Excellent - fine plucking standard |
| `two_leaves_bud` | Primary ✅ | Good - standard fine plucking |
| `three_plus_leaves_bud` | Secondary ⚠️ | "Pick earlier - take only 2 leaves and a bud" |
| `single_soft_leaf` | Primary ✅ | Good - tender young leaf |
| `coarse_leaf` | Secondary ⚠️ | "These leaves are too old - pick younger growth" |
| `banji (soft)` | Primary ✅ | Acceptable dormant shoot |
| `banji (hard)` | Secondary ⚠️ | "Dormant shoots - your bushes may need pruning" |

### Dashboard Threshold System

To maintain action-oriented workflows, Primary % maps to familiar categories:

| Category | Primary % | Dashboard Color | Joseph's Action |
|----------|-----------|-----------------|-----------------|
| **WIN** | ≥85% | 🟢 Green | Celebrate, maintain relationship |
| **WATCH** | 70-84% | 🟡 Yellow | Monitor, send encouragement |
| **ACTION NEEDED** | <70% | 🔴 Red | Assign extension officer visit |

### SMS Design: Percentage + Visual + Top Issue

```
Mama Wanjiku, chai yako:
✅ 82% daraja la kwanza!
Tatizo: majani 3+ (coarse)
Kesho: chuma majani 2 tu + bud
```

**Why this works:**
- ✅/⚠️ gives instant emotional feedback
- Percentage shows progress trajectory (65% → 78% → 82%)
- Top issue (leaf type) explains WHY
- Action is specific and achievable
- Characters: ~140/160 ✓

---

## Key Design Challenges

1. **160-Character SMS Constraint** - The farmer's entire experience must fit in SMS. Every word must convey identity, result (Primary %), reasoning (leaf type issue), and actionable next step.

2. **Extreme Tech Diversity** - Same platform serves basic feature phones (SMS) and modern web dashboards. Design patterns must adapt gracefully.

3. **Low-Literacy Accessibility** - Visual indicators (✅/⚠️) instead of complex terminology. Names instead of IDs. Photos at factory kiosks for visual confirmation. Percentage communicates progress simply.

4. **Action-Oriented Over Data-Heavy** - Dashboards must answer "what should I do?" not "here's data." One-click contact, clear categorization (Action Needed / Watch / Wins) based on Primary % thresholds.

5. **Cultural & Language Authenticity** - Swahili messaging that feels human, not systematic. Celebration of progress. Trust through transparency.

6. **One-Way Communication Limitation** - Farmers receive but cannot respond via traditional SMS. Need mechanism for questions, disputes, or callbacks without building full chat support.

7. **Shared Device Reality** - Rural households often share phones. UX must handle multiple farmer identities per phone number gracefully.

8. **Binary to Actionable** - TBK's binary grading (Primary/Secondary) must translate into specific, actionable coaching tied to leaf type issues.

## Design Opportunities

1. **Primary Percentage as Progress Metric** - Communicates quality improvement trajectory. "Up from 72% to 85% Primary this week!" shows tangible progress.

2. **Progress Celebration Engine** - Visible improvement tracking motivates behavior change. "Pongezi! 85% daraja la kwanza!"

3. **Keyword-Based Two-Way Communication** - Simple SMS keywords (HELP, DISPUTE) create tickets for factory team. Gives farmers agency without complex chat infrastructure.
   - *War Room Decision: Keyword triggers → DAPR event → factory dashboard ticket*

4. **Personalized Multi-Farmer SMS** - Handle shared phones by including farmer name prominently. "Mama Wanjiku, your tea: ⭐⭐⭐⭐"
   - *Phase 1: Name in SMS + kiosk lookup*
   - *Phase 2: WhatsApp multi-profile selection*

5. **Temporal Intelligence Dashboard** - Day-of-week and time-of-day heatmaps reveal systemic issues (transport, storage, timing).
   - *War Room Decision: Pattern visualization with drill-down, not AI-generated hypotheses*

6. **Lightweight Delegation Workflow** - Joseph assigns problem farmers to extension officers directly from dashboard.
   - *War Room Decision: Assign button → notification → DONE keyword closes loop. Not a full CRM.*

7. **Industry Benchmarking** - Give factory owners competitive context with anonymized regional comparisons.
   - *Phase 2 feature*

## Key Design Principle

> *"Boring technology that works"* - Every feature justified by clear action, minimal scope, measurable outcome.

## Phase Boundaries

| Phase | Scope |
|-------|-------|
| **Phase 1** | Core SMS experience, keyword responses (HELP/DISPUTE), basic dashboard with temporal patterns, lightweight delegation |
| **Phase 2** | WhatsApp enhancements, multi-profile selection, industry benchmarking, advanced analytics |

## Architectural Flags (For Architect Discussion)

 **Collection Point Data Gap** - Focus group revealed Joseph needs to identify quality patterns by collection point, not just individual farmers. Currently, the collection point is not captured in the data model. Consider:
1.  Adding Collection Point entity to Plantation Model, 
2. Updating QC Analyzer tagging to include collection_point_id. UX value: HIGH for factory quality managers. Requires cross-project coordination (QC Analyzer + Cloud Platform).

---
