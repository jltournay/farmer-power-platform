/**
 * Region List Page
 *
 * Displays all regions in the platform.
 * Placeholder - full implementation in Story 9.2.
 */

import { Box, Typography, Paper } from '@mui/material';
import PublicIcon from '@mui/icons-material/Public';

/**
 * Region list page component.
 */
export function RegionList(): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Regions
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <PublicIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Region Management
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Full implementation coming in Story 9.2
        </Typography>
      </Paper>
    </Box>
  );
}
