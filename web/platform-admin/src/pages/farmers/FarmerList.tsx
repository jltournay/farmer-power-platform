/**
 * Farmer List Page
 *
 * Displays all farmers with filtering capabilities.
 * Placeholder - full implementation in Story 9.5.
 */

import { Box, Typography, Paper } from '@mui/material';
import AgricultureIcon from '@mui/icons-material/Agriculture';

/**
 * Farmer list page component.
 */
export function FarmerList(): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Farmers
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <AgricultureIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Farmer Management
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Full implementation coming in Story 9.5
        </Typography>
      </Paper>
    </Box>
  );
}
