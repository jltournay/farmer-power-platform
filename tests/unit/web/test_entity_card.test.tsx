import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EntityCard, ThemeProvider } from '@fp/ui-components';
import PersonIcon from '@mui/icons-material/Person';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('EntityCard', () => {
  describe('rendering', () => {
    it('renders title', () => {
      renderWithTheme(<EntityCard title="John Kamau" />);

      expect(screen.getByText('John Kamau')).toBeInTheDocument();
    });

    it('renders subtitle when provided', () => {
      renderWithTheme(
        <EntityCard title="John Kamau" subtitle="Nyeri County" />
      );

      expect(screen.getByText('Nyeri County')).toBeInTheDocument();
    });

    it('renders icon when provided', () => {
      renderWithTheme(
        <EntityCard title="John" icon={<PersonIcon data-testid="icon" />} />
      );

      expect(screen.getByTestId('icon')).toBeInTheDocument();
    });

    it('renders status badge when provided', () => {
      renderWithTheme(
        <EntityCard
          title="John"
          statusBadge={<span data-testid="badge">Active</span>}
        />
      );

      expect(screen.getByTestId('badge')).toBeInTheDocument();
    });

    it('renders metric with label', () => {
      renderWithTheme(
        <EntityCard title="John" metric="92%" metricLabel="Primary" />
      );

      expect(screen.getByText('92%')).toBeInTheDocument();
      expect(screen.getByText('Primary')).toBeInTheDocument();
    });

    it('renders children content', () => {
      renderWithTheme(
        <EntityCard title="John">
          <div data-testid="extra">Extra content</div>
        </EntityCard>
      );

      expect(screen.getByTestId('extra')).toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('calls onClick when clicked', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      renderWithTheme(<EntityCard title="John" onClick={handleClick} />);

      await user.click(screen.getByText('John'));

      expect(handleClick).toHaveBeenCalled();
    });

    it('is not clickable when onClick is not provided', () => {
      renderWithTheme(<EntityCard title="John" />);

      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });

  describe('selection', () => {
    it('shows selected state', () => {
      const { container } = renderWithTheme(
        <EntityCard title="John" selected={true} />
      );

      const card = container.querySelector('.MuiCard-root');
      expect(card).toHaveStyle({ borderColor: expect.stringContaining('') });
    });
  });

  describe('accessibility', () => {
    it('has article role', () => {
      renderWithTheme(<EntityCard title="John" />);

      expect(screen.getByRole('article')).toBeInTheDocument();
    });
  });
});
