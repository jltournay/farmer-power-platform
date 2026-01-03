import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LeafTypeTag, ThemeProvider } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('LeafTypeTag', () => {
  describe('rendering', () => {
    it('renders three_plus_leaves_bud in English', () => {
      renderWithTheme(<LeafTypeTag leafType="three_plus_leaves_bud" />);

      expect(screen.getByText('3+ leaves')).toBeInTheDocument();
    });

    it('renders coarse_leaf in English', () => {
      renderWithTheme(<LeafTypeTag leafType="coarse_leaf" />);

      expect(screen.getByText('coarse leaf')).toBeInTheDocument();
    });

    it('renders hard_banji in English', () => {
      renderWithTheme(<LeafTypeTag leafType="hard_banji" />);

      expect(screen.getByText('hard banji')).toBeInTheDocument();
    });

    it('renders three_plus_leaves_bud in Swahili', () => {
      renderWithTheme(
        <LeafTypeTag leafType="three_plus_leaves_bud" language="sw" />
      );

      expect(screen.getByText('majani 3+')).toBeInTheDocument();
    });

    it('renders coarse_leaf in Swahili', () => {
      renderWithTheme(<LeafTypeTag leafType="coarse_leaf" language="sw" />);

      expect(screen.getByText('majani magumu')).toBeInTheDocument();
    });

    it('renders hard_banji in Swahili', () => {
      renderWithTheme(<LeafTypeTag leafType="hard_banji" language="sw" />);

      expect(screen.getByText('banji ngumu')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has aria-label with label and coaching tip', () => {
      renderWithTheme(<LeafTypeTag leafType="three_plus_leaves_bud" />);

      const tag = screen.getByText('3+ leaves').closest('div');
      expect(tag).toHaveAttribute(
        'aria-label',
        '3+ leaves: Pick only 2 leaves + bud for best quality'
      );
    });

    it('has role="button" when clickable', () => {
      renderWithTheme(
        <LeafTypeTag leafType="coarse_leaf" onClick={() => {}} />
      );

      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('does not have role="button" when not clickable', () => {
      renderWithTheme(<LeafTypeTag leafType="coarse_leaf" />);

      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    it('is focusable when clickable', () => {
      renderWithTheme(
        <LeafTypeTag leafType="hard_banji" onClick={() => {}} />
      );

      const tag = screen.getByRole('button');
      expect(tag).toHaveAttribute('tabIndex', '0');
    });

    it('is focusable when showTooltip is true', () => {
      renderWithTheme(<LeafTypeTag leafType="hard_banji" showTooltip />);

      const tag = screen.getByText('hard banji').closest('div');
      expect(tag).toHaveAttribute('tabIndex', '0');
    });
  });

  describe('tooltip', () => {
    it('shows tooltip on hover', async () => {
      const user = userEvent.setup();
      renderWithTheme(<LeafTypeTag leafType="three_plus_leaves_bud" />);

      const tag = screen.getByText('3+ leaves');
      await user.hover(tag);

      await waitFor(() => {
        expect(
          screen.getByText('Pick only 2 leaves + bud for best quality')
        ).toBeInTheDocument();
      });
    });

    it('shows tooltip on focus', async () => {
      const user = userEvent.setup();
      renderWithTheme(<LeafTypeTag leafType="coarse_leaf" />);

      const tag = screen.getByText('coarse leaf').closest('div')!;
      await user.click(tag); // Focus via click
      tag.focus();

      await waitFor(() => {
        expect(
          screen.getByText('Avoid old/mature leaves - pick young leaves')
        ).toBeInTheDocument();
      });
    });

    it('does not show tooltip when showTooltip is false', async () => {
      const user = userEvent.setup();
      renderWithTheme(
        <LeafTypeTag leafType="hard_banji" showTooltip={false} />
      );

      const tag = screen.getByText('hard banji');
      await user.hover(tag);

      // Wait a bit for any tooltip to appear
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(
        screen.queryByText('Harvest earlier in morning for softer stems')
      ).not.toBeInTheDocument();
    });

    it('shows Swahili coaching tip when language is sw', async () => {
      const user = userEvent.setup();
      renderWithTheme(
        <LeafTypeTag leafType="three_plus_leaves_bud" language="sw" />
      );

      const tag = screen.getByText('majani 3+');
      await user.hover(tag);

      await waitFor(() => {
        expect(
          screen.getByText('Chuma majani 2 na chipukizi tu kwa ubora bora')
        ).toBeInTheDocument();
      });
    });
  });

  describe('interaction', () => {
    it('calls onClick when clicked', async () => {
      const onClick = vi.fn();
      const user = userEvent.setup();

      renderWithTheme(
        <LeafTypeTag leafType="three_plus_leaves_bud" onClick={onClick} />
      );

      await user.click(screen.getByRole('button'));

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('calls onClick when Enter key is pressed', async () => {
      const onClick = vi.fn();
      const user = userEvent.setup();

      renderWithTheme(
        <LeafTypeTag leafType="coarse_leaf" onClick={onClick} />
      );

      const tag = screen.getByRole('button');
      tag.focus();
      await user.keyboard('{Enter}');

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('calls onClick when Space key is pressed', async () => {
      const onClick = vi.fn();
      const user = userEvent.setup();

      renderWithTheme(<LeafTypeTag leafType="hard_banji" onClick={onClick} />);

      const tag = screen.getByRole('button');
      tag.focus();
      await user.keyboard(' ');

      expect(onClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('coaching tips content', () => {
    it('has correct coaching tip for three_plus_leaves_bud in English', () => {
      renderWithTheme(<LeafTypeTag leafType="three_plus_leaves_bud" />);

      const tag = screen.getByText('3+ leaves').closest('div');
      expect(tag?.getAttribute('aria-label')).toContain(
        'Pick only 2 leaves + bud'
      );
    });

    it('has correct coaching tip for coarse_leaf in English', () => {
      renderWithTheme(<LeafTypeTag leafType="coarse_leaf" />);

      const tag = screen.getByText('coarse leaf').closest('div');
      expect(tag?.getAttribute('aria-label')).toContain(
        'Avoid old/mature leaves'
      );
    });

    it('has correct coaching tip for hard_banji in English', () => {
      renderWithTheme(<LeafTypeTag leafType="hard_banji" />);

      const tag = screen.getByText('hard banji').closest('div');
      expect(tag?.getAttribute('aria-label')).toContain(
        'Harvest earlier in morning'
      );
    });
  });
});
