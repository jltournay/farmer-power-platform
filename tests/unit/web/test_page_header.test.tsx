import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PageHeader, ThemeProvider } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('PageHeader', () => {
  describe('rendering', () => {
    it('renders title', () => {
      renderWithTheme(<PageHeader title="Farmers" />);

      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Farmers');
    });

    it('renders subtitle when provided', () => {
      renderWithTheme(
        <PageHeader title="Farmers" subtitle="Manage farmer records" />
      );

      expect(screen.getByText('Manage farmer records')).toBeInTheDocument();
    });

    it('renders action buttons', () => {
      renderWithTheme(
        <PageHeader
          title="Farmers"
          actions={[
            { id: 'add', label: 'Add Farmer', onClick: vi.fn() },
          ]}
        />
      );

      expect(screen.getByRole('button', { name: 'Add Farmer' })).toBeInTheDocument();
    });

    it('renders back button when backHref is provided', () => {
      renderWithTheme(
        <PageHeader title="Detail" backHref="/list" onBack={vi.fn()} />
      );

      expect(screen.getByLabelText('Go back')).toBeInTheDocument();
    });

    it('renders status badge when provided', () => {
      renderWithTheme(
        <PageHeader
          title="John Kamau"
          statusBadge={<span data-testid="status">Active</span>}
        />
      );

      expect(screen.getByTestId('status')).toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('calls action onClick when clicked', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      renderWithTheme(
        <PageHeader
          title="Farmers"
          actions={[{ id: 'add', label: 'Add', onClick: handleClick }]}
        />
      );

      await user.click(screen.getByRole('button', { name: 'Add' }));

      expect(handleClick).toHaveBeenCalled();
    });

    it('calls onBack when back button is clicked', async () => {
      const user = userEvent.setup();
      const handleBack = vi.fn();

      renderWithTheme(
        <PageHeader title="Detail" backHref="/list" onBack={handleBack} />
      );

      await user.click(screen.getByLabelText('Go back'));

      expect(handleBack).toHaveBeenCalled();
    });
  });

  describe('accessibility', () => {
    it('uses h1 for title', () => {
      renderWithTheme(<PageHeader title="Page Title" />);

      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveTextContent('Page Title');
    });

    it('back button has accessible label', () => {
      renderWithTheme(
        <PageHeader title="Detail" backHref="/list" onBack={vi.fn()} />
      );

      expect(screen.getByLabelText('Go back')).toBeInTheDocument();
    });
  });
});
