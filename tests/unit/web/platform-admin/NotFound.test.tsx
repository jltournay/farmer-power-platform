/**
 * NotFound Page Tests
 *
 * Tests for 404 page functionality.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@fp/ui-components';
import { NotFound } from '@/pages/NotFound';
import { describe, it, expect } from 'vitest';

function MockDashboard() {
  return <div data-testid="dashboard">Dashboard</div>;
}

function renderNotFound() {
  return render(
    <MemoryRouter initialEntries={['/unknown-page']}>
      <ThemeProvider>
        <Routes>
          <Route path="/dashboard" element={<MockDashboard />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </ThemeProvider>
    </MemoryRouter>
  );
}

describe('NotFound', () => {
  it('renders 404 message', () => {
    renderNotFound();
    expect(screen.getByText('Page Not Found')).toBeInTheDocument();
  });

  it('renders descriptive text', () => {
    renderNotFound();
    expect(screen.getByText(/does not exist or has been moved/i)).toBeInTheDocument();
  });

  it('renders go to dashboard button', () => {
    renderNotFound();
    expect(screen.getByRole('button', { name: /go to dashboard/i })).toBeInTheDocument();
  });

  it('navigates to dashboard when button is clicked', async () => {
    const user = userEvent.setup();
    renderNotFound();

    const button = screen.getByRole('button', { name: /go to dashboard/i });
    await user.click(button);

    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
  });

  it('renders error icon', () => {
    renderNotFound();
    // The error icon should be present (check for svg element)
    expect(document.querySelector('svg')).toBeInTheDocument();
  });
});
