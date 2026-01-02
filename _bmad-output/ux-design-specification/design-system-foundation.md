# Design System Foundation

## Design System Choice

**Material UI v6 + Design Token System:**
- **Web Dashboards:** React 18 + Material UI v6 (MUI)
- **SMS/Voice:** Design Token System with standardized templates

> **Note:** This document has been updated to align with [ADR-002 Frontend Architecture](../architecture/adr/ADR-002-frontend-architecture.md), which is the authoritative source for technology decisions.

## Rationale for Selection

| Factor | Decision Driver |
|--------|-----------------|
| **Enterprise Ready** | MUI v6 provides production-grade components with TypeScript support |
| **Accessibility** | MUI components have ARIA built-in, WCAG 2.1 AA compliant |
| **Performance** | Tree-shaking support, optimized bundle sizes |
| **Multi-Channel** | Token system ensures consistency from SMS to web dashboards |
| **Data Grids** | MUI X DataGrid for complex farmer lists and grading tables |
| **Theming** | Comprehensive theme system with design token support |

## Implementation Approach

**Layer 1: Design Tokens (Shared Foundation)**

| Token | MUI Theme Key | Value | Usage |
|-------|---------------|-------|-------|
| Forest Green | `palette.primary.main` | #1B4332 | Brand, headers, CTAs |
| Earth Brown | `palette.secondary.main` | #5C4033 | Secondary actions |
| Harvest Gold | `palette.warning.main` | #D4A03A | WATCH status, warnings |
| Warm Red | `palette.error.main` | #C1292E | ACTION status, errors |
| Warm White | `palette.background.default` | #FFFDF9 | Page backgrounds |
| Spacing Unit | `spacing(1)` | 4px | Base spacing multiplier |
| Border Radius | `shape.borderRadius` | 6px | Subtle rounding for cards |

**Layer 2: Web Components (Admin Dashboards)**
- MUI DataGrid (MUI X) for grading results and farmer lists
- MUI Card for dashboard widgets and farmer cards
- MUI TextField, Select, Button for forms
- Custom StatusBadge component (see 6-component-strategy.md)
- MUI X Charts for analytics visualization

**Layer 3: SMS Templates**
```
DAILY:  [STATUS] Primary: XX% | Secondary: XX% | Kgs: XX
WEEKLY: 📊 Week Summary: [GRADE] Avg XX% Primary
ALERT:  ⚠️ ACTION NEEDED: [Issue]. Reply HELP for tips.
```

**Layer 4: Voice UX Patterns**
- Numbered menu structure (Press 1, 2, 3...)
- Confirmation before actions ("Press 1 to confirm")
- Clear separators between information chunks

## Customization Strategy

**Brand Colors (Earth & Growth Palette):**

| Purpose      | Name          | Hex       | Usage                                    |
|--------------|---------------|-----------|------------------------------------------|
| Primary      | Forest Green  | #1B4332   | Headers, CTAs, WIN status, brand         |
| Secondary    | Earth Brown   | #5C4033   | Secondary actions, supporting elements   |
| Warning      | Harvest Gold  | #D4A03A   | WATCH status, warnings                   |
| Error        | Warm Red      | #C1292E   | ACTION NEEDED status, errors             |
| Background   | Warm White    | #FFFDF9   | Page backgrounds                         |
| Neutral      | Slate Gray    | #64748B   | Secondary text, borders                  |

**Status Colors (TBK Categories):**

| Status | Background | Text/Icon | Usage |
|--------|------------|-----------|-------|
| WIN | #D8F3DC | #1B4332 | ≥85% Primary |
| WATCH | #FFF8E7 | #D4A03A | 70-84% Primary |
| ACTION NEEDED | #FFE5E5 | #C1292E | <70% Primary |

**Typography:**
- **Web:** Inter font family (clean, professional)
- **SMS:** Plain text, standardized abbreviations
- **Data:** Tabular figures for numbers (Inter supports this)

**Responsive Strategy:**
- Mobile-first for Farmer Registration UI
- Desktop-optimized for Factory/Platform Admin dashboards
- SMS: 160 character constraint respected

**Reference:** For detailed component specifications, see [6-component-strategy.md](./6-component-strategy.md).

---
