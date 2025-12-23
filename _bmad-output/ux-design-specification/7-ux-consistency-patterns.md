# 7. UX Consistency Patterns

## 7.1 Button Hierarchy

**Primary Actions (Forest Green `#1B4332`):**

| Context | Button | Example |
|---------|--------|---------|
| **Dashboard** | Single CTA per card | "Assign Officer" |
| **Forms** | Submit/Save | "Register Farmer" |
| **Modals** | Confirm action | "Confirm Assignment" |

**Secondary Actions (Outlined, Forest Green border):**

| Context | Button | Example |
|---------|--------|---------|
| **Dashboard** | Alternative action | "View Details" |
| **Forms** | Cancel/Back | "Cancel" |
| **Cards** | Less prominent action | "Edit" |

**Tertiary Actions (Text only, no background):**

| Context | Button | Example |
|---------|--------|---------|
| **Navigation** | Breadcrumb links | "← Back to Dashboard" |
| **Inline** | Learn more | "Why this grade?" |
| **Tables** | Row actions | "View", "Export" |

**Icon Buttons (Quick Actions):**

| Icon | Action | Used In |
|------|--------|---------|
| 📞 | Call farmer | FarmerCard |
| 👤 | Assign officer | FarmerCard |
| 💬 | Send message | FarmerCard |
| ⬇️ | Download | Reports |
| 🔄 | Refresh | Dashboard |

**Button States:**
- **Default:** Solid fill / outlined
- **Hover:** Slight elevation (2px shadow)
- **Active:** Pressed state, darker shade
- **Disabled:** 50% opacity, no pointer
- **Loading:** Spinner replaces text, width maintained

---

## 7.2 Feedback Patterns

**Status Feedback (TBK Categories):**

| Status | Color | Icon | Background | Usage |
|--------|-------|------|------------|-------|
| **WIN** | `#1B4332` | ✅ | `#D8F3DC` | ≥85% Primary |
| **WATCH** | `#D4A03A` | ⚠️ | `#FFF8E7` | 70-84% Primary |
| **ACTION** | `#C1292E` | 🔴 | `#FFE5E5` | <70% Primary |

**System Feedback (Snackbar/Toast):**

| Type | Color | Icon | Duration | Example |
|------|-------|------|----------|---------|
| **Success** | Forest Green | ✓ | 4s auto-dismiss | "Farmer assigned successfully" |
| **Warning** | Harvest Gold | ⚠ | 6s, manual dismiss | "SMS quota at 80%" |
| **Error** | Warm Red | ✕ | Manual dismiss only | "Failed to send SMS. Retry?" |
| **Info** | Slate Blue | ℹ | 4s auto-dismiss | "3 new farmers registered today" |

**Position:** Bottom-left on desktop, bottom-center on mobile

**Progress Feedback:**

| Context | Pattern | Example |
|---------|---------|---------|
| **Page Load** | Skeleton screens | Dashboard cards shimmer |
| **Data Fetch** | Spinner in context | "Loading farmers..." |
| **Long Operation** | Progress bar with % | "Exporting report: 45%" |
| **Background** | Badge notification | "Report ready" badge on nav |

---

## 7.3 Form Patterns

**Input Field Anatomy:**

```
Label (required *)
┌─────────────────────────────────────┐
│  Placeholder text                    │
└─────────────────────────────────────┘
Helper text or error message
```

**Validation Timing:**

| Field Type | Validate On | Example |
|------------|-------------|---------|
| **Phone Number** | Blur + Format | Auto-format to +254 XXX XXX XXX |
| **Required Fields** | Blur | "Farmer name is required" |
| **Email** | Blur | "Enter a valid email address" |
| **Farmer ID** | Change (debounced) | Check uniqueness, show ✓ or ✕ |

**Error Display:**

| Pattern | When to Use |
|---------|-------------|
| **Inline below field** | Single field validation errors |
| **Summary at top** | Form-level errors on submit |
| **Shake animation** | Invalid input attempt |
| **Border color change** | `#C1292E` border on error |

**Form Layout:**

| Form Type | Layout | Example |
|-----------|--------|---------|
| **Simple (1-4 fields)** | Single column, full width | Quick assignment |
| **Standard (5-10 fields)** | Single column with sections | Farmer registration |
| **Complex (10+ fields)** | Multi-step wizard | Factory onboarding |

**Required Field Indication:** Red asterisk (*) after label

---

## 7.4 Navigation Patterns

**Top Navigation Bar (AppBar):**

```
┌─────────────────────────────────────────────────────────────────┐
│  [Logo] FARMER POWER    Dashboard | Farmers | Reports    [User]│
└─────────────────────────────────────────────────────────────────┘
```

