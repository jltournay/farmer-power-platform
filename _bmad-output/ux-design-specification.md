---
stepsCompleted: [1, 2]
inputDocuments: ['analysis/product-brief-farmer-power-platform-2025-12-16.md']
workflowType: 'ux-design'
lastStep: 2
project_name: 'farmer-power-platform'
user_name: 'Jeanlouistournay'
date: '2025-12-17'
---

# UX Design Specification farmer-power-platform

**Author:** Jeanlouistournay
**Date:** 2025-12-17

---

## Executive Summary

### Project Vision

Farmer Power Platform transforms tea quality data into tangible value for all stakeholders. By connecting real-time AI grading directly to pricing and actionable feedback, the platform creates a virtuous circle: better farming practices → measurably better outcomes → higher prices for farmers and less waste for factories.

The UX challenge is bridging extreme user diversity - from basic feature phones receiving 160-character SMS messages in Swahili to factory managers expecting modern action-oriented dashboards.

### Target Users

**Primary (Cloud Platform):**

| User | Context | Primary Interface |
|------|---------|-------------------|
| **Wanjiku (Farmer)** | 800,000 smallholders, feature phones, 70% income from tea | SMS (160 chars, Swahili/Kikuyu/Luo) |
| **Joseph (Factory Quality Manager)** | Reviews dashboards, identifies problem farmers, manages 2 extension officers | Web Dashboard |
| **Factory Owner** | Makes subscription decisions, reviews ROI, needs competitive intelligence | Web Dashboard (reports) |
| **Regulator (Tea Board of Kenya)** | National quality trends, regional comparisons | Web Dashboard (analytics) |

**Out of Scope (QC Analyzer Hardware):**
- Peter (Collection Clerk) - Uses tagging device
- Grace (Factory QC Operator) - Uses QC Analyzer interface

### Key Design Challenges

1. **160-Character SMS Constraint** - The farmer's entire experience must fit in SMS. Every word must convey identity, result, reasoning, and actionable next step.

2. **Extreme Tech Diversity** - Same platform serves basic feature phones (SMS) and modern web dashboards. Design patterns must adapt gracefully.

3. **Low-Literacy Accessibility** - Stars (⭐⭐⭐⭐) instead of letter grades. Names instead of IDs. Photos at factory kiosks for visual confirmation.

4. **Action-Oriented Over Data-Heavy** - Dashboards must answer "what should I do?" not "here's data." One-click contact, clear categorization (Action Needed / Watch / Wins).

5. **Cultural & Language Authenticity** - Swahili messaging that feels human, not systematic. Celebration of progress. Trust through transparency.

6. **One-Way Communication Limitation** - Farmers receive but cannot respond via traditional SMS. Need mechanism for questions, disputes, or callbacks without building full chat support.

7. **Shared Device Reality** - Rural households often share phones. UX must handle multiple farmer identities per phone number gracefully.

### Design Opportunities

1. **Universal Star Rating System** - Communicates quality instantly across literacy levels. ⭐⭐⭐⭐⭐ is universally understood.

2. **Progress Celebration Engine** - Visible improvement tracking motivates behavior change. "Up from 3 stars last week!"

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

### Key Design Principle

> *"Boring technology that works"* - Every feature justified by clear action, minimal scope, measurable outcome.

### Phase Boundaries

| Phase | Scope |
|-------|-------|
| **Phase 1** | Core SMS experience, keyword responses (HELP/DISPUTE), basic dashboard with temporal patterns, lightweight delegation |
| **Phase 2** | WhatsApp enhancements, multi-profile selection, industry benchmarking, advanced analytics |

### Architectural Flags (For Architect Discussion)

 **Collection Point Data Gap** - Focus group revealed Joseph needs to identify quality patterns by collection point, not just individual farmers. Currently, the collection point is not captured in the data model. Consider:
1.  Adding Collection Point entity to Plantation Model, 
2. Updating QC Analyzer tagging to include collection_point_id. UX value: HIGH for factory quality managers. Requires cross-project coordination (QC Analyzer + Cloud Platform).

---

## Dashboard MVP - Priority Deliverable

