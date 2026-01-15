import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Sidebar, ThemeProvider } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

// Simple icon mock
const MockIcon = () => <span data-testid="mock-icon">Icon</span>;

const sampleItems = [
  { id: 'home', label: 'Home', icon: <MockIcon />, href: '/' },
  { id: 'farmers', label: 'Farmers', icon: <MockIcon />, href: '/farmers' },
];

describe('Sidebar', () => {
  describe('rendering', () => {
    it('renders all menu items', () => {
      renderWithTheme(<Sidebar items={sampleItems} />);

      expect(screen.getByText('Home')).toBeInTheDocument();
      expect(screen.getByText('Farmers')).toBeInTheDocument();
    });

    it('renders brand name when provided', () => {
      renderWithTheme(
        <Sidebar items={sampleItems} brandName="Farmer Power" />
      );

      expect(screen.getByText('Farmer Power')).toBeInTheDocument();
    });

    it('hides brand name when collapsed', () => {
      renderWithTheme(
        <Sidebar items={sampleItems} brandName="Farmer Power" collapsed={true} />
      );

      expect(screen.queryByText('Farmer Power')).not.toBeInTheDocument();
    });

    it('highlights active item', () => {
      renderWithTheme(<Sidebar items={sampleItems} activeItem="home" />);

      // ListItemButton gets Mui-selected class when active
      const homeItem = screen.getByText('Home').closest('.MuiListItemButton-root');
      expect(homeItem).toHaveClass('Mui-selected');
    });
  });

  describe('interactions', () => {
    it('calls onItemClick when item is clicked', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      renderWithTheme(
        <Sidebar items={sampleItems} onItemClick={handleClick} />
      );

      await user.click(screen.getByText('Home'));

      expect(handleClick).toHaveBeenCalledWith(sampleItems[0]);
    });

    it('calls onCollapse when toggle button is clicked', async () => {
      const user = userEvent.setup();
      const handleCollapse = vi.fn();

      renderWithTheme(
        <Sidebar items={sampleItems} collapsed={false} onCollapse={handleCollapse} />
      );

      await user.click(screen.getByLabelText('Collapse sidebar'));

      expect(handleCollapse).toHaveBeenCalledWith(true);
    });
  });

  describe('accessibility', () => {
    it('has aria-label on menu items', () => {
      renderWithTheme(<Sidebar items={sampleItems} />);

      // ListItemButton has aria-label for accessibility
      expect(screen.getByLabelText('Home')).toBeInTheDocument();
      expect(screen.getByLabelText('Farmers')).toBeInTheDocument();
    });

    it('has aria-label on collapse button', () => {
      renderWithTheme(<Sidebar items={sampleItems} collapsed={false} />);

      expect(screen.getByLabelText('Collapse sidebar')).toBeInTheDocument();
    });
  });
});
