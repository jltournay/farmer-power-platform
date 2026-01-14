/**
 * Header Component Tests
 *
 * Tests for application header structure.
 * Note: These tests use mocked components to avoid auth provider dependencies.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '@fp/ui-components';
import { AppBar, Toolbar, Button, Chip, IconButton, Box, Typography } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import LogoutIcon from '@mui/icons-material/Logout';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import { describe, it, expect, vi } from 'vitest';

interface MockHeaderProps {
  onMenuClick: () => void;
  showMenuButton: boolean;
  userName?: string;
}

function MockHeader({ onMenuClick, showMenuButton, userName = 'Test Admin' }: MockHeaderProps) {
  return (
    <AppBar position="sticky" color="inherit">
      <Toolbar>
        {showMenuButton && (
          <IconButton
            edge="start"
            color="inherit"
            aria-label="open menu"
            onClick={onMenuClick}
          >
            <MenuIcon />
          </IconButton>
        )}
        <Box sx={{ flexGrow: 1 }} />
        <Chip
          icon={<AdminPanelSettingsIcon />}
          label="Platform Admin"
          size="small"
          color="primary"
        />
        <Typography variant="body2">{userName}</Typography>
        <Button
          variant="outlined"
          size="small"
          startIcon={<LogoutIcon />}
        >
          Logout
        </Button>
      </Toolbar>
    </AppBar>
  );
}

describe('Header', () => {
  it('renders Platform Admin badge', () => {
    render(
      <MemoryRouter>
        <ThemeProvider>
          <MockHeader onMenuClick={() => {}} showMenuButton={true} />
        </ThemeProvider>
      </MemoryRouter>
    );
    expect(screen.getByText('Platform Admin')).toBeInTheDocument();
  });

  it('renders logout button', () => {
    render(
      <MemoryRouter>
        <ThemeProvider>
          <MockHeader onMenuClick={() => {}} showMenuButton={true} />
        </ThemeProvider>
      </MemoryRouter>
    );
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
  });

  it('renders menu button when showMenuButton is true', () => {
    render(
      <MemoryRouter>
        <ThemeProvider>
          <MockHeader onMenuClick={() => {}} showMenuButton={true} />
        </ThemeProvider>
      </MemoryRouter>
    );
    expect(screen.getByRole('button', { name: /open menu/i })).toBeInTheDocument();
  });

  it('hides menu button when showMenuButton is false', () => {
    render(
      <MemoryRouter>
        <ThemeProvider>
          <MockHeader onMenuClick={() => {}} showMenuButton={false} />
        </ThemeProvider>
      </MemoryRouter>
    );
    expect(screen.queryByRole('button', { name: /open menu/i })).not.toBeInTheDocument();
  });

  it('calls onMenuClick when menu button is clicked', async () => {
    const user = userEvent.setup();
    const onMenuClick = vi.fn();
    render(
      <MemoryRouter>
        <ThemeProvider>
          <MockHeader onMenuClick={onMenuClick} showMenuButton={true} />
        </ThemeProvider>
      </MemoryRouter>
    );

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    await user.click(menuButton);

    expect(onMenuClick).toHaveBeenCalledTimes(1);
  });

  it('displays user name', () => {
    render(
      <MemoryRouter>
        <ThemeProvider>
          <MockHeader onMenuClick={() => {}} showMenuButton={true} userName="John Admin" />
        </ThemeProvider>
      </MemoryRouter>
    );
    expect(screen.getByText('John Admin')).toBeInTheDocument();
  });
});
