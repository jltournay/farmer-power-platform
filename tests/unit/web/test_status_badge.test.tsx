import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StatusBadge, ThemeProvider } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('StatusBadge', () => {
  describe('rendering', () => {
    it('renders WIN status with correct label', () => {
      renderWithTheme(<StatusBadge status="win" />);

      const badge = screen.getByRole('status');
      expect(badge).toHaveTextContent('WIN');
    });

    it('renders WATCH status with correct label', () => {
      renderWithTheme(<StatusBadge status="watch" />);

      const badge = screen.getByRole('status');
      expect(badge).toHaveTextContent('WATCH');
    });

    it('renders ACTION NEEDED status with correct label', () => {
      renderWithTheme(<StatusBadge status="action" />);

      const badge = screen.getByRole('status');
      expect(badge).toHaveTextContent('ACTION NEEDED');
    });

    it('renders custom label when provided', () => {
      renderWithTheme(<StatusBadge status="win" label="Excellent" />);

      const badge = screen.getByRole('status');
      expect(badge).toHaveTextContent('Excellent');
    });

    it('displays count when provided', () => {
      renderWithTheme(<StatusBadge status="action" count={7} />);

      expect(screen.getByText('7')).toBeInTheDocument();
    });

    it('does not display count when zero', () => {
      renderWithTheme(<StatusBadge status="action" count={0} />);

      expect(screen.queryByText('0')).not.toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has role="status"', () => {
      renderWithTheme(<StatusBadge status="win" />);

      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has correct aria-label for win status', () => {
      renderWithTheme(<StatusBadge status="win" />);

      expect(screen.getByRole('status')).toHaveAttribute(
        'aria-label',
        'Quality status: win'
      );
    });

    it('has correct aria-label for watch status', () => {
      renderWithTheme(<StatusBadge status="watch" />);

      expect(screen.getByRole('status')).toHaveAttribute(
        'aria-label',
        'Quality status: watch'
      );
    });

    it('has correct aria-label for action status', () => {
      renderWithTheme(<StatusBadge status="action" />);

      expect(screen.getByRole('status')).toHaveAttribute(
        'aria-label',
        'Quality status: action'
      );
    });

    it('is focusable when clickable', () => {
      renderWithTheme(<StatusBadge status="win" onClick={() => {}} />);

      const badge = screen.getByRole('status');
      expect(badge).toHaveAttribute('tabIndex', '0');
    });

    it('is not focusable when not clickable', () => {
      renderWithTheme(<StatusBadge status="win" />);

      const badge = screen.getByRole('status');
      expect(badge).not.toHaveAttribute('tabIndex');
    });
  });

  describe('interaction', () => {
    it('calls onClick when clicked', async () => {
      const onClick = vi.fn();
      const user = userEvent.setup();

      renderWithTheme(<StatusBadge status="win" onClick={onClick} />);

      await user.click(screen.getByRole('status'));

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('calls onClick when Enter key is pressed', async () => {
      const onClick = vi.fn();
      const user = userEvent.setup();

      renderWithTheme(<StatusBadge status="win" onClick={onClick} />);

      const badge = screen.getByRole('status');
      badge.focus();
      await user.keyboard('{Enter}');

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('calls onClick when Space key is pressed', async () => {
      const onClick = vi.fn();
      const user = userEvent.setup();

      renderWithTheme(<StatusBadge status="win" onClick={onClick} />);

      const badge = screen.getByRole('status');
      badge.focus();
      await user.keyboard(' ');

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('does not call onClick when non-interactive key is pressed', async () => {
      const onClick = vi.fn();
      const user = userEvent.setup();

      renderWithTheme(<StatusBadge status="win" onClick={onClick} />);

      const badge = screen.getByRole('status');
      badge.focus();
      await user.keyboard('a');

      expect(onClick).not.toHaveBeenCalled();
    });
  });

  describe('sizes', () => {
    it('renders small size', () => {
      renderWithTheme(<StatusBadge status="win" size="small" />);

      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('renders medium size (default)', () => {
      renderWithTheme(<StatusBadge status="win" />);

      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('renders large size', () => {
      renderWithTheme(<StatusBadge status="win" size="large" />);

      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });
});
