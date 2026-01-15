import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { Grid } from '@mui/material';
import { MetricCard } from './MetricCard';
import PeopleIcon from '@mui/icons-material/People';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';

const meta: Meta<typeof MetricCard> = {
  component: MetricCard,
  title: 'DataDisplay/MetricCard',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof MetricCard>;

/** Basic metric card */
export const Basic: Story = {
  args: {
    value: '342',
    label: 'Active Farmers',
  },
};

/** With icon */
export const WithIcon: Story = {
  args: {
    value: '342',
    label: 'Active Farmers',
    icon: <PeopleIcon />,
  },
};

/** With trend indicator */
export const WithTrend: Story = {
  args: {
    value: '342',
    label: 'Active Farmers',
    icon: <PeopleIcon />,
    trend: 'up',
    trendValue: 12,
    trendPeriod: 'vs last month',
  },
};

/** Negative trend */
export const NegativeTrend: Story = {
  args: {
    value: '$12,450',
    label: 'LLM Costs',
    icon: <AttachMoneyIcon />,
    trend: 'down',
    trendValue: 8,
    trendPeriod: 'vs last week',
    color: 'warning',
  },
};

/** Success color variant */
export const SuccessColor: Story = {
  args: {
    value: '92%',
    label: 'Win Rate',
    icon: <CheckCircleIcon />,
    trend: 'up',
    trendValue: 5,
    color: 'success',
  },
};

/** Warning color variant */
export const WarningColor: Story = {
  args: {
    value: '23',
    label: 'Farmers at Risk',
    icon: <WarningIcon />,
    trend: 'up',
    trendValue: 3,
    color: 'warning',
  },
};

/** Error color variant */
export const ErrorColor: Story = {
  args: {
    value: '7',
    label: 'Critical Issues',
    icon: <WarningIcon />,
    trend: 'stable',
    trendValue: 0,
    color: 'error',
  },
};

/** Clickable metric card */
export const Clickable: Story = {
  args: {
    value: '342',
    label: 'Active Farmers',
    icon: <PeopleIcon />,
    trend: 'up',
    trendValue: 12,
    trendPeriod: 'vs last month',
    onClick: fn(),
  },
};

/** Dashboard layout with multiple metrics */
export const DashboardGrid: Story = {
  render: () => (
    <Grid container spacing={2}>
      <Grid item xs={12} sm={6} md={3}>
        <MetricCard
          value="342"
          label="Active Farmers"
          icon={<PeopleIcon />}
          trend="up"
          trendValue={12}
          trendPeriod="vs last month"
          color="primary"
        />
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <MetricCard
          value="92%"
          label="Win Rate"
          icon={<CheckCircleIcon />}
          trend="up"
          trendValue={5}
          color="success"
        />
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <MetricCard
          value="23"
          label="At Risk"
          icon={<WarningIcon />}
          trend="down"
          trendValue={8}
          color="warning"
        />
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <MetricCard
          value="$1,234"
          label="Monthly Cost"
          icon={<AttachMoneyIcon />}
          trend="up"
          trendValue={15}
        />
      </Grid>
    </Grid>
  ),
};

/** Large value formatting */
export const LargeValues: Story = {
  render: () => (
    <Grid container spacing={2}>
      <Grid item xs={12} sm={6} md={3}>
        <MetricCard
          value="1,234,567"
          label="Total Events"
          icon={<TrendingUpIcon />}
        />
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <MetricCard
          value="$2.5M"
          label="Revenue"
          icon={<AttachMoneyIcon />}
          color="success"
        />
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <MetricCard
          value="99.9%"
          label="Uptime"
          icon={<CheckCircleIcon />}
          color="success"
        />
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <MetricCard
          value="<1s"
          label="Avg Response"
          icon={<TrendingUpIcon />}
        />
      </Grid>
    </Grid>
  ),
};
