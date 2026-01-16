/**
 * Sidebar Component
 *
 * Navigation sidebar with role-based menu items for Platform Admin.
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
  Tooltip,
  useTheme,
} from '@mui/material';
import PublicIcon from '@mui/icons-material/Public';
import AgricultureIcon from '@mui/icons-material/Agriculture';
import FactoryIcon from '@mui/icons-material/Factory';
import GradingIcon from '@mui/icons-material/Grading';
import PeopleIcon from '@mui/icons-material/People';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
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
  dividerAfter?: boolean;
}

/**
 * Menu items with role-based visibility.
 * Platform Admin navigation structure per AC 9.1.4
 */
const menuItems: MenuItem[] = [
  {
    label: 'Regions',
    path: '/regions',
    icon: <PublicIcon />,
    roles: ['platform_admin'],
  },
  {
    label: 'Farmers',
    path: '/farmers',
    icon: <AgricultureIcon />,
    roles: ['platform_admin'],
  },
  {
    label: 'Factories',
    path: '/factories',
    icon: <FactoryIcon />,
    roles: ['platform_admin'],
    dividerAfter: true,
  },
  {
    label: 'Grading Models',
    path: '/grading-models',
    icon: <GradingIcon />,
    roles: ['platform_admin'],
  },
  {
    label: 'Users',
    path: '/users',
    icon: <PeopleIcon />,
    roles: ['platform_admin'],
    dividerAfter: true,
  },
  {
    label: 'Health',
    path: '/health',
    icon: <MonitorHeartIcon />,
    roles: ['platform_admin'],
  },
  {
    label: 'Knowledge',
    path: '/knowledge',
    icon: <MenuBookIcon />,
    roles: ['platform_admin'],
  },
  {
    label: 'Costs',
    path: '/costs',
    icon: <AttachMoneyIcon />,
    roles: ['platform_admin'],
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
 * - Dividers between logical groups
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
            src={`${import.meta.env.VITE_BASE_URL || '/'}logo.png`}
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
        {visibleItems.map((item, index) => (
          <Box key={item.path}>
            <ListItem disablePadding sx={{ mb: 0.5 }}>
              <Tooltip title={open ? '' : item.label} placement="right" arrow>
                <ListItemButton
                  selected={isActive(item.path)}
                  onClick={() => navigate(item.path)}
                  aria-label={item.label}
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
              </Tooltip>
            </ListItem>
            {item.dividerAfter && index < visibleItems.length - 1 && (
              <Divider sx={{ my: 1 }} />
            )}
          </Box>
        ))}
      </List>
    </Drawer>
  );
}
