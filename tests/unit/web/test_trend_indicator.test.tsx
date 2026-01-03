import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TrendIndicator, ThemeProvider } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('TrendIndicator', () => {
  describe('rendering', () => {
    it('renders upward trend with positive value', () => {
      renderWithTheme(<TrendIndicator direction="up" value={12} />);

      const indicator = screen.getByRole('img');
      expect(indicator).toHaveTextContent('+12%');
    });

    it('renders downward trend with negative value', () => {
      renderWithTheme(<TrendIndicator direction="down" value={5} />);

      const indicator = screen.getByRole('img');
      expect(indicator).toHaveTextContent('-5%');
    });

    it('renders stable trend with value', () => {
      renderWithTheme(<TrendIndicator direction="stable" value={0} />);

      const indicator = screen.getByRole('img');
      expect(indicator).toHaveTextContent('0%');
    });

    it('renders period when provided', () => {
      renderWithTheme(
        <TrendIndicator direction="up" value={8} period="vs last week" />
      );

      expect(screen.getByText('vs last week')).toBeInTheDocument();
    });

    it('does not render period when not provided', () => {
      renderWithTheme(<TrendIndicator direction="up" value={8} />);

      expect(screen.queryByText('vs last week')).not.toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has role="img"', () => {
      renderWithTheme(<TrendIndicator direction="up" value={12} />);

      expect(screen.getByRole('img')).toBeInTheDocument();
    });

    it('has correct aria-label for upward trend', () => {
      renderWithTheme(<TrendIndicator direction="up" value={12} />);

      expect(screen.getByRole('img')).toHaveAttribute(
        'aria-label',
        'Quality trend: up 12%'
      );
    });

    it('has correct aria-label for downward trend', () => {
      renderWithTheme(<TrendIndicator direction="down" value={5} />);

      expect(screen.getByRole('img')).toHaveAttribute(
        'aria-label',
        'Quality trend: down 5%'
      );
    });

    it('has correct aria-label for stable trend', () => {
      renderWithTheme(<TrendIndicator direction="stable" value={0} />);

      expect(screen.getByRole('img')).toHaveAttribute(
        'aria-label',
        'Quality trend: stable 0%'
      );
    });

    it('includes period in aria-label when provided', () => {
      renderWithTheme(
        <TrendIndicator direction="up" value={8} period="vs last week" />
      );

      expect(screen.getByRole('img')).toHaveAttribute(
        'aria-label',
        'Quality trend: up 8% vs last week'
      );
    });

    it('uses icon + text + color (not color alone)', () => {
      renderWithTheme(<TrendIndicator direction="up" value={12} />);

      // Should have both an icon (SVG) and text
      const indicator = screen.getByRole('img');
      expect(indicator).toContainHTML('svg'); // MUI icon
      expect(indicator).toHaveTextContent('+12%'); // Text
    });
  });

  describe('sizes', () => {
    it('renders small size', () => {
      renderWithTheme(<TrendIndicator direction="up" value={8} size="small" />);

      expect(screen.getByRole('img')).toBeInTheDocument();
    });

    it('renders medium size (default)', () => {
      renderWithTheme(<TrendIndicator direction="up" value={8} />);

      expect(screen.getByRole('img')).toBeInTheDocument();
    });
  });

  describe('value formatting', () => {
    it('always shows + for positive values', () => {
      renderWithTheme(<TrendIndicator direction="up" value={15} />);

      expect(screen.getByText('+15%')).toBeInTheDocument();
    });

    it('always shows - for negative values', () => {
      renderWithTheme(<TrendIndicator direction="down" value={7} />);

      expect(screen.getByText('-7%')).toBeInTheDocument();
    });

    it('shows value without sign for stable', () => {
      renderWithTheme(<TrendIndicator direction="stable" value={0} />);

      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('handles large values', () => {
      renderWithTheme(<TrendIndicator direction="up" value={150} />);

      expect(screen.getByText('+150%')).toBeInTheDocument();
    });
  });
});
