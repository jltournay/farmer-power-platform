import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { Breadcrumb } from './Breadcrumb';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';

const meta: Meta<typeof Breadcrumb> = {
  component: Breadcrumb,
  title: 'Shell/Breadcrumb',
  tags: ['autodocs'],
  argTypes: {
    onNavigate: {
      action: 'navigate',
      description: 'Called when a breadcrumb link is clicked',
    },
  },
};

export default meta;
type Story = StoryObj<typeof Breadcrumb>;

/** Simple two-level breadcrumb */
export const TwoLevel: Story = {
  args: {
    items: [
      { label: 'Farmers', href: '/farmers' },
      { label: 'John Kamau' },
    ],
    onNavigate: fn(),
  },
};

/** Multi-level breadcrumb trail */
export const MultiLevel: Story = {
  args: {
    items: [
      { label: 'Factories', href: '/factories' },
      { label: 'Nyeri Tea Factory', href: '/factories/nyeri-001' },
      { label: 'Collection Points', href: '/factories/nyeri-001/collection-points' },
      { label: 'Karatina CP' },
    ],
    onNavigate: fn(),
  },
};

/** Breadcrumb with custom icons */
export const WithIcons: Story = {
  args: {
    items: [
      { label: 'Documents', href: '/docs', icon: <FolderIcon sx={{ mr: 0.5, fontSize: 18 }} /> },
      { label: 'Grading Models', href: '/docs/grading', icon: <FolderIcon sx={{ mr: 0.5, fontSize: 18 }} /> },
      { label: 'Kenya Tea Grades.pdf', icon: <DescriptionIcon sx={{ mr: 0.5, fontSize: 18 }} /> },
    ],
    onNavigate: fn(),
  },
};

/** Breadcrumb without home item */
export const NoHome: Story = {
  args: {
    items: [
      { label: 'Settings', href: '/settings' },
      { label: 'Notifications' },
    ],
    homeItem: null,
    onNavigate: fn(),
  },
};

/** Single item (just current page) */
export const SingleItem: Story = {
  args: {
    items: [
      { label: 'Dashboard' },
    ],
    onNavigate: fn(),
  },
};