### Strategic Rationale

**Why Now (Even with Mock Data):**

| Purpose | Value |
|---------|-------|
| **User Validation** | Test with Joseph: "Is this what you need to act?" before building the backend |
| **Investor Demo** | Tangible proof of concept beats slides - "This is real" |
| **Design Alignment** | Force decisions on layout, actions, information hierarchy early |
| **Development Spec** | Developers build TO the prototype, reducing ambiguity |

> *"Tangible beats theoretical"* - A clickable prototype with fake data validates more assumptions than months of requirements documents.

### MVP Screens to Prototype

#### Screen 1: Joseph's Daily Command Center (Homepage)

**Purpose:** Answer "What should I do today?" in 5 seconds

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  FARMER POWER         [Factory: Kericho Tea]     Joseph ▼      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔴 ACTION NEEDED (7)          🟡 WATCH (12)      🟢 WINS (23) │
│  ┌─────────────────────┐                                        │
│  │ Wanjiku M. ⭐⭐       │  ← Farmer card                        │
│  │ 3 consecutive drops │                                        │
│  │ [📞 Call] [👤 Assign]│  ← One-click actions                  │
│  └─────────────────────┘                                        │
│  ┌─────────────────────┐                                        │
│  │ DISPUTE REQUEST     │  ← From SMS keyword                    │
│  │ James K. - "Grade   │                                        │
│  │ wrong" - 2hrs ago   │                                        │
│  │ [📋 Review] [📞 Call]│                                        │
│  └─────────────────────┘                                        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  TODAY'S INTAKE                    QUALITY TREND (7 days)       │
│  ┌──────────────────┐              ┌──────────────────────┐     │
│  │ 847 bags graded  │              │    ████              │     │
│  │ ⭐⭐⭐⭐ avg (76)   │              │  ██████  ████        │     │
│  │ ▲ 3% vs yesterday│              │ ████████████████     │     │
│  └──────────────────┘              └──────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

**Key Interactions:**
- Click ACTION NEEDED / WATCH / WINS to filter farmer list
- Click farmer card → Farmer detail view
- Click [Assign] → Extension officer selection dropdown
- Click [Call] → Opens WhatsApp/phone with pre-filled message

**Mock Data Needed:**
- 50 sample farmers with names, grades, trends
- 5-10 dispute requests
- 7 days of quality scores

---

#### Screen 2: Farmer Detail View

