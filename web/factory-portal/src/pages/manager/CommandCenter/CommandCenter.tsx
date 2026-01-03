/**
 * Command Center Page
 *
 * Factory Manager's main dashboard showing farmer quality overview.
 * This is a placeholder component for Story 0.5.7.
 */

import { Box, Typography, Paper } from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';

/**
 * Command Center placeholder component.
 *
 * Will be implemented in a future story with:
 * - Farmer quality grid with WIN/WATCH/ACTION categories
 * - Quick actions for contacting farmers
 * - Real-time quality event updates
 */
export function CommandCenter(): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Command Center
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
        <DashboardIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          Coming Soon
        </Typography>
        <Typography variant="body2" color="text.secondary" textAlign="center">
          The Command Center dashboard will display farmer quality metrics,
          <br />
          categorized by WIN, WATCH, and ACTION status.
        </Typography>
      </Paper>
    </Box>
  );
}
