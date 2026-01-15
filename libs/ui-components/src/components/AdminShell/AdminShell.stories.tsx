import type { Meta, StoryObj } from '@storybook/react';
import { Box, Typography } from '@mui/material';
import { AdminShell } from './AdminShell';
import { Sidebar } from '../Sidebar';
import { Breadcrumb } from '../Breadcrumb';
import { PageHeader } from '../PageHeader';
import HomeIcon from '@mui/icons-material/Home';
import PeopleIcon from '@mui/icons-material/People';
import FactoryIcon from '@mui/icons-material/Factory';
import SettingsIcon from '@mui/icons-material/Settings';

const sampleSidebarItems = [
  { id: 'home', label: 'Home', icon: <HomeIcon />, href: '/' },
  { id: 'farmers', label: 'Farmers', icon: <PeopleIcon />, href: '/farmers' },
  { id: 'factories', label: 'Factories', icon: <FactoryIcon />, href: '/factories', group: 'Management' },
  { id: 'settings', label: 'Settings', icon: <SettingsIcon />, href: '/settings', group: 'Admin' },
];

const meta: Meta<typeof AdminShell> = {
  component: AdminShell,
  title: 'Shell/AdminShell',
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof AdminShell>;

/** Basic layout with sidebar expanded */
export const Default: Story = {
  render: () => (
    <AdminShell
      sidebar={
        <Sidebar
          items={sampleSidebarItems}
          activeItem="farmers"
          collapsed={false}
          onCollapse={() => {}}
        />
      }
      breadcrumbComponent={
        <Breadcrumb
          items={[
            { label: 'Home', href: '/' },
            { label: 'Farmers' },
          ]}
        />
      }
      sidebarOpen={true}
      sidebarWidth={240}
    >
      <PageHeader title="Farmers" subtitle="Manage farmer records" />
      <Box sx={{ p: 2 }}>
        <Typography>Main content area</Typography>
      </Box>
    </AdminShell>
  ),
};

/** Layout with collapsed sidebar */
export const CollapsedSidebar: Story = {
  render: () => (
    <AdminShell
      sidebar={
        <Sidebar
          items={sampleSidebarItems}
          activeItem="farmers"
          collapsed={true}
          onCollapse={() => {}}
        />
      }
      sidebarOpen={false}
      sidebarWidth={64}
    >
      <PageHeader title="Farmers" />
      <Box sx={{ p: 2 }}>
        <Typography>Content with collapsed sidebar</Typography>
      </Box>
    </AdminShell>
  ),
};

/** Layout with all shell components */
export const FullLayout: Story = {
  render: () => (
    <AdminShell
      sidebar={
        <Sidebar
          items={sampleSidebarItems}
          activeItem="factories"
          collapsed={false}
          onCollapse={() => {}}
          brandLogo={<Box sx={{ width: 32, height: 32, bgcolor: 'primary.main', borderRadius: 1 }} />}
          brandName="Farmer Power"
        />
      }
      breadcrumbComponent={
        <Breadcrumb
          items={[
            { label: 'Home', href: '/' },
            { label: 'Factories', href: '/factories' },
            { label: 'Nyeri Tea Factory' },
          ]}
        />
      }
      sidebarOpen={true}
      sidebarWidth={240}
    >
      <PageHeader
        title="Nyeri Tea Factory"
        subtitle="Factory details and collection points"
        backHref="/factories"
      />
      <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
        <Typography variant="h6">Factory Information</Typography>
        <Typography>Location: Nyeri County, Kenya</Typography>
        <Typography>Collection Points: 12</Typography>
      </Box>
    </AdminShell>
  ),
};