| Element | Behavior |
|---------|----------|
| **Logo** | Click returns to Dashboard |
| **Nav Items** | Active state = underline + bold |
| **Factory Context** | Dropdown for multi-factory users |
| **User Menu** | Avatar → Settings, Logout |

**Breadcrumb Navigation:**

```
Dashboard > Farmers > Wanjiku Muthoni (WM-4521)
```

| Rule | Implementation |
|------|----------------|
| **Max depth** | 4 levels |
| **Truncation** | Middle items become "..." if >4 |
| **Current page** | Not clickable, bold |

**Drill-Down Pattern:**

| Level | View | Example |
|-------|------|---------|
| **1. List** | Summary cards | All farmers grid |
| **2. Detail** | Full record | Farmer profile |
| **3. Sub-detail** | Specific data | Single delivery history |

**Back Navigation:**
- Arrow icon (←) + "Back to [Parent]"
- Position: Top-left of content area
- Keyboard: ESC returns to parent (in modals)

---

## 7.5 Modal & Overlay Patterns

**Modal Sizes:**

| Size | Width | Use Case |
|------|-------|----------|
| **Small** | 400px | Confirmations, single field |
| **Medium** | 600px | Forms, previews |
| **Large** | 800px | Complex operations, tables |
| **Full** | 90% viewport | Photo gallery, reports |

**Modal Anatomy:**

```
┌─────────────────────────────────────┐
│  Title                        [✕]   │
├─────────────────────────────────────┤
│                                     │
│  Content area                       │
│                                     │
├─────────────────────────────────────┤
│           [Cancel]  [Confirm]       │
└─────────────────────────────────────┘
```

**Overlay Rules:**

| Rule | Implementation |
|------|----------------|
| **Backdrop** | Semi-transparent black (rgba 0,0,0,0.5) |
| **Close** | X button, ESC key, backdrop click |
| **Focus trap** | Tab cycles within modal |
| **Scroll** | Body scroll locked, modal scrolls if needed |

**Confirmation Dialogs:**

| Severity | Title Color | Confirm Button |
|----------|-------------|----------------|
| **Info** | Default | "Confirm" (Primary) |
| **Warning** | Harvest Gold | "Proceed" (Warning) |
| **Destructive** | Warm Red | "Delete" (Error color) |

---

## 7.6 Empty & Loading States

**Empty States:**

| Context | Message | Action |
|---------|---------|--------|
| **No farmers in category** | "No farmers need action today 🎉" | None (celebration) |
| **No search results** | "No farmers match '[query]'" | "Clear search" link |
| **First-time user** | "Start by adding your first farmer" | "Add Farmer" button |
| **No data yet** | "Waiting for first delivery data" | Info about timeline |

**Empty State Anatomy:**

```
┌─────────────────────────────────────┐
│                                     │
│         [Illustration/Icon]         │
│                                     │
│     Primary message (16px bold)     │
│  Secondary message (14px regular)   │
│                                     │
│         [Action Button]             │
│                                     │
└─────────────────────────────────────┘
```

**Loading States:**

| Context | Pattern | Duration Threshold |
|---------|---------|-------------------|
| **Initial page** | Skeleton screens | Immediate |
| **Data refresh** | Spinner in header | After 500ms |
| **Button action** | Inline spinner | After 200ms |
| **Long operation** | Progress bar + message | After 2s |

**Skeleton Screen Rules:**
- Match layout of actual content
- Subtle pulse animation
- Gray placeholder blocks
- No flickering on fast loads

---

## 7.7 Search & Filter Patterns

**Search Input:**

```
┌─────────────────────────────────────┐
│  🔍  Search farmers by name or ID   │
└─────────────────────────────────────┘
```

| Behavior | Implementation |
|----------|----------------|
| **Debounce** | 300ms before search executes |
| **Min chars** | 2 characters to trigger search |
| **Clear** | X button appears when text entered |
| **Results** | Dropdown with top 5 matches |

**Filter Chips:**

```
Active Filters: [🔴 ACTION NEEDED ✕] [Kericho Region ✕] [Clear All]
```

| Behavior | Implementation |
|----------|----------------|
| **Add filter** | Dropdown → Select → Chip appears |
| **Remove filter** | Click X on chip |
| **Clear all** | Single action removes all filters |
| **Persist** | Filters persist in URL params |

**Sort Controls:**

| Pattern | When to Use |
|---------|-------------|
| **Column header click** | Tables with sortable data |
| **Dropdown** | Card/grid layouts |
| **Toggle** | Ascending/descending switch |

---

## 7.8 Data Display Patterns

**Number Formatting:**

