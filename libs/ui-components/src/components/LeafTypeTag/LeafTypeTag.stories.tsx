import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { LeafTypeTag } from './LeafTypeTag';

const meta: Meta<typeof LeafTypeTag> = {
  component: LeafTypeTag,
  title: 'Components/LeafTypeTag',
  tags: ['autodocs'],
  argTypes: {
    leafType: {
      control: 'select',
      options: ['three_plus_leaves_bud', 'coarse_leaf', 'hard_banji'],
      description: 'Leaf type from TBK grading model',
    },
    language: {
      control: 'select',
      options: ['en', 'sw'],
      description: 'Display language',
    },
    showTooltip: {
      control: 'boolean',
      description: 'Show coaching tooltip',
    },
    onClick: {
      action: 'clicked',
      description: 'Click handler (opens coaching card)',
    },
  },
  args: {
    onClick: undefined,
    showTooltip: true,
    language: 'en',
  },
};

export default meta;
type Story = StoryObj<typeof LeafTypeTag>;

/** Three or more leaves with bud - rejection category */
export const ThreePlusLeavesBud: Story = {
  args: {
    leafType: 'three_plus_leaves_bud',
  },
};

/** Coarse leaf - rejection category */
export const CoarseLeaf: Story = {
  args: {
    leafType: 'coarse_leaf',
  },
};

/** Hard banji - conditional rejection */
export const HardBanji: Story = {
  args: {
    leafType: 'hard_banji',
  },
};

/** Swahili language */
export const SwahiliLanguage: Story = {
  args: {
    leafType: 'three_plus_leaves_bud',
    language: 'sw',
  },
};

/** Without tooltip */
export const WithoutTooltip: Story = {
  args: {
    leafType: 'coarse_leaf',
    showTooltip: false,
  },
};

/** Clickable tag */
export const Clickable: Story = {
  args: {
    leafType: 'hard_banji',
    onClick: fn(),
  },
};

/** All leaf types - English */
export const AllTypesEnglish: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
      <LeafTypeTag leafType="three_plus_leaves_bud" language="en" />
      <LeafTypeTag leafType="coarse_leaf" language="en" />
      <LeafTypeTag leafType="hard_banji" language="en" />
    </div>
  ),
};

/** All leaf types - Swahili */
export const AllTypesSwahili: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
      <LeafTypeTag leafType="three_plus_leaves_bud" language="sw" />
      <LeafTypeTag leafType="coarse_leaf" language="sw" />
      <LeafTypeTag leafType="hard_banji" language="sw" />
    </div>
  ),
};

/** Language comparison */
export const LanguageComparison: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <span style={{ width: '80px', fontSize: '0.875rem' }}>English:</span>
        <LeafTypeTag leafType="three_plus_leaves_bud" language="en" />
        <LeafTypeTag leafType="coarse_leaf" language="en" />
        <LeafTypeTag leafType="hard_banji" language="en" />
      </div>
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <span style={{ width: '80px', fontSize: '0.875rem' }}>Swahili:</span>
        <LeafTypeTag leafType="three_plus_leaves_bud" language="sw" />
        <LeafTypeTag leafType="coarse_leaf" language="sw" />
        <LeafTypeTag leafType="hard_banji" language="sw" />
      </div>
    </div>
  ),
};
