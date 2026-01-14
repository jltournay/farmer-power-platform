/**
 * Sidebar Component
 *
 * Navigation sidebar with role-based menu items.
 * Collapses to icons only on smaller screens.
 */

import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Divider,
  Typography,
  useTheme,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import BarChartIcon from '@mui/icons-material/BarChart';
import SettingsIcon from '@mui/icons-material/Settings';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { useAuth } from '@fp/auth';

/**
 * Menu item definition.
 */
interface MenuItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  roles: string[];
}

/**
 * Menu items with role-based visibility.
 */
const menuItems: MenuItem[] = [
  {
    label: 'Command Center',
    path: '/command-center',
    icon: <DashboardIcon />,
    roles: ['factory_manager', 'factory_owner', 'platform_admin'],
  },
  {
    label: 'ROI Summary',
    path: '/roi',
    icon: <BarChartIcon />,
    roles: ['factory_owner', 'platform_admin'],
  },
  {
    label: 'Settings',
    path: '/settings',
    icon: <SettingsIcon />,
    roles: ['factory_admin', 'platform_admin'],
  },
];

interface SidebarProps {
  open: boolean;
  width: number;
  collapsedWidth: number;
  onToggle: () => void;
}

/**
 * Sidebar navigation component.
 *
 * Features:
 * - Role-based menu item visibility
 * - Active route highlighting
 * - Collapsible to icons only
 * - Responsive drawer on mobile
 */
export function Sidebar({ open, width, collapsedWidth, onToggle }: SidebarProps): JSX.Element {
  const theme = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  const currentWidth = open ? width : collapsedWidth;

  // Filter menu items based on user role
  const visibleItems = menuItems.filter((item) => {
    if (!user) return false;
    // Platform admin sees all
    if (user.role === 'platform_admin') return true;
    return item.roles.includes(user.role);
  });

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: currentWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: currentWidth,
          boxSizing: 'border-box',
          backgroundColor: 'background.paper',
          borderRight: `1px solid ${theme.palette.divider}`,
          transition: theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          overflowX: 'hidden',
        },
      }}
    >
      {/* Logo/Brand area */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: open ? 'space-between' : 'center',
          p: 2,
          minHeight: 64,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            component="img"
            src="/logo.png"
            alt="Farmer Power"
            sx={{
              height: 32,
              width: 'auto',
            }}
          />
          {open && (
            <Typography
              variant="h6"
              sx={{
                color: 'primary.main',
                fontWeight: 700,
                whiteSpace: 'nowrap',
              }}
            >
              Farmer Power
            </Typography>
          )}
        </Box>
        <IconButton onClick={onToggle} size="small" aria-label={open ? 'Collapse sidebar' : 'Expand sidebar'}>
          {open ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </Box>

      <Divider />

      {/* Navigation items */}
      <List sx={{ px: 1, py: 2 }}>
        {visibleItems.map((item) => (
          <ListItem key={item.path} disablePadding sx={{ mb: 0.5 }}>
            <ListItemButton
              selected={isActive(item.path)}
              onClick={() => navigate(item.path)}
              sx={{
                borderRadius: 1,
                minHeight: 48,
                justifyContent: open ? 'initial' : 'center',
                px: 2.5,
                '&.Mui-selected': {
                  backgroundColor: 'primary.main',
                  color: 'primary.contrastText',
                  '&:hover': {
                    backgroundColor: 'primary.dark',
                  },
                  '& .MuiListItemIcon-root': {
                    color: 'primary.contrastText',
                  },
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: 0,
                  mr: open ? 2 : 'auto',
                  justifyContent: 'center',
                  color: isActive(item.path) ? 'inherit' : 'text.secondary',
                }}
              >
                {item.icon}
              </ListItemIcon>
              {open && <ListItemText primary={item.label} />}
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Drawer>
  );
}
