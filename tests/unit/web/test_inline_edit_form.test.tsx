import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { InlineEditForm, ThemeProvider } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

const sampleFields = [
  { id: 'name', label: 'Name', required: true },
  { id: 'email', label: 'Email', type: 'email' as const },
  { id: 'phone', label: 'Phone', type: 'tel' as const },
];

const sampleValues = {
  name: 'John Kamau',
  email: 'john@example.com',
  phone: '+254712345678',
};

describe('InlineEditForm', () => {
  describe('read mode', () => {
    it('displays field values in read mode', () => {
      renderWithTheme(
        <InlineEditForm
          fields={sampleFields}
          values={sampleValues}
          onSave={vi.fn()}
        />
      );

      expect(screen.getByText('John Kamau')).toBeInTheDocument();
      expect(screen.getByText('john@example.com')).toBeInTheDocument();
    });

    it('shows edit button in read mode', () => {
      renderWithTheme(
        <InlineEditForm
          title="Contact Info"
          fields={sampleFields}
          values={sampleValues}
          onSave={vi.fn()}
        />
      );

      expect(screen.getByLabelText('Edit')).toBeInTheDocument();
    });

    it('shows dash for empty values', () => {
      renderWithTheme(
        <InlineEditForm
          fields={[{ id: 'name', label: 'Name' }]}
          values={{ name: '' }}
          onSave={vi.fn()}
        />
      );

      expect(screen.getByText('—')).toBeInTheDocument();
    });
  });

  describe('edit mode', () => {
    it('shows text fields in edit mode', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <InlineEditForm
          title="Info"
          fields={sampleFields}
          values={sampleValues}
          onSave={vi.fn()}
        />
      );

      await user.click(screen.getByLabelText('Edit'));

      expect(screen.getByLabelText('Name *')).toBeInTheDocument();
      expect(screen.getByLabelText('Email')).toBeInTheDocument();
    });

    it('shows Save and Cancel buttons in edit mode', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <InlineEditForm
          title="Info"
          fields={sampleFields}
          values={sampleValues}
          onSave={vi.fn()}
        />
      );

      await user.click(screen.getByLabelText('Edit'));

      expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('calls onSave with updated values', async () => {
      const user = userEvent.setup();
      const handleSave = vi.fn().mockResolvedValue(true);

      renderWithTheme(
        <InlineEditForm
          title="Info"
          fields={sampleFields}
          values={sampleValues}
          onSave={handleSave}
        />
      );

      await user.click(screen.getByLabelText('Edit'));
      await user.clear(screen.getByLabelText('Name *'));
      await user.type(screen.getByLabelText('Name *'), 'Jane Doe');
      await user.click(screen.getByRole('button', { name: 'Save' }));

      await waitFor(() => {
        expect(handleSave).toHaveBeenCalledWith(
          expect.objectContaining({ name: 'Jane Doe' })
        );
      });
    });

    it('cancels editing and reverts changes', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <InlineEditForm
          title="Info"
          fields={sampleFields}
          values={sampleValues}
          onSave={vi.fn()}
        />
      );

      await user.click(screen.getByLabelText('Edit'));
      await user.clear(screen.getByLabelText('Name *'));
      await user.type(screen.getByLabelText('Name *'), 'Changed');
      await user.click(screen.getByRole('button', { name: 'Cancel' }));

      expect(screen.getByText('John Kamau')).toBeInTheDocument();
    });

    it('cancels on Escape key', async () => {
      const user = userEvent.setup();

      renderWithTheme(
        <InlineEditForm
          title="Info"
          fields={sampleFields}
          values={sampleValues}
          onSave={vi.fn()}
        />
      );

      await user.click(screen.getByLabelText('Edit'));
      await user.keyboard('{Escape}');

      expect(screen.getByLabelText('Edit')).toBeInTheDocument();
    });
  });

  describe('validation', () => {
    it('shows error for required empty field', async () => {
      const user = userEvent.setup();
      const handleSave = vi.fn().mockResolvedValue(true);

      renderWithTheme(
        <InlineEditForm
          title="Info"
          fields={sampleFields}
          values={sampleValues}
          onSave={handleSave}
        />
      );

      await user.click(screen.getByLabelText('Edit'));
      await user.clear(screen.getByLabelText('Name *'));
      await user.click(screen.getByRole('button', { name: 'Save' }));

      expect(screen.getByText('Name is required')).toBeInTheDocument();
      expect(handleSave).not.toHaveBeenCalled();
    });
  });
});
