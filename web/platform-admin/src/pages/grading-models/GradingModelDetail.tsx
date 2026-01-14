/**
 * Grading Model Detail Page
 *
 * Displays and edits a specific grading model.
 * Placeholder - full implementation in Story 9.6.
 */

import { useParams } from 'react-router-dom';
import { Box, Typography, Paper } from '@mui/material';
import GradingIcon from '@mui/icons-material/Grading';

/**
 * Grading model detail page component.
 */
export function GradingModelDetail(): JSX.Element {
  const { modelId } = useParams<{ modelId: string }>();

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Grading Model: {modelId}
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <GradingIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Grading Model Configuration
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Full implementation coming in Story 9.6
        </Typography>
      </Paper>
    </Box>
  );
}
