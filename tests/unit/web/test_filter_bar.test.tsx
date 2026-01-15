import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FilterBar, ThemeProvider } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

const sampleFilters = [
  {
    id: 'status',
    label: 'Status',
    options: [
      { value: 'active', label: 'Active' },
      { value: 'pending', label: 'Pending' },
    ],
  },
  {
    id: 'region',
    label: 'Region',
    options: [
      { value: 'nyeri', label: 'Nyeri' },
      { value: 'kiambu', label: 'Kiambu' },
    ],
  },
];

describe('FilterBar', () => {
  describe('rendering', () => {
    it('renders search input by default', () => {
      renderWithTheme(<FilterBar />);

      expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument();
    });

    it('hides search input when showSearch is false', () => {
      renderWithTheme(<FilterBar showSearch={false} />);

      expect(screen.queryByPlaceholderText('Search...')).not.toBeInTheDocument();
    });

    it('renders filter dropdowns', () => {
      renderWithTheme(<FilterBar filters={sampleFilters} />);

      expect(screen.getByLabelText('Status')).toBeInTheDocument();
      expect(screen.getByLabelText('Region')).toBeInTheDocument();
    });

    it('shows clear all button when filters are active', () => {
      renderWithTheme(
        <FilterBar
          filters={sampleFilters}
          filterValues={{ status: 'active' }}
          onClearAll={vi.fn()}
        />
      );

      expect(screen.getByText(/Clear all/)).toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('calls onSearchChange when typing in search', async () => {
      const user = userEvent.setup();
      const handleSearch = vi.fn();

      renderWithTheme(<FilterBar onSearchChange={handleSearch} />);

      await user.type(screen.getByPlaceholderText('Search...'), 'john');

      expect(handleSearch).toHaveBeenCalled();
    });

    it('calls onClearAll when clear button is clicked', async () => {
      const user = userEvent.setup();
      const handleClear = vi.fn();

      renderWithTheme(
        <FilterBar
          searchTerm="test"
          onClearAll={handleClear}
        />
      );

      await user.click(screen.getByText(/Clear all/));

      expect(handleClear).toHaveBeenCalled();
    });

    it('calls onFilterChange when filter is changed', async () => {
      const user = userEvent.setup();
      const handleFilterChange = vi.fn();

      renderWithTheme(
        <FilterBar
          filters={sampleFilters}
          filterValues={{}}
          onFilterChange={handleFilterChange}
        />
      );

      // Open the status dropdown
      await user.click(screen.getByLabelText('Status'));
      // Select an option
      await user.click(screen.getByText('Active'));

      expect(handleFilterChange).toHaveBeenCalledWith('status', 'active');
    });
  });

  describe('accessibility', () => {
    it('search input is accessible via placeholder', () => {
      renderWithTheme(<FilterBar />);

      // TextField uses placeholder for identification
      expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument();
    });

    it('clear search button has aria-label', () => {
      renderWithTheme(<FilterBar searchTerm="test" onSearchChange={vi.fn()} />);

      expect(screen.getByLabelText('Clear search')).toBeInTheDocument();
    });
  });
});