**Purpose:** Everything Joseph needs to help ONE farmer

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back                    Wanjiku Muthoni (WM-4521)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CURRENT STATUS              CONTACT                            │
│  ⭐⭐ (52/100)                📱 +254 712 345 678                │
│  ▼ Down 23 points            📍 Kericho Region                  │
│  in 2 weeks                  [📞 Call] [💬 WhatsApp]            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  QUALITY HISTORY (30 days)                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ⭐⭐⭐⭐                                                    │  │
│  │ ⭐⭐⭐     ████                                            │  │
│  │ ⭐⭐           ████  ████                                  │  │
│  │ ⭐                       ████  ████                       │  │
│  │      Week 1  Week 2  Week 3  Week 4                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  RECENT ISSUES                 AI RECOMMENDATION                │
│  • High moisture (3x)          "Moisture pattern suggests       │
│  • Yellow leaves (2x)           drying time issue.              │
│  • Woody stems (1x)             Recommend: Extension visit      │
│                                 to check drying setup."         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  LAST SMS SENT                 ACTIONS                          │
│  "Mama Wanjiku, chai yako:     [👤 Assign to Extension Officer] │
│   ⭐⭐ (52). Unyevu mwingi.     [📝 Add Note]                    │
│   Anika zaidi = ⭐⭐⭐⭐!"        [📸 View Photos]                 │
│   — Sent 2hrs ago                                               │
└─────────────────────────────────────────────────────────────────┘
```

**Key Interactions:**
- Click quality history points → See that day's details + photos
- Click [Assign] → Dropdown with extension officers
- Click [View Photos] → Gallery of QC images for this farmer

---

#### Screen 3: Temporal Patterns View

**Purpose:** Surface systemic issues (day/time patterns)

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  QUALITY PATTERNS                          [This Week ▼]        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DAY OF WEEK HEATMAP                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │        Mon   Tue   Wed   Thu   Fri   Sat   Sun           │  │
│  │  Avg    78    81    79    68    75    82    80           │  │
│  │        🟢    🟢    🟢    🔴    🟡    🟢    🟢           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ⚠️ PATTERN DETECTED: Quality drops 14% on Thursdays            │
│     [Drill Down →]                                              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  DRILL DOWN: Thursday Quality                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Top Issues on Thursdays:                                 │  │
│  │  • High moisture: 45% of bags (vs 23% other days)         │  │
│  │  • Yellow leaves: 31% of bags (vs 18% other days)         │  │
│  │                                                           │  │
│  │  Affected Farmers: 127 (click to view list)               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Interactions:**
- Click day → See that day's detailed breakdown
- Click "Affected Farmers" → Filtered farmer list

---

#### Screen 4: SMS Preview Panel

**Purpose:** Show investors/users what farmers actually receive

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  SMS PREVIEW - What Farmers See                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────┐                       │
│  │  📱 Feature Phone Preview           │                       │
│  │  ┌─────────────────────────────┐    │                       │
│  │  │                             │    │                       │
│  │  │  NEW MESSAGE                │    │                       │
│  │  │  From: FARMER-POWER         │    │                       │
│  │  │                             │    │                       │
│  │  │  Mama Wanjiku, chai yako:   │    │                       │
│  │  │  ⭐⭐⭐⭐ (78)                │    │                       │
│  │  │  Pongezi! Juu kutoka 3      │    │                       │
│  │  │  wiki iliyopita!            │    │                       │
│  │  │  Endelea hivyo = ⭐⭐⭐⭐⭐!   │    │                       │
│  │  │                             │    │                       │
│  │  │  Reply HELP for assistance  │    │                       │
│  │  │                             │    │                       │
│  │  └─────────────────────────────┘    │                       │
│  │                                     │                       │
│  │  Characters: 142/160 ✓             │                       │
│  └─────────────────────────────────────┘                       │
│                                                                 │
│  MESSAGE VARIANTS:                                              │
│  [Grade Up ✓] [Grade Down] [First Delivery] [Dispute Response] │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Interactions:**
- Toggle between message variants to see different scenarios
- Shows character count (must stay under 160)

---

#### Screen 5: Regulator Dashboard (Tea Board of Kenya)

**Purpose:** National quality intelligence for policy and branding decisions

**Why This Screen Matters:**
- Regulatory endorsement = factory adoption accelerator
- Demonstrates platform value beyond individual factories
- Supports "Kenya Tea" national branding initiatives
- Shows investors the ecosystem play (not just B2B SaaS)

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  FARMER POWER - Tea Board of Kenya          [Q4 2025 ▼]  Admin │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  NATIONAL QUALITY OVERVIEW                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                                                          │  │
│  │   KENYA TEA QUALITY INDEX: 76.4  (▲ 4.2% vs last year)  │  │
│  │   ════════════════════════════════════════               │  │
│  │                                                          │  │
│  │   Factories Reporting: 47 / 100                          │  │
│  │   Farmers Covered: 423,000                               │  │
│  │   Quality Events This Quarter: 2.3M                      │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  REGIONAL COMPARISON                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                                                          │  │
│  │   Region          Avg Score    Trend      Factories     │  │
│  │   ─────────────────────────────────────────────────────  │  │
│  │   Kericho         81.2        ▲ +6%       12            │  │
│  │   Nandi           78.4        ▲ +3%       9             │  │
│  │   Nyeri           74.1        ━ 0%        8             │  │
│  │   Murang'a        71.8        ▼ -2%       7             │  │
│  │   Kisii           69.3        ▲ +8%       6             │  │
│  │   [View all 15 regions →]                                │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  GRADE DISTRIBUTION (National)         YEAR-OVER-YEAR          │
│  ┌────────────────────────┐            ┌────────────────────┐  │
│  │  ⭐⭐⭐⭐⭐ Grade A: 18%  │            │  2024  ████████    │  │
│  │  ⭐⭐⭐⭐  Grade B: 34%  │            │  2025  ██████████  │  │
│  │  ⭐⭐⭐   Grade C: 31%  │            │        ▲ 12% more  │  │
│  │  ⭐⭐    Grade D: 17%  │            │        Grade A+B   │  │
│  └────────────────────────┘            └────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  TOP QUALITY ISSUES (National)         SEASONAL PATTERNS        │
│  ┌────────────────────────┐            ┌────────────────────┐  │
│  │  1. Moisture: 34%      │            │  Peak harvest:     │  │
│  │  2. Leaf age: 28%      │            │  Mar-May quality   │  │
│  │  3. Handling: 19%      │            │  drops 8%          │  │
│  │  4. Disease: 12%       │            │  (capacity strain) │  │
│  │  5. Other: 7%          │            │                    │  │
│  └────────────────────────┘            └────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  EXPORT READINESS                                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Premium Export Grade (A+B): 52% of national production   │  │
│  │  Target for "Kenya Premium" certification: 60%            │  │
│  │  Gap to close: 8% (est. achievable in 18 months)         │  │
│  │                                                          │  │
│  │  [📊 Download Full Report]  [📈 Export to Ministry]      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Interactions:**
- Click region → Drill down to factory-level data (anonymized)
- Click grade distribution → See trend over time
- Click "Download Full Report" → PDF for ministry presentations
- Date range selector for historical comparison

**Value Proposition for Regulators:**
- **Policy Evidence:** Data-driven decisions on farmer support programs
- **National Branding:** "Kenya Tea Quality Index" for international marketing
- **Regional Targeting:** Identify regions needing extension officer investment
- **Export Strategy:** Track progress toward premium certification goals

**Mock Data Needed:**
- 15 regions with quality scores and trends
- National aggregates (factories, farmers, events)
- Grade distribution percentages
- Year-over-year comparison data

---

### Prototype Specifications

| Aspect | Recommendation |
|--------|----------------|
| **Tool** | Figma (clickable prototype) or HTML/Tailwind (functional mock) |
| **Fidelity** | Medium - real layout, placeholder visuals, clickable navigation |
| **Mock Data** | 50 farmers, 7 days history, realistic Kenyan names |
| **Languages** | English dashboard, Swahili SMS previews |
| **Responsive** | Desktop-first (Joseph uses laptop), tablet-friendly |

### Validation Plan

| Audience | What to Test | Success Criteria |
|----------|--------------|------------------|
| **Joseph (QC Manager)** | "Can you find the farmer who needs help most?" | Identifies ACTION NEEDED in <10 seconds |
| **Joseph** | "How would you assign this to your extension officer?" | Completes in <3 clicks |
| **Factory Owner** | "What's the ROI story here?" | Can articulate waste reduction value |
| **Regulator (Tea Board)** | "Which region needs the most support?" | Identifies lowest-performing region in <15 seconds |
| **Regulator** | "How does this help Kenya's tea export brand?" | Can explain Quality Index → Export Readiness story |
| **Investor** | "How does this help farmers?" | Understands the feedback loop from dashboard → SMS → farmer improvement |
| **Investor** | "What's the ecosystem play?" | Sees value across farmers → factories → regulators |

### Mock Data Requirements

```yaml
# Factory Manager Dashboard Data
farmers:
  count: 50
  fields:
    - name (Kenyan names, "Mama/Baba" prefix)
    - phone (+254...)
    - region
    - grade_history (30 days)
    - issues (moisture, leaves, stems)
    - trend (improving/declining/stable)

