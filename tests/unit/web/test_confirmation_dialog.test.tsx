import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfirmationDialog, ThemeProvider } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('ConfirmationDialog', () => {
  describe('rendering', () => {
    it('renders title', () => {
      renderWithTheme(
        <ConfirmationDialog
          open={true}
          title="Delete Item"
          message="Are you sure?"
          onConfirm={vi.fn()}
          onClose={vi.fn()}
        />
      );

      expect(screen.getByText('Delete Item')).toBeInTheDocument();
    });

    it('renders message', () => {
      renderWithTheme(
        <ConfirmationDialog
          open={true}
          title="Delete"
          message="This action cannot be undone."
          onConfirm={vi.fn()}
          onClose={vi.fn()}
        />
      );

      expect(screen.getByText('This action cannot be undone.')).toBeInTheDocument();
    });

    it('renders custom button text', () => {
      renderWithTheme(
        <ConfirmationDialog
          open={true}
          title="Delete"
          message="Are you sure?"
          confirmText="Yes, Delete"
          cancelText="No, Keep"
          onConfirm={vi.fn()}
          onClose={vi.fn()}
        />
      );

      expect(screen.getByRole('button', { name: 'Yes, Delete' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'No, Keep' })).toBeInTheDocument();
    });

    it('does not render when closed', () => {
      renderWithTheme(
        <ConfirmationDialog
          open={false}
          title="Delete"
          message="Are you sure?"
          onConfirm={vi.fn()}
          onClose={vi.fn()}
        />
      );

      expect(screen.queryByText('Delete')).not.toBeInTheDocument();
    });

    it('shows loading state', () => {
      renderWithTheme(
        <ConfirmationDialog
          open={true}
          title="Delete"
          message="Are you sure?"
          loading={true}
          onConfirm={vi.fn()}
          onClose={vi.fn()}
        />
      );

      expect(screen.getByText('Processing...')).toBeInTheDocument();
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('calls onConfirm when confirm button is clicked', async () => {
      const user = userEvent.setup();
      const handleConfirm = vi.fn();

      renderWithTheme(
        <ConfirmationDialog
          open={true}
          title="Delete"
          message="Are you sure?"
          onConfirm={handleConfirm}
          onClose={vi.fn()}
        />
      );

      await user.click(screen.getByRole('button', { name: 'Confirm' }));

      expect(handleConfirm).toHaveBeenCalled();
    });

    it('calls onClose when cancel button is clicked', async () => {
      const user = userEvent.setup();
      const handleClose = vi.fn();

      renderWithTheme(
        <ConfirmationDialog
          open={true}
          title="Delete"
          message="Are you sure?"
          onConfirm={vi.fn()}
          onClose={handleClose}
        />
      );

      await user.click(screen.getByRole('button', { name: 'Cancel' }));

      expect(handleClose).toHaveBeenCalled();
    });

    it('calls onClose when close icon is clicked', async () => {
      const user = userEvent.setup();
      const handleClose = vi.fn();

      renderWithTheme(
        <ConfirmationDialog
          open={true}
          title="Delete"
          message="Are you sure?"
          onConfirm={vi.fn()}
          onClose={handleClose}
        />
      );

      await user.click(screen.getByLabelText('Close'));

      expect(handleClose).toHaveBeenCalled();
    });

    it('disables buttons when loading', () => {
      renderWithTheme(
        <ConfirmationDialog
          open={true}
          title="Delete"
          message="Are you sure?"
          loading={true}
          onConfirm={vi.fn()}
          onClose={vi.fn()}
        />
      );

      expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Processing...' })).toBeDisabled();
    });
  });

  describe('accessibility', () => {
    it('has proper dialog role', () => {
      renderWithTheme(
        <ConfirmationDialog
          open={true}
          title="Delete"
          message="Are you sure?"
          onConfirm={vi.fn()}
          onClose={vi.fn()}
        />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('has aria-labelledby for title', () => {
      renderWithTheme(
        <ConfirmationDialog
          open={true}
          title="Delete"
          message="Are you sure?"
          onConfirm={vi.fn()}
          onClose={vi.fn()}
        />
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-labelledby', 'confirmation-dialog-title');
    });

    it('has aria-describedby for message', () => {
      renderWithTheme(
        <ConfirmationDialog
          open={true}
          title="Delete"
          message="Are you sure?"
          onConfirm={vi.fn()}
          onClose={vi.fn()}
        />
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-describedby', 'confirmation-dialog-description');
    });
  });
});
