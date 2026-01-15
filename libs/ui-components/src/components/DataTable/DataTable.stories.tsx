import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import type { GridColDef } from '@mui/x-data-grid';
import { DataTable } from './DataTable';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { Chip } from '@mui/material';

interface Farmer {
  id: string;
  name: string;
  phone: string;
  region: string;
  status: 'win' | 'watch' | 'action';
  primaryPct: number;
}

const sampleFarmers: Farmer[] = [
  { id: '1', name: 'John Kamau', phone: '+254712345678', region: 'Nyeri', status: 'win', primaryPct: 92 },
  { id: '2', name: 'Mary Wanjiku', phone: '+254712345679', region: 'Kiambu', status: 'watch', primaryPct: 78 },
  { id: '3', name: 'Peter Mwangi', phone: '+254712345680', region: 'Meru', status: 'action', primaryPct: 65 },
  { id: '4', name: 'Grace Nyambura', phone: '+254712345681', region: 'Nyeri', status: 'win', primaryPct: 88 },
  { id: '5', name: 'James Ochieng', phone: '+254712345682', region: 'Kisumu', status: 'watch', primaryPct: 72 },
];

const statusColorMap = {
  win: 'success',
  watch: 'warning',
  action: 'error',
} as const;

const columns: GridColDef<Farmer>[] = [
  { field: 'name', headerName: 'Name', flex: 1, minWidth: 150 },
  { field: 'phone', headerName: 'Phone', flex: 1, minWidth: 140 },
  { field: 'region', headerName: 'Region', flex: 1, minWidth: 100 },
  {
    field: 'status',
    headerName: 'Status',
    width: 120,
    renderCell: (params) => {
      const value = params.value as 'win' | 'watch' | 'action';
      return (
        <Chip
          label={value.toUpperCase()}
          color={statusColorMap[value]}
          size="small"
        />
      );
    },
  },
  {
    field: 'primaryPct',
    headerName: 'Primary %',
    width: 110,
    valueFormatter: (value) => `${value}%`,
  },
];

const meta: Meta<typeof DataTable<Farmer>> = {
  component: DataTable,
  title: 'DataDisplay/DataTable',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof DataTable<Farmer>>;

/** Basic table with data */
export const Default: Story = {
  args: {
    columns,
    rows: sampleFarmers,
  },
};

/** Table with row actions */
export const WithActions: Story = {
  args: {
    columns,
    rows: sampleFarmers,
    actions: [
      { id: 'view', label: 'View', icon: <VisibilityIcon />, onClick: fn() },
      { id: 'edit', label: 'Edit', icon: <EditIcon />, onClick: fn() },
      { id: 'delete', label: 'Delete', icon: <DeleteIcon />, onClick: fn() },
    ],
  },
};

/** Table with clickable rows */
export const ClickableRows: Story = {
  args: {
    columns,
    rows: sampleFarmers,
    onRowClick: fn(),
  },
};

/** Table with checkbox selection */
export const WithSelection: Story = {
  args: {
    columns,
    rows: sampleFarmers,
    checkboxSelection: true,
    onRowSelectionChange: fn(),
  },
};

/** Loading state */
export const Loading: Story = {
  args: {
    columns,
    rows: [],
    loading: true,
  },
};

/** Empty state */
export const Empty: Story = {
  args: {
    columns,
    rows: [],
    noRowsText: 'No farmers found. Try adjusting your filters.',
  },
};

/** Compact density */
export const CompactDensity: Story = {
  args: {
    columns,
    rows: sampleFarmers,
    density: 'compact',
    actions: [
      { id: 'edit', label: 'Edit', icon: <EditIcon />, onClick: fn() },
    ],
  },
};