quality_events:
  count: 500 (10 per farmer average)
  fields:
    - date
    - grade (A/B/C/D with scores)
    - issues[]
    - farmer_id

disputes:
  count: 10
  fields:
    - farmer_id
    - message
    - timestamp
    - status (pending/resolved)

# Regulator Dashboard Data
regions:
  count: 15
  fields:
    - name (Kericho, Nandi, Nyeri, Murang'a, Kisii, etc.)
    - avg_score (65-85 range)
    - trend_percentage (-5% to +10%)
    - factory_count (5-15)
    - farmer_count (20,000-80,000)

national_aggregates:
  fields:
    - quality_index (76.4)
    - total_factories (100)
    - factories_reporting (47)
    - total_farmers (800,000)
    - farmers_covered (423,000)
    - quality_events_quarterly (2.3M)
    - grade_distribution:
        A: 18%
        B: 34%
        C: 31%
        D: 17%
    - export_readiness_percentage (52%)
    - export_target (60%)

year_over_year:
  fields:
    - previous_year_index (72.2)
    - current_year_index (76.4)
    - improvement_percentage (4.2%)
    - grade_ab_previous (46%)
    - grade_ab_current (52%)
```

---

## Voice IVR Experience Design

### Strategic Rationale

**The Accessibility Gap:**

SMS delivers quality scores and brief recommendations, but farmers with limited literacy or basic phones cannot access detailed explanations of how to improve. Voice IVR bridges this gap.

| Channel | Content Depth | Best For |
|---------|---------------|----------|
| **SMS** | 160 chars, brief summary | Quick notification, score delivery |
| **Voice IVR** | 2-3 minutes spoken | Detailed explanations, step-by-step guidance |
| **WhatsApp** | Rich media, unlimited | Farmers with smartphones |

**Target Users:**
- Farmers with basic feature phones (no smartphone required)
- Low-literacy farmers who prefer spoken instructions
- Farmers who want detailed action plan explanations beyond SMS summary

### SMS → Voice Handoff Design

Every SMS includes a voice IVR prompt for farmers who want more detail:

```
┌─────────────────────────────────────┐
│  📱 SMS Message                     │
│  ┌─────────────────────────────┐    │
│  │                             │    │
│  │  Mama Wanjiku, chai yako:   │    │
│  │  ⭐⭐⭐⭐ (78)                │    │
│  │  Unyevu mwingi.             │    │
│  │  Piga *384# kwa maelezo     │    │
│  │  zaidi.                     │    │
│  │                             │    │
│  └─────────────────────────────┘    │
│                                     │
│  Translation:                       │
│  "Mama Wanjiku, your tea:           │
│   ⭐⭐⭐⭐ (78). Too much moisture.   │
│   Call *384# for more details."    │
│                                     │
│  Characters: 98/160 ✓              │
└─────────────────────────────────────┘
```

**Key Design Principles:**
1. **SMS is complete on its own** - Farmer gets the score and key issue
2. **Voice is optional enrichment** - "Piga *384#" is an invitation, not required
3. **One shortcode to remember** - Same number (*384#) for all farmers

---

### IVR Call Flow Design

**Complete Flow Diagram:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VOICE IVR CALL FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STEP 1: FARMER DIALS *384#                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  System looks up farmer by caller ID                                   │  │
│  │  → Found: Proceed to Step 2                                           │  │
│  │  → Not Found: "Please enter your farmer ID followed by #"             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  STEP 2: GREETING (5 seconds)                                                │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔊 "Habari! Karibu Farmer Power."                                     │  │
│  │     "Hello! Welcome to Farmer Power."                                 │  │
│  │                                                                        │  │
│  │  🔊 "Bonyeza 1 kwa Kiswahili"                                          │  │
│  │     "Press 1 for Swahili"                                             │  │
│  │  🔊 "Bonyeza 2 kwa Gĩkũyũ"                                              │  │
│  │     "Press 2 for Kikuyu"                                              │  │
│  │  🔊 "Bonyeza 3 kwa Dholuo"                                              │  │
│  │     "Press 3 for Luo"                                                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  STEP 3: LANGUAGE SELECTION (User presses 1, 2, or 3)                        │
│  ┌──────┐  ┌──────┐  ┌──────┐                                               │
│  │  1   │  │  2   │  │  3   │                                               │
│  │ SW   │  │ KI   │  │ LUO  │                                               │
│  └──┬───┘  └──┬───┘  └──┬───┘                                               │
│     └─────────┴─────────┘                                                    │
│               │                                                              │
│               ▼                                                              │
│  STEP 4: PERSONALIZED GREETING (5 seconds)                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔊 [Swahili] "Jambo Mama Wanjiku!"                                    │  │
│  │     "Hello Mama Wanjiku!"                                             │  │
│  │                                                                        │  │
│  │  🔊 "Tuna mpango wako wa wiki hii."                                    │  │
│  │     "We have your action plan for this week."                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  STEP 5: QUALITY SUMMARY (15 seconds)                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔊 "Chai yako wiki hii imepata nyota nne kati ya tano."               │  │
│  │     "Your tea this week received 4 out of 5 stars."                   │  │
│  │                                                                        │  │
│  │  🔊 "Hii ni vizuri! Umepanda kutoka nyota tatu wiki iliyopita."        │  │
│  │     "This is good! You went up from 3 stars last week."               │  │
│  │                                                                        │  │
│  │  🔊 "Tatizo kuu: Unyevu mwingi katika majani yako."                   │  │
│  │     "Main issue: Too much moisture in your leaves."                   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  STEP 6: ACTION PLAN (60-90 seconds)                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔊 "Hivi ndivyo unavyoweza kuboresha:"                                │  │
│  │     "Here is how you can improve:"                                    │  │
│  │                                                                        │  │
│  │  🔊 "[Pause 0.5s] Moja: Anika majani kwa masaa mawili zaidi           │  │
│  │      kabla ya kupeleka kiwandani."                                    │  │
│  │     "One: Dry your leaves for two more hours before taking            │  │
│  │      them to the factory."                                            │  │
│  │                                                                        │  │
│  │  🔊 "[Pause 0.8s] Mbili: Usivune asubuhi na mapema sana               │  │
│  │      wakati bado kuna umande."                                        │  │
│  │     "Two: Don't harvest too early in the morning when there           │  │
│  │      is still dew."                                                   │  │
│  │                                                                        │  │
│  │  🔊 "[Pause 0.8s] Tatu: Tumia kapu lenye mashimo madogo               │  │
│  │      ili hewa iweze kupita."                                          │  │
│  │     "Three: Use a basket with small holes so air can pass             │  │
│  │      through."                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  STEP 7: CLOSING (10 seconds)                                                │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔊 "Ukifuata ushauri huu, chai yako itapata nyota tano!"              │  │
│  │     "If you follow this advice, your tea will get 5 stars!"           │  │
│  │                                                                        │  │
│  │  🔊 "Ukihitaji msaada, wasiliana na afisa wa kilimo wako."            │  │
│  │     "If you need help, contact your extension officer."              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  STEP 8: OPTIONS MENU (Repeats until hangup)                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔊 "Bonyeza 1 kusikiliza tena. Bonyeza 2 kwa msaada.                  │  │
│  │      Bonyeza 9 kumaliza."                                             │  │
│  │     "Press 1 to listen again. Press 2 for help. Press 9 to end."     │  │
│  │                                                                        │  │
│  │  ┌──────┐  ┌──────┐  ┌──────┐                                         │  │
│  │  │  1   │  │  2   │  │  9   │                                         │  │
│  │  │REPLAY│  │ HELP │  │ END  │                                         │  │
│  │  └──────┘  └──────┘  └──────┘                                         │  │
│  │     │          │          │                                            │  │
│  │     ▼          ▼          ▼                                            │  │
│  │  Go to      Transfer    "Asante!                                      │  │
│  │  Step 4     to human    Kwaheri."                                     │  │
│  │             (if avail)  (Goodbye)                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### Voice UX Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Speak Slowly** | TTS rate set to 0.9x (slightly slower than normal) |
| **Use Pauses** | 0.5s pause after greeting, 0.8s between action items |
| **Repeat Key Info** | Star rating and main issue mentioned twice |
| **Simple Language** | 6th-grade reading level equivalent |
| **Action-Oriented** | Each step starts with a verb: "Anika..." (Dry...), "Usivune..." (Don't harvest...) |
| **Encouraging Tone** | Celebrate progress: "Umepanda!" (You went up!) |
| **Limited Length** | Max 3 action items per call (cognitive load) |

---

### Multi-Language Voice Templates

**Quality Summary Template:**

| Language | Template |
|----------|----------|
| **Swahili** | "Chai yako wiki hii imepata nyota {STARS} kati ya tano. {TREND_MESSAGE}. Tatizo kuu: {MAIN_ISSUE}." |
| **Kikuyu** | "Mũtĩ waku wa wiki ĩno nĩũtũĩkĩire nyota {STARS} kũrĩ ithano. {TREND_MESSAGE}. Thĩna mũnene: {MAIN_ISSUE}." |
| **Luo** | "Yathi mari mar jumani oyudo sulwe {STARS} kuom abich. {TREND_MESSAGE}. Chandruok maduong: {MAIN_ISSUE}." |

**Trend Messages:**

| Trend | Swahili | English |
|-------|---------|---------|
| **Up** | "Pongezi! Umepanda kutoka nyota {PREV} wiki iliyopita!" | "Congrats! You went up from {PREV} stars last week!" |
| **Same** | "Hii ni sawa na wiki iliyopita." | "This is the same as last week." |
| **Down** | "Hii imeshuka kutoka nyota {PREV} wiki iliyopita. Usijali, tunaweza kuboresha!" | "This went down from {PREV} stars last week. Don't worry, we can improve!" |

---

### Voice Accessibility Features

| Feature | Design Decision |
|---------|-----------------|
| **No Smartphone Required** | Works on any phone that can dial *384# |
| **Language Selection First** | Farmer chooses their preferred language immediately |
| **Replay Option** | Press 1 to hear the entire message again (max 3 replays) |
| **Human Fallback** | Press 2 connects to extension officer (during working hours) |
| **Caller ID Lookup** | Automatic farmer identification - no need to enter ID |
| **Call Duration** | Max 5 minutes (cost control + attention span) |
| **Phone Quality Audio** | 8kHz sample rate optimized for phone speakers |

---

### Voice IVR Success Metrics

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| **Call Completion Rate** | >80% | Farmers listen to full message |
| **Replay Rate** | 20-40% | Some replay is healthy (absorbing info), too much = confusing |
| **Help Request Rate** | <10% | Most farmers understand without needing human support |
| **Caller ID Match Rate** | >95% | Seamless identification reduces friction |
| **Average Call Duration** | 2-3 min | Sweet spot for comprehension without fatigue |

---

### Dashboard Integration (Joseph's View)

Factory managers see Voice IVR engagement in farmer profiles:

```
┌─────────────────────────────────────────────────────────────────┐
│  FARMER DETAIL: Wanjiku Muthoni (WM-4521)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  COMMUNICATION HISTORY                                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Dec 18, 10:32 AM  📱 SMS sent (⭐⭐⭐⭐, moisture issue)      │ │
│  │  Dec 18, 10:45 AM  📞 Voice IVR called (2:34 duration)      │ │
│  │                        ↳ Language: Swahili                  │ │
│  │                        ↳ Replayed: Yes (1x)                 │ │
│  │                        ↳ Help requested: No                 │ │
│  │  Dec 11, 09:15 AM  📱 SMS sent (⭐⭐⭐, leaf age issue)        │ │
│  │  Dec 11, 09:22 AM  📞 Voice IVR called (1:58 duration)      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ENGAGEMENT INSIGHTS                                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  📊 This farmer regularly uses Voice IVR (4/4 weeks)        │ │
│  │  💡 Prefers Swahili, listens to full messages               │ │
│  │  ✓  Good engagement = likely following recommendations      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### Voice UX Validation Plan

| Test | Method | Success Criteria |
|------|--------|------------------|
| **Comprehension** | Play voice message to 10 farmers, ask what actions they should take | 8/10 correctly identify main actions |
| **Language Quality** | Native speaker review of TTS output | "Natural-sounding, not robotic" |
| **Call Flow** | User testing with feature phones | Complete call without confusion |
| **Accessibility** | Test with farmers who can't read SMS | Can take action based on voice alone |

---

<!-- Additional UX design sections will be appended through subsequent workflow steps -->