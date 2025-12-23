# 3. Visual Design Foundation

## 3.1 Color System

**Theme: Earth & Growth**
A palette rooted in agricultural identity that conveys confidence through natural, grounded tones.

**Primary Colors:**
- **Deep Forest Green** (`#1B4332`) - Primary actions, success states, "WIN" indicators
- **Rich Earth Brown** (`#5C4033`) - Secondary elements, grounding, navigation
- **Harvest Gold** (`#D4A03A`) - Accents, highlights, premium indicators, "WATCH" states

**Semantic Colors:**
- **Success/WIN:** Forest Green (`#1B4332`) with light green background (`#D8F3DC`)
- **Warning/WATCH:** Harvest Gold (`#D4A03A`) with cream background (`#FFF8E7`)
- **Alert/ACTION NEEDED:** Warm Red (`#C1292E`) with light red background (`#FFE5E5`)
- **Neutral/Info:** Slate (`#4A5568`) with light gray background (`#F7FAFC`)

**Background Hierarchy:**
- Primary background: Warm white (`#FFFDF9`)
- Card/container background: Pure white (`#FFFFFF`)
- Section dividers: Light sage (`#E8F0E8`)

**Accessibility Compliance:**
- All text combinations meet WCAG 2.1 AA (4.5:1 contrast minimum)
- Critical UI elements meet AAA (7:1) for outdoor/bright light visibility
- Color-blind safe: Never rely on color alone—always pair with icons/text

## 3.2 Typography System

**Tone: Warm & Trustworthy**
Typography that feels approachable yet professional, optimized for mixed data and coaching content.

**Font Stack:**
- **Primary (Headings):** Inter or system sans-serif (clean, modern, excellent number legibility)
- **Secondary (Body):** Inter or system sans-serif (consistency, broad language support)
- **Data/Numbers:** Tabular figures enabled for alignment in tables and dashboards

**Type Scale (8px base unit):**

| Element | Size | Weight | Line Height | Use |
|---------|------|--------|-------------|-----|
| Display | 32px | 600 | 1.2 | Hero metrics, Primary % |
| H1 | 24px | 600 | 1.3 | Page titles |
| H2 | 20px | 600 | 1.3 | Section headers |
| H3 | 16px | 600 | 1.4 | Card titles, farmer names |
| Body | 16px | 400 | 1.5 | Coaching text, descriptions |
| Body Small | 14px | 400 | 1.5 | Secondary info, timestamps |
| Caption | 12px | 400 | 1.4 | Labels, hints |

**Readability Optimizations:**
- Minimum 16px for body text (critical for outdoor/mobile viewing)
- Maximum 65 characters per line for coaching content
- High contrast mode available for bright sunlight conditions

## 3.3 Spacing & Layout Foundation

**Approach: Balanced Density**
Maximize information value while maintaining visual breathing room.

**Spacing Scale (4px base):**
- `xs`: 4px - Tight grouping (label to value)
- `sm`: 8px - Related elements
- `md`: 16px - Standard component padding
- `lg`: 24px - Section separation
- `xl`: 32px - Major section breaks
- `2xl`: 48px - Page-level spacing

**Grid System:**
- **Mobile (< 640px):** Single column, full-width cards
- **Tablet (640-1024px):** 2-column grid for dashboards
- **Desktop (> 1024px):** 3-4 column grid with sidebar navigation

**Layout Principles:**
1. **Data proximity:** Related metrics grouped within 8px, contextual actions within 16px
2. **Scannable hierarchy:** WIN/WATCH/ACTION badges visible without scrolling
3. **Touch-friendly:** Minimum 44px touch targets for all interactive elements
4. **Thumb-zone aware:** Primary actions in bottom 60% of mobile screens

## 3.4 Accessibility Considerations

**Multi-Context Design:**
Given the diverse usage contexts (Joseph's tablet in bright sunlight, Wanjiku's basic phone, Factory owner's office), the visual system must adapt:

**Bright Sunlight (Field Use):**
- High contrast mode toggle (increases contrast to 10:1+)
- Larger touch targets (minimum 48px)
- Bold status indicators with icons + color + text
- Dark text on light backgrounds only (no light-on-dark in sunlight)

**Basic Phone Optimization:**
- Core functionality works without images loading
- Text-based fallbacks for all iconography
- Compressed color palette for low-color displays
- Single-column layouts that work on 320px screens

**Office/Desktop:**
- Full visual richness available
- Hover states and tooltips enhance discovery
- Keyboard navigation support
- Print-friendly views for reports

**Universal Accessibility:**
- Screen reader compatible (ARIA labels on all interactive elements)
- Focus indicators visible (3px green outline)
- No information conveyed by color alone
- Minimum 200% zoom support without horizontal scrolling

 ### 3.5 Component Library

**Implementation: Material UI v6 (MUI)**

The web dashboards will be built using Material UI v6 as the component library. This decision aligns with the Command Center design direction and provides:

| Benefit | Application |
|---------|-------------|
| **Consistent Components** | Pre-built Cards, Tables, Buttons match Command Center patterns |
| **Theming System** | Custom Earth & Growth palette via MUI theme provider |
| **Responsive Grid** | Built-in breakpoints for desktop/tablet/mobile |
| **Accessibility** | WCAG 2.1 AA compliance built into components |
| **Data Display** | DataGrid for farmer lists, Charts integration |

**Theme Configuration:**
- Primary: Forest Green (`#1B4332`)
- Secondary: Earth Brown (`#5C4033`)
- Warning: Harvest Gold (`#D4A03A`)
- Error: Warm Red (`#C1292E`)
- Background: Warm White (`#FFFDF9`)

**Key Component Mapping (Step 11 will expand):**
- Action Strip → MUI Card + Grid
- Farmer Card → MUI ListItem + IconButton
- Status Badges → MUI Chip with semantic colors
- Navigation → MUI AppBar + Toolbar

---
