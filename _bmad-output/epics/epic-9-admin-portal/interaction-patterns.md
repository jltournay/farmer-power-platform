# Interaction Patterns

## 1. Inline Editing Pattern

All detail screens support inline editing:
- **View Mode:** Read-only display with [Edit] button
- **Edit Mode:** Fields become editable, [Save] [Cancel] buttons appear
- **Validation:** Real-time validation with error messages
- **Auto-save:** Optional draft saving for complex forms

## 2. Navigation Patterns

**Top-level screens (Regions, Farmers):**
```
🌍 Regions › Nyeri Highland
👨‍🌾 Farmers › Wanjiku Muthoni (WM-0041)
```

**Hierarchical screens (Factories → CPs):**
```
🏭 Factories › Nyeri Tea Factory › Nyeri Central CP
```

Cross-linking: [View Farmers →] on Region/CP opens Farmers list pre-filtered.

## 3. List-to-Detail Pattern

All lists follow consistent pattern:
- Search bar (top)
- Filters (below search)
- Data table/cards (main area)
- Pagination (bottom)
- Click row → navigate to detail

## 4. Create Flow Pattern

All create actions:
- [+ Add {Entity}] button in list or parent detail
- Modal or full-page form
- Required fields marked with *
- [Create] [Cancel] actions
- Success → redirect to new entity detail

## 5. Status Indicator Pattern

Consistent status display:
- ● Active (green)
- ○ Inactive (gray)
- ◐ Seasonal (yellow) - for Collection Points only

## 6. Performance Indicator Pattern

Quality percentages use tier colors:
- 🟢 ≥85% (Premium)
- 🟡 ≥70% (Standard)
- 🟠 ≥50% (Acceptable)
- 🔴 <50% (Below Standard)
