# Design System Foundation

## Design System Choice

**Hybrid Themeable System:**
- **Web Dashboards:** Tailwind CSS + shadcn/ui (Radix primitives)
- **SMS/Voice:** Design Token System with standardized templates

## Rationale for Selection

| Factor | Decision Driver |
|--------|-----------------|
| **Speed** | Startup MVP requires rapid development - shadcn/ui provides copy-paste components |
| **Performance** | African network conditions need lightweight assets - Tailwind purges unused CSS |
| **Accessibility** | Radix primitives have ARIA built-in for admin interfaces |
| **Multi-Channel** | Token system ensures consistency from SMS to web dashboards |
| **Brand Flexibility** | Tailwind's utility classes allow full brand customization |
| **Team Efficiency** | No complex component library to learn - just HTML + classes |

## Implementation Approach

**Layer 1: Design Tokens (Shared Foundation)**

| Token | Value | Usage |
|-------|-------|-------|
| `--color-win` | #22C55E | Primary ≥85%, success states |
| `--color-watch` | #F59E0B | Primary 70-84%, warnings |
| `--color-action` | #EF4444 | Primary <70%, errors, alerts |
| `--color-primary` | #16A34A | Brand, agriculture theme |
| `--spacing-unit` | 4px | Base spacing multiplier |
| `--radius-default` | 6px | Subtle rounding for cards |

**Layer 2: Web Components (Admin Dashboards)**
- shadcn/ui DataTable for grading results and farmer lists
- shadcn/ui Cards for dashboard widgets
- shadcn/ui Forms for registration and settings
- Custom traffic light Badge component
- Recharts for analytics visualization

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

**Brand Colors:**

| Purpose    | Hex     | Usage                            |
|------------|---------|----------------------------------|
| Primary    | #16A34A | Headers, CTAs, agriculture theme |
| WIN        | #22C55E | Success badges, ≥85% Primary     |
| WATCH      | #F59E0B | Warning badges, 70-84% Primary   |
| ACTION     | #EF4444 | Error badges, <70% Primary       |
| Neutral    | #64748B | Secondary text, borders          |
| Background | #F8FAFC | Page backgrounds                 |

**Typography:**
- **Web:** Inter font family (clean, professional)
- **SMS:** Plain text, standardized abbreviations
- **Data:** Monospace for grading numbers

**Responsive Strategy:**
- Mobile-first for Farmer Registration UI
- Desktop-optimized for Factory/Platform Admin dashboards
- SMS: 160 character constraint respected

---
