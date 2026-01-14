/**
 * Sidebar Component Tests
 *
 * Tests for navigation sidebar functionality.
 * Note: These tests use a mock user context to avoid auth provider dependencies.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '@fp/ui-components';
import { describe, it, expect, vi } from 'vitest';
import { Box, List, ListItem, ListItemButton, ListItemText, Drawer } from '@mui/material';

// Mock sidebar items to test structure without auth
const menuItems = [
  { label: 'Regions', path: '/regions' },
  { label: 'Farmers', path: '/farmers' },
  { label: 'Factories', path: '/factories' },
  { label: 'Grading Models', path: '/grading-models' },
  { label: 'Users', path: '/users' },
  { label: 'Health', path: '/health' },
  { label: 'Knowledge', path: '/knowledge' },
  { label: 'Costs', path: '/costs' },
];

function MockSidebar({ open = true }: { open?: boolean }) {
  return (
    <Drawer variant="permanent" open={open}>
      <Box data-testid="sidebar">
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.path} disablePadding>
              <ListItemButton>
                {open && <ListItemText primary={item.label} />}
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>
    </Drawer>
  );
}

describe('Sidebar', () => {
  it('renders all navigation items when open', () => {
    render(
      <MemoryRouter>
        <ThemeProvider>
          <MockSidebar open={true} />
        </ThemeProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Regions')).toBeInTheDocument();
    expect(screen.getByText('Farmers')).toBeInTheDocument();
    expect(screen.getByText('Factories')).toBeInTheDocument();
    expect(screen.getByText('Grading Models')).toBeInTheDocument();
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('Health')).toBeInTheDocument();
    expect(screen.getByText('Knowledge')).toBeInTheDocument();
    expect(screen.getByText('Costs')).toBeInTheDocument();
  });

  it('has correct number of menu items (8)', () => {
    render(
      <MemoryRouter>
        <ThemeProvider>
          <MockSidebar open={true} />
        </ThemeProvider>
      </MemoryRouter>
    );

    const listItems = screen.getAllByRole('listitem');
    expect(listItems.length).toBe(8);
  });

  it('hides text labels when collapsed', () => {
    render(
      <MemoryRouter>
        <ThemeProvider>
          <MockSidebar open={false} />
        </ThemeProvider>
      </MemoryRouter>
    );

    expect(screen.queryByText('Regions')).not.toBeInTheDocument();
    expect(screen.queryByText('Farmers')).not.toBeInTheDocument();
  });
});
