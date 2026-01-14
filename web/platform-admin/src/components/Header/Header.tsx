/**
 * Header Component
 *
 * Application header with user info and logout functionality.
 * Shows "Platform Admin" badge instead of factory name.
 */

import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Button,
  Chip,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import LogoutIcon from '@mui/icons-material/Logout';
import PersonIcon from '@mui/icons-material/Person';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import { useAuth } from '@fp/auth';

interface HeaderProps {
  onMenuClick: () => void;
  showMenuButton: boolean;
}

/**
 * Application header component.
 *
 * Displays:
 * - Menu toggle button (on mobile/collapsed)
 * - User name and "Platform Admin" badge
 * - Logout button
 */
export function Header({ onMenuClick, showMenuButton }: HeaderProps): JSX.Element {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  return (
    <AppBar
      position="sticky"
      color="inherit"
      elevation={1}
      sx={{
        backgroundColor: 'background.paper',
        borderBottom: 1,
        borderColor: 'divider',
      }}
    >
      <Toolbar>
        {/* Menu toggle button */}
        {showMenuButton && (
          <IconButton
            edge="start"
            color="inherit"
            aria-label="open menu"
            onClick={onMenuClick}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
        )}

        {/* Spacer */}
        <Box sx={{ flexGrow: 1 }} />

        {/* User info */}
        {user && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {/* Platform Admin badge */}
            <Chip
              icon={<AdminPanelSettingsIcon />}
              label="Platform Admin"
              size="small"
              color="primary"
              sx={{ display: { xs: 'none', sm: 'flex' } }}
            />

            {/* User info */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <PersonIcon sx={{ color: 'text.secondary', fontSize: 20 }} />
              <Typography
                variant="body2"
                sx={{
                  fontWeight: 500,
                  display: { xs: 'none', sm: 'block' },
                }}
              >
                {user.name}
              </Typography>
            </Box>

            {/* Logout button */}
            <Button
              variant="outlined"
              size="small"
              startIcon={<LogoutIcon />}
              onClick={handleLogout}
              sx={{ ml: 1 }}
            >
              Logout
            </Button>
          </Box>
        )}
      </Toolbar>
    </AppBar>
  );
}
