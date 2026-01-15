import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { PageHeader } from './PageHeader';
import { StatusBadge } from '../StatusBadge';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';

const meta: Meta<typeof PageHeader> = {
  component: PageHeader,
  title: 'Shell/PageHeader',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof PageHeader>;

/** Simple title only */
export const TitleOnly: Story = {
  args: {
    title: 'Dashboard',
  },
};

/** Title with subtitle */
export const WithSubtitle: Story = {
  args: {
    title: 'Farmers',
    subtitle: 'Manage farmer records across all regions',
  },
};

/** Title with primary action */
export const WithAction: Story = {
  args: {
    title: 'Farmers',
    subtitle: '342 registered farmers',
    actions: [
      { id: 'add', label: 'Add Farmer', icon: <AddIcon />, variant: 'contained', onClick: fn() },
    ],
  },
};

/** Detail page with back navigation */
export const DetailPage: Story = {
  args: {
    title: 'John Kamau',
    subtitle: 'Farmer ID: FRM-001 | Nyeri County',
    backHref: '/farmers',
    onBack: fn(),
    actions: [
      { id: 'edit', label: 'Edit', icon: <EditIcon />, variant: 'outlined', onClick: fn() },
      { id: 'delete', label: 'Delete', icon: <DeleteIcon />, variant: 'outlined', color: 'error', onClick: fn() },
    ],
  },
};

/** With status badge */
export const WithStatusBadge: Story = {
  args: {
    title: 'John Kamau',
    subtitle: 'Farmer ID: FRM-001',
    backHref: '/farmers',
    onBack: fn(),
    statusBadge: <StatusBadge status="win" size="small" />,
    actions: [
      { id: 'edit', label: 'Edit', variant: 'outlined', onClick: fn() },
    ],
  },
};

/** Multiple action buttons */
export const MultipleActions: Story = {
  args: {
    title: 'Grading Models',
    subtitle: 'Configure quality grading rules',
    actions: [
      { id: 'export', label: 'Export', icon: <DownloadIcon />, variant: 'outlined', onClick: fn() },
      { id: 'add', label: 'New Model', icon: <AddIcon />, variant: 'contained', onClick: fn() },
    ],
  },
};
