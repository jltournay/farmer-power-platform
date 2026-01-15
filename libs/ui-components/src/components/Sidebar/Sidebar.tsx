/**
 * Sidebar Component
 *
 * Collapsible navigation sidebar with grouped menu items and icons.
 * Generic component that can be used by any admin application.
 *
 * Accessibility:
 * - aria-label on toggle button
 * - Tooltip on collapsed items for screen readers
 * - 48px minimum touch target for items
 * - Focus ring: 3px Forest Green outline
 */

import { styled } from '@mui/material/styles';
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
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import type { ReactNode } from 'react';

/** Sidebar menu item definition */
export interface SidebarItem {
  /** Unique identifier for the item */
  id: string;
  /** Display label */
  label: string;
  /** Icon to display (React node) */
  icon: ReactNode;
  /** Navigation href or path */
  href: string;
  /** Optional group name for dividers between groups */
  group?: string;
}

/** Sidebar component props */
export interface SidebarProps {
  /** Menu items to display */
  items: SidebarItem[];
  /** Whether sidebar is collapsed (icons only) */
  collapsed?: boolean;
  /** Callback when collapse state changes */
  onCollapse?: (collapsed: boolean) => void;
  /** Currently active item ID */
  activeItem?: string;
  /** Callback when an item is clicked */
  onItemClick?: (item: SidebarItem) => void;
  /** Optional brand logo element */
  brandLogo?: ReactNode;
  /** Optional brand name text */
  brandName?: string;
  /** Width when expanded (default: 240) */
  width?: number;
  /** Width when collapsed (default: 64) */
  collapsedWidth?: number;
}

const StyledDrawer = styled(Drawer, {
  shouldForwardProp: (prop) => prop !== 'currentWidth',
})<{ currentWidth: number }>(({ theme, currentWidth }) => ({
  width: currentWidth,
  flexShrink: 0,
  '& .MuiDrawer-paper': {
    width: currentWidth,
    boxSizing: 'border-box',
    backgroundColor: theme.palette.background.paper,
    borderRight: `1px solid ${theme.palette.divider}`,
    transition: theme.transitions.create('width', {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
    overflowX: 'hidden',
  },
}));

/**
 * Sidebar provides collapsible navigation for admin applications.
 *
 * @example
 * ```tsx
 * <Sidebar
 *   items={[
 *     { id: 'home', label: 'Home', icon: <HomeIcon />, href: '/' },
 *     { id: 'farmers', label: 'Farmers', icon: <PeopleIcon />, href: '/farmers' },
 *   ]}
 *   activeItem="farmers"
 *   collapsed={false}
 *   onCollapse={(c) => setCollapsed(c)}
 *   onItemClick={(item) => navigate(item.href)}
 * />
 * ```
 */
export function Sidebar({
  items,
  collapsed = false,
  onCollapse,
  activeItem,
  onItemClick,
  brandLogo,
  brandName,
  width = 240,
  collapsedWidth = 64,
}: SidebarProps): JSX.Element {
  const theme = useTheme();
  const currentWidth = collapsed ? collapsedWidth : width;
  const open = !collapsed;

  const handleToggle = () => {
    onCollapse?.(!collapsed);
  };

  const handleItemClick = (item: SidebarItem) => {
    onItemClick?.(item);
  };

  // Group items by their group property
  const groupedItems: Array<{ group: string | null; items: SidebarItem[] }> = [];
  let currentGroup: string | null | undefined = undefined; // Use undefined as sentinel to distinguish from null group

  items.forEach((item) => {
    const itemGroup = item.group ?? null;
    if (itemGroup !== currentGroup) {
      groupedItems.push({ group: itemGroup, items: [item] });
      currentGroup = itemGroup;
    } else {
      const lastGroup = groupedItems[groupedItems.length - 1];
      if (lastGroup) {
        lastGroup.items.push(item);
      }
    }
  });

  return (
    <StyledDrawer variant="permanent" currentWidth={currentWidth}>
      {/* Brand area */}
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
          {brandLogo}
          {open && brandName && (
            <Typography
              variant="h6"
              sx={{
                color: 'primary.main',
                fontWeight: 700,
                whiteSpace: 'nowrap',
              }}
            >
              {brandName}
            </Typography>
          )}
        </Box>
        <IconButton
          onClick={handleToggle}
          size="small"
          aria-label={open ? 'Collapse sidebar' : 'Expand sidebar'}
          sx={{
            '&:focus': {
              outline: `3px solid ${theme.palette.primary.main}`,
              outlineOffset: '2px',
            },
          }}
        >
          {open ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </Box>

      <Divider />

      {/* Navigation items */}
      <List sx={{ px: 1, py: 2 }}>
        {groupedItems.map((group, groupIndex) => (
          <Box key={group.group ?? `group-${groupIndex}`}>
            {group.items.map((item) => (
              <ListItem key={item.id} disablePadding sx={{ mb: 0.5 }}>
                <Tooltip title={open ? '' : item.label} placement="right" arrow>
                  <ListItemButton
                    selected={activeItem === item.id}
                    onClick={() => handleItemClick(item)}
                    aria-label={item.label}
                    sx={{
                      borderRadius: 1,
                      minHeight: 48,
                      justifyContent: open ? 'initial' : 'center',
                      px: 2.5,
                      '&:focus': {
                        outline: `3px solid ${theme.palette.primary.main}`,
                        outlineOffset: '-3px',
                      },
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
                        color: activeItem === item.id ? 'inherit' : 'text.secondary',
                      }}
                    >
                      {item.icon}
                    </ListItemIcon>
                    {open && <ListItemText primary={item.label} />}
                  </ListItemButton>
                </Tooltip>
              </ListItem>
            ))}
            {groupIndex < groupedItems.length - 1 && <Divider sx={{ my: 1 }} />}
          </Box>
        ))}
      </List>
    </StyledDrawer>
  );
}

export default Sidebar;
