/**
 * Factory Detail Page
 *
 * Displays factory configuration and its collection points.
 * Placeholder - full implementation in Story 9.3.
 */

import { useParams } from 'react-router-dom';
import { Box, Typography, Paper } from '@mui/material';
import FactoryIcon from '@mui/icons-material/Factory';

/**
 * Factory detail page component.
 */
export function FactoryDetail(): JSX.Element {
  const { factoryId } = useParams<{ factoryId: string }>();

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Factory: {factoryId}
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <FactoryIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Factory Configuration
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Full implementation coming in Story 9.3
        </Typography>
      </Paper>
    </Box>
  );
}
