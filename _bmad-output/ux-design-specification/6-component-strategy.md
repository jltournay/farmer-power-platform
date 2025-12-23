# 6. Component Strategy

## 6.1 Design System Coverage Analysis

**Material UI v6 Components Available:**

| MUI Component | Usage in Farmer Power |
|---------------|----------------------|
| `Card` / `Paper` | Container for farmer cards, stats panels |
| `Grid` / `Stack` | Action strip layout, responsive grids |
| `DataGrid` (MUI X) | Farmer lists, grading history tables |
| `Chip` | Status badges (WIN/WATCH/ACTION) |
| `IconButton` / `Button` | Call, Assign, Message actions |
| `AppBar` / `Toolbar` | Top navigation, factory context |
| `Typography` | Headings, Primary %, farmer names |
| `Avatar` | Farmer initials display |
| `LinearProgress` | Progress indicators, factory targets |
| `Charts` (MUI X) | Trend lines, Primary % history |
| `Dialog` / `Modal` | Assignment dialogs, confirmations |
| `TextField` / `Select` | Forms, search, filters |
| `Tabs` | Dashboard sections, farmer detail views |
| `Tooltip` | Leaf type explanations, coaching tips |
| `Badge` | Notification counts |
| `Alert` / `Snackbar` | System messages, confirmations |

**Gap Analysis:**

| Need | MUI Coverage | Custom Required? |
|------|--------------|------------------|
| Action Strip | `Grid` + `Card` composition | **Partial** - need semantic styling |
| Farmer Card | `Card` + `ListItem` | **Partial** - need status integration |
| Status Badge | `Chip` | **Yes** - need WIN/WATCH/ACTION variants |
| Trend Indicator | None | **Yes** - custom with icon + text |
| Leaf Type Tag | `Chip` | **Partial** - need coaching tooltips |
| SMS Preview | None | **Yes** - phone mockup component |
| IVR Flow | None | **Yes** - flowchart-style display |
| Coaching Card | `Card` | **Partial** - need visual template |
| ROI Metric | `Card` | **Partial** - need hero layout |

---

## 6.2 Custom Component Specifications

### StatusBadge

**Purpose:** Display farmer quality category with instant visual recognition

**Anatomy:**
```
┌─────────────────┐
│ [Icon] LABEL    │
└─────────────────┘
```

**Variants:**

| Variant | Icon | Background | Text Color |
|---------|------|------------|------------|
| `win` | ✅ | `#D8F3DC` | Forest Green (`#1B4332`) |
| `watch` | ⚠️ | `#FFF8E7` | Harvest Gold (`#D4A03A`) |
| `action` | 🔴 | `#FFE5E5` | Warm Red (`#C1292E`) |

**States:** default, hover (slight elevation), clickable (cursor pointer)

**Props:**
```typescript
interface StatusBadgeProps {
  status: 'win' | 'watch' | 'action';
  label?: string; // Override default "WIN", "WATCH", "ACTION NEEDED"
  count?: number; // For action strip counts
  onClick?: () => void;
  size?: 'small' | 'medium' | 'large';
}
```

**Accessibility:** `role="status"`, `aria-label="Quality status: [status]"`

---

### TrendIndicator

**Purpose:** Show quality trajectory at a glance

**Anatomy:**
```
↑ +12%   ↓ -5%   → 0%
```

**Variants:**

| Trend | Icon | Color |
|-------|------|-------|
| `up` | ↑ / ArrowUpward | Forest Green (`#1B4332`) |
| `down` | ↓ / ArrowDownward | Warm Red (`#C1292E`) |
| `stable` | → / TrendingFlat | Slate Gray (`#64748B`) |

**Props:**
```typescript
interface TrendIndicatorProps {
  direction: 'up' | 'down' | 'stable';
  value: number; // Percentage change
  period?: string; // "vs last week", "since launch"
  size?: 'small' | 'medium';
}
```

---

### FarmerCard

**Purpose:** Single farmer overview with quick actions

**Anatomy:**
```
┌─────────────────────────────────────────┐
│ [Avatar] Mama Wanjiku          🟢 87%   │
│          WM-4521               ↑ +12%   │
│                                         │
│ [LeafTag: 3+ leaves]                    │
│                                         │
│ [📞 Call]  [👤 Assign]  [💬 Message]   │
└─────────────────────────────────────────┘
```

**States:**
- Default
- Hover (elevation, highlight)
- Selected (border accent)
- Has Assignment (officer badge visible)

**Props:**
```typescript
interface FarmerCardProps {
  farmer: {
    id: string;
    name: string;
    preferredName: string;
    primaryPct: number;
    trend: { direction: 'up' | 'down' | 'stable'; value: number };
    topIssue?: LeafType;
    assignedOfficer?: string;
  };
  onCall: () => void;
  onAssign: () => void;
  onMessage: () => void;
  onClick: () => void;
  compact?: boolean; // For list view
}
```

---

### LeafTypeTag

**Purpose:** Display leaf type issue with coaching tooltip

**Anatomy:**
```
┌────────────────┐
│ 🌿 3+ leaves   │ → Hover: "Pick only 2 leaves + bud"
└────────────────┘
```

**Variants:** One per TBK leaf type causing Secondary grade

| Leaf Type | Label (Swahili) | Label (English) |
|-----------|-----------------|-----------------|
| `three_plus_leaves_bud` | majani 3+ | 3+ leaves |
| `coarse_leaf` | majani magumu | coarse leaf |
| `hard_banji` | banji ngumu | hard banji |

