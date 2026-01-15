/**
 * AdminShell Component
 *
 * Main layout wrapper with sidebar + content area + breadcrumb header.
 * Generic layout component that can be used by any admin application.
 *
 * Accessibility:
 * - Proper landmark regions (main, nav)
 * - Focus management for sidebar toggle
 */

import { Box, useTheme } from '@mui/material';
import type { ReactNode } from 'react';
import type { BreadcrumbItem } from '../Breadcrumb';

/** AdminShell component props */
export interface AdminShellProps {
  /** Sidebar content (pass a Sidebar component) */
  sidebar: ReactNode;
  /** Breadcrumb items for navigation trail */
  breadcrumbs?: BreadcrumbItem[];
  /** Optional breadcrumb component to render */
  breadcrumbComponent?: ReactNode;
  /** Optional header component to render above content */
  header?: ReactNode;
  /** Main page content */
  children: ReactNode;
  /** Current sidebar width in pixels */
  sidebarWidth?: number;
  /** Whether sidebar is currently open */
  sidebarOpen?: boolean;
}

/**
 * AdminShell provides the main application layout structure.
 *
 * @example
 * ```tsx
 * <AdminShell
 *   sidebar={<Sidebar items={menuItems} open={isOpen} onToggle={toggle} />}
 *   breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Farmers' }]}
 *   sidebarWidth={240}
 *   sidebarOpen={isOpen}
 * >
 *   <PageContent />
 * </AdminShell>
 * ```
 */
export function AdminShell({
  sidebar,
  breadcrumbComponent,
  header,
  children,
  sidebarWidth = 240,
  sidebarOpen = true,
}: AdminShellProps): JSX.Element {
  const theme = useTheme();
  const currentWidth = sidebarOpen ? sidebarWidth : 64;

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <Box component="nav" aria-label="Main navigation">
        {sidebar}
      </Box>

      {/* Main content area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          marginLeft: `${currentWidth}px`,
          transition: theme.transitions.create('margin', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
        }}
      >
        {/* Header */}
        {header}

        {/* Breadcrumb navigation */}
        {breadcrumbComponent}

        {/* Page content */}
        <Box
          sx={{
            flexGrow: 1,
            p: 3,
            backgroundColor: 'background.default',
            overflow: 'auto',
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
}

export default AdminShell;
