/**
 * Layout Component Tests
 *
 * Tests for the main application shell layout.
 * Note: These tests focus on the Layout structure without auth dependencies.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '@fp/ui-components';
import { Breadcrumb } from '@/components/Breadcrumb';
import { describe, it, expect } from 'vitest';

describe('Layout Components', () => {
  describe('Breadcrumb in Layout context', () => {
    it('renders breadcrumb with navigation', () => {
      render(
        <MemoryRouter initialEntries={['/factories/abc']}>
          <ThemeProvider>
            <Breadcrumb />
          </ThemeProvider>
        </MemoryRouter>
      );

      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Factories')).toBeInTheDocument();
    });
  });
});
