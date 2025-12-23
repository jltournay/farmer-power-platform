# 8. Responsive Design & Accessibility

## 8.1 Responsive Strategy

### Device Priority Matrix

| Device | Primary Users | Use Context | Priority |
|--------|---------------|-------------|----------|
| Desktop (1280px+) | Factory Managers, HQ Staff | Office-based monitoring | High |
| Tablet (768-1279px) | Field Officers on-site | Collection center visits | High |
| Mobile (320-767px) | Field Officers in transit | Quick checks, emergency actions | Critical |

### Desktop Strategy (Command Center Focus)
- **Multi-panel layouts**: Dashboard grid with 3-4 column layouts
- **Persistent side navigation**: Full navigation always visible
- **Data density optimization**: Display more farmers per view (15-20 rows)
- **Advanced features exposed**: Bulk actions, export controls, advanced filters
- **Hover interactions**: Tooltip previews, quick action menus

### Tablet Strategy (Touch-Optimized)
- **2-column responsive grid**: Farmers list + detail panel
- **Collapsible side navigation**: Hamburger menu to maximize content area
- **Touch targets**: Minimum 48x48px for all interactive elements
- **Swipe gestures**: Swipe to reveal quick actions on farmer cards
- **Landscape optimization**: Side-by-side comparison views

### Mobile Strategy (Field-First)
- **Single-column layouts**: One task at a time focus
- **Bottom navigation**: Thumb-friendly primary actions
- **Sticky action headers**: Call/SMS actions always accessible
- **Progressive disclosure**: Key metrics first, details on tap
- **Offline indicators**: Clear connectivity status badges

---

## 8.2 Breakpoint Strategy

### Mobile-First Breakpoints (MUI v6 Integration)

```typescript
const breakpoints = {
  values: {
    xs: 0,      // Mobile portrait
    sm: 600,    // Mobile landscape / Small tablet
    md: 900,    // Tablet
    lg: 1200,   // Desktop
    xl: 1536,   // Large desktop
  },
};
```

### Layout Transformations

**xs (0-599px) - Mobile Portrait:**
- Single column, stacked cards
- Bottom navigation bar
- Full-width action buttons
- Collapsed header with status summary

**sm (600-899px) - Mobile Landscape/Small Tablet:**
- Optional 2-column for lists
- Side-by-side action buttons
- Expanded metrics row

**md (900-1199px) - Tablet:**
- 2-column master-detail layout
- Persistent filter sidebar
- Grid card layouts

**lg (1200-1535px) - Desktop:**
- Full Command Center layout
- 3-column dashboard grid
- Advanced data tables

**xl (1536px+) - Large Desktop:**
- 4-column dashboard capability
- Side-by-side farmer comparison
- Extended analytics panels

---

## 8.3 Accessibility Strategy

### WCAG 2.1 AA Compliance (Target)

Farmer Power Platform targets **WCAG 2.1 Level AA** compliance:
- Industry-standard accessibility
- Legal compliance for government/NGO partnerships
- Inclusive design for diverse Field Officer capabilities

### Color Contrast Compliance

| Element | Foreground | Background | Ratio | Status |
|---------|------------|------------|-------|--------|
| Body text | #1A1A1A | #FFFDF9 | 14.5:1 | Pass AAA |
| Primary button | #FFFFFF | #1B4332 | 8.6:1 | Pass AAA |
| WIN badge | #FFFFFF | #1B4332 | 8.6:1 | Pass AAA |
| WATCH badge | #1A1A1A | #D4A03A | 5.2:1 | Pass AA |
| ACTION badge | #FFFFFF | #C1292E | 5.4:1 | Pass AA |
| Link text | #1B4332 | #FFFDF9 | 7.5:1 | Pass AAA |

### Keyboard Navigation Requirements

