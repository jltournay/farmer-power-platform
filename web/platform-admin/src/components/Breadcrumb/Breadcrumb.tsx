/**
 * Breadcrumb Component
 *
 * Dynamic breadcrumb navigation that builds trail from current URL path.
 * Shows hierarchical position within the admin portal.
 */

import { useLocation, Link as RouterLink } from 'react-router-dom';
import { Breadcrumbs, Link, Typography, Box } from '@mui/material';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import HomeIcon from '@mui/icons-material/Home';

/**
 * Route label mapping for human-readable breadcrumb text.
 */
const routeLabels: Record<string, string> = {
  dashboard: 'Dashboard',
  regions: 'Regions',
  farmers: 'Farmers',
  factories: 'Factories',
  'collection-points': 'Collection Points',
  'grading-models': 'Grading Models',
  users: 'Users',
  health: 'Platform Health',
  knowledge: 'Knowledge Library',
  costs: 'Cost Dashboard',
};

/**
 * Get human-readable label for a path segment.
 * Falls back to capitalized segment if no label exists.
 */
function getLabel(segment: string): string {
  // Check if it's a known route
  if (routeLabels[segment]) {
    return routeLabels[segment];
  }

  // If it looks like an ID (contains numbers or hyphens with numbers), return as-is
  if (/\d/.test(segment)) {
    return segment;
  }

  // Capitalize first letter and replace hyphens with spaces
  return segment
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Breadcrumb navigation component.
 *
 * Features:
 * - Automatically builds breadcrumb trail from URL path
 * - Home icon links to dashboard
 * - Current page is not a link (text only)
 * - Intermediate segments are clickable links
 */
export function Breadcrumb(): JSX.Element {
  const location = useLocation();

  // Split path into segments, filtering out empty strings
  const pathSegments = location.pathname.split('/').filter(Boolean);

  // Don't show breadcrumb on dashboard (home page)
  if (pathSegments.length === 0 || (pathSegments.length === 1 && pathSegments[0] === 'dashboard')) {
    return <Box sx={{ height: 8 }} />; // Small spacer for consistent layout
  }

  // Path segments that are not navigable (no standalone page exists)
  const skipSegments = ['collection-points'];

  // Build breadcrumb items
  const breadcrumbItems: Array<{ label: string; path: string }> = [];

  let currentPath = '';
  pathSegments.forEach((segment) => {
    currentPath += `/${segment}`;
    // Skip segments that don't have their own page
    if (skipSegments.includes(segment)) {
      return;
    }
    breadcrumbItems.push({
      label: getLabel(segment),
      path: currentPath,
    });
  });

  // Mark last item
  const itemsWithLast = breadcrumbItems.map((item, index) => ({
    ...item,
    isLast: index === breadcrumbItems.length - 1,
  }));

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
      <Breadcrumbs
        separator={<NavigateNextIcon fontSize="small" />}
        aria-label="breadcrumb"
      >
        {/* Home/Dashboard link */}
        <Link
          component={RouterLink}
          to="/dashboard"
          sx={{
            display: 'flex',
            alignItems: 'center',
            color: 'text.secondary',
            textDecoration: 'none',
            '&:hover': {
              color: 'primary.main',
              textDecoration: 'underline',
            },
          }}
        >
          <HomeIcon sx={{ mr: 0.5, fontSize: 20 }} />
          Dashboard
        </Link>

        {/* Path segments */}
        {itemsWithLast
          .filter((item) => item.label !== 'Dashboard') // Don't duplicate dashboard
          .map((item) =>
            item.isLast ? (
              <Typography
                key={item.path}
                color="text.primary"
                sx={{ fontWeight: 500 }}
              >
                {item.label}
              </Typography>
            ) : (
              <Link
                key={item.path}
                component={RouterLink}
                to={item.path}
                sx={{
                  color: 'text.secondary',
                  textDecoration: 'none',
                  '&:hover': {
                    color: 'primary.main',
                    textDecoration: 'underline',
                  },
                }}
              >
                {item.label}
              </Link>
            )
          )}
      </Breadcrumbs>
    </Box>
  );
}
