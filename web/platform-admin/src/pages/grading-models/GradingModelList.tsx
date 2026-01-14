/**
 * Grading Model List Page
 *
 * Displays all grading models in the platform.
 * Placeholder - full implementation in Story 9.6.
 */

import { Box, Typography, Paper } from '@mui/material';
import GradingIcon from '@mui/icons-material/Grading';

/**
 * Grading model list page component.
 */
export function GradingModelList(): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Grading Models
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <GradingIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Grading Model Management
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Full implementation coming in Story 9.6
        </Typography>
      </Paper>
    </Box>
  );
}
