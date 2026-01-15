import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DataTable, ThemeProvider } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

interface TestRow {
  id: string;
  name: string;
  status: string;
}

const columns = [
  { field: 'name', headerName: 'Name', flex: 1 },
  { field: 'status', headerName: 'Status', width: 100 },
];

const rows: TestRow[] = [
  { id: '1', name: 'John Kamau', status: 'Active' },
  { id: '2', name: 'Mary Wanjiku', status: 'Pending' },
];

describe('DataTable', () => {
  describe('rendering', () => {
    it('renders column headers', () => {
      renderWithTheme(<DataTable columns={columns} rows={rows} />);

      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    it('renders row data', () => {
      renderWithTheme(<DataTable columns={columns} rows={rows} />);

      expect(screen.getByText('John Kamau')).toBeInTheDocument();
      expect(screen.getByText('Mary Wanjiku')).toBeInTheDocument();
    });

    it('shows loading state', () => {
      renderWithTheme(<DataTable columns={columns} rows={[]} loading={true} />);

      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('shows custom no rows text when empty', () => {
      renderWithTheme(
        <DataTable columns={columns} rows={[]} noRowsText="No farmers found" />
      );

      expect(screen.getByText('No farmers found')).toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('calls onRowClick when row is clicked', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      renderWithTheme(
        <DataTable columns={columns} rows={rows} onRowClick={handleClick} />
      );

      // DataGrid cells are clickable
      const cell = screen.getByText('John Kamau');
      await user.click(cell);

      // DataGrid may need the row click to propagate
      expect(handleClick).toHaveBeenCalled();
    });
  });

  describe('selection', () => {
    it('renders checkboxes when checkboxSelection is true', () => {
      renderWithTheme(
        <DataTable columns={columns} rows={rows} checkboxSelection={true} />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBeGreaterThan(0);
    });
  });
});