**Props:**
```typescript
interface LeafTypeTagProps {
  leafType: 'three_plus_leaves_bud' | 'coarse_leaf' | 'hard_banji';
  language?: 'en' | 'sw';
  showTooltip?: boolean;
  onClick?: () => void; // Opens coaching card
}
```

**Accessibility:** Tooltip accessible via focus, not just hover

---

### ActionStrip

**Purpose:** Dashboard header showing category counts

**Anatomy:**
```
┌────────────────┬────────────────┬────────────────┐
│  🔴 ACTION     │  ⚠️ WATCH      │  ✅ WINS       │
│     NEEDED     │                │                │
│                │                │                │
│      7         │      23        │      145       │
│   <70%         │   70-84%       │    ≥85%        │
└────────────────┴────────────────┴────────────────┘
```

**Props:**
```typescript
interface ActionStripProps {
  counts: {
    action: number;
    watch: number;
    win: number;
  };
  selected?: 'action' | 'watch' | 'win' | null;
  onSelect: (category: 'action' | 'watch' | 'win') => void;
}
```

---

### SMSPreview

**Purpose:** Show farmers what they receive (for demos, template editing)

**Anatomy:**
```
┌─────────────────────────────┐
│  ┌───────────────────────┐  │
│  │ NEW MESSAGE           │  │
│  │ From: FARMER-POWER    │  │
│  │                       │  │
│  │ Mama Wanjiku, chai    │  │
│  │ yako: ✅ 82%...       │  │
│  │                       │  │
│  └───────────────────────┘  │
│                             │
│  Characters: 138/160 ✓     │
└─────────────────────────────┘
```

**Props:**
```typescript
interface SMSPreviewProps {
  message: string;
  senderName?: string;
  variant?: 'win' | 'watch' | 'action' | 'first_delivery';
  showCharCount?: boolean;
  maxChars?: number;
}
```

---

### ROIMetricCard

**Purpose:** Hero metric display for factory owners

**Anatomy:**
```
┌──────────────────────────────────────┐
│  YOUR RESULTS SINCE DEPLOYMENT       │
│                                      │
│        78%              +18%         │
│     Premium        since launch      │
│  ████████████████                    │
│                                      │
│  Est. waste reduction: $4,200/mo     │
│                                      │
│           [View Details →]           │
└──────────────────────────────────────┘
```

**Props:**
```typescript
interface ROIMetricCardProps {
  primaryMetric: { value: number; label: string; unit?: string };
  comparison: { value: number; label: string; direction: 'up' | 'down' };
  secondaryMetric?: { value: string; label: string };
  onViewDetails?: () => void;
}
```

---

## 6.3 Component Implementation Strategy

**Foundation Layer (MUI v6 Direct Use):**
- `ThemeProvider` with Earth & Growth palette
- `CssBaseline` for consistent styling
- `Grid`, `Stack`, `Box` for layout
- `Typography` for text hierarchy
- `AppBar`, `Toolbar` for navigation
- `DataGrid` for tabular data
- `Dialog`, `Modal` for overlays
- `TextField`, `Select`, `Button` for forms

**Composition Layer (MUI + Custom Styling):**
- `Card` → FarmerCard wrapper
- `Chip` → StatusBadge, LeafTypeTag
- `LinearProgress` → Factory progress toward target
- `Charts` → Primary % trend lines

**Custom Layer (New Components):**
- ActionStrip
- TrendIndicator
- SMSPreview
- ROIMetricCard
- CoachingCard (visual instruction panel)
- IVRFlowDisplay (voice menu visualization)

**MUI Theme Configuration:**
```typescript
const farmerPowerTheme = createTheme({
  palette: {
    primary: { main: '#1B4332' },      // Forest Green
    secondary: { main: '#5C4033' },    // Earth Brown
    warning: { main: '#D4A03A' },      // Harvest Gold
    error: { main: '#C1292E' },        // Warm Red
    background: { default: '#FFFDF9' } // Warm White
  },
  typography: {
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  shape: {
    borderRadius: 6
  }
});
```

---

## 6.4 Implementation Roadmap

**Phase 1 - Core Dashboard (MVP):**

| Component | Priority | Needed For |
|-----------|----------|------------|
| StatusBadge | P0 | All farmer displays |
| TrendIndicator | P0 | Farmer cards, ROI |
| ActionStrip | P0 | Joseph's homepage |
| FarmerCard | P0 | Farmer list views |
| LeafTypeTag | P0 | Issue identification |

**Phase 2 - Factory Management:**

| Component | Priority | Needed For |
|-----------|----------|------------|
| ROIMetricCard | P1 | Owner dashboard |
| SMSPreview | P1 | Template editing, demos |
| CoachingCard | P1 | Farmer detail view |

**Phase 3 - Advanced Features:**

| Component | Priority | Needed For |
|-----------|----------|------------|
| IVRFlowDisplay | P2 | Voice system admin |
| CollectionPointMap | P2 | Pattern analysis |
| BenchmarkChart | P2 | Competitive context |

---

## 6.5 Component Summary

| Category | Count | Approach |
|----------|-------|----------|
| **MUI Direct** | 15+ | Use as-is with theme tokens |
| **MUI Composed** | 5 | Wrap with custom props/styling |
| **Custom Built** | 7 | Build using MUI primitives + tokens |

**Design Tokens Used Across All:**
- Colors: Forest Green, Earth Brown, Harvest Gold, Warm Red
- Typography: Inter, tabular figures for numbers
- Spacing: 4px base unit
- Border radius: 6px (cards), 16px (badges)
- Shadows: MUI elevation scale

---
