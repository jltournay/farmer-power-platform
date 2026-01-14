/**
 * Farmer Detail Page
 *
 * Displays and edits a specific farmer.
 * Placeholder - full implementation in Story 9.5.
 */

import { useParams } from 'react-router-dom';
import { Box, Typography, Paper } from '@mui/material';
import AgricultureIcon from '@mui/icons-material/Agriculture';

/**
 * Farmer detail page component.
 */
export function FarmerDetail(): JSX.Element {
  const { farmerId } = useParams<{ farmerId: string }>();

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Farmer: {farmerId}
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <AgricultureIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Farmer Details
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Full implementation coming in Story 9.5
        </Typography>
      </Paper>
    </Box>
  );
}
