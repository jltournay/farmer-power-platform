/**
 * Collection Point Detail Page
 *
 * Displays collection point configuration within a factory hierarchy.
 * Placeholder - full implementation in Story 9.4.
 */

import { useParams } from 'react-router-dom';
import { Box, Typography, Paper } from '@mui/material';
import LocationOnIcon from '@mui/icons-material/LocationOn';

/**
 * Collection point detail page component.
 */
export function CollectionPointDetail(): JSX.Element {
  const { factoryId, cpId } = useParams<{ factoryId: string; cpId: string }>();

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Collection Point: {cpId}
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Factory: {factoryId}
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <LocationOnIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Collection Point Configuration
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Full implementation coming in Story 9.4
        </Typography>
      </Paper>
    </Box>
  );
}
