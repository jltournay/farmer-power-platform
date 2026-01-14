/**
 * Factory List Page
 *
 * Displays all factories in the platform.
 * Placeholder - full implementation in Story 9.3.
 */

import { Box, Typography, Paper } from '@mui/material';
import FactoryIcon from '@mui/icons-material/Factory';

/**
 * Factory list page component.
 */
export function FactoryList(): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Factories
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <FactoryIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Factory Management
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Full implementation coming in Story 9.3
        </Typography>
      </Paper>
    </Box>
  );
}
