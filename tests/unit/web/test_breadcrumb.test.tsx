import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Breadcrumb, ThemeProvider } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('Breadcrumb', () => {
  describe('rendering', () => {
    it('renders all breadcrumb items', () => {
      renderWithTheme(
        <Breadcrumb
          items={[
            { label: 'Factories', href: '/factories' },
            { label: 'Nyeri Tea Factory' },
          ]}
        />
      );

      expect(screen.getByText('Home')).toBeInTheDocument();
      expect(screen.getByText('Factories')).toBeInTheDocument();
      expect(screen.getByText('Nyeri Tea Factory')).toBeInTheDocument();
    });

    it('renders home item by default', () => {
      renderWithTheme(<Breadcrumb items={[{ label: 'Page' }]} />);

      expect(screen.getByText('Home')).toBeInTheDocument();
    });

    it('hides home item when set to null', () => {
      renderWithTheme(
        <Breadcrumb items={[{ label: 'Page' }]} homeItem={null} />
      );

      expect(screen.queryByText('Home')).not.toBeInTheDocument();
    });

    it('returns null when no items and no home item', () => {
      const { container } = renderWithTheme(
        <Breadcrumb items={[]} homeItem={null} />
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe('interactions', () => {
    it('calls onNavigate when link is clicked', async () => {
      const user = userEvent.setup();
      const handleNavigate = vi.fn();

      renderWithTheme(
        <Breadcrumb
          items={[
            { label: 'Factories', href: '/factories' },
            { label: 'Nyeri' },
          ]}
          onNavigate={handleNavigate}
        />
      );

      await user.click(screen.getByText('Factories'));

      expect(handleNavigate).toHaveBeenCalledWith('/factories');
    });
  });

  describe('accessibility', () => {
    it('has breadcrumb aria-label', () => {
      renderWithTheme(<Breadcrumb items={[{ label: 'Page' }]} />);

      expect(screen.getByLabelText('breadcrumb')).toBeInTheDocument();
    });

    it('marks current page with aria-current', () => {
      renderWithTheme(
        <Breadcrumb items={[{ label: 'Current Page' }]} />
      );

      expect(screen.getByText('Current Page')).toHaveAttribute('aria-current', 'page');
    });
  });
});
