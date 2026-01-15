import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MetricCard, ThemeProvider } from '@fp/ui-components';
import PeopleIcon from '@mui/icons-material/People';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('MetricCard', () => {
  describe('rendering', () => {
    it('renders value', () => {
      renderWithTheme(<MetricCard value={342} label="Farmers" />);

      expect(screen.getByText('342')).toBeInTheDocument();
    });

    it('renders string value', () => {
      renderWithTheme(<MetricCard value="$1,234" label="Revenue" />);

      expect(screen.getByText('$1,234')).toBeInTheDocument();
    });

    it('renders label', () => {
      renderWithTheme(<MetricCard value={100} label="Active Farmers" />);

      expect(screen.getByText('Active Farmers')).toBeInTheDocument();
    });

    it('renders icon when provided', () => {
      renderWithTheme(
        <MetricCard
          value={100}
          label="Farmers"
          icon={<PeopleIcon data-testid="icon" />}
        />
      );

      expect(screen.getByTestId('icon')).toBeInTheDocument();
    });

    it('renders trend indicator when provided', () => {
      renderWithTheme(
        <MetricCard
          value={100}
          label="Farmers"
          trend="up"
          trendValue={12}
          trendPeriod="vs last month"
        />
      );

      // TrendIndicator uses role="img" with aria-label containing the trend info
      expect(screen.getByRole('img', { name: /12%/i })).toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('calls onClick when clicked', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      renderWithTheme(
        <MetricCard value={100} label="Farmers" onClick={handleClick} />
      );

      await user.click(screen.getByRole('figure'));

      expect(handleClick).toHaveBeenCalled();
    });

    it('is keyboard accessible when clickable', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      renderWithTheme(
        <MetricCard value={100} label="Farmers" onClick={handleClick} />
      );

      const card = screen.getByRole('figure');
      card.focus();
      await user.keyboard('{Enter}');

      expect(handleClick).toHaveBeenCalled();
    });
  });

  describe('colors', () => {
    it('applies success color variant', () => {
      const { container } = renderWithTheme(
        <MetricCard value={100} label="Farmers" color="success" />
      );

      const card = container.querySelector('.MuiCard-root');
      expect(card).toBeInTheDocument();
    });

    it('applies warning color variant', () => {
      const { container } = renderWithTheme(
        <MetricCard value={100} label="Farmers" color="warning" />
      );

      const card = container.querySelector('.MuiCard-root');
      expect(card).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has figure role', () => {
      renderWithTheme(<MetricCard value={100} label="Farmers" />);

      expect(screen.getByRole('figure')).toBeInTheDocument();
    });

    it('has aria-label with value and label', () => {
      renderWithTheme(<MetricCard value={100} label="Farmers" />);

      expect(screen.getByRole('figure')).toHaveAttribute(
        'aria-label',
        'Farmers: 100'
      );
    });

    it('uses custom description when provided', () => {
      renderWithTheme(
        <MetricCard value={100} label="Farmers" description="Total active farmers in the system" />
      );

      expect(screen.getByRole('figure')).toHaveAttribute(
        'aria-label',
        'Total active farmers in the system'
      );
    });
  });
});