| Type | Format | Example |
|------|--------|---------|
| **Percentage** | No decimals for Primary % | "82%" |
| **Currency (KES)** | Thousands separator | "KES 4,200" |
| **Currency (USD)** | 2 decimals | "$4,200.00" |
| **Count** | Abbreviated if >1000 | "1.2K farmers" |
| **Trend** | Sign + value | "+12%" or "-5%" |

**Date & Time:**

| Context | Format | Example |
|---------|--------|---------|
| **Today** | "Today, 2:30 PM" | Recent activity |
| **This week** | "Mon, 2:30 PM" | Weekly view |
| **Older** | "Dec 18, 2025" | Historical data |
| **Relative** | "2 hours ago" | Timestamps |

**Table Patterns:**

| Feature | Implementation |
|---------|----------------|
| **Zebra striping** | Alternate row backgrounds |
| **Hover row** | Slight background highlight |
| **Sticky header** | Fixed during scroll |
| **Actions column** | Right-aligned, icon buttons |
| **Pagination** | Bottom, show range "1-25 of 127" |

---

## 7.9 Multi-Channel Consistency

**SMS Patterns (160 chars):**

```
[Name], chai yako:
[Status Emoji] [Primary %] daraja la kwanza
Tatizo: [Leaf Type Issue]
[Action Tip]
```

| Element | Rule |
|---------|------|
| **Name** | Always preferred name ("Mama Wanjiku") |
| **Status** | ✅ for WIN, ⚠️ for WATCH, 🔴 for ACTION |
| **Language** | Default Swahili, respects preference |
| **Character count** | Always shown during template editing |

**Voice IVR Patterns:**

| Element | Rule |
|---------|------|
| **Language first** | Always offer language selection |
| **Pauses** | 0.8s between options, 0.5s after greeting |
| **Key mapping** | 1=Repeat, 2=Help, 9=End (consistent) |
| **Confirmation** | "Press 1 to confirm" before actions |

**Dashboard ↔ SMS Alignment:**

| Dashboard Element | SMS Equivalent |
|-------------------|----------------|
| WIN badge | ✅ emoji |
| WATCH badge | ⚠️ emoji |
| ACTION badge | 🔴 emoji |
| Primary % | "XX% daraja la kwanza" |
| Leaf type tag | "Tatizo: [issue]" |
| Trend indicator | "Juu kutoka XX%" |

---

## 7.10 Accessibility Patterns

**Focus Management:**

| Pattern | Implementation |
|---------|----------------|
| **Focus ring** | 3px Forest Green outline |
| **Skip links** | "Skip to main content" on Tab |
| **Focus trap** | Modals, dropdowns trap focus |
| **Return focus** | After modal close, return to trigger |

**Keyboard Navigation:**

| Key | Action |
|-----|--------|
| **Tab** | Move to next focusable element |
| **Shift+Tab** | Move to previous element |
| **Enter/Space** | Activate button/link |
| **Escape** | Close modal/dropdown |
| **Arrow keys** | Navigate within menus |

**Screen Reader Patterns:**

| Element | ARIA Implementation |
|---------|---------------------|
| **Status badges** | `role="status" aria-label="Quality: WIN"` |
| **Charts** | `aria-describedby` with text summary |
| **Icons** | `aria-hidden="true"` if decorative |
| **Live regions** | `aria-live="polite"` for updates |

**Color Independence:**

| Pattern | Implementation |
|---------|----------------|
| **Status indicators** | Color + Icon + Text label |
| **Error states** | Red border + ✕ icon + error text |
| **Charts** | Patterns/shapes in addition to colors |
| **Links** | Underline in addition to color |

---

## 7.11 Error Recovery Patterns

**Error Hierarchy:**

| Level | Display | Recovery |
|-------|---------|----------|
| **Field error** | Inline below field | Fix and re-validate |
| **Form error** | Summary banner + inline | Fix highlighted fields |
| **API error** | Toast notification | Retry button |
| **System error** | Full-page message | Refresh or contact support |

**Error Messages:**

| Pattern | Example |
|---------|---------|
| **What happened** | "Unable to assign extension officer" |
| **Why** | "The officer is already at capacity (5 farmers)" |
| **What to do** | "Choose a different officer or wait until tomorrow" |

**Retry Patterns:**

| Context | Pattern |
|---------|---------|
| **API failure** | "Retry" button in toast |
| **Form submit** | Re-enable submit button |
| **Background sync** | Auto-retry with exponential backoff |
| **Offline** | Queue action, sync when online |

**Offline Patterns:**

| Feature | Behavior |
|---------|----------|
| **Indicator** | Yellow banner: "You're offline" |
| **Read access** | Cached data remains visible |
| **Write access** | Queue actions, show pending badge |
| **Sync** | Auto-sync when online, show notification |

---
