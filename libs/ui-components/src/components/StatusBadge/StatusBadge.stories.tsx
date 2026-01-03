import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { StatusBadge } from './StatusBadge';

const meta: Meta<typeof StatusBadge> = {
  component: StatusBadge,
  title: 'Components/StatusBadge',
  tags: ['autodocs'],
  argTypes: {
    status: {
      control: 'select',
      options: ['win', 'watch', 'action'],
      description: 'Status variant',
    },
    label: {
      control: 'text',
      description: 'Custom label override',
    },
    count: {
      control: 'number',
      description: 'Optional count display',
    },
    size: {
      control: 'select',
      options: ['small', 'medium', 'large'],
      description: 'Size variant',
    },
    onClick: {
      action: 'clicked',
      description: 'Click handler for interactive badges',
    },
  },
  args: {
    onClick: undefined,
  },
};

export default meta;
type Story = StoryObj<typeof StatusBadge>;

/** WIN status - Quality >= 85% */
export const Win: Story = {
  args: {
    status: 'win',
  },
};

/** WATCH status - Quality 70-84% */
export const Watch: Story = {
  args: {
    status: 'watch',
  },
};

/** ACTION NEEDED status - Quality < 70% */
export const ActionNeeded: Story = {
  args: {
    status: 'action',
  },
};

/** Badge with count for action strips */
export const WithCount: Story = {
  args: {
    status: 'action',
    count: 7,
  },
};

/** Custom label override */
export const CustomLabel: Story = {
  args: {
    status: 'win',
    label: 'Excellent',
  },
};

/** Small size variant */
export const SmallSize: Story = {
  args: {
    status: 'win',
    size: 'small',
  },
};

/** Large size variant */
export const LargeSize: Story = {
  args: {
    status: 'action',
    size: 'large',
  },
};

/** Clickable badge */
export const Clickable: Story = {
  args: {
    status: 'action',
    count: 12,
    onClick: fn(),
  },
};

/** All variants together */
export const AllVariants: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
      <StatusBadge status="win" />
      <StatusBadge status="watch" />
      <StatusBadge status="action" />
      <StatusBadge status="action" count={5} />
    </div>
  ),
};

/** Size comparison */
export const SizeComparison: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
      <StatusBadge status="win" size="small" />
      <StatusBadge status="win" size="medium" />
      <StatusBadge status="win" size="large" />
    </div>
  ),
};
