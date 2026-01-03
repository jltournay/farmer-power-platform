import type { Meta, StoryObj } from '@storybook/react';
import { TrendIndicator } from './TrendIndicator';

const meta: Meta<typeof TrendIndicator> = {
  component: TrendIndicator,
  title: 'Components/TrendIndicator',
  tags: ['autodocs'],
  argTypes: {
    direction: {
      control: 'select',
      options: ['up', 'down', 'stable'],
      description: 'Trend direction',
    },
    value: {
      control: 'number',
      description: 'Percentage change value',
    },
    period: {
      control: 'text',
      description: 'Optional period description',
    },
    size: {
      control: 'select',
      options: ['small', 'medium'],
      description: 'Size variant',
    },
  },
};

export default meta;
type Story = StoryObj<typeof TrendIndicator>;

/** Upward trend - positive change */
export const Up: Story = {
  args: {
    direction: 'up',
    value: 12,
  },
};

/** Downward trend - negative change */
export const Down: Story = {
  args: {
    direction: 'down',
    value: 5,
  },
};

/** Stable trend - no change */
export const Stable: Story = {
  args: {
    direction: 'stable',
    value: 0,
  },
};

/** With period description */
export const WithPeriod: Story = {
  args: {
    direction: 'up',
    value: 8,
    period: 'vs last week',
  },
};

/** Small size variant */
export const SmallSize: Story = {
  args: {
    direction: 'up',
    value: 15,
    size: 'small',
  },
};

/** All variants together */
export const AllVariants: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
      <TrendIndicator direction="up" value={12} />
      <TrendIndicator direction="down" value={5} />
      <TrendIndicator direction="stable" value={0} />
    </div>
  ),
};

/** With periods */
export const WithPeriods: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <TrendIndicator direction="up" value={12} period="vs last week" />
      <TrendIndicator direction="down" value={3} period="since launch" />
      <TrendIndicator direction="stable" value={0} period="this month" />
    </div>
  ),
};

/** Size comparison */
export const SizeComparison: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
      <TrendIndicator direction="up" value={8} size="small" />
      <TrendIndicator direction="up" value={8} size="medium" />
    </div>
  ),
};
