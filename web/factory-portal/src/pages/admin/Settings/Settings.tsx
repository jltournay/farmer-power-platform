/**
 * Settings Page
 *
 * Factory Admin settings and configuration.
 * This is a placeholder component for Story 0.5.7.
 */

import { Box, Typography, Paper } from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';

/**
 * Settings placeholder component.
 *
 * Will be implemented in a future story with:
 * - Factory configuration
 * - User management
 * - Notification preferences
 * - Integration settings
 */
export function Settings(): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Settings
      </Typography>

      <Paper
        sx={{
          p: 4,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 300,
          backgroundColor: 'background.paper',
        }}
      >
        <SettingsIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          Coming Soon
        </Typography>
        <Typography variant="body2" color="text.secondary" textAlign="center">
          Factory settings and configuration options
          <br />
          will be available here.
        </Typography>
      </Paper>
    </Box>
  );
}
