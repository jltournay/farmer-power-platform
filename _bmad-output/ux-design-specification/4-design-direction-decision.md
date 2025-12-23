# 4. Design Direction Decision

## Selected Direction: Command Center (Direction 1)

**Decision Date:** 2025-12-23
**Decision Maker:** Jeanlouistournay

## Direction Overview

The Command Center design direction was selected as the primary visual and interaction approach for Farmer Power Platform's web dashboards. This action-first layout is optimized to answer Joseph's core question: **"What should I do today?"** in 5 seconds or less.

## Key Characteristics

| Aspect | Implementation |
|--------|----------------|
| **Layout Philosophy** | Action-first, not data-first |
| **Primary Visual Element** | Prominent WIN/WATCH/ACTION status cards |
| **Information Hierarchy** | Status counts → Priority farmers → Contextual metrics |
| **Interaction Pattern** | One-click actions (Call, Assign) directly on farmer cards |
| **Navigation** | Horizontal top bar with clear factory context |

## Why Command Center

**Alignment with User Needs:**

1. **Joseph (Quality Manager):**
   - Answers "What should I do today?" immediately
   - 7 ACTION NEEDED farmers visible at first glance
   - One-click Call/Assign buttons reduce friction
   - Works on tablet in bright sunlight conditions

2. **Factory Owner:**
   - Clear status overview (counts per category)
   - ROI proof visible in trend charts
   - Professional, trustworthy aesthetic

3. **TBK Grading Model:**
   - WIN/WATCH/ACTION categories map directly to Primary % thresholds
   - Leaf type issues displayed as issue tags
   - Progress tracking visible in trend visualization

## Design Direction Mockup Reference

Interactive mockups available at: `_bmad-output/ux-design-directions.html`

**Direction 1 Key Elements:**
- Forest green header with harvest gold logo accent
- Three-column action strip (ACTION NEEDED / WATCH / WINS)
- Priority farmer list with inline actions
- Stats panel with trend charts
- Issue tags showing top leaf type problems

## Alternatives Considered

| Direction | Why Not Selected |
|-----------|------------------|
| **2. Analytics Dashboard** | Too data-heavy for daily operations; better for monthly reviews |
| **3. Mobile-First Cards** | Good for field use, but Joseph primarily uses desktop |
| **4. Dense Professional** | High density overwhelming for quick daily decisions |
| **5. Split View** | Good for deep dives, but adds clicks to common actions |
| **6. Kanban Workflow** | Gamification doesn't match "boring technology that works" principle |

## Implementation Notes

**Components to Build:**
1. Action Strip (3-column status cards with counts)
2. Priority Farmer Card (name, Primary %, issue tag, action buttons)
3. Stats Panel (Today's Intake, Factory Average, Trend Chart)
4. Top Navigation Bar (logo, nav items, user/factory context)

**Color Application:**
- Forest Green (`#1B4332`) for header, primary buttons
- Harvest Gold (`#D4A03A`) for logo accent, WATCH badges
- Warm Red (`#C1292E`) for ACTION NEEDED badges
- Light backgrounds for cards and content areas

---
