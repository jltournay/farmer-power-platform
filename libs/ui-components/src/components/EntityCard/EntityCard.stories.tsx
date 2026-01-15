import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { Box, Grid } from '@mui/material';
import { EntityCard } from './EntityCard';
import { StatusBadge } from '../StatusBadge';
import { TrendIndicator } from '../TrendIndicator';
import PersonIcon from '@mui/icons-material/Person';
import FactoryIcon from '@mui/icons-material/Factory';
import PublicIcon from '@mui/icons-material/Public';

const meta: Meta<typeof EntityCard> = {
  component: EntityCard,
  title: 'DataDisplay/EntityCard',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof EntityCard>;

/** Basic card with title and subtitle */
export const Basic: Story = {
  args: {
    title: 'John Kamau',
    subtitle: 'Nyeri County, Kenya',
    icon: <PersonIcon />,
  },
};

/** Card with status badge */
export const WithStatus: Story = {
  args: {
    title: 'John Kamau',
    subtitle: 'Nyeri County',
    icon: <PersonIcon />,
    statusBadge: <StatusBadge status="win" size="small" />,
  },
};

/** Card with metric display */
export const WithMetric: Story = {
  args: {
    title: 'John Kamau',
    subtitle: 'Nyeri County',
    icon: <PersonIcon />,
    statusBadge: <StatusBadge status="win" size="small" />,
    metric: '92%',
    metricLabel: 'Primary',
  },
};

/** Clickable card */
export const Clickable: Story = {
  args: {
    title: 'John Kamau',
    subtitle: 'Nyeri County',
    icon: <PersonIcon />,
    statusBadge: <StatusBadge status="watch" size="small" />,
    metric: '78%',
    metricLabel: 'Primary',
    onClick: fn(),
  },
};

/** Selected card */
export const Selected: Story = {
  args: {
    title: 'John Kamau',
    subtitle: 'Nyeri County',
    icon: <PersonIcon />,
    statusBadge: <StatusBadge status="win" size="small" />,
    selected: true,
    onClick: fn(),
  },
};

/** Card with additional content */
export const WithChildren: Story = {
  args: {
    title: 'John Kamau',
    subtitle: 'Nyeri County',
    icon: <PersonIcon />,
    statusBadge: <StatusBadge status="win" size="small" />,
    metric: '92%',
    metricLabel: 'Primary',
    children: (
      <Box sx={{ mt: 1 }}>
        <TrendIndicator direction="up" value={5} period="vs last week" size="small" />
      </Box>
    ),
    onClick: fn(),
  },
};

/** Factory card variant */
export const FactoryCard: Story = {
  args: {
    title: 'Nyeri Tea Factory',
    subtitle: '12 collection points',
    icon: <FactoryIcon />,
    metric: '1,234',
    metricLabel: 'Farmers',
    onClick: fn(),
  },
};

/** Grid of cards */
export const CardGrid: Story = {
  render: () => (
    <Grid container spacing={2}>
      {[
        { id: '1', name: 'John Kamau', region: 'Nyeri', status: 'win' as const, metric: '92%' },
        { id: '2', name: 'Mary Wanjiku', region: 'Kiambu', status: 'watch' as const, metric: '78%' },
        { id: '3', name: 'Peter Mwangi', region: 'Meru', status: 'action' as const, metric: '65%' },
        { id: '4', name: 'Grace Nyambura', region: 'Nyeri', status: 'win' as const, metric: '88%' },
      ].map((farmer) => (
        <Grid key={farmer.id} item xs={12} sm={6} md={3}>
          <EntityCard
            title={farmer.name}
            subtitle={farmer.region}
            icon={<PersonIcon />}
            statusBadge={<StatusBadge status={farmer.status} size="small" />}
            metric={farmer.metric}
            metricLabel="Primary"
            onClick={() => console.log(`Clicked ${farmer.name}`)}
          />
        </Grid>
      ))}
    </Grid>
  ),
};

/** Region card variant */
export const RegionCard: Story = {
  args: {
    title: 'Nyeri - High Altitude',
    subtitle: 'Elevation: 1800-2200m',
    icon: <PublicIcon />,
    metric: '342',
    metricLabel: 'Farmers',
    onClick: fn(),
  },
};
