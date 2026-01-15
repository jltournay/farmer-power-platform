import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { fn } from '@storybook/test';
import { Box } from '@mui/material';
import { Sidebar } from './Sidebar';
import HomeIcon from '@mui/icons-material/Home';
import PeopleIcon from '@mui/icons-material/People';
import FactoryIcon from '@mui/icons-material/Factory';
import PublicIcon from '@mui/icons-material/Public';
import GradingIcon from '@mui/icons-material/Grading';
import SettingsIcon from '@mui/icons-material/Settings';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';

const sampleItems = [
  { id: 'regions', label: 'Regions', icon: <PublicIcon />, href: '/regions' },
  { id: 'farmers', label: 'Farmers', icon: <PeopleIcon />, href: '/farmers' },
  { id: 'factories', label: 'Factories', icon: <FactoryIcon />, href: '/factories' },
  { id: 'grading', label: 'Grading Models', icon: <GradingIcon />, href: '/grading-models', group: 'Configuration' },
  { id: 'health', label: 'Health', icon: <MonitorHeartIcon />, href: '/health', group: 'System' },
  { id: 'costs', label: 'Costs', icon: <AttachMoneyIcon />, href: '/costs' },
  { id: 'settings', label: 'Settings', icon: <SettingsIcon />, href: '/settings' },
];

const meta: Meta<typeof Sidebar> = {
  component: Sidebar,
  title: 'Shell/Sidebar',
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
  },
  argTypes: {
    collapsed: {
      control: 'boolean',
      description: 'Whether sidebar is collapsed',
    },
    activeItem: {
      control: 'select',
      options: ['regions', 'farmers', 'factories', 'grading', 'health', 'costs', 'settings'],
      description: 'Currently active menu item',
    },
  },
};

export default meta;
type Story = StoryObj<typeof Sidebar>;

/** Expanded sidebar with all items visible */
export const Expanded: Story = {
  args: {
    items: sampleItems,
    activeItem: 'farmers',
    collapsed: false,
    onCollapse: fn(),
    onItemClick: fn(),
    brandName: 'Farmer Power',
    brandLogo: <Box sx={{ width: 32, height: 32, bgcolor: 'primary.main', borderRadius: 1 }} />,
  },
};

/** Collapsed sidebar with icons only */
export const Collapsed: Story = {
  args: {
    items: sampleItems,
    activeItem: 'farmers',
    collapsed: true,
    onCollapse: fn(),
    onItemClick: fn(),
    brandLogo: <Box sx={{ width: 32, height: 32, bgcolor: 'primary.main', borderRadius: 1 }} />,
  },
};

/** Interactive sidebar with toggle functionality */
export const Interactive: Story = {
  render: function InteractiveSidebar() {
    const [collapsed, setCollapsed] = useState(false);
    const [activeItem, setActiveItem] = useState('farmers');

    return (
      <Sidebar
        items={sampleItems}
        collapsed={collapsed}
        onCollapse={setCollapsed}
        activeItem={activeItem}
        onItemClick={(item) => setActiveItem(item.id)}
        brandName="Farmer Power"
        brandLogo={<Box sx={{ width: 32, height: 32, bgcolor: 'primary.main', borderRadius: 1 }} />}
      />
    );
  },
};

/** Sidebar with grouped items and dividers */
export const WithGroups: Story = {
  args: {
    items: [
      { id: 'home', label: 'Home', icon: <HomeIcon />, href: '/' },
      { id: 'farmers', label: 'Farmers', icon: <PeopleIcon />, href: '/farmers' },
      { id: 'factories', label: 'Factories', icon: <FactoryIcon />, href: '/factories', group: 'Management' },
      { id: 'regions', label: 'Regions', icon: <PublicIcon />, href: '/regions' },
      { id: 'grading', label: 'Grading', icon: <GradingIcon />, href: '/grading', group: 'Configuration' },
      { id: 'settings', label: 'Settings', icon: <SettingsIcon />, href: '/settings', group: 'Admin' },
    ],
    activeItem: 'factories',
    collapsed: false,
    onCollapse: fn(),
    onItemClick: fn(),
    brandName: 'Platform Admin',
  },
};
