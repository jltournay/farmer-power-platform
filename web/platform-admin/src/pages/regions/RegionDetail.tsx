/**
 * Region Detail Page
 *
 * Displays and edits a specific region.
 * Placeholder - full implementation in Story 9.2.
 */

import { useParams } from 'react-router-dom';
import { Box, Typography, Paper } from '@mui/material';
import PublicIcon from '@mui/icons-material/Public';

/**
 * Region detail page component.
 */
export function RegionDetail(): JSX.Element {
  const { regionId } = useParams<{ regionId: string }>();

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Region: {regionId}
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <PublicIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Region Configuration
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Full implementation coming in Story 9.2
        </Typography>
      </Paper>
    </Box>
  );
}
