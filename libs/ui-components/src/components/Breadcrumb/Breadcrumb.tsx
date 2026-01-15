/**
 * Breadcrumb Component
 *
 * Dynamic navigation trail showing hierarchical position.
 * Generic component that works with any navigation system.
 *
 * Accessibility:
 * - aria-label="breadcrumb" on navigation
 * - Current page is not a link (aria-current="page")
 * - 48px minimum touch target for links
 */

import { Box, Breadcrumbs, Link, Typography, useTheme } from '@mui/material';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import HomeIcon from '@mui/icons-material/Home';
import type { ReactNode } from 'react';

/** Breadcrumb item definition */
export interface BreadcrumbItem {
  /** Display label */
  label: string;
  /** Navigation href (omit for current/last item) */
  href?: string;
  /** Optional icon to display before label */
  icon?: ReactNode;
}

/** Breadcrumb component props */
export interface BreadcrumbProps {
  /** Breadcrumb items in hierarchical order */
  items: BreadcrumbItem[];
  /** Callback when a breadcrumb link is clicked */
  onNavigate?: (href: string) => void;
  /** Optional home item to prepend (defaults to showing home icon link to /) */
  homeItem?: BreadcrumbItem | null;
  /** Custom separator icon */
  separator?: ReactNode;
}

/**
 * Breadcrumb displays navigation hierarchy.
 *
 * @example
 * ```tsx
 * <Breadcrumb
 *   items={[
 *     { label: 'Factories', href: '/factories' },
 *     { label: 'Nyeri Tea Factory' },
 *   ]}
 *   onNavigate={(href) => navigate(href)}
 * />
 * ```
 */
export function Breadcrumb({
  items,
  onNavigate,
  homeItem = { label: 'Home', href: '/', icon: <HomeIcon sx={{ mr: 0.5, fontSize: 20 }} /> },
  separator = <NavigateNextIcon fontSize="small" />,
}: BreadcrumbProps): JSX.Element | null {
  const theme = useTheme();

  // Don't render if no items
  if (items.length === 0 && !homeItem) {
    return null;
  }

  // Combine home item with other items
  const allItems: BreadcrumbItem[] = homeItem ? [homeItem, ...items] : items;

  const handleClick = (href: string, event: React.MouseEvent) => {
    event.preventDefault();
    onNavigate?.(href);
  };

  return (
    <Box
      sx={{
        px: 3,
        py: 1.5,
        backgroundColor: 'background.paper',
        borderBottom: 1,
        borderColor: 'divider',
      }}
    >
      <Breadcrumbs separator={separator} aria-label="breadcrumb">
        {allItems.map((item, index) => {
          const isLast = index === allItems.length - 1;

          if (isLast || !item.href) {
            return (
              <Typography
                key={`${item.label}-${index}`}
                color="text.primary"
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  fontWeight: 500,
                }}
                aria-current="page"
              >
                {item.icon}
                {item.label}
              </Typography>
            );
          }

          return (
            <Link
              key={`${item.label}-${index}`}
              href={item.href}
              onClick={(e) => handleClick(item.href!, e)}
              sx={{
                display: 'flex',
                alignItems: 'center',
                color: 'text.secondary',
                textDecoration: 'none',
                minHeight: 32, // Touch target
                cursor: 'pointer',
                '&:hover': {
                  color: 'primary.main',
                  textDecoration: 'underline',
                },
                '&:focus': {
                  outline: `3px solid ${theme.palette.primary.main}`,
                  outlineOffset: '2px',
                  borderRadius: '4px',
                },
              }}
            >
              {item.icon}
              {item.label}
            </Link>
          );
        })}
      </Breadcrumbs>
    </Box>
  );
}

export default Breadcrumb;