- **Tab order**: Logical flow through interactive elements
- **Focus indicators**: 3px Forest Green (#1B4332) outline
- **Skip links**: "Skip to main content" / "Skip to farmer list"
- **Escape handling**: Close modals and overlays
- **Arrow keys**: Navigate within tables and lists

### Screen Reader Support

```html
<!-- Farmer Card ARIA Structure -->
<article role="article" aria-labelledby="farmer-name-123">
  <h3 id="farmer-name-123">Peter Kimani</h3>
  <div role="status" aria-live="polite">
    Primary Score: 78% - Watch Status
  </div>
  <div role="group" aria-label="Quick actions">
    <button aria-label="Call Peter Kimani">Call</button>
    <button aria-label="Send SMS to Peter Kimani">SMS</button>
  </div>
</article>
```

### Touch Target Requirements

| Element Type | Minimum Size | Farmer Power Standard |
|-------------|--------------|----------------------|
| Buttons | 44x44px | 48x48px |
| List items | 44px height | 56px height |
| Icons (actionable) | 44x44px | 48x48px |
| Form inputs | 44px height | 48px height |

---

## 8.4 Kenya-Specific Considerations

### Low-Bandwidth Optimization
- **Lazy loading**: Images and charts load on scroll
- **Data caching**: Farmer lists cached for offline browsing
- **Compressed assets**: SVG icons, WebP images
- **Progressive enhancement**: Core functions work without JS-heavy features

### Multilingual Support
- **Swahili language option**: UI text localization ready
- **RTL consideration**: Structure supports future RTL languages
- **Number formatting**: Localized percentage and currency display

### Device Constraints
- **Older Android support**: Target Android 8.0+ (common in Kenya)
- **Limited storage**: Minimal local data footprint
- **Battery awareness**: Reduce background processes

---

## 8.5 Testing Strategy

### Responsive Testing Matrix

| Test Type | Tools | Frequency |
|-----------|-------|-----------|
| Browser DevTools | Chrome, Firefox, Safari | Every PR |
| Real device testing | Samsung A-series, iPhone SE | Sprint review |
| Network throttling | Chrome DevTools (3G/4G) | Key flows |
| Touch simulation | BrowserStack | Monthly |

### Accessibility Testing Matrix

| Test Type | Tools | Frequency |
|-----------|-------|-----------|
| Automated scanning | axe-core, Lighthouse | Every PR |
| Screen reader | VoiceOver (Mac), NVDA (Win) | Sprint review |
| Keyboard navigation | Manual testing | Every feature |
| Color contrast | Contrast checker plugins | Design review |
| Motion reduction | prefers-reduced-motion | Quarterly |

### Target Device Testing

**Primary Test Devices:**
- Samsung Galaxy A13 (popular Kenya mid-range)
- iPhone SE (compact iOS testing)
- iPad 9th gen (tablet baseline)
- Desktop Chrome (1920x1080)

**Network Testing Conditions:**
- 3G (750 Kbps) - Rural simulation
- 4G (10 Mbps) - Urban simulation
- Offline - Cached data validation

---

## 8.6 Implementation Guidelines

### Responsive CSS Patterns

```scss
// Mobile-first base styles
.farmer-card {
  display: flex;
  flex-direction: column;
  padding: 16px;

  // Tablet: Side-by-side layout
  @media (min-width: 900px) {
    flex-direction: row;
    align-items: center;
  }

  // Desktop: Compact with hover states
  @media (min-width: 1200px) {
    padding: 12px 16px;

    &:hover {
      .quick-actions { opacity: 1; }
    }
  }
}
```

### MUI v6 Responsive Components

```typescript
// Responsive Grid Configuration
<Grid container spacing={{ xs: 2, md: 3 }}>
  <Grid size={{ xs: 12, md: 6, lg: 4 }}>
    <FarmerCard />
  </Grid>
</Grid>

// Responsive Typography
<Typography
  variant="h1"
  sx={{ fontSize: { xs: '1.5rem', md: '2rem', lg: '2.5rem' } }}
>
  Command Center
</Typography>
```

### Accessibility Implementation

```typescript
// Focus Management Hook
const useFocusReturn = () => {
  const triggerRef = useRef<HTMLElement>(null);

  const returnFocus = useCallback(() => {
    triggerRef.current?.focus();
  }, []);

  return { triggerRef, returnFocus };
};

// Accessible Modal Pattern
<Dialog
  aria-labelledby="modal-title"
  aria-describedby="modal-description"
  onClose={handleClose}
  disablePortal={false}
>
  <DialogTitle id="modal-title">Edit Farmer</DialogTitle>
  <DialogContent id="modal-description">
    {/* Form content */}
  </DialogContent>
</Dialog>
```

### Reduced Motion Support

```scss
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 8.7 Progressive Enhancement Layers

| Layer | Features | Fallback |
|-------|----------|----------|
| Core HTML | Forms, navigation, content | Always available |
| CSS Enhancements | Grid layouts, animations | Graceful degradation |
| JavaScript | Filters, real-time updates | Server-side alternatives |
| PWA Features | Offline mode, push notifications | Standard web experience |

---

<!-- Additional UX design sections will be appended through subsequent workflow steps -->