import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FileDropzone, ThemeProvider } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('FileDropzone', () => {
  describe('rendering', () => {
    it('renders dropzone area', () => {
      renderWithTheme(<FileDropzone />);

      expect(screen.getByText(/Drag & drop files here/)).toBeInTheDocument();
    });

    it('renders browse button', () => {
      renderWithTheme(<FileDropzone />);

      expect(screen.getByRole('button', { name: 'Browse Files' })).toBeInTheDocument();
    });

    it('renders helper text when provided', () => {
      renderWithTheme(
        <FileDropzone helperText="Supported formats: PDF, CSV" />
      );

      expect(screen.getByText('Supported formats: PDF, CSV')).toBeInTheDocument();
    });

    it('renders error message when provided', () => {
      renderWithTheme(
        <FileDropzone error="File upload failed" />
      );

      expect(screen.getByText('File upload failed')).toBeInTheDocument();
    });

    it('renders uploaded files list', () => {
      renderWithTheme(
        <FileDropzone
          files={[
            { name: 'document.pdf', size: 1024, type: 'application/pdf' },
            { name: 'data.csv', size: 2048, type: 'text/csv' },
          ]}
        />
      );

      expect(screen.getByText('document.pdf')).toBeInTheDocument();
      expect(screen.getByText('data.csv')).toBeInTheDocument();
    });

    it('shows file size', () => {
      renderWithTheme(
        <FileDropzone
          files={[{ name: 'document.pdf', size: 1024, type: 'application/pdf' }]}
        />
      );

      expect(screen.getByText('1 KB')).toBeInTheDocument();
    });

    it('shows upload progress', () => {
      renderWithTheme(
        <FileDropzone
          files={[{ name: 'document.pdf', size: 1024, type: 'application/pdf', progress: 50 }]}
        />
      );

      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('shows completed state', () => {
      renderWithTheme(
        <FileDropzone
          files={[{ name: 'document.pdf', size: 1024, type: 'application/pdf', complete: true }]}
        />
      );

      // Complete state shows check icon
      expect(screen.getByTestId('CheckCircleIcon')).toBeInTheDocument();
    });
  });

  describe('disabled state', () => {
    it('shows disabled state', () => {
      renderWithTheme(<FileDropzone disabled={true} />);

      expect(screen.getByRole('button', { name: 'Browse Files' })).toBeDisabled();
    });
  });

  describe('interactions', () => {
    it('calls onFileRemove when remove button is clicked', async () => {
      const user = userEvent.setup();
      const handleRemove = vi.fn();

      renderWithTheme(
        <FileDropzone
          files={[{ name: 'document.pdf', size: 1024, type: 'application/pdf' }]}
          onFileRemove={handleRemove}
        />
      );

      await user.click(screen.getByLabelText('Remove document.pdf'));

      expect(handleRemove).toHaveBeenCalledWith(0);
    });
  });

  describe('accessibility', () => {
    it('has aria-label on dropzone', () => {
      renderWithTheme(<FileDropzone />);

      expect(screen.getByLabelText('File upload dropzone')).toBeInTheDocument();
    });

    it('is keyboard accessible', async () => {
      const user = userEvent.setup();
      renderWithTheme(<FileDropzone />);

      const dropzone = screen.getByLabelText('File upload dropzone');
      dropzone.focus();

      // Should be focusable
      expect(dropzone).toHaveFocus();
    });

    it('remove button has accessible label', () => {
      renderWithTheme(
        <FileDropzone
          files={[{ name: 'test.pdf', size: 1024, type: 'application/pdf' }]}
          onFileRemove={vi.fn()}
        />
      );

      expect(screen.getByLabelText('Remove test.pdf')).toBeInTheDocument();
    });
  });
});
