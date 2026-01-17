/**
 * Breadcrumb Component Tests
 *
 * Tests for breadcrumb navigation functionality.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '@fp/ui-components';
import { Breadcrumb } from '@/components/Breadcrumb';
import { describe, it, expect } from 'vitest';

function renderBreadcrumb(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ThemeProvider>
        <Breadcrumb />
      </ThemeProvider>
    </MemoryRouter>
  );
}

describe('Breadcrumb', () => {
  it('renders dashboard link as home', () => {
    renderBreadcrumb('/regions');
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('renders current page as text (not link)', () => {
    renderBreadcrumb('/regions');
    const regionsText = screen.getByText('Regions');
    expect(regionsText.tagName).not.toBe('A');
  });

  it('renders intermediate segments as links', () => {
    renderBreadcrumb('/factories/factory-123/collection-points/cp-456');

    // Dashboard should be a link
    expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument();

    // Factories should be a link
    expect(screen.getByRole('link', { name: /factories/i })).toBeInTheDocument();

    // Factory ID should be a link
    expect(screen.getByRole('link', { name: /factory-123/i })).toBeInTheDocument();

    // Collection Points is skipped (not a navigable page)
    expect(screen.queryByRole('link', { name: /collection points/i })).not.toBeInTheDocument();

    // CP ID should be text (last segment)
    expect(screen.getByText('cp-456')).toBeInTheDocument();
  });

  it('displays minimal content on dashboard', () => {
    renderBreadcrumb('/dashboard');
    // On dashboard, we just show a spacer
    expect(screen.queryByRole('link', { name: /dashboard/i })).not.toBeInTheDocument();
  });

  it('handles region detail path correctly', () => {
    renderBreadcrumb('/regions/nandi-medium');

    expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /regions/i })).toBeInTheDocument();
    // The segment is transformed: nandi-medium -> Nandi Medium
    expect(screen.getByText('Nandi Medium')).toBeInTheDocument();
  });

  it('maps route segments to readable labels', () => {
    renderBreadcrumb('/grading-models');
    expect(screen.getByText('Grading Models')).toBeInTheDocument();
  });

  it('capitalizes unknown segments', () => {
    renderBreadcrumb('/some-unknown-path');
    expect(screen.getByText('Some Unknown Path')).toBeInTheDocument();
  });
});
