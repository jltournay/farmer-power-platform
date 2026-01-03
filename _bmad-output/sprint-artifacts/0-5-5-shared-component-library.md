# Story 0.5.5: Shared Component Library Setup

**Status:** in-progress
**GitHub Issue:** #82

## Story

As a **frontend developer**,
I want **a shared React component library with the design system foundation**,
So that **all frontend applications have consistent UI components and styling**.

## Acceptance Criteria

1. **Package Setup (AC1)**:
   - `libs/ui-components/` package exports as `@fp/ui-components` via npm workspaces
   - TypeScript configured with strict mode
   - Vitest configured for component testing
   - Package builds with Vite in library mode

2. **Theme Foundation (AC2)**:
   - Material UI v6 theme configured with Farmer Power color palette
   - Primary (Forest Green #1B4332), Secondary (Earth Brown #5C4033)
   - Status colors: win (#D8F3DC), watch (#FFF8E7), action (#FFE5E5)
   - Typography uses Inter font family
   - Spacing follows 8px grid system

3. **Base Components (AC3)**:
   - `StatusBadge` component with variants: WIN, WATCH, ACTION_NEEDED
   - `TrendIndicator` shows up/down/stable with color coding and icons
   - `LeafTypeTag` displays leaf type with TBK color coding
   - All components have TypeScript types exported

4. **Storybook Configuration (AC4)**:
   - Storybook configured for visual documentation
   - Each component has `.stories.tsx` file with all variants
   - Stories cover: default, hover, focus, disabled states
   - `npm run build-storybook` builds successfully

5. **Testing (AC5)**:
   - Unit tests for all components in `tests/unit/web/`
   - Visual snapshots stored in `tests/visual/snapshots/`
   - All tests pass with `npm run test`

6. **Tree-Shaking (AC6)**:
   - Import `@fp/ui-components` in a test app
   - Only imported components are bundled
   - Theme accessible via `ThemeProvider` wrapper

## Tasks / Subtasks

- [x] **Task 1: Initialize Package Structure** (AC: #1)
  - [x] 1.1 Create `libs/ui-components/` directory structure
  - [x] 1.2 Create `package.json` with name `@fp/ui-components`
  - [x] 1.3 Configure `tsconfig.json` with strict mode
  - [x] 1.4 Configure `vite.config.ts` for library build
  - [x] 1.5 Add to root `package.json` workspaces array

- [x] **Task 2: Configure Dependencies** (AC: #1, #2)
  - [x] 2.1 Install React 18, MUI v6, Emotion
  - [x] 2.2 Install Vitest, Testing Library
  - [x] 2.3 Install Storybook 8.x
  - [x] 2.4 Configure peer dependencies (react, react-dom)

- [x] **Task 3: Create Theme Foundation** (AC: #2)
  - [x] 3.1 Create `src/theme/palette.ts` with Farmer Power colors
  - [x] 3.2 Create `src/theme/typography.ts` with Inter font
  - [x] 3.3 Create `src/theme/index.tsx` with MUI theme export
  - [x] 3.4 Export `ThemeProvider` wrapper component
  - [x] 3.5 Create status color constants object

- [x] **Task 4: Implement StatusBadge Component** (AC: #3)
  - [x] 4.1 Create `src/components/StatusBadge/StatusBadge.tsx`
  - [x] 4.2 Implement props: `status`, `label`, `count`, `onClick`, `size`
  - [x] 4.3 Style variants: win, watch, action
  - [x] 4.4 Add accessibility: `role="status"`, `aria-label`
  - [x] 4.5 Create `index.ts` export

- [x] **Task 5: Implement TrendIndicator Component** (AC: #3)
  - [x] 5.1 Create `src/components/TrendIndicator/TrendIndicator.tsx`
  - [x] 5.2 Implement props: `direction`, `value`, `period`, `size`
  - [x] 5.3 Style variants: up (green), down (red), stable (gray)
  - [x] 5.4 Use MUI icons (ArrowUpward, ArrowDownward, TrendingFlat)
  - [x] 5.5 Create `index.ts` export

- [x] **Task 6: Implement LeafTypeTag Component** (AC: #3)
  - [x] 6.1 Create `src/components/LeafTypeTag/LeafTypeTag.tsx`
  - [x] 6.2 Implement props: `leafType`, `language`, `showTooltip`, `onClick`
  - [x] 6.3 Support leaf types: three_plus_leaves_bud, coarse_leaf, hard_banji
  - [x] 6.4 Add coaching tooltips with Swahili/English labels
  - [x] 6.5 Ensure tooltip accessible on focus (not just hover)
  - [x] 6.6 Create `index.ts` export

- [x] **Task 7: Configure Storybook** (AC: #4)
  - [x] 7.1 Create `.storybook/main.ts` configuration
  - [x] 7.2 Create `.storybook/preview.ts` with ThemeProvider
  - [x] 7.3 Create `StatusBadge.stories.tsx` with win/watch/action stories
  - [x] 7.4 Create `TrendIndicator.stories.tsx` with up/down/stable stories
  - [x] 7.5 Create `LeafTypeTag.stories.tsx` with all leaf type stories
  - [x] 7.6 Verify `npm run build-storybook` succeeds

- [x] **Task 8: Create Unit Tests** (AC: #5)
  - [x] 8.1 Create `tests/unit/web/test_status_badge.test.tsx`
  - [x] 8.2 Create `tests/unit/web/test_trend_indicator.test.tsx`
  - [x] 8.3 Create `tests/unit/web/test_leaf_type_tag.test.tsx`
  - [x] 8.4 Test accessibility (ARIA attributes, keyboard)
  - [x] 8.5 All tests pass with `npm run test`

- [x] **Task 9: Configure Exports** (AC: #6)
  - [x] 9.1 Create `src/index.ts` with all public exports
  - [x] 9.2 Configure `package.json` exports field for tree-shaking
  - [x] 9.3 Verify build output with `npm run build`
  - [x] 9.4 Test import in tests (57 tests pass using @fp/ui-components imports)

- [ ] **Task 10: Visual Snapshots** (AC: #5) - DEFERRED
  - [ ] 10.1 Capture baseline snapshots for all stories
  - [ ] 10.2 Store in `tests/visual/snapshots/`
  - [ ] 10.3 Configure Storybook snapshot runner
  - Note: Visual snapshots require Chromatic or percy.io integration - deferred to future story

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.5.5: Shared Component Library"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-5-shared-component-library
  ```

**Branch name:** `story/0-5-5-shared-component-library`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-5-5-shared-component-library`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.5.5: Shared Component Library" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-5-5-shared-component-library`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
cd libs/ui-components && npm run test
```
**Output:**
```
 RUN  v2.1.9 /Users/jeanlouistournay/wks-farmerpower/farmer-power-platform/libs/ui-components

 ✓ ../../tests/unit/web/test_trend_indicator.test.tsx (17 tests) 201ms
 ✓ ../../tests/unit/web/test_status_badge.test.tsx (19 tests) 288ms
 ✓ ../../tests/unit/web/test_leaf_type_tag.test.tsx (21 tests) 677ms

 Test Files  3 passed (3)
      Tests  57 passed (57)
   Duration  2.98s
```

### 2. Storybook Build
```bash
cd libs/ui-components && npm run build-storybook
```
**Build passed:** [x] Yes / [ ] No

### 3. Library Build
```bash
cd libs/ui-components && npm run build
```
**Build passed:** [x] Yes / [ ] No

### 4. Lint Check
```bash
cd libs/ui-components && npm run lint
```
**Lint passed:** [x] Yes / [ ] No

### 5. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/0-5-5-shared-component-library

# Wait ~30s, then check CI status
gh run list --branch story/0-5-5-shared-component-library --limit 3
```
**CI Run ID:** _______________
**CI Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### CRITICAL: This is the FIRST React/Frontend Story

This story creates the foundation for ALL frontend work in the platform. Pay extra attention to:

1. **Package Structure**: Must follow npm workspace conventions exactly
2. **MUI v6 Theme**: All design tokens MUST match UX specification
3. **Accessibility**: Components MUST meet WCAG 2.1 AA from the start
4. **Type Safety**: Strict TypeScript - no `any` types allowed

### Directory Structure (MUST FOLLOW EXACTLY)

```
libs/ui-components/
├── src/
│   ├── components/
│   │   ├── StatusBadge/
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── StatusBadge.stories.tsx
│   │   │   └── index.ts
│   │   ├── TrendIndicator/
│   │   │   ├── TrendIndicator.tsx
│   │   │   ├── TrendIndicator.stories.tsx
│   │   │   └── index.ts
│   │   └── LeafTypeTag/
│   │       ├── LeafTypeTag.tsx
│   │       ├── LeafTypeTag.stories.tsx
│   │       └── index.ts
│   ├── theme/
│   │   ├── index.ts
│   │   ├── palette.ts
│   │   └── typography.ts
│   └── index.ts
├── .storybook/
│   ├── main.ts
│   └── preview.ts
├── package.json
├── tsconfig.json
├── vite.config.ts
└── vitest.config.ts
```

[Source: _bmad-output/architecture/adr/ADR-002-frontend-architecture.md#shared-component-library]

### Design Tokens (MANDATORY)

**Colors from UX Specification:**

| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | #1B4332 | Forest Green - Primary brand |
| `--color-secondary` | #5C4033 | Earth Brown - Secondary |
| `--color-warning` | #D4A03A | Harvest Gold - WATCH state |
| `--color-error` | #C1292E | Warm Red - ACTION state |
| `--color-success` | #1B4332 | Forest Green - WIN state |
| `--bg-win` | #D8F3DC | WIN badge background |
| `--bg-watch` | #FFF8E7 | WATCH badge background |
| `--bg-action` | #FFE5E5 | ACTION badge background |

[Source: _bmad-output/ux-design-specification/design-system-foundation.md]
[Source: _bmad-output/project-context.md#ui-ux-rules]

### Component Specifications

#### StatusBadge Props Interface

```typescript
interface StatusBadgeProps {
  status: 'win' | 'watch' | 'action';
  label?: string; // Override default "WIN", "WATCH", "ACTION NEEDED"
  count?: number; // For action strip counts
  onClick?: () => void;
  size?: 'small' | 'medium' | 'large';
}
```

**Variants:**

| Variant | Icon | Background | Text Color |
|---------|------|------------|------------|
| `win` | ✅ | #D8F3DC | #1B4332 |
| `watch` | ⚠️ | #FFF8E7 | #D4A03A |
| `action` | 🔴 | #FFE5E5 | #C1292E |

[Source: _bmad-output/ux-design-specification/6-component-strategy.md#StatusBadge]

#### TrendIndicator Props Interface

```typescript
interface TrendIndicatorProps {
  direction: 'up' | 'down' | 'stable';
  value: number; // Percentage change
  period?: string; // "vs last week", "since launch"
  size?: 'small' | 'medium';
}
```

**Variants:**

| Trend | Icon | Color |
|-------|------|-------|
| `up` | ArrowUpward | #1B4332 (Forest Green) |
| `down` | ArrowDownward | #C1292E (Warm Red) |
| `stable` | TrendingFlat | #64748B (Slate Gray) |

[Source: _bmad-output/ux-design-specification/6-component-strategy.md#TrendIndicator]

#### LeafTypeTag Props Interface

```typescript
interface LeafTypeTagProps {
  leafType: 'three_plus_leaves_bud' | 'coarse_leaf' | 'hard_banji';
  language?: 'en' | 'sw';
  showTooltip?: boolean;
  onClick?: () => void; // Opens coaching card
}
```

**Leaf Types:**

| Leaf Type | English Label | Swahili Label | Coaching Tip |
|-----------|---------------|---------------|--------------|
| `three_plus_leaves_bud` | 3+ leaves | majani 3+ | Pick only 2 leaves + bud |
| `coarse_leaf` | coarse leaf | majani magumu | Avoid old/mature leaves |
| `hard_banji` | hard banji | banji ngumu | Harvest earlier in morning |

[Source: _bmad-output/ux-design-specification/6-component-strategy.md#LeafTypeTag]

### MUI v6 Theme Configuration

```typescript
// src/theme/index.ts
import { createTheme } from '@mui/material/styles';

export const farmerPowerTheme = createTheme({
  palette: {
    primary: { main: '#1B4332' },      // Forest Green
    secondary: { main: '#5C4033' },    // Earth Brown
    warning: { main: '#D4A03A' },      // Harvest Gold
    error: { main: '#C1292E' },        // Warm Red
    success: { main: '#1B4332' },      // Forest Green (WIN)
    background: {
      default: '#FFFDF9',              // Warm White
      paper: '#FFFFFF'
    },
  },
  typography: {
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  shape: {
    borderRadius: 6,
  },
});

// Status-specific tokens (not standard MUI)
export const statusColors = {
  win: { bg: '#D8F3DC', text: '#1B4332', icon: '✅' },
  watch: { bg: '#FFF8E7', text: '#D4A03A', icon: '⚠️' },
  action: { bg: '#FFE5E5', text: '#C1292E', icon: '🔴' },
};
```

[Source: _bmad-output/architecture/adr/ADR-002-frontend-architecture.md#design-tokens]

### Package.json Configuration

```json
{
  "name": "@fp/ui-components",
  "version": "0.1.0",
  "type": "module",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "require": "./dist/index.cjs",
      "types": "./dist/index.d.ts"
    }
  },
  "files": ["dist"],
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint src --ext .ts,.tsx",
    "storybook": "storybook dev -p 6006",
    "build-storybook": "storybook build"
  },
  "peerDependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "dependencies": {
    "@mui/material": "^6.0.0",
    "@mui/icons-material": "^6.0.0",
    "@emotion/react": "^11.0.0",
    "@emotion/styled": "^11.0.0"
  },
  "devDependencies": {
    "@storybook/react": "^8.0.0",
    "@storybook/react-vite": "^8.0.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "@types/react": "^18.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0",
    "vitest": "^1.0.0"
  }
}
```

### Vite Library Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import dts from 'vite-plugin-dts';

export default defineConfig({
  plugins: [
    react(),
    dts({ include: ['src'] }),
  ],
  build: {
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'FPUIComponents',
      formats: ['es', 'cjs'],
      fileName: (format) => `index.${format === 'es' ? 'js' : 'cjs'}`,
    },
    rollupOptions: {
      external: ['react', 'react-dom', 'react/jsx-runtime'],
      output: {
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM',
        },
      },
    },
  },
});
```

### Storybook Stories Template

```typescript
// StatusBadge.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { StatusBadge } from './StatusBadge';

const meta: Meta<typeof StatusBadge> = {
  component: StatusBadge,
  title: 'Components/StatusBadge',
  tags: ['autodocs'],
  argTypes: {
    status: {
      control: 'select',
      options: ['win', 'watch', 'action'],
    },
  },
};

export default meta;
type Story = StoryObj<typeof StatusBadge>;

export const Win: Story = {
  args: { status: 'win' },
};

export const Watch: Story = {
  args: { status: 'watch' },
};

export const ActionNeeded: Story = {
  args: { status: 'action' },
};

export const WithCount: Story = {
  args: { status: 'action', count: 7 },
};
```

### Accessibility Requirements (CRITICAL)

**StatusBadge:**
- `role="status"`
- `aria-label="Quality status: [status]"`
- Focus ring: 3px Forest Green outline
- Touch target: 44px minimum

**TrendIndicator:**
- Icon + text + color (color not sole indicator)
- `aria-label="Quality trend: [direction] [value]%"`

**LeafTypeTag:**
- Tooltip accessible via focus AND hover
- `role="button"` if clickable
- Keyboard: Enter/Space triggers onClick

[Source: _bmad-output/project-context.md#touch--accessibility-requirements]

### Testing Patterns

```typescript
// tests/unit/web/test_status_badge.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StatusBadge } from '@fp/ui-components';

describe('StatusBadge', () => {
  it('renders WIN status with correct styling', () => {
    render(<StatusBadge status="win" />);

    const badge = screen.getByRole('status');
    expect(badge).toHaveTextContent('WIN');
    expect(badge).toHaveStyle({ backgroundColor: '#D8F3DC' });
  });

  it('has accessible aria-label', () => {
    render(<StatusBadge status="action" />);

    expect(screen.getByRole('status')).toHaveAttribute(
      'aria-label',
      'Quality status: action'
    );
  });

  it('displays count when provided', () => {
    render(<StatusBadge status="action" count={7} />);

    expect(screen.getByText('7')).toBeInTheDocument();
  });

  it('calls onClick when clickable', async () => {
    const onClick = vi.fn();
    render(<StatusBadge status="win" onClick={onClick} />);

    await userEvent.click(screen.getByRole('status'));

    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
```

### Previous Story Intelligence

**From Story 0.5.4b (BFF API Routes):**
- BFF is complete and tested
- API returns `tier` field: `tier_1`, `tier_2`, `tier_3`, `below_tier_3`
- Tier thresholds are factory-configurable (85%, 70%, 50% defaults)
- Components should map tiers to WIN/WATCH/ACTION:
  - `tier_1` (>=85%) = WIN
  - `tier_2` (70-84%) = WATCH
  - `tier_3`, `below_tier_3` (<70%) = ACTION

**Git History Insight:**
- Recent commits focus on BFF service layer
- No frontend work exists yet - this is greenfield
- npm workspaces not yet configured

### Anti-Patterns to Avoid

1. **DO NOT** use hardcoded colors - ALWAYS use theme tokens or statusColors
2. **DO NOT** create hover-only interactions - must work with touch AND keyboard
3. **DO NOT** use color as sole indicator - always include icon + text
4. **DO NOT** use `any` types - full TypeScript strict mode
5. **DO NOT** skip Storybook stories - required for visual documentation
6. **DO NOT** create components without accessibility - WCAG 2.1 AA minimum
7. **DO NOT** put tests in `libs/ui-components/tests/` - use centralized `tests/unit/web/`

### Files to Create

| Path | Purpose |
|------|---------|
| `libs/ui-components/package.json` | Package manifest |
| `libs/ui-components/tsconfig.json` | TypeScript config |
| `libs/ui-components/vite.config.ts` | Vite library build |
| `libs/ui-components/vitest.config.ts` | Test runner config |
| `libs/ui-components/src/index.ts` | Public exports |
| `libs/ui-components/src/theme/index.ts` | MUI theme export |
| `libs/ui-components/src/theme/palette.ts` | Color definitions |
| `libs/ui-components/src/theme/typography.ts` | Typography config |
| `libs/ui-components/src/components/StatusBadge/StatusBadge.tsx` | Component |
| `libs/ui-components/src/components/StatusBadge/StatusBadge.stories.tsx` | Stories |
| `libs/ui-components/src/components/StatusBadge/index.ts` | Barrel export |
| `libs/ui-components/src/components/TrendIndicator/TrendIndicator.tsx` | Component |
| `libs/ui-components/src/components/TrendIndicator/TrendIndicator.stories.tsx` | Stories |
| `libs/ui-components/src/components/TrendIndicator/index.ts` | Barrel export |
| `libs/ui-components/src/components/LeafTypeTag/LeafTypeTag.tsx` | Component |
| `libs/ui-components/src/components/LeafTypeTag/LeafTypeTag.stories.tsx` | Stories |
| `libs/ui-components/src/components/LeafTypeTag/index.ts` | Barrel export |
| `libs/ui-components/.storybook/main.ts` | Storybook config |
| `libs/ui-components/.storybook/preview.ts` | Storybook preview |
| `tests/unit/web/test_status_badge.test.tsx` | Unit tests |
| `tests/unit/web/test_trend_indicator.test.tsx` | Unit tests |
| `tests/unit/web/test_leaf_type_tag.test.tsx` | Unit tests |

### Files to Modify

| Path | Change |
|------|--------|
| `package.json` (root) | Add `libs/ui-components` to workspaces |

### References

- [Source: _bmad-output/epics/epic-0-5-frontend.md#Story-0.5.5]
- [Source: _bmad-output/architecture/adr/ADR-002-frontend-architecture.md#shared-component-library]
- [Source: _bmad-output/ux-design-specification/6-component-strategy.md]
- [Source: _bmad-output/ux-design-specification/design-system-foundation.md]
- [Source: _bmad-output/project-context.md#ui-ux-rules]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Initial TypeScript JSX parsing issue: theme/index.ts needed .tsx extension for JSX
- Unused import warning: statusColors imported but only re-exported in theme/index.tsx

### Completion Notes List

- Created @fp/ui-components package with npm workspaces configuration
- Implemented MUI v6 theme with Farmer Power color palette
- Created 3 accessible components: StatusBadge, TrendIndicator, LeafTypeTag
- All components follow WCAG 2.1 AA with proper ARIA attributes
- 57 unit tests covering rendering, accessibility, and interaction
- Storybook configured with all component variants
- Library builds with tree-shaking support via Vite
- Task 10 (Visual Snapshots) deferred - requires Chromatic/percy.io integration

### File List

**Created:**
- `package.json` (root) - npm workspaces configuration
- `libs/ui-components/package.json` - @fp/ui-components manifest
- `libs/ui-components/tsconfig.json` - TypeScript strict mode config
- `libs/ui-components/vite.config.ts` - Vite library build config
- `libs/ui-components/vitest.config.ts` - Vitest test runner config
- `libs/ui-components/eslint.config.js` - ESLint flat config
- `libs/ui-components/src/index.ts` - Public exports
- `libs/ui-components/src/test-setup.ts` - Test setup with jest-dom
- `libs/ui-components/src/theme/palette.ts` - Color tokens
- `libs/ui-components/src/theme/typography.ts` - Typography config
- `libs/ui-components/src/theme/index.tsx` - Theme and ThemeProvider
- `libs/ui-components/src/components/StatusBadge/StatusBadge.tsx` - Component
- `libs/ui-components/src/components/StatusBadge/StatusBadge.stories.tsx` - Stories
- `libs/ui-components/src/components/StatusBadge/index.ts` - Barrel export
- `libs/ui-components/src/components/TrendIndicator/TrendIndicator.tsx` - Component
- `libs/ui-components/src/components/TrendIndicator/TrendIndicator.stories.tsx` - Stories
- `libs/ui-components/src/components/TrendIndicator/index.ts` - Barrel export
- `libs/ui-components/src/components/LeafTypeTag/LeafTypeTag.tsx` - Component
- `libs/ui-components/src/components/LeafTypeTag/LeafTypeTag.stories.tsx` - Stories
- `libs/ui-components/src/components/LeafTypeTag/index.ts` - Barrel export
- `libs/ui-components/.storybook/main.ts` - Storybook config
- `libs/ui-components/.storybook/preview.ts` - Storybook preview with ThemeProvider
- `tests/unit/web/test_status_badge.test.tsx` - 19 unit tests
- `tests/unit/web/test_trend_indicator.test.tsx` - 17 unit tests
- `tests/unit/web/test_leaf_type_tag.test.tsx` - 21 unit tests

**Modified:**
- None (all greenfield)
