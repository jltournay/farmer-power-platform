import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AdminShell, ThemeProvider } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('AdminShell', () => {
  describe('rendering', () => {
    it('renders sidebar content', () => {
      renderWithTheme(
        <AdminShell sidebar={<div data-testid="sidebar">Sidebar</div>}>
          <div>Content</div>
        </AdminShell>
      );

      expect(screen.getByTestId('sidebar')).toBeInTheDocument();
    });

    it('renders children content', () => {
      renderWithTheme(
        <AdminShell sidebar={<div>Sidebar</div>}>
          <div data-testid="content">Main Content</div>
        </AdminShell>
      );

      expect(screen.getByTestId('content')).toBeInTheDocument();
    });

    it('renders breadcrumb component when provided', () => {
      renderWithTheme(
        <AdminShell
          sidebar={<div>Sidebar</div>}
          breadcrumbComponent={<nav data-testid="breadcrumb">Breadcrumb</nav>}
        >
          <div>Content</div>
        </AdminShell>
      );

      expect(screen.getByTestId('breadcrumb')).toBeInTheDocument();
    });

    it('renders header component when provided', () => {
      renderWithTheme(
        <AdminShell
          sidebar={<div>Sidebar</div>}
          header={<header data-testid="header">Header</header>}
        >
          <div>Content</div>
        </AdminShell>
      );

      expect(screen.getByTestId('header')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has nav landmark for sidebar', () => {
      renderWithTheme(
        <AdminShell sidebar={<div>Sidebar</div>}>
          <div>Content</div>
        </AdminShell>
      );

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('has main landmark for content', () => {
      renderWithTheme(
        <AdminShell sidebar={<div>Sidebar</div>}>
          <div>Content</div>
        </AdminShell>
      );

      expect(screen.getByRole('main')).toBeInTheDocument();
    });
  });
});
